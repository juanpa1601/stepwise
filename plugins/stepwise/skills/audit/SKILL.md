---
name: audit
description: Reviews code in three modes. "self" reviews the current step's local diff with stepwise:code-reviewer against the ADR, fixes blockers, asks once about suggestions and questions, re-reviews only the fixes and writes the "Code review" section of the step's traceability (run by /close, or by hand). "comments [<num>]" fetches the unresolved review comments of a PR (by default the feature's main PR), verifies each one against the real code, classifies it and, with approval, turns the valid ones into a new ADR step or a new feature. "pr <num>" reviews someone else's PR and drafts inline comments. Never posts on GitHub without explicit approval.
argument-hint: self | comments [<pr number>] | pr <pr number>
disable-model-invocation: true
---

# /audit

Run the mode in `$ARGUMENTS`: `self`, `comments [<num>]` or `pr <num>`. With anything else, list the three modes and stop. Talk to the user in their language. Write every file with the Write and Edit tools (shell edits are blocked by the `stepwise` hooks).

**Never publish on GitHub without explicit approval** of the exact text: no `gh pr comment`, `gh pr review`, `gh pr edit`, `gh api` with a method other than GET (except the read-only `gh api graphql` queries below, which are POST but do not write) or any GraphQL `mutation` (thread resolution) until the user says yes to what you showed.

**Never put a body on the command line** (no `-f body=`, `--body`, `--field body`): quotes, backticks, `$(...)`, line breaks or accents break it or run in the shell. Write the JSON (`{"body": "<text>"}`, or the review JSON) with the Write tool in a temporary directory **outside the repo** (the session's scratchpad if there is one) and send it with `gh api -X POST <endpoint> --input <file>`, or pass a text file with `--body-file <file>`.

## 0. Common preconditions (change nothing yet)

1. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `self` needs `Tests (step)`, `Lint/format`, `Type check`, `Decision docs`, `Traceability`; `comments` needs `Base branch` only without `<num>`, and `Decision docs` to find comments already handled (section 2.2) and to write an ADR step (check them when you get there; reading and classifying needs none; without `Decision docs`, skip the "already handled" search, say so and propose the line); `pr` needs `Decision docs`.
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
2. **Branch name.** A step branch matches `^(?P<feature>.+)-step-(?P<n>\d+)$`, taking the **last** `-step-`: `multi-step-form-step-2` is feature `multi-step-form`, step `2`. A name that contains `-step-` without a trailing number (`multi-step-form`) is a feature branch, not an error.
3. **GitHub** (`comments` and `pr`). `git remote get-url origin` must contain `github.com` and `gh auth status` must be logged in. Take `<owner>/<repo>` from `gh repo view --json nameWithOwner -q .nameWithOwner`. Otherwise stop and say so.

## 1. `self`: the step's diff before closing

1. **Branch.** It must be a step branch (section 0.2). Otherwise stop and say so. The ADR is `Decision docs` for `<feature>`; it must exist.
2. **Review.** Delegate to `stepwise:code-reviewer` with: the ADR path, step `<n>`, and the diff range "local `git diff <feature>...HEAD` plus uncommitted changes (`git diff HEAD`, and untracked files from `git status --short`)".
3. **One round with the user**, only if there are suggestions or questions. Ask in a single round, before fixing anything:
   - **suggestions:** one multiple-choice question, "which do we fix now?", listing each one (`R<n>: <problem>`). Unchosen ones are debt.
   - **questions:** asked as they are.
   - Use `AskUserQuestion` when it exists (`multiSelect: true` for suggestions; 4 options per question at most, so split them into several questions of the same call). Without it (for example in `claude -p`), ask in plain text as a numbered list and **end the turn**; continue when the answers arrive.
   - If an answer changes the ADR, update it with Edit in this step.
4. **Fix** in the main session, without asking, every `blocker`, plus the suggestions the user chose. Fix only what the finding says. If a fix needs a design change or contradicts the ADR, stop and propose the ADR change: never merge a step with an open blocker.
   - **Apply every fix before the second pass**, including text in the ADR or the traceability: nothing is completed after it.
   - **Totals in `## Pruebas` or `## Evidencia de regresión` that a fix made stale** (for example a test was added) are not edited by hand: rerun what produced them (`test-runner`) and replace them with that output. When `/close` runs this mode, the full-suite totals are rewritten by its section 2; say so in the finding's result.
5. **Tests of the fixes.** If the fixes changed code or tests, run `stepwise:test-runner step <paths of the touched tests>` (always with paths), <!-- shared:test-runner-foreground -->in the foreground (never `run_in_background`; wait for its report, the agent's own message with `Command:` and `Totals:` and not the notice that its task finished, without `sleep`, polling or other work meanwhile)<!-- /shared:test-runner-foreground --> until green, then `Lint/format` and `Type check` exactly as declared (skip `none`), keeping only changes to the step's files. **If `Tests (step)` is `none`**, skip `test-runner`; lint and type check still run. **Manual CAs**, whatever the fixes changed (code, tests, documentation or configuration): for each manual CA the fixes touched (every CA with `Tests (step): none`, or one the ADR marks `(manual: <reason>)`), run again its manual verification (`## Pruebas` → `### Verificación manual`) and update its `Obtenido`, or mark it `pendiente` for the user.
6. **Second pass, once.** Delegate to `stepwise:code-reviewer` again with the same input plus "re-review only these fixes: `<id>: <what changed, path:line>`". There is no third pass.
   - Every fix `fixed`: go on.
   - A fix wrong or incomplete, or a **new `blocker`**: stop and ask the user what to do. Do not fix or complete it without review, and do not go on to `/close`'s next section until the user answers.
   - A new suggestion: record it as debt; do not fix it (no unreviewed fixes).
7. **Traceability.** Write the `## Code review` section of the `Traceability` file: create the file if it does not exist; if it exists, keep the rest (`## Evidencia de regresión`, `## Pruebas`). **Do not commit.**
   - **No `## Code review` yet:** write it with the format below.
   - **`## Code review` already exists** (for example `/close` ran again after a failure): **do not replace it.** Keep every earlier round as it is and append the new one at the end of the section, under `### Ronda <k> (<YYYY-MM-DD>)`, with the same format minus the `## Code review` heading. `<k>` is the number of rounds already there plus one; a section without `### Ronda` headings counts as round 1.
   ```markdown
   ## Code review
   `stepwise:code-reviewer` sobre el diff local del paso: **<N> bloqueantes, <N> sugerencias y <N> preguntas.** <who chose what>.

   | id | Tipo | Hallazgo | Resultado |
   |---|---|---|---|
   | R1 | blocker | <problem> | Arreglado sin preguntar: <what changed> |
   | R2 | suggestion | <problem> | Arreglado | Deuda (elección del usuario) |
   | R3 | question | <question> | <answer, and the ADR change if any> |

   - **Pasada sobre los arreglos:** <ids> `fixed` | <what it found and what the user decided>.
   - **Deuda:** <ids with their reason> | ninguna.
   - **Huella:** sha256:<hex>
   ```
   With no findings: `` `stepwise:code-reviewer` sobre el diff local del paso: sin hallazgos. ``, no table, and the `Huella` line.
   - **`Huella` of the round:** the fingerprint of the **final** diff, after every fix and the second pass, computed from the project root with `python3 "<this skill's directory>/../close/scripts/fingerprint.py" <feature> <Traceability file> <ADR file>` (it only reads and prints `sha256:<hex>`). Every round records it; if the script fails, write `- **Huella:** no disponible (<error>)`. `/close` skips a new review when the last round has the current fingerprint and no open `blocker`.
8. **Report** (at most 6 lines): the counts, what was fixed, the debt, the traceability path and one line **`Code changed by fixes: yes | no`** ("yes" when a fix touched anything other than the ADR or the traceability), and the round's `Huella`. `/close` decides whether to rerun the suite by comparing fingerprints, not by that line.

## 2. `comments [<num>]`: review comments on a PR

1. **PR.** `<num>` if given. Otherwise the feature's main PR: take `<feature>` from the current branch (section 0.2; a branch that is not a step branch is the feature itself) and run `gh pr list --head <feature> --base <Base branch> --state all --json number,state,url`. With several results, take the open one; if none or several are open, ask. If there is none, stop and ask for the number.
   **`<feature>` is always the PR's:** read `gh pr view <num> --json state,url,headRefName,baseRefName` and take `<feature>` from `headRefName` (section 0.2), never from the current branch. Its ADR is `Decision docs` for that `<feature>`.
2. **Fetch with `gh`** (`--paginate`; GET, plus the read-only GraphQL query):
   - inline comments: `gh api repos/<owner>/<repo>/pulls/<num>/comments`;
   - reviews: `gh api repos/<owner>/<repo>/pulls/<num>/reviews` (state and body);
   - general comments: `gh api repos/<owner>/<repo>/issues/<num>/comments`;
   - thread state and author, with a read-only query (no `mutation`):
     ```bash
     gh api graphql --paginate -F owner=<owner> -F name=<repo> -F number=<num> -f query='
       query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
         repository(owner: $owner, name: $name) { pullRequest(number: $number) { state url
           reviewThreads(first: 100, after: $endCursor) { pageInfo { hasNextPage endCursor }
             nodes { id isResolved isOutdated path line
               comments(first: 50) { nodes { databaseId author { login } body url } } } } } } }'
     ```

   **Ignore resolved threads.** Also skip review bodies that only summarize the PR (for example Copilot's "Pull request overview"), empty bodies, and your own or the PR author's replies; say how many you skipped. Keep `isOutdated` threads, marked as such.

   **Already handled:** a comment may be cited in this feature's ADR (an earlier "Atender review" step) or in the ADR of another feature (a `/spec` made after the PR was merged). For each comment, search **every** ADR under `Decision docs` (replace `<feature>` with `*`, e.g. `docs/decisions/*/business-rules.md`) with Grep for the anchor of its URL, which also matches the full URL, ending in a word boundary so `discussion_r1001` does not match `discussion_r10012`: `discussion_r<databaseId>\b` (inline), `issuecomment-<id>\b` (general) or `pullrequestreview-<id>\b` (review).
   - **In one ADR, under the `CA-n` of one step:** it is `atendido`; do not classify it again. Take `<feature>` from that ADR's folder and the step `<n>` whose `CA-n` cites it. Find the commit of its fix: the merge of `<feature>-step-<n>` into `<feature>` (`gh pr list --head <feature>-step-<n> --state merged --json mergeCommit`, or `git log --merges --first-parent <feature>`). If it is merged, take the reply drafted under that CA, put the commit link in it and offer it for publication (section 2.7). If it is not merged yet, list it as pending (feature and step) and go on.
   - **In several ADRs, or in the `CA-n` of several steps of one ADR** (for example a redone "Atender review"): ask the user which feature and step handle it, and which drafted reply to offer; do not guess.
   - **In none:** classify it (sections 2.3 and 2.4).
3. **Verify each comment against the real code.** Do not assume it is correct: a premise (Copilot's or a human's) can be false. For each one, check its claim in the code as it is now (on the PR's head branch, or `<feature>` if you are on it): read the cited `path:line` yourself when it is one place, or launch `stepwise:explore` agents in parallel, one per comment, with the claim to verify. Every verdict cites `path:line`.
4. **Classify:**
   - `válido`: the claim holds and needs a fix;
   - `no aplica`: the claim is false, already handled, or out of the feature's scope; the reason is the reply;
   - `requiere decisión`: it holds, but fixing it is a product or design choice; ask the user.
5. **Show a table and ask for approval** (the user can change any classification):

   | id | Autor | Dónde | Comentario | Verificación | Clase | Acción / respuesta propuesta |
   |---|---|---|---|---|---|---|
   | C1 | `<login>` | `<path>:<line>` | <one line> | <what the code shows, path:line> | válido | <fix> |

   Ask the `requiere decisión` ones in the same round (section 1.3 rules). End the turn and wait.
6. **With the approval:**
   - **Draft the replies first** (section 2.7), so they go into the ADR before its commit.
   - **PR open:** add a new step "Atender review" to the ADR, as `/spec` adds a new step: you must be on `<feature>` with a clean tree and up to date (`git fetch`, or `gh api repos/<owner>/<repo>/branches/<feature> -q .commit.sha` if the fetch fails; if you cannot confirm it, stop and ask). Append one `CA-n` per `válido` comment in Given/When/Then, continuing the numbering; under each, the comment URL and its drafted reply (`Respuesta: Arreglado en <commit link>.`). Touch nothing already done. Commit only the ADR (`docs(<feature>): add step <n> to ADR`), push it (same HTTPS fallback as `/close`), and add the step as an unchecked item to the main PR checklist (`gh pr edit <num> --body-file <file>`, changing nothing else). Then tell the user to go on with `/implement <n>`.
   - **PR merged:** do not touch that ADR. Propose the `/spec` line for a new feature with those fixes, ready to copy: `/spec <summary>: C1 <url>, C2 <url>…`, and ask `/spec` to put each comment URL and its drafted reply under its `CA-n`, so a later run finds them as `atendido`.
7. **Replies.** Draft one reply per comment and show them: `no aplica` with the reason; `válido` with "Arreglado en <commit link>" pending the commit. Publish only with explicit approval of the exact text:
   - `válido`: only after the fix is merged into the PR's branch, with the link to the commit (`https://github.com/<owner>/<repo>/commit/<sha>`). Until then, the drafts stay in the ADR under each CA, and a later run of this mode finds them as `atendido` (section 2.2) and offers them.
   - Write each body as JSON with Write outside the repo (see the rule at the top) and publish with `--input`. Which id each endpoint takes:

     | To | Command | Id |
     |---|---|---|
     | Reply in an inline thread | `gh api -X POST repos/<owner>/<repo>/pulls/<num>/comments/<databaseId>/replies --input <file>` | `databaseId` (REST id) of the thread's **root** comment: the first node of `comments` in the GraphQL query (2.2); the same as `id` in `pulls/<num>/comments`. Never the thread's `id` |
     | Answer a general comment or a review body | `gh api -X POST repos/<owner>/<repo>/issues/<num>/comments --input <file>` | the PR number (GitHub has no replies there); quote or link the comment's URL in the text |
     | Resolve a thread | `gh api graphql -F threadId=<id> -f query='mutation($threadId: ID!) { resolveReviewThread(input: {threadId: $threadId}) { thread { isResolved } } }'` | the thread's GraphQL `id` (`PRRT_…`) from the query in 2.2 |

     The file holds only `{"body": "<text>"}`, with the text escaped as JSON (`\"`, `\\`, `\n`).
   - Resolve the thread only with the same approval.
8. **Report** (at most 6 lines): PR, counts by class, skipped comments, what was written (ADR step or `/spec` line) and what is still unpublished.

## 3. `pr <num>`: someone else's PR

**The local checkout is not the PR** (it may be another branch, or the PR may be merged since). In this mode, the only local file you read is `CLAUDE.md` at the project root, for `## Project commands`. Every other file of the repository, also to confirm something on the base branch, is read from GitHub as plain text: `gh api "repos/<owner>/<repo>/contents/<path>?ref=<headRefOid or base branch>" -H "Accept: application/vnd.github.raw"`. To find files, list the tree: `gh api "repos/<owner>/<repo>/git/trees/<headRefOid>?recursive=1" -q '.tree[].path'`. Never Read, Grep or Glob on the project directory, and never `git grep`, `git show` or `git log` on it, for this mode. Files you saved outside the repo (the ADR) are read with Read.

1. **Read the PR:** `gh pr view <num> --json number,title,author,state,url,baseRefName,headRefName,headRefOid,body,files`.
2. **ADR.** Take `<feature>` from `headRefName` (section 0.2) and look for `Decision docs` for it among the PR's files or at its head, as plain text: `gh api "repos/<owner>/<repo>/contents/<path>?ref=<headRefOid>" -H "Accept: application/vnd.github.raw"` (without that header the content comes in base64). If it exists, save its text with Write in a temporary directory outside the repo and pass that path; otherwise pass `none` and say so. Never `git fetch` or `git checkout` the PR.
3. **Review.** Delegate to `stepwise:code-reviewer` with: the ADR path (or `none`), scope `PR`, the diff `gh pr diff <num>`, `<owner>/<repo>`, `headRefOid`, and the `Tests (step)` and `Traceability` values from the local `CLAUDE.md` (the same source as this session, so both use the same values). To check a finding yourself afterwards, follow the rule above (GitHub only, never the checkout).
4. **Draft** in the user's language (or the PR's, if different, ask which):
   - one inline comment per finding, anchored to a line the diff adds or changes (`path`, `line`, `side: RIGHT`): what is wrong and the proposed fix; a finding on a line outside the diff goes into the summary;
   - a summary: counts, blockers first, and what was reviewed.
5. **Show the draft and ask for the verdict:** `COMMENT`, `REQUEST_CHANGES` or `APPROVE`. **The user chooses it; never pick it yourself**, not even as a default. GitHub rejects `REQUEST_CHANGES` and `APPROVE` on your own PR: say so if the PR is the user's.
6. **Publish only with explicit approval** of the draft and the verdict: write the review JSON (`{"commit_id": "<headRefOid>", "event": "<verdict>", "body": "<summary>", "comments": [{"path", "line", "side", "body"}]}`) with Write in a temporary directory outside the repo and run `gh api -X POST repos/<owner>/<repo>/pulls/<num>/reviews --input <file>`. Always with `--input`, never with `-f`/`-F` fields (the rule at the top).
7. **Report:** the review link, or "draft not published".
