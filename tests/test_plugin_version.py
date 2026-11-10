"""Versión del plugin `stepwise`.

Claude Code usa la `version` de `plugin.json` para saber si hay una
actualización: un cambio publicado sin subirla no llega a los proyectos. Este
test falla si `plugins/stepwise/` cambió respecto de la última publicación y la
`version` no.

Referencia: el tag `stepwise--v*` de versión más alta (no tiene que ser
alcanzable desde `HEAD`: vive en el merge de `main`); sin tags, `origin/main`;
sin ninguno, el test se salta. Compara el árbol de trabajo, con los archivos
sin seguimiento no ignorados, y no hace `fetch`.
"""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = "plugins/stepwise"
MANIFEST = f"{PLUGIN_DIR}/.claude-plugin/plugin.json"
TAG_PATTERN = "stepwise--v*"
FALLBACK_REF = "origin/main"
NO_REFERENCE = "no reference: no stepwise--v* tag and no origin/main"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class Check(NamedTuple):
    ok: bool
    message: str


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def reference(repo: Path) -> str | None:
    """El tag `stepwise--v*` de versión más alta; si no hay, `origin/main`."""
    tags = _git(repo, "tag", "--list", TAG_PATTERN, "--sort=-v:refname")
    found = [t for t in tags.stdout.splitlines() if t.strip()]
    if found:
        return found[0].strip()
    head = _git(repo, "rev-parse", "--verify", "--quiet", f"{FALLBACK_REF}^{{commit}}")
    return FALLBACK_REF if head.returncode == 0 else None


def _version(text: str | None) -> str | None:
    if text is None:
        return None
    value = json.loads(text).get("version")
    return value if isinstance(value, str) else None


def version_at(repo: Path, ref: str) -> str | None:
    shown = _git(repo, "show", f"{ref}:{MANIFEST}")
    return _version(shown.stdout if shown.returncode == 0 else None)


def current_version(repo: Path) -> str | None:
    path = repo / MANIFEST
    return _version(path.read_text(encoding="utf-8") if path.exists() else None)


def plugin_changed(repo: Path, ref: str) -> bool:
    """Hay diferencias en `plugins/stepwise/` entre `ref` y el árbol de trabajo."""
    diff = _git(repo, "diff", "--quiet", ref, "--", PLUGIN_DIR)
    if diff.returncode not in (0, 1):
        raise RuntimeError(f"git diff {ref} failed: {diff.stderr.strip()}")
    if diff.returncode == 1:
        return True
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "--", PLUGIN_DIR)
    return bool(untracked.stdout.strip())


def check_version(repo: Path) -> Check | None:
    """`None` si no hay referencia; si no, si la `version` cumple la regla."""
    ref = reference(repo)
    if ref is None:
        return None
    if not plugin_changed(repo, ref):
        return Check(True, f"{PLUGIN_DIR}/ unchanged since {ref}")
    before, now = version_at(repo, ref), current_version(repo)
    if now == before:
        return Check(
            False,
            f"{PLUGIN_DIR}/ changed since {ref} but version is still {now}: "
            f"bump it in {MANIFEST} (ADR release-1.0)",
        )
    return Check(True, f"version {before} at {ref} -> {now}")


def check_or_skip(repo: Path) -> Check:
    """Como `check_version`, pero sin referencia salta el test con `NO_REFERENCE`."""
    result = check_version(repo)
    if result is None:
        raise unittest.SkipTest(NO_REFERENCE)
    return result


class TempRepo:
    """Repo git temporal con un `plugins/stepwise/` mínimo."""

    def __init__(self, path: Path) -> None:
        self.path = path
        # Rama inicial fija: no depende de `init.defaultBranch` de quien corre.
        self.git("init", "-q", "-b", "develop")
        self.write("README.md", "repo\n")

    def git(self, *args: str) -> str:
        done = subprocess.run(
            [
                "git",
                "-c", "user.name=test",
                "-c", "user.email=test@example.com",
                "-c", "commit.gpgsign=false",
                "-c", "tag.gpgsign=false",
                "-c", "core.hooksPath=",
                *args,
            ],
            cwd=self.path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return done.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def set_version(self, version: str | None) -> None:
        manifest: dict[str, str] = {"name": "stepwise"}
        if version is not None:
            manifest["version"] = version
        self.write(MANIFEST, json.dumps(manifest) + "\n")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


class VersionCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = TempRepo(Path(self._tmp.name))
        self.repo.set_version("1.0.0")
        self.repo.write(f"{PLUGIN_DIR}/skills/spec/SKILL.md", "spec\n")
        self.repo.commit("release 1.0.0")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def tag(self, name: str, ref: str = "HEAD") -> None:
        self.repo.git("tag", "-a", name, ref, "-m", name)

    def assertFails(self, mentions: str) -> None:
        result = check_version(self.repo.path)
        assert result is not None
        self.assertFalse(result.ok, result.message)
        self.assertIn(mentions, result.message)
        self.assertIn("version is still 1.0.0", result.message)

    def assertPasses(self) -> None:
        result = check_version(self.repo.path)
        assert result is not None
        self.assertTrue(result.ok, result.message)

    # CA-1
    def test_committed_change_without_bump_fails_and_bump_passes(self) -> None:
        self.tag("stepwise--v1.0.0")
        self.repo.write(f"{PLUGIN_DIR}/skills/spec/SKILL.md", "spec v2\n")
        self.repo.commit("change skill")
        self.assertFails("stepwise--v1.0.0")
        self.repo.set_version("1.0.1")
        self.assertPasses()

    def test_uncommitted_change_without_bump_fails(self) -> None:
        self.tag("stepwise--v1.0.0")
        self.repo.write(f"{PLUGIN_DIR}/skills/spec/SKILL.md", "spec v2\n")
        self.assertFails("stepwise--v1.0.0")
        self.repo.set_version("1.1.0")
        self.assertPasses()

    def test_untracked_file_without_bump_fails(self) -> None:
        self.tag("stepwise--v1.0.0")
        self.repo.write(f"{PLUGIN_DIR}/agents/new.md", "agent\n")
        self.assertFails("stepwise--v1.0.0")
        self.repo.set_version("1.1.0")
        self.assertPasses()

    # CA-2
    def test_no_change_passes(self) -> None:
        self.tag("stepwise--v1.0.0")
        self.assertPasses()

    def test_change_outside_plugin_passes(self) -> None:
        self.tag("stepwise--v1.0.0")
        self.repo.write("plugins/other/skills/x/SKILL.md", "x\n")
        self.repo.write("docs/context.md", "contexto\n")
        self.repo.commit("outside stepwise")
        self.assertPasses()

    # CA-3
    def test_highest_stepwise_tag_wins_even_if_unreachable(self) -> None:
        self.tag("stepwise--v1.9.0")
        self.repo.git("switch", "-q", "-c", "main")
        self.repo.set_version("1.10.0")
        self.repo.commit("release 1.10.0")
        self.tag("stepwise--v1.10.0")
        self.tag("other--v9.0.0")
        self.repo.git("switch", "-q", "-")
        self.assertEqual(reference(self.repo.path), "stepwise--v1.10.0")
        self.repo.git("merge-base", "--is-ancestor", "stepwise--v1.9.0", "HEAD")
        with self.assertRaises(subprocess.CalledProcessError):
            self.repo.git("merge-base", "--is-ancestor", "stepwise--v1.10.0", "HEAD")

    # CA-4
    def test_without_tags_compares_against_origin_main(self) -> None:
        self.repo.set_version(None)
        published = self.repo.commit("published without version")
        self.repo.git("update-ref", "refs/remotes/origin/main", published)
        self.assertEqual(reference(self.repo.path), FALLBACK_REF)
        self.repo.write(f"{PLUGIN_DIR}/skills/spec/SKILL.md", "spec v2\n")
        self.repo.commit("change skill")
        result = check_version(self.repo.path)
        assert result is not None
        self.assertFalse(result.ok, result.message)
        self.assertIn(FALLBACK_REF, result.message)
        self.repo.set_version("1.0.0")
        self.assertPasses()

    def test_without_tag_or_origin_main_there_is_no_reference(self) -> None:
        self.assertIsNone(reference(self.repo.path))
        self.assertIsNone(check_version(self.repo.path))
        with self.assertRaises(unittest.SkipTest) as skipped:
            check_or_skip(self.repo.path)
        self.assertEqual(str(skipped.exception), NO_REFERENCE)


class RepoVersionTests(unittest.TestCase):
    """CA-5: este repo."""

    def test_stepwise_manifest_has_semver_version(self) -> None:
        version = current_version(REPO_ROOT)
        self.assertEqual(version, "1.0.0")
        assert version is not None
        self.assertRegex(version, SEMVER)

    def test_marketplace_entries_have_no_version(self) -> None:
        marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
        )
        entries = {p["name"]: p for p in marketplace["plugins"]}
        self.assertNotIn("version", entries["stepwise"])

    def test_version_check_passes_against_real_reference(self) -> None:
        result = check_or_skip(REPO_ROOT)
        self.assertTrue(result.ok, result.message)


if __name__ == "__main__":
    unittest.main()
