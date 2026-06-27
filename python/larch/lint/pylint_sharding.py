"""Lexicographic-basename sharding for the pylint CI pass.

Splits the Python source tree into shards by file *basename* so a shard's
membership never depends on directory layout. The tree is being repartitioned
into subpackages; basename keying keeps sharding stable across that move and
needs no per-file assignment map. Enumeration is recursive (``rglob``), so files
are found wherever they live.

Cut points are tuned for even pylint *wall time* -- pylint cost tracks
parse+inference, not file count -- and may need re-tuning after large renames or
when a leading-name cluster (for example ``test_*``) grows lopsided. Re-tune by
timing ``make py-lint-shard PYLINT_SHARD_ID=N PYLINT_SHARD_COUNT=3`` for each
shard and shifting CUT_POINTS until the wall times converge; ``--print-files``
dumps a shard's file list without running pylint.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Lexicographic basename cut points: N-1 cut points define N shards. A file with
# basename < CUT_POINTS[0] is shard 1; CUT_POINTS[k-1] <= base < CUT_POINTS[k] is
# shard k+1; base >= CUT_POINTS[-1] is the last shard. Current 3-way split:
#   shard 1: basenames < "p"          -> non-test source a..o (+ fast checks)
#   shard 2: "p" <= base < "test_e"   -> p*/r*/s* source + test_a..test_d
#   shard 3: base >= "test_e"         -> test_e..test_z + timing/tokens/tracking
#
# Tuned from real per-shard CI timings (4-core runners), not line count. Shard 1
# (a..o source) is the lightest pylint shard on CI -- the ``test_*`` shards lint
# heavier despite fewer lines -- so it carries the one-time ruff + AST ratchet
# fast checks (~10s on CI), which evens the per-shard wall times to ~30/27/23s.
# Cuts sit on robust boundaries -- never inside a same-prefix cluster
# (``review_*``, ``report_*``, ``plan_*``) whose files move together -- so a
# rename shifts at most a whole prefix group, never one file mid-cluster.
# Re-measure and nudge after large renames; the gate wall time is the *max*
# shard. Moving the fast checks to a heavier shard inflates that shard (verified
# on CI); keep them on the lightest.
CUT_POINTS: tuple[str, ...] = ("p", "test_e")

PYLINT_BIN = "pylint"

# Replicate the .pylintrc discovery ignores so an explicit per-shard file list
# matches the coverage of a bare ``pylint .`` invocation.
_IGNORE_BASENAMES = frozenset({"models.py"})
_IGNORE_SUFFIXES = ("_pb2.py", "_pb2_grpc.py")
_IGNORE_DIR_PARTS = frozenset({"__pycache__", ".venv", ".mypy_cache"})


def source_dir_for(root: Path) -> Path:
    """Return the Python source root (``<root>/python``)."""
    return root / "python"


def enumerate_py_files(source_dir: Path) -> list[str]:
    """Return source-relative ``.py`` paths pylint would lint, sorted by basename."""
    found: list[str] = []
    for path in source_dir.rglob("*.py"):
        if any(part in _IGNORE_DIR_PARTS for part in path.parts):
            continue
        name = path.name
        if name in _IGNORE_BASENAMES or name.endswith(_IGNORE_SUFFIXES):
            continue
        found.append(path.relative_to(source_dir).as_posix())
    found.sort(key=lambda rel: (Path(rel).name, rel))
    return found


def assign_shard(basename: str, *, cut_points: Sequence[str]) -> int:
    """Return the 1-based shard for ``basename`` given lexicographic cut points."""
    for index, cut in enumerate(cut_points):
        if basename < cut:
            return index + 1
    return len(cut_points) + 1


def files_for_shard(
    files: Sequence[str],
    *,
    shard_id: int,
    shard_count: int,
    cut_points: Sequence[str] = CUT_POINTS,
) -> list[str]:
    """Return the subset of ``files`` assigned to ``shard_id``.

    The union over ``shard_id in [1, shard_count]`` is exactly ``files`` and the
    shards are disjoint, so coverage can never drop or double-count.
    """
    if shard_count < 1:
        raise ValueError(f"shard_count must be >= 1, got {shard_count}")
    if not 1 <= shard_id <= shard_count:
        raise ValueError(f"shard_id must be in [1, {shard_count}], got {shard_id}")
    if len(cut_points) != shard_count - 1:
        raise ValueError(
            f"need {shard_count - 1} cut points for {shard_count} shards, "
            f"got {len(cut_points)}"
        )
    return [
        rel
        for rel in files
        if assign_shard(Path(rel).name, cut_points=cut_points) == shard_id
    ]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cli.py lint pylint-shard", description="Run pylint on one basename shard."
    )
    _ = parser.add_argument("--shard-id", type=int, required=True)
    _ = parser.add_argument("--shard-count", type=int, required=True)
    _ = parser.add_argument("--jobs", default=None, help="pylint -j value")
    _ = parser.add_argument(
        "--root", default=str(Path(__file__).resolve().parents[3])
    )
    _ = parser.add_argument(
        "--print-files",
        action="store_true",
        help="print the shard's files (one per line) instead of running pylint",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    source_dir = source_dir_for(Path(parsed.root).resolve())
    if not source_dir.is_dir():
        print(f"pylint-shard: python directory not found: {source_dir}", file=sys.stderr)
        return 2
    try:
        files = files_for_shard(
            enumerate_py_files(source_dir),
            shard_id=parsed.shard_id,
            shard_count=parsed.shard_count,
        )
    except ValueError as exc:
        print(f"pylint-shard: {exc}", file=sys.stderr)
        return 2
    if parsed.print_files:
        print("\n".join(files))
        return 0
    if not files:
        print(
            f"pylint-shard: shard {parsed.shard_id}/{parsed.shard_count} has no files",
            file=sys.stderr,
        )
        return 0
    return _run_pylint(jobs=parsed.jobs, files=files, source_dir=source_dir)


def _run_pylint(*, jobs: str | None, files: list[str], source_dir: Path) -> int:
    """Run pylint over ``files`` from ``source_dir`` and return its exit code.

    Runs from ``source_dir`` so pylint finds .pylintrc and resolves imports as a
    bare ``pylint .`` does; output streams to inherited stdout/stderr. pylint is
    invoked as ``python -m pylint`` so it shares this interpreter's venv. This
    child-linter call mirrors lint_complexity_baseline._run_ruff.
    """
    cmd = [sys.executable, "-m", PYLINT_BIN]
    if jobs is not None:
        cmd += ["-j", str(jobs)]
    cmd += files
    # lint-subprocess-via-runner: ok runs the pylint linter as a child process
    proc = subprocess.run(cmd, cwd=source_dir, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
