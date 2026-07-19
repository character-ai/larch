# pyright: reportUnusedCallResult=false
"""Branch push orchestration for ``cli.py push branch`` and ``push force``."""

from __future__ import annotations

from dataclasses import dataclass

import argparse
import sys
from pathlib import Path
from larch.git import git
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from larch.core.repo_roots import larch_entrypoint
from larch.core import logging_util
from larch.core import proc
from larch.core import rust_runtime
from larch.git import rebase


def _checkout_ours(path: str) -> CommandResult:
    entrypoint = larch_entrypoint(Path(__file__).resolve().parents[3])
    return proc.run([str(entrypoint), "git", "checkout-ours", path])


def _rebase_skip() -> CommandResult:
    entrypoint = larch_entrypoint(Path(__file__).resolve().parents[3])
    return proc.run([str(entrypoint), "git", "rebase-skip"])


def assert_clean_worktree(runner: Runner, *, cwd: str | None = None) -> None:
    """Fail closed when the working tree has uncommitted changes (#2434)."""
    result = git.status_porcelain(runner, cwd=cwd)
    if result.returncode != 0:
        msg = "git status --porcelain failed before push"
        raise ShipError(msg)
    if result.stdout.strip():
        msg = "uncommitted working-tree changes detected before push"
        raise ShipError(msg)


# CLI entrypoints migrated from push_cli.py.
_REBASE_FAILED_EXIT = 3
_CHECKPOINT_LOAD_ROUTING = "load-routing"


def _checkpoint_next_for_exit(exit_code: int) -> str:
    if exit_code == 0:
        return "continue"
    return _CHECKPOINT_LOAD_ROUTING


def _parse(*, parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def _rebase_sanitize(text: str) -> str:
    return " ".join(text.split())


def _conflict_files_csv(result: rebase.RebasePushResult) -> str:
    if result.conflict_files:
        return result.conflict_files
    files: list[str] = git.try_unmerged_paths(proc)
    if not files:
        files = [item.path for item in git.try_conflict_files(proc)]
    return ",".join(files)


def _is_trivial_conflict_file(path: str) -> bool:
    return path.startswith("larch-logs/")


def _split_conflict_csv(value: str) -> list[str]:
    return [item for item in value.split(",") if item]


def _partition_checkpoint_conflicts(
    conflicts: list[str],
) -> tuple[list[str], list[str]]:
    trivial = [path for path in conflicts if _is_trivial_conflict_file(path)]
    nontrivial = [
        path
        for path in conflicts
        if not _is_trivial_conflict_file(path)
    ]
    return trivial, nontrivial


def _current_unmerged_conflict_files() -> str:
    files = git.try_unmerged_paths(proc)
    if files:
        return ",".join(files)
    return ",".join(item.path for item in git.try_conflict_files(proc))


def _conflict_upstream_deleted(path: str) -> bool:
    for item in git.try_conflict_files(proc):
        if item.path == path:
            return not item.stage_2
    return False


def _resolve_trivial_conflict_file(path: str) -> bool:
    checkout = _checkout_ours(path)
    if checkout.returncode != 0:
        if not _conflict_upstream_deleted(path):
            print(f"WARN rebase-probe: failed to resolve trivial conflict {path}", file=sys.stderr)
            return False
        removed = git.rm(proc, path, force=True)
        if removed.returncode != 0:
            print(f"WARN rebase-probe: failed to resolve trivial conflict {path}", file=sys.stderr)
            return False
        return True
    staged = git.add(proc, path)
    if staged.returncode != 0:
        print(f"WARN rebase-probe: failed to stage trivial conflict {path}", file=sys.stderr)
        return False
    return True


def _empty_continue_result(result: rebase.RebasePushResult) -> bool:
    return _is_empty_or_already_applied_rebase_error(result.rebase_error)


def _is_empty_or_already_applied_rebase_error(text: str) -> bool:
    lowered = text.lower()
    if "nothing to commit" in lowered:
        return True
    if "no changes" in lowered:
        return True
    return "all merge conflicts were fixed" in lowered


def _continue_checkpoint_rebase() -> rebase.RebasePushResult:
    return rebase.rebase_push(
        proc,
        continue_mode=True,
        no_push=True,
        keep_on_conflict=True,
    )


def _handle_empty_continue_rc3(result: rebase.RebasePushResult) -> rebase.RebasePushResult | None:
    while True:
        unmerged = _current_unmerged_conflict_files()
        if unmerged:
            return rebase.RebasePushResult(exit_code=1, conflict_files=unmerged)
        if not _empty_continue_result(result):
            return None
        skipped = _rebase_skip()
        if skipped.returncode != 0:
            print("WARN rebase-probe: git rebase --skip failed after empty continue", file=sys.stderr)
            return None
        if not git.rebase_in_progress(proc):
            return rebase.RebasePushResult(exit_code=0)
        result = _continue_checkpoint_rebase()
        if result.exit_code != _REBASE_FAILED_EXIT:
            return result


def _checkpoint_rebase_result(
    *,
    base_remote: str,
    base_ref: str,
) -> rebase.RebasePushResult:
    result = rebase.rebase_push(
        proc,
        no_push=True,
        skip_if_pushed=True,
        keep_on_conflict=True,
        base_remote=base_remote,
        base_ref=base_ref,
    )
    if result.exit_code != 1:
        return result

    for _iteration in range(50):
        cf: str = _conflict_files_csv(result)
        if not cf:
            return rebase.RebasePushResult(exit_code=1, conflict_files="")
        conflicts: list[str] = _split_conflict_csv(cf)
        trivial, nontrivial = _partition_checkpoint_conflicts(conflicts)
        if not trivial:
            return rebase.RebasePushResult(exit_code=1, conflict_files=cf)
        for path in trivial:
            if not _resolve_trivial_conflict_file(path):
                return rebase.RebasePushResult(
                    exit_code=1,
                    conflict_files=_current_unmerged_conflict_files(),
                )
        if nontrivial:
            cf_now = _current_unmerged_conflict_files()
            return rebase.RebasePushResult(exit_code=1, conflict_files=cf_now or ",".join(nontrivial))
        result = _continue_checkpoint_rebase()
        if result.exit_code == _REBASE_FAILED_EXIT:
            handled = _handle_empty_continue_rc3(result)
            if handled is None:
                return result
            result = handled
        if result.exit_code != 1:
            return result
    print(
        "WARN rebase-probe: trivial conflict pre-pass hit iteration cap; surfacing current conflicts",
        file=sys.stderr,
    )
    return rebase.RebasePushResult(exit_code=1, conflict_files=_current_unmerged_conflict_files())


def rebase_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push rebase")
    parser.add_argument("--continue", dest="continue_mode", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--skip-if-pushed", action="store_true")
    parser.add_argument("--keep-on-conflict", action="store_true")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 3
    result = rebase.rebase_push(
        proc,
        continue_mode=args.continue_mode,
        no_push=args.no_push,
        skip_if_pushed=args.skip_if_pushed,
        keep_on_conflict=args.keep_on_conflict,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
    if result.skipped_already_pushed:
        logging_util.emit_kv(key="SKIPPED_ALREADY_PUSHED", value="true")
    if result.skipped_already_fresh:
        logging_util.emit_kv(key="SKIPPED_ALREADY_FRESH", value="true")
    if result.conflict_files:
        logging_util.emit_kv(key="CONFLICT_FILES", value=result.conflict_files)
    if result.rebase_error:
        logging_util.emit_kv(key="REBASE_ERROR", value=result.rebase_error)
    if result.push_error:
        logging_util.emit_kv(key="PUSH_ERROR", value=result.push_error)
    return result.exit_code


@dataclass(frozen=True)
class CheckpointProbeResult:
    """Typed routing output for the Step 1.r rebase checkpoint."""

    exit_code: int
    routing: dict[str, str]
    advisory_lines: tuple[str, ...] = ()
    stderr: str = ""


def checkpoint_probe(
    *, step_prefix: str, short_name: str, forked_target: str = "false",
    base_remote: str | None = None, base_ref: str | None = None,
) -> CheckpointProbeResult:
    """Run the checkpoint's rebase and phantom checks without re-entering cli.py."""
    _ = short_name
    remote = base_remote or ("upstream" if forked_target == "true" else "origin")
    result = _checkpoint_rebase_result(base_remote=remote, base_ref=base_ref or "main")
    routing = {"REBASE_RC": str(result.exit_code)}
    if result.skipped_already_pushed:
        routing["SKIPPED_ALREADY_PUSHED"] = "true"
    if result.skipped_already_fresh:
        routing["SKIPPED_ALREADY_FRESH"] = "true"
    outcome, route = {
        0: ("skipped" if result.skipped_already_pushed or result.skipped_already_fresh else "ok", "continue"),
        1: ("conflict", "conflict"),
    }.get(result.exit_code, ("failed", "bail"))
    routing.update(REBASE_OUTCOME=outcome, ROUTE=route)
    if result.exit_code == 1 or result.conflict_files:
        routing["CONFLICT_FILES"] = _conflict_files_csv(result)
    if result.rebase_error:
        routing["REBASE_ERROR"] = _rebase_sanitize(result.rebase_error)
    elif result.exit_code not in {0, 1}:
        error = "rebase-failed" if result.exit_code == _REBASE_FAILED_EXIT else f"unexpected-rc-{result.exit_code}"
        routing["REBASE_ERROR"] = error
    routing["CHECKPOINT_NEXT"] = _checkpoint_next_for_exit(result.exit_code)
    if result.exit_code != 0:
        return CheckpointProbeResult(result.exit_code, routing)
    advisory: list[str] = []
    _append_phantom_checkpoint_lines(advisory, step_prefix=step_prefix)
    return CheckpointProbeResult(0, routing, tuple(advisory))


def _append_phantom_checkpoint_lines(lines: list[str], *, step_prefix: str) -> None:
    probe = rust_runtime.phantom_probe(proc, step=f"{step_prefix}-post-rebase")
    lines.extend(probe.lines)


def _render_checkpoint_probe_output(result: CheckpointProbeResult) -> str:
    lines = [f"{key}={value}" for key, value in result.routing.items()]
    lines.extend(result.advisory_lines)
    return "\n".join(lines) + "\n"


def checkpoint_probe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push checkpoint-probe")
    parser.add_argument("step_prefix")
    parser.add_argument("short_name")
    parser.add_argument("--base-remote", default=None)
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 2
    print(f"→ rebase-probe: {args.step_prefix} {args.short_name}", file=sys.stderr)
    base_remote = args.base_remote or ("upstream" if args.forked_target == "true" else "origin")
    base_ref = args.base_ref or "main"
    result = checkpoint_probe(
        step_prefix=args.step_prefix, short_name=args.short_name, forked_target=args.forked_target,
        base_remote=base_remote, base_ref=base_ref,
    )
    sys.stdout.write(_render_checkpoint_probe_output(result))
    return result.exit_code
