"""Relevant-checks runner and contains-pins checker.

Contains the run-relevant-checks pipeline, the contains-pins assertion checker,
and their supporting utilities. See checks_lint_fix.py for the lint-fix dispatch
loop and repair-loop CLI.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import fnmatch
import os
import re
import sys
import tempfile
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from larch.core import config
from larch.core import proc
from larch.core import redact
from larch.core.proc import CommandResult, Runner

_RCC_MAX_ITER_CAP: Final = 6
CHECKS_FAILURE_DIGEST_MAX_BYTES: Final = 8192
_CHECKS_FAILURE_DIGEST_ERROR_MAX_BYTES: Final = 512
_CHECKS_FAILURE_DIGEST_MARKER_RE: Final = re.compile(
    r"ERROR:|Error:|FAILED|Failed|Traceback|AssertionError|DEFECT:"
)
_CHECKS_FAILURE_DIGEST_LINT_ROW_RE: Final = re.compile(
    r"^[^\s:][^:]*:\d+(?::\d+)?(?::)?\s+[A-Z][A-Z0-9]*\d+[A-Z0-9]*(?:\s|$)"
)
_CHECKS_FAILURE_DIGEST_MAKE_ERROR_RE: Final = re.compile(
    r"^make(?:\[\d+\])?: \*\*\* .*\bError \d+\b"
)
_CHECKS_FAILURE_DIGEST_LOCATION_RE: Final = re.compile(
    r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+):(\d+)(?::\d+)?\b"
)
_CHECKS_FAILURE_DIGEST_PRECOMMIT_RE: Final = re.compile(r"^(.+?)(?:\.{2,}|\s{2,})Failed\b")
_CHECKS_FAILURE_DIGEST_DIRECT_RE: Final = re.compile(r"^=== Running direct relevant make target\(s\): (.+) ===$")


def plugin_scripts_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts"


@dataclass(frozen=True)
class ChecksResult:
    ok: bool
    exit_code: int
    site: str
    redacted_log_path: str | None
    phase: str
    coverage: str
    skipped: bool
    warn: str | None
    raw_log_path: str | None = None
    failure_reason: str | None = None
    digest_file_path: str | None = None


@dataclass(frozen=True)
class FixOutcome:
    status: str
    delta_paths: tuple[str, ...]
    failure_reason: str | None
    commit_sha: str | None
    head_changed: bool
    coder_tool: str | None
    ledger_ready: bool = False
    ledger_site: str = ""
    ledger_trigger: str = ""
    ledger_step: str = ""
    ledger_phase: str = ""
    ledger_dispatcher: str = ""
    ledger_exit_code: int | None = None
    ledger_failure_detail_log: str = ""
    coder_log_path: str = ""
    stderr_tail_path: str = ""


# Mutable: delta_paths and ledger_* fields are filled in across fix-loop iterations.
@dataclass
class LoopResult:
    status: str
    delta_paths: tuple[str, ...] = ()
    last_fix_status: str = ""
    ledger_ready: bool = False
    ledger_site: str = ""
    ledger_trigger: str = ""
    ledger_step: str = ""
    ledger_phase: str = ""
    ledger_dispatcher: str = ""
    ledger_exit_code: int | None = None
    ledger_failure_detail_log: str = ""
    coder_log_path: str = ""
    stderr_tail_path: str = ""


def normalize_max_iter(raw: str | int | None = None) -> int:
    """Port of normalize_rcc_max_iter in the Python ship driver."""
    raw_str = "" if raw is None else str(raw).strip()
    if not raw_str.isdigit():
        return config.RCC_MAX_ITER_DEFAULT
    stripped = raw_str.lstrip("0")
    if stripped == "":
        return config.RCC_MAX_ITER_DEFAULT
    if len(stripped) > 1:
        return _RCC_MAX_ITER_CAP
    value = int(stripped)
    if value < 1:
        return config.RCC_MAX_ITER_DEFAULT
    if value > _RCC_MAX_ITER_CAP:
        return _RCC_MAX_ITER_CAP
    return value


def _canonical_dir(path: Path) -> Path | None:
    try:
        if not path.is_dir() or path.is_symlink():
            return None
        return path.resolve()
    except OSError:
        return None


def _under_root(*, path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def validate_tmpdir(tmpdir: str) -> Path | None:
    """Port of validate_tmpdir in python/cli.py checks run-relevant."""
    if not tmpdir.startswith("/"):
        return None
    candidate = Path(tmpdir)
    if not candidate.is_dir() or candidate.is_symlink():
        return None
    canonical = _canonical_dir(candidate)
    if canonical is None:
        return None
    basename = canonical.name
    if not basename.startswith(("claude-implement-", "claude-review-")):
        return None
    xdg_cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    cache_root = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    accepted_root: Path | None = None
    cache_sessions = _canonical_dir(cache_root / "larch" / "sessions")
    if cache_sessions is not None and _under_root(path=canonical, root=cache_sessions):
        accepted_root = cache_sessions
    if accepted_root is None:
        parent = canonical.parent
        for candidate_root in (Path("/tmp"), Path("/private/tmp")):  # noqa: S108
            resolved = _canonical_dir(candidate_root)
            if resolved is not None and parent == resolved:
                accepted_root = resolved
                break
    if accepted_root is None:
        return None
    return canonical


def resolve_checks_log_path(*, candidate: str, allowed_root: Path) -> Path | None:
    path = Path(candidate)
    try:
        if not path.is_file() or path.is_symlink():
            return None
        resolved = path.resolve(strict=True)
        root = allowed_root.resolve(strict=True)
    except OSError:
        return None
    if not _under_root(path=resolved, root=root) or resolved == root:
        return None
    return resolved


def _scan_checks_log_markers(path: Path) -> tuple[bool, bool, bool]:
    """Stream-scan the full log for phase/coverage markers (bash grep parity)."""
    has_precommit = False
    has_agent_lint = False
    has_agent_lint_warning = False
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if "=== Running pre-commit" in line:
                    has_precommit = True
                if "=== Running agent-lint ===" in line:
                    has_agent_lint = True
                if "WARNING: agent-lint not found on PATH" in line:
                    has_agent_lint_warning = True
    except OSError:
        return False, False, False
    return has_precommit, has_agent_lint, has_agent_lint_warning


def read_log_file_text(path: Path) -> str | None:
    try:
        if not path.is_file() or path.is_symlink():
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _mark_step_ledger(*, runner: Runner, canonical_tmp: Path, site: str) -> None:
    if site == "step3":
        label = "Step 3 — checks first pass"
    elif site == "step6":
        label = "Step 6 — checks second pass"
    else:
        return
    cli = plugin_scripts_dir().parent / "python" / "cli.py"
    env = {**os.environ, "IMPLEMENT_TMPDIR": str(canonical_tmp), "LARCH_TIMING_SKILL": "implement"}
    _ = runner.run(["python3", str(cli), "token", "mark", label], env=env)
    timing_env = {**env, "DESIGN_TMPDIR": ""}
    _ = runner.run(["python3", str(cli), "timing", "mark", label], env=timing_env)


def record_checks_vendor_task(  # noqa: PLR0913,RUF100
    *,
    runner: Runner,
    canonical_tmp: Path,
    task_kind: str,
    start_s: int,
    end_s: int,
    output_basename: str,
    exit_code: int,
    status: str = "complete",
) -> None:
    with contextlib.suppress(Exception):
        cli = plugin_scripts_dir().parent / "python" / "cli.py"
        env = {**os.environ, "IMPLEMENT_TMPDIR": str(canonical_tmp), "LARCH_TIMING_SKILL": "implement"}
        timing_env = {**env, "DESIGN_TMPDIR": ""}
        _ = runner.run([
            "python3",
            str(cli),
            "timing",
            "record-vendor-task",
            "--vendor",
            "claude",
            "--task-kind",
            task_kind,
            "--start-s",
            str(start_s),
            "--end-s",
            str(end_s),
            "--output",
            str(canonical_tmp / output_basename),
            "--exit-code",
            str(exit_code),
            "--status",
            status,
        ], env=timing_env)


def _coverage_from_markers(
    *,
    ok: bool,
    has_precommit: bool,
    has_agent_lint: bool,
) -> str:
    if not ok:
        return "changed-file-only"
    if has_precommit and has_agent_lint:
        return "full"
    if not has_precommit and has_agent_lint:
        return "post-check-only"
    return "changed-file-only"


def _phase_from_markers(*, ok: bool, has_precommit: bool, has_agent_lint: bool) -> str:
    if ok:
        return "unknown"
    if has_agent_lint:
        return "agent-lint"
    if has_precommit:
        return "pre-commit"
    return "unknown"


def _allocate_log_file(*, log_dir: Path, site: str) -> tuple[int, Path] | None:
    for attempt in range(1, 101):
        log_file = log_dir / f"{site}-{attempt}.log"
        try:
            fd = os.open(log_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        except OSError:
            return None
        else:
            return fd, log_file
    return None



def _checks_failure(  # noqa: PLR0913,RUF100
    *,
    site: str,
    exit_code: int,
    reason: str,
    raw_log_path: str | None = None,
    redacted_log_path: str | None = None,
    phase: str = "unknown",
    coverage: str = "changed-file-only",
    warn: str | None = None,
    digest_file_path: str | None = None,
) -> ChecksResult:
    return ChecksResult(
        ok=False,
        exit_code=exit_code,
        site=site,
        redacted_log_path=redacted_log_path,
        phase=phase,
        coverage=coverage,
        skipped=False,
        warn=warn,
        raw_log_path=raw_log_path,
        failure_reason=reason,
        digest_file_path=digest_file_path,
    )


def _clean_child_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith("LARCH_QUIET_"):
            del env[key]
    for key in ("CLAUDE_PLUGIN_ROOT", "LARCH_CLAUDE_PLUGIN_ROOT"):
        _ = env.pop(key, None)
    return env


def _write_log(*, log_fd: int, text: str) -> None:
    _ = os.write(log_fd, text.encode("utf-8", errors="replace"))


def _run_logged(
    *, runner: Runner,
    argv: Sequence[str],
    cwd: str,
    log_fd: int,
    env: dict[str, str],
) -> CommandResult:
    return runner.run(argv, cwd=cwd, env=env, stdout=log_fd, stderr=log_fd)


def _command_available(*, runner: Runner, name: str, cwd: str, env: dict[str, str]) -> bool:
    result = runner.run(
        ["bash", "-lc", f"command -v {name} >/dev/null 2>&1"],
        cwd=cwd,
        env=env,
    )
    return result.returncode == 0


def _python311_available(runner: Runner, *, cwd: str, env: dict[str, str]) -> bool:
    result = runner.run(
        [
            "python3",
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)",
        ],
        cwd=cwd,
        env=env,
    )
    return result.returncode == 0


def _pytest_available(runner: Runner, *, cwd: str, env: dict[str, str]) -> bool:
    result = runner.run(["python3", "-m", "pytest", "--version"], cwd=cwd, env=env)
    return result.returncode == 0


def _resolve_repo_root(*, runner: Runner, repo_root: str) -> Path | None:
    candidate = Path(repo_root) if repo_root else Path.cwd()
    if not candidate.is_dir() or candidate.is_symlink():
        return None
    result = runner.run(["git", "rev-parse", "--show-toplevel"], cwd=str(candidate))
    if result.returncode != 0:
        return None
    raw = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not raw:
        return None
    resolved = Path(raw)
    if not resolved.is_dir() or resolved.is_symlink():
        return None
    try:
        return resolved.resolve()
    except OSError:
        return None


def _git_lines(*, runner: Runner, argv: Sequence[str], cwd: str) -> tuple[str, ...]:
    result = runner.run(argv, cwd=cwd)
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def _changed_files(runner: Runner, *, cwd: str) -> tuple[str, ...]:
    branch_diff: tuple[str, ...] = ()
    # Prefer the remote-tracking origin/main over a possibly-stale local main so
    # mid-run rebases onto an advanced origin/main do not widen the changed-file
    # set with already-merged upstream files (issue #5460).
    if runner.run(["git", "rev-parse", "--verify", "origin/main"], cwd=cwd).returncode == 0:
        branch_diff = _git_lines(runner=runner, argv=["git", "diff", "--name-only", "origin/main...HEAD"], cwd=cwd)
    elif runner.run(["git", "rev-parse", "--verify", "main"], cwd=cwd).returncode == 0:
        branch_diff = _git_lines(runner=runner, argv=["git", "diff", "--name-only", "main...HEAD"], cwd=cwd)
    staged = _git_lines(runner=runner, argv=["git", "diff", "--cached", "--name-only"], cwd=cwd)
    unstaged = _git_lines(runner=runner, argv=["git", "diff", "--name-only"], cwd=cwd)
    untracked = _git_lines(runner=runner, argv=["git", "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    return tuple(sorted({*branch_diff, *staged, *unstaged, *untracked}))


def _existing_regular_files(*, repo: Path, paths: Iterable[str]) -> tuple[str, ...]:
    regular: list[str] = []
    for raw in paths:
        path = repo / raw
        try:
            if path.is_file():
                regular.append(raw)
        except OSError:
            continue
    return tuple(regular)


_DIRECT_TARGET_RULES: Final[tuple[tuple[tuple[str, ...], tuple[str, ...], bool, bool], ...]] = (
    (("scripts/read-result-env.sh", "scripts/read-result-env.md"), ("test-read-result-env", "test-design-structure"), False, False),
    (("scripts/test-read-result-env.sh", "scripts/test-read-result-env.md"), ("test-read-result-env",), False, False),
    (("python/larch/state/session_env.py", "python/test_session_env.py"), ("test-design-structure", "py-test"), False, False),
    (("python/plan_quality.py", "python/test_plan_quality.py"), ("test-design-publish", "test-design-stage-terminal-state", "test-design-failure-report", "test-design-step5c", "test-design-structure"), False, False),
    (("skills/design/scripts/design-step5c.sh", "skills/design/scripts/test-design-step5c.sh", "skills/design/scripts/test-design-step5c.md"), ("test-design-step5c", "test-design-publish", "test-design-stage-terminal-state"), False, False),
    (("skills/design/SKILL.md", "skills/design/references/*.md"), ("test-design-structure", "test-render-cost-line-callsites"), False, False),
    (("skills/design/SKILL.md", "skills/design/references/plan-review.md", "skills/design/scripts/design-step3-mav.sh", "skills/design/scripts/design-step3-mav.md", "skills/design/scripts/test-design-step3-mav.sh", "skills/design/scripts/test-design-step3-mav.md", "skills/design/scripts/test-step3-orchestrator-fence.sh", "skills/design/scripts/test-step3-orchestrator-fence.md"), ("test-design-step3-mav", "test-step3-orchestrator-fence"), False, False),
    (("scripts/test-implement-anti-polling-rule.sh", "AGENTS.md", "skills/design/SKILL.md", "skills/shared/design-background-wait.md", "skills/shared/orchestrator-never.md", "skills/implement/SKILL.md"), ("test-implement-anti-polling-rule",), False, False),
    (("python/upgrade_larch.py", "python/test_upgrade_larch.py"), ("py-test",), False, False),
    (("python/design_argv.py", "python/test_design_argv.py"), ("test-parse-design-argv",), False, False),
    (("python/design_lifecycle.py", "python/tests/design/test_design_lifecycle.py"), ("test-design-step2b-drafter", "test-design-driver", "test-design-step0-init", "test-design-step1d5", "test-design-stage-terminal-state", "test-design-step-final-summary", "test-design-failure-report", "test-design-step5c", "test-design-structure", "test-step0b-router-flag-recovery"), False, False),
    (("python/design_log_publish_flow.py", "python/test_design_log_publish_flow.py"), ("test-design-log-publish",), False, False),
    (("python/design_log_ship.py", "python/test_design_log_ship.py"), ("test-design-log-ship",), False, False),
    (("python/design_oos.py", "python/test_design_oos.py"), ("test-file-design-oos",), False, False),
    (("python/design_pause.py", "python/test_design_pause.py"), ("test-design-pause-resume",), False, False),
    (("python/design_postplan.py", "python/test_design_postplan.py"), ("test-design-postplan-emit",), False, False),
    (("python/design_publish.py", "python/test_design_publish.py"), ("test-design-publish",), False, False),
    (("python/design_step_log.py", "python/test_design_step_log.py"), ("test-run-step1-plan-log",), False, False),
    (("python/design_summary.py", "python/test_design_summary.py"), ("test-render-final-summary", "test-render-final-summary-bash32", "test-design-failure-report"), False, False),
    (("skills/design/scripts/test-step3-review-cap.sh", "skills/design/scripts/test-step3-review-cap.md"), ("test-step3-review-cap",), False, False),
    (("python/larch/review/plan_review.py", "python/test_plan_review.py"), ("test-plan-review", "test-design-multi-round-integration", "test-design-log-publish"), False, False),
    (("python/larch/review/plan_review_panel.py", "python/test_plan_review_panel.py"), ("test-plan-review-panel", "test-dispatch-plan-review-panel", "test-dispatch-plan-voters"), False, False),
    (("python/plan_quality.py", "python/test_plan_quality.py", "skills/design/scripts/test-auto-fix-plan-commands.sh"), ("test-auto-fix-plan-commands", "test-design-step-validator-autofix"), False, False),
    (("python/plan_quality.py", "python/test_plan_quality.py"), ("test-design-postplan-emit",), False, False),
    (("python/plan_quality.py", "python/test_plan_quality.py"), ("test-design-driver", "test-step0b-router-flag-recovery"), False, False),
    (("python/design_lifecycle.py", "python/tests/design/test_design_lifecycle.py"), ("test-check-plan-size",), False, False),
    (("python/plan_quality.py", "python/test_plan_quality.py"), ("test-run-step1-plan-log",), False, False),
    (("python/larch/agents/agents.py", "python/test_agents.py", "python/checks.py"), ("py-test", "test-launch-codex-exec", "test-launch-codex-ci", "test-launch-cursor-ci", "test-parse-codex-usage", "test-token-vendor-scrapers", "test-degraded-tools-gate", "test-run-external-agent"), False, False),
    (("python/larch/review/plan_review.py", "skills/design/scripts/design-step3-review.sh", "skills/design/scripts/design-step3-review.md", "skills/design/scripts/test-design-step3-review.sh", "skills/design/scripts/test-design-step3-review.md"), ("test-design-step3-review", "test-plan-review"), False, False),
    (("python/larch/review/plan_review.py", "skills/design/references/plan-review.md", "python/test_plan_review.py", "skills/design/scripts/dedup-plan-lines.py", "skills/design/scripts/dedup-plan-lines.md"), ("test-plan-review", "test-design-step3-review", "test-design-multi-round-integration"), False, False),
    (("scripts/test-design-multi-round-integration.sh", "scripts/test-design-multi-round-integration.md"), ("test-design-log-publish", "test-design-multi-round-integration"), False, False),
    (("scripts/test-design-structure.sh", "scripts/test-design-structure.md"), ("test-design-structure",), False, False),
    (("skills/implement/SKILL.md",), ("test-implement-structure", "test-render-cost-line-callsites"), False, False),
    (("skills/*/SKILL.md", "skills/*/references/*.md"), ("test-references-headers",), False, False),
    (("scripts/lint-readability-preamble.tsv", "scripts/lint-readability-preamble.tsv.md"), ("test-lint-readability-preamble",), False, False),
    (("python/larch/lint/lint_readability_preamble.py", "python/tests/lint/test_lint_readability_preamble.py", "skills/shared/readability-style.md", "skills/*/SKILL.md", ".claude/skills/*/SKILL.md"), ("test-lint-readability-preamble", "test-design-structure", "test-brainstorm-prompts"), False, False),
    (
        (
            "python/larch/lint/lint_bg_wait_coverage.py",
            "python/tests/lint/test_lint_bg_wait_coverage.py",
            "Makefile",
            ".pre-commit-config.yaml",
        ),
        (
            "test-lint-bg-wait-coverage",
            "test-hook-bg-poll-guard",
            "test-hook-no-progress-guard",
        ),
        False,
        False,
    ),

    (("python/rendering.py", "python/test_rendering.py"), ("test-plan-review", "test-launch-claude-subprocess", "test-lib-scope-anchor-handoff", "test-plan-review-panel", "test-dispatch-plan-review-panel", "test-dispatch-plan-voters", "test-aggregate-findings"), False, False),
    (("python/decompose.py", "python/test_decompose.py"), ("test-decompose-file-issues", "test-decompose-panel-dispatch", "test-decompose-aggregator"), True, True),
    (("python/plan_scout.py", "python/test_plan_scout.py"), ("test-scout-dynamic-archetypes", "test-scout-plan-archetypes-wrapper", "test-dispatch-panel-core-dynamic"), True, True),
    (("python/issue_wire.py", "python/test_issue_wire.py", "python/plan_quality.py", "python/test_plan_quality.py", "python/redact.py", "python/gh.py", "python/rendering.py", "python/test_rendering.py", ".claude/rules/gh-body-file.md", "AGENTS.md", "SECURITY.md", "agent-lint.toml", "docs/issue-anchored-plan.md", "docs/linting.md", "python/test_plan_review.py", "scripts/test-legacy-title-prefix-literals-scope.sh"), ("test-design-structure", "test-review-structure", "test-research-structure"), True, True),
    (("scripts/resolve-upstream-larch-repo.sh", "scripts/resolve-upstream-larch-repo.md", "scripts/test-resolve-upstream-larch-repo.sh", "scripts/test-resolve-upstream-larch-repo.md"), ("test-resolve-upstream-larch-repo",), False, False),
    (("scripts/file-failure-report-cross-repo.sh", "scripts/file-failure-report-cross-repo.md", "scripts/test-file-failure-report-cross-repo.sh", "scripts/test-file-failure-report-cross-repo.md"), ("test-file-failure-report-cross-repo", "test-design-failure-report"), False, False),
    (("python/larch/state/stall_recovery.py", "python/stall-recovery-report.md", "python/stall-recovery-report-allowlists.tsv", "python/test_stall_recovery.py", "skills/implement/references/stall-recovery.md"), ("test-stall-recovery-report", "test-design-stage-terminal-state", "test-design-failure-report"), False, False),
    (("python/blocker.py", "python/test_blocker.py"), ("test-blocker",), True, True),
    (("python/issue_query.py", "python/test_issue_query.py"), ("test-issue-query",), True, True),
    (("python/larch/state/admission.py", "python/test_admission.py"), ("test-implement-admission",), False, False),
    (("python/larch/state/dirty_tree.py", "python/test_dirty_tree.py"), ("test-check-mid-run-dirty-tree", "test-check-scope-reduction-marker"), False, False),
    (("python/architectural_guidelines.py", "python/test_architectural_guidelines.py", "python/issue_wire.py", "python/test_issue_wire.py"), ("py-test",), False, False),
    (("python/larch/state/bootstrap.py", "python/test_bootstrap.py"), ("test-implement-bootstrap", "test-implement-bootstrap-invoke", "test-parse-bootstrap-routing-envelope"), False, False),
    (("python/preflight.py", "python/test_preflight.py"), ("test-implement-preflight",), False, False),
    (("python/larch/state/finalize.py", "python/test_finalize.py"), ("test-implement-finalize",), False, False),
    (("python/larch/state/closeout.py", "python/test_closeout.py"), ("test-step-16-17",), False, False),
    (("python/final_report.py", "python/test_final_report.py"), ("test-write-final-report", "test-step-18b-final-report"), False, False),
    (("python/larch/report/final_report.py",), ("test-write-final-report", "test-step-18b-final-report"), False, True),
    (("python/larch/report/progress_report.py",), (), False, True),
    (("python/larch/report/review_phase_detail.py",), (), False, True),
    (("python/larch/rendering/gantt.py",), (), False, True),
    (("python/larch/implement/checks.py", "python/larch/implement/checks_run_relevant.py", "python/larch/implement/checks_lint_fix.py"), (), False, True),
    (("python/pr_body.py", "python/test_pr_body.py", "python/ship.py", "python/test_ship.py", "python/final_report.py", "python/test_final_report.py"), ("py-test",), False, False),
    (("skills/implement/scripts/step-architectural-guidelines-*.sh", "skills/implement/scripts/step-architectural-guidelines-*.md", "skills/implement/scripts/test-architectural-guidelines-step.sh", "skills/implement/scripts/test-architectural-guidelines-step.md", "scripts/residual-bash-paths.txt"), ("test-architectural-guidelines-step", "test-implement-fence-shape"), False, False),
    (("skills/implement/references/ship-pr-exit-matrix.md", "skills/implement/references/conflict-resolution.md", "scripts/test-implement-fence-shape.sh"), ("test-implement-fence-shape",), False, False),
    (("python/oos.py", "python/test_oos.py"), (), True, True),
    (("python/larch/review/review_pipeline.py", "python/larch/review/review_pipeline_shared.py", "python/larch/review/review_gather.py", "python/larch/review/review_prune.py", "python/larch/review/review_dispatch_panel.py", "python/larch/review/review_collect.py", "python/larch/review/review_threshold.py", "python/larch/review/review_core_body.py", "python/test_review_pipeline.py"), ("test-gather-context", "test-review-core", "test-dispatch-panel-core", "test-dispatch-panel-core-dynamic", "test-dispatch-panel-reuse", "test-dispatch-panel-limits", "test-collect-findings"), True, True),
    (("python/larch/review/review_aggregate.py", "python/test_review_aggregate.py"), ("test-aggregate-findings",), True, True),
    (("python/compose_review.py", "python/test_compose_review.py"), ("test-compose-review-findings",), True, True),
    (("python/larch/review/review_tally.py", "python/test_review_tally.py"), ("test-emit-tally", "test-tally-code-votes"), True, True),
    (("python/larch/review/review_and_fix.py", "python/test_review_and_fix.py", "skills/review-and-fix/SKILL.md"), ("test-review-and-fix",), True, True),
    (("python/*.py",), (), True, True),
    (("python/fixtures/**",), (), False, True),
    (("skills/report-tokens/SKILL.md", "skills/report-tokens/scripts/plot-cost-over-time.py", "skills/report-tokens/scripts/plot-cost-over-time.md", "docs/run-logs.md"), ("py-test",), False, False),
    (("python/migrated-scripts.tsv",), ("lint-retired-scripts",), False, True),
    (("python/pyproject.toml", "python/ruff.toml", "python/pyrightconfig.json", "python/.pylintrc", "python/requirements-dev.txt", "python/requirements-test.txt"), (), True, True),
)


def _append_once(*, items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _patterns_match(*, path: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if "/" in pattern and "**" not in pattern and path.count("/") != pattern.count("/"):
            continue
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def _append_py_lint_target(  # noqa: PLR0913,RUF100
    *, runner: Runner,
    targets: list[str],
    cwd: str,
    env: dict[str, str],
    log_fd: int,
    warned: set[str],
) -> None:
    if not _python311_available(runner, cwd=cwd, env=env):
        if "py-lint" not in warned:
            _write_log(log_fd=log_fd, text="WARNING: python3 >= 3.11 not found — skipping py-lint direct relevant target\n")
            warned.add("py-lint")
        return
    missing = [tool for tool in ("ruff", "pylint", "pyright") if not _command_available(runner=runner, name=tool, cwd=cwd, env=env)]
    if missing:
        if "py-lint" not in warned:
            _write_log(log_fd=log_fd, text=f"WARNING: Python lint tools not found on PATH ({' '.join(missing)}) — skipping py-lint direct relevant target\n")
            warned.add("py-lint")
        return
    _append_once(items=targets, item="py-lint")


def _append_py_test_target(  # noqa: PLR0913,RUF100
    *, runner: Runner,
    targets: list[str],
    cwd: str,
    env: dict[str, str],
    log_fd: int,
    warned: set[str],
) -> None:
    if not _python311_available(runner, cwd=cwd, env=env):
        if "py-test" not in warned:
            _write_log(log_fd=log_fd, text="WARNING: python3 >= 3.11 not found — skipping py-test direct relevant target\n")
            warned.add("py-test")
        return
    if not _pytest_available(runner, cwd=cwd, env=env):
        if "py-test" not in warned:
            _write_log(log_fd=log_fd, text="WARNING: python3 pytest not found — skipping py-test direct relevant target\n")
            warned.add("py-test")
        return
    _append_once(items=targets, item="py-test")


_HARNESS_PARTITION_TARGET: Final = "test-harness-shards-coverage"


def _enforced_partition_files(repo: Path) -> frozenset[str]:
    """Read the strict-partition ENFORCED tuple from the harness guard.

    Single source of truth is ``scripts/lint-harness-pytest-partition.py``; parse
    it with ``ast`` (no code execution). Return an empty set on any read/parse
    failure so a missing or malformed guard never blocks relevant checks.
    """
    guard = repo / "scripts" / "lint-harness-pytest-partition.py"
    try:
        tree = ast.parse(guard.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError, SyntaxError):
        return frozenset()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "ENFORCED" for target in node.targets):
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List)):
            return frozenset()
        files: set[str] = set()
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                files.add(elt.value)
        return frozenset(files)
    return frozenset()


def _append_partition_guard_target(  # noqa: PLR0913,RUF100
    *, runner: Runner,
    targets: list[str],
    cwd: str,
    env: dict[str, str],
    log_fd: int,
    warned: set[str],
) -> None:
    """Append the harness partition guard target (gated on py3.11 + pytest).

    The guard runs ``pytest --co`` per harness selection, so it needs the same
    toolchain as ``py-test``; gate identically to avoid spurious local failures.
    """
    if not _python311_available(runner, cwd=cwd, env=env):
        if "harness-partition" not in warned:
            _write_log(log_fd=log_fd, text="WARNING: python3 >= 3.11 not found — skipping test-harness-shards-coverage relevant target\n")
            warned.add("harness-partition")
        return
    if not _pytest_available(runner, cwd=cwd, env=env):
        if "harness-partition" not in warned:
            _write_log(log_fd=log_fd, text="WARNING: python3 pytest not found — skipping test-harness-shards-coverage relevant target\n")
            warned.add("harness-partition")
        return
    _append_once(items=targets, item=_HARNESS_PARTITION_TARGET)


def _direct_targets(
    *, runner: Runner,
    changed: tuple[str, ...],
    cwd: str,
    env: dict[str, str],
    log_fd: int,
) -> tuple[str, ...]:
    targets: list[str] = []
    warned: set[str] = set()
    for path in changed:
        for patterns, rule_targets, wants_py_lint, wants_py_test in _DIRECT_TARGET_RULES:
            if not _patterns_match(path=path, patterns=patterns):
                continue
            for target in rule_targets:
                _append_once(items=targets, item=target)
            if wants_py_lint:
                _append_py_lint_target(runner=runner, targets=targets, cwd=cwd, env=env, log_fd=log_fd, warned=warned)
            if wants_py_test:
                _append_py_test_target(runner=runner, targets=targets, cwd=cwd, env=env, log_fd=log_fd, warned=warned)
    # An ENFORCED multi-target pytest file changed: run the strict-partition guard
    # locally so an uncovered new test fails before CI rather than only in CI and
    # forcing the autonomous CI-fix loop (issue #4867 secondary).
    enforced = _enforced_partition_files(Path(cwd))
    if enforced and any(path in enforced for path in changed):
        _append_partition_guard_target(runner=runner, targets=targets, cwd=cwd, env=env, log_fd=log_fd, warned=warned)
    return tuple(targets)


_MAKE_TARGET_RE: Final = re.compile(r"^([A-Za-z0-9_.-]+)\s*:")


def _make_targets(repo: Path) -> set[str] | None:
    makefile = repo / "Makefile"
    if not makefile.is_file() or makefile.is_symlink():
        return None
    targets: set[str] = set()
    for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
        match: re.Match[str] | None = _MAKE_TARGET_RE.match(line)
        if match and not match.group(1).startswith("."):
            targets.add(match.group(1))
    return targets


def _filter_defined_make_targets(*, repo: Path, targets: tuple[str, ...], log_fd: int) -> tuple[str, ...]:
    defined = _make_targets(repo)
    if defined is None:
        return targets
    filtered = tuple(target for target in targets if target in defined)
    missing = tuple(target for target in targets if target not in defined)
    if missing:
        _write_log(log_fd=log_fd, text=f"\nWARNING: skipping undefined direct make target(s): {' '.join(missing)}\n")
    return filtered


def _run_agent_lint(runner: Runner, *, cwd: str, log_fd: int, env: dict[str, str]) -> int | None:
    if _command_available(runner=runner, name="agent-lint", cwd=cwd, env=env):
        _write_log(log_fd=log_fd, text="\n=== Running agent-lint ===\n")
        result = _run_logged(runner=runner, argv=["agent-lint", "--pedantic", cwd], cwd=cwd, log_fd=log_fd, env=env)
        return result.returncode
    _write_log(log_fd=log_fd, text="\nWARNING: agent-lint not found on PATH — skipping\n")
    return None


def _redact_log(*, log_file: Path, redacted_file: Path) -> bool:
    log_text = read_log_file_text(log_file)
    if log_text is None:
        return False
    try:
        _ = redacted_file.write_text(redact.redact(log_text), encoding="utf-8")
        redacted_file.chmod(0o600)
    except OSError:
        with contextlib.suppress(OSError):
            redacted_file.unlink(missing_ok=True)
        return False
    return True


@dataclass
class _ChecksFailureDigestRecord:
    check: str
    failure_count: int = 0
    first_location: str = "unknown"
    first_error: str = "unknown"


@dataclass
class _ChecksFailureDigestParseState:
    records: dict[str, _ChecksFailureDigestRecord]
    current_check: str = "unknown"
    fallback_line: str = ""
    pending_location: str | None = None
    pending_error_line: str = ""


def _utf8_prefix(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _digest_line(text: str) -> str:
    return _utf8_prefix(text.strip().replace("\r", ""), _CHECKS_FAILURE_DIGEST_ERROR_MAX_BYTES) or "unknown"


def _direct_digest_check(header_targets: str) -> str:
    targets = tuple(target for target in header_targets.split() if target)
    if len(targets) == 1:
        return targets[0]
    return "direct-make"


def _precommit_digest_check(line: str) -> str | None:
    match = _CHECKS_FAILURE_DIGEST_PRECOMMIT_RE.match(line)
    if match is None:
        return None
    return match.group(1).strip(" .") or None


def _digest_check_for_line(line: str, current_check: str) -> str:
    if line.startswith("DEFECT:"):
        return "contains-pins"
    precommit_check = _precommit_digest_check(line)
    if precommit_check:
        return precommit_check
    if "pre-commit not found" in line:
        return "pre-commit"
    return current_check


def _digest_header_context(line: str, current_check: str) -> tuple[str, bool]:
    direct_match = _CHECKS_FAILURE_DIGEST_DIRECT_RE.match(line)
    if "=== Running pre-commit" in line:
        return "pre-commit", True
    if direct_match is not None:
        return _direct_digest_check(direct_match.group(1)), True
    if line == "=== Running agent-lint ===":
        return "agent-lint", True
    return current_check, False


def _record_for_check(
    records: dict[str, _ChecksFailureDigestRecord],
    check: str,
) -> _ChecksFailureDigestRecord:
    record = records.get(check)
    if record is None:
        record = _ChecksFailureDigestRecord(check=check)
        records[check] = record
    return record


def _apply_digest_location(
    record: _ChecksFailureDigestRecord,
    *,
    line: str,
    pending_location: str | None,
) -> None:
    if record.first_location != "unknown":
        return
    location_match = _CHECKS_FAILURE_DIGEST_LOCATION_RE.search(line)
    if location_match is not None:
        record.first_location = f"{location_match.group(1)}:{location_match.group(2)}"
    elif pending_location is not None:
        record.first_location = pending_location


@dataclass(frozen=True)
class _DigestLineContext:
    line: str
    marker_match: re.Match[str] | None
    pending_location: str | None = None
    is_precommit_banner: bool = False
    is_error_evidence: bool = False


def _update_digest_record(
    records: dict[str, _ChecksFailureDigestRecord],
    *,
    check: str,
    context: _DigestLineContext,
) -> None:
    record = _record_for_check(records, check)
    _apply_digest_location(record, line=context.line, pending_location=context.pending_location)
    if context.is_precommit_banner:
        record.failure_count += 1
        return
    if context.marker_match is None:
        location_match = _CHECKS_FAILURE_DIGEST_LOCATION_RE.search(context.line)
        if (context.is_error_evidence or location_match is not None) and record.first_error == "unknown":
            record.first_error = _digest_line(context.line)
        return
    record.failure_count += 1
    if record.first_error == "unknown":
        record.first_error = _digest_line(context.line)


def _digest_record_group(record: _ChecksFailureDigestRecord) -> str:
    return (
        f"check={record.check}\n"
        f"failure_count={record.failure_count}\n"
        f"first_location={record.first_location}\n"
        f"first_error={record.first_error}\n"
    )


def _checks_failure_digest_header(*, site: str, truncated: bool) -> str:
    return (
        "CHECKS_FAILURE_DIGEST v1\n"
        f"site={site}\n"
        f"digest_truncated={'true' if truncated else 'false'}\n"
    )


def _is_checks_failure_error_evidence(line: str) -> bool:
    return (
        _CHECKS_FAILURE_DIGEST_LINT_ROW_RE.search(line) is not None
        or _CHECKS_FAILURE_DIGEST_MAKE_ERROR_RE.search(line) is not None
    )


def _flush_pending_digest_record(
    records: dict[str, _ChecksFailureDigestRecord],
    *,
    check: str,
    pending_location: str | None,
    pending_error_line: str,
) -> None:
    if check in records or not pending_error_line:
        return
    record = _record_for_check(records, check)
    if pending_location is not None:
        record.first_location = pending_location
    record.first_error = _digest_line(pending_error_line)


def _flush_and_reset_pending_digest_state(state: _ChecksFailureDigestParseState) -> None:
    _flush_pending_digest_record(
        state.records,
        check=state.current_check,
        pending_location=state.pending_location,
        pending_error_line=state.pending_error_line,
    )
    state.pending_location = None
    state.pending_error_line = ""


def _handle_digest_header_line(state: _ChecksFailureDigestParseState, line: str) -> bool:
    next_check, is_header = _digest_header_context(line, state.current_check)
    if not is_header:
        state.current_check = next_check
        return False
    _flush_and_reset_pending_digest_state(state)
    state.current_check = next_check
    return True


def _handle_precommit_digest_line(state: _ChecksFailureDigestParseState, line: str) -> bool:
    precommit_check = _precommit_digest_check(line)
    if precommit_check is None:
        return False
    if precommit_check != state.current_check:
        _flush_and_reset_pending_digest_state(state)
    state.current_check = precommit_check
    _update_digest_record(
        state.records,
        check=precommit_check,
        context=_DigestLineContext(line=line, marker_match=None, is_precommit_banner=True),
    )
    return True


def _handle_defect_digest_context(state: _ChecksFailureDigestParseState, line: str) -> None:
    if not line.startswith("DEFECT:"):
        return
    if state.current_check != "contains-pins":
        _flush_and_reset_pending_digest_state(state)
    state.current_check = "contains-pins"


def _capture_pending_digest_location(state: _ChecksFailureDigestParseState, line: str) -> None:
    location_match = _CHECKS_FAILURE_DIGEST_LOCATION_RE.search(line)
    if location_match is None:
        return
    state.pending_location = f"{location_match.group(1)}:{location_match.group(2)}"
    if not state.pending_error_line:
        state.pending_error_line = line


def _record_digest_marker_or_evidence(
    state: _ChecksFailureDigestParseState,
    *,
    line: str,
    check: str,
    marker_match: re.Match[str] | None,
) -> None:
    if marker_match is not None:
        if not state.fallback_line:
            state.fallback_line = line
        _update_digest_record(
            state.records,
            check=check,
            context=_DigestLineContext(line=line, marker_match=marker_match, pending_location=state.pending_location),
        )
        state.pending_location = None
        state.pending_error_line = ""
        return
    if _is_checks_failure_error_evidence(line):
        if not state.fallback_line:
            state.fallback_line = line
        creates_record = check not in state.records
        _update_digest_record(
            state.records,
            check=check,
            context=_DigestLineContext(
                line=line,
                marker_match=None,
                pending_location=state.pending_location,
                is_error_evidence=True,
            ),
        )
        if creates_record:
            state.records[check].failure_count += 1
        return
    if check in state.records:
        _update_digest_record(
            state.records,
            check=check,
            context=_DigestLineContext(line=line, marker_match=None, pending_location=state.pending_location),
        )


def _parse_checks_failure_records(
    redacted_log_text: str,
) -> dict[str, _ChecksFailureDigestRecord]:
    state = _ChecksFailureDigestParseState(records={})
    for line in redacted_log_text.splitlines():
        if _handle_digest_header_line(state, line):
            continue

        if _handle_precommit_digest_line(state, line):
            continue

        _handle_defect_digest_context(state, line)
        _capture_pending_digest_location(state, line)
        marker_match = _CHECKS_FAILURE_DIGEST_MARKER_RE.search(line)
        check = _digest_check_for_line(line, state.current_check)
        _record_digest_marker_or_evidence(state, line=line, check=check, marker_match=marker_match)

    _flush_and_reset_pending_digest_state(state)
    if not state.records:
        record = _record_for_check(state.records, "unknown")
        record.first_error = _digest_line(state.fallback_line) if state.fallback_line else "unknown"
    return state.records


def _assemble_checks_failure_digest(
    *, records: dict[str, _ChecksFailureDigestRecord], site: str
) -> str:
    body_groups = [_digest_record_group(record) for record in records.values()]
    selected: list[str] = []
    truncated = False
    header = _checks_failure_digest_header(site=site, truncated=False)
    for group in body_groups:
        candidate = header + "".join(selected) + group
        if len(candidate.encode("utf-8")) > CHECKS_FAILURE_DIGEST_MAX_BYTES:
            truncated = True
            break
        selected.append(group)
    header = _checks_failure_digest_header(site=site, truncated=truncated)
    digest = header + "".join(selected)
    if len(digest.encode("utf-8")) <= CHECKS_FAILURE_DIGEST_MAX_BYTES:
        return digest
    return _utf8_prefix(digest, CHECKS_FAILURE_DIGEST_MAX_BYTES)


def _build_checks_failure_digest(*, redacted_log_text: str, site: str) -> str:
    records = _parse_checks_failure_records(redacted_log_text)
    return _assemble_checks_failure_digest(records=records, site=site)


def _write_failure_digest_from_redacted(
    *,
    redacted_file: Path,
    site: str,
    attempt: str,
    log_dir: Path,
) -> str | None:
    redacted_text = read_log_file_text(redacted_file)
    if redacted_text is None:
        return None
    digest_file = log_dir / f"{site}-{attempt}.digest.txt"
    try:
        digest = _build_checks_failure_digest(redacted_log_text=redacted_text, site=site)
        _ = digest_file.write_text(digest, encoding="utf-8")
        digest_file.chmod(0o600)
    except OSError:
        with contextlib.suppress(OSError):
            digest_file.unlink(missing_ok=True)
        return None
    return str(digest_file)


def _is_no_validation_phases_log(log_file: Path) -> bool:
    text = read_log_file_text(log_file)
    return text is not None and "ERROR: no validation phases ran" in text


def _finish_logged_result(
    *,
    result_code: int,
    site: str,
    log_file: Path,
    log_dir: Path,
    warn_override: str | None = None,
) -> ChecksResult:
    has_precommit, has_agent_lint, has_warn = _scan_checks_log_markers(log_file)
    ok = result_code == 0
    coverage = _coverage_from_markers(ok=ok, has_precommit=has_precommit, has_agent_lint=has_agent_lint)
    phase = _phase_from_markers(ok=ok, has_precommit=has_precommit, has_agent_lint=has_agent_lint)
    warn = warn_override or ("agent-lint-missing" if has_warn else None)
    if result_code == 2 and _is_no_validation_phases_log(log_file):  # noqa: PLR2004
        attempt = log_file.name.rsplit("-", 1)[-1].removesuffix(".log")
        redacted_file = log_dir / f"{site}-{attempt}.redacted.log"
        redacted_path = str(redacted_file) if _redact_log(log_file=log_file, redacted_file=redacted_file) else None
        digest_path = (
            _write_failure_digest_from_redacted(
                redacted_file=redacted_file,
                site=site,
                attempt=attempt,
                log_dir=log_dir,
            )
            if redacted_path is not None
            else None
        )
        return _checks_failure(
            site=site,
            exit_code=2,
            reason="no-validation-phases",
            raw_log_path=str(log_file),
            redacted_log_path=redacted_path,
            phase="none",
            coverage="none",
            warn=warn,
            digest_file_path=digest_path,
        )
    if ok:
        return ChecksResult(
            ok=True,
            exit_code=0,
            site=site,
            redacted_log_path=None,
            phase=phase,
            coverage=coverage,
            skipped=False,
            warn=warn,
            raw_log_path=str(log_file),
        )
    attempt = log_file.name.rsplit("-", 1)[-1].removesuffix(".log")
    redacted_file = log_dir / f"{site}-{attempt}.redacted.log"
    if not _redact_log(log_file=log_file, redacted_file=redacted_file):
        return _checks_failure(
            site=site,
            exit_code=1,
            reason="redaction-failed",
            phase=phase,
            coverage=coverage,
            warn="redaction-failed",
        )
    digest_path = _write_failure_digest_from_redacted(
        redacted_file=redacted_file,
        site=site,
        attempt=attempt,
        log_dir=log_dir,
    )
    return _checks_failure(
        site=site,
        exit_code=result_code,
        reason="checks-failed",
        raw_log_path=str(log_file),
        redacted_log_path=str(redacted_file),
        phase=phase,
        coverage=coverage,
        warn=warn,
        digest_file_path=digest_path,
    )


def _run_contains_pin_phase(*, repo: Path, changed: tuple[str, ...], log_fd: int) -> int:
    changed_file: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            changed_file = Path(handle.name)
            for path in changed:
                _ = handle.write(f"{path}\n")
        with contextlib.redirect_stdout(_FdTextWriter(log_fd)), contextlib.redirect_stderr(_FdTextWriter(log_fd)):
            return check_contains_pins_main(["--changed-files", str(changed_file), "--repo-root", str(repo)])
    finally:
        if changed_file is not None:
            with contextlib.suppress(OSError):
                changed_file.unlink()


class _FdTextWriter:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def write(self, text: str) -> int:
        _write_log(log_fd=self.fd, text=text)
        return len(text)

    def flush(self) -> None:
        return None


def _run_relevant_checks_inner(  # noqa: PLR0911,PLR0912,PLR0915,RUF100
    runner: Runner,
    *,
    repo: Path,
    log_fd: int,
) -> int:
    env = _clean_child_env()
    cwd = str(repo)
    phases_run = 0

    changed = _changed_files(runner, cwd=cwd)
    if not changed:
        _write_log(log_fd=log_fd, text="No modified files detected — running full-repo post-checks if available.\n")
        agent_rc = _run_agent_lint(runner, cwd=cwd, log_fd=log_fd, env=env)
        if agent_rc is not None:
            phases_run += 1
            rc = agent_rc
        else:
            rc = 0
        if phases_run == 0:
            _write_log(log_fd=log_fd, text="\nERROR: no validation phases ran — pre-commit had no eligible files (no changes, or no regular files for pre-commit) and agent-lint was unavailable or skipped.\n")
            return 2
        return rc

    regular = _existing_regular_files(repo=repo, paths=changed)
    if not regular:
        _write_log(log_fd=log_fd, text="No existing regular files to pass to pre-commit.\n")
        targets = _direct_targets(runner=runner, changed=changed, cwd=cwd, env=env, log_fd=log_fd)
        targets = _filter_defined_make_targets(repo=repo, targets=targets, log_fd=log_fd)
        direct_ran = False
        if targets:
            _write_log(log_fd=log_fd, text=f"\n=== Running direct relevant make target(s): {' '.join(targets)} ===\n")
            make_result = _run_logged(runner=runner, argv=["make", *targets], cwd=cwd, log_fd=log_fd, env=env)
            phases_run += 1
            direct_ran = True
            if make_result.returncode != 0:
                return make_result.returncode
        pins_rc = _run_contains_pin_phase(repo=repo, changed=changed, log_fd=log_fd)
        if pins_rc != 0:
            return pins_rc
        agent_rc = _run_agent_lint(runner, cwd=cwd, log_fd=log_fd, env=env)
        if agent_rc is not None:
            phases_run += 1
            rc = agent_rc
        else:
            rc = 0
        if not direct_ran and agent_rc is None:
            _write_log(log_fd=log_fd, text="\nERROR: no validation phases ran — pre-commit had no eligible files (no changes, or no regular files for pre-commit) and agent-lint was unavailable or skipped.\n")
            return 2
        return rc

    if not _command_available(runner=runner, name="pre-commit", cwd=cwd, env=env):
        _write_log(log_fd=log_fd, text="ERROR: pre-commit not found. Run: pip install pre-commit (or: make setup)\n")
        return 1

    _write_log(log_fd=log_fd, text=f"=== Running pre-commit on {len(regular)} changed file(s) ===\n")
    precommit = _run_logged(runner=runner, argv=["pre-commit", "run", "--files", *regular], cwd=cwd, log_fd=log_fd, env=env)
    if precommit.returncode != 0:
        return precommit.returncode
    phases_run += 1

    targets = _direct_targets(runner=runner, changed=changed, cwd=cwd, env=env, log_fd=log_fd)
    targets = _filter_defined_make_targets(repo=repo, targets=targets, log_fd=log_fd)
    if targets:
        _write_log(log_fd=log_fd, text=f"\n=== Running direct relevant make target(s): {' '.join(targets)} ===\n")
        make_result = _run_logged(runner=runner, argv=["make", *targets], cwd=cwd, log_fd=log_fd, env=env)
        phases_run += 1
        if make_result.returncode != 0:
            return make_result.returncode

    pins_rc = _run_contains_pin_phase(repo=repo, changed=changed, log_fd=log_fd)
    phases_run += 1
    if pins_rc != 0:
        return pins_rc

    agent_rc = _run_agent_lint(runner, cwd=cwd, log_fd=log_fd, env=env)
    if agent_rc is not None:
        phases_run += 1
        if agent_rc != 0:
            return agent_rc
    return 0


def run_relevant_checks(
    runner: Runner,
    *,
    site: str,
    tmpdir: str,
    repo_root: str,
) -> ChecksResult:
    """Run relevant checks natively and capture a redacted failure log."""
    if (
        not site
        or not re.fullmatch(r"[A-Za-z0-9._-]+", site)
        or site.startswith(".")
        or ".." in site
    ):
        return _checks_failure(site=site, exit_code=2, reason="site-validation")
    canonical_tmp = validate_tmpdir(tmpdir)
    if canonical_tmp is None:
        return _checks_failure(site=site, exit_code=2, reason="tmpdir-validation")
    outcome: ChecksResult | None = None
    start_s = int(time.time())
    try:
        outcome = _run_relevant_checks_impl(
            runner,
            site=site,
            tmpdir=tmpdir,
            repo_root=repo_root,
        )
    finally:
        end_s = int(time.time())
        exit_code = outcome.exit_code if outcome is not None else 1
        record_checks_vendor_task(
            runner=runner,
            canonical_tmp=canonical_tmp,
            task_kind="claude-relevant-checks",
            start_s=start_s,
            end_s=end_s,
            output_basename="claude-relevant-checks.txt",
            exit_code=exit_code,
            status="complete",
        )
    assert outcome is not None
    return outcome


def _run_relevant_checks_impl(  # noqa: PLR0911,RUF100
    runner: Runner,
    *,
    site: str,
    tmpdir: str,
    repo_root: str,
) -> ChecksResult:
    if (
        not site
        or not re.fullmatch(r"[A-Za-z0-9._-]+", site)
        or site.startswith(".")
        or ".." in site
    ):
        return _checks_failure(site=site, exit_code=2, reason="site-validation")
    canonical_tmp = validate_tmpdir(tmpdir)
    if canonical_tmp is None:
        return _checks_failure(site=site, exit_code=2, reason="tmpdir-validation")
    _mark_step_ledger(runner=runner, canonical_tmp=canonical_tmp, site=site)
    repo = _resolve_repo_root(runner=runner, repo_root=repo_root)
    if repo is None:
        return _checks_failure(site=site, exit_code=1, reason="repo-root-unresolved")
    log_dir = canonical_tmp / "relevant-checks"
    try:
        log_dir.mkdir(mode=0o700, exist_ok=True)
    except OSError:
        return _checks_failure(site=site, exit_code=1, reason="log-dir-create-failed")
    if log_dir.is_symlink():
        return _checks_failure(site=site, exit_code=1, reason="log-dir-symlink-rejected")
    try:
        log_dir.chmod(0o700)
    except OSError:
        return _checks_failure(site=site, exit_code=1, reason="log-dir-chmod-failed")
    allocated = _allocate_log_file(log_dir=log_dir, site=site)
    if allocated is None:
        return _checks_failure(site=site, exit_code=1, reason="log-alloc-failed")
    log_fd, log_file = allocated
    try:
        try:
            rc = _run_relevant_checks_inner(
                runner,
                repo=repo,
                log_fd=log_fd,
            )
        except Exception as exc:  # fail closed and retain the captured diagnostic
            _write_log(log_fd=log_fd, text=f"ERROR: relevant checks internal failure: {exc}\n")
            rc = 1
        if not log_file.is_file() or log_file.is_symlink() or log_file.parent.resolve() != log_dir.resolve():
            return _checks_failure(site=site, exit_code=1, reason="log-validation-failed")
    finally:
        with contextlib.suppress(OSError):
            os.close(log_fd)
    return _finish_logged_result(result_code=rc, site=site, log_file=log_file, log_dir=log_dir)


def _normalize_rel(*, path: str, repo_root: Path) -> str:
    raw = path
    root_text = str(repo_root)
    if raw.startswith(root_text + os.sep):
        raw = raw.removeprefix(root_text + os.sep)
    raw = raw.removeprefix("./")
    parts: list[str] = []
    for part in raw.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                _ = parts.pop()
            else:
                parts.append(part)
        else:
            parts.append(part)
    return "/".join(parts)


def _read_changed_scope(*, path: Path | None, repo_root: Path) -> set[str] | None:
    if path is None:
        return None
    rels: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if raw:
            rels.add(_normalize_rel(path=raw, repo_root=repo_root))
    return rels



def _assertion_in_scope(*, script: str, target: str | None, changed: set[str] | None) -> bool:
    if changed is None:
        return True
    if script in changed:
        return True
    return bool(target and target in changed)


_REPO_ASSIGN_RE: Final = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)="\$REPO_ROOT/([^"]*)"\s*$')
_SCRIPT_ASSIGN_RE: Final = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)="\$SCRIPT_DIR/\.\./([^"]*)"\s*$')
_CONTAINS_PREFIX_RE: Final = re.compile(r'^\s*contains\s+"\$([A-Za-z_][A-Za-z0-9_]*)"\s+')
_DOUBLE_QUOTED_LITERAL_ESCAPES: Final = frozenset(("$", '"', "\\"))


def _scan_shell_quoted_literal(rest: str) -> tuple[str | None, bool]:
    if not rest:
        return None, False
    quote = rest[0]
    if quote == "'":
        end = rest.find("'", 1)
        if end < 0:
            return None, False
        literal = rest[1:end]
        suffix = rest[end + 1:]
        return (literal, True) if suffix[:1].isspace() else (None, False)
    if quote != '"':
        return None, False
    body: list[str] = []
    escaped = False
    bare_dollar = False
    for index, char in enumerate(rest[1:], start=1):
        if escaped:
            if char in _DOUBLE_QUOTED_LITERAL_ESCAPES:
                body.append(char)
            else:
                body.append("\\")
                body.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "$":
            bare_dollar = True
            body.append(char)
            continue
        if char == '"':
            suffix = rest[index + 1:]
            if bare_dollar or not suffix[:1].isspace():
                return None, False
            return "".join(body), True
        body.append(char)
    return None, False


def _scan_contains_pin_script(  # noqa: C901,PLR0911,PLR0912,RUF100
    script: Path,
    *,
    repo_root: Path,
    changed: set[str] | None,
) -> int:
    script_rel = _normalize_rel(path=str(script), repo_root=repo_root)
    script_dir = Path(script_rel).parent
    script_parent = script_dir.parent if str(script_dir) != "." else Path()
    vars_to_rel: dict[str, str] = {}
    defects = 0
    for line_no, line in enumerate(script.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        repo_assign: re.Match[str] | None = _REPO_ASSIGN_RE.match(line)
        if repo_assign:
            vars_to_rel[repo_assign.group(1)] = _normalize_rel(path=repo_assign.group(2), repo_root=repo_root)
            continue
        script_assign: re.Match[str] | None = _SCRIPT_ASSIGN_RE.match(line)
        if script_assign:
            raw = str(script_parent / script_assign.group(2)) if str(script_parent) else script_assign.group(2)
            vars_to_rel[script_assign.group(1)] = _normalize_rel(path=raw, repo_root=repo_root)
            continue
        contains: re.Match[str] | None = _CONTAINS_PREFIX_RE.match(line)
        if not contains:
            continue
        var = contains.group(1)
        target_rel: str | None = vars_to_rel.get(var)
        literal, canonical = _scan_shell_quoted_literal(line[contains.end():])
        if not canonical:
            if _assertion_in_scope(script=script_rel, target=target_rel, changed=changed):
                print(f"SKIPPED_NON_CANONICAL: {script_rel}:{line_no}: assertion shape not in v1 grammar", file=sys.stderr)
            continue
        if target_rel is None:
            if _assertion_in_scope(script=script_rel, target=target_rel, changed=changed):
                print(f"UNRESOLVED_VAR: {script_rel}:{line_no}: could not resolve ${var}", file=sys.stderr)
            continue
        if not _assertion_in_scope(script=script_rel, target=target_rel, changed=changed):
            continue
        assert literal is not None
        target = (repo_root / target_rel).resolve()
        try:
            _ = target.relative_to(repo_root.resolve())
        except ValueError:
            print(f"UNRESOLVED_VAR: {script_rel}:{line_no}: could not resolve ${var}", file=sys.stderr)
            continue
        if not target.is_file() or target.is_symlink():
            print(f"UNRESOLVED_VAR: {script_rel}:{line_no}: could not resolve ${var}", file=sys.stderr)
            continue
        if literal not in target.read_text(encoding="utf-8", errors="replace"):
            print(f"DEFECT: {script_rel}:{line_no}: literal '{literal}' not found in {target_rel}")
            defects += 1
    return defects


def _contains_pin_test_scripts(repo_root: Path) -> tuple[Path, ...]:
    scripts: list[Path] = []
    root_scripts = repo_root / "scripts"
    if root_scripts.is_dir():
        scripts.extend(sorted(root_scripts.glob("test-*.sh")))
    skills = repo_root / "skills"
    if skills.is_dir():
        scripts.extend(sorted(skills.glob("*/scripts/test-*.sh")))
    return tuple(path for path in scripts if path.is_file())


def check_contains_pins_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py checks contains-pins")
    _ = parser.add_argument("--changed-files", default="")
    _ = parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    if not repo_root.is_dir():
        print(f"ERROR: --repo-root is not a directory: {repo_root}", file=sys.stderr)
        return 2
    changed_path = Path(args.changed_files) if args.changed_files else None
    if changed_path is not None and not changed_path.is_file():
        print(f"ERROR: --changed-files path not found: {changed_path}", file=sys.stderr)
        return 2
    changed = _read_changed_scope(path=changed_path, repo_root=repo_root)
    defects = 0
    for script in _contains_pin_test_scripts(repo_root):
        defects += _scan_contains_pin_script(script, repo_root=repo_root, changed=changed)
    print(f"DEFECTS={defects}")
    return 1 if defects else 0


def default_repo_root() -> str:
    raw = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if raw:
        return raw
    result = proc.run(["git", "rev-parse", "--show-toplevel"], cwd=str(Path.cwd()))
    return result.stdout.strip() if result.returncode == 0 else ""


def checks_run_relevant_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py checks run-relevant")
    _ = parser.add_argument("--site", required=True)
    _ = parser.add_argument("--tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", os.environ.get("REVIEW_TMPDIR", "")))
    _ = parser.add_argument("--repo-root", default="")
    _ = parser.add_argument("--allow-skip", action="store_true")
    args = parser.parse_args(argv)
    repo_root = args.repo_root or default_repo_root()
    result = run_relevant_checks(proc, site=args.site, tmpdir=args.tmpdir, repo_root=repo_root)
    if result.skipped and args.allow_skip:
        print(f"RELEVANT_CHECKS_SKIPPED=true SITE={result.site}")
        return 0
    if result.ok:
        line = f"RELEVANT_CHECKS_OK=true SITE={result.site} COVERAGE={result.coverage} PHASE={result.phase}"
        if result.warn:
            line += f" WARN={result.warn}"
        print(line)
        return 0
    reason = result.failure_reason or "checks-failed"
    parts = ["STATUS=fail", f"FAILURE_REASON={reason}"]
    if result.redacted_log_path:
        parts.extend([
            f"EXIT_CODE={result.exit_code}",
            f"PHASE={result.phase}",
        ])
        if result.digest_file_path:
            parts.append(f"DIGEST_FILE={result.digest_file_path}")
        parts.extend([
            f"REDACTED_LOG_FILE={result.redacted_log_path}",
        ])
    print(" ".join(parts))
    return result.exit_code or 1
