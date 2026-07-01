"""Sensitive corpus building and tier-B public file validation for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from pathlib import Path

from larch.state._tokens import (
    _DEFAULT_ATTEMPTS_FILE,
    _DEFAULT_CLASSIFICATION_FILE,
    _DEFAULT_ESCALATION_FALLBACK,
    _DEFAULT_ESCALATION_LEDGER,
    _DEFAULT_RECORD_FAILURE_MARKER,
    _DEFAULT_SENSITIVE_CORPUS,
    _safe_bail_reason_value,
    _safe_matched_pattern_value,
    _safe_step,
    _safe_token,
    _validate_tmpdir_local_file,
    _validate_tmpdir_write_path,
    emit,
    read_kv,
)
from larch.state._detail_log import _read_validated_failure_detail_log
from larch.state._escalation import _artifact_path, _validate_artifact_prefix

MAX_PUBLIC_FILE_BYTES = 256_000
SAFE_SMALL_INTEGER_DIGITS = 4

_SENSITIVE_TOKEN_ALLOWLIST = frozenset({
    "larch-defect", "environment", "operator-action", "terminal-failure", "escalation-success",
    "merged", "force-merged-externally", "pr-created", "pr-created-draft", "forked-dry-run",
    "main-agent-required", "lint-fix-loop", "ship-pr", "codex", "cursor", "claude", "approved",
    "approved-partition", "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
    "failed-judge-panel", "failed-publish-tail",
})

_SENSITIVE_ASSIGNMENT_RE = re.compile(r"(?:^|[\s(])([A-Z][A-Z0-9_]{2,})=([^\s]{3,})")


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
        "step2-impl", "step5-review", "step8-shippr", "checks-commit-route-retry",
    }:
        return True
    if _safe_token(kind="source-script", value=value, generic=True):
        return True
    if _safe_matched_pattern_value(value) != "redacted":
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9._+-]+", value) and value in {"codex", "cursor", "claude", "bash", "python", "split-path"})


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
    build_sensitive_corpus_from_evidence(
        tmpdir=tmpdir,
        sensitive_file=sensitive_file,
        class_file=class_file,
        attempts_file=attempts_file,
        ledger=ledger,
        fallback=fallback,
        marker=marker,
        out_file=sensitive_file,
    )
    emit(key="SENSITIVE_CORPUS_FILE", value=sensitive_file)
    return 0
