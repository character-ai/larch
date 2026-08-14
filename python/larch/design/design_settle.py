"""In-process /design Step 3.5 settle: dedup, postplan, dialectic clear, action dispatch."""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from larch import io as larch_io
from larch.core import config
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env
from larch.design import design_dialectic, design_pause
from larch.design.design_session import (
    SettleDispatchResult,
    WrapperArgs,
    _design_require_plugin_root,  # type: ignore[reportPrivateUsage]  # settle reuses design_session wrapper internals
    _parse_common_wrapper_args,  # type: ignore[reportPrivateUsage]  # settle reuses design_session wrapper internals
    _print_text,  # type: ignore[reportPrivateUsage]  # settle reuses design_session wrapper internals
    _rehydrate_wrapper_env,  # type: ignore[reportPrivateUsage]  # settle reuses design_session wrapper internals
    settle_next_action_for,
)
from larch.state.session_env import validate_design_tmpdir

SettleSite = Literal["gate-a", "gate-b", "discussion-round2", "gate-c"]
SETTLE_SITES: Final[frozenset[str]] = frozenset({"gate-a", "gate-b", "discussion-round2", "gate-c"})
POSTPLAN_SITE_BY_SETTLE: Final[Mapping[str, str]] = {
    "gate-a": "discussion-round2",
    "gate-b": "gate-b",
    "gate-c": "gate-c",
    "discussion-round2": "discussion-round2",
}
_LABEL: Final[str] = "design-step35-settle"
_DIALECTIC_WARN: Final[str] = (
    f"**⚠ {_LABEL}: dialectic-clear-stale failed after {{where}}; "
    "stale clarifier artifacts may linger (Gate C fingerprint binding still gates debate).**"
)
_ROUND_ENV_KEYS: Final[frozenset[str]] = frozenset(
    {"FINAL_ROUND_NUM", "STEP3_REVIEW_ROUND_NUM", "ROUND_NUM"}
)
_PAUSE_OUTPUT_MARKERS: Final[frozenset[str]] = frozenset(
    {
        "PAUSE_OK=true",
        "POSTPLAN_EMIT_STATUS=paused",
        "POSTPLAN_RC=11",
        "POSTPLAN_STATUS=pause-save",
    }
)


@dataclass(frozen=True)
class SettleRequest:
    """Typed settle inputs for one Gate A/B/C or discussion-round2 settle call."""

    site: SettleSite
    design_tmpdir: Path
    round_num: str | None = None
    force_dedup: bool = False
    session_env_path: str = ""
    claude_pid: str = ""
    plugin_root: str = ""
    public_argv: tuple[str, ...] = ()
    issue_number: str = ""
    repo: str = ""
    final_round_num: str = ""
    step3_review_round_num: str = ""
    env_round_num: str = ""


@dataclass(frozen=True)
class SettleResult:
    """Settle outcome: process exit rc plus the optional action row already emitted."""

    exit_rc: int
    next_action: str = ""


@dataclass(frozen=True)
class ChildCapture:
    """Stdout/stderr capture from one injectable child owner."""

    rc: int
    stdout: str
    stderr: str = ""


DedupRunner = Callable[[Path], ChildCapture]
PostplanRunner = Callable[[SettleRequest, str], ChildCapture]
DialecticClearRunner = Callable[[Path], int]
PauseSaveRunner = Callable[[SettleRequest], ChildCapture]


@dataclass(frozen=True)
class SettleRunners:
    """Injectable owners for offline parity and production defaults."""

    dedup: DedupRunner
    postplan: PostplanRunner
    dialectic_clear: DialecticClearRunner
    pause_save: PauseSaveRunner


@dataclass(frozen=True)
class _GateBPaths:
    round_num: str
    ready_marker: Path
    phase_file: Path


@dataclass(frozen=True)
class _SettleFlagScan:
    site: str
    round_num: str
    force_dedup: bool
    public_argv: tuple[str, ...]
    error: str = ""


def _default_dedup(design_tmpdir: Path) -> ChildCapture:
    result = subprocess.run(
        [
            str(larch_entrypoint()),
            "plan-review",
            "gate-b-dedup",
            "--design-tmpdir",
            str(design_tmpdir),
            "--dedup",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=larch_entrypoint_env(),
    )
    return ChildCapture(rc=result.returncode, stdout=result.stdout, stderr=result.stderr)


def _default_postplan(request: SettleRequest, postplan_site: str) -> ChildCapture:
    from larch.design.design_step2b import step2b_postplan_main  # noqa: PLC0415 - deferred to keep settle import light

    # Honor the typed request path even when callers invoke step35_settle_for
    # without going through step35_settle_main's env rehydrate.
    os.environ[config.ENV_DESIGN_TMPDIR] = str(request.design_tmpdir)
    argv: list[str] = [
        "--session-env-path",
        request.session_env_path,
        "--claude-pid",
        request.claude_pid,
        "--plugin-root",
        request.plugin_root or os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, ""),
        "--site",
        postplan_site,
        *request.public_argv,
    ]
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = step2b_postplan_main(argv)
    return ChildCapture(rc=int(rc), stdout=buf.getvalue(), stderr=err.getvalue())


def _default_dialectic_clear(design_tmpdir: Path) -> int:
    # Match design dialectic-clear-stale CLI: shape errors are fail-open warnings
    # at settle, not hard aborts (Gate C fingerprint binding still gates debate).
    try:
        return int(design_dialectic.clear_stale(design_tmpdir, reason="plan-rewrite"))
    except design_dialectic.DialecticShapeError:
        return 2


def _default_pause_save(request: SettleRequest) -> ChildCapture:
    # Preserve bash wrapper argv shape: pass ISSUE_NUMBER through even when empty
    # so pause-save applies the same required-flag rejection as before.
    args = ["--design-tmpdir", str(request.design_tmpdir), "--issue", request.issue_number]
    if request.repo:
        args.extend(["--repo", request.repo])
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = design_pause.pause_save_main(args)
    return ChildCapture(rc=int(rc), stdout=buf.getvalue(), stderr=err.getvalue())


def default_settle_runners() -> SettleRunners:
    return SettleRunners(
        dedup=_default_dedup,
        postplan=_default_postplan,
        dialectic_clear=_default_dialectic_clear,
        pause_save=_default_pause_save,
    )


def _emit_next_action(action: str) -> None:
    print(f"SETTLE_NEXT_ACTION={action}")


def _atomic_write_line(*, path: Path, value: str) -> None:
    larch_io.atomic_write(path=path, text=f"{value}\n", prefix=f".{path.name}.", nofollow=True)


def _print_child(capture: ChildCapture) -> None:
    _print_text(capture.stdout)
    if capture.stderr:
        print(capture.stderr, end="" if capture.stderr.endswith("\n") else "\n", file=sys.stderr)


def _resolve_gate_b_round(request: SettleRequest) -> str | None:
    for candidate in (
        request.round_num or "",
        request.final_round_num,
        request.step3_review_round_num,
        request.env_round_num,
    ):
        if candidate.isdigit():
            return candidate
    return None


def _parse_postplan_rc(stdout: str) -> tuple[str, int]:
    first = ""
    count = 0
    for line in stdout.splitlines():
        if line.startswith("POSTPLAN_RC="):
            value = line.removeprefix("POSTPLAN_RC=")
            if count == 0:
                first = value
            count += 1
    return first, count


def _pause_signal_in_output(stdout: str) -> bool:
    return any(line in _PAUSE_OUTPUT_MARKERS for line in stdout.splitlines())


def _restore_gate_b_snapshot(*, request: SettleRequest, gate_b_round: str) -> None:
    if request.site != "gate-b" or not gate_b_round:
        return
    snapshot = request.design_tmpdir / f"plan-pre-apply-round-{gate_b_round}.txt"
    if snapshot.is_file() and not snapshot.is_symlink():
        _ = shutil.copyfile(snapshot, request.design_tmpdir / "plan.txt")


def _warn_dialectic(*, where: str) -> None:
    print(_DIALECTIC_WARN.format(where=where), file=sys.stderr)


def _dispatch_next_action(*, site: str, postplan_rc: int) -> SettleResult:
    result: SettleDispatchResult = settle_next_action_for(site=site, postplan_rc=postplan_rc)
    if not result.action:
        print(f"{_LABEL}: settle-next-action failed for site={site} postplan_rc={postplan_rc}", file=sys.stderr)
        return SettleResult(exit_rc=3)
    _emit_next_action(result.action)
    return SettleResult(exit_rc=result.exit_rc, next_action=result.action)


def _handle_pause_requested(*, request: SettleRequest, runners: SettleRunners) -> SettleResult | None:
    if not (request.design_tmpdir / ".pause-requested").is_file():
        return None
    pause = runners.pause_save(request)
    _print_child(pause)
    pause_ok = any(line == "PAUSE_OK=true" for line in pause.stdout.splitlines())
    if pause_ok or (request.design_tmpdir / ".pause-save-complete").is_file():
        _emit_next_action("pause")
        return SettleResult(exit_rc=11, next_action="pause")
    return SettleResult(exit_rc=pause.rc)


def _gate_b_paths(request: SettleRequest) -> tuple[_GateBPaths | None, SettleResult | None]:
    if request.site != "gate-b":
        return None, None
    resolved = _resolve_gate_b_round(request)
    if resolved is None:
        print(
            f"{_LABEL}: Gate B requires --round-num or FINAL_ROUND_NUM, "
            "STEP3_REVIEW_ROUND_NUM, or ROUND_NUM",
            file=sys.stderr,
        )
        return None, SettleResult(exit_rc=2)
    return (
        _GateBPaths(
            round_num=resolved,
            ready_marker=request.design_tmpdir / f".gate-b-postapply-ready-{resolved}",
            phase_file=request.design_tmpdir / f".step3-round-{resolved}.phase",
        ),
        None,
    )


def _should_skip_gate_b_dedup(*, request: SettleRequest, paths: _GateBPaths | None) -> bool:
    if request.site != "gate-b" or paths is None or request.force_dedup:
        return False
    if not paths.ready_marker.is_file():
        return False
    if not paths.phase_file.is_file() or paths.phase_file.is_symlink():
        return True
    phase_text = paths.phase_file.read_text(encoding="utf-8", errors="replace").rstrip("\n")
    return phase_text != "awaiting-postplan-operator"


def _run_dedup_phase(
    *,
    request: SettleRequest,
    runners: SettleRunners,
    paths: _GateBPaths | None,
) -> SettleResult | None:
    if _should_skip_gate_b_dedup(request=request, paths=paths):
        return None
    dedup = runners.dedup(request.design_tmpdir)
    _print_child(dedup)
    if dedup.rc == 1:
        _restore_gate_b_snapshot(request=request, gate_b_round=paths.round_num if paths else "")
        _emit_next_action("dedup-revise")
        print(
            f"{_LABEL}: post-rewrite dedup requires plan revision; retry settle after cleanup",
            file=sys.stderr,
        )
        return SettleResult(exit_rc=1, next_action="dedup-revise")
    if dedup.rc != 0:
        print(f"{_LABEL}: post-rewrite dedup failed with rc {dedup.rc}", file=sys.stderr)
        return SettleResult(exit_rc=dedup.rc)
    if runners.dialectic_clear(request.design_tmpdir) != 0:
        _warn_dialectic(where="dedup")
    if paths is not None:
        _atomic_write_line(path=paths.ready_marker, value="ready")
    return None


def _dispatch_postplan_rc(
    *,
    request: SettleRequest,
    runners: SettleRunners,
    paths: _GateBPaths | None,
    postplan: ChildCapture,
) -> SettleResult:
    machine_rc, machine_count = _parse_postplan_rc(postplan.stdout)
    if machine_count != 1:
        msg = (
            "postplan output missing anchored POSTPLAN_RC row"
            if machine_count == 0
            else "postplan output contained multiple POSTPLAN_RC rows"
        )
        print(f"{_LABEL}: {msg}", file=sys.stderr)
        return SettleResult(exit_rc=3)
    if machine_rc == "0":
        if postplan.rc != 0:
            print(f"{_LABEL}: POSTPLAN_RC=0 with child rc {postplan.rc}", file=sys.stderr)
            return SettleResult(exit_rc=3)
        if runners.dialectic_clear(request.design_tmpdir) != 0:
            _warn_dialectic(where="postplan")
        if paths is not None:
            _atomic_write_line(path=paths.phase_file, value="awaiting-continuation")
        return _dispatch_next_action(site=request.site, postplan_rc=0)
    if machine_rc in {"10", "11", "12", "13"}:
        if machine_rc in {"10", "13"} and paths is not None:
            _atomic_write_line(path=paths.phase_file, value="awaiting-postplan-operator")
        return _dispatch_next_action(site=request.site, postplan_rc=int(machine_rc))
    print(f"{_LABEL}: unexpected POSTPLAN_RC={machine_rc}", file=sys.stderr)
    return SettleResult(exit_rc=3)


def step35_settle_for(*, request: SettleRequest, runners: SettleRunners | None = None) -> SettleResult:
    """Run settle for a typed request; emit stdout/stderr contract rows as side effects."""
    active = runners if runners is not None else default_settle_runners()
    paused = _handle_pause_requested(request=request, runners=active)
    if paused is not None:
        return paused
    paths, gate_b_error = _gate_b_paths(request)
    if gate_b_error is not None:
        return gate_b_error
    dedup_error = _run_dedup_phase(request=request, runners=active, paths=paths)
    if dedup_error is not None:
        return dedup_error
    if paths is not None:
        _atomic_write_line(path=paths.phase_file, value="awaiting-post-apply")
    with contextlib.suppress(FileNotFoundError):
        (request.design_tmpdir / ".pause-save-complete").unlink()
    postplan = active.postplan(request, POSTPLAN_SITE_BY_SETTLE[request.site])
    _print_child(postplan)
    if _pause_signal_in_output(postplan.stdout) or (request.design_tmpdir / ".pause-save-complete").is_file():
        _emit_next_action("pause")
        return SettleResult(exit_rc=11, next_action="pause")
    return _dispatch_postplan_rc(request=request, runners=active, paths=paths, postplan=postplan)


def _load_round_env_keys(session_env_path: str) -> dict[str, str]:
    """Read Gate B round keys from the session env file (not on the shared allowlist)."""
    if not session_env_path:
        return {}
    return larch_io.read_kvs(
        session_env_path,
        allowed_keys=_ROUND_ENV_KEYS,
        duplicate_policy="first",
        skip_comments=True,
        reject_symlink=True,
        on_error_default=True,
        errors="replace",
        default={},
    )


def _consume_flag_value(args: list[str], index: int) -> tuple[str, int] | None:
    if index + 1 >= len(args):
        return None
    return args[index + 1], index + 2


@dataclass
class _FlagScanState:
    site: str = ""
    round_num: str = ""
    force_dedup: bool = False
    public_argv: list[str] | None = None
    error: str = ""
    index: int = 0


def _apply_settle_flag(state: _FlagScanState, *, token: str, args: list[str]) -> bool:
    """Mutate scan state for one token. Returns False when scanning should stop."""
    continue_scan = True
    if token == "--":
        state.public_argv = args[state.index + 1 :]
        continue_scan = False
    elif token == "--site":
        consumed = _consume_flag_value(args, state.index)
        if consumed is None:
            state.error = "--site requires a value"
            continue_scan = False
        else:
            state.site, state.index = consumed
    elif token == "--round-num":
        consumed = _consume_flag_value(args, state.index)
        if consumed is None:
            state.error = "--round-num requires a value"
            continue_scan = False
        else:
            state.round_num, state.index = consumed
    elif token == "--force-dedup":
        state.force_dedup = True
        state.index += 1
    elif token in {"--session-env-path", "--claude-pid", "--plugin-root"}:
        state.index += 2 if state.index + 1 < len(args) else 1
    elif token.startswith("--") and state.index + 1 < len(args) and not args[state.index + 1].startswith("--"):
        state.index += 2
    else:
        state.index += 1
    return continue_scan


def _scan_settle_flags(argv: Sequence[str], parsed: WrapperArgs) -> _SettleFlagScan:
    state = _FlagScanState(public_argv=list(parsed.public_argv_words or []))
    args = list(argv)
    while state.index < len(args):
        if not _apply_settle_flag(state, token=args[state.index], args=args):
            break
    if state.error:
        return _SettleFlagScan(site="", round_num="", force_dedup=False, public_argv=(), error=state.error)
    site = parsed.site or state.site
    return _SettleFlagScan(
        site=site,
        round_num=state.round_num,
        force_dedup=state.force_dedup,
        public_argv=tuple(state.public_argv or ()),
    )


def _build_settle_request(
    *,
    parsed: WrapperArgs,
    flags: _SettleFlagScan,
) -> tuple[SettleRequest | None, int]:
    if flags.site not in SETTLE_SITES:
        print(
            f"{_LABEL}: --site must be gate-b, gate-a, discussion-round2, or gate-c",
            file=sys.stderr,
        )
        return None, 2
    env = _rehydrate_wrapper_env(parsed)
    round_env = _load_round_env_keys(parsed.session_env_path)
    if parsed.plugin_root:
        os.environ[config.ENV_CLAUDE_PLUGIN_ROOT] = parsed.plugin_root
    req_rc = _design_require_plugin_root()
    if req_rc != 0:
        return None, req_rc
    design_tmpdir_raw = env.get("DESIGN_TMPDIR", "") or os.environ.get(config.ENV_DESIGN_TMPDIR, "")
    if not design_tmpdir_raw:
        print("/design Step 3.5 settle: DESIGN_TMPDIR required", file=sys.stderr)
        return None, 2
    ok, err = validate_design_tmpdir(design_tmpdir_raw)
    if not ok:
        print(f"ERROR={err}", file=sys.stderr)
        return None, 2
    design_tmpdir = Path(design_tmpdir_raw).resolve()
    os.environ[config.ENV_DESIGN_TMPDIR] = str(design_tmpdir)
    request = SettleRequest(
        site=flags.site,  # type: ignore[arg-type]  # narrowed by SETTLE_SITES membership above
        design_tmpdir=design_tmpdir,
        round_num=flags.round_num or None,
        force_dedup=flags.force_dedup,
        session_env_path=parsed.session_env_path,
        claude_pid=parsed.claude_pid,
        plugin_root=parsed.plugin_root or os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, ""),
        public_argv=flags.public_argv,
        issue_number=env.get("ISSUE_NUMBER", "") or os.environ.get(config.ENV_ISSUE_NUMBER, ""),
        repo=env.get("REPO", "") or os.environ.get(config.ENV_REPO, ""),
        final_round_num=round_env.get("FINAL_ROUND_NUM", "") or os.environ.get("FINAL_ROUND_NUM", ""),
        step3_review_round_num=round_env.get("STEP3_REVIEW_ROUND_NUM", "")
        or os.environ.get("STEP3_REVIEW_ROUND_NUM", ""),
        env_round_num=round_env.get("ROUND_NUM", "") or os.environ.get("ROUND_NUM", ""),
    )
    return request, 0


def _parse_settle_argv(argv: Sequence[str]) -> tuple[SettleRequest | None, int]:
    """Parse settle CLI argv into a SettleRequest, or return (None, exit_rc)."""
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"{_LABEL}: {exc}", file=sys.stderr)
        return None, 2
    flags = _scan_settle_flags(argv, parsed)
    if flags.error:
        print(f"{_LABEL}: {flags.error}", file=sys.stderr)
        return None, 2
    return _build_settle_request(parsed=parsed, flags=flags)


def step35_settle_main(argv: Sequence[str] | None = None) -> int:
    """CLI entry for design step35-settle and plan-review step35-settle."""
    request, parse_rc = _parse_settle_argv(argv or [])
    if request is None:
        return parse_rc
    return step35_settle_for(request=request).exit_rc


__all__ = [
    "POSTPLAN_SITE_BY_SETTLE",
    "SETTLE_SITES",
    "ChildCapture",
    "SettleRequest",
    "SettleResult",
    "SettleRunners",
    "SettleSite",
    "default_settle_runners",
    "step35_settle_for",
    "step35_settle_main",
]
