#!/usr/bin/env python3
"""cleanup-implement-logs.py — retroactive log cleanup for larch-logs/implement/.

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
  python3 scripts/cleanup-implement-logs.py

  # execute for real
  python3 scripts/cleanup-implement-logs.py --execute

  # restrict to a single run dir (for spot-checking)
  python3 scripts/cleanup-implement-logs.py --run-dir larch-logs/implement/<UUID> --execute

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
from pathlib import Path

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

def _delete(path: Path, execute: bool, stats_attr: str, stats: Stats) -> None:
    """Delete path and its sidecar files (.meta, .json) when they exist."""
    targets = [path]
    for ext in _SIDECAR_EXTS:
        sidecar = path.parent / (path.name + ext)
        if sidecar.exists() and sidecar != path:
            targets.append(sidecar)
    for t in targets:
        if execute:
            try:
                t.unlink()
            except OSError as exc:
                stats.errors.append(f"unlink {t}: {exc}")
                return
        setattr(stats, stats_attr, getattr(stats, stats_attr) + 1)


# ---------------------------------------------------------------------------
# Action 1: Delete dyn-*-prompt.md
# ---------------------------------------------------------------------------

def delete_dyn_prompts(run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in run_dir.rglob("dyn-*-prompt.md"):
        _delete(p, execute, "dyn_prompt_deleted", stats)


# ---------------------------------------------------------------------------
# Action 2: Delete aggregator-output.txt when byte-identical to findings.md
# ---------------------------------------------------------------------------

def delete_identical_aggregator(run_dir: Path, execute: bool, stats: Stats) -> None:
    for agg in run_dir.rglob("aggregator-output.txt"):
        findings = agg.parent / "findings.md"
        if not findings.is_file():
            continue
        if filecmp.cmp(str(agg), str(findings), shallow=False):
            _delete(agg, execute, "aggregator_deleted", stats)


# ---------------------------------------------------------------------------
# Action 3: Delete scout-round*-manifest.json.raw
# ---------------------------------------------------------------------------

def delete_raw_manifests(run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in run_dir.rglob("scout-round*-manifest.json.raw"):
        _delete(p, execute, "raw_manifest_deleted", stats)


# ---------------------------------------------------------------------------
# Action 4: Delete refresh sidecars
# ---------------------------------------------------------------------------

_REFRESH_NAMES = {
    "token-report-refresh.json",
    "timing-report-refresh.json",
}

def delete_refresh_sidecars(run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in run_dir.rglob("*"):
        name = p.name
        if name in _REFRESH_NAMES:
            _delete(p, execute, "refresh_deleted", stats)
        elif p.is_file() and name.startswith("session-transcript-refresh."):
            _delete(p, execute, "refresh_deleted", stats)


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


def delete_cursor_phase_retry(run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in run_dir.rglob("cursor-specialist-*-output-*.txt"):
        if _is_cursor_phase_retry(p.name):
            _delete(p, execute, "cursor_phase_retry_deleted", stats)


# ---------------------------------------------------------------------------
# Action 6: Upgrade session-transcript.jsonl v1 → v2
# ---------------------------------------------------------------------------

def _upgrade_transcript(path: Path, execute: bool, stats: Stats) -> None:
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
        header = json.loads(lines[0])
    except json.JSONDecodeError:
        stats.errors.append(f"header parse failed: {path}")
        return

    if header.get("v", 1) >= 2:
        return  # Already v2 — skip

    out_lines: list[str] = []
    header["v"] = 2
    out_lines.append(json.dumps(header, ensure_ascii=False, separators=(",", ":")))

    for line in lines[1:]:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            out_lines.append(line)
            continue

        if rec.get("role") == "assistant":
            new_blocks = []
            for blk in rec.get("blocks", []):
                if blk.get("type") != "tool_call":
                    new_blocks.append(blk)
                    continue
                name = blk.get("name", "")
                inp = blk.get("input")

                if inp and "elided_input_bytes" not in blk and "input_bytes" not in inp:
                    if name in STUB_INPUT_TOOLS:
                        # Stub Edit/Write/NotebookEdit: preserve file_path, record byte count
                        file_path = (
                            inp.get("file_path")
                            or inp.get("notebook_path")
                            or inp.get("path")
                            or ""
                        )
                        input_bytes = len(json.dumps(inp, ensure_ascii=False))
                        new_blk = dict(blk)
                        new_blk["input"] = {"file_path": file_path, "input_bytes": input_bytes}
                        new_blocks.append(new_blk)
                        continue
                    else:
                        # Elide large inputs for other tools
                        serialized = json.dumps(inp, ensure_ascii=False)
                        if len(serialized) > INPUT_CAP_BYTES:
                            new_blk = {k: v for k, v in blk.items() if k != "input"}
                            new_blk["elided_input_bytes"] = len(serialized)
                            new_blocks.append(new_blk)
                            continue

                new_blocks.append(blk)

            new_rec = dict(rec)
            new_rec["blocks"] = new_blocks
            out_lines.append(json.dumps(new_rec, ensure_ascii=False, separators=(",", ":")))
        else:
            out_lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))

    if execute:
        try:
            path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            stats.errors.append(f"write {path}: {exc}")
            return

    stats.transcript_upgraded += 1


def upgrade_transcripts(run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in run_dir.rglob("session-transcript.jsonl"):
        _upgrade_transcript(p, execute, stats)


# ---------------------------------------------------------------------------
# Action 7: Consolidate breadcrumbs/larch-quiet-*.log → breadcrumbs/quiet.log
# ---------------------------------------------------------------------------

def consolidate_breadcrumbs(run_dir: Path, execute: bool, stats: Stats) -> None:
    bc_dir = run_dir / "breadcrumbs"
    if not bc_dir.is_dir():
        return

    quiet_log = bc_dir / "quiet.log"
    # Skip if quiet.log already exists (Phase 1 already ran for this run dir)
    if quiet_log.exists():
        return

    individual = sorted(bc_dir.glob("larch-quiet-*.log"))
    if not individual:
        return

    if execute:
        parts: list[str] = []
        for f in individual:
            parts.append(f"=== {f.name} ===\n")
            try:
                parts.append(f.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                parts.append("")
        try:
            quiet_log.write_text("".join(parts), encoding="utf-8")
        except OSError as exc:
            stats.errors.append(f"write {quiet_log}: {exc}")
            return

        for f in individual:
            try:
                f.unlink()
            except OSError as exc:
                stats.errors.append(f"unlink {f}: {exc}")

    stats.breadcrumbs_consolidated += 1
    stats.breadcrumb_files_removed += len(individual)


# ---------------------------------------------------------------------------
# Action 8: Drop 'body' field from code-review-tally.json
# ---------------------------------------------------------------------------

def strip_tally_body(run_dir: Path, execute: bool, stats: Stats) -> None:
    for p in run_dir.glob("code-review-tally.json"):
        try:
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            stats.errors.append(f"read/parse {p}: {exc}")
            continue

        modified = False
        if isinstance(data, list):
            for rec in data:
                if isinstance(rec, dict) and "body" in rec:
                    del rec["body"]
                    modified = True
        elif isinstance(data, dict) and "body" in data:
            del data["body"]
            modified = True

        if modified:
            if execute:
                try:
                    p.write_text(
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

def remove_python_larch_logs(repo_root: Path, execute: bool, stats: Stats) -> None:
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

def process_run_dir(run_dir: Path, execute: bool, stats: Stats) -> None:
    delete_dyn_prompts(run_dir, execute, stats)
    delete_identical_aggregator(run_dir, execute, stats)
    delete_raw_manifests(run_dir, execute, stats)
    delete_refresh_sidecars(run_dir, execute, stats)
    delete_cursor_phase_retry(run_dir, execute, stats)
    upgrade_transcripts(run_dir, execute, stats)
    consolidate_breadcrumbs(run_dir, execute, stats)
    strip_tally_body(run_dir, execute, stats)


def main() -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the cleanup. Without this flag, runs in dry-run mode.",
    )
    p.add_argument(
        "--run-dir",
        metavar="PATH",
        help="Restrict to a single run directory (for spot-checking).",
    )
    args = p.parse_args()

    execute = args.execute
    if not execute:
        print("DRY-RUN mode — pass --execute to apply changes")

    repo_root = Path(__file__).resolve().parent.parent
    stats = Stats()

    if args.run_dir:
        run_dirs = [Path(args.run_dir).resolve()]
    else:
        impl_root = repo_root / "larch-logs" / "implement"
        if not impl_root.is_dir():
            print(f"ERROR: {impl_root} not found", file=sys.stderr)
            return 1
        run_dirs = sorted(d for d in impl_root.iterdir() if d.is_dir())

    total = len(run_dirs)
    for i, run_dir in enumerate(run_dirs, 1):
        if i % 100 == 0 or i == total:
            print(f"  [{i}/{total}] {run_dir.name}", flush=True)
        process_run_dir(run_dir, execute, stats)

    if not args.run_dir:
        remove_python_larch_logs(repo_root, execute, stats)

    print()
    stats.report()
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
