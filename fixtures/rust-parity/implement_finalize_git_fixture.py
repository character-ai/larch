"""Create a deterministic local Git topology around a finalize parity command."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
REPOSITORY = ROOT / "repo"


def git(*arguments: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *arguments],
        check=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        cwd=REPOSITORY,
    )
    return result.stdout.strip() if capture else ""


def setup(scenario: str) -> None:
    REPOSITORY.mkdir()
    git("init", "--quiet")
    git("config", "user.name", "Parity User")
    git("config", "user.email", "parity@example.invalid")
    (REPOSITORY / "base.txt").write_text("base\n", encoding="utf-8")
    git("add", "base.txt")
    git("commit", "--quiet", "-m", "Implement feature (#7)")
    git("branch", "-M", "main")
    git("init", "--quiet", "--bare", str(ROOT / "remote.git"))
    git("remote", "add", "origin", str(ROOT / "remote.git"))
    git("push", "--quiet", "origin", "main")
    if scenario == "postbump-main":
        return
    git("checkout", "--quiet", "-b", "feature")
    if scenario == "postbump-present":
        git("push", "--quiet", "origin", "feature")
    if scenario == "postbump-conflict":
        (REPOSITORY / "base.txt").write_text("feature change\n", encoding="utf-8")
        git("commit", "--quiet", "-am", "Feature conflict")
        git("checkout", "--quiet", "main")
        (REPOSITORY / "base.txt").write_text("upstream change\n", encoding="utf-8")
        git("commit", "--quiet", "-am", "Upstream conflict")
        git("push", "--quiet", "origin", "main")
        git("checkout", "--quiet", "feature")
        return
    (REPOSITORY / "feature.txt").write_text("feature\n", encoding="utf-8")
    git("add", "feature.txt")
    git("commit", "--quiet", "-m", "Feature work")
    if scenario == "teardown-stall":
        (REPOSITORY / "dirty.txt").write_text("preserve me\n", encoding="utf-8")


def snapshot() -> None:
    branch = git("branch", "--show-current", capture=True)
    branches = git(
        "for-each-ref", "--format=%(refname:short)", "refs/heads", capture=True
    )
    subject = git("log", "-1", "--format=%s", capture=True)
    dirty = bool(git("status", "--porcelain", capture=True))
    stash_count = len(git("stash", "list", capture=True).splitlines())
    stalled_sentinel = (REPOSITORY / ".git/larch-stalled-run.txt").is_file()
    remote = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", "feature"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
        cwd=REPOSITORY,
    )
    remote_state = "absent"
    if remote.returncode == 0:
        remote_oid = remote.stdout.split()[0] if remote.stdout.split() else ""
        head_oid = git("rev-parse", "HEAD", capture=True)
        remote_state = "matches-head" if remote_oid == head_oid else "diverged"
    Path("git-result.txt").write_text(
        f"CURRENT_BRANCH={branch}\n"
        f"LOCAL_BRANCHES={','.join(branches.splitlines())}\n"
        f"HEAD_SUBJECT={subject}\n"
        f"REMOTE_FEATURE={remote_state}\n"
        f"WORKTREE_DIRTY={'true' if dirty else 'false'}\n"
        f"STASH_COUNT={stash_count}\n"
        f"STALL_SENTINEL={'present' if stalled_sentinel else 'absent'}\n",
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    setup(sys.argv[1])
    result = subprocess.run(sys.argv[2:], check=False, cwd=REPOSITORY)
    snapshot()
    shutil.rmtree(REPOSITORY / ".git")
    shutil.rmtree(ROOT / "remote.git")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
