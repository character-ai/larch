# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportPrivateUsage=false
"""Manifest dataclasses, state readers, and manifest lifecycle for larch run-logs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from larch.core import config
from larch.core.run_context import RunContext
from larch.report import tokens
from larch.errors import ShipError

from larch.report.run_log_batch import (
    _atomic_write,
    _read_kv_file,
    _read_state_kv,
    _resolve_log_root,
    _run_dir,
    validate_run_id_slug,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]

_MANIFEST_SCHEMA_VERSION = 2

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


_MANIFEST_IMMUTABLE = frozenset(
    {"schema_version", "skill", "run_id", "started_at", "operator_cwd", "operator_repo_root"},
)


def _manifest_cli_path(*, log_root: Path, skill: str, run_id: str) -> Path:
    return _run_dir(log_root=log_root, skill=skill, run_id=run_id) / "manifest.json"


def _read_manifest_v2(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("manifest must be a JSON object")
    return cast("dict[str, Any]", data)


def _write_manifest_v2(*, path: Path, data: dict[str, Any]) -> None:
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


def _update_manifest_v2(*, path: Path, updates: dict[str, Any]) -> dict[str, Any]:
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
    _write_manifest_v2(path=path, data=out)
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


def _read_session_env_key(*, ctx: RunContext, key: str) -> str:
    return _read_kv_file(path=Path(ctx.tmpdir) / "session-env.sh", key=key)


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


def read_state_kv(*, state_file: str | None, key: str) -> str:
    """Read a single KEY=value from an implement state file."""
    return _read_state_kv(state_file=state_file, key=key)


def read_resume_counters(state_file: str | None) -> ResumeCounters:
    """Read persisted CI-loop counters without raising on corrupt state."""
    if not state_file:
        return ResumeCounters(0, 0, 0, 0)
    return ResumeCounters(
        iteration=_parse_nonnegative_int(_read_state_kv(state_file=state_file, key="ITERATION")),
        rebase_count=_parse_nonnegative_int(_read_state_kv(state_file=state_file, key="REBASE_COUNT")),
        fix_attempts=_parse_nonnegative_int(_read_state_kv(state_file=state_file, key="FIX_ATTEMPTS")),
        transient_retries=_parse_nonnegative_int(
            _read_state_kv(state_file=state_file, key="TRANSIENT_RETRIES"),
        ),
    )


def _state_bool_or_default(raw: str, *, default: bool) -> bool:
    text = raw.strip()
    if text == "true":
        return True
    if text == "false":
        return False
    return default


def read_durable_flags(*, state_file: str | None, ctx: RunContext) -> DurableFlags:
    """Read durable mode flags state-first, falling back to the run context."""
    if not state_file:
        return DurableFlags(
            repo_unavailable=ctx.repo_unavailable,
            forked_target=ctx.forked_target,
            forked=ctx.forked,
            merge=ctx.merge,
            draft=ctx.draft,
        )
    raw_forked_target = _read_state_kv(state_file=state_file, key="FORKED_TARGET")
    forked_target = _state_bool_or_default(raw_forked_target, default=ctx.forked_target)
    forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked
    return DurableFlags(
        repo_unavailable=_state_bool_or_default(
            _read_state_kv(state_file=state_file, key="REPO_UNAVAILABLE"),
            default=ctx.repo_unavailable,
        ),
        forked_target=forked_target,
        forked=forked,
        merge=_state_bool_or_default(_read_state_kv(state_file=state_file, key="MERGE"), default=ctx.merge),
        draft=_state_bool_or_default(_read_state_kv(state_file=state_file, key="DRAFT"), default=ctx.draft),
    )


def parse_pr_number(*, state_file: str | None, ctx_pr_number: int | str | None) -> int | None:
    """Parse the persisted PR number; ignore stale context when state exists."""
    if not state_file:
        return None
    raw = _read_state_kv(state_file=state_file, key="PR_NUMBER")
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


def effective_run_id(ctx: RunContext) -> str:
    """Prefer validated state-file RUN_ID over ctx.run_id for log paths."""
    state_run_id = _read_state_kv(state_file=ctx.state_file, key="RUN_ID")
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
        _read_state_kv(state_file=ctx.state_file, key="ISSUE_NUMBER")
        or _read_state_kv(state_file=ctx.state_file, key="ISSUE")
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
    _write_manifest_v2(path=_manifest_path(ctx), data=manifest.to_json(existing=None))
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
    _write_manifest(ctx=ctx, manifest=updated)
    return updated


def _recover_manifest_from_run_dir(*, ctx: RunContext, run_id: str, run_dir: Path) -> Manifest | None:
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
                recovered = _recover_manifest_from_run_dir(ctx=ctx, run_id=rid, run_dir=run_dir)
                if recovered is not None:
                    try:
                        _write_manifest_v2(path=primary, data=recovered.to_json(existing=None))
                    except OSError:
                        return ManifestRecovery(recovered, recovery_ok=False)
                    return ManifestRecovery(recovered, recovery_ok=True)
        elif run_dir.is_dir():
            recovered = _recover_manifest_from_run_dir(ctx=ctx, run_id=rid, run_dir=run_dir)
            if recovered is not None:
                try:
                    _write_manifest_v2(path=primary, data=recovered.to_json(existing=None))
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


def _write_manifest(*, ctx: RunContext, manifest: Manifest) -> None:
    path = _manifest_path(ctx)
    if path.is_file():
        try:
            data = _read_manifest_v2(path)
            if data.get("schema_version") == _MANIFEST_SCHEMA_VERSION:
                updated = replace(manifest, updated_at=_now_utc())
                _write_manifest_v2(path=path, data=updated.to_json(existing=data))
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
        merge_result = _read_state_kv(state_file=ctx.state_file, key="MERGE_RESULT")
        run_id = _read_state_kv(state_file=ctx.state_file, key="RUN_ID")
        no_logs_commit = _read_state_kv(state_file=ctx.state_file, key="NO_LOGS_COMMIT") == "true"
    else:
        merge_result = ctx.merge_result
        run_id = ctx.run_id
        no_logs_commit = ctx.no_logs_commit
    if not merge_result:
        merge_result = _read_kv_file(path=finalize_state, key="MERGE_RESULT")
    if not run_id:
        run_id = _read_kv_file(path=finalize_state, key="RUN_ID")
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


def _manifest_step9a1_explicitly_skipped(manifest: Manifest) -> bool:
    return manifest.steps_ran.get("step9a1") is False


def _manifest_step9a1_explicitly_ran(manifest: Manifest) -> bool:
    return manifest.steps_ran.get("step9a1") is True


def _manifest_steps_ran_nonempty_without_step9a1(manifest: Manifest) -> bool:
    return bool(manifest.steps_ran) and "step9a1" not in manifest.steps_ran


# Expose _resolve_log_root for callers that import it via this module
__all__ = [
    "RECOVERY_REASON_MANIFEST_LOST",
    "REFRESH_SKIP_RECOVERY_FAILED",
    "_MANIFEST_IMMUTABLE",
    "_MANIFEST_SCHEMA_VERSION",
    "_V2_EMIT_EXTRA_EXCLUDED_KEYS",
    "_V2_RESERVED_KEYS",
    "DurableFlags",
    "Manifest",
    "ManifestRecovery",
    "RefreshSkip",
    "ResumeCounters",
    "_manifest_cli_path",
    "_manifest_path",
    "_manifest_step9a1_explicitly_ran",
    "_manifest_step9a1_explicitly_skipped",
    "_manifest_steps_ran_nonempty_without_step9a1",
    "_now_utc",
    "_parse_manifest_scalar",
    "_pre_push_probe",
    "_read_manifest_v2",
    "_read_session_env_key",
    "_read_state_kv",
    "_recover_manifest_from_run_dir",
    "_resolve_consumer_repo_root",
    "_resolve_log_root",
    "_run_log_dir",
    "_update_manifest_v2",
    "_write_manifest",
    "_write_manifest_v2",
    "effective_run_id",
    "init_run",
    "load_or_recover_manifest",
    "load_or_recover_manifest_checked",
    "manifest_status",
    "parse_pr_number",
    "read_durable_flags",
    "read_resume_counters",
    "read_state_kv",
    "update_manifest",
]
