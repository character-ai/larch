"""Python CLI entrypoint for committed /design run-log publishing."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Sequence

_PR_URL_RE = re.compile(r"/pull/([0-9]+)")


def _emit(k: str, v: str) -> None:
    print(f"{k}={v}")


def _validate_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value))


def _validate_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", value))


def _persist_metadata(design_tmpdir: Path, pr_number: str, pr_url: str, recovery_branch: str) -> None:
    with contextlib.suppress(OSError):
        _ = (design_tmpdir / ".design-log-publish-metadata.env").write_text(
            f"DESIGN_LOG_PR_NUMBER={pr_number}\nDESIGN_LOG_PR_URL={pr_url}\nDESIGN_LOG_RECOVERY_BRANCH={recovery_branch}\n",
            encoding="utf-8",
        )


def _copy_tree_redacted(plugin_root: Path, source: Path, dest: Path) -> bool:
    if source.is_symlink():
        return False
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
            return False
        sec = subprocess.run(
            [sys.executable, str(plugin_root / "python" / "cli.py"), "redact", "secrets"],
            input=red.stdout,
            text=True,
            capture_output=True,
            check=False,
        )
        if sec.returncode != 0:
            return False
        _ = dest.write_text(sec.stdout, encoding="utf-8")
        return True
    if source.is_dir():
        for child in source.iterdir():
            if child.is_symlink():
                continue
            if not _copy_tree_redacted(plugin_root, child, dest / child.name):
                return False
        return True
    return True


def _run(argv: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def _default_base_ref(repo_root: str) -> str:
    head = _run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_root)
    target = head.stdout.strip()
    if head.returncode == 0 and target.startswith("origin/"):
        return target.split("/", 1)[1]
    return "main"


def _spawn_detached_admin_merge(cli: str, pr_number: str, repo: str, repo_root: str) -> None:
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


def _publish_design_logs(
    plugin_root: Path,
    design_tmpdir: Path,
    run_id: str,
    issue: str,
    repo: str,
) -> tuple[bool, str, str, str]:
    """Commit the design run tree on a dedicated branch via a disposable worktree, push it, and open a PR.

    Returns ``(publish_ok, pr_number, pr_url, recovery_branch)``. The operator
    working tree is never touched: every write lands inside the worktree, so the
    next ``/implement`` preflight stays clean even if this fails (issue #4395).
    ``recovery_branch`` is set only when a commit exists but could not be turned
    into a PR, so the operator can finish it manually.
    """
    top = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = top.stdout.strip()
    if top.returncode != 0 or not repo_root:
        return (False, "", "", "")
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
            return (False, "", "", "")
        branch_created = True
        wt_log_root = worktree / "larch-logs"
        run_dest = wt_log_root / "design" / run_id
        run_dest.mkdir(parents=True, exist_ok=True)
        init = _run(
            [sys.executable, cli, "run-log", "init", "--log-root", str(wt_log_root),
             "--skill", "design", "--run-id", run_id, "--issue", issue],
        )
        if init.returncode != 0:
            return (False, "", "", "")
        for child in design_tmpdir.iterdir():
            if child.name == ".design-log-publish-metadata.env":
                continue
            if not _copy_tree_redacted(plugin_root, child, run_dest / child.name):
                return (False, "", "", "")
        base_sha = _run(["git", "rev-parse", "HEAD"], cwd=str(worktree)).stdout.strip()
        commit = _run(
            [sys.executable, cli, "run-log", "commit", "--log-root", str(wt_log_root),
             "--skill", "design", "--run-id", run_id],
            cwd=str(worktree),
        )
        head_sha = _run(["git", "rev-parse", "HEAD"], cwd=str(worktree)).stdout.strip()
        if commit.returncode != 0 or not head_sha or head_sha == base_sha:
            print(f"design log-publish: run-log commit produced no commit: {commit.stderr.strip()}", file=sys.stderr)
            return (False, "", "", "")
        push = _run(["git", "push", "-u", "origin", branch], cwd=str(worktree))
        if push.returncode != 0:
            print(f"design log-publish: push failed; local branch {branch} kept for recovery: {push.stderr.strip()}", file=sys.stderr)
            keep_branch_for_recovery = True
            return (False, "", "", branch)
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
            return (False, "", "", branch)
        pr_url = pr.stdout.strip().splitlines()[-1] if pr.stdout.strip() else ""
        match = _PR_URL_RE.search(pr_url)
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
            _spawn_detached_admin_merge(cli, pr_number, repo, repo_root)
        return (True, pr_number, pr_url, "")
    finally:
        _ = _run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo_root)
        if branch_created and not keep_branch_for_recovery:
            _ = _run(["git", "branch", "-D", branch], cwd=repo_root)
        shutil.rmtree(wt_parent, ignore_errors=True)


def log_publish_main(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed = {"--design-tmpdir": "", "--run-id": "", "--issue": "", "--repo": "", "--reason": "final"}
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
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    if not parsed["--issue"].isdigit() or parsed["--issue"] == "0":
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    if not _validate_slug(parsed["--run-id"]):
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0
    if parsed["--repo"] and not _validate_repo(parsed["--repo"]):
        return 1
    if parsed["--reason"] not in {"final", "pause"}:
        _emit("PUBLISH_OK", "false")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0

    if dry_run:
        for cmd in ("git", "gh"):
            if shutil.which(cmd) is None:
                _emit("PUBLISH_OK", "false")
                _emit("PR_NUMBER", "")
                _emit("PR_URL", "")
                return 0
        repo_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S607
        if not repo_root:
            _emit("PUBLISH_OK", "false")
            _emit("PR_NUMBER", "")
            _emit("PR_URL", "")
            return 0
        _persist_metadata(design_tmpdir, "", "", "")
        _emit("PUBLISH_OK", "true")
        _emit("PR_NUMBER", "")
        _emit("PR_URL", "")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    publish_ok, pr_number, pr_url, recovery_branch = _publish_design_logs(
        plugin_root,
        design_tmpdir,
        parsed["--run-id"],
        parsed["--issue"],
        parsed["--repo"],
    )
    _persist_metadata(design_tmpdir, pr_number, pr_url, recovery_branch)
    _emit("PUBLISH_OK", "true" if publish_ok else "false")
    _emit("PR_NUMBER", pr_number)
    _emit("PR_URL", pr_url)
    if recovery_branch:
        _emit("RECOVERY_BRANCH", recovery_branch)
    return 0
