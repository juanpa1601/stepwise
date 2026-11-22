# Changelog

Changes to the `stepwise` plugin. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/) with the [versioning rule](plugins/stepwise/README.md#versioning).

## [Unreleased]

## [2.1.0] - 2026-11-21

### Added
- **The `/worktree` skill**, user-invoked only, with a guide in [`docs/worktrees.md`](docs/worktrees.md): `new <folder>` creates a `--detach` worktree from `origin/<Base branch>` in `../<folder>`, creates the `.venv` if `Lint/format` uses it, gives the command to copy the environment files and enters it with `EnterWorktree`; `remove <folder>`, once the main PR is merged, takes the test compose down with `-p <worktree project>`, `rm -s -v -f` and `down --rmi local`, with the user's yes deletes only the volumes with that project's label and prefix (it stops if a container of that project belongs to another folder), and removes the worktree without deleting the branch or using `--force`.
- **The `skills/worktree/scripts/worktree_check.py` script**, read-only and offline, used by `/worktree`. `new <folder>` validates `../<folder>` (the name, that it doesn't exist, and that its Docker Compose project name isn't another worktree's, a `-p` or `--project-directory` of the commands, a top-level `name:` or the folder of a compose file outside the root) and reports the `.venv`, the test compose files and the environment files to copy, by name only. `remove <folder>` checks a registered worktree with a branch and reports its feature, its Compose project and the compose calls to take down.

### Changed
- **The plugin README is now in English**, like the root README and this CHANGELOG. The section names and markers the skills write (`## Pruebas`, `### Tests del paso`, `después del merge`…) don't change and are quoted verbatim. The `Versionado` section is now `Versioning` (`#versioning`).

## [2.0.0] - 2026-11-18

### Added
- **The `/regression` skill:** runs `Tests (full)` once on `<feature>`, with every step merged, in the background from the main session (`run_tests.py full --timeout 3600`, with a manual fallback). When green, it writes `regression.md`, commits and pushes it on `<feature>`, and it is the only skill that takes the main PR out of draft. When red, it fixes nothing and proposes a correction step with `/spec`.

### Changed
- **Major:** `/check` and `/close` run only the step's tests (the ones `/implement` lists under `### Tests del paso`), never `Tests (full)`, and the last `/close` leaves the main PR in draft and asks for `/regression`. A project in the middle of a feature when it updates: `/check` builds the list for a step that has none, and the main PR leaves draft through `/regression`.

## [1.1.0] - 2026-11-10

### Added
- **The optional `Prompts` key** in `## Project commands`: with it, `/spec` saves the exact request text to `<Prompts>/<YYYY-MM-DD>-spec.md` (or `-spec-step-<n>.md` for a new step), with a short header, in the same commit as the ADR, and the ADR links it from "Fuente / Documento". Without the key, nothing changes.
- **Karma in `scripts/run_tests.py`**: it reads Karma's summary (`Totals:` with the skipped count, and `Failures:` with the test, its spec and the message), and it strips ANSI codes from every line before reading and reporting it, also in generic mode.

## [1.0.0] - 2026-11-09
First public release.

### Added
- **Skills**, invoked only by the user (`/stepwise:<skill>`):
  - `/spec`: interviews, investigates and writes the ADR with `CA-n` criteria and steps; with approval, creates the branch and the draft main PR;
  - `/implement <n>`: implements a step test-first on `<feature>-step-<n>`, without committing;
  - `/check`: full suite, migrations, lint and type check, with 3 fix attempts, and records "Pruebas" with the fingerprint;
  - `/audit`: `self` (the step's diff with `code-reviewer`), `comments [<num>]` (a PR's review comments) and `pr <num>` (someone else's PR); never posts without approval;
  - `/close`: `/audit self`, traceability, commit, push, Sub-PR merged with `--merge` and the main PR checklist.
- **Agents:** `explore` (Sonnet, read-only search), `test-runner` (Haiku, runs `scripts/run_tests.py`) and `code-reviewer` (Opus, `blocker`, `suggestion` and `question` findings).
- **`PreToolUse` hooks:** `block_inplace_edits`, `block_env_access` and `ask_gh_api_writes`.
- **Scripts:** `scripts/run_tests.py`, `skills/close/scripts/fingerprint.py` and `skills/check/scripts/settings_alignment.py`.
- **The `## Project commands` contract** in each project's `CLAUDE.md`, with the optional `Docs paths` key.
- **Manual criteria** `(manual: <motivo>)`, projects without tests (`none`) and `después del merge` verifications.
- **The `ask` rule list** in `references/ask-rules.json`, which `/check` compares with the project's `.claude/settings.json`.

[Unreleased]: https://github.com/juanpa1601/stepwise/compare/stepwise--v2.1.0...main
[2.1.0]: https://github.com/juanpa1601/stepwise/compare/stepwise--v2.0.0...stepwise--v2.1.0
[2.0.0]: https://github.com/juanpa1601/stepwise/compare/stepwise--v1.1.0...stepwise--v2.0.0
[1.1.0]: https://github.com/juanpa1601/stepwise/compare/stepwise--v1.0.0...stepwise--v1.1.0
[1.0.0]: https://github.com/juanpa1601/stepwise/releases/tag/stepwise--v1.0.0
