---
name: spec
description: Plans a new feature, a bug fix or a new step of an existing feature. Investigates the code with stepwise:explore, interviews the user only on what the code cannot answer, writes the ADR (numbered acceptance criteria CA-n in Given/When/Then, steps with the criteria each covers, out of scope, risks, open decisions) and, after approval, creates the feature branch, commits the ADR (with the optional Prompts key, also the request text as a prompt file, in the same commit) and opens the main PR in draft. Never writes code.
argument-hint: <description of the feature, bug or new step>
disable-model-invocation: true
---

# /spec

Plan the request in `$ARGUMENTS`. Follow the sections in order. Talk to the user in their language; the ADR is written in the language of the template.

**You never write code, tests or migrations.** The only files you write are the ADR and, when `Prompts` is declared, the prompt file (section 6), with the Write and Edit tools (shell edits are blocked by the `stepwise` hooks).

## 0. Preconditions (change nothing yet)

1. **Request.** If `$ARGUMENTS` is empty, ask for the description and stop.
2. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `Base branch`, `Decision docs`.
   <!-- shared:project-commands -->
   - If the section or a key is missing, change nothing. Reply with every missing key and the exact line to add, and stop:
     ```
     Missing: <"## Project commands" section | keys "<key>", ...> in CLAUDE.md
     Proposed lines:
     - <key>: <value>
     ```
     Use a value the project already documents (cite `path:line`); otherwise write `<value>`. Never edit `CLAUDE.md` without approval and never guess.
   <!-- /shared:project-commands -->
   - In `Decision docs`, `<feature>` is replaced by the feature name.
   - **Optional key `Prompts`:** a folder (for example `- Prompts: docs/prompts/<feature>/`), with `<feature>` replaced. If it is missing, do not ask for it and do not stop: no prompt file is written, and the summary (section 5) and the report (section 7) say so.
3. **Working tree.** `git status --short` must show no changes to tracked files. If it does, stop and ask: switching branches would carry them along.

## 1. Classify the request

Decide which one it is:
- **feature:** new behavior;
- **bug:** something that worked or should work and fails;
- **new step:** more work for a feature that already has an ADR (the current branch is `<feature>`, or the request names it, and `Decision docs` for it exists).

If it is not clear, ask (section 3 rules) before investigating.

**New step, before writing anything:** you must be on `<feature>` (not a `-step-<n>` branch) and it must be up to date: `git fetch origin <feature>` and compare with `origin/<feature>`; if the fetch fails and the remote is GitHub, compare `gh api repos/<owner>/<repo>/branches/<feature> -q .commit.sha` with `git rev-parse <feature>`. If either check fails, stop and say so. If neither the fetch nor `gh api` can confirm it (for example the remote is not GitHub and the fetch fails), stop and ask; do not assume it is up to date.

## 2. Investigate

1. Launch one or more `stepwise:explore` agents **in parallel**, each with one concrete question and its breadth ("medium" or "very thorough"): where the behavior lives, what tests cover it, which conventions apply, what a bug's path is.
2. Read `CLAUDE.md` and the `README.md` of each folder the work will touch (and its parents up to the root), when they exist.
3. For a new step, read the existing ADR in full.

## 3. Interview

Ask only what the code and the docs do not answer: scope, business rules, edge cases, permissions, expected behavior of a bug.

- **4 questions at most per round.** Use `AskUserQuestion` when it exists in the session. If it does not (for example in `claude -p`), ask in plain text as a numbered list and **end the turn**; continue when the answers arrive.
- Do not fill gaps with assumptions. What the user leaves open goes to "Decisiones Abiertas" in the ADR.
- If the request and the code already answer everything, skip the interview and say so in one line.

## 4. Write the ADR

1. **Feature name:** kebab-case, at most 4 words (for a bug, start with `fix-`). It is the branch name. For a new step, use the existing one.
2. **Path:** `Decision docs` with `<feature>` replaced.
3. Read `references/decision-template.md` (in this skill's directory, not the project's) and follow its structure. **150 lines at most.**
   - **Acceptance criteria:** numbered `CA-1`, `CA-2`… in Given/When/Then ("Dado / Cuando / Entonces"), each verifiable with a test, except the manual ones below.
   - **Manual CAs:** a CA with no reasonable automated test (a step that only touches configuration or documentation, or a check only the user can run, such as another `/stepwise:` skill) gets the mark `(manual: <reason>)` right after its id: `**CA-<n> (manual: <reason>):**`. The reason is required. The mark is only a proposal until the user approves the ADR: list every marked CA in the approval summary (section 5). If the user rejects a mark, remove it and make that CA testable. With `Tests (step): none`, every CA is manual and needs no mark. In a bug, mark the regression CA manual only when no automated test can reproduce the error; `/implement` then records its manual reproduction under `## Evidencia de regresión`, as with `Tests (step): none`.
   - **Steps:** each one with the CAs it covers and a small scope (which files or modules). Every CA is covered by some step.
   - **Out of scope** and **risks**, always filled.
   - **Bug:** `CA-1` is a regression test that reproduces the error (the input, the wrong result today and the expected result).
   - **New step:** update the existing ADR instead of creating another: append the new CAs and steps, continuing the numbering, and touch nothing that is already done.
   - **Source (`Fuente / Documento`), with `Prompts`:** link the prompt file that section 6 will write (its path relative to the ADR). For a new step, add the link to that step's prompt file and keep what the field already says.
   - Remove the template's HTML comments.

## 5. Approval

Show a short summary: type, feature name and branch, the CAs (one line each), the CAs proposed as manual (`CA-<n>: manual — <reason>`, one line each, or "ninguno"), the steps with their CAs, the open decisions, and the prompt file (its path, or, without `Prompts`, the line `Prompt: no se guarda (sin la clave opcional Prompts)` written literally, without translating or rewording it). Ask for approval and end the turn.

- **Without explicit approval, do not write the prompt file, create branches, commit, push or open PRs.**
- If the user asks for changes, edit the ADR and show the summary again.

## 6. After approval

**Git rules:** <!-- shared:git-rules -->Never `--squash`, `--rebase`, `--delete-branch`, `--force` or `push --force`, and never delete branches, local or remote. If the project's `CLAUDE.md` says something different about merges, rebases or branch deletion, stop and ask which rule applies.<!-- /shared:git-rules -->

**Remote:** `git remote get-url origin`. It is GitHub if the URL contains `github.com`. Otherwise, warn that the main PR is skipped (not a failure). With no `origin` at all, warn that push and PR are skipped.

**Push:** `git push origin <branch>` (without `-u`). <!-- shared:push-https -->If SSH fails with `Permission denied (publickey)`, the remote is GitHub and `gh auth status` is logged in, retry once over HTTPS for that command only, without changing the remote or the global configuration:<!-- /shared:push-https -->
```bash
git -c credential.helper= -c credential.helper='!gh auth git-credential' push https://github.com/<owner>/<repo>.git <branch>
```

**Prompt file** (only with `Prompts`; written with Write, never before approval):
- **Path:** the `Prompts` folder plus `<YYYY-MM-DD>-spec.md` for a feature or a bug, or `<YYYY-MM-DD>-spec-step-<n>.md` for a new step, where `<n>` is the number of the first step this `/spec` adds. The date is today's.
- **Already exists:** check it right before the Write, after the approval, with Glob on the exact path: an earlier check (for example in the summary) does not count, because the file may appear in between. If it exists, do not write it. Stop before the commit, show the path and ask: overwrite, use another name, or do not save it. Do not commit until the user answers. For another name, repeat this check on the new path before writing.
- **The ADR's link follows the final path:** before the commit, if the path written differs from the one in `Fuente / Documento` (another date, or another name the user chose), fix the link. If the user chose not to save it, remove that link and leave the field as it would be without `Prompts`.
- **Length:** do not check it; each project has its own limits and tests.
- **Content:** this header, in the language of the ADR template, then the request exactly as received, character by character: `$ARGUMENTS`. No summary, translation, reformatting, code fence or trimming, and none of the interview answers (those live in the ADR).
  ```markdown
  # Prompt de /spec: <feature>

  - **Fecha:** <YYYY-MM-DD>
  - **Tipo:** <feature | bug | paso nuevo (paso <n>)>
  - **Rama:** `<feature>`
  - **ADR:** [`<ADR path>`](<ADR path relative to the prompt file>)

  ---

  ```

### New feature or bug

1. **Update the base:** `git fetch origin <Base branch>`. If the fetch fails and the remote is GitHub, compare `gh api repos/<owner>/<repo>/branches/<Base branch> -q .commit.sha` with `git rev-parse <Base branch>`; if they differ, stop and ask the user to update it. If neither the fetch nor `gh api` can confirm it, stop and ask; do not assume it is up to date. With no `origin` at all, warn and use the local `<Base branch>`. Start from `origin/<Base branch>` only when the fetch worked; after the `gh api` check, or with no `origin`, start from the local `<Base branch>`, which is the one that was checked.
2. **Branch:** if `<feature>` already exists (local or remote), stop and ask. Otherwise `git switch --no-track -c <feature> <start point>` (the untracked ADR comes along). `--no-track` keeps `<feature>` from tracking `origin/<Base branch>` when the start point is that remote branch.
3. **Prompt file** (only with `Prompts`): write it now, on `<feature>`, following **Prompt file** above.
4. **Commit:** stage only the ADR and, if it was written, the prompt file. Message in English: `docs(<feature>): add ADR`.
5. **Push** `<feature>`.
6. **Main PR (GitHub only):** write the body with Write in a temporary directory and run `gh pr create --draft --base <Base branch> --head <feature> --title "[<feature>] <summary>" --body-file <file>`. The title goes on the command line: write `<summary>` without the literal name of an environment file (say "archivos de entorno"), because `block_env_access` reads the whole command. Body, in the ADR's language:
   ```markdown
   Documento de decisiones: [`<ADR path>`](<ADR path>)

   ## Pasos
   - [ ] **Paso 1:** <title> (CA-1, CA-2)
   - [ ] **Paso 2:** <title> (CA-3)
   ```
   If `gh` fails, report it and keep the branch and the commit.

### New step

1. Branch and freshness were checked in section 1; stay on `<feature>`.
2. **Prompt file** (only with `Prompts`): write it now, following **Prompt file** above.
3. Commit only the ADR and, if it was written, the prompt file: `docs(<feature>): add step <n> to ADR`, and push.
4. **Main PR (GitHub only):** `gh pr list --head <feature> --base <Base branch> --state open --json number,body`. Add the new steps as unchecked items to its checklist with `gh pr edit <number> --body-file <file>`, changing nothing else. If there is no main PR, warn and skip.

## 7. Report

Six lines at most: ADR path, prompt file path (or, without `Prompts`, the line `Prompt: no guardado (sin la clave opcional Prompts)` written literally, without translating or rewording it), branch, commit, main PR link (or why it was skipped), and "next: `/implement 1`" (or the new step's number).
