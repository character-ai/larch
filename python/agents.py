"""Agent launcher helpers and failure classification."""

from __future__ import annotations

import re
from pathlib import Path
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import config
import git
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
_QUOTA_RE = re.compile(
    r"usage limit|rate[ _-]?limit|too many requests|quota|429 too many|over your usage",
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
    failure_log: str | Path | None = None


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


def is_quota_failure(tool: str, sidecar: str | Path | None) -> bool:
    """Port of external_is_quota_failure in lib-external-launcher-common.sh.

    Detects a usage-limit / quota / rate-limit failure (an environmental
    account condition, distinct from auth) for codex/cursor only (#3378).
    """
    if tool not in ("codex", "cursor"):
        return False
    if not sidecar:
        return False
    path = Path(sidecar)
    if not path.is_file():
        return False
    return bool(_QUOTA_RE.search(path.read_text(encoding="utf-8", errors="replace")))


def parse_launcher_exit_text(text: str) -> int:
    """Read LAUNCHER_EXIT= from launcher stdout capture; missing → 0."""
    for line in text.splitlines():
        if line.startswith("LAUNCHER_EXIT="):
            raw = line.split("=", 1)[1].strip().strip("\r")
            try:
                return int(raw)
            except ValueError:
                return 0
    return 0


def read_launcher_exit(output_file: str | Path) -> int:
    """Read LAUNCHER_EXIT= from a launcher capture file; missing → 0."""
    path = Path(output_file)
    if not path.is_file():
        return 0
    return parse_launcher_exit_text(
        path.read_text(encoding="utf-8", errors="replace"),
    )


def parse_launcher_failure_class(log_file: str | Path | None) -> str:
    """Last LAUNCHER_FAILURE_CLASS= from launcher capture; unknown/missing → health."""
    if log_file is None:
        return "health"
    path = Path(log_file)
    if not path.is_file():
        return "health"
    last = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("LAUNCHER_FAILURE_CLASS="):
            last = line.split("=", 1)[1].strip().strip("\r")
    if last in ("none", "health", "other"):
        return last
    return "health"


def effective_failure_class(attempt: TierAttempt) -> str:
    """Failure class from capture log when present, else ``attempt.failure``."""
    if attempt.failure_log is not None:
        return parse_launcher_failure_class(attempt.failure_log)
    return attempt.failure.failure_class


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
    # Usage-limit / quota: environmental account condition; class health so the
    # CI-fix waterfall escalates to the next vendor instead of bailing (#3378).
    # The explicit quota message takes precedence over the transient heuristic.
    if (sidecar and is_quota_failure(tool, sidecar)) or (
        output_file and is_quota_failure(tool, output_file)
    ):
        return LaunchFailure(failure_class="health", reason="quota")
    if output_file and is_transient_infra_failure(tool, launcher_exit, output_file):
        return LaunchFailure(failure_class="health", reason="health-probe")
    if launcher_exit == config.EXIT_TIMEOUT:
        return LaunchFailure(failure_class="other", reason="timeout")
    if sidecar:
        p = Path(sidecar)
        text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        if _PARSE_RE.search(text):
            return LaunchFailure(failure_class="other", reason="parse")
        if _REFUSAL_RE.search(text):
            return LaunchFailure(failure_class="other", reason="refusal")
    if output_file:
        p = Path(output_file)
        text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        if _PARSE_RE.search(text):
            return LaunchFailure(failure_class="other", reason="parse")
    return LaunchFailure(failure_class="other", reason="unknown")


_DEFAULT_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def build_launch_argv(
    tier: str,
    *,
    role: str,
    output: str,
    run_id: str,
    repo: str,
    plan_file: str | None = None,
    failure_log: str | None = None,
    conflict_files: str | None = None,
    timeout_sec: int = config.SUBPROCESS_DEFAULT_TIMEOUT_SEC,
    scripts_dir: str | Path | None = None,
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
    root = Path(scripts_dir) if scripts_dir is not None else _DEFAULT_SCRIPTS_DIR
    argv = [
        str(root / script),
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
    if conflict_files:
        argv.extend(["--conflict-files", conflict_files])
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
    conflict_files: str | None = None,
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
        conflict_files=conflict_files,
        timeout_sec=timeout_sec,
    )
    return runner.run(argv, timeout=float(timeout_sec), cwd=cwd)


LaunchFn = Callable[[str], TierAttempt]


def run_waterfall(
    tiers: Sequence[str],
    launch_fn: LaunchFn,
    *,
    first_tier: str | None = None,
    runner: Runner | None = None,
    cwd: str | None = None,
) -> WaterfallResult:
    """Iterate tiers; short-circuit when the first tier fails with class 'other'.

    Health-class failures fall through to the next tier. When ``runner`` is set,
    snapshot tracked/untracked paths before the loop and revert deltas after each
    failed tier (``recovery_waterfall_paths_delta_revert`` parity).
    """
    tier_list = list(tiers)
    if first_tier and first_tier in tier_list:
        start = tier_list.index(first_tier)
        tier_list = [*tier_list[start:], *tier_list[:start]]
    baseline_tracked: frozenset[str] | None = None
    baseline_untracked: frozenset[str] | None = None
    if runner is not None:
        baseline_tracked = git.tracked_dirty_paths(runner, cwd=cwd)
        baseline_untracked = git.untracked_dirty_paths(runner, cwd=cwd)
    attempts: list[TierAttempt] = []
    first = tier_list[0] if tier_list else ""
    for idx, tier in enumerate(tier_list):
        attempt = launch_fn(tier)
        attempts.append(attempt)
        if attempt.launcher_exit == 0 and attempt.wrapper_rc == 0:
            return WaterfallResult(
                winning_tier=tier,
                attempts=tuple(attempts),
            )
        if runner is not None and baseline_tracked is not None and baseline_untracked is not None:
            git.paths_delta_revert(
                runner,
                baseline_tracked,
                baseline_untracked,
                cwd=cwd,
            )
        failure_class = effective_failure_class(attempt)
        if (
            idx == 0
            and tier == first
            and attempt.wrapper_rc == 0
            and failure_class == "other"
        ):
            return WaterfallResult(
                winning_tier=None,
                attempts=tuple(attempts),
                short_circuited=True,
            )
    return WaterfallResult(winning_tier=None, attempts=tuple(attempts))
