---
name: worktree
description: Creates or removes a git worktree for one feature, next to the main copy. "new <folder>" checks the folder with worktree_check.py, runs git fetch origin <Base branch> and git worktree add --detach ../<folder> origin/<Base branch>, creates the .venv from the main copy's pip freeze when Lint/format uses one, gives the user the command to copy the environment files (never runs it) and enters the worktree with EnterWorktree path. "remove <folder>" requires the feature's main PR merged, takes down the tests compose from the worktree folder with -p <the worktree's own Compose project>, docker rm -f -v of its one-off containers, rm -s -v -f and down --rmi local (never down -v), then, after the user says yes, removes only the volumes Docker labels with that project and whose name starts with <project>_ (stopping when a container of that project has another working_dir, and refusing a project name that another worktree or the main copy, a -p, a --project-directory, a name: or the folder of a compose file not at the root already uses, or a compose file it cannot read or whose name: has a $ variable), then runs git worktree remove and git worktree prune from the main copy, without deleting the branch or using --force.
argument-hint: new <folder> | remove <folder>
disable-model-invocation: true
---

# /worktree

Create or remove a worktree for one feature, as [the worktrees guide](https://github.com/juanpa1601/stepwise/blob/main/docs/worktrees.md) explains by hand. The request is `$ARGUMENTS`. Follow the sections in order. Talk to the user in their language.

**Environment files are the user's.** The `block_env_access` hook denies any command that names one, and this skill never reads, copies or names them in a command of its own: it only prints the copy command for the user to run (section 1.5).

## 0. Preconditions (change nothing yet)

1. **Request.** `$ARGUMENTS` must be `new <folder>` or `remove <folder>`, with one folder name and nothing else. Otherwise ask for it and stop.
2. **Project commands.** Read `CLAUDE.md` at the project root (the session directory), only the `## Project commands` section. Keys needed: `Base branch`, `Tests (step)`, `Tests (full)`, `Lint/format`, `Migrations check`.
   <!-- shared:project-commands -->
   - If the section or a key is missing, change nothing. Reply with every missing key and the exact line to add, and stop:
     ```
     Missing: <"## Project commands" section | keys "<key>", ...> in CLAUDE.md
     Proposed lines:
     - <key>: <value>
     ```
     Use a value the project already documents (cite `path:line`); otherwise write `<value>`. Never edit `CLAUDE.md` without approval and never guess.
   <!-- /shared:project-commands -->
3. **Git rules.** <!-- shared:git-rules -->Never `--squash`, `--rebase`, `--delete-branch`, `--force` or `push --force`, and never delete branches, local or remote. If the project's `CLAUDE.md` says something different about merges, rebases or branch deletion, stop and ask which rule applies.<!-- /shared:git-rules --> Never `git worktree remove --force`, and never `ExitWorktree` with `remove`.
4. **From the main copy.** Both modes run from the root of the main copy: `EnterWorktree` only enters a worktree outside `.claude/worktrees/` from there, and `git worktree remove` cannot remove the folder the session is in. The script (below) refuses anywhere else. For `remove` from inside the worktree it removes, see section 2.1.
5. **Remote.** `git remote get-url origin`. It is GitHub if the URL contains `github.com` (take `<owner>/<repo>` from it). With no `origin`, stop: `new` needs `git fetch origin` and `remove` cannot confirm the merge.

**The script** (it only reads, never writes a file and never opens an environment file), from the project root:

```bash
python3 "<this skill's directory>/scripts/worktree_check.py" <new | remove> <folder>
```

Exit 0 prints `ok` and the lines each section uses. Exit 1 (`error: <reason>` on stderr) means the folder cannot be used: show the reason and stop, changing nothing. Exit 2 is bad usage, a missing `## Project commands` or a git failure: show it and stop.

## 1. `new <folder>`

1. **Check.** Run the script with `new <folder>`. Keep its lines: `Carpeta:` (the absolute path of `../<folder>`), `Proyecto:`, `venv:`, `compose:`, `Proyecto fijo:` and `Entorno:`.
2. **Update the base.** `git fetch origin <Base branch>`. If it fails, stop: nothing was created.
3. **Create.** `git worktree add --detach "<Carpeta>" "origin/<Base branch>"`. HEAD stays detached: `/spec` creates `<feature>` there. If it fails, report it and stop.
4. **`.venv`**, only with `venv: yes (<python>)`, where `<python>` is the main copy's (for example `.venv/Scripts/python.exe`):
   1. `"<python>" -m venv "<Carpeta>/.venv"`, which uses the same interpreter as the main copy's `.venv`.
   2. `"<python>" -m pip freeze --exclude-editable`. Drop each line that points to a local path (` @ file:`, `-e`, a path instead of a version) and list them in the report: they would install from the main copy. Write the remaining lines with Write to a requirements file in a temporary directory outside the repo (the session's scratchpad if there is one).
   3. `"<Carpeta>/<python>" -m pip install -r "<that file>"`, with `run_in_background` (an install can pass the 600 s of a foreground call), and wait for its notice without `sleep` or polling.
   - With `venv: yes (aviso: la copia principal no tiene .venv)`, create nothing and say that `Lint/format` will fail in the worktree until the user creates one.
   - If a command fails, report it with the command to run by hand and go on: the worktree is created and usable.
5. **Environment files.** With `Entorno: <files>`, give the user one block to run in their own terminal (Git Bash), from the main copy, with one line per file (the path without the ` (sin ignorar)` mark); add `mkdir -p "<Carpeta>/<dir>" && ` before the `cp` when the file is in a subfolder:
   ```bash
   cp "<file>" "<Carpeta>/<file>"
   ```
   Do not run it, and do not check afterwards whether the files arrived. With `Entorno: ninguno`, say there is nothing to copy.
   - **`(sin ignorar)`:** git does not ignore that file. Once copied, it is an untracked file in the worktree, and `git worktree remove` refuses to remove it (section 2.4) until the user deletes it. Say so, and suggest adding it to the `.gitignore`.
6. **Enter.** Load `EnterWorktree` if it is deferred, and call it with `path` set to `<Carpeta>`. From here on, the session works in the worktree.
   - If it fails or does not exist, report the error and give the user `cd "<Carpeta>" && claude`. In a project with the plugin installed in `local` scope, the session needs `--plugin-dir` (the guide, section 3).
7. **Report**, at most 7 lines: the worktree and its commit (`git -C "<Carpeta>" rev-parse --short HEAD`), the `.venv` (created, skipped and why, or failed), the dropped `pip freeze` lines, the copy command still to run (or "nothing to copy") and the `(sin ignorar)` warning, whether the session entered, and "next: `/spec <description>`". When `Proyecto fijo:` is not `ninguno` (a `-p` or `--project-directory` in the commands, a top-level `name:` in a compose file, or the folder of a compose file not at the root, from which Compose takes the project name), warn that every worktree shares one Compose project, so their tests do not run in parallel (the guide, section 4). When `Entorno:` is not `ninguno`, add one fixed line, without opening any file: if a copied environment file defines `COMPOSE_PROJECT_NAME`, every worktree shares one project too.

## 2. `remove <folder>`

1. **Session inside that worktree.** If `git rev-parse --show-toplevel` is `../<folder>`: when this session entered it with `EnterWorktree`, call `ExitWorktree` with `action: "keep"` and go on from the main copy. Otherwise stop and ask the user to run `/stepwise:worktree remove <folder>` from a session in the main copy.
2. **Check.** Run the script with `remove <folder>`. Keep `Carpeta:`, `Rama:`, `Feature:`, `Proyecto:` and `Llamadas compose:`. Exit 1 stops here, for example:
   - a detached HEAD (no feature, so no main PR);
   - with a compose, a folder name that normalizes to no Compose project name: take the compose down by hand (the guide, section 7);
   - a registered worktree whose folder no longer exists: give the user `git worktree prune`;
   - with a compose, a `Proyecto:` that belongs to someone else (another worktree or the main copy, a `-p` or `--project-directory` of the commands, a top-level `name:`, or the folder of a compose file not at the root), or a compose whose project the script cannot know (a file it cannot read, or a `name:` with a `$` variable). That project is not only this worktree's, so it must not be taken down: tell the user so, and point to the guide, section 7, to remove the worktree by hand with `git worktree remove` and `git worktree prune`, without taking the compose down.
3. **Main PR merged.** On GitHub: `gh pr list --head <Feature> --base <Base branch> --state merged --json number,url`. A non-empty list means merged. Without GitHub: `git fetch origin <Base branch>` and `git merge-base --is-ancestor <Feature> origin/<Base branch>`. If it is not merged, or neither check can confirm it (for example `gh` fails), stop: nothing is taken down or removed.
4. **Nothing left to lose.** `git -C "<Carpeta>" status --short`. If it shows anything (modified or untracked files), show it and stop before taking anything down: `git worktree remove` would refuse afterwards, with the test volumes already gone. Never `--force`. Ignored files (environment files, `.venv`) do not show and go with the folder.
5. **Tests compose.** For each call of `Llamadas compose:` (separated by `;`; `<files>` is that call's `-f` options, together, so an override goes down with its base), from the worktree folder, always with `-p "<Proyecto>"`. Without it, Compose takes the project name from `COMPOSE_PROJECT_NAME` (which can come from a copied environment file), from a top-level `name:` in the file, or from the folder of the first `-f` file, and any of them can be a project the worktrees share with the main copy.
   1. **Whose the project is**, once, before any call. Docker labels are host-wide, so another repo, or a `COMPOSE_PROJECT_NAME`, may use the same project name:
      ```bash
      docker ps -a --filter "label=com.docker.compose.project=<Proyecto>" --format '{{.ID}} {{.Label "com.docker.compose.project.working_dir"}}'
      ```
      If any container's `working_dir` is not `<Carpeta>` or a folder inside it (compare without case and with `\` as `/` on Windows), stop before taking anything down: the project name is also someone else's. Point to the guide, section 7, to remove the worktree by hand without taking the compose down. With no output, the worktree's project has no containers (its tests never ran, or ran under a shared project name): say so in the report, not "taken down".
   2. **One-off containers**, once: `rm` leaves out the containers of a `run` without `--rm`, and `down` without `-v` would leave their anonymous volumes behind. With the IDs of `docker ps -a -q --filter "label=com.docker.compose.project=<Proyecto>" --filter "label=com.docker.compose.oneoff=True"` (all checked in item 1), run `docker rm -f -v <those>`; with none, skip it.
   3. **Take it down, never with `down -v`**, for each call:
      ```bash
      (cd "<Carpeta>" && docker compose -p "<Proyecto>" <files> rm -s -v -f)
      (cd "<Carpeta>" && docker compose -p "<Proyecto>" <files> down --rmi local)
      ```
      `rm -s -v -f` stops and removes the project's service containers with their anonymous volumes; `down --rmi local` removes its networks and the images it built without an `image:` of their own. `down -v` would also remove a volume with its own `name:`, which every worktree and the main copy share, and the script does not read the compose files to know: the volumes to remove come from Docker's labels (item 4).
   4. **The project's own volumes**, once, after every call:
      ```bash
      docker volume ls -q --filter "label=com.docker.compose.project=<Proyecto>"
      ```
      Keep only the names that start with `<Proyecto>_` (Compose prefixes a volume without its own `name:` with the project). Leave every other name (a volume with its own `name:` that this project created first, which others may use). **Show both lists and ask the user before removing** (`AskUserQuestion` when it exists; otherwise ask in plain text and end the turn), with this fixed line: Docker labels are host-wide, so if another repo uses the project `<Proyecto>` and its containers are gone, these volumes may be its own. Then, only with a yes, `docker volume rm <the prefixed ones>`; without it, leave them and give the user that command. If `docker volume rm` refuses one (in use), report it and go on.
   - Never use `docker compose config` to find volumes: it prints the services' environment, filled from the environment files.
   - With `Llamadas compose: none`, skip this item and say so. If a command fails, report it and stop before removing the worktree.
6. **Remove**, from the main copy:
   1. `git worktree remove "<Carpeta>"`. If git still refuses because of modified or untracked files, run `git -C "<Carpeta>" status --short`, show it and stop: never `--force`. If the folder is in use (another session or an editor open there), ask the user to close it and stop.
   2. `git worktree prune`.
7. **Check.** `git worktree list` no longer shows `<Carpeta>`, and the branch `<Rama>` is still there (`git branch --list <Rama>`). The remote branch is not touched.
8. **Report**, at most 5 lines: the PR that was merged, each compose taken down (or skipped, and why), the volumes removed and the ones left, the worktree removed and pruned, the branch kept, and what stopped, if anything.
