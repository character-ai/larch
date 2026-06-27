"""Residual Bash path manifest reader."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_MANIFEST = Path("scripts/residual-bash-paths.txt")
_EXCLUDED_PREFIXES = ("larch-logs/", "node_modules/")
_SHELL_GLOBS = ("*.sh", "*.inc.bash")


def _repo_root_from_cwd(cwd: Path | None = None) -> Path:
    start = (cwd or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / _MANIFEST).is_file():
            return candidate
    return Path(__file__).resolve().parents[3]


def _validate_rel_path(raw: str) -> str:
    if raw.startswith("/") or "\0" in raw:
        raise ValueError(f"invalid residual bash path: {raw!r}")
    parts = Path(raw).parts
    if any(part == ".." for part in parts):
        raise ValueError(f"invalid residual bash path: {raw!r}")
    if raw.startswith(_EXCLUDED_PREFIXES):
        raise ValueError(f"excluded residual bash path: {raw!r}")
    if not raw.endswith((".sh", ".inc.bash")):
        raise ValueError(f"residual bash path must end with .sh or .inc.bash: {raw!r}")
    return raw


def read_residual_paths(
    root: str | Path | None = None,
    *,
    check_exists: bool = False,
) -> list[str]:
    root_path = Path(root).resolve() if root is not None else _repo_root_from_cwd()
    manifest = root_path / _MANIFEST
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"could not read residual bash manifest: {manifest}") from exc

    paths: list[str] = []
    seen: set[str] = set()
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        rel = _validate_rel_path(stripped)
        if rel in seen:
            raise ValueError(f"duplicate residual bash path at {manifest}:{lineno}: {rel}")
        seen.add(rel)
        if rel.startswith(_EXCLUDED_PREFIXES):
            continue
        if check_exists and not (root_path / rel).is_file():
            raise ValueError(f"missing residual bash path under {root_path}: {rel}")
        paths.append(rel)
    return paths


def _git_shell_paths(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z", *_SHELL_GLOBS],  # noqa: S607
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        return []
    raw = proc.stdout.decode("utf-8", errors="surrogateescape")
    return [part for part in raw.split("\0") if part]


def intersect_git_shell_paths(root: str | Path) -> list[str]:
    root_path = Path(root).resolve()
    manifest_paths = read_residual_paths(root_path)
    git_paths = set(_git_shell_paths(root_path))
    return [rel for rel in manifest_paths if rel in git_paths]


def paths_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py residual-bash paths")
    _ = parser.add_argument("--root", default=None, help="repository or fixture root")
    _ = parser.add_argument("--null-delimited", action="store_true", help="emit NUL-delimited paths")
    _ = parser.add_argument(
        "--check-exists",
        action="store_true",
        help="fail when a manifest row is missing under --root",
    )
    _ = parser.add_argument(
        "--intersect-git",
        action="store_true",
        help="emit only manifest rows present in git ls-files shell listing",
    )
    args = parser.parse_args(argv)
    try:
        if args.intersect_git:
            paths = intersect_git_shell_paths(args.root or _repo_root_from_cwd())
            if args.check_exists:
                _ = read_residual_paths(args.root, check_exists=True)
        else:
            paths = read_residual_paths(args.root, check_exists=args.check_exists)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    sep = "\0" if args.null_delimited else "\n"
    if paths:
        _ = sys.stdout.write(sep.join(paths) + sep)
    return 0


if __name__ == "__main__":
    raise SystemExit(paths_main())
