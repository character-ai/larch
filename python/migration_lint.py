"""Retired-scripts manifest lint for the sh-to-py migration.

Checks that no tracked file references any retired script path (full repo-relative
path only — never bare basename matching). Exits 0 when clean, 1 on findings, 2
on usage/manifest errors.

Contract KV on stdout (fd 3 / contract_stream after quiet_init):
    LINT_STATUS=ok|findings
    RETIRED_PATHS=<count>
    RETIRED_REFS=<count of reference occurrences>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import logging_util
import proc


_MANIFEST_DEFAULT = "python/migrated-scripts.tsv"
_EXCLUSION_SEGMENTS = frozenset({"larch-logs"})
_EXCLUSION_FILES = frozenset({"CHANGELOG.md"})


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    """Parse args; return None on usage/manifest error (caller exits 2)."""
    parser = argparse.ArgumentParser(
        prog="cli.py lint retired-scripts",
        description="Lint references to retired script paths.",
    )
    _ = parser.add_argument(
        "--manifest",
        default=_MANIFEST_DEFAULT,
        help="Path to the retired-scripts TSV manifest (default: %(default)s)",
    )
    _ = parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def _parse_manifest(manifest_path: Path) -> list[str] | None:
    """Return list of retired repo-relative paths. Returns None on error."""
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return None
    retired: list[str] = []
    for lineno, raw in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].strip():  # noqa: PLR2004
            print(
                f"ERROR: manifest line {lineno} malformed "
                f"(expected path<TAB>retired_by): {raw!r}",
                file=sys.stderr,
            )
            return None
        path = parts[0].strip()
        if path:
            retired.append(path)
    return retired


def _is_binary(path: Path) -> bool:
    try:
        return b"\x00" in path.read_bytes()[:8192]
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    args_list = argv if argv is not None else sys.argv[1:]
    # Parse args BEFORE quiet_init so usage errors reach caller stdout/stderr.
    parsed = _parse_args(args_list)
    if parsed is None:
        return 2

    logging_util.quiet_init(argv0="cli.py")

    manifest_path = Path(parsed.manifest)
    root_path = Path(parsed.root).resolve()
    manifest_abs = (
        (root_path / manifest_path).resolve()
        if not manifest_path.is_absolute()
        else manifest_path.resolve()
    )

    retired = _parse_manifest(manifest_abs)
    if retired is None:
        return 2

    if not retired:
        logging_util.emit_kv("LINT_STATUS", "ok")
        logging_util.emit_kv("RETIRED_PATHS", "0")
        logging_util.emit_kv("RETIRED_REFS", "0")
        return 0

    manifest_rel = (
        str(manifest_abs.relative_to(root_path))
        if manifest_abs.is_relative_to(root_path)
        else str(manifest_abs)
    )

    # Check: any retired path still present on disk is itself an error.
    still_present = [r for r in retired if (root_path / r).exists()]
    if still_present:
        for path in still_present:
            logging_util.BreadcrumbWriter().emit(
                f"ERROR: retired path still present in the tree: {path}"
            )
        logging_util.emit_kv("LINT_STATUS", "findings")
        logging_util.emit_kv("RETIRED_PATHS", str(len(retired)))
        logging_util.emit_kv("RETIRED_REFS", "0")
        return 1

    result = proc.run(["git", "ls-files", "-z"], cwd=str(root_path))
    if result.returncode != 0:
        print(
            f"ERROR: git ls-files failed: {result.stderr.strip()}", file=sys.stderr
        )
        return 2

    tracked_rel: list[str] = [p for p in result.stdout.split("\x00") if p]
    retired_set = set(retired)
    writer = logging_util.BreadcrumbWriter()
    ref_count = 0

    for rel in tracked_rel:
        parts = Path(rel).parts
        if any(seg in _EXCLUSION_SEGMENTS for seg in parts):
            continue
        if Path(rel).name in _EXCLUSION_FILES:
            continue
        if rel == manifest_rel:
            continue
        abs_path = root_path / rel
        if _is_binary(abs_path):
            continue
        try:
            lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line_text in enumerate(lines, 1):
            for retired_path in retired_set:
                if retired_path in line_text:
                    writer.emit(f"{rel}:{lineno}: references retired path {retired_path!r}")
                    ref_count += 1

    if ref_count > 0:
        logging_util.emit_kv("LINT_STATUS", "findings")
        logging_util.emit_kv("RETIRED_PATHS", str(len(retired_set)))
        logging_util.emit_kv("RETIRED_REFS", str(ref_count))
        return 1

    logging_util.emit_kv("LINT_STATUS", "ok")
    logging_util.emit_kv("RETIRED_PATHS", str(len(retired_set)))
    logging_util.emit_kv("RETIRED_REFS", "0")
    return 0
