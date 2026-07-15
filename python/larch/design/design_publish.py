"""Python CLI entrypoint for /design publish."""

from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

from larch import io as larch_io
from larch.report import design_diagram_log
from larch.calibration import difficulty
from larch.core import architectural_guidelines, config, proc
from larch.report import run_logs
from larch.design import design_step0_env, plan_grammar
from larch.design.design_core import capture_contract_stream_to_paths
from larch.design.design_terminal import stage_terminal_state_core
from larch.git.repo_roots import consumer_repo_root


@dataclass(frozen=True)
class TranscriptCaptureContext:
    """Inputs for design-session transcript capture before committed log publish."""

    design_tmpdir: Path
    plugin_root: Path
    session_id: str
    issue: str
    repo: str
    claude_pid: str
    warning_step_label: str


@dataclass(frozen=True)
class GuidelineAssessmentCompleteness:
    guidelines_status: str
    required: bool
    present: bool
    artifact: str
    reason: str


@dataclass(frozen=True)
class InvariantAssessmentCompleteness:
    invariants_status: str
    required: bool
    present: bool
    artifact: str
    reason: str


def _emit_rows(rows: list[tuple[str, str]]) -> None:
    for key, value in rows:
        print(f"{key}={value}")


def _write_result_env(*, path: Path, rows: list[tuple[str, str]]) -> bool:
    try:
        larch_io.write_kvs(path=path, values=rows, atomic=True, create_parent=False, mode=0o600)
    except (OSError, ValueError):
        return False
    return True


def _checkpoint_result_env(*, path: Path, rows: list[tuple[str, str]], phase: str) -> None:
    _replace_kv(rows=rows, key="LATEST_PHASE", value=phase)
    if not _write_result_env(path=path, rows=rows):
        raise OSError(f"publish result checkpoint failed at {phase}")


def _write_bounded_phase_stderr(*, design_tmpdir: Path, filename: str, text: str) -> None:
    data = text.encode("utf-8", errors="replace")[-config.DESIGN_PUBLISH_TAIL_BYTE_CAP :]
    larch_io.atomic_write(
        path=design_tmpdir / filename,
        text=data.decode("utf-8", errors="replace"),
        create_parent=False,
        nofollow=True,
        mode=0o600,
    )


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _replace_kv(*, rows: list[tuple[str, str]], key: str, value: str) -> None:
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx][0] == key:
            rows[idx] = (key, value)
            return
    rows.append((key, value))


def _count_missing_script_defects(log_file: str) -> str:
    path = Path(log_file) if log_file else None
    if path is None or not path.is_file() or path.is_symlink():
        return "0"
    try:
        count = sum(
            1
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if "kind=missing-script" in line
        )
    except OSError:
        return "0"
    return str(count)


def _is_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value))


_TERMINAL_STATUSES_REQUIRING_SENTINEL = frozenset({"complete", "cap-hit"})
_REASON_TOKEN_RE = re.compile(r"REASON_TOKEN=([^ \t);,]+)")


def _read_review_round_count(design_tmpdir: Path) -> int:
    """Return the launched-round count from review-round-count.txt (0 if absent/invalid).

    Mirrors plan_review._read_count. Used as a defense-in-depth fallback by
    review_provenance when a result-env writer omits the round-count keys (#5210).
    """
    path = design_tmpdir / "review-round-count.txt"
    if not path.is_file() or path.is_symlink():
        return 0
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return 0
    return int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0


def _resolve_publish_difficulty_rating(*, design_tmpdir: Path, plan_text: str) -> tuple[difficulty.DifficultyRating | None, bool]:
    raw_path = design_tmpdir / difficulty.DESIGN_RAW_RATING_BASENAME
    raw_present = raw_path.exists() or raw_path.is_symlink()
    if raw_present:
        raw_rating = difficulty.read_rating_file(raw_path)
        if raw_rating is None:
            return None, True
        return raw_rating, False
    tier = difficulty.plan_difficulty(plan_text)
    if not tier:
        return None, False
    try:
        return difficulty.validate_rating_object(
            {
                "predicted_tier": tier,
                "confidence": "medium",
                "rationale": "design plan metadata",
            }
        ), False
    except ValueError:
        return None, False


def _touch_step5b5_sentinel(design_tmpdir: Path) -> None:
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-5b.5").touch()


def _write_diagram_sanitizer_failure(
    *,
    design_tmpdir: Path,
    reason: str,
    exit_code: int | str,
) -> None:
    failure_log = design_tmpdir / "architecture-diagram-sanitizer.failure.log"
    safe_reason = re.sub(r"[^A-Za-z0-9._:-]+", "-", reason).strip("-") or "unknown"
    _ = failure_log.write_text(
        f"reason={safe_reason}\nexit-code={exit_code}\nsite=design Step 5b.5\n",
        encoding="utf-8",
    )
    _ = design_diagram_log.write_bounded_diagram_failure_log(
        design_tmpdir,
        site="design Step 5b.5",
        reason=safe_reason,
        exit_code=exit_code,
        raw_capture_path=failure_log,
    )
    run_logs.append_execution_issue(
        log_file=design_tmpdir / "execution-issues.md",
        category="Warnings",
        entry=design_diagram_log.bounded_diagram_warning_body(
            reason=safe_reason,
            exit_code=exit_code,
        ),
    )


def _skip_diagram_candidate(
    *,
    design_tmpdir: Path,
    reason: str,
    exit_code: int | str,
) -> bool:
    try:
        with contextlib.suppress(OSError):
            (design_tmpdir / "architecture-diagram.md").unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            (design_tmpdir / "architecture-diagram.candidate.md").unlink(missing_ok=True)
        _ = (design_tmpdir / "architecture-diagram.skipped").write_text("", encoding="utf-8")
        _write_diagram_sanitizer_failure(
            design_tmpdir=design_tmpdir,
            reason=reason,
            exit_code=exit_code,
        )
        _touch_step5b5_sentinel(design_tmpdir)
    except OSError:
        return False
    return True


def _sanitize_diagram_candidate(*, design_tmpdir: Path, plugin_root: Path) -> bool:
    """Complete the Step 5b.5 diagram sanitize gate before publishing."""
    sentinel = design_tmpdir / ".completed" / "step-5b.5"
    if sentinel.is_file():
        return True

    candidate = design_tmpdir / "architecture-diagram.candidate.md"
    accepted = design_tmpdir / "architecture-diagram.md"
    skipped = design_tmpdir / "architecture-diagram.skipped"
    failure_log = design_tmpdir / "architecture-diagram-sanitizer.failure.log"
    try:
        if not candidate.is_file() or not os.access(candidate, os.R_OK):
            return _skip_diagram_candidate(
                design_tmpdir=design_tmpdir,
                reason="candidate-missing",
                exit_code=2,
            )

        sanitizer = proc.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "mermaid",
                "sanitize",
                "--input",
                str(candidate),
                "--from-md",
                "--warnings-step",
                "5b.5",
            ],
            check=False,
        )
        sanitizer_output = (sanitizer.stdout or "") + "\n" + (sanitizer.stderr or "")
        status = _parse_kv(sanitizer_output).get("STATUS", "")
        if sanitizer.returncode == 0 and status != "rejected":
            with contextlib.suppress(OSError):
                skipped.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                failure_log.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                (design_tmpdir / "architecture-diagram-generation.failure.log").unlink(missing_ok=True)
            _ = candidate.replace(accepted)
            _touch_step5b5_sentinel(design_tmpdir)
            return True

        match = _REASON_TOKEN_RE.search(sanitizer_output)
        reason_token = match.group(1) if match else "unknown"
        return _skip_diagram_candidate(
            design_tmpdir=design_tmpdir,
            reason=f"sanitizer-rejected:{reason_token}",
            exit_code=sanitizer.returncode,
        )
    except OSError:
        return False
    except BaseException as exc:
        return _skip_diagram_candidate(
            design_tmpdir=design_tmpdir,
            reason=f"sanitizer-exception:{exc.__class__.__name__}",
            exit_code=1,
        )


def review_provenance(design_tmpdir: Path) -> tuple[str, int, bool]:
    """Return (review_status, rounds_completed, provenance_present) from .step3-review-result.env."""
    result_env = design_tmpdir / ".step3-review-result.env"
    if not result_env.is_file() or result_env.is_symlink():
        return "", 0, False
    kv = larch_io.read_kvs(
        result_env,
        duplicate_policy="last",
        errors="replace",
    )
    status = kv.get("STEP3_REVIEW_LOOP_STATUS", "")
    if not status:
        loop = kv.get("LOOP_STATUS", "")
        tally = kv.get("TALLY_PLAN_REVIEW_STATUS", "")
        if loop == "complete":
            status = "complete"
        elif loop in {"cap-reached", "cap-hit"}:
            status = "cap-hit"
        elif loop in {
            "panel-failed", "panel-init-failed", "panel-skipped",
            "tally-error", "degraded-empty-collector",
            "main-agent-vote-required", "postplan-failed",
        }:
            status = loop
        elif tally:
            status = tally
    rounds_raw = kv.get("ROUNDS_COMPLETED", "") or kv.get("REVIEW_ROUND_COUNT", "")
    try:
        rounds = int(rounds_raw) if rounds_raw.strip().isdigit() else 0
    except (ValueError, AttributeError):
        rounds = 0
    if not rounds_raw.strip():
        # #5210 defense-in-depth: when a result-env writer omits both ROUNDS_COMPLETED
        # and REVIEW_ROUND_COUNT, recover the launched-round count from the durable
        # review-round-count.txt so a cleanly-reviewed plan is not refused as rounds=0.
        rounds = _read_review_round_count(design_tmpdir)
    provenance_present = bool(status or rounds_raw.strip())
    return status, rounds, provenance_present


def _splice_plan_provenance(*, text: str, review_status: str, rounds_completed: int) -> str:
    """Insert or replace review provenance above optional size trailers and before diff_lines."""
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] = lines[-1] + "\n"
    trailers = plan_grammar.parse_final_trailers("".join(lines), require_diff_lines=True)
    if not trailers.matches:
        return text
    trailer_start = trailers.start_line - 1
    diff_idx = trailer_start + len(trailers.matches) - 1
    difficulty_match = trailers.get("difficulty")
    provenance = [
        f"review_status: {review_status}\n",
        f"rounds_completed: {rounds_completed}\n",
    ]
    if difficulty_match is not None:
        provenance.append(f"difficulty: {difficulty_match.value}\n")
    optional_lines = [
        lines[trailer_start + idx]
        for idx, match in enumerate(trailers.matches)
        if match.key in plan_grammar.OPTIONAL_SIZE_TRAILER_KEYS
    ]
    return (
        "".join(lines[:trailer_start])
        + "".join(provenance)
        + "".join(optional_lines)
        + "".join(lines[diff_idx:])
    )


def _check_publish_plan_size(*, design_tmpdir: Path, plugin_root: Path) -> tuple[bool, str]:
    plan = design_tmpdir / "plan.txt"
    # lint-subprocess-via-runner: ok publish tail probes the sibling CLI contract exactly.
    check_size = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "plan",
            "check-size",
            "--design-tmpdir",
            str(design_tmpdir),
            "--plan-file",
            str(plan),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LARCH_QUIET_DISABLE": "1"},
    )
    size_kv = _parse_kv((check_size.stdout or "") + "\n" + (check_size.stderr or ""))
    if check_size.returncode != 0 or size_kv.get("PLAN_SIZE_STATUS", "") != "ok":
        return False, "size-check-failed"
    size_trigger_fired = size_kv.get("SIZE_TRIGGER_FIRED", "")
    if size_trigger_fired not in {"true", "false"}:
        return False, "size-check-failed"
    if size_trigger_fired == "true":
        return False, "oversize-no-override"
    return True, ""


def _refresh_composed_plan_md(*, design_tmpdir: Path) -> None:
    plan_txt = design_tmpdir / "plan.txt"
    if not plan_txt.is_file() or plan_txt.stat().st_size == 0:
        return
    composed_plan = design_tmpdir / "composed-plan.md"
    with contextlib.suppress(OSError):
        composed_plan.unlink()
    from larch.design import design_step5c  # noqa: PLC0415 - circular import: design_step5c imports publish_core at its call site too

    design_step5c._auto_compose_plan_md(design_tmpdir)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001 - sibling module private helper, no public API exists


def _publish_refusal_reason(*, design_tmpdir: Path, plugin_root: Path, blocked_reason: str) -> str:
    if blocked_reason:
        return f"review-provenance:{blocked_reason}"
    size_ok, size_refusal = _check_publish_plan_size(design_tmpdir=design_tmpdir, plugin_root=plugin_root)
    if not size_ok:
        return f"plan-size:{size_refusal}"
    return ""


def _emit_publish_refusal(*, reason: str, kvs: list[tuple[str, str]], result_env: Path) -> None:
    if reason.startswith("plan-size:"):
        size_refusal = reason.removeprefix("plan-size:")
        print(
            f"**⚠ 5c: publish refused: plan-size guardrail returned {size_refusal};"
            " decompose, override, or retry /design after repair**",
            flush=True,
        )
        _replace_kv(rows=kvs, key="PUBLISH_REFUSE_REASON", value=size_refusal)
    else:
        blocked_reason = reason.removeprefix("review-provenance:")
        print(
            f"**⚠ 5c: publish refused: review provenance indicates {blocked_reason};"
            " plan review did not complete; re-run /design**",
            flush=True,
        )
        _replace_kv(rows=kvs, key="PUBLISH_REFUSE_REASON", value=reason)
    _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="defects-found")
    _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value="1")
    _emit_rows(kvs)
    _ = _write_result_env(path=result_env, rows=kvs)


def check_invariant_assessment_completeness(
    *,
    design_tmpdir: Path,
    repo_root: Path,
    outcome: str = "approved",
) -> InvariantAssessmentCompleteness:
    invariants = architectural_guidelines.read_invariants(repo_root=repo_root)
    artifact = architectural_guidelines.INVARIANT_DESIGN_ASSESSMENT
    required = (
        outcome in {"approved", "approved-partition"}
        and invariants.status == "present"
        and bool(invariants.content.strip())
    )
    path = design_tmpdir / artifact
    present = path.is_file() and not path.is_symlink()
    if not required:
        reason = (
            "outcome-not-approved"
            if outcome not in {"approved", "approved-partition"}
            else f"invariants-{invariants.status}"
        )
        if invariants.status == "present" and not invariants.content.strip():
            reason = "invariants-empty"
    elif present:
        reason = "present"
    elif path.is_symlink():
        reason = "artifact-symlink"
    elif path.exists():
        reason = "artifact-not-regular"
    else:
        reason = "artifact-missing"
    return InvariantAssessmentCompleteness(
        invariants_status=invariants.status,
        required=required,
        present=present,
        artifact=artifact,
        reason=reason,
    )


def check_guideline_assessment_completeness(
    *,
    design_tmpdir: Path,
    repo_root: Path,
    outcome: str = "approved",
) -> GuidelineAssessmentCompleteness:
    guidelines = architectural_guidelines.read_guidelines(repo_root=repo_root)
    artifact = architectural_guidelines.DESIGN_ASSESSMENT
    required = outcome in {"approved", "approved-partition"} and guidelines.status == "present"
    path = design_tmpdir / artifact
    present = path.is_file() and not path.is_symlink()
    if not required:
        reason = "outcome-not-approved" if outcome not in {"approved", "approved-partition"} else f"guidelines-{guidelines.status}"
    elif present:
        reason = "present"
    elif path.is_symlink():
        reason = "artifact-symlink"
    elif path.exists():
        reason = "artifact-not-regular"
    else:
        reason = "artifact-missing"
    return GuidelineAssessmentCompleteness(
        guidelines_status=guidelines.status,
        required=required,
        present=present,
        artifact=artifact,
        reason=reason,
    )


def _emit_missing_invariant_assessment_refusal(
    *,
    design_tmpdir: Path,
    result: InvariantAssessmentCompleteness,
    kvs: list[tuple[str, str]],
    result_env: Path,
) -> None:
    del design_tmpdir
    print(
        "**⚠ 5c: publish refused: missing architectural-invariant-assessment.md; "
        "return to Gate C to persist the architectural-invariant assessment before publish.**",
        flush=True,
    )
    _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="not-run")
    _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value="0")
    _replace_kv(rows=kvs, key="VALIDATE_LOG_FILE", value="")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_REQUIRED", value="true")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_PRESENT", value="false")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_STATUS", value="missing")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_ARTIFACT", value=result.artifact)
    _replace_kv(rows=kvs, key="PUBLISH_REFUSE_REASON", value="missing-invariant-assessment")
    _emit_rows(kvs)
    _ = _write_result_env(path=result_env, rows=kvs)


def _emit_missing_guideline_assessment_refusal(
    *,
    design_tmpdir: Path,
    result: GuidelineAssessmentCompleteness,
    kvs: list[tuple[str, str]],
    result_env: Path,
) -> None:
    del design_tmpdir
    print(
        "**⚠ 5c: publish refused: missing architectural-guideline-assessment.md; "
        "return to Gate C to persist the architectural-guideline assessment before publish.**",
        flush=True,
    )
    _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="not-run")
    _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value="0")
    _replace_kv(rows=kvs, key="VALIDATE_LOG_FILE", value="")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_REQUIRED", value="true")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_PRESENT", value="false")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_STATUS", value="missing")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_ARTIFACT", value=result.artifact)
    _replace_kv(rows=kvs, key="PUBLISH_REFUSE_REASON", value="missing-guideline-assessment")
    _emit_rows(kvs)
    _ = _write_result_env(path=result_env, rows=kvs)




def _persisted_note_publishable(*, path: Path, kind: architectural_guidelines.AssessmentKind) -> bool:
    """Classify a present, regular assessment note for the Gate C publish gate.

    Invariants publish only when the note classifies clean; a violation note fails
    closed. Guidelines publish when the note is clean, or a deviation carrying
    exactly one validated documented-exception (the fence-aware shared helper);
    a bare or malformed deviation fails closed. An unreadable note fails closed.
    """
    try:
        note = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    classification = architectural_guidelines.classify_note_for_kind(note, kind=kind)
    if classification == config.ASSESSMENT_OUTCOME_CLEAN:
        return True
    if kind.is_invariant:
        return False
    return architectural_guidelines.guideline_exception_valid(note)


def _emit_invariant_violation_refusal(
    *,
    result: InvariantAssessmentCompleteness,
    kvs: list[tuple[str, str]],
    result_env: Path,
) -> None:
    print(
        "**⚠ 5c: publish refused: architectural-invariant-assessment.md records a violation; "
        "return to Gate C to resolve the invariant violation before publish.**",
        flush=True,
    )
    _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="not-run")
    _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value="0")
    _replace_kv(rows=kvs, key="VALIDATE_LOG_FILE", value="")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_REQUIRED", value="true")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_PRESENT", value="true")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_STATUS", value="violation")
    _replace_kv(rows=kvs, key="ARCH_INVARIANT_ASSESSMENT_ARTIFACT", value=result.artifact)
    _replace_kv(rows=kvs, key="PUBLISH_REFUSE_REASON", value="invariant-violation")
    _emit_rows(kvs)
    _ = _write_result_env(path=result_env, rows=kvs)


def _emit_invalid_guideline_deviation_refusal(
    *,
    result: GuidelineAssessmentCompleteness,
    kvs: list[tuple[str, str]],
    result_env: Path,
) -> None:
    print(
        "**⚠ 5c: publish refused: architectural-guideline-assessment.md records a guideline deviation "
        "without a documented exception; return to Gate C to fix the plan or record an exception before publish.**",
        flush=True,
    )
    _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="not-run")
    _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value="0")
    _replace_kv(rows=kvs, key="VALIDATE_LOG_FILE", value="")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_REQUIRED", value="true")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_PRESENT", value="true")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_STATUS", value="deviation")
    _replace_kv(rows=kvs, key="ARCH_GUIDE_ASSESSMENT_ARTIFACT", value=result.artifact)
    _replace_kv(rows=kvs, key="PUBLISH_REFUSE_REASON", value="invalid-guideline-deviation")
    _emit_rows(kvs)
    _ = _write_result_env(path=result_env, rows=kvs)


def _append_transcript_warning(*, design_tmpdir: Path, warning_step_label: str, status: str, message: str) -> None:
    run_logs.append_execution_issue(
        log_file=design_tmpdir / "execution-issues.md",
        category="Warnings",
        entry=f"design Step {warning_step_label} session-transcript {status}: {message}",
    )


def _remove_root_transcript(*, design_tmpdir: Path, warning_step_label: str) -> bool:
    root_transcript = design_tmpdir / "session-transcript.jsonl"
    try:
        if root_transcript.exists() or root_transcript.is_symlink():
            root_transcript.unlink()
    except OSError as exc:
        _append_transcript_warning(
            design_tmpdir=design_tmpdir,
            warning_step_label=warning_step_label,
            status="stale-root-removal-failed",
            message=f"could not remove stale root transcript before publish: {exc}",
        )
        return False
    return True


def _snapshot_has_transcript_source(snapshot: Path) -> bool:
    try:
        data = _parse_kv(snapshot.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False
    if not (data.get("TRANSCRIPT_PATH") and data.get("SESSION_DIR") and data.get("SESSION_UUID")):
        return False
    try:
        return Path(data["TRANSCRIPT_PATH"]).is_file()
    except OSError:
        return False


def _reuse_cached_claude_source_snapshot(*, snapshot: Path) -> Path | None:
    try:
        if snapshot.is_file() and snapshot.stat().st_size > 0:
            if _snapshot_has_transcript_source(snapshot):
                return snapshot
            with contextlib.suppress(OSError):
                snapshot.unlink()
    except OSError:
        return None
    return None


def _fetch_claude_source_snapshot(
    *,
    design_tmpdir: Path,
    plugin_root: Path,
    snapshot: Path,
    warning_step_label: str,
) -> Path | None:
    result = proc.run(
        [sys.executable, str(plugin_root / "python" / "cli.py"), "token", "claude-source"],
    )
    if result.returncode != 0 or "TRANSCRIPT_PATH=" not in result.stdout:
        _append_transcript_warning(
            design_tmpdir=design_tmpdir,
            warning_step_label=warning_step_label,
            status="snapshot-skipped",
            message="Claude source snapshot materialization failed; transcript capture skipped.",
        )
        return None
    try:
        larch_io.atomic_write(snapshot, result.stdout, prefix=f".{snapshot.name}.", nofollow=True)
    except OSError as exc:
        _append_transcript_warning(
            design_tmpdir=design_tmpdir,
            warning_step_label=warning_step_label,
            status="snapshot-write-failed",
            message=f"Claude source snapshot write failed; transcript capture skipped: {exc}",
        )
        return None
    return snapshot


def _materialize_claude_source_snapshot(
    *,
    design_tmpdir: Path,
    plugin_root: Path,
    session_id: str,
    warning_step_label: str,
) -> Path | None:
    snapshot = design_tmpdir / "claude-source.env"
    cached = _reuse_cached_claude_source_snapshot(snapshot=snapshot)
    if cached is not None:
        return cached
    if not session_id:
        _append_transcript_warning(
            design_tmpdir=design_tmpdir,
            warning_step_label=warning_step_label,
            status="snapshot-skipped",
            message="SESSION_ID was absent from source-env.sh; transcript capture skipped.",
        )
        return None
    return _fetch_claude_source_snapshot(
        design_tmpdir=design_tmpdir,
        plugin_root=plugin_root,
        snapshot=snapshot,
        warning_step_label=warning_step_label,
    )


def _refresh_design_source_env(*, ctx: TranscriptCaptureContext, source_env: Path, snapshot: Path, session_id: str) -> bool:
    result = proc.run(
        [
            sys.executable,
            str(ctx.plugin_root / "python" / "cli.py"),
            "session",
            "write-design-env",
            "--output",
            str(source_env),
            "--design-tmpdir",
            str(ctx.design_tmpdir),
            "--session-id",
            session_id,
            "--issue-number",
            ctx.issue,
            "--claude-pid",
            ctx.claude_pid,
            "--claude-source-file",
            str(snapshot),
            *(["--repo", ctx.repo] if ctx.repo else []),
        ],
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(ctx.plugin_root)},
    )
    if result.returncode == 0:
        return True
    _append_transcript_warning(
        design_tmpdir=ctx.design_tmpdir,
        warning_step_label=ctx.warning_step_label,
        status="source-env-refresh-failed",
        message="could not persist LARCH_CLAUDE_SOURCE_FILE; continuing with transcript capture.",
    )
    return False


def capture_design_transcript(*, ctx: TranscriptCaptureContext) -> bool:
    """Capture and hoist a design session transcript before committed log publish.

    Returns False only for publish-blocking hygiene failures. Capture skip statuses
    leave the root transcript absent and return True so log publish can continue.
    """
    if not _remove_root_transcript(design_tmpdir=ctx.design_tmpdir, warning_step_label=ctx.warning_step_label):
        return False
    source_env = ctx.design_tmpdir / "source-env.sh"
    source_data = design_step0_env._load_source_env(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        path=source_env,
        allow_keys={"SESSION_ID"},
    )
    source_session_id = source_data.get("SESSION_ID", "")
    if source_session_id and source_session_id != ctx.session_id:
        _append_transcript_warning(
            design_tmpdir=ctx.design_tmpdir,
            warning_step_label=ctx.warning_step_label,
            status="session-id-drift",
            message=(
                "source-env.sh SESSION_ID disagrees with publish --session-id; "
                "transcript capture skipped."
            ),
        )
        return True
    canonical_session_id = ctx.session_id
    snapshot = _materialize_claude_source_snapshot(
        design_tmpdir=ctx.design_tmpdir,
        plugin_root=ctx.plugin_root,
        session_id=canonical_session_id,
        warning_step_label=ctx.warning_step_label,
    )
    if snapshot is None:
        return True
    _ = _refresh_design_source_env(
        ctx=ctx,
        source_env=source_env,
        snapshot=snapshot,
        session_id=canonical_session_id,
    )
    staging_root = ctx.design_tmpdir / "larch-logs"
    capture = proc.run(
        [
            sys.executable,
            str(ctx.plugin_root / "python" / "cli.py"),
            "run-log",
            "capture-transcript",
            "--source-file",
            str(snapshot),
            "--skill",
            "design",
            "--run-id",
            canonical_session_id,
            "--log-root",
            str(staging_root),
            "--tmpdir",
            str(ctx.design_tmpdir),
            "--defer-commit",
            "true",
            "--execution-issues-log",
            str(ctx.design_tmpdir / "execution-issues.md"),
            "--warning-step-label",
            ctx.warning_step_label,
        ],
    )
    status = ""
    for line in capture.stdout.splitlines():
        if line.startswith("SESSION_TRANSCRIPT_STATUS="):
            print(line)
            status = line.removeprefix("SESSION_TRANSCRIPT_STATUS=")
    root_transcript = ctx.design_tmpdir / "session-transcript.jsonl"
    staged = staging_root / "design" / canonical_session_id / "session-transcript.jsonl"
    if capture.returncode != 0 or status != "captured":
        with contextlib.suppress(OSError):
            root_transcript.unlink(missing_ok=True)
        return True
    try:
        _ = staged.replace(root_transcript)
    except OSError as exc:
        with contextlib.suppress(OSError):
            root_transcript.unlink(missing_ok=True)
        _append_transcript_warning(
            design_tmpdir=ctx.design_tmpdir,
            warning_step_label=ctx.warning_step_label,
            status="hoist-failed",
            message=f"capture succeeded but transcript hoist failed: {exc}",
        )
        return False
    return True


def _run_log_publish_after_capture(
    *,
    ctx: TranscriptCaptureContext,
    kvs: list[tuple[str, str]],
    result_env: Path,
    outcome: str,
    write_result_env_on_publish_failure: bool = True,
) -> int | None:
    # Break the design_publish <-> design_log_publish_flow import cycle at the call site.
    from larch.design import design_log_publish_flow  # noqa: PLC0415 - cycle with design_log_publish_flow

    # Redirect stdout too: the prior subprocess path swallowed log-publish stdout.
    _stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(_stdout_buf), contextlib.redirect_stderr(stderr_buf):
        result = design_log_publish_flow.run_log_publish(
            design_log_publish_flow.LogPublishRequest(
                design_tmpdir=ctx.design_tmpdir,
                run_id=ctx.session_id,
                issue=ctx.issue,
                repo=ctx.repo,
                outcome=outcome,
                plugin_root=ctx.plugin_root,
            )
        )
    _write_bounded_phase_stderr(
        design_tmpdir=ctx.design_tmpdir,
        filename=config.DESIGN_PUBLISH_LOG_STDERR_FILE,
        text=stderr_buf.getvalue(),
    )
    kvs.append(("PUBLISH_OK", "true" if result.publish_ok else "false"))
    if result.pr_number:
        kvs.append(("PR_NUMBER", result.pr_number))
    if result.pr_url:
        kvs.append(("PR_URL", result.pr_url))
    if result.recovery_branch:
        kvs.append(("RECOVERY_BRANCH", result.recovery_branch))
        kvs.append(("LOG_RECOVERY_BRANCH", result.recovery_branch))
    if result.exit_code != 0 and not result.recovery_branch:
        _replace_kv(rows=kvs, key="PUBLISH_OK", value="false")
        if write_result_env_on_publish_failure:
            _emit_rows(kvs)
            try:
                _checkpoint_result_env(path=result_env, rows=kvs, phase="log-publish-failed")
            except OSError as exc:
                print(str(exc), file=sys.stderr)
        return 5
    scrub_violations = result.secret_scrub_violations or "0"
    if scrub_violations.isdigit() and int(scrub_violations) > 0:
        print(
            f"**⚠ SECURITY: redact scrub-log-secrets redacted {scrub_violations} "
            "secret-shaped value(s) from this /design run's logs before flush. "
            "A credential was almost certainly exposed in the session; ROTATE it now "
            "and check chat/PRs for the same value.**",
            flush=True,
        )
    if result.exit_code == 0 and not result.publish_ok:
        if write_result_env_on_publish_failure:
            _emit_rows(kvs)
            return 0 if _write_result_env(path=result_env, rows=kvs) else 3
        return 0
    return None


def _stage_failed_plan_write(
    *,
    design_tmpdir: Path,
    kvs: list[tuple[str, str]],
) -> None:
    """Stage the terminal state before failure reporting and run-log publication."""
    detail_log = design_tmpdir / "design-plan-write.failure.log"
    if not detail_log.is_file():
        _ = detail_log.write_text("named-block write failed\n", encoding="utf-8")
    stdout_log = design_tmpdir / "design-plan-write-stage.stdout.log"
    stderr_log = design_tmpdir / "design-plan-write-stage.stderr.log"
    values = dict(kvs)
    stage_args = [
        "--design-tmpdir",
        str(design_tmpdir),
        "--outcome",
        "failed-plan-write",
        "--step",
        "step5c",
        "--phase",
        "plan-write",
        "--site",
        "design-publish",
        "--trigger",
        "plan-write-failed",
        "--bail-reason",
        "plan-write-failed",
        "--exit-code",
        "1",
        "--source-script",
        "design-publish",
        "--summary-outcome",
        "failed-plan-write",
        "--failure-detail-log",
        str(detail_log),
    ]
    for flag, key in (
        ("--publish-attempt-id", "PUBLISH_ATTEMPT_ID"),
        ("--publish-rc-source", "PUBLISH_RC_SOURCE"),
        ("--latest-phase", "LATEST_PHASE"),
        ("--plan-write-ok", "PLAN_WRITE_OK"),
        ("--publish-ok", "PUBLISH_OK"),
        ("--renamed", "RENAMED"),
        ("--log-publish-attempted", "LOG_PUBLISH_ATTEMPTED"),
        ("--log-publish-completed", "LOG_PUBLISH_COMPLETED"),
        ("--designed-admission-ready", "DESIGNED_ADMISSION_READY"),
        ("--pr-url", "PR_URL"),
        ("--recovery-branch", "RECOVERY_BRANCH"),
    ):
        if values.get(key, ""):
            stage_args.extend([flag, values[key]])
    stage_rc = capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout_log,
        stderr_log,
        stage_args,
    )
    staged = "STAGED=true" in stdout_log.read_text(encoding="utf-8", errors="replace") if stdout_log.is_file() else False
    if stage_rc != 0 or not staged:
        run_logs.append_execution_issue(
            log_file=design_tmpdir / "execution-issues.md",
            category="Warnings",
            entry="design Step 5c plan-write terminal-state staging failed; failure report may be unavailable.",
        )


def _finalize_failed_plan_write(
    *,
    design_tmpdir: Path,
    transcript_capture: TranscriptCaptureContext | None,
    kvs: list[tuple[str, str]],
    result_env: Path,
) -> int:
    _stage_failed_plan_write(design_tmpdir=design_tmpdir, kvs=kvs)
    if transcript_capture is not None:
        _ = _run_log_publish_after_capture(
            ctx=transcript_capture,
            kvs=kvs,
            result_env=result_env,
            outcome="failed-plan-write",
            write_result_env_on_publish_failure=False,
        )
    _emit_rows(kvs)
    return 1 if _write_result_env(path=result_env, rows=kvs) else 3


def publish_core(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed = {
        "--design-tmpdir": "",
        "--issue": "",
        "--session-id": "",
        "--claude-pid": "",
        "--repo": "",
    }
    skip_validate = False
    session_id_provided = False
    i = 0
    while i < len(args):
        token = args[i]
        if token in parsed:
            if i + 1 >= len(args):
                return 5
            if token == "--session-id":
                session_id_provided = True
            parsed[token] = args[i + 1]
            i += 2
            continue
        if token == "--skip-validate":
            skip_validate = True
            i += 1
            continue
        if token in {"-h", "--help"}:
            return 0
        return 5
    if not parsed["--design-tmpdir"] or not parsed["--issue"] or not session_id_provided or not parsed["--claude-pid"]:
        return 5
    if not parsed["--issue"].isdigit() or parsed["--issue"] == "0":
        return 5
    if not parsed["--claude-pid"].isdigit() or parsed["--claude-pid"] == "0":
        return 5
    if parsed["--repo"] and not _is_repo(parsed["--repo"]):
        return 5

    design_tmpdir = Path(parsed["--design-tmpdir"]).resolve()
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
    result_env = design_tmpdir / config.DESIGN_PUBLISH_RESULT_FILE
    final_summary_path = design_tmpdir / "final-summary.md"
    attempt_id = os.environ.get(config.ENV_LARCH_DESIGN_PUBLISH_ATTEMPT_ID, "")
    if not attempt_id:
        attempt_id = f"direct-{os.getpid()}-{os.urandom(8).hex()}"
    if not re.fullmatch(r"[A-Za-z0-9._-]{8,128}", attempt_id):
        return 5
    kvs: list[tuple[str, str]] = [
        ("PUBLISH_ATTEMPT_ID", attempt_id),
        ("PUBLISH_RC_SOURCE", config.DESIGN_PUBLISH_RC_SOURCE_RETURNED),
        ("LATEST_PHASE", "initialized"),
        ("PLAN_WRITE_OK", "false"),
        ("PUBLISH_OK", "false"),
        ("RENAMED", "false"),
        ("LOG_PUBLISH_ATTEMPTED", "false"),
        ("LOG_PUBLISH_COMPLETED", "false"),
        ("VALIDATE_STATUS", "not-run"),
        ("VALIDATE_DEFECT_COUNT", "0"),
        ("VALIDATE_SKIPPED_COUNT", "0"),
        ("VALIDATE_UNSAFE_TOKEN_COUNT", "0"),
        ("VALIDATE_MISSING_SCRIPT_COUNT", "0"),
        ("VALIDATE_LOG_FILE", ""),
        ("FINAL_SUMMARY_PATH", str(final_summary_path)),
        ("DESIGNED_ADMISSION_READY", "false"),
        ("PUBLISH_REFUSE_REASON", ""),
    ]
    if not (design_tmpdir / ".completed" / "step-5b").is_file():
        return 5
    try:
        _checkpoint_result_env(path=result_env, rows=kvs, phase="initialized")
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 5
    _refresh_composed_plan_md(design_tmpdir=design_tmpdir)
    composed_plan = design_tmpdir / "composed-plan.md"
    if not composed_plan.is_file() or composed_plan.stat().st_size == 0:
        _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="defects-found")
        _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value="1")
        _replace_kv(rows=kvs, key="VALIDATE_LOG_FILE", value=str(design_tmpdir / "validate-plan-commands.log"))
        _emit_rows(kvs)
        _ = _write_result_env(path=result_env, rows=kvs)
        return 4

    review_status, rounds_completed, provenance_present = review_provenance(design_tmpdir)
    step3_sentinel = (design_tmpdir / ".completed" / "step-3").is_file()
    _BLOCKED_STATUSES = {"panel-init-failed", "panel-skipped"}
    blocked_reason = ""
    if review_status in _BLOCKED_STATUSES:
        blocked_reason = review_status
    elif provenance_present and rounds_completed == 0:
        blocked_reason = "rounds_completed=0"
    elif review_status in _TERMINAL_STATUSES_REQUIRING_SENTINEL and not step3_sentinel:
        blocked_reason = f"{review_status} without .completed/step-3"
    refusal_reason = _publish_refusal_reason(
        design_tmpdir=design_tmpdir,
        plugin_root=plugin_root,
        blocked_reason=blocked_reason,
    )
    if refusal_reason:
        _emit_publish_refusal(reason=refusal_reason, kvs=kvs, result_env=result_env)
        return 4

    if (design_tmpdir / ".pause-requested").is_file():
        pause = subprocess.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "design",
                "pause-save",
                "--design-tmpdir",
                str(design_tmpdir),
                "--issue",
                parsed["--issue"],
                *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
            ],
            check=False,
        )
        return int(pause.returncode)

    if not _sanitize_diagram_candidate(design_tmpdir=design_tmpdir, plugin_root=plugin_root):
        return 5

    if review_status or rounds_completed:
        original = composed_plan.read_text(encoding="utf-8", errors="replace")
        original = _splice_plan_provenance(text=original, review_status=review_status, rounds_completed=rounds_completed)
        _ = composed_plan.write_text(original, encoding="utf-8")
    plan_text = composed_plan.read_text(encoding="utf-8", errors="replace")
    design_rating, raw_rating_invalid = _resolve_publish_difficulty_rating(design_tmpdir=design_tmpdir, plan_text=plan_text)
    if raw_rating_invalid:
        return 5
    if design_rating is not None:
        rewritten = difficulty.rewrite_plan_difficulty(plan_text, design_rating.adjusted_tier)
        if rewritten != plan_text:
            _ = composed_plan.write_text(rewritten, encoding="utf-8")
            plan_text = rewritten

    repo_root_arg = Path(consumer_repo_root() or plugin_root)

    if skip_validate:
        _replace_kv(rows=kvs, key="VALIDATE_STATUS", value="skipped")
    else:
        validate_env: dict[str, str] = {
            **os.environ,
            "DESIGN_TMPDIR": str(design_tmpdir),
            "LARCH_QUIET_DISABLE": "1",
            "CLAUDE_PLUGIN_ROOT": str(plugin_root),
            "LARCH_REQUIRE_PLAN_DIFFICULTY": "1",
        }
        validate = subprocess.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "plan",
                "validate",
                "--plan-file",
                str(composed_plan),
                "--source-kind",
                "composed",
                "--design-tmpdir",
                str(design_tmpdir),
                "--repo-root",
                str(repo_root_arg),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=validate_env,
        )
        parsed_validate = _parse_kv((validate.stdout or "") + "\n" + (validate.stderr or ""))
        _replace_kv(rows=kvs, key="VALIDATE_STATUS", value=parsed_validate.get("VALIDATE_STATUS", "not-run"))
        _replace_kv(rows=kvs, key="VALIDATE_DEFECT_COUNT", value=parsed_validate.get("VALIDATE_DEFECT_COUNT", "0"))
        _replace_kv(rows=kvs, key="VALIDATE_SKIPPED_COUNT", value=parsed_validate.get("VALIDATE_SKIPPED_COUNT", "0"))
        _replace_kv(rows=kvs, key="VALIDATE_UNSAFE_TOKEN_COUNT", value=parsed_validate.get("VALIDATE_UNSAFE_TOKEN_COUNT", "0"))
        _replace_kv(rows=kvs, key="VALIDATE_LOG_FILE", value=parsed_validate.get("VALIDATE_LOG_FILE", ""))
        _replace_kv(rows=kvs, key="VALIDATE_MISSING_SCRIPT_COUNT", value=_count_missing_script_defects(parsed_validate.get("VALIDATE_LOG_FILE", "")))
        if dict(kvs).get("VALIDATE_STATUS") == "defects-found":
            _emit_rows(kvs)
            _ = _write_result_env(path=result_env, rows=kvs)
            return 4
        if validate.returncode != 0 or dict(kvs).get("VALIDATE_STATUS") != "ok":
            return 5

    invariant_completeness = check_invariant_assessment_completeness(
        design_tmpdir=design_tmpdir,
        repo_root=repo_root_arg,
        outcome="approved",
    )
    if invariant_completeness.required and not invariant_completeness.present:
        _emit_missing_invariant_assessment_refusal(
            design_tmpdir=design_tmpdir,
            result=invariant_completeness,
            kvs=kvs,
            result_env=result_env,
        )
        return 4
    if invariant_completeness.required and invariant_completeness.present and not _persisted_note_publishable(
        path=design_tmpdir / invariant_completeness.artifact,
        kind=architectural_guidelines.INVARIANTS,
    ):
        _emit_invariant_violation_refusal(
            result=invariant_completeness,
            kvs=kvs,
            result_env=result_env,
        )
        return 4

    completeness = check_guideline_assessment_completeness(
        design_tmpdir=design_tmpdir,
        repo_root=repo_root_arg,
        outcome="approved",
    )
    if completeness.required and not completeness.present:
        _emit_missing_guideline_assessment_refusal(
            design_tmpdir=design_tmpdir,
            result=completeness,
            kvs=kvs,
            result_env=result_env,
        )
        return 4
    if completeness.required and completeness.present and not _persisted_note_publishable(
        path=design_tmpdir / completeness.artifact,
        kind=architectural_guidelines.GUIDELINES,
    ):
        _emit_invalid_guideline_deviation_refusal(
            result=completeness,
            kvs=kvs,
            result_env=result_env,
        )
        return 4

    redacted_plan = design_tmpdir / "composed-plan.redacted.md"
    redact = subprocess.run(
        [sys.executable, str(plugin_root / "python" / "cli.py"), "redact", "secrets"],
        input=composed_plan.read_text(encoding="utf-8", errors="replace"),
        text=True,
        capture_output=True,
        check=False,
    )
    if redact.returncode != 0 or not redact.stdout:
        return 5
    _ = redacted_plan.write_text(redact.stdout, encoding="utf-8")

    block = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "named-block",
            "write",
            "--marker",
            "plan",
            "--issue",
            parsed["--issue"],
            "--content-file",
            str(redacted_plan),
            *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
        ],
        stdout=subprocess.DEVNULL,
        check=False,
    )
    if block.returncode != 0:
        transcript_capture = (
            TranscriptCaptureContext(
                design_tmpdir=design_tmpdir,
                plugin_root=plugin_root,
                session_id=parsed["--session-id"],
                issue=parsed["--issue"],
                repo=parsed["--repo"],
                claude_pid=parsed["--claude-pid"],
                warning_step_label="5c",
            )
            if parsed["--session-id"]
            else None
        )
        return _finalize_failed_plan_write(
            design_tmpdir=design_tmpdir,
            transcript_capture=transcript_capture,
            kvs=kvs,
            result_env=result_env,
        )
    _replace_kv(rows=kvs, key="PLAN_WRITE_OK", value="true")
    _checkpoint_result_env(path=result_env, rows=kvs, phase="plan-write")
    if design_rating is not None:
        design_tier = design_rating.adjusted_tier
        sync_args = [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "difficulty",
            "sync-labels",
            "--issue",
            parsed["--issue"],
            "--tier",
            design_tier,
        ]
        if parsed["--repo"]:
            sync_args.extend(["--repo", parsed["--repo"]])
        _ = subprocess.run(sync_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        raw_rating = design_tmpdir / difficulty.DESIGN_RAW_RATING_BASENAME
        record_path = design_tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME
        record_args = [
            sys.executable, str(plugin_root / "python" / "cli.py"), "difficulty", "write-record",
            "--output", str(record_path), "--rater", "design", "--rater-tool", "claude",
            "--rater-model", "unknown", "--design-tier", design_tier, "--fallback-tier", design_tier,
            "--fallback-rationale", "design plan metadata",
        ]
        if raw_rating.is_file() and not raw_rating.is_symlink():
            record_args.extend(["--raw-rating-file", str(raw_rating), "--design-raw-rating-file", str(raw_rating)])
        record = subprocess.run(record_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if record.returncode == 0 and record_path.is_file():
            run_id = os.environ.get("RUN_ID", "")
            run_id_path = design_tmpdir / "run-id.txt"
            if not run_id and run_id_path.is_file():
                run_id = run_id_path.read_text(encoding="utf-8", errors="replace").strip()
            if run_id:
                _ = subprocess.run(
                    [
                        sys.executable, str(plugin_root / "python" / "cli.py"), "run-log", "write",
                        "--skill", "design", "--run-id", run_id, "--batch", "difficulty-rating",
                        "--input-file", str(record_path),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

    _checkpoint_result_env(path=result_env, rows=kvs, phase="difficulty")

    # Upsert the architecture diagram into the shared larch:diagrams comment.
    # Step 5c consumes post-approval artifacts written by Step 5b.5. It clears
    # Architecture content only when Step 5b.5 wrote an explicit skip marker; a
    # missing tmpdir file after the sentinel is warning-only and must not wipe a
    # valid issue diagram.
    arch_file = design_tmpdir / "architecture-diagram.md"
    arch_skipped = design_tmpdir / "architecture-diagram.skipped"
    upsert_args: list[str] = ["--issue", parsed["--issue"]]
    if parsed["--repo"]:
        upsert_args += ["--repo", parsed["--repo"]]
    run_upsert = False
    if arch_file.is_file() and arch_file.stat().st_size > 0:
        run_upsert = True
        upsert_args += ["--architecture-file", str(arch_file)]
    elif arch_skipped.is_file():
        run_upsert = True
        upsert_args += ["--clear-architecture"]
    else:
        run_logs.append_execution_issue(
            log_file=design_tmpdir / "execution-issues.md",
            category="Warnings",
            entry=design_diagram_log.bounded_diagram_warning_body(
                reason="diagram-artifact-missing-after-step5b5",
                exit_code=0,
            ),
        )
    if run_upsert:
        upsert = proc.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "diagrams",
                "upsert",
                *upsert_args,
            ],
            check=False,
        )
        upsert_stderr_file = design_tmpdir / "diagrams-architecture-upsert.stderr"
        _ = upsert_stderr_file.write_text(upsert.stderr or "", encoding="utf-8")
        _ = (design_tmpdir / "diagrams-architecture-upsert.stdout").write_text(
            upsert.stdout or "", encoding="utf-8"
        )
        upsert_kv = _parse_kv(upsert.stdout)
        upsert_status = upsert_kv.get("UPSERT_STATUS", "")
        if upsert_status:
            kvs.append(("UPSERT_STATUS", upsert_status))
        if upsert_kv.get("ARCHITECTURE_SOURCE"):
            kvs.append(("ARCHITECTURE_SOURCE", upsert_kv["ARCHITECTURE_SOURCE"]))
        if upsert_status == "failed" or upsert.returncode != 0:
            _ = proc.run(
                [
                    sys.executable,
                    str(plugin_root / "python" / "cli.py"),
                    "run-log",
                    "append-failure",
                    "--log",
                    str(design_tmpdir / "execution-issues.md"),
                    "--site",
                    "design Step 5c.5",
                    "--tool",
                    "python/cli.py diagrams upsert architecture",
                    "--exit-code",
                    str(upsert.returncode),
                    "--category",
                    "Warnings",
                    "--output-file",
                    str(upsert_stderr_file),
                    "--redact",
                ],
                check=False,
            )

    _checkpoint_result_env(path=result_env, rows=kvs, phase="diagram-upsert")

    rename: subprocess.CompletedProcess[str] = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "tracking-issue",
            "rename",
            "--issue",
            parsed["--issue"],
            "--state",
            "designed",
            *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _write_bounded_phase_stderr(
        design_tmpdir=design_tmpdir,
        filename=config.DESIGN_PUBLISH_RENAME_STDERR_FILE,
        text=rename.stderr or "",
    )
    renamed = _parse_kv(rename.stdout)
    renamed_value = renamed.get("RENAMED", "")
    new_title = renamed.get("NEW_TITLE", "")
    if renamed_value:
        kvs.append(("RENAMED", renamed_value))
    if new_title:
        kvs.append(("NEW_TITLE", new_title))
    if renamed_value == "true" or new_title.startswith("[DESIGNED] "):
        _replace_kv(rows=kvs, key="DESIGNED_ADMISSION_READY", value="true")
    _checkpoint_result_env(path=result_env, rows=kvs, phase="tracking-issue-rename")

    if parsed["--session-id"]:
        _replace_kv(rows=kvs, key="LOG_PUBLISH_ATTEMPTED", value="true")
        _checkpoint_result_env(path=result_env, rows=kvs, phase="log-publish")
        publish_rc = _run_log_publish_after_capture(
            ctx=TranscriptCaptureContext(
                design_tmpdir=design_tmpdir,
                plugin_root=plugin_root,
                session_id=parsed["--session-id"],
                issue=parsed["--issue"],
                repo=parsed["--repo"],
                claude_pid=parsed["--claude-pid"],
                warning_step_label="5c",
            ),
            kvs=kvs,
            result_env=result_env,
            outcome="approved",
        )
        if publish_rc is not None:
            return publish_rc
        _replace_kv(rows=kvs, key="LOG_PUBLISH_COMPLETED", value="true")
    _checkpoint_result_env(path=result_env, rows=kvs, phase="complete")
    _emit_rows(kvs)
    return 0


def publish_main(argv: Sequence[str]) -> int:
    return publish_core(argv)
