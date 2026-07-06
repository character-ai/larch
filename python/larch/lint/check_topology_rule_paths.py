"""Validate topology TSV runtime authorities."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from larch.lint import lint_common

TOPOLOGY_TSV = "skills/shared/topology.tsv"
EXPECTED_TSV_COLUMNS = 4


def fail(message: str) -> NoReturn:
    print(f"check-topology-rule-paths: {message}", file=sys.stderr)
    sys.exit(1)


def path_has_segment(*, path: str, segment: str) -> bool:
    return segment in path.split("/")


def validate_repo_path(*, row: int, path: str, repo_root: Path, repo_root_resolved: Path) -> Path:
    if path != path.strip():
        fail(f"row {row}: runtime_authority must not contain leading or trailing whitespace")
    if not path:
        fail(f"row {row}: empty runtime_authority")
    if path.startswith("/"):
        fail(f"row {row}: runtime_authority must be repo-relative: {path}")
    if path.startswith("./"):
        fail(f"row {row}: runtime_authority must not start with ./ : {path}")
    if path.startswith("-"):
        fail(f"row {row}: runtime_authority must not start with -: {path}")
    if path.startswith(":"):
        fail(f"row {row}: runtime_authority must not start with : (reserved for git pathspec magic): {path}")
    if "//" in path:
        fail(f"row {row}: runtime_authority must not contain duplicate slash: {path}")
    if "\t" in path:
        fail(f"row {row}: runtime_authority must not contain tabs")
    if "\n" in path:
        fail(f"row {row}: runtime_authority must not contain newlines")
    if path_has_segment(path=path, segment=".."):
        fail(f"row {row}: runtime_authority must not contain parent traversal: {path}")
    if path_has_segment(path=path, segment="."):
        fail(f"row {row}: runtime_authority must not contain . path segments: {path}")
    full_path = repo_root / path
    resolved = full_path.resolve(strict=False)
    try:
        _ = resolved.relative_to(repo_root_resolved)
    except ValueError:
        fail(f"row {row}: runtime_authority must resolve within repo root: {path}")
    return full_path


def _check_git_tracked(*, row: int, path: str, repo_root: Path) -> None:
    proc = subprocess.run(
        [lint_common.GIT, "-C", str(repo_root), "ls-files", "--error-unmatch", "--", path],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        fail(f"row {row}: runtime_authority is not tracked by git: {path}")


def _read_authority_file(*, row: int, value: str, rel_path: str, full_path: Path) -> None:
    if not full_path.exists():
        fail(f"row {row}: runtime_authority file does not exist: {rel_path}")
    if full_path.is_symlink() or not full_path.is_file():
        fail(f"row {row}: runtime_authority must be a regular file: {rel_path}")
    try:
        text = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        fail(f"row {row}: unable to read runtime_authority {rel_path}: {exc}")
    if value not in text:
        fail(f"row {row}: runtime_authority {rel_path} does not contain value {value!r}")


def read_topology_authorities(*, topology_tsv: Path, repo_root: Path, repo_root_resolved: Path) -> set[str]:
    authorities: set[str] = set()
    enforce_git_tracked = lint_common.git_rooted(repo_root)
    try:
        with topology_tsv.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        fail(f"unable to read {TOPOLOGY_TSV}: {exc}")

    for row, line in enumerate(text.split("\n"), 1):
        if "\r" in line:
            fail(f"row {row}: CRLF line endings not allowed (use LF)")
        if line == "" or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != EXPECTED_TSV_COLUMNS or fields[0] == "" or fields[1] == "" or fields[3] == "":
            fail(
                f"row {row}: malformed row; expected exactly four tab-separated columns "
                "with key, value, and runtime_authority non-empty"
            )
        full_path = validate_repo_path(row=row, path=fields[3], repo_root=repo_root, repo_root_resolved=repo_root_resolved)
        _read_authority_file(row=row, value=fields[1], rel_path=fields[3], full_path=full_path)
        if enforce_git_tracked:
            _check_git_tracked(row=row, path=fields[3], repo_root=repo_root)
        authorities.add(fields[3])

    if not authorities:
        fail(f"{TOPOLOGY_TSV} has no data rows")
    return authorities


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root to validate (default: this module's parent directory).",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    repo_root = args.root.resolve()
    repo_root_resolved = repo_root.resolve()
    topology_tsv = repo_root / TOPOLOGY_TSV
    _ = read_topology_authorities(
        topology_tsv=topology_tsv,
        repo_root=repo_root,
        repo_root_resolved=repo_root_resolved,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
