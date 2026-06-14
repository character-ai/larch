"""Retired-scripts manifest lint for the sh-to-py migration.

Checks that no tracked file references any retired script path. Most checks use
full repo-relative paths only; dev skill markdown also catches scoped
same-directory bare basenames for orphaned script docs. Exits 0 when clean, 1 on
findings, 2 on usage/manifest errors.

Contract KV on stdout (fd 3 / contract_stream after quiet_init):
    LINT_STATUS=ok|findings
    RETIRED_PATHS=<count>
    RETIRED_REFS=<count of reference occurrences>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import logging_util
import proc


_MANIFEST_DEFAULT = "python/migrated-scripts.tsv"
_EXCLUSION_SEGMENTS = frozenset({"larch-logs"})
_EXCLUSION_FILES = frozenset({"CHANGELOG.md"})
_EXCLUSION_PATHS = frozenset({".claude-plugin/plugin.json"})


def _script_dir_refs(retired_path: str) -> tuple[str, ...]:
    basename = Path(retired_path).name
    return (
        f"$SCRIPT_DIR/{basename}",
        f"${{SCRIPT_DIR}}/{basename}",
    )


def _ship_pr_live_ref(line_text: str, retired_path: str) -> bool:
    """Return true only for live ship-pr invocation/source forms."""
    stripped = line_text.strip()
    if not stripped or stripped.startswith("#"):
        return False
    basename = re.escape(Path(retired_path).name)
    full_path = re.escape(retired_path)
    script_dir_path = rf"(?:\$\{{SCRIPT_DIR\}}|\$SCRIPT_DIR)(?:/[^\"'\s;|&)]+)*/{basename}"
    patterns = (
        re.compile(
            rf"(^|[\s;|&(])(?:(?:source|\.)\s+)?[\"']?{script_dir_path}[\"']?(?=$|[\s;|&)>])"
        ),
        re.compile(
            rf"(^|[\s;|&(])(?:(?:source|\.)\s+)?[\"']?{full_path}[\"']?(?=$|[\s;|&)>])"
        ),
        re.compile(
            rf"(^|[\s;|&(])(?:source|\.)\s+[\"']?{basename}[\"']?(?=$|[\s;|&)>])"
        ),
    )
    return any(pattern.search(line_text) is not None for pattern in patterns)


def _dev_skill_markdown_bare_basename_ref(
    repo_root: Path,
    rel: str,
    line_text: str,
    retired_path: str,
    retired_dir: Path,
) -> bool:
    rel_path = Path(rel)
    if rel_path.suffix != ".md":
        return False
    if rel_path.parts[:2] != (".claude", "skills"):
        return False
    if rel_path.parent != retired_dir:
        return False
    if "# lint-ignore" in line_text:
        return False
    if (repo_root / rel_path.with_suffix(".sh")).exists():
        return False
    basename = Path(retired_path).name
    bare_name = re.compile(
        rf"(?<![A-Za-z0-9_./-]){re.escape(basename)}(?![A-Za-z0-9_./-])"
    )
    return bare_name.search(line_text) is not None


def _implement_skill_markdown_bare_basename_ref(
    rel: str,
    line_text: str,
    retired_path: str,
) -> bool:
    if rel != "skills/implement/SKILL.md":
        return False
    if "# lint-ignore" in line_text:
        return False
    basename = Path(retired_path).name
    bare_name = re.compile(
        rf"(?<![A-Za-z0-9_./-]){re.escape(basename)}(?![A-Za-z0-9_./-])"
    )
    return bare_name.search(line_text) is not None


def _line_references_retired(
    repo_root: Path,
    rel: str,
    rel_dir: Path,
    line_text: str,
    retired_path: str,
    retired_dir: Path,
    retired_refs: tuple[str, ...],
) -> bool:
    """Return True if ``line_text`` references ``retired_path``.

    The parent directories (``rel_dir``/``retired_dir``) and ``$SCRIPT_DIR``
    reference forms (``retired_refs``) are precomputed by the caller so this
    runs in the hot (line x retired_path) loop without per-pair ``Path``
    construction; the behavior is identical to comparing
    ``Path(rel).parent == Path(retired_path).parent`` inline.
    """
    if rel == "scripts/ship-pr.sh":
        return _ship_pr_live_ref(line_text, retired_path)
    if retired_path in line_text:
        return True
    if rel_dir == retired_dir and any(ref in line_text for ref in retired_refs):
        return True
    if _implement_skill_markdown_bare_basename_ref(rel, line_text, retired_path):
        return True
    return _dev_skill_markdown_bare_basename_ref(
        repo_root,
        rel,
        line_text,
        retired_path,
        retired_dir,
    )


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

    result = proc.run(["git", "ls-files", "-z", "--", ".", ":(exclude)larch-logs/**"], cwd=str(root_path))
    if result.returncode != 0:
        print(
            f"ERROR: git ls-files failed: {result.stderr.strip()}", file=sys.stderr
        )
        return 2

    tracked_rel: list[str] = [p for p in result.stdout.split("\x00") if p]
    retired_set = set(retired)
    # Precompute per-retired-path data once so the hot (line x retired_path)
    # loop does no Path construction or repeated _script_dir_refs work. The
    # earlier non-empty guard guarantees retired_set is non-empty here.
    retired_list = sorted(retired_set)
    retired_dirs = {r: Path(r).parent for r in retired_list}
    retired_refs = {r: _script_dir_refs(r) for r in retired_list}
    # Cheap prefilter: every retired reference form carries the retired
    # basename. Build basename -> retired path candidates so common prose lines
    # avoid the expensive all-retired-path inner loop.
    retired_by_basename: dict[str, list[str]] = {}
    for retired_path in retired_list:
        retired_by_basename.setdefault(Path(retired_path).name, []).append(retired_path)
    writer = logging_util.BreadcrumbWriter()
    ref_count = 0

    for rel in tracked_rel:
        rel_parts_str = f"/{rel}/"
        if any(f"/{seg}/" in rel_parts_str for seg in _EXCLUSION_SEGMENTS):
            continue
        if rel in _EXCLUSION_PATHS:
            continue
        rel_name = rel.rsplit("/", 1)[-1]
        if rel_name in _EXCLUSION_FILES:
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
        rel_dir = Path(rel).parent
        for lineno, line_text in enumerate(lines, 1):
            # All currently retired script paths are .sh/.md siblings; skip
            # ordinary lines before checking basename membership.
            if ".sh" not in line_text and ".md" not in line_text:
                continue
            candidate_paths: set[str] = set()
            for basename, paths_for_basename in retired_by_basename.items():
                if basename in line_text:
                    candidate_paths.update(paths_for_basename)
            if not candidate_paths:
                continue
            for retired_path in sorted(candidate_paths):
                if _line_references_retired(
                    root_path,
                    rel,
                    rel_dir,
                    line_text,
                    retired_path,
                    retired_dirs[retired_path],
                    retired_refs[retired_path],
                ):
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
