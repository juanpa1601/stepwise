"""Solo /regression corre la suite completa y saca el PR principal de draft.

ADR release-2.0.0, CA-7: un `SKILL.md` distinto de
`skills/regression/SKILL.md` no delega `"full"` a `test-runner`, no invoca
`run_tests.py` con `full` y no contiene `gh pr ready`. Cada violación se
reporta como `ruta:línea`.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = "plugins/stepwise/skills/*/SKILL.md"
OWNER = "plugins/stepwise/skills/regression/SKILL.md"
RULES = (
    (
        'delega "full" a test-runner',
        re.compile(
            r"test-runner.*[\"'`]full[\"'`]|[\"'`]full[\"'`].*test-runner"
        ),
    ),
    (
        "invoca run_tests.py con full",
        re.compile(r"run_tests\.py[\"'`]?\s+full\b"),
    ),
    ("contiene gh pr ready", re.compile(r"gh pr ready")),
)


def find_violations(files: dict[str, str]) -> list[str]:
    """Devuelve `ruta:línea: regla` por cada violación fuera de OWNER."""
    errors: list[str] = []
    for path, text in sorted(files.items()):
        if path == OWNER:
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            for label, pattern in RULES:
                if pattern.search(line):
                    errors.append(f"{path}:{number}: {label}")
    return errors


def repo_files() -> dict[str, str]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(REPO_ROOT.glob(SKILLS))
    }


CHECK = "plugins/stepwise/skills/check/SKILL.md"


class FindViolationsTest(unittest.TestCase):
    def test_full_delegated_to_test_runner(self) -> None:
        text = 'uno\nDelegate the suite to `stepwise:test-runner`: "full", now.\n'
        self.assertEqual(
            find_violations({CHECK: text}),
            [f'{CHECK}:2: delega "full" a test-runner'],
        )

    def test_full_before_test_runner(self) -> None:
        text = 'Run "full" with test-runner.'
        self.assertEqual(
            find_violations({CHECK: text}),
            [f'{CHECK}:1: delega "full" a test-runner'],
        )

    def test_full_in_backticks_or_single_quotes(self) -> None:
        text = (
            "Delegate to `stepwise:test-runner`: `full`.\n"
            "Run 'full' with test-runner.\n"
        )
        self.assertEqual(
            find_violations({CHECK: text}),
            [
                f'{CHECK}:1: delega "full" a test-runner',
                f'{CHECK}:2: delega "full" a test-runner',
            ],
        )

    def test_run_tests_full(self) -> None:
        text = 'a\nb\npython3 "<dir>/scripts/run_tests.py" full --timeout 9\n'
        self.assertEqual(
            find_violations({CHECK: text}),
            [f"{CHECK}:3: invoca run_tests.py con full"],
        )

    def test_run_tests_full_after_any_quote(self) -> None:
        text = (
            "python3 '<dir>/scripts/run_tests.py' full\n"
            "`<dir>/scripts/run_tests.py` full\n"
            "python3 <dir>/scripts/run_tests.py full\n"
        )
        self.assertEqual(
            find_violations({CHECK: text}),
            [
                f"{CHECK}:1: invoca run_tests.py con full",
                f"{CHECK}:2: invoca run_tests.py con full",
                f"{CHECK}:3: invoca run_tests.py con full",
            ],
        )

    def test_gh_pr_ready(self) -> None:
        text = "Then run `gh pr ready <num>`."
        self.assertEqual(
            find_violations({CHECK: text}),
            [f"{CHECK}:1: contiene gh pr ready"],
        )

    def test_owner_is_exempt(self) -> None:
        text = (
            'python3 "<dir>/scripts/run_tests.py" full --timeout 3600\n'
            "gh pr ready <num>\n"
        )
        self.assertEqual(find_violations({OWNER: text}), [])

    def test_step_mode_is_allowed(self) -> None:
        text = (
            'Delegate to `stepwise:test-runner`: "step <paths>".\n'
            'python3 "<dir>/scripts/run_tests.py" step a b\n'
            "Never the full suite.\n"
        )
        self.assertEqual(find_violations({CHECK: text}), [])


class RepoFullSuiteOwnerTest(unittest.TestCase):
    def test_only_regression_runs_full_suite_or_marks_ready(self) -> None:
        """CA-7"""
        files = repo_files()
        self.assertTrue(files, f"no se encontraron archivos {SKILLS}")
        self.assertEqual(
            find_violations(files),
            [],
            "solo /regression corre la suite completa o usa gh pr ready",
        )


if __name__ == "__main__":
    unittest.main()
