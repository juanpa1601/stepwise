"""PreToolUse hook (Read, Grep, Glob, Edit, MultiEdit, Write, Bash, PowerShell): deny access to ``.env`` files.

Reads the hook JSON from stdin and denies (``permissionDecision: deny``) when the tool targets a file whose name is
``.env`` or starts with ``.env.`` (``.env.docker``, ``.env.local``, ``.env.production``...):

- ``Read``, ``Edit``, ``MultiEdit`` and ``Write`` through ``file_path``;
- ``Grep`` through ``path`` (a file) or ``glob`` (a pattern that names an ``.env`` file); its ``pattern`` is a regex
  over file contents, not a path, so searching the text ``.env`` in the code passes;
- ``Glob`` through ``path`` or ``pattern``;
- ``Bash`` and ``PowerShell`` when the command names one anywhere: any path, quoted or not, as an argument, an
  option value (``--env-file=.env``, ``-d @.env``, ``-v .env:/app``), a glob (``.env*``) or inside inline code
  (``python -c "open('.env')"``). That includes ``cp .env.example .env``: creating ``.env`` is left to the user, as
  with ``Write``.

The shell check reads the whole command text, so it also denies a command that only *mentions* an ``.env`` name:
``git commit -m "... .env ..."``, ``gh pr create --title "... .env ..."``, ``grep -rn '\\.env' src``. Pass messages,
titles and bodies through a file (``git commit -F <file>``, ``--body-file``) or write them without the literal name.

Templates meant to be read and committed pass: ``.env.example``, ``.env.sample``, ``.env.template`` and ``.env.dist``.
Look-alikes pass too: ``.venv/``, ``.env/`` used as a folder (``.env/bin/python``), ``environment.py``, ``.envrc``,
``env.py``, ``ENV_VAR=1``, ``printenv``, ``$env:PATH``. Anything else prints ``{}`` and runs unchanged.

Limits: this is a guard against mistakes, not a security boundary. A program that reads ``.env`` by itself
(``manage.py runserver``, ``docker compose up``), a name built at run time and ``Grep`` over a folder that holds an
``.env`` not ignored by git are not detected. Real secrets should not live in the project tree if the risk matters.

Part of the ``stepwise`` plugin (layer 1). Standard library only, Python 3.10 or later; ``hooks.json`` runs it with
``python3 "${CLAUDE_PLUGIN_ROOT}/hooks/block_env_access.py"``.
"""

import json
import re
import sys

REASON: str = (
    "Access to .env files is blocked: they hold secrets. Do not read, copy or print the file, from a tool or the "
    "shell. Name the variable you need and ask the user for its value (or ask them to run the command themselves "
    "and paste only what is safe to share); if the task truly needs the file, stop and ask the user."
)
ALLOWED_TEMPLATES: frozenset[str] = frozenset({".env.example", ".env.sample", ".env.template", ".env.dist"})
_FILE_TOOLS: frozenset[str] = frozenset({"Read", "Edit", "MultiEdit", "Write"})
_SHELL_TOOLS: frozenset[str] = frozenset({"Bash", "PowerShell"})
# An ``.env`` name inside a glob: start of the pattern or after a separator, then ``.env`` at the end or before ``.``,
# ``*``, ``?``, ``[`` or ``{``.
_GLOB_ENV: re.Pattern[str] = re.compile(r"(?:^|[/\\{,])\.env(?=$|[.*?\[{,}])")
# An ``.env`` file named in a shell command: ``.env`` (plus ``.<suffix>``, globs included) after a word boundary of the
# shell (start, blank, quote, separator, operator, ``=``, ``:``, ``@`` as in ``curl -d @.env``) and followed by the end
# of the word, a glob character (``.env*``, ``.env?``) or ``:`` (``-v .env:/app/x``). A ``/`` or ``\`` after it means a
# folder (``.env/bin/python``), which passes. A glob or brace suffix is never a template (``.env.examp*``,
# ``.env.{local,production}``).
_SHELL_ENV: re.Pattern[str] = re.compile(
    r"(?:^|(?<=[\s'\"`=:@/\\(){}<>|;&,]))(\.env(?:\.[\w.\-*?\[\]{}]+)?)(?=$|[\s'\"`(){}<>|;&,:*?\[])"
)


def _name(path: str) -> str:
    """Return the last component of a path written with ``/`` or ``\\``."""
    return path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def is_env_file(path: str) -> bool:
    """Return whether ``path`` names an ``.env`` file that is not a template."""
    name: str = _name(path).lower()
    if name in ALLOWED_TEMPLATES:
        return False
    return name == ".env" or name.startswith(".env.")


def _glob_names_env(pattern: str) -> bool:
    """Return whether a ``Grep`` or ``Glob`` pattern can match an ``.env`` file other than the templates."""
    lowered: str = pattern.lower()
    if lowered in ALLOWED_TEMPLATES or any(lowered.endswith(f"/{name}") for name in ALLOWED_TEMPLATES):
        return False
    return bool(_GLOB_ENV.search(lowered))


def command_names_env(command: str) -> bool:
    """Return whether a shell command names an ``.env`` file that is not a template."""
    return any(match.rstrip(".") not in ALLOWED_TEMPLATES for match in _SHELL_ENV.findall(command.lower()))


def violation(
    tool_name: str,
    tool_input: dict[str, object]
) -> bool:
    """Return whether the tool call reads or writes an ``.env`` file."""
    if tool_name in _FILE_TOOLS:
        file_path: object = tool_input.get("file_path")
        return isinstance(file_path, str) and is_env_file(file_path)
    if tool_name in ("Grep", "Glob"):
        path: object = tool_input.get("path")
        pattern: object = tool_input.get("glob" if tool_name == "Grep" else "pattern")
        return (isinstance(path, str) and is_env_file(path)) or (
            isinstance(pattern, str) and _glob_names_env(pattern)
        )
    if tool_name in _SHELL_TOOLS:
        command: object = tool_input.get("command")
        return isinstance(command, str) and command_names_env(command)
    return False


def main() -> None:
    """Print the hook decision: deny with a reason, or ``{}``."""
    try:
        payload: object = json.load(sys.stdin)
    except ValueError:
        print("{}")
        return
    if not isinstance(payload, dict):
        print("{}")
        return
    tool_input: object = payload.get("tool_input")
    if not isinstance(tool_input, dict) or not violation(str(payload.get("tool_name", "")), tool_input):
        print("{}")
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - a broken hook must never block a tool call
        print("{}")
    sys.exit(0)
