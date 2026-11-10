"""Tests of the plugin's hook registration: ``filter_test_output`` is retired.

Standard library only (``unittest``). From the root of this repository::

    python3 -m unittest discover plugins/stepwise/hooks/tests -v
"""

import json
import unittest
from pathlib import Path

HOOKS: Path = Path(__file__).resolve().parents[1]
HOOKS_JSON: Path = HOOKS / "hooks.json"
PLUGIN_JSON: Path = HOOKS.parent / ".claude-plugin" / "plugin.json"
RETIRED: str = "filter_test_output"


class RetiredHookTests(unittest.TestCase):
    """CA-11: ``hooks.json`` keeps its 3 ``PreToolUse`` entries and nothing names the retired hook."""

    def test_hooks_json_has_three_entries_without_the_retired_hook(self) -> None:
        config: object = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        assert isinstance(config, dict)
        entries: list[dict[str, object]] = config["hooks"]["PreToolUse"]
        self.assertEqual(len(entries), 3)
        commands: list[str] = [handler["command"] for entry in entries for handler in entry["hooks"]]
        self.assertEqual(len(commands), 3)
        self.assertFalse([command for command in commands if RETIRED in command], commands)

    def test_hook_and_its_test_do_not_exist(self) -> None:
        self.assertFalse((HOOKS / f"{RETIRED}.py").exists())
        self.assertFalse((HOOKS / "tests" / f"test_{RETIRED}.py").exists())

    def test_plugin_description_does_not_name_it(self) -> None:
        manifest: object = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        assert isinstance(manifest, dict)
        self.assertNotIn(RETIRED, manifest["description"])


if __name__ == "__main__":
    unittest.main()
