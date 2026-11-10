"""Run the project's tests from its ``## Project commands`` and report them in 10 lines.

Usage, from the project root::

    python3 <path to this script> full | step <paths or test ids...> [--timeout <seconds>]

``full`` runs ``Tests (full)``; ``step`` runs ``Tests (step)`` plus the given paths, modules or test ids (required;
each one matches ``[A-Za-z0-9_./:\\[\\]][A-Za-z0-9_./:\\[\\]-]*``, so no shell syntax and no leading ``-``). The
command comes only from ``CLAUDE.md`` in the working directory and runs once, exactly as written, with the shell of
Claude Code's Bash tool (``-c``): on Windows ``CLAUDE_CODE_GIT_BASH_PATH`` (when it exists and is named ``bash.exe``,
``sh.exe``, ``bash`` or ``sh``), else ``SHELL`` (an absolute path that exists), never ``bash`` from the ``PATH`` and
never ``System32`` (WSL); elsewhere ``SHELL``, else ``/bin/sh``.

The output (stdout and stderr together, read as UTF-8 with ``errors="replace"``) is parsed for pytest and unittest
summaries. A value chained with ``&&`` gets one total per command (up to 6 commands, so the report fits in 10 lines;
with more, one total and a note): summary k goes to command k. Any other runner gets
its exit code and its last lines (``runner not recognized``). ``total`` is the runner's own (``Ran N tests``) or
``passed + failed + errors + skipped + xfailed + xpassed``, without ``deselected`` or ``warnings``.

After ``--timeout`` seconds (570 by default, below the 600 s of a Bash call) the whole process tree is killed and the
report says ``timeout after <N> s``. The script does not clean up containers or other resources of the stack.

Exit codes: the test command's; 124 on timeout; 2 when nothing ran (missing section or key, ``step`` without paths,
an invalid path or timeout, no shell); 0 when the key is ``none``. It never writes a file. ``Tests output`` (the
retired key of the ``filter-test-output`` hook) is ignored.

Standard library only (Python 3.10 or later).
"""

import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT: int = 570
TIMEOUT_EXIT: int = 124
STOP_EXIT: int = 2
GRACE: int = 5
MAX_LINES: int = 10
MAX_FAILURES: int = 5
MAX_PARTS: int = 6  # Command + Totals + 6 rows + Failures + 1 failure = 10 lines
MAX_TEXT: int = 200
KEYS: dict[str, str] = {"step": "Tests (step)", "full": "Tests (full)"}
SHELL_NAMES: frozenset[str] = frozenset({"bash.exe", "sh.exe", "bash", "sh"})

_SECTION: str = "## Project commands"
_KEY_LINE: re.Pattern[str] = re.compile(r"-\s+(?P<key>[^:]+?)\s*:\s*(?P<value>.*?)\s*")
_TOKEN: re.Pattern[str] = re.compile(r"[A-Za-z0-9_./:\[\]][A-Za-z0-9_./:\[\]-]*")
_PYTEST_COUNT: str = r"\d+ (?:failed|passed|skipped|deselected|xfailed|xpassed|warnings?|errors?)"
_PYTEST_SUMMARY: re.Pattern[str] = re.compile(
    rf"=*\s*(?P<counts>{_PYTEST_COUNT}(?:, {_PYTEST_COUNT})*|no tests ran) in (?P<time>[0-9.]+s(?: \([0-9:]+\))?)\s*=*"
)
_UNITTEST_RAN: re.Pattern[str] = re.compile(r"Ran (?P<total>\d+) tests? in (?P<time>[0-9.]+s)")
_UNITTEST_RESULT: re.Pattern[str] = re.compile(r"(?P<status>OK|FAILED|NO TESTS RAN)(?: \((?P<counts>[^)]*)\))?")
_PYTEST_HEADER: re.Pattern[str] = re.compile(r"_{3,} (?P<name>.+?) _{3,}")
_PYTEST_SECTION: re.Pattern[str] = re.compile(r"=+ (?P<title>.+?) =+")
_PYTEST_LOCATION: re.Pattern[str] = re.compile(r"(?P<path>(?:[A-Za-z]:)?[^:\s][^:]*?):(?P<line>\d+):(?: .*)?")
_PYTEST_SHORT: re.Pattern[str] = re.compile(r"(?:FAILED|ERROR) (?P<id>\S+)(?: - .*)?")
_UNITTEST_HEADER: re.Pattern[str] = re.compile(r"(?:FAIL|ERROR): (?P<test>\S+) \((?P<dotted>[^)]+)\).*")
_UNITTEST_FRAME: re.Pattern[str] = re.compile(r'  File "(?P<path>.+)", line (?P<line>\d+), in .*')
_FOREIGN_ABSOLUTE: re.Pattern[str] = re.compile(r"[A-Za-z]:[\\/]")


@dataclass
class Summary:
    """The totals of one runner's summary and the failures printed before it (``- <id> — <where>: <error>``)."""

    total: int
    failed: int
    errors: int
    skipped: int
    time: str
    failures: list[str] = field(default_factory=list)
    failed_status: bool = False  # FAILED or no tests ran, even without failures or errors

    @property
    def bad(self) -> bool:
        """Return whether this summary is the one of a command that failed."""
        return bool(self.failed or self.errors or self.failed_status)

    def text(self) -> str:
        """Return the totals in the report's format."""
        return f"{self.total} total, {self.failed} failed, {self.errors} errors, {self.skipped} skipped in {self.time}"


class Stop(Exception):
    """Nothing runs: the message is the whole report and the exit code is ``code``."""

    def __init__(
        self,
        lines: list[str],
        code: int = STOP_EXIT
    ) -> None:
        super().__init__("\n".join(lines))
        self.lines: list[str] = lines
        self.code: int = code


def project_commands(text: str) -> tuple[bool, dict[str, str]]:
    """Return whether ``## Project commands`` exists and its ``- <Key>: <value>`` lines, up to the next ``## ``
    heading. The first line of a repeated key wins."""
    commands: dict[str, str] = {}
    found: bool = False
    inside: bool = False
    for line in text.splitlines():
        stripped: str = line.strip()
        if stripped.startswith("## ") or stripped == "##":
            inside = stripped == _SECTION
            found = found or inside
            continue
        if not inside:
            continue
        match: re.Match[str] | None = _KEY_LINE.fullmatch(stripped)
        if match and match["key"] not in commands:
            commands[match["key"]] = match["value"]
    return found, commands


def contract_command(
    root: Path,
    key: str
) -> str:
    """Return the value of ``key`` in ``root/CLAUDE.md``; raise ``Stop`` when it is missing, empty or ``none``."""
    try:
        text: str = (root / "CLAUDE.md").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        text = ""
    found, commands = project_commands(text)
    missing: str = f'key "{key}"' if found else f'"{_SECTION}" section'
    value: str = commands.get(key, "")
    if not value:
        raise Stop([f"Missing: {missing} in CLAUDE.md", f"Proposed line: - {key}: <command>"])
    if value == "none":
        raise Stop([f'The project has no "{key}" command (declared as none).'], 0)
    return value


def parse_args(argv: list[str]) -> tuple[str, list[str], int]:
    """Return the mode, the paths and the timeout of ``argv``; raise ``Stop`` when they are not valid."""
    args: list[str] = list(argv)
    timeout: int = DEFAULT_TIMEOUT
    if "--timeout" in args:
        at: int = args.index("--timeout")
        value: str = args[at + 1] if at + 1 < len(args) else ""
        if not re.fullmatch(r"[0-9]+", value) or int(value) < 1:
            raise Stop([f"Invalid timeout: {value}"])
        timeout = int(value)
        del args[at:at + 2]
    if not args or args[0] not in KEYS:
        raise Stop(["Usage: run_tests.py full | step <paths or test ids...> [--timeout <seconds>]"])
    mode, paths = args[0], args[1:]
    if mode == "full" and paths:
        raise Stop(['Mode "full" takes no paths.'])
    if mode == "step" and not paths:
        raise Stop(['Mode "step" needs paths, modules or test ids; none given.'])
    for path in paths:
        if not _TOKEN.fullmatch(path):
            raise Stop([f"Invalid path: {path}"])
    return mode, paths, timeout


def _system_shell(
    path: Path,
    env: dict[str, str]
) -> bool:
    """Return whether ``path`` lives in the Windows system folders (WSL's ``bash.exe``) or in ``WindowsApps``."""
    system_root: Path = Path(env.get("SystemRoot") or env.get("SYSTEMROOT") or r"C:\Windows")
    folder: str = str(path.resolve().parent).lower()
    system: set[str] = {str((system_root / name).resolve()).lower() for name in ("System32", "SysWOW64", "Sysnative")}
    return folder in system or "windowsapps" in folder


def choose_shell(
    env: dict[str, str],
    windows: bool
) -> str | None:
    """Return the shell that runs the command, or ``None`` on Windows when neither ``CLAUDE_CODE_GIT_BASH_PATH`` nor
    ``SHELL`` names a usable one."""
    if not windows:
        shell: str = env.get("SHELL", "")
        return shell if shell and Path(shell).is_absolute() and Path(shell).is_file() else "/bin/sh"
    candidates: list[tuple[str, bool]] = [(env.get("CLAUDE_CODE_GIT_BASH_PATH", ""), True), (env.get("SHELL", ""), False)]
    for value, named in candidates:
        if not value:
            continue
        path: Path = Path(value)
        if named and path.name.lower() not in SHELL_NAMES:
            continue
        if path.is_absolute() and path.is_file() and not _system_shell(path, env):
            return str(path)
    return None


def split_chain(command: str) -> list[str]:
    """Return the parts of ``command`` split on top-level ``&&`` (outside quotes and parentheses), stripped."""
    parts: list[str] = []
    current: list[str] = []
    quote: str = ""
    depth: int = 0
    index: int = 0
    while index < len(command):
        char: str = command[index]
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(command):
                current.append(command[index:index + 2])
                index += 2
                continue
            quote = "" if char == quote else quote
        elif char == "\\" and index + 1 < len(command):
            current.append(command[index:index + 2])
            index += 2
            continue
        elif char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "&" and command.startswith("&&", index) and depth == 0:
            parts.append("".join(current).strip())
            current = []
            index += 2
            continue
        current.append(char)
        index += 1
    parts.append("".join(current).strip())
    return [part for part in parts if part]


def _clip(text: str) -> str:
    """Return ``text`` on one line of at most ``MAX_TEXT`` characters."""
    text = " ".join(text.split())
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 3] + "..."


def project_path(
    text: str,
    root: Path
) -> str | None:
    """Return ``text`` relative to ``root`` (POSIX style) when it is project code, else ``None`` (outside the root,
    or in ``site-packages`` / ``dist-packages``)."""
    if os.name != "nt" and _FOREIGN_ABSOLUTE.match(text):
        return None
    path: Path = Path(text.replace("\\", "/"))
    if not path.is_absolute():
        path = root / path
    try:
        relative: Path = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    if {"site-packages", "dist-packages"} & set(relative.parts):
        return None
    return relative.as_posix()


def _failure(
    test: str,
    location: tuple[str, str] | None,
    error: str
) -> str:
    """Return one failure line of the report."""
    where: str = f"{location[0]}:{location[1]}: " if location else ""
    return _clip(f"- {test} — {where}{error}") if error or where else _clip(f"- {test}")


def pytest_failures(
    lines: list[str],
    root: Path
) -> list[str]:
    """Return the failure lines of a pytest run (``lines`` ends with its summary), in short-summary order."""
    blocks: dict[str, tuple[tuple[str, str] | None, str]] = {}
    section: str = ""
    name: str = ""
    location: tuple[str, str] | None = None
    error: str = ""
    in_error: bool = False
    ids: list[str] = []
    for line in [*lines, "=== end ==="]:
        heading: re.Match[str] | None = _PYTEST_SECTION.fullmatch(line)
        header: re.Match[str] | None = _PYTEST_HEADER.fullmatch(line)
        if (heading or header) and name:
            blocks.setdefault(name, (location, error))
            name = ""
        if heading:
            section = heading["title"]
            continue
        if section == "short test summary info":
            short: re.Match[str] | None = _PYTEST_SHORT.fullmatch(line)
            if short:
                ids.append(short["id"])
            continue
        if section not in ("FAILURES", "ERRORS"):
            continue
        if header:
            name = re.sub(r"^ERROR (?:at (?:setup|teardown) of|collecting) ", "", header["name"])
            location, error, in_error = None, "", False
            continue
        if line.startswith("E "):
            if not in_error:
                error = line[1:].strip()  # the first line of the last group of "E" lines
            in_error = True
            continue
        in_error = False
        found: re.Match[str] | None = _PYTEST_LOCATION.fullmatch(line)
        relative: str | None = project_path(found["path"], root) if found else None
        if found and relative:
            location = (relative, found["line"])
    if not ids:
        ids = list(blocks)
    result: list[str] = []
    for test_id in ids:
        key: str = ".".join(test_id.split("::")[1:]) or test_id  # a collection error has no "::"
        where, error = blocks.get(key, (None, ""))
        result.append(_failure(test_id, where, error))
    return result


def unittest_failures(
    lines: list[str],
    root: Path
) -> list[str]:
    """Return the failure lines of a unittest run (``lines`` ends with its summary), in output order."""
    result: list[str] = []
    index: int = 0
    while index < len(lines):
        header: re.Match[str] | None = _UNITTEST_HEADER.fullmatch(lines[index])
        index += 1
        if not header:
            continue
        frames: list[tuple[str, str]] = []
        error: str = ""
        if index + 1 < len(lines) and not lines[index].startswith(("-----", "=====")) and lines[
            index + 1
        ].startswith("-----"):
            index += 1  # the first line of the test's docstring
        if index < len(lines) and lines[index].startswith("-----"):
            index += 1  # the rule under the header
        while index < len(lines) and not lines[index].startswith(("=====", "-----")):
            line: str = lines[index]
            index += 1
            frame: re.Match[str] | None = _UNITTEST_FRAME.fullmatch(line)
            if frame:
                relative: str | None = project_path(frame["path"], root)
                if relative:
                    frames.append((relative, frame["line"]))
                error = ""
                continue
            if not error and line.strip() and not line.startswith(" ") and not line.startswith("Traceback"):
                error = line
        dotted: str = header["dotted"]
        if dotted.endswith(f".{header['test']}"):
            name: str = ".".join(dotted.split(".")[-2:])
        else:  # Python 3.10 and earlier: "FAIL: test_x (pkg.mod.Case)"
            name = f"{dotted.split('.')[-1]}.{header['test']}"
            dotted = f"{dotted}.{header['test']}"
        test: str = f"{frames[0][0]}::{name}" if frames else dotted
        result.append(_failure(test, frames[-1] if frames else None, error))
    return result


def summaries(
    output: str,
    root: Path
) -> list[Summary]:
    """Return the pytest and unittest summaries of ``output``, in order, each with the failures printed after the
    previous one."""
    lines: list[str] = [line.rstrip() for line in output.splitlines()]
    found: list[Summary] = []
    start: int = 0
    index: int = 0
    while index < len(lines):
        line: str = lines[index]
        pytest: re.Match[str] | None = _PYTEST_SUMMARY.fullmatch(line)
        ran: re.Match[str] | None = _UNITTEST_RAN.fullmatch(line)
        if pytest:
            counts: dict[str, int] = {}
            for part in re.findall(r"(\d+) (\w+)", pytest["counts"]):
                word: str = part[1].rstrip("s") if part[1] in ("errors", "warnings") else part[1]
                counts[word] = int(part[0])
            total: int = sum(counts.get(word, 0) for word in ("passed", "failed", "error", "skipped", "xfailed", "xpassed"))
            summary: Summary = Summary(total, counts.get("failed", 0), counts.get("error", 0), counts.get("skipped", 0),
                                       pytest["time"], failed_status=total == 0)
            summary.failures = pytest_failures(lines[start:index + 1], root)
            found.append(summary)
            start = index + 1
        elif ran:
            result: re.Match[str] | None = None
            end: int = index + 1
            while end < len(lines) and end <= index + 3:
                result = _UNITTEST_RESULT.fullmatch(lines[end])
                if result:
                    break
                end += 1
            if result:
                fields: dict[str, int] = {
                    key.strip(): int(value) for key, value in re.findall(r"([a-z ]+)=(\d+)", result["counts"] or "")
                }
                summary = Summary(int(ran["total"]), fields.get("failures", 0), fields.get("errors", 0),
                                  fields.get("skipped", 0), ran["time"], failed_status=result["status"] != "OK")
                summary.failures = unittest_failures(lines[start:end + 1], root)
                found.append(summary)
                start = end + 1
                index = end
        index += 1
    return found


def kill_tree(
    process: subprocess.Popen[bytes],
    windows: bool
) -> None:
    """Kill ``process`` and every process it started."""
    if windows:
        taskkill: Path = Path(os.environ.get("SystemRoot") or r"C:\Windows") / "System32" / "taskkill.exe"
        subprocess.run([str(taskkill), "/T", "/F", "/PID", str(process.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=GRACE)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def execute(
    command: str,
    shell: str,
    timeout: int,
    windows: bool
) -> tuple[str, int, bool, float]:
    """Run ``command`` once with ``shell -c`` from the working directory; return its output, exit code, whether it
    timed out and the seconds it took."""
    options: dict[str, object] = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if windows else {"start_new_session": True}  # type: ignore[attr-defined]
    )
    start: float = time.monotonic()
    process: subprocess.Popen[bytes] = subprocess.Popen(
        [shell, "-c", command], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        **options  # type: ignore[arg-type]
    )
    timed_out: bool = False
    try:
        raw, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(process, windows)
        try:
            raw, _ = process.communicate(timeout=GRACE * 2)
        except subprocess.TimeoutExpired:
            process.kill()
            raw = b""
    code: int = process.returncode if process.returncode is not None else 1
    return raw.decode("utf-8", errors="replace"), code if code >= 0 else 128 - code, timed_out, time.monotonic() - start


def _seconds(value: float) -> str:
    """Return a measured duration in the runners' style."""
    return f"{value:.1f}s"


def _merged(
    found: list[Summary],
    elapsed: float
) -> Summary:
    """Return one summary with the sums of ``found`` and the measured time."""
    merged: Summary = Summary(0, 0, 0, 0, _seconds(elapsed))
    for summary in found:
        merged.total += summary.total
        merged.failed += summary.failed
        merged.errors += summary.errors
        merged.skipped += summary.skipped
        merged.failures += summary.failures
    return merged


def report(
    command: str,
    output: str,
    code: int,
    timed_out: bool,
    elapsed: float,
    timeout: int,
    root: Path
) -> list[str]:
    """Return the report lines (at most ``MAX_LINES``)."""
    parts: list[str] = split_chain(command) or [command]
    found: list[Summary] = summaries(output, root)
    head: list[str] = [f"Command: {command}"]
    note: str = ""
    failures: list[str] = [line for summary in found for line in summary.failures]
    if not found and not timed_out:
        last: list[str] = [line.rstrip()[:MAX_TEXT] for line in output.splitlines() if line.strip()]
        head += [f"Totals: not available (exit {code})", "Note: runner not recognized; last lines:"]
        room: int = MAX_LINES - len(head)
        return head + (last[-room:] if room > 0 else [])
    if len(parts) == 1:
        if timed_out:
            head.append(f"Totals: timeout after {timeout} s")
        else:
            head.append(f"Totals: {(found[0] if len(found) == 1 else _merged(found, elapsed)).text()}")
    else:
        rows: list[str] | None = (
            chain_rows(parts, found, code, timed_out, timeout) if len(parts) <= MAX_PARTS else None
        )
        if rows is None:
            head.append(f"Totals: {_merged(found, elapsed).text()}")
            note = "Note: per-command totals not available" + (f"; timeout after {timeout} s" if timed_out else "")
        else:
            head += ["Totals:", *rows]
            if timed_out and not any("timeout after" in row for row in rows):
                note = f"Note: timeout after {timeout} s"
    tail: list[str] = [note] if note else []
    if not failures:
        return head + ["Failures: none"] + tail
    room = MAX_LINES - len(head) - len(tail) - 1
    shown: list[str] = failures[:max(min(MAX_FAILURES, room), 0)]
    if not shown:
        return head + [f"Failures: {len(failures)} not shown (no room in the report)"] + tail
    return head + ["Failures:", *shown] + tail


def chain_rows(
    parts: list[str],
    found: list[Summary],
    code: int,
    timed_out: bool,
    timeout: int
) -> list[str] | None:
    """Return one ``Totals`` row per part of a chain, or ``None`` when the summaries cannot be matched to the parts."""
    count: int = len(found)
    if count > len(parts):
        return None
    rows: list[str] = [f"- {part}: {summary.text()}" for part, summary in zip(parts, found)]
    if count == len(parts):
        return rows
    if timed_out:
        stopped: int = count
        rows.append(f"- {parts[stopped]}: timeout after {timeout} s")
    elif code == 0:
        return None
    elif count and found[-1].bad:
        stopped = count - 1
    else:
        stopped = count
        rows.append(f"- {parts[stopped]}: not available (exit {code})")
    reason: str = "timed out" if timed_out else "failed"
    rows += [f"- {part}: not run ({parts[stopped]} {reason})" for part in parts[stopped + 1:]]
    return rows


def main(argv: list[str]) -> int:
    """Run the mode of ``argv``, print the report and return the exit code."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    windows: bool = os.name == "nt"
    root: Path = Path.cwd()
    try:
        mode, paths, timeout = parse_args(argv)
        command: str = " ".join([contract_command(root, KEYS[mode]), *paths])
        shell: str | None = choose_shell(dict(os.environ), windows)
        if shell is None:
            raise Stop(["shell not found"])
    except Stop as stop:
        print("\n".join(stop.lines))
        return stop.code
    output, code, timed_out, elapsed = execute(command, shell, timeout, windows)
    print("\n".join(report(command, output, code, timed_out, elapsed, timeout, root)))
    return TIMEOUT_EXIT if timed_out else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
