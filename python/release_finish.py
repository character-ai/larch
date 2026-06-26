# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: PLR2004, PLR5501, SIM115
# pylint: skip-file
"""Finish a release by tagging, creating/editing GitHub Release, and promoting."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from larch.core import proc
from larch.core import redact

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _e(*, msg: str, code: int = 1) -> int:
    print(msg, file=sys.stderr)
    return code


def _git(*argv: str) -> proc.CommandResult:
    return proc.run(["git", *argv])


def _gh(*argv: str) -> proc.CommandResult:
    return proc.run(["gh", *argv])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _origin_repo(root: Path) -> str | None:
    override = os.environ.get("LARCH_RELEASE_FINISH_ORIGIN_REPO", "")
    if override:
        return override
    res = proc.run(
        ["python3", str(root / "python" / "cli.py"), "gh", "remote-repo", "origin"],
        cwd=str(root),
    )
    return res.stdout.strip() if res.returncode == 0 else None


def _plugin_version_at(oid: str) -> str | None:
    blob = _git("show", f"{oid}:.claude-plugin/plugin.json")
    if blob.returncode != 0:
        return None
    try:
        value: Any = json.loads(blob.stdout).get("version")
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, str) and value else None


def _fetch_origin_main() -> bool:
    res = _git("fetch", "origin", "main")
    if res.returncode != 0:
        print(f"ERROR=fetch-failed: {res.stderr.replace(chr(10), ' ')}", file=sys.stderr)
        return False
    return True


def _query_pr(*, repo: str, pr: str, field: str) -> str:
    res = _gh("pr", "view", pr, "--repo", repo, "--json", field)
    if res.returncode != 0:
        return ""
    try:
        data: Any = json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        return ""
    value: Any = data.get(field)
    if field == "mergeCommit" and isinstance(value, dict):
        return str(value.get("oid") or "")
    return str(value or "")


def _remote_tag_oid(tag: str) -> str:
    res = _git("ls-remote", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    if res.returncode != 0:
        return ""
    direct = ""
    peeled = ""
    for line in res.stdout.splitlines():
        parts: list[str] = line.split()
        if len(parts) < 2:
            continue
        if parts[1] == f"refs/tags/{tag}^{{}}":
            peeled = parts[0]
        elif parts[1] == f"refs/tags/{tag}":
            direct = parts[0]
    return peeled or direct


def _redacted_notes(notes_file: Path) -> Path:
    text = notes_file.read_text(encoding="utf-8")
    text = redact.redact_tmpdir_paths(text)
    text = redact.redact(text)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
    handle.write(text)
    handle.close()
    return Path(handle.name)


def _promote_release(*, version: str, repo: str, root: Path) -> proc.CommandResult:
    return proc.run([sys.executable, str(root / "python/cli.py"), "release", "promote", version, "--repo", repo], cwd=str(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release finish")
    parser.add_argument("--version", required=True)
    parser.add_argument("--notes-file", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args(argv)
    if not _SEMVER_RE.fullmatch(args.version):
        return _e(msg=f"ERROR=invalid semver: {args.version}", code=2)
    notes = Path(args.notes_file)
    if not notes.is_file():
        return _e(msg=f"ERROR=notes file not found: {notes}", code=2)
    if not _REPO_RE.fullmatch(args.repo):
        return _e(msg=f"ERROR=invalid --repo value: {args.repo}", code=2)
    if not re.fullmatch(r"[0-9]+", args.pr):
        return _e(msg=f"ERROR=invalid --pr value: {args.pr}", code=2)
    root = _repo_root()
    origin_repo = _origin_repo(root)
    if origin_repo != args.repo:
        return _e(msg=f"ERROR=origin-repo-mismatch: origin ({origin_repo}) != --repo ({args.repo})")
    old_cwd = Path.cwd()
    os.chdir(root)
    redacted_notes = _redacted_notes(notes)
    try:
        tag = f"v{args.version}"
        merge_oid = ""
        for attempt in range(5):
            if not _fetch_origin_main():
                return 1
            merge_oid = _query_pr(repo=args.repo, pr=args.pr, field="mergeCommit")
            if merge_oid and merge_oid != "null" and _SHA_RE.fullmatch(merge_oid):
                break
            merge_oid = ""
            if attempt < 4:
                time.sleep(2)
        if not _fetch_origin_main():
            return 1
        target = merge_oid
        if not target:
            state = _query_pr(repo=args.repo, pr=args.pr, field="state")
            origin_main = _git("rev-parse", "origin/main^{commit}").stdout.strip()
            if state == "MERGED" and origin_main and _plugin_version_at(origin_main) == args.version:
                target = origin_main
            else:
                return _e(msg="ERROR=merge-commit-missing")
        resolved = False
        on_origin_main = False
        for attempt in range(5):
            if not _fetch_origin_main():
                return 1
            resolved = _git("rev-parse", "--verify", f"{target}^{{commit}}").returncode == 0
            if not resolved:
                _ = _git("fetch", "origin", target)
                resolved = _git("rev-parse", "--verify", f"{target}^{{commit}}").returncode == 0
            if resolved:
                origin_main = _git("rev-parse", "origin/main^{commit}").stdout.strip()
                target_oid = _git("rev-parse", f"{target}^{{commit}}").stdout.strip()
                on_origin_main = _git("merge-base", "--is-ancestor", target, "origin/main").returncode == 0 or target_oid == origin_main
                if on_origin_main:
                    break
            if attempt < 4:
                time.sleep(2)
        if not resolved:
            return _e(msg="ERROR=fetch-failed: could not resolve TARGET_OID after fetch")
        if not on_origin_main:
            return _e(msg="ERROR=target-oid-not-on-origin-main")
        at_version = _plugin_version_at(target)
        env_at = os.environ.get("LARCH_RELEASE_FINISH_AT_VERSION", "")
        if env_at and env_at != at_version:
            return _e(msg=f"ERROR=LARCH_RELEASE_FINISH_AT_VERSION ({env_at}) != plugin.json at TARGET_OID ({at_version})")
        if at_version != args.version:
            return _e(msg=f"ERROR=version mismatch at TARGET_OID: expected {args.version} got {at_version or '<empty>'}")
        remote_oid = _remote_tag_oid(tag)
        if remote_oid and remote_oid != target:
            return _e(msg=f"ERROR=remote tag {tag} exists on different commit ({remote_oid} != {target})")
        local = _git("rev-parse", "--verify", f"{tag}^{{commit}}")
        if local.returncode == 0:
            local_oid = local.stdout.strip()
            if local_oid != target:
                if remote_oid == target:
                    if _git("tag", "-f", tag, target).returncode != 0:
                        return 1
                else:
                    return _e(msg=f"ERROR=local tag {tag} points at {local_oid} not {target}")
        else:
            if _git("tag", tag, target).returncode != 0:
                return 1
        if not remote_oid:
            push = _git("push", "origin", tag)
            if push.returncode != 0:
                remote_oid = _remote_tag_oid(tag)
                if not remote_oid or remote_oid != target:
                    return _e(msg="ERROR=tag push failed and remote tag missing or on wrong OID")
        if _gh("release", "view", tag, "--repo", args.repo).returncode == 0:
            if _gh("release", "edit", tag, "--repo", args.repo, "--title", tag, "--notes-file", str(redacted_notes)).returncode != 0:
                return 1
            action = "edit"
        else:
            if _gh("release", "create", tag, "--repo", args.repo, "--title", tag, "--notes-file", str(redacted_notes)).returncode != 0:
                return 1
            action = "create"
        if _promote_release(version=args.version, repo=args.repo, root=root).returncode != 0:
            return _e(msg="ERROR=promote-release-failed")
        print(f"RELEASE_ACTION={action}")
        print(f"TARGET_OID={target}")
        print(f"TAG={tag}")
        print(f"VERSION={args.version}")
        return 0
    finally:
        redacted_notes.unlink(missing_ok=True)
        os.chdir(old_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
