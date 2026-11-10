---
name: implement
description: >-
  Implements step <n> of the current feature's ADR on a new branch <feature>-step-<n>. For each acceptance criterion of the step it writes the test first (for a bug, it records that the regression test fails before the fix), then the code, and runs the step's tests with stepwise:test-runner until green; with "Tests (step) none", or for a criterion the ADR marks "(manual: <reason>)", it records a manual verification for that criterion instead. Then runs lint and type check. Stops and proposes an ADR change when the step is incomplete or wrong. Does not commit.
argument-hint: <step number>
disable-model-invocation: true
---

# /implement

Implement step `$ARGUMENTS` of the feature's ADR. Follow the sections in order. Talk to the user in their language. Write every file with the Write and Edit tools (shell edits are blocked by the `stepwise` hooks).

**Stop rule:** when a check fails, stop before changing anything and say what failed and what you propose. Do not improvise around it.

## 0. Preconditions (change nothing yet)

1. **Step number.** `$ARGUMENTS` must be a positive integer `<n>`. Otherwise ask for it and stop.
2. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `Tests (step)`, `Lint/format`, `Type check`, `Base branch`, `Decision docs`, `Traceability`.
   <!-- shared:project-commands -->
   - If the section or a key is missing, change nothing. Reply with every missing key and the exact line to add, and stop:
     ```
     Missing: <"## Project commands" section | keys "<key>", ...> in CLAUDE.md
     Proposed lines:
     - <key>: <value>
     ```
     Use a value the project already documents (cite `path:line`); otherwise write `<value>`. Never edit `CLAUDE.md` without approval and never guess.
   <!-- /shared:project-commands -->
   - A value of `none` means that check does not apply. In `Decision docs` and `Traceability`, replace `<feature>` and `<n>`; if `Traceability` ends with `/`, the file is `<dir>step-<n>.md`.
   - **`Tests (step): none`** (a project without automated tests): tell the user now, in one line, that the step will have no automated test and each CA gets a manual verification instead, and go on. Sections 3 and 4 say what changes.
3. **Branch.** `git branch --show-current` is `<feature>`: not `Base branch`, and not a step branch. A step branch matches `^(?P<feature>.+)-step-(?P<n>\d+)$`, taking the **last** `-step-` (`multi-step-form-step-2` is feature `multi-step-form`, step `2`); a feature name that contains `-step-` without a trailing number (`multi-step-form`) is valid. The ADR (`Decision docs` for `<feature>`) exists. Otherwise stop.
4. **Clean tree.** `git status --short` is empty. Otherwise stop and ask.
5. **Up to date.** `git fetch origin <feature>` and compare with `origin/<feature>`. If the fetch fails (for example SSH `Permission denied (publickey)`) and the remote is GitHub, compare `gh api repos/<owner>/<repo>/branches/<feature> -q .commit.sha` with `git rev-parse <feature>`. If the local branch is behind, stop and ask the user to update it. If the remote has no `<feature>` or there is no remote, warn and continue. If the remote has it but neither the fetch nor `gh api` can confirm it, stop and ask.
6. **Step exists.** The ADR's list of steps has step `<n>`. Otherwise stop.
7. **Previous step merged** (only if `<n>` > 1). `<feature>-step-<n-1>` (local or `origin/`) must be an ancestor of `<feature>`: `git merge-base --is-ancestor <that branch> <feature>`. If neither branch exists and the remote is GitHub, accept a merged Sub-PR: `gh pr list --head <feature>-step-<n-1> --base <feature> --state merged`. If you cannot confirm it, stop.
8. **Branch is free.** `<feature>-step-<n>` does not exist, local or remote. Otherwise stop and ask.

## 1. Read the step and check the ADR

1. Read the ADR in full: step `<n>`, its CAs, the business rules, the out of scope and the open decisions.
2. Read `CLAUDE.md` and the `README.md` of the folders the step touches. Use `stepwise:explore` only for what you cannot locate yourself.
3. **Check that the step can be implemented as written.** Stop and propose the exact ADR change (the lines to add or replace) if:
   - the step lists no CA, or lists a CA that does not exist;
   - a CA lacks Given, When or Then, or its result cannot be checked with a test and the CA is not marked `(manual: <reason>)` (propose the mark, with its reason, as the ADR change);
   - a CA is marked `(manual)` without a reason;
   - implementing it needs a decision the ADR leaves open or does not take (a behavior, a rule, a permission, an edge case);
   - the step contradicts a business rule, the out of scope, or the code as it is.

   Do not edit the ADR without approval. If approved, apply it with Edit: it goes in this step's commit.

## 2. Branch

`git switch -c <feature>-step-<n>`.

## 3. Bug: regression evidence before any fix

Only if the ADR type is `bug`, and before touching any code:
1. **Write the tests of every CA of the step** not marked `(manual: <reason>)` first. Follow the project's test conventions (location, naming, framework).
2. **Run them once**, before any fix, with `stepwise:test-runner step <test paths or ids>`, <!-- shared:test-runner-foreground -->in the foreground (never `run_in_background`; wait for its report, the agent's own message with `Command:` and `Totals:` and not the notice that its task finished, without `sleep`, polling or other work meanwhile)<!-- /shared:test-runner-foreground -->.
   - **Only the regression CA** (the one the ADR marks as regression, usually `CA-1`) must **fail**, for the reason in the CA. If it passes, stop: the test does not reproduce the bug.
   - The other CAs may already pass before the fix (for example a case that never broke): that is not a stop. Record which ones passed.
   - **Regression CA marked `(manual: <reason>)`:** no test has to fail; its manual reproduction (below) replaces the failure line of item 3. If the step has no test left, skip items 2 and 3.
3. **Save the evidence** in the `Traceability` file, under `## Evidencia de regresión` (create the file if it does not exist; keep any other section): the command, the totals, the failure line of the regression CA and `Pasaban antes del arreglo: CA-<n>, ... | ninguno`.

**With `Tests (step): none`, or when the ADR marks the regression CA `(manual: <reason>)`**, a manual reproduction replaces its failing test:
1. Before touching any code, write the reproduction of the regression CA under `## Evidencia de regresión`: steps, expected result, and the result obtained **before** the fix, which must show the bug. Run it yourself when you can (a command, a request, reading the output); if it needs the user (a browser, a device, credentials), write the steps, ask the user to run them and wait for the result. If it does not show the bug, stop: the reproduction is wrong.
2. After the fix (section 4), run it again and add the result **after** the fix, which must pass, with who ran it (`Claude` or `usuario`).

## 4. For each CA of the step

1. **Test first:** write or adjust the test that checks the CA (for a bug, it already exists from section 3). Follow the project's test conventions.
2. **Implement** the code for that CA.
3. **Run** `stepwise:test-runner step <paths of the step's tests>` (always with paths), <!-- shared:test-runner-foreground -->in the foreground (never `run_in_background`; wait for its report, the agent's own message with `Command:` and `Totals:` and not the notice that its task finished, without `sleep`, polling or other work meanwhile)<!-- /shared:test-runner-foreground -->. Fix and rerun until green. If it keeps failing for a reason outside the step, stop and report it.

**With `Tests (step): none`, or for a CA the ADR marks `(manual: <reason>)`**, a manual verification replaces items 1 and 3 for that CA. In a project with tests, a CA without the mark still needs a test, and the other CAs of the step keep theirs.
1. **Implement** the code for the CA.
2. **Write the verification** in the `Traceability` file, under `## Pruebas` → `### Verificación manual` (create the file or the section if missing; keep any other section), one entry per CA:
   ```markdown
   - **CA-<n>:** <the CA in one line>
     - Pasos: <numbered steps someone else can repeat>
     - Esperado: <the Then of the CA>
     - Obtenido: <what happened> | pendiente de confirmar por el usuario | después del merge: <why it cannot run before>
     - Ejecutó: Claude | usuario | pendiente | después del merge
   ```
3. **Run it yourself** when you can. If it needs the user, leave `Obtenido: pendiente de confirmar por el usuario`, say so in the report and ask them to run it. If it needs a command only the user can type (a `/stepwise:` skill is user-only), `Pasos` gives that exact command with its arguments, and the report asks for it in one line. A failing verification is fixed like a red test.
4. **After the merge.** Only when the verification **cannot** run before the step is merged (it needs the merged branch, a deploy, or the step's own `/close`), mark it `Ejecutó: después del merge` and write the reason in `Obtenido`. `/close` does not block the merge on it: it adds it to the main PR checklist, and the last step's `/close` keeps the main PR in draft until it is confirmed. A `pendiente` one still blocks the merge.

## 5. Lint and type check

Run `Lint/format`, then `Type check`, exactly as declared, from the project root; skip each one that is `none`. **No files to check:** if `Lint/format` exits 0 and its output has the exact line `no files to check` (the marker a project prints when its command, scoped to some files, found none in the step), report it as `sin archivos que revisar`, not `ok`. It is not a failure. Fix what they report in the files of the step. If they changed files, keep only the changes to the step's files; list the other files they touched in the report and ask the user before reverting them.

## 6. Scope

Do only what step `<n>` asks: no refactors, renames, extra features or files the step does not need. If you find that the ADR has a gap or is wrong, stop and propose the change (section 1.3). Work outside the step goes to the report as a suggestion.

## 7. Report

**New session needed.** Claude Code loads agents, skills and commands when the session starts. If the step adds, deletes or changes any file under `.claude/agents/`, `.claude/skills/` or `.claude/commands/` (check `git status --short --untracked-files=all`, deletions included; without `--untracked-files=all`, a new `.claude/` folder shows up only as `?? .claude/`), add the `Session` line to the report: until the user opens a new session, the old ones stay loaded and can be confused with the plugin's (`stepwise:explore`, `stepwise:test-runner`). It does not stop the step. Without such a change, leave the line out.

**Do not commit.** At most 10 lines:
```
Step <n> of <feature> on <feature>-step-<n> (not committed).
Files: <path>, <path>, ...
CA-1: <test id> — green | manual — ok | manual — pending user | manual — after merge
CA-2: <test id> — green | manual — ok | manual — pending user | manual — after merge
Regression evidence: <Traceability file> (only for a bug)
No automated tests: manual verifications in <Traceability file> (only with Tests (step): none)
Pending user: CA-<n>: type `<exact command>` (or run <steps>) and tell me the result (only if one is pending)
Session: the step changed local agents, skills or commands (<paths>); open a new session before /check (only then)
Lint/format: <ok | sin archivos que revisar | none>. Type check: <ok | none>.
Next: /check
```
