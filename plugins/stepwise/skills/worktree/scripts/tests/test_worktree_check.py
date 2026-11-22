"""Tests of ``worktree_check.py``: run the real script against temporary git repositories.

Standard library only (``unittest``). Needs ``git`` on the ``PATH``. From the root of this repository::

    python3 -m unittest discover plugins/stepwise/skills/worktree/scripts/tests -v
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT: Path = Path(__file__).resolve().parents[1] / "worktree_check.py"
GUIDE: str = "https://github.com/juanpa1601/stepwise/blob/main/docs/worktrees.md"
GITIGNORE: str = ".env\n.env.*\nnode_modules/\n.venv/\n"


def contract(
    lint: str = "none",
    step: str = "python3 -m unittest",
    full: str = "python3 -m unittest discover",
    migrations: str = "none"
) -> str:
    """Return a ``CLAUDE.md`` with a ``## Project commands`` section built from the given values."""
    return (
        "# Project\n\n## Project commands\n"
        f"- Tests (step): {step}\n"
        f"- Tests (full): {full}\n"
        f"- Lint/format: {lint}\n"
        "- Type check: none\n"
        f"- Migrations check: {migrations}\n"
        "- Base branch: develop\n\n"
        "## Other\n- Tests (full): ignored\n"
    )


class RepoCase(unittest.TestCase):
    """A main copy at ``<tmp>/parent/main`` with one commit, and helpers to change it and run the script."""

    def setUp(self) -> None:
        self._tmp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.parent: Path = Path(self._tmp.name).resolve() / "parent"
        self.main: Path = self.parent / "main"
        self.main.mkdir(parents=True)
        self.git("init", "-q", "-b", "develop")
        self.write(".gitignore", GITIGNORE)
        self.write("CLAUDE.md", contract())
        self.commit()

    def tearDown(self) -> None:
        subprocess.run(["git", "worktree", "prune"], cwd=self.main, capture_output=True)
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        """Run git in the main copy and return its output; fail the test if git fails."""
        result: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.main, capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write(self, relative: str, text: str, root: Path | None = None) -> None:
        """Write ``text`` to ``relative`` under ``root`` (by default, the main copy)."""
        path: Path = (root or self.main) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self) -> None:
        """Commit everything that is not ignored."""
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fixture")

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the script from the main copy with ``args``."""
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.main, capture_output=True, text=True, encoding="utf-8"
        )

    def lines(self, *args: str) -> list[str]:
        """Run the script, assert exit 0 and return its output lines."""
        result: subprocess.CompletedProcess[str] = self.run_script(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.splitlines()

    def field(self, lines: list[str], name: str) -> str:
        """Return the value of the ``<name>: <value>`` line in ``lines``."""
        for line in lines:
            if line.startswith(f"{name}: "):
                return line[len(name) + 2:]
        self.fail(f"no {name} line in {lines}")


class NewValidTests(RepoCase):
    """CA-1: a valid, new folder outside the repository."""

    def test_reports_every_field(self) -> None:
        lines: list[str] = self.lines("new", "feat-a")
        self.assertEqual(lines[0], "ok")
        self.assertEqual(self.field(lines, "Carpeta"), (self.parent / "feat-a").as_posix())
        self.assertEqual(self.field(lines, "Proyecto"), "feat-a")
        self.assertEqual(self.field(lines, "venv"), "no")
        self.assertEqual(self.field(lines, "compose"), "none")
        self.assertEqual(self.field(lines, "Proyecto fijo"), "ninguno")
        self.assertEqual(self.field(lines, "Entorno"), "ninguno")
        self.assertFalse((self.parent / "feat-a").exists())

    def test_creates_nothing(self) -> None:
        before: str = self.git("worktree", "list", "--porcelain")
        self.lines("new", "feat-a")
        self.assertEqual(self.git("worktree", "list", "--porcelain"), before)
        self.assertEqual(self.git("status", "--short"), "")


class NewInvalidTests(RepoCase):
    """CA-2: an invalid folder exits with a reason and changes nothing."""

    def assert_refused(self, folder: str, reason: str) -> None:
        result: subprocess.CompletedProcess[str] = self.run_script("new", folder)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_bad_names(self) -> None:
        for folder in ("Feat", "a/b", "a\\b", "a.b", "..", ".", "-a", "_a", "a b"):
            with self.subTest(folder=folder):
                self.assert_refused(folder, "nombre inválido")
                self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_empty_name(self) -> None:
        self.assert_refused("", "nombre inválido")

    def test_folder_exists(self) -> None:
        (self.parent / "taken").mkdir()
        self.assert_refused("taken", "ya existe")

    def test_other_worktree_with_same_folder_name(self) -> None:
        other: Path = Path(self._tmp.name).resolve() / "elsewhere" / "Shared"
        other.parent.mkdir()
        self.git("worktree", "add", "-q", "--detach", str(other), "HEAD")
        self.assert_refused("shared", "otro worktree")
        self.assertFalse((self.parent / "shared").exists())

    def test_compose_trims_leading_underscores_and_dashes(self) -> None:
        for name in ("_shared", "-shared"):
            with self.subTest(name=name):
                other: Path = Path(self._tmp.name).resolve() / f"o{name}" / name
                other.parent.mkdir()
                self.git("worktree", "add", "-q", "--detach", str(other), "HEAD")
                self.assert_refused("shared", "otro worktree")
                self.git("worktree", "remove", str(other))

    def test_main_copy_folder_name_counts(self) -> None:
        self.assert_refused("main", "ya existe")

    def test_project_taken_by_the_commands_or_the_compose(self) -> None:
        """With a compose, ``new`` refuses a project name that a ``-p``, a ``--project-directory`` or a top-level
        ``name:`` already fixes, and a ``name:`` with a ``$`` variable."""
        cases: tuple[tuple[str, str, str, str], ...] = (
            ("proj", "docker compose -p proj -f a.yml run test", "", "-p proj"),
            ("shared", "docker compose --project-directory ci/shared -f a.yml run test", "", "--project-directory"),
            ("parent", "docker compose --project-directory .. -f a.yml run test", "", "--project-directory .."),
            ("app-test", "docker compose -f a.yml run test", "name: app-test\nservices: {}\n", "name: app-test"),
            ("dollar", "docker compose -f a.yml run test", "name: ${APP:-dollar}\nservices: {}\n", "depende de una variable"),
        )
        for folder, full, compose, reason in cases:
            with self.subTest(folder=folder):
                self.write("a.yml", compose or "services: {}\n")
                self.write("CLAUDE.md", contract(full=full))
                self.assert_refused(folder, reason)
                self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)
                self.assertFalse((self.parent / folder).exists())


class MainCopyTests(RepoCase):
    """CA-7: both modes run only from the root of the main copy."""

    def run_from(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
        )

    def test_refused_from_a_linked_worktree(self) -> None:
        linked: Path = self.parent / "linked"
        self.git("worktree", "add", "-q", "-b", "feat", str(linked))
        for args in (("new", "x"), ("remove", "linked")):
            with self.subTest(args=args):
                result: subprocess.CompletedProcess[str] = self.run_from(linked, *args)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("copia principal", result.stderr)
        self.assertFalse((self.parent / "x").exists())

    def test_refused_from_a_subfolder(self) -> None:
        sub: Path = self.main / "sub"
        sub.mkdir()
        result: subprocess.CompletedProcess[str] = self.run_from(sub, "new", "x")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("raíz de la copia principal", result.stderr)


class VenvTests(RepoCase):
    """CA-3: ``venv: yes`` only when ``Lint/format`` mentions ``.venv``."""

    def set_lint(self, lint: str) -> None:
        self.write("CLAUDE.md", contract(lint=lint))

    def test_posix_python(self) -> None:
        self.set_lint('py=.venv/bin/python; [ -x "$py" ] || py=.venv/Scripts/python; "$py" -m ruff check')
        self.write(".venv/bin/python", "")
        self.assertEqual(self.field(self.lines("new", "x"), "venv"), "yes (.venv/bin/python)")

    def test_windows_python(self) -> None:
        self.set_lint(".venv/Scripts/python -m ruff check")
        self.write(".venv/Scripts/python.exe", "")
        self.assertEqual(self.field(self.lines("new", "x"), "venv"), "yes (.venv/Scripts/python.exe)")

    def test_missing_main_venv_is_a_warning(self) -> None:
        self.set_lint(".venv/bin/python -m ruff check")
        self.assertEqual(
            self.field(self.lines("new", "x"), "venv"), "yes (aviso: la copia principal no tiene .venv)"
        )

    def test_python_search_order(self) -> None:
        self.set_lint(".venv/Scripts/python -m ruff check")
        self.write(".venv/Scripts/python", "")
        self.write(".venv/bin/python", "")
        self.assertEqual(self.field(self.lines("new", "x"), "venv"), "yes (.venv/Scripts/python)")
        self.write(".venv/Scripts/python.exe", "")
        self.assertEqual(self.field(self.lines("new", "x"), "venv"), "yes (.venv/Scripts/python.exe)")

    def test_lint_without_venv(self) -> None:
        self.set_lint("ruff check .")
        self.write(".venv/bin/python", "")
        self.assertEqual(self.field(self.lines("new", "x"), "venv"), "no")

    def test_lint_none(self) -> None:
        self.set_lint("none")
        self.assertEqual(self.field(self.lines("new", "x"), "venv"), "no")


class ComposeTests(RepoCase):
    """CA-4: compose files from ``-f``/``--file`` of the tests and migrations commands."""

    def compose_of(self, **values: str) -> str:
        self.write("CLAUDE.md", contract(**values))
        return self.field(self.lines("new", "x"), "compose")

    def test_each_file_once_in_order(self) -> None:
        self.assertEqual(
            self.compose_of(
                step="docker compose -f docker-compose.test.yml run --build --rm test pytest",
                full="docker compose --file=ci/compose.yml run --rm test && docker compose -f docker-compose.test.yml down",
                migrations='docker-compose --file "docker-compose.test.yml" run --rm test manage.py makemigrations --check',
            ),
            "docker-compose.test.yml, ci/compose.yml",
        )

    def test_fixed_project_names_are_reported(self) -> None:
        """CA-1 and CA-2: a ``-p``/``--project-name`` or ``--project-directory`` in the commands, or a top-level
        ``name:`` in the compose file, makes every worktree share one Compose project."""
        self.write("a.yml", "'name': app-test\nservices:\n  test:\n    image: x\n    name: not-top-level\n")
        self.write("CLAUDE.md", contract(
            step="docker compose -p proj -f a.yml run test",
            full="docker compose --project-name=other -f b.yml run test && docker compose -f a.yml down",
            migrations="docker compose --project-directory ./ops -f a.yml run test",
        ))
        lines: list[str] = self.lines("new", "x")
        self.assertEqual(
            self.field(lines, "Proyecto fijo"),
            "-p proj, -p other, --project-directory ops, name: app-test (a.yml)",
        )

    def test_folder_of_a_compose_outside_the_root_is_reported(self) -> None:
        """CA-1: without ``-p``, Compose names the project after the folder of the compose file, so a compose file
        outside the root fixes one project for every worktree."""
        self.write("CLAUDE.md", contract(full="docker compose -f ci/compose.yml run test"))
        self.assertEqual(self.field(self.lines("new", "x"), "Proyecto fijo"), "carpeta de ci/compose.yml")

    def test_leading_dot_slash_is_dropped(self) -> None:
        """``./x.yml`` is the same file as ``x.yml``, at the root."""
        self.assertEqual(
            self.compose_of(step="docker compose -f ./x.yml run test", full="docker compose -f x.yml run test"), "x.yml"
        )

    def test_without_docker_compose(self) -> None:
        self.assertEqual(self.compose_of(step="rm -f x && pytest", full="tail -f log"), "none")

    def test_flag_of_another_command_is_ignored(self) -> None:
        self.assertEqual(
            self.compose_of(full="tail -f log.txt && docker compose -f a.yml run test; rm -f b.yml"), "a.yml"
        )

    def test_flags_after_the_subcommand_are_ignored(self) -> None:
        self.assertEqual(
            self.compose_of(
                step="docker compose -p proj --env-file vars.txt -f a.yml run --rm test tail -f log",
                full="docker compose --project-directory . --file b.yml logs -f web",
            ),
            "a.yml, b.yml",
        )


class EnvFilesTests(RepoCase):
    """CA-5: environment files to copy, by name only."""

    def env_of(self, compose: str | None = None) -> str:
        if compose is not None:
            self.write("docker-compose.test.yml", compose)
            self.git("add", "docker-compose.test.yml")
            self.git("commit", "-q", "-m", "compose")
            self.write("CLAUDE.md", contract(full="docker compose -f docker-compose.test.yml run --rm test"))
        return self.field(self.lines("new", "x"), "Entorno")

    def test_ignored_env_files_without_templates(self) -> None:
        for name in (".env", ".env.local", "api/.env.docker", ".env.example", ".env.sample", ".envrc"):
            self.write(name, "SECRET=1\n")
        self.assertEqual(self.env_of(), ".env, .env.local, api/.env.docker")

    def test_whole_ignored_folders_are_not_listed(self) -> None:
        self.write("node_modules/pkg/.env", "SECRET=1\n")
        self.write(".venv/.env", "SECRET=1\n")
        self.assertEqual(self.env_of(), "ninguno")

    def test_env_file_forms_of_the_compose(self) -> None:
        for name in (".env.docker", "config/db.env", "cache.env", ".env.web", "same/level.env"):
            self.write(name, "SECRET=1\n")
        compose: str = (
            "services:\n"
            "  test:\n"
            "    env_file: .env.docker\n"
            "  db:\n"
            "    env_file:\n"
            "      - ./config/db.env  # comment\n"
            "      - path: \"cache.env\"\n"
            "        required: false\n"
            "  web:\n"
            "    env_file: ['.env.web', \"${HOME}/x.env\"]\n"
            "    image: x\n"
            "  worker:\n"
            "    env_file:\n"
            "    - same/level.env\n"
            "    image: y\n"
        )
        self.assertEqual(
            self.env_of(compose),
            ".env.docker, config/db.env (sin ignorar), cache.env (sin ignorar), .env.web, same/level.env (sin ignorar)",
        )

    def test_env_file_outside_or_missing_is_not_listed(self) -> None:
        compose: str = (
            "services:\n"
            "  test:\n"
            "    env_file:\n"
            "      - ../outside.env\n"
            "      - /abs/x.env\n"
            "      - C:/abs/y.env\n"
            "      - path: missing.env\n"
            "        required: false\n"
        )
        (self.parent / "outside.env").write_text("SECRET=1\n", encoding="utf-8")
        self.assertEqual(self.env_of(compose), "ninguno")

    def test_env_file_paths_are_resolved_inside_the_root(self) -> None:
        self.write("inside.env", "A=1\n")
        self.write("sub/keep.txt", "")  # ``sub/`` exists, so ``sub/../..`` really leaves the root
        (self.parent / "outside.env").write_text("SECRET=1\n", encoding="utf-8")
        compose: str = (
            "services:\n"
            "  test:\n"
            "    env_file:\n"
            "      - sub/../../outside.env\n"
            "      - sub\\..\\..\\outside.env\n"
            "      - sub/../inside.env\n"
        )
        self.assertEqual(self.env_of(compose), "inside.env (sin ignorar)")

    def test_ignored_compose_env_file_is_not_marked(self) -> None:
        """An untracked file that git does not ignore would block ``git worktree remove`` once copied, so it is
        marked; one inside an ignored folder is not."""
        self.write("secrets/db.env", "A=1\n")
        self.write(".gitignore", GITIGNORE + "secrets/\n")
        self.commit()
        self.assertEqual(self.env_of("services:\n  test:\n    env_file: secrets/db.env\n"), "secrets/db.env")

    def test_absolute_compose_file_lists_no_relative_env_file(self) -> None:
        """A compose given by an absolute ``-f`` is the main copy's own file, so the worktree reads its environment
        files from the main copy too; ``Entorno:`` never lists an absolute path."""
        self.write("config/db.env", "A=1\n")
        self.write("docker-compose.test.yml", "services:\n  test:\n    env_file: config/db.env\n")
        self.git("add", "docker-compose.test.yml")
        self.git("commit", "-q", "-m", "compose")
        absolute: str = (self.main / "docker-compose.test.yml").as_posix()
        self.write("CLAUDE.md", contract(full=f"docker compose -f {absolute} run --rm test"))
        lines: list[str] = self.lines("new", "x")
        self.assertEqual(self.field(lines, "compose"), absolute)
        self.assertEqual(self.field(lines, "Entorno"), "ninguno")

    def test_compose_env_file_is_listed_once_with_the_ignored_one(self) -> None:
        self.write(".env.docker", "SECRET=1\n")
        self.assertEqual(self.env_of("services:\n  test:\n    env_file: .env.docker\n"), ".env.docker")

    def test_tracked_env_file_is_not_listed(self) -> None:
        self.write("config/tracked.env", "A=1\n")
        self.commit()
        self.assertEqual(self.env_of("services:\n  test:\n    env_file: config/tracked.env\n"), "ninguno")


class RemoveTests(RepoCase):
    """CA-6: the feature of a registered worktree that is not the main copy."""

    def add(self, folder: str, *args: str) -> Path:
        path: Path = self.parent / folder
        self.git("worktree", "add", "-q", *args, str(path))
        return path

    def test_feature_branch(self) -> None:
        self.add("wt", "-b", "feat")
        lines: list[str] = self.lines("remove", "wt")
        self.assertEqual(lines[0], "ok")
        self.assertEqual(self.field(lines, "Carpeta"), (self.parent / "wt").as_posix())
        self.assertEqual(self.field(lines, "Rama"), "feat")
        self.assertEqual(self.field(lines, "Feature"), "feat")
        self.assertEqual(self.field(lines, "Proyecto"), "wt")
        self.assertEqual(self.field(lines, "compose"), "none")
        self.assertEqual(self.field(lines, "Llamadas compose"), "none")

    def test_empty_project_name_is_refused_with_a_compose(self) -> None:
        """``-p ""`` is no ``-p`` for Compose, so a folder that normalizes to nothing is refused when there is a
        compose to take down."""
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run --rm test"))
        self.commit()
        self.add("___", "-b", "feat")
        self.assert_refused("___", "proyecto de Compose")

    def test_empty_project_name_without_compose_is_accepted(self) -> None:
        """Without a compose no ``-p`` ever runs, so the name does not matter."""
        self.add("___", "-b", "feat")
        lines: list[str] = self.lines("remove", "___")
        self.assertEqual(self.field(lines, "compose"), "none")
        self.assertEqual(self.field(lines, "Llamadas compose"), "none")

    def test_project_taken_by_someone_else_is_refused(self) -> None:
        """With ``-p "<Proyecto>"``, ``rm``, ``down`` and the label-and-prefix ``volume rm`` would remove what
        belongs to another project."""
        cases: tuple[tuple[str, str, str, str], ...] = (
            ("ci", "docker compose -f ci/compose.yml run test", "", "la carpeta de ci/compose.yml"),
            ("proj", "docker compose -p proj -f a.yml run test", "", "-p proj"),
            ("app-test", "docker compose -f a.yml run test", "name: app-test\nservices: {}\n", "name: app-test"),
            ("shared", "docker compose --project-directory ci/shared -f a.yml run test", "", "--project-directory"),
            ("parent", "docker compose --project-directory .. -f a.yml run test", "", "--project-directory .."),
            # The top-level ``name:`` with its key between quotes, and in a JSON compose file.
            ("quoted-name", "docker compose -f a.yml run test", "\"name\": quoted-name\nservices: {}\n", "name: quoted"),
            ("json-name", "docker compose -f a.yml run test", "{\"name\": \"json-name\", \"services\": {}}\n", "name: json"),
            # An indented root mapping (after ``---``) and a YAML flow mapping.
            ("indented-name", "docker compose -f a.yml run test", "---\n  name: indented-name\n  services: {}\n",
             "name: indented"),
            ("flow-name", "docker compose -f a.yml run test", "{services: {}, name: 'flow-name'}\n", "name: flow"),
            # A name with a variable may fix any project, this one included.
            ("dollar", "docker compose -f a.yml run test", "name: ${APP:-dollar}\nservices: {}\n", "depende de una variable"),
        )
        for folder, full, compose, reason in cases:
            with self.subTest(folder=folder):
                if compose:
                    self.write("a.yml", compose)
                self.write("CLAUDE.md", contract(full=full))
                self.commit()
                self.add(folder, "-b", f"feat-{folder}")
                self.assert_refused(folder, reason)

    def test_project_of_another_worktree_is_refused(self) -> None:
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run test"))
        self.commit()
        self.add("other", "-b", "feat-a")
        self.add("-other", "-b", "feat-b")
        self.assert_refused("-other", "el worktree")

    def test_project_of_the_main_copy_is_refused(self) -> None:
        """``_main`` normalizes to ``main``, the main copy's own project."""
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run test"))
        self.commit()
        self.add("_main", "-b", "feat")
        result: subprocess.CompletedProcess[str] = self.run_script("remove", "_main")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("la copia principal", result.stderr)
        self.assertIn("no lo bajes", result.stderr)

    def test_new_refuses_a_project_taken_by_the_commands(self) -> None:
        """CA-2: ``new`` applies the same refusal."""
        self.write("CLAUDE.md", contract(full="docker compose -f ci/compose.yml run test"))
        result: subprocess.CompletedProcess[str] = self.run_script("new", "ci")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("la carpeta de ci/compose.yml", result.stderr)

    def test_calls_keep_their_files_together(self) -> None:
        """An override is taken down with its base, in one ``down``."""
        self.write("CLAUDE.md", contract(
            step="docker compose -f base.yml -f test.yml run --rm test",
            full="docker compose -f base.yml -f test.yml run --rm test && docker compose -f ./c.yml down",
        ))
        self.commit()
        self.add("wt", "-b", "feat")
        self.assertEqual(
            self.field(self.lines("remove", "wt"), "Llamadas compose"), "-f base.yml -f test.yml; -f c.yml"
        )

    def test_call_files_are_shell_quoted(self) -> None:
        """A path with a space stays one word in ``ps`` and ``down``."""
        self.write("CLAUDE.md", contract(full='docker compose -f "my dir/c.yml" run --rm test'))
        self.commit()
        self.add("wt", "-b", "feat")
        self.assertEqual(self.field(self.lines("remove", "wt"), "Llamadas compose"), "-f 'my dir/c.yml'")

    def test_unreadable_compose_is_refused(self) -> None:
        """CA-2 and CA-6: a compose file in UTF-16 (what ``>`` writes in Windows PowerShell 5.1) may fix any
        project, so ``remove`` and ``new`` refuse it instead of skipping it."""
        (self.main / "wt.yml").write_text("name: other\nservices: {}\n", encoding="utf-16")
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run --rm test"))
        self.commit()
        self.add("wt", "-b", "feat")
        self.assert_refused("wt", "no se puede leer")
        result: subprocess.CompletedProcess[str] = self.run_script("new", "fresh")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no se puede leer", result.stderr)

    def test_remove_reads_no_volumes(self) -> None:
        """The script does not read volumes. The skill removes only the ones Docker labels with the project and
        that carry its prefix, so a volume with its own ``name:`` changes nothing in the report."""
        self.write("wt.yml", "volumes:\n  data:\n    name: shared\nservices: {}\n")
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run --rm test"))
        self.commit()
        self.add("wt", "-b", "feat")
        lines: list[str] = self.lines("remove", "wt")
        self.assertEqual(lines[-1], "Llamadas compose: -f wt.yml")
        self.assertFalse([line for line in lines if line.startswith("Volúmenes")], lines)

    def test_project_is_the_folder_as_compose_normalizes_it(self) -> None:
        """``remove`` fixes ``-p`` to the worktree's own Compose project."""
        self.add("_My.Wt", "-b", "feat")
        self.assertEqual(self.field(self.lines("remove", "_My.Wt"), "Proyecto"), "mywt")

    def test_step_branch_takes_the_last_step(self) -> None:
        self.add("wt", "-b", "multi-step-form-step-2")
        self.assertEqual(self.field(self.lines("remove", "wt"), "Feature"), "multi-step-form")

    def test_compose_from_the_worktree_contract(self) -> None:
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run --rm test"))
        self.commit()
        self.write("CLAUDE.md", contract())
        self.add("wt", "-b", "feat")
        self.assertEqual(self.field(self.lines("remove", "wt"), "compose"), "wt.yml")

    def assert_refused(self, folder: str, reason: str) -> None:
        result: subprocess.CompletedProcess[str] = self.run_script("remove", folder)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)

    def test_not_registered(self) -> None:
        (self.parent / "plain").mkdir()
        self.assert_refused("plain", "no es un worktree")

    def test_main_copy(self) -> None:
        self.assert_refused("main", "copia principal")

    def test_detached_head(self) -> None:
        self.add("wt", "--detach")
        self.assert_refused("wt", "HEAD separado")

    def test_registered_worktree_without_its_folder(self) -> None:
        """A registered worktree whose folder is gone is refused with ``git worktree prune``, not a contract
        error."""
        shutil.rmtree(self.add("wt", "-b", "feat"))
        self.assert_refused("wt", "git worktree prune")

    def test_rejection_points_to_the_guide_url(self) -> None:
        self.write("CLAUDE.md", contract(full="docker compose -f wt.yml run test"))
        self.commit()
        self.add("_main", "-b", "feat")
        self.assert_refused("_main", GUIDE)

    def test_path_in_name(self) -> None:
        for folder in ("a/b", "..", ".", ""):
            with self.subTest(folder=folder):
                self.assert_refused(folder, "nombre inválido")


class UsageTests(RepoCase):
    """CA-7: usage and contract errors exit with 2."""

    def test_bad_usage(self) -> None:
        for args in ((), ("new",), ("other", "x"), ("new", "x", "y")):
            with self.subTest(args=args):
                self.assertEqual(self.run_script(*args).returncode, 2)

    def test_missing_section(self) -> None:
        self.write("CLAUDE.md", "# Project\n")
        result: subprocess.CompletedProcess[str] = self.run_script("new", "x")
        self.assertEqual(result.returncode, 2)
        self.assertIn("## Project commands", result.stderr)

    def test_git_failure(self) -> None:
        plain: Path = Path(self._tmp.name).resolve() / "plain"
        plain.mkdir()
        environment: dict[str, str] = {**os.environ, "GIT_CEILING_DIRECTORIES": str(plain.parent)}
        result: subprocess.CompletedProcess[str] = subprocess.run(
            [sys.executable, str(SCRIPT), "new", "x"],
            cwd=plain, capture_output=True, text=True, encoding="utf-8", env=environment
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("error: git", result.stderr)


if __name__ == "__main__":
    unittest.main()
