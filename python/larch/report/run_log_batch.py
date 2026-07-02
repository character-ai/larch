# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Batch registry, path utilities, and low-level I/O for larch run-logs."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from larch.core import redact
from larch import io as larch_io
from larch.errors import ShipError

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REQUIRED_FILES_TSV = _REPO_ROOT / "docs" / "run-logs-required-files.tsv"
_VOTE_OUTPUT_TRUNCATE_BYTES = 2048
_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_QUIET_LOG_RE = re.compile(r"^larch-quiet-[A-Za-z0-9._-]+-[0-9]+\.log$")
# Non-unique placeholder run-ids (e.g. ``run-1``). Real runs name their log
# directory after the unique session run-id (a UUID, or the session tmpdir
# basename). A ``run-<N>`` value is a stale/degraded fallback that collides
# across concurrent runs and clones, so the same shared path lands in every
# PR and breaks rebases (issue #4397). Such a value must never name a run-log
# directory that is copied into the consumer repo.
_PLACEHOLDER_RUN_ID_RE = re.compile(r"^run-[0-9]+$")


@dataclass(frozen=True)
class BatchInfo:
    extension: str
    mode: str
    sanitizer: str


_LARCH_LOG_BATCHES: dict[str, BatchInfo] = {
    "parent-issue": BatchInfo(".md", "replace", "none"),
    "pre-review-head": BatchInfo(".txt", "replace", "none"),
    "pre-review-untracked": BatchInfo(".txt", "replace", "none"),
    "codex-impl-transcript": BatchInfo(".txt", "replace", "none"),
    "codex-impl-transcript-meta": BatchInfo(".txt.meta", "replace", "none"),
    "codex-impl-transcript-prompt": BatchInfo(".txt", "replace", "none"),
    "codex-commit-message": BatchInfo(".txt", "replace", "none"),
    "codex-impl-manifest-raw": BatchInfo(".json", "replace", "none"),
    "plan-review-tally": BatchInfo(".json", "replace", "json-object"),
    "code-review-tally": BatchInfo(".json", "replace", "json-object"),
    "review-findings-full": BatchInfo(".jsonl", "replace", "none"),
    "reviewer-prune-ledger": BatchInfo(".tsv", "replace", "none"),
    "review-context": BatchInfo(".md", "replace", "none"),
    "review-findings": BatchInfo(".ndjson", "append", "json-lines"),
    "review-panel-manifest": BatchInfo(".ndjson", "replace", "none"),
    "panel-prompt-sizes": BatchInfo(".tsv", "replace", "none"),
    "review-round-summary": BatchInfo(".md", "replace", "none"),
    "review-scout-manifest": BatchInfo(".json", "replace", "json-object"),
    "review-tally": BatchInfo(".md", "replace", "none"),
    "review-findings-classification-round-1": BatchInfo(".tsv", "replace", "none"),
    "review-findings-classification-round-2": BatchInfo(".tsv", "replace", "none"),
    "review-findings-classification-round-3": BatchInfo(".tsv", "replace", "none"),
    "review-findings-classification-round-4": BatchInfo(".tsv", "replace", "none"),
    "review-findings-classification-round-5": BatchInfo(".tsv", "replace", "none"),
    "version-bump-reasoning": BatchInfo(".md", "replace", "none"),
    "oos-issues": BatchInfo(".ndjson", "append", "json-lines"),
    "run-statistics": BatchInfo(".md", "replace", "none"),
    "token-report": BatchInfo(".json", "replace", "none"),
    "timing-report": BatchInfo(".json", "replace", "none"),
    "execution-issues": BatchInfo(".ndjson", "append", "json-lines"),
    "final-bail-reason": BatchInfo(".txt", "replace", "none"),
    "include-probe-evidence": BatchInfo(".md", "replace", "none"),
    "session-transcript": BatchInfo(".jsonl", "replace", "none"),
    "vendor-failure-diagnostics": BatchInfo(".txt", "replace", "none"),
    "plan-goals-test": BatchInfo(".md", "replace", "plan-goals"),
    "ship-route-exit-handoff": BatchInfo(".env", "replace", "none"),
}


def _batch_extension(slug: str) -> str:
    return _LARCH_LOG_BATCHES[slug].extension


def _batch_mode(slug: str) -> str:
    return _LARCH_LOG_BATCHES[slug].mode


def _batch_sanitizer(slug: str) -> str:
    return _LARCH_LOG_BATCHES[slug].sanitizer


def _batch_list() -> tuple[str, ...]:
    return tuple(sorted(_LARCH_LOG_BATCHES))


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _emit_larch_log_envelope(
    *,
    path: Path | None = None,
    written: bool,
    unchanged: bool,
    commit_sha: str = "",
    error: str = "",
    extra: dict[str, str | int] | None = None,
) -> None:
    size = path.stat().st_size if path is not None and path.is_file() else 0
    print(f"LOG_WRITTEN={'true' if written else 'false'}")
    print(f"LOG_PATH={path if path is not None else ''}")
    print(f"BYTES={size}")
    print(f"SHA256={_sha256_file(path) if path is not None else ''}")
    print(f"COMMIT_SHA={commit_sha}")
    print(f"UNCHANGED={'true' if unchanged else 'false'}")
    if error:
        print(f"ERROR={error}")
    for key, value in (extra or {}).items():
        print(f"{key}={value}")


def _larch_log_fail(*, code: int, message: str) -> int:
    _emit_larch_log_envelope(
        path=None,
        written=False,
        unchanged=False,
        error=message,
    )
    return code


def validate_run_id_slug(run_id: str) -> bool:
    if not run_id or ".." in run_id or "/" in run_id or "\\" in run_id:
        return False
    return _SLUG_RE.match(run_id) is not None


def is_placeholder_run_id(run_id: str) -> bool:
    """True for non-unique placeholder run-ids (e.g. ``run-1``).

    Such a value must never name a run-log directory that is committed into the
    consumer repo: it is shared across concurrent runs and clones, so the same
    path lands in every PR and breaks rebases (issue #4397).
    """
    return bool(_PLACEHOLDER_RUN_ID_RE.match(run_id))


def _warn_placeholder_run_id(run_id: str) -> None:
    print(
        f"**⚠ run-log: refusing to commit non-unique placeholder run-id {run_id!r}; "
        "expected a unique session run-id (issue #4397). Skipping run-log commit.**",
        file=sys.stderr,
    )


def _validate_slug(*, label: str, value: str) -> None:
    if not validate_run_id_slug(value):
        raise ValueError(f"invalid {label}: {value}")


def _validate_plan_goals_payload(path: Path) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_section = False
    saw = False
    body_lines: list[str] = []
    last_test_plan = 0
    for line in lines:
        if line == "## Implementation Plan":
            if not saw:
                in_section = True
            saw = True
            continue
        if in_section:
            body_lines.append(line)
            if line == "## Test plan":
                last_test_plan = len(body_lines)
    if not saw:
        raise ValueError("plan-goals sanitizer rejected: missing Implementation Plan section")
    limit = last_test_plan - 1 if last_test_plan > 0 else len(body_lines)
    impl_body = [line for line in body_lines[:limit] if line.strip()]
    if not impl_body:
        raise ValueError("plan-goals sanitizer rejected: Implementation Plan body is empty")
    first = impl_body[0].strip().lower()
    if re.fullmatch(r"(see plan\.txt|see attached|see linked|tbd|todo)\.?", first):
        raise ValueError(
            "plan-goals sanitizer rejected: Implementation Plan body is a pointer-only placeholder",
        )


def _batch_validate_payload(*, batch: str, path: Path) -> None:
    sanitizer = _batch_sanitizer(batch)
    text = path.read_text(encoding="utf-8", errors="replace")
    if sanitizer == "json-object":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"batch {batch} requires a JSON object")
    elif sanitizer == "json-lines":
        for line in text.splitlines():
            if not line.strip():
                continue
            json.loads(line)
    elif sanitizer == "none":
        return
    elif sanitizer == "plan-goals":
        _validate_plan_goals_payload(path)
    else:
        raise ValueError(f"unsupported sanitizer for batch {batch}: {sanitizer}")


def _resolve_log_root(log_root: str | None = None) -> Path:
    raw = log_root or os.environ.get("LARCH_LOG_ROOT", "")
    if not raw:
        raise ValueError("--log-root is required (or export LARCH_LOG_ROOT for test isolation)")
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError(f"--log-root must be an absolute path: {raw}")
    return path


def _run_dir(*, log_root: Path, skill: str, run_id: str) -> Path:
    return log_root / skill / run_id


def _repo_run_dir(*, repo_root: Path, skill: str, run_id: str) -> Path:
    return repo_root / "larch-logs" / skill / run_id


def _batch_path(*, log_root: Path, skill: str, run_id: str, batch: str) -> Path:
    return _run_dir(log_root=log_root, skill=skill, run_id=run_id) / f"{batch}{_batch_extension(batch)}"


def _atomic_write(*, path: Path, content: str) -> None:
    larch_io.atomic_write(path, content, prefix=".manifest-", nofollow=True)


def _read_kv_file(*, path: Path, key: str) -> str:
    return larch_io.read_kv(path=path, key=key, first_match=True, errors="strict", on_error_default=True)


def _read_state_kv(*, state_file: str | None, key: str) -> str:
    if not state_file:
        return ""
    return _read_kv_file(path=Path(state_file), key=key)


def _redact_to_temp(input_file: Path, *, cap_bytes: int | None = None) -> Path:
    content = redact.redact(input_file.read_text(encoding="utf-8", errors="replace"))
    if cap_bytes is not None and len(content.encode("utf-8")) > cap_bytes:
        original = len(content.encode("utf-8"))
        raw = content.encode("utf-8")[:cap_bytes].decode("utf-8", errors="ignore")
        content = f"{raw}\n[TRUNCATED: original {original} bytes]\n"
    fd, tmp_name = tempfile.mkstemp(prefix="larch-log-payload.", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    tmp.write_text(content, encoding="utf-8")
    return tmp


def _write_batch(
    *, log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
    input_file: Path,
) -> tuple[Path, bool, bool]:
    if batch not in _LARCH_LOG_BATCHES:
        raise ValueError(f"unknown batch: {batch}")
    if _batch_mode(batch) != "replace":
        raise ValueError(f"batch {batch} is append-only; use append")
    cap = 8192 if batch == "codex-impl-transcript" else None
    tmp = _redact_to_temp(input_file, cap_bytes=cap)
    try:
        _batch_validate_payload(batch=batch, path=tmp)
        path = _batch_path(log_root=log_root, skill=skill, run_id=run_id, batch=batch)
        if path.is_file() and path.read_bytes() == tmp.read_bytes():
            return path, False, True
        _atomic_write(path=path, content=tmp.read_text(encoding="utf-8"))
        return path, True, False
    finally:
        tmp.unlink(missing_ok=True)


def _append_batch(
    *, log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
    record_file: Path,
) -> tuple[Path, bool, bool]:
    if batch not in _LARCH_LOG_BATCHES:
        raise ValueError(f"unknown batch: {batch}")
    if _batch_mode(batch) != "append":
        raise ValueError(f"batch {batch} is replace-only; use write")
    tmp = _redact_to_temp(record_file)
    try:
        _batch_validate_payload(batch=batch, path=tmp)
        path = _batch_path(log_root=log_root, skill=skill, run_id=run_id, batch=batch)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = tmp.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)
        return path, True, False
    finally:
        tmp.unlink(missing_ok=True)


def _redact_batch_payload(text: str) -> str:
    redacted = redact.redact(text)
    if "[content truncated" in redacted:
        msg = "redaction failed for run-log batch payload"
        raise ShipError(msg)
    return redacted


def _normalize_body_for_hash(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].startswith("### "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        _ = lines.pop(0)
    while lines and not lines[-1].strip():
        _ = lines.pop()
    return "\n".join(lines)


_APPEND_LOCK_ATTEMPTS = 100


def _append_execution_issue(*, log_file: Path, category: str, entry: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.write_text("", encoding="utf-8")
    lock = log_file.with_name(log_file.name + ".lock.d")
    for attempt in range(_APPEND_LOCK_ATTEMPTS):
        try:
            lock.mkdir()
            break
        except FileExistsError as exc:
            if attempt == _APPEND_LOCK_ATTEMPTS - 1:
                raise OSError(f"could not acquire lock: {lock}") from exc
            time.sleep(0.05)
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        header = f"### {category}"
        if header in text.splitlines():
            lines = text.splitlines()
            out: list[str] = []
            inserted = False
            in_target = False
            for line in lines:
                if line == header:
                    in_target = True
                    out.append(line)
                    continue
                if in_target and line.startswith("### "):
                    if not inserted:
                        out.extend(["", entry.rstrip("\n")])
                        inserted = True
                    in_target = False
                out.append(line)
            if in_target and not inserted:
                out.extend(["", entry.rstrip("\n")])
            new_text = "\n".join(out) + "\n"
        else:
            prefix = "\n" if text else ""
            new_text = text.rstrip("\n") + prefix + header + "\n\n" + entry.rstrip("\n") + "\n"
        _atomic_write(path=log_file, content=new_text)
    finally:
        with suppress(OSError):
            lock.rmdir()


def append_execution_issue(*, log_file: Path, category: str, entry: str) -> None:
    _append_execution_issue(log_file=log_file, category=category, entry=entry)


_EXECUTION_ISSUE_CATEGORIES = {
    "Pre-existing Code Issues",
    "Tool Failures",
    "Permission Prompts",
    "External Reviewer Issues",
    "CI Issues",
    "Warnings",
    "Q/A",
}

# Round artifact filtering constants (used by run_log_write_round_main in run_logs.py)
_ROUND_SIDECAR_FILES = frozenset({
    "review-tally.env",
    "collect-agent-results.log",
    "review-summary.json",
    "coder.env",
    "coder-codex.wrapper.log",
    "coder-cursor.wrapper.log",
})

_ROUND_ARTIFACT_ALLOW = (
    "prune-decision.env",
    "prune-nit.env",
    "pre-vote-oos-gate.env",
    "collector-results.env",
    "review-core-threshold.env",
    "findings-classification.tsv",
    "scout-archetype-yield.tsv",
    "rejected-findings.md",
    "oos-dropped-before-vote.md",
    "oos-accepted-review.md",
    "review-round-summary.md",
    "voting-tally.md",
    "aggregator-validate.stderr",
    "aggregator-dispatch.stderr",
    "review-dirty-tree-summary.env",
    "panel-manifest.ndjson",
    "panel-prompt-sizes.tsv",
    "code-voter-slots.ndjson",
    "coder-prompt.md",
    "coder-tool.txt",
    "coder-cursor.log",
    "round-meta.json",
)

_ROUND_ARTIFACT_ALLOW_GLOBS = (
    "cursor-ci-stall-*.json",
    "dirty-checkpoint-*.env",
    "*.dropped-slots",
    "dropped-*-*.txt",
    "voter*-diag.txt",
    "voting-tally-degraded-attempt-*.md",
    "*-parse-rate-diag.txt",
    "skipped-findings*.md",
    "scout-round*-status.env",
    "scout-round*-manifest.json",
)

_ROUND_ARTIFACT_DENY_GLOBS = (
    "cursor-specialist-*-output.txt",
    "cursor-specialist-*-output.txt.meta",
    "cursor-specialist-*-output.txt.json",
    "cursor-specialist-*-output.txt.cap-hit",
    "codex-specialist-*-output.txt",
    "codex-specialist-*-output.txt.meta",
    "codex-specialist-*-output.txt.json",
    "codex-specialist-*-output.txt.cap-hit",
    "cursor-specialist-*-output-phase*.txt",
    "cursor-specialist-*-output-phase*.txt.*",
    "cursor-specialist-*-output-retry.txt",
    "cursor-specialist-*-output-retry.txt.*",
    "codex-specialist-*-output-phase*.txt",
    "codex-specialist-*-output-phase*.txt.*",
    "codex-specialist-*-output-retry.txt",
    "codex-specialist-*-output-retry.txt.*",
    "*.dirty-tree",
    "*.untracked-baseline",
    "*.done",
    "*.diag",
    "*.sidecar",
    "*.events.jsonl",
    "*.sidecar.history",
    "*.events.history",
    "*.failure-diag",
    "*-output.txt.prompt",
    "*-output-*.txt.prompt",
    "coder-output.log",
    "coder-codex.log",
    "*-vote-prompt.txt",
    "dyn-*-codex-output-retry*.txt",
    "dyn-*-codex-output-retry*.txt.meta",
    "dyn-*-codex-output-retry*.txt.json",
    "dyn-*-codex-output-retry*.txt.cap-hit",
    "skipped-findings.security.md",
    "submodule-paths.txt",
    "submodule-scrub.log",
    "submodule-revert.log",
    "coder-commit.log",
    "dyn-*-prompt.md",
    "scout-round*-manifest.json.raw",
    "findings.md",
    "accepted-findings.md",
    "rejected-findings-full.md",
    "oos.md",
    "reviewer-dyn-*.md",
)

_ROUND_ARTIFACT_DEBUG_GLOBS = (
    "dyn-*-codex-output.txt",
    "dyn-*-codex-output-phase*.txt",
    "dyn-*-codex-output.txt.meta",
    "dyn-*-codex-output-phase*.txt.meta",
    "dyn-*-codex-output.txt.json",
    "dyn-*-codex-output-phase*.txt.json",
    "dyn-*-codex-output.txt.cap-hit",
    "dyn-*-codex-output-phase*.txt.cap-hit",
    "*-vote-output*.txt",
    "*-vote-output*.txt.*",
    "*-ns-retry*.txt",
    "*-ns-retry*.txt.*",
    "*-output-first-pass.txt",
    "*-output.txt",
    "*-output-*.txt",
    "*-output.txt.meta",
    "*-output-*.txt.meta",
    "*-output.txt.json",
    "*-output-*.txt.json",
    "*-output.txt.cap-hit",
    "*-output-*.txt.cap-hit",
)


def _round_name_matches(*, name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def _is_round_sidecar_file(name: str) -> bool:
    return name in _ROUND_SIDECAR_FILES


def _round_artifact_included(name: str) -> bool:
    if _round_name_matches(name=name, patterns=_ROUND_ARTIFACT_DENY_GLOBS):
        return False
    if name in _ROUND_ARTIFACT_ALLOW or _round_name_matches(name=name, patterns=_ROUND_ARTIFACT_ALLOW_GLOBS):
        return True
    return os.environ.get("LARCH_FLUSH_DEBUG") == "1" and _round_name_matches(
        name=name,
        patterns=_ROUND_ARTIFACT_DEBUG_GLOBS,
    )


def _stage_round_artifact(*, src: Path, name: str) -> str:
    text = src.read_text(encoding="utf-8", errors="replace")
    if "-vote-output" in name:
        raw = text.encode("utf-8")
        if len(raw) > _VOTE_OUTPUT_TRUNCATE_BYTES:
            text = raw[:_VOTE_OUTPUT_TRUNCATE_BYTES].decode(
                "utf-8",
                errors="ignore",
            ) + f"\n[TRUNCATED: original {len(raw)} bytes]\n"
    if name.startswith("dropped-") or name.endswith(".dropped-slots"):
        scrubbed, findings = redact.scrub_log_secrets(text)
        if findings:
            _, residual = redact.scrub_log_secrets(scrubbed)
            if residual:
                raise ShipError(f"secret survived scrubbing in round artifact {name}")
        text = scrubbed
    return redact.redact(text)
