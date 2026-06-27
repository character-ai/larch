# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: FURB167, SIM102
# pylint: skip-file
"""Read-only release preparation helper."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from larch.core import config
from larch.core import proc
import version_bump
from larch.errors import ShipError

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_PR_SUFFIX_RE = re.compile(r"\(#([0-9]+)\)$")
_git_cwd: str | None = None


def _emit_error(token: str, *diagnostics: str, extra: list[str] | None = None) -> int:
    print(f"ERROR={token}")
    for line in extra or []:
        print(line)
    for diag in diagnostics:
        if diag:
            print(diag, file=sys.stderr)
    return 1


def _gh_json(argv: list[str]) -> object | None:
    res = proc.run(["gh", *argv])
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout or "null")
    except json.JSONDecodeError:
        return None


def _git(*argv: str) -> proc.CommandResult:
    return proc.run(["git", *argv], cwd=_git_cwd)


def _git_stdout(*argv: str) -> str:
    return _git(*argv).stdout.strip()


def _tsv(value: object) -> str:
    return str(value if value is not None else "").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _semver_tuple(v: str) -> tuple[int, int, int]:
    a, b, c = v.split(".")
    return int(a), int(b), int(c)


def _apply_override(*, current: str, override: str) -> tuple[str, str]:
    bump = override.upper()
    maj, min_, patch = _semver_tuple(current)
    if bump == "MAJOR":
        return bump, f"{maj + 1}.0.0"
    if bump == "MINOR":
        return bump, f"{maj}.{min_ + 1}.0"
    return bump, f"{maj}.{min_}.{patch + 1}"


def _origin_repo(repo_root: Path) -> str | None:
    override = __import__("os").environ.get("LARCH_RELEASE_PREPARE_ORIGIN_REPO", "")
    if override:
        return override
    res = proc.run(
        ["python3", str(repo_root / "python" / "cli.py"), "gh", "remote-repo", "origin"],
        cwd=str(repo_root),
    )
    return res.stdout.strip() if res.returncode == 0 else None


def _write_pr_row(*, path: Path, pr: dict[str, object]) -> None:
    labels = pr.get("labels")
    label_names = ""
    if isinstance(labels, list):
        label_names = ",".join(str(x.get("name", "")) for x in labels if isinstance(x, dict))
    author = pr.get("author")
    if isinstance(author, dict):
        author_login = str(author.get("login") or "unknown")
    else:
        author_login = "unknown"
    row = [pr.get("number", ""), pr.get("title", ""), label_names, author_login, pr.get("url", "")]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(_tsv(x) for x in row) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release prepare")
    parser.add_argument("--repo", default="character-ai/larch")
    parser.add_argument("--bump", choices=["major", "minor", "patch"])
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    if not _REPO_RE.fullmatch(args.repo):
        return _emit_error("invalid-args", f"invalid --repo value: {args.repo}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[3]
    global _git_cwd  # noqa: PLW0603
    _git_cwd = str(repo_root)
    if _origin_repo(repo_root) != args.repo:
        return _emit_error("origin-repo-mismatch", f"origin does not match --repo ({args.repo})")
    releases = _gh_json(["release", "list", "--repo", args.repo, "--json", "tagName,isLatest", "--limit", "100"])
    if not isinstance(releases, list):
        return _emit_error("gh-release-list-failed", "gh release list failed")
    latest = [r.get("tagName") for r in releases if isinstance(r, dict) and r.get("isLatest") is True]
    if len(latest) != 1:
        return _emit_error("no-unique-latest-release", extra=[f"LATEST_COUNT={len(latest)}"])
    baseline = str(latest[0])
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", baseline):
        return _emit_error("invalid-baseline-tag", f"baseline tag has invalid format: {baseline}")
    if _git("fetch", "origin", "main", "--tags").returncode != 0:
        return _emit_error("baseline-tag-unresolvable", "git fetch origin main --tags failed")
    if _git("rev-parse", "--verify", f"{baseline}^{{commit}}").returncode != 0:
        return _emit_error("baseline-tag-unresolvable", f"baseline tag not resolvable: {baseline}")
    if _git("merge-base", "--is-ancestor", baseline, "origin/main").returncode != 0:
        return _emit_error("baseline-not-on-main", f"baseline tag {baseline} is not an ancestor of origin/main")
    main_oid = _git_stdout("rev-parse", "main^{commit}")
    origin_oid = _git_stdout("rev-parse", "origin/main^{commit}")
    head_oid = _git_stdout("rev-parse", "HEAD^{commit}")
    if not main_oid or not origin_oid:
        return _emit_error("stale-local-main", "main or origin/main not resolvable")
    if main_oid != origin_oid:
        return _emit_error("stale-local-main", f"main ({main_oid}) != origin/main ({origin_oid})")
    if head_oid != origin_oid:
        return _emit_error("stale-local-main", f"HEAD ({head_oid}) != origin/main ({origin_oid})")
    prs = _gh_json(["pr", "list", "--repo", args.repo, "--state", "open", "--json", "headRefName"])
    if not isinstance(prs, list):
        return _emit_error("release-pr-list-failed", "gh pr list failed")
    if any(re.fullmatch(r"release/v[0-9]+\.[0-9]+\.[0-9]+", str(p.get("headRefName", ""))) for p in prs if isinstance(p, dict)):
        return _emit_error("release-cut-in-progress", f"open release/v* PR exists on {args.repo}")
    origin_plugin = _git("show", "origin/main:.claude-plugin/plugin.json")
    if origin_plugin.returncode == 0:
        try:
            ov: Any = json.loads(origin_plugin.stdout).get("version")
        except json.JSONDecodeError:
            ov = None
        if isinstance(ov, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", ov):
            if _semver_tuple(ov) > _semver_tuple(baseline[1:]):
                log = _git("log", f"{baseline}..origin/main", "--format=%s")
                if re.search(r"^Release v[0-9]+\.[0-9]+\.[0-9]+( \(#[0-9]+\))?$", log.stdout, re.M):
                    return _emit_error("release-already-cut", f"origin/main version {ov} is ahead of baseline {baseline[1:]} with Release commit")
    subjects = _git("log", f"{baseline}..origin/main", "--format=%s").stdout.splitlines()
    pr_nums: list[int] = sorted({int(m.group(1)) for s in subjects for m in [_PR_SUFFIX_RE.search(s)] if m})
    pr_list_file = out_dir / "pr-list.tsv"
    pr_list_file.write_text("", encoding="utf-8")
    written: set[int] = set()
    ignored: set[int] = set()
    missing: list[str] = []
    for n in pr_nums:
        pr = _gh_json(["pr", "view", str(n), "--repo", args.repo, "--json", "number,title,labels,author,url"])
        if not isinstance(pr, dict):
            missing.append(str(n))
            continue
        if str(pr.get("title", "")).startswith(config.TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX):
            ignored.add(int(pr.get("number", n)))
            continue
        _write_pr_row(path=pr_list_file, pr=pr)
        written.add(int(pr.get("number", n)))
    if missing:
        return _emit_error("pr-metadata-incomplete", f"could not fetch PR metadata for: {' '.join(missing)}")
    orphan_shas: list[str] = []
    for line in _git("log", f"{baseline}..origin/main", "--format=%H %s").stdout.splitlines():
        if not line.strip():
            continue
        sha, _, subj = line.partition(" ")
        if _PR_SUFFIX_RE.search(subj):
            continue
        api = proc.run(["gh", "api", f"repos/{args.repo}/commits/{sha}/pulls"])
        if api.returncode != 0:
            return _emit_error("pr-metadata-incomplete", f"commits-to-pulls lookup failed for {sha}: {api.stderr.strip()}")
        try:
            pulls: Any = json.loads(api.stdout or "[]")
        except json.JSONDecodeError:
            return _emit_error("pr-metadata-incomplete", f"commits-to-pulls lookup failed for {sha}")
        if pulls:
            p = pulls[0]
            num = int(p.get("number", 0))
            if num in written or num in ignored:
                continue
            if str(p.get("title", "")).startswith(config.TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX):
                ignored.add(num)
                continue
            row = {
                "number": num,
                "title": p.get("title", ""),
                "labels": p.get("labels", []),
                "author": {"login": (p.get("user") or {}).get("login", "unknown")},
                "url": p.get("html_url", ""),
            }
            _write_pr_row(path=pr_list_file, pr=row)
            written.add(num)
            print(f"NOTE: commit {sha} resolved to PR #{num} via GitHub API ({subj})", file=sys.stderr)
        else:
            print(f"WARN: commit {sha} has no associated pull request: {subj}", file=sys.stderr)
            orphan_shas.append(sha)
    if orphan_shas:
        csv = ",".join(orphan_shas)
        print(f"UNMATCHED_COMMITS={csv}")
        return _emit_error("unmatched-commits", f"commits with no associated pull request: {csv}")
    try:
        classification = version_bump.classify_bump(proc, base_ref=baseline, head_ref="origin/main", cwd=str(repo_root))
    except ShipError as exc:
        return _emit_error("classify-bump-failed", f"classify-bump failed: {exc}")
    current = classification.current_version
    new = classification.new_version
    bump = classification.bump_type
    if args.bump:
        bump, new = _apply_override(current=current, override=args.bump)
    print(f"BASELINE_TAG={baseline}")
    print(f"CURRENT_VERSION={current}")
    print(f"NEW_VERSION={new}")
    print(f"BUMP_TYPE={bump}")
    print(f"PR_COUNT={len(written)}")
    print(f"IGNORED_LARCHLOG_PR_COUNT={len(ignored)}")
    print(f"PR_LIST_FILE={pr_list_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
