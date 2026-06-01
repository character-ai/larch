"""larch-log manifest lifecycle and split flush entrypoints."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import config
import git
import redact
from proc import CommandResult, Runner
from run_context import RunContext

_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class Manifest:
    status: str
    version: str
    run_id: str
    steps_ran: dict[str, Any]
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class RefreshSkip:
    skipped: bool
    reason: str


def _atomic_write(path: Path, content: str) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=".manifest-", suffix=".tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        _ = tmp_path.write_text(content, encoding="utf-8")
        _ = tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def validate_run_id_slug(run_id: str) -> bool:
    if not run_id or ".." in run_id or "/" in run_id or "\\" in run_id:
        return False
    return _SLUG_RE.match(run_id) is not None


def _manifest_path(ctx: RunContext) -> Path:
    return Path(ctx.tmpdir) / "manifest.json"


def _read_state_kv(state_file: str | None, key: str) -> str:
    if not state_file or not Path(state_file).is_file():
        return ""
    for line in Path(state_file).read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name == key:
            return value
    return ""


def init_run(
    ctx: RunContext,
    *,
    run_id: str | None = None,
) -> Manifest:
    rid = run_id or ctx.run_id
    manifest = Manifest(
        status=config.MANIFEST_STATUS_PARTIAL,
        version="1",
        run_id=rid,
        steps_ran={},
    )
    _write_manifest(ctx, manifest)
    return manifest


def _manifest_to_dict(manifest: Manifest) -> dict[str, Any]:
    return {
        "status": manifest.status,
        "version": manifest.version,
        "run_id": manifest.run_id,
        "steps_ran": manifest.steps_ran,
        "created_at": manifest.created_at,
        "updated_at": manifest.updated_at,
    }


def _dict_to_manifest(data: dict[str, Any]) -> Manifest:
    steps_raw = data.get("steps_ran", {})
    steps = cast("dict[str, Any]", steps_raw) if isinstance(steps_raw, dict) else {}
    return Manifest(
        status=str(data.get("status", config.MANIFEST_STATUS_PARTIAL)),
        version=str(data.get("version", "1")),
        run_id=str(data.get("run_id", "")),
        steps_ran=steps,
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
    )


def update_manifest(ctx: RunContext, **changes: object) -> Manifest:
    current = load_or_recover_manifest(ctx)
    steps = dict(current.steps_ran)
    for key, value in changes.items():
        if key == "steps_ran" and isinstance(value, dict):
            steps.update(cast("dict[str, Any]", value))
        elif key == "status":
            current = Manifest(
                status=str(value),
                version=current.version,
                run_id=current.run_id,
                steps_ran=steps,
                created_at=current.created_at,
                updated_at=current.updated_at,
            )
        else:
            steps[str(key)] = value
    updated = Manifest(
        status=current.status,
        version=current.version,
        run_id=current.run_id,
        steps_ran=steps,
        created_at=current.created_at,
        updated_at=current.updated_at,
    )
    _write_manifest(ctx, updated)
    return updated


def load_or_recover_manifest(ctx: RunContext) -> Manifest:
    path = _manifest_path(ctx)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return _dict_to_manifest(cast("dict[str, Any]", data))
        except json.JSONDecodeError:
            pass
    log_root = Path(ctx.tmpdir) / "larch-logs" / "implement"
    if log_root.is_dir():
        for child in sorted(log_root.iterdir()):
            if child.is_dir():
                return Manifest(
                    status=config.MANIFEST_STATUS_PARTIAL,
                    version="1",
                    run_id=child.name,
                    steps_ran={"recovered": True},
                )
    return init_run(ctx)


def _write_manifest(ctx: RunContext, manifest: Manifest) -> None:
    _atomic_write(
        _manifest_path(ctx),
        json.dumps(_manifest_to_dict(manifest), indent=2, sort_keys=True) + "\n",
    )


def _pre_push_probe(ctx: RunContext) -> RefreshSkip:
    if not ctx.state_file:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_STATE_FILE_MISSING)
    merge_result = _read_state_kv(ctx.state_file, "MERGE_RESULT")
    if merge_result in config.POST_MERGE_MERGE_RESULTS:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_POST_MERGE)
    run_id = _read_state_kv(ctx.state_file, "RUN_ID")
    if not run_id:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_RUN_ID)
    if not validate_run_id_slug(run_id):
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_INVALID_RUN_ID)
    if _read_state_kv(ctx.state_file, "NO_LOGS_COMMIT") == "true":
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_LOGS_COMMIT)
    return RefreshSkip(skipped=False, reason="")


def flush_logs_pre(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> RefreshSkip:
    """Pre-push refresh: may git-commit log batches (caller owns push)."""
    skip = _pre_push_probe(ctx)
    if skip.skipped:
        return skip
    manifest = load_or_recover_manifest(ctx)
    log_root = Path(ctx.tmpdir) / "larch-logs"
    _render_token_timing_batches(ctx, log_root)
    _ = capture_session_transcript(ctx, defer_commit=True)
    step9a1 = _step9a1_heuristic(ctx)
    manifest = update_manifest(
        ctx,
        steps_ran={**manifest.steps_ran, "step9a1": step9a1},
    )
    _ = manifest
    commit_result = _larch_log_commit(runner, ctx, log_root, cwd=cwd)
    if commit_result.returncode != 0:
        return RefreshSkip(skipped=True, reason="commit-failed")
    return RefreshSkip(skipped=False, reason="")


def flush_logs_post(ctx: RunContext) -> RefreshSkip:
    """Post-merge tmpdir-only flush; never git-commits."""
    manifest = load_or_recover_manifest(ctx)
    log_root = Path(ctx.tmpdir) / "larch-logs"
    _render_token_timing_batches(ctx, log_root)
    done = Manifest(
        status=config.MANIFEST_STATUS_DONE,
        version=manifest.version,
        run_id=manifest.run_id,
        steps_ran=manifest.steps_ran,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
    )
    _write_manifest(ctx, done)
    return RefreshSkip(skipped=False, reason="")


def _render_token_timing_batches(ctx: RunContext, log_root: Path) -> None:
    token_path = Path(ctx.tmpdir) / "token-report-refresh.json"
    timing_path = Path(ctx.tmpdir) / "timing-report-refresh.json"
    for path in (token_path, timing_path):
        if not path.is_file():
            _ = path.write_text("{}", encoding="utf-8")
        batch_dir = log_root / "implement" / ctx.run_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        dest = batch_dir / path.name
        _ = dest.write_text(
            redact.redact(path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )


def capture_session_transcript(
    ctx: RunContext,
    *,
    defer_commit: bool = False,
) -> Path | None:
    """Write session transcript stub into tmpdir (refresh-mode parity)."""
    _ = defer_commit
    out = Path(ctx.tmpdir) / "session-transcript-refresh.txt"
    if not out.is_file():
        _ = out.write_text("", encoding="utf-8")
    return out


def _step9a1_heuristic(ctx: RunContext) -> str:
    if ctx.forked:
        return "fork-skip"
    if _read_state_kv(ctx.state_file, "FORKED_TARGET"):
        return "fork-target"
    return "default"


def _larch_log_commit(
    runner: Runner,
    ctx: RunContext,
    log_root: Path,
    *,
    cwd: str | None = None,
) -> CommandResult:
    if not log_root.exists():
        return CommandResult(("true",), 0, "", "", 0.0)
    _ = git.add(runner, "larch-logs", cwd=cwd)
    subject = f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{ctx.run_id}"
    return git.commit(runner, subject, cwd=cwd)


def path_under_repo(repo_root: Path, rel_path: str) -> bool:
    if "\x00" in rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
        return False
    try:
        resolved = (repo_root / rel_path).resolve()
        _ = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return False
    return True
