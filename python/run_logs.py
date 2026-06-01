"""larch-log manifest lifecycle and split flush entrypoints."""

from __future__ import annotations

import json
import os
import re
import shutil
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


def effective_run_id(ctx: RunContext) -> str:
    """Prefer validated state-file RUN_ID over ctx.run_id for log paths."""
    state_run_id = _read_state_kv(ctx.state_file, "RUN_ID")
    if state_run_id and validate_run_id_slug(state_run_id):
        return state_run_id
    return ctx.run_id


def _manifest_path(ctx: RunContext) -> Path:
    run_id = effective_run_id(ctx)
    return Path(ctx.tmpdir) / "larch-logs" / "implement" / run_id / "manifest.json"


def _run_log_dir(ctx: RunContext) -> Path:
    return Path(ctx.tmpdir) / "larch-logs" / "implement" / effective_run_id(ctx)


def init_run(
    ctx: RunContext,
    *,
    run_id: str | None = None,
) -> Manifest:
    rid = run_id or effective_run_id(ctx)
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


def _newest_run_child(log_root: Path) -> Path | None:
    candidates = [child for child in log_root.iterdir() if child.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_or_recover_manifest(ctx: RunContext) -> Manifest:
    candidates: list[Path] = []
    primary = _manifest_path(ctx)
    candidates.append(primary)
    if validate_run_id_slug(ctx.run_id):
        alt = Path(ctx.tmpdir) / "larch-logs" / "implement" / ctx.run_id / "manifest.json"
        if alt not in candidates:
            candidates.append(alt)
    state_run_id = _read_state_kv(ctx.state_file, "RUN_ID")
    if state_run_id and validate_run_id_slug(state_run_id):
        state_path = (
            Path(ctx.tmpdir) / "larch-logs" / "implement" / state_run_id / "manifest.json"
        )
        if state_path not in candidates:
            candidates.append(state_path)
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return _dict_to_manifest(cast("dict[str, Any]", data))
            except json.JSONDecodeError:
                pass
    log_root = Path(ctx.tmpdir) / "larch-logs" / "implement"
    newest = _newest_run_child(log_root) if log_root.is_dir() else None
    if newest is not None:
        return Manifest(
            status=config.MANIFEST_STATUS_PARTIAL,
            version="1",
            run_id=newest.name,
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


def _render_execution_issues_batch(ctx: RunContext, batch_dir: Path) -> None:
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    batch_path = batch_dir / "execution-issues.ndjson"
    if not issue_log.is_file():
        return
    if batch_path.is_file():
        return
    _ = batch_path.write_text("", encoding="utf-8")


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
    run_dir = _run_log_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    _render_execution_issues_batch(ctx, run_dir)
    _render_token_timing_batches(ctx, log_root)
    _ = capture_session_transcript(ctx, defer_commit=True)
    step9a1 = _step9a1_heuristic(ctx)
    _ = update_manifest(
        ctx,
        steps_ran={**manifest.steps_ran, "step9a1": step9a1},
    )
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
    run_id = effective_run_id(ctx)
    token_path = Path(ctx.tmpdir) / "token-report-refresh.json"
    timing_path = Path(ctx.tmpdir) / "timing-report-refresh.json"
    for path in (token_path, timing_path):
        if not path.is_file():
            _ = path.write_text("{}", encoding="utf-8")
        batch_dir = log_root / "implement" / run_id
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
    run_dir = _run_log_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    dest = run_dir / "session-transcript-refresh.txt"
    if not dest.is_file():
        _ = dest.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    return out


def _step9a1_heuristic(ctx: RunContext) -> str:
    if ctx.forked:
        return "fork-skip"
    if _read_state_kv(ctx.state_file, "FORKED_TARGET"):
        return "fork-target"
    return "default"


def _publish_run_tree_to_repo(
    ctx: RunContext,
    log_root: Path,
    *,
    cwd: str | None,
) -> str:
    """Copy tmpdir run tree into repo larch-logs (larch-log.sh commit parity)."""
    run_id = effective_run_id(ctx)
    if not validate_run_id_slug(run_id):
        return ""
    src = log_root / "implement" / run_id
    if not src.is_dir():
        return ""
    if cwd is None:
        return f"larch-logs/implement/{run_id}"
    repo_root = Path(cwd)
    dest = repo_root / "larch-logs" / "implement" / run_id
    if src.resolve() != dest.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        _ = shutil.copytree(src, dest)
    return f"larch-logs/implement/{run_id}"


def _larch_log_commit(
    runner: Runner,
    ctx: RunContext,
    log_root: Path,
    *,
    cwd: str | None = None,
) -> CommandResult:
    rel = _publish_run_tree_to_repo(ctx, log_root, cwd=cwd)
    if not rel:
        return CommandResult(("true",), 0, "", "", 0.0)
    status = git.status_porcelain_paths(runner, rel, cwd=cwd)
    if status.returncode != 0:
        return status
    if not status.stdout.strip():
        return CommandResult(("true",), 0, "", "", 0.0)
    _ = git.add(runner, rel, cwd=cwd)
    if git.diff_quiet(runner, rel, cached=True, cwd=cwd):
        return CommandResult(("true",), 0, "", "", 0.0)
    subject = f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{effective_run_id(ctx)}"
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
