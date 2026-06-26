# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: ARG001, E701, E702, E703, F401, FURB162, FURB167, PERF401, PIE810, PLR2004, PLR5501, RUF059, SIM105, SIM115
# pylint: skip-file
"""Audit run-log helper CLI verbs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import oos_disposition
import proc
from architectural_guidelines import CLEAN_PRESENTATION_NOTE
from run_log_tolerance import stale_bail_heading_with_pr_evidence
from self_review_tally import self_review_tally_items

_CANONICAL = {"code-quality", "risk-integration", "correctness", "architecture", "security"}
_DESIGN_RUN_TITLE_RE = re.compile(r"^chore\(larch-logs\): design run [0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$")
_DESIGN_RUN_ID_RE = re.compile(r"^chore\(larch-logs\): design run ([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})$")
_TERMINAL_RE = re.compile(r"(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?)$")
GENERIC_CODEX_SLOTS = frozenset({"generalist", "codex-plan-generic"})


def _validate_skill( *,skill: str, prog: str) -> bool:
    if skill in {"design", "implement"}:
        return True
    msg = f"{prog}: --skill is required (allowed: design, implement)" if not skill else f"{prog}: --skill must be design or implement (got: {skill})"
    print(msg, file=sys.stderr)
    return False


def _json_line(obj: dict[str, object]) -> None:
    print(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))


def match_audit_report_title( *,skill: str, title: str) -> bool:
    if skill == "implement":
        return bool(re.match(r"^\[(Run Logs Audit |Implement Run Logs Audit ).* Report\]", title))
    if skill == "design":
        return bool(re.match(r"^\[Design Run Logs Audit .* Report\]", title))
    return False


def match_design_run_log_pr_title(title: str) -> bool:
    return bool(_DESIGN_RUN_TITLE_RE.match(title or ""))


def extract_design_run_log_pr_id(title: str) -> str:
    m = _DESIGN_RUN_ID_RE.match(title or "")
    return m.group(1) if m else ""


def title_match_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs title-match")
    p.add_argument("--skill", required=True)
    p.add_argument("--title", required=True)
    args = p.parse_args(argv)
    if not _validate_skill(skill=args.skill, prog="audit-title-matcher.sh"):
        return 1
    return 0 if match_audit_report_title(skill=args.skill, title=args.title) else 1


def title_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs title")
    p.add_argument("--skill", required=True)
    p.add_argument("--pr-list", required=True)
    p.add_argument("--timestamp", required=True)
    args = p.parse_args(argv)
    if not _validate_skill(skill=args.skill, prog="audit-title.sh"):
        return 1
    nums = sorted({int(tok.strip()) for tok in args.pr_list.split(",") if tok.strip().isdigit()})
    if not nums:
        print("audit-title.sh: --pr-list contains no valid PR numbers", file=sys.stderr)
        return 1
    prefix = "Implement Run Logs Audit" if args.skill == "implement" else "Design Run Logs Audit"
    if len(nums) == 1:
        prs = f"#{nums[0]}"
    elif nums[-1] - nums[0] + 1 == len(nums):
        prs = f"#{nums[0]}-#{nums[-1]}"
    else:
        prs = ", ".join(f"#{n}" for n in nums)
    print(f"TITLE=[{prefix} {args.timestamp} Report] PRs {prs}")
    return 0


def pacific_timestamp_main(argv: list[str] | None = None) -> int:
    if argv:
        print("audit-pacific-timestamp.sh: unexpected argument(s)", file=sys.stderr)
        return 1
    try:
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        ts = now.strftime("%Y-%m-%dT%H:%M%z")
        ts = ts[:-2] + ":" + ts[-2:]
        source = "tz_america_los_angeles"
    except ZoneInfoNotFoundError:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
        source = "utc_fallback"
    print(f"PACIFIC_TIMESTAMP={ts}")
    print(f"PACIFIC_TIMESTAMP_SOURCE={source}")
    return 0


def _load_json( *,text: str, default: object) -> object:
    try:
        return json.loads(text or "null")
    except json.JSONDecodeError:
        return default


def _clean_reason(text: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", text).strip()


def _redact_remote_url(url: str) -> str:
    return re.sub(r"(?<=//)[^/@]+@", "<redacted>@", url)


def _git_commit(ref: str) -> str:
    return proc.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"]).stdout.strip()


def _run_dir_invalid( *,canon: Path, skill: str) -> str:
    parts = canon.parts
    for idx, part in enumerate(parts):
        if part != "larch-logs":
            continue
        if idx + 1 >= len(parts):
            return f"run-dir must live under larch-logs/{skill}: {canon}"
        found_skill = parts[idx + 1]
        if found_skill in {"design", "implement"}:
            if found_skill != skill:
                return f"run-dir must live under larch-logs/{skill} for --skill={skill}: {canon}"
            if len(parts) == idx + 2:
                return f"run-dir resolves to skill log root instead of a specific run: {canon}"
            return ""
    return ""


def _round_number(path: Path) -> int | None:
    m = re.fullmatch(r"round-([0-9]+)", path.name)
    return int(m.group(1)) if m else None


def _codex_round_adherence_violations(run_dir: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    for manifest in run_dir.glob("round-*/panel-manifest.ndjson"):
        round_num = _round_number(manifest.parent)
        if round_num is None or round_num in {1, 2}:
            continue
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            slot = str(row.get("slot") or "")
            if row.get("tool") == "codex" and slot in GENERIC_CODEX_SLOTS:
                violations.append((round_num, slot))
    return violations


def _codex_round_adherence_scan_obj(*, name: str, pr: int, run_dir: Path) -> dict[str, object]:
    violations = _codex_round_adherence_violations(run_dir)
    obj: dict[str, object] = {"scan": name, "pr": pr, "result": "pass" if not violations else "fail"}
    if violations:
        obj["rounds_with_generic_codex"] = sorted({round_num for round_num, _slot in violations})
        obj["violations"] = [{"round": round_num, "slot": slot} for round_num, slot in violations]
    return obj


def _guideline_assessment_scan_obj(*, name: str, pr: int, run_dir: Path) -> dict[str, object]:
    path = run_dir / "architectural-guideline-assessment.md"
    if not path.exists() and not path.is_symlink():
        return {
            "scan": name,
            "pr": pr,
            "result": "informational",
            "detail": "no committed guideline assessment artifact; expected for older runs or absent/invalid guidelines",
        }
    if path.is_symlink() or not path.is_file():
        return {"scan": name, "pr": pr, "result": "fail", "detail": "assessment artifact must be a regular non-symlink file"}
    body = path.read_text(encoding="utf-8", errors="replace")
    if not body.strip():
        return {"scan": name, "pr": pr, "result": "fail", "detail": "assessment artifact is empty"}
    kind = "clean" if body.rstrip("\n") == CLEAN_PRESENTATION_NOTE else "deviation"
    return {"scan": name, "pr": pr, "result": "pass", "assessment_kind": kind}


_NAMED_RUN_SCAN_HANDLERS = {
    "codex-round1-adherence": _codex_round_adherence_scan_obj,
    "guideline-assessment": _guideline_assessment_scan_obj,
}


def _merged_prs(repo: str) -> list[dict[str, object]] | None:
    owner, name = repo.split("/", 1)
    page = 1
    out: dict[int, dict[str, object]] = {}
    while page <= 10000:
        res = proc.run(["gh", "api", f"repos/{owner}/{name}/pulls?state=closed&per_page=100&page={page}"])
        if res.returncode != 0:
            print(f"audit-resolve-prs: gh api pulls page {page} failed", file=sys.stderr)
            return None
        data = _load_json(text=res.stdout, default=[])
        if not isinstance(data, list):
            print(f"audit-resolve-prs: gh api pulls page {page} returned invalid JSON", file=sys.stderr)
            return None
        batch: list[dict[str, object]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            base = item.get("base")
            if item.get("merged_at") and isinstance(base, dict) and base.get("ref") == "main":
                batch.append({"number": item.get("number"), "mergedAt": item.get("merged_at"), "title": item.get("title", "")})
        for pr in batch:
            try:
                out[int(pr["number"])] = pr
            except (TypeError, ValueError):
                pass
        if len(data) < 100:
            break
        page += 1
    return sorted(out.values(), key=lambda p: str(p.get("mergedAt") or ""))


def _skill_filter( *,skill: str, prs: list[dict[str, object]]) -> list[dict[str, object]]:
    if skill == "design":
        return [p for p in prs if match_design_run_log_pr_title(str(p.get("title") or ""))]
    return [p for p in prs if not match_design_run_log_pr_title(str(p.get("title") or ""))]


def _kv_error(msg: str) -> int:
    safe = re.sub(r"[\x00-\x1f\x7f]", "", msg)
    print("IMPLICIT_SINCE_LAST_AUDIT=false")
    print("PRIOR_REPORT_NUMBER=")
    print("PR_LIST=")
    print("PR_COUNT=0")
    print("RESOLVED_ECHO=")
    print(f"ERROR={safe}")
    return 0


def _kv_ok( *,implicit: str, prior: str, nums: list[int], echo: str) -> int:
    pr_list = ",".join(str(n) for n in nums)
    print(f"IMPLICIT_SINCE_LAST_AUDIT={implicit}")
    print(f"PRIOR_REPORT_NUMBER={prior}")
    print(f"PR_LIST={pr_list}")
    print(f"PR_COUNT={len(nums)}")
    safe_echo = re.sub(r"[\x00-\x1f\x7f]", "", echo)
    print(f"RESOLVED_ECHO={safe_echo}")
    print("ERROR=")
    return 0


def resolve_prs_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs resolve-prs", add_help=True)
    p.add_argument("--skill", required=True)
    p.add_argument("--repo", default="character-ai/larch")
    p.add_argument("--verbal-description", default="")
    try:
        args = p.parse_args(argv)
    except SystemExit:
        return 1
    if not _validate_skill(skill=args.skill, prog="audit-resolve-prs.sh"):
        return 1
    verbal = args.verbal_description.strip()

    def list_after( *,ts: str, scope: str) -> list[int] | None:
        prs = _merged_prs(args.repo)
        if prs is None:
            _kv_error(f"merged PR listing/filter failed during {scope}: gh api failed or returned invalid merged PR data")
            return None
        return [int(p["number"]) for p in _skill_filter(skill=args.skill, prs=[p for p in prs if str(p.get("mergedAt") or "") > ts])]

    if not verbal or verbal == "since last audit":
        implicit = "true" if not verbal else "false"
        res = proc.run(["gh", "issue", "list", "--state", "all", "--limit", "100000", "--label", "audit-report", "--repo", args.repo, "--json", "number,title,createdAt"])
        if res.returncode != 0:
            return _kv_error(f"gh issue list failed while resolving prior audit-report issue for --skill={args.skill}")
        prior_list = _load_json(text=res.stdout, default=[])
        if not isinstance(prior_list, list) or not prior_list:
            return _kv_error(f"no prior audit-report issue found for --skill={args.skill}")
        prior_list = sorted([x for x in prior_list if isinstance(x, dict)], key=lambda x: str(x.get("createdAt") or ""), reverse=True)
        prior_num = ""
        for issue in prior_list:
            if match_audit_report_title(skill=args.skill, title=str(issue.get("title") or "")):
                prior_num = str(issue.get("number") or "")
                break
        if not prior_num:
            return _kv_error(f"no prior audit-report issue found for --skill={args.skill}")
        body_res = proc.run(["gh", "issue", "view", prior_num, "--repo", args.repo, "--json", "body"])
        body = ""
        if body_res.returncode != 0:
            return _kv_error(f"gh issue view failed for prior audit-report #{prior_num}")
        body_obj = _load_json(text=body_res.stdout, default={})
        if isinstance(body_obj, dict):
            body = str(body_obj.get("body") or "")
        m = re.search(r"audited_pr_range:[\s\S]*?\n\s*last:\s*['\"]?([0-9]+)['\"]?", _top_frontmatter(body))
        if not m:
            return _kv_error(f"prior audit-report #{prior_num} has malformed or missing frontmatter (audited_pr_range.last)")
        last_pr = m.group(1)
        merged_res = proc.run(["gh", "pr", "view", last_pr, "--repo", args.repo, "--json", "mergedAt"])
        merged_obj = _load_json(text=merged_res.stdout, default={}) if merged_res.returncode == 0 else {}
        merged_at = str(merged_obj.get("mergedAt") or "") if isinstance(merged_obj, dict) else ""
        if not merged_at:
            return _kv_error(f"could not get mergedAt for prior PR #{last_pr}")
        nums = list_after(ts=merged_at, scope="since last audit")
        if nums is None:
            return 0
        if not nums:
            return _kv_error(f"no new PRs merged after prior audit (last PR: #{last_pr}, skill={args.skill})")
        refs = ", ".join(f"#{n}" for n in nums)
        extra = ", implicit default: empty/omitted positional" if implicit == "true" else ""
        return _kv_ok(implicit=implicit, prior=prior_num, nums=nums, echo=f"Resolved since last audit (--skill={args.skill}{extra}) to: [{refs}]. Proceeding.")
    m_last = re.match(r"^last\s+([0-9]+)\s+PRs?$", verbal)
    if m_last:
        n = int(m_last.group(1))
        prs = _merged_prs(args.repo)
        if prs is None:
            return _kv_error(f"merged PR listing/filter failed during last {n} PRs: gh api failed or returned invalid merged PR data")
        filtered = _skill_filter(skill=args.skill, prs=prs)
        nums = [int(p["number"]) for p in (filtered[-n:] if n > 0 else [])]
        if not nums:
            return _kv_error(f"empty PR list after merge-time sort (last {n} PRs, skill={args.skill})")
        return _kv_ok(implicit="false", prior="", nums=nums, echo=f"Resolved last {n} PRs (--skill={args.skill}) to: [{', '.join(f'#{x}' for x in nums)}]. Proceeding.")
    if verbal.startswith("since "):
        ts = verbal[len("since "):].strip()
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})", ts):
            return _kv_error(f"since <ISO> must be a full instant (YYYY-MM-DDThh:mm[:ss][.frac][Z|±hh:mm]); got: {ts}")
        nums = list_after(ts=ts, scope=f"since {ts}")
        if nums is None:
            return 0
        if not nums:
            return _kv_error(f"no PRs merged after {ts} (or empty gh result, skill={args.skill})")
        return _kv_ok(implicit="false", prior="", nums=nums, echo=f"Resolved since {ts} (--skill={args.skill}) to: [{', '.join(f'#{x}' for x in nums)}]. Proceeding.")
    m = re.match(r"^(PR\s+)?#([0-9]+)$", verbal)
    if m:
        n = m.group(2)
        res = proc.run(["gh", "pr", "view", n, "--repo", args.repo, "--json", "title"])
        obj = _load_json(text=res.stdout, default={}) if res.returncode == 0 else {}
        title = str(obj.get("title") or "") if isinstance(obj, dict) else ""
        if not title:
            return _kv_error(f"could not resolve PR #{n} title for --skill={args.skill}")
        if (args.skill == "design") != match_design_run_log_pr_title(title):
            return _kv_error(f"PR #{n} title does not match --skill={args.skill}")
        return _kv_ok(implicit="false", prior="", nums=[int(n)], echo=f"Resolved {verbal} (--skill={args.skill}) to: [#{n}]. Proceeding.")
    return _kv_error(f"unrecognized verbal description: {verbal}")


def preflight_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs preflight")
    p.add_argument("--skill", required=True)
    p.add_argument("--repo", default="character-ai/larch")
    p.add_argument("--allow-concurrent", action="store_true")
    args = p.parse_args(argv)
    if args.skill not in {"design", "implement"}:
        print("PREFLIGHT_OK=false")
        print(f"REASON=--skill must be design or implement (got: {args.skill})")
        return 0
    if proc.run(["git", "fetch", "origin", "main"]).returncode != 0:
        print("PREFLIGHT_OK=false\nREASON=git fetch origin main failed")
        return 0
    branch = proc.run(["git", "branch", "--show-current"]).stdout.strip()
    if branch == "main" and proc.run(["git", "pull", "--ff-only", "origin", "main"]).returncode != 0:
        print("PREFLIGHT_OK=false\nREASON=git pull --ff-only origin main failed (working tree may be dirty or branch is not ff-only)")
        return 0
    main_oid = _git_commit("main")
    origin_oid = _git_commit("origin/main")
    if not main_oid or not origin_oid:
        print("PREFLIGHT_OK=false\nREASON=local main or origin/main is not resolvable")
        return 0
    if main_oid != origin_oid:
        print("PREFLIGHT_OK=false\nREASON=local main is stale or diverged from origin/main")
        return 0
    if proc.run(["git", "status", "--porcelain"]).stdout.strip():
        print("PREFLIGHT_OK=false\nREASON=working tree is dirty")
        return 0
    remote_url = proc.run(["git", "config", "--get", "remote.origin.url"]).stdout.strip()
    gh_res = proc.run(["gh", "repo", "view", args.repo, "--json", "url"])
    gh_url = ""
    if gh_res.returncode == 0:
        obj = _load_json(text=gh_res.stdout, default={})
        gh_url = str(obj.get("url") or "") if isinstance(obj, dict) else ""
    rem_match = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?$", remote_url)
    remote_repo = rem_match.group(1) if rem_match else ""
    gh_repo = gh_url.removeprefix("https://github.com/")
    if not remote_repo or not gh_repo:
        safe_remote = _redact_remote_url(remote_url) if remote_url else "<empty>"
        safe_gh = _redact_remote_url(gh_url) if gh_url else "<empty>"
        print(f"PREFLIGHT_OK=false\nREASON=could not determine repo identity (remote={safe_remote} gh={safe_gh})")
        return 0
    if remote_repo != gh_repo:
        print(f"PREFLIGHT_OK=false\nREASON=repo mismatch: normalized_remote_origin={remote_repo} gh_repo_identity={gh_repo} (expected clone to match gh repo view {args.repo})")
        return 0
    if not args.allow_concurrent:
        cutoff = (datetime.now(UTC) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = proc.run(["gh", "issue", "list", "--state", "all", "--label", "audit-report", "--repo", args.repo, "--json", "number,createdAt", "--limit", "50"])
        arr = _load_json(text=res.stdout, default=[]) if res.returncode == 0 else []
        if isinstance(arr, list) and any(isinstance(x, dict) and str(x.get("createdAt") or "") > cutoff for x in arr):
            print("PREFLIGHT_OK=false\nREASON=audit-report filed within the 5-minute concurrency window; use --allow-concurrent to override")
            return 0
    print("PREFLIGHT_OK=true\nREASON=")
    return 0


def _manifest_epoch(path: Path) -> float:
    try:
        val = json.loads(path.read_text(encoding="utf-8")).get("started_at")
        if isinstance(val, str) and val:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return -9e18


def _manifest_fields( *,path: Path, pr: str = "") -> tuple[str, str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "", "", ""
    return str(data.get("started_at") or ""), str(data.get("larch_version") or ""), str(data.get("closes_issue") or "")


def _parent_issue_number(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = re.search(r"(?m)^ISSUE_NUMBER=([0-9]+)\s*$", text)
    return match.group(1) if match else ""


def _report_pr_view_failed( *,pr: str, field: str, res: proc.CommandResult) -> None:
    reason = _clean_reason(res.stderr or res.stdout or "gh pr view failed")
    print(f"audit-map-runs.sh: MAP_GH_PR_VIEW_FAILED=true PR={pr} FIELD={field} REASON={reason}", file=sys.stderr)


def map_runs_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs map-runs")
    p.add_argument("--skill", required=True)
    p.add_argument("--pr-list", required=True)
    p.add_argument("--repo", default="character-ai/larch")
    p.add_argument("--log-root", default="")
    args = p.parse_args(argv)
    if not _validate_skill(skill=args.skill, prog="audit-map-runs.sh"):
        return 1
    log_root = args.log_root or f"larch-logs/{args.skill}"
    if args.log_root and (log_root == "larch-logs" or log_root.endswith("/larch-logs")):
        log_root = f"{log_root}/{args.skill}"
    if args.log_root and re.search(r"(^|/)larch-logs/(design|implement)$", log_root) and not log_root.endswith(f"/{args.skill}") and log_root != f"larch-logs/{args.skill}":
        print(f"audit-map-runs.sh: --log-root must be larch-logs/{args.skill} when --skill={args.skill} (got: {args.log_root})", file=sys.stderr)
        return 1
    root = Path(log_root)
    if not root.is_dir():
        print(f"audit-map-runs.sh: log root not found: {log_root}", file=sys.stderr)
        return 1
    for token in args.pr_list.split(","):
        pr = token.strip()
        if not pr or not re.fullmatch(r"[0-9]+", pr):
            if pr:
                print(f"audit-map-runs.sh: skipping invalid PR token in --pr-list (non-integer): {pr}", file=sys.stderr)
            continue
        run_id = started = ver = closes = ""
        if args.skill == "design":
            res = proc.run(["gh", "pr", "view", pr, "--repo", args.repo, "--json", "title"])
            if res.returncode != 0:
                _report_pr_view_failed(pr=pr, field="title", res=res)
            obj = _load_json(text=res.stdout, default={}) if res.returncode == 0 else {}
            run_id = extract_design_run_log_pr_id(str(obj.get("title") or "")) if isinstance(obj, dict) else ""
            mf = root / run_id / "manifest.json"
            if run_id and mf.is_file():
                started, ver, _ = _manifest_fields(path=mf)
            print(f"{pr}\t{run_id}\t{started}\t{ver}\t")
            continue
        body_res = proc.run(["gh", "pr", "view", pr, "--repo", args.repo, "--json", "body"])
        if body_res.returncode != 0:
            _report_pr_view_failed(pr=pr, field="body", res=body_res)
            print(f"{pr}\t\t\t\t")
            continue
        body_obj = _load_json(text=body_res.stdout, default={}) if body_res.returncode == 0 else {}
        body = str(body_obj.get("body") or "") if isinstance(body_obj, dict) else ""
        for kw in ("Closes", "Fixes", "Resolves"):
            nums = sorted(set(re.findall(rf"{kw}\s+#([0-9]+)", body, flags=re.I)))
            if len(nums) == 1:
                closes = nums[0]
                break
            if len(nums) > 1:
                print(f"audit-map-runs.sh: MAP_PR_BODY_CLOSING_AMBIGUOUS=true KEYWORD={kw}", file=sys.stderr)
                break
        candidates: list[Path] = []
        if closes:
            for parent in root.glob("*/parent-issue.md"):
                if _parent_issue_number(parent) == closes:
                    candidates.append(parent.parent)
        if candidates:
            candidates.sort(key=lambda d: _manifest_epoch(d / "manifest.json"), reverse=True)
            best_epoch = _manifest_epoch(candidates[0] / "manifest.json")
            tied = [d for d in candidates if _manifest_epoch(d / "manifest.json") == best_epoch]
            if len(tied) > 1:
                joined = ",".join(sorted(d.name for d in tied))
                print(f"audit-map-runs.sh: MAP_PARENT_ISSUE_AMBIGUOUS=true ISSUE_NUMBER={closes} RUNS={joined}", file=sys.stderr)
            else:
                best = candidates[0]
                run_id = best.name
                started, ver, _ = _manifest_fields(path=best / "manifest.json")
        if not run_id:
            manifests: list[Path] = []
            for mf in root.glob("*/manifest.json"):
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    if str(data.get("pr_number") or "") == pr:
                        manifests.append(mf)
                except json.JSONDecodeError:
                    pass
            if manifests:
                manifests.sort(key=_manifest_epoch, reverse=True)
                mf = manifests[0]
                run_id = mf.parent.name
                started, ver, closes2 = _manifest_fields(path=mf)
                closes = closes or closes2
        print(f"{pr}\t{run_id}\t{started}\t{ver}\t{closes}")
    return 0


def _read_json_file(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _round_meta_signals(run_dir: Path) -> tuple[bool, list[dict[str, object]]]:
    signals: list[dict[str, object]] = []
    any_meta = False
    for meta in sorted(run_dir.glob("round-*/round-meta.json")):
        data = _read_json_file(meta)
        if isinstance(data, dict) and isinstance(data.get("reviewer_signals"), list):
            any_meta = True
            signals.extend(x for x in data["reviewer_signals"] if isinstance(x, dict))
    return any_meta, signals


def _scan_required( *,run_dir: Path, pr: int, required: Path | None) -> dict[str, object] | tuple[dict[str, object], bool]:
    if required is None or not required.is_file():
        return {"scan": "required-file-presence", "pr": pr, "result": "skip", "detail": "required-files-tsv not provided"}
    manifest = _read_json_file(run_dir / "manifest.json")
    sr_raw = manifest.get("steps_ran") if isinstance(manifest, dict) else None
    sr = sr_raw if isinstance(sr_raw, dict) else {}
    def has(rel: str) -> bool:
        if "*" in rel:
            return any(p.is_file() for p in run_dir.glob(rel))
        return (run_dir / rel).is_file()
    def steps_false(c: str) -> bool:
        return sr.get(c) is False
    def empty_steps() -> bool:
        return isinstance(manifest, dict) and (sr_raw is None or (isinstance(sr_raw, dict) and not sr_raw))
    def bail_signal() -> bool:
        if stale_bail_heading_with_pr_evidence(run_dir=run_dir, manifest=manifest, pr=pr):
            return False
        fs = run_dir / "final-summary.md"
        if not fs.is_file():
            return False
        for line in fs.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                return bool(_TERMINAL_RE.search(line.strip()))
        return False
    def nonempty_without_step9a1() -> bool:
        return bool(sr) and "step9a1" not in sr
    def cond(c: str, *, chain: bool = False) -> bool:
        if c == "always": return True
        if c == "step5":
            return not steps_false("step5") and (has("code-review-tally.json") or has("review-findings-full.jsonl") or cond("step7a"))
        if c == "step7a":
            if steps_false("step7a"): return False
            if empty_steps() and bail_signal() and not (has("token-report.json") or has("timing-report.json") or has("execution-issues.ndjson") or has("session-transcript.jsonl")): return False
            return has("token-report.json") or has("timing-report.json") or has("execution-issues.ndjson") or has("session-transcript.jsonl") or cond("step8")
        if c == "step8":
            if steps_false("step8"): return False
            if empty_steps() and bail_signal() and not has("version-bump-reasoning.md"): return False
            return has("version-bump-reasoning.md") or has("final-summary.md") or cond("step9a1", chain=True)
        if c == "step9a1":
            if steps_false("step9a1"): return False
            if sr.get("step9a1") is True: return True
            if empty_steps() and bail_signal() and not has("run-statistics.md"): return False
            if bail_signal() and not has("run-statistics.md") and nonempty_without_step9a1(): return False
            return has("run-statistics.md") if chain else True
        if c == "exn-agg-validate-fail":
            f = run_dir / "execution-issues.ndjson"
            return f.is_file() and "merged output failed validation" in f.read_text(encoding="utf-8", errors="replace")
        if c == "exn-agg-dispatch-fail":
            f = run_dir / "execution-issues.ndjson"
            return f.is_file() and any(
                x in f.read_text(encoding="utf-8", errors="replace")
                for x in (
                    "dispatch-with-waterfall exited non-zero",
                    "agent dispatch-waterfall exited non-zero",
                    "DISPATCH_OK=false",
                )
            )
        return False
    missing: list[str] = []
    for raw in required.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#") or raw.startswith("relative_path"):
            continue
        parts = raw.split("\t")
        rel = parts[0]
        c = parts[1] if len(parts) > 1 else "always"
        if c not in {"always", "step5", "step7a", "step8", "step9a1", "exn-agg-validate-fail", "exn-agg-dispatch-fail"}:
            return {"scan": "required-file-presence", "pr": pr, "result": "error", "detail": f"unsupported required-files condition (registry drift): {c}"}, True
        if rel.startswith("/") or ".." in rel:
            missing.append(f"{rel} (invalid path)")
            continue
        if cond(c) and not has(rel):
            missing.append(rel)
    return ({"scan": "required-file-presence", "pr": pr, "result": "pass", "count": 0} if not missing else {"scan": "required-file-presence", "pr": pr, "result": "fail", "missing": missing})


def _iter_ndjson(path: Path) -> tuple[list[dict[str, object]], bool]:
    rows: list[dict[str, object]] = []
    err = False
    if not path.is_file():
        return rows, err
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            err = True
    return rows, err


def _eligible_review_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    eligible: list[dict[str, object]] = []
    for row in rows:
        phase = str(row.get("phase") or "")
        outcome = str(row.get("outcome") or "")
        if phase == "retroactive-backfill" or not outcome:
            continue
        eligible.append(row)
    return eligible


def _self_review_tally_rows(run_dir: Path) -> list[dict[str, object]]:
    data = _read_json_file(run_dir / "code-review-tally.json")
    rows: list[dict[str, object]] = []
    for item in self_review_tally_items(data):
        rows.append(
            {
                "id": item.finding_id,
                "source": "committed-self-review-tally",
                "phase": "code-review",
                "outcome": item.outcome,
                "category": "",
                "severity": "(none)",
                "body_severity": "",
                "focus_area": "",
            }
        )
    return rows


def _category_string(row: dict[str, object]) -> str:
    cat = row.get("category")
    if cat is None:
        return ""
    if isinstance(cat, (dict, list)):
        return ""
    if isinstance(cat, bool):
        return "true" if cat else "false"
    return str(cat)


def _mangled_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for r in rows:
        cat = _category_string(r)
        if r.get("outcome") == "accepted" and str(r.get("phase") or "") == "plan-review" and cat and cat not in _CANONICAL:
            out.append(r)
    return out


def _codex_generalist_timing_elapsed(run_dir: Path) -> int:
    report = _read_json_file(run_dir / "timing-report.json")
    if not isinstance(report, dict):
        return 0
    def seconds_value(row: dict[str, object]) -> int | None:
        seconds = row.get("max_seconds", row.get("average_seconds", row.get("duration_seconds", row.get("duration_s", row.get("elapsed_seconds")))))
        try:
            return int(float(seconds))
        except (TypeError, ValueError):
            return None
    rows = report.get("vendor_task_averages")
    preferred: list[int] = []
    fallback: list[int] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or row.get("vendor") != "codex":
                continue
            task = str(row.get("task_kind") or "")
            elapsed = seconds_value(row)
            if elapsed is None:
                continue
            if task in {"codex-review-generic", "codex-phase1-generic"}:
                preferred.append(elapsed)
            elif task == "codex-review":
                fallback.append(elapsed)
    for key in ("steps", "per_step"):
        step_rows = report.get(key)
        if not isinstance(step_rows, list):
            continue
        for row in step_rows:
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get(k) or "").lower() for k in ("vendor", "task_kind", "task", "name", "step", "label"))
            elapsed = seconds_value(row)
            if elapsed is None:
                continue
            if "codex" in text and ("generalist" in text or "generic" in text):
                preferred.append(elapsed)
            elif "step 5" in text and "code review" in text:
                fallback.append(elapsed)
    return max(preferred or fallback or [0])


def scan_run_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs scan-run")
    p.add_argument("--skill", required=True)
    p.add_argument("--run-dir")
    p.add_argument("--pr", required=True)
    p.add_argument("--scans-tsv", required=True)
    p.add_argument("--required-files-tsv", default="")
    p.add_argument("--current-version", default="")
    args = p.parse_args(argv)
    if not _validate_skill(skill=args.skill, prog="audit-runs scan-run"):
        return 1
    if not re.fullmatch(r"[0-9]+", args.pr or ""):
        _json_line({"scan": "audit-scan-run-args", "pr": None, "result": "error", "detail": f"--pr must be a non-empty decimal integer: {args.pr}"})
        return 1
    pr = int(args.pr)
    if not args.run_dir:
        _json_line({"scan": "run-dir-missing", "pr": pr, "incomplete": True, "result": "error", "detail": "run-dir not found: "})
        return 1
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        _json_line({"scan": "run-dir-missing", "pr": pr, "incomplete": True, "result": "error", "detail": f"run-dir not found: {args.run_dir}"})
        return 1
    canon = run_dir.resolve()
    invalid = _run_dir_invalid(canon=canon, skill=args.skill)
    if invalid:
        _json_line({"scan": "run-dir-invalid", "pr": pr, "incomplete": True, "result": "error", "detail": invalid})
        return 1
    scans = Path(args.scans_tsv)
    if not scans.is_file():
        _json_line({"scan": "scans-registry", "pr": pr, "result": "error", "detail": f"scans-tsv not found: {args.scans_tsv}"})
        return 1
    required = Path(args.required_files_tsv) if args.required_files_tsv else None
    rows, jsonl_err = _iter_ndjson(run_dir / "review-findings-full.jsonl")
    if args.skill == "implement":
        eligible_rows = _eligible_review_rows(rows)
        if not jsonl_err and not eligible_rows:
            rows = _self_review_tally_rows(run_dir)
        else:
            rows = eligible_rows
    has_review_rows = bool(rows)
    mangled_cache: list[dict[str, object]] | None = None
    signals_any, signals = _round_meta_signals(run_dir)
    exit_code = 0
    scan_names = [line.split("\t", 1)[0] for line in scans.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#") and not line.startswith("name")]
    for name in scan_names:
        obj: dict[str, object]
        if name == "required-file-presence":
            res = _scan_required(run_dir=run_dir, pr=pr, required=required)
            if isinstance(res, tuple):
                obj, fatal = res
                if fatal: exit_code = 1
            else:
                obj = res
        elif name == "exon-misclassification":
            count = sum(len(re.findall(r"\| FINDING_.* \| 0 \| 0 \| [1-9][0-9]* \|.*\| rejected \|", f.read_text(encoding="utf-8", errors="replace"))) for f in run_dir.glob("round-*/voting-tally.md"))
            obj = {"scan": name, "pr": pr, "result": "pass" if count == 0 else "fail", "count": count}
        elif name == "oos-category-mangle":
            if not (run_dir / "review-findings-full.jsonl").is_file() and not has_review_rows: obj = {"scan": name, "pr": pr, "result": "skip", "detail": "review-findings-full.jsonl not found"}
            elif jsonl_err: obj = {"scan": name, "pr": pr, "result": "error", "detail": "jq failed (oos-category-mangle): parse error"}
            else:
                mangled_cache = _mangled_rows(rows); c=len(mangled_cache); obj={"scan":name,"pr":pr,"result":"pass" if c==0 else "fail","count":c};
                if c: obj["detail"] = f"{c} plan-review accepted rows with prose category (not canonical)"
        elif name == "rej-category-blank":
            if not (run_dir / "review-findings-full.jsonl").is_file() and not has_review_rows: obj={"scan":name,"pr":pr,"result":"skip","detail":"review-findings-full.jsonl not found"}
            else:
                c=sum(1 for r in rows if str(r.get("id") or "").startswith("REJ_") and not r.get("category") and re.search(r"###[ \t]+FINDING_[0-9A-Za-z_]+:[ \t]*(code-quality|risk-integration|correctness|architecture|security)(:|\n|$)", str(r.get("prose_body") or "")))
                obj={"scan":name,"pr":pr,"result":"pass" if c==0 else "fail","count":c};
                if c: obj["rej_blank_with_cat_in_prose"] = c
        elif name == "ns-retry-sidecars":
            reasons: list[str] = []
            if signals_any:
                signaled: set[str] = set()
                for s in signals:
                    rr=str(s.get("ns_retry_reason") or "")
                    if rr:
                        reasons.append(rr if rr in {"NO_ISSUES_FOUND_TOO_THIN","OUTPUT_EMPTY","JSON_PARSE_FAIL","UNKNOWN"} else "UNKNOWN")
                        if s.get("output_basename"): signaled.add(str(s.get("output_basename")))
                for side in run_dir.glob("round-*/*-ns-retry*.txt"):
                    base=side.name.removesuffix("-ns-retry.txt")+".txt"
                    if base not in signaled: reasons.append("UNKNOWN")
            else:
                reasons=["UNKNOWN" for _ in run_dir.glob("round-*/*-ns-retry*.txt")]
                if not reasons: obj={"scan":name,"pr":pr,"result":"skip","detail":"reviewer_signals signal unavailable"}; _json_line(obj); continue
                c=Counter(reasons); obj={"scan":name,"pr":pr,"result":"fail","count":len(reasons),"reasons":dict(sorted(c.items())),"detail":"legacy sidecar fallback (reviewer_signals unavailable)"}; _json_line(obj); continue
            c=Counter(reasons); obj={"scan":name,"pr":pr,"result":"pass" if not reasons else "fail","count":len(reasons),"reasons":dict(sorted(c.items()))}
        elif name == "cursor-ci-stall-causes":
            files=list(run_dir.glob("round-*/cursor-ci-stall-*.json")); chans: list[str] = []; parsed=0
            for f in files:
                data=_read_json_file(f)
                if isinstance(data, dict): parsed+=1; chans.append(str(data.get("channel") or "UNKNOWN"))
                else: chans.append("UNKNOWN")
            obj={"scan":name,"pr":pr,"result":"pass" if not files else "informational","count":len(files),"parsed_files":parsed,"channels":dict(sorted(Counter(chans).items()))}
        elif name in _NAMED_RUN_SCAN_HANDLERS:
            obj = _NAMED_RUN_SCAN_HANDLERS[name](name=name, pr=pr, run_dir=run_dir)
        elif name == "codex-generalist-waste":
            meta=_read_json_file(run_dir/"round-1/round-meta.json")
            sigs=meta.get("reviewer_signals") if isinstance(meta,dict) else None
            if not isinstance(sigs,list): obj={"scan":name,"pr":pr,"result":"skip","detail":"reviewer_signals signal unavailable"}
            else:
                rk=next((str(s.get("result_kind") or "") for s in sigs if isinstance(s,dict) and s.get("output_basename")=="codex-generalist-output.txt"),"")
                if not rk: obj={"scan":name,"pr":pr,"result":"skip","detail":"reviewer_signals signal unavailable"}
                else:
                    elapsed=0
                    if isinstance(meta, dict):
                        logs=meta.get("wrapper_logs")
                        codex_log=str(logs.get("codex") or "") if isinstance(logs, dict) else ""
                        vals=[int(x) for x in re.findall(r"([0-9]+)s elapsed", codex_log)]
                        elapsed=max(vals) if vals else 0
                    if not elapsed:
                        elapsed=_codex_generalist_timing_elapsed(run_dir)
                    no_issues = rk == "NO_ISSUES_FOUND"
                    obj={"scan":name,"pr":pr,"result":"fail" if no_issues and elapsed > 120 else "pass","result_kind":rk,"elapsed_seconds":elapsed}
                    if obj["result"] == "fail": obj["detail"]="codex-generalist returned NO_ISSUES_FOUND after more than 120 seconds"
        elif name == "execution-issues-categories":
            ex,err=_iter_ndjson(run_dir/"execution-issues.ndjson")
            if not (run_dir/"execution-issues.ndjson").is_file(): obj={"scan":name,"pr":pr,"result":"skip","detail":"execution-issues.ndjson not found"}
            else:
                non=sum(1 for r in ex if isinstance(r.get("category"),str) and r.get("category") != "Warnings"); warn=sum(1 for r in ex if r.get("category")=="Warnings"); obj={"scan":name,"pr":pr,"result":"pass" if non==0 else "fail","non_warnings":non,"warnings":warn}
        elif name == "cache-freshness":
            mf=_read_json_file(run_dir/"manifest.json")
            if not isinstance(mf,dict): obj={"scan":name,"pr":pr,"result":"skip","detail":"manifest.json not found"}
            else:
                rv=str(mf.get("larch_version") or "")
                if not args.current_version or args.current_version=="unknown": obj={"scan":name,"pr":pr,"result":"skip","detail":"current-version unset","run_version":rv}
                elif not rv: obj={"scan":name,"pr":pr,"result":"fail","detail":"manifest larch_version empty","current_version":args.current_version}
                elif rv != args.current_version and tuple(map(int,re.findall(r"\d+",rv)[:3] or [0])) < tuple(map(int,re.findall(r"\d+",args.current_version)[:3] or [0])): obj={"scan":name,"pr":pr,"result":"informational","run_version":rv,"current_version":args.current_version,"detail":"run plugin version behind current"}
                else: obj={"scan":name,"pr":pr,"result":"pass","run_version":rv,"current_version":args.current_version}
        elif name == "changelog-rebase-conflicts":
            ex,_=_iter_ndjson(run_dir/"execution-issues.ndjson")
            if not (run_dir/"execution-issues.ndjson").is_file(): obj={"scan":name,"pr":pr,"result":"skip","detail":"execution-issues.ndjson not found"}
            else:
                c=sum(1 for r in ex if "changelog" in str(r.get("body") or "").lower() and ("rebase" in str(r.get("body") or "").lower() or "conflict" in str(r.get("body") or "").lower()))
                obj={"scan":name,"pr":pr,"result":"pass" if c==0 else "fail","count":c}
        elif name == "coder-tool":
            by: dict[str, str] = {}
            for rd in run_dir.glob("round-*"):
                tool=""; meta=_read_json_file(rd/"round-meta.json")
                if isinstance(meta,dict) and isinstance(meta.get("coder"),dict): tool=str(meta["coder"].get("CODER_TOOL") or "")
                env=rd/"coder.env"
                if not tool and env.is_file():
                    m=re.search(r"CODER_TOOL=([^\s]+)", env.read_text(encoding="utf-8",errors="replace")); tool=m.group(1) if m else ""
                if tool: by[rd.name]=tool
            obj={"scan":name,"pr":pr,"result":"pass","by_round":by}
        elif name == "trailing-content-no-issues-found":
            if not signals_any: obj={"scan":name,"pr":pr,"result":"skip","detail":"reviewer_signals signal unavailable"}
            else:
                c=sum(1 for s in signals if s.get("first_pass_trailing_content") is True); obj={"scan":name,"pr":pr,"result":"pass" if c==0 else "fail","count":c}
        elif name == "oos-silent-drop":
            counts=oos_disposition.analyze_run_dir(run_dir)
            if counts.non_security_oos_blocks == 0: obj={"scan":name,"pr":pr,"result":"skip","detail":"no non-security OOS blocks in canonical oos-accepted-*.md"}
            elif counts.ndjson_parse_error: obj={"scan":name,"pr":pr,"result":"error","detail":"jq parse failure while reading oos-issues.ndjson for rejected-OOS markers"}
            else:
                ok=counts.issue_urls>0 or counts.inline_triage_hits>=counts.non_security_oos_blocks or counts.rejected_oos_markers>=counts.non_security_oos_blocks
                obj={"scan":name,"pr":pr,"result":"pass" if ok else "fail","non_security_oos_blocks":counts.non_security_oos_blocks,"issue_urls":counts.issue_urls,"inline_triage_hits":counts.inline_triage_hits,"rejected_oos_markers":counts.rejected_oos_markers}
                if not ok: obj["detail"]="accepted OOS blocks without filed URLs, sufficient Inline-triage breadcrumbs, or explicit rejected-OOS markers in oos-issues.ndjson"
        else:
            _json_line({"scan": name, "pr": pr, "result": "error", "detail": "unknown scan name in scans registry (registry drift vs audit-runs scan-run)"})
            return 1
        _json_line(obj)
    # category-stats
    if (run_dir/"review-findings-full.jsonl").is_file() or has_review_rows:
        if jsonl_err:
            _json_line({"scan":"category-stats","pr":pr,"partial_data":True,"partial_reason":"malformed_review_findings_jsonl","detail":"jq failed (category-stats): parse error","canonical":0,"blank":0,"mangled":0,"oos_blank":0,"rej_blank":0})
        else:
            mangled=mangled_cache if mangled_cache is not None else _mangled_rows(rows)
            _json_line({"scan":"category-stats","pr":pr,"partial_data":False,"canonical":sum(1 for r in rows if _category_string(r) in _CANONICAL),"blank":sum(1 for r in rows if not _category_string(r)),"mangled":len(mangled),"oos_blank":sum(1 for r in rows if str(r.get("id") or "").startswith("OOS_") and not _category_string(r)),"rej_blank":sum(1 for r in rows if str(r.get("id") or "").startswith("REJ_") and not _category_string(r))})
    else:
        if args.skill=="design": _json_line({"scan":"category-stats","pr":pr,"partial_data":False,"skip_reason":"design_run_has_no_review_findings_jsonl","detail":"design runs intentionally omit review-findings-full.jsonl","canonical":0,"blank":0,"mangled":0,"oos_blank":0,"rej_blank":0})
        else: _json_line({"scan":"category-stats","pr":pr,"partial_data":True,"partial_reason":"missing_review_findings_jsonl","detail":"review-findings-full.jsonl not found","canonical":0,"blank":0,"mangled":0,"oos_blank":0,"rej_blank":0})
    mf=_read_json_file(run_dir/"manifest.json")
    ended=prnull=gap=False
    if isinstance(mf,dict):
        is_v2=isinstance(mf.get("schema_version"),int) and int(mf.get("schema_version"))>=2
        ended=("ended_at" in mf and (mf.get("ended_at") in (None,""))) if is_v2 else not str(mf.get("ended_at") or "")
        prnull=("pr_number" in mf and mf.get("pr_number") is None) if is_v2 else (mf.get("pr_number") is None or str(mf.get("pr_number") or "")=="")
        gap=mf.get("pr_number") not in (None,"") and str(mf.get("pr_number")) != str(pr)
    _json_line({"scan":"cross-cutting","pr":pr,"ended_at_null":ended,"pr_number_null":prnull,"manifest_pr_number_mismatch_with_audited_pr":gap,"self_deploying_gap":gap})
    return exit_code


def _prior_value( *,text: str, key: str) -> int:
    m = re.search(rf"^\s*{re.escape(key)}:\s*([0-9]+)\s*$", text, re.M)
    return int(m.group(1)) if m else 0


def _top_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    if lines[0].strip() != "---":
        return ""
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:idx])
    return ""


def compute_counters_main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog="cli.py audit-runs compute-counters"); p.add_argument("--scan-results-dir", required=True); p.add_argument("--prior-frontmatter", default=""); args=p.parse_args(argv)
    d=Path(args.scan_results_dir)
    if not d.is_dir(): print(f"audit-compute-counters.sh: directory not found: {d}", file=sys.stderr); return 1
    prior_body=Path(args.prior_frontmatter).read_text(encoding="utf-8") if args.prior_frontmatter and Path(args.prior_frontmatter).is_file() else ""
    prior=_top_frontmatter(prior_body)
    p_exon=_prior_value(text=prior,key="exon_misclassifications"); p_mang=_prior_value(text=prior,key="oos_categories_mangled"); p_clean=_prior_value(text=prior,key="oos_categories_clean"); p_blank=_prior_value(text=prior,key="oos_categories_blank"); p_ns=max(_prior_value(text=prior,key="ns_retries_cursor_specialist"),_prior_value(text=prior,key="ns_retries_cursor_specialist_launches")); p_ch=_prior_value(text=prior,key="changelog_rebase_conflicts")
    def num_or_zero(value: object) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return 0
    de=dm=dc=db=dn=dskip=dch=0; partial=False; files=0
    for f in d.glob("scan-results-*.ndjson"):
        files+=1; rows,_=_iter_ndjson(f)
        for r in rows:
            if r.get("scan")=="exon-misclassification": de+=num_or_zero(r.get("count"))
            elif r.get("scan")=="oos-category-mangle": dm+=num_or_zero(r.get("count"))
            elif r.get("scan")=="category-stats":
                if r.get("partial_data") is True: partial=True
                if not (r.get("partial_data") is True and "review-findings-full.jsonl not found" in str(r.get("detail") or "")):
                    dc+=num_or_zero(r.get("canonical")); db+=num_or_zero(r.get("oos_blank"))
            elif r.get("scan")=="ns-retry-sidecars":
                if r.get("result")=="fail": dn+=num_or_zero(r.get("count"))
                elif r.get("result")=="skip": dskip+=1
            elif r.get("scan")=="changelog-rebase-conflicts": dch+=num_or_zero(r.get("count"))
    for k,v in [("SCAN_FILES_FOUND",files),("EXON_MISCLASSIFICATIONS",p_exon+de),("EXON_DELTA",de),("OOS_CATEGORIES_MANGLED",p_mang+dm),("OOS_MANGLED_DELTA",dm),("OOS_CATEGORIES_CLEAN",p_clean+dc),("OOS_CLEAN_DELTA",dc),("OOS_CATEGORIES_BLANK",p_blank+db),("OOS_BLANK_DELTA",db),("NS_RETRIES_CURSOR_SPECIALIST",p_ns+dn),("NS_RETRIES_DELTA",dn),("NS_RETRIES_SKIPPED_RUNS",dskip),("CHANGELOG_REBASE_CONFLICTS",p_ch+dch),("CHANGELOG_DELTA",dch)]: print(f"{k}={v}")
    print(f"CATEGORY_STATS_PARTIAL={str(partial).lower()}")
    return 0


def close_priors_main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog="cli.py audit-runs close-priors"); p.add_argument("--skill",required=True); p.add_argument("--new-issue-number",required=True); p.add_argument("--repo",default="character-ai/larch"); args=p.parse_args(argv)
    if not _validate_skill(skill=args.skill,prog="audit-close-priors.sh"): return 1
    res=proc.run(["gh","issue","list","--state","open","--limit","100000","--label","audit-report","--repo",args.repo,"--json","number,title"])
    if res.returncode != 0:
        print("ISSUE_LIST_FAILED=true\nREASON=gh issue list failed")
        return 1
    try:
        arr=json.loads(res.stdout or "null")
    except json.JSONDecodeError:
        print("ISSUE_LIST_FAILED=true\nREASON=gh issue list returned invalid JSON")
        return 1
    if not isinstance(arr,list): print("ISSUE_LIST_FAILED=true\nREASON=gh issue list returned invalid JSON"); return 1
    body: Path | None = None
    try:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        try:
            handle.write(f"Superseded by #{args.new_issue_number}")
            body = Path(handle.name)
        finally:
            handle.close()
    except OSError:
        print("BODY_FILE_FAILED=true\nREASON=mktemp failed")
        return 1
    try:
        for issue in arr:
            if not isinstance(issue,dict): continue
            num=str(issue.get("number") or "")
            if num==args.new_issue_number or not match_audit_report_title(skill=args.skill,title=str(issue.get("title") or "")): continue
            if proc.run(["gh","issue","comment",num,"--repo",args.repo,"--body-file",str(body)]).returncode!=0: print(f"CLOSE_FAILED={num}\tREASON=gh issue comment failed"); continue
            if proc.run(["gh","issue","close",num,"--repo",args.repo]).returncode!=0: print(f"CLOSE_FAILED={num}\tREASON=gh issue close failed"); continue
            print(f"CLOSED_NUMBER={num}")
    finally:
        if body is not None:
            body.unlink(missing_ok=True)
    return 0
