from __future__ import annotations

import csv
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
TOPOLOGY_PATH = REPO_ROOT / "skills" / "shared" / "topology.tsv"
PATH_COLUMNS = ("runtime_authority",)

Runner = Callable[..., subprocess.CompletedProcess[Any]]
DEFAULT_RUNNER: Runner = getattr(subprocess, "run")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def _is_local_path(value: str) -> bool:
    if not value or value in {"-", "n/a", "N/A"}:
        return False
    return "://" not in value and not value.startswith("#")


def _repo_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            fail(f"path is outside repository: {value}")
    return path.as_posix()


def _check_tracked(*, row: int, path: str, runner: Runner = DEFAULT_RUNNER) -> None:
    proc = runner(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        fail(f"row {row}: runtime_authority is not tracked by git: {path}")


def _iter_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            fail(f"{path}: missing header row")
        missing = [column for column in PATH_COLUMNS if column not in reader.fieldnames]
        if missing:
            fail(f"{path}: missing required column(s): {', '.join(missing)}")
        return list(reader)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or ())
    if args:
        fail("usage: check_topology_rule_paths.py")

    if not TOPOLOGY_PATH.exists():
        fail(f"missing topology file: {TOPOLOGY_PATH.relative_to(REPO_ROOT)}")

    for index, row in enumerate(_iter_rows(TOPOLOGY_PATH), start=2):
        for column in PATH_COLUMNS:
            value = (row.get(column) or "").strip()
            if not _is_local_path(value):
                continue
            _check_tracked(row=index, path=_repo_relative_path(value))

    return 0


if __name__ == "__main__":
    sys.exit(main())
