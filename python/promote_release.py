# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Release promotion CLI helpers."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from larch.core import logging_util
from larch.core import proc

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def _repo_args(repo: str | None) -> list[str]:
    return ["--repo", repo] if repo else []


def _err(msg: str) -> int:
    if not msg.startswith("ERROR="):
        msg = "ERROR=" + msg.removeprefix("ERROR: ").removeprefix("ERROR=")
    logging_util.diagnostic(msg)
    return 1


def promote_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release promote")
    parser.add_argument("version")
    parser.add_argument("--repo")
    args = parser.parse_args(argv)
    if args.repo and not _REPO_RE.fullmatch(args.repo):
        return _err(f"invalid --repo value: {args.repo}")
    if not _SEMVER_RE.fullmatch(args.version):
        return _err(f"invalid semver format: {args.version} (expected X.Y.Z)")
    logging_util.quiet_init(argv0="promote-release.sh")
    tag = f"v{args.version}"
    repo_args = _repo_args(args.repo)
    if proc.run(["gh", "release", "view", tag, *repo_args]).returncode != 0:
        return _err(f"release {tag} not found.")
    cur = proc.run([
        "gh", "release", "list", *repo_args, "--json", "tagName,isLatest", "--jq",
        'map(select(.isLatest)) | .[0].tagName // ""',
    ])
    if cur.returncode != 0:
        return _err(cur.stderr or "gh release list failed")
    if cur.stdout.strip() == tag:
        pre = proc.run(["gh", "release", "view", tag, *repo_args, "--json", "isPrerelease", "--jq", ".isPrerelease"])
        if pre.returncode != 0:
            return _err(pre.stderr or f"gh release view {tag} failed")
        if pre.stdout.strip() == "true":
            if proc.run(["gh", "release", "edit", tag, *repo_args, "--prerelease=false"]).returncode != 0:
                return _err(f"gh release edit {tag} failed")
            logging_util.emit(f"{tag} is already the latest release; cleared pre-release flag.")
        else:
            logging_util.emit(f"{tag} is already the latest release.")
        return 0
    if proc.run(["gh", "release", "edit", tag, *repo_args, "--latest", "--prerelease=false"]).returncode != 0:
        return _err(f"gh release edit {tag} failed")
    logging_util.emit(f"Promoted {tag} to latest release.")
    return 0


def _jq_bool(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def promote_latest_main(argv: list[str] | None = None) -> int:
    logging_util.reset_quiet_state()
    parser = argparse.ArgumentParser(prog="cli.py release promote-latest")
    parser.add_argument("--repo", default="character-ai/larch")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not _REPO_RE.fullmatch(args.repo):
        return _err(f"ERROR=Invalid --repo value: {args.repo}")
    res = proc.run([
        "gh", "release", "list", "--repo", args.repo, "--limit", "100", "--exclude-drafts",
        "--json", "tagName,isPrerelease,isLatest,publishedAt,createdAt",
    ])
    if res.returncode != 0:
        return _err((res.stderr or "ERROR=gh release list failed").strip())
    try:
        releases: Any = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        return _err("ERROR=Invalid gh release list JSON")
    releases = [r for r in releases if isinstance(r, dict)]
    releases.sort(key=lambda r: str(r.get("publishedAt") or ""), reverse=True)
    if not releases:
        return _err(f"ERROR=No non-draft releases found for {args.repo}")
    latest = releases[0]
    tag = str(latest.get("tagName") or "")
    was_pre = _jq_bool(latest.get("isPrerelease"))
    was_latest = _jq_bool(latest.get("isLatest"))
    published = str(latest.get("publishedAt") or latest.get("createdAt") or "")
    print(f"RELEASE_REPO={args.repo}")
    print(f"RELEASE_TAG={tag}")
    print(f"RELEASE_PUBLISHED_AT={published}")
    print(f"RELEASE_WAS_PRERELEASE={was_pre}")
    print(f"RELEASE_WAS_LATEST={was_latest}")
    if args.dry_run:
        print("DRY_RUN=true")
        return 0
    if was_pre == "false" and was_latest == "true":
        print("RELEASE_ALREADY_LATEST=true")
        return 0
    print("RELEASE_ALREADY_LATEST=false")
    edit = proc.run(["gh", "release", "edit", tag, "--repo", args.repo, "--prerelease=false", "--latest"])
    if edit.returncode != 0:
        return _err((edit.stderr or "ERROR=gh release edit failed").strip())
    ver = proc.run([
        "gh", "release", "list", "--repo", args.repo, "--limit", "100", "--exclude-drafts",
        "--json", "tagName,isPrerelease,isLatest",
    ])
    if ver.returncode != 0:
        return _err("ERROR=Promoted release verification failed")
    try:
        found: Any = next(r for r in json.loads(ver.stdout or "[]") if r.get("tagName") == tag)
    except (json.JSONDecodeError, StopIteration):
        return _err(f"ERROR=Promoted release {tag} was not found during verification")
    is_pre = _jq_bool(found.get("isPrerelease"))
    is_latest = _jq_bool(found.get("isLatest"))
    print(f"RELEASE_IS_PRERELEASE={is_pre}")
    print(f"RELEASE_IS_LATEST={is_latest}")
    if is_pre != "false" or is_latest != "true":
        return _err(f"ERROR=Release {tag} verification failed: isPrerelease={is_pre} isLatest={is_latest}")
    return 0
