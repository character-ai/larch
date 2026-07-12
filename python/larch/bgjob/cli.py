"""CLI entrypoints for bgjob."""

from __future__ import annotations

import argparse
import os
import shlex
from pathlib import Path
from typing import Never

from larch.bgjob import adapt, daemon, model, registry, wait
from larch.core import config, process_identity
from larch.report.progress_file import resolve_owned_run_id, validate_run_id
from larch.state import session_env


_DESIGN_SESSION_ENV_KEYS = session_env.WRITE_DESIGN_ENV_KEYS


class _MachineArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        _ = message
        raise ValueError("invalid command arguments")


def _add_common_job_args(parser: argparse.ArgumentParser, *, tmpdir_required: bool = True) -> None:
    _ = parser.add_argument("--step", required=True)
    _ = parser.add_argument("--tmpdir", required=tmpdir_required, default="")
    _ = parser.add_argument("--run-id", default="")


def _build_spec(args: argparse.Namespace) -> model.JobSpec:
    step = model.validate_slug(str(args.step), label="step")
    tmpdir = model.checked_dir(Path(args.tmpdir), label="tmpdir")
    clone_path = Path.cwd().resolve()
    run_id = resolve_owned_run_id(explicit=str(args.run_id) or None, tmpdir=tmpdir) or model.default_run_id(
        tmpdir=tmpdir,
        clone_path=clone_path,
    )
    log_dir_arg = Path(args.log_dir) if args.log_dir else None
    log_dir, _, _ = model.log_paths(tmpdir=tmpdir, log_dir=log_dir_arg, step=step)
    sentinels = tuple(model.ensure_under(Path(raw), tmpdir, label="sentinel") for raw in args.sentinel)
    owner = daemon.owner_identity_from_env(args.owner_pid)
    merge_result_env = Path(args.merge_result_env) if args.merge_result_env else None
    if merge_result_env is not None:
        if merge_result_env.is_symlink():
            raise ValueError(f"merge-result-env must not be a symlink: {merge_result_env}")
        if merge_result_env.parent.is_symlink():
            raise ValueError(f"merge-result-env parent must not be a symlink: {merge_result_env.parent}")
    return model.JobSpec(
        step=step,
        tmpdir=tmpdir,
        log_dir=log_dir,
        budget_s=int(args.budget_s),
        command=tuple(args.command),
        run_id=run_id,
        owner=owner,
        sentinel_paths=sentinels,
        merge_result_env=merge_result_env,
    )


def start_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py bgjob start")
    _add_common_job_args(parser)
    _ = parser.add_argument("--budget-s", required=True, type=int)
    _ = parser.add_argument("--log-dir", default="")
    _ = parser.add_argument("--owner-pid", default="")
    _ = parser.add_argument("--sentinel", action="append", default=[])
    _ = parser.add_argument("--merge-result-env", default="")
    _ = parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        print("BGJOB_ERROR=missing-command")
        return 2
    if args.budget_s <= 0:
        print("BGJOB_ERROR=invalid-budget")
        return 2
    try:
        return daemon.start_daemon(_build_spec(args))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"BGJOB_ERROR={type(exc).__name__}:{exc}")
        return 2


def _adapt_parser() -> _MachineArgumentParser:
    parser = _MachineArgumentParser(prog="cli.py bgjob adapt")
    _add_common_job_args(parser, tmpdir_required=False)
    _ = parser.add_argument("--budget-s", type=int)
    _ = parser.add_argument("--log-dir", default="")
    _ = parser.add_argument("--owner-pid", default="")
    _ = parser.add_argument("--sentinel", action="append", default=[])
    _ = parser.add_argument("--session-env-path", default="")
    _ = parser.add_argument("--clear-on-fresh", default="")
    _ = parser.add_argument("--replace-completed-result", action="store_true")
    _ = parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def _adapt_contract_error(args: argparse.Namespace) -> str:
    if not args.command:
        return "missing-command"
    if args.budget_s is None:
        return "invalid-input"
    if args.budget_s <= 0:
        return "invalid-budget"
    return ""


def _adapt_tmpdir(*, args: argparse.Namespace, session_values: dict[str, str]) -> str:
    explicit = str(args.tmpdir)
    session_tmpdir = session_values.get(config.ENV_DESIGN_TMPDIR, "")
    if session_tmpdir and explicit and Path(session_tmpdir).resolve() != Path(explicit).resolve():
        raise adapt.AdaptError("session-env-tmpdir-mismatch")
    tmpdir = (
        explicit
        or session_tmpdir
        or os.environ.get(config.ENV_DESIGN_TMPDIR, "")
        or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    )
    if not tmpdir:
        raise adapt.AdaptError("missing-tmpdir")
    return tmpdir


def _prepare_adapt_args(argv: list[str] | None) -> argparse.Namespace:
    try:
        args = _adapt_parser().parse_args(argv)
    except (argparse.ArgumentError, ValueError) as exc:
        raise adapt.AdaptError("invalid-input") from exc
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    error_token = _adapt_contract_error(args)
    if error_token:
        raise adapt.AdaptError(error_token)
    session_values = (
        _resolve_session_env(
            path=Path(args.session_env_path),
            claude_pid=str(args.owner_pid),
        )
        if args.session_env_path
        else {}
    )
    for key, value in session_values.items():
        os.environ[key] = value
    args.tmpdir = _adapt_tmpdir(args=args, session_values=session_values)
    args.merge_result_env = ""
    return args


def adapt_main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv or [])
    if "--resolve-session-env" in raw_argv:
        return _resolve_session_env_argv(raw_argv)
    try:
        args = _prepare_adapt_args(argv)
        options = adapt.AdaptOptions(
            clear_on_fresh=Path(args.clear_on_fresh) if args.clear_on_fresh else None,
            replace_completed_result=bool(args.replace_completed_result),
        )
        return adapt.start_or_reattach(_build_spec(args), options=options)
    except adapt.AdaptError as exc:
        print(f"BGJOB_ERROR={exc.token}")
        return 2
    except (OSError, RuntimeError, ValueError):
        print("BGJOB_ERROR=invalid-input")
        return 2


def _session_env_source(*, path: Path, claude_pid: str) -> Path:
    if path.is_symlink():
        resolved = session_env.resolve_trusted_design_session_env_source(
            path=path,
            claude_pid=claude_pid,
        )
        if resolved is None:
            raise adapt.AdaptError("session-env-unsafe")
        return resolved
    if not path.is_file():
        raise adapt.AdaptError("session-env-missing")
    return path


def _resolve_session_env(*, path: Path, claude_pid: str) -> dict[str, str]:
    source = _session_env_source(path=path, claude_pid=claude_pid)
    try:
        text = source.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise adapt.AdaptError("session-env-unsafe") from exc
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "#!/usr/bin/env bash":
            continue
        pair = session_env.parse_allowlisted_env_line(
            raw=line,
            allowlist=_DESIGN_SESSION_ENV_KEYS,
            reject_newline_rhs=True,
        )
        if pair is None:
            raise adapt.AdaptError("session-env-malformed")
        values[pair[0]] = pair[1]
    raw_tmpdir = values.get(config.ENV_DESIGN_TMPDIR, "")
    ok, _message = session_env.validate_design_tmpdir(raw_tmpdir)
    if not raw_tmpdir:
        raise adapt.AdaptError("design-tmpdir-missing")
    if not ok or not Path(raw_tmpdir).is_dir():
        raise adapt.AdaptError("design-tmpdir-invalid")
    values[config.ENV_DESIGN_TMPDIR] = str(Path(raw_tmpdir).resolve())
    return values


def _resolve_session_env_argv(argv: list[str]) -> int:
    parser = _MachineArgumentParser(prog="cli.py bgjob adapt --resolve-session-env")
    _ = parser.add_argument("--resolve-session-env", action="store_true")
    _ = parser.add_argument("--session-env-path", default="")
    _ = parser.add_argument("--owner-pid", default="")
    try:
        args = parser.parse_args(argv)
    except (argparse.ArgumentError, ValueError):
        print("BGJOB_ERROR=invalid-input")
        return 2
    if not args.resolve_session_env or not args.session_env_path:
        print("BGJOB_ERROR=invalid-input")
        return 2
    try:
        values = _resolve_session_env(
            path=Path(args.session_env_path),
            claude_pid=str(args.owner_pid),
        )
    except adapt.AdaptError as exc:
        print(f"BGJOB_ERROR={exc.token}")
        return 2
    for key, value in values.items():
        print(f"export {key}={shlex.quote(value)}")
    return 0


def wait_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py bgjob wait")
    _add_common_job_args(parser, tmpdir_required=False)
    _ = parser.add_argument("--max-wait-s", type=int, default=config.BGJOB_WAIT_DEFAULT_CHUNK_S)
    _ = parser.add_argument("--poll-interval-s", type=float, default=1.0)
    args = parser.parse_args(argv)
    tmpdir_raw = str(args.tmpdir) or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not tmpdir_raw:
        print("BGJOB_ERROR=missing-tmpdir")
        return 2
    try:
        step = model.validate_slug(str(args.step), label="step")
        run_id = validate_run_id(str(args.run_id)) if args.run_id else None
        return wait.wait_once(
            tmpdir=Path(tmpdir_raw),
            step=step,
            max_wait_s=args.max_wait_s,
            run_id=run_id,
            poll_interval_s=args.poll_interval_s,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"BGJOB_ERROR={type(exc).__name__}:{exc}")
        return 2


def status_main(argv: list[str] | None = None) -> int:
    _ = argv
    for path, entry in registry.iter_entries():
        if entry is None:
            print(f"BGJOB_STATUS=INVALID REGISTRY={path}")
            continue
        live = registry.child_liveness(entry)
        print(f"BGJOB_STATUS=REGISTRY STEP={entry.step} RUN_ID={entry.run_id} LIVE={str(live.live).lower()} REASON={live.reason}")
    return 0


def reap_main(argv: list[str] | None = None) -> int:
    _ = argv
    count = 0
    for path, entry in registry.iter_entries():
        if entry is None:
            registry.unlink_entry(path)
            count += 1
            continue
        result = entry.result_env.is_file() and not entry.result_env.is_symlink()
        child_live = registry.child_liveness(entry)
        daemon_live = registry.daemon_liveness(entry)
        if result or (not child_live.live and not daemon_live.live):
            registry.unlink_entry(path)
            count += 1
            continue
        if registry.entry_expired(entry):
            _ = process_identity.terminate_validated_process_group(
                recorded=entry.child,
                log_path=None,
                caller="bgjob-reap",
                reason="expired-registry",
            )
            registry.unlink_entry(path)
            count += 1
    print(f"BGJOB_REAPED={count}")
    return 0
