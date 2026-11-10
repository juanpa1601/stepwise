"""Tests of ``block_inplace_edits.py``: run the real hook through stdin/stdout for each command shape.

Standard library only (``unittest``). The project is a temporary directory created per run, so no path of a real
machine or project appears here. From the root of this repository::

    python3 -m unittest discover plugins/stepwise/hooks/tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK: Path = Path(__file__).resolve().parents[1] / "block_inplace_edits.py"
TEMP: str = tempfile.gettempdir().replace("\\", "/")
TEMP_WINDOWS: str = tempfile.gettempdir()
# Git Bash ``/tmp`` is the user temporary directory on Windows; elsewhere it is ``/tmp`` itself.
GIT_BASH_TMP: Path = Path(tempfile.gettempdir()) if os.name == "nt" else Path("/tmp")

# Set in ``setUpModule``: a fresh project directory outside the temporary directory's direct children used below.
PROJECT: Path = Path()
GIT_BASH_PROJECT: str = ""


def _to_git_bash(path: Path) -> str:
    """Return ``C:/x`` as Git Bash ``/c/x`` (unchanged on POSIX)."""
    drive, rest = os.path.splitdrive(path.resolve().as_posix())
    if drive:
        return f"/{drive[0].lower()}{rest}"
    return path.as_posix()


def decide(
    command: str,
    tool: str = "Bash"
) -> str:
    """Run the hook on a Bash (or PowerShell) command and return ``deny`` or ``pass``."""
    payload: str = json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "cwd": str(PROJECT),
        "tool_input": {"command": command},
    })
    env: dict[str, str] = {**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT)}
    completed: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603 - fixed interpreter and script
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        check=True
    )
    output: dict[str, object] = json.loads(completed.stdout)
    specific: object = output.get("hookSpecificOutput")
    if isinstance(specific, dict) and specific.get("permissionDecision") == "deny":
        reason: str = str(specific.get("permissionDecisionReason"))
        assert "use Read + Edit" in reason and "stop and ask the user" in reason
        return "deny"
    return "pass"


def denied_bash() -> list[str]:
    """Bash edits of repository files: ``sed -i``, ``perl -i``, redirections, heredocs and ``tee``."""
    return [
        "sed -i 's/a/b/' app/README.md",
        "sed -i.bak -e 's/a/b/' pyproject.toml",
        "sed --in-place 's/a/b/' CLAUDE.md",
        f"cd {GIT_BASH_PROJECT} && sed -i 's/x/y/' app/apps.py",
        "perl -pi -e 's/a/b/' app/README.md",
        "perl -i -pe 's/a/b/' requirements.in",
        "echo x > app/new_module.py",
        "echo x >> docs/notes.md",
        "printf 'a' > settings.toml",
        "echo '{}' > .claude/settings.json",
        "echo x > compose.yml",
        "echo x > compose.yaml",
        "echo x > requirements.txt",
        "echo x &> app/out.py",
        "cat <<EOF > app/x.py\nprint('a > b.md')\nEOF",
        "cat > docs/x.md <<'EOF'\nhola\nEOF",
        "cat <<EOF | tee app/x.py\nprint(1)\nEOF",
        "echo x | tee -a docs/notes.md > /dev/null",
        f"echo x > {PROJECT.as_posix()}/app/abs.py",
        "echo x > $CLAUDE_PROJECT_DIR/app/env.py",
    ]


# Untracked scripts in the temporary directory, named through Git Bash ``/tmp`` (created in ``setUpModule``).
WRITER_SCRIPT: str = "block_inplace_edits_test_mover.py"
READER_SCRIPT: str = "block_inplace_edits_test_reader.py"


def denied_scripts() -> list[str]:
    """Inline Python or Node with a write API, and untracked writing scripts."""
    return [
        "python -c \"open('app/x.py', 'w').write('a')\"",
        "python -c \"f = open(Path('a.md'), mode='a+')\"",
        "python3 -c \"from pathlib import Path; Path('app/x.py').write_text('a')\"",
        "python3 -c \"import pathlib; pathlib.Path('x.bin').write_bytes(b'')\"",
        "python -c \"import shutil; shutil.copyfile('a.py', 'b.py')\"",
        "python -c \"import shutil; shutil.move('a.py', 'b.py')\"",
        "python -c \"import os; os.replace('a', 'b')\"",
        "python -c \"import os; os.remove('a')\"",
        "py -3 -c \"from pathlib import Path; Path('a').unlink()\"",
        ".venv/Scripts/python.exe -c \"from pathlib import Path; Path('a').rename('b')\"",
        "uv run python -c \"open('x', 'x')\"",
        "docker compose run --rm test sh -c \"python3 -c 'import pathlib; pathlib.Path(\\\"x\\\").write_text(\\\"y\\\")'\"",
        "docker compose exec web bash -lc \"cd /app && python -c 'open(\\\"a\\\", \\\"w\\\")'\"",
        "python - <<'EOF'\nfrom pathlib import Path\nPath('app/x.py').write_text('a')\nEOF",
        "cat <<'EOF' | python3\nopen('app/x.py', 'w').write('a')\nEOF",
        f"python /tmp/{WRITER_SCRIPT}",
        f"cd {GIT_BASH_PROJECT} && python3 /tmp/{WRITER_SCRIPT} app/x.py",
        "cat > /tmp/new_mover.py <<'EOF'\nfrom pathlib import Path\nPath('a').write_text('b')\nEOF\npython /tmp/new_mover.py",
        "node -e \"require('fs').writeFileSync('app/x.py', 'a')\"",
        "node -e \"const fs = require('fs'); fs.appendFileSync('a.md', 'b')\"",
        "node -p \"fs.promises.unlink('a')\"",
    ]


SCRIPT_ALLOWED: list[str] = [
    "python -c \"import json; print(1)\"",
    "python -c \"import json, sys; print(json.load(open('pyproject.toml', 'rb')))\"",
    "python -c \"import sys; sys.stdout.write('ok')\"",
    "python manage.py makemigrations --check",
    "python manage.py migrate",
    "pytest",
    "python -m pytest app -q",
    "python3 -m unittest discover plugins/stepwise/hooks/tests",
    "uv pip compile requirements.in -o requirements.txt",
    "git mv a b",
    "git commit -m \"python -c 'open(x, \\\"w\\\")'\"",
    "python scripts/check_data.py",
    f"python /tmp/{READER_SCRIPT}",
    "python --version",
    "ruff check . && isort --check-only . && mypy .",
    "node -e \"console.log(require('fs').readFileSync('package.json', 'utf8'))\"",
]


def allowed_bash() -> list[str]:
    """Reads, output to the temporary directory, descriptor duplications, git and docker compose."""
    return [
        "ls > /dev/null",
        "python manage.py check 2>&1",
        "python manage.py check > /dev/null 2>&1",
        f"echo x > {TEMP}/scratch.py",
        "echo x > /tmp/scratch.md",
        f"cat <<EOF > {TEMP}/notes.md\nhola > mundo.py\nEOF",
        "echo x | tee /tmp/out.txt",
        "sed -n '1,20p' app/README.md",
        "sed -n '/-i/p' app/README.md",
        "sed 's/a/b/' app/README.md",
        "sed -i 's/a/b/' /tmp/scratch.txt",
        "grep -n 'x > y.py' app/README.md",
        "grep -rn foo app | head -5",
        "cat app/README.md",
        "git log --oneline -3",
        "git diff > /dev/null",
        "git show HEAD:CLAUDE.md > /tmp/old.md",
        "docker compose run --rm test pytest app 2>&1 | tail -20",
        "echo x > app/output.log",
        "python -c \"print(1 > 0)\"",
    ]


PS_DENIED: list[str] = [
    "Set-Content -Path app/x.py -Value 'a'",
    "Set-Content app/x.py 'a'",
    "Set-Content -LiteralPath:app\\x.md -Value a",
    "sc app/x.py 'a'",
    "Add-Content -Path README.md -Value 'more'",
    "ac README.md 'more'",
    "'a' | Out-File app/x.py",
    "'a' | Out-File -FilePath \"app/x.py\" -Encoding utf8",
    "'a' | Out-File -Append -FilePath app/x.py",
    "Get-Content a.txt | Tee-Object -FilePath app/x.py",
    "'a' | tee app/x.json",
    "'a' > app/x.py",
    "'a' >> docs/x.md",
    "Write-Output a *> app/x.txt",
    "Get-Process 2> app/x.txt",
    "\"a\" > \"$env:CLAUDE_PROJECT_DIR/app/x.py\"",
    "'a' > \"$PWD\\app\\x.py\"",
    "[IO.File]::WriteAllText('app/x.py', 'a')",
    "[System.IO.File]::AppendAllText(\"$PWD/README.md\", 'a')",
    "New-Item -Path app/x.py -ItemType File -Value 'a'",
    "ni app/x.py -Value a -Force",
    "New-Item -Path app -Name x.py -Value 'a'",
    "Copy-Item C:/scratch/x.py app/y.py",
    "Move-Item -Path a.txt -Destination app/y.py",
    "Rename-Item app/x.txt x.py",
    "@'\nimport os\n'@ | Set-Content app/x.py",
    "@\"\nprint('a')\n\"@ > app/x.py",
    "Set-Location app; Set-Content x.py 'a'",
    "cd docs; 'a' > x.md",
    "Get-Date; Set-Content app/x.py 'a'",
    "Get-Date && Set-Content app/x.py 'a'",
    "python -c \"open('x','w').write('a')\"",
    "& .venv/Scripts/python.exe -c \"import pathlib; pathlib.Path('x').write_text('a')\"",
    "@'\nimport pathlib\npathlib.Path('app/x.py').write_text('a')\n'@ | python -",
    "node -e \"require('fs').writeFileSync('x', 'a')\"",
    "powershell -NoProfile -Command \"Set-Content app/x.py 'a'\"",
    "pwsh -c \"'a' > app/x.py\"",
    "docker compose run --rm test sh -c \"python -c 'import pathlib; pathlib.Path(1).write_text(2)'\"",
    "docker compose exec web python -c \"open('x', 'w')\"",
    "Set-Content `\n  -Path app/x.py `\n  -Value a",
]

PS_ALLOWED: list[str] = [
    "git status",
    "git log --oneline -5 > $null",
    "docker compose run --rm test pytest app/tests/test_x.py",
    "docker compose --profile test build test",
    ".venv/Scripts/python.exe -m pytest",
    "python3 -m unittest discover plugins/stepwise/hooks/tests",
    "Get-Content app/x.py -TotalCount 20",
    "Select-String -Path app/*.py -Pattern 'foo'",
    "Get-Date > $null",
    "Get-Date > $NULL",
    "git status 2>$null",
    "Get-Item x 2>&1",
    "Remove-Item x -ErrorAction SilentlyContinue | Out-Null",
    "'a' | Out-Null",
    f"Set-Content -Path '{TEMP_WINDOWS}\\x.py' -Value 'a'",
    f"'a' > '{TEMP}/x.md'",
    f"'a' | Out-File \"{TEMP_WINDOWS}\\x.txt\"",
    f"[IO.File]::WriteAllText('{TEMP}/x.py', 'a')",
    "'a' > app/x.log",
    "New-Item -ItemType Directory -Force app/tmpdir",
    "New-Item -Path app/x.py -ItemType File",
    "Copy-Item app/x.py C:/scratch/x.py",
    "Rename-Item app/x.py x.txt",
    "Write-Output 'Set-Content app/x.py' # not a command",
    "Write-Output \"a > app/x.py\"",
    "Write-Output 'a > app/x.py'",
    "python -c \"print(open('app/x.py').read())\"",
    "$env:X = 'a'; Get-ChildItem",
    "powershell -NoProfile -Command \"Get-Date\"",
    f"Set-Location '{TEMP_WINDOWS}'; Set-Content x.py 'a'",
    "@'\nSet-Content app/x.py\n'@ | Write-Output",
]


def setUpModule() -> None:
    """Create the project directory and the untracked writer and reader scripts."""
    global PROJECT, GIT_BASH_PROJECT  # noqa: PLW0603 - module fixtures shared by the case lists
    PROJECT = Path(tempfile.mkdtemp(prefix="block_inplace_edits_project_")).resolve()
    GIT_BASH_PROJECT = _to_git_bash(PROJECT)
    GIT_BASH_TMP.joinpath(WRITER_SCRIPT).write_text("from pathlib import Path\nPath('a').write_text('b')\n", "utf-8")
    GIT_BASH_TMP.joinpath(READER_SCRIPT).write_text("import json\nprint(json.dumps({'a': 1}))\n", "utf-8")


def tearDownModule() -> None:
    """Remove the project directory and the temporary scripts."""
    shutil.rmtree(PROJECT, ignore_errors=True)
    for name in (WRITER_SCRIPT, READER_SCRIPT):
        GIT_BASH_TMP.joinpath(name).unlink(missing_ok=True)


class BlockInplaceEditsTests(unittest.TestCase):
    """Each denied shape is denied and each allowed shape passes."""

    def test_bash_writes_denied(self) -> None:
        """``sed -i``, ``perl -i``, heredocs, ``tee`` and redirections to a repository file are denied."""
        for command in denied_bash():
            with self.subTest(command=command):
                self.assertEqual(decide(command), "deny")

    def test_bash_reads_allowed(self) -> None:
        """Reads, output to the temporary directory, descriptor duplications, git and docker compose pass."""
        for command in allowed_bash():
            with self.subTest(command=command):
                self.assertEqual(decide(command), "pass")

    def test_script_writes_denied(self) -> None:
        """Inline Python or Node with a write API, and untracked writing scripts, are denied."""
        for command in denied_scripts():
            with self.subTest(command=command):
                self.assertEqual(decide(command), "deny")

    def test_script_reads_allowed(self) -> None:
        """Read-only inline code, tools, ``manage.py``, git and tracked or read-only scripts pass."""
        for command in SCRIPT_ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(decide(command), "pass")

    def test_powershell_writes_denied(self) -> None:
        """PowerShell writes of a repository file, and script writes, are denied."""
        for command in PS_DENIED:
            with self.subTest(command=command):
                self.assertEqual(decide(command, "PowerShell"), "deny")

    def test_powershell_reads_allowed(self) -> None:
        """PowerShell reads, ``$null``, ``Out-Null``, git, docker compose and writes outside the project pass."""
        for command in PS_ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(decide(command, "PowerShell"), "pass")

    def test_non_bash_payload_passes(self) -> None:
        """A payload without a command, or invalid JSON, prints ``{}``."""
        for raw in ("{}", "not json", json.dumps({"tool_input": {}})):
            with self.subTest(raw=raw):
                completed: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603
                    [sys.executable, str(HOOK)],
                    input=raw,
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.assertEqual(completed.stdout.strip(), "{}")


WRITER_CODE: str = "p = 'out.txt'\nwith open(p, 'w') as handle:\n    handle.write('a')\n"


class UntrackedScriptsInGitProjectTests(unittest.TestCase):
    """A writing script that git would show in the diff passes; one outside the project or ignored is denied."""

    def setUp(self) -> None:
        """Point the hook at a fresh git project with a ``.gitignore`` and three writing scripts."""
        global PROJECT  # noqa: PLW0603 - ``decide`` reads the module project directory
        self.previous: Path = PROJECT
        PROJECT = Path(tempfile.mkdtemp(prefix="block_inplace_edits_git_")).resolve()
        subprocess.run(["git", "init", "-q", str(PROJECT)], check=True)  # noqa: S603, S607 - fixed arguments
        PROJECT.joinpath(".gitignore").write_text("ignored/\n", "utf-8")
        PROJECT.joinpath("tests").mkdir()
        PROJECT.joinpath("tests", "test_new.py").write_text(WRITER_CODE, "utf-8")
        PROJECT.joinpath("ignored").mkdir()
        PROJECT.joinpath("ignored", "writer.py").write_text(WRITER_CODE, "utf-8")
        self.outside: Path = GIT_BASH_TMP / "block_inplace_edits_test_outside.py"
        self.outside.write_text(WRITER_CODE, "utf-8")

    def tearDown(self) -> None:
        """Remove the git project and the outside script, and restore the module project directory."""
        global PROJECT  # noqa: PLW0603
        shutil.rmtree(PROJECT, ignore_errors=True)
        self.outside.unlink(missing_ok=True)
        PROJECT = self.previous

    def test_untracked_not_ignored_script_allowed(self) -> None:
        """CA-H2: an untracked, not ignored ``.py`` inside the project with ``open(p, 'w')`` passes."""
        for command, tool in (
            ("python tests/test_new.py", "Bash"),
            ("python3 -I tests/test_new.py", "Bash"),
            (f"python {_to_git_bash(PROJECT)}/tests/test_new.py", "Bash"),
            ("python tests\\test_new.py", "PowerShell"),
        ):
            with self.subTest(command=command, tool=tool):
                self.assertEqual(decide(command, tool), "pass")

    def test_outside_or_ignored_script_denied(self) -> None:
        """CA-H3: the same script outside the project (``/tmp``) or in an ignored path is denied."""
        for command, tool in (
            (f"python /tmp/{self.outside.name}", "Bash"),
            ("python ignored/writer.py", "Bash"),
            ("python ignored\\writer.py", "PowerShell"),
            ("python tests/missing.py -c \"open('x', 'w')\"", "Bash"),
        ):
            with self.subTest(command=command, tool=tool):
                self.assertEqual(decide(command, tool), "deny")


if __name__ == "__main__":
    unittest.main()
