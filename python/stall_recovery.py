"""Stall recovery report helpers shared by /implement and /design."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, UTC
from pathlib import Path

import config

MAX_PUBLIC_FILE_BYTES = 256_000
ALLOWLIST_TABLE_COLUMNS = 4
RETRY_POLICY_TABLE_COLUMNS = 3

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STALL_RECOVERY_SH = _REPO_ROOT / "skills" / "implement" / "scripts" / "stall-recovery-report.sh"

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
    "plan-write-failed", "publish-failed", "panel-failed", "tally-error",
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
    "validator-autofix-skipped-cycle-cap", "operator-action",
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


def _safe_token(kind: str, value: str, *, generic: bool) -> bool:
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


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


def read_kv(path: Path, key: str, default: str = "") -> str:
    if not path.is_file():
        return default
    prefix = key + "="
    value = default
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            value = line[len(prefix):].strip("\r")
    return value


def write_kvs(path: Path, values: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
    tmp.replace(path)


def _state(tmpdir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for file in (tmpdir / "ship-pr-state.sh", tmpdir / "finalize-state.sh"):
        if file.is_file():
            for line in file.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k] = v.strip("\r")
    return out


def _classify_text(text: str, bail: str, step: str, phase: str, *, detail_log_valid: bool = False) -> tuple[str, str, str]:
    _ = phase
    if step == "rebase-failed":
        return "transient-infra", "step8-shippr", "rebase-transient"
    lower = f"{bail}\n{text}".lower()
    if "submodule-edit-required-out-of-scope" in lower:
        return "submodule-restricted", "none", "submodule-restricted-bail-token"
    if "protected-path" in lower:
        return "protected-path", "step2-impl", "protected-path-bail-token"
    if any(x in lower for x in ("orchestrator-envelope-invalid", "wrapper-validation-failure", "dirty-state-after-timeout", "main-branch-post-dispatch")):
        return "dispatch-failure", "step2-impl", "dispatch-bail-token"
    if any(x in lower for x in ("api rate limit", "network timeout", "timeout", "temporarily unavailable")):
        return "transient-infra", "step8-shippr", "transient-output"
    if any(x in lower for x in ("pytest", "failing test", "jest", "failed with")):
        return "test-failure", "step2-impl", "test-output"
    if any(x in lower for x in ("shellcheck", "markdownlint", "ruff", "lint-fix-loop", "lint")):
        return "lint-failure", "step5-review", "lint-output"
    if step in {"3", "6"}:
        return "contract-failure", "none", "step-contract"
    if detail_log_valid and bail == "ci-fix-exhausted":
        return "ci-fix-exhausted", "step8-shippr", "ci-fix-exhausted-with-detail"
    if bail in {"adopted-issue-closed", "tracking-init-failed", "recovery-out-of-scope"}:
        return "unrecoverable", "none", "bail-token"
    if bail == "ci-fix-exhausted":
        return "unrecoverable", "none", "bail-token"
    return "unrecoverable", "none", "fallback"


def classify(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    st = _state(tmpdir)
    step = args.stall_step or st.get("STALL_STEP", "")
    phase = args.phase or st.get("PHASE", "")
    bail = args.bail_reason or st.get("BAIL_REASON", "")
    detail = ""
    detail_log_valid = False
    if args.failure_detail_log:
        detail_path = Path(args.failure_detail_log)
        if detail_path.is_file() and _validate_tmpdir_local_file(tmpdir, detail_path):
            detail = detail_path.read_text(encoding="utf-8", errors="replace")[:8192]
            detail_log_valid = True
    klass, hint, pattern = _classify_text(detail, bail, step, phase, detail_log_valid=detail_log_valid)
    signature = hashlib.sha256(f"{klass}\n{bail}\n{detail}".encode()).hexdigest()[:16]
    attempts = Path(args.attempts_file) if args.attempts_file else tmpdir / "stall-recovery-attempts.env"
    if attempts.is_file() and read_kv(attempts, "last_signature") == signature and read_kv(attempts, "last_outcome") == "failed":
        klass = "same-cause-repeat"
        hint = "none"
    values = {
        "FAILURE_CLASS": klass,
        "FAILURE_SIGNATURE": signature,
        "RESUME_HINT": hint,
        "STALL_STEP": step,
        "PHASE": phase,
        "BAIL_REASON": bail,
        "EXIT_CODE": args.exit_code or st.get("EXIT_CODE", ""),
        "MATCHED_CLASSIFIER_PATTERN": pattern,
        "DISPATCHER": args.dispatcher or st.get("DISPATCHER", ""),
    }
    for k, v in values.items():
        emit(k, v)
    write_kvs(tmpdir / "stall-recovery-classification.env", values)
    return 0


def init_attempts(args: argparse.Namespace) -> int:
    path = Path(args.attempts_file or Path(args.implement_tmpdir) / "stall-recovery-attempts.env")
    if not path.exists():
        write_kvs(path, {"version": 1, "created_utc": datetime.now(UTC).isoformat(), "attempt_count": 0})
    return 0


def record_attempt(args: argparse.Namespace) -> int:
    path = Path(args.attempts_file or Path(args.implement_tmpdir) / "stall-recovery-attempts.env")
    count = int(read_kv(path, "attempt_count", "0") or 0) + 1
    values = {"version": 1, "created_utc": read_kv(path, "created_utc", datetime.now(UTC).isoformat()), "attempt_count": count, "last_class": args.failure_class, "last_signature": args.signature, "last_resume_hint": args.resume_hint, "last_outcome": args.outcome}
    write_kvs(path, values)
    return 0


def retry_policy(args: argparse.Namespace) -> int:
    klass = args.failure_class
    caps: dict[str, tuple[int, str]] = {
        "transient-infra": (4, "sleep-seconds.sh 5"),
        "test-failure": (8, "none"),
        "lint-failure": (8, "none"),
        "ci-fix-exhausted": (8, "none"),
        "dispatch-failure": (3, "none"),
        "protected-path": (1, "none"),
        "submodule-restricted": (0, "none"),
        "same-cause-repeat": (2, "none"),
        "contract-failure": (0, "none"),
        "unrecoverable": (0, "none"),
    }
    max_attempts, delay = caps.get(klass, (0, "none"))
    emit("FAILURE_CLASS", klass)
    emit("MAX_ATTEMPTS", max_attempts)
    emit("RETRY_DELAY", delay)
    return 0


def normalize_outcome(args: argparse.Namespace) -> int:
    st = _state(Path(args.implement_tmpdir))
    if st.get("STALL_TRACKING") == "true":
        outcome = "stalled"
        success = "false"
    elif st.get("MERGE_RESULT") == "already_merged":
        outcome = "force-merged-externally"
        success = "true"
    else:
        outcome = "completed"
        success = "true"
    emit("IMPLEMENT_NORMALIZED_OUTCOME", outcome)
    emit("IMPLEMENT_OUTCOME_SUCCEEDED", success)
    return 0


def normalize_issue_env(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    out = Path(args.issue_stdout_file)
    env = tmpdir / "stall-recovery-issue.env"
    def fail(reason: str) -> int:
        with contextlib.suppress(OSError):
            env.unlink()
        emit("NORMALIZED", "false")
        emit("REASON", reason)
        return 0
    if args.issue_exit_code is None:
        return fail("issue-exit-code-missing")
    if str(args.issue_exit_code) != "0":
        return fail("issue-exit-code")
    text = out.read_text(encoding="utf-8", errors="replace") if out.is_file() else ""
    if re.search(r"^ISSUES_FAILED=[1-9]", text, re.MULTILINE):
        return fail("issues-failed-nonzero")
    if re.search(r"^ISSUE_1_FAILED=true", text, re.MULTILINE):
        return fail("issue-1-failed")
    num = read_kv(out, "ISSUE_1_NUMBER") or read_kv(out, "ISSUE_1_DUPLICATE_OF_NUMBER")
    url = read_kv(out, "ISSUE_1_URL") or read_kv(out, "ISSUE_1_DUPLICATE_OF_URL")
    if not re.match(r"https://github\.com/.+/.+/issues/\d+$", url or ""):
        return fail("issue-url-missing")
    write_kvs(env, {"ISSUE_NUMBER": num, "ISSUE_URL": url})
    emit("NORMALIZED", "true")
    emit("ISSUE_NUMBER", num)
    emit("ISSUE_URL", url)
    return 0


def _artifact_path(tmpdir: Path, default_name: str, prefix: str) -> Path:
    if not prefix or prefix == "stall-recovery":
        return tmpdir / default_name
    return tmpdir / (prefix + default_name.removeprefix("stall-recovery"))


def record_escalation(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    prefix = getattr(args, "artifact_prefix", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    site = args.site
    trigger = args.trigger
    step = args.step
    phase = args.phase
    dispatcher = args.dispatcher
    exit_code = args.exit_code
    if not _safe_token("site", site, generic=generic) or not _safe_token("trigger", trigger, generic=generic):
        print("stall-recovery: record-escalation token validation failed", file=sys.stderr)
        return 1
    if not _safe_token("step", step, generic=generic) or not _safe_token("phase", phase, generic=generic):
        print("stall-recovery: record-escalation token validation failed", file=sys.stderr)
        return 1
    rel_log = ""
    detail_log = getattr(args, "failure_detail_log", "") or ""
    if detail_log:
        detail_path = Path(detail_log)
        if not _validate_tmpdir_local_file(tmpdir, detail_path):
            print("stall-recovery: --failure-detail-log invalid", file=sys.stderr)
            return 1
        try:
            rel = detail_path.resolve().relative_to(tmpdir.resolve())
            rel_log = str(rel)
        except ValueError:
            rel_log = "redacted"
    ledger = _artifact_path(tmpdir, "stall-recovery-escalation-ledger.tsv", prefix)
    row = (
        f"utc={datetime.now(UTC).isoformat()}\tsite={site}\ttrigger={trigger}\tstep={step}\tphase={phase}"
        f"\tdispatcher={dispatcher}\texit_code={exit_code}\tfailure_detail_log={rel_log}\n"
    )
    try:
        old = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
        if old and not old.endswith("\n"):
            old += "\n"
        ledger.write_text(old + row, encoding="utf-8")
        emit("ESCALATION_RECORDED", "true")
        emit("ESCALATION_LEDGER_FILE", ledger)
    except OSError:
        (tmpdir / "stall-recovery-escalation-record-failure.env").write_text("RECORD_ESCALATION_FAILED=true\nREASON=canonical-ledger-not-writable\n", encoding="utf-8")
        (tmpdir / "stall-recovery-escalation-ledger.fallback.tsv").write_text(row, encoding="utf-8")
        emit("ESCALATION_RECORDED", "false")
        emit("ESCALATION_FALLBACK_WRITTEN", "true")
    return 0


def compose_report(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    cls = tmpdir / "stall-recovery-classification.env"
    root = tmpdir / "stall-recovery-root-cause.md"
    bounded = tmpdir / "stall-recovery-bounded-root-cause.md"
    summary = "larch stall recovery report"
    if root.is_file():
        m = re.search(r"^summary=(.*)$", root.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
        if m:
            summary = m.group(1)
    kind = args.report_kind
    title_kind = "terminal" if kind == "terminal-failure" else "escalation"
    profile = getattr(args, "profile", "implement")
    artifact_prefix = getattr(args, "artifact_prefix", "") or ""
    if profile == "generic":
        first = artifact_prefix.split("-")[0] if artifact_prefix else ""
        skill_label = f"/{first}" if first else "/generic"
    else:
        skill_label = "/implement"
    body = f"[Bug] {skill_label} {title_kind}: {summary}\n\n| Field | Value |\n| --- | --- |\n| Failure class | `{read_kv(cls, 'FAILURE_CLASS', 'unknown')}` |\n| Run ID | `{read_kv(tmpdir / 'parent-issue.md', 'RUN_ID', 'unknown')}` |\n| Larch version | `unknown` |\n\n"
    if bounded.is_file():
        body += bounded.read_text(encoding="utf-8", errors="replace") + "\n"
    sig = hashlib.sha256(body.encode()).hexdigest()[:16]
    if args.surface == "issue-input":
        body = f"### {body}<!-- larch-stall:signature={sig} -->\n"
    if args.output_file:
        Path(args.output_file).write_text(body, encoding="utf-8")
    if args.surface == "chat-print" and not args.output_file:
        sys.stdout.write(body)
    emit("STALL_RECOVERY_REPORT_STATUS", "dry-run" if os.environ.get("LARCH_STALL_RECOVERY_DRY_RUN") else "printed")
    emit("REPORT_DEDUP_SIGNATURE", sig)
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
        emit("STALL_RECOVERY_REPORT_STATUS", "dry-run")
        return 0
    body_file = Path(args.body_file) if args.body_file else tmpdir / "stall-recovery-issue-input.md"
    attempts_file = Path(args.attempts_file) if args.attempts_file else tmpdir / "stall-recovery-tier-a-attempts.md"
    escalation_file = Path(args.escalation_ledger_file) if args.escalation_ledger_file else tmpdir / "stall-recovery-tier-a-escalation.md"
    root_file = Path(args.root_cause_file) if args.root_cause_file else tmpdir / "stall-recovery-tier-a-root-cause.md"
    for slice_file in (attempts_file, escalation_file, root_file):
        if not slice_file.is_file():
            slice_file.write_text("", encoding="utf-8")
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    helper = plugin_root / "scripts" / "file-failure-report-cross-repo.sh"
    if not helper.is_file():
        emit("STALL_RECOVERY_REPORT_STATUS", "lookup-failed-open")
        emit("STALL_RECOVERY_REPORT_FALLBACK_REASON", "helper-missing")
        return 0
    repo_proc = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], text=True, capture_output=True, check=False)  # noqa: S607
    repo = repo_proc.stdout.strip()
    if not repo:
        emit("STALL_RECOVERY_REPORT_STATUS", "lookup-failed-open")
        emit("STALL_RECOVERY_REPORT_FALLBACK_REASON", "current-repo-unresolved")
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


def validate_token(args: argparse.Namespace) -> int:
    token = args.token or ""
    kind = getattr(args, "token_kind", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if not token or not re.fullmatch(r"[A-Za-z0-9._:-]+", token) or ".." in token or "/" in token:
        emit("TOKEN_VALID", "false")
        return 1
    if kind and not _safe_token(kind, token, generic=generic):
        emit("TOKEN_VALID", "false")
        return 1
    emit("TOKEN_VALID", "true")
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
        "protected-path-modified", "qa-pending-missing", "redactor-not-executable", "resume-incompatible",
        "submodule-dirty", "submodule-edit-required-out-of-scope", "local-unfixable", "checks-failed",
        "checks-timeout", "ci-health-failed", "ci-timeout", "ci-status-error", "ci-too-many-rebases",
        "no-fix-path", "main-agent-required", "coder-main-agent-required", "main-agent-vote-required",
    }
    return value in expanded


def _safe_source_script_value(value: str, *, generic: bool) -> bool:
    if value in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"}:
        return True
    return generic and value in _GENERIC_SOURCE_SCRIPTS


def _terminal_state_value_valid(key: str, value: str, tmpdir: Path, *, generic: bool) -> bool:
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
        return _safe_token("site", value, generic=generic)
    if key == "TRIGGER":
        return _safe_token("trigger", value, generic=generic)
    if key == "BAIL_REASON":
        return _safe_bail_reason_value(value, generic=generic)
    if key == "EXIT_CODE":
        return value == "unknown" or (value.isdigit() and re.fullmatch(r"[0-9]+", value) is not None)
    if key == "FAILURE_DETAIL_LOG":
        if not value:
            return True
        return _validate_tmpdir_local_file(tmpdir, Path(value))
    if key == "SOURCE_SCRIPT":
        return _safe_source_script_value(value, generic=generic)
    if key == "ROOT_CAUSE_HINT":
        return not value or value in {"larch-defect", "environment", "operator-action"}
    if key in {"OCCURRED_AT", "EVIDENCE_REF"}:
        return not value or not _reject_rawish_terminal_value(value)
    return False


def validate_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if not tmpdir.is_dir():
        emit("VALID", "false")
        return 1
    state_file = Path(getattr(args, "primary_state_file", None) or tmpdir / "design-failure-terminal-state.env")
    if not state_file.is_file():
        emit("VALID", "false")
        return 1
    found: dict[str, str] = {}
    for raw in state_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            emit("VALID", "false")
            return 1
        k, v = line.split("=", 1)
        if k not in _TERMINAL_STATE_ALLOWED_KEYS:
            emit("VALID", "false")
            return 1
        found[k] = v
    for required in _TERMINAL_STATE_REQUIRED_KEYS:
        if required not in found:
            emit("VALID", "false")
            return 1
        if required != "FAILURE_DETAIL_LOG" and not found[required]:
            emit("VALID", "false")
            return 1
    for key, value in found.items():
        if key == "FAILURE_DETAIL_LOG":
            if not _terminal_state_value_valid(key, value, tmpdir, generic=generic):
                emit("VALID", "false")
                return 1
            continue
        if _reject_rawish_terminal_value(value):
            emit("VALID", "false")
            return 1
        if not _terminal_state_value_valid(key, value, tmpdir, generic=generic):
            emit("VALID", "false")
            return 1
    emit("VALID", "true")
    return 0


_SENSITIVE_TOKEN_ALLOWLIST = frozenset({
    "larch-defect", "environment", "operator-action", "terminal-failure", "escalation-success",
    "merged", "force-merged-externally", "pr-created", "pr-created-draft", "forked-dry-run",
    "main-agent-required", "lint-fix-loop", "ship-pr", "codex", "cursor", "claude", "approved",
    "approved-partition", "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail",
})


def _sensitive_token_rejects_file(corpus_path: Path, candidate_path: Path) -> bool:
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
        if "=" in stripped:
            _key, _, value = stripped.partition("=")
            if value in _SENSITIVE_TOKEN_ALLOWLIST:
                continue
            if value and value not in {"", stripped} and value in candidate_text:
                return True
        if stripped in candidate_text:
            return True
    if re.search(r"https?://|git@github\.com:|github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", candidate_text):
        return True
    return bool(re.search(r"(^|[\s`(])/(Users|home|private|tmp|var|Volumes)/[^\s`)]+", candidate_text))


def validate_tier_b_public_file(args: argparse.Namespace) -> int:
    path = Path(args.public_file)
    tmpdir = Path(args.tmpdir) if args.tmpdir else Path(args.implement_tmpdir)
    if not (path.is_absolute() and not path.is_symlink() and path.is_file()):
        emit("PUBLIC_FILE_VALID", "false")
        return 1
    if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
        emit("PUBLIC_FILE_VALID", "false")
        return 1
    corpus_path_str = getattr(args, "sensitive_corpus_file", None)
    if not corpus_path_str:
        emit("PUBLIC_FILE_VALID", "false")
        return 1
    cp = Path(corpus_path_str)
    if not (cp.is_absolute() and not cp.is_symlink() and (cp == tmpdir or tmpdir in cp.parents) and cp.is_file()):
        emit("PUBLIC_FILE_VALID", "false")
        return 1
    try:
        if _sensitive_token_rejects_file(cp, path):
            emit("PUBLIC_FILE_VALID", "false")
            return 1
    except OSError:
        emit("PUBLIC_FILE_VALID", "false")
        return 1
    emit("PUBLIC_FILE_VALID", "true")
    return 0


def clear_stall(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    for name in ("stall-recovery-classification.env", "stall-recovery-issue.env"):
        with contextlib.suppress(OSError):
            (tmpdir / name).unlink()
    emit("CLEARED", "true")
    return 0


def seed_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    write_kvs(tmpdir / "ship-pr-state.sh", {"STALL_TRACKING": "true", "STALL_STEP": args.step or "unknown", "PHASE": args.phase or "unknown"})
    emit("SEEDED", "true")
    return 0


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _issue_url_number(url: str) -> str | None:
    match = re.fullmatch(r"https://github.com/[^/#]+/[^/#]+/issues/(\d+)", url)
    return match.group(1) if match else None


def _validate_tmpdir_local_file(tmpdir: Path, file_path: Path) -> bool:
    if not file_path.is_absolute() or file_path.is_symlink() or not file_path.is_file():
        return False
    try:
        _ = file_path.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        return False
    return True


def _delegate_stall_recovery_subcommand(sub: str, rest: list[str]) -> int:
    if not _STALL_RECOVERY_SH.is_file():
        print(f"stall-recovery: missing script: {_STALL_RECOVERY_SH}", file=sys.stderr)
        return 1
    completed = subprocess.run(["/bin/bash", str(_STALL_RECOVERY_SH), sub, *rest], check=False)
    return completed.returncode


def is_larch_dev_clone(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    forked = read_kv(tmpdir / "ship-pr-state.sh", "FORKED_TARGET") or read_kv(tmpdir / "session-env.sh", "FORKED_TARGET")
    if forked and _truthy(forked):
        emit("LARCH_DEV_CLONE", "false")
        return 0
    root = getattr(args, "working_tree_root", "") or ""
    if not root:
        completed = subprocess.run(["/usr/bin/git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
        root = completed.stdout.strip() if completed.returncode == 0 else ""
    dev_clone = bool(root) and (Path(root) / "skills" / "implement" / "SKILL.md").is_file()
    emit("LARCH_DEV_CLONE", "true" if dev_clone else "false")
    return 0


def normalize_file_failure_report_env(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.is_dir():
        print("stall-recovery: --implement-tmpdir must exist", file=sys.stderr)
        return 1
    env_file = Path(args.file_failure_report_env)
    if not _validate_tmpdir_local_file(tmpdir, env_file):
        print("stall-recovery: --file-failure-report-env invalid", file=sys.stderr)
        return 1
    status = read_kv(env_file, "FILE_FAILURE_REPORT_STATUS")
    url = read_kv(env_file, "FILE_FAILURE_REPORT_URL")
    reason = read_kv(env_file, "FILE_FAILURE_REPORT_FALLBACK_REASON")
    allowed = {"filed", "dry-run", "dedup-comment", "no-match", "fallback-print-required", "lookup-failed-open"}
    if status not in allowed:
        status = "fallback-print-required"
        reason = reason or "helper-status-missing"
    emit("STALL_RECOVERY_REPORT_STATUS", status)
    if url:
        emit("STALL_RECOVERY_REPORT_URL", url)
        number = _issue_url_number(url)
        if number:
            emit("STALL_RECOVERY_REPORT_ISSUE_URL", url)
            emit("STALL_RECOVERY_REPORT_ISSUE_NUMBER", number)
    if reason:
        emit("STALL_RECOVERY_REPORT_FALLBACK_REASON", reason)
    return 0


def populate_sensitive_corpus(rest: list[str], *, implement_tmpdir: str) -> int:
    if not any(arg == "--implement-tmpdir" for arg in rest):
        rest = ["--implement-tmpdir", implement_tmpdir, *rest]
    return _delegate_stall_recovery_subcommand("populate-sensitive-corpus", rest)


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
        "ci-fix-exhausted": (8, "none"),
        "dispatch-failure": (3, "none"),
        "protected-path": (1, "none"),
        "submodule-restricted": (0, "none"),
        "same-cause-repeat": (2, "none"),
        "contract-failure": (0, "none"),
        "unrecoverable": (0, "none"),
    }
    return [f"{klass}\t{max_attempts}\t{delay}" for klass in classes for max_attempts, delay in [caps[klass]]]


def _doc_allowlist_lines() -> list[str]:
    contract = _REPO_ROOT / "skills" / "implement" / "scripts" / "stall-recovery-report.md"
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
    contract = _REPO_ROOT / "skills" / "implement" / "scripts" / "stall-recovery-report.md"
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
    tsv_path = _REPO_ROOT / "skills" / "implement" / "scripts" / "stall-recovery-report-allowlists.tsv"
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
    compound_safe = _safe_token("trigger", "ci-local-unfixable:job_1,job-2", generic=False)
    compound_bad = _safe_token("trigger", "ci-local-unfixable:../../secret", generic=False)
    if not compound_safe or compound_bad:
        print("stall-recovery: ci-local-unfixable compound grammar drift", file=sys.stderr)
        return 1
    for token in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
        if not _safe_bail_reason_value(token, generic=False):
            print(f"stall-recovery: runtime bail token not render-safe: {token}", file=sys.stderr)
            return 1
    emit("LINT_OK", "true")
    return 0


def chat_print(args: argparse.Namespace) -> int:
    if args.input_file and Path(args.input_file).is_file():
        sys.stdout.write(Path(args.input_file).read_text(encoding="utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("stall-recovery: missing subcommand", file=sys.stderr)
        return 2
    sub, rest = argv[0], argv[1:]
    p = argparse.ArgumentParser(prog=f"cli.py stall-recovery {sub}")
    p.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", "."))
    if sub == "classify":
        p.add_argument("--failure-detail-log")
        p.add_argument("--attempts-file")
        p.add_argument("--bail-reason", default="")
        p.add_argument("--in-memory-stall-tracking")
        p.add_argument("--stall-step", default="")
        p.add_argument("--phase", default="")
        p.add_argument("--exit-code", default="")
        p.add_argument("--dispatcher", default="")
        ns, _ = p.parse_known_args(rest)
        return classify(ns)
    if sub == "init-attempts":
        p.add_argument("--attempts-file")
        ns, _ = p.parse_known_args(rest)
        return init_attempts(ns)
    if sub == "record-attempt":
        p.add_argument("--attempts-file")
        p.add_argument("--class", dest="failure_class", required=True)
        p.add_argument("--signature", required=True)
        p.add_argument("--resume-hint", default="none")
        p.add_argument("--outcome", default="failed")
        ns, _ = p.parse_known_args(rest)
        return record_attempt(ns)
    if sub == "retry-policy":
        p.add_argument("--class", dest="failure_class", required=True)
        ns, _ = p.parse_known_args(rest)
        return retry_policy(ns)
    if sub == "normalize-outcome":
        ns, _ = p.parse_known_args(rest)
        return normalize_outcome(ns)
    if sub == "normalize-issue-env":
        p.add_argument("--issue-stdout-file", required=True)
        p.add_argument("--issue-exit-code")
        ns, _ = p.parse_known_args(rest)
        return normalize_issue_env(ns)
    if sub == "record-escalation":
        p.add_argument("--site", required=True)
        p.add_argument("--trigger", required=True)
        p.add_argument("--step", required=True)
        p.add_argument("--phase", required=True)
        p.add_argument("--dispatcher", required=True)
        p.add_argument("--exit-code", default="unknown")
        p.add_argument("--failure-detail-log", default="")
        p.add_argument("--artifact-prefix", default="")
        p.add_argument("--profile", default="implement")
        ns, _ = p.parse_known_args(rest)
        return record_escalation(ns)
    if sub == "dedup-tier-a-report":
        p.add_argument("--body-file")
        p.add_argument("--attempts-file")
        p.add_argument("--escalation-ledger-file")
        p.add_argument("--root-cause-file")
        ns, _ = p.parse_known_args(rest)
        return dedup_tier_a_report(ns)
    if sub == "compose-report":
        p.add_argument("--report-kind", default="terminal-failure")
        p.add_argument("--surface", default="chat-print")
        p.add_argument("--output-file")
        p.add_argument("--profile", default="implement")
        p.add_argument("--artifact-prefix", default="")
        ns, _ = p.parse_known_args(rest)
        return compose_report(ns)
    if sub == "validate-token":
        p.add_argument("--token", default="")
        p.add_argument("--value", default="")
        p.add_argument("--token-kind", default="")
        p.add_argument("--profile", default="implement")
        p.add_argument("--artifact-prefix", default="")
        ns, _ = p.parse_known_args(rest)
        ns.token = ns.token or ns.value
        return validate_token(ns)
    if sub == "validate-terminal-state":
        p.add_argument("--primary-state-file", default="")
        p.add_argument("--profile", default="implement")
        p.add_argument("--artifact-prefix", default="")
        ns, _ = p.parse_known_args(rest)
        return validate_terminal_state(ns)
    if sub == "validate-tier-b-public-file":
        p.add_argument("--public-file", required=True)
        p.add_argument("--tmpdir")
        p.add_argument("--sensitive-corpus-file", default="")
        p.add_argument("--profile", default="implement")
        p.add_argument("--artifact-prefix", default="")
        ns, _ = p.parse_known_args(rest)
        return validate_tier_b_public_file(ns)
    if sub == "clear-stall":
        ns, _ = p.parse_known_args(rest)
        return clear_stall(ns)
    if sub == "seed-terminal-state":
        p.add_argument("--step")
        p.add_argument("--phase")
        ns, _ = p.parse_known_args(rest)
        return seed_terminal_state(ns)
    if sub == "chat-print":
        p.add_argument("--input-file")
        ns, _ = p.parse_known_args(rest)
        return chat_print(ns)
    if sub == "is-larch-dev-clone":
        p.add_argument("--working-tree-root", default="")
        ns, _ = p.parse_known_args(rest)
        return is_larch_dev_clone(ns)
    if sub == "normalize-file-failure-report-env":
        p.add_argument("--file-failure-report-env", required=True)
        ns, _ = p.parse_known_args(rest)
        return normalize_file_failure_report_env(ns)
    if sub == "populate-sensitive-corpus":
        ns, _ = p.parse_known_args(rest)
        return populate_sensitive_corpus(rest, implement_tmpdir=str(ns.implement_tmpdir))
    if sub == "lint":
        return lint_subcommand(rest)
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
