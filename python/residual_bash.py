"""Residual Bash path manifest reader."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_MANIFEST = Path("scripts/residual-bash-paths.txt")
_EXCLUDED_PREFIXES = ("larch-logs/", "node_modules/")


def _repo_root_from_cwd(cwd: Path | None = None) -> Path:
    start = (cwd or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / _MANIFEST).is_file():
            return candidate
    return Path(__file__).resolve().parents[1]


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


def read_residual_paths(root: str | Path | None = None) -> list[str]:
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
        paths.append(rel)
    return paths


def paths_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py residual-bash paths")
    _ = parser.add_argument("--root", default=None, help="repository or fixture root")
    _ = parser.add_argument("--null-delimited", action="store_true", help="emit NUL-delimited paths")
    args = parser.parse_args(argv)
    try:
        paths = read_residual_paths(args.root)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    sep = "\0" if args.null_delimited else "\n"
    if paths:
        _ = sys.stdout.write(sep.join(paths) + sep)
    return 0


if __name__ == "__main__":
    raise SystemExit(paths_main())
