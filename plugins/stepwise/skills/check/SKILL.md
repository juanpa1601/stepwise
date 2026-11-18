---
name: check
description: Verifies the current step (<feature>-step-<n>) before review and close. Runs only the step's tests (the "Tests del paso" list /implement wrote; skipped and recorded as "sin tests del paso" when the list is "ninguno", or as none when "Tests (step)" is none) with stepwise:test-runner, never the full suite (that is /regression's), then the project's Migrations check, Lint/format and Type check; on failure analyzes the cause, fixes only what belongs to the step, reruns lint and type check on it and reruns the step's tests, with 3 attempts at most, and asks before touching a failure that likely already existed on <feature>. When everything passes, writes the "Pruebas" section of the step's traceability file with the step's fingerprint and the plugin alignment of the project's .claude/settings.json (a warning, never a failure). Does not commit.
disable-model-invocation: true
---

# /check

Verify the current step. Follow the sections in order. Talk to the user in their language. Write every file with the Write and Edit tools (shell edits are blocked by the `stepwise` hooks).

## 0. Preconditions (change nothing yet)

1. **Branch.** `git branch --show-current` must match `^(?P<feature>.+)-step-(?P<n>\d+)$`, taking the **last** `-step-` (`multi-step-form-step-2` is feature `multi-step-form`, step `2`). Otherwise stop and say so.
2. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `Tests (step)`, `Lint/format`, `Type check`, `Migrations check`, `Decision docs`, `Traceability`.
   <!-- shared:project-commands -->
   - If the section or a key is missing, change nothing. Reply with every missing key and the exact line to add, and stop:
     ```
     Missing: <"## Project commands" section | keys "<key>", ...> in CLAUDE.md
     Proposed lines:
     - <key>: <value>
     ```
     Use a value the project already documents (cite `path:line`); otherwise write `<value>`. Never edit `CLAUDE.md` without approval and never guess.
   <!-- /shared:project-commands -->
   - A value of `none` means that check does not apply: skip it and record it. In `Decision docs` and `Traceability`, replace `<feature>` and `<n>`; if `Traceability` ends with `/`, the file is `<dir>step-<n>.md`.
3. **Step scope.** Read step `<n>` and its CAs in the ADR, and list the step's changes: `git diff --name-only <feature>` plus untracked files (`git status --short`). This is what "belongs to the step" means below.
4. **Step tests list.** Read `## Pruebas` → `### Tests del paso` in the `Traceability` file (`/implement` writes it). Skip this item if `Tests (step)` is `none`.
   - **Missing** (a step implemented with an older version of the plugin): build the list from the step's changes (item 3), taking the files that are tests by the project's conventions (location, naming, framework). Show it and ask the user to confirm or correct it before running anything, then write it in that subsection (before `### Verificación manual`, if there is one), one per line as ``- `<path or id>` ``, or `ninguno`. This is the only write allowed in section 0: create the `Traceability` file, or its `## Pruebas` section, if it is missing.
   - **Present:** compare it with the step's changes. If a test file among them is not in the list, warn in one line and ask whether to add it; do not run anything until the user answers.

## 1. Run

1. <!-- shared:step-tests -->Run the step's tests: the list in `## Pruebas` → `### Tests del paso` of the `Traceability` file. With `Tests (step)` `none`, skip them and record `none`. If the list says `ninguno`, do not call `test-runner` and record `sin tests del paso`. Otherwise delegate to `stepwise:test-runner`: "step <every path or id of the list, separated by spaces>", never the full suite (only `/regression` runs it),<!-- /shared:step-tests --> <!-- shared:test-runner-foreground -->in the foreground (never `run_in_background`; wait for its report, the agent's own message with `Command:` and `Totals:` and not the notice that its task finished, without `sleep`, polling or other work meanwhile)<!-- /shared:test-runner-foreground -->. Do not run it in the main session.
2. Run `Migrations check` exactly as declared, from the project root, unless it is `none`.
3. Run `Lint/format`, then `Type check`, exactly as declared, from the project root, unless they are `none`. They run **always**, also when the step's tests ran and passed on the first try, or there were none. A failure of either one is a failure of the step, handled like a failing test (section 2). **No files to check:** if `Lint/format` exits 0 and its output has the exact line `no files to check` (the marker a project prints when its scoped command found no files), record it as `sin archivos que revisar`, not `ok`; it is not a failure and costs no attempt.
4. **Plugin alignment.** Run, from the project root (it only reads):
   ```bash
   python3 "<this skill's directory>/scripts/settings_alignment.py"
   ```
   It compares the project's `.claude/settings.json` with the plugin's `ask` rules and checks that `stepwise@stepwise` is enabled and that the `stepwise` marketplace reads `ref: main`. It prints at most 5 lines and exits with 0 (aligned; an `Extra (info):` line is information only), 1 (misaligned) or 2 (the file does not exist, is not valid JSON or has an invalid structure; the message goes to stderr). Keep its output for section 3.
   - **It is a warning, never a failure:** exit 1 or 2 does not fail the step, costs no attempt and is not rerun in section 2. **Never edit `.claude/settings.json`** to fix it: only report it.
   - If the script cannot run (for example `python3` is missing), record `no disponible (<error>)`.

If everything that ran passes (the plugin alignment of item 4 never counts as a failure), or nothing ran, go to section 3.

## 2. On failure

**3 attempts at most.** An attempt is one fix followed by a rerun of what failed (section 1: the step's tests, `Migrations check`, `Lint/format` or `Type check`; every one the fix could affect).

For each failure:
1. **Analyze the cause in the main session:** read the failing test and the code it exercises, by range. Do not delegate the analysis.
2. **Is it the step's?** It belongs to the step when the failing test, or the code it exercises, is in the step's changes, or a change of the step plausibly causes it.
   - If you suspect it **already failed on `<feature>`** (neither the test nor the code it exercises is in the step's changes, and nothing in the step explains it), **ask the user before touching it**: fix it in this step, or leave it and record it. Do not spend an attempt on it until they answer. If they choose to leave it, it is recorded as pre-existing and does not block the rest.
3. **Fix only what belongs to the step.** No unrelated refactors, no skipping or deleting tests, no weakening assertions, no editing the ADR's criteria to make a test pass. If the fix needs a design change or contradicts the ADR, stop and propose the change.
4. **Lint and types after the fix.** Run `Lint/format`, then `Type check`, exactly as declared, from the project root; skip each one that is `none`. Fix what they report in the step's files. If they changed files, keep only the changes to the step's files; list the other files they touched and ask the user before reverting them.
5. **Tests the fix touched.** If the fix creates or modifies a test, add its path or id to `### Tests del paso` (replacing `ninguno` if that was the list) before rerunning.
6. **Rerun.**

If it still fails after the third attempt, **stop**. Do not write the list of `## Pruebas` (section 3); the `### Tests del paso` subsection that sections 0.4 and 2 wrote stays as it is. Report the diagnosis in at most 10 lines: what fails (`file::test — file:line: error`), the cause you found, the 3 attempts and why each one did not work, and what you propose.

## 3. Traceability ("Pruebas")

When everything passes (or the only failures are pre-existing ones the user chose to leave), compute the step's **fingerprint**, after the last fix and the last run of `Lint/format` and `Type check` (a formatter may rewrite files), from the project root:

```bash
python3 "<this skill's directory>/../close/scripts/fingerprint.py" <feature> <Traceability file> <ADR file>
```

It prints `sha256:<hex>`: a hash of the diff against `<feature>` with the untracked files, without the traceability and the ADR. It only reads. If it fails, write `- **Huella:** no disponible (<error>)`; `/close` will then rerun everything.

**Code fingerprint, only if `## Project commands` declares `Docs paths`** (an optional key: git pathspecs of files no test, code lint or migration reads, for example `'*.md' 'docs/**'`). Run the same command with `--docs` and the value exactly as written appended:

```bash
python3 "<this skill's directory>/../close/scripts/fingerprint.py" <feature> <Traceability file> <ADR file> --docs <Docs paths>
```

It prints the fingerprint without those paths; the root `CLAUDE.md` always counts. Write it as `- **Huella de código:** sha256:<hex>` (or `no disponible (<error>)`). Without the key, or with `Docs paths: none`, do not run it and do not write the line.

Then write the `## Pruebas` section of the `Traceability` file. Create the file if it does not exist; if it exists, replace only the list of that section and keep the rest (for example `## Evidencia de regresión` and the `### Tests del paso` and `### Verificación manual` subsections, which stay below the list, unchanged except for what sections 0.4 and 2 added to `### Tests del paso`). **Do not commit.**

```markdown
## Pruebas
- **Tests del paso (`Tests (step)`):** `<command>`: <N> total, <N> failed, <N> errors, <N> skipped, en <time>. | sin tests del paso | `none`: el proyecto no tiene tests automáticos; se saltó.
- **Migrations check:** `<command>`: <result> | `none`.
- **Lint/format:** `<command>`: <result> | sin archivos que revisar | `none`.
- **Type check:** `<command>`: <result> | `none`.
- **Alineación del plugin:** ok | ok; Extra (info): <rules> | <resumen> | no disponible (<error>).
- **Intentos:** <0 to 3>.
- **Arreglos:**
  - `<path>`: <what was wrong and what changed> (<test that caught it>).
- **Fallos preexistentes que se dejaron:** <test — motivo, decisión del usuario> | ninguno.
- **Verificación manual:** <N> CA, <N> ok, <N> pendientes de confirmar por el usuario, <N> después del merge (ver abajo). | no aplica.
- **Huella de código:** sha256:<hex>   (only with `Docs paths`)
- **Huella:** sha256:<hex>
```

The `Alineación del plugin` line comes from section 1.4: `ok` on exit 0 (with `; Extra (info): <rules>` when the script printed that line); on exit 1, `<resumen>` is the script's lines after `desalineado`, joined with `; ` (for example `Faltan: Bash(gh pr merge:*); Plugin: no habilitado`); on exit 2, the script's error line.

The `Huella` line goes last, right after `Huella de código` when there is one. `/close` compares them with new fingerprints to decide whether to rerun anything.

The `Verificación manual` line appears only when `/implement` wrote that subsection (`Tests (step): none`, or CAs the ADR marks `(manual: <reason>)`); count its entries as they are, without running them again. If one is pending, say so in the report: `/close` does not merge a step with an unconfirmed manual verification unless the user says so. One marked `después del merge` does not block the merge: `/close` adds it to the main PR checklist.

Write `ninguno` where there is nothing. The command and totals come from the `test-runner` report, as run, so `/close` does not rerun or rebuild them.

## 4. Report

At most 5 lines: the totals, the migrations check, the attempts and fixes, the traceability path, and "next: `/close`" (it runs `/audit self`). When the alignment script exited with 1 or 2, or could not run (`no disponible`), add `Alineación del plugin: <resumen>` to the migrations check line, as a warning that does not block the step. Not for `ok`, with or without `Extra (info)`.
