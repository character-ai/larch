"""Stall recovery report helpers shared by /implement and /design."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, UTC
from pathlib import Path

import larch_io
import config
# run_logs is used only in a function-scoped helper; this closes a benign cycle.
import run_logs  # pylint: disable=cyclic-import

MAX_PUBLIC_FILE_BYTES = 256_000
ALLOWLIST_TABLE_COLUMNS = 4
RETRY_POLICY_TABLE_COLUMNS = 3
CONTROL_CHAR_ORDINAL_LIMIT = 32
SAFE_SMALL_INTEGER_DIGITS = 4
MAX_OPTIONAL_EVIDENCE_BYTES = 65_536

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CLASSIFICATION_FILE = "stall-recovery-classification.env"
_DEFAULT_ATTEMPTS_FILE = "stall-recovery-attempts.env"
_DEFAULT_ESCALATION_LEDGER = "stall-recovery-escalation-ledger.tsv"
_DEFAULT_ESCALATION_FALLBACK = "stall-recovery-escalation-fallback.tsv"
_DEFAULT_RECORD_FAILURE_MARKER = "stall-recovery-escalation-record-failure.env"
_DEFAULT_ROOT_CAUSE_FILE = "stall-recovery-root-cause.md"
_DEFAULT_BOUNDED_ROOT_CAUSE_FILE = "stall-recovery-bounded-root-cause.md"
_DEFAULT_SENSITIVE_CORPUS = "stall-recovery-sensitive-corpus.env"
_DEFAULT_ISSUE_INPUT = "stall-recovery-issue-input.md"
_DEFAULT_CHAT_PRINT = "stall-recovery-chat-print.md"
_DEFAULT_TITLE_FILE = "stall-recovery-title.txt"
_DEFAULT_OPERATOR_ACTION_RECORD = "stall-recovery-operator-action-record.md"
_DEFAULT_OPERATOR_ACTION_SENTINEL = "stall-recovery-operator-action.env"
_DEFAULT_TIER_A_ATTEMPTS_SLICE = "stall-recovery-tier-a-attempts.md"
_DEFAULT_TIER_A_ESCALATION_SLICE = "stall-recovery-tier-a-escalation.md"
_DEFAULT_TIER_A_ROOT_CAUSE_SLICE = "stall-recovery-tier-a-root-cause.md"
_DEFAULT_TIER_B_ATTEMPTS_SLICE = "stall-recovery-bounded-attempts.md"
_DEFAULT_TIER_B_ESCALATION_SLICE = "stall-recovery-bounded-escalation-summary.md"
_DEFAULT_TIER_B_ROOT_CAUSE_SLICE = "stall-recovery-bounded-root-cause-public.md"

_OUTCOMES = frozenset({
    "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail", "approved", "approved-partition",
})
_GENERIC_SITES = frozenset({
    "step2b", "gate-b", "step3-review", "discussion-round2", "step5c",
    "design-publish", "clarify-loop", "judge-panel", "decompose-panel",
})
_COMMON_SITES = frozenset({
    "step3", "step5", "step5-self-review", "step5-mav", "step6", "step8", "step18a",
    "review-loop", "lint-fix-loop", "ship-pr", "ship-pr-ci-initial", "ship-pr-ci-merge",
    "ship-pr-ci-per-job", "ship-pr-internal", "recovery-inline",
})
_GENERIC_TRIGGERS = frozenset({
    "main-agent-apply-required", "postplan-operator-required", "exhausted", "failed",
    "unavailable", "skipped-cycle-cap", "postplan-failed", "publish-tail-failed",
    "plan-write-failed", "publish-failed", "panel-failed", "panel-init-failed", "tally-error",
    "degraded-empty-collector", "judge-panel-collapse", "decompose-panel-retry-exhausted",
})
_COMMON_TRIGGERS = frozenset({
    "main-agent-required", "coder-main-agent-required", "main-agent-vote-required",
    "fix-attempts-exhausted", "design-flaw", "escalate", "all-vendors-failed",
    "ci-fix-exhausted", "first-fixer-non-health", "local-unfixable",
    "ship-pr-internal-lint-fix", "lint-fix-main-agent-required", "step2-impl",
    "step8-shippr", "dispatch-failed",
})
_GENERIC_BAILS = frozenset({
    "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail", "clarify-hard-halt", "postplan-failed",
    "publish-failed", "publish-tail-failed", "plan-write-failed", "judge-panel-collapse",
    "decompose-panel-retry-exhausted", "validator-autofix-exhausted",
    "validator-autofix-failed", "validator-autofix-unavailable",
    "validator-autofix-skipped-cycle-cap", "operator-action", "panel-init-failed",
})
_GENERIC_STEPS = frozenset({
    "validator", "postplan", "publish", "clarify", "panel", "judge-panel", "step2b", "step3", "step5c",
})
_GENERIC_PHASES = frozenset({
    "plan-write", "publish", "postplan", "clarify-loop", "judge-panel", "validation", "teardown",
})
_COMMON_PHASES = frozenset({
    "checks", "review", "implementation", "impl", "step2", "step5", "step8", "ship", "ship-pr",
    "pr-prep", "pr-create", "ci-initial", "ci-merge", "evaluate-failure", "force-push-gate",
    "bump", "merge", "postmerge", "rebase-failed",
})
_GENERIC_SOURCE_SCRIPTS = frozenset({
    "split-path", "design-publish", "design-step3-review", "design-step5c",
    "clarify-loop", "prompt-step", "validator", "postplan", "decompose-panel", "bash", "python",
})
_DISPATCH_BAIL_TOKENS = frozenset({
    "branch-changed", "cap_hit", "codex-runtime-failure", "cursor-bailed-no-reason",
    "cursor-modified-history", "cursor-runtime-failure", "detached-head-prohibited",
    "dirty-state-after-timeout", "interactive-subprocess-unsupported", "main-branch-post-dispatch",
    "main-branch-prohibited", "manifest-missing", "manifest-oos-materialization-failed",
    "manifest-schema-invalid", "protected-path-modified", "qa-pending-missing",
    "redactor-not-executable", "resume-incompatible", "submodule-dirty",
    "wrapper-validation-failure", "orchestrator-envelope-invalid",
})


def _safe_outcome(value: str) -> bool:
    return value in _OUTCOMES or (
        value.startswith("cancelled-") and bool(re.fullmatch(r"[A-Za-z0-9._:-]+", value))
    )


def _safe_step(value: str, *, generic: bool) -> bool:
    if generic and value in _GENERIC_STEPS:
        return True
    if value in {"bump-branch-guard", "merge-loop-iteration-cap", "rebase-failed"}:
        return True
    if re.fullmatch(r"[2-9]|1[0-5]", value):
        return True
    return bool(re.fullmatch(r"(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", value))


def _safe_token(*, kind: str, value: str, generic: bool) -> bool:
    if not value:
        return False
    if kind == "outcome":
        return _safe_outcome(value)
    if kind == "step":
        return _safe_step(value, generic=generic)
    if kind == "phase":
        return value in _COMMON_PHASES or (generic and value in _GENERIC_PHASES)
    if kind == "site":
        return value in _COMMON_SITES or (generic and value in _GENERIC_SITES)
    if kind == "trigger":
        return (
            value in _COMMON_TRIGGERS
            or (generic and value in _GENERIC_TRIGGERS)
            or bool(re.fullmatch(r"ci-local-unfixable:[A-Za-z0-9_,-]+", value))
        )
    if kind == "bail":
        return not value or (generic and value in _GENERIC_BAILS)
    if kind == "source-script":
        return generic and value in _GENERIC_SOURCE_SCRIPTS
    if kind == "root-cause":
        return value in {"larch-defect", "environment", "operator-action"}
    return False


def emit(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def read_kv(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=False, cr_strip="strip", on_error_default=False)


def write_kvs(*, path: Path, values: Mapping[str, object]) -> None:
    larch_io.write_kvs(path=path, values=values)


def _latest_attempt_signature(path: Path) -> str:
    if not path.is_file():
        return ""
    count = read_kv(path=path, key="attempt_count", default="0")
    if not count.isdigit() or count == "0":
        return ""
    return read_kv(path=path, key=f"attempt.{count}.signature", default="")


def _safe_matched_pattern_value(value: str) -> str:
    allowed = {
        "no-stall", "no-match", "step-contract", "terminal-step", "rebase-transient",
        "protected-path-bail-token", "submodule-restricted-bail-token", "terminal-bail",
        "recovery-out-of-scope", "test-output", "lint-output", "dispatch-output",
        "dispatch-bail-token", "transient-output", "ci-fix-exhausted-with-detail",
        "same-cause-repeat", "fallback", "bail-token", "lint-fix-bail-token",
    }
    return value if value in allowed else "redacted"



def _read_optional_evidence(path: Path) -> str:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return ""
    try:
        if path.stat().st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def validate_failure_detail_log(*, tmpdir: Path, path: Path, flag: str = "--failure-detail-log") -> bool:
    if not path.is_absolute():
        print(f"stall-recovery: {flag} must be absolute", file=sys.stderr)
        return False
    if path.is_symlink():
        print(f"stall-recovery: {flag} must not be a symlink", file=sys.stderr)
        return False
    try:
        _ = path.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        print(f"stall-recovery: {flag} outside implement tmpdir", file=sys.stderr)
        return False
    except OSError:
        print(f"stall-recovery: {flag} outside implement tmpdir", file=sys.stderr)
        return False
    if not path.is_file():
        print(f"stall-recovery: {flag} outside implement tmpdir", file=sys.stderr)
        return False
    try:
        if path.stat().st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
            print(f"stall-recovery: {flag} exceeds 64KiB", file=sys.stderr)
            return False
    except OSError:
        print(f"stall-recovery: {flag} unreadable", file=sys.stderr)
        return False
    return True


def _read_validated_failure_detail_log(*, tmpdir: Path, path: Path) -> tuple[str, bool]:
    if not validate_failure_detail_log(tmpdir=tmpdir, path=path):
        return "", False
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            print("stall-recovery: --failure-detail-log must be regular", file=sys.stderr)
            return "", False
        if st.st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
            print("stall-recovery: --failure-detail-log exceeds 64KiB", file=sys.stderr)
            return "", False
        with os.fdopen(fd, "rb") as handle:
            fd = None
            return handle.read(MAX_OPTIONAL_EVIDENCE_BYTES).decode("utf-8", errors="replace"), True
    except OSError as exc:
        if exc.errno == getattr(os, "ELOOP", 40):
            print("stall-recovery: --failure-detail-log must not be a symlink", file=sys.stderr)
        else:
            print("stall-recovery: --failure-detail-log unreadable", file=sys.stderr)
        return "", False
    finally:
        if fd is not None:
            os.close(fd)


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


def _read_state_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip("\r")
    return out


def _text_file_contains(*, path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return needle.lower() in text.lower()


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


def _resume_hint_for(*, klass: str, step: str, phase: str) -> str:
    safe_step = _safe_step_value(step)
    if klass in {"contract-failure", "same-cause-repeat", "unrecoverable", "submodule-restricted"}:
        return "none"
    if safe_step in {"3", "6", "12d", "bump-branch-guard"}:
        return "none"
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
    if args.failure_detail_log:
        detail_path = Path(args.failure_detail_log)
        detail, detail_log_valid = _read_validated_failure_detail_log(tmpdir=tmpdir, path=detail_path)
        if detail_log_valid:
            failure_detail_log_value = args.failure_detail_log
    memory_stall = getattr(args, "in_memory_stall_tracking", "")
    primary_stall = _read_state_file(state_file).get("STALL_TRACKING", "false")
    finalize_stall = _read_state_file(Path(finalize_state_file) if finalize_state_file else tmpdir / "finalize-state.sh").get("STALL_TRACKING", "false")
    session_stall = _read_state_file(Path(session_env_file) if session_env_file else tmpdir / "session-env.sh").get("STALL_TRACKING", "false")
    any_stall = _truthy(memory_stall) or _truthy(primary_stall) or _truthy(finalize_stall) or _truthy(session_stall)
    evidence = detail
    if not detail_log_valid:
        for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh"):
            state_path = tmpdir / name
            evidence = f"{evidence}\n{_read_optional_evidence(state_path)}"
    if not any_stall:
        klass, _hint, pattern = ("unrecoverable", "none", "no-stall")
    else:
        klass, _hint, pattern = _classify_text(text=evidence, bail=bail, step=step, phase=phase, detail_log_valid=detail_log_valid)
    hint = _resume_hint_for(klass=klass, step=step, phase=phase)
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
    if detail_log:
        detail_path = Path(detail_log)
        evidence, detail_log_valid = _read_validated_failure_detail_log(tmpdir=tmpdir, path=detail_path)
        if detail_log_valid:
            failure_detail_log_value = detail_log
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
    path = Path(args.attempts_file) if args.attempts_file else tmpdir / "stall-recovery-attempts.env"
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
    path = Path(args.attempts_file) if args.attempts_file else tmpdir / "stall-recovery-attempts.env"
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


def _has_pr_evidence(*, ship: Mapping[str, str], fin: Mapping[str, str]) -> bool:
    pr_number = (ship.get("PR_NUMBER") or fin.get("PR_NUMBER") or "").strip()
    if pr_number and pr_number != "0":
        return True
    pr_url = (ship.get("PR_URL") or fin.get("PR_URL") or "").strip()
    return bool(pr_url and pr_url != "N/A")


def _state_value(*, ship: Mapping[str, str], fin: Mapping[str, str], key: str) -> str:
    return ship.get(key) or fin.get(key, "")


def _is_nonzero_exit_code(value: str) -> bool:
    text = value.strip()
    if not text or text == "unknown":
        return False
    try:
        return int(text) != 0
    except ValueError:
        return False


_IN_FLIGHT_SHIP_PHASES = frozenset({"ci-initial", "rebase", "pr-create"})


def _finalize_phase_is_stale_stall_overlay(
    *, ship: Mapping[str, str],
    fin: Mapping[str, str],
    any_stall: bool,
) -> bool:
    if any_stall:
        return False
    ship_phase = ship.get("PHASE", "").strip()
    fin_phase = fin.get("PHASE", "").strip()
    return fin_phase == "stalled" and ship_phase in _IN_FLIGHT_SHIP_PHASES


def _phase_counts_as_stalled(
    *, ship: Mapping[str, str],
    fin: Mapping[str, str],
    any_stall: bool,
) -> bool:
    ship_phase = ship.get("PHASE", "").strip()
    fin_phase = fin.get("PHASE", "").strip()
    if ship_phase == "stalled":
        return True
    if fin_phase != "stalled":
        return False
    return not _finalize_phase_is_stale_stall_overlay(ship=ship, fin=fin, any_stall=any_stall)


def _is_healthy_pre_terminal_pr_snapshot(*, ship: Mapping[str, str], fin: Mapping[str, str]) -> bool:
    if _state_value(ship=ship, fin=fin, key="BAIL_REASON").strip():
        return False
    if _state_value(ship=ship, fin=fin, key="IMPLEMENT_BAIL_REASON").strip():
        return False
    if _state_value(ship=ship, fin=fin, key="PHASE").strip() == "stalled":
        return False
    return not _is_nonzero_exit_code(_state_value(ship=ship, fin=fin, key="EXIT_CODE"))


def normalized_outcome_values(args: argparse.Namespace) -> dict[str, str]:
    tmpdir = Path(args.implement_tmpdir)
    ship = _read_state_file(tmpdir / "ship-pr-state.sh")
    fin = _read_state_file(tmpdir / "finalize-state.sh")
    ses = _read_state_file(tmpdir / "session-env.sh")
    seed = _read_state_file(tmpdir / "ship-seed-input.env")
    classification = _read_state_file(tmpdir / _DEFAULT_CLASSIFICATION_FILE)
    memory_stall = getattr(args, "in_memory_stall_tracking", "") or os.environ.get("STALL_TRACKING", "false")
    ship_stall = ship.get("STALL_TRACKING", "false")
    fin_stall = fin.get("STALL_TRACKING", "false")
    ses_stall = ses.get("STALL_TRACKING", "false")
    any_stall = _truthy(memory_stall) or _truthy(ship_stall) or _truthy(fin_stall) or _truthy(ses_stall)
    phase_stalled = _phase_counts_as_stalled(ship=ship, fin=fin, any_stall=any_stall)
    merge_result = ship.get("MERGE_RESULT") or fin.get("MERGE_RESULT", "")
    merge = ship.get("MERGE") or fin.get("MERGE", "")
    draft = ship.get("DRAFT") or fin.get("DRAFT", "false")
    pr_number = ship.get("PR_NUMBER") or fin.get("PR_NUMBER", "")
    forked = ship.get("FORKED_TARGET") or fin.get("FORKED_TARGET") or ses.get("FORKED_TARGET", "false")
    ci_passed = ship.get("CI_PASSED") or fin.get("CI_PASSED", "false")
    design_done = fin.get("DESIGN_ONLY_DONE", "false")
    bail_user = fin.get("BAIL_NEEDS_USER_INPUT", "false")

    if any_stall or phase_stalled:
        outcome = "stalled"
    elif _truthy(forked):
        outcome = "forked-dry-run"
    elif _truthy(design_done):
        outcome = "design-only"
    elif merge_result in {"merged", "admin_merged"}:
        outcome = "merged"
    elif merge_result == "already_merged":
        outcome = "force-merged-externally"
    elif (
        _has_pr_evidence(ship=ship, fin=fin)
        and not merge_result
        and _is_healthy_pre_terminal_pr_snapshot(ship=ship, fin=fin)
        and not _truthy(bail_user)
    ):
        outcome = "pr-created-draft" if _truthy(draft) else "pr-created"
    else:
        outcome = "bailed"
    if _truthy(bail_user) and outcome == "bailed":
        outcome = "bailed-needs-user-input"
    succeeded = outcome in {"merged", "force-merged-externally", "pr-created", "pr-created-draft", "forked-dry-run"} and not any_stall
    merge_downgraded = (
        outcome == "pr-created"
        and _truthy(seed.get("MERGE", "false"))
        and not _truthy(merge)
        and classification.get("STALL_STEP") == "5"
        and classification.get("RESUME_HINT") == "step8-shippr"
        and _text_file_contains(path=tmpdir / "execution-issues.md", needle="panel-failed")
    )
    return {
        "IMPLEMENT_NORMALIZED_OUTCOME": outcome,
        "IMPLEMENT_OUTCOME_SUCCEEDED": "true" if succeeded else "false",
        "IMPLEMENT_MERGE_DOWNGRADED": "true" if merge_downgraded else "false",
        "IMPLEMENT_ANY_STALL_TRACKING": "true" if any_stall else "false",
        "IMPLEMENT_MEMORY_STALL_TRACKING": memory_stall or "false",
        "IMPLEMENT_SHIP_STALL_TRACKING": ship_stall or "false",
        "IMPLEMENT_FINALIZE_STALL_TRACKING": fin_stall or "false",
        "IMPLEMENT_SESSION_STALL_TRACKING": ses_stall or "false",
        "IMPLEMENT_MERGE_RESULT": merge_result,
        "IMPLEMENT_PR_NUMBER": pr_number,
        "IMPLEMENT_DRAFT": draft or "false",
        "IMPLEMENT_MERGE": merge,
        "IMPLEMENT_FORKED_TARGET": forked or "false",
        "IMPLEMENT_CI_PASSED": ci_passed or "false",
        "IMPLEMENT_DESIGN_ONLY_DONE": design_done or "false",
        "IMPLEMENT_BAIL_NEEDS_USER_INPUT": bail_user or "false",
    }

def normalize_outcome(args: argparse.Namespace) -> int:
    for key, value in normalized_outcome_values(args).items():
        emit(key=key, value=value)
    return 0


_ISSUE_STDOUT_KEY_RE = re.compile(
    r"^(ISSUES_(CREATED|FAILED|DEDUPLICATED)|"
    r"ISSUE_1_(FAILED|NUMBER|URL|DUPLICATE|DUPLICATE_OF_NUMBER|DUPLICATE_OF_URL))="
)
_ISSUE_STDOUT_KEY_LIKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*=")


def _filter_issue_stdout(text: str) -> dict[str, str]:
    records: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.replace("\r", " ")
        if _ISSUE_STDOUT_KEY_RE.match(line):
            key, value = line.split("=", 1)
            records.append((key, value))
        elif records and not _ISSUE_STDOUT_KEY_LIKE_RE.match(line):
            key, value = records[-1]
            records[-1] = (key, value + " " + line)
    filtered: dict[str, str] = {}
    for key, value in records:
        filtered[key] = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    return filtered


def _issue_value_is_url(url: str) -> bool:
    return bool(re.match(r"https://github\.com/.+/.+/issues/\d+$", url or ""))


def normalize_issue_env(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    out = Path(args.issue_stdout_file)
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=out):
        print("stall-recovery: --issue-stdout-file outside implement tmpdir", file=sys.stderr)
        return 1
    env = tmpdir / "stall-recovery-issue.env"
    def fail(reason: str) -> int:
        with contextlib.suppress(OSError):
            env.unlink()
        emit(key="NORMALIZED", value="false")
        emit(key="REASON", value=reason)
        return 0
    if args.issue_exit_code is None:
        return fail("issue-exit-code-missing")
    exit_code = str(args.issue_exit_code)
    if not exit_code.isdigit():
        print("stall-recovery: --issue-exit-code must be a non-negative integer", file=sys.stderr)
        return 2
    if exit_code != "0":
        return fail("issue-exit-code")
    text = out.read_text(encoding="utf-8", errors="replace") if out.is_file() else ""
    filtered = _filter_issue_stdout(text)
    issues_failed = filtered.get("ISSUES_FAILED", "")
    if issues_failed != "0":
        if not issues_failed or not issues_failed.isdigit():
            return fail("issues-failed-invalid")
        return fail("issues-failed-nonzero")
    if _truthy(filtered.get("ISSUE_1_FAILED", "")):
        return fail("issue-1-failed")
    issue_number = filtered.get("ISSUE_1_NUMBER", "")
    issue_url = filtered.get("ISSUE_1_URL", "")
    duplicate = filtered.get("ISSUE_1_DUPLICATE", "")
    duplicate_number = filtered.get("ISSUE_1_DUPLICATE_OF_NUMBER", "")
    duplicate_url = filtered.get("ISSUE_1_DUPLICATE_OF_URL", "")
    if (
        (_truthy(duplicate) or not issue_number)
        and duplicate_number
        and (_issue_value_is_url(duplicate_url) or not _issue_value_is_url(issue_url))
    ):
        issue_number = duplicate_number
        issue_url = duplicate_url
    if not issue_number or not issue_number.isdigit():
        return fail("issue-number-missing")
    if not _issue_value_is_url(issue_url):
        return fail("issue-url-missing")
    write_kvs(path=env, values={"ISSUE_NUMBER": issue_number, "ISSUE_URL": issue_url})
    emit(key="NORMALIZED", value="true")
    emit(key="ISSUE_NUMBER", value=issue_number)
    emit(key="ISSUE_URL", value=issue_url)
    return 0


def _validate_artifact_prefix(prefix: str) -> bool:
    if not prefix:
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9]+(-[A-Za-z0-9]+)*", prefix))


def _artifact_path(*, tmpdir: Path, default_name: str, prefix: str) -> Path:
    if not prefix or prefix == "stall-recovery":
        return tmpdir / default_name
    return tmpdir / (prefix + default_name.removeprefix("stall-recovery"))


def _append_ledger_row_atomic(*, ledger: Path, row: str) -> bool:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    old = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
    if old and not old.endswith("\n"):
        old += "\n"
    content = old + row
    tmp = ledger.with_suffix(ledger.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(ledger)
        written = ledger.read_text(encoding="utf-8")
        return row.rstrip("\n") in written
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        return False


def record_escalation(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    prefix = getattr(args, "artifact_prefix", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return 2

    def hard_fail(reason: str) -> int:
        _append_record_escalation_tool_failure(tmpdir=tmpdir, reason=reason)
        return 1

    site = args.site
    trigger = args.trigger
    step = args.step
    phase = args.phase
    dispatcher = args.dispatcher
    exit_code = args.exit_code
    if not _safe_token(kind="site", value=site, generic=generic) or not _safe_token(kind="trigger", value=trigger, generic=generic):
        print("stall-recovery: record-escalation token validation failed", file=sys.stderr)
        return hard_fail("token-validation-failed")
    if not _safe_token(kind="step", value=step, generic=generic) or not _safe_token(kind="phase", value=phase, generic=generic):
        print("stall-recovery: record-escalation token validation failed", file=sys.stderr)
        return hard_fail("token-validation-failed")
    rel_log = ""
    detail_log = getattr(args, "failure_detail_log", "") or ""
    if detail_log:
        detail_path = Path(detail_log)
        if not validate_failure_detail_log(tmpdir=tmpdir, path=detail_path):
            print("stall-recovery: --failure-detail-log invalid", file=sys.stderr)
            return hard_fail("failure-detail-log-invalid")
        try:
            rel = detail_path.resolve().relative_to(tmpdir.resolve())
            rel_log = str(rel)
        except ValueError:
            rel_log = "redacted"
    ledger = _artifact_path(tmpdir=tmpdir, default_name="stall-recovery-escalation-ledger.tsv", prefix=prefix)
    fallback = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix)
    marker = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=prefix)
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=ledger):
        print("stall-recovery: record-escalation ledger path invalid", file=sys.stderr)
        return hard_fail("ledger-path-invalid")
    safe_dispatcher = _safe_dispatcher_value(dispatcher, generic=generic)
    raw_exit_code = str(exit_code or "")
    safe_exit_code = raw_exit_code if re.fullmatch(r"[0-9]+|unknown", raw_exit_code) else "unknown"
    row = (
        f"utc={datetime.now(UTC).isoformat()}\tsite={site}\ttrigger={trigger}\tstep={step}\tphase={phase}"
        f"\tdispatcher={safe_dispatcher}\texit_code={safe_exit_code}\tfailure_detail_log={rel_log}\n"
    )
    try:
        if ledger.is_file() and not os.access(ledger, os.W_OK):
            raise OSError("canonical-ledger-not-writable")
        if _append_ledger_row_atomic(ledger=ledger, row=row):
            emit(key="ESCALATION_RECORDED", value="true")
            emit(key="ESCALATION_LEDGER_FILE", value=ledger)
        else:
            raise OSError("canonical-ledger-write-failed")
    except OSError:
        marker = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=prefix)
        fallback = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix)
        if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=fallback) or not _validate_tmpdir_write_path(tmpdir=tmpdir, path=marker):
            print("stall-recovery: record-escalation fallback path invalid", file=sys.stderr)
            return hard_fail("fallback-path-invalid")
        marker.write_text("RECORD_ESCALATION_FAILED=true\nREASON=canonical-ledger-not-writable\n", encoding="utf-8")
        fallback.write_text(row, encoding="utf-8")
        emit(key="ESCALATION_RECORDED", value="false")
        emit(key="ESCALATION_FALLBACK_WRITTEN", value="true")
    return 0


def compose_report(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.is_dir():
        print("stall-recovery: --implement-tmpdir must exist", file=sys.stderr)
        return 1
    kind = str(getattr(args, "report_kind", "") or "terminal-failure")
    surface = str(getattr(args, "surface", "") or "chat-print")
    if kind not in {"terminal-failure", "escalation-success"}:
        print("stall-recovery: --report-kind must be terminal-failure or escalation-success", file=sys.stderr)
        return 1
    if surface not in {"issue-input", "chat-print"}:
        print("stall-recovery: --surface must be issue-input or chat-print", file=sys.stderr)
        return 1

    prefix = getattr(args, "artifact_prefix", "") or ""
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return 2
    profile = getattr(args, "profile", "implement") or "implement"
    class_file = _compose_path(args=args, attr="classification_file", tmpdir=tmpdir, default_name=_DEFAULT_CLASSIFICATION_FILE, prefix=prefix)
    attempts_file = _compose_path(args=args, attr="attempts_file", tmpdir=tmpdir, default_name=_DEFAULT_ATTEMPTS_FILE, prefix=prefix)
    ledger = _compose_path(args=args, attr="escalation_ledger_file", tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_LEDGER, prefix=prefix)
    fallback = _compose_path(args=args, attr="escalation_fallback_file", tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix)
    marker = _compose_path(args=args, attr="record_failure_marker", tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=prefix)
    root_file = _compose_path(args=args, attr="root_cause_file", tmpdir=tmpdir, default_name=_DEFAULT_ROOT_CAUSE_FILE, prefix=prefix)
    bounded_file = _compose_path(args=args, attr="bounded_root_cause_file", tmpdir=tmpdir, default_name=_DEFAULT_BOUNDED_ROOT_CAUSE_FILE, prefix=prefix)
    title_file = _compose_path(args=args, attr="title_file", tmpdir=tmpdir, default_name=_DEFAULT_TITLE_FILE, prefix=prefix)
    sensitive_file = _compose_path(args=args, attr="sensitive_corpus_file", tmpdir=tmpdir, default_name=_DEFAULT_SENSITIVE_CORPUS, prefix=prefix)
    session_env_file = Path(getattr(args, "session_env_file", "") or tmpdir / "session-env.sh")
    default_output = _DEFAULT_ISSUE_INPUT if surface == "issue-input" else _DEFAULT_CHAT_PRINT
    out_file = _compose_path(args=args, attr="output_file", tmpdir=tmpdir, default_name=default_output, prefix=prefix)

    if kind == "escalation-success" and not class_file.exists():
        if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=class_file):
            return _compose_error("--classification-file outside implement tmpdir")
        write_kvs(path=class_file, values={
            "FAILURE_CLASS": "",
            "FAILURE_SIGNATURE": hashlib.sha256(b"escalation-success").hexdigest(),
            "RESUME_HINT": "none",
            "STALL_STEP": "unknown",
            "PHASE": "unknown",
            "STALL_TRACKING": "false",
            "BAIL_REASON": "",
            "EXIT_CODE": "unknown",
            "MATCHED_CLASSIFIER_PATTERN": "no-stall",
            "DISPATCHER": "unknown",
        })
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=class_file):
        return _compose_error("--classification-file invalid")
    if attempts_file.exists():
        if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=attempts_file):
            return _compose_error("--attempts-file invalid")
    else:
        if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=attempts_file):
            return _compose_error("--attempts-file outside implement tmpdir")
        write_kvs(path=attempts_file, values={"version": 1, "created_utc": datetime.now(UTC).isoformat(), "attempt_count": 0})
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=out_file):
        return _compose_error("--output-file outside implement tmpdir")
    for label, path in (
        ("--escalation-ledger-file", ledger),
        ("--escalation-fallback-file", fallback),
        ("--record-failure-marker", marker),
        ("--title-file", title_file),
    ):
        if path.exists() and not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=path):
            return _compose_error(f"{label} invalid")
    if kind == "escalation-success" and not any(path.is_file() and path.stat().st_size > 0 for path in (ledger, fallback, marker)) and not _record_escalation_tool_failure_present(tmpdir):
        return _compose_error("escalation-success report requires escalation evidence")
    if surface == "issue-input" and not _tier_a_allowed(tmpdir=tmpdir, args=args):
        return _compose_error("issue-input surface requires larch dev clone and non-forked target")
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=root_file) or not _validate_root_cause_artifact(root_file):
        return _compose_error("--root-cause-file invalid")

    verdict = _parse_root_cause_file(path=root_file, key="verdict", default="")
    summary = _parse_root_cause_file(path=root_file, key="summary", default="")
    if verdict == "operator-action":
        record = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_OPERATOR_ACTION_RECORD, prefix=prefix)
        sentinel = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_OPERATOR_ACTION_SENTINEL, prefix=prefix)
        record.write_text(f"REPORT_KIND={kind}\nVERDICT=operator-action\nROOT_CAUSE_FILE={root_file}\n", encoding="utf-8")
        sentinel.write_text("STALL_RECOVERY_OPERATOR_ACTION=true\n", encoding="utf-8")
        emit(key="STALL_RECOVERY_REPORT_KIND", value=kind)
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="skipped_operator_action")
        emit(key="STALL_RECOVERY_REPORT_TIER", value="skipped")
        emit(key="STALL_RECOVERY_REPORT_ARTIFACT", value=record)
        emit(key="STALL_RECOVERY_REPORT_VERDICT", value="operator-action")
        return 0

    title = _safe_title_summary(title_file.read_text(encoding="utf-8", errors="replace") if title_file.is_file() else "")
    if not title:
        title = _safe_title_summary(summary)
    if not title:
        return _compose_error("unsafe title and root-cause summary")
    skill_label = _report_skill_label(profile=profile, prefix=prefix)
    if kind == "terminal-failure":
        title = f"[Bug] {skill_label} terminal: {title} ({_safe_class_value(read_kv(path=class_file, key='FAILURE_CLASS', default='unrecoverable'))} at {_safe_step_value(read_kv(path=class_file, key='STALL_STEP', default=''))})"
    else:
        site = _first_escalation_field(field_name="site", ledger=ledger, fallback=fallback)
        trigger = _first_escalation_field(field_name="trigger", ledger=ledger, fallback=fallback)
        title = f"[Bug] {skill_label} escalation: {title} ({site or 'redacted'}:{trigger or 'redacted'})"
    report_sig = _report_dedup_signature(kind=kind, class_file=class_file, ledger=ledger, fallback=fallback, profile=profile, prefix=prefix, skill_label=skill_label)

    if surface == "issue-input":
        tier = "A"
        body = _report_marker(report_sig) + "\n" + _compose_tier_a_issue(kind=kind, class_file=class_file, attempts_file=attempts_file, ledger=ledger, fallback=fallback, marker=marker, root_file=root_file, title=title, tmpdir=tmpdir, session_env_file=session_env_file)
        redacted_body = _redact_text(body)
        if redacted_body is None:
            return _compose_redaction_failed()
        if not _write_tier_a_comment_payloads(tmpdir=tmpdir, attempts_file=attempts_file, ledger=ledger, fallback=fallback, marker=marker, root_file=root_file, prefix=prefix):
            return _compose_redaction_failed()
        body = redacted_body
    else:
        tier = "B"
        if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=sensitive_file):
            return _compose_error("--sensitive-corpus-file invalid")
        if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=bounded_file) or not _validate_root_cause_artifact(bounded_file):
            return _compose_error("--bounded-root-cause-file invalid")
        effective = tmpdir / f"{(prefix or 'stall-recovery')}-sensitive-corpus.effective"
        build_sensitive_corpus_from_evidence(
            tmpdir=tmpdir,
            sensitive_file=sensitive_file,
            class_file=class_file,
            attempts_file=attempts_file,
            ledger=ledger,
            fallback=fallback,
            marker=marker,
            out_file=effective,
        )
        if _sensitive_token_rejects_file(corpus_path=effective, candidate_path=bounded_file):
            with contextlib.suppress(OSError):
                effective.unlink()
            return _compose_error("bounded root-cause contains sensitive token")
        body = f"### {title}\n\n{_report_marker(report_sig)}\n" + _compose_tier_b_projection(kind=kind, class_file=class_file, attempts_file=attempts_file, ledger=ledger, fallback=fallback, marker=marker, root_file=root_file, bounded_file=bounded_file, skill_label=skill_label, session_env_file=session_env_file)
        raw_candidate = out_file.with_suffix(out_file.suffix + ".raw-check")
        raw_candidate.write_text(body, encoding="utf-8")
        if _sensitive_token_rejects_file(corpus_path=effective, candidate_path=raw_candidate):
            with contextlib.suppress(OSError):
                effective.unlink()
                raw_candidate.unlink()
            return _compose_error("chat-print contains sensitive token")
        with contextlib.suppress(OSError):
            effective.unlink()
            raw_candidate.unlink()
        _write_tier_b_comment_payloads(tmpdir=tmpdir, attempts_file=attempts_file, ledger=ledger, fallback=fallback, marker=marker, bounded_file=bounded_file, prefix=prefix)

    if surface == "chat-print":
        redacted_body = _redact_text(body)
        if redacted_body is None:
            return _compose_redaction_failed()
        body = redacted_body

    out_file.write_text(body, encoding="utf-8")
    dry_run = _truthy(os.environ.get("LARCH_STALL_RECOVERY_DRY_RUN")) or _truthy(os.environ.get("DRY_RUN_DECISION"))
    emit(key="STALL_RECOVERY_REPORT_KIND", value=kind)
    emit(key="STALL_RECOVERY_REPORT_TIER", value=tier)
    emit(key="STALL_RECOVERY_REPORT_ARTIFACT", value=out_file)
    emit(key="STALL_RECOVERY_REPORT_VERDICT", value=verdict)
    emit(key="REPORT_DEDUP_SIGNATURE", value=report_sig)
    emit(key="DRY_RUN_DECISION", value="true" if dry_run else "false")
    if dry_run:
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="dry-run")
        return 0
    if surface == "issue-input" and _truthy(os.environ.get("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES")) and not _truthy(os.environ.get("LARCH_STALL_RECOVERY_ENABLE_TEST_FILING")):
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="printed")
        return 0
    if surface == "chat-print":
        _emit_chat_print_filing_status(tmpdir=tmpdir, out_file=out_file, title=title, sensitive_file=sensitive_file, prefix=prefix)
    return 0


def _emit_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            print(line)


def dedup_tier_a_report(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    if os.environ.get("LARCH_STALL_RECOVERY_DRY_RUN"):
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="dry-run")
        return 0
    prefix = getattr(args, "artifact_prefix", "") or ""
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return 2
    body_file = _compose_path(args=args, attr="body_file", tmpdir=tmpdir, default_name=_DEFAULT_ISSUE_INPUT, prefix=prefix)
    attempts_file = _compose_path(args=args, attr="attempts_file", tmpdir=tmpdir, default_name=_DEFAULT_TIER_A_ATTEMPTS_SLICE, prefix=prefix)
    escalation_file = _compose_path(args=args, attr="escalation_ledger_file", tmpdir=tmpdir, default_name=_DEFAULT_TIER_A_ESCALATION_SLICE, prefix=prefix)
    root_file = _compose_path(args=args, attr="root_cause_file", tmpdir=tmpdir, default_name=_DEFAULT_TIER_A_ROOT_CAUSE_SLICE, prefix=prefix)
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=body_file):
        print("stall-recovery: --body-file outside implement tmpdir", file=sys.stderr)
        return 1
    for label, slice_file in (
        ("--attempts-file", attempts_file),
        ("--escalation-ledger-file", escalation_file),
        ("--root-cause-file", root_file),
    ):
        if slice_file.is_file() and not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=slice_file):
            print(f"stall-recovery: {label} outside implement tmpdir", file=sys.stderr)
            return 1
    for slice_file in (attempts_file, escalation_file, root_file):
        if not slice_file.is_file():
            if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=slice_file):
                print("stall-recovery: dedup slice path outside implement tmpdir", file=sys.stderr)
                return 1
            slice_file.write_text("", encoding="utf-8")
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    helper = plugin_root / "scripts" / "file-failure-report-cross-repo.sh"
    if not helper.is_file():
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="lookup-failed-open")
        emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value="helper-missing")
        return 0
    repo_proc = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], text=True, capture_output=True, check=False)  # noqa: S607
    repo = repo_proc.stdout.strip()
    if not repo:
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="lookup-failed-open")
        emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value="current-repo-unresolved")
        return 0
    out = tmpdir / "stall-recovery-tier-a-dedup.env"
    with out.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [
                str(helper),
                "--repo",
                repo,
                "--body-file",
                str(body_file),
                "--dedup-only",
                "--publication-tier",
                "tier-a",
                "--attempts-file",
                str(attempts_file),
                "--escalation-ledger-file",
                str(escalation_file),
                "--root-cause-file",
                str(root_file),
            ],
            stdout=handle,
            check=False,
        )
    _emit_env_file(out)
    return 0


def _reject_rawish_token_value(value: str) -> bool:
    if any(ch in value for ch in "\n\r "):
        return True
    if ".." in value or "/" in value:
        return True
    lower = value.lower()
    return any(token in lower for token in ("http://", "https://", "github.com", "`", "<script", "<!--"))


def validate_token(args: argparse.Namespace) -> int:
    token = args.token or ""
    kind = getattr(args, "token_kind", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if not token or _reject_rawish_token_value(token):
        emit(key="TOKEN_VALID", value="false")
        return 1
    if kind == "bail":
        valid = _safe_bail_reason_value(token, generic=generic)
    elif kind:
        valid = _safe_token(kind=kind, value=token, generic=generic)
    else:
        valid = True
    if kind and not valid:
        emit(key="TOKEN_VALID", value="false")
        return 1
    emit(key="TOKEN_VALID", value="true")
    return 0


_TERMINAL_STATE_ALLOWED_KEYS = {
    "DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME", "SUMMARY_OUTCOME",
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE",
    "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT", "ROOT_CAUSE_HINT", "OCCURRED_AT", "EVIDENCE_REF",
}
_TERMINAL_STATE_REQUIRED_KEYS = {
    "DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME",
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE",
    "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT",
}


def _reject_rawish_terminal_value(value: str) -> bool:
    if any(ch in value for ch in "\n\r"):
        return True
    lower = value.lower()
    return any(token in lower for token in ("http://", "https://", "github.com", "/users/", "/home/", " larch ", "```"))


def _safe_bail_reason_value(value: str, *, generic: bool) -> bool:
    if not value:
        return True
    if generic and value in _GENERIC_BAILS:
        return True
    if value in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
        return True
    if re.fullmatch(r"ci-local-unfixable:[A-Za-z0-9_,-]+", value):
        return True
    expanded = {
        "adopted-issue-closed", "adopted-issue-is-pr", "branch-create-failed", "ci-fix-exhausted",
        "dirty-state-after-timeout", "dirty-tree", "fix-attempts-exhausted", "main-branch-post-dispatch",
        "orchestrator-envelope-invalid", "protected-path-edit-required-out-of-scope", "qa-loop-exceeded",
        "recovery-out-of-scope", "review-required", "run-flags-persist-failed", "ship-pr-internal-lint-fix",
        "tracking-init-failed", "wrapper-validation-failure", "branch-changed", "cap_hit",
        "codex-runtime-failure", "cursor-bailed-no-reason", "cursor-modified-history", "cursor-runtime-failure",
        "detached-head-prohibited", "interactive-subprocess-unsupported", "main-branch-prohibited",
        "manifest-missing", "manifest-oos-materialization-failed", "manifest-schema-invalid",
        "protected-path-modified", "protected-path-modification-required",
        "qa-pending-missing", "redactor-not-executable", "resume-incompatible",
        "submodule-dirty", "submodule-edit-required-out-of-scope", "local-unfixable", "checks-failed",
        "checks-timeout", "ci-health-failed", "ci-timeout", "ci-status-error", "ci-too-many-rebases",
        "no-fix-path", "main-agent-required", "coder-main-agent-required", "main-agent-vote-required",
    }
    return value in expanded


def _safe_source_script_value(value: str, *, generic: bool) -> bool:
    if value in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"}:
        return True
    return generic and value in _GENERIC_SOURCE_SCRIPTS


def _render_safe_bail_reason_value(value: str, *, generic: bool) -> str:
    if not value:
        return ""
    return value if _safe_bail_reason_value(value, generic=generic) else "redacted"


def _render_safe_source_script_value(value: str, *, generic: bool) -> str:
    if not value:
        return "unknown"
    return value if _safe_source_script_value(value, generic=generic) else "redacted"


def _terminal_state_value_valid(*, key: str, value: str, tmpdir: Path, generic: bool) -> bool:
    if key == "DESIGN_FAILURE_VERSION":
        return value == "1"
    if key == "DESIGN_FAILURE_KIND":
        return value == "terminal"
    if key in {"FAILURE_OUTCOME", "SUMMARY_OUTCOME"}:
        return _safe_outcome(value)
    if key == "STALL_STEP":
        return _safe_step(value, generic=generic)
    if key == "PHASE":
        return value in _COMMON_PHASES or (generic and value in _GENERIC_PHASES)
    if key == "SITE":
        return _safe_token(kind="site", value=value, generic=generic)
    if key == "TRIGGER":
        return _safe_token(kind="trigger", value=value, generic=generic)
    if key == "BAIL_REASON":
        return _safe_bail_reason_value(value, generic=generic)
    if key == "EXIT_CODE":
        return value == "unknown" or (value.isdigit() and re.fullmatch(r"[0-9]+", value) is not None)
    if key == "FAILURE_DETAIL_LOG":
        if not value:
            return True
        return _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=Path(value))
    if key == "SOURCE_SCRIPT":
        return _safe_source_script_value(value, generic=generic)
    if key == "ROOT_CAUSE_HINT":
        return not value or value in {"larch-defect", "environment", "operator-action"}
    if key in {"OCCURRED_AT", "EVIDENCE_REF"}:
        return not value or not _reject_rawish_terminal_value(value)
    return False


def _validated_terminal_state_values(*, tmpdir: Path, state_file: Path, generic: bool) -> dict[str, str] | None:
    if not tmpdir.is_dir() or not state_file.is_file():
        return None
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=state_file):
        return None
    found: dict[str, str] = {}
    for raw in state_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return None
        k, v = line.split("=", 1)
        if k not in _TERMINAL_STATE_ALLOWED_KEYS:
            return None
        found[k] = v
    for required in _TERMINAL_STATE_REQUIRED_KEYS:
        if required not in found:
            return None
        if required != "FAILURE_DETAIL_LOG" and not found[required]:
            return None
    for key, value in found.items():
        if key == "FAILURE_DETAIL_LOG":
            if not _terminal_state_value_valid(key=key, value=value, tmpdir=tmpdir, generic=generic):
                return None
            continue
        if _reject_rawish_terminal_value(value):
            return None
        if not _terminal_state_value_valid(key=key, value=value, tmpdir=tmpdir, generic=generic):
            return None
    return found


def validate_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    state_file = Path(getattr(args, "primary_state_file", None) or tmpdir / "design-failure-terminal-state.env")
    if _validated_terminal_state_values(tmpdir=tmpdir, state_file=state_file, generic=generic) is None:
        emit(key="VALID", value="false")
        return 1
    emit(key="VALID", value="true")
    return 0


_SENSITIVE_TOKEN_ALLOWLIST = frozenset({
    "larch-defect", "environment", "operator-action", "terminal-failure", "escalation-success",
    "merged", "force-merged-externally", "pr-created", "pr-created-draft", "forked-dry-run",
    "main-agent-required", "lint-fix-loop", "ship-pr", "codex", "cursor", "claude", "approved",
    "approved-partition", "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail",
})


_SENSITIVE_ASSIGNMENT_RE = re.compile(r"(?:^|[\s(])([A-Z][A-Z0-9_]{2,})=([^\s]{3,})")


def _candidate_has_sensitive_assignment(candidate_text: str) -> bool:
    for match in _SENSITIVE_ASSIGNMENT_RE.finditer(candidate_text):
        value = match.group(2).rstrip(".,;:)")
        key = match.group(1)
        if key in {"RUN_ID", "LARCH_TOKEN_SESSION_ID"} and re.fullmatch(r"[A-Za-z0-9._:-]+", value):
            continue
        if key in {"LARCH_PLUGIN_VERSION", "LARCH_VERSION"} and re.fullmatch(r"[A-Za-z0-9._+-]+", value):
            continue
        if not _sensitive_value_is_allowlisted(value):
            return True
    return False


def _sensitive_token_rejects_file(*, corpus_path: Path, candidate_path: Path) -> bool:
    if not corpus_path.is_file():
        return False
    try:
        corpus_text = corpus_path.read_text(encoding="utf-8", errors="replace")
        candidate_text = candidate_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    for token in corpus_text.splitlines():
        stripped = token.strip()
        if not stripped or re.fullmatch(r"[A-Za-z0-9_-]", stripped):
            continue
        if stripped in _SENSITIVE_TOKEN_ALLOWLIST:
            continue
        if _sensitive_value_is_allowlisted(stripped):
            continue
        if "=" in stripped:
            _, _, value = stripped.partition("=")
            if value in _SENSITIVE_TOKEN_ALLOWLIST:
                continue
            if _sensitive_value_is_allowlisted(value):
                continue
            if value and value not in {"", stripped} and value in candidate_text:
                return True
        if stripped in candidate_text:
            return True
    if re.search(r"https?://|git@github\.com:|github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", candidate_text):
        return True
    if re.search(r"(^|[\s`(])/(Users|home|private|tmp|var|Volumes)/[^\s`)]+", candidate_text):
        return True
    if re.search(r"(^|[\s`(])[A-Za-z0-9_.-]{2,}/[A-Za-z0-9_./-]{2,}", candidate_text):
        return True
    return _candidate_has_sensitive_assignment(candidate_text)


def _sensitive_value_is_allowlisted(value: str) -> bool:
    if value in {"", "true", "false", "TRUE", "FALSE", "True", "False", "unknown", "none", "n/a", "N/A", "-"}:
        return True
    if value.isdigit() and len(value) <= SAFE_SMALL_INTEGER_DIGITS:
        return True
    if _safe_bail_reason_value(value, generic=True):
        return True
    if _safe_step(value, generic=True):
        return True
    if _safe_token(kind="phase", value=value, generic=True):
        return True
    if _safe_token(kind="site", value=value, generic=True):
        return True
    if _safe_token(kind="trigger", value=value, generic=True):
        return True
    if value in {
        "lint-failure", "test-failure", "transient-infra", "dispatch-failure", "protected-path",
        "submodule-restricted", "unrecoverable", "same-cause-repeat", "contract-failure",
        "ci-fix-exhausted", "no-stall", "fallback", "bail-token", "step-contract",
        "transient-output", "test-output", "lint-output", "lint-fix-bail-token",
        "dispatch-output", "dispatch-bail-token", "terminal-bail", "terminal-step",
        "rebase-transient", "recovery-out-of-scope", "ci-fix-exhausted-with-detail",
        "step2-impl", "step5-review", "step8-shippr",
    }:
        return True
    if _safe_token(kind="source-script", value=value, generic=True):
        return True
    if _safe_matched_pattern_value(value) != "redacted":
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9._+-]+", value) and value in {"codex", "cursor", "claude", "bash", "python", "split-path"})


def build_sensitive_corpus_from_evidence(
    *,
    tmpdir: Path,
    sensitive_file: Path,
    class_file: Path,
    attempts_file: Path,
    ledger: Path,
    fallback: Path,
    marker: Path,
    out_file: Path,
) -> None:
    sources = [
        sensitive_file,
        class_file,
        attempts_file,
        ledger,
        fallback,
        marker,
        tmpdir / "ship-pr-state.sh",
        tmpdir / "finalize-state.sh",
        tmpdir / "session-env.sh",
        tmpdir / "source-env.sh",
        tmpdir / "execution-issues.md",
        tmpdir / "run-log-pointer.txt",
        tmpdir / "plan.txt",
        tmpdir / "feature-description.txt",
        tmpdir / "issue-body.txt",
        tmpdir / "composed-plan.md",
        tmpdir / "final-summary.md",
        tmpdir / "validate-plan-commands.log",
        tmpdir / "design-log-publish.failure.log",
        tmpdir / "design-plan-write.failure.log",
        tmpdir / "design-publish-tail.failure.log",
    ]
    detail_log = read_kv(path=class_file, key="FAILURE_DETAIL_LOG", default="")
    if detail_log:
        detail_path = Path(detail_log)
        _, detail_valid = _read_validated_failure_detail_log(tmpdir=tmpdir, path=detail_path)
        if detail_valid:
            sources.append(detail_path)
    lines: list[str] = []
    for src in sources:
        if src.is_file() and not src.is_symlink():
            with contextlib.suppress(OSError):
                text = src.read_text(encoding="utf-8", errors="replace")
                lines.extend(text.splitlines())
                lines.extend(re.findall(r"https?://[^\s`)\]]+", text))
                lines.extend(re.findall(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text))
                lines.extend(re.findall(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text))
                lines.extend(
                    match.group(0).strip()
                    for match in re.finditer(r"(?:^|[\s`(])/(?:Users|home|private|tmp|var|Volumes)/[^\s`)]+", text, re.MULTILINE)
                )
    out_file.write_text("\n".join(line.strip() for line in lines if line.strip()) + "\n", encoding="utf-8")


def validate_tier_b_public_file(args: argparse.Namespace) -> int:
    path = Path(args.public_file)
    tmpdir = Path(args.tmpdir) if args.tmpdir else Path(args.implement_tmpdir)
    if not (path.is_absolute() and not path.is_symlink() and path.is_file()):
        emit(key="PUBLIC_FILE_VALID", value="false")
        return 1
    if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
        emit(key="PUBLIC_FILE_VALID", value="false")
        return 1
    corpus_path_str = getattr(args, "sensitive_corpus_file", None)
    if not corpus_path_str:
        emit(key="PUBLIC_FILE_VALID", value="false")
        return 1
    cp = Path(corpus_path_str)
    if not (cp.is_absolute() and not cp.is_symlink() and (cp == tmpdir or tmpdir in cp.parents) and cp.is_file()):
        emit(key="PUBLIC_FILE_VALID", value="false")
        return 1
    effective = tmpdir / f"{(getattr(args, 'artifact_prefix', '') or 'stall-recovery')}-sensitive-corpus.public.effective"
    build_sensitive_corpus_from_evidence(
        tmpdir=tmpdir,
        sensitive_file=cp,
        class_file=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_CLASSIFICATION_FILE, prefix=getattr(args, "artifact_prefix", "") or ""),
        attempts_file=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ATTEMPTS_FILE, prefix=getattr(args, "artifact_prefix", "") or ""),
        ledger=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_LEDGER, prefix=getattr(args, "artifact_prefix", "") or ""),
        fallback=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=getattr(args, "artifact_prefix", "") or ""),
        marker=_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=getattr(args, "artifact_prefix", "") or ""),
        out_file=effective,
    )
    try:
        if _sensitive_token_rejects_file(corpus_path=effective, candidate_path=path):
            emit(key="PUBLIC_FILE_VALID", value="false")
            return 1
    except OSError:
        emit(key="PUBLIC_FILE_VALID", value="false")
        return 1
    with contextlib.suppress(OSError):
        effective.unlink()
    emit(key="PUBLIC_FILE_VALID", value="true")
    return 0


def _state_layer_paths(tmpdir: Path) -> list[Path]:
    return [tmpdir / name for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh")]


def _state_file_syntax_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return False
    return True


def _rewrite_state_keys(*, path: Path, updates: Mapping[str, str]) -> bool:
    if path.is_symlink() or not path.is_file() or not os.access(path, os.W_OK):
        return False
    existing: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            existing[key] = value
    existing.update(updates)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text("".join(f"{key}={value}\n" for key, value in existing.items()), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        return False
    return True


def clear_stall(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    for name in ("stall-recovery-classification.env", "stall-recovery-issue.env"):
        with contextlib.suppress(OSError):
            (tmpdir / name).unlink()
    present = False
    for path in _state_layer_paths(tmpdir):
        if path.is_symlink() and not path.exists():
            emit(key="CLEARED", value="false")
            return 3
        if not path.exists():
            continue
        present = True
        if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK | os.W_OK):
            emit(key="CLEARED", value="false")
            return 3
        if not _state_file_syntax_ok(path):
            emit(key="CLEARED", value="false")
            return 3
    if not present:
        emit(key="CLEARED", value="true")
        return 0
    for path in _state_layer_paths(tmpdir):
        if not path.is_file():
            continue
        if not _rewrite_state_keys(path=path, updates={
                "STALL_TRACKING": "false",
                "STALL_STEP": "",
                "BAIL_REASON": "",
                "IMPLEMENT_BAIL_REASON": "",
                "EXIT_CODE": "unknown",
            }):
            emit(key="CLEARED", value="false")
            return 1
        if read_kv(path=path, key="STALL_TRACKING") != "false" or read_kv(path=path, key="STALL_STEP") != "":
            emit(key="CLEARED", value="false")
            return 1
    emit(key="CLEARED", value="true")
    return 0


def seed_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    state = tmpdir / "ship-pr-state.sh"
    stall_step_arg = getattr(args, "stall_step", "") or getattr(args, "step", "") or ""
    phase_arg = getattr(args, "phase", "") or ""
    if state.is_symlink() and not state.exists():
        emit(key="SEEDED", value="false")
        return 3
    if state.is_file() and not state.is_symlink() and not _state_file_syntax_ok(state):
        emit(key="SEEDED", value="false")
        return 3
    seed_mode = ""
    step = _safe_step_value(stall_step_arg or read_kv(path=state, key="STALL_STEP", default="8") or "8")
    phase = _safe_phase_value(phase_arg or read_kv(path=state, key="PHASE", default="ci-initial") or "ci-initial")
    if stall_step_arg:
        step = _safe_step_value(stall_step_arg)
    if phase_arg:
        phase = _safe_phase_value(phase_arg)
    if state.is_file() and state.stat().st_size > 0 and any("=" in line for line in state.read_text(encoding="utf-8", errors="replace").splitlines()):
        seed_mode = "rewrite"
        if not _rewrite_state_keys(path=state, updates={"STALL_TRACKING": "true", "STALL_STEP": step, "PHASE": phase}):
            emit(key="SEEDED", value="false")
            return 1
    else:
        seed_mode = "seed"
        tmpdir.mkdir(parents=True, exist_ok=True)
        content = {
            "PHASE": phase,
            "STALL_TRACKING": "true",
            "STALL_STEP": step,
            "BAIL_REASON": "",
            "BAIL_FAILURE_DETAIL_LOG": "",
            "EXIT_CODE": "4",
        }
        tmp = state.with_suffix(state.suffix + ".tmp")
        try:
            tmp.write_text("".join(f"{key}={value}\n" for key, value in content.items()), encoding="utf-8")
            tmp.replace(state)
        except OSError:
            emit(key="SEEDED", value="false")
            return 1
    if read_kv(path=state, key="STALL_TRACKING") != "true":
        emit(key="SEEDED", value="false")
        return 1
    emit(key="SEEDED", value="true")
    emit(key="SEED_MODE", value=seed_mode)
    return 0


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _issue_url_number(url: str) -> str | None:
    match: re.Match[str] | None = re.fullmatch(r"https://github.com/[^/#]+/[^/#]+/issues/(\d+)", url)
    return match.group(1) if match else None


def _validate_tmpdir_local_file(*, tmpdir: Path, file_path: Path) -> bool:
    if not file_path.is_absolute() or file_path.is_symlink() or not file_path.is_file():
        return False
    try:
        _ = file_path.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        return False
    return True


def is_larch_dev_clone(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    forked = read_kv(path=tmpdir / "ship-pr-state.sh", key="FORKED_TARGET") or read_kv(path=tmpdir / "session-env.sh", key="FORKED_TARGET")
    if forked and _truthy(forked):
        emit(key="LARCH_DEV_CLONE", value="false")
        return 0
    root = getattr(args, "working_tree_root", "") or ""
    if not root:
        completed = subprocess.run(["/usr/bin/git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
        root = completed.stdout.strip() if completed.returncode == 0 else ""
    dev_clone = bool(root) and (Path(root) / "skills" / "implement" / "SKILL.md").is_file()
    emit(key="LARCH_DEV_CLONE", value="true" if dev_clone else "false")
    return 0


def normalize_file_failure_report_env(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.is_dir():
        print("stall-recovery: --implement-tmpdir must exist", file=sys.stderr)
        return 1
    env_file = Path(args.file_failure_report_env)
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=env_file):
        print("stall-recovery: --file-failure-report-env invalid", file=sys.stderr)
        return 1
    status = read_kv(path=env_file, key="FILE_FAILURE_REPORT_STATUS")
    url = read_kv(path=env_file, key="FILE_FAILURE_REPORT_URL")
    reason = read_kv(path=env_file, key="FILE_FAILURE_REPORT_FALLBACK_REASON")
    allowed = {"filed", "dry-run", "dedup-comment", "no-match", "fallback-print-required", "lookup-failed-open"}
    if status not in allowed:
        status = "fallback-print-required"
        reason = reason or "helper-status-missing"
    emit(key="STALL_RECOVERY_REPORT_STATUS", value=status)
    if url:
        emit(key="STALL_RECOVERY_REPORT_URL", value=url)
        number = _issue_url_number(url)
        if number:
            emit(key="STALL_RECOVERY_REPORT_ISSUE_URL", value=url)
            emit(key="STALL_RECOVERY_REPORT_ISSUE_NUMBER", value=number)
    if reason:
        emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value=reason)
    return 0


def populate_sensitive_corpus(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    prefix = getattr(args, "artifact_prefix", "") or ""
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return 2
    sensitive_file = Path(args.sensitive_corpus_file) if getattr(args, "sensitive_corpus_file", "") else _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_SENSITIVE_CORPUS, prefix=prefix)
    class_file = Path(args.classification_file) if getattr(args, "classification_file", "") else _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_CLASSIFICATION_FILE, prefix=prefix)
    attempts_file = Path(args.attempts_file) if getattr(args, "attempts_file", "") else _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ATTEMPTS_FILE, prefix=prefix)
    ledger = Path(args.escalation_ledger_file) if getattr(args, "escalation_ledger_file", "") else _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_LEDGER, prefix=prefix)
    fallback = Path(args.escalation_fallback_file) if getattr(args, "escalation_fallback_file", "") else _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix)
    marker = Path(args.record_failure_marker) if getattr(args, "record_failure_marker", "") else _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=prefix)
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=sensitive_file):
        print("stall-recovery: --sensitive-corpus-file outside implement tmpdir", file=sys.stderr)
        return 1
    for label, path in (
        ("--classification-file", class_file),
        ("--attempts-file", attempts_file),
        ("--escalation-ledger-file", ledger),
        ("--escalation-fallback-file", fallback),
        ("--record-failure-marker", marker),
    ):
        if path.is_file() and not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=path):
            print(f"stall-recovery: {label} outside implement tmpdir", file=sys.stderr)
            return 1
    effective = tmpdir / f"{(prefix or 'stall-recovery')}-sensitive-corpus.effective"
    try:
        build_sensitive_corpus_from_evidence(
            tmpdir=tmpdir,
            sensitive_file=sensitive_file,
            class_file=class_file,
            attempts_file=attempts_file,
            ledger=ledger,
            fallback=fallback,
            marker=marker,
            out_file=effective,
        )
        sensitive_file.write_text(effective.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    finally:
        with contextlib.suppress(OSError):
            effective.unlink()
    emit(key="SENSITIVE_CORPUS_FILE", value=sensitive_file)
    return 0


def _compose_error(message: str) -> int:
    print(f"stall-recovery: {message}", file=sys.stderr)
    return 1


def _compose_path(*, args: argparse.Namespace, attr: str, tmpdir: Path, default_name: str, prefix: str) -> Path:
    value = getattr(args, attr, "") or ""
    return Path(value) if value else _artifact_path(tmpdir=tmpdir, default_name=default_name, prefix=prefix)


def _validate_tmpdir_write_path(*, tmpdir: Path, path: Path) -> bool:
    if not path.is_absolute() or path.is_symlink():
        return False
    try:
        resolved_parent = path.parent.resolve(strict=True)
        resolved_tmpdir = tmpdir.resolve(strict=True)
    except OSError:
        return False
    if resolved_parent != resolved_tmpdir and resolved_tmpdir not in resolved_parent.parents:
        return False
    return not path.exists() or (path.is_file() and not path.is_symlink())


def _parse_root_cause_file(*, path: Path, key: str, default: str = "") -> str:
    return read_kv(path=path, key=key, default=default)


def _root_cause_prose(path: Path) -> str:
    lines: list[str] = []
    seen = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            if seen:
                lines.append("")
            continue
        if raw.startswith(("verdict=", "confidence=", "summary=")):
            continue
        seen = True
        lines.append(raw)
    return "\n".join(lines).strip()


def _validate_root_cause_artifact(path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    verdict = _parse_root_cause_file(path=path, key="verdict", default="")
    confidence = _parse_root_cause_file(path=path, key="confidence", default="")
    summary = _parse_root_cause_file(path=path, key="summary", default="")
    if verdict not in {"larch-defect", "environment", "operator-action"}:
        return False
    if confidence not in {"low", "medium", "high"}:
        return False
    if not summary or "\n" in summary or "\r" in summary:
        return False
    return bool(_root_cause_prose(path))


def _safe_title_summary(summary: str) -> str:
    value = summary.strip()
    if not value or any(ch in value for ch in "\r\n"):
        return ""
    lower = value.lower()
    if value.startswith(("/", "#")) or ".." in value or "`" in value or "<!-- larch:" in value:
        return ""
    if "github.com" in lower or "/pull/" in lower or "larch-logs/" in value:
        return ""
    if any(ord(ch) < CONTROL_CHAR_ORDINAL_LIMIT for ch in value):
        return ""
    if re.search(r"(^|\s)[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+", value):
        return ""
    return value


def _report_skill_label(*, profile: str, prefix: str) -> str:
    if profile != "generic":
        return "/implement"
    if prefix == "design-failure":
        return "/design"
    if prefix:
        return f"/{prefix.split('-', 1)[0]}"
    return "/generic"


def _safe_class_value(value: str) -> str:
    allowed = {
        "transient-infra", "test-failure", "lint-failure", "dispatch-failure", "protected-path",
        "submodule-restricted", "ci-fix-exhausted", "same-cause-repeat", "contract-failure", "unrecoverable",
        "environment", "operator-action", "larch-defect", "",
    }
    return value if value in allowed else "unrecoverable"


def _safe_step_value(value: str) -> str:
    if _safe_step(value, generic=True):
        return value
    return value if value == "unknown" else "unknown"


def _safe_phase_value(value: str) -> str:
    if _safe_token(kind="phase", value=value, generic=True):
        return value
    return value if value == "unknown" else "unknown"


def _safe_dispatcher_value(value: str, *, generic: bool = False) -> str:
    if not value:
        return "unknown"
    if value in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"}:
        return value
    if generic and value in _GENERIC_SOURCE_SCRIPTS:
        return value
    return "redacted"


def _safe_bail_value(value: str) -> str:
    if not value:
        return "none"
    return value if _safe_bail_reason_value(value, generic=True) else "redacted"


def _safe_simple_token(value: str, *, fallback: str = "redacted") -> str:
    return value if value and re.fullmatch(r"[A-Za-z0-9._:-]+", value) else fallback


def _read_source_env_export(*, path: Path, key: str) -> str:
    """Read an ``export KEY=value`` assignment from a shell source-env file.

    Mirrors the retired stall-recovery report helper ``source_env_export_get``: only honors a
    line whose first token is ``export``, strips matching surrounding single or
    double quotes, and refuses to follow symlinks.
    """
    if not path.is_file() or path.is_symlink():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("export "):
            continue
        body = stripped[len("export "):].lstrip()
        if not body.startswith(f"{key}="):
            continue
        value = body[len(key) + 1:]
        quote = value[:1]
        if quote in ("'", '"') and value[-1:] == quote:
            value = value[1:-1]
        return value
    return ""


def _read_run_id(*, tmpdir: Path, session_env_file: Path | None = None) -> str:
    value = read_kv(path=tmpdir / "parent-issue.md", key="RUN_ID", default="")
    if not value and (tmpdir / "session-id").is_file():
        value = (tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip()
    if not value:
        if session_env_file is not None:
            value = _read_source_env_export(path=session_env_file, key="SESSION_ID")
        else:
            value = _read_source_env_export(path=tmpdir / "source-env.sh", key="SESSION_ID")
    return _safe_simple_token(value, fallback="unknown")


def _read_larch_version() -> str:
    for path in (_REPO_ROOT / "VERSION", _REPO_ROOT / "package.json"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name == "VERSION":
            value = text.strip()
        else:
            match: re.Match[str] | None = re.search(r'"version"\s*:\s*"([^"]+)"', text)
            value = match.group(1) if match else ""
        if re.fullmatch(r"[A-Za-z0-9._+-]+", value):
            return value
    return "unknown"


def _first_escalation_field(*, field_name: str, ledger: Path, fallback: Path) -> str:
    for path in (ledger, fallback):
        if not path.is_file():
            continue
        for row in path.read_text(encoding="utf-8", errors="replace").splitlines():
            for field in row.split("\t"):
                key, sep, value = field.partition("=")
                if sep and key == field_name:
                    return _safe_simple_token(value)
    return ""


def _append_escalation_row_summaries(*, path: Path, label: str = "") -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return ""
    lines: list[str] = []
    for row in path.read_text(encoding="utf-8", errors="replace").splitlines():
        values: dict[str, str] = {}
        for field in row.split("\t"):
            key, sep, value = field.partition("=")
            if sep:
                values[key] = value
        site = _safe_simple_token(values.get("site", ""))
        trigger = _safe_simple_token(values.get("trigger", ""))
        if values.get("site") or values.get("trigger"):
            prefix = f"{label} " if label else ""
            lines.append(f"- {prefix}site=`{site}` trigger=`{trigger}`")
    if not lines and label:
        lines.append(f"- {label} present")
    return "\n".join(lines)


def _record_escalation_tool_failure_present(tmpdir: Path) -> bool:
    execution = tmpdir / "execution-issues.md"
    if not execution.is_file() or execution.is_symlink():
        return False
    return bool(re.search(r"^#{2,3}\s+Tool Failure: record-escalation(\s|$)", execution.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))


def _append_record_escalation_tool_failure(*, tmpdir: Path, reason: str) -> None:
    execution = tmpdir / "execution-issues.md"
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=execution):
        return
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"\n## Tool Failure: record-escalation\n\n"
        f"- utc: `{ts}`\n"
        f"- helper: `python/cli.py stall-recovery record-escalation`\n"
        f"- reason: `{reason}`\n"
    )
    with contextlib.suppress(OSError):
        run_logs.append_execution_issue(log_file=execution, category="Tool Failures", entry=entry)


def _attempts_table(attempts_file: Path) -> str:
    attempt_count_raw = read_kv(path=attempts_file, key="attempt_count", default="0")
    attempt_count = int(attempt_count_raw) if attempt_count_raw.isdigit() else 0
    lines = ["| Attempt | Class | Resume hint | Outcome | UTC |", "|---|---|---|---|---|"]
    if attempt_count == 0:
        lines.append("| none | n/a | n/a | n/a | n/a |")
        return "\n".join(lines)
    lines.extend(
            f"| `{idx}` | `{_safe_class_value(read_kv(path=attempts_file, key=f'attempt.{idx}.class', default=''))}` | "
            f"`{_safe_simple_token(read_kv(path=attempts_file, key=f'attempt.{idx}.resume_hint', default=''), fallback='none')}` | "
            f"`{_safe_simple_token(read_kv(path=attempts_file, key=f'attempt.{idx}.outcome', default=''), fallback='failed')}` | "
            f"`{_safe_simple_token(read_kv(path=attempts_file, key=f'attempt.{idx}.utc', default=''), fallback='unknown')}` |"
            for idx in range(1, attempt_count + 1)
        )
    return "\n".join(lines)


def _report_dedup_signature(*, kind: str, class_file: Path, ledger: Path, fallback: Path, profile: str, prefix: str, skill_label: str) -> str:
    seed: list[str] = []
    seed.append("larch-stall-report-dedup-generic-v1" if profile == "generic" else "larch-stall-report-dedup-v1")
    if profile == "generic":
        seed.extend([f"skill_label={skill_label}", f"artifact_prefix={prefix}"])
    seed.extend([
        f"report_kind={kind}",
        f"failure_class={_safe_class_value(read_kv(path=class_file, key='FAILURE_CLASS', default='unrecoverable'))}",
        f"step={_safe_step_value(read_kv(path=class_file, key='STALL_STEP', default=''))}",
        f"phase={_safe_phase_value(read_kv(path=class_file, key='PHASE', default=''))}",
        f"safe_bail_token={_safe_bail_value(read_kv(path=class_file, key='BAIL_REASON', default=''))}",
    ])
    if kind == "escalation-success":
        seed.extend([
            f"escalation_site={_first_escalation_field(field_name='site', ledger=ledger, fallback=fallback)}",
            f"escalation_trigger={_first_escalation_field(field_name='trigger', ledger=ledger, fallback=fallback)}",
        ])
    return hashlib.sha256("\n".join(seed).encode()).hexdigest()


def _report_marker(signature: str) -> str:
    return f"<!-- larch-stall:signature={signature} -->"


def _append_file_section(*, label: str, path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        return ""
    return f"\n## {label}\n\n{path.read_text(encoding='utf-8', errors='replace')}\n"


def _compose_tier_a_issue(
    *, kind: str,
    class_file: Path,
    attempts_file: Path,
    ledger: Path,
    fallback: Path,
    marker: Path,
    root_file: Path,
    title: str,
    tmpdir: Path,
    session_env_file: Path,
) -> str:
    bail = read_kv(path=class_file, key="BAIL_REASON_RAW", default="") or read_kv(path=class_file, key="BAIL_REASON", default="") or "none"
    body = [
        f"### {title}",
        "",
        "## Report metadata",
        "",
        f"- **Report kind**: `{kind}`",
        f"- **Failure class**: `{_safe_class_value(read_kv(path=class_file, key='FAILURE_CLASS', default='unrecoverable'))}`",
        f"- **Step**: `{_safe_step_value(read_kv(path=class_file, key='STALL_STEP', default=''))}`",
        f"- **Bail reason**: `{_safe_bail_value(bail)}`",
        f"- **Run ID**: `{_read_run_id(tmpdir=tmpdir, session_env_file=session_env_file)}`",
        f"- **Branch**: `{_safe_simple_token(read_kv(path=tmpdir / 'session-env.sh', key='BRANCH_NAME', default='') or read_kv(path=tmpdir / 'ship-pr-state.sh', key='BRANCH_NAME', default='') or read_kv(path=tmpdir / 'session-env.sh', key='BRANCH', default='') or read_kv(path=tmpdir / 'ship-pr-state.sh', key='BRANCH', default=''), fallback='unknown')}`",
        f"- **PR URL**: `{read_kv(path=tmpdir / 'ship-pr-state.sh', key='PR_URL', default='') or read_kv(path=tmpdir / 'finalize-state.sh', key='PR_URL', default='') or 'unknown'}`",
        _append_file_section(label="Root-cause finding", path=root_file),
        "\n## Attempts\n\n" + _attempts_table(attempts_file),
        _append_file_section(label="Escalation ledger", path=ledger),
        _append_file_section(label="Fallback escalation evidence", path=fallback),
        _append_file_section(label="Record-failure marker", path=marker),
    ]
    if _record_escalation_tool_failure_present(tmpdir):
        body.append("\n## Record-escalation Tool Failure\n\n- tagged record-escalation Tool Failure present\n")
    detail_log = read_kv(path=class_file, key="FAILURE_DETAIL_LOG", default="")
    if detail_log:
        detail_content, detail_valid = _read_validated_failure_detail_log(tmpdir=tmpdir, path=Path(detail_log))
        if detail_valid:
            body.append("\n## Validated failure-detail log\n\n" + detail_content + "\n")
    body.append(_append_file_section(label="Run-log pointer", path=tmpdir / "run-log-pointer.txt"))
    return "\n".join(part for part in body if part)


def _compose_tier_b_projection(
    *, kind: str,
    class_file: Path,
    attempts_file: Path,
    ledger: Path,
    fallback: Path,
    marker: Path,
    root_file: Path,
    bounded_file: Path,
    skill_label: str,
    session_env_file: Path,
) -> str:
    tmpdir = class_file.parent
    bail = _safe_bail_value(read_kv(path=class_file, key="BAIL_REASON", default=""))
    summary = _parse_root_cause_file(path=bounded_file, key="summary", default=_parse_root_cause_file(path=root_file, key="summary", default=""))
    rows = [
        f"## {skill_label} {kind} report",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Report kind | `{kind}` |",
    ]
    if kind == "escalation-success":
        rows.append("| Recovery outcome | `success` |")
    else:
        rows.append(f"| Failure class | `{_safe_class_value(read_kv(path=class_file, key='FAILURE_CLASS', default='unrecoverable'))}` |")
    rows.extend([
        f"| Step | `{_safe_step_value(read_kv(path=class_file, key='STALL_STEP', default=''))}` |",
        f"| Phase | `{_safe_phase_value(read_kv(path=class_file, key='PHASE', default=''))}` |",
        f"| Bail reason | `{bail}` |",
        f"| Exit code | `{_safe_simple_token(read_kv(path=class_file, key='EXIT_CODE', default=''), fallback='unknown')}` |",
        f"| Dispatcher | `{_safe_simple_token(read_kv(path=class_file, key='DISPATCHER', default=''), fallback='unknown')}` |",
        f"| Matched classifier pattern | `{_safe_simple_token(read_kv(path=class_file, key='MATCHED_CLASSIFIER_PATTERN', default=''), fallback='redacted')}` |",
        f"| Larch version | `{_read_larch_version()}` |",
        f"| Run ID | `{_read_run_id(tmpdir=tmpdir, session_env_file=session_env_file)}` |",
        f"| Root-cause verdict | `{_parse_root_cause_file(path=root_file, key='verdict', default='')}` |",
        f"| Root-cause confidence | `{_parse_root_cause_file(path=root_file, key='confidence', default='')}` |",
        "",
        "## Bounded root-cause summary",
        "",
        summary,
        "",
        "## Bounded root-cause details",
        "",
        _root_cause_prose(bounded_file),
        "",
        "## Attempts",
        "",
        _attempts_table(attempts_file),
        "",
        "## Escalation evidence",
        "",
    ])
    evidence = [_append_escalation_row_summaries(path=ledger), _append_escalation_row_summaries(path=fallback, label="fallback")]
    if marker.is_file() and marker.stat().st_size > 0:
        evidence.append("- record-failure marker present")
    if _record_escalation_tool_failure_present(tmpdir):
        evidence.append("- tagged record-escalation Tool Failure present")
    rows.append("\n".join(line for line in evidence if line))
    return "\n".join(rows).rstrip() + "\n"


def _write_tier_a_comment_payloads(*, tmpdir: Path, attempts_file: Path, ledger: Path, fallback: Path, marker: Path, root_file: Path, prefix: str) -> bool:
    _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_A_ATTEMPTS_SLICE, prefix=prefix).write_text(_attempts_table(attempts_file) + "\n", encoding="utf-8")
    escalation = "\n".join(
        part for part in (
            _append_file_section(label="Escalation ledger", path=ledger),
            _append_file_section(label="Fallback escalation evidence", path=fallback),
            _append_file_section(label="Record-failure marker", path=marker),
            "\n## Record-escalation Tool Failure\n\n- tagged record-escalation Tool Failure present\n" if _record_escalation_tool_failure_present(tmpdir) else "",
        )
        if part
    )
    redacted_escalation = _redact_text(escalation)
    redacted_root = _redact_text(root_file.read_text(encoding="utf-8", errors="replace"))
    if redacted_escalation is None or redacted_root is None:
        return False
    _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_A_ESCALATION_SLICE, prefix=prefix).write_text(redacted_escalation, encoding="utf-8")
    _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_A_ROOT_CAUSE_SLICE, prefix=prefix).write_text(redacted_root, encoding="utf-8")
    return True


def _write_tier_b_comment_payloads(*, tmpdir: Path, attempts_file: Path, ledger: Path, fallback: Path, marker: Path, bounded_file: Path, prefix: str) -> None:
    _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_B_ATTEMPTS_SLICE, prefix=prefix).write_text(_attempts_table(attempts_file) + "\n", encoding="utf-8")
    evidence = [_append_escalation_row_summaries(path=ledger), _append_escalation_row_summaries(path=fallback, label="fallback")]
    if marker.is_file() and marker.stat().st_size > 0:
        evidence.append("- record-failure marker present")
    if _record_escalation_tool_failure_present(tmpdir):
        evidence.append("- tagged record-escalation Tool Failure present")
    _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_B_ESCALATION_SLICE, prefix=prefix).write_text("\n".join(line for line in evidence if line) + "\n", encoding="utf-8")
    root_public = "## Bounded root-cause summary\n\n" + _parse_root_cause_file(path=bounded_file, key="summary", default="") + "\n\n## Bounded root-cause details\n\n" + _root_cause_prose(bounded_file) + "\n"
    _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_B_ROOT_CAUSE_SLICE, prefix=prefix).write_text(root_public, encoding="utf-8")


def _tier_a_allowed(*, tmpdir: Path, args: argparse.Namespace) -> bool:
    forked = (
        read_kv(path=tmpdir / "ship-pr-state.sh", key="FORKED_TARGET", default="")
        or read_kv(path=tmpdir / "finalize-state.sh", key="FORKED_TARGET", default="")
        or read_kv(path=tmpdir / "session-env.sh", key="FORKED_TARGET", default="")
        or "false"
    )
    if _truthy(forked):
        return False
    root = (
        os.environ.get("CLAUDE_PROJECT_DIR", "")
        or os.environ.get("REPO_ROOT", "")
        or read_kv(path=Path(getattr(args, "session_env_file", "") or tmpdir / "session-env.sh"), key="REPO_ROOT", default="")
        or read_kv(path=tmpdir / "ship-pr-state.sh", key="REPO_ROOT", default="")
    )
    if not root:
        completed = subprocess.run(["/usr/bin/git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
        root = completed.stdout.strip() if completed.returncode == 0 else ""
    return bool(root) and (Path(root) / "skills" / "implement" / "SKILL.md").is_file()


def _redact_text(text: str) -> str | None:
    redactor = _REPO_ROOT / "python" / "cli.py"
    if not redactor.is_file():
        return None
    completed = subprocess.run([sys.executable, str(redactor), "redact", "secrets"], input=text, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout


def _compose_redaction_failed() -> int:
    emit(key="STALL_RECOVERY_REPORT_STATUS", value="fallback-print-required")
    emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value="redactor-failed")
    return _compose_error("redactor failed")


def _emit_chat_print_filing_status(*, tmpdir: Path, out_file: Path, title: str, sensitive_file: Path, prefix: str) -> None:
    if _truthy(os.environ.get("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES")) and not _truthy(os.environ.get("LARCH_STALL_RECOVERY_ENABLE_TEST_FILING")):
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="printed")
        return
    resolver = _REPO_ROOT / "scripts" / "resolve-upstream-larch-repo.sh"
    helper = _REPO_ROOT / "scripts" / "file-failure-report-cross-repo.sh"
    repo_proc = subprocess.run([str(resolver)], capture_output=True, text=True, check=False) if resolver.is_file() else None
    upstream_repo = repo_proc.stdout.strip() if repo_proc and repo_proc.returncode == 0 else ""
    if not upstream_repo:
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="fallback-print-required")
        emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value="upstream-repo-unresolved")
        return
    if not helper.is_file():
        emit(key="STALL_RECOVERY_REPORT_STATUS", value="fallback-print-required")
        emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value="cross-repo-helper-missing")
        return
    helper_out = _artifact_path(tmpdir=tmpdir, default_name="stall-recovery-tier-b-file.env", prefix=prefix)
    completed = subprocess.run(
        [
            str(helper),
            "--repo", upstream_repo,
            "--body-file", str(out_file),
            "--title", title,
            "--publication-tier", "tier-b",
            "--attempts-file", str(_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_B_ATTEMPTS_SLICE, prefix=prefix)),
            "--escalation-ledger-file", str(_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_B_ESCALATION_SLICE, prefix=prefix)),
            "--root-cause-file", str(_artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_TIER_B_ROOT_CAUSE_SLICE, prefix=prefix)),
            "--sensitive-corpus-file", str(sensitive_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    helper_out.write_text(completed.stdout, encoding="utf-8")
    normalize_file_failure_report_env(argparse.Namespace(implement_tmpdir=str(tmpdir), file_failure_report_env=str(helper_out)))


_CODE_ALLOWLIST_LINES = """chat-print	report_kind	REPORT_KIND	enum
chat-print	failing_step	STALL_STEP	enum
chat-print	failing_phase	PHASE	enum
chat-print	failure_class	FAILURE_CLASS	enum
chat-print	bail_reason	BAIL_REASON	expanded-bail-token-union
chat-print	exit_code	EXIT_CODE	integer-or-unknown
chat-print	dispatcher	DISPATCHER	enum
chat-print	matched_classifier_pattern	MATCHED_CLASSIFIER_PATTERN	enum
chat-print	larch_version	larch-version	token
chat-print	run_id	RUN_ID	token-or-unknown
chat-print	attempt_table	attempts-file	allowlisted-attempt-fields
chat-print	escalation_site	escalation-ledger	enum
chat-print	escalation_trigger	escalation-ledger	enum
chat-print	fallback_escalation_marker	escalation-fallback	present-marker
chat-print	record_failure_marker	record-failure-marker	present-marker
chat-print	record_escalation_tool_failure	execution-issues	present-marker
chat-print	bounded_root_cause	bounded-root-cause-file	validated-larch-internal-prose
""".strip().splitlines()


def _retry_policy_lines() -> list[str]:
    classes = (
        "transient-infra", "test-failure", "lint-failure", "dispatch-failure", "protected-path",
        "submodule-restricted", "ci-fix-exhausted", "same-cause-repeat", "contract-failure", "unrecoverable",
    )
    caps = {
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
    return [f"{klass}\t{max_attempts}\t{delay}" for klass in classes for max_attempts, delay in [caps[klass]]]


def _doc_allowlist_lines() -> list[str]:
    contract = _REPO_ROOT / "python" / "stall-recovery-report.md"
    if not contract.is_file():
        return []
    lines: list[str] = []
    in_block = False
    for raw in contract.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip() == "<!-- stall-recovery-allowlist:begin -->":
            in_block = True
            continue
        if raw.strip() == "<!-- stall-recovery-allowlist:end -->":
            break
        if not in_block or "|" not in raw or raw.lstrip().startswith("surface"):
            continue
        parts = [part.strip() for part in raw.strip().strip("|").split("|")]
        if len(parts) >= ALLOWLIST_TABLE_COLUMNS and parts[0] not in {"---", "surface"}:
            lines.append("\t".join(parts[:ALLOWLIST_TABLE_COLUMNS]))
    return lines


def _doc_retry_policy_lines() -> list[str]:
    contract = _REPO_ROOT / "python" / "stall-recovery-report.md"
    if not contract.is_file():
        return []
    lines: list[str] = []
    in_table = False
    for raw in contract.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip() == "| failure_class | attempts | delay |":
            in_table = True
            continue
        if in_table and raw.strip().startswith("|---"):
            continue
        if in_table and raw.strip().startswith("| "):
            parts = [part.strip().strip("`") for part in raw.strip().strip("|").split("|")]
            if len(parts) >= RETRY_POLICY_TABLE_COLUMNS:
                lines.append(f"{parts[0]}\t{parts[1]}\t{parts[2]}")
            continue
        if in_table:
            break
    return lines


def lint_subcommand(rest: list[str]) -> int:
    _ = rest
    tsv_path = _REPO_ROOT / "python" / "stall-recovery-report-allowlists.tsv"
    if not tsv_path.is_file():
        print(f"stall-recovery: missing allowlist TSV: {tsv_path}", file=sys.stderr)
        return 1
    tsv_lines = [line for line in tsv_path.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    code_lines = sorted(_CODE_ALLOWLIST_LINES)
    doc_lines = sorted(_doc_allowlist_lines())
    if sorted(tsv_lines) != code_lines:
        print("stall-recovery: allowlist drift between TSV and code", file=sys.stderr)
        return 1
    if doc_lines and sorted(tsv_lines) != doc_lines:
        print("stall-recovery: allowlist drift between TSV and doc", file=sys.stderr)
        return 1
    retry_doc = sorted(_doc_retry_policy_lines())
    retry_code = sorted(_retry_policy_lines())
    if retry_doc and retry_doc != retry_code:
        print("stall-recovery: retry-policy drift between code and doc", file=sys.stderr)
        return 1
    compound_safe = _safe_token(kind="trigger", value="ci-local-unfixable:job_1,job-2", generic=False)
    compound_bad = _safe_token(kind="trigger", value="ci-local-unfixable:../../secret", generic=False)
    if not compound_safe or compound_bad:
        print("stall-recovery: ci-local-unfixable compound grammar drift", file=sys.stderr)
        return 1
    for token in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
        if not _safe_bail_reason_value(token, generic=False):
            print(f"stall-recovery: runtime bail token not render-safe: {token}", file=sys.stderr)
            return 1
    emit(key="LINT_OK", value="true")
    return 0


_GLOBAL_STALL_FLAGS = frozenset({
    "--profile",
    "--artifact-prefix",
    "--implement-tmpdir",
    "--primary-state-file",
    "--finalize-state-file",
    "--session-env-file",
})


def _parse_leading_global_flags(argv: list[str]) -> tuple[list[str], dict[str, str] | None]:
    globals_dict: dict[str, str] = {}
    idx = 0
    while idx < len(argv) and argv[idx] in _GLOBAL_STALL_FLAGS:
        flag = argv[idx]
        if idx + 1 >= len(argv):
            print(f"stall-recovery: {flag} requires a value", file=sys.stderr)
            return argv, None
        key = flag[2:].replace("-", "_")
        globals_dict[key] = argv[idx + 1]
        idx += 2
    prefix = globals_dict.get("artifact_prefix", "")
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return argv[idx:], None
    return argv[idx:], globals_dict


def _global_default(*, globals_dict: dict[str, str] | None, key: str, fallback: str = "") -> str:
    if globals_dict and key in globals_dict:
        return globals_dict[key]
    return fallback


def _add_implement_tmpdir_arg(*, p: argparse.ArgumentParser, globals_dict: dict[str, str] | None) -> None:
    p.add_argument(
        "--implement-tmpdir",
        default=_global_default(globals_dict=globals_dict, key="implement_tmpdir", fallback=os.environ.get("IMPLEMENT_TMPDIR", ".")),
    )


def _add_compose_report_args(*, p: argparse.ArgumentParser, globals_dict: dict[str, str] | None) -> None:
    p.add_argument("--report-kind", default="terminal-failure")
    p.add_argument("--surface", default="chat-print")
    p.add_argument("--attempts-file", default="")
    p.add_argument("--classification-file", default="")
    p.add_argument("--escalation-ledger-file", default="")
    p.add_argument("--escalation-fallback-file", default="")
    p.add_argument("--record-failure-marker", default="")
    p.add_argument("--root-cause-file", default="")
    p.add_argument("--bounded-root-cause-file", default="")
    p.add_argument("--title-file", default="")
    p.add_argument("--sensitive-corpus-file", default="")
    p.add_argument("--output-file")
    p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
    p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
    p.add_argument("--primary-state-file", default=_global_default(globals_dict=globals_dict, key="primary_state_file", fallback=""))
    p.add_argument("--finalize-state-file", default=_global_default(globals_dict=globals_dict, key="finalize_state_file", fallback=""))
    p.add_argument("--session-env-file", default=_global_default(globals_dict=globals_dict, key="session_env_file", fallback=""))


def chat_print(args: argparse.Namespace) -> int:
    args.surface = "chat-print"
    return compose_report(args)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    rest, globals_dict = _parse_leading_global_flags(argv)
    if globals_dict is None:
        return 2
    if not rest:
        print("stall-recovery: missing subcommand", file=sys.stderr)
        return 2
    sub, sub_argv = rest[0], rest[1:]
    p = argparse.ArgumentParser(prog=f"cli.py stall-recovery {sub}")
    _add_implement_tmpdir_arg(p=p, globals_dict=globals_dict)
    if sub == "classify":
        p.add_argument("--failure-detail-log")
        p.add_argument("--attempts-file")
        p.add_argument("--bail-reason", default="")
        p.add_argument("--in-memory-stall-tracking")
        p.add_argument("--primary-state-file", default=_global_default(globals_dict=globals_dict, key="primary_state_file", fallback=""))
        p.add_argument("--finalize-state-file", default=_global_default(globals_dict=globals_dict, key="finalize_state_file", fallback=""))
        p.add_argument("--session-env-file", default=_global_default(globals_dict=globals_dict, key="session_env_file", fallback=""))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--stall-step", default="")
        p.add_argument("--phase", default="")
        p.add_argument("--exit-code", default="")
        p.add_argument("--dispatcher", default="")
        ns, _ = p.parse_known_args(sub_argv)
        return classify(ns)
    if sub == "init-attempts":
        p.add_argument("--attempts-file")
        ns, _ = p.parse_known_args(sub_argv)
        return init_attempts(ns)
    if sub == "record-attempt":
        p.add_argument("--attempts-file")
        p.add_argument("--class", dest="failure_class", required=True)
        p.add_argument("--signature", required=True)
        p.add_argument("--resume-hint", default="none")
        p.add_argument("--outcome", default="failed")
        ns, _ = p.parse_known_args(sub_argv)
        return record_attempt(ns)
    if sub == "retry-policy":
        p.add_argument("--class", dest="failure_class", required=True)
        ns, _ = p.parse_known_args(sub_argv)
        return retry_policy(ns)
    if sub == "normalize-outcome":
        p.add_argument("--in-memory-stall-tracking", default="")
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_outcome(ns)
    if sub == "normalize-issue-env":
        p.add_argument("--issue-stdout-file", required=True)
        p.add_argument("--issue-exit-code")
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_issue_env(ns)
    if sub == "record-escalation":
        p.add_argument("--site", required=True)
        p.add_argument("--trigger", required=True)
        p.add_argument("--step", required=True)
        p.add_argument("--phase", required=True)
        p.add_argument("--dispatcher", required=True)
        p.add_argument("--exit-code", default="unknown")
        p.add_argument("--failure-detail-log", default="")
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        ns, _ = p.parse_known_args(sub_argv)
        return record_escalation(ns)
    if sub == "dedup-tier-a-report":
        p.add_argument("--body-file", default="")
        p.add_argument("--attempts-file", default="")
        p.add_argument("--escalation-ledger-file", default="")
        p.add_argument("--root-cause-file", default="")
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return dedup_tier_a_report(ns)
    if sub == "compose-report":
        _add_compose_report_args(p=p, globals_dict=globals_dict)
        ns, _ = p.parse_known_args(sub_argv)
        return compose_report(ns)
    if sub == "validate-token":
        p.add_argument("--token", default="")
        p.add_argument("--value", default="")
        p.add_argument("--token-kind", default="")
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        ns.token = ns.token or ns.value
        return validate_token(ns)
    if sub == "validate-terminal-state":
        p.add_argument("--primary-state-file", default=_global_default(globals_dict=globals_dict, key="primary_state_file", fallback=""))
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return validate_terminal_state(ns)
    if sub == "validate-tier-b-public-file":
        p.add_argument("--public-file", required=True)
        p.add_argument("--tmpdir")
        p.add_argument("--sensitive-corpus-file", default="")
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return validate_tier_b_public_file(ns)
    if sub == "clear-stall":
        ns, _ = p.parse_known_args(sub_argv)
        return clear_stall(ns)
    if sub == "seed-terminal-state":
        p.add_argument("--stall-step")
        p.add_argument("--phase")
        ns, _ = p.parse_known_args(sub_argv)
        return seed_terminal_state(ns)
    if sub == "chat-print":
        _add_compose_report_args(p=p, globals_dict=globals_dict)
        ns, _ = p.parse_known_args(sub_argv)
        return chat_print(ns)
    if sub == "is-larch-dev-clone":
        p.add_argument("--working-tree-root", default="")
        ns, _ = p.parse_known_args(sub_argv)
        return is_larch_dev_clone(ns)
    if sub == "normalize-file-failure-report-env":
        p.add_argument("--file-failure-report-env", required=True)
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_file_failure_report_env(ns)
    if sub == "populate-sensitive-corpus":
        p.add_argument("--sensitive-corpus-file", default="")
        p.add_argument("--classification-file", default="")
        p.add_argument("--attempts-file", default="")
        p.add_argument("--escalation-ledger-file", default="")
        p.add_argument("--escalation-fallback-file", default="")
        p.add_argument("--record-failure-marker", default="")
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return populate_sensitive_corpus(ns)
    if sub == "lint":
        return lint_subcommand(sub_argv)
    print(f"stall-recovery: unknown subcommand: {sub}", file=sys.stderr)
    return 2


def init_attempts_main(argv: list[str] | None = None) -> int:
    return main(["init-attempts", *(argv or [])])


def classify_main(argv: list[str] | None = None) -> int:
    return main(["classify", *(argv or [])])


def record_escalation_main(argv: list[str] | None = None) -> int:
    return main(["record-escalation", *(argv or [])])


def normalize_outcome_main(argv: list[str] | None = None) -> int:
    return main(["normalize-outcome", *(argv or [])])


def compose_report_main(argv: list[str] | None = None) -> int:
    return main(["compose-report", *(argv or [])])


def dedup_tier_a_report_main(argv: list[str] | None = None) -> int:
    return main(["dedup-tier-a-report", *(argv or [])])


def normalize_file_failure_report_env_main(argv: list[str] | None = None) -> int:
    return main(["normalize-file-failure-report-env", *(argv or [])])


def normalize_issue_env_main(argv: list[str] | None = None) -> int:
    return main(["normalize-issue-env", *(argv or [])])


def validate_token_main(argv: list[str] | None = None) -> int:
    return main(["validate-token", *(argv or [])])


def validate_terminal_state_main(argv: list[str] | None = None) -> int:
    return main(["validate-terminal-state", *(argv or [])])


def validate_tier_b_public_file_main(argv: list[str] | None = None) -> int:
    return main(["validate-tier-b-public-file", *(argv or [])])


def populate_sensitive_corpus_main(argv: list[str] | None = None) -> int:
    return main(["populate-sensitive-corpus", *(argv or [])])


def chat_print_main(argv: list[str] | None = None) -> int:
    return main(["chat-print", *(argv or [])])


def record_attempt_main(argv: list[str] | None = None) -> int:
    return main(["record-attempt", *(argv or [])])


def retry_policy_main(argv: list[str] | None = None) -> int:
    return main(["retry-policy", *(argv or [])])


def is_larch_dev_clone_main(argv: list[str] | None = None) -> int:
    return main(["is-larch-dev-clone", *(argv or [])])


def clear_stall_main(argv: list[str] | None = None) -> int:
    return main(["clear-stall", *(argv or [])])


def seed_terminal_state_main(argv: list[str] | None = None) -> int:
    return main(["seed-terminal-state", *(argv or [])])


def lint_main(argv: list[str] | None = None) -> int:
    return main(["lint", *(argv or [])])
