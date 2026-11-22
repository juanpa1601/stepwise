# Several features in parallel with `git worktree`

A guide for carrying two or more features at once with the `stepwise` plugin: one worktree per feature and one Claude Code session in each. It works for any project that uses the plugin. Whatever is specific to this repo goes in **In this repo** boxes, and whatever hasn't been tested yet carries the **unverified** mark (full list at the end).

Decisions and criteria: [ADR `release-2.1.0`](decisions/release-2.1.0/business-rules.md).

## Why it is needed
Each skill works on the current branch of the folder where the session was opened:
- `/implement` requires being on `<feature>` with a clean tree ([implement/SKILL.md:30-31](../plugins/stepwise/skills/implement/SKILL.md));
- `/check` and `/close` require a `<feature>-step-<n>` branch, and `/close` ends with `git switch <feature>` ([close/SKILL.md:86](../plugins/stepwise/skills/close/SKILL.md));
- `/regression` requires being on `<feature>`, with every step merged ([regression/SKILL.md](../plugins/stepwise/skills/regression/SKILL.md), section 0);
- all of them read the `CLAUDE.md` of the session's folder, and `run_tests.py` runs the tests from there ([run_tests.py:627](../plugins/stepwise/scripts/run_tests.py)).

A working copy carries only one feature at a time. Switching branches in the middle of a step drags the uncommitted changes along or clashes with the clean tree.

## 1. What a worktree is
A worktree is **another working copy on the same `.git`**, not a clone: nothing is downloaded and commits exist only once.

| Shared between worktrees | Specific to each worktree |
|---|---|
| Commits, branches and tags | `HEAD` (the branch or commit checked out) |
| Remotes and what `git fetch` brings | The index (what is staged) |
| The configuration (`.git/config`) and git hooks | The files in the folder |
| The stash: `git stash list` shows everyone's | Ignored files: environment files, `.venv`, `.claude/settings.local.json` |

**A branch can only be active in one worktree.** Git rejects `git switch <branch>` if another worktree has it checked out (`fatal: '<branch>' is already used by worktree at ...`). In practice:
- `<feature>` and its `<feature>-step-<n>` branches live only in their worktree. Don't check them out in the main copy: `/close` runs `git switch <feature>` and would fail.
- The main copy can stay on `<Base branch>`. `/spec` doesn't need it checked out: it starts from `origin/<Base branch>` (next section).
- Careful with `git stash pop`: there is a single stash for everyone.

## 2. Step by step
**With the skill:** from a session in the main copy, `/stepwise:worktree new <folder>` does the steps of this section and of section 3: it validates the folder, creates the worktree, creates the `.venv` if needed, gives you the command to copy the environment files and moves the session into the worktree with `EnterWorktree` ([skill](../plugins/stepwise/skills/worktree/SKILL.md)). What follows is the same thing, by hand.

From the main copy, in Git Bash:

```bash
git fetch origin <Base branch>
git worktree add --detach ../<folder> origin/<Base branch>
```

- **`--detach`:** the worktree starts with a detached HEAD, without a branch. `/spec` creates the branch.
- **`../<folder>`, outside the repo.** For example `../myapp-reports`, next to the main copy. Don't use `.claude/worktrees/` or any other folder inside the repo:
  - the worktree shows up as an untracked file in the main copy (if `.gitignore` doesn't ignore it) and breaks the clean tree `/implement` requires;
  - a session opened there would also load the parent folder's `CLAUDE.md`, if Claude Code reads them upward from the session's folder (**unverified**).
- **A different folder name for each worktree.** Docker Compose takes the project name from it (section 4).

Then:
1. Copy the files that start out empty (section 3).
2. Open a Claude Code session in `../<folder>`: a terminal with `cd ../<folder> && claude`, or a new VS Code window with that folder.
3. Run `/spec <description>`. Once approved, `/spec` creates `<feature>` with `git switch --no-track -c <feature> origin/<Base branch>` ([spec/SKILL.md:109](../plugins/stepwise/skills/spec/SKILL.md)). The starting point is explicit, so it doesn't matter that HEAD is detached. Verified: in a `--detach` worktree, `/spec` investigated, interviewed and reached the approval summary without stopping, and once approved it created `<feature>` from `origin/<Base branch>`, without upstream.
4. Continue the workflow in that same session: `/implement <n>` → `/check` → `/close` (which runs `/audit self`) for each step, and at the end `/regression` on `<feature>`. `/regression` runs the full suite and is the only thing that takes the main PR out of draft ([regression/SKILL.md:84](../plugins/stepwise/skills/regression/SKILL.md)). If another feature reached `<Base branch>` first, integrate before `/regression` (section 6). The full cycle, from `/spec` to the merge, has been done inside a worktree.

For a feature that already exists on the remote (if `<feature>` isn't checked out in another worktree):

```bash
git fetch origin <feature>
git worktree add ../<folder> <feature>
```

Without `--detach`. If the local `<feature>` branch already existed, bring it up to date inside the worktree with `git pull origin <feature>`: `/implement` stops if it is behind ([implement/SKILL.md:32](../plugins/stepwise/skills/implement/SKILL.md)).

## 3. What starts out empty
A worktree brings only the versioned files. The ignored ones don't come along:

- **Environment files** (`.env`, `.env.docker` and the like). You copy them from the main copy: the `block_env_access` hook denies Claude reading them, writing them and even naming them in a command ([block_env_access.py:40-79](../plugins/stepwise/hooks/block_env_access.py)). Don't try to get around it. Without them, Compose fails when reading the `env_file`.
- **The host `.venv`**, if the project's `Lint/format` uses it (for example `.venv/bin/python` or `.venv/Scripts/python`). Create one in the worktree with the same dependencies as the main copy's. Without it, `/check` and `/close` fail at the lint.
- **`.claude/settings.local.json`.** The permissions you approved with "Always allow" in the main copy aren't there: the worktree session asks for them again. `.claude/settings.json` does come along, because it is versioned.

> **In this repo:** the plugin is installed in `local` scope, and that installation lives in `.claude/settings.local.json` ([README.md:90-91](../README.md#developing-stepwise)), which doesn't reach the worktree. Open the session with the worktree's own checkout:
> ```bash
> claude --plugin-dir "<absolute path to the worktree>/plugins/stepwise"
> ```
> That way the session uses the skills from that feature's branch, not those of another copy. What the `local` installation does inside a worktree is **unverified**.

In a project with the plugin in `user` scope (the normal case), the plugin is already available in any folder and there is nothing to do.

## 4. Docker and tests in parallel
Compose isolates by **project name**. Without `-p` or `COMPOSE_PROJECT_NAME`, the name comes from the compose file's folder, and it only allows lowercase letters, digits, `-` and `_` ([Compose documentation](https://docs.docker.com/compose/how-tos/project-name/)). When it takes it from the folder, Compose normalizes it (lowercase, without the other characters), so `api.v2` and `apiv2` would give the same project (**unverified**: the documentation gives the rule, not the normalization). Two worktrees with different folders are two projects: their own containers, networks and volumes, and the services find each other by name inside their network.

**Rules to avoid breaking it:**
1. **Different folder names**, also when they are in different parents and after normalizing them: `a/api` and `b/api` are the same project `api`.
2. **No top-level `name:`** in the test compose file: it fixes the project name and merges both worktrees into one.
3. **The test compose file at the root.** Without `-p`, Compose takes the project name from the folder of the first `-f` file, so `-f ci/compose.yml` gives the project `ci` in every worktree. `/stepwise:worktree new` reports it in `Proyecto fijo:`.
4. **No `container_name`:** two containers can't have the same name.
5. **No `ports`:** a host port can only be published by one. Tests don't need it; they talk over the project's network.
6. **No fixed `name:` or `external: true`** in the networks and volumes of the test compose file: those are shared between projects.
7. **No `COMPOSE_PROJECT_NAME`** in the `.env` of the compose folder (the one Compose reads to interpolate variables) or in an `--env-file`: it would do the same as `name:`. In an `env_file:` file it doesn't matter, because it only goes into the container.

**What clashes anyway:**
- The app and E2E compose files that publish the same port (`<port>:<port>`): only one at a time on the whole machine, regardless of the worktree.
- **The BuildKit cache is shared:** the second build reuses the layers of the first (good), but the two `--build`s compete for CPU and disk, and a `docker builder prune` in one worktree empties everyone's cache.

**A typical case:** a test compose file used by `Tests (step)`, `Tests (full)` and `Migrations check`, without `name:`, `container_name`, `ports`, fixed networks or external volumes, runs in parallel. The app and E2E compose files of the same project, which publish the same host port, don't. A database image that declares a volume gets an anonymous volume per project: it survives between runs (`run --rm` doesn't take down the `depends_on`) and `down -v` removes it. Every environment file those compose files read is copied to each worktree.

**Verified:** `Tests (full)` running at the same time in two worktrees of the same project. During the run, `docker ps` showed two complete projects (`<folder-a>-test-run-<id>`, `<folder-a>-<service>-1` and the same with `<folder-b>`), and `docker network ls`, two networks (`<folder-a>_default` and `<folder-b>_default`). There was no name or port clash, and both suites passed. A port that `docker ps` may show on the `test-run` containers is the image's `EXPOSE`, not a port published on the host.

## 5. Performance of `/check`, `/close` and `/regression`
Since `stepwise` 2.0.0, the full suite runs only once per feature:

| Skill | What it runs | Limit |
|---|---|---|
| `/check` and `/close` | Only the step's tests (`### Tests del paso` in the traceability), with `Tests (step)` | 570 s of `run_tests.py` ([run_tests.py:41](../plugins/stepwise/scripts/run_tests.py)) |
| `/regression` | `Tests (full)` on `<feature>`, with every step merged, in the background from the main session | 3600 s (`run_tests.py full --timeout 3600`, [regression/SKILL.md:42](../plugins/stepwise/skills/regression/SKILL.md)) |

- **Two suites at once** compete for CPU, RAM and disk, and each one takes longer than alone: two `/regression`s, or a `/regression` and a `/check` with many tests. If `Tests (step)` rebuilds the image (`--build`), each step run pays for the build too.
- **When a limit expires**, `run_tests.py` kills the process tree, reports `timeout after <N> s` and exits with 124. The notice comes out in the `Totals:` line; when the command chains several with `&&`, it comes out in the row of the part that expired or in the `Note:` line. It doesn't clean up containers. In `/regression`, the timeout falls back to the manual run: the skill gives you the `Tests (full)` command to run by hand and paste the totals.
- **Measured:** with a single-process pytest suite, each run in parallel took somewhat longer than the same run alone. Both fit in the 3600 s of `/regression`, and none of them, not even the solo one, would have fit in the 570 s of `test-runner`. Why the time of the same suite varies between runs (the machine, Docker's memory, the build) is **unverified**.
- **After a timeout**, or after any `docker compose run`, the `depends_on` services stay up (verified). Also, the timeout kills the `docker compose run` client and whatever that client started on the host ([run_tests.py:473-494](../plugins/stepwise/scripts/run_tests.py)). It probably doesn't kill the container: the `test` container (`<project>-test-run-<id>`) would keep running the tests, competing with the other suite, until it finishes (**unverified** with the timeout; see section 9). What was observed was a parallel run whose two clients exited with code 1 because their output went to a pipe that was closed. Afterwards, `docker ps` still showed both `test-run` containers up, and one of them finished on its own, with code 0. Check with `docker ps` and take everything down with the cleanup in section 7 before repeating.
- **To avoid stepping on each other:** run `/regression` in one worktree while the other is in `/spec`, `/implement` or review.

**Levers to speed it up** (recommendations only; each project decides them in its own feature):
- **`pytest-xdist`** (`-n auto`): spreads the tests across processes. With `pytest-django`, each process uses its own test database, so it is worth measuring first with a large `Tests (step)`.
- **Less output:** options such as `--verbose`, `-s`, `--capture=no`, `log_cli = true`, `showlocals = true` or `--durations=10` in `pytest.ini`. Less output is less work for pytest and for `run_tests.py`, which reads all of it.
- **Don't repeat what `Migrations check` checks:** if the `command` of the test service runs `makemigrations --check --dry-run` before the tests, `Tests (full)` repeats in `/regression` what `Migrations check` already checked in each `/check`.

## 6. Integration
Two features that touch the same files clash when the second one is merged. It is resolved on the `<feature>` of the feature that arrives second.

**When:** after its last `/close` (already on `<feature>`, without a step branch open) and before `/regression`. Steps, in Git Bash:

```bash
git fetch origin <Base branch>
git merge --no-ff --no-commit origin/<Base branch>
# resolve the conflicts, if any
git add <resolved files>
# run Tests (full) from CLAUDE.md; if they fail, fix, git add and repeat
git commit
git push origin <feature>
```

`--no-commit` also stops a conflict-free merge before the commit, and `--no-ff` ensures there is a merge to stop. That way `Tests (full)` always runs before the merge commit. Never `rebase` or `--force` (the plugin's git rules).

- **How to combine the two features is the user's decision,** not Claude's, and it is recorded as a rule in the ADR of the feature that integrates.
- **That way `/regression` tests what goes into `<Base branch>`:** after merging the main PR, `<Base branch>` is the commit `/regression` tested plus only its `regression.md` (verified).
- **A merge that is clean for git can be wrong.** For example: one feature changes the default of a function, and the other adds, in another file, a new call that counts on the old default. Git merges everything without a conflict, and only the tests of the second feature, run on the merged code, show that the new call is now wrong. That's why `Tests (full)` is run after integrating and before the merge commit.
- **Risk: the conflict that is only behavioral.** If there is no text conflict, GitHub lets the second feature be merged without integrating. Its two `/regression` runs pass, each on its own branch, and `<Base branch>` ends up broken. Until the plugin checks it, the rule is that before `/regression` this must hold:

  ```bash
  git fetch origin <Base branch>
  git merge-base --is-ancestor origin/<Base branch> <feature> && echo integrada
  ```

  If it doesn't print `integrada` (integrated), integrate first. Repeat the check right before merging the main PR: if `<Base branch>` moved since `/regression`, integrate and run `/regression` again. An option on GitHub: the "Require branches to be up to date before merging" protection on `<Base branch>`. In a private repo it isn't in the free plan: GitHub answers 403 (`Upgrade to GitHub Pro or make this repository public to enable this feature`).
- **Why not a "stage" branch between the features and `<Base branch>`?** The conflict moves, it doesn't disappear. It would be resolved outside the feature's PR and ADR, and after its `/regression`. A "stage" only makes sense as pre-production after `<Base branch>`, and that is not the topic of this guide.
- **A feature that depends on another doesn't go in parallel:** wait for the first one to reach `<Base branch>` and create the worktree afterwards.

> **In this repo:** almost every feature that changes `plugins/stepwise/` touches the same three places:
> - `version` in `plugins/stepwise/.claude-plugin/plugin.json`;
> - its literal in `tests/test_plugin_version.py` (`assertEqual(version, "<version>")`, [`:257`](../tests/test_plugin_version.py));
> - `## [Unreleased]` in [CHANGELOG.md](../CHANGELOG.md).
>
> If the first feature already bumped the `version` on `main` and it hasn't been released yet, the second one keeps that version (unless it needs a higher level) and only adds its line to the CHANGELOG. The rule is in [Versioning](../plugins/stepwise/README.md#versioning).

## 7. Cleanup
**With the skill:** from a session in the main copy, `/stepwise:worktree remove <folder>` checks that the feature's main PR is merged and does the steps below. It stops if the worktree has a detached HEAD, if its folder no longer exists (it gives you `git worktree prune`), if `git status --short` of the worktree shows anything (before taking anything down) or if a `down` fails. It takes the test compose down with `-p <folder>` (normalized the way Compose does it), so neither a `name:` in the file nor `COMPOSE_PROJECT_NAME` takes it to another project. It refuses if that name already belongs to another worktree or to the main copy, to a `-p` or a `--project-directory` in the commands, to a `name:` or to the folder of a compose file outside the root, or if it doesn't know which project a compose file fixes (it can't read it, or its `name:` has a `$` variable). It also stops if a container of that project has a `working_dir` outside the worktree: Docker labels apply to the whole machine, and another repo may use the same name. In those cases the project is shared and the worktree is removed by hand with `git worktree remove` and `git worktree prune`, without taking the compose down. It never uses `down -v`, which would also delete a volume with its own `name:`, shared by every copy. It removes one-off containers with `docker rm -f -v`, runs `rm -s -v -f` (containers and their anonymous volumes) and `down --rmi local`, and then shows you the volumes Docker labeled with that project (`com.docker.compose.project`) whose name starts with `<project>_`. It only deletes them if you say yes.

By hand: once the main PR is merged, from the worktree folder and before deleting it:

```bash
docker compose -f <test compose file> down -v --rmi local
```

`-v` removes the project's volumes and `--rmi local` the images it built without their own `image:`.

> **With a volume with its own `name:`** (or external) in the test compose file, don't use `down -v`: it deletes that volume, which is the same for every copy. First remove the one-off containers (those from a `run` without `--rm`, which `rm` doesn't touch) with `docker rm -f -v $(docker ps -aq --filter label=com.docker.compose.project=<project> --filter label=com.docker.compose.oneoff=True)`. Then use `docker compose -f <test compose file> rm -s -v -f` (containers and their anonymous volumes) and `docker compose -f <test compose file> down --rmi local`, and delete by hand only the `<project>_*` volumes from `docker volume ls`.

Then, from the main copy:

```bash
git worktree remove ../<folder>
git worktree prune
```

- `git worktree remove` refuses if there are uncommitted changes or untracked files (`fatal: '<path>' contains modified or untracked files, use --force to delete it`). Don't use `--force`: first look at what was left with `git -C <path> status --short`. Ignored files (environment files, `.venv`) don't block it and are deleted with the folder. Both things were verified.
- `git worktree prune` cleans up the record of a worktree whose folder no longer exists.
- **The branch isn't deleted:** the plugin's git rules forbid deleting branches, local or remote.

## 8. Quick checklist
1. `/stepwise:worktree new <folder>` (or, by hand, `git fetch origin <Base branch>` and `git worktree add --detach ../<folder> origin/<Base branch>`), with a new folder name.
2. Copy the environment files (the skill gives you the command) and create the `.venv` if `Lint/format` uses it (the skill creates it).
3. Open the session in `../<folder>` (in this repo, with `--plugin-dir`).
4. `/spec`, `/implement <n>` → `/check` → `/close` for each step, and `/regression` at the end, all in that session.
5. Before `/regression`: if another feature reached `<Base branch>` first, integrate it (section 6) and check `git merge-base --is-ancestor origin/<Base branch> <feature>`. Repeat it right before merging the main PR.
6. Only one `/regression` at a time, and nothing that publishes the same host port in parallel.
7. When you finish: `/stepwise:worktree remove <folder>`. By hand (section 7): `docker compose ... down -v --rmi local` or, with a volume with its own `name:`, the `docker rm -f -v` of the one-offs, `rm -s -v -f`, `down --rmi local` and `docker volume rm` of the `<project>_*` ones; then `git worktree remove` and `git worktree prune`.

### Common problems
| Symptom | Cause | What to do |
|---|---|---|
| `fatal: '<branch>' is already used by worktree at '<path>'` (before git 2.42: `is already checked out at ...`) | The branch is checked out in another worktree | `git worktree list`; work in that worktree or switch the other copy to `<Base branch>` |
| Compose fails with `env file <path>\.env.docker not found` | The environment file wasn't copied, or it ended up with another name or in another folder (one possible cause, unverified: Windows Explorer adds `.txt`) | Copy it yourself from Git Bash: `cp <main copy>/.env.docker ../<folder>/` |
| `/check` fails at the lint with `.venv/...: No such file` | The worktree has no `.venv` | Create it in the worktree (section 3) |
| The `stepwise` skills don't show up (in this repo) | The `local` installation didn't reach the worktree | Open the session with `--plugin-dir` |
| `timeout after 570 s` in `/check` or `/close` | The step's tests, with another suite alongside or already at the limit on their own | Check `docker ps`, take the services down (section 7) and repeat when the other worktree finishes |
| `timeout after 3600 s` in `/regression` | The full suite, with another one alongside or already at the limit on its own | Check `docker ps`, take the services down and follow `/regression`'s manual fallback |
| `Bind for 0.0.0.0:<port> failed: port is already allocated` | The app or E2E is already running in another folder | Take that one down with `docker compose down` |
| `/implement` stops because of untracked files in the main copy | A worktree inside the repo | Move it out: `git worktree move <path> ../<folder>` |

## 9. Unverified
- **The parent folder's `CLAUDE.md`:** whether a session opened in a worktree inside the repo loads it too.
- **The normalization of the Compose project name** (`api.v2` and `apiv2`).
- **Why a suite's time varies between runs** of the same tests: the machine, Docker's memory or the build.
- **The `test` container with the `run_tests.py` timeout:** it was observed surviving when the client exits because of a closed pipe, not with the timeout itself.
- **Claude Code's memory per path:** it isn't known whether a session in the worktree shares the main copy's automatic memory or starts with an empty one. What was seen: the worktree session's history ended up in its own folder under `~/.claude/projects/`, not in the main copy's, and a `memory/` folder appeared only under the main copy's path. It is a hint that the automatic memory is one per repo and shared between worktrees, but it isn't fully verified.
- **The plugin's `local` scope in a worktree** (in this repo): what a session opened there loads without `--plugin-dir`.
