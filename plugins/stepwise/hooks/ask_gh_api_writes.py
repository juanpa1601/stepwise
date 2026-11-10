"""PreToolUse hook (Bash and PowerShell): ask before a ``gh api`` call that writes to GitHub.

Reads the hook JSON from stdin, splits the command with ``shlex`` and finds every ``gh api`` call: alone, after
``&&``, ``||``, ``;``, ``|`` or ``&``, or inside ``$(...)`` and backticks (quoted or not). It answers
``permissionDecision: ask``, with a reason that shows the method and the path, when a call:

- sets a method other than ``GET`` (or ``HEAD``) with ``-X``, ``-X<METHOD>``, ``--method <METHOD>`` or
  ``--method=<METHOD>``, before or after the path;
- sends fields or a body (``-f``, ``-F``, ``--field``, ``--raw-field``, ``--input``, attached forms included) without
  an explicit ``GET``: ``gh`` then sends a ``POST``;
- is ``gh api graphql`` with a ``mutation`` in its fields, or with a query it cannot read (``-F query=@<file>``,
  ``--input``, a ``$(...)`` value, a variable such as ``query="$Q"``).

Each line is its own command (a ``\\`` in Bash or a backtick in PowerShell before the line break continues it).
In PowerShell the escape character is the backtick and ``\\`` is plain, and an unquoted Windows path to ``gh`` or
``gh.exe`` counts as ``gh``.

Reads pass silently (``{}``): ``branches/<b> -q .commit.sha``, ``contents`` with the raw ``Accept``,
``git/trees/<sha>?recursive=1``, ``--paginate``, ``-X GET -f per_page=100``, a graphql query without ``mutation``.
Text that only mentions ``gh api`` inside quotes (``grep "gh api -X POST" x.md``) and other commands
(``git commit -F <file>``) pass too.

``ask`` rather than ``deny``: ``/audit`` and ``/close`` publish with ``gh api`` after the user approves. The hook
reaches every project with the plugin, subagents included. The ``ask`` rules of each project's
``.claude/settings.json`` stay as the text backup (ADR §3.2).

Limits: a call built at run time or nested inside ``sh -c "..."`` is not seen. A hook ``ask`` is denied in
``dontAsk`` mode. Any internal error prints ``{}`` and exits with 0.

Part of the ``stepwise`` plugin. Standard library only, Python 3.10 or later; ``hooks.json`` runs it with
``python3 "${CLAUDE_PLUGIN_ROOT}/hooks/ask_gh_api_writes.py"``.
"""

import json
import re
import shlex
import sys

_SHELL_TOOLS: frozenset[str] = frozenset({"Bash", "PowerShell"})
_SEPARATORS: frozenset[str] = frozenset({"&&", "||", ";", "|", "&", "(", ")", ";;", "|&"})
_READ_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})
_FIELD_FLAGS: frozenset[str] = frozenset({"-f", "-F", "--field", "--raw-field"})
_VALUE_FLAGS: frozenset[str] = frozenset({
    "-X", "--method", "-f", "-F", "--field", "--raw-field", "--input", "-H", "--header", "-q", "--jq", "-t",
    "--template", "--hostname", "--cache", "-p", "--preview",
})
_MUTATION: re.Pattern[str] = re.compile(r"\bmutation\b", re.IGNORECASE)


def _split_lines(
    command: str,
    powershell: bool
) -> str:
    """Join continued lines (``\\`` or a PowerShell backtick before the line break) and turn every other line break
    outside quotes into ``;``, so each line is its own command. An escaped quote (``\\'`` or ``\\"`` in Bash, a
    backtick before it in PowerShell, where ``\\`` is a plain character) does not open or close a quote."""
    escape: str = "`" if powershell else "\\"
    command = re.sub(re.escape(escape) + r"\r?\n", " ", command)
    result: list[str] = []
    quote: str = ""
    index: int = 0
    while index < len(command):
        char: str = command[index]
        if quote != "'" and char in escape and index + 1 < len(command):
            result.append(command[index:index + 2])
            index += 2
            continue
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char == "\n":
            char = " ; "
        result.append(char)
        index += 1
    return "".join(result)


def _tokens(
    command: str,
    powershell: bool
) -> list[str]:
    """Split ``command`` like a POSIX shell, with operators and line breaks as their own tokens. In PowerShell the
    escape character is the backtick, not ``\\``."""
    lexer: shlex.shlex = shlex.shlex(_split_lines(command, powershell), posix=True, punctuation_chars=True)
    if powershell:
        lexer.escape = "`"
    lexer.whitespace_split = True
    return list(lexer)


def _substitutions(token: str) -> list[str]:
    """Return the text of every ``$(...)`` and backtick substitution inside ``token`` (the raw command text)."""
    found: list[str] = re.findall(r"`([^`]*)`", token)
    start: int = token.find("$(")
    while start != -1:
        depth: int = 0
        end: int = start + 1
        while end < len(token):
            if token[end] == "(":
                depth += 1
            elif token[end] == ")":
                depth -= 1
                if depth == 0:
                    break
            end += 1
        found.append(token[start + 2:end])
        start = token.find("$(", end)
    return found


def _is_gh(token: str) -> bool:
    """Return whether ``token`` runs the ``gh`` executable. An unquoted Windows path loses its backslashes in
    ``shlex`` (``C:\\tools\\gh.exe`` becomes ``C:toolsgh.exe``), so a drive-letter token ending in ``gh`` or
    ``gh.exe`` counts too."""
    name: str = re.split(r"[\\/]", token)[-1].lower()
    return name in ("gh", "gh.exe") or re.fullmatch(r"[a-z]:.*gh(\.exe)?", token, re.IGNORECASE) is not None


def _hidden_query(query: str) -> bool:
    """Return whether a graphql ``query`` cannot be read from the command: a file (``@x``), a variable (``$Q``,
    ``${Q}``, ``$q`` in PowerShell), a ``${`` or a ``$`` right after a word character anywhere (a GraphQL variable
    is ``$name`` after a space or a bracket, never ``${`` nor ``mu$X``) or anything without the braces every query
    has."""
    return query.startswith(("@", "$")) or re.search(r"\w\$|\$\{", query) is not None or "{" not in query


def _write(args: list[str]) -> str | None:
    """Return ``"<METHOD> <path>"`` when the ``gh api`` arguments ``args`` write, else ``None``."""
    method: str | None = None
    has_fields: bool = False
    has_input: bool = False
    path: str = ""
    values: list[str] = []
    index: int = 0
    while index < len(args):
        arg: str = args[index]
        value: str | None = None
        flag: str = arg
        if arg.startswith("--") and "=" in arg:
            flag, value = arg.split("=", 1)
        elif re.fullmatch(r"-[XfFHqtp].+", arg):
            flag, value = arg[:2], arg[2:]
        if flag in _VALUE_FLAGS and value is None:
            index += 1
            value = args[index] if index < len(args) else ""
        if flag in ("-X", "--method"):
            method = (value or "").upper()
        elif flag in _FIELD_FLAGS:
            has_fields = True
            values.append(value or "")
        elif flag == "--input":
            has_input = True
        elif not flag.startswith("-") and not path:
            path = arg
        index += 1
    if path == "graphql":
        unreadable: bool = has_input or any(
            "$(" in v or "`" in v or (v.startswith("query=") and _hidden_query(v[6:])) for v in values
        )
        if unreadable or any(_MUTATION.search(v) for v in values):
            return "POST graphql"
        return None
    if method is not None:
        return None if method in _READ_METHODS else f"{method} {path}"
    if has_fields or has_input:
        return f"POST {path}"
    return None


def find_write(
    command: str,
    powershell: bool = False
) -> str | None:
    """Return ``"<METHOD> <path>"`` of the first ``gh api`` write in ``command``, else ``None``."""
    for inner in _substitutions(command):
        found: str | None = find_write(inner, powershell)
        if found:
            return found
    try:
        tokens: list[str] = _tokens(command, powershell)
    except ValueError:
        tokens = _split_lines(command, powershell).split()
    for index in range(len(tokens) - 1):
        if not (_is_gh(tokens[index]) and tokens[index + 1] == "api"):
            continue
        args: list[str] = []
        for token in tokens[index + 2:]:
            if token in _SEPARATORS or _is_gh(token):
                break
            args.append(token)
        found = _write(args)
        if found:
            return found
    return None


def main() -> None:
    """Print the hook decision: ask with a reason, or ``{}``."""
    try:
        payload: object = json.load(sys.stdin)
    except ValueError:
        print("{}")
        return
    if not isinstance(payload, dict) or payload.get("tool_name") not in _SHELL_TOOLS:
        print("{}")
        return
    tool_input: object = payload.get("tool_input")
    command: object = tool_input.get("command") if isinstance(tool_input, dict) else None
    powershell: bool = payload.get("tool_name") == "PowerShell"
    found: str | None = find_write(command, powershell) if isinstance(command, str) else None
    if not found:
        print("{}")
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"gh api writes to GitHub ({found}). Approve only if you asked for this change; a subagent must "
                "never publish."
            ),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - a broken hook must never block a tool call
        print("{}")
    sys.exit(0)
