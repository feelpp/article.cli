"""Portable paper provenance: read Git once and export a Typst JSON snapshot.

Git access is outside the document compiler. Archived documents retain the frozen
snapshot, while working repositories refresh it through article-cli. LaTeX keeps
its established gitinfo2 adapter in git_hooks.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .command_runner import DEFAULT_RUNNER, CommandRunner

TYPST_METADATA_FILE = "gitHeadLocal.json"
# Generated provenance must not make the next snapshot dirty by itself.
METADATA_EXCLUDES = (
    ":(exclude)gitHeadLocal.gin",
    ":(glob,exclude)**/gitHeadLocal.gin",
    ":(exclude)gitHeadLocal.json",
    ":(glob,exclude)**/gitHeadLocal.json",
)


@dataclass(frozen=True)
class GitSnapshot:
    """Format-neutral, deterministic paper version state (no build timestamp)."""

    commit: str = ""
    short_commit: str = ""
    branch: str = "unversioned"
    description: str = "unversioned"
    release: str = ""
    commit_date: str = ""
    dirty: bool = False
    schema_version: int = 1


def read_git_snapshot(
    start_path: Path, runner: CommandRunner = DEFAULT_RUNNER
) -> Optional[GitSnapshot]:
    """Read an existing commit; tracked source edits define the dirty flag."""

    def git(*args):
        try:
            result = runner.run(["git", *args], cwd=start_path)
            return result.stdout.strip() if result.returncode == 0 else None
        except (FileNotFoundError, OSError):
            return None

    fields = git("log", "-1", "--format=%H%n%h%n%cI", "HEAD")
    if not fields:
        return None
    values = fields.splitlines()
    if len(values) != 3:
        return None
    # Query at the Git root so changes in sibling documents are visible too.
    root = git("rev-parse", "--show-toplevel")
    if not root:
        return None
    result = runner.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            ".",
            *METADATA_EXCLUDES,
        ],
        cwd=Path(root),
    )
    if result.returncode:
        return None
    dirty = bool(result.stdout.strip())
    description = git("describe", "--tags", "--long", "--always") or values[1]
    release = git("describe", "--tags", "--abbrev=0") or ""
    return GitSnapshot(
        commit=values[0],
        short_commit=values[1],
        commit_date=values[2],
        branch=git("symbolic-ref", "--quiet", "--short", "HEAD") or "detached",
        description=description + ("-*" if dirty else ""),
        release=release,
        dirty=dirty,
    )


def write_typst_snapshot(snapshot: GitSnapshot, directory: Path) -> Path:
    """Write a stable, safely escaped snapshot beside the main document."""
    path = directory / TYPST_METADATA_FILE
    content = (
        json.dumps(asdict(snapshot), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    )
    if not path.is_file() or path.read_text() != content:
        path.write_text(content)
    return path


def refresh_typst_metadata(
    directory: Path, dry_run: bool = False
) -> Optional[GitSnapshot]:
    """Refresh when Git is available; preserve an archive's existing snapshot."""
    snapshot = read_git_snapshot(directory)
    if snapshot is not None and not dry_run:
        write_typst_snapshot(snapshot, directory)
    return snapshot
