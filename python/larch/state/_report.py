"""Report composition, deduplication, and chat printing for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from larch.state._tokens import (
    _DEFAULT_CLASSIFICATION_FILE,
    _DEFAULT_ATTEMPTS_FILE,
    _DEFAULT_BOUNDED_ROOT_CAUSE_FILE,
    _DEFAULT_CHAT_PRINT,
    _DEFAULT_ESCALATION_FALLBACK,
    _DEFAULT_ESCALATION_LEDGER,
    _DEFAULT_ISSUE_INPUT,
    _DEFAULT_OPERATOR_ACTION_RECORD,
    _DEFAULT_OPERATOR_ACTION_SENTINEL,
    _DEFAULT_RECORD_FAILURE_MARKER,
    _DEFAULT_ROOT_CAUSE_FILE,
    _DEFAULT_SENSITIVE_CORPUS,
    _DEFAULT_TIER_A_ATTEMPTS_SLICE,
    _DEFAULT_TIER_A_ESCALATION_SLICE,
    _DEFAULT_TIER_A_ROOT_CAUSE_SLICE,
    _DEFAULT_TIER_B_ATTEMPTS_SLICE,
    _DEFAULT_TIER_B_ESCALATION_SLICE,
    _DEFAULT_TIER_B_ROOT_CAUSE_SLICE,
    _DEFAULT_TITLE_FILE,
    _REPO_ROOT,
    _safe_bail_value,
    _safe_class_value,
    _safe_phase_value,
    _safe_simple_token,
    _safe_step_value,
    _safe_title_summary,
    _report_skill_label,
    _truthy,
    _validate_tmpdir_local_file,
    _validate_tmpdir_write_path,
    emit,
    read_kv,
    write_kvs,
)
from larch.state._detail_log import _read_failure_detail_log_with_sidecar_fallback
from larch.state._escalation import (
    _artifact_path,
    _record_escalation_tool_failure_present,
    _validate_artifact_prefix,
)
from larch.state._corpus import (
    _sensitive_token_rejects_file,
    build_sensitive_corpus_from_evidence,
)
from larch.state._normalize import normalize_file_failure_report_env

ALLOWLIST_TABLE_COLUMNS = 4
RETRY_POLICY_TABLE_COLUMNS = 3


def _compose_error(message: str) -> int:
    print(f"stall-recovery: {message}", file=sys.stderr)
    return 1


def _compose_path(*, args: argparse.Namespace, attr: str, tmpdir: Path, default_name: str, prefix: str) -> Path:
    value = getattr(args, attr, "") or ""
    return Path(value) if value else _artifact_path(tmpdir=tmpdir, default_name=default_name, prefix=prefix)


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
            match = re.search(r'"version"\s*:\s*"([^"]+)"', text)
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


def _compose_tier_a_issue(  # noqa: PLR0913,RUF100
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
    dedup_marker: str,
) -> str:
    bail = read_kv(path=class_file, key="BAIL_REASON_RAW", default="") or read_kv(path=class_file, key="BAIL_REASON", default="") or "none"
    body = [
        f"### {title}",
        dedup_marker,
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
    detail_content, detail_valid, _detail_log_path = _read_failure_detail_log_with_sidecar_fallback(
        tmpdir=tmpdir,
        primary=detail_log,
        ledger=ledger,
        fallback=fallback,
        allow_without_primary=True,
    )
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
        body = _compose_tier_a_issue(
            kind=kind,
            class_file=class_file,
            attempts_file=attempts_file,
            ledger=ledger,
            fallback=fallback,
            marker=marker,
            root_file=root_file,
            title=title,
            tmpdir=tmpdir,
            session_env_file=session_env_file,
            dedup_marker=_report_marker(report_sig),
        )
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
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
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
    return normalize_file_failure_report_env(
        argparse.Namespace(implement_tmpdir=str(tmpdir), file_failure_report_env=str(out))
    )


def chat_print(args: argparse.Namespace) -> int:
    args.surface = "chat-print"
    return compose_report(args)
