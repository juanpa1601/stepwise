"""Tests of ``fingerprint.py`` (CA-G2): run the real script in a throwaway git repository.

Standard library only (``unittest``). From the root of this repository::

    python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests -v
"""

import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT: Path = Path(__file__).resolve().parents[1] / "fingerprint.py"
TRACE: str = "docs/pull-requests/feat/step-1.md"
ADR: str = "docs/decisions/feat/business-rules.md"
DOCS: tuple[str, ...] = ("--docs", "*.md", "docs/**")


def git(
    root: Path,
    *args: str
) -> str:
    """Run git in ``root`` and return its stdout."""
    completed: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603 - fixed program
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True
    )
    return completed.stdout


class RepoCase(unittest.TestCase):
    """A throwaway repository on ``feat-step-1``, branched from ``feat``, and helpers to run the script in it."""

    def setUp(self) -> None:
        self._tmp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.root: Path = Path(self._tmp.name)
        git(self.root, "init", "-q", "-b", "feat")
        self.write(".gitignore", "build/\n")
        self.write("app.py", "x = 1\n")
        self.write("README.md", "readme\n")
        self.write("CLAUDE.md", "## Project commands\n")
        self.write("sub/CLAUDE.md", "nested\n")
        self.write("docs/guide.txt", "guide\n")
        self.write(ADR, "adr\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        git(self.root, "switch", "-q", "-c", "feat-step-1")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(
        self,
        path: str,
        text: str
    ) -> None:
        """Write ``text`` to ``path`` inside the repository."""
        target: Path = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode())

    def run_script(
        self,
        *args: str
    ) -> subprocess.CompletedProcess[str]:
        """Run the script in the repository and return the finished process."""
        return subprocess.run(  # noqa: S603 - fixed interpreter and script
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False
        )

    def fingerprint(self) -> str:
        """Return the fingerprint of the step against ``feat``, excluding the traceability and the ADR."""
        completed: subprocess.CompletedProcess[str] = self.run_script("feat", TRACE, ADR)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def code_fingerprint(self) -> str:
        """Return the code fingerprint (``--docs '*.md' 'docs/**'``) of the step against ``feat``."""
        completed: subprocess.CompletedProcess[str] = self.run_script("feat", TRACE, ADR, *DOCS)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def both(self) -> tuple[str, str]:
        """Return the full and the code fingerprint, in that order."""
        return self.fingerprint(), self.code_fingerprint()


class FingerprintTest(RepoCase):
    """The fingerprint follows the step's diff and ignores the traceability and the ADR."""

    def test_format_and_stable(self) -> None:
        self.write("app.py", "x = 2\n")
        first: str = self.fingerprint()
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(first, self.fingerprint())

    def test_tracked_change_changes_it(self) -> None:
        before: str = self.fingerprint()
        self.write("app.py", "x = 2\n")
        after: str = self.fingerprint()
        self.assertNotEqual(before, after)
        self.write("app.py", "x = 3\n")
        self.assertNotEqual(after, self.fingerprint())

    def test_staged_and_committed_changes_count(self) -> None:
        self.write("app.py", "x = 2\n")
        unstaged: str = self.fingerprint()
        git(self.root, "add", "app.py")
        self.assertEqual(unstaged, self.fingerprint())
        git(self.root, "commit", "-q", "-m", "step")
        self.assertEqual(unstaged, self.fingerprint())

    def test_untracked_files_count(self) -> None:
        before: str = self.fingerprint()
        self.write("new.py", "a\n")
        with_new: str = self.fingerprint()
        self.assertNotEqual(before, with_new)
        self.write("new.py", "b\n")
        self.assertNotEqual(with_new, self.fingerprint())

    def test_untracked_path_counts(self) -> None:
        self.write("one.py", "a\n")
        first: str = self.fingerprint()
        (self.root / "one.py").rename(self.root / "two.py")
        self.assertNotEqual(first, self.fingerprint())

    def test_traceability_and_adr_excluded(self) -> None:
        self.write("app.py", "x = 2\n")
        before: str = self.fingerprint()
        self.write(TRACE, "## Pruebas\n")
        self.write(ADR, "adr changed\n")
        self.assertEqual(before, self.fingerprint())

    def test_ignored_files_excluded(self) -> None:
        before: str = self.fingerprint()
        self.write("build/out.txt", "x\n")
        self.assertEqual(before, self.fingerprint())

    def test_does_not_touch_the_index(self) -> None:
        self.write("app.py", "x = 2\n")
        self.write("new.py", "a\n")
        status: str = git(self.root, "status", "--porcelain")
        self.fingerprint()
        self.assertEqual(status, git(self.root, "status", "--porcelain"))

    def test_untracked_nested_repository(self) -> None:
        before: str = self.fingerprint()
        git(self.root, "init", "-q", "nested")
        self.write("nested/a.txt", "a\n")
        with_nested: str = self.fingerprint()
        self.assertNotEqual(before, with_nested)
        self.assertEqual(with_nested, self.fingerprint())

    def test_untracked_symlinks(self) -> None:
        self.write("target.txt", "a\n")
        before: str = self.fingerprint()
        try:
            os.symlink(self.root / "missing.txt", self.root / "broken.lnk")
            os.symlink(self.root / "docs", self.root / "dir.lnk", target_is_directory=True)
        except OSError as error:  # Windows without the symlink privilege
            self.skipTest(f"cannot create symlinks: {error}")
        with_links: str = self.fingerprint()
        self.assertNotEqual(before, with_links)
        self.assertEqual(with_links, self.fingerprint())

    @unittest.skipIf(os.name == "nt", "the file system only takes valid Unicode names")
    def test_untracked_non_utf8_name(self) -> None:
        before: str = self.fingerprint()
        (self.root / os.fsdecode(b"bad-\xff.txt")).write_bytes(b"x\n")
        completed: subprocess.CompletedProcess[str] = self.run_script("feat", TRACE, ADR)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotEqual(before, completed.stdout.strip())

    def test_unknown_feature_fails(self) -> None:
        completed: subprocess.CompletedProcess[str] = self.run_script("nope")
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(re.search(r"nope", completed.stderr))
        self.assertEqual(completed.stdout, "")

    def test_feature_required(self) -> None:
        completed: subprocess.CompletedProcess[str] = self.run_script()
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")


class CodeFingerprintTest(RepoCase):
    """CA-6: with ``--docs <pathspec> ...`` the fingerprint ignores those paths, except the root ``CLAUDE.md``."""

    def test_code_format_and_stable(self) -> None:
        self.write("app.py", "x = 2\n")
        first: str = self.code_fingerprint()
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(first, self.code_fingerprint())

    def test_tracked_docs_change_keeps_code(self) -> None:
        full, code = self.both()
        self.write("README.md", "readme changed\n")
        self.write("docs/guide.txt", "guide changed\n")
        self.write("sub/CLAUDE.md", "nested changed\n")
        self.assertNotEqual(full, self.fingerprint())
        self.assertEqual(code, self.code_fingerprint())

    def test_untracked_docs_file_keeps_code(self) -> None:
        full, code = self.both()
        self.write("docs/new/page.md", "new\n")
        self.write("NOTES.md", "notes\n")
        self.assertNotEqual(full, self.fingerprint())
        self.assertEqual(code, self.code_fingerprint())

    def test_code_change_changes_both(self) -> None:
        full, code = self.both()
        self.write("app.py", "x = 2\n")
        self.assertNotEqual(full, self.fingerprint())
        self.assertNotEqual(code, self.code_fingerprint())

    def test_untracked_code_file_changes_code(self) -> None:
        code: str = self.code_fingerprint()
        self.write("new.py", "a\n")
        self.assertNotEqual(code, self.code_fingerprint())

    def test_root_claude_md_always_counts(self) -> None:
        full, code = self.both()
        self.write("CLAUDE.md", "## Project commands\n- Tests (full): other\n")
        self.assertNotEqual(full, self.fingerprint())
        self.assertNotEqual(code, self.code_fingerprint())

    def test_untracked_root_claude_md_counts(self) -> None:
        git(self.root, "rm", "-q", "--cached", "CLAUDE.md")
        git(self.root, "commit", "-q", "-m", "untrack")
        code: str = self.code_fingerprint()
        self.write("CLAUDE.md", "## Project commands\n- changed\n")
        self.assertNotEqual(code, self.code_fingerprint())

    def test_traceability_and_adr_still_excluded(self) -> None:
        self.write("app.py", "x = 2\n")
        code: str = self.code_fingerprint()
        self.write(TRACE, "## Pruebas\n")
        self.write(ADR, "adr changed\n")
        self.assertEqual(code, self.code_fingerprint())

    def test_without_docs_docs_still_count(self) -> None:
        before: str = self.fingerprint()
        self.write("README.md", "readme changed\n")
        self.assertNotEqual(before, self.fingerprint())

    def test_docs_needs_a_pathspec(self) -> None:
        completed: subprocess.CompletedProcess[str] = self.run_script("feat", TRACE, ADR, "--docs")
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("--docs", completed.stderr)

    def test_docs_rejects_magic_pathspecs(self) -> None:
        for spec in (":(glob)docs/**", ":!docs"):
            with self.subTest(spec=spec):
                completed: subprocess.CompletedProcess[str] = self.run_script("feat", TRACE, ADR, "--docs", spec)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertIn(spec, completed.stderr)

    def test_without_docs_value_unchanged(self) -> None:
        self.write("app.py", "x = 2\n")
        self.write("new.py", "a\n")
        diff: bytes = subprocess.run(  # noqa: S603 - fixed program
            ["git", "-c", "core.quotepath=off", "diff", "--binary", "--no-ext-diff", "--no-textconv", "feat",
             "--", ".", f":(exclude,literal){ADR}", f":(exclude,literal){TRACE}"],
            cwd=self.root,
            capture_output=True,
            check=True
        ).stdout
        expected = hashlib.sha256(diff + b"\0untracked\0new.py\0" + b"a\n")
        self.assertEqual(f"sha256:{expected.hexdigest()}", self.fingerprint())

    def test_docs_does_not_touch_the_index(self) -> None:
        self.write("README.md", "readme changed\n")
        self.write("NOTES.md", "notes\n")
        status: str = git(self.root, "status", "--porcelain")
        self.code_fingerprint()
        self.assertEqual(status, git(self.root, "status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
