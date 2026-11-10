"""PreToolUse hook (Bash and PowerShell): deny shell edits of repository files; the Edit tool must be used instead.

Reads the hook JSON from stdin and denies (``permissionDecision: deny``) a Bash command that, on a file inside
``$CLAUDE_PROJECT_DIR``:

- runs ``sed -i`` / ``sed --in-place`` or ``perl -i`` (any flag cluster with ``i``, such as ``-i.bak`` or ``-pi``);
- redirects with ``>``, ``>>`` or ``&>`` to a ``.py``, ``.md``, ``.toml``, ``.yml``, ``.yaml``, ``.json``, ``.in`` or
  ``.txt`` file (``cat <<EOF > file`` included);
- pipes into ``tee`` (with or without ``-a``) towards one of those files.

It also denies, wherever the target file is (scripts that write files skip format hooks, path rules and the
``/rewind`` checkpoints), and also inside ``sh -c "..."`` / ``bash -c "..."`` (``docker compose run|exec`` included):

- inline Python (``python``, ``python3``, ``py``, any directory or ``.exe``) run with ``-c`` or from stdin (``-``, a
  heredoc or a pipe) whose code holds a write API: ``open(`` with a ``w``, ``a``, ``x`` or ``+`` mode,
  ``.write_text(``, ``.write_bytes(``, ``.write(`` (not ``sys.stdout``/``sys.stderr``), ``shutil.copy*``,
  ``shutil.move``, ``os.replace``, ``os.rename``, ``os.remove``, ``.unlink(`` or ``.rename(``;
- a ``.py`` script that git does not list (outside the repository, Git Bash ``/tmp`` included, or in an ignored path)
  whose content holds one of those APIs; a script that does not exist yet is judged by the command text, since the
  same command usually creates it. An untracked, not ignored script inside the project passes: it is reviewed with
  the diff (nothing checks that it was written with Write or Edit; a ``cp`` into the project also makes it pass);
- ``node -e`` / ``node -p`` with ``fs.writeFile``, ``fs.appendFile``, ``fs.rename``, ``fs.copyFile`` or ``fs.unlink``
  (``Sync`` and ``fs.promises`` variants included).

Allowed: redirections to ``/dev/null``, to the temporary directory or to the scratchpad (anything outside the
project), descriptor duplications such as ``2>&1``, reads (``sed -n``, ``grep``, ``cat`` without redirection),
``python -m`` (pytest, pip, ruff...), scripts git lists (``manage.py``, ``scripts/*.py``, the hooks, the tests,
new tests not yet committed), read-only inline Python, and every ``git`` and ``docker compose`` command except for
the script checks. Anything else prints ``{}`` and runs unchanged.

Heredoc bodies are ignored by the redirection checks (their ``>`` are content, not redirections). Paths are resolved
against the command's ``cd <dir> &&`` prefix, if any, and otherwise the hook ``cwd``; Git Bash paths such as
``/c/Users/...`` are mapped to ``C:/Users/...`` before comparing them with the project directory.

PowerShell tool (matcher ``Bash|PowerShell``): ``tool_name == "PowerShell"`` sends the command to
``powershell_violation``, which tokenizes it with PowerShell's quoting (``'``, ``"``, backtick, here-strings) and
denies ``Set-Content``/``Add-Content``/``Out-File``/``Tee-Object``, ``>``/``>>``/``*>``, ``[IO.File]::Write*``,
``New-Item -Value`` and ``Copy-Item``/``Move-Item``/``Rename-Item`` towards a ``.py`` on a protected repository file,
plus the same script writes (``python -c``, ``@'…'@ | python -``, ``node -e``, ``sh -c``) and ``powershell -Command``
recursively. ``> $null``, ``2>$null``, ``Out-Null``, reads and writes outside the project pass. Standard library only.

Limits: this is a heuristic over the command text. An obfuscated write (``exec``, base64, ``getattr``, a renamed
import) is not detected; the team rule (edit only with Edit or Write) remains the norm.

Part of the ``stepwise`` plugin (layer 1). Standard library only, Python 3.10 or later; ``hooks.json`` runs it with
``python3 "${CLAUDE_PLUGIN_ROOT}/hooks/block_inplace_edits.py"`` on ``Bash|PowerShell``.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

REASON: str = (
    "Editing files from the shell or with scripts is blocked: use Read + Edit (or Write for a new file). "
    "To move a block between files: Write in the destination and Edit in the source. "
    "If it truly cannot be done that way, stop and ask the user."
)
PROTECTED_SUFFIXES: frozenset[str] = frozenset({".py", ".md", ".toml", ".yml", ".yaml", ".json", ".in", ".txt"})
SAFE_TARGETS: frozenset[str] = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr", "NUL", "nul"})

# `>`, `>>` or `&>` (optionally after a descriptor number), but not `>&N` duplications.
_REDIRECT: re.Pattern[str] = re.compile(r"""(?<![<>])\d*&?>>?(?!&)\|?\s*("[^"]+"|'[^']+'|[^\s;&|<>()]+)""")
_INPLACE: re.Pattern[str] = re.compile(r"(?:^|[\s;&|(])(?:sed|perl)\s+(?:[^;&|]*\s)?(?:-[a-zA-Z]*i|--in-place)")
_TEE: re.Pattern[str] = re.compile(r"\|\s*tee\s+([^;&|]*)")
_CD: re.Pattern[str] = re.compile(r"""^\s*cd\s+("[^"]+"|'[^']+'|[^\s;&|]+)\s*&&""")
_SEGMENT_SPLIT: re.Pattern[str] = re.compile(r"&&|\|\||;|\n")
_EXEMPT: re.Pattern[str] = re.compile(r"^\s*(?:git\s|docker(?:\s+|-)compose\b)")
_GIT_BASH_DRIVE: re.Pattern[str] = re.compile(r"^/([a-zA-Z])(/|$)")
_PYTHON: re.Pattern[str] = re.compile(r"^(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?$", re.IGNORECASE)
_NODE: re.Pattern[str] = re.compile(r"^node(?:\.exe)?$", re.IGNORECASE)
_SHELL: re.Pattern[str] = re.compile(r"^(?:sh|bash|dash|zsh)(?:\.exe)?$", re.IGNORECASE)
_SHELL_COMMAND_FLAG: re.Pattern[str] = re.compile(r"^-[a-zA-Z]*c[a-zA-Z]*$")
_PYTHON_CODE_FLAG: re.Pattern[str] = re.compile(r"^-[a-zA-Z]*c$")
_OPERATOR: re.Pattern[str] = re.compile(r"^[;&|()<>]+$")
_PYTHON_FLAGS_WITH_VALUE: frozenset[str] = frozenset({"-X", "-W", "-Q"})
_NODE_CODE_FLAGS: frozenset[str] = frozenset({"-e", "-p", "--eval", "--print", "-pe"})
_PYTHON_WRITE: re.Pattern[str] = re.compile(
    r"""\bopen\s*\(.{0,200}?['"][rbt]*[wax+][rbtwax+]*['"]"""
    r"""|\.write_(?:text|bytes)\s*\("""
    r"""|(?<!stdout)(?<!stderr)\.write\s*\("""
    r"""|\bshutil\.(?:copy\w*|move)\s*\("""
    r"""|\bos\.(?:replace|rename|remove|unlink)\s*\("""
    r"""|\.(?:unlink|rename)\s*\("""
)
_NODE_WRITE: re.Pattern[str] = re.compile(
    r"(?:\bfs|\))(?:\.promises)?\.(?:writeFile|appendFile|rename|copyFile|unlink)(?:Sync)?\s*\("
)
_MAX_SHELL_DEPTH: int = 3
_GIT_TIMEOUT_SECONDS: float = 5.0
# Opening line of a heredoc (kept: it may carry a redirection), then its body up to the delimiter line (dropped).
_HEREDOC: re.Pattern[str] = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*)\n.*?\n[ \t]*\3[ \t]*(?=\n|$)", re.DOTALL)


def _unquote(token: str) -> str:
    """Strip one level of matching quotes."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def _split(text: str) -> list[str]:
    """Split shell words, falling back to whitespace when the quoting is unbalanced."""
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def _to_path(
    raw: str,
    base: Path
) -> Path:
    """Resolve a shell path (Git Bash or native) against ``base`` into a normalized absolute path."""
    text: str = os.path.expandvars(os.path.expanduser(_unquote(raw)))
    text = _GIT_BASH_DRIVE.sub(lambda match: f"{match.group(1)}:/", text)
    path: Path = Path(text)
    if not path.is_absolute():
        path = base / path
    return Path(os.path.normcase(os.path.abspath(path)))


def _inside(
    path: Path,
    project: Path
) -> bool:
    """Return whether ``path`` lies inside the project directory."""
    return path == project or project in path.parents


def _is_protected_target(
    raw: str,
    base: Path,
    project: Path
) -> bool:
    """Return whether writing to ``raw`` would touch a protected file of the repository."""
    if raw.startswith("&") or raw in SAFE_TARGETS:
        return False
    path: Path = _to_path(raw, base)
    return path.suffix.lower() in PROTECTED_SUFFIXES and _inside(path, project)


def _inplace_edits_project_file(
    part: str,
    base: Path,
    project: Path
) -> bool:
    """Return whether a ``sed -i`` / ``perl -i`` command edits a file inside the project.

    Every non-flag operand counts (the sed script included): one that resolves inside the project to an existing file
    or to a protected suffix denies the command, so an ambiguous shape inside the project is denied conservatively.
    """
    for operand in _split(part)[1:]:
        if operand.startswith("-"):
            continue
        path: Path = _to_path(operand, base)
        if _inside(path, project) and (path.is_file() or path.suffix.lower() in PROTECTED_SUFFIXES):
            return True
    return False


def _words(text: str) -> list[str]:
    """Split a command into shell words, with ``;``, ``&&``, ``|``, ``<``... as separate tokens."""
    lexer: shlex.shlex = shlex.shlex(
        text,
        posix=True,
        punctuation_chars=True
    )
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return text.split()


def _program(word: str) -> str:
    """Return the program name of a word (``/opt/venv/bin/python3`` → ``python3``)."""
    return word.replace("\\", "/").rsplit("/", 1)[-1]


def _script_path(
    raw: str,
    base: Path
) -> Path:
    """Resolve a script path; on Windows, Git Bash ``/tmp/...`` is the user temporary directory."""
    if os.name == "nt" and raw.startswith("/tmp/"):
        raw = f"{tempfile.gettempdir()}/{raw[len('/tmp/'):]}"
    return _to_path(raw, base)


def _in_diff(
    path: Path,
    project: Path
) -> bool:
    """Return whether git lists ``path``: tracked, or untracked and not ignored (so it shows in the step's diff).

    Such a script is reviewed with the diff. The pathspec is case-insensitive, since paths are normcased.
    """
    if not _inside(path, project):
        return False
    relative: str = path.relative_to(project).as_posix()
    try:
        completed: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603 - fixed git arguments
            [  # noqa: S607
                "git", "-C", str(project), "ls-files", "--cached", "--others", "--exclude-standard",
                "--", f":(icase,literal){relative}"
            ],
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and bool(completed.stdout.strip())


def _untracked_script_writes(
    raw: str,
    command: str,
    base: Path,
    project: Path
) -> bool:
    """Return whether a ``.py`` script that git does not list (outside the project or ignored) holds a write API.

    A script inside the project that git lists (tracked, or untracked and not ignored) passes: it shows in the diff,
    where it is reviewed. A script that cannot be read yet is judged by the whole command text: the same command
    usually creates it (``cat > /tmp/x.py <<EOF ... EOF; python /tmp/x.py``).
    """
    path: Path = _script_path(raw, base)
    if _in_diff(path, project):
        return False
    try:
        content: str = path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except OSError:
        return bool(_PYTHON_WRITE.search(command))
    return bool(_PYTHON_WRITE.search(content))


def _python_writes(
    words: list[str],
    start: int,
    command: str,
    base: Path,
    project: Path
) -> bool:
    """Return whether the Python interpreter whose arguments begin at ``words[start]`` writes files.

    ``-c`` checks its code; ``-m`` runs a module and passes; ``-``, a heredoc, a pipe or no script reads the code from
    stdin, so the whole command (heredoc bodies included) is checked; a ``.py`` operand is checked by
    ``_untracked_script_writes``.
    """
    position: int = start
    while position < len(words):
        word: str = words[position]
        if _PYTHON_CODE_FLAG.match(word):
            return position + 1 < len(words) and bool(_PYTHON_WRITE.search(words[position + 1]))
        if word == "-m":
            return False
        if word == "<" and position + 1 < len(words):
            script: str = words[position + 1]
            return script.lower().endswith(".py") and _untracked_script_writes(script, command, base, project)
        if word == "-" or _OPERATOR.match(word):
            return bool(_PYTHON_WRITE.search(command))
        if word in _PYTHON_FLAGS_WITH_VALUE:
            position += 2
            continue
        if word.startswith("-"):
            position += 1
            continue
        return word.lower().endswith(".py") and _untracked_script_writes(word, command, base, project)
    return bool(_PYTHON_WRITE.search(command))


def _script_writes(
    command: str,
    base: Path,
    project: Path,
    depth: int = 0
) -> bool:
    """Return whether ``command`` writes files through inline Python or Node, or an untracked Python script.

    Every word is inspected, not only the first of a segment, so ``uv run python``, ``docker compose exec web python``
    and ``.venv/Scripts/python.exe`` are covered; ``sh -c "..."`` strings are inspected recursively.
    """
    if depth > _MAX_SHELL_DEPTH:
        return False
    words: list[str] = _words(_HEREDOC.sub(r"\1", command))
    for index, word in enumerate(words):
        program: str = _program(word)
        following: str | None = words[index + 1] if index + 1 < len(words) else None
        code: str | None = words[index + 2] if index + 2 < len(words) else None
        if _SHELL.match(program) and following and _SHELL_COMMAND_FLAG.match(following) and code is not None:
            if _script_writes(code, base, project, depth + 1):
                return True
        elif _PYTHON.match(program):
            if _python_writes(words, index + 1, command, base, project):
                return True
        elif _NODE.match(program) and following in _NODE_CODE_FLAGS and code is not None:
            if _NODE_WRITE.search(code):
                return True
    return False


def violation(
    command: str,
    cwd: Path,
    project: Path
) -> bool:
    """Return whether ``command`` edits a repository file in place from the shell, or writes files with a script."""
    base: Path = cwd
    cd_match: re.Match[str] | None = _CD.match(command)
    if cd_match:
        base = _to_path(cd_match.group(1), cwd)
    if _script_writes(command, base, project):
        return True
    without_bodies: str = _HEREDOC.sub(r"\1", command)
    for segment in _SEGMENT_SPLIT.split(without_bodies):
        if not segment.strip() or _EXEMPT.match(segment):
            continue
        for part in segment.split("|"):
            if _INPLACE.search(f" {part}") and _inplace_edits_project_file(part.strip(), base, project):
                return True
        for match in _REDIRECT.finditer(segment):
            if _is_protected_target(match.group(1), base, project):
                return True
        for match in _TEE.finditer(segment):
            for target in _split(match.group(1)):
                if not target.startswith("-") and _is_protected_target(target, base, project):
                    return True
    return False


# --- PowerShell ------------------------------------------------------------------------------------------------------

PS_SAFE_TARGETS: frozenset[str] = frozenset({"$null"})
_PS_ENV: re.Pattern[str] = re.compile(r"\$\{env:(\w+)\}|\$env:(\w+)", re.IGNORECASE)
_PS_PWD: re.Pattern[str] = re.compile(r"\$(?:\{PWD\}|PWD\b)", re.IGNORECASE)
_PS_STREAM: re.Pattern[str] = re.compile(r"^[1-6*]$")
_PS_SEPARATORS: str = "|;&(){}"
_PS_IO_FILE: re.Pattern[str] = re.compile(
    r"""\[(?:System\.)?IO\.File\]::(?:Write|Append)\w*\s*\(\s*(?:'([^']*)'|"([^"]*)")""",
    re.IGNORECASE
)
_PS_SHELL: re.Pattern[str] = re.compile(r"^(?:powershell|pwsh)(?:\.exe)?$", re.IGNORECASE)
_PS_ALIASES: dict[str, str] = {
    "sc": "set-content",
    "ac": "add-content",
    "tee": "tee-object",
    "ni": "new-item",
    "copy": "copy-item",
    "cp": "copy-item",
    "cpi": "copy-item",
    "move": "move-item",
    "mv": "move-item",
    "mi": "move-item",
    "ren": "rename-item",
    "rni": "rename-item",
    "cd": "set-location",
    "chdir": "set-location",
    "sl": "set-location",
    "pushd": "push-location",
}
_PS_WRITERS: frozenset[str] = frozenset({"set-content", "add-content", "out-file", "tee-object"})
_PS_LOCATION: frozenset[str] = frozenset({"set-location", "push-location"})
_PS_SWITCHES: frozenset[str] = frozenset({
    "append", "force", "nonewline", "noclobber", "passthru", "whatif", "confirm", "asbytestream", "recurse",
    "container", "verbose", "noprofile", "noninteractive", "nologo",
})
_PS_PATH: tuple[tuple[str, ...], frozenset[str]] = (("path", "filepath", "literalpath"), frozenset({"lp", "pspath"}))

PsToken = tuple[str, str]  # (kind, text); kind is word, op, redirect (text: the operator) or merge (2>&1)


def _ps_expand(
    text: str,
    cwd: Path
) -> str:
    """Expand ``$env:NAME``, ``${env:NAME}`` and ``$PWD`` in an unquoted or double-quoted piece."""
    def environment(match: re.Match[str]) -> str:
        value: str | None = os.environ.get(match.group(1) or match.group(2))
        return value if value is not None else match.group(0)

    text = _PS_ENV.sub(environment, text)
    return _PS_PWD.sub(lambda _: cwd.as_posix(), text)


class _PowerShellLexer:
    """Split a PowerShell command into words, separators and redirections.

    Understands single quotes (``''`` escapes one), double quotes (backtick escapes, ``""``), here-strings
    (``@'…'@`` and ``@"…"@``), the backtick escape and line continuation, ``#`` comments, ``;``, ``|``, ``&&``,
    ``||``, ``&``, parentheses and braces as separators, and the ``>``, ``>>``, ``N>``, ``*>`` and ``N>&1``
    redirections. ``$env:NAME``, ``${env:NAME}`` and ``$PWD`` are expanded outside single quotes.
    """

    def __init__(
        self,
        command: str,
        cwd: Path
    ) -> None:
        self._text = command.replace("\r\n", "\n")
        self._cwd = cwd
        self._position: int = 0
        self._tokens: list[PsToken] = []
        self._pieces: list[tuple[str, bool]] = []
        self._in_word: bool = False

    def _add(
        self,
        text: str,
        expand: bool
    ) -> None:
        """Append a piece to the current word."""
        self._pieces.append((text, expand))
        self._in_word = True

    def _raw_word(self) -> str:
        """Return the current word without expansion (to recognize a stream number such as ``2``)."""
        return "".join(text for text, _ in self._pieces)

    def _flush(self) -> None:
        """Close the current word, if any."""
        if self._in_word:
            self._tokens.append(("word", "".join(_ps_expand(t, self._cwd) if e else t for t, e in self._pieces)))
        self._pieces = []
        self._in_word = False

    def _single_quoted(self) -> None:
        """Read a ``'…'`` string; ``''`` is one quote."""
        text: str = self._text
        position: int = self._position + 1
        chunk: list[str] = []
        while position < len(text):
            if text[position] == "'":
                if text[position + 1:position + 2] == "'":
                    chunk.append("'")
                    position += 2
                    continue
                break
            chunk.append(text[position])
            position += 1
        self._add("".join(chunk), False)
        self._position = position + 1

    def _double_quoted(self) -> None:
        """Read a ``"…"`` string; the backtick escapes the next character and ``""`` is one quote."""
        text: str = self._text
        position: int = self._position + 1
        chunk: list[str] = []
        while position < len(text):
            character: str = text[position]
            if character == "`" and position + 1 < len(text):
                chunk.append(text[position + 1])
                position += 2
                continue
            if character == '"':
                if text[position + 1:position + 2] == '"':
                    chunk.append('"')
                    position += 2
                    continue
                break
            chunk.append(character)
            position += 1
        self._add("".join(chunk), True)
        self._position = position + 1

    def _here_string(self) -> bool:
        """Read a here-string when one starts at the current position; return whether it did."""
        text: str = self._text
        quote: str = text[self._position + 1:self._position + 2]
        line_end: int = text.find("\n", self._position)
        if quote not in ("'", '"') or line_end < 0 or text[self._position + 2:line_end].strip():
            return False
        closing: int = text.find(f"\n{quote}@", line_end)
        if closing < 0:
            return False
        self._add(text[line_end + 1:closing], quote == '"')
        self._position = closing + 3
        return True

    def _redirection(self) -> None:
        """Read ``>``, ``>>``, ``N>``, ``*>`` or ``N>&1``; a lone stream number before it is not a word."""
        prefix: str = ""
        if self._in_word and _PS_STREAM.match(self._raw_word()):
            prefix = self._raw_word()
            self._pieces = []
            self._in_word = False
        self._flush()
        text: str = self._text
        position: int = self._position + 1
        operator: str = f"{prefix}>"
        if text[position:position + 1] == ">":
            operator += ">"
            position += 1
        if text[position:position + 1] == "&" and text[position + 1:position + 2].isdigit():
            self._tokens.append(("merge", f"{operator}&{text[position + 1]}"))
            position += 2
        else:
            self._tokens.append(("redirect", operator))
        self._position = position

    def _separator(self, character: str) -> None:
        """Emit a separator; ``&&`` and ``||`` are one token."""
        self._flush()
        following: str = self._text[self._position + 1:self._position + 2]
        if character in "&|" and following == character:
            self._tokens.append(("op", character * 2))
            self._position += 2
            return
        self._tokens.append(("op", character))
        self._position += 1

    def tokens(self) -> list[PsToken]:
        """Return the tokens of the command."""
        text: str = self._text
        while self._position < len(text):
            character: str = text[self._position]
            following: str = text[self._position + 1:self._position + 2]
            if character == "`":
                if following != "\n":
                    self._add(following, False)
                self._position += 2
            elif character in " \t\r":
                self._flush()
                self._position += 1
            elif character == "\n":
                self._flush()
                self._tokens.append(("op", ";"))
                self._position += 1
            elif character == "#" and not self._in_word:
                line_end: int = text.find("\n", self._position)
                self._position = len(text) if line_end < 0 else line_end
            elif character == "'":
                self._single_quoted()
            elif character == '"':
                self._double_quoted()
            elif character == "@" and not self._in_word and self._here_string():
                continue
            elif character == "$" and following == "{":
                closing: int = text.find("}", self._position)
                end: int = len(text) if closing < 0 else closing + 1
                self._add(text[self._position:end], True)
                self._position = end
            elif character == ">":
                self._redirection()
            elif character in _PS_SEPARATORS:
                self._separator(character)
            else:
                self._add(character, True)
                self._position += 1
        self._flush()
        return self._tokens


def _ps_elements(tokens: list[PsToken]) -> list[list[PsToken]]:
    """Split the tokens into pipeline elements (every separator ends one)."""
    elements: list[list[PsToken]] = [[]]
    for token in tokens:
        if token[0] == "op":
            elements.append([])
        else:
            elements[-1].append(token)
    return [element for element in elements if element]


def _ps_arguments(words: list[str]) -> tuple[dict[str, str], list[str]]:
    """Split cmdlet arguments into named parameters (lowercased, ``-Name:value`` included) and positional ones."""
    named: dict[str, str] = {}
    positional: list[str] = []
    index: int = 0
    while index < len(words):
        word: str = words[index]
        if len(word) > 1 and word.startswith("-") and word[1].isalpha():
            name: str
            separator: str
            value: str
            name, separator, value = word[1:].partition(":")
            name = name.lower()
            if separator:
                named[name] = value
            elif name in _PS_SWITCHES or index + 1 >= len(words):
                named[name] = ""
            else:
                named[name] = words[index + 1]
                index += 1
        else:
            positional.append(word)
        index += 1
    return named, positional


def _ps_named(
    named: dict[str, str],
    full_names: tuple[str, ...],
    aliases: frozenset[str] = frozenset()
) -> str | None:
    """Return the value of a parameter given by its full name, an alias or an abbreviation of 3+ letters."""
    for key, value in named.items():
        if key in full_names or key in aliases or (len(key) >= 3 and any(full.startswith(key) for full in full_names)):
            return value
    return None


def _ps_path_argument(
    named: dict[str, str],
    positional: list[str],
    index: int = 0
) -> str | None:
    """Return the ``-Path``/``-FilePath``/``-LiteralPath`` value, or the positional argument at ``index``."""
    value: str | None = _ps_named(named, *_PS_PATH)
    if value is not None:
        return value
    return positional[index] if len(positional) > index else None


def _ps_cmdlet_writes(
    cmdlet: str,
    words: list[str],
    base: Path,
    project: Path
) -> bool:
    """Return whether a cmdlet writes a protected repository file (or moves, copies or renames one to ``.py``)."""
    named: dict[str, str]
    positional: list[str]
    named, positional = _ps_arguments(words[1:])
    target: str | None
    if cmdlet in _PS_WRITERS:
        target = _ps_path_argument(named, positional)
        return target is not None and _is_protected_target(target, base, project)
    if cmdlet == "new-item":
        if _ps_named(named, ("value",), frozenset({"va"})) is None:
            return False
        target = _ps_path_argument(named, positional)
        name: str | None = _ps_named(named, ("name",))
        if name is not None:
            target = f"{target}/{name}" if target else name
        return target is not None and _is_protected_target(target, base, project)
    source: str | None = _ps_path_argument(named, positional)
    if cmdlet in ("copy-item", "move-item"):
        target = _ps_named(named, ("destination",)) or (positional[1] if len(positional) > 1 else None)
        if target is None:
            return False
        destination: Path = _to_path(target, base)
        into_directory: bool = destination.is_dir() and source is not None and source.lower().endswith(".py")
        return _inside(destination, project) and (destination.suffix.lower() == ".py" or into_directory)
    if cmdlet == "rename-item" and source is not None:
        target = _ps_named(named, ("newname",)) or (positional[1] if len(positional) > 1 else None)
        if target is None:
            return False
        renamed: Path = _to_path(target, _to_path(source, base).parent)
        return _inside(renamed, project) and renamed.suffix.lower() == ".py"
    return False


def _ps_script_writes(
    words: list[str],
    command: str,
    base: Path,
    project: Path,
    depth: int
) -> bool:
    """Return whether a pipeline element writes files with inline Python or Node, ``sh -c`` or a nested PowerShell.

    Every word is inspected (``& .venv/Scripts/python.exe``, ``docker compose exec web python``…). Python reading its
    code from stdin (``@'…'@ | python -``) is judged by the whole command, here-string included.
    """
    for index, word in enumerate(words):
        program: str = _program(word)
        following: str | None = words[index + 1] if index + 1 < len(words) else None
        code: str | None = words[index + 2] if index + 2 < len(words) else None
        if _SHELL.match(program) and following and _SHELL_COMMAND_FLAG.match(following) and code is not None:
            if _script_writes(code, base, project, depth + 1):
                return True
        elif _PYTHON.match(program):
            if _python_writes(words, index + 1, command, base, project):
                return True
        elif _NODE.match(program) and following in _NODE_CODE_FLAGS and code is not None:
            if _NODE_WRITE.search(code):
                return True
        elif _PS_SHELL.match(program):
            for position in range(index + 1, len(words)):
                flag: str = words[position].lower()
                if flag.startswith("-c") and "-command".startswith(flag):
                    nested: str = " ".join(words[position + 1:])
                    if powershell_violation(nested, base, project, depth + 1):
                        return True
                    break
    return False


def _ps_exempt(words: list[str]) -> bool:
    """Return whether the element is ``git`` or ``docker compose`` (only the script checks apply to them)."""
    program: str = _program(words[0]).lower().removesuffix(".exe")
    return program in ("git", "docker-compose") or (program == "docker" and words[1:2] == ["compose"])


def powershell_violation(
    command: str,
    cwd: Path,
    project: Path,
    depth: int = 0
) -> bool:
    """Return whether a PowerShell command writes a repository file, or writes files with a script.

    Denied on a protected repository file: ``Set-Content``, ``Add-Content``, ``Out-File`` and ``Tee-Object`` (named or
    positional path, aliases included), the ``>``, ``>>`` and ``*>`` redirections, ``[IO.File]::Write*|Append*``,
    ``New-Item … -Value``, and ``Copy-Item``/``Move-Item``/``Rename-Item`` towards a ``.py``; here-strings piped into
    them count. Everywhere: the script writes of the Bash checks and ``powershell|pwsh -Command``, recursively.
    ``Set-Location``/``cd`` changes the base of the next statements.
    """
    if depth > _MAX_SHELL_DEPTH:
        return False
    base: Path = cwd
    for match in _PS_IO_FILE.finditer(command):
        literal: str = match.group(1) if match.group(1) is not None else _ps_expand(match.group(2), base)
        if _is_protected_target(literal, base, project):
            return True
    for element in _ps_elements(_PowerShellLexer(command, cwd).tokens()):
        words: list[str] = []
        targets: list[str] = []
        pending_redirect: bool = False
        for kind, text in element:
            if kind == "redirect":
                pending_redirect = True
            elif kind == "word" and pending_redirect:
                targets.append(text)
                pending_redirect = False
            elif kind == "word":
                words.append(text)
        if not words:
            continue
        if _ps_script_writes(words, command, base, project, depth):
            return True
        if _ps_exempt(words):
            continue
        if any(t.lower() not in PS_SAFE_TARGETS and _is_protected_target(t, base, project) for t in targets):
            return True
        cmdlet: str = _program(words[0]).lower()
        cmdlet = _PS_ALIASES.get(cmdlet, cmdlet)
        if cmdlet in _PS_LOCATION:
            named: dict[str, str]
            positional: list[str]
            named, positional = _ps_arguments(words[1:])
            location: str | None = _ps_path_argument(named, positional)
            if location is not None:
                base = _to_path(location, base)
            continue
        if _ps_cmdlet_writes(cmdlet, words, base, project):
            return True
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
    command: object = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        print("{}")
        return
    project_dir: str = os.environ.get("CLAUDE_PROJECT_DIR") or str(payload.get("cwd") or os.getcwd())
    project: Path = _to_path(project_dir, Path.cwd())
    cwd: Path = _to_path(str(payload.get("cwd") or project_dir), project)
    check: Callable[[str, Path, Path], bool] = (
        powershell_violation if payload.get("tool_name") == "PowerShell" else violation
    )
    if not check(command, cwd, project):
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
    except Exception:  # noqa: BLE001 - a broken hook must never block a command
        print("{}")
    sys.exit(0)
