# stepwise

A [Claude Code](https://claude.com/claude-code) plugin for step-by-step feature delivery. Every feature gets an ADR with numbered acceptance criteria, split into small steps. Each step is implemented test-first, verified, reviewed and merged as its own Sub-PR, with a traceability file per step.

## The flow

```
spec → implement → check → audit → close
```

| Stage | Skill | What it does |
|---|---|---|
| Plan | `/stepwise:spec <description>` | Investigates the code, interviews you only on what the code can't answer, and writes the ADR (acceptance criteria `CA-n` in Given/When/Then, steps, risks). With your approval, creates the feature branch and opens the main PR as a draft. Never writes code. |
| Implement | `/stepwise:implement <n>` | Creates `<feature>-step-<n>` and, for each criterion, writes the test first and then the code until the step's tests pass. No commit. |
| Verify | `/stepwise:check` | Runs the full suite, migrations check, lint and type check. Fixes only what belongs to the step (3 attempts at most) and records the results with a fingerprint of the diff. |
| Review | `/stepwise:audit self \| comments [<pr>] \| pr <pr>` | `self` reviews the step's diff and fixes blockers; `comments` triages a PR's unresolved review comments; `pr` drafts a review of someone else's PR. Never posts to GitHub without your approval. |
| Close | `/stepwise:close` | Runs `/audit self` if needed, completes the traceability, commits, pushes, opens and merges the Sub-PR into the feature branch, and ticks the step in the main PR. |

You chain the stages yourself: the skills are user-invoked only (`disable-model-invocation`), so Claude never starts one on its own. When no other command uses the name, the short form works too (`/spec`, `/check`…).

## Installation

```
/plugin marketplace add juanpa1601/stepwise
/plugin install stepwise@stepwise
```

Then restart the session: skills load when a session starts. To enable it for everyone on a project, add this to the project's `.claude/settings.json`:

```json
"extraKnownMarketplaces": {
  "stepwise": { "source": { "source": "github", "repo": "juanpa1601/stepwise", "ref": "main" }, "autoUpdate": true }
},
"enabledPlugins": { "stepwise@stepwise": true }
```

**Requirements:** git, the [GitHub CLI](https://cli.github.com/) (`gh`) for the PR steps, and `python3` 3.10+ for the hooks and scripts (standard library only). On Windows, Claude Code must use Git Bash, and if cloning fails with `Filename too long`, run `git config --global core.longpaths true`.

## Agents

| Agent | Model | What it does |
|---|---|---|
| `stepwise:explore` | Sonnet | Read-only codebase search; returns conclusions with `path:line`. |
| `stepwise:test-runner` | Haiku | Runs the project's tests through `scripts/run_tests.py` and reports totals and the first failures in 10 lines at most. |
| `stepwise:code-reviewer` | Opus | Reviews a diff against the ADR with clean context and returns `blocker`, `suggestion` and `question` findings with a proposed fix. Never edits or posts. |

## Hooks

- `block_inplace_edits`: denies editing project files from the shell (`sed -i`, redirections, `Set-Content`…) and asks for Edit/Write, so every change goes through the diff.
- `block_env_access`: denies reading or writing `.env` files (templates such as `.env.example` are allowed).
- `ask_gh_api_writes`: asks for confirmation before any `gh api` call that writes.

They are guards against mistakes, not a security boundary.

## Configuration

Nothing is configured inside the plugin. Each project declares its commands in its `CLAUDE.md`, and every skill and agent reads them from there; if a key is missing, they stop and propose the line. Use `none` for keys that don't apply:

```markdown
## Project commands
- Tests (step): pytest
- Tests (full): pytest
- Lint/format: ruff check .
- Type check: mypy .
- Migrations check: none
- Base branch: main
- Decision docs: docs/decisions/<feature>/business-rules.md
- Traceability: docs/pull-requests/<feature>/step-<n>.md
```

- **Optional keys:** `Docs paths` (for example `'*.md' 'docs/**'`) lets `/close` skip re-running the suite when only documentation changed. `Prompts` (for example `docs/prompts/<feature>/`) makes `/spec` save the exact request in that folder, in the same commit as the ADR, which links it.
- **Permissions:** declare the `ask` rules from [`references/ask-rules.json`](plugins/stepwise/references/ask-rules.json) in the project's `.claude/settings.json`, so commits, pushes and GitHub writes always ask first. `/check` warns when they drift.
- **Compaction window (recommended):** add `"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "500000"` (a string, no suffix) to the `env` of the project's `.claude/settings.json`. At 200K, a long step with `/close` compacts halfway through; at 1M it almost never compacts, but every turn costs more. The plugin can't set it, because a plugin's `settings.json` drops `env`, and the project value wins over the user one.
- **Language:** the skills talk to you in your language, but the ADR, traceability and PR templates they write are in Spanish.
- **Adopting it in an existing project:** see the [migration template](docs/migration-template.md).

The full reference (fingerprints, manual criteria, projects without tests, versioning) is in the [plugin README](plugins/stepwise/README.md), and the design decisions are in [the ADR](docs/decisions/bootstrap/business-rules.md).

## Developing stepwise

This repo uses its own flow. Once per clone, in a Claude Code session at the repo root:

```
/plugin marketplace add ./ --scope local
/plugin install stepwise@stepwise --scope local
```

To try uncommitted changes, start a session with `claude --plugin-dir <absolute path>/plugins/stepwise`. Tests are listed under `## Project commands` in [`CLAUDE.md`](CLAUDE.md). Every change under `plugins/stepwise/` must bump `version` in `plugin.json`, as `tests/test_plugin_version.py` enforces.

## License

[MIT](LICENSE)
