---
name: regression
description: Runs the full suite ("Tests (full)") once on the feature branch <feature>, after every step of the ADR is merged, and is the only skill that takes the main PR out of draft. Checks the branch, a clean and up-to-date tree and that every step is merged; runs run_tests.py full with a 3600 s timeout in the background from the main session and waits for the notice (falls back to the user running the command by hand on a timeout or when the background run is not available). Green - writes regression.md next to the steps' traceability, commits and pushes it on <feature>, proposes the main PR's "Verificación Global" and asks before marking it ready, never while a "después del merge" verification is unticked unless the user says so. Red - never fixes on <feature>; diagnoses the failures, names the step that likely introduced them and hands the /stepwise:spec line for a correction step.
disable-model-invocation: true
---

# /regression

Run the full suite on `<feature>` and, if it is green, take the main PR out of draft. Follow the sections in order. Talk to the user in their language. Write every file with the Write and Edit tools (shell edits are blocked by the `stepwise` hooks).

**Never fix on `<feature>`:** this skill does not edit code, tests or the ADR. A failure ends in a correction step added with `/spec` (section 2). The only file it writes in the repo is `regression.md`.

## 0. Preconditions (change nothing yet)

1. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `Tests (full)`, `Base branch`, `Decision docs`, `Traceability`.
   <!-- shared:project-commands -->
   - If the section or a key is missing, change nothing. Reply with every missing key and the exact line to add, and stop:
     ```
     Missing: <"## Project commands" section | keys "<key>", ...> in CLAUDE.md
     Proposed lines:
     - <key>: <value>
     ```
     Use a value the project already documents (cite `path:line`); otherwise write `<value>`. Never edit `CLAUDE.md` without approval and never guess.
   <!-- /shared:project-commands -->
   - In `Decision docs` and `Traceability`, replace `<feature>`. The record goes in the folder of `Traceability` (the value itself if it ends with `/`, otherwise its parent folder): `<that folder>/regression.md`.
2. **Branch.** `git branch --show-current` is `<feature>`: not `Base branch`, and not a step branch. A step branch matches `^(?P<feature>.+)-step-(?P<n>\d+)$`, taking the **last** `-step-` (`multi-step-form-step-2` is feature `multi-step-form`, step `2`); on one, stop and say to run `/regression` on `<feature>` after its last step is closed. The ADR (`Decision docs` for `<feature>`) exists. Otherwise stop.
3. **Clean tree.** `git status --short` shows no changes to tracked files. Otherwise stop and ask.
4. **Up to date.** `git fetch origin <feature>` and compare with `origin/<feature>`. If the fetch fails (for example SSH `Permission denied (publickey)`) and the remote is GitHub, compare `gh api repos/<owner>/<repo>/branches/<feature> -q .commit.sha` with `git rev-parse <feature>`. If they differ, stop and ask the user to update `<feature>`. If neither the fetch nor `gh api` can confirm it, stop and ask; do not assume it is up to date. With no `origin`, warn and continue on the local branch.
5. **Git rules.** <!-- shared:git-rules -->Never `--squash`, `--rebase`, `--delete-branch`, `--force` or `push --force`, and never delete branches, local or remote. If the project's `CLAUDE.md` says something different about merges, rebases or branch deletion, stop and ask which rule applies.<!-- /shared:git-rules -->
6. **Remote.** `git remote get-url origin`. It is GitHub if the URL contains `github.com` (take `<owner>/<repo>` from it).
7. **Every step merged.** Take the steps from the ADR's list of steps.
   - **GitHub:** `gh pr list --head <feature> --base <Base branch> --state open --json number,body,isDraft`. With no open main PR, stop and say so. Every step must be ticked in its `## Pasos` checklist (`- [x] **Paso <k>:**`).
   - **Not GitHub, or no `origin`:** for every step `<k>`, `<feature>-step-<k>` (local or `origin/`) must be an ancestor of `<feature>`: `git merge-base --is-ancestor <that branch> <feature>`. A step whose branch does not exist cannot be confirmed: stop and ask.
   - If a step is missing, stop and list the missing steps (`Paso <k>: <title>`) and what is next for each one (`/implement <k>`, `/check` or `/close`).

## 1. Full suite

1. **Commit under test:** `git rev-parse HEAD`. Keep it for `regression.md`, also when `Tests (full)` is `none`.
2. **`Tests (full)` is `none`:** do not run anything; record `none` and go to section 3.
3. **Run in the background, from the main session.** Do not delegate it to `stepwise:test-runner`: a subagent that leaves a process in the background and finishes does not get its notice. Run this with the Bash tool and `run_in_background: true`, from the project root, exactly once:
   ```bash
   python3 "<this skill's directory>/../../scripts/run_tests.py" full --timeout 3600
   ```
   The foreground limit of a Bash call (600 s) does not apply to a background run, so suites of 20 or 30 minutes fit. The script's report has at most 10 lines (`Command:`, `Totals:`, `Failures:`, `Note:`), so it does not flood the context.
4. **Wait for the notice** that the command finished. Do not start a second copy, do not stop it, and make no `sleep`, polling, early read of its output or other work meanwhile: the notice is the signal. If you have to end your turn to receive it, say only, in one line, that the suite is still running; that is waiting, not a missing notice. Then read the output file the notice names, only with `tail -n 20 "<output file>"`: the path in double quotes and with forward slashes (`C:/Users/...`, never `C:\Users\...`, which Bash mangles).
5. **Manual fallback** (not a failure, costs nothing): when the report says `timeout after 3600 s`, when the background run cannot be started, or when no notice arrives (for example the session cannot wait for it). Give the user the exact `Tests (full)` command, ask them to run it from the project root and paste its totals and failures, and **end the turn**. Continue with what they paste; it is recorded with `Ejecutó: usuario`.
6. **Green:** the command exited with 0 and every `Totals` row says `0 failed, 0 errors`, with no `not available` or `not run` row: section 3. **Not readable:** a `not available` row with exit 0 (a runner the script does not recognize): show the report's last lines and ask the user whether it passed; their answer decides green or red. **Red:** anything else, section 2.

## 2. Red: diagnose, do not fix

1. **Change nothing:** no edits to code, tests or the ADR, no commit, no `regression.md`, no PR changes.
2. **For each failure** (the report lists 5 at most): read the failing test and the code it exercises, by range, in the main session. Find the step that likely introduced it: `git log --oneline <Base branch>..<feature> -- <files>` and the step's merge commit (`Merge pull request #<num> from <owner>/<feature>-step-<k>`).
3. **Pre-existing:** if neither the test nor the code it exercises is in `git diff --name-only <Base branch>...<feature>` and nothing in the feature explains it, it likely fails on `Base branch` too. Ask the user: leave it (it is recorded in `regression.md` as pre-existing, with their decision) or fix it with a correction step. Continue as green (section 3) only if every failure is left that way **and** their number equals `failed + errors` in `Totals`: the report lists 5 at most (`Failures: <N> not shown`), so with more, ask the user for the full list first; never leave a failure the user has not seen.
4. **Report**, at most 10 lines: each failure (`<file>::<test> — <file>:<line>: <error>`), the likely cause, the step (`Paso <k>`, commit), and the line for the correction step, ready to copy:
   ```
   /stepwise:spec <feature> Paso de corrección: <test> falla en <file>:<line> (<error>), introducido en el paso <k> (<commit>). Causa probable: <cause>.
   ```
   Then stop. Say to run `/regression` again once that step is closed.

## 3. Green: record and ready

1. **Verifications after the merge** (GitHub): read the main PR body (`gh pr view <num> --json body,isDraft`) and list every unticked `- [ ] Verificación después del merge (...)` item.
2. **Record.** First check that `<feature>` did not move during the run: `git fetch origin <feature>`, and `origin/<feature>` is still the commit under test (section 1.1); if the fetch fails, compare `gh api repos/<owner>/<repo>/branches/<feature> -q .commit.sha` with it instead (no `origin`: skip this check). If it moved, stop: write nothing, commit nothing and do not touch the main PR; say a commit arrived during the run and to run `/regression` again once `<feature>` is updated. If neither confirms it, stop and ask. Then write `regression.md` (Write; replace it if it exists, git keeps the history):
   ```markdown
   # [<feature>] Regresión

   - **Fecha:** <YYYY-MM-DD>
   - **Rama:** `<feature>`
   - **Commit probado:** `<sha from section 1.1>`
   - **Comando:** `<the Command line of the report>` | `none`: el proyecto no tiene suite automática.
   - **Totales:** <the Totals of the report, one line per command when it chains several>
   - **Ejecutó:** segundo plano (`run_tests.py full --timeout 3600`) | usuario
   - **Fallos preexistentes que se dejaron:** <test — motivo, decisión del usuario> | ninguno
   - **Verificaciones después del merge:** <N sin marcar: item, item> | todas confirmadas | ninguna
   ```
3. **Commit** only that file: `git add <that folder>/regression.md`, by path (never `git add -A`: the tree may have untracked files); write the message with Write in a temporary directory outside the repo (the session's scratchpad if there is one) and run `git commit -F <file>`, with the message `docs(<feature>): add regression run`.
4. **Push:** `git push origin <feature>` (without `-u`). <!-- shared:push-https -->If SSH fails with `Permission denied (publickey)`, the remote is GitHub and `gh auth status` is logged in, retry once over HTTPS for that command only, without changing the remote or the global configuration:<!-- /shared:push-https -->
   ```bash
   git -c credential.helper= -c credential.helper='!gh auth git-credential' push https://github.com/<owner>/<repo>.git <feature>
   ```
   **Push rejected because `origin/<feature>` moved** after the check of item 2 (non-fast-forward): stop. Do not `pull`, do not retry and do not edit the main PR: the green run is not of the current `<feature>`. Report that the commit of `regression.md` stayed local and not pushed, and give the user the exact command to drop it, `git reset --keep HEAD~1` (it removes only that commit and leaves the tree clean; it refuses instead of discarding other local changes), then to update `<feature>` and run `/regression` again.
   **Not GitHub:** stop after the push and report what was skipped. With no `origin`, skip the push too.
5. **Main PR body.** Fill its "Verificación Global" section with the run (command, totals, who ran it, a link to `regression.md`), replacing `pendiente de /regression`, and tick `Suite completa en verde` in "Checklist de Entrega". If either section is missing (for example the user declined the description in the last `/close`), add it from `../close/references/main-pr-template.md` (from this skill's directory). Change nothing else. Show it and **ask** before applying it with `gh pr edit <num> --body-file <file>` (written with Write in a temporary directory outside the repo). Without a yes, the body stays as it was.
6. **Ready.** Offer `gh pr ready <num>` only when all of these hold, and **ask** before running it; without a yes, the PR stays in draft:
   - the suite is green, or its only failures are pre-existing ones the user chose to leave, or `Tests (full)` is `none`;
   - no `Verificación después del merge` item is unticked (read the body again);
   - the body has no "Verificación de instalación desde `develop`" section with placeholders still in it (`/close` leaves it unfilled when the verification did not run);
   - **same commit:** `git fetch origin <feature>`, and `origin/<feature>` is the commit of `regression.md`. If the fetch fails (for example SSH `Permission denied (publickey)`), compare `gh api repos/<owner>/<repo>/branches/<feature> -q .commit.sha` with that commit instead. If neither confirms it, stop and ask; do not assume it. If another commit arrived, stop and say to run `/regression` again.
7. **Unticked verifications or an unfilled installation section:** while a `Verificación después del merge` item is unticked, or the "Verificación de instalación desde `develop`" section still has placeholders, do not run `gh pr ready` and do not offer it: list what is missing and say the PR stays in draft until it is confirmed (ticked on GitHub) or filled. Only if the user explicitly says to mark it ready anyway: add `- **Ready sin confirmar:** <qué quedó sin confirmar (verificaciones, instalación) y la decisión del usuario, YYYY-MM-DD>` to `regression.md`, commit it (`docs(<feature>): record ready decision`) and push it as in items 3 and 4, check the same commit again (item 6) and ask before `gh pr ready <num>`.

## 4. Report

At most 6 lines: the totals and who ran them (background or user), the commit tested, `regression.md` and its commit, the main PR body (applied or not), ready (done, declined, or why not: unticked verifications, a new commit, a failing suite), and on red the `/stepwise:spec` line.
