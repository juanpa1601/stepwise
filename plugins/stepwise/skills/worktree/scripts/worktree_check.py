"""Read-only checks for ``/stepwise:worktree``.

Usage, from the root of the main copy::

    python3 <path to this script> new <folder>
    python3 <path to this script> remove <folder>

``new`` validates ``../<folder>`` before the skill creates the worktree. The name must match
``^[a-z0-9][a-z0-9_-]*$`` (so the Docker Compose project name is the folder name), ``../<folder>`` must not exist,
no other worktree of ``git worktree list`` may have the same folder name once Compose normalizes it, and, with a
compose, the name must not be a ``-p`` or ``--project-directory`` of the commands, a top-level ``name:`` or the
folder of a compose file not at the root, and every compose file must be readable as UTF-8, with no ``$``
variable in its top-level ``name:`` (it is refused otherwise). It reads
``## Project commands`` of the main copy's ``CLAUDE.md`` and prints::

    ok
    Carpeta: <absolute path of ../<folder>>
    Proyecto: <the folder name as Docker Compose normalizes it into a project name>
    venv: yes (<python of the main copy's .venv>) | yes (aviso: la copia principal no tiene .venv) | no
    compose: <compose files of the tests, in order> | none
    Proyecto fijo: <each -p/--project-name and --project-directory of the commands, top-level name: and folder outside the root of the compose files> | ninguno
    Entorno: <environment files to copy, relative to the root> | ninguno

``remove`` checks that ``../<folder>`` is a registered worktree whose folder exists (otherwise it suggests
``git worktree prune``), not the main copy and not on a detached HEAD, and
prints ``ok``, ``Carpeta:``, ``Rama:``, ``Feature:`` (the branch, or ``<feature>`` of ``<feature>-step-<n>``),
``Proyecto:`` (for ``docker compose -p``), ``compose:`` (from the worktree's own ``CLAUDE.md``),
and ``Llamadas compose:`` (the ``-f`` files of each call, together and shell-quoted, for one ``rm`` and one
``down`` each). It does not read volumes: the skill removes only the ones Docker labels with the project and that
carry its prefix. With a compose, it refuses a folder that normalizes to no project name, or
whose project name belongs to another worktree (the main copy included), to a ``-p`` or ``--project-directory`` of
the commands, to a top-level ``name:`` or to the folder of a compose file not at the root, and the same compose
files ``new`` refuses (not UTF-8, or a ``name:`` with a ``$`` variable).

- ``venv: yes`` when ``Lint/format`` mentions ``.venv``; the python is ``.venv/Scripts/python.exe``,
  ``.venv/Scripts/python`` or ``.venv/bin/python``, the first that exists in the main copy.
- It must run from the root of the main copy (the first entry of ``git worktree list``); otherwise it refuses.
- ``compose``: each global ``-f``/``--file`` (before the subcommand) of a ``docker compose`` or ``docker-compose``
  call in ``Tests (step)``, ``Tests (full)`` and ``Migrations check``, once, without a leading ``./``.
- ``Entorno``: the ``env_file:`` entries of those compose files given by a relative path that resolve to a file
  inside the main copy and that git does not track (an absolute compose file is read from where it is, by every
  worktree), marked ``(sin ignorar)`` when git does not ignore them, then the files ignored by
  git named ``.env`` or ``.env.*`` (``git ls-files --others --ignored --exclude-standard --directory``, so a whole
  ignored folder such as ``node_modules/`` is not walked), without the templates ``.env.example``, ``.env.sample``,
  ``.env.template`` and ``.env.dist``. Only names: it never opens an environment file.

Exit codes: 0 ok; 1 refused (the reason goes to stderr as ``error: <reason>``); 2 bad usage, no
``## Project commands`` section or git failed. Read-only and offline: it runs only read-only git commands and
never writes a file.

Standard library only (Python 3.10 or later).
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath

SECTION: str = "## Project commands"
GUIDE: str = "https://github.com/juanpa1601/stepwise/blob/main/docs/worktrees.md"
COMPOSE_KEYS: tuple[str, ...] = ("Tests (step)", "Tests (full)", "Migrations check")
TEMPLATES: frozenset[str] = frozenset({".env.example", ".env.sample", ".env.template", ".env.dist"})
VENV_PYTHONS: tuple[str, ...] = (".venv/Scripts/python.exe", ".venv/Scripts/python", ".venv/bin/python")
_KEY_LINE: re.Pattern[str] = re.compile(r"-\s+(?P<key>[^:]+?)\s*:\s*(?P<value>.*?)\s*")
_NEW_NAME: re.Pattern[str] = re.compile(r"[a-z0-9][a-z0-9_-]*")
_STEP_BRANCH: re.Pattern[str] = re.compile(r"(?P<feature>.+)-step-(?P<n>\d+)")
# A ``docker compose`` or ``docker-compose`` call, up to the next shell separator.
_COMPOSE_CALL: re.Pattern[str] = re.compile(r"docker(?:\s+|-)compose\b(?P<args>[^;&|\n]*)")
# Global options of ``docker compose`` that take a value as the next word.
_VALUE_OPTIONS: frozenset[str] = frozenset({
    "-f", "--file", "-p", "--project-name", "--project-directory", "--env-file", "--profile", "--ansi",
    "--progress", "--parallel",
})
_ENV_FILE: re.Pattern[str] = re.compile(r"(?P<indent>\s*)env_file\s*:\s*(?P<rest>.*)")


class Refused(Exception):
    """The folder cannot be used: exit 1."""


class Failed(Exception):
    """Bad usage, no contract or git failed: exit 2."""


def git(root: Path, *args: str) -> str:
    """Return the output of a read-only git command run in ``root``; raise ``Failed`` if it fails."""
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8"
        )
    except OSError as error:
        raise Failed(f"no se pudo correr git ({error})") from error
    if result.returncode != 0:
        raise Failed(f"git {' '.join(args)} falló: {result.stderr.strip()}")
    return result.stdout


def project_commands(root: Path) -> dict[str, str]:
    """Return the ``- <Key>: <value>`` lines of ``## Project commands`` in ``root/CLAUDE.md`` (first one wins)."""
    try:
        text: str = (root / "CLAUDE.md").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        text = ""
    commands: dict[str, str] = {}
    found: bool = False
    inside: bool = False
    for line in text.splitlines():
        stripped: str = line.strip()
        if stripped.startswith("## ") or stripped == "##":
            inside = stripped == SECTION
            found = found or inside
            continue
        match: re.Match[str] | None = _KEY_LINE.fullmatch(stripped) if inside else None
        if match and match["key"] not in commands:
            commands[match["key"]] = match["value"]
    if not found:
        raise Failed(f'falta la sección "{SECTION}" en {(root / "CLAUDE.md").as_posix()}')
    return commands


def global_values(
    args: str,
    names: tuple[str, ...]
) -> list[str]:
    """Return the values of the global options ``names`` of a ``docker compose`` call, which end at the first word
    that is not an option (the subcommand)."""
    try:
        words: list[str] = shlex.split(args)
    except ValueError:  # unbalanced quotes
        words = args.split()
    values: list[str] = []
    index: int = 0
    while index < len(words) and words[index].startswith("-"):
        word: str = words[index]
        option, _, value = word.partition("=")
        if option in names:
            if value:
                values.append(value)
            elif index + 1 < len(words):
                values.append(words[index + 1])
        if not value and option in _VALUE_OPTIONS:
            index += 1
        index += 1
    return values


def _compose_values(
    commands: dict[str, str],
    names: tuple[str, ...]
) -> list[str]:
    """Return each value of the global options ``names`` of the ``docker compose`` calls in the tests and
    migrations commands, once, without a leading ``./``."""
    found: list[str] = []
    for key in COMPOSE_KEYS:
        for call in _COMPOSE_CALL.finditer(commands.get(key, "")):
            for value in global_values(call["args"], names):
                while value.startswith("./"):
                    value = value[2:]  # the same file, at the root
                if value and value not in found:
                    found.append(value)
    return found


def compose_files(commands: dict[str, str]) -> list[str]:
    """Return each global ``-f``/``--file`` of the ``docker compose`` calls in the tests and migrations commands,
    once."""
    return _compose_values(commands, ("-f", "--file"))


def compose_calls(commands: dict[str, str]) -> list[list[str]]:
    """Return the ``-f``/``--file`` files of each ``docker compose`` call of the tests and migrations commands,
    together (an override is taken down with its base), each group once."""
    calls: list[list[str]] = []
    for key in COMPOSE_KEYS:
        for call in _COMPOSE_CALL.finditer(commands.get(key, "")):
            files: list[str] = []
            for value in global_values(call["args"], ("-f", "--file")):
                while value.startswith("./"):
                    value = value[2:]
                if value:
                    files.append(value)
            if files and files not in calls:
                calls.append(files)
    return calls


def _read(path: Path) -> str | None:
    """Return the text of a versioned file, or ``None`` when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


_TOP_LEVEL_KEY: re.Pattern[str] = re.compile(
    r"""(?P<key>"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[A-Za-z0-9_.-]+)\s*:(?P<rest>(?:\s.*)?)"""
)


def _top_level_key(line: str) -> tuple[str, str, bool] | None:
    """Return ``(key, rest, quoted)`` for a line at column 0 that is a simple mapping key (bare or between quotes,
    which are removed), or ``None`` for anything else: JSON, a complex key, an anchor, a merge key, a
    directive."""
    match: re.Match[str] | None = _TOP_LEVEL_KEY.fullmatch(line)
    if not match:
        return None
    key: str = match["key"]
    quoted: bool = key[:1] in ("'", '"')
    return (_unquote(key) if quoted else key), match["rest"], quoted


def _top_level_name(text: str) -> str | None:
    """Return the top-level ``name:`` of a compose file, or ``None``. The key may be between quotes, and a compose
    file written in JSON is read as JSON. The root mapping may be indented (after ``---`` or not) or a YAML flow
    mapping, where any ``name:`` counts, a nested one too: a refusal too many, never one too few."""
    try:
        data: object = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, dict):
        name: object = data.get("name")
        return name if isinstance(name, str) and name else None
    content: list[str] = [
        line for line in (raw.split(" #", 1)[0].rstrip() for raw in text.splitlines())
        if line.strip() and not line.lstrip().startswith(("#", "%")) and line.strip() not in ("---", "...")
    ]
    if not content:
        return None
    if content[0].lstrip().startswith("{"):
        flow: re.Match[str] | None = re.search(
            r"""[{,]\s*["']?name["']?\s*:\s*(?P<name>"[^"]*"|'[^']*'|[^,}\s][^,}]*)""", "\n".join(content)
        )
        return (_unquote(flow["name"]) or None) if flow else None
    indent: int = len(content[0]) - len(content[0].lstrip())
    for line in content:
        if len(line) - len(line.lstrip()) == indent:
            top: tuple[str, str, bool] | None = _top_level_key(line[indent:])
            if top and top[0] == "name" and top[1].strip():
                return _unquote(top[1])
    return None


def _project_directory_name(
    root: Path,
    folder: str
) -> str | None:
    """Return the Compose project name a ``--project-directory <folder>`` gives, resolved against ``root`` (so
    ``..`` is the parent every sibling worktree shares), or ``None`` when it is ``root`` itself (each worktree its
    own) or normalizes to nothing."""
    full: Path = (root / folder).resolve()
    if _key(full) == _key(root):
        return None
    return _project_name(full.name) or None


def fixed_projects(
    root: Path,
    commands: dict[str, str],
    composes: list[str]
) -> list[str]:
    """Return what fixes one Compose project name for every worktree: each ``-p``/``--project-name`` and
    ``--project-directory`` of the commands, the top-level ``name:`` of each compose file, and the folder of each
    compose file that is not at the root."""
    fixed: list[str] = [f"-p {name}" for name in _compose_values(commands, ("-p", "--project-name"))]
    fixed += [
        f"--project-directory {folder}" for folder in _compose_values(commands, ("--project-directory",))
        if _project_directory_name(root, folder)
    ]
    for compose in composes:
        text: str | None = _read(root / compose)
        name: str | None = _top_level_name(text) if text is not None else None
        if name:
            fixed.append(f"name: {name} ({compose})")
    fixed += [f"carpeta de {compose}" for compose in composes if _outside_root(compose)]
    return fixed


def _outside_root(compose: str) -> bool:
    """Return whether a compose file is not at the root: without ``-p``, Compose names the project after its
    folder, the same one for every worktree."""
    return str(PurePosixPath(compose.replace("\\", "/")).parent) not in ("", ".")


def taken_projects(
    root: Path,
    commands: dict[str, str],
    composes: list[str],
    others: list[tuple[Path, str]]
) -> dict[str, str]:
    """Return the Compose project names that belong to someone else, with whose they are: the other worktrees'
    folders (``others``, each with its label; the main copy included), the ``-p`` values of the commands, the
    top-level ``name:`` of the compose files and the folder of a compose file that is not at the root. Raise
    ``Refused`` for a compose file that exists but cannot be read, or whose ``name:`` has a ``$`` variable: its
    project could be any one."""
    taken: dict[str, str] = {}
    for path, label in others:
        taken.setdefault(_project_name(path.name), f"{label} {path.as_posix()}")
    for name in _compose_values(commands, ("-p", "--project-name")):
        taken.setdefault(_project_name(name), f"-p {name} de los comandos de tests")
    for folder in _compose_values(commands, ("--project-directory",)):
        # Without -p, Compose names the project after this folder, for every worktree.
        directory_name: str | None = _project_directory_name(root, folder)
        if directory_name:
            taken.setdefault(directory_name, f"--project-directory {folder} de los comandos de tests")
    for compose in composes:
        text: str | None = _read(root / compose)
        # A file it cannot read, or a name with a variable, may fix any project, this one included.
        if text is None and (root / compose).is_file():
            raise Refused(
                f"no sé qué proyecto de Compose fija {compose} (no se puede leer como UTF-8), así que no puedo "
                "comprobar que el de esta carpeta sea solo suyo; si es para quitar un worktree, hazlo a mano "
                f"({GUIDE}, sección 7, sin bajar el compose)"
            )
        name: str | None = _top_level_name(text) if text is not None else None
        if name and "$" in name:
            raise Refused(
                f"no sé qué proyecto de Compose fija {compose} (name: {name} depende de una variable), así que no "
                "puedo comprobar que el de esta carpeta sea solo suyo; si es para quitar un worktree, hazlo a mano "
                f"({GUIDE}, sección 7, sin bajar el compose)"
            )
        if name:
            taken.setdefault(_project_name(name), f"name: {name} de {compose}")
        if _outside_root(compose):
            parent: PurePosixPath = PurePosixPath(compose.replace("\\", "/")).parent
            taken.setdefault(_project_name(parent.name), f"la carpeta de {compose}")
    taken.pop("", None)
    return taken


def _unquote(value: str) -> str:
    """Return a YAML scalar without its comment and quotes."""
    value = value.strip()
    if value[:1] in ("'", '"'):
        return value[1:value.find(value[0], 1)] if value.find(value[0], 1) > 0 else value[1:]
    return value.split(" #", 1)[0].strip()


def env_file_entries(text: str) -> list[str]:
    """Return the paths of the ``env_file:`` entries of a compose file: a scalar, a flow list or a block list of
    paths or of ``path:`` mappings."""
    entries: list[str] = []
    lines: list[str] = text.splitlines()
    for index, line in enumerate(lines):
        match: re.Match[str] | None = _ENV_FILE.fullmatch(line)
        if not match:
            continue
        rest: str = match["rest"].split(" #", 1)[0].strip() if not match["rest"].startswith(("'", '"')) else match["rest"]
        if rest.startswith("["):
            entries.extend(_unquote(item) for item in rest.strip("[]").split(",") if item.strip())
            continue
        if rest:
            entries.append(_unquote(rest))
            continue
        for item in lines[index + 1:]:
            if not item.strip() or item.strip().startswith("#"):
                continue
            indent: int = len(item) - len(item.lstrip())
            # A block list may sit at the key's own indentation (``env_file:`` then ``- x`` below it).
            if indent < len(match["indent"]) or (indent == len(match["indent"]) and not item.strip().startswith("- ")):
                break
            value: str = item.strip().removeprefix("- ").strip()
            if value.startswith("path:"):
                entries.append(_unquote(value.removeprefix("path:")))
            elif item.strip().startswith("- ") and ":" not in value.split(" #", 1)[0]:
                entries.append(_unquote(value))
    return [entry for entry in entries if entry and "$" not in entry]


def is_env_name(name: str) -> bool:
    """Return whether ``name`` is ``.env`` or ``.env.*`` and not a template."""
    lowered: str = name.lower()
    return lowered not in TEMPLATES and (lowered == ".env" or lowered.startswith(".env."))


def _is_absolute(path: str) -> bool:
    """Return whether ``path`` is absolute in POSIX or Windows terms (``/x``, ``\\x``, ``C:x``)."""
    return bool(re.match(r"[A-Za-z]:|[\\/]", path))


def env_files(
    root: Path,
    composes: list[str]
) -> list[str]:
    """Return the environment files to copy into a new worktree, relative to ``root``, by name only. An
    ``env_file:`` that git does not ignore is marked ``(sin ignorar)``: copied into the worktree, it is an untracked
    file that blocks ``git worktree remove``."""
    tracked: set[str] = set(git(root, "ls-files", "-z").split("\0"))
    ignored: list[str] = [
        path for path in git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory")
        .split("\0") if path
    ]
    top: Path = root.resolve()
    found: list[str] = []
    for compose in composes:
        if _is_absolute(compose):
            continue  # the worktree reads this compose file, and its environment files, from where it is
        try:
            text: str = (root / compose).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        for entry in env_file_entries(text):
            if _is_absolute(entry):
                continue  # the worktree reads the same file
            full: Path = (top / compose).parent.joinpath(entry).resolve()
            if not full.is_relative_to(top) or not full.is_file():
                continue  # outside the project, or not in the main copy: there is nothing to copy
            path: str = full.relative_to(top).as_posix()
            if path in tracked or path in found or f"{path} (sin ignorar)" in found:
                continue
            is_ignored: bool = path in ignored or any(
                folder.endswith("/") and path.startswith(folder) for folder in ignored
            )
            found.append(path if is_ignored else f"{path} (sin ignorar)")
    for path in ignored:
        if not path.endswith("/") and is_env_name(PurePosixPath(path).name) and path not in found:
            found.append(path)
    return found


def venv_status(
    root: Path,
    commands: dict[str, str]
) -> str:
    """Return the ``venv:`` value: whether ``Lint/format`` uses ``.venv`` and the main copy's python."""
    if ".venv" not in commands.get("Lint/format", ""):
        return "no"
    for python in VENV_PYTHONS:
        if (root / python).is_file():
            return f"yes ({python})"
    return "yes (aviso: la copia principal no tiene .venv)"


def worktrees(root: Path) -> list[tuple[Path, str | None]]:
    """Return each worktree of ``git worktree list --porcelain`` (the main copy first) with its branch, or ``None``
    on a detached HEAD."""
    found: list[tuple[Path, str | None]] = []
    for block in git(root, "worktree", "list", "--porcelain").split("\n\n"):
        lines: list[str] = block.splitlines()
        paths: list[str] = [line.removeprefix("worktree ") for line in lines if line.startswith("worktree ")]
        branches: list[str] = [line.removeprefix("branch ") for line in lines if line.startswith("branch ")]
        if paths:
            branch: str | None = branches[0].removeprefix("refs/heads/") if branches else None
            found.append((Path(paths[0]), branch))
    return found


def _key(path: Path) -> str:
    """Return a comparable form of ``path``."""
    return os.path.normcase(str(path.resolve()))


def _project_name(name: str) -> str:
    """Return a folder name as Docker Compose normalizes it into a project name."""
    return re.sub(r"[^a-z0-9_-]", "", name.lower()).lstrip("_-")


def require_main_copy(
    root: Path,
    listed: list[tuple[Path, str | None]]
) -> None:
    """Raise ``Refused`` unless ``root`` is the root of the main copy (the first worktree of the list)."""
    if not listed or _key(listed[0][0]) != _key(root):
        main: str = listed[0][0].as_posix() if listed else "?"
        raise Refused(f"córrelo desde la raíz de la copia principal ({main}), no desde {root.as_posix()}")


def check_new(
    root: Path,
    folder: str
) -> list[str]:
    """Return the report of ``new <folder>``; raise ``Refused`` when the folder cannot be used."""
    if not _NEW_NAME.fullmatch(folder):
        raise Refused(f"nombre inválido: {folder!r} (se espera ^[a-z0-9][a-z0-9_-]*$)")
    listed: list[tuple[Path, str | None]] = worktrees(root)
    require_main_copy(root, listed)
    commands: dict[str, str] = project_commands(root)
    target: Path = root.resolve().parent / folder
    if target.exists():
        raise Refused(f"ya existe: {target.as_posix()}")
    for path, _ in listed:
        if _project_name(path.name) == folder:
            raise Refused(f"otro worktree usa la carpeta {path.name}: {path.as_posix()}")
    composes: list[str] = compose_files(commands)
    taken: dict[str, str] = taken_projects(root, commands, composes, [])
    if composes and folder in taken:
        raise Refused(f"el proyecto de Compose {folder} coincide con {taken[folder]}: elige otra carpeta")
    found: list[str] = env_files(root, composes)
    return [
        "ok",
        f"Carpeta: {target.as_posix()}",
        f"Proyecto: {_project_name(folder)}",
        f"venv: {venv_status(root, commands)}",
        f"compose: {', '.join(composes) or 'none'}",
        f"Proyecto fijo: {', '.join(fixed_projects(root, commands, composes)) or 'ninguno'}",
        f"Entorno: {', '.join(found) or 'ninguno'}",
    ]


def check_remove(
    root: Path,
    folder: str
) -> list[str]:
    """Return the report of ``remove <folder>``; raise ``Refused`` when it is not a worktree that can be removed."""
    if not folder or folder in (".", "..") or "/" in folder or "\\" in folder:
        raise Refused(f"nombre inválido: {folder!r} (una carpeta junto a la copia principal)")
    target: Path = root.resolve().parent / folder
    listed: list[tuple[Path, str | None]] = worktrees(root)
    require_main_copy(root, listed)
    matches: list[int] = [index for index, (path, _) in enumerate(listed) if _key(path) == _key(target)]
    if not matches:
        raise Refused(f"no es un worktree de este repo: {target.as_posix()}")
    if matches[0] == 0:
        raise Refused(f"es la copia principal: {target.as_posix()}")
    if not target.is_dir():
        raise Refused(f"la carpeta de este worktree ya no existe: {target.as_posix()}; corre git worktree prune")
    branch: str | None = listed[matches[0]][1]
    if branch is None:
        raise Refused(f"HEAD separado en {target.as_posix()}: no hay feature ni PR principal")
    step: re.Match[str] | None = _STEP_BRANCH.fullmatch(branch)
    commands: dict[str, str] = project_commands(target)
    composes: list[str] = compose_files(commands)
    project: str = _project_name(target.name)
    if composes and not project:
        raise Refused(
            f"{target.name!r} no da un nombre de proyecto de Compose (y -p vacío equivale a no pasarlo): "
            "baja el compose de tests a mano"
        )
    others: list[tuple[Path, str]] = [
        (path, "la copia principal" if index == 0 else "el worktree")
        for index, (path, _) in enumerate(listed) if index != matches[0]
    ]
    taken: dict[str, str] = taken_projects(target, commands, composes, others)
    if composes and project in taken:
        raise Refused(
            f"el proyecto de Compose {project} también es de {taken[project]}: no lo bajes, que quitaría lo que "
            f"comparten; quita el worktree a mano ({GUIDE}, sección 7, sin bajar el compose)"
        )
    calls: str = "; ".join(" ".join(f"-f {shlex.quote(file)}" for file in call) for call in compose_calls(commands))
    return [
        "ok",
        f"Carpeta: {target.as_posix()}",
        f"Rama: {branch}",
        f"Feature: {step['feature'] if step else branch}",
        f"Proyecto: {project}",
        f"compose: {', '.join(composes) or 'none'}",
        f"Llamadas compose: {calls or 'none'}",
    ]


def main(argv: list[str]) -> int:
    """Print the report of ``argv`` (``new <folder>`` or ``remove <folder>``) and return the exit code."""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr] - the messages carry accents
    if len(argv) != 2 or argv[0] not in ("new", "remove"):
        print("Usage: worktree_check.py new <folder> | remove <folder>", file=sys.stderr)
        return 2
    root: Path = Path.cwd()
    try:
        lines: list[str] = check_new(root, argv[1]) if argv[0] == "new" else check_remove(root, argv[1])
    except Refused as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except Failed as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
