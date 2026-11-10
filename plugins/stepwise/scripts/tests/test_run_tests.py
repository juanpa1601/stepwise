"""Tests of ``run_tests.py``: run the real script in a temporary project.

The fixtures are real outputs of pytest 8.2.2 and unittest (Python 3.14, Windows), captured from sample suites; the
root of each capture is written as ``{ROOT}``, and ``emit.py`` puts the temporary project's root in its place, so
the frames of the capture fall inside the project the script reads.

Standard library only (``unittest``). From the root of this repository::

    python3 -m unittest discover plugins/stepwise/scripts/tests -v
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import ModuleType

SCRIPT: Path = Path(__file__).resolve().parents[1] / "run_tests.py"
FIXTURES: Path = Path(__file__).resolve().parent / "fixtures"
PY: str = Path(sys.executable).as_posix()

EMIT: str = """import os
import sys
from pathlib import Path

data = Path(sys.argv[1]).read_bytes().replace(b"{ROOT}", os.getcwd().encode("utf-8"))
for arg in sys.argv[3:]:
    if arg.startswith("log="):
        with open(arg[4:], "a", encoding="utf-8") as log:
            log.write(sys.argv[1] + "\\n")
sys.stdout.buffer.write(data)
sys.stdout.flush()
sys.exit(int(sys.argv[2]))
"""
TOUCH: str = 'open("ran.txt", "w").close()\n'
SPAWN: str = """import subprocess
import sys
import time

subprocess.Popen([sys.executable, "beat.py"])
time.sleep(60)
"""
BEAT: str = """import time

count = 0
while True:
    count += 1
    with open("beat.txt", "w", encoding="utf-8") as beat:
        beat.write(str(count))
    time.sleep(0.1)
"""
JEST: str = """ PASS  src/sum.test.js
 FAIL  src/app.test.js
  * app > renders
    expect(received).toBe(expected)
Tests:       1 failed, 2 passed, 3 total
Time:        1.2 s
"""


def load_module() -> ModuleType:
    """Import ``run_tests.py`` without writing bytecode next to it."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("run_tests", SCRIPT)
    module: ModuleType = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def emit(
    name: str,
    code: int = 0,
    log: str | None = None
) -> str:
    """Return the command that prints the fixture ``name`` (from the project root) and exits with ``code``."""
    return f'"{PY}" emit.py {name} {code}' + (f" log={log}" if log else "")


class ProjectCase(unittest.TestCase):
    """A temporary project with the helper scripts, the fixtures and a ``CLAUDE.md`` written per test."""

    def setUp(self) -> None:
        self._tmp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.root: Path = Path(self._tmp.name)
        for name, text in (("emit.py", EMIT), ("touch.py", TOUCH), ("spawn.py", SPAWN), ("beat.py", BEAT)):
            (self.root / name).write_text(text, encoding="utf-8")
        (self.root / "jest.txt").write_text(JEST, encoding="utf-8")
        for fixture in FIXTURES.iterdir():
            shutil.copyfile(fixture, self.root / fixture.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def contract(self, **commands: str) -> None:
        """Write ``CLAUDE.md`` with ``## Project commands`` and the given keys (``step``, ``full``, ``output``)."""
        keys: dict[str, str] = {"step": "Tests (step)", "full": "Tests (full)", "output": "Tests output"}
        lines: list[str] = ["# Project", "", "## Project commands"]
        lines += [f"- {keys[key]}: {value}" for key, value in commands.items()]
        lines += ["- Base branch: develop", "", "## Other", "- Tests (full): ignored"]
        (self.root / "CLAUDE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_script(
        self,
        *args: str,
        env: dict[str, str] | None = None
    ) -> tuple[list[str], int]:
        """Run the script in the project; return its output lines (UTF-8, at most 10) and its exit code."""
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            capture_output=True,
            env=os.environ.copy() if env is None else env,
            timeout=120
        )
        self.assertEqual(result.stderr, b"")
        lines: list[str] = result.stdout.decode("utf-8").splitlines()
        self.assertLessEqual(len(lines), 10, lines)
        return lines, result.returncode


class PytestTests(ProjectCase):
    """CA-1: pytest summaries, the ``total`` formula and the failures."""

    FAILURES: list[str] = [
        "- tests/test_sample.py::test_fail — tests/test_sample.py:15: assert 1 == 2",
        "- tests/test_sample.py::TestGroup::test_method_fail — tests/helpers.py:5: "
        "json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)",
        "- tests/test_sample.py::TestGroup::test_param[2] — tests/test_sample.py:53: AssertionError: n must be 1",
        "- tests/test_sample.py::test_error — tests/test_sample.py:20: RuntimeError: fixture boom",
    ]

    def test_quiet_green(self) -> None:
        self.contract(full=emit("pytest_q_pass.txt"))
        lines, code = self.run_script("full")
        self.assertEqual(lines, [
            f"Command: {emit('pytest_q_pass.txt')}",
            "Totals: 3 total, 0 failed, 0 errors, 0 skipped in 0.22s",
            "Failures: none",
        ])
        self.assertEqual(code, 0)

    def test_quiet_with_failures_errors_and_rfe(self) -> None:
        self.contract(full=emit("pytest_q_fail.txt", 1))
        lines, code = self.run_script("full")
        self.assertEqual(lines, [
            f"Command: {emit('pytest_q_fail.txt', 1)}",
            "Totals: 10 total, 3 failed, 1 errors, 1 skipped in 0.23s",
            "Failures:",
            *self.FAILURES,
        ])
        self.assertEqual(code, 1)

    def test_verbose_leaves_out_deselected(self) -> None:
        self.contract(full=emit("pytest_verbose.txt", 1))
        lines, code = self.run_script("full")
        self.assertEqual(lines[1], "Totals: 10 total, 3 failed, 1 errors, 1 skipped in 0.27s")
        self.assertEqual(lines[2:], ["Failures:", *self.FAILURES])
        self.assertEqual(code, 1)

    def test_collection_error(self) -> None:
        self.contract(full=emit("pytest_collect.txt", 2))
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:], [
            "Totals: 1 total, 0 failed, 1 errors, 0 skipped in 0.24s",
            "Failures:",
            "- tests/test_broken.py — tests/test_broken.py:1: ModuleNotFoundError: No module named 'missing_module_xyz'",
        ])
        self.assertEqual(code, 2)

    def test_at_most_five_failures(self) -> None:
        self.contract(full=emit("pytest_many.txt", 1))
        lines, code = self.run_script("full")
        self.assertEqual(lines[1], "Totals: 7 total, 7 failed, 0 errors, 0 skipped in 0.18s")
        self.assertEqual(lines[3:], [
            f"- tests/test_many.py::test_many[{n}] — tests/test_many.py:6: AssertionError: value {n}" for n in range(5)
        ])
        self.assertEqual(code, 1)


class UnittestTests(ProjectCase):
    """CA-2: unittest summaries and failures located in the project's last frame."""

    def test_ok(self) -> None:
        self.contract(full=emit("unittest_ok.txt"))
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:], ["Totals: 2 total, 0 failed, 0 errors, 0 skipped in 0.000s", "Failures: none"])
        self.assertEqual(code, 0)

    def test_ok_with_skipped(self) -> None:
        self.contract(full=emit("unittest_skip.txt"))
        lines, _ = self.run_script("full")
        self.assertEqual(lines[1], "Totals: 2 total, 0 failed, 0 errors, 1 skipped in 0.000s")

    def test_failed(self) -> None:
        self.contract(step=emit("unittest_fail.txt", 1))
        lines, code = self.run_script("step", "tests/test_bad.py")
        self.assertEqual(lines, [
            f"Command: {emit('unittest_fail.txt', 1)} tests/test_bad.py",
            "Totals: 5 total, 1 failed, 2 errors, 1 skipped in 0.009s",
            "Failures:",
            "- tests/test_bad.py::BadCase.test_errors — tests/helpers.py:5: "
            "json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)",
            "- tests/test_bad.py::BadCase.test_stdlib_error — tests/test_bad.py:18: json.decoder.JSONDecodeError: "
            "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
            "- tests/test_bad.py::BadCase.test_fails — tests/test_bad.py:12: "
            "AssertionError: '�and�' != 'nandu'",
        ])
        self.assertEqual(code, 1)


    def test_docstring_between_header_and_traceback(self) -> None:
        self.contract(full=emit("unittest_doc.txt", 1))
        lines, _ = self.run_script("full")
        self.assertEqual(lines[1:], [
            "Totals: 2 total, 1 failed, 0 errors, 0 skipped in 0.003s",
            "Failures:",
            "- tests/test_doc.py::DocCase.test_documented — tests/test_doc.py:7: AssertionError: 1 != 2",
        ])

    def test_python_310_header(self) -> None:
        # Python 3.10 and earlier print "FAIL: test_x (mod.Case)": the real 3.14 header, without the method.
        text: str = (FIXTURES / "unittest_fail.txt").read_text(encoding="utf-8")
        (self.root / "old.txt").write_text(text.replace(".BadCase.test_fails)", ".BadCase)"), encoding="utf-8")
        self.contract(full=emit("old.txt", 1))
        lines, _ = self.run_script("full")
        self.assertEqual(lines[-1], "- tests/test_bad.py::BadCase.test_fails — tests/test_bad.py:12: "
                                    "AssertionError: '�and�' != 'nandu'")


class GenericTests(ProjectCase):
    """CA-3: an unknown runner reports its exit code and its last lines."""

    def test_unknown_runner(self) -> None:
        self.contract(full=emit("jest.txt", 3))
        lines, code = self.run_script("full")
        self.assertEqual(lines[:3], [
            f"Command: {emit('jest.txt', 3)}",
            "Totals: not available (exit 3)",
            "Note: runner not recognized; last lines:",
        ])
        self.assertEqual(lines[-2:], ["Tests:       1 failed, 2 passed, 3 total", "Time:        1.2 s"])
        self.assertEqual(code, 3)


class ChainTests(ProjectCase):
    """CA-4: a ``&&`` value runs once, with one total per command."""

    def test_second_command_fails(self) -> None:
        first, second = emit("unittest_ok.txt", 0, "calls.log"), emit("unittest_fail.txt", 1, "calls.log")
        self.contract(full=f"{first} && {second}")
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:4], [
            "Totals:",
            f"- {first}: 2 total, 0 failed, 0 errors, 0 skipped in 0.000s",
            f"- {second}: 5 total, 1 failed, 2 errors, 1 skipped in 0.009s",
        ])
        self.assertEqual(lines[4], "Failures:")
        self.assertTrue(lines[5].startswith("- tests/test_bad.py::BadCase.test_errors — "), lines)
        self.assertEqual(code, 1)
        calls: list[str] = (self.root / "calls.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(calls, ["unittest_ok.txt", "unittest_fail.txt"])

    def test_first_command_fails(self) -> None:
        first, second = emit("unittest_fail.txt", 1), emit("unittest_ok.txt")
        self.contract(full=f"{first} && {second}")
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:4], [
            "Totals:",
            f"- {first}: 5 total, 1 failed, 2 errors, 1 skipped in 0.009s",
            f"- {second}: not run ({first} failed)",
        ])
        self.assertEqual(code, 1)

    def test_command_fails_without_summary(self) -> None:
        first, second, third = emit("unittest_ok.txt"), emit("jest.txt", 2), emit("unittest_skip.txt")
        self.contract(full=f"{first} && {second} && {third}")
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:5], [
            "Totals:",
            f"- {first}: 2 total, 0 failed, 0 errors, 0 skipped in 0.000s",
            f"- {second}: not available (exit 2)",
            f"- {third}: not run ({second} failed)",
        ])
        self.assertEqual(code, 2)

    def test_failed_status_without_failures(self) -> None:
        first, second = emit("pytest_none.txt", 5), emit("unittest_ok.txt")
        self.contract(full=f"{first} && {second}")
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:4], [
            "Totals:",
            f"- {first}: 0 total, 0 failed, 0 errors, 0 skipped in 0.01s",
            f"- {second}: not run ({first} failed)",
        ])
        self.assertEqual(code, 5)

    def test_more_than_six_commands(self) -> None:
        self.contract(full=" && ".join([emit("unittest_ok.txt")] * 8))
        lines, code = self.run_script("full")
        self.assertRegex(lines[1], r"^Totals: 16 total, 0 failed, 0 errors, 0 skipped in [0-9.]+s$")
        self.assertEqual(lines[2:], ["Failures: none", "Note: per-command totals not available"])
        self.assertEqual(code, 0)

    def test_six_commands_keep_one_failure(self) -> None:
        self.contract(full=" && ".join([emit("unittest_ok.txt")] * 5 + [emit("unittest_fail.txt", 1)]))
        lines, code = self.run_script("full")
        self.assertEqual(len(lines), 10)
        self.assertEqual(lines[8], "Failures:")
        self.assertTrue(lines[9].startswith("- tests/test_bad.py::BadCase.test_errors — "), lines)
        self.assertEqual(code, 1)

    def test_summaries_do_not_match_commands(self) -> None:
        first, second = emit("unittest_ok.txt"), emit("jest.txt")
        self.contract(full=f"{first} && {second}")
        lines, code = self.run_script("full")
        self.assertRegex(lines[1], r"^Totals: 2 total, 0 failed, 0 errors, 0 skipped in [0-9.]+s$")
        self.assertEqual(lines[-1], "Note: per-command totals not available")
        self.assertEqual(code, 0)

    def test_no_summary_at_all_is_generic(self) -> None:
        self.contract(full=f"{emit('jest.txt')} && {emit('jest.txt', 4)}")
        lines, code = self.run_script("full")
        self.assertEqual(lines[1:3], ["Totals: not available (exit 4)", "Note: runner not recognized; last lines:"])
        self.assertEqual(code, 4)


class TimeoutTests(ProjectCase):
    """CA-5: the script's own timeout kills the whole process tree."""

    def read_beat(self) -> str:
        """Return the heartbeat counter of the grandchild (empty when it is not there yet)."""
        try:
            return (self.root / "beat.txt").read_text(encoding="utf-8")
        except OSError:
            return ""

    def test_timeout_kills_the_tree(self) -> None:
        self.contract(full=f'"{PY}" spawn.py')
        start: float = time.monotonic()
        lines, code = self.run_script("full", "--timeout", "2")
        self.assertLess(time.monotonic() - start, 30)
        self.assertEqual(lines[1], "Totals: timeout after 2 s")
        self.assertEqual(code, 124)
        self.assertNotEqual(self.read_beat(), "", "the grandchild never started")
        before: str = self.read_beat()
        time.sleep(1.0)
        self.assertEqual(self.read_beat(), before, "the grandchild is still alive")

    def test_timeout_with_more_summaries_than_commands(self) -> None:
        three: bytes = (FIXTURES / "unittest_ok.txt").read_bytes() * 3
        (self.root / "three.txt").write_bytes(three)
        self.contract(full=f'{emit("three.txt")} && "{PY}" spawn.py')
        lines, code = self.run_script("full", "--timeout", "2")
        self.assertEqual(lines[-1], "Note: per-command totals not available; timeout after 2 s")
        self.assertEqual(code, 124)

    def test_default_timeout(self) -> None:
        self.assertEqual(load_module().DEFAULT_TIMEOUT, 570)

    def test_invalid_timeout(self) -> None:
        self.contract(full=emit("unittest_ok.txt"))
        for value in ("0", "abc", "²"):
            lines, code = self.run_script("full", "--timeout", value)
            self.assertEqual(lines, [f"Invalid timeout: {value}"])
            self.assertEqual(code, 2)


class ContractTests(ProjectCase):
    """CA-6: a missing section or key runs nothing; ``none`` is not an error."""

    def test_missing_file_or_section(self) -> None:
        lines, code = self.run_script("full")
        self.assertEqual(lines, [
            'Missing: "## Project commands" section in CLAUDE.md',
            "Proposed line: - Tests (full): <command>",
        ])
        self.assertEqual(code, 2)
        (self.root / "CLAUDE.md").write_text("# Project\n\n## Other\n- Tests (full): x\n", encoding="utf-8")
        self.assertEqual(self.run_script("full"), (lines, 2))

    def test_missing_key(self) -> None:
        self.contract(full=f'"{PY}" touch.py')
        lines, code = self.run_script("step", "tests/test_a.py")
        self.assertEqual(lines, [
            'Missing: key "Tests (step)" in CLAUDE.md',
            "Proposed line: - Tests (step): <command>",
        ])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "ran.txt").exists())

    def test_none(self) -> None:
        self.contract(full="none")
        lines, code = self.run_script("full")
        self.assertEqual(lines, ['The project has no "Tests (full)" command (declared as none).'])
        self.assertEqual(code, 0)


class StepPathsTests(ProjectCase):
    """CA-7: ``step`` needs valid paths and runs nothing without them."""

    def test_step_without_paths(self) -> None:
        self.contract(step=f'"{PY}" touch.py')
        lines, code = self.run_script("step")
        self.assertEqual(lines, ['Mode "step" needs paths, modules or test ids; none given.'])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "ran.txt").exists())

    def test_invalid_paths(self) -> None:
        self.contract(step=f'"{PY}" touch.py')
        for token in ("a;b", "$HOME", "a|b", "-k"):
            lines, code = self.run_script("step", "tests/test_a.py", token)
            self.assertEqual(lines, [f"Invalid path: {token}"])
            self.assertEqual(code, 2)
        self.assertFalse((self.root / "ran.txt").exists())

    def test_valid_ids(self) -> None:
        self.contract(step=emit("unittest_ok.txt"))
        lines, code = self.run_script("step", "tests/test_a.py::Case::test_b[1-2]", "pkg.mod.Case.test_c")
        self.assertEqual(lines[0], f"Command: {emit('unittest_ok.txt')} tests/test_a.py::Case::test_b[1-2] "
                                   "pkg.mod.Case.test_c")
        self.assertEqual(code, 0)


class OutputTests(ProjectCase):
    """CA-8: invalid UTF-8 and long outputs give a short report and leave no files."""

    def test_invalid_utf8_and_long_output(self) -> None:
        data: bytes = b"\xff\xfe broken\n" + "ñandú ≠ 1\n".encode("utf-8")
        data += b"".join(b"line %d\n" % n for n in range(1500))
        data += (FIXTURES / "unittest_ok.txt").read_bytes()
        (self.root / "big.bin").write_bytes(data)
        self.contract(full=emit("big.bin"))
        before: set[str] = {path.name for path in self.root.iterdir()}
        lines, code = self.run_script("full")
        self.assertEqual(lines[1], "Totals: 2 total, 0 failed, 0 errors, 0 skipped in 0.000s")
        self.assertEqual(code, 0)
        self.assertEqual({path.name for path in self.root.iterdir()}, before)


class ShellTests(unittest.TestCase):
    """CA-9: the shell is the one Claude Code's Bash uses, never WSL's ``bash`` from the ``PATH``."""

    def setUp(self) -> None:
        self.module: ModuleType = load_module()
        self._tmp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.root: Path = Path(self._tmp.name)
        self.windir: Path = self.root / "Windows"
        self.wsl: Path = self.file("Windows/System32/bash.exe")
        self.git_bash: Path = self.file("Git/bin/bash.exe")
        self.shell: Path = self.file("Git/usr/bin/bash.exe")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def file(self, name: str) -> Path:
        """Create an empty file ``name`` under the temporary directory and return its path."""
        path: Path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        return path

    def choose(self, **env: str) -> str | None:
        """Return the shell chosen on Windows for ``env`` (with the fake ``SystemRoot``)."""
        return self.module.choose_shell({"SystemRoot": str(self.windir), **env}, windows=True)

    def test_git_bash_path_first(self) -> None:
        self.assertEqual(self.choose(CLAUDE_CODE_GIT_BASH_PATH=str(self.git_bash), SHELL=str(self.shell)),
                         str(self.git_bash))

    def test_git_bash_path_ignored_when_invalid(self) -> None:
        zsh: Path = self.file("Git/bin/zsh.exe")
        for value in (str(zsh), str(self.root / "missing" / "bash.exe"), str(self.wsl)):
            self.assertEqual(self.choose(CLAUDE_CODE_GIT_BASH_PATH=value, SHELL=str(self.shell)), str(self.shell))

    def test_shell_must_exist_be_absolute_and_not_wsl(self) -> None:
        for value in (str(self.root / "missing" / "bash"), "bash.exe", str(self.wsl)):
            self.assertIsNone(self.choose(SHELL=value, PATH=str(self.wsl.parent)))

    def test_never_from_path(self) -> None:
        self.assertIsNone(self.choose(PATH=os.pathsep.join([str(self.wsl.parent), str(self.git_bash.parent)])))

    def test_posix(self) -> None:
        self.assertEqual(self.module.choose_shell({"SHELL": str(self.shell)}, windows=False), str(self.shell))
        self.assertEqual(self.module.choose_shell({}, windows=False), "/bin/sh")


@unittest.skipUnless(os.name == "nt", "Windows only")
class WindowsShellTests(ProjectCase):
    """CA-9 on a real Windows: Git Bash runs the command, and without it the script stops."""

    def test_runs_in_git_bash(self) -> None:
        self.contract(full="uname -s")
        lines, code = self.run_script("full")
        self.assertEqual(code, 0)
        self.assertRegex("\n".join(lines[3:]), r"MINGW|MSYS")

    def test_shell_not_found(self) -> None:
        self.contract(full=f'"{PY}" touch.py')
        env: dict[str, str] = {
            key: value for key, value in os.environ.items() if key.upper() not in ("SHELL", "CLAUDE_CODE_GIT_BASH_PATH")
        }
        lines, code = self.run_script("full", env=env)
        self.assertEqual(lines, ["shell not found"])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "ran.txt").exists())


class RetiredKeyTests(ProjectCase):
    """CA-10: ``Tests output`` is ignored without an error."""

    def test_tests_output_is_ignored(self) -> None:
        self.contract(full=emit("pytest_q_fail.txt", 1))
        without: tuple[list[str], int] = self.run_script("full")
        self.contract(full=emit("pytest_q_fail.txt", 1), output="tail -n 50")
        self.assertEqual(self.run_script("full"), without)


if __name__ == "__main__":
    unittest.main()
