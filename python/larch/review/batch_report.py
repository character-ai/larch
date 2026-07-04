"""Findings processing and batch log flush for the review-and-fix subsystem."""
# ruff: noqa: SIM114, PIE810, PERF401
# pyright: reportUnusedCallResult=false, reportArgumentType=false

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
from pathlib import Path

from larch.report import run_logs
from larch.review import review_pipeline
from larch.review import voting
from larch.review._raf_util import (
    _PY_CLI,
    _append_text,
    _err,
    _read_text,
    _run,
    _write_text,
)
from larch.review.review_types import ReviewCoreStatus, parse_findings_text

_FINDING_RE = re.compile(r"^### FINDING_[0-9]+:")
_SKIPPED_RE = re.compile(r"^SKIPPED:\s*(FINDING_\d+)")
_OOS_HEADING_RE = re.compile(r"^### FINDING_[0-9]+:.*\[(?:OUT_OF_SCOPE|OOS)\]")
_SETTLING_CORE_STATUSES = frozenset({
    ReviewCoreStatus.ok,
    ReviewCoreStatus.fix_required,
    ReviewCoreStatus.cap_reached,
    ReviewCoreStatus.zero_findings,
})


def _skip_ratio_threshold() -> float:
    raw = os.environ.get("LARCH_SKIP_RATIO_THRESHOLD", "")
    if not raw:
        return 0.5
    try:
        value = float(raw)
    except ValueError:
        _err(f"⚠ review-and-fix: invalid LARCH_SKIP_RATIO_THRESHOLD={raw}; using 0.5")
        return 0.5
    if 0 < value < 1:
        return value
    _err(f"⚠ review-and-fix: invalid LARCH_SKIP_RATIO_THRESHOLD={raw}; using 0.5")
    return 0.5


def _core_status_is(core_status: str, *statuses: ReviewCoreStatus) -> bool:
    return ReviewCoreStatus.from_wire(core_status) in statuses


def _reviewer_prune_status_records(core_status: str) -> bool:
    return ReviewCoreStatus.from_wire(core_status) in _SETTLING_CORE_STATUSES


def _clear_reviewer_prune_round(*, ledger: Path, round_num: int, work_dir: Path) -> None:
    if not ledger:
        return
    work_dir.mkdir(parents=True, exist_ok=True)
    empty_manifest = work_dir / "reviewer-prune-clear-empty.ndjson"
    empty_classification = work_dir / "reviewer-prune-clear-classification.tsv"
    _write_text(path=empty_manifest, text="")
    _write_text(path=empty_classification, text="finding_id\treviewer_slots\tvoting_result\n")
    try:
        review_pipeline.reviewer_prune_record(ledger=ledger, round_num=round_num, manifest=empty_manifest, classification=empty_classification)
    except Exception as exc:
        _err(f"WARN: reviewer-prune clear failed for round {round_num}: {exc}")


def _append_round_oos_artifact(*, round_num: int, round_oos: Path, oos_jsonl: Path, oos_markdown: Path) -> None:
    if not round_oos.is_file() or not round_oos.stat().st_size:
        return
    body = _read_text(round_oos)
    record = {"round": round_num, "source": "code-review", "body": body}
    with oos_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    if oos_markdown.is_file() and oos_markdown.stat().st_size:
        _append_text(path=oos_markdown, text="\n")
    _append_text(path=oos_markdown, text=body)
    mirror = oos_markdown.parent / "oos-accepted-review.md"
    shutil.copyfile(oos_markdown, mirror)


def _oos_write_seq(oos_markdown: Path) -> int:
    if not oos_markdown.is_file():
        return 0
    count = 0
    for line in _read_text(oos_markdown).splitlines():
        if line.startswith("### OOS_"):
            count += 1
    return count


def _extract_finding_block(*, text: str, finding_id: str) -> str:
    for finding in parse_findings_text(text, boundary="any_heading"):
        if finding.finding_id == finding_id:
            block = finding.block.rstrip()
            return block + ("\n" if block else "")
    return ""


def _process_skipped_findings(*,
    round_dir: Path,
    in_scope_file: Path,
    coder_log: Path,
    implement_tmpdir: Path,
) -> tuple[int, bool]:
    if not coder_log.is_file() or not in_scope_file.is_file():
        return 0, False
    text = _read_text(coder_log)
    skip_ids = list(dict.fromkeys(_SKIPPED_RE.findall(text)))
    if not skip_ids:
        return 0, False
    skipped_file = round_dir / "skipped-findings.md"
    skipped_security_file = round_dir / "skipped-findings.security.md"
    _write_text(path=skipped_file, text="")
    _write_text(path=skipped_security_file, text="")
    oos_jsonl = implement_tmpdir / "accumulated-oos.jsonl"
    oos_markdown = implement_tmpdir / "accumulated-oos.md"
    oos_seq = _oos_write_seq(oos_markdown)
    in_scope_text = _read_text(in_scope_file)
    skipped_count = 0
    for skip_id in skip_ids:
        block = _extract_finding_block(text=in_scope_text, finding_id=skip_id)
        if not block.strip():
            continue
        block_file = round_dir / f"{skip_id}.skipped.md"
        _write_text(path=block_file, text=block)
        try:
            sec_rc = 0 if voting.is_security_block(block_file) else 1
        except SystemExit:
            return skipped_count, True
        if sec_rc == 0:
            _append_text(path=skipped_security_file, text=block + "\n")
        else:
            oos_seq += 1
            result = _run([
                "python3", str(_PY_CLI), "oos", "normalize-header",
                "--seq", str(oos_seq),
                "--block-file", str(block_file),
            ])
            if result.returncode != 0:
                return skipped_count, True
            _append_text(path=skipped_file, text=result.stdout)
            if not result.stdout.endswith("\n"):
                _append_text(path=skipped_file, text="\n")
        skipped_count += 1
    if skipped_file.stat().st_size:
        _append_round_oos_artifact(round_num=int(round_dir.name.split("-", 1)[1]), round_oos=skipped_file, oos_jsonl=oos_jsonl, oos_markdown=oos_markdown)
    if skipped_security_file.stat().st_size:
        security_audit_file = implement_tmpdir / "skipped-security-findings.md"
        if security_audit_file.is_file() and security_audit_file.stat().st_size:
            _append_text(path=security_audit_file, text="\n")
        _append_text(path=security_audit_file, text=_read_text(skipped_security_file))
    return skipped_count, False


def _compose_review_findings_output(*, impl_tmpdir: Path, output: Path) -> bool:
    design_dir = impl_tmpdir / "design-export"
    args = ["--implement-tmpdir", str(impl_tmpdir), "--issue", "0", "--output", str(output)]
    if design_dir.is_dir():
        args = ["--design-artifacts-dir", str(design_dir), *args]
    result = _run(["python3", str(_PY_CLI), "review", "compose-findings", *args])
    return result.returncode == 0 and output.is_file()


def _count_code_review_findings(findings_file: Path) -> tuple[int, int, bool]:
    if not findings_file.is_file():
        return 0, 0, False
    try:
        text = _read_text(findings_file)
    except OSError:
        return 0, 0, False
    accepted = rejected = 0
    seen_code_review = False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("phase") != "code-review":
            continue
        seen_code_review = True
        if record.get("outcome") == "accepted":
            accepted += 1
        elif record.get("outcome") == "rejected":
            rejected += 1
    return accepted, rejected, seen_code_review


def _derive_code_review_tally(findings_file: Path) -> tuple[int, int]:
    accepted, rejected, _seen_code_review = _count_code_review_findings(findings_file)
    return accepted, rejected


def _tally_flush_sidecar_text(result: object) -> str:
    return (
        f"voting write-tally failed (returncode={getattr(result, 'returncode', '')})\n"
        "--- stderr ---\n"
        f"{getattr(result, 'stderr', '') or ''}"
        "\n--- stdout ---\n"
        f"{getattr(result, 'stdout', '') or ''}"
        "\n"
    )


def observe_code_review_tally_flush(*, impl_tmpdir: Path, run_id: str, result: object) -> None:
    sidecar = impl_tmpdir / "code-review-tally.flush.err"
    run_root = impl_tmpdir / "larch-logs" / "implement" / run_id
    run_root_sidecar = run_root / "code-review-tally.flush.err"
    if getattr(result, "returncode", 0) == 0:
        with contextlib.suppress(FileNotFoundError):
            sidecar.unlink()
        with contextlib.suppress(FileNotFoundError):
            run_root_sidecar.unlink()
        return

    content = _tally_flush_sidecar_text(result)
    with contextlib.suppress(OSError):
        _write_text(path=sidecar, text=content)
    with contextlib.suppress(OSError):
        run_root.mkdir(parents=True, exist_ok=True)
        _write_text(path=run_root_sidecar, text=content)
    rel_sidecar = f"larch-logs/implement/{run_id}/code-review-tally.flush.err"
    entry = (
        "\n## Larch-log batch — `code-review-tally` write failed\n\n"
        f"`voting write-tally` exited with rc={getattr(result, 'returncode', '')}. "
        f"See `{rel_sidecar}` for stderr/stdout.\n"
    )
    with contextlib.suppress(OSError):
        run_logs.append_execution_issue(log_file=impl_tmpdir / "execution-issues.md", category="Warnings", entry=entry)


def _sorted_round_dirs(impl_tmpdir: Path) -> list[tuple[int, Path]]:
    rounds: list[tuple[int, Path]] = []
    for path in impl_tmpdir.glob("round-*"):
        if path.is_dir() and re.fullmatch(r"round-\d+", path.name):
            rounds.append((int(path.name.split("-", 1)[1]), path))
    rounds.sort(key=lambda item: item[0])
    return rounds


def _rejected_body_start_line(text: str) -> int:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines) or lines[idx].strip() != "# Rejected Findings":
        return 1
    idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines):
        return 2
    return idx + 1


def write_rejected_findings_aggregate(*, impl_tmpdir: Path, fallback_file: Path | None = None) -> None:
    if not impl_tmpdir.is_dir():
        raise ValueError(f"implement tmpdir not a directory: {impl_tmpdir}")
    output_file = impl_tmpdir / "rejected-findings.md"
    round_dirs = _sorted_round_dirs(impl_tmpdir)
    any_full = any((round_dir / "rejected-findings-full.md").is_file() and (round_dir / "rejected-findings-full.md").stat().st_size for _, round_dir in round_dirs)
    if not any_full:
        if fallback_file and fallback_file.is_file():
            shutil.copyfile(fallback_file, output_file)
        else:
            with contextlib.suppress(FileNotFoundError):
                output_file.unlink()
        return
    parts: list[str] = []
    for round_num, round_dir in round_dirs:
        full_file = round_dir / "rejected-findings-full.md"
        compact_file = round_dir / "rejected-findings.md"
        if full_file.is_file() and full_file.stat().st_size:
            round_file = full_file
        elif compact_file.is_file() and compact_file.stat().st_size:
            round_file = compact_file
        else:
            continue
        if not parts:
            parts.append("# Rejected Findings\n\n")
        body_start = _rejected_body_start_line(_read_text(round_file))
        body_lines = _read_text(round_file).splitlines()[body_start - 1:]
        parts.append(f"# Review Round {round_num}\n\n")
        parts.extend(line + "\n" for line in body_lines)
        parts.append("\n")
    if parts:
        _write_text(path=output_file, text="".join(parts))
    else:
        with contextlib.suppress(FileNotFoundError):
            output_file.unlink()


def _render_rejected_findings_for_tally(path: Path) -> str:
    lines: list[str] = []
    for line in _read_text(path).splitlines():
        if line.startswith("### [") or line.startswith("### FINDING_"):
            lines.append(line)
        elif lines:
            lines.append(line)
    return "\n".join(lines)


def _build_tally_body(*, impl_tmpdir: Path, rounds: int, derived_accepted: int, derived_rejected: int) -> str:
    parts = [f"Rounds: {rounds} | {derived_accepted} accepted, {derived_rejected} rejected\n"]
    summary_skip = re.compile(
        r"^- (?:Accepted findings|Rejected findings|Exonerated findings|Neutral findings): |^- \d+ accepted, \d+ rejected \("
    )
    summary_files: list[Path] = []
    root_summary = impl_tmpdir / "review-round-summary.md"
    if root_summary.is_file() and root_summary.stat().st_size:
        summary_files = [root_summary]
    else:
        round_dirs = sorted(
            (p for p in impl_tmpdir.glob("round-*/review-round-summary.md") if p.is_file()),
            key=lambda p: int(p.parent.name.split("-", 1)[1]),
        )
        summary_files = round_dirs
    for summary in summary_files:
        if not summary.is_file() or not summary.stat().st_size:
            continue
        parts.append("\n")
        for line in _read_text(summary).splitlines():
            if not summary_skip.match(line):
                parts.append(line + "\n")
        parts.append("\n")
    for name in ("rejected-findings.md", "rejected-findings-full.md"):
        rejected = impl_tmpdir / name
        if rejected.is_file() and rejected.stat().st_size:
            parts.append("\n## Rejected Code Review Findings\n\n")
            parts.append(_render_rejected_findings_for_tally(rejected))
            parts.append("\n")
            break
    if rounds > 0:
        voting_tally = impl_tmpdir / f"round-{rounds}" / "voting-tally.md"
        if voting_tally.is_file() and voting_tally.stat().st_size:
            parts.append("\n## Voting Tally\n\n")
            parts.append(_read_text(voting_tally))
            parts.append("\n")
    return "".join(parts)


def flush_review_batches(*,
    impl_tmpdir: Path,
    run_id: str,
    rounds: int,
    _accepted: int,
    _rejected: int,
    exonerated: int = 0,
    _neutral: int = 0,
    composed_findings_source: Path | None = None,
) -> bool:
    if not impl_tmpdir.is_dir() or not run_id:
        return True
    batch_input = impl_tmpdir / "larch-log-batches-input"
    batch_input.mkdir(parents=True, exist_ok=True)
    body_file = batch_input / "code-review-tally-body.md"
    findings_file = batch_input / "review-findings-full.jsonl"
    if composed_findings_source and composed_findings_source.is_file() and composed_findings_source.stat().st_size:
        shutil.copyfile(composed_findings_source, findings_file)
    elif not _compose_review_findings_output(impl_tmpdir=impl_tmpdir, output=findings_file):
        _err("⚠ review-and-fix: failed to compose review-findings-full batch; skipping tally flush")
        return True
    derived_accepted, derived_rejected = _derive_code_review_tally(findings_file)
    _write_text(path=body_file, text=_build_tally_body(impl_tmpdir=impl_tmpdir, rounds=rounds, derived_accepted=derived_accepted, derived_rejected=derived_rejected))
    tally_result = _run([
        "python3", str(_PY_CLI), "voting", "write-tally",
        "--log-root", str(impl_tmpdir / "larch-logs"),
        "--skill", "implement",
        "--run-id", run_id,
        "--phase", "code-review",
        "--mode", "hard",
        "--rounds", str(rounds),
        "--accepted", str(derived_accepted),
        "--rejected", str(derived_rejected),
        "--exonerated", str(exonerated),
        "--body-file", str(body_file),
    ])
    observe_code_review_tally_flush(impl_tmpdir=impl_tmpdir, run_id=run_id, result=tally_result)
    if tally_result.returncode != 0:
        _err("⚠ review-and-fix: failed to flush code-review-tally batch")
        if tally_result.stderr:
            _err(tally_result.stderr.rstrip())
    findings_err = impl_tmpdir / "review-findings-full.flush.err"
    findings_flush = _run([
        "python3", str(_PY_CLI), "run-log", "write",
        "--log-root", str(impl_tmpdir / "larch-logs"),
        "--skill", "implement",
        "--run-id", run_id,
        "--batch", "review-findings-full",
        "--input-file", str(findings_file),
    ])
    if findings_flush.returncode != 0:
        _err(f"⚠ review-and-fix: run-log write review-findings-full failed (rc={findings_flush.returncode})")
        _write_text(path=findings_err, text=findings_flush.stderr + findings_flush.stdout)
    else:
        with contextlib.suppress(FileNotFoundError):
            findings_err.unlink()
    ledger = impl_tmpdir / "reviewer-prune-ledger.tsv"
    if ledger.is_file():
        ledger_err = impl_tmpdir / "reviewer-prune-ledger.flush.err"
        ledger_flush = _run([
            "python3", str(_PY_CLI), "run-log", "write",
            "--log-root", str(impl_tmpdir / "larch-logs"),
            "--skill", "implement",
            "--run-id", run_id,
            "--batch", "reviewer-prune-ledger",
            "--input-file", str(ledger),
        ])
        if ledger_flush.returncode != 0:
            _err(f"⚠ review-and-fix: run-log write reviewer-prune-ledger failed (rc={ledger_flush.returncode})")
            _write_text(path=ledger_err, text=ledger_flush.stderr + ledger_flush.stdout)
        else:
            with contextlib.suppress(FileNotFoundError):
                ledger_err.unlink()
    return tally_result.returncode == 0


def _append_scout_flush_warning(*, implement_tmpdir: Path, round_num: int, detail: str, label: str) -> None:
    entry = (
        f"\n## Larch-log batch — `review-scout-manifest` {label} (round {round_num})\n\n"
        f"{detail.rstrip()}\n"
    )
    with contextlib.suppress(OSError):
        run_logs.append_execution_issue(log_file=implement_tmpdir / "execution-issues.md", category="Warnings", entry=entry)


def flush_scout_manifest(*,
    implement_tmpdir: Path,
    run_id: str,
    round_num: int,
    round_dir: Path,
    core: dict[str, str],
) -> None:
    if not implement_tmpdir.is_dir() or not run_id:
        return
    scout_status = core.get("SCOUT_STATUS", "na") or "na"
    if scout_status == "na":
        return
    scout_payload = round_dir / ".scout-payload.json"
    scout_flush_err = round_dir / "review-and-fix-scout-flush.log"
    with contextlib.suppress(FileNotFoundError):
        scout_payload.unlink()
        scout_flush_err.unlink()
    manifest_basename = Path(core["SCOUT_MANIFEST"]).name if core.get("SCOUT_MANIFEST") else ""
    yield_tsv_basename = Path(core["YIELD_TSV_FILE"]).name if core.get("YIELD_TSV_FILE") else ""
    dynamic_slots_raw = core.get("DYNAMIC_SLOTS", "0") or "0"
    if not dynamic_slots_raw.isdigit():
        msg = f"invalid DYNAMIC_SLOTS for review-scout-manifest payload: {dynamic_slots_raw or '<empty>'}"
        _write_text(path=scout_flush_err, text=msg + "\n")
        _append_scout_flush_warning(implement_tmpdir=implement_tmpdir, round_num=round_num, detail=msg, label="payload validation")
        return
    payload = {
        "status": scout_status,
        "dynamic_slots": int(dynamic_slots_raw),
        "manifest_basename": manifest_basename,
        "yield_tsv_basename": yield_tsv_basename,
    }
    try:
        _write_text(path=scout_payload, text=json.dumps(payload, separators=(",", ":")) + "\n")
    except OSError as exc:
        msg = f"review-scout-manifest payload build failed: {exc}"
        _write_text(path=scout_flush_err, text=msg + "\n")
        _append_scout_flush_warning(implement_tmpdir=implement_tmpdir, round_num=round_num, detail=msg, label="payload build")
        return
    if not scout_payload.is_file() or not scout_payload.stat().st_size:
        return
    result = _run([
        "python3", str(_PY_CLI), "run-log", "write",
        "--log-root", str(implement_tmpdir / "larch-logs"),
        "--skill", "implement",
        "--run-id", run_id,
        "--batch", "review-scout-manifest",
        "--input-file", str(scout_payload),
    ])
    with contextlib.suppress(FileNotFoundError):
        scout_payload.unlink()
    if result.returncode != 0:
        _write_text(path=scout_flush_err, text=result.stderr + result.stdout)
        _append_scout_flush_warning(
            implement_tmpdir=implement_tmpdir,
            round_num=round_num,
            detail=f"run-log write review-scout-manifest failed (rc={result.returncode})",
            label="run-log write"
        )
    else:
        with contextlib.suppress(FileNotFoundError):
            scout_flush_err.unlink()


def flush_round_log_after_coder(*, impl_tmpdir: Path, run_id: str, round_num: int, round_dir: Path) -> None:
    if not impl_tmpdir.is_dir() or not run_id or round_num <= 0 or not round_dir.is_dir():
        return
    flush_err = round_dir / "review-and-fix-write-round.log"
    result = _run([
        "python3", str(_PY_CLI), "run-log", "write-round",
        "--log-root", str(impl_tmpdir / "larch-logs"),
        "--skill", "implement",
        "--run-id", run_id,
        "--round", str(round_num),
        "--source-dir", str(round_dir),
    ])
    if result.returncode != 0:
        _err(f"⚠ review-and-fix: late round log flush failed (round {round_num}, rc={result.returncode})")
        _write_text(path=flush_err, text=result.stderr + result.stdout)
    else:
        with contextlib.suppress(FileNotFoundError):
            flush_err.unlink()
# pyright: reportPrivateUsage=false, reportUnusedFunction=false
