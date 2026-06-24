# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""larch-log manifest lifecycle and split flush entrypoints."""

from __future__ import annotations

import fnmatch
import hashlib
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path
from collections.abc import Mapping
from typing import Any, cast

import config
import design_diagram_log
import final_report
import git
import larch_io
import logging_util
import pr_body
import proc
import redact
import timing
import tokens
import stall_recovery
from errors import ShipError
from run_log_tolerance import terminal_bail_skip_signal
from proc import CommandResult, Runner
from run_context import RunContext

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REQUIRED_FILES_TSV = _REPO_ROOT / "docs" / "run-logs-required-files.tsv"
_MANIFEST_SCHEMA_VERSION = 2
_VOTE_OUTPUT_TRUNCATE_BYTES = 2048
_TERMINAL_OUTCOME_SUFFIX = re.compile(
    r"(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?)$",
)

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
}


def _batch_extension(slug: str) -> str:
    return _LARCH_LOG_BATCHES[slug].extension


def _batch_mode(slug: str) -> str:
    return _LARCH_LOG_BATCHES[slug].mode


def _batch_sanitizer(slug: str) -> str:
    return _LARCH_LOG_BATCHES[slug].sanitizer


def _batch_list() -> tuple[str, ...]:
    return tuple(sorted(_LARCH_LOG_BATCHES))


_V2_CORE_KEYS = frozenset({"status", "schema_version", "run_id", "steps_ran", "started_at", "updated_at"})
_V2_RESERVED_KEYS = frozenset({
    "skill",
    "operator_cwd",
    "operator_repo_root",
    "parent_skill",
    "issue_number",
    "larch_version",
    "model_roster",
    "effort",
    "attempt",
    "superseded_by",
    "stalled_at_step",
    "flags",
    "pr_number",
})
_V2_EXTRA_PROMOTABLE_RESERVED_KEYS = frozenset({"stalled_at_step", "pr_number", "issue_number"})
_V2_PARSE_EXCLUDED_KEYS = _V2_CORE_KEYS | _V2_RESERVED_KEYS
_V2_EMIT_EXTRA_EXCLUDED_KEYS = _V2_CORE_KEYS | (_V2_RESERVED_KEYS - _V2_EXTRA_PROMOTABLE_RESERVED_KEYS)


def _empty_manifest_reserved() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class Manifest:
    status: str
    version: str
    run_id: str
    steps_ran: dict[str, Any]
    created_at: str = ""
    updated_at: str = ""
    extra: dict[str, Any] | None = None
    # Reserved v2 metadata is kept separate from extension keys. Immutable fields
    # are guarded by _MANIFEST_IMMUTABLE; mutable fields such as stalled_at_step,
    # issue_number, and pr_number may be updated by manifest writers.
    reserved: dict[str, Any] = field(default_factory=_empty_manifest_reserved)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Manifest:
        steps_raw = data.get("steps_ran", {})
        steps = dict(cast("dict[str, Any]", steps_raw)) if isinstance(steps_raw, dict) else {}
        if data.get("schema_version") == _MANIFEST_SCHEMA_VERSION:
            reserved: dict[str, Any] = {key: data[key] for key in _V2_RESERVED_KEYS if key in data}
            extra = {key: value for key, value in data.items() if key not in _V2_PARSE_EXCLUDED_KEYS}
            return cls(
                status=str(data.get("status", config.MANIFEST_STATUS_PARTIAL)),
                version="2",
                run_id=str(data.get("run_id", "")),
                steps_ran=steps,
                created_at=str(data.get("started_at", "")),
                updated_at=str(data.get("updated_at", "")),
                extra=extra or None,
                reserved=dict(reserved),
            )
        extra = {
            key: value
            for key, value in data.items()
            if key not in {"status", "version", "run_id", "steps_ran", "created_at", "updated_at"}
        }
        return cls(
            status=str(data.get("status", config.MANIFEST_STATUS_PARTIAL)),
            version=str(data.get("version", "1")),
            run_id=str(data.get("run_id", "")),
            steps_ran=steps,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            extra=extra or None,
        )

    @classmethod
    def synthesize_v2(
        cls,
        *,
        skill: str,
        run_id: str,
        steps_ran: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Manifest:
        ts = _now_utc()
        data: dict[str, Any] = {
            "schema_version": 2,
            "skill": skill,
            "run_id": run_id,
            "operator_cwd": "<OPERATOR_CWD>",
            "operator_repo_root": "<REPO_ROOT>",
            "parent_skill": None,
            "issue_number": None,
            "larch_version": _plugin_version(),
            "model_roster": {
                "main": _resolve_main_model(),
            },
            "effort": os.environ.get("CLAUDE_CODE_EFFORT_LEVEL") or os.environ.get("CLAUDE_EFFORT", "unknown"),
            "started_at": ts,
            "updated_at": ts,
            "attempt": 1,
            "superseded_by": None,
            "stalled_at_step": None,
            "steps_ran": steps_ran or {},
            "flags": {},
        }
        if extra:
            data.update(extra)
        return cls.from_json(data)

    def to_json(self, existing: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if str(self.version) == "2":
            data = dict(existing or {})
            data.pop("version", None)
            data.pop("created_at", None)
            data["schema_version"] = 2
            data["status"] = self.status
            data["run_id"] = self.run_id
            data["steps_ran"] = dict(self.steps_ran)
            data["started_at"] = self.created_at
            data["updated_at"] = self.updated_at
            data.update(dict(self.reserved))
            if self.extra:
                for key, value in self.extra.items():
                    if key in _V2_EMIT_EXTRA_EXCLUDED_KEYS:
                        continue
                    data[key] = value
            return data
        data = dict(self.extra or {})
        data.update({
            "status": self.status,
            "version": self.version,
            "run_id": self.run_id,
            "steps_ran": dict(self.steps_ran),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        })
        return data


@dataclass(frozen=True)
class RefreshSkip:
    skipped: bool
    reason: str
    error: str = ""


@dataclass(frozen=True)
class ManifestRecovery:
    manifest: Manifest
    recovery_ok: bool


RECOVERY_REASON_MANIFEST_LOST = "manifest_lost_mid_run"
REFRESH_SKIP_RECOVERY_FAILED = "manifest-recovery-failed"


@dataclass(frozen=True)
class ResumeCounters:
    iteration: int
    rebase_count: int
    fix_attempts: int
    transient_retries: int


@dataclass(frozen=True)
class DurableFlags:
    repo_unavailable: bool
    forked_target: bool
    forked: bool
    merge: bool
    draft: bool


def _atomic_write(path: Path, content: str) -> None:
    larch_io.atomic_write(path, content, prefix=".manifest-", nofollow=True)


def _resolve_log_root(log_root: str | None = None) -> Path:
    raw = log_root or os.environ.get("LARCH_LOG_ROOT", "")
    if not raw:
        raise ValueError("--log-root is required (or export LARCH_LOG_ROOT for test isolation)")
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError(f"--log-root must be an absolute path: {raw}")
    return path


def _resolve_consumer_repo_root(cwd: str | None) -> Path:
    result = subprocess.run(
        ["git", "-C", cwd or str(Path.cwd()), "rev-parse", "--show-toplevel"],  # noqa: S607
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ShipError("cwd is outside a git worktree")
    return Path(result.stdout.strip())


def _run_dir(log_root: Path, skill: str, run_id: str) -> Path:
    return log_root / skill / run_id


def _repo_run_dir(repo_root: Path, skill: str, run_id: str) -> Path:
    return repo_root / "larch-logs" / skill / run_id


def _batch_path(log_root: Path, skill: str, run_id: str, batch: str) -> Path:
    return _run_dir(log_root, skill, run_id) / f"{batch}{_batch_extension(batch)}"


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


def _larch_log_fail(code: int, message: str) -> int:
    _emit_larch_log_envelope(
        path=None,
        written=False,
        unchanged=False,
        error=message,
    )
    return code


def _validate_slug(label: str, value: str) -> None:
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


def _batch_validate_payload(batch: str, path: Path) -> None:
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
    log_root: Path,
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
        _batch_validate_payload(batch, tmp)
        path = _batch_path(log_root, skill, run_id, batch)
        if path.is_file() and path.read_bytes() == tmp.read_bytes():
            return path, False, True
        _atomic_write(path=path, content=tmp.read_text(encoding="utf-8"))
        return path, True, False
    finally:
        tmp.unlink(missing_ok=True)


def _append_batch(
    log_root: Path,
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
        _batch_validate_payload(batch, tmp)
        path = _batch_path(log_root, skill, run_id, batch)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = tmp.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)
        return path, True, False
    finally:
        tmp.unlink(missing_ok=True)


_MANIFEST_IMMUTABLE = frozenset(
    {"schema_version", "skill", "run_id", "started_at", "operator_cwd", "operator_repo_root"},
)


def _manifest_cli_path(log_root: Path, skill: str, run_id: str) -> Path:
    return _run_dir(log_root, skill, run_id) / "manifest.json"


def _read_manifest_v2(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("manifest must be a JSON object")
    return cast("dict[str, Any]", data)


def _write_manifest_v2(path: Path, data: dict[str, Any]) -> None:
    _atomic_write(path=path, content=json.dumps(data, indent=2, sort_keys=True) + "\n")


def _parse_manifest_scalar(raw: str) -> Any:
    if raw == "null":
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if re.fullmatch(r"-?[0-9]+", raw):
        return int(raw)
    return raw


def _update_manifest_v2(path: Path, updates: dict[str, Any]) -> dict[str, Any]:
    data = _read_manifest_v2(path)
    manifest = Manifest.from_json(data)
    steps: dict[str, Any] = dict(manifest.steps_ran)
    reserved: dict[str, Any] = dict(manifest.reserved)
    extra: dict[str, Any] = dict(manifest.extra or {})
    status = manifest.status
    for key, value in updates.items():
        if key in _MANIFEST_IMMUTABLE:
            raise ValueError(f"immutable-field:{key}")
        if key.startswith("steps_ran."):
            steps[key.split(".", 1)[1]] = value
        elif key == "steps_ran" and isinstance(value, dict):
            steps.update(cast("dict[str, Any]", value))
        elif key == "status":
            status = str(value)
        elif key in _V2_RESERVED_KEYS:
            reserved[key] = value
        else:
            extra[key] = value
    updated = replace(
        manifest,
        status=status,
        steps_ran=steps,
        updated_at=_now_utc(),
        extra=extra or None,
        reserved=reserved,
    )
    out = updated.to_json(existing=data)
    _write_manifest_v2(path, out)
    return out


def _plugin_version() -> str:
    plugin_json = _REPO_ROOT / ".claude-plugin" / "plugin.json"
    if plugin_json.is_file():
        try:
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                version = str(cast("dict[str, Any]", data).get("version", "") or "").strip()
                if version and version != "null":
                    return version
        except (OSError, json.JSONDecodeError):
            pass
    return "unknown"


def _resolve_main_model() -> str:
    """Main-agent model for manifest metadata.

    Prefers an explicit env override, else reads the active session transcript
    (newest at run-log init, before subagents spawn, so it reflects the
    orchestrator model rather than a spawned reviewer), else "unknown".
    """
    explicit = os.environ.get("CLAUDE_CODE_MODEL") or os.environ.get("CLAUDE_MODEL")
    if explicit:
        return explicit
    try:
        model = tokens.read_main_model()
    except Exception:
        model = ""
    return model or "unknown"


def _now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def read_state_kv(state_file: str | None, key: str) -> str:
    """Read a single KEY=value from an implement state file."""
    return _read_state_kv(state_file, key)


def _parse_nonnegative_int(raw: str) -> int:
    text = raw.strip()
    if not re.fullmatch(r"[0-9]+", text):
        return 0
    return int(text)


def _parse_positive_int(raw: str) -> int | None:
    text = raw.strip()
    if not re.fullmatch(r"[0-9]+", text):
        return None
    value = int(text)
    return value if value > 0 else None


def read_resume_counters(state_file: str | None) -> ResumeCounters:
    """Read persisted CI-loop counters without raising on corrupt state."""
    if not state_file:
        return ResumeCounters(0, 0, 0, 0)
    return ResumeCounters(
        iteration=_parse_nonnegative_int(_read_state_kv(state_file, "ITERATION")),
        rebase_count=_parse_nonnegative_int(_read_state_kv(state_file, "REBASE_COUNT")),
        fix_attempts=_parse_nonnegative_int(_read_state_kv(state_file, "FIX_ATTEMPTS")),
        transient_retries=_parse_nonnegative_int(
            _read_state_kv(state_file, "TRANSIENT_RETRIES"),
        ),
    )


def _state_bool_or_default(raw: str, *, default: bool) -> bool:
    text = raw.strip()
    if text == "true":
        return True
    if text == "false":
        return False
    return default


def read_durable_flags(state_file: str | None, ctx: RunContext) -> DurableFlags:
    """Read durable mode flags state-first, falling back to the run context."""
    if not state_file:
        return DurableFlags(
            repo_unavailable=ctx.repo_unavailable,
            forked_target=ctx.forked_target,
            forked=ctx.forked,
            merge=ctx.merge,
            draft=ctx.draft,
        )
    raw_forked_target = _read_state_kv(state_file, "FORKED_TARGET")
    forked_target = _state_bool_or_default(raw_forked_target, default=ctx.forked_target)
    forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked
    return DurableFlags(
        repo_unavailable=_state_bool_or_default(
            _read_state_kv(state_file, "REPO_UNAVAILABLE"),
            default=ctx.repo_unavailable,
        ),
        forked_target=forked_target,
        forked=forked,
        merge=_state_bool_or_default(_read_state_kv(state_file, "MERGE"), default=ctx.merge),
        draft=_state_bool_or_default(_read_state_kv(state_file, "DRAFT"), default=ctx.draft),
    )


def parse_pr_number(state_file: str | None, ctx_pr_number: int | str | None) -> int | None:
    """Parse the persisted PR number; ignore stale context when state exists."""
    if not state_file:
        return None
    raw = _read_state_kv(state_file, "PR_NUMBER")
    if raw.strip():
        return _parse_positive_int(raw)
    _ = ctx_pr_number
    return None


def manifest_status(ctx: RunContext) -> str:
    """Return the run-log manifest status without initializing or recovering it."""
    run_id = effective_run_id(ctx)
    if not run_id:
        return ""
    path = Path(ctx.tmpdir) / "larch-logs" / "implement" / run_id / "manifest.json"
    if not path.is_file():
        return ""
    try:
        return Manifest.from_json(_read_manifest_v2(path)).status
    except (OSError, json.JSONDecodeError, TypeError):
        return ""


def _read_kv_file(path: Path, key: str) -> str:
    return larch_io.read_kv(path, key, first_match=True, errors="strict", on_error_default=True)


def _read_state_kv(state_file: str | None, key: str) -> str:
    if not state_file:
        return ""
    return _read_kv_file(Path(state_file), key)


def _read_session_env_key(ctx: RunContext, key: str) -> str:
    return _read_kv_file(Path(ctx.tmpdir) / "session-env.sh", key)


def _report_subprocess_env(ctx: RunContext) -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    env["IMPLEMENT_TMPDIR"] = ctx.tmpdir
    env["LARCH_TIMING_SKILL"] = "implement"
    _ = env.pop("DESIGN_TMPDIR", None)
    for export_key, file_key in (
        ("LARCH_TOKEN_SESSION_ID", "LARCH_TOKEN_SESSION_ID"),
        ("LARCH_CLAUDE_SOURCE_FILE", "LARCH_CLAUDE_SOURCE_FILE"),
        ("LARCH_TIMING_LEDGER", "LARCH_TIMING_LEDGER"),
    ):
        value = _read_session_env_key(ctx, file_key)
        if value:
            env[export_key] = value
    return env


def _write_report_json(path: Path, data: dict[str, object]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    _ = tmp.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    _ = tmp.replace(path)


def _render_ledger_reports(runner: Runner, ctx: RunContext, log_root: Path) -> None:
    """Re-render token/timing JSON from ledgers (python3 python/cli.py run-log refresh parity)."""
    _ = runner
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    tmpdir = Path(ctx.tmpdir)
    token_path = tmpdir / "token-report-refresh.json"
    timing_path = tmpdir / "timing-report-refresh.json"
    env = _report_subprocess_env(ctx)
    with suppress(Exception):
        rendered = tokens.token_report(mode="full", fmt="json", env=env)
        if isinstance(rendered, dict):
            _write_report_json(token_path, rendered)
    if token_path.is_file():
        with suppress(Exception):
            _write_batch(log_root, "implement", run_id, "token-report", token_path)
    with suppress(Exception):
        ledger = timing.resolve_timing_ledger_path(env=env)
        if ledger is not None:
            data = timing.TimingReport(ledger).render_json(env=env)
            _write_report_json(timing_path, data)
    if timing_path.is_file():
        with suppress(Exception):
            _write_batch(log_root, "implement", run_id, "timing-report", timing_path)


def effective_run_id(ctx: RunContext) -> str:
    """Prefer validated state-file RUN_ID over ctx.run_id for log paths."""
    state_run_id = _read_state_kv(ctx.state_file, "RUN_ID")
    if state_run_id and validate_run_id_slug(state_run_id):
        return state_run_id
    if validate_run_id_slug(ctx.run_id):
        return ctx.run_id
    return ""


def _manifest_path(ctx: RunContext) -> Path:
    run_id = effective_run_id(ctx)
    return Path(ctx.tmpdir) / "larch-logs" / "implement" / run_id / "manifest.json"


def _run_log_dir(ctx: RunContext) -> Path:
    return Path(ctx.tmpdir) / "larch-logs" / "implement" / effective_run_id(ctx)


def _issue_number_from_context(ctx: RunContext) -> int | None:
    raw = (
        _read_state_kv(ctx.state_file, "ISSUE_NUMBER")
        or _read_state_kv(ctx.state_file, "ISSUE")
        or str(ctx.issue_number or ctx.issue or "")
    )
    return int(raw) if raw.isdigit() else None


def init_run(
    ctx: RunContext,
    *,
    run_id: str | None = None,
    recovery_reason: str = "",
) -> Manifest:
    rid = run_id or effective_run_id(ctx)
    extra: dict[str, Any] = {"status": config.MANIFEST_STATUS_PARTIAL}
    if recovery_reason:
        extra["recovery_reason"] = recovery_reason
        issue_number = _issue_number_from_context(ctx)
        if issue_number is not None:
            extra["issue_number"] = issue_number
    manifest = Manifest.synthesize_v2(skill="implement", run_id=rid, extra=extra)
    _write_manifest_v2(_manifest_path(ctx), manifest.to_json(existing=None))
    return manifest


def update_manifest(ctx: RunContext, **changes: object) -> Manifest:
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        msg = "manifest recovery failed"
        raise ShipError(msg)
    current = recovery.manifest
    steps = dict(current.steps_ran)
    status = current.status
    version = current.version
    run_id = current.run_id
    created_at = current.created_at
    updated_at = current.updated_at
    extra = dict(current.extra or {})
    reserved = dict(current.reserved)
    for key, value in changes.items():
        if key == "steps_ran" and isinstance(value, dict):
            steps.update(cast("dict[str, Any]", value))
        elif key == "status":
            status = str(value)
        elif key == "version":
            version = str(value)
        elif key == "run_id":
            run_id = str(value)
        elif key == "created_at":
            created_at = str(value)
        elif key == "updated_at":
            updated_at = str(value)
        elif key in _V2_RESERVED_KEYS:
            reserved[key] = value
        else:
            extra[key] = value
    updated = Manifest(
        status=status,
        version=version,
        run_id=run_id,
        steps_ran=steps,
        created_at=created_at,
        updated_at=updated_at,
        extra=extra or None,
        reserved=reserved,
    )
    _write_manifest(ctx, updated)
    return updated


def _recover_manifest_from_run_dir(ctx: RunContext, run_id: str, run_dir: Path) -> Manifest | None:
    if not run_dir.is_dir():
        return None
    steps: dict[str, Any] = {"recovered": True}
    if (run_dir / "execution-issues.ndjson").is_file():
        steps["execution_issues"] = True
    if (run_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson").is_file():
        steps["token_report"] = True
    extra: dict[str, Any] = {"recovery_reason": RECOVERY_REASON_MANIFEST_LOST, "status": config.MANIFEST_STATUS_PARTIAL}
    issue_number = _issue_number_from_context(ctx)
    if issue_number is not None:
        extra["issue_number"] = issue_number
    return Manifest.synthesize_v2(
        skill="implement",
        run_id=run_id,
        steps_ran=steps,
        extra=extra,
    )


def load_or_recover_manifest_checked(ctx: RunContext) -> ManifestRecovery:
    rid = effective_run_id(ctx)
    if rid:
        primary = Path(ctx.tmpdir) / "larch-logs" / "implement" / rid / "manifest.json"
        run_dir = primary.parent
        if primary.is_file():
            try:
                data = _read_manifest_v2(primary)
                return ManifestRecovery(Manifest.from_json(data), recovery_ok=True)
            except json.JSONDecodeError:
                recovered = _recover_manifest_from_run_dir(ctx, rid, run_dir)
                if recovered is not None:
                    try:
                        _write_manifest_v2(primary, recovered.to_json(existing=None))
                    except OSError:
                        return ManifestRecovery(recovered, recovery_ok=False)
                    return ManifestRecovery(recovered, recovery_ok=True)
        elif run_dir.is_dir():
            recovered = _recover_manifest_from_run_dir(ctx, rid, run_dir)
            if recovered is not None:
                try:
                    _write_manifest_v2(primary, recovered.to_json(existing=None))
                except OSError:
                    return ManifestRecovery(recovered, recovery_ok=False)
                return ManifestRecovery(recovered, recovery_ok=True)
        try:
            manifest = init_run(ctx, run_id=rid, recovery_reason=RECOVERY_REASON_MANIFEST_LOST)
        except OSError:
            manifest = Manifest(
                status=config.MANIFEST_STATUS_PARTIAL,
                version="1",
                run_id=rid,
                steps_ran={},
                extra={"recovery_reason": RECOVERY_REASON_MANIFEST_LOST},
            )
            return ManifestRecovery(manifest, recovery_ok=False)
        return ManifestRecovery(manifest, recovery_ok=True)
    try:
        return ManifestRecovery(init_run(ctx), recovery_ok=True)
    except OSError:
        return ManifestRecovery(
            Manifest(
                status=config.MANIFEST_STATUS_PARTIAL,
                version="1",
                run_id="",
                steps_ran={},
            ),
            recovery_ok=False,
        )


def load_or_recover_manifest(ctx: RunContext) -> Manifest:
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        msg = "manifest recovery failed"
        raise ShipError(msg)
    return recovery.manifest


def _write_manifest(ctx: RunContext, manifest: Manifest) -> None:
    path = _manifest_path(ctx)
    if path.is_file():
        try:
            data = _read_manifest_v2(path)
            if data.get("schema_version") == _MANIFEST_SCHEMA_VERSION:
                updated = replace(manifest, updated_at=_now_utc())
                _write_manifest_v2(path, updated.to_json(existing=data))
                return
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    updated = replace(manifest, updated_at=manifest.updated_at or _now_utc())
    _atomic_write(
        path=path,
        content=json.dumps(updated.to_json(existing=None), indent=2, sort_keys=True) + "\n"
    )


def _pre_push_probe(ctx: RunContext) -> RefreshSkip:
    tmpdir = Path(ctx.tmpdir)
    finalize_state = tmpdir / "finalize-state.sh"
    if ctx.state_file:
        merge_result = _read_state_kv(ctx.state_file, "MERGE_RESULT")
        run_id = _read_state_kv(ctx.state_file, "RUN_ID")
        no_logs_commit = _read_state_kv(ctx.state_file, "NO_LOGS_COMMIT") == "true"
    else:
        merge_result = ctx.merge_result
        run_id = ctx.run_id
        no_logs_commit = ctx.no_logs_commit
    if not merge_result:
        merge_result = _read_kv_file(finalize_state, "MERGE_RESULT")
    if not run_id:
        run_id = _read_kv_file(finalize_state, "RUN_ID")
    if (tmpdir / "post-merge-sentinel").is_file() and not merge_result:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_POST_MERGE)
    if merge_result in config.POST_MERGE_MERGE_RESULTS:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_POST_MERGE)
    if not run_id:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_RUN_ID)
    if not validate_run_id_slug(run_id):
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_INVALID_RUN_ID)
    if no_logs_commit:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_LOGS_COMMIT)
    return RefreshSkip(skipped=False, reason="")


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


def _should_flush_execution_issues(
    ctx: RunContext,
    issue_log: Path,
    batch_path: Path,
) -> bool:
    if not issue_log.is_file() or issue_log.stat().st_size == 0:
        return False
    tmp = Path(ctx.tmpdir)
    if (tmp / ".execution-issues-step7a-reached").is_file():
        return True
    if (tmp / ".execution-issues-flushed.sha").is_file():
        return True
    return batch_path.is_file()


def _render_execution_issues_batch(
    ctx: RunContext,
    batch_dir: Path,
    *,
    step_label: str,
    source_label: str,
) -> None:
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    batch_path = batch_dir / "execution-issues.ndjson"
    if not _should_flush_execution_issues(ctx, issue_log, batch_path):
        return
    file_sha = hashlib.sha256(issue_log.read_bytes()).hexdigest()
    existing = batch_path.read_text(encoding="utf-8") if batch_path.is_file() else ""
    records: list[str] = []
    current_cat = "Tool Failures"
    body_lines: list[str] = []
    for line in issue_log.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            if body_lines:
                record = _execution_issue_record(
                    body_lines,
                    current_cat,
                    step_label,
                    source_label,
                    file_sha,
                    existing,
                )
                if record is not None:
                    records.append(record)
                body_lines = []
            current_cat = line.removeprefix("### ")
            continue
        body_lines.append(line)
    if body_lines:
        record = _execution_issue_record(
            body_lines,
            current_cat,
            step_label,
            source_label,
            file_sha,
            existing,
        )
        if record is not None:
            records.append(record)
    if not records:
        return
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    with batch_path.open("a", encoding="utf-8") as handle:
        for record in records:
            _ = handle.write(record + "\n")
    sentinel = Path(ctx.tmpdir) / ".execution-issues-flushed.sha"
    _ = sentinel.write_text(file_sha, encoding="utf-8")


def render_execution_issues_batch(
    ctx: RunContext,
    batch_dir: Path,
    *,
    step_label: str,
    source_label: str,
) -> None:
    _render_execution_issues_batch(
        ctx,
        batch_dir,
        step_label=step_label,
        source_label=source_label,
    )


def _execution_issue_record(
    body_lines: list[str],
    category: str,
    step_label: str,
    source_label: str,
    file_sha: str,
    existing_batch: str,
) -> str | None:
    body = "\n".join(body_lines)
    redacted_body = _redact_batch_payload(body)
    norm_sha = hashlib.sha256(
        _normalize_body_for_hash(redacted_body).encode("utf-8"),
    ).hexdigest()
    if f'"source_sha256":"{norm_sha}"' in existing_batch:
        return None
    payload = {
        "phase": "implement",
        "step": step_label,
        "category": category,
        "source": source_label,
        "source_sha256": norm_sha or file_sha,
        "body": redacted_body,
    }
    return json.dumps(payload, sort_keys=True)


def _reconcile_terminal_manifest_from_ctx(ctx: RunContext) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    run_dir = _run_log_dir(ctx)
    if not (run_dir / "final-summary.md").is_file():
        return
    outcome_values = stall_recovery.normalized_outcome_values(
        argparse.Namespace(implement_tmpdir=ctx.tmpdir, in_memory_stall_tracking=""),
    )
    outcome = outcome_values.get("IMPLEMENT_NORMALIZED_OUTCOME", "bailed")
    rc, err = final_report._reconcile_manifest_for_terminal_report(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        Path(ctx.tmpdir),
        run_id=run_id,
        outcome=outcome,
    )
    if rc != 0:
        msg = err or "manifest reconcile failed"
        raise ShipError(msg)


def _write_final_report(
    runner: Runner,
    ctx: RunContext,
    *,
    skip_tracking_upsert: bool = False,
) -> None:
    _ = runner
    rc, _comment_url, error = pr_body.write_final_report(
        Path(ctx.tmpdir),
        skip_tracking_upsert=skip_tracking_upsert,
    )
    if rc != 0:
        msg = error or "final report write failed"
        raise ShipError(msg)


def write_final_report_comment(runner: Runner, ctx: RunContext) -> None:
    _ = runner
    rc, _comment_url, error = pr_body.write_final_report(Path(ctx.tmpdir), comment_only=True)
    if rc != 0:
        msg = error or "final report comment write failed"
        raise ShipError(msg)


def _stage_vendor_failure_diagnostics(ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    script = _REPO_ROOT / "scripts" / "flush-vendor-failure-diagnostics.sh"
    if not script.is_file():
        return
    with suppress(Exception):
        _ = proc.run(
            [
                "bash",
                str(script),
                "--tmpdir",
                ctx.tmpdir,
                "--run-id",
                run_id,
                "--log-root",
                str(log_root),
            ],
            cwd=str(_REPO_ROOT),
        )


def _stage_pre_commit(
    runner: Runner,
    ctx: RunContext,
    log_root: Path,
    *,
    mode: str = "refresh",
    strict_final_report: bool = False,
) -> None:
    run_dir = _run_log_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    if mode == "refresh":
        _render_execution_issues_batch(
            ctx,
            run_dir,
            step_label="pre-push",
            source_label="execution-issues.md pre-push refresh",
        )
        if strict_final_report:
            _write_final_report(runner, ctx, skip_tracking_upsert=True)
            final_summary = run_dir / "final-summary.md"
            if not final_summary.is_file():
                msg = "final-summary.md missing after final report write"
                raise ShipError(msg)
        else:
            with suppress(ShipError):
                _write_final_report(runner, ctx)
        _render_ledger_reports(runner, ctx, log_root)
        _render_token_timing_batches(ctx, log_root)
    else:
        _render_execution_issues_batch(
            ctx,
            run_dir,
            step_label="commit-tail",
            source_label="execution-issues.md commit-tail",
        )
    _stage_vendor_failure_diagnostics(ctx, log_root)
    if mode == "refresh":
        _ = capture_session_transcript(ctx, runner, defer_commit=True)
        _render_execution_issues_batch(
            ctx,
            run_dir,
            step_label="pre-push-post-transcript",
            source_label="execution-issues.md post-transcript refresh",
        )
        if (run_dir / "final-summary.md").is_file():
            _reconcile_terminal_manifest_from_ctx(ctx)


def flush_logs_pre(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
    strict_final_report: bool = False,
) -> RefreshSkip:
    """Pre-push refresh: may git-commit log batches (caller owns push)."""
    skip = _pre_push_probe(ctx)
    if skip.skipped:
        return skip
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    log_root = Path(ctx.tmpdir) / "larch-logs"
    try:
        _stage_pre_commit(
            runner,
            ctx,
            log_root,
            mode="refresh",
            strict_final_report=strict_final_report,
        )
    except ShipError as exc:
        if strict_final_report:
            return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED, error=str(exc).strip())
        raise
    if strict_final_report and not (_run_log_dir(ctx) / "final-summary.md").is_file():
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    step9a1 = _step9a1_heuristic(ctx)
    steps_update = dict(manifest.steps_ran)
    if step9a1 is not None:
        steps_update["step9a1"] = step9a1
    try:
        _ = update_manifest(ctx, steps_ran=steps_update)
    except (OSError, ShipError):
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    if cwd is None:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_REPO_CWD)
    try:
        commit_result = _commit_run(log_root, "implement", effective_run_id(ctx), cwd=cwd)
    except (OSError, ShipError) as exc:
        return RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_COMMIT_FAILED,
            error=str(exc).strip(),
        )
    if commit_result.returncode != 0:
        err = (commit_result.stderr or commit_result.stdout or "").strip()
        return RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_COMMIT_FAILED,
            error=err,
        )
    if commit_result.argv in {("larch-log-volatile-only",), ("true",)}:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_VOLATILE_ONLY)
    return RefreshSkip(skipped=False, reason="")


def commit_larch_logs(
    runner: Runner,
    ctx: RunContext,
    log_root: Path,
    *,
    cwd: str | None,
) -> CommandResult:
    _ = runner
    return _commit_run(log_root, "implement", effective_run_id(ctx), cwd=cwd)


def flush_logs_post(
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RefreshSkip:
    """Post-merge tmpdir-only flush; never git-commits."""
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    log_root = Path(ctx.tmpdir) / "larch-logs"
    resolved = merge_result or _read_state_kv(ctx.state_file, "MERGE_RESULT") or ctx.merge_result
    finalize = resolved in config.POST_MERGE_MERGE_RESULTS
    pr_number = _read_state_kv(ctx.state_file, "PR_NUMBER") if ctx.state_file else ""
    if not pr_number and ctx.pr_number is not None:
        pr_number = str(ctx.pr_number)
    try:
        if runner is not None:
            _write_final_report(runner, ctx)
            _render_ledger_reports(runner, ctx, log_root)
        _render_token_timing_batches(ctx, log_root)
    except ShipError as exc:
        reason = "redaction-failed" if "redaction" in str(exc).lower() else "post-merge-refresh-failed"
        return RefreshSkip(skipped=True, reason=reason)
    if (_run_log_dir(ctx) / "final-summary.md").is_file():
        try:
            _reconcile_terminal_manifest_from_ctx(ctx)
        except ShipError:
            return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
        recovery = load_or_recover_manifest_checked(ctx)
        if not recovery.recovery_ok:
            return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
        manifest = recovery.manifest
    status = config.MANIFEST_STATUS_DONE if finalize else manifest.status
    extra = dict(manifest.extra or {})
    reserved = dict(manifest.reserved)
    if str(pr_number).isdigit():
        reserved["pr_number"] = int(pr_number)
    updated = Manifest(
        status=status,
        version=manifest.version,
        run_id=manifest.run_id,
        steps_ran=dict(manifest.steps_ran),
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        extra=extra or None,
        reserved=reserved,
    )
    try:
        _write_manifest(ctx, updated)
    except OSError:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    return RefreshSkip(skipped=False, reason="")


def finalize_postmerge_logs(
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RefreshSkip:
    """Central postmerge finalization path: recover, write done/pr, then report."""
    return flush_logs_post(ctx, merge_result=merge_result, runner=runner)


def _token_sidecar_paths(tmpdir: Path) -> tuple[tuple[str, Path], ...]:
    pairs: list[tuple[str, Path]] = []
    for tool in ("codex", "cursor", "claude"):
        path = tmpdir / f"{tool}-tokens.json"
        if path.is_file():
            pairs.append((tool, path))
    return tuple(pairs)


def _timing_sidecar_paths(tmpdir: Path) -> tuple[tuple[str, Path], ...]:
    pairs: list[tuple[str, Path]] = []
    for tool in ("codex", "cursor", "claude"):
        path = tmpdir / f"{tool}-timing.json"
        if path.is_file():
            pairs.append((tool, path))
    return tuple(pairs)


def _render_token_timing_batches(ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    tmpdir = Path(ctx.tmpdir)
    token_path = tmpdir / "token-report-refresh.json"
    timing_path = tmpdir / "timing-report-refresh.json"
    batch_dir = log_root / "implement" / run_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    sidecars: list[tuple[str, Path]] = list(_token_sidecar_paths(tmpdir))
    has_canonical_sidecars = bool(sidecars)
    if token_path.is_file():
        sidecars.append(("refresh", token_path))
    timing_sidecars: list[tuple[str, Path]] = list(_timing_sidecar_paths(tmpdir))
    has_canonical_sidecars = has_canonical_sidecars or bool(timing_sidecars)
    if timing_path.is_file():
        timing_sidecars.append(("refresh", timing_path))
    if not has_canonical_sidecars:
        # No per-tool sidecars; refresh JSONs served as the only input — write
        # them as the canonical report and return.  Do NOT copy the -refresh.json
        # files themselves into batch_dir: they are volatile in-loop snapshots and
        # are byte-identical to token-report.json / timing-report.json in nearly
        # all runs (issue #3708 Phase 1).
        if token_path.is_file():
            _ = tokens.scrape_run(
                sidecar_paths=(("refresh", token_path),),
                timing_sidecar_paths=(("refresh", timing_path),) if timing_path.is_file() else (),
                output_path=batch_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson",
                timing_output_path=batch_dir / f"{config.RUN_LOG_BATCH_TIMING_REPORT}.ndjson",
            )
        return
    _ = tokens.scrape_run(
        sidecar_paths=tuple(sidecars),
        timing_sidecar_paths=tuple(timing_sidecars),
        output_path=batch_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson",
        timing_output_path=batch_dir / f"{config.RUN_LOG_BATCH_TIMING_REPORT}.ndjson",
    )
    # Do NOT copy the -refresh.json files into batch_dir: they are volatile
    # in-loop snapshots that duplicate the canonical NDJSON written above.


def capture_session_transcript(
    ctx: RunContext,
    runner: Runner,
    *,
    defer_commit: bool = False,
) -> Path | None:
    """Copy refresh transcript into run tree with redaction (defer-commit parity)."""
    _ = runner
    run_id = effective_run_id(ctx)
    if not run_id:
        return None
    log_root = Path(ctx.tmpdir) / "larch-logs"
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    source = os.environ.get("LARCH_CLAUDE_SOURCE_FILE", "")
    no_logs = _read_state_kv(ctx.state_file, "NO_LOGS_COMMIT") or ("true" if ctx.no_logs_commit else "false")
    if source:
        _ = capture_transcript_main([
            "--source-file",
            source,
            "--log-root",
            str(log_root),
            "--skill",
            "implement",
            "--run-id",
            run_id,
            "--no-logs-commit",
            no_logs,
            "--execution-issues-log",
            str(issue_log),
            "--warning-step-label",
            "pre-push-refresh",
            "--refresh-mode",
            "true",
            "--defer-commit",
            "true" if defer_commit else "false",
        ])
    # Do NOT copy session-transcript-refresh.txt into the run tree: it is a
    # volatile in-loop snapshot that duplicates the canonical batch in nearly
    # all runs (issue #3708 Phase 1).
    out = Path(ctx.tmpdir) / "session-transcript-refresh.txt"
    return out if out.is_file() else None


def _read_finalize_kv(tmpdir: Path, key: str) -> str:
    return _read_kv_file(tmpdir / "finalize-state.sh", key)


def _read_run_flags_kv(tmpdir: Path, key: str) -> str:
    return _read_kv_file(tmpdir / "run-flags.sh", key)


def _step9a1_heuristic(ctx: RunContext) -> bool | None:
    tmpdir = Path(ctx.tmpdir)
    log_root = tmpdir / "larch-logs"
    run_id = effective_run_id(ctx)
    if not run_id:
        return None
    design_done = _read_finalize_kv(tmpdir, "DESIGN_ONLY_DONE") == "true"
    no_issues = _read_run_flags_kv(tmpdir, "NO_ISSUES") == "true"
    if design_done and no_issues:
        return False
    run_dir = log_root / "implement" / run_id
    manifest_path = run_dir / "manifest.json"
    stats = run_dir / "run-statistics.md"
    if manifest_path.is_file():
        with suppress(OSError, json.JSONDecodeError, TypeError):
            manifest = Manifest.from_json(_read_manifest_v2(manifest_path))
            if _manifest_step9a1_explicitly_skipped(manifest):
                return False
            if _manifest_step9a1_explicitly_ran(manifest):
                return stats.is_file()
    if stats.is_file():
        return True
    forked_target = _read_state_kv(ctx.state_file, "FORKED_TARGET") == "true"
    if ctx.forked or forked_target:
        return False
    ndjson = run_dir / "oos-issues.ndjson"
    if ndjson.is_file() and ndjson.stat().st_size > 0:
        return False
    return None


def _publish_run_tree_to_repo(
    ctx: RunContext,
    log_root: Path,
    *,
    cwd: str | None,
) -> str:
    """Copy tmpdir run tree into repo larch-logs (python3 python/cli.py run-log commit parity)."""
    run_id = effective_run_id(ctx)
    if not validate_run_id_slug(run_id):
        return ""
    if is_placeholder_run_id(run_id):
        _warn_placeholder_run_id(run_id)
        return ""
    src = log_root / "implement" / run_id
    if not src.is_dir():
        return ""
    if cwd is None:
        return f"larch-logs/implement/{run_id}"
    # Always resolve destination from _REPO_ROOT (file-relative constant), never
    # from cwd — a CWD that is a repo subdirectory (e.g. python/) would otherwise
    # produce a stray tree at python/larch-logs/… instead of larch-logs/….
    dest = _REPO_ROOT / "larch-logs" / "implement" / run_id
    if src.resolve() != dest.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest.parent, prefix=f".{run_id}.") as tmp:
            tmp_dest = Path(tmp) / run_id
            _safe_copy_run_tree(src, tmp_dest)
            backup = dest.parent / f".{run_id}.old"
            if backup.exists():
                shutil.rmtree(backup)
            if dest.exists():
                _ = dest.replace(backup)
            _ = tmp_dest.replace(dest)
            if backup.exists():
                shutil.rmtree(backup)
    return f"larch-logs/implement/{run_id}"


def _safe_copy_run_tree(src: Path, dest: Path) -> None:
    """Copy run tree without preserving symlinks that escape the source root."""
    src_root = src.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_symlink():
            resolved = item.resolve()
            try:
                _ = resolved.relative_to(src_root)
            except ValueError as exc:
                msg = "refusing symlink escaping run log tree"
                raise ShipError(msg) from exc
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if resolved.is_file():
                    _ = shutil.copy2(resolved, target)
            continue
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.copy2(item, target)


_VOLATILE_REFRESH_BASENAMES = frozenset({
    "token-report-refresh.json",
    "timing-report-refresh.json",
    "session-transcript-refresh.txt",
    "token-report-refresh.redacted.json",
    "timing-report-refresh.redacted.json",
    "session-transcript-refresh.redacted.txt",
})
_PORCELAIN_PATH_OFFSET = 3
_IMPLEMENT_RUN_REL_PARTS = 3


def _status_line_path(line: str) -> str:
    if len(line) <= _PORCELAIN_PATH_OFFSET:
        return ""
    path = line[_PORCELAIN_PATH_OFFSET:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path


def _volatile_file_paths(rel: str, cwd: str, status_stdout: str) -> tuple[str, ...] | None:
    if not rel.startswith("larch-logs/implement/") or len(rel.split("/")) != _IMPLEMENT_RUN_REL_PARTS:
        return None
    root = Path(cwd) / rel
    paths: list[str] = []
    for line in status_stdout.splitlines():
        path = _status_line_path(line)
        if not path:
            return None
        if path.rstrip("/") == rel and line.startswith("?? "):
            if not root.is_dir():
                return None
            for item in sorted(root.rglob("*")):
                if item.is_file():
                    item_rel = item.relative_to(Path(cwd)).as_posix()
                    if item.name not in _VOLATILE_REFRESH_BASENAMES:
                        return None
                    paths.append(item_rel)
            continue
        if not path.startswith(f"{rel}/"):
            return None
        if Path(path).name not in _VOLATILE_REFRESH_BASENAMES:
            return None
        paths.append(path)
    return tuple(dict.fromkeys(paths))


def _volatile_only_under_run_tree(rel: str, cwd: str, status_stdout: str) -> tuple[str, ...] | None:
    paths = _volatile_file_paths(rel, cwd, status_stdout)
    if paths is None or not paths:
        return None
    return paths


def _run_git_cleanup(runner: Runner, argv: list[str], *, cwd: str | None) -> None:
    result = runner.run(argv, cwd=cwd)
    if result.returncode != 0:
        msg = f"run-log volatile cleanup failed ({result.returncode}): {' '.join(argv)}"
        raise ShipError(msg)


def _cleanup_volatile_run_tree(
    runner: Runner,
    rel: str,
    paths: tuple[str, ...],
    status_stdout: str,
    *,
    cwd: str,
) -> None:
    lines = status_stdout.splitlines()
    has_staged = any(
        not line.startswith("?? ") and line[:1] != " "
        for line in lines
    )
    if has_staged:
        _run_git_cleanup(runner, ["git", "reset", "HEAD", "--", rel], cwd=cwd)
    tracked_paths = tuple(
        path
        for line in lines
        if not line.startswith("?? ")
        for path in (_status_line_path(line),)
        if path in paths
    )
    if tracked_paths:
        _run_git_cleanup(
            runner,
            ["git", "restore", "--worktree", "--staged", "--source=HEAD", "--", *tracked_paths],
            cwd=cwd,
        )
    clean_paths = tuple(
        clean_path
        for line in lines
        if line.startswith("?? ")
        for path in (_status_line_path(line),)
        for clean_path in (
            paths
            if path.rstrip("/") == rel
            else (path,)
        )
        if clean_path in paths
    )
    if clean_paths:
        _run_git_cleanup(runner, ["git", "clean", "-fd", "--", *clean_paths], cwd=cwd)
    repo_status = git.status_porcelain(runner, cwd=cwd)
    if repo_status.returncode != 0:
        msg = "git status failed after volatile run-log cleanup"
        raise ShipError(msg)
    if repo_status.stdout.strip():
        snippet = "\n".join(repo_status.stdout.splitlines()[:20])
        msg = f"volatile run-log cleanup left dirty porcelain:\n{snippet}"
        raise ShipError(msg)


def _scrub_run_tree(directory: Path) -> tuple[int, int]:
    """Scrub secret-shaped values from every file under ``directory`` in place
    before commit (parity with python3 python/cli.py redact scrub-log-secrets).

    Returns ``(total_violations, files_scrubbed)``. Files with no secret are
    left byte-for-byte untouched. Fail-closed: raises :class:`ShipError` if a
    detected secret survives scrubbing, so the caller aborts rather than commits.
    """
    total = 0
    files_scrubbed = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scrubbed, findings = redact.scrub_log_secrets(original)
        if not findings:
            continue
        _, residual = redact.scrub_log_secrets(scrubbed)
        if residual:
            msg = f"secret survived scrubbing in {path}"
            raise ShipError(msg)
        _ = path.write_text(scrubbed, encoding="utf-8")
        total += sum(findings.values())
        files_scrubbed += 1
    return total, files_scrubbed


def _warn_secret_scrub(violations: int, files_scrubbed: int, directory: Path) -> None:
    """Emit a loud stderr warning when the pre-flush gate redacted a secret."""
    banner = (
        "\n"
        "#############################################################################\n"
        "##  !!  SECRETS DETECTED AND SCRUBBED FROM RUN LOGS BEFORE FLUSH  !!\n"
        "#############################################################################\n"
        f"## scrubbed {violations} secret-shaped value(s) across "
        f"{files_scrubbed} file(s) in:\n"
        f"##   {directory}\n"
        "## The flush proceeds with redacted content, but a credential was almost\n"
        "## certainly exposed in this run -- ROTATE it now and check chat/PRs for\n"
        "## the same value.\n"
        "#############################################################################\n"
    )
    logging_util.BreadcrumbWriter().emit(redact.redact_outbound(banner))


def _larch_log_commit(
    runner: Runner,
    ctx: RunContext,
    log_root: Path,
    *,
    cwd: str | None = None,
) -> CommandResult:
    sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    if sentinel.exists():
        raise ShipError("refusing larch-log commit after post-merge sentinel")
    # Guard: refuse when the caller's cwd is not the repo root — staging
    # larch-logs/ from a subdirectory (e.g. python/) would create a stray tree
    # at python/larch-logs/… and silently pollute git history.
    if cwd is not None and Path(cwd).resolve() != _REPO_ROOT.resolve():
        raise ShipError(
            f"refusing larch-log commit: cwd {cwd!r} is not repo root {str(_REPO_ROOT)!r}"
        )
    git_root = str(_REPO_ROOT)
    if (_REPO_ROOT / ".git").exists():
        branch = git.try_current_branch(runner, cwd=git_root)
        default_branches = {"main", "master"}
        origin_head = runner.run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=git_root,
        )
        if origin_head.returncode == 0 and origin_head.stdout.strip().startswith("origin/"):
            default_branches.add(origin_head.stdout.strip().split("/", 1)[1])
        if branch in default_branches:
            raise ShipError(f"refusing larch-log commit on default branch {branch}")
    rel = _publish_run_tree_to_repo(ctx, log_root, cwd=cwd)
    if not rel:
        return CommandResult(("true",), 0, "", "", 0.0)
    # Pre-flush secret gate: scrub Cursor keys et al. from the staged run tree
    # before commit (parity with python3 python/cli.py redact scrub-log-secrets). Fail-closed via
    # ShipError if a detected secret survives.
    violations = 0
    if cwd is not None:
        scrub_dir = _REPO_ROOT / rel
        if scrub_dir.is_dir():
            violations, files_scrubbed = _scrub_run_tree(scrub_dir)
            if violations > 0:
                _warn_secret_scrub(violations, files_scrubbed, scrub_dir)
    status = git.status_porcelain_paths(runner, rel, cwd=git_root)
    if status.returncode != 0:
        return status
    if not status.stdout.strip():
        return CommandResult(("true",), 0, "", "", 0.0)
    if cwd is not None:
        volatile_paths = _volatile_only_under_run_tree(rel, git_root, status.stdout)
        if volatile_paths is not None:
            _cleanup_volatile_run_tree(
                runner,
                rel,
                volatile_paths,
                status.stdout,
                cwd=git_root,
            )
            return CommandResult(("larch-log-volatile-only",), 0, "", "", 0.0)
    _ = git.add(runner, rel, cwd=git_root)
    if git.diff_quiet(runner, rel, cached=True, cwd=git_root):
        return CommandResult(("true",), 0, "", "", 0.0)
    subject = f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{effective_run_id(ctx)}"
    return git.commit(runner, subject, cwd=git_root)


def _tree_backup_path(dest: Path) -> Path:
    return dest.parent / f".{dest.name}.removing"


def _remove_backup_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _validate_tree_destination(dest: Path) -> None:
    if dest.is_symlink():
        raise ValueError(f"refusing to replace symlink destination: {dest}")
    if dest.exists() and not dest.is_dir():
        raise ValueError(f"refusing to replace non-directory destination: {dest}")


def _restore_publish_backup(backup: Path, dest: Path) -> None:
    if not (backup.exists() or backup.is_symlink()):
        return
    if backup.is_symlink() or not backup.is_dir():
        raise ValueError(f"refusing to restore non-directory backup: {backup}")
    backup.rename(dest)
    _validate_tree_destination(dest)


def _restore_publish_backup_after_failure(backup: Path, dest: Path) -> None:
    if backup.exists() and not dest.exists():
        with suppress(OSError):
            backup.rename(dest)


def _replace_tree_with_backup(staged: Path, dest: Path) -> None:
    _validate_tree_destination(dest)
    backup = _tree_backup_path(dest)
    backup_exists = backup.exists() or backup.is_symlink()
    if backup_exists and dest.exists():
        _remove_backup_path(backup)
    elif backup_exists:
        _restore_publish_backup(backup, dest)

    moved_to_backup = False
    if dest.exists():
        dest.rename(backup)
        moved_to_backup = True
    try:
        staged.rename(dest)
    except Exception:
        if moved_to_backup:
            _restore_publish_backup_after_failure(backup, dest)
        raise
    if backup.exists() or backup.is_symlink():
        _remove_backup_path(backup)


def _replace_staged_tree_or_error(staged: Path, dest: Path) -> str | None:
    backup = _tree_backup_path(dest)
    try:
        _validate_tree_destination(dest)
    except ValueError as exc:
        return str(exc)
    try:
        if dest.exists() or backup.exists() or backup.is_symlink():
            _replace_tree_with_backup(staged, dest)
        else:
            staged.replace(dest)
    except ValueError as exc:
        return str(exc)
    return None


def _update_commit_manifest_with_warning(manifest: Path) -> None:
    if not manifest.is_file():
        return
    try:
        _update_manifest_v2(manifest, {})
    except (OSError, json.JSONDecodeError, TypeError, ValueError, UnicodeError) as exc:
        print(f"WARN: larch-log commit manifest update failed: {exc}", file=sys.stderr)


def _publish_breadcrumbs_with_warning(log_root: Path, dest: Path) -> None:
    bread_src = log_root.parent / "breadcrumbs"
    if not (bread_src.is_dir() and log_root.name == "larch-logs"):
        return
    try:
        breadcrumb_rc = publish_breadcrumbs_main(
            ["--source-dir", str(bread_src), "--dest-dir", str(dest / "breadcrumbs")],
        )
    except (OSError, ValueError, ShipError, UnicodeError) as exc:
        print(f"WARN: larch-log commit breadcrumb publish failed: {exc}", file=sys.stderr)
        return
    if breadcrumb_rc != 0:
        print(f"WARN: larch-log commit breadcrumb publish failed: rc={breadcrumb_rc}", file=sys.stderr)


def _copy_tree_to_repo(
    log_root: Path,
    repo_root: Path,
    skill: str,
    run_id: str,
) -> tuple[list[str], Path, int, str | None]:
    src = _run_dir(log_root, skill, run_id)
    dest = _repo_run_dir(repo_root, skill, run_id)
    rels: list[str] = []
    scrub_violations = 0
    if src.is_dir():
        if src.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=dest.parent, prefix=f".{run_id}.") as tmp:
                tmp_dest = Path(tmp) / run_id
                _safe_copy_run_tree(src, tmp_dest)
                try:
                    count, _files_scrubbed = _scrub_run_tree(tmp_dest)
                except ShipError as exc:
                    return [], dest, scrub_violations, str(exc)
                scrub_violations += count
                replace_error = _replace_staged_tree_or_error(tmp_dest, dest)
                if replace_error:
                    return [], dest, scrub_violations, replace_error
        rels.append(f"larch-logs/{skill}/{run_id}")
    shared_src = log_root / "shared"
    shared_dest = repo_root / "larch-logs" / "shared"
    if shared_src.is_dir():
        if shared_src.resolve() != shared_dest.resolve():
            shared_dest.mkdir(parents=True, exist_ok=True)
            for item in sorted(shared_src.iterdir()):
                if not item.exists() or item.is_symlink():
                    continue
                dest_item = shared_dest / item.name
                if item.is_dir():
                    _safe_copy_run_tree(item, dest_item)
                elif item.is_file():
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_item)
            try:
                count, _files_scrubbed = _scrub_run_tree(shared_dest)
            except ShipError as exc:
                return [], dest, scrub_violations, str(exc)
            scrub_violations += count
        rels.append("larch-logs/shared")
    return rels, dest, scrub_violations, None


def _git_stdout(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=str(cwd), text=True, capture_output=True, check=False)


def _default_branches(repo_root: Path) -> set[str]:
    branches = {"main", "master"}
    origin_head = _git_stdout(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=repo_root,
    )
    if origin_head.returncode == 0 and origin_head.stdout.strip().startswith("origin/"):
        branches.add(origin_head.stdout.strip().split("/", 1)[1])
    return branches


def _commit_run(log_root: Path, skill: str, run_id: str, *, cwd: str | None, pre_scrub_violations: int = 0) -> CommandResult:
    sentinel = log_root.parent / "post-merge-sentinel"
    if sentinel.exists():
        return CommandResult(
            ("run-log", "commit"),
            1,
            "",
            "refusing larch-log commit after post-merge sentinel\n",
            0.0,
        )
    repo_root = _resolve_consumer_repo_root(cwd)
    branch = _git_stdout(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if branch.returncode == 0 and branch.stdout.strip() in _default_branches(repo_root):
        return CommandResult(
            ("run-log", "commit"),
            1,
            "",
            f"refusing larch-log commit on default branch {branch.stdout.strip()}\n",
            0.0,
        )
    if is_placeholder_run_id(run_id):
        _warn_placeholder_run_id(run_id)
        return CommandResult(("true",), 0, "", "", 0.0)
    manifest = _manifest_cli_path(log_root, skill, run_id)
    _update_commit_manifest_with_warning(manifest)
    rels, dest, copy_tree_violations, scrub_error = _copy_tree_to_repo(log_root, repo_root, skill, run_id)
    violations = pre_scrub_violations + copy_tree_violations
    if scrub_error:
        return CommandResult(("run-log", "commit"), 1, "", f"{scrub_error}\n", 0.0)
    if not rels:
        return CommandResult(("true",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    _publish_breadcrumbs_with_warning(log_root, dest)
    status = _git_stdout(["git", "status", "--porcelain", "--", *rels], cwd=repo_root)
    if status.returncode != 0:
        return CommandResult(tuple(status.args), status.returncode, status.stdout, status.stderr, 0.0)
    if not status.stdout.strip():
        return CommandResult(("true",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    run_rel = f"larch-logs/{skill}/{run_id}"
    volatile_paths = _volatile_only_under_run_tree(run_rel, str(repo_root), status.stdout)
    if volatile_paths is not None:
        _cleanup_volatile_run_tree(
            proc,
            run_rel,
            volatile_paths,
            status.stdout,
            cwd=str(repo_root),
        )
        return CommandResult(("larch-log-volatile-only",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    add = _git_stdout(["git", "add", "--", *rels], cwd=repo_root)
    if add.returncode != 0:
        return CommandResult(tuple(add.args), add.returncode, add.stdout, add.stderr, 0.0)
    diff = _git_stdout(["git", "diff", "--cached", "--quiet", "--", *rels], cwd=repo_root)
    if diff.returncode == 0:
        return CommandResult(("true",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    subject = f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{run_id}"
    commit = _git_stdout(["git", "commit", "-m", subject, "--", *rels], cwd=repo_root)
    if commit.returncode != 0:
        return CommandResult(tuple(commit.args), commit.returncode, commit.stdout, commit.stderr, 0.0)
    sha = _git_stdout(["git", "rev-parse", "HEAD"], cwd=repo_root)
    stdout = f"{sha.stdout.strip()}\nSECRET_SCRUB_VIOLATIONS={violations}\n"
    _ = dest
    return CommandResult(tuple(commit.args), 0, stdout, commit.stderr, 0.0)


def _parse_common(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return None
    try:
        _validate_slug("skill", args.skill)
        _validate_slug("run-id", args.run_id)
        args.log_root_path = _resolve_log_root(getattr(args, "log_root", ""))
    except (ValueError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return None
    return args


def _common_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, add_help=False)
    parser.add_argument("--log-root", default="")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--run-id", required=True)
    return parser


def larch_log_init_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log init")
    parser.add_argument("--parent-skill", default="")
    parser.add_argument("--issue", default="")
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid init arguments")
    if args.parent_skill:
        try:
            _validate_slug("parent-skill", args.parent_skill)
        except ValueError as exc:
            return _larch_log_fail(1, str(exc))
    if args.issue and not str(args.issue).isdigit():
        return _larch_log_fail(1, f"invalid issue: {args.issue}")
    path = _manifest_cli_path(args.log_root_path, args.skill, args.run_id)
    if path.is_file():
        _emit_larch_log_envelope(path=path, written=False, unchanged=True)
        return 0
    extra: dict[str, Any] = {
        "parent_skill": args.parent_skill or None,
        "issue_number": int(args.issue) if args.issue else None,
    }
    manifest = Manifest.synthesize_v2(skill=args.skill, run_id=args.run_id, extra=extra)
    _write_manifest_v2(path, manifest.to_json(existing=None))
    _emit_larch_log_envelope(path=path, written=True, unchanged=False)
    return 0


def larch_log_write_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log write")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--commit", action="store_true")
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid write arguments")
    if not Path(args.input_file).is_file():
        return _larch_log_fail(1, f"input file not found: {args.input_file}")
    try:
        path, written, unchanged = _write_batch(args.log_root_path, args.skill, args.run_id, args.batch, Path(args.input_file))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _larch_log_fail(1 if isinstance(exc, ValueError) else 2, str(exc))
    _emit_larch_log_envelope(path=path, written=written, unchanged=unchanged)
    return 0


def larch_log_append_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log append")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--record-file", required=True)
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid append arguments")
    if not Path(args.record_file).is_file():
        return _larch_log_fail(1, f"record file not found: {args.record_file}")
    try:
        path, written, unchanged = _append_batch(args.log_root_path, args.skill, args.run_id, args.batch, Path(args.record_file))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _larch_log_fail(1 if isinstance(exc, ValueError) else 2, str(exc))
    _emit_larch_log_envelope(path=path, written=written, unchanged=unchanged)
    return 0


def larch_log_exists_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log exists")
    parser.add_argument("--batch", required=True)
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid exists arguments")
    if args.batch not in _LARCH_LOG_BATCHES:
        return _larch_log_fail(1, f"unknown batch: {args.batch}")
    path = _batch_path(args.log_root_path, args.skill, args.run_id, args.batch)
    _emit_larch_log_envelope(path=path, written=False, unchanged=path.exists())
    return 0


def larch_log_manifest_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log manifest")
    parser.add_argument("--field", action="append", default=[])
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid manifest arguments")
    path = _manifest_cli_path(args.log_root_path, args.skill, args.run_id)
    if not path.is_file():
        return _larch_log_fail(1, f"manifest not found: {path}")
    updates: dict[str, Any] = {}
    for assignment in args.field:
        if "=" not in assignment:
            return _larch_log_fail(1, f"invalid field assignment: {assignment}")
        key, _, raw = assignment.partition("=")
        updates[key] = _parse_manifest_scalar(raw)
    try:
        _update_manifest_v2(path, updates)
    except ValueError as exc:
        return _larch_log_fail(1, str(exc))
    _emit_larch_log_envelope(path=path, written=True, unchanged=False)
    return 0


def larch_log_commit_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log commit")
    parser.add_argument("--pre-scrub-violations", default="0")
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid commit arguments")
    if not str(args.pre_scrub_violations).isdigit():
        return _larch_log_fail(1, "invalid --pre-scrub-violations: expected non-negative integer")
    try:
        result = _commit_run(
            args.log_root_path,
            args.skill,
            args.run_id,
            cwd=str(Path.cwd()),
            pre_scrub_violations=int(args.pre_scrub_violations),
        )
    except ShipError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        return result.returncode
    commit_sha = ""
    extra: dict[str, str | int] = {}
    for line in result.stdout.splitlines():
        if re.fullmatch(r"[0-9a-f]{40}", line):
            commit_sha = line
        elif line.startswith("SECRET_SCRUB_VIOLATIONS="):
            extra["SECRET_SCRUB_VIOLATIONS"] = line.split("=", 1)[1]
    unchanged = result.argv in {("true",), ("larch-log-volatile-only",)}
    path = _repo_run_dir(_resolve_consumer_repo_root(str(Path.cwd())), args.skill, args.run_id)
    _emit_larch_log_envelope(
        path=path if path.exists() else None,
        written=bool(commit_sha),
        unchanged=unchanged,
        commit_sha=commit_sha,
        extra=extra,
    )
    return 0


_BREADCRUMB_SOURCE_TMPDIR_ENV: tuple[str, ...] = (
    "IMPLEMENT_TMPDIR",
    "DESIGN_TMPDIR",
    "REVIEW_TMPDIR",
    "RESEARCH_TMPDIR",
)


def _breadcrumb_source_confined(source_root: Path) -> bool:
    """Defense-in-depth: is the breadcrumb source under a session tmpdir?

    Backs the SECURITY.md guarantee that a breadcrumbs hint outside the active
    session tmpdir is a publish-nothing no-op. The live caller always derives
    ``--source-dir`` from ``log_root.parent`` (the session tmpdir), so this
    never trips on the supported path; it guards a future caller that passes an
    operator-controlled or escaped ``--source-dir``. When no session tmpdir env
    var is set there is no reference root, so legacy behavior is preserved
    (treated as confined).
    """
    roots: list[Path] = []
    for key in _BREADCRUMB_SOURCE_TMPDIR_ENV:
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        with suppress(OSError):
            roots.append(Path(raw).resolve())
    if not roots:
        return True
    try:
        resolved = source_root.resolve()
    except OSError:
        return False
    return any(resolved == root or root in resolved.parents for root in roots)


def publish_breadcrumbs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log publish-breadcrumbs", add_help=False)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--dest-dir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    src = Path(args.source_dir)
    dest = Path(args.dest_dir)
    if not src.is_dir():
        print(f"publish-breadcrumbs: source directory not found: {src}", file=sys.stderr)
        return 1
    source_root = src.parent
    if not _breadcrumb_source_confined(source_root):
        # Per SECURITY.md: a breadcrumbs hint whose session root falls outside
        # every active session tmpdir is a publish-nothing no-op (defense-in-depth;
        # live callers always derive --source-dir from log_root.parent). This is a
        # no-op, not the removed source-directory-wide rejection — the per-file
        # symlink/hardlink/redaction guards below remain the fail-closed surface.
        return 0
    quiet_logs = sorted(
        item for item in source_root.iterdir() if _QUIET_LOG_RE.fullmatch(item.name)
    )
    if not quiet_logs:
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".breadcrumbs.") as tmp:
        staged = Path(tmp) / dest.name
        quiet_log = staged / "quiet.log"
        redacted_parts: list[str] = []
        for item in quiet_logs:
            if item.is_symlink():
                print(f"publish-breadcrumbs: refusing symlink quiet log: {item}", file=sys.stderr)
                return 1
            try:
                stat_result = item.stat()
            except OSError as exc:
                print(f"publish-breadcrumbs: cannot stat quiet log {item}: {exc}", file=sys.stderr)
                return 1
            if not item.is_file():
                continue
            if stat_result.st_nlink > 1:
                print(f"publish-breadcrumbs: refusing hardlinked quiet log: {item}", file=sys.stderr)
                return 1
            out = Path(tmp) / f"{item.name}.redacted"
            state = Path(tmp) / ".redact-state"
            redact.redact_breadcrumb_file(item, out, state)
            redacted_parts.append(f"=== {item.name} ===\n")
            redacted_parts.append(out.read_text(encoding="utf-8", errors="replace"))
        if not redacted_parts:
            return 0
        quiet_log.parent.mkdir(parents=True, exist_ok=True)
        quiet_log.write_text("".join(redacted_parts), encoding="utf-8")
        replace_error = _replace_staged_tree_or_error(staged, dest)
        rc = 0
        if replace_error:
            print(f"publish-breadcrumbs: {replace_error}", file=sys.stderr)
            rc = 1
    return rc


def larch_log_flush_main(argv: list[str]) -> int:
    if argv:
        print(f"python3 python/cli.py run-log flush: unknown argument: {argv[0]}", file=sys.stderr)
        return 0
    tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir or os.environ.get("LARCH_NO_LOGS_COMMIT") == "true":
        return 0
    sid = Path(tmpdir) / "session-id"
    if not sid.exists() or (Path(tmpdir) / "post-merge-sentinel").exists():
        return 0
    run_id = sid.read_text(encoding="utf-8", errors="replace").strip()
    if not validate_run_id_slug(run_id):
        return 0
    log_root = Path(tmpdir) / "larch-logs"
    ctx = RunContext(
        branch="",
        issue="",
        repo="",
        run_id=run_id,
        tmpdir=tmpdir,
        merge=False,
        draft=False,
        forked=False,
        manifest_path=str(log_root / "implement" / run_id / "manifest.json"),
        tool_label="",
        no_admin_fallback=False,
        repo_unavailable=False,
    )
    try:
        _stage_pre_commit(proc, ctx, log_root, mode="flush")
        result = _commit_run(log_root, "implement", run_id, cwd=str(Path.cwd()))
        if result.returncode != 0:
            detail = result.stderr.strip()
            if detail:
                print(
                    f"WARN: larch-log flush failed: rc={result.returncode}: {detail}",
                    file=sys.stderr,
                )
            else:
                print(f"WARN: larch-log flush failed: rc={result.returncode}", file=sys.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("SECRET_SCRUB_VIOLATIONS=") and not line.endswith("=0"):
                print(
                    "WARN: larch-log flush scrubbed secret-shaped values before commit",
                    file=sys.stderr,
                )
    except Exception as exc:
        print(f"WARN: larch-log flush failed: {exc}", file=sys.stderr)
    return 0


def _load_refresh_session_env(tmpdir: Path) -> None:
    session_env = tmpdir / "session-env.sh"
    if not session_env.is_file():
        return
    for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
        value = _read_kv_file(session_env, key)
        if value:
            os.environ[key] = value
    os.environ["IMPLEMENT_TMPDIR"] = str(tmpdir)


def _refresh_context(tmpdir: Path, state_file: Path, run_id: str) -> RunContext:
    return RunContext(
        branch="",
        issue=_read_kv_file(state_file, "ISSUE_NUMBER") or "",
        repo="",
        run_id=run_id,
        tmpdir=str(tmpdir),
        merge=False,
        draft=False,
        forked=_read_kv_file(state_file, "FORKED_TARGET") == "true",
        manifest_path=str(tmpdir / "larch-logs" / "implement" / run_id / "manifest.json"),
        tool_label="",
        no_admin_fallback=False,
        repo_unavailable=False,
        state_file=str(state_file),
        no_logs_commit=_read_kv_file(state_file, "NO_LOGS_COMMIT") == "true",
        merge_result=_read_kv_file(state_file, "MERGE_RESULT"),
    )


def refresh_run_logs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log refresh", add_help=False)
    parser.add_argument("--state-file", default="")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("REFRESH_COMMITTED=false REASON=usage-error")
        return 0
    tmpdir = Path(args.implement_tmpdir)
    state_file = Path(args.state_file) if args.state_file else tmpdir / "finalize-state.sh"
    if not state_file.is_file():
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_STATE_FILE_MISSING}")
        return 0
    run_id = _read_kv_file(state_file, "RUN_ID")
    if not run_id:
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_NO_RUN_ID}")
        return 0
    if not validate_run_id_slug(run_id):
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_INVALID_RUN_ID}")
        return 0
    if _read_kv_file(state_file, "NO_LOGS_COMMIT") == "true":
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_NO_LOGS_COMMIT}")
        return 0
    if (tmpdir / "post-merge-sentinel").is_file() or _read_kv_file(state_file, "MERGE_RESULT") in config.POST_MERGE_MERGE_RESULTS:
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_POST_MERGE}")
        return 0
    _load_refresh_session_env(tmpdir)
    ctx = _refresh_context(tmpdir, state_file, run_id)
    skip = flush_logs_pre(proc, ctx, cwd=str(Path.cwd()))
    if skip.skipped:
        if skip.reason in {
            config.REFRESH_SKIP_COMMIT_FAILED,
            REFRESH_SKIP_RECOVERY_FAILED,
        }:
            err = " ".join(skip.error.split())
            if err:
                print(f"REFRESH_COMMITTED=false REASON={skip.reason} ERROR={err}")
            else:
                print(f"REFRESH_COMMITTED=false REASON={skip.reason}")
        elif skip.reason == config.REFRESH_SKIP_VOLATILE_ONLY:
            print("REFRESH_COMMITTED=false REASON=no-changes")
        else:
            print(f"REFRESH_SKIPPED=true REASON={skip.reason}")
    else:
        print("REFRESH_COMMITTED=true")
    return 0


def _capture_transcript_append_warning(
    issues_log: Path | None,
    step_label: str,
    status: str,
    message: str,
) -> None:
    if issues_log is None:
        return
    entry = f"- **Step {step_label} — session-transcript status={status}:** {message}"
    with suppress(OSError):
        _append_execution_issue(issues_log, "Warnings", entry)


def _capture_transcript_emit(
    issues_log: Path | None,
    step_label: str,
    status: str,
    message: str,
) -> int:
    _capture_transcript_append_warning(issues_log, step_label, status, message)
    print(f"SESSION_TRANSCRIPT_STATUS={status}")
    return 0


def _capture_transcript_redact_stderr(path: Path) -> str:
    if not path.is_file():
        return ""
    snippet = " ".join(path.read_text(encoding="utf-8", errors="replace").split())
    try:
        snippet = redact.redact_secrets_only(snippet)
    except Exception:
        snippet = "<REDACTION_FAILED>"
    return snippet[:300]


def capture_transcript_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log capture-transcript", add_help=False)
    parser.add_argument("--source-file", default="")
    parser.add_argument("--log-root", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--no-logs-commit", default="false")
    parser.add_argument("--execution-issues-log", default="")
    parser.add_argument("--warning-step-label", default="7a")
    parser.add_argument("--refresh-mode", default="false")
    parser.add_argument("--defer-commit", default="false")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("SESSION_TRANSCRIPT_STATUS=usage-error")
        return 0
    if args.no_logs_commit not in {"true", "false"} or args.refresh_mode not in {"true", "false"} or args.defer_commit not in {"true", "false"}:
        print("SESSION_TRANSCRIPT_STATUS=usage-error")
        return 0
    issues_log = Path(args.execution_issues_log) if args.execution_issues_log else None
    log_root = Path(args.log_root)
    existing_transcript = log_root / args.skill / args.run_id / "session-transcript.jsonl"
    source = Path(args.source_file) if args.source_file else None
    transcript_path: Path | None = None
    if source is None or not source.is_file() or source.stat().st_size == 0:
        if args.refresh_mode == "true" and existing_transcript.is_file():
            return _capture_transcript_emit(
                issues_log,
                args.warning_step_label,
                "source-file-missing",
                "Claude source file was empty or not a regular file; refresh skipped and prior transcript retained.",
            )
        return _capture_transcript_emit(
            issues_log,
            args.warning_step_label,
            "source-file-missing",
            "Claude source file was empty or not a regular file; transcript capture skipped.",
        )
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("TRANSCRIPT_PATH="):
            transcript_path = Path(line.removeprefix("TRANSCRIPT_PATH=").strip())
            break
    if transcript_path is None or not transcript_path.is_file():
        if args.refresh_mode == "true" and existing_transcript.is_file():
            return _capture_transcript_emit(
                issues_log,
                args.warning_step_label,
                "transcript-path-missing",
                "Claude source file did not contain a TRANSCRIPT_PATH entry; refresh skipped and prior transcript retained.",
            )
        return _capture_transcript_emit(
            issues_log,
            args.warning_step_label,
            "transcript-path-missing",
            "Claude source file did not contain a TRANSCRIPT_PATH entry; transcript capture skipped.",
        )
    rendered = Path(tempfile.mkstemp(prefix="session-transcript.", suffix=".jsonl")[1])
    render_err = Path(tempfile.mkstemp(prefix="render-stderr.", suffix=".log")[1])
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "python/cli.py"),
                "run-log",
                "render-session-transcript",
                "--input",
                str(transcript_path),
                "--output",
                str(rendered),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            if result.stderr:
                render_err.write_text(result.stderr, encoding="utf-8")
            msg = _capture_transcript_redact_stderr(render_err) or "session-transcript renderer exited non-zero with no stderr"
            return _capture_transcript_emit(
                issues_log,
                args.warning_step_label,
                "render-failed",
                f"session-transcript render failed; transcript was not committed: {msg}",
            )
        if not rendered.is_file() or rendered.stat().st_size == 0:
            return _capture_transcript_emit(
                issues_log,
                args.warning_step_label,
                "render-empty",
                "session-transcript renderer produced an empty file; transcript was not committed.",
            )
        _write_batch(log_root, args.skill, args.run_id, "session-transcript", rendered)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _capture_transcript_emit(
            issues_log,
            args.warning_step_label,
            "write-failed",
            f"larch-log write failed; transcript was not captured: {exc}",
        )
    finally:
        rendered.unlink(missing_ok=True)
        render_err.unlink(missing_ok=True)
    if args.no_logs_commit == "true":
        return _capture_transcript_emit(
            issues_log,
            args.warning_step_label,
            "suppressed-no-logs-commit",
            "--no-logs-commit was set; transcript was written under the staging log root but not committed.",
        )
    if args.defer_commit == "true":
        print("SESSION_TRANSCRIPT_STATUS=captured")
        return 0
    commit = _commit_run(log_root, args.skill, args.run_id, cwd=str(Path.cwd()))
    if commit.returncode != 0:
        err = (commit.stderr or "larch-log commit failed").strip().replace("\n", " ")
        return _capture_transcript_emit(
            issues_log,
            args.warning_step_label,
            "commit-failed",
            err,
        )
    print("SESSION_TRANSCRIPT_STATUS=captured")
    return 0


def _resolve_required_files_manifest(raw: str) -> Path:
    if not raw:
        return _REQUIRED_FILES_TSV
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (_REPO_ROOT / raw.removeprefix("./")).resolve()
    if not str(candidate).startswith(str(_REPO_ROOT.resolve())):
        msg = "LARCH_VERIFY_MANIFEST resolves outside repository root"
        raise ValueError(msg)
    return candidate


def _manifest_field(manifest: Manifest, key: str) -> str:
    value = manifest.reserved.get(key) if key in _V2_RESERVED_KEYS else None
    if value is None and manifest.extra:
        value = manifest.extra.get(key)
    if key == "pr_number":
        if isinstance(value, bool):
            return ""
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return ""
    if key == "status":
        return manifest.status
    return ""


def _manifest_step9a1_explicitly_skipped(manifest: Manifest) -> bool:
    return manifest.steps_ran.get("step9a1") is False


def _manifest_step9a1_explicitly_ran(manifest: Manifest) -> bool:
    return manifest.steps_ran.get("step9a1") is True


def _manifest_steps_ran_empty(manifest: Manifest) -> bool:
    return len(manifest.steps_ran) == 0


def _manifest_steps_ran_nonempty_without_step9a1(manifest: Manifest) -> bool:
    return bool(manifest.steps_ran) and "step9a1" not in manifest.steps_ran


def _final_summary_heading_bail_signal(run_dir: Path) -> bool:
    summary = run_dir / "final-summary.md"
    if not summary.is_file():
        return False
    for line in summary.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            return bool(_TERMINAL_OUTCOME_SUFFIX.search(line.rstrip("\r\n")))
    return False


def _final_summary_bail_signal_without_pr_evidence(
    run_dir: Path,
    manifest_pr_number: str,
    manifest_data: Manifest | None = None,
) -> bool:
    manifest_obj: object | None = manifest_data.to_json(existing=None) if manifest_data is not None else None
    if manifest_obj is None and manifest_pr_number.strip().isdigit():
        manifest_obj = {"pr_number": int(manifest_pr_number)}
    pr = int(manifest_pr_number) if manifest_pr_number.strip().isdigit() else 0
    return terminal_bail_skip_signal(run_dir, manifest_obj, pr)


def _verify_has_file(run_dir: Path, relative_path: str) -> bool:
    return (run_dir / relative_path).is_file()


def _verify_condition_reached(
    condition: str,
    run_dir: Path,
    manifest_data: Manifest,
    *,
    manifest_status: str,
    manifest_pr_number: str,
    chain: bool = False,
) -> bool:
    if condition == "always":
        return True
    if condition == "step5":
        return (
            _verify_has_file(run_dir, "code-review-tally.json")
            or _verify_has_file(run_dir, "review-findings-full.jsonl")
            or _verify_condition_reached(
                "step7a",
                run_dir,
                manifest_data,
                manifest_status=manifest_status,
                manifest_pr_number=manifest_pr_number,
            )
        )
    if condition == "step7a":
        if (
            _manifest_steps_ran_empty(manifest_data)
            and _final_summary_bail_signal_without_pr_evidence(
                run_dir,
                manifest_pr_number,
                manifest_data,
            )
            and not (
                _verify_has_file(run_dir, "token-report.json")
                or _verify_has_file(run_dir, "timing-report.json")
                or _verify_has_file(run_dir, "execution-issues.ndjson")
                or _verify_has_file(run_dir, "session-transcript.jsonl")
            )
        ):
            return False
        return (
            _verify_has_file(run_dir, "token-report.json")
            or _verify_has_file(run_dir, "timing-report.json")
            or _verify_has_file(run_dir, "execution-issues.ndjson")
            or _verify_has_file(run_dir, "session-transcript.jsonl")
            or _verify_condition_reached(
                "step8",
                run_dir,
                manifest_data,
                manifest_status=manifest_status,
                manifest_pr_number=manifest_pr_number,
            )
        )
    if condition == "step8":
        if (
            _manifest_steps_ran_empty(manifest_data)
            and _final_summary_bail_signal_without_pr_evidence(
                run_dir,
                manifest_pr_number,
                manifest_data,
            )
            and not _verify_has_file(run_dir, "version-bump-reasoning.md")
        ):
            return False
        return (
            _verify_has_file(run_dir, "version-bump-reasoning.md")
            or _verify_has_file(run_dir, "final-summary.md")
            or _verify_condition_reached(
                "step9a1",
                run_dir,
                manifest_data,
                manifest_status=manifest_status,
                manifest_pr_number=manifest_pr_number,
                chain=True,
            )
        )
    if condition == "step9a1":
        # Intentional divergence from the retired bash verify-completeness, which
        # OR-ed run-statistics.md / oos-issues.ndjson / PR-number / status=done /
        # final-summary.md. Step 9a.1 completion is authoritative ONLY via
        # run-statistics.md plus explicit steps_ran.step9a1 markers (#4427): an
        # oos-issues.ndjson alone is provisional disposition evidence and must
        # NOT count, and a steps_ran.step9a1=true without run-statistics.md is a
        # stale or corrupt marker that must fail the scan. See the "bail-time
        # steps_ran invariant" in skills/implement/SKILL.md and the asserting
        # tests test_verify_completeness_stale_step9a1_true_without_stats_fails
        # and test_flush_logs_pre_downgrades_stale_step9a1_true_with_ndjson_only.
        if _manifest_step9a1_explicitly_skipped(manifest_data):
            return False
        if _manifest_step9a1_explicitly_ran(manifest_data):
            return True
        if (
            _manifest_steps_ran_empty(manifest_data)
            and _final_summary_bail_signal_without_pr_evidence(
                run_dir,
                manifest_pr_number,
                manifest_data,
            )
            and not _verify_has_file(run_dir, "run-statistics.md")
        ):
            return False
        if (
            _final_summary_bail_signal_without_pr_evidence(
                run_dir,
                manifest_pr_number,
                manifest_data,
            )
            and not _verify_has_file(run_dir, "run-statistics.md")
            and _manifest_steps_ran_nonempty_without_step9a1(manifest_data)
        ):
            return False
        return _verify_has_file(run_dir, "run-statistics.md") if chain else True
    if condition == "exn-agg-validate-fail":
        path = run_dir / "execution-issues.ndjson"
        return path.is_file() and "merged output failed validation" in path.read_text(encoding="utf-8", errors="replace")
    if condition == "exn-agg-dispatch-fail":
        path = run_dir / "execution-issues.ndjson"
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
        return (
            "dispatch-with-waterfall exited non-zero" in text
            or "agent dispatch-waterfall exited non-zero" in text
            or "DISPATCH_OK=false" in text
        )
    msg = f"unsupported manifest condition: {condition}"
    raise ValueError(msg)


def verify_completeness_main(argv: list[str]) -> int:
    if not argv:
        print("MISSING=manifest", file=sys.stderr)
        return 1
    run_dir = Path(argv[0])
    if not run_dir.is_dir():
        print(f"verify-completeness: run dir not found: {run_dir}", file=sys.stderr)
        return 1
    try:
        manifest_tsv = _resolve_required_files_manifest(os.environ.get("LARCH_VERIFY_MANIFEST", ""))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not manifest_tsv.is_file():
        print(f"verify-completeness: manifest not found: {manifest_tsv}", file=sys.stderr)
        return 1
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        print("MISSING=manifest")
        return 1
    try:
        manifest_data = _read_manifest_v2(manifest_path)
        manifest = Manifest.from_json(manifest_data)
    except (OSError, json.JSONDecodeError, TypeError):
        print("MISSING=manifest")
        return 1
    manifest_status = _manifest_field(manifest, "status")
    manifest_pr_number = _manifest_field(manifest, "pr_number")
    missing: list[str] = []
    for line in manifest_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if not parts or parts[0] == "relative_path":
            continue
        relative_path, condition = parts[0], parts[1] if len(parts) > 1 else "always"
        if ".." in relative_path.split("/"):
            print(f"verify-completeness: invalid relative_path (..): {relative_path}", file=sys.stderr)
            return 1
        if not re.fullmatch(r"[A-Za-z0-9_./*-]+", relative_path):
            print(f"verify-completeness: invalid characters in relative_path: {relative_path}", file=sys.stderr)
            return 1
        if not _verify_condition_reached(
            condition,
            run_dir,
            manifest,
            manifest_status=manifest_status,
            manifest_pr_number=manifest_pr_number,
        ):
            continue
        if "*" in relative_path:
            if relative_path.count("*") > 1:
                print(
                    f"verify-completeness: relative_path must contain at most one * wildcard: {relative_path}",
                    file=sys.stderr,
                )
                return 1
            glob_hits = list(run_dir.glob(relative_path))
            if not any(hit.is_file() for hit in glob_hits):
                missing.append(relative_path)
        elif not _verify_has_file(run_dir, relative_path):
            missing.append(relative_path)
    if missing:
        print("MISSING=" + ",".join(missing))
        return 1
    print("OK")
    return 0


_APPEND_LOCK_ATTEMPTS = 100


def _append_execution_issue(log_file: Path, category: str, entry: str) -> None:
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


def append_execution_issue(log_file: Path, category: str, entry: str) -> None:
    _append_execution_issue(log_file, category, entry)


_EXECUTION_ISSUE_CATEGORIES = {
    "Pre-existing Code Issues",
    "Tool Failures",
    "Permission Prompts",
    "External Reviewer Issues",
    "CI Issues",
    "Warnings",
    "Q/A",
}


def append_entry_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="append-execution-issue.sh")
    parser = argparse.ArgumentParser(prog="append-execution-issue.sh", add_help=False)
    parser.add_argument("--log", required=True)
    parser.add_argument("--category", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--entry")
    group.add_argument("--entry-file")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv("FAILED", "true")
        logging_util.emit_kv("USAGE", "append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)")
        return 1
    if args.category not in _EXECUTION_ISSUE_CATEGORIES:
        logging_util.emit_kv("FAILED", "true")
        logging_util.emit_kv("ERROR", f"unsupported category: {args.category}")
        return 1
    try:
        entry = Path(args.entry_file).read_text(encoding="utf-8") if args.entry_file else args.entry
        _append_execution_issue(Path(args.log), args.category, entry)
    except OSError as exc:
        logging_util.emit_kv("FAILED", "true")
        logging_util.emit_kv("ERROR", str(exc))
        return 2
    logging_util.emit_kv("APPENDED", "true")
    logging_util.emit_kv("LOG", args.log)
    return 0


def append_failure_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="python3 python/cli.py run-log append-failure")
    parser = argparse.ArgumentParser(prog="python3 python/cli.py run-log append-failure", add_help=False)
    parser.add_argument("--log", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--verdict", default="")
    parser.add_argument("--retry-count", default="")
    parser.add_argument("--transient-retry-count", default="")
    parser.add_argument("--redact", action="store_true")
    parser.add_argument("--status-label", default="failed")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv("FAILED", "true")
        return 1
    if args.category not in {"Tool Failures", "External Reviewer Issues", "CI Issues", "Warnings"}:
        logging_util.emit_kv("FAILED", "true")
        logging_util.emit_kv("ERROR", f"unsupported category: {args.category}")
        return 1
    for attr in ("exit_code", "retry_count", "transient_retry_count"):
        value = getattr(args, attr)
        if value and not re.fullmatch(r"[0-9]+", value):
            logging_util.emit_kv("FAILED", "true")
            logging_util.emit_kv("ERROR", f"--{attr.replace('_', '-')} must be a non-negative integer")
            return 1
    output = Path(args.output_file)
    if output.is_file() and output.stat().st_size:
        body = output.read_text(encoding="utf-8", errors="replace")
    else:
        body = f"no diagnostics captured (exit {args.exit_code})\n"
    if args.redact:
        body = redact.redact_secrets_only(redact.redact_tmpdir_paths(body))
    if args.category == "Warnings" and "diagram" in f"{args.site} {args.output_file}".lower():
        body = design_diagram_log.sanitize_diagram_capture(body)
    suffix = ""
    if args.verdict:
        suffix += f" — {args.verdict}"
    if args.retry_count and args.transient_retry_count:
        suffix += f" — auth-retries={args.retry_count}, transient-retries={args.transient_retry_count}"
    elif args.retry_count:
        suffix += f" — retries={args.retry_count}"
    entry = (
        f"- **Step {args.site} — {args.tool} {args.status_label} "
        f"(exit {args.exit_code}{suffix})**:\n"
        "  ```\n"
        f"{body.rstrip()}\n"
        "  ```\n"
    )
    try:
        _append_execution_issue(Path(args.log), args.category, entry)
    except OSError as exc:
        logging_util.emit_kv("FAILED", "true")
        logging_util.emit_kv("ERROR", str(exc))
        return 2
    logging_util.emit_kv("APPENDED", "true")
    logging_util.emit_kv("LOG", args.log)
    return 0


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
    "collector-results.env",
    "review-core-threshold.env",
    "findings-classification.tsv",
    "scout-archetype-yield.tsv",
    "rejected-findings.md",
    "oos-accepted-review.md",
    "review-round-summary.md",
    "voting-tally.md",
    "aggregator-validate.stderr",
    "aggregator-dispatch.stderr",
    "review-dirty-tree-summary.env",
    "panel-manifest.ndjson",
    "code-voter-slots.ndjson",
    "coder-prompt.md",
    "coder-tool.txt",
    "coder-cursor.log",
    "round-meta.json",
)

_ROUND_ARTIFACT_ALLOW_GLOBS = (
    "cursor-ci-stall-*.json",
    "dirty-checkpoint-*.env",
    "voter*-diag.txt",
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


def _round_name_matches(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def _is_round_sidecar_file(name: str) -> bool:
    return name in _ROUND_SIDECAR_FILES


def _round_artifact_included(name: str) -> bool:
    if _round_name_matches(name, _ROUND_ARTIFACT_DENY_GLOBS):
        return False
    if name in _ROUND_ARTIFACT_ALLOW or _round_name_matches(name, _ROUND_ARTIFACT_ALLOW_GLOBS):
        return True
    return os.environ.get("LARCH_FLUSH_DEBUG") == "1" and _round_name_matches(
        name,
        _ROUND_ARTIFACT_DEBUG_GLOBS,
    )


def _stage_round_artifact(src: Path, name: str) -> str:
    text = src.read_text(encoding="utf-8", errors="replace")
    if "-vote-output" in name:
        raw = text.encode("utf-8")
        if len(raw) > _VOTE_OUTPUT_TRUNCATE_BYTES:
            text = raw[:_VOTE_OUTPUT_TRUNCATE_BYTES].decode(
                "utf-8",
                errors="ignore",
            ) + f"\n[TRUNCATED: original {len(raw)} bytes]\n"
    return redact.redact(text)


def larch_log_write_round_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log write-round")
    parser.add_argument("--round", required=True)
    parser.add_argument("--source-dir", required=True)
    args = _parse_common(parser, argv)
    if args is None:
        return _larch_log_fail(1, "invalid write-round arguments")
    if not str(args.round).isdigit() or int(args.round) <= 0:
        return _larch_log_fail(1, "--round must be a positive integer")
    source = Path(args.source_dir)
    if not source.is_dir() or source.is_symlink():
        return _larch_log_fail(1, f"source directory not found: {source}")
    dynamic_dir = source / "dynamic-archetypes"
    if dynamic_dir.is_symlink():
        return _larch_log_fail(2, f"dynamic-archetypes must not be a symlink: {dynamic_dir}")
    dest = _run_dir(args.log_root_path, args.skill, args.run_id) / f"round-{args.round}"
    prev_round_dir = _run_dir(args.log_root_path, args.skill, args.run_id) / f"round-{int(args.round) - 1}"
    dest.mkdir(parents=True, exist_ok=True)
    written = False
    archetype_refs: dict[str, str] = {}
    seen: dict[str, Path] = {}
    scan_dirs = [source]
    if dynamic_dir.is_dir():
        scan_dirs.append(dynamic_dir)
    for scan_dir in scan_dirs:
        for item in sorted(scan_dir.iterdir()):
            if not item.is_file() or item.is_symlink():
                continue
            name = item.name
            if _is_round_sidecar_file(name):
                continue
            if name.startswith("reviewer-dyn-") and name.endswith(".md"):
                redacted = redact.redact(item.read_text(encoding="utf-8", errors="replace"))
                digest = hashlib.sha256(redacted.encode("utf-8")).hexdigest()[:12]
                shared = args.log_root_path / "shared" / "archetypes"
                shared.mkdir(parents=True, exist_ok=True)
                pool_path = shared / f"{digest}.md"
                if not pool_path.is_file():
                    _atomic_write(path=pool_path, content=redacted)
                slot = "dyn-" + name.removeprefix("reviewer-dyn-").removesuffix(".md")
                archetype_refs[slot] = digest
                written = True
                continue
            if not _round_artifact_included(name):
                continue
            if name == "aggregator-output.txt":
                agg_findings = item.parent / "findings.md"
                if agg_findings.is_file() and agg_findings.read_bytes() == item.read_bytes():
                    continue
            if name.startswith("scout-round") and name.endswith("-manifest.json"):
                prev_manifest = prev_round_dir / name
                if prev_manifest.is_file() and prev_manifest.read_bytes() == item.read_bytes():
                    continue
            if name in seen:
                return _larch_log_fail(
                    2,
                    f"duplicate round artifact basename '{name}' from {item} and {seen[name]}",
                )
            seen[name] = item
            content = _stage_round_artifact(item, name)
            out = dest / name
            if not out.exists() or out.read_text(encoding="utf-8", errors="replace") != content:
                _atomic_write(path=out, content=content)
                written = True
    panel_manifest = dest / "panel-manifest.ndjson"
    if archetype_refs and panel_manifest.is_file():
        lines: list[str] = []
        changed = False
        for line in panel_manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append(line)
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                lines.append(line)
                continue
            if not isinstance(row, dict):
                lines.append(line)
                continue
            row_dict = cast("dict[str, Any]", row)
            slot = str(row_dict.get("slot", ""))
            if slot in archetype_refs and "archetype_ref" not in row:
                row["archetype_ref"] = archetype_refs[slot]
                changed = True
            lines.append(json.dumps(row, ensure_ascii=False))
        if changed:
            _atomic_write(path=panel_manifest, content="\n".join(lines) + "\n")
            written = True
    _emit_larch_log_envelope(path=dest, written=written, unchanged=not written)
    return 0


def path_under_repo(repo_root: Path, rel_path: str) -> bool:
    if "\x00" in rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
        return False
    try:
        resolved = (repo_root / rel_path).resolve()
        _ = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return False
    return True
