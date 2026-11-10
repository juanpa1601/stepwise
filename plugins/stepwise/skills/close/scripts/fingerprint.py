"""Fingerprint of a step: a sha256 of its diff against ``<feature>`` (ADR, CA-G2).

Usage, from the project root::

    python3 <path to this script> <feature> [<excluded path> ...] [--docs <pathspec> ...]

Hashes ``git diff --binary <feature>`` (the working tree against ``<feature>``: committed, staged and unstaged
changes) without the excluded paths, plus the path and the content of every untracked file that git does not
ignore, in order (a symlink counts by its target, a nested repository by its name; names are bytes, not decoded). The step's traceability file and its ADR are passed as excluded paths, so editing them does not
change the fingerprint. Prints ``sha256:<hex>``. Read-only: it never touches the index or the working tree.

``--docs`` takes the git pathspecs of ``Docs paths`` (plain ones, without magic
such as ``:(glob)`` or ``:!``, for example ``'*.md' 'docs/**'``) and prints the **code fingerprint** instead: the same hash without those paths, tracked or untracked.
The root ``CLAUDE.md`` always counts, because it holds the project's contract (``## Project commands``).

Standard library only (Python 3.10 or later).
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def git(
    root: Path,
    *args: str
) -> bytes:
    """Run git in ``root`` and return its stdout; raise ``RuntimeError`` with git's message on failure."""
    completed: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603 - fixed program
        ["git", "-c", "core.quotepath=off", *args],
        cwd=root,
        capture_output=True,
        check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode(errors="replace").strip() or f"git {args[0]} failed")
    return completed.stdout


CONTRACT: str = "CLAUDE.md"


def fingerprint(
    root: Path,
    feature: str,
    excluded: list[str],
    docs: list[str] | None = None
) -> str:
    """Return ``sha256:<hex>`` of the diff of ``root`` against ``feature``, without ``excluded``.

    With ``docs`` (git pathspecs), return the code fingerprint: also without those paths, except the root
    ``CLAUDE.md``, which is hashed apart so it always counts.
    """
    git(root, "rev-parse", "--verify", "--quiet", f"{feature}^{{commit}}")
    normalized: set[str] = {Path(path).as_posix() for path in excluded}
    pathspec: list[str] = ["--", ".", *(f":(exclude,literal){path}" for path in sorted(normalized))]
    docs_pathspec: list[str] = [f":(exclude){spec}" for spec in docs or []]
    diff: list[str] = ["diff", "--binary", "--no-ext-diff", "--no-textconv", feature]
    digest = hashlib.sha256()
    digest.update(git(root, *diff, *pathspec, *docs_pathspec))
    if docs:
        digest.update(b"\0contract\0" + git(root, *diff, "--", f":(literal){CONTRACT}"))
    excluded_names: set[bytes] = {os.fsencode(path) for path in normalized}
    others: list[str] = ["ls-files", "--others", "--exclude-standard", "-z"]
    names: set[bytes] = split_names(git(root, *others, *(["--", ".", *docs_pathspec] if docs else [])))
    if docs:
        names |= split_names(git(root, *others, "--", f":(literal){CONTRACT}"))
    untracked: list[bytes] = sorted(name for name in names if name not in excluded_names)
    for name in untracked:
        digest.update(b"\0untracked\0" + name + b"\0")
        digest.update(entry_bytes(root / os.fsdecode(name.rstrip(b"/"))))
    return f"sha256:{digest.hexdigest()}"


def split_names(listed: bytes) -> set[bytes]:
    """Return the non-empty names of a ``git ls-files -z`` output."""
    return {name for name in listed.split(b"\0") if name}


def entry_bytes(path: Path) -> bytes:
    """Return what identifies an untracked entry: a link's target, a regular file's content, or a type marker.

    A nested repository shows up as ``dir/`` and is not read: its own history is not part of the step.
    """
    if path.is_symlink():
        return b"symlink\0" + os.fsencode(os.readlink(path))
    if path.is_file():
        return path.read_bytes()
    return b"directory\0" if path.is_dir() else b"other\0"


def main(argv: list[str]) -> int:
    """Print the fingerprint for ``argv`` (``<feature> [<excluded> ...] [--docs <pathspec> ...]``); return the code."""
    usage: str = "Usage: fingerprint.py <feature> [<excluded path> ...] [--docs <pathspec> ...]"
    if not argv or argv[0] == "--docs":
        print(usage, file=sys.stderr)
        return 2
    docs: list[str] | None = None
    if "--docs" in argv:
        split: int = argv.index("--docs")
        argv, docs = argv[:split], argv[split + 1:]
        if not docs:
            print(f"{usage}\n--docs needs at least one pathspec", file=sys.stderr)
            return 2
        magic: list[str] = [spec for spec in docs if spec.startswith(":")]
        if magic:
            print(
                f"--docs takes plain pathspecs ('*.md', 'docs/**'), without magic: {' '.join(magic)}",
                file=sys.stderr
            )
            return 2
    try:
        root: Path = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
        print(fingerprint(root, argv[0], argv[1:], docs))
    except (RuntimeError, OSError) as error:
        print(f"fingerprint: cannot compute it against '{argv[0]}': {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
