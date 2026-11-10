"""Tests of ``settings_alignment.py``: run the real script in a temporary project.

Standard library only (``unittest``). From the root of this repository::

    python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests -v
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT: Path = Path(__file__).resolve().parents[1] / "settings_alignment.py"
RULES_FILE: Path = Path(__file__).resolve().parents[4] / "references" / "ask-rules.json"
PLUGIN: str = "stepwise@stepwise"
MARKETPLACE: str = "stepwise"


def plugin_rules() -> list[str]:
    """Return the ``ask`` rules of the plugin's data file."""
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))["ask"]


def aligned(rules: list[str] | None = None) -> dict[str, object]:
    """Return an aligned ``settings.json`` with ``rules`` (by default, the plugin's) as its ``ask`` list."""
    return {
        "permissions": {"ask": plugin_rules() if rules is None else rules},
        "enabledPlugins": {PLUGIN: True},
        "extraKnownMarketplaces": {
            MARKETPLACE: {
                "source": {"source": "github", "repo": "juanpa1601/stepwise", "ref": "main"},
                "autoUpdate": True
            }
        }
    }


def copy_plugin(
    root: Path,
    rules_text: str
) -> Path:
    """Copy the script into a plugin tree under ``root`` with ``rules_text`` as its data file; return the copy."""
    script: Path = root / "stepwise" / "skills" / "check" / "scripts" / SCRIPT.name
    script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    rules: Path = root / "stepwise" / "references" / "ask-rules.json"
    rules.parent.mkdir(parents=True)
    rules.write_text(rules_text, encoding="utf-8")
    return script


class ProjectCase(unittest.TestCase):
    """A temporary project directory and helpers to write its settings and run the script in it."""

    def setUp(self) -> None:
        self._tmp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.root: Path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_text(
        self,
        text: str,
        path: str = ".claude/settings.json"
    ) -> None:
        """Write ``text`` to ``path`` inside the project."""
        target: Path = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def write_settings(self, settings: object) -> None:
        """Write ``settings`` as the project's ``.claude/settings.json``."""
        self.write_text(json.dumps(settings, indent=2))

    def run_script(
        self,
        *args: str,
        script: Path = SCRIPT
    ) -> subprocess.CompletedProcess[str]:
        """Run ``script`` (by default, the plugin's) from the project root and return the finished process."""
        return subprocess.run(  # noqa: S603 - fixed interpreter and script
            [sys.executable, str(script), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False
        )

    def lines(self, completed: subprocess.CompletedProcess[str]) -> list[str]:
        """Return the non-empty lines of stdout and stderr together."""
        return [line for line in (completed.stdout + completed.stderr).splitlines() if line.strip()]


class AlignedTest(ProjectCase):
    """CA-2, CA-5 and CA-6: aligned settings exit with 0."""

    def test_aligned(self) -> None:
        """CA-2: the 11 rules, the plugin enabled and the marketplace on ``main`` print ``ok``."""
        self.write_settings(aligned())
        completed: subprocess.CompletedProcess[str] = self.run_script()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(self.lines(completed), ["ok"])

    def test_extra_rule_is_information(self) -> None:
        """CA-5: a project rule outside the plugin's list is reported as information and keeps 0."""
        self.write_settings(aligned([*plugin_rules(), "Bash(gh api graphql:*)"]))
        completed: subprocess.CompletedProcess[str] = self.run_script()
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(self.lines(completed), ["ok", "Extra (info): Bash(gh api graphql:*)"])

    def test_utf8_bom(self) -> None:
        """An aligned file saved with a UTF-8 BOM (some Windows editors) is read as valid JSON."""
        self.write_text(chr(0xFEFF) + json.dumps(aligned()))
        completed: subprocess.CompletedProcess[str] = self.run_script()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(self.lines(completed), ["ok"])

    def test_order_and_repeats_are_ignored(self) -> None:
        """CA-6: the rules in another order, or with a repeated one, are still aligned."""
        rules: list[str] = plugin_rules()
        for case, project in (("reversed", rules[::-1]), ("repeated", [*rules, rules[0]])):
            with self.subTest(case=case):
                self.write_settings(aligned(project))
                completed: subprocess.CompletedProcess[str] = self.run_script()
                self.assertEqual(completed.returncode, 0, completed.stdout)
                self.assertEqual(self.lines(completed), ["ok"])


class MisalignedTest(ProjectCase):
    """CA-3, CA-4, CA-7 and CA-8: misaligned settings exit with 1."""

    def test_missing_rule(self) -> None:
        """CA-3: a missing plugin rule is listed in ``Faltan:``."""
        self.write_settings(aligned([rule for rule in plugin_rules() if rule != "Bash(gh pr ready:*)"]))
        completed: subprocess.CompletedProcess[str] = self.run_script()
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertEqual(self.lines(completed), ["desalineado", "Faltan: Bash(gh pr ready:*)"])

    def test_empty_settings(self) -> None:
        """CA-4: with ``{}``, every rule of the data file is missing, and so are the plugin and the marketplace."""
        self.write_settings({})
        completed: subprocess.CompletedProcess[str] = self.run_script()
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertEqual(
            self.lines(completed),
            [
                "desalineado",
                f"Faltan: {', '.join(plugin_rules())}",
                "Plugin: no habilitado",
                "Marketplace: no declarado"
            ]
        )

    def test_rules_come_from_data_file(self) -> None:
        """CA-4: a copy of the script in a plugin tree with its own ``ask-rules.json`` reports that file's rules."""
        with tempfile.TemporaryDirectory() as plugin_dir:
            script: Path = copy_plugin(Path(plugin_dir), json.dumps({"ask": ["Bash(x:*)"]}))
            self.write_settings({})
            completed: subprocess.CompletedProcess[str] = self.run_script(script=script)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("Faltan: Bash(x:*)", self.lines(completed))

    def test_plugin_not_enabled(self) -> None:
        """CA-7: the plugin absent from ``enabledPlugins``, or set to ``false``, is not enabled."""
        for case, enabled in (("absent", {"other@market": True}), ("false", {PLUGIN: False}), ("no key", None)):
            with self.subTest(case=case):
                settings: dict[str, object] = aligned()
                if enabled is None:
                    del settings["enabledPlugins"]
                else:
                    settings["enabledPlugins"] = enabled
                self.write_settings(settings)
                completed: subprocess.CompletedProcess[str] = self.run_script()
                self.assertEqual(completed.returncode, 1, completed.stdout)
                self.assertEqual(self.lines(completed), ["desalineado", "Plugin: no habilitado"])

    def test_marketplace(self) -> None:
        """CA-8: the marketplace undeclared, without ``ref`` or on another ``ref``."""
        cases: tuple[tuple[str, object, str], ...] = (
            ("undeclared", {"other": {"source": {"source": "github", "repo": "x/y", "ref": "main"}}},
             "Marketplace: no declarado"),
            ("no ref", {MARKETPLACE: {"source": {"source": "github", "repo": "x/y"}}},
             "Marketplace: sin ref (se espera main)"),
            ("other ref", {MARKETPLACE: {"source": {"source": "github", "repo": "x/y", "ref": "develop"}}},
             "Marketplace: ref develop (se espera main)")
        )
        for case, marketplaces, expected in cases:
            with self.subTest(case=case):
                settings: dict[str, object] = aligned()
                settings["extraKnownMarketplaces"] = marketplaces
                self.write_settings(settings)
                completed: subprocess.CompletedProcess[str] = self.run_script()
                self.assertEqual(completed.returncode, 1, completed.stdout)
                self.assertEqual(self.lines(completed), ["desalineado", expected])


class ErrorTest(ProjectCase):
    """CA-9: a missing file, invalid JSON or an invalid structure exit with 2 and say which case and the path."""

    def assert_error(
        self,
        case: str,
        path: str = ".claude/settings.json",
        *args: str
    ) -> None:
        """Run the script and check exit 2 with one line naming ``case`` and ``path``."""
        completed: subprocess.CompletedProcess[str] = self.run_script(*args)
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        lines: list[str] = self.lines(completed)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(case, lines[0])
        self.assertIn(path, lines[0])

    def test_missing_file(self) -> None:
        """No ``.claude/settings.json``."""
        self.assert_error("no existe")

    def test_invalid_json(self) -> None:
        """A file that is not valid JSON."""
        self.write_text('{"permissions": {"ask": [}')
        self.assert_error("no es JSON válido")

    def test_invalid_structure(self) -> None:
        """A root that is not an object, ``permissions`` that is not one, or an ``ask`` that is not a list of text."""
        for case, settings in (
            ("root list", ["Bash(git push:*)"]),
            ("permissions list", {"permissions": ["Bash(git push:*)"]}),
            ("ask text", {"permissions": {"ask": "Bash(git push:*)"}}),
            ("ask numbers", {"permissions": {"ask": ["Bash(git push:*)", 3]}})
        ):
            with self.subTest(case=case):
                self.write_settings(settings)
                self.assert_error("estructura inválida")

    def test_bad_data_file(self) -> None:
        """A plugin data file whose root is not an object with ``ask`` exits with 2, not with a traceback."""
        for case, text in (("list", '["Bash(x:*)"]'), ("text", '"Bash(x:*)"'), ("no ask", "{}")):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as plugin_dir:
                script: Path = copy_plugin(Path(plugin_dir), text)
                self.write_settings(aligned())
                completed: subprocess.CompletedProcess[str] = self.run_script(script=script)
                self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertIn("ask-rules.json", completed.stderr)

    def test_given_path(self) -> None:
        """The optional argument is the file to read; its errors name that path."""
        self.write_settings(aligned())
        self.assert_error("no existe", "other/settings.json", "other/settings.json")
        self.write_text(json.dumps(aligned()), "other/settings.json")
        completed: subprocess.CompletedProcess[str] = self.run_script("other/settings.json")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_too_many_arguments(self) -> None:
        """More than one argument prints the usage and exits with 2."""
        completed: subprocess.CompletedProcess[str] = self.run_script("a.json", "b.json")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Usage", completed.stderr)


class OutputTest(ProjectCase):
    """CA-10: at most 5 lines and no file written or changed, whatever the result."""

    def snapshot(self) -> dict[str, tuple[bytes, int]]:
        """Return the content and modification time of every file in the project."""
        return {
            str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*") if path.is_file()
        }

    def test_bounded_and_read_only(self) -> None:
        """Aligned, worst case (missing, extra, plugin and marketplace), invalid JSON and no file."""
        worst: dict[str, object] = {"permissions": {"ask": ["Bash(gh api graphql:*)"]}}
        for case, text in (
            ("aligned", json.dumps(aligned())),
            ("worst", json.dumps(worst)),
            ("invalid", "{"),
            ("no file", None)
        ):
            with self.subTest(case=case):
                settings: Path = self.root / ".claude" / "settings.json"
                if text is None:
                    settings.unlink(missing_ok=True)
                else:
                    self.write_text(text)
                before: dict[str, tuple[bytes, int]] = self.snapshot()
                completed: subprocess.CompletedProcess[str] = self.run_script()
                self.assertLessEqual(len(self.lines(completed)), 5, self.lines(completed))
                self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
