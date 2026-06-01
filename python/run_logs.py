"""larch-log manifest lifecycle and split flush entrypoints."""

from __future__ import annotations

import hashlib
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
import tokens
from errors import ShipError
from proc import CommandResult, Runner
from run_context import RunContext

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WRITE_FINAL_REPORT = (
    _REPO_ROOT / "skills" / "implement" / "scripts" / "write-final-report.sh"
)
_CAPTURE_SESSION_TRANSCRIPT = _REPO_ROOT / "scripts" / "capture-session-transcript.sh"
_TOKEN_REPORT = _REPO_ROOT / "scripts" / "token-report.sh"
_TIMING_REPORT = _REPO_ROOT / "scripts" / "timing-report.sh"
_LARCH_LOG = _REPO_ROOT / "scripts" / "larch-log.sh"

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


def read_state_kv(state_file: str | None, key: str) -> str:
    """Read a single KEY=value from an implement state file."""
    return _read_state_kv(state_file, key)


def _read_state_kv(state_file: str | None, key: str) -> str:
    if not state_file or not Path(state_file).is_file():
        return ""
    try:
        text = Path(state_file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    for line in text.splitlines():
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name == key:
            return value
    return ""


def _read_session_env_key(ctx: RunContext, key: str) -> str:
    path = Path(ctx.tmpdir) / "session-env.sh"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    for line in text.splitlines():
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name == key:
            return value
    return ""


def _report_subprocess_env(ctx: RunContext) -> dict[str, str]:
    env = dict(os.environ)
    env["IMPLEMENT_TMPDIR"] = ctx.tmpdir
    for export_key, file_key in (
        ("LARCH_TOKEN_SESSION_ID", "LARCH_TOKEN_SESSION_ID"),
        ("LARCH_CLAUDE_SOURCE_FILE", "LARCH_CLAUDE_SOURCE_FILE"),
        ("LARCH_TIMING_LEDGER", "LARCH_TIMING_LEDGER"),
    ):
        value = _read_session_env_key(ctx, file_key)
        if value:
            env[export_key] = value
    return env


def _render_ledger_reports(runner: Runner, ctx: RunContext, log_root: Path) -> None:
    """Re-render token/timing JSON from ledgers (refresh-run-logs.sh parity)."""
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    tmpdir = Path(ctx.tmpdir)
    token_path = tmpdir / "token-report-refresh.json"
    timing_path = tmpdir / "timing-report-refresh.json"
    env = _report_subprocess_env(ctx)
    if _TOKEN_REPORT.is_file():
        _ = runner.run(
            [
                "bash",
                str(_TOKEN_REPORT),
                "--full",
                "--format",
                "json",
                "--output",
                str(token_path),
            ],
            cwd=str(_REPO_ROOT),
            env=env,
        )
    if _LARCH_LOG.is_file() and token_path.is_file():
        _ = runner.run(
            [
                "bash",
                str(_LARCH_LOG),
                "write",
                "--log-root",
                str(log_root),
                "--skill",
                "implement",
                "--run-id",
                run_id,
                "--batch",
                "token-report",
                "--input-file",
                str(token_path),
            ],
            cwd=str(_REPO_ROOT),
            env=env,
        )
    if _TIMING_REPORT.is_file():
        _ = runner.run(
            [
                "bash",
                str(_TIMING_REPORT),
                "--full",
                "--format",
                "json",
                "--output",
                str(timing_path),
            ],
            cwd=str(_REPO_ROOT),
            env=env,
        )
    if _LARCH_LOG.is_file() and timing_path.is_file():
        _ = runner.run(
            [
                "bash",
                str(_LARCH_LOG),
                "write",
                "--log-root",
                str(log_root),
                "--skill",
                "implement",
                "--run-id",
                run_id,
                "--batch",
                "timing-report",
                "--input-file",
                str(timing_path),
            ],
            cwd=str(_REPO_ROOT),
            env=env,
        )


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
    status = current.status
    version = current.version
    run_id = current.run_id
    created_at = current.created_at
    updated_at = current.updated_at
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
    updated = Manifest(
        status=status,
        version=version,
        run_id=run_id,
        steps_ran=steps,
        created_at=created_at,
        updated_at=updated_at,
    )
    _write_manifest(ctx, updated)
    return updated


def _newest_run_child(log_root: Path) -> Path | None:
    candidates = [child for child in log_root.iterdir() if child.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _recover_manifest_from_run_dir(run_id: str, run_dir: Path) -> Manifest | None:
    if not run_dir.is_dir():
        return None
    steps: dict[str, Any] = {"recovered": True}
    if (run_dir / "execution-issues.ndjson").is_file():
        steps["execution_issues"] = True
    if (run_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson").is_file():
        steps["token_report"] = True
    return Manifest(
        status=config.MANIFEST_STATUS_PARTIAL,
        version="1",
        run_id=run_id,
        steps_ran=steps,
    )


def load_or_recover_manifest(ctx: RunContext) -> Manifest:
    rid = effective_run_id(ctx)
    if rid:
        primary = Path(ctx.tmpdir) / "larch-logs" / "implement" / rid / "manifest.json"
        run_dir = primary.parent
        if primary.is_file():
            try:
                data = json.loads(primary.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return _dict_to_manifest(cast("dict[str, Any]", data))
            except json.JSONDecodeError:
                recovered = _recover_manifest_from_run_dir(rid, run_dir)
                if recovered is not None:
                    _write_manifest(ctx, recovered)
                    return recovered
        elif run_dir.is_dir():
            recovered = _recover_manifest_from_run_dir(rid, run_dir)
            if recovered is not None:
                _write_manifest(ctx, recovered)
                return recovered
        return init_run(ctx, run_id=rid)
    log_root = Path(ctx.tmpdir) / "larch-logs" / "implement"
    if validate_run_id_slug(ctx.run_id):
        preferred = log_root / ctx.run_id
        if preferred.is_dir():
            recovered = _recover_manifest_from_run_dir(ctx.run_id, preferred)
            if recovered is not None:
                _write_manifest(ctx, recovered)
                return recovered
    newest = _newest_run_child(log_root) if log_root.is_dir() else None
    if (
        newest is not None
        and validate_run_id_slug(newest.name)
        and (
            not validate_run_id_slug(ctx.run_id)
            or newest.name == ctx.run_id
        )
    ):
        recovered_path = newest / "manifest.json"
        if recovered_path.is_file():
            try:
                data = json.loads(recovered_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    manifest = _dict_to_manifest(cast("dict[str, Any]", data))
                    if manifest.run_id == newest.name:
                        return manifest
            except json.JSONDecodeError:
                pass
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


def _write_final_report(runner: Runner, ctx: RunContext) -> None:
    if not _WRITE_FINAL_REPORT.is_file():
        return
    _ = runner.run(
        ["bash", str(_WRITE_FINAL_REPORT), "--implement-tmpdir", ctx.tmpdir],
        cwd=str(_REPO_ROOT),
    )


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
    _render_execution_issues_batch(
        ctx,
        run_dir,
        step_label="pre-push",
        source_label="execution-issues.md pre-push refresh",
    )
    _write_final_report(runner, ctx)
    _render_ledger_reports(runner, ctx, log_root)
    _render_token_timing_batches(ctx, log_root)
    _ = capture_session_transcript(ctx, runner, defer_commit=True)
    _render_execution_issues_batch(
        ctx,
        run_dir,
        step_label="pre-push-post-transcript",
        source_label="execution-issues.md post-transcript refresh",
    )
    step9a1 = _step9a1_heuristic(ctx)
    steps_update = dict(manifest.steps_ran)
    if step9a1 is not None:
        steps_update["step9a1"] = step9a1
    _ = update_manifest(ctx, steps_ran=steps_update)
    if cwd is None:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_REPO_CWD)
    commit_result = _larch_log_commit(runner, ctx, log_root, cwd=cwd)
    if commit_result.returncode != 0:
        return RefreshSkip(skipped=True, reason="commit-failed")
    return RefreshSkip(skipped=False, reason="")


def flush_logs_post(
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RefreshSkip:
    """Post-merge tmpdir-only flush; never git-commits."""
    manifest = load_or_recover_manifest(ctx)
    log_root = Path(ctx.tmpdir) / "larch-logs"
    if runner is not None:
        _write_final_report(runner, ctx)
    try:
        if runner is not None:
            _render_ledger_reports(runner, ctx, log_root)
        _render_token_timing_batches(ctx, log_root)
    except ShipError:
        return RefreshSkip(skipped=True, reason="redaction-failed")
    resolved = merge_result or _read_state_kv(ctx.state_file, "MERGE_RESULT")
    finalize = resolved in config.POST_MERGE_MERGE_RESULTS
    updated = Manifest(
        status=config.MANIFEST_STATUS_DONE if finalize else manifest.status,
        version=manifest.version,
        run_id=manifest.run_id,
        steps_ran=manifest.steps_ran,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
    )
    _write_manifest(ctx, updated)
    return RefreshSkip(skipped=False, reason="")


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
    for path in (token_path, timing_path):
        if not path.is_file():
            _ = path.write_text("{}", encoding="utf-8")
    batch_dir = log_root / "implement" / run_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    sidecars: list[tuple[str, Path]] = list(_token_sidecar_paths(tmpdir))
    if token_path.is_file():
        sidecars.append(("refresh", token_path))
    timing_sidecars: list[tuple[str, Path]] = list(_timing_sidecar_paths(tmpdir))
    if timing_path.is_file():
        timing_sidecars.append(("refresh", timing_path))
    _ = tokens.scrape_run(
        sidecar_paths=tuple(sidecars),
        timing_sidecar_paths=tuple(timing_sidecars),
        output_path=batch_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson",
        timing_output_path=batch_dir / f"{config.RUN_LOG_BATCH_TIMING_REPORT}.ndjson",
    )
    for path in (token_path, timing_path):
        dest = batch_dir / path.name
        _ = dest.write_text(
            _redact_batch_payload(path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )


def capture_session_transcript(
    ctx: RunContext,
    runner: Runner,
    *,
    defer_commit: bool = False,
) -> Path | None:
    """Copy refresh transcript into run tree with redaction (defer-commit parity)."""
    run_id = effective_run_id(ctx)
    if not run_id:
        return None
    log_root = Path(ctx.tmpdir) / "larch-logs"
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    source = os.environ.get("LARCH_CLAUDE_SOURCE_FILE", "")
    no_logs = _read_state_kv(ctx.state_file, "NO_LOGS_COMMIT") or "false"
    if _CAPTURE_SESSION_TRANSCRIPT.is_file():
        _ = runner.run(
            [
                "bash",
                str(_CAPTURE_SESSION_TRANSCRIPT),
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
            ],
            cwd=str(_REPO_ROOT),
        )
    out = Path(ctx.tmpdir) / "session-transcript-refresh.txt"
    run_dir = _run_log_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    dest = run_dir / "session-transcript-refresh.txt"
    if out.is_file() and out.stat().st_size > 0:
        raw = out.read_text(encoding="utf-8")
        if raw.strip():
            _ = dest.write_text(_redact_batch_payload(raw), encoding="utf-8")
    elif dest.is_file() and dest.stat().st_size > 0:
        pass
    elif not dest.is_file():
        _ = dest.write_text("", encoding="utf-8")
    return out if out.is_file() else dest


def _read_finalize_kv(tmpdir: Path, key: str) -> str:
    path = tmpdir / "finalize-state.sh"
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name == key:
            return value
    return ""


def _read_run_flags_kv(tmpdir: Path, key: str) -> str:
    path = tmpdir / "run-flags.sh"
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name == key:
            return value
    return ""


def _step9a1_heuristic(ctx: RunContext) -> bool | None:
    tmpdir = Path(ctx.tmpdir)
    log_root = tmpdir / "larch-logs"
    run_id = effective_run_id(ctx)
    if not run_id:
        return None
    forked_target = _read_state_kv(ctx.state_file, "FORKED_TARGET") == "true"
    if ctx.forked or forked_target:
        return False
    design_done = _read_finalize_kv(tmpdir, "DESIGN_ONLY_DONE") == "true"
    no_issues = _read_run_flags_kv(tmpdir, "NO_ISSUES") == "true"
    if design_done and no_issues:
        return False
    run_dir = log_root / "implement" / run_id
    if (run_dir / "oos-issues.ndjson").is_file() or (run_dir / "run-statistics.md").is_file():
        return True
    return None


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
        _safe_copy_run_tree(src, dest)
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
