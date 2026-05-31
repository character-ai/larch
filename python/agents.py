"""Agent launcher helpers and failure classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Sequence

import config
from proc import CommandResult, Runner

_PARSE_RE = re.compile(
    r"invalid json|unexpected token|parse error|jq: error|syntaxerror|"
    r"unmarshal|cannot unmarshal",
    re.IGNORECASE,
)
_REFUSAL_RE = re.compile(
    r"refused to|refusal|denied by policy|policy violation",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LaunchFailure:
    failure_class: str
    reason: str


@dataclass(frozen=True)
class TierAttempt:
    tier: str
    wrapper_rc: int
    launcher_exit: int
    failure: LaunchFailure


@dataclass(frozen=True)
class WaterfallResult:
    winning_tier: str | None
    attempts: tuple[TierAttempt, ...]
    short_circuited: bool = False


def is_transient_infra_failure(
    tool: str,
    exit_code: int,
    output_file: str | Path | None,
) -> bool:
    """Port of external_is_transient_infra_failure in lib-external-launcher-common.sh."""
    if tool == "codex":
        if exit_code not in {5, 7}:
            return False
    elif tool == "cursor":
        if exit_code not in {4, 8}:
            return False
    else:
        return False
    if output_file is None:
        return True
    path = Path(output_file)
    if not path.is_file():
        return True
    return path.stat().st_size == 0


def classify_launch_failure(
    launcher_exit: int,
    sidecar: str | Path | None = None,
    *,
    auth_verdict: str = "unclassified",
    binary_present: bool = True,
    tool: str = "cursor",
    output_file: str | Path | None = None,
) -> LaunchFailure:
    """Port of external_classify_launch_failure."""
    if launcher_exit == 0:
        return LaunchFailure(failure_class="none", reason="")
    if not binary_present:
        return LaunchFailure(failure_class="health", reason="binary-missing")
    if auth_verdict == "auth":
        return LaunchFailure(failure_class="health", reason="auth")
    if output_file and is_transient_infra_failure(tool, launcher_exit, output_file):
        return LaunchFailure(failure_class="health", reason="health-probe")
    if launcher_exit == config.EXIT_TIMEOUT:
        return LaunchFailure(failure_class="other", reason="timeout")
    for path in (sidecar, output_file):
        if not path:
            continue
        p = Path(path)
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if _PARSE_RE.search(text):
            return LaunchFailure(failure_class="other", reason="parse")
        if _REFUSAL_RE.search(text):
            return LaunchFailure(failure_class="other", reason="refusal")
    return LaunchFailure(failure_class="other", reason="unknown")


def build_launch_argv(
    tier: str,
    *,
    role: str,
    output: str,
    run_id: str,
    repo: str,
    plan_file: str | None = None,
    failure_log: str | None = None,
    timeout_sec: int = config.SUBPROCESS_DEFAULT_TIMEOUT_SEC,
) -> list[str]:
    """Build per-tool launcher argv (parity with launch-*-ci.sh flags)."""
    script_map = {
        "cursor": "launch-cursor-ci.sh",
        "codex": "launch-codex-ci.sh",
        "claude": "launch-claude-ci.sh",
    }
    script = script_map.get(tier)
    if script is None:
        msg = f"unknown tier: {tier}"
        raise ValueError(msg)
    argv = [
        f"scripts/{script}",
        "--role",
        role,
        "--output",
        output,
        "--run-id",
        run_id,
        "--repo",
        repo,
        "--timeout",
        str(timeout_sec),
    ]
    if plan_file:
        argv.extend(["--plan-file", plan_file])
    if failure_log:
        argv.extend(["--failure-log", failure_log])
    return argv


def launch_tier(
    runner: Runner,
    tier: str,
    *,
    role: str,
    output: str,
    run_id: str,
    repo: str,
    plan_file: str | None = None,
    failure_log: str | None = None,
    timeout_sec: int = config.SUBPROCESS_DEFAULT_TIMEOUT_SEC,
    cwd: str | None = None,
) -> CommandResult:
    argv = build_launch_argv(
        tier,
        role=role,
        output=output,
        run_id=run_id,
        repo=repo,
        plan_file=plan_file,
        failure_log=failure_log,
        timeout_sec=timeout_sec,
    )
    return runner.run(argv, timeout=float(timeout_sec), cwd=cwd)


LaunchFn = Callable[[str], TierAttempt]


def run_waterfall(
    tiers: Sequence[str],
    launch_fn: LaunchFn,
    *,
    first_tier: str | None = None,
) -> WaterfallResult:
    """Iterate tiers; short-circuit when the first tier fails with class 'other'.

    Health-class failures fall through to the next tier.
    """
    attempts: list[TierAttempt] = []
    first = first_tier or (tiers[0] if tiers else "")
    for idx, tier in enumerate(tiers):
        attempt = launch_fn(tier)
        attempts.append(attempt)
        if attempt.launcher_exit == 0 and attempt.wrapper_rc == 0:
            return WaterfallResult(
                winning_tier=tier,
                attempts=tuple(attempts),
            )
        if (
            idx == 0
            and tier == first
            and attempt.wrapper_rc == 0
            and attempt.failure.failure_class == "other"
        ):
            return WaterfallResult(
                winning_tier=None,
                attempts=tuple(attempts),
                short_circuited=True,
            )
    return WaterfallResult(winning_tier=None, attempts=tuple(attempts))
