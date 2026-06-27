"""Reject committed run-log directories that use a non-unique placeholder run-id.

Run-log directories must be named after the unique per-run session id (a UUID, or
the session tmpdir basename). A ``run-<N>`` value (e.g. ``run-1``) is a stale or
degraded fallback that collides across concurrent runs and clones, so the same
shared path lands in every PR and breaks rebases (issue #4397). This lint fails
when any tracked ``larch-logs/<skill>/run-<N>/`` path exists.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

GIT = shutil.which("git") or "git"

# larch-logs/<skill>/run-<N>/...  for the per-run log roots.
_PLACEHOLDER_PATH_RE = re.compile(r"^larch-logs/(implement|design|review)/run-[0-9]+(?:/|$)")


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint run-log-run-id", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _tracked_log_paths(root: Path) -> list[str]:
    proc = subprocess.run(
        [GIT, "-C", str(root), "ls-files", "-z", "--", "larch-logs"],
        check=False,
        stdout=subprocess.PIPE,
    )
    return [chunk.decode() for chunk in proc.stdout.split(b"\0") if chunk]


def find_violations(root: Path) -> list[str]:
    """Return sorted tracked paths whose run-id segment is a placeholder."""
    return sorted({path for path in _tracked_log_paths(root) if _PLACEHOLDER_PATH_RE.match(path)})


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv=argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = Path(parsed.root)
    if not root.is_dir():
        print(f"lint-run-log-run-id: --root is not a directory: {root}", file=sys.stderr)
        return 2
    violations = find_violations(root.resolve())
    if not violations:
        return 0
    print(
        "lint-run-log-run-id: committed run-log directories use a non-unique "
        "placeholder run-id (issue #4397):",
        file=sys.stderr,
    )
    for path in violations:
        print(f"  {path}", file=sys.stderr)
    print(
        "Run-log directories must be named after the unique session run-id "
        "(a UUID), not run-<N>.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
