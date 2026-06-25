# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoint for /set-up-forked-open-source-repo."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import proc
from redact import redact_outbound
from retry import with_transient_retry

OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
OWNER_REPO_PARTS = 2
REMOTE_PAIR_COUNT = 2
LS_REMOTE_FIELD_COUNT = 2


class SetupError(RuntimeError):
    """Raised for setup failures after a user-visible diagnostic."""


@dataclass(frozen=True)
class RemoteSnapshot:
    entries: list[tuple[str, str]] = field(default_factory=list)


# Mutable builder: the argv parser fills fields and toggles remote_phase_active during setup.
@dataclass
class SetupContext:
    upstream: str = ""
    fork: str = ""
    mirror_confirmed: bool = False
    init_submodules: bool = False
    gh_host: str = "github.com"
    preflight_remote_classification: str = ""
    lock_file: Path | None = None
    lock_dir: Path | None = None
    snapshot: RemoteSnapshot | None = None
    remote_phase_active: bool = False


def out_kv(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def err(message: str) -> None:
    print(message, file=sys.stderr)


def die(message: str) -> None:
    err(f"ERROR: {message}")
    raise SetupError(message)


def validate_owner_repo(*, value: str, label: str) -> None:
    if OWNER_REPO_RE.match(value) is None:
        die(f"{label} must have owner/repo shape")


def parse_args(argv: list[str]) -> SetupContext:
    ctx = SetupContext()
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--upstream":
            if index + 1 >= len(argv):
                die("--upstream requires a value")
            ctx.upstream = argv[index + 1]
            index += 2
        elif arg == "--fork":
            if index + 1 >= len(argv):
                die("--fork requires a value")
            ctx.fork = argv[index + 1]
            index += 2
        elif arg == "--mirror-confirmed":
            ctx.mirror_confirmed = True
            index += 1
        elif arg == "--init-submodules":
            ctx.init_submodules = True
            index += 1
        elif arg in {"-h", "--help"}:
            err("Usage: setup --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]")
            raise SystemExit(0)
        else:
            err("Usage: setup --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]")
            die(f"unknown argument: {arg}")
    if not ctx.upstream:
        die("missing --upstream")
    if not ctx.fork:
        die("missing --fork")
    validate_owner_repo(value=ctx.upstream, label="--upstream")
    validate_owner_repo(value=ctx.fork, label="--fork")
    return ctx


def normalize_github_url(url: str) -> tuple[str, str] | None:
    value = url.rstrip("/")
    value = value.removesuffix(".git")
    host = ""
    rest = ""
    if value.startswith("git@") and ":" in value:
        after = value.removeprefix("git@")
        host, rest = after.split(":", 1)
    elif value.startswith("ssh://git@"):
        after = value.removeprefix("ssh://git@")
        host, rest = after.split("/", 1) if "/" in after else ("", "")
    elif value.startswith("ssh://"):
        after = value.removeprefix("ssh://")
        host, rest = after.split("/", 1) if "/" in after else ("", "")
    elif value.startswith("https://"):
        after = value.removeprefix("https://")
        host, rest = after.split("/", 1) if "/" in after else ("", "")
    elif value.startswith("git://"):
        after = value.removeprefix("git://")
        host, rest = after.split("/", 1) if "/" in after else ("", "")
    if not host or "/" in host or "@" in host or "://" in host or re.match(r"^[A-Za-z0-9.-]+(:[0-9]+)?$", host) is None:
        return None
    parts = rest.split("/")
    if len(parts) < OWNER_REPO_PARTS or not parts[0] or not parts[1]:
        return None
    return host.lower(), f"{parts[0]}/{parts[1]}".lower()


def git_stdout(args: list[str], *, ok_empty: bool = False) -> str:
    result = proc.run(["git", *args])
    if result.returncode != 0 and not ok_empty:
        die(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def git_config_values(key: str) -> list[str]:
    result = proc.run(["git", "config", "--get-all", key])
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def git_remotes() -> list[str]:
    result = proc.run(["git", "remote"])
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def classify_remote_state(*, upstream: str, fork: str, expected_host: str) -> str:
    remotes: set[str] = set()
    origin_seen = False
    upstream_seen = False
    fork_count = 0
    fork_remote = ""
    origin_canonical = ""
    upstream_canonical = ""
    bad = False
    for remote in git_remotes():
        urls = git_config_values(f"remote.{remote}.url")
        pushurls = git_config_values(f"remote.{remote}.pushurl")
        if len(urls) > 1 or len(pushurls) > 1:
            return "state-ambiguous"
        for url in urls:
            parsed = normalize_github_url(url)
            if parsed is None:
                bad = True
                continue
            host, canonical = parsed
            if host != expected_host.lower():
                bad = True
                continue
            remotes.add(remote)
            if remote == "origin":
                origin_seen = True
                origin_canonical = canonical
            if remote == "upstream":
                upstream_seen = True
                upstream_canonical = canonical
            if canonical == fork:
                fork_count += 1
                fork_remote = remote
            elif canonical != upstream:
                bad = True
    if bad or not origin_seen:
        return "state-ambiguous"
    if origin_canonical == fork and upstream_seen and upstream_canonical == upstream:
        return "state-already-configured" if fork_count == 1 and len(remotes) == REMOTE_PAIR_COUNT else "state-ambiguous"
    if origin_canonical == upstream and not upstream_seen:
        if fork_count == 0 and len(remotes) == 1:
            return "state-origin-upstream-only"
        if fork_count == 1 and len(remotes) == REMOTE_PAIR_COUNT and fork_remote != "origin":
            return f"state-origin-upstream-named-fork {fork_remote}"
    return "state-ambiguous"


def https_url(*, ctx: SetupContext, kind: str, owner_repo: str) -> str:
    env_name = f"LARCH_FORKED_REPO_URL_OVERRIDE_{kind}_HTTPS"
    if os.environ.get("LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE") == "1" and os.environ.get(env_name):
        return os.environ[env_name]
    return f"https://{ctx.gh_host}/{owner_repo}.git"


def ssh_url(*, ctx: SetupContext, kind: str, owner_repo: str) -> str:
    env_name = f"LARCH_FORKED_REPO_URL_OVERRIDE_{kind}_SSH"
    if os.environ.get("LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE") == "1" and os.environ.get(env_name):
        return os.environ[env_name]
    return f"git@{ctx.gh_host}:{owner_repo}.git"


def _transient_proc_run(argv: list[str]) -> proc.CommandResult:
    def attempt() -> tuple[proc.CommandResult, int, str]:
        result = proc.run(argv)
        content = (result.stdout or "") + (result.stderr or "")
        return result, result.returncode, content

    return with_transient_retry(attempt).value


def remote_main_sha(url: str) -> str:
    result = _transient_proc_run(["git", "ls-remote", url, "refs/heads/main"])
    if result.returncode != 0:
        return ""
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == LS_REMOTE_FIELD_COUNT and parts[1] == "refs/heads/main":
            return parts[0]
    return ""


def _live_worktree_paths() -> list[str]:
    worktrees = proc.run(["git", "worktree", "list", "--porcelain"])
    paths: list[str] = []
    current_path = ""
    prunable = False
    for line in worktrees.stdout.splitlines():
        if not line:
            if current_path and not prunable:
                paths.append(current_path)
            current_path = ""
            prunable = False
            continue
        if line.startswith("worktree "):
            current_path = line.removeprefix("worktree ")
        elif line.startswith("prunable"):
            prunable = True
    if current_path and not prunable:
        paths.append(current_path)
    if not paths:
        paths = [git_stdout(["rev-parse", "--show-toplevel"])]
    return paths


def all_worktrees_clean() -> bool:
    for path in _live_worktree_paths():
        status = proc.run(["git", "-C", path, "status", "--porcelain"])
        if status.stdout.strip():
            err(f"ERROR: working tree '{path}' is dirty; commit or stash before running")
            return False
    return True


def no_op_in_progress() -> bool:
    sentinels = ("MERGE_HEAD", "REBASE_HEAD", "rebase-apply", "rebase-merge", "CHERRY_PICK_HEAD", "REVERT_HEAD")
    for path in _live_worktree_paths():
        git_dir = proc.run(["git", "-C", path, "rev-parse", "--absolute-git-dir"])
        if git_dir.returncode != 0:
            return False
        for sentinel in sentinels:
            if (Path(git_dir.stdout.strip()) / sentinel).exists():
                err(f"ERROR: git operation in progress in '{path}' ({sentinel}); resolve it before running")
                return False
    return True


def acquire_lock(ctx: SetupContext) -> None:
    common = git_stdout(["rev-parse", "--git-common-dir"])
    lock_file = Path(common).resolve() / "larch-fork-setup.lock"
    lock_dir = Path(f"{lock_file}.d")
    try:
        lock_dir.mkdir()
    except OSError:
        holder = "unknown"
        holder_file = lock_dir / "holder"
        if holder_file.is_file():
            holder = holder_file.read_text(encoding="utf-8").strip() or "unknown"
        die(f"another setup-forked-open-source-repo run is in progress (lock={lock_dir}, holder={holder})")
    (lock_dir / "holder").write_text(f"{os.getpid()}\n", encoding="utf-8")
    ctx.lock_file = lock_file
    ctx.lock_dir = lock_dir


def release_lock(ctx: SetupContext) -> None:
    if ctx.lock_dir is None:
        return
    try:
        (ctx.lock_dir / "holder").unlink(missing_ok=True)
        ctx.lock_dir.rmdir()
    except OSError:
        pass


def phase_preflight(ctx: SetupContext) -> None:
    root = git_stdout(["rev-parse", "--show-toplevel"])
    os.chdir(root)
    acquire_lock(ctx)
    if proc.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/main"]).returncode != 0:
        die("local refs/heads/main is absent")
    current = git_stdout(["symbolic-ref", "--short", "HEAD"], ok_empty=True)
    if current != "main":
        die("current checkout must be main")
    if "origin" in git_remotes():
        urls = git_config_values("remote.origin.url")
        if len(urls) > 1:
            die("multiple remote.origin.url entries; refuse early")
        parsed = normalize_github_url(urls[0] if urls else "")
        if parsed is None:
            die(f"origin remote URL '{urls[0] if urls else ''}' is not a recognized GitHub-compatible URL; refusing to fetch")
        ctx.gh_host = parsed[0]
    auth = proc.run(["gh", "auth", "status", "--hostname", ctx.gh_host])
    if auth.returncode != 0:
        err("ERROR: gh auth status failed:")
        err(redact_outbound(auth.stderr))
        raise SetupError("gh auth status failed")
    if not all_worktrees_clean():
        die("working tree is dirty; commit or stash before running")
    if not no_op_in_progress():
        die("git operation in progress; resolve it before running")
    if "origin" in git_remotes():
        upstream_lc = ctx.upstream.lower()
        fork_lc = ctx.fork.lower()
        ctx.preflight_remote_classification = classify_remote_state(upstream=upstream_lc, fork=fork_lc, expected_host=ctx.gh_host)
        if ctx.preflight_remote_classification.split()[0] == "state-ambiguous":
            die("ambiguous remote state; refusing to call GitHub before remotes are resolved")
        git_stdout(["fetch", "origin"])
        if proc.run(["git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main"]).returncode != 0:
            die("origin/main is absent after fetch")
        if proc.run(["git", "merge-base", "--is-ancestor", "main", "origin/main"]).returncode != 0:
            if proc.run(["git", "merge-base", "--is-ancestor", "origin/main", "main"]).returncode == 0:
                die("local main is ahead of origin/main; push or reset manually before running")
            die("local main and origin/main have diverged")


def phase_github(ctx: SetupContext) -> None:
    view = proc.run(["gh", "repo", "view", ctx.fork, "--json", "nameWithOwner,parent,defaultBranchRef"])
    if view.returncode != 0:
        combined = f"{view.stdout}\n{view.stderr}"
        if re.search(r"404|not[_ -]?found|Could not resolve to a Repository", combined, re.IGNORECASE):
            err(f"Fork {ctx.fork} was not found. Create it at https://{ctx.gh_host}/{ctx.upstream}/fork, then rerun this skill.")
            out_kv(key="SETUP_FORKED_REPO_RESULT", value="fork_missing")
            raise SystemExit(0)
        err("ERROR: gh repo view failed:")
        err(redact_outbound(view.stderr))
        raise SetupError("gh repo view failed")
    try:
        data: object = json.loads(view.stdout)
    except json.JSONDecodeError as exc:
        err("ERROR: gh repo view returned invalid JSON:")
        err(str(exc))
        raise SetupError("invalid JSON") from exc
    parent_obj = data.get("parent") if isinstance(data, dict) else None
    if isinstance(parent_obj, dict):
        parent = parent_obj.get("nameWithOwner") or ""
        if not parent and isinstance(parent_obj.get("owner"), dict):
            owner = parent_obj["owner"].get("login")
            name = parent_obj.get("name")
            parent = f"{owner}/{name}" if owner and name else ""
    else:
        parent = ""
    if parent.lower() != ctx.upstream.lower():
        die(f"fork parent mismatch: expected {ctx.upstream}, got {parent or '<none>'}")
    upstream_https = https_url(ctx=ctx, kind="UPSTREAM", owner_repo=ctx.upstream)
    fork_https = https_url(ctx=ctx, kind="FORK", owner_repo=ctx.fork)
    upstream_sha = remote_main_sha(upstream_https)
    fork_sha = remote_main_sha(fork_https)
    if not upstream_sha:
        die("upstream has no refs/heads/main")
    if not fork_sha:
        die("fork has no refs/heads/main")
    if upstream_sha == fork_sha:
        out_kv(key="SETUP_FORKED_REPO_RESULT", value="mirror_skipped_in_sync")
        return
    err(f"Fork main differs from upstream main: upstream={upstream_sha} fork={fork_sha}. Confirming will overwrite fork branches/tags to match upstream.")
    if not ctx.mirror_confirmed:
        if not sys.stdin.isatty():
            die("mirror divergence detected; rerun with --mirror-confirmed")
        err("Mirror-sync fork now? [y/N] ")
        reply = sys.stdin.readline().strip()
        if reply.lower() not in {"y", "yes"}:
            die("mirror sync declined")
    if remote_main_sha(upstream_https) != upstream_sha or remote_main_sha(fork_https) != fork_sha:
        die("remote moved during confirmation; rerun")
    if not all_worktrees_clean() or not no_op_in_progress():
        die("working tree became dirty before mirror push")
    tmp = Path(tempfile.mkdtemp(prefix="larch-forked-mirror."))
    try:
        clone_dir = tmp / "upstream.git"
        git_stdout(["clone", "--mirror", upstream_https, str(clone_dir)])
        pushed_sha = proc.run(["git", "-C", str(clone_dir), "rev-parse", "refs/heads/main"]).stdout.strip()
        if not pushed_sha:
            die("mirror clone has no refs/heads/main")
        push = _transient_proc_run(
            [
                "git",
                "-C",
                str(clone_dir),
                "push",
                "--prune",
                ssh_url(ctx=ctx, kind="FORK", owner_repo=ctx.fork),
                "+refs/heads/*:refs/heads/*",
                "+refs/tags/*:refs/tags/*",
            ],
        )
        if push.returncode != 0:
            die("mirror push to fork failed")
        post_sha = remote_main_sha(fork_https)
        if post_sha != pushed_sha:
            die(f"fork refs/heads/main did not match what was pushed (expected {pushed_sha}, got {post_sha or '<none>'})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out_kv(key="SETUP_FORKED_REPO_RESULT", value="mirror_synced")


def snapshot_remote_state() -> RemoteSnapshot:
    result = proc.run(["git", "config", "--get-regexp", "^(remote|branch)\\."])
    entries: list[tuple[str, str]] = []
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if " " in line:
                key, value = line.split(" ", 1)
                entries.append((key, value))
    return RemoteSnapshot(entries)


def restore_remote_state(snapshot: RemoteSnapshot) -> bool:
    if os.environ.get("LARCH_FORKED_REPO_INJECT_FAILURE") == "rollback":
        err("RECOVERY_REPORT rollback_failed=true reason=injected-rollback-failure")
        return False
    ok = True
    keys = proc.run(["git", "config", "--name-only", "--get-regexp", "^(remote|branch)\\."])
    if keys.returncode == 0:
        for key in keys.stdout.splitlines():
            if not key:
                continue
            if proc.run(["git", "config", "--unset-all", key]).returncode != 0:
                ok = False
    for key, value in snapshot.entries:
        if proc.run(["git", "config", "--add", key, value]).returncode != 0:
            ok = False
    if not ok:
        err("RECOVERY_REPORT rollback_failed=true reason=git-config-restore-failed")
    return ok


def rollback_remotes_if_active(ctx: SetupContext) -> None:
    if not ctx.remote_phase_active or ctx.snapshot is None:
        return
    err("ERROR: remote rewrite failed; attempting rollback")
    if not restore_remote_state(ctx.snapshot):
        err("RECOVERY_REPORT rollback_failed=true reason=restore-remote-state-failed")


def phase_remotes(ctx: SetupContext) -> None:
    ctx.snapshot = snapshot_remote_state()
    ctx.remote_phase_active = True
    classification = ctx.preflight_remote_classification or classify_remote_state(upstream=ctx.upstream.lower(), fork=ctx.fork.lower(), expected_host=ctx.gh_host)
    state, _, named_fork = classification.partition(" ")
    fork_ssh = ssh_url(ctx=ctx, kind="FORK", owner_repo=ctx.fork)
    try:
        if state == "state-already-configured":
            pass
        elif state == "state-origin-upstream-only":
            git_stdout(["remote", "rename", "origin", "upstream"])
            if os.environ.get("LARCH_FORKED_REPO_INJECT_FAILURE") == "after-rename-origin-upstream":
                die("injected failure")
            git_stdout(["remote", "add", "origin", fork_ssh])
        elif state == "state-origin-upstream-named-fork":
            git_stdout(["remote", "rename", "origin", "upstream"])
            if os.environ.get("LARCH_FORKED_REPO_INJECT_FAILURE") == "after-rename-origin-upstream":
                die("injected failure")
            git_stdout(["remote", "rename", named_fork, "origin"])
        else:
            die("ambiguous remote state; refusing to mutate.")
        proc.run(["git", "config", "--unset-all", "remote.upstream.pushurl"])
        git_stdout(["config", "--add", "remote.upstream.pushurl", "larch-disabled://upstream-push-disabled"])
        proc.run(["git", "config", "--unset-all", "remote.origin.pushurl"])
        if os.environ.get("LARCH_FORKED_REPO_INJECT_FAILURE") in {"fetch", "rollback"}:
            die("injected failure")
        git_stdout(["fetch", "origin", "--prune", "--tags"])
        git_stdout(["branch", "--set-upstream-to=origin/main", "main"])
        if not all_worktrees_clean():
            die("working tree became dirty before fast-forward")
        if proc.run(["git", "merge-base", "--is-ancestor", "origin/main", "main"]).returncode != 0:
            git_stdout(["merge", "--ff-only", "origin/main"])
    except Exception:
        rollback_remotes_if_active(ctx)
        raise


def phase_submodules(ctx: SetupContext) -> None:
    if ctx.init_submodules and Path(".gitmodules").is_file():
        result = _transient_proc_run(["git", "submodule", "update", "--init", "--recursive"])
        if result.returncode != 0:
            die("git submodule update --init --recursive failed")


def phase_verify(ctx: SetupContext) -> None:
    if os.environ.get("LARCH_FORKED_REPO_INJECT_FAILURE") == "in-verify":
        die("injected failure")
    err("")
    err("Final remotes:")
    remotes = proc.run(["git", "remote", "-v"])
    if remotes.stdout:
        err(remotes.stdout.rstrip())
    err("")
    err("Disabled upstream push sentinel:")
    sentinel = proc.run(["git", "config", "--get-regexp", "^remote\\.upstream\\.pushurl$"])
    if sentinel.stdout:
        err(sentinel.stdout.rstrip())
    if git_stdout(["config", "--get", "branch.main.remote"]) != "origin":
        die("branch.main.remote is not origin")
    if git_stdout(["config", "--get", "branch.main.merge"]) != "refs/heads/main":
        die("branch.main.merge is not refs/heads/main")
    err("")
    err(f"Fork workflow: branch off origin/main, push topic branches to origin, and open PRs from {ctx.fork}:<branch> to {ctx.upstream}:main.")
    out_kv(key="SETUP_FORKED_REPO_RESULT", value="ok")
    ctx.remote_phase_active = False


def setup_main(argv: list[str]) -> int:
    ctx: SetupContext | None = None
    try:
        ctx = parse_args(argv)
        phase_preflight(ctx)
        phase_github(ctx)
        phase_remotes(ctx)
        phase_submodules(ctx)
        phase_verify(ctx)
    except SystemExit as exc:
        return int(exc.code or 0)
    except SetupError:
        if ctx is not None:
            rollback_remotes_if_active(ctx)
        return 1
    finally:
        if ctx is not None:
            release_lock(ctx)
    return 0
