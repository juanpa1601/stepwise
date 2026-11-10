---
name: close
description: Closes the current step (<feature>-step-<n>) after /check. Runs /audit self (code review, fixes, "Code review" section) unless its last round has the same fingerprint, reruns the full suite, migrations, lint and type check only if the step's fingerprint changed since /check (only lint and type check when just the project's "Docs paths" changed), completes the step's traceability from its own template keeping "Evidencia de regresión", "Pruebas" and "Code review", then commits, pushes, opens the Sub-PR into <feature>, merges it with --merge and ticks the step in the main PR checklist, adding the manual verifications marked "después del merge". On the ADR's last step it also writes the main PR description and asks before marking it ready, never while one of those verifications is unconfirmed unless the user says so. Stops and asks for /check if "Pruebas" is missing.
disable-model-invocation: true
---

# /close

Close the current step. Follow the sections in order. Talk to the user in their language. Write every file with the Write and Edit tools (shell edits are blocked by the `stepwise` hooks).

**Stop rule:** if a section fails and the fix is not obvious and local to the step, stop. Do not merge; leave the Sub-PR open if it exists, record the failure in the traceability file and report it.

## 0. Preconditions (change nothing yet)

1. **Branch.** `git branch --show-current` must match `^(?P<feature>.+)-step-(?P<n>\d+)$`, taking the **last** `-step-` (`multi-step-form-step-2` is feature `multi-step-form`, step `2`). Otherwise stop and say so.
2. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `Tests (step)`, `Tests (full)`, `Lint/format`, `Type check`, `Migrations check`, `Base branch`, `Decision docs`, `Traceability`.
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
3. **`/check` ran.** The `Traceability` file exists and has a `## Pruebas` section. Otherwise stop: "run `/check` first".
4. **Git rules.** Merges only with `gh pr merge <num> --merge`. <!-- shared:git-rules -->Never `--squash`, `--rebase`, `--delete-branch`, `--force` or `push --force`, and never delete branches, local or remote. If the project's `CLAUDE.md` says something different about merges, rebases or branch deletion, stop and ask which rule applies.<!-- /shared:git-rules -->
5. **Remote.** `git remote get-url origin`. It is GitHub if the URL contains `github.com` (take `<owner>/<repo>` from it). Otherwise warn now: the commit and push are done, but the Sub-PR, the merge and the main PR (sections 4.4 to 6) are skipped. That is not a failure. With no `origin`, the push is skipped too.

**Fingerprint.** Sections 1 and 2 compare the step's fingerprint, computed from the project root with the script in this skill's directory (it only reads):

```bash
python3 "<this skill's directory>/scripts/fingerprint.py" <feature> <Traceability file> <ADR file>
```

It prints `sha256:<hex>`: a hash of the diff against `<feature>` with the untracked files, without the traceability and the ADR. If it fails, treat every comparison as "changed" and say why.

**Code fingerprint**, only when `## Project commands` declares `Docs paths` (optional; not `none`): the same command with `--docs <Docs paths>` appended, the value exactly as written. It leaves those paths out, except the root `CLAUDE.md`.

## 1. `/audit self`

1. Compute the fingerprint. If `## Code review` exists, its **last round** (the last `### Ronda <k>`, or the whole section if it has none) records the same `Huella` and has no open `blocker`, **do not run `/audit self` again**: append to the end of `## Code review` the line `- **\`/close\` (<YYYY-MM-DD>):** no se repitió \`/audit self\`: misma huella que la ronda <k> (sha256:<first 12 hex>).` and go to section 2.
2. Otherwise (no section, no `Huella` in the last round, another fingerprint or an open `blocker`), read the `audit` skill next to this one (`../audit/SKILL.md` from this skill's directory) and run its section 1 (`self`) as written, including its round with the user and its stops. It records the fingerprint of the round. Then continue here.

## 2. Suite after changes

Whenever this section runs `Lint/format`, report it as `/check` does: if it exits 0 and its output has the exact line `no files to check`, the `## Pruebas` line says `sin archivos que revisar`, not `ok`.

1. Compute the fingerprint again and compare it with the `- **Huella:**` line of `## Pruebas`.
2. **Same:** do not rerun anything: `## Pruebas` stays as `/check` wrote it.
3. **Different, but only documentation changed:** `Docs paths` is declared, `## Pruebas` has a `- **Huella de código:**` line, and the code fingerprint computed now equals it. Do not rerun `Tests (full)` nor `Migrations check`; run `Lint/format` and `Type check` exactly as declared, from the project root (skip `none`).
   - **Green:** update `## Pruebas` with Edit: replace the `Lint/format` and `Type check` lines with the new run, replace the `Huella de código` and `Huella` lines with fingerprints computed again **after** these runs, and add a line `- **Corrida en \`/close\`:** solo cambiaron rutas de \`Docs paths\`; se corrieron \`Lint/format\` y \`Type check\`, no la suite ni \`Migrations check\`.` If a formatter rewrote a file outside `Docs paths`, the code fingerprint changes: go to item 4 instead.
   - **Failure:** stop (stop rule), as in item 4.
4. **Different, or `## Pruebas` has no `Huella`** (changes after `/check`, review fixes, or an older `/check`): before the commit, delegate to `stepwise:test-runner`: "full", **once**, <!-- shared:test-runner-foreground -->in the foreground (never `run_in_background`; wait for its report, the agent's own message with `Command:` and `Totals:` and not the notice that its task finished, without `sleep`, polling or other work meanwhile)<!-- /shared:test-runner-foreground --> (skip it if `Tests (full)` is `none`), and run `Migrations check`, `Lint/format` and `Type check` exactly as declared, from the project root (skip `none`).
   - **Green:** update `## Pruebas` with Edit: replace the totals and the `Migrations check`, `Lint/format` and `Type check` lines with the new run, replace the `Huella` line with a fingerprint computed again **after** these runs (a formatter in `Lint/format` may rewrite files; if it did, say which); with `Docs paths`, also write or replace `- **Huella de código:**` (computed again with `--docs <Docs paths>`) right before `Huella`, which stays last; and add a line `- **Corrida en \`/close\`:** la huella cambió (<reason: review fixes, changes after \`/check\`>).` Keep the rest of the section.
   - **Failure:** stop (stop rule). Do not commit; say to fix it and run `/check`, then `/close` again.

## 3. Traceability

1. Read `references/step-pr-template.md` (in this skill's directory) and complete the `Traceability` file with its structure: `{{FEATURE_NAME}}` and `{{FEATURE_BRANCH}}` are `<feature>`, `{{STEP_NUM}}` is `<n>`, `{{BASE_BRANCH}}` is `Base branch`, `{{DECISION_DOC}}` and `{{TRACEABILITY_FILE}}` the two paths, `{{DESCRIPCION_BREVE}}` a short summary.
2. **Keep `## Evidencia de regresión`, `## Pruebas` and `## Code review` exactly as they are**, in the template's order. Without regression evidence (not a bug), drop that section.
3. Fill the summary, the changes (`git diff --name-only <feature>` plus untracked files of the step) and the step's decisions. Tick the checklist items that hold; leave the others unticked and say why. Remove the template's HTML comments.
4. Check that the step matches its CAs and rules in the ADR. If it contradicts a rule, stop and ask.

## 4. Commit, push and Sub-PR

1. **Commit.** `git status --short`; stage only the step's files by path (never `git add -A`, `.env*`, secrets or `settings.local.json`). **One commit**, Conventional Commits in English (`feat(<scope>): ...`, `fix(...)`, `docs(...)`, `chore(...)`). Always write the message with Write in a temporary directory outside the repo (the session's scratchpad if there is one) and run `git commit -F <file>`, never `-m`, even if the text does not mention an environment file: `block_env_access` reads the whole command, so a message that names one would be denied.
2. **Push** without `-u`: `git push origin <feature>-step-<n>`. <!-- shared:push-https -->If SSH fails with `Permission denied (publickey)`, the remote is GitHub and `gh auth status` is logged in, retry once over HTTPS for that command only, without changing the remote or the global configuration:<!-- /shared:push-https -->
   ```bash
   git -c credential.helper= -c credential.helper='!gh auth git-credential' push https://github.com/<owner>/<repo>.git <feature>-step-<n>
   ```
   If the user denies a command that asks for approval (`git commit`, `git push`, `gh pr merge`), stop there and report what is left; it is not a failure of the step.
3. **Not GitHub:** stop after the push. Report what was skipped and finish.
4. Check that `gh api repos/<owner>/<repo>/branches/<feature>-step-<n> -q .commit.sha` equals `git rev-parse HEAD`.
5. **Sub-PR**, in Spanish: write the body with Write in a temporary directory outside the repo (the session's scratchpad if there is one) and run `gh pr create --base <feature> --head <feature>-step-<n> --title "[<feature>] Paso <n>: <resumen>" --body-file <file>`, always with `--body-file`, never `--body`. The title goes on the command line: write `<resumen>` without the literal name of an environment file (say "archivos de entorno"). Body: a link to the traceability file (`https://github.com/<owner>/<repo>/blob/<feature>-step-<n>/<path>`), the summary, the `## Pruebas` totals and the code review counts.
6. **Merge** only if the suite is green (or only pre-existing failures the user chose to leave, or `Tests (full)` is `none`), no `blocker` is open and no manual verification in `## Pruebas` is still `pendiente` (or the user said to merge anyway, recorded in the traceability): `gh pr merge <num> --merge`. A verification marked `después del merge` does not block the merge: it goes to the main PR checklist (section 5.2).

## 5. Main PR

1. `gh pr list --head <feature> --base <Base branch> --state open --json number,body,isDraft`. If there is none, warn and skip this section.
2. In its checklist (the `## Pasos` list `/spec` writes, or the Sub-PR list the PR already has), tick step `<n>` and add the Sub-PR number and the traceability link; if the step is not listed, add it as a ticked item. For each manual verification of this step marked `después del merge` (`## Pruebas` → `### Verificación manual`), add an unticked item right below the step: `- [ ] Verificación después del merge (paso <n>, CA-<k>): <pasos>`. If the user says one of them, from this or an earlier step, has been confirmed, tick it. Change nothing else. Write the body with Write in a temporary directory outside the repo (the session's scratchpad if there is one) and run `gh pr edit <num> --body-file <file>`.
3. **Last step of the ADR** (`<n>` is the highest step in its list of steps): write the main PR description from `references/main-pr-template.md` (same replacements; `{{DESCRIPCION_GENERAL}}` from the ADR's objective), keeping the checklist from step 2 as its `## Pasos`. Drop the section "Verificación de instalación desde `develop`" unless the PR's base is `main` **and** the repo publishes plugins (it has `.claude-plugin/marketplace.json` at its root); drop its checklist item too. In that case the section is required: fill it only with a verification that really ran, otherwise leave it with its placeholders and say the PR is not ready. Show it and **ask** before applying it with `gh pr edit <num> --body-file <file>` (written with Write in a temporary directory outside the repo (the session's scratchpad if there is one)): it replaces the whole body, including text people wrote. Then **ask** again before `gh pr ready <num>`. Without a yes, the body stays as it was and the PR stays in draft.
   - **Verifications after the merge:** read the PR body again (`gh pr view <num> --json body`). While any `- [ ] Verificación después del merge (...)` item is unticked, do not run `gh pr ready` and do not offer it: list the unticked items and say the PR stays in draft until they are confirmed (ticked on GitHub, or the user tells `/close` and it ticks them). Only if the user explicitly says to mark it ready anyway, do it and record that decision in the traceability.
4. Update the local feature branch: `git switch <feature>` and `git pull origin <feature>` (the same HTTPS fallback applies, with `pull`).

## 6. Report

At most 6 lines: the commit, the Sub-PR link and merge, the main PR checklist, the code review counts and debt (or "same fingerprint, not repeated"), the suite (reused from `/check` or rerun, and why), the verifications after the merge still unconfirmed, and what was skipped and why.
