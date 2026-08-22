"""One-call Step 0 bootstrap for ``/complete-umbrella``."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from larch import io as larch_io
from larch.core import proc
from larch.core.proc import Runner
from larch.core.repo_roots import larch_entrypoint

_PLUGIN_ROOT: Final = Path(__file__).resolve().parents[2]
_SKILL: Final = "complete-umbrella"
_RUN_LEAVES_STEP: Final = "complete-umbrella-leaves"
_BOOTSTRAP_COPY: Final = "complete-umbrella-bootstrap.env"
_MODEL_COPY: Final = "model.env"
_KEY_RE: Final = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_WIRE_BREAK_RE: Final = re.compile(r"[\x00\n\r\v\f\x1c-\x1e\x85\u2028\u2029]")
_OWNER_REPO_RE: Final = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?/[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$"
)
_MODEL_RE: Final = re.compile(r"^[^\s]+$")
_CURRENT_STEPS: Final = frozenset(
    {"start", "select", "launch", "verify", "audit", "failed"}
)
_RESUME_ACTIONS: Final = frozenset({"wait", "reselect", "needs-design", "failed"})
_LIFECYCLE_KEYS: Final = (
    "RUN_ID",
    "SKILL",
    "LOG_ROOT",
    "RUN_DIR",
    "CONTEXT_FILE",
    "RUN_LOG_STORAGE",
    "RUN_LOG_STORAGE_REASON",
    "STORAGE_BASE_URI",
    "CLIENT_REPO",
    "TOOL_REPO_URI",
    "RUN_LOGS_URI",
    "STORAGE_PREFLIGHT",
    "PREFLIGHT_OK",
    "LIFECYCLE_STARTED",
)
_RESUME_KEYS: Final = (
    "RESUME_FOUND",
    "RESUME_ACTION",
    "COMPLETE_UMBRELLA_TMPDIR",
    "COMPLETE_UMBRELLA_POINTER",
    "BGJOB_STEP",
    "CURRENT_LEAF",
    "CURRENT_STEP",
    "TRANSIENT_ATTEMPT_COUNT",
    "CHILD_STATUS",
    "CHILD_FAILURE_CLASS",
    "NEXT_ACTION",
    "FAILED_STEP",
    "FAILED_LEAF",
    "FAILURE_REASON",
)


class BootstrapError(RuntimeError):
    """A named bootstrap stage failed before its postcondition held."""

    def __init__(
        self,
        stage: str,
        detail: str,
        *,
        diagnostics: str = "",
        tmpdir: Path | None = None,
    ) -> None:
        super().__init__(detail)
        self.stage = stage
        self.detail = _single_line(detail)
        self.diagnostics = diagnostics
        self.tmpdir = tmpdir


@dataclass(frozen=True)
class CommandEnvelope:
    """Captured output from one Rust-owned bootstrap stage."""

    values: Mapping[str, str]
    stdout: str
    stderr: str


@dataclass(frozen=True)
class BootstrapResult:
    """Complete process output for the Python CLI boundary."""

    exit_code: int
    stdout: str
    stderr: str


def _single_line(value: str) -> str:
    sanitized: str = _WIRE_BREAK_RE.sub(" ", value)
    collapsed: str = " ".join(sanitized.split())
    return collapsed[:500] or "stage failed"


def _require_wire_value(value: str, *, key: str, stage: str) -> str:
    if _WIRE_BREAK_RE.search(value) is not None:
        raise BootstrapError(stage, f"invalid line break in {key}")
    return value


def _parse_envelope(*, stage: str, stdout: str, stderr: str) -> CommandEnvelope:
    if _WIRE_BREAK_RE.search(stdout.replace("\n", "")) is not None:
        raise BootstrapError(
            stage,
            "invalid line break in machine stdout",
            diagnostics=stderr,
        )
    parsed: dict[str, list[str]] = larch_io.parse_kv(
        stdout,
        duplicate_policy="all",
        key_pattern=_KEY_RE,
        cr_strip="none",
    )
    source_row_count: int = sum(bool(line) for line in stdout.split("\n"))
    parsed_row_count: int = sum(len(values) for values in parsed.values())
    if parsed_row_count != source_row_count:
        raise BootstrapError(
            stage,
            "malformed non-KV stdout",
            diagnostics=stderr,
        )
    duplicates: list[str] = sorted(key for key, values in parsed.items() if len(values) != 1)
    if duplicates:
        raise BootstrapError(
            stage,
            f"duplicate machine key(s): {', '.join(duplicates)}",
            diagnostics=stderr,
        )
    values: dict[str, str] = {key: items[0] for key, items in parsed.items()}
    return CommandEnvelope(values=values, stdout=stdout, stderr=stderr)


def _capture_command(
    runner: Runner,
    *,
    stage: str,
    argv: Sequence[str],
    repo_root: Path,
    environ: Mapping[str, str],
) -> proc.CommandResult:
    if any("\x00" in argument for argument in argv):
        raise BootstrapError(stage, "command argument contains a NUL byte")
    try:
        result: proc.CommandResult = runner.run(
            argv,
            cwd=str(repo_root),
            env=environ,
        )
    except OSError as exc:
        raise BootstrapError(stage, str(exc)) from exc
    return result


def _command_failure(*, stage: str, result: proc.CommandResult) -> BootstrapError:
    detail: str = result.stderr or result.stdout or f"command exited {result.returncode}"
    return BootstrapError(stage, detail, diagnostics=result.stderr)


def _run_command(
    runner: Runner,
    *,
    stage: str,
    argv: Sequence[str],
    repo_root: Path,
    environ: Mapping[str, str],
) -> proc.CommandResult:
    result: proc.CommandResult = _capture_command(
        runner,
        stage=stage,
        argv=argv,
        repo_root=repo_root,
        environ=environ,
    )
    if result.returncode != 0:
        raise _command_failure(stage=stage, result=result)
    return result


def _run_stage(
    runner: Runner,
    *,
    stage: str,
    argv: Sequence[str],
    repo_root: Path,
    environ: Mapping[str, str],
) -> CommandEnvelope:
    result: proc.CommandResult = _run_command(
        runner,
        stage=stage,
        argv=argv,
        repo_root=repo_root,
        environ=environ,
    )
    return _parse_envelope(stage=stage, stdout=result.stdout, stderr=result.stderr)


def _require_key(values: Mapping[str, str], key: str, *, stage: str) -> str:
    if key not in values:
        raise BootstrapError(stage, f"missing {key}")
    return values[key]


def _require_nonempty(values: Mapping[str, str], key: str, *, stage: str) -> str:
    value: str = _require_key(values, key, stage=stage)
    if not value:
        raise BootstrapError(stage, f"empty {key}")
    return value


def _require_uint(value: str, *, key: str, positive: bool = False, stage: str) -> int:
    if not value.isascii() or not value.isdigit():
        raise BootstrapError(stage, f"invalid {key}")
    try:
        parsed: int = int(value, 10)
    except ValueError as exc:
        raise BootstrapError(stage, f"invalid {key}") from exc
    if positive and parsed == 0:
        raise BootstrapError(stage, f"invalid {key}")
    return parsed


def _validate_lifecycle(envelope: CommandEnvelope) -> None:
    stage: str = "lifecycle-start"
    for key in _LIFECYCLE_KEYS:
        _ = _require_key(envelope.values, key, stage=stage)
    for key in ("RUN_ID", "LOG_ROOT", "RUN_DIR", "CONTEXT_FILE", "CLIENT_REPO"):
        _ = _require_nonempty(envelope.values, key, stage=stage)
    if envelope.values["SKILL"] != _SKILL:
        raise BootstrapError(stage, "lifecycle start returned the wrong SKILL")
    if envelope.values["LIFECYCLE_STARTED"] != "true" or envelope.values["PREFLIGHT_OK"] != "true":
        raise BootstrapError(stage, "lifecycle start did not report success")
    storage_pair: tuple[str, str] = (
        envelope.values["RUN_LOG_STORAGE"],
        envelope.values["STORAGE_PREFLIGHT"],
    )
    if storage_pair not in {
        ("enabled", "ok"),
        ("disabled", "skipped-disabled"),
    }:
        raise BootstrapError(stage, "lifecycle start returned an invalid storage state")


def _validated_repo_root(environ: Mapping[str, str]) -> Path:
    project_dir: str = environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        raise BootstrapError("repository-root", "CLAUDE_PROJECT_DIR is required")
    _ = _require_wire_value(
        project_dir,
        key="CLAUDE_PROJECT_DIR",
        stage="repository-root",
    )
    try:
        root: Path = Path(project_dir).resolve(strict=True)
    except OSError as exc:
        raise BootstrapError("repository-root", str(exc)) from exc
    if not root.is_dir():
        raise BootstrapError("repository-root", "CLAUDE_PROJECT_DIR is not a directory")
    _ = _require_wire_value(str(root), key="REPO_ROOT", stage="repository-root")
    return root


def _validated_owner_pid(environ: Mapping[str, str], *, fallback_pid: int) -> int:
    raw: str = environ.get("LARCH_CLAUDE_PID") or environ.get("CLAUDE_PID") or str(fallback_pid)
    return _require_uint(raw, key="CLAUDE_PID", positive=True, stage="owner-pid")


def _validated_repository(stdout: str) -> str:
    repository: str = stdout.removesuffix("\n")
    _ = _require_wire_value(repository, key="REPO", stage="repository-resolve")
    if _OWNER_REPO_RE.fullmatch(repository) is None:
        raise BootstrapError("repository-resolve", "repository must use exact OWNER/REPO syntax")
    return repository


def _validated_tmpdir(raw: str, *, stage: str) -> Path:
    _ = _require_wire_value(raw, key="SESSION_TMPDIR", stage=stage)
    path: Path = Path(raw)
    if not path.is_absolute():
        raise BootstrapError(stage, "session tmpdir must be absolute")
    try:
        return larch_io.validate_trusted_directory(path)
    except OSError as exc:
        raise BootstrapError(stage, str(exc)) from exc


def _validate_pointer(raw: str, *, stage: str) -> str:
    _ = _require_wire_value(raw, key="COMPLETE_UMBRELLA_POINTER", stage=stage)
    path: Path = Path(raw)
    if not path.is_absolute():
        raise BootstrapError(stage, "run pointer must be absolute")
    try:
        larch_io.assert_no_symlink_path_or_ancestors(path)
        mode: int = path.lstat().st_mode
    except OSError as exc:
        raise BootstrapError(stage, f"run pointer is unavailable: {exc}") from exc
    if not stat.S_ISREG(mode):
        raise BootstrapError(stage, "run pointer is not a regular file")
    return str(path)


def _validate_resume(envelope: CommandEnvelope) -> str:
    stage: str = "resume"
    found: str = _require_key(envelope.values, "RESUME_FOUND", stage=stage)
    if found == "false":
        return found
    if found != "true":
        raise BootstrapError(stage, "invalid RESUME_FOUND")
    action: str = _require_key(envelope.values, "RESUME_ACTION", stage=stage)
    if action not in _RESUME_ACTIONS:
        raise BootstrapError(stage, "invalid RESUME_ACTION")
    _ = _validated_tmpdir(
        _require_nonempty(envelope.values, "COMPLETE_UMBRELLA_TMPDIR", stage=stage),
        stage=stage,
    )
    _ = _validate_pointer(
        _require_nonempty(envelope.values, "COMPLETE_UMBRELLA_POINTER", stage=stage),
        stage=stage,
    )
    if _require_key(envelope.values, "BGJOB_STEP", stage=stage) != _RUN_LEAVES_STEP:
        raise BootstrapError(stage, "invalid BGJOB_STEP")
    current_step: str = _require_key(envelope.values, "CURRENT_STEP", stage=stage)
    if current_step not in _CURRENT_STEPS:
        raise BootstrapError(stage, "invalid CURRENT_STEP")
    _ = _require_uint(
        _require_key(envelope.values, "CURRENT_LEAF", stage=stage),
        key="CURRENT_LEAF",
        stage=stage,
    )
    _ = _require_uint(
        _require_key(envelope.values, "TRANSIENT_ATTEMPT_COUNT", stage=stage),
        key="TRANSIENT_ATTEMPT_COUNT",
        stage=stage,
    )
    if action in {"needs-design", "failed"}:
        expected_next: str = "needs-design" if action == "needs-design" else "failed"
        if _require_key(envelope.values, "NEXT_ACTION", stage=stage) != expected_next:
            raise BootstrapError(stage, "invalid NEXT_ACTION")
        _ = _require_nonempty(envelope.values, "FAILED_STEP", stage=stage)
        _ = _require_uint(
            _require_key(envelope.values, "FAILED_LEAF", stage=stage),
            key="FAILED_LEAF",
            stage=stage,
        )
        _ = _require_nonempty(envelope.values, "FAILURE_REASON", stage=stage)
    return found


def _validate_start(envelope: CommandEnvelope, *, issue: int, tmpdir: Path) -> str:
    stage: str = "start"
    if _require_key(envelope.values, "UMBRELLA_STARTED", stage=stage) != "true":
        raise BootstrapError(stage, "start did not report UMBRELLA_STARTED=true")
    started_issue: int = _require_uint(
        _require_key(envelope.values, "UMBRELLA_ISSUE", stage=stage),
        key="UMBRELLA_ISSUE",
        positive=True,
        stage=stage,
    )
    if started_issue != issue:
        raise BootstrapError(stage, "start returned the wrong umbrella issue")
    started_tmpdir: Path = _validated_tmpdir(
        _require_nonempty(envelope.values, "COMPLETE_UMBRELLA_TMPDIR", stage=stage),
        stage=stage,
    )
    if started_tmpdir != tmpdir:
        raise BootstrapError(stage, "start returned a different session tmpdir")
    return _validate_pointer(
        _require_nonempty(envelope.values, "COMPLETE_UMBRELLA_POINTER", stage=stage),
        stage=stage,
    )


def _setup_session(
    runner: Runner,
    *,
    entrypoint: Path,
    repo_root: Path,
    environ: Mapping[str, str],
) -> tuple[Path, str]:
    stage: str = "session-setup"
    result: proc.CommandResult = _capture_command(
        runner,
        stage=stage,
        argv=[
            str(entrypoint),
            "session",
            "setup",
            "--prefix",
            "claude-complete-umbrella",
            "--skip-preflight",
            "--skip-branch-check",
            "--skip-repo-check",
        ],
        repo_root=repo_root,
        environ=environ,
    )
    envelope: CommandEnvelope = _parse_envelope(
        stage=stage,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    if result.returncode != 0:
        raw_tmpdir: str = envelope.values.get("SESSION_TMPDIR", "")
        published_tmpdir: Path | None = (
            _validated_tmpdir(raw_tmpdir, stage=stage) if raw_tmpdir else None
        )
        failure: BootstrapError = _command_failure(stage=stage, result=result)
        raise BootstrapError(
            failure.stage,
            failure.detail,
            diagnostics=failure.diagnostics,
            tmpdir=published_tmpdir,
        )
    tmpdir: Path = _validated_tmpdir(
        _require_nonempty(envelope.values, "SESSION_TMPDIR", stage=stage),
        stage=stage,
    )
    return tmpdir, envelope.stderr


def _activate_write_sentinel(environ: Mapping[str, str], *, owner_pid: int) -> Path:
    xdg_cache: str = environ.get("XDG_CACHE_HOME", "")
    home: str = environ.get("HOME", "")
    if not xdg_cache and not home:
        raise BootstrapError(
            "write-hook",
            "XDG_CACHE_HOME and HOME are unset",
        )
    base_text: str = xdg_cache or home
    _ = _require_wire_value(
        base_text,
        key="XDG_CACHE_HOME" if xdg_cache else "HOME",
        stage="write-hook",
    )
    base: Path = Path(xdg_cache) if xdg_cache else Path(home) / ".cache"
    try:
        directory: Path = larch_io.ensure_trusted_directory(
            base / "larch" / "deny-edit-write-active",
            mode=0o700,
        )
        sentinel: Path = directory / f"complete-umbrella-{owner_pid}"
        larch_io.trusted_atomic_write(sentinel, "", root=directory, mode=0o600)
    except OSError as exc:
        raise BootstrapError("write-hook", str(exc)) from exc
    _ = _require_wire_value(
        str(sentinel),
        key="COMPLETE_UMBRELLA_WRITE_SENTINEL",
        stage="write-hook",
    )
    return sentinel


def _validated_model(text: str, *, stage: str) -> str:
    envelope: CommandEnvelope = _parse_envelope(stage=stage, stdout=text, stderr="")
    model: str = _require_nonempty(envelope.values, "CLAUDE_MODEL", stage=stage)
    if model == "unknown" or _MODEL_RE.fullmatch(model) is None:
        raise BootstrapError(stage, "invalid CLAUDE_MODEL")
    return model


def _model_for_run(
    runner: Runner,
    *,
    entrypoint: Path,
    repo_root: Path,
    tmpdir: Path,
    environ: Mapping[str, str],
) -> tuple[str, str]:
    model_path: Path = tmpdir / _MODEL_COPY
    try:
        present: bool = larch_io.trusted_file_present(model_path, root=tmpdir)
    except OSError as exc:
        raise BootstrapError("model-read", str(exc)) from exc
    if present:
        try:
            text: str = larch_io.read_trusted_text(
                model_path,
                root=tmpdir,
                reject_cr=True,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            raise BootstrapError("model-read", str(exc)) from exc
        return _validated_model(text, stage="model-read"), ""
    envelope: CommandEnvelope = _run_stage(
        runner,
        stage="model-resolve",
        argv=[str(entrypoint), "agent", "read-claude-model"],
        repo_root=repo_root,
        environ=environ,
    )
    try:
        model: str = _validated_model(envelope.stdout, stage="model-resolve")
    except BootstrapError as exc:
        raise BootstrapError(
            exc.stage,
            exc.detail,
            diagnostics=envelope.stderr,
        ) from exc
    try:
        larch_io.trusted_atomic_write(
            model_path,
            envelope.stdout,
            root=tmpdir,
            mode=0o600,
        )
    except OSError as exc:
        raise BootstrapError("model-copy", str(exc), diagnostics=envelope.stderr) from exc
    return model, envelope.stderr


def _diagnostic_copy(tmpdir: Path, text: str) -> None:
    try:
        larch_io.trusted_atomic_write(
            tmpdir / _BOOTSTRAP_COPY,
            text,
            root=tmpdir,
            mode=0o600,
        )
    except OSError as exc:
        raise BootstrapError("diagnostic-copy", str(exc)) from exc


def _failure_result(
    *,
    rows: dict[str, str],
    warnings: list[str],
    error: BootstrapError,
    tmpdir: Path | None,
) -> BootstrapResult:
    diagnostic_tmpdir: Path | None = tmpdir or error.tmpdir
    if error.tmpdir is not None:
        _ = rows.setdefault("SESSION_TMPDIR", str(error.tmpdir))
        _ = rows.setdefault("COMPLETE_UMBRELLA_TMPDIR", str(error.tmpdir))
    rows["BOOTSTRAP_OK"] = "false"
    rows["BOOTSTRAP_STAGE"] = error.stage
    rows["BOOTSTRAP_ERROR"] = error.detail
    stdout: str = larch_io.format_kvs(rows)
    if diagnostic_tmpdir is not None and error.stage != "diagnostic-copy":
        try:
            _diagnostic_copy(diagnostic_tmpdir, stdout)
        except BootstrapError as copy_error:
            warnings.append(f"complete-umbrella bootstrap diagnostic copy failed: {copy_error.detail}\n")
    if error.diagnostics:
        warnings.append(error.diagnostics)
    warnings.append(
        f"ERROR: complete-umbrella bootstrap failed at stage={error.stage}: {error.detail}\n"
    )
    return BootstrapResult(exit_code=1, stdout=stdout, stderr="".join(warnings))


def bootstrap(  # noqa: PLR0913,PLR0915 - linear stages retain partial failure state.
    runner: Runner,
    *,
    issue: int,
    operator_invoked: bool,
    lifecycle_parent_context: str,
    environ: Mapping[str, str],
    plugin_root: Path = _PLUGIN_ROOT,
    fallback_pid: int,
) -> BootstrapResult:
    """Run every Step 0 stage and return one consolidated machine envelope."""
    rows: dict[str, str] = {}
    warnings: list[str] = []
    tmpdir: Path | None = None
    try:
        if issue <= 0:
            raise BootstrapError("arguments", "--issue must be a positive integer")
        if not operator_invoked:
            raise BootstrapError("arguments", "--operator-invoked is required")
        repo_root: Path = _validated_repo_root(environ)
        owner_pid: int = _validated_owner_pid(environ, fallback_pid=fallback_pid)
        entrypoint: Path = larch_entrypoint(plugin_root, use_env=False)
        child_env: dict[str, str] = dict(environ)
        child_env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

        lifecycle_argv: list[str] = [
            str(entrypoint),
            "run-log",
            "lifecycle-start",
            "--repo-root",
            str(repo_root),
            "--skill",
            _SKILL,
        ]
        if lifecycle_parent_context:
            lifecycle_argv.extend(
                ["--lifecycle-parent-context", lifecycle_parent_context]
            )
        lifecycle: CommandEnvelope = _run_stage(
            runner,
            stage="lifecycle-start",
            argv=lifecycle_argv,
            repo_root=repo_root,
            environ=child_env,
        )
        warnings.append(lifecycle.stderr)
        _validate_lifecycle(lifecycle)
        for key in _LIFECYCLE_KEYS:
            rows[key] = lifecycle.values[key]

        repository_result: proc.CommandResult = _run_command(
            runner,
            stage="repository-resolve",
            argv=[str(entrypoint), "gh", "resolve-repo"],
            repo_root=repo_root,
            environ=child_env,
        )
        warnings.append(repository_result.stderr)
        repository: str = _validated_repository(repository_result.stdout)
        rows["REPO_ROOT"] = str(repo_root)
        rows["REPO"] = repository
        rows["UMBRELLA"] = str(issue)
        rows["COMPLETE_UMBRELLA_OWNER_PID"] = str(owner_pid)

        resume: CommandEnvelope = _run_stage(
            runner,
            stage="resume",
            argv=[
                str(entrypoint),
                "complete-umbrella",
                "resume",
                "--repository",
                repository,
                "--issue",
                str(issue),
                "--claude-pid",
                str(owner_pid),
                "--operator-invoked",
            ],
            repo_root=repo_root,
            environ=child_env,
        )
        warnings.append(resume.stderr)
        resume_found: str = _validate_resume(resume)
        rows["RESUME_FOUND"] = resume_found
        if resume_found == "true":
            for key in _RESUME_KEYS[1:]:
                if key in resume.values:
                    rows[key] = resume.values[key]
            tmpdir = _validated_tmpdir(
                rows["COMPLETE_UMBRELLA_TMPDIR"],
                stage="resume",
            )
        else:
            tmpdir, setup_stderr = _setup_session(
                runner,
                entrypoint=entrypoint,
                repo_root=repo_root,
                environ=child_env,
            )
            warnings.append(setup_stderr)
            rows["SESSION_TMPDIR"] = str(tmpdir)
            rows["COMPLETE_UMBRELLA_TMPDIR"] = str(tmpdir)
            start: CommandEnvelope = _run_stage(
                runner,
                stage="start",
                argv=[
                    str(entrypoint),
                    "complete-umbrella",
                    "start",
                    "--repository",
                    repository,
                    "--issue",
                    str(issue),
                    "--tmpdir",
                    str(tmpdir),
                    "--claude-pid",
                    str(owner_pid),
                    "--operator-invoked",
                ],
                repo_root=repo_root,
                environ=child_env,
            )
            warnings.append(start.stderr)
            rows["RESUME_ACTION"] = "reselect"
            rows["COMPLETE_UMBRELLA_TMPDIR"] = str(tmpdir)
            rows["COMPLETE_UMBRELLA_POINTER"] = _validate_start(
                start,
                issue=issue,
                tmpdir=tmpdir,
            )
            rows["BGJOB_STEP"] = _RUN_LEAVES_STEP
            rows["CURRENT_LEAF"] = "0"
            rows["CURRENT_STEP"] = "select"
            rows["TRANSIENT_ATTEMPT_COUNT"] = "0"

        rows["UMBRELLA_STARTED"] = "true"
        rows["SESSION_TMPDIR"] = str(tmpdir)
        sentinel: Path = _activate_write_sentinel(child_env, owner_pid=owner_pid)
        rows["COMPLETE_UMBRELLA_WRITE_SENTINEL"] = str(sentinel)

        action: str = rows["RESUME_ACTION"]
        if action in {"wait", "reselect"}:
            model, model_stderr = _model_for_run(
                runner,
                entrypoint=entrypoint,
                repo_root=repo_root,
                tmpdir=tmpdir,
                environ=child_env,
            )
            warnings.append(model_stderr)
            rows["CLAUDE_MODEL"] = model
        else:
            rows["CLAUDE_MODEL"] = ""

        rows["BOOTSTRAP_OK"] = "true"
        stdout: str = larch_io.format_kvs(rows)
        _diagnostic_copy(tmpdir, stdout)
        return BootstrapResult(exit_code=0, stdout=stdout, stderr="".join(warnings))
    except BootstrapError as error:
        return _failure_result(
            rows=rows,
            warnings=warnings,
            error=error,
            tmpdir=tmpdir,
        )


def bootstrap_main(argv: list[str]) -> int:
    """CLI entrypoint for ``complete-umbrella bootstrap``."""
    parser = argparse.ArgumentParser(prog="cli.py complete-umbrella bootstrap")
    _ = parser.add_argument("--issue", type=int, required=True)
    _ = parser.add_argument("--lifecycle-parent-context", default="")
    _ = parser.add_argument("--operator-invoked", action="store_true")
    args = parser.parse_args(argv)
    result: BootstrapResult = bootstrap(
        proc,
        issue=args.issue,
        operator_invoked=args.operator_invoked,
        lifecycle_parent_context=args.lifecycle_parent_context,
        environ=os.environ,
        fallback_pid=os.getppid(),
    )
    _ = sys.stdout.write(result.stdout)
    _ = sys.stderr.write(result.stderr)
    return result.exit_code
