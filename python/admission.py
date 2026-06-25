# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""/implement admission, preflight, and fork-env entrypoints."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import larch_io
import logging_util
import retry

_PY_CLI = Path(__file__).with_name("cli.py")
_PROBE_ERROR_EXIT = 2
_TMP_FALLBACK = "/tmp"  # noqa: S108 - parity fallback for larch bootstrap tmpdirs.
_transient_retry_sleeper = retry.default_sleeper


def _emit_kv(*, key: str, value: str) -> None:
    logging_util.emit_kv(key=key, value=_single_line(value))


def _single_line(value: str) -> str:
    return re.sub(r" +", " ", value.replace("\r", " ").replace("\n", " ")).strip()


def _run(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, capture_output=True, text=True, errors="replace", env=env, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"{exc}\n")


def _normal_issue(value: str) -> int | None:
    if not value or not value.isdigit():
        return None
    number = int(value, 10)
    return number if number > 0 else None


def _has_managed_prefix(title: str) -> bool:
    return title.startswith(("[DESIGNING] ", "[IMPLEMENTING] ", "[DONE] ", "[STALLED] ", "[IN PROGRESS] ", "[PLANNED] "))


def _has_designed_prefix(title: str) -> bool:
    return title.startswith("[DESIGNED] ")


def _has_report_prefix(title: str) -> bool:
    return re.search(r"^\[[^]]*\s+report\]", title, re.IGNORECASE) is not None


def _resolve_repo() -> str | None:
    result = _run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _gh_issue_view(*, issue: int, repo: str) -> tuple[int, str]:
    argv = ["gh", "issue", "view", str(issue), "--repo", repo, "--json", "title,state,labels"]
    first = _run(argv)
    if first.returncode == 0:
        return 0, first.stdout
    second = _run(argv)
    return second.returncode, second.stdout


def _git_fetch_origin_main() -> subprocess.CompletedProcess[str]:
    def attempt() -> tuple[subprocess.CompletedProcess[str], int, str]:
        result = _run(["git", "fetch", "origin", "main", "--quiet"])
        return result, result.returncode, result.stdout + result.stderr

    return retry.with_transient_retry(attempt, sleeper=_transient_retry_sleeper).value


def _atomic_text(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, prefix=f".{path.name}.", newline="\n")


def _blockers(*, issue: int, repo: str) -> tuple[int, str]:
    env = {**os.environ, "LARCH_QUIET_DISABLE": "1", "REPO": repo}
    result = _run(
        [sys.executable, str(Path(__file__).with_name("cli.py")), "blocker", "all-open", "--issue", str(issue), "--repo", repo],
        env=env,
    )
    if result.returncode != 0:
        return result.returncode, ""
    for line in result.stdout.splitlines():
        if line.startswith("BLOCKERS="):
            return 0, line.split("=", 1)[1].strip()
    return 0, ""


def _blocker_failure(rc: int) -> int:
    _emit_kv(key="ADMISSION_ERROR", value=f"blocker check failed (exit {rc})")
    return 2


def _read_parent_sentinel(issue: int) -> bool:
    tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return False
    path = Path(tmpdir) / "parent-issue.md"
    if not path.is_file():
        return False
    data: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key] = value.strip()
    except OSError:
        return False
    parent_issue = _normal_issue(data.get("ISSUE_NUMBER", ""))
    if parent_issue != issue:
        return False
    parent_run_id = data.get("RUN_ID", "")
    return not parent_run_id or parent_run_id == os.environ.get("RUN_ID", "")


def gate_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="admission gate", add_help=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--repo", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if int(exc.code or 0) != 0:
            _emit_kv(key="ADMISSION_ERROR", value="argument validation failed")
            return 2
        return 0
    issue = _normal_issue(args.issue)
    if issue is None:
        _emit_kv(key="ADMISSION_ERROR", value="--issue must be a positive integer")
        return 2
    repo = args.repo or (_resolve_repo() or "")
    if not repo:
        _emit_kv(key="ADMISSION_ERROR", value="could not resolve repo (gh repo view failed)")
        return 2
    view_rc, raw = _gh_issue_view(issue=issue, repo=repo)
    if view_rc != 0:
        detail = _single_line(raw)
        _emit_kv(key="ADMISSION_ERROR", value=f"gh issue view failed{': ' + detail if detail else ''}")
        return 2
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _emit_kv(key="ADMISSION_ERROR", value="issue json parse failed (malformed gh issue view response)")
        return 2
    title = str(data.get("title") or "")
    state = str(data.get("state") or "")
    labels = data.get("labels") or []
    if state == "CLOSED":
        _emit_kv(key="ADMISSION_ERROR", value=f"issue #{issue} is CLOSED")
        return 2

    if _read_parent_sentinel(issue):
        blocker_rc, blockers = _blockers(issue=issue, repo=repo)
        if blocker_rc != 0:
            return _blocker_failure(blocker_rc)
        if blockers:
            _emit_kv(key="ADMISSION_RESULT", value="has-blockers")
            _emit_kv(key="BLOCKERS", value=blockers)
            return 4
        if _has_report_prefix(title):
            _emit_kv(key="ADMISSION_RESULT", value="report-title")
            _emit_kv(key="TITLE", value=title)
            return 7
        _emit_kv(key="ADMISSION_RESULT", value="pass")
        _emit_kv(key="RESUME", value="true")
        return 0

    if _has_managed_prefix(title):
        _emit_kv(key="ADMISSION_RESULT", value="managed-prefix")
        _emit_kv(key="TITLE", value=title)
        return 5
    if _has_report_prefix(title):
        _emit_kv(key="ADMISSION_RESULT", value="report-title")
        _emit_kv(key="TITLE", value=title)
        return 7
    if any(isinstance(label, dict) and label.get("name") == "audit-report" for label in labels):
        _emit_kv(key="ADMISSION_RESULT", value="audit-report-label")
        return 6
    blocker_rc, blockers = _blockers(issue=issue, repo=repo)
    if blocker_rc != 0:
        return _blocker_failure(blocker_rc)
    if blockers:
        _emit_kv(key="ADMISSION_RESULT", value="has-blockers")
        _emit_kv(key="BLOCKERS", value=blockers)
        return 4
    if not _has_designed_prefix(title):
        _emit_kv(key="ADMISSION_RESULT", value="missing-designed-prefix")
        _emit_kv(key="TITLE", value=title)
        return 5
    _emit_kv(key="ADMISSION_RESULT", value="pass")
    return 0


def _clean_tree() -> str:
    result = _run([sys.executable, str(_PY_CLI), "git", "clean-tree", "--fail-closed"])
    if result.stderr:
        sys.stderr.write(result.stderr)
    for line in result.stdout.splitlines():
        if line.startswith("CLEAN="):
            return line.split("=", 1)[1]
    return ""


def preflight_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="admission preflight", add_help=False)
    parser.add_argument("--skip-branch-check", action="store_true")
    parser.add_argument("--skip-clean-check", action="store_true")
    try:
        args, rest = parser.parse_known_args(argv)
    except SystemExit:
        return 3
    if rest:
        parser.print_usage(sys.stderr)
        print(f"Unknown option: {rest[0]}", file=sys.stderr)
        return 3
    if not args.skip_branch_check:
        result = _run(["git", "symbolic-ref", "--short", "HEAD"])
        current = result.stdout.strip() if result.returncode == 0 else ""
        if current != "main":
            _emit_kv(key="PREFLIGHT", value="fail")
            _emit_kv(key="PREFLIGHT_ERROR", value=f"Not on main branch (on '{current}'). Switch to main first, or pass --skip-branch-check.")
            return 1
    if not args.skip_clean_check:
        clean = _clean_tree()
        if clean == "false":
            _emit_kv(key="PREFLIGHT", value="fail")
            _emit_kv(key="PREFLIGHT_ERROR", value="Working tree is not clean. Commit or stash changes first.")
            return 2
        if clean != "true":
            _emit_kv(key="PREFLIGHT", value="fail")
            _emit_kv(key="PREFLIGHT_ERROR", value="Could not determine working-tree cleanliness (helper produced no CLEAN= line).")
            return 2
    fetch = _git_fetch_origin_main()
    if fetch.returncode != 0:
        _emit_kv(key="PREFLIGHT", value="fail")
        _emit_kv(key="PREFLIGHT_ERROR", value="git fetch origin main failed.")
        return 3
    if not args.skip_branch_check:
        sync = _run([sys.executable, str(_PY_CLI), "git", "check-main-sync"])
        fields: dict[str, str] = dict(line.split("=", 1) for line in sync.stdout.splitlines() if "=" in line)
        sync_status = fields.get("SYNC_STATUS", "")
        sync_error = fields.get("ERROR", "")
        if sync_status == "blocked" or sync.returncode == 1:
            _emit_kv(key="PREFLIGHT", value="fail")
            _emit_kv(key="PREFLIGHT_ERROR", value=sync_error or "local main is ahead of origin/main with non-log changes; push or reconcile before re-running")
            return 3
        if not (sync.returncode == _PROBE_ERROR_EXIT and sync_status == "probe-error") and sync.returncode != 0:
            _emit_kv(key="PREFLIGHT", value="fail")
            _emit_kv(key="PREFLIGHT_ERROR", value=sync_error or f"cli.py git check-main-sync exited unexpectedly (exit {sync.returncode})")
            return 3
    if not args.skip_branch_check and not args.skip_clean_check:
        rebase = _run(["git", "rebase", "origin/main", "--quiet"])
        if rebase.returncode != 0:
            _ = _run(["git", "rebase", "--abort"])
            _emit_kv(key="PREFLIGHT", value="fail")
            _emit_kv(key="PREFLIGHT_ERROR", value="git rebase origin/main failed.")
            return 3
    status = _run(["git", "status", "--porcelain"])
    if not args.skip_clean_check or not status.stdout:
        git_path = _run(["git", "rev-parse", "--git-path", "larch-stalled-run.txt"])
        sentinel = git_path.stdout.strip()
        if sentinel:
            with contextlib.suppress(OSError):
                Path(sentinel).unlink(missing_ok=True)
    _emit_kv(key="PREFLIGHT", value="ok")
    return 0


def _github_remote_repo(remote: str) -> tuple[int, str, str]:
    result = _run([sys.executable, str(_PY_CLI), "gh", "remote-repo", remote])
    return result.returncode, result.stdout.strip(), result.stderr


def fork_env_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="admission fork-env", add_help=True)
    parser.add_argument("--tmpdir", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    upstream = _run(["git", "remote", "get-url", "upstream"])
    if upstream.returncode != 0:
        print("--forked requires the clone to be configured for the fork-PR workflow:", file=sys.stderr)
        print("  origin -> your fork; upstream -> the upstream repo.", file=sys.stderr)
        print("See docs/installation-and-setup.md (Fork CI dry-runs) for the full", file=sys.stderr)
        print("remote-add walkthrough; the minimum is:", file=sys.stderr)
        print("  git remote add upstream <https-or-ssh-url-of-upstream-repo>", file=sys.stderr)
        return 1
    origin_rc, fork_repo, origin_err = _github_remote_repo("origin")
    if origin_rc != 0:
        if origin_err:
            sys.stderr.write(origin_err)
        return 2
    upstream_rc, upstream_repo, upstream_err = _github_remote_repo("upstream")
    if upstream_rc != 0:
        if upstream_err:
            sys.stderr.write(upstream_err)
        return 2
    fork_owner = fork_repo.split("/", 1)[0]
    if args.tmpdir:
        bootstrap_tmpdir = Path(args.tmpdir)
        try:
            bootstrap_tmpdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"admission fork-env: could not create bootstrap tmpdir: {exc}", file=sys.stderr)
            return 2
    else:
        try:
            bootstrap_tmpdir = Path(tempfile.mkdtemp(prefix="larch-fork-bootstrap.", dir=os.environ.get("TMPDIR") or _TMP_FALLBACK))
        except OSError as exc:
            print(f"admission fork-env: could not create bootstrap tmpdir: {exc}", file=sys.stderr)
            return 2
    caller_env = bootstrap_tmpdir / "caller-env.sh"
    try:
        _atomic_text(path=caller_env, text=f"REPO={fork_repo}\n")
    except OSError as exc:
        print(f"admission fork-env: could not write caller-env.sh: {exc}", file=sys.stderr)
        return 2
    _emit_kv(key="BOOTSTRAP_TMPDIR", value=str(bootstrap_tmpdir))
    _emit_kv(key="CALLER_ENV_PATH", value=str(caller_env))
    _emit_kv(key="FORK_REPO", value=fork_repo)
    _emit_kv(key="UPSTREAM_REPO", value=upstream_repo)
    _emit_kv(key="FORK_OWNER", value=fork_owner)
    _emit_kv(key="FORKED_TARGET", value="true")
    return 0
