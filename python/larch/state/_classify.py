"""Stall classification, attempt tracking, and state reading for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from larch.core import config
from larch.state._tokens import (
    _DEFAULT_ATTEMPTS_FILE,
    _DEFAULT_CLASSIFICATION_FILE,
    _DEFAULT_ESCALATION_FALLBACK,
    _DEFAULT_ESCALATION_LEDGER,
    _DISPATCH_BAIL_TOKENS,
    _abandoned_checks_marker_stall_step,
    _read_state_file,
    _render_safe_bail_reason_value,
    _render_safe_source_script_value,
    _report_skill_label,
    _safe_dispatcher_value,
    _safe_matched_pattern_value,
    _safe_phase_value,
    _safe_step_value,
    _state_file_syntax_ok,
    _truthy,
    _validate_tmpdir_write_path,
    emit,
    read_kv,
    write_kvs,
)
from larch.state._detail_log import _read_failure_detail_log_with_sidecar_fallback, _read_optional_evidence
from larch.state._escalation import _artifact_path, _validate_artifact_prefix
from larch.state._validate import _validated_terminal_state_values


def _latest_attempt_signature(path: Path) -> str:
    if not path.is_file():
        return ""
    count = read_kv(path=path, key="attempt_count", default="0")
    if not count.isdigit() or count == "0":
        return ""
    return read_kv(path=path, key=f"attempt.{count}.signature", default="")


def _validate_attempts_file_path(*, tmpdir: Path, path: Path) -> bool:
    if not path.is_absolute():
        print("stall-recovery: --attempts-file must be absolute", file=sys.stderr)
        return False
    if path.is_symlink():
        print("stall-recovery: --attempts-file must not be a symlink", file=sys.stderr)
        return False
    try:
        _ = path.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        print("stall-recovery: --attempts-file outside implement tmpdir", file=sys.stderr)
        return False
    except OSError:
        print("stall-recovery: --attempts-file outside implement tmpdir", file=sys.stderr)
        return False
    if path.exists() and not path.is_file():
        print("stall-recovery: --attempts-file outside implement tmpdir", file=sys.stderr)
        return False
    return True


def _check_implement_primary_state_preflight(state_file: Path) -> bool:
    if state_file.is_symlink():
        print("stall-recovery: symlinked ship-pr-state.sh", file=sys.stderr)
        return False
    if state_file.is_file() and not _state_file_syntax_ok(state_file):
        print("stall-recovery: malformed ship-pr-state.sh", file=sys.stderr)
        return False
    return True


def _merged_state(
    tmpdir: Path,
    *,
    primary_state_file: str = "",
    finalize_state_file: str = "",
    session_env_file: str = "",
) -> dict[str, str]:
    state_file = Path(primary_state_file) if primary_state_file else tmpdir / "ship-pr-state.sh"
    finalize_file = Path(finalize_state_file) if finalize_state_file else tmpdir / "finalize-state.sh"
    session_file = Path(session_env_file) if session_env_file else tmpdir / "session-env.sh"
    return _read_state_file(state_file) | _read_state_file(finalize_file) | _read_state_file(session_file)


def _resume_hint_for(*, klass: str, step: str, phase: str, pattern: str = "") -> str:
    safe_step = _safe_step_value(step)
    if klass in {"contract-failure", "same-cause-repeat", "unrecoverable", "submodule-restricted"}:
        return "none"
    if safe_step in {"3", "6", "12d", "bump-branch-guard"}:
        return "checks-commit-route-retry" if pattern == "checks-leg-abandoned" and safe_step == "3" else "none"
    if safe_step == "2":
        return "step2-impl"
    if safe_step == "5":
        return "step5-review"
    if safe_step in {"8", "9", "10", "11", "12", "13", "14", "15", "rebase-failed"}:
        return "step8-shippr"
    if safe_step and re.fullmatch(r"(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", safe_step):
        return "step8-shippr"
    if safe_step and safe_step != "unknown":
        return "none"
    if phase.startswith("review"):
        return "step5-review"
    if phase.startswith(("impl", "step2")):
        return "step2-impl"
    if not phase:
        return "none"
    return "step8-shippr"


def _classify_text(*, text: str, bail: str, step: str, phase: str, detail_log_valid: bool = False) -> tuple[str, str, str]:
    _ = phase
    if step == "rebase-failed":
        return "transient-infra", "step8-shippr", "rebase-transient"
    if step in {"3", "6"}:
        return "contract-failure", "none", "step-contract"
    if step == "merge-loop-iteration-cap":
        return "unrecoverable", "none", "terminal-step"
    if bail == "protected-path-edit-required-out-of-scope":
        return "protected-path", "step2-impl", "protected-path-bail-token"
    if bail == "submodule-edit-required-out-of-scope":
        return "submodule-restricted", "none", "submodule-restricted-bail-token"
    if bail in {"adopted-issue-closed", "tracking-init-failed"}:
        return "unrecoverable", "none", "terminal-bail"
    if bail == "recovery-out-of-scope":
        return "unrecoverable", "none", "recovery-out-of-scope"
    if bail == "ci-fix-exhausted":
        pattern = "ci-fix-exhausted-with-detail" if detail_log_valid else "terminal-bail"
        return "unrecoverable", "none", pattern
    lower = f"{bail}\n{text}".lower()
    if any(token in lower for token in config.LINT_FIX_BAIL_REASON_TOKENS):
        return "lint-failure", "step5-review", "lint-fix-bail-token"
    if "submodule-edit-required-out-of-scope" in lower:
        return "submodule-restricted", "none", "submodule-restricted-bail-token"
    if "protected-path-edit-required-out-of-scope" in lower:
        return "protected-path", "step2-impl", "protected-path-bail-token"
    if any(x in lower for x in ("pytest", "jest", "vitest", "rspec", "go test", "test failed", "failing test", "tests failed", "failed with")):
        return "test-failure", "step2-impl", "test-output"
    if re.search(r"relevant-checks.*fail|lint.*failed", lower) or any(
        x in lower for x in ("lint-fix", "shellcheck", "markdownlint", "pre-commit", "lint-fix-loop")
    ):
        return "lint-failure", "step5-review", "lint-output"
    if bail in _DISPATCH_BAIL_TOKENS:
        return "dispatch-failure", "step2-impl", "dispatch-bail-token"
    if re.search(r"envelope-invalid|invalid.*envelope|orchestrator-envelope-invalid|wrapper-validation|step2.*dispatch", lower):
        return "dispatch-failure", "step2-impl", "dispatch-output"
    if re.search(
        r"rate limit|api rate|network/auth issue|network (error|failure|unavailable)|timed? out|timeout|"
        r"connection (reset|refused)|temporary failure|tls handshake|dns failure|name resolution|"
        r"github unavailable|github api unavailable|service unavailable|http 5\d\d",
        lower,
    ):
        return "transient-infra", "step8-shippr", "transient-output"
    return "unrecoverable", "none", "fallback"


def _resolve_step_with_abandoned_marker(*, tmpdir: Path, any_stall: bool, step: str) -> tuple[bool, str, str | None]:
    abandoned_marker_step = None if any_stall else _abandoned_checks_marker_stall_step(tmpdir)
    if abandoned_marker_step is None:
        return any_stall, step, None
    return True, step or abandoned_marker_step, abandoned_marker_step


def _classify_short_circuit(*, abandoned_marker_step: str | None, any_stall: bool) -> tuple[str, str, str] | None:
    if abandoned_marker_step is not None:
        return "transient-infra", "checks-commit-route-retry", "checks-leg-abandoned"
    if not any_stall:
        return "unrecoverable", "none", "no-stall"
    return None


def classify(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    primary_state_file = getattr(args, "primary_state_file", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    prefix = getattr(args, "artifact_prefix", "") or ""
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return 2
    if profile == "generic":
        state_file = (
            Path(primary_state_file)
            if primary_state_file
            else _artifact_path(tmpdir=tmpdir, default_name="stall-recovery-terminal-state.env", prefix=prefix)
        )
        return _classify_generic_from_terminal_state(args=args, tmpdir=tmpdir, state_file=state_file)

    finalize_state_file = getattr(args, "finalize_state_file", "") or ""
    session_env_file = getattr(args, "session_env_file", "") or ""
    state_file = Path(primary_state_file) if primary_state_file else tmpdir / "ship-pr-state.sh"
    if not _check_implement_primary_state_preflight(state_file):
        return 3
    st = _merged_state(
        tmpdir,
        primary_state_file=primary_state_file,
        finalize_state_file=finalize_state_file,
        session_env_file=session_env_file,
    )
    step = args.stall_step or st.get("STALL_STEP", "")
    phase = args.phase or st.get("PHASE", "")
    bail = args.bail_reason or st.get("BAIL_REASON", "") or st.get("IMPLEMENT_BAIL_REASON", "")
    bail_raw = (bail.splitlines()[0] if bail else "")
    detail = ""
    detail_log_valid = False
    failure_detail_log_value = ""
    detail, detail_log_valid, failure_detail_log_value = _read_failure_detail_log_with_sidecar_fallback(
        tmpdir=tmpdir,
        primary=args.failure_detail_log or "",
        ledger=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_LEDGER, prefix=prefix),
        fallback=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix),
    )
    memory_stall = getattr(args, "in_memory_stall_tracking", "")
    primary_stall = _read_state_file(state_file).get("STALL_TRACKING", "false")
    finalize_stall = _read_state_file(Path(finalize_state_file) if finalize_state_file else tmpdir / "finalize-state.sh").get("STALL_TRACKING", "false")
    session_stall = _read_state_file(Path(session_env_file) if session_env_file else tmpdir / "session-env.sh").get("STALL_TRACKING", "false")
    any_stall = _truthy(memory_stall) or _truthy(primary_stall) or _truthy(finalize_stall) or _truthy(session_stall)
    any_stall, step, abandoned_marker_step = _resolve_step_with_abandoned_marker(tmpdir=tmpdir, any_stall=any_stall, step=step)
    evidence = detail
    if not detail_log_valid:
        for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh"):
            state_path = tmpdir / name
            evidence = f"{evidence}\n{_read_optional_evidence(state_path)}"
    short_circuit = _classify_short_circuit(abandoned_marker_step=abandoned_marker_step, any_stall=any_stall)
    klass, _hint, pattern = short_circuit or _classify_text(text=evidence, bail=bail, step=step, phase=phase, detail_log_valid=detail_log_valid)
    hint = _resume_hint_for(klass=klass, step=step, phase=phase, pattern=pattern)
    evidence_digest = hashlib.sha256(evidence[:2048].encode()).hexdigest()[:16] if evidence else ""
    signature = hashlib.sha256(
        f"class={klass}\nhint={hint}\nstep={step}\nphase={phase}\nbail={bail}\nevidence={evidence_digest}\n".encode(),
    ).hexdigest()
    if args.attempts_file:
        attempts = Path(args.attempts_file)
        if not _validate_attempts_file_path(tmpdir=tmpdir, path=attempts):
            return 1
        if attempts.is_file() and klass not in {"contract-failure", "unrecoverable"} and _latest_attempt_signature(attempts) == signature:
            klass = "same-cause-repeat"
            hint = "none"
            pattern = "same-cause-repeat"
    classification_file = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_CLASSIFICATION_FILE, prefix=getattr(args, "artifact_prefix", "") or "")
    raw_exit_code = args.exit_code or st.get("EXIT_CODE", "unknown")
    exit_code = raw_exit_code if re.fullmatch(r"[0-9]+|unknown", raw_exit_code or "") else "unknown"
    raw_dispatcher = args.dispatcher or st.get("DISPATCHER", "") or st.get("CODER_TOOL", "")
    values = {
        "FAILURE_CLASS": klass,
        "FAILURE_SIGNATURE": signature,
        "RESUME_HINT": hint,
        "STALL_STEP": _safe_step_value(step),
        "PHASE": _safe_phase_value(phase),
        "STALL_TRACKING": "true" if any_stall else "false",
        "BAIL_REASON": _render_safe_bail_reason_value(bail, generic=False),
        "BAIL_REASON_RAW": bail_raw,
        "FAILURE_DETAIL_LOG": failure_detail_log_value,
        "EXIT_CODE": exit_code,
        "MATCHED_CLASSIFIER_PATTERN": _safe_matched_pattern_value(pattern),
        "DISPATCHER": _safe_dispatcher_value(raw_dispatcher, generic=False),
    }
    for k, v in values.items():
        emit(key=k, value=v)
    write_kvs(path=classification_file, values=values)
    emit(key="CLASSIFICATION_FILE", value=classification_file)
    return 0


def _classify_generic_from_terminal_state(*, args: argparse.Namespace, tmpdir: Path, state_file: Path) -> int:
    prefix = getattr(args, "artifact_prefix", "") or ""
    found = _validated_terminal_state_values(tmpdir=tmpdir, state_file=state_file, generic=True)
    if found is None:
        emit(key="VALID", value="false")
        return 1
    stall_step = found.get("STALL_STEP", "")
    phase = found.get("PHASE", "")
    bail_reason = found.get("BAIL_REASON", "")
    exit_code = found.get("EXIT_CODE", "")
    source_script = found.get("SOURCE_SCRIPT", "")
    detail_log = found.get("FAILURE_DETAIL_LOG", "")
    evidence = ""
    failure_detail_log_value = ""
    detail_log_valid = False
    evidence, detail_log_valid, failure_detail_log_value = _read_failure_detail_log_with_sidecar_fallback(
        tmpdir=tmpdir,
        primary=detail_log,
        ledger=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_LEDGER, prefix=prefix),
        fallback=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix),
    )
    if not detail_log_valid:
        evidence = _read_optional_evidence(state_file)
    klass, _hint, pattern = _classify_text(text=evidence, bail=bail_reason, step=stall_step, phase=phase, detail_log_valid=detail_log_valid)
    resume_hint = "none"
    evidence_digest = hashlib.sha256(evidence[:2048].encode()).hexdigest()[:16] if evidence else ""
    skill_label = _report_skill_label(profile="generic", prefix=prefix)
    signature = hashlib.sha256(
        (
            f"profile=generic\nskill={skill_label}\nclass={klass}\nhint={resume_hint}\n"
            f"step={stall_step}\nphase={phase}\nbail={bail_reason}\nevidence={evidence_digest}\n"
        ).encode(),
    ).hexdigest()
    if args.attempts_file:
        attempts = Path(args.attempts_file)
        if not _validate_attempts_file_path(tmpdir=tmpdir, path=attempts):
            return 1
        if attempts.is_file() and klass not in {"contract-failure", "unrecoverable"} and _latest_attempt_signature(attempts) == signature:
            klass = "same-cause-repeat"
            pattern = "same-cause-repeat"
    exit_code = exit_code if re.fullmatch(r"[0-9]+|unknown", exit_code or "") else "unknown"
    values = {
        "FAILURE_CLASS": klass,
        "FAILURE_SIGNATURE": signature,
        "RESUME_HINT": resume_hint,
        "STALL_STEP": _safe_step_value(stall_step),
        "PHASE": _safe_phase_value(phase),
        "STALL_TRACKING": "true",
        "BAIL_REASON": _render_safe_bail_reason_value(bail_reason, generic=True),
        "BAIL_REASON_RAW": bail_reason,
        "FAILURE_DETAIL_LOG": failure_detail_log_value,
        "EXIT_CODE": exit_code,
        "MATCHED_CLASSIFIER_PATTERN": _safe_matched_pattern_value(pattern),
        "DISPATCHER": _render_safe_source_script_value(source_script, generic=True),
    }
    classification_file = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_CLASSIFICATION_FILE, prefix=prefix)
    for key, value in values.items():
        emit(key=key, value=value)
    write_kvs(path=classification_file, values=values)
    emit(key="CLASSIFICATION_FILE", value=classification_file)
    return 0


def init_attempts(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    path = Path(args.attempts_file) if args.attempts_file else tmpdir / _DEFAULT_ATTEMPTS_FILE
    if not _validate_attempts_file_path(tmpdir=tmpdir, path=path):
        return 1
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=path):
        print("stall-recovery: --attempts-file outside implement tmpdir", file=sys.stderr)
        return 1
    if not path.exists():
        write_kvs(path=path, values={"version": 1, "created_utc": datetime.now(UTC).isoformat(), "attempt_count": 0})
    emit(key="ATTEMPTS_FILE", value=path)
    emit(key="ATTEMPT_COUNT", value=read_kv(path=path, key="attempt_count", default="0"))
    return 0


def record_attempt(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    path = Path(args.attempts_file) if args.attempts_file else tmpdir / _DEFAULT_ATTEMPTS_FILE
    if not _validate_attempts_file_path(tmpdir=tmpdir, path=path):
        return 1
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=path):
        print("stall-recovery: --attempts-file outside implement tmpdir", file=sys.stderr)
        return 1
    now = datetime.now(UTC).isoformat()
    if path.exists():
        raw_count = read_kv(path=path, key="attempt_count", default="0")
        if not raw_count.isdigit():
            print("stall-recovery: attempt_count is malformed", file=sys.stderr)
            return 1
        count = int(raw_count)
        text = path.read_text(encoding="utf-8", errors="replace")
        lines: list[str] = []
        replaced = False
        for line in text.splitlines():
            if line.startswith("attempt_count="):
                lines.append(f"attempt_count={count + 1}")
                replaced = True
            else:
                lines.append(line)
        if not replaced:
            lines.append(f"attempt_count={count + 1}")
    else:
        count = 0
        lines = ["version=1", f"created_utc={now}", "attempt_count=1"]
    next_count = count + 1
    lines.extend([
        f"attempt.{next_count}.class={args.failure_class}",
        f"attempt.{next_count}.signature={args.signature}",
        f"attempt.{next_count}.resume_hint={args.resume_hint}",
        f"attempt.{next_count}.outcome={args.outcome}",
        f"attempt.{next_count}.utc={now}",
        f"last_class={args.failure_class}",
        f"last_signature={args.signature}",
        f"last_resume_hint={args.resume_hint}",
        f"last_outcome={args.outcome}",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    tmp.replace(path)
    emit(key="ATTEMPT_COUNT", value=next_count)
    return 0


def retry_policy(args: argparse.Namespace) -> int:
    klass = args.failure_class
    caps: dict[str, tuple[int, str]] = {
        "transient-infra": (4, "sleep-seconds.sh 5"),
        "test-failure": (8, "none"),
        "lint-failure": (8, "none"),
        "ci-fix-exhausted": (0, "none"),
        "dispatch-failure": (3, "none"),
        "protected-path": (1, "none"),
        "submodule-restricted": (0, "none"),
        "same-cause-repeat": (2, "none"),
        "contract-failure": (0, "none"),
        "unrecoverable": (0, "none"),
    }
    max_attempts, delay = caps.get(klass, (0, "none"))
    emit(key="FAILURE_CLASS", value=klass)
    emit(key="MAX_ATTEMPTS", value=max_attempts)
    emit(key="RETRY_DELAY", value=delay)
    return 0
