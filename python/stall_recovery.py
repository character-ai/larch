"""Stall recovery report helpers shared by /implement and /design."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import sys
from collections.abc import Mapping
from datetime import datetime, UTC
from pathlib import Path

MAX_PUBLIC_FILE_BYTES = 256_000

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
    if value in _OUTCOMES:
        return True
    if value.startswith("cancelled-") and re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        return True
    return False


def _safe_step(value: str, generic: bool) -> bool:
    if generic and value in _GENERIC_STEPS:
        return True
    if value in {"bump-branch-guard", "merge-loop-iteration-cap", "rebase-failed"}:
        return True
    if re.fullmatch(r"[2-9]|1[0-5]", value):
        return True
    if re.fullmatch(r"(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", value):
        return True
    return False


def _safe_token(kind: str, value: str, generic: bool) -> bool:
    if not value:
        return False
    if kind == "outcome":
        return _safe_outcome(value)
    if kind == "step":
        return _safe_step(value, generic)
    if kind == "phase":
        return value in _COMMON_PHASES or (generic and value in _GENERIC_PHASES)
    if kind == "site":
        return value in _COMMON_SITES or (generic and value in _GENERIC_SITES)
    if kind == "trigger":
        if value in _COMMON_TRIGGERS:
            return True
        if generic and value in _GENERIC_TRIGGERS:
            return True
        if re.fullmatch(r"ci-local-unfixable:[A-Za-z0-9_,-]+", value):
            return True
        return False
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


def _classify_text(text: str, bail: str, step: str, phase: str) -> tuple[str, str, str]:
    _ = phase
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
    if bail in {"adopted-issue-closed", "tracking-init-failed", "recovery-out-of-scope", "ci-fix-exhausted"}:
        return "unrecoverable", "none", "bail-token"
    return "unrecoverable", "none", "fallback"


def classify(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    st = _state(tmpdir)
    step = args.stall_step or st.get("STALL_STEP", "")
    phase = args.phase or st.get("PHASE", "")
    bail = args.bail_reason or st.get("BAIL_REASON", "")
    detail = ""
    if args.failure_detail_log and Path(args.failure_detail_log).is_file():
        detail = Path(args.failure_detail_log).read_text(encoding="utf-8", errors="replace")[:8192]
    klass, hint, pattern = _classify_text(detail, bail, step, phase)
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
    caps = {"transient-infra": (4, "sleep-seconds.sh 5"), "same-cause-repeat": (2, "none"), "lint-failure": (2, "none"), "test-failure": (2, "none")}
    max_attempts, delay = caps.get(klass, (1, "none"))
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


def record_escalation(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    ledger = tmpdir / "stall-recovery-escalation-ledger.tsv"
    row = f"utc={datetime.now(UTC).isoformat()}\tsite={args.site}\ttrigger={args.trigger}\tstep={args.step}\tphase={args.phase}\tdispatcher={args.dispatcher}\texit_code={args.exit_code}\n"
    try:
        old = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
        if old and not old.endswith("\n"):
            old += "\n"
        ledger.write_text(old + row, encoding="utf-8")
        emit("ESCALATION_RECORDED", "true")
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


def validate_token(args: argparse.Namespace) -> int:
    token = args.token or ""
    kind = getattr(args, "token_kind", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if not token or not re.fullmatch(r"[A-Za-z0-9._:-]+", token) or ".." in token or "/" in token:
        emit("TOKEN_VALID", "false")
        return 1
    if kind and not _safe_token(kind, token, generic):
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
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE", "SOURCE_SCRIPT",
}


def validate_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.is_dir():
        emit("TERMINAL_STATE_VALID", "false")
        return 1
    state_file = Path(getattr(args, "primary_state_file", None) or tmpdir / "design-failure-terminal-state.env")
    if not state_file.is_file():
        emit("TERMINAL_STATE_VALID", "false")
        return 1
    found: dict[str, str] = {}
    for raw in state_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            emit("TERMINAL_STATE_VALID", "false")
            return 1
        k, v = line.split("=", 1)
        if k not in _TERMINAL_STATE_ALLOWED_KEYS:
            emit("TERMINAL_STATE_VALID", "false")
            return 1
        found[k] = v
    missing = _TERMINAL_STATE_REQUIRED_KEYS - set(found)
    if missing:
        emit("TERMINAL_STATE_VALID", "false")
        return 1
    emit("TERMINAL_STATE_VALID", "true")
    return 0


def validate_tier_b_public_file(args: argparse.Namespace) -> int:
    path = Path(args.public_file)
    tmpdir = Path(args.tmpdir) if args.tmpdir else Path(args.implement_tmpdir)
    ok = path.is_absolute() and not path.is_symlink() and (path == tmpdir or tmpdir in path.parents) and path.is_file() and path.stat().st_size <= MAX_PUBLIC_FILE_BYTES
    emit("PUBLIC_FILE_VALID", str(ok).lower())
    return 0 if ok else 1


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
        p.add_argument("--exit-code", required=True)
        ns, _ = p.parse_known_args(rest)
        return record_escalation(ns)
    if sub in {"compose-report", "dedup-tier-a-report"}:
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
        ns, _ = p.parse_known_args(rest)
        return validate_terminal_state(ns)
    if sub == "validate-tier-b-public-file":
        p.add_argument("--public-file", required=True)
        p.add_argument("--tmpdir")
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
    if sub in {"populate-sensitive-corpus", "normalize-file-failure-report-env", "is-larch-dev-clone", "lint"}:
        emit("STATUS", "ok")
        return 0
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
