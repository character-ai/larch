"""CLI entrypoints for bgjob."""

from __future__ import annotations

import argparse
from pathlib import Path

from larch.bgjob import daemon, model, registry, wait
from larch.core import config, process_identity


def _add_common_job_args(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument("--step", required=True)
    _ = parser.add_argument("--tmpdir", required=True)
    _ = parser.add_argument("--run-id", default="")


def _build_spec(args: argparse.Namespace) -> model.JobSpec:
    step = model.validate_slug(str(args.step), label="step")
    tmpdir = model.checked_dir(Path(args.tmpdir), label="tmpdir")
    clone_path = Path.cwd().resolve()
    run_id = model.validate_slug(str(args.run_id), label="run-id") if args.run_id else model.default_run_id(
        tmpdir=tmpdir,
        clone_path=clone_path,
    )
    log_dir_arg = Path(args.log_dir) if args.log_dir else None
    log_dir, _, _ = model.log_paths(tmpdir=tmpdir, log_dir=log_dir_arg, step=step)
    sentinels = tuple(model.ensure_under(Path(raw), tmpdir, label="sentinel") for raw in args.sentinel)
    owner = daemon.owner_identity_from_env(args.owner_pid)
    merge_result_env = Path(args.merge_result_env).resolve() if args.merge_result_env else None
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


def wait_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py bgjob wait")
    _add_common_job_args(parser)
    _ = parser.add_argument("--max-wait-s", type=int, default=config.BGJOB_WAIT_DEFAULT_CHUNK_S)
    _ = parser.add_argument("--poll-interval-s", type=float, default=1.0)
    args = parser.parse_args(argv)
    try:
        step = model.validate_slug(str(args.step), label="step")
        run_id = model.validate_slug(str(args.run_id), label="run-id") if args.run_id else None
        return wait.wait_once(
            tmpdir=Path(args.tmpdir),
            step=step,
            max_wait_s=args.max_wait_s,
            run_id=run_id,
            poll_interval_s=args.poll_interval_s,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"BGJOB_ERROR={type(exc).__name__}:{exc}")
        return 2


def status_main(argv: list[str] | None = None) -> int:  # noqa: ARG001 - uniform CLI signature
    for path, entry in registry.iter_entries():
        if entry is None:
            print(f"BGJOB_STATUS=INVALID REGISTRY={path}")
            continue
        live = registry.child_liveness(entry)
        print(f"BGJOB_STATUS=REGISTRY STEP={entry.step} RUN_ID={entry.run_id} LIVE={str(live.live).lower()} REASON={live.reason}")
    return 0


def reap_main(argv: list[str] | None = None) -> int:  # noqa: ARG001 - uniform CLI signature
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
