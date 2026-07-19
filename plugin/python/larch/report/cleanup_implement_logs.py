# ruff: noqa: PLR2004,SIM114,SIM103,TC006
"""cleanup_implement_logs.py — retroactive log cleanup for larch-logs/implement/.

Applies the Phase 1 publish-time rules retroactively to committed run dirs:

  1. Delete round-N/dyn-*-prompt.md (rendered dynamic-reviewer prompts).
  2. Delete round-N/aggregator-output.txt when byte-identical to findings.md.
  3. Delete scout-round*-manifest.json.raw (cooked .json is canonical).
  4. Delete refresh sidecars: token-report-refresh.json,
     timing-report-refresh.json, session-transcript-refresh.*.
  5. Delete cursor-specialist-*-output-phase*.txt and
     cursor-specialist-*-output-retry.txt (keep *-ns-retry*).
  6. Upgrade session-transcript.jsonl from schema v1 to v2 (stub
     Edit/Write/NotebookEdit inputs; elide large tool_call inputs).
  7. Consolidate breadcrumbs/larch-quiet-*.log into breadcrumbs/quiet.log.
  8. Drop the 'body' field from code-review-tally.json records.
  9. Remove the stray python/larch-logs/ tree entirely.

Usage:
  # dry-run (default): print what would be done
  python3 python/cli.py run-log cleanup-implement-logs

  # execute for real
  python3 python/cli.py run-log cleanup-implement-logs --execute

  # restrict to a single run dir (for spot-checking)
  python3 python/cli.py run-log cleanup-implement-logs --run-dir larch-logs/implement/<UUID> --execute

Exit codes:
  0  success
  1  unexpected error
"""
from __future__ import annotations

import argparse
import filecmp
import fnmatch
import json
import shutil
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import cast

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STUB_INPUT_TOOLS = {"Edit", "Write", "NotebookEdit"}
INPUT_CAP_BYTES = 1024

# Sidecar extensions that travel alongside deletable files.
_SIDECAR_EXTS = (".meta", ".json")

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

class Stats:
    def __init__(self) -> None:
        self.dyn_prompt_deleted = 0
        self.aggregator_deleted = 0
        self.raw_manifest_deleted = 0
        self.refresh_deleted = 0
        self.cursor_phase_retry_deleted = 0
        self.transcript_upgraded = 0
        self.breadcrumbs_consolidated = 0
        self.breadcrumb_files_removed = 0
        self.tally_body_stripped = 0
        self.python_larch_logs_removed = 0
        self.errors: list[str] = []

    def report(self) -> None:
        print("=== cleanup-implement-logs summary ===")
        print(f"  dyn-*-prompt.md deleted:             {self.dyn_prompt_deleted}")
        print(f"  aggregator-output.txt deleted:       {self.aggregator_deleted}")
        print(f"  scout-round*.json.raw deleted:       {self.raw_manifest_deleted}")
        print(f"  refresh sidecars deleted:            {self.refresh_deleted}")
        print(f"  cursor phase/retry files deleted:    {self.cursor_phase_retry_deleted}")
        print(f"  session-transcript.jsonl upgraded:   {self.transcript_upgraded}")
        print(f"  breadcrumbs dirs consolidated:       {self.breadcrumbs_consolidated}")
        print(f"  larch-quiet-*.log files removed:     {self.breadcrumb_files_removed}")
        print(f"  code-review-tally body stripped:     {self.tally_body_stripped}")
        print(f"  python/larch-logs/ entries removed:  {self.python_larch_logs_removed}")
        if self.errors:
            print(f"  ERRORS ({len(self.errors)}):")
            for e in self.errors[:20]:
                print(f"    {e}")
            if len(self.errors) > 20:
                print(f"    ... and {len(self.errors) - 20} more")


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _delete(
    *, path: Path,
    execute: bool,
    stats_attr: str,
    stats: Stats,
    run_dir_resolved: Path,
) -> None:
    """Delete path and its sidecar files (.meta, .json) when they exist."""
    targets = [path]
    for ext in _SIDECAR_EXTS:
        sidecar = path.parent / (path.name + ext)
        if sidecar.exists() and sidecar != path:
            targets.append(sidecar)
    for t in targets:
        if not _within_run_dir(path=t, run_dir_resolved=run_dir_resolved):
            continue
        if execute:
            try:
                t.unlink()
            except OSError as exc:
                stats.errors.append(f"unlink {t}: {exc}")
                return
        setattr(stats, stats_attr, getattr(stats, stats_attr) + 1)


# ---------------------------------------------------------------------------
# Containment helpers — keep destructive actions inside the run dir
# ---------------------------------------------------------------------------

def _within_run_dir(*, path: Path, run_dir_resolved: Path) -> bool:
    """Return True when *path* resolves to a location inside *run_dir_resolved*.

    The path is fully resolved (collapsing symlinks and ``..``) before the
    containment check, so a symlink that escapes the run dir — whether the final
    component or an intermediate directory component — is reported as outside.
    Read/write/unlink callers skip escaping paths so a planted symlink inside a
    run dir cannot lure the destructive cleanup actions out of the tree. Mirrors
    the top-level guard in :func:`_resolve_single_run_dir`.
    """
    try:
        return path.resolve().is_relative_to(run_dir_resolved)
    except (OSError, RuntimeError):
        return False


def _contained(*, run_dir: Path, paths: Iterable[Path]) -> Iterator[Path]:
    """Yield only the *paths* that resolve inside *run_dir*, skipping escapes."""
    run_dir_resolved = run_dir.resolve()
    return (p for p in paths if _within_run_dir(path=p, run_dir_resolved=run_dir_resolved))


# ---------------------------------------------------------------------------
# Action 1: Delete dyn-*-prompt.md
# ---------------------------------------------------------------------------

def delete_dyn_prompts(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    run_dir_resolved = run_dir.resolve()
    for p in _contained(run_dir=run_dir, paths=run_dir.rglob("dyn-*-prompt.md")):
        _delete(path=p, execute=execute, stats_attr="dyn_prompt_deleted", stats=stats, run_dir_resolved=run_dir_resolved)


# ---------------------------------------------------------------------------
# Action 2: Delete aggregator-output.txt when byte-identical to findings.md
# ---------------------------------------------------------------------------

def delete_identical_aggregator(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    run_dir_resolved = run_dir.resolve()
    for agg in _contained(run_dir=run_dir, paths=run_dir.rglob("aggregator-output.txt")):
        findings = agg.parent / "findings.md"
        if not findings.is_file():
            continue
        # Don't read through a findings.md that escapes the run dir via symlink.
        if not _within_run_dir(path=findings, run_dir_resolved=run_dir_resolved):
            continue
        if filecmp.cmp(str(agg), str(findings), shallow=False):
            _delete(path=agg, execute=execute, stats_attr="aggregator_deleted", stats=stats, run_dir_resolved=run_dir_resolved)
    # Clean up orphaned aggregator sidecars (e.g. .meta committed when the Phase 1
    # deny skipped the .txt but the sidecar slipped through).
    for ext in _SIDECAR_EXTS:
        for sidecar in _contained(run_dir=run_dir, paths=run_dir.rglob(f"aggregator-output.txt{ext}")):
            parent = sidecar.parent / "aggregator-output.txt"
            if not parent.exists():
                if execute:
                    try:
                        sidecar.unlink()
                    except OSError as exc:
                        stats.errors.append(f"unlink orphan {sidecar}: {exc}")
                        continue
                stats.aggregator_deleted += 1


# ---------------------------------------------------------------------------
# Action 3: Delete scout-round*-manifest.json.raw
# ---------------------------------------------------------------------------

def delete_raw_manifests(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    run_dir_resolved = run_dir.resolve()
    for p in _contained(run_dir=run_dir, paths=run_dir.rglob("scout-round*-manifest.json.raw")):
        _delete(path=p, execute=execute, stats_attr="raw_manifest_deleted", stats=stats, run_dir_resolved=run_dir_resolved)


# ---------------------------------------------------------------------------
# Action 4: Delete refresh sidecars
# ---------------------------------------------------------------------------

_REFRESH_NAMES = {
    "token-report-refresh.json",
    "timing-report-refresh.json",
}

def delete_refresh_sidecars(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    run_dir_resolved = run_dir.resolve()
    for p in _contained(run_dir=run_dir, paths=run_dir.rglob("*")):
        name = p.name
        if name in _REFRESH_NAMES:
            _delete(path=p, execute=execute, stats_attr="refresh_deleted", stats=stats, run_dir_resolved=run_dir_resolved)
        elif p.is_file() and name.startswith("session-transcript-refresh."):
            _delete(path=p, execute=execute, stats_attr="refresh_deleted", stats=stats, run_dir_resolved=run_dir_resolved)


# ---------------------------------------------------------------------------
# Action 5: Delete cursor-specialist phase/retry files (keep ns-retry)
# ---------------------------------------------------------------------------

def _is_cursor_phase_retry(name: str) -> bool:
    """Return True for cursor-specialist-*-output-{phase*,retry}.txt (not ns-retry)."""
    if not name.startswith("cursor-specialist-"):
        return False
    # Keep ns-retry
    if "ns-retry" in name:
        return False
    # Match phase variants: -output-phaseN.txt
    if fnmatch.fnmatch(name, "cursor-specialist-*-output-phase*.txt"):
        return True
    # Match plain retry: -output-retry.txt (not ns-retry, already filtered above)
    if fnmatch.fnmatch(name, "cursor-specialist-*-output-retry.txt"):
        return True
    return False


def delete_cursor_phase_retry(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    run_dir_resolved = run_dir.resolve()
    for p in _contained(run_dir=run_dir, paths=run_dir.rglob("cursor-specialist-*-output-*.txt")):
        if _is_cursor_phase_retry(p.name):
            _delete(path=p, execute=execute, stats_attr="cursor_phase_retry_deleted", stats=stats, run_dir_resolved=run_dir_resolved)


# ---------------------------------------------------------------------------
# Action 6: Upgrade session-transcript.jsonl v1 → v2
# ---------------------------------------------------------------------------

def _upgrade_transcript(*, path: Path, execute: bool, stats: Stats) -> None:
    """Apply v2 transforms to an already-rendered v1 session-transcript.jsonl."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        stats.errors.append(f"read {path}: {exc}")
        return

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return

    try:
        parsed_header: object = json.loads(lines[0])
    except json.JSONDecodeError:
        stats.errors.append(f"header parse failed: {path}")
        return
    if not isinstance(parsed_header, dict):
        stats.errors.append(f"header parse failed: {path}")
        return
    header = cast(dict[str, object], parsed_header)

    if cast(int, header.get("v", 1)) >= 2:
        return  # Already v2 — skip

    out_lines: list[str] = []
    header["v"] = 2
    out_lines.append(json.dumps(header, ensure_ascii=False, separators=(",", ":")))

    for line in lines[1:]:
        try:
            parsed_rec: object = json.loads(line)
        except json.JSONDecodeError:
            out_lines.append(line)
            continue
        if not isinstance(parsed_rec, dict):
            out_lines.append(line)
            continue
        rec = cast(dict[str, object], parsed_rec)

        if rec.get("role") == "assistant":
            new_blocks: list[object] = []
            blocks = rec.get("blocks", [])
            if not isinstance(blocks, list):
                out_lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
                continue
            block_items = cast(list[object], blocks)
            for blk in block_items:
                if not isinstance(blk, dict):
                    new_blocks.append(blk)
                    continue
                block = cast(dict[str, object], blk)
                if block.get("type") != "tool_call":
                    new_blocks.append(block)
                    continue
                name = block.get("name", "")
                inp = block.get("input")

                if (
                    isinstance(inp, dict)
                    and inp
                    and "elided_input_bytes" not in block
                    and "input_bytes" not in inp
                ):
                    input_map = cast(dict[str, object], inp)
                    if name in STUB_INPUT_TOOLS:
                        # Stub Edit/Write/NotebookEdit: preserve file_path, record byte count
                        file_path = (
                            input_map.get("file_path")
                            or input_map.get("notebook_path")
                            or input_map.get("path")
                            or ""
                        )
                        input_bytes = len(json.dumps(input_map, ensure_ascii=False))
                        new_blk = dict(block)
                        new_blk["input"] = {"file_path": file_path, "input_bytes": input_bytes}
                        new_blocks.append(new_blk)
                        continue
                    # Elide large inputs for other tools
                    serialized = json.dumps(input_map, ensure_ascii=False)
                    if len(serialized) > INPUT_CAP_BYTES:
                        new_blk = {k: v for k, v in block.items() if k != "input"}
                        new_blk["elided_input_bytes"] = len(serialized)
                        new_blocks.append(new_blk)
                        continue

                new_blocks.append(block)

            new_rec = dict(rec)
            new_rec["blocks"] = new_blocks
            out_lines.append(json.dumps(new_rec, ensure_ascii=False, separators=(",", ":")))
        else:
            out_lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))

    if execute:
        try:
            _ = path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            stats.errors.append(f"write {path}: {exc}")
            return

    stats.transcript_upgraded += 1


def upgrade_transcripts(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in _contained(run_dir=run_dir, paths=run_dir.rglob("session-transcript.jsonl")):
        _upgrade_transcript(path=p, execute=execute, stats=stats)


# ---------------------------------------------------------------------------
# Action 7: Consolidate breadcrumbs/larch-quiet-*.log → breadcrumbs/quiet.log
# ---------------------------------------------------------------------------

def _write_consolidated_quiet_log(
    *, quiet_log: Path, individual: list[Path], stats: Stats
) -> bool:
    """Concatenate *individual* logs into *quiet_log*, then unlink the sources.

    Returns ``False`` (recording an error) when the consolidated write fails, so
    the caller skips the success counters. Per-file read and unlink failures are
    recorded but do not abort the consolidation.
    """
    parts: list[str] = []
    for f in individual:
        parts.append(f"=== {f.name} ===\n")
        try:
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            parts.append("")
    try:
        _ = quiet_log.write_text("".join(parts), encoding="utf-8")
    except OSError as exc:
        stats.errors.append(f"write {quiet_log}: {exc}")
        return False

    for f in individual:
        try:
            f.unlink()
        except OSError as exc:
            stats.errors.append(f"unlink {f}: {exc}")
    return True


def consolidate_breadcrumbs(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    run_dir_resolved = run_dir.resolve()
    bc_dir = run_dir / "breadcrumbs"
    if not bc_dir.is_dir():
        return
    # Refuse when breadcrumbs/ is a symlink that escapes the run dir, so the
    # read/write/unlink below cannot operate on an external directory.
    if not _within_run_dir(path=bc_dir, run_dir_resolved=run_dir_resolved):
        return

    quiet_log = bc_dir / "quiet.log"
    # Skip if quiet.log already exists (Phase 1 already ran for this run dir)
    if quiet_log.exists():
        return
    # A planted quiet.log symlink that resolves outside the run dir would make
    # write_text() overwrite an external file; refuse to consolidate then.
    if not _within_run_dir(path=quiet_log, run_dir_resolved=run_dir_resolved):
        return

    # Skip individual logs that escape the run dir via symlink — reading them
    # would copy external content into quiet.log.
    individual = [
        f
        for f in sorted(bc_dir.glob("larch-quiet-*.log"))
        if _within_run_dir(path=f, run_dir_resolved=run_dir_resolved)
    ]
    if not individual:
        return

    if execute and not _write_consolidated_quiet_log(quiet_log=quiet_log, individual=individual, stats=stats):
        return

    stats.breadcrumbs_consolidated += 1
    stats.breadcrumb_files_removed += len(individual)


# ---------------------------------------------------------------------------
# Action 8: Drop 'body' field from code-review-tally.json
# ---------------------------------------------------------------------------

def strip_tally_body(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in _contained(run_dir=run_dir, paths=run_dir.glob("code-review-tally.json")):
        try:
            raw = p.read_text(encoding="utf-8")
            data: object = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            stats.errors.append(f"read/parse {p}: {exc}")
            continue

        modified = False
        if isinstance(data, list):
            records = cast(list[object], data)
            for rec in records:
                if isinstance(rec, dict) and "body" in rec:
                    record = cast(dict[str, object], rec)
                    del record["body"]
                    modified = True
        elif isinstance(data, dict) and "body" in data:
            del data["body"]
            modified = True

        if modified:
            if execute:
                try:
                    _ = p.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                except OSError as exc:
                    stats.errors.append(f"write {p}: {exc}")
                    continue
            stats.tally_body_stripped += 1


# ---------------------------------------------------------------------------
# Action 9: Remove python/larch-logs/ tree
# ---------------------------------------------------------------------------

def remove_python_larch_logs(*, repo_root: Path, execute: bool, stats: Stats) -> None:
    target = repo_root / "python" / "larch-logs"
    if not target.exists():
        return
    count = sum(1 for _ in target.rglob("*") if _.is_file())
    if execute:
        try:
            shutil.rmtree(str(target))
        except OSError as exc:
            stats.errors.append(f"rmtree {target}: {exc}")
            return
    stats.python_larch_logs_removed += count


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def process_run_dir(*, run_dir: Path, execute: bool, stats: Stats) -> None:
    delete_dyn_prompts(run_dir=run_dir, execute=execute, stats=stats)
    delete_identical_aggregator(run_dir=run_dir, execute=execute, stats=stats)
    delete_raw_manifests(run_dir=run_dir, execute=execute, stats=stats)
    delete_refresh_sidecars(run_dir=run_dir, execute=execute, stats=stats)
    delete_cursor_phase_retry(run_dir=run_dir, execute=execute, stats=stats)
    upgrade_transcripts(run_dir=run_dir, execute=execute, stats=stats)
    consolidate_breadcrumbs(run_dir=run_dir, execute=execute, stats=stats)
    strip_tally_body(run_dir=run_dir, execute=execute, stats=stats)


def _resolve_single_run_dir(*, run_dir_arg: str, impl_root: Path) -> Path | None:
    """Resolve a ``--run-dir`` argument and confirm it stays inside impl_root.

    Both paths are resolved (collapsing symlinks and ``..``) before the
    containment check, so a symlinked or parent-traversing argument cannot
    escape the ``larch-logs/implement/`` tree. Returns the resolved run dir,
    or ``None`` when it would escape ``impl_root`` — the caller must then
    refuse to run, since the cleanup actions delete files destructively.
    """
    run_dir = Path(run_dir_arg).resolve()
    if not run_dir.is_relative_to(impl_root.resolve()):
        return None
    return run_dir


def _list_bulk_run_dirs(impl_root: Path) -> list[Path]:
    """List run directories directly under impl_root for bulk cleanup.

    Returns only real directories that stay inside ``impl_root``. An entry
    that is a symlink resolving outside ``impl_root`` is skipped, so a planted
    symlink cannot lure the destructive cleanup actions into following it and
    deleting files outside the ``larch-logs/implement/`` tree. This applies the
    same containment guard the ``--run-dir`` path uses via
    :func:`_resolve_single_run_dir` (``d.is_dir()`` alone follows symlinks).
    """
    run_dirs: list[Path] = []
    for entry in sorted(impl_root.iterdir()):
        if not entry.is_dir():
            continue
        if _resolve_single_run_dir(run_dir_arg=str(entry), impl_root=impl_root) is None:
            continue
        run_dirs.append(entry)
    return run_dirs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = p.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the cleanup. Without this flag, runs in dry-run mode.",
    )
    _ = p.add_argument(
        "--run-dir",
        metavar="PATH",
        help="Restrict to a single run directory (for spot-checking).",
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    execute = args.execute
    if not execute:
        print("DRY-RUN mode: pass --execute to apply changes")

    repo_root = Path(__file__).resolve().parent.parent
    impl_root = (repo_root / "larch-logs" / "implement").resolve()
    stats = Stats()

    if args.run_dir:
        run_dir = _resolve_single_run_dir(run_dir_arg=args.run_dir, impl_root=impl_root)
        if run_dir is None:
            print(
                f"ERROR: --run-dir must resolve to a path inside {impl_root} "
                f"(got {Path(args.run_dir).resolve()})",
                file=sys.stderr,
            )
            return 1
        run_dirs = [run_dir]
    else:
        if not impl_root.is_dir():
            print(f"ERROR: {impl_root} not found", file=sys.stderr)
            return 1
        run_dirs = _list_bulk_run_dirs(impl_root)

    total = len(run_dirs)
    for i, run_dir in enumerate(run_dirs, 1):
        if i % 100 == 0 or i == total:
            print(f"  [{i}/{total}] {run_dir.name}", flush=True)
        process_run_dir(run_dir=run_dir, execute=execute, stats=stats)

    if not args.run_dir:
        remove_python_larch_logs(repo_root=repo_root, execute=execute, stats=stats)

    print()
    stats.report()
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
