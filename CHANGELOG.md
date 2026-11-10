# Changelog

Changes to the `stepwise` plugin. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/) with the [versioning rule](plugins/stepwise/README.md#versionado).

## [Unreleased]

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

[Unreleased]: https://github.com/juanpa1601/stepwise/compare/stepwise--v1.0.0...main
[1.0.0]: https://github.com/juanpa1601/stepwise/releases/tag/stepwise--v1.0.0
