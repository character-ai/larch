"""Python CLI entrypoint for committed /design run-log publishing."""

from __future__ import annotations

import contextlib
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Sequence

from larch.core import redact
from larch.design import design_publish
from larch.design.design_summary import _resolve_summary_mode

_PR_URL_RE = re.compile(r"/pull/([0-9]+)")
_RUN_LOG_COMMIT_SCRUB_FAILURE_RE = re.compile(
    r"(secret survived scrubbing|scrub_log_secrets|scrub-log-secrets|scrubber|scrub_error)",
    re.IGNORECASE,
)


class SecretScrubFailure(RuntimeError):
    """Raised when a publish path cannot prove secret scrubbing succeeded."""


def _emit(*, k: str, v: str) -> None:
    print(f"{k}={v}")


def _validate_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value))


def _validate_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", value))


def _persist_metadata(*, design_tmpdir: Path, pr_number: str, pr_url: str, recovery_branch: str) -> None:
    with contextlib.suppress(OSError):
        _ = (design_tmpdir / ".design-log-publish-metadata.env").write_text(
            f"DESIGN_LOG_PR_NUMBER={pr_number}\nDESIGN_LOG_PR_URL={pr_url}\nDESIGN_LOG_RECOVERY_BRANCH={recovery_branch}\n",
            encoding="utf-8",
        )


# Raw machine sidecars/transcripts the /design lanes drop into $DESIGN_TMPDIR.
# They are launch carriers, not human-facing run content: a single Codex
# `.events.jsonl` event stream is ~770 KB per lane, and the committed design log
# ballooned ~40x (8.6 MB/run vs ~0.2 MB/run before) once that capture landed and
# the publish copied them. The pre-port bash publisher (`design-log-publish.sh`,
# `design_artifact_excluded`) excluded exactly this class; the Python port
# (#3681 / #4404) dropped the filter and copied the whole tmpdir, regressing the
# behavior SECURITY.md still documents. This restores that exclusion.
#
# The filter is applied by basename at every tree depth (top level and inside
# `plan-review/round-N/`), so it intentionally lists ONLY universal-crud carriers
# that never appear as curated content. The bash predicate also deduped
# human-readable top-level copies (`findings.md`, `voting-tally.md`,
# `*-vote-output.txt`, `round-meta.json`) that are canonical in the subtree;
# those are NOT listed here because a basename rule cannot tell the top-level
# duplicate from the curated subtree copy, and keeping the small duplicate is
# harmless. Curated forensics (plan.txt, findings.md, voting-tally.md,
# `*-vote-output.txt`, the plan-review/round-N/ subtree) are preserved.
_PUBLISH_EXCLUDE_SUFFIXES = (
    ".events.jsonl",
    ".events.history",
    ".prompt",
    ".meta",
    ".sidecar",
    ".sidecar.history",
    ".token-record",
    ".dirty-tree",
    ".untracked-baseline",
    ".diag",
    ".done",
    ".cap-hit",
    ".launch-stderr",
    ".launcher-stderr",
    ".stderr-tail",
    ".porcelain",
    ".txt.json",
    ".txt.tsv",
)

# Glob-matched basenames. `*-plan-*-output*.txt` is the raw per-lane reviewer /
# voter / drafter transcript (cursor-plan-*, codex-primary-plan-*, claude-plan-*,
# their dyn-* and -phase/-retry variants); it deliberately spares
# `aggregator-output.txt` (no `-plan-`) and the curated `*-vote-output.txt` (no
# `-plan-`). `*-plan-*-output*.txt.*` sweeps any sidecar of those transcripts not
# already caught by suffix. The rest are prompt carriers, the step2b drafter raw
# family, slot-named collector failure logs, and raw scout stems.
_PUBLISH_EXCLUDE_GLOBS = (
    "*-plan-*-output*.txt",
    "*-plan-*-output*.txt.*",
    "*-prompt.txt",
    "*-prompt.md",
    "step2b-codex-raw.*",
    "*-collector.failure.log",
    "*-diagram-failure.bounded.log",
    "*.raw.cursor",
    "*.raw.claude",
)

# Exact basenames: the aggregate plan-review collector stderr, the dropped-slot
# diagnostic sidecar (both documented in SECURITY.md), and the pre-redaction
# duplicate of composed-plan.md (the publish redacts on copy, so the `.redacted`
# twin adds nothing).
_PUBLISH_EXCLUDE_NAMES = frozenset({
    "plan-review-collector.stderr",
    "plan-review-slots.ndjson.output-files.dropped-slots",
    "composed-plan.redacted.md",
    "findings-ledger.tsv",
    "claude-source.env",
    "source-env.sh",
})

# Whole subtrees of raw transcripts (plan-autofix drafts) or internal step
# sentinels (.completed) that carry no committed-log value.
_PUBLISH_EXCLUDE_DIRS = frozenset({
    "plan-autofix",
    ".completed",
    "larch-logs",
})

# GitHub-redundant snapshots: top-level duplicates of content already on GitHub.
# issue-body.txt / issue.json snapshot the issue body; architecture-diagram*.md,
# architecture-diagram.skipped, and diagram failure captures are consumed by the
# issue-scoped larch:diagrams tail or local repair flow; a top-level
# panel-manifest.ndjson duplicates the per-round panel manifests. Unlike the sets
# above (matched by basename at every tree depth), these are dropped at the TOP
# LEVEL ONLY: panel-manifest.ndjson is a curated file under plan-review/round-N/,
# so a blanket basename rule would wrongly drop the kept subtree copies. Restores
# the pre-#3681 bash filter (Phase 3d / #3721 / #3929).
_PUBLISH_EXCLUDE_TOPLEVEL_NAMES = frozenset({
    "issue-body.txt",
    "issue.json",
    "architecture-diagram.md",
    "architecture-diagram.candidate.md",
    "architecture-diagram.skipped",
    "architecture-diagram-generation.failure.log",
    "architecture-diagram-sanitizer.failure.log",
    "panel-manifest.ndjson",
    "panel-prompt-sizes.tsv",
})


def _publish_excluded(name: str, *, is_dir: bool, top_level: bool = False) -> bool:
    """Return True for raw machine sidecars/transcripts that must not be committed.

    ``name`` is a single path component (basename). Directory names are matched
    against ``_PUBLISH_EXCLUDE_DIRS``; files against the exact-name, suffix, and
    glob sets. When ``top_level`` is set (``name`` sits directly under the design
    tmpdir root), GitHub-redundant snapshots in ``_PUBLISH_EXCLUDE_TOPLEVEL_NAMES``
    are also dropped; nested copies of those basenames are kept so curated subtree
    files survive.
    """
    if is_dir:
        return name in _PUBLISH_EXCLUDE_DIRS
    if top_level and name in _PUBLISH_EXCLUDE_TOPLEVEL_NAMES:
        return True
    if name in _PUBLISH_EXCLUDE_NAMES:
        return True
    if name.endswith(_PUBLISH_EXCLUDE_SUFFIXES):
        return True
    return any(fnmatch.fnmatchcase(name, glob) for glob in _PUBLISH_EXCLUDE_GLOBS)


def _copy_tree_redacted(*, plugin_root: Path, source: Path, dest: Path) -> tuple[bool, int]:
    if source.is_symlink():
        return False, 0
    if source.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        red = subprocess.run(
            [sys.executable, str(plugin_root / "python" / "cli.py"), "redact", "tmpdir-paths"],
            input=source.read_text(encoding="utf-8", errors="replace"),
            text=True,
            capture_output=True,
            check=False,
        )
        if red.returncode != 0:
            raise SecretScrubFailure(
                f"redact tmpdir-paths failed for {source}: {red.stderr.strip()}"
            )
        try:
            scrubbed, findings = redact.scrub_log_secrets(red.stdout)
        except Exception as exc:
            raise SecretScrubFailure(f"secret scrubber failed for {source}") from exc
        if findings:
            try:
                _, residual = redact.scrub_log_secrets(scrubbed)
            except Exception as exc:
                raise SecretScrubFailure(f"secret scrubber failed for {source}") from exc
            if residual:
                print(
                    f"design log-publish: secret survived scrubbing in {source}",
                    file=sys.stderr,
                )
                raise SecretScrubFailure(f"secret survived scrubbing in {source}")
        if scrubbed and not scrubbed.endswith("\n"):
            scrubbed += "\n"
        _ = dest.write_text(scrubbed, encoding="utf-8")
        return True, sum(findings.values())
    if source.is_dir():
        total = 0
        for child in source.iterdir():
            if child.is_symlink():
                continue
            if _publish_excluded(child.name, is_dir=child.is_dir()):
                continue
            ok, count = _copy_tree_redacted(plugin_root=plugin_root, source=child, dest=dest / child.name)
            if not ok:
                return False, total
            total += count
        return True, total
    return True, 0


def _run(argv: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def _default_base_ref(repo_root: str) -> str:
    head = _run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_root)
    target = head.stdout.strip()
    if head.returncode == 0 and target.startswith("origin/"):
        return target.split("/", 1)[1]
    return "main"


def _spawn_detached_admin_merge(*, cli: str, pr_number: str, repo: str, repo_root: str) -> None:
    """Launch the design-log admin-merge waiter as a detached background process.

    Routes the automated log PR through the existing ``ship design-log`` path
    (``design_log_ship.run_design_log_ci_merge``): it polls required CI checks to
    green, then runs ``gh pr merge --admin --squash --delete-branch`` -- bypassing
    the review gate that GitHub-native ``--auto`` can never satisfy for an
    unreviewed automated PR (issue #4524). Detached via ``start_new_session`` so
    the /design orchestrator is not blocked on CI (issue #4404). Best-effort: a
    launch failure leaves the PR open for manual/CI merge.
    """
    argv = [sys.executable, cli, "ship", "design-log", "--pr-number", pr_number]
    if repo:
        argv += ["--repo", repo]
    try:
        _ = subprocess.Popen(  # pylint: disable=consider-using-with
            argv,
            cwd=repo_root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        print(
            f"design log-publish: detached admin-merge launch failed; "
            f"PR #{pr_number} left open for manual/CI merge: {exc}",
            file=sys.stderr,
        )


def _scrub_violations(commit_stdout: str) -> str:
    """Return the SECRET_SCRUB_VIOLATIONS count from ``run-log commit`` stdout.

    Mirrors the retired design-publish.sh parse: the last occurrence wins and a
    missing or non-numeric value defaults to ``"0"``. The committed design log is
    scrubbed before commit, so a non-zero count means a secret-shaped value was
    redacted from the logs and the operator must rotate the exposed credential.
    """
    value = "0"
    for line in commit_stdout.splitlines():
        if line.startswith("SECRET_SCRUB_VIOLATIONS="):
            candidate = line.split("=", 1)[1].strip()
            value = candidate if candidate.isdigit() else "0"
    return value


def _run_log_commit_scrub_failed(commit: subprocess.CompletedProcess[str]) -> bool:
    text = f"{commit.stdout}\n{commit.stderr}"
    return bool(_RUN_LOG_COMMIT_SCRUB_FAILURE_RE.search(text))


def _publish_design_logs(
    *, plugin_root: Path,
    design_tmpdir: Path,
    run_id: str,
    issue: str,
    repo: str,
) -> tuple[bool, str, str, str, str]:
    """Commit the design run tree on a dedicated branch via a disposable worktree, push it, and open a PR.

    Returns ``(publish_ok, pr_number, pr_url, recovery_branch, scrub_violations)``. The operator
    working tree is never touched: every write lands inside the worktree, so the
    next ``/implement`` preflight stays clean even if this fails (issue #4395).
    ``recovery_branch`` is set only when a commit exists but could not be turned
    into a PR, so the operator can finish it manually.
    """
    top = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = top.stdout.strip()
    if top.returncode != 0 or not repo_root:
        return (False, "", "", "", "0")
    branch = f"larch-logs/design-{run_id}"
    cli = str(plugin_root / "python" / "cli.py")
    repo_args = ["--repo", repo] if repo else []
    wt_parent = Path(tempfile.mkdtemp(prefix="larch-design-log-"))
    worktree = wt_parent / "wt"
    branch_created = False
    keep_branch_for_recovery = False
    try:
        add = _run(["git", "worktree", "add", "-b", branch, str(worktree), "HEAD"], cwd=repo_root)
        if add.returncode != 0:
            print(f"design log-publish: worktree add failed: {add.stderr.strip()}", file=sys.stderr)
            return (False, "", "", "", "0")
        branch_created = True
        wt_log_root = worktree / "larch-logs"
        run_dest = wt_log_root / "design" / run_id
        run_dest.mkdir(parents=True, exist_ok=True)
        init = _run(
            [sys.executable, cli, "run-log", "init", "--log-root", str(wt_log_root),
             "--skill", "design", "--run-id", run_id, "--issue", issue],
        )
        if init.returncode != 0:
            return (False, "", "", "", "0")
        pre_scrub_violations = 0
        for child in design_tmpdir.iterdir():
            if child.name == ".design-log-publish-metadata.env":
                continue
            if _publish_excluded(child.name, is_dir=child.is_dir(), top_level=True):
                continue
            ok, scrub_count = _copy_tree_redacted(plugin_root=plugin_root, source=child, dest=run_dest / child.name)
            if not ok:
                return (False, "", "", "", "0")
            pre_scrub_violations += scrub_count
        base_sha = _run(["git", "rev-parse", "HEAD"], cwd=str(worktree)).stdout.strip()
        commit = _run(
            [sys.executable, cli, "run-log", "commit", "--log-root", str(wt_log_root),
             "--skill", "design", "--run-id", run_id, "--pre-scrub-violations", str(pre_scrub_violations)],
            cwd=str(worktree),
        )
        head_sha = _run(["git", "rev-parse", "HEAD"], cwd=str(worktree)).stdout.strip()
        if commit.returncode != 0 or not head_sha or head_sha == base_sha:
            if commit.returncode != 0 and _run_log_commit_scrub_failed(commit):
                raise SecretScrubFailure("run-log commit scrub failure")
            print(f"design log-publish: run-log commit produced no commit: {commit.stderr.strip()}", file=sys.stderr)
            return (False, "", "", "", "0")
        scrub_violations = _scrub_violations(commit.stdout)
        push = _run(["git", "push", "-u", "origin", branch], cwd=str(worktree))
        if push.returncode != 0:
            print(f"design log-publish: push failed; local branch {branch} kept for recovery: {push.stderr.strip()}", file=sys.stderr)
            keep_branch_for_recovery = True
            return (False, "", "", branch, scrub_violations)
        body_file = wt_parent / "pr-body.txt"
        _ = body_file.write_text(
            f"Automated design log directory for run {run_id}. Merged once required CI checks pass.\n",
            encoding="utf-8",
        )
        pr = _run(
            ["gh", "pr", "create", "--head", branch, "--base", _default_base_ref(repo_root),
             "--title", f"chore(larch-logs): design run {run_id}", "--body-file", str(body_file), *repo_args],
            cwd=repo_root,
        )
        if pr.returncode != 0:
            print(f"design log-publish: gh pr create failed; pushed branch {branch} kept for recovery: {pr.stderr.strip()}", file=sys.stderr)
            return (False, "", "", branch, scrub_violations)
        pr_url = pr.stdout.strip().splitlines()[-1] if pr.stdout.strip() else ""
        match: re.Match[str] | None = _PR_URL_RE.search(pr_url)
        pr_number = match.group(1) if match else ""
        # Launch the wait-then-admin-merge waiter detached so the log PR squashes
        # in once required CI checks pass, without stalling the /design orchestrator
        # on CI (preserving the non-blocking goal of #4404). GitHub-native --auto
        # cannot satisfy the active "Code review" ruleset's required-review gate
        # that an unreviewed automated PR never receives, so the log PR is routed
        # through the existing ship design-log path (run_design_log_ci_merge), which
        # waits for required checks then merges with --admin --delete-branch,
        # bypassing only the review gate (#4524). Best-effort: a launch failure
        # leaves the PR open for manual/CI merge and the working tree is already
        # clean either way.
        if pr_number:
            _spawn_detached_admin_merge(cli=cli, pr_number=pr_number, repo=repo, repo_root=repo_root)
        return (True, pr_number, pr_url, "", scrub_violations)
    finally:
        _ = _run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo_root)
        if branch_created and not keep_branch_for_recovery:
            _ = _run(["git", "branch", "-D", branch], cwd=repo_root)
        shutil.rmtree(wt_parent, ignore_errors=True)


def _default_outcome_for_reason(reason: str) -> str:
    return "paused" if reason == "pause" else "approved"


def _render_final_summary_before_copy(
    *,
    design_tmpdir: Path,
    outcome: str,
    issue: str,
    repo: str,
    run_id: str,
) -> bool:
    from larch.design.design_summary import (  # noqa: PLC0415
        FinalSummaryRenderRequest,
        render_final_summary_for_request,
    )

    return render_final_summary_for_request(
        FinalSummaryRenderRequest(
            design_tmpdir=design_tmpdir,
            outcome=outcome,
            mode=_resolve_summary_mode(design_tmpdir),
            issue_number=issue,
            session_id=run_id,
            repo=repo,
            upsert_summary_comment=False,
            stdout_log_path=design_tmpdir / f"render-final-summary.{outcome}.pre-publish.stdout.log",
        )
    )


def log_publish_main(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed = {"--design-tmpdir": "", "--run-id": "", "--issue": "", "--repo": "", "--reason": "final", "--outcome": ""}
    dry_run = False
    i = 0
    while i < len(args):
        token = args[i]
        if token in parsed:
            if i + 1 >= len(args):
                return 1
            parsed[token] = args[i + 1]
            i += 2
            continue
        if token == "--dry-run":
            dry_run = True
            i += 1
            continue
        if token in {"-h", "--help"}:
            return 0
        return 1
    if not parsed["--design-tmpdir"] or not parsed["--run-id"] or not parsed["--issue"]:
        return 1
    design_tmpdir = Path(parsed["--design-tmpdir"])
    if not design_tmpdir.is_dir():
        _emit(k="PUBLISH_OK", v="false")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        return 0
    if not parsed["--issue"].isdigit() or parsed["--issue"] == "0":
        _emit(k="PUBLISH_OK", v="false")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        return 0
    if not _validate_slug(parsed["--run-id"]):
        _emit(k="PUBLISH_OK", v="false")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        return 0
    if parsed["--repo"] and not _validate_repo(parsed["--repo"]):
        return 1
    if parsed["--reason"] not in {"final", "pause"}:
        _emit(k="PUBLISH_OK", v="false")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        return 0
    warning_step_label = "5c" if parsed["--reason"] == "final" else "pause"

    if dry_run:
        for cmd in ("git", "gh"):
            if shutil.which(cmd) is None:
                _emit(k="PUBLISH_OK", v="false")
                _emit(k="PR_NUMBER", v="")
                _emit(k="PR_URL", v="")
                return 0
        repo_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S607
        if not repo_root:
            _emit(k="PUBLISH_OK", v="false")
            _emit(k="PR_NUMBER", v="")
            _emit(k="PR_URL", v="")
            return 0
        _persist_metadata(design_tmpdir=design_tmpdir, pr_number="", pr_url="", recovery_branch="")
        _emit(k="PUBLISH_OK", v="true")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
    capture_ctx = design_publish._TranscriptCaptureContext(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        design_tmpdir=design_tmpdir,
        plugin_root=plugin_root,
        session_id=parsed["--run-id"],
        issue=parsed["--issue"],
        repo=parsed["--repo"],
        claude_pid=os.environ.get("LARCH_CLAUDE_PID", "") or os.environ.get("PPID", ""),
        warning_step_label=warning_step_label,
    )
    if not design_publish._capture_design_transcript(ctx=capture_ctx):  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        _emit(k="PUBLISH_OK", v="false")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        return 0

    outcome = parsed["--outcome"] or _default_outcome_for_reason(parsed["--reason"])
    if not _render_final_summary_before_copy(
        design_tmpdir=design_tmpdir,
        outcome=outcome,
        issue=parsed["--issue"],
        repo=parsed["--repo"],
        run_id=parsed["--run-id"],
    ):
        print("design log-publish: final-summary render failed; continuing without stale summary", file=sys.stderr)

    try:
        publish_ok, pr_number, pr_url, recovery_branch, scrub_violations = _publish_design_logs(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            run_id=parsed["--run-id"],
            issue=parsed["--issue"],
            repo=parsed["--repo"],
        )
    except SecretScrubFailure as exc:
        print(f"design log-publish: secret scrub failed: {exc}", file=sys.stderr)
        _emit(k="PUBLISH_OK", v="false")
        _emit(k="PR_NUMBER", v="")
        _emit(k="PR_URL", v="")
        _emit(k="SECRET_SCRUB_VIOLATIONS", v="0")
        return 1
    _persist_metadata(design_tmpdir=design_tmpdir, pr_number=pr_number, pr_url=pr_url, recovery_branch=recovery_branch)
    _emit(k="PUBLISH_OK", v="true" if publish_ok else "false")
    _emit(k="PR_NUMBER", v=pr_number)
    _emit(k="PR_URL", v=pr_url)
    if recovery_branch:
        _emit(k="RECOVERY_BRANCH", v=recovery_branch)
    _emit(k="SECRET_SCRUB_VIOLATIONS", v=scrub_violations)
    return 0
