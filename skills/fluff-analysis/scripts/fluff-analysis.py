#!/usr/bin/env python3
"""fluff-analysis.py — characterize review "fluff" from committed larch run logs.

Reads committed design + implement run logs (and, optionally, in-progress design
session temp dirs), normalizes every review finding into one record stream, and
prints a markdown report: acceptance baselines, low-acceptance semantic groups,
testing breakdown, severity/quality/uncertain correlations, reviewer-lane splits,
an "accepted-but-low-value" proxy, an optional pre/post-cutoff comparison, and
data-driven recommendations for tightening reviewer/judge instructions.

Stdlib only. Run directly:
  python3 fluff-analysis.py [--log-root DIR] [--include-in-progress] ...
See fluff-analysis.md for the full contract.
"""
import argparse
import collections
import collections.abc
import csv
import concurrent.futures
import datetime
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
python_dir = repo_root / "python"
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))

from larch.core import config  # noqa: E402
from larch.core.architectural_guidelines import CLEAN_PRESENTATION_NOTE, DESIGN_ASSESSMENT, GUIDELINE_SHIP_OUTCOME_SIDECAR  # noqa: E402
from larch.issue.audit_runs import implement_step8_reachable  # noqa: E402
from larch.issue.rejected_analysis import (  # noqa: E402
    _lookup_jsonl_record,
    _records_by_round_and_token,
)
from larch.implement.ship_guidelines import GUIDELINE_SHIP_REASON_TOKENS  # noqa: E402
from larch.review.self_review_tally import self_review_tally_items  # noqa: E402

# --------------------------------------------------------------------------
# semantic-group classifier — a finding may carry many tags (multi-label)
# --------------------------------------------------------------------------
TAG_PATTERNS = {
    # Out-of-Scope ("fluff") signals named by skills/shared/review-acceptance-rubric.md
    "rub:cleaner/clarity":      r"\bcleaner\b|more readable|for clarity|readability|easier to read",
    "rub:more-robust":          r"more robust|be more robust|increase robustness",
    "rub:idiomatic/bestprac":   r"idiomatic|best practice|conventional|more consistent|consistency|uniform",
    "rub:flexible/futureproof": r"more flexible|future[- ]proof|extensib|generaliz",
    "rub:while-were-here":      r"while (we|you)('| a)re here|since (we|you)('| a)re|opportunistic|as a bonus|also worth",
    "rub:defensive/incase":     r"defensive|in case|just in case|guard against|cannot (occur|happen)|can'?t (occur|happen)|should never|belt and suspenders",
    "rub:configurability":      r"configurab|make .* configurable|add (a |an )?(flag|option|env var|knob)|parameteriz",
    "rub:rename":               r"\brename\b|renaming|better name|clearer name",
    "rub:nice-to-have":         r"nice to have|would be nice|consider (adding|using|whether)|might want to|could also|optional(ly)?",
    # broad themes
    "theme:testing":         r"\btest\b|\btests\b|harness|assertion|\bassert\b|coverage|fixture|\bTDD\b|red[- ]green|test case",
    "theme:docs/comments":   r"\bdoc\b|\bdocs\b|documentation|readme|changelog|\bcomment\b|docstring|prose|wording|\btypo\b|\.md\b|spelling",
    "theme:naming":          r"\brename\b|naming|variable name|function name|identifier name|misnomer",
    "theme:style/lint":      r"\bstyle\b|formatting|whitespace|\blint\b|casing|indent|trailing|quote style",
    "theme:refactor/dry":    r"refactor|deduplicat|\bDRY\b|extract (a )?(helper|function|method)|consolidat|simplif|collaps|factor out|reduce duplication",
    "theme:perf":            r"performance|efficien|optimiz|\bslow\b|latency|\bO\(|caching|redundant (work|call|read)",
    "theme:error-handling":  r"error handling|error message|\bexception\b|failure mode|\bretry\b|fallback|graceful|swallow",
    "theme:robustness":      r"robust|race condition|concurren|idempoten|atomic|resource leak|cleanup|partial failure|signal handling",
    "theme:edge-case":       r"edge case|boundary|corner case|off[- ]by[- ]one|empty (input|list|string)|\bnull\b|\bnil\b|unset|zero[- ]length",
    "theme:validation":      r"validate|validation|sanitiz|input check|bounds check|malformed|untrusted|guardrail",
    "theme:security":        r"secret|injection|\bssrf\b|traversal|redact|\bleak\b|\bauth\b|permission|sandbox|\bvuln|crypto|credential|token leak|password",
    "theme:completeness":    r"missing|omit|incomplete|not (updated|covered|handled|wired|listed)|left out|forgot|fails to (update|cover|include)|absent from",
    "theme:correctness":     r"incorrect|\bwrong\b|\bbug\b|logic error|inverted|mismatch|broken|does not (match|work)|doesn'?t (match|work)|stale",
    "theme:backward-compat": r"backward|back[- ]compat|breaking change|migration|deprecat|existing caller|wire (format|surface)",
    "theme:portability":     r"portab|bash 3\.2|macos|posix|gnu vs bsd|platform[- ]specific|cross[- ]shell|awk implementation",
}
TAGS = {k: re.compile(v, re.IGNORECASE) for k, v in TAG_PATTERNS.items()}

SEV_BODY = ["blocker", "critical", "major", "important", "minor", "latent", "nit", "trivial"]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def pct(num, den):
    return (100.0 * num / den) if den else 0.0


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def manifest_started(run_dir):
    try:
        data = json.loads(read_text(os.path.join(run_dir, "manifest.json")) or "{}")
        return data.get("started_at")
    except (ValueError, TypeError):
        return None


def manifest_larch_version(run_dir):
    try:
        data = json.loads(read_text(os.path.join(run_dir, "manifest.json")) or "{}")
    except (ValueError, TypeError):
        return ""
    value = data.get("larch_version", "")
    return value if isinstance(value, str) else ""


def tools_from(label):
    low = (label or "").lower()
    out = []
    if "codex" in low:
        out.append("Codex")
    if "cursor" in low:
        out.append("Cursor")
    if "claude" in low or "main" in low:
        out.append("Claude")
    return out


def is_dynamic(label):
    return "dyn-" in (label or "").lower()


def normalize_severity(raw):
    value = (raw or "").strip().lower()
    aliases = {
        "blocker": "important",
        "critical": "important",
        "major": "important",
        "important": "important",
        "minor": "latent",
        "latent": "latent",
        "nit": "nit",
        "trivial": "nit",
        "none": "(none)",
        "(none)": "(none)",
    }
    return aliases.get(value, "(none)")


def normalize_design_severity(raw):
    value = (raw or "").strip().lower()
    aliases = {
        "major": "important",
        "important": "important",
        "minor": "latent",
        "latent": "latent",
        "nit": "nit",
        "none": "(none)",
        "(none)": "(none)",
    }
    return aliases.get(value, "(none)")


def find_severity(text):
    match = re.search(r"\*\*Severity\*\*:\s*([a-zA-Z-]+)", text or "")
    if match:
        return normalize_severity(match.group(1))
    match = re.search(r"\[(blocker|critical|major|important|minor|latent|nit|trivial)\]", (text or "").lower())
    return normalize_severity(match.group(1)) if match else "(none)"


def find_focus(text):
    match = re.search(r"\*\*Focus area\*\*:\s*([a-zA-Z-]+)", text or "")
    return match.group(1).lower() if match else ""


def tags_of(text):
    return [name for name, rx in TAGS.items() if rx.search(text)]


def modal(values):
    values = [v for v in values if v]
    return collections.Counter(values).most_common(1)[0][0] if values else ""


def parse_cutoff(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        sys.stderr.write("WARN: could not parse --cutoff %r; pre/post section disabled\n" % raw)
        return None


def period_of(cutoff, started_at=None, mtime=None):
    if cutoff is None:
        return "all"
    when = None
    if started_at:
        try:
            when = datetime.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            when = None
    elif mtime:
        when = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
    if when is None:
        return "unknown"
    if cutoff.tzinfo is not None and when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return "post" if when >= cutoff else "pre"


def parse_larch_version(raw):
    raw = (raw or "").strip()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def parse_since_version(raw):
    if not raw:
        return None
    parsed = parse_larch_version(raw)
    if parsed is None:
        raise argparse.ArgumentTypeError("expected X.Y.Z")
    return parsed


def period_of_version(since_version, larch_ver):
    parsed = parse_larch_version(larch_ver)
    if parsed is None:
        return "unknown"
    return "post" if parsed >= since_version else "pre"


# --------------------------------------------------------------------------
# parsers (defensive against format drift across the log corpus)
# --------------------------------------------------------------------------
HEAD_RE = re.compile(r"(?m)^#{2,4}\s+((?:FINDING|OOS|REJ)[_A-Z0-9]*\d)\b[:\s]?(.*)$")


def parse_md_blocks(text):
    """Parse `### FINDING_N:` style blocks into {id: {title, fields, raw}}."""
    out = {}
    matches = list(HEAD_RE.finditer(text or ""))
    for i, match in enumerate(matches):
        fid = match.group(1)
        title = (match.group(2) or "").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        fields = {}
        for fmatch in re.finditer(r"(?m)^\s*-\s+\*\*(.+?)\*\*:\s*(.*)$", body):
            key = fmatch.group(1).strip().lower()
            if key not in fields:
                fields[key] = fmatch.group(2).strip()
        rec = {"title": title, "fields": fields, "raw": title + "\n" + body}
        if fid not in out or (len(rec["fields"]) > len(out[fid]["fields"])):
            out[fid] = rec
    return out


def parse_voting_tally(text):
    out = {}
    for line in (text or "").splitlines():
        match = re.match(r"\s*\|\s*((?:FINDING|OOS|REJ)[_A-Z0-9]*\d)\s*\|(.+)\|\s*$", line)
        if not match:
            continue
        cells = [c.strip() for c in match.group(2).split("|")]
        out[match.group(1)] = {"result": cells[-1].lower() if cells else ""}
    return out


def _cells(line):
    return line.split("\t")


def parse_design_tsv(text):
    """Parse design findings-classification.tsv header supersets."""
    out = {}
    lines = (text or "").splitlines()
    if not lines:
        return out
    for row in csv.DictReader(lines, delimiter="\t"):
        fid = (row.get("finding_id") or "").strip()
        if not re.match(r"^(FINDING|OOS|REJ)", fid):
            continue
        out[fid] = {
            "result": (row.get("voting_result") or "").strip().lower(),
            "reviewers": (row.get("finding_reviewers") or "").strip(),
            "severities": [normalize_design_severity(row.get(f"v{idx}_severity") or "") for idx in (1, 2, 3) if row.get(f"v{idx}_severity")],
            "qualities": [(row.get(f"v{idx}_quality") or "").strip().lower() for idx in (1, 2, 3) if row.get(f"v{idx}_quality")],
            "correctness": [(row.get(f"v{idx}_correctness") or "").strip().lower() for idx in (1, 2, 3) if row.get(f"v{idx}_correctness")],
            "uncertain": [(row.get(f"v{idx}_uncertain") or "").strip().lower() for idx in (1, 2, 3) if row.get(f"v{idx}_uncertain")],
            "body_severity": (row.get("body_severity") or "").strip(),
            "scope": (row.get("scope") or "").strip(),
        }
    return out


def parse_impl_tsv(text):
    """Parse implement/code-review TSV ratings from compact and named schemas."""
    out = {}
    lines = (text or "").splitlines()
    if not lines:
        return out
    header = lines[0].split("\t")
    has_named_ratings = all(f"v{idx}_severity" in header for idx in (1, 2, 3))
    if has_named_ratings:
        for row in csv.DictReader(lines, delimiter="\t"):
            fid = (row.get("finding_id") or "").strip()
            if not re.match(r"^(FINDING|OOS|REJ)", fid):
                continue
            out[fid] = {
                "voting_result": (row.get("voting_result") or "").strip().lower(),
                "body_severity": (row.get("body_severity") or "").strip(),
                "scope": (row.get("scope") or "").strip(),
                "severities": [(row.get(f"v{idx}_severity") or "").lower() for idx in (1, 2, 3) if row.get(f"v{idx}_severity")],
                "qualities": [(row.get(f"v{idx}_quality") or "").lower() for idx in (1, 2, 3) if row.get(f"v{idx}_quality")],
                "correctness": [(row.get(f"v{idx}_correctness") or "").lower() for idx in (1, 2, 3) if row.get(f"v{idx}_correctness")],
                "uncertain": [(row.get(f"v{idx}_uncertain") or "").lower() for idx in (1, 2, 3) if row.get(f"v{idx}_uncertain")],
            }
        return out
    for line in lines[1:]:
        cells = _cells(line)
        if len(cells) != 18 or not re.match(r"^(FINDING|OOS|REJ)", cells[0]):
            continue

        def get(idx, row=cells):
            return row[idx].strip() if idx < len(row) else ""

        out[cells[0]] = {
            "voting_result": get(2).lower(),
            "body_severity": "",
            "scope": "",
            "severities": [s.lower() for s in (get(5), get(10), get(15)) if s],
            "qualities": [q.lower() for q in (get(6), get(11), get(16)) if q],
            "correctness": [c.lower() for c in (get(4), get(9), get(14)) if c],
            "uncertain": [u.lower() for u in (get(7), get(12), get(17)) if u],
        }
    return out



def _scope_is_oos(scope, finding_id):
    value = (scope or "").strip().lower()
    return value in {"oos", "out_of_scope", "out-of-scope"} or str(finding_id or "").upper().startswith("OOS_")


def _reviewer_claimed_tier(body_severity, *, corpus):
    raw = (body_severity or "").strip().lower()
    if not raw:
        return "(none)"
    if raw in {"blocker", "critical", "blocking"}:
        return "important"
    if corpus == "design":
        return normalize_design_severity(raw)
    return normalize_severity(raw)


def _round_from_path(path):
    match = re.search(r"round-(\d+)", str(path).replace(os.sep, "/"))
    return match.group(1) if match else ""


def _run_has_multiple_rounds(run_dir):
    return sum(1 for path in glob.glob(os.path.join(run_dir, "round-*")) if os.path.isdir(path)) > 1


def _run_has_round_local_jsonl(run_dir):
    return bool(glob.glob(os.path.join(run_dir, "round-*", "review-findings-full.jsonl")))


def _load_jsonl(path):
    records = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, dict):
            records.append(data)
    return records


def _impl_jsonl_records_by_round(run_dir):
    by_round = collections.defaultdict(list)
    round_local = sorted(glob.glob(os.path.join(run_dir, "round-*", "review-findings-full.jsonl")))
    if round_local:
        for path in round_local:
            round_num = _round_from_path(path)
            for record in _load_jsonl(path):
                if not record.get("round_num"):
                    record["round_num"] = round_num
                by_round[str(record.get("round_num") or round_num)].append(record)
        return dict(by_round)
    for record in _load_jsonl(os.path.join(run_dir, "review-findings-full.jsonl")):
        by_round[str(record.get("round_num") or "")].append(record)
    return dict(by_round)


def _impl_fn_rows_from_run(run_dir, jsonl_records, *, cutoff=None, since_version=None):
    run_id = os.path.basename(run_dir)
    started = manifest_started(run_dir)
    larch_version = manifest_larch_version(run_dir)
    period = period_of_version(since_version, larch_version) if since_version is not None else period_of(cutoff, started_at=started)
    all_records = []
    for records in jsonl_records.values():
        all_records.extend(records)
    by_token = _records_by_round_and_token(all_records)
    multi_round = _run_has_multiple_rounds(run_dir)
    allow_unscoped = not multi_round and not _run_has_round_local_jsonl(run_dir)
    rows = []
    for tsv in sorted(glob.glob(os.path.join(run_dir, "round-*", "findings-classification.tsv"))):
        round_num = _round_from_path(tsv)
        for fid, trow in parse_impl_tsv(read_text(tsv)).items():
            verdict = (trow.get("voting_result") or "").strip().lower()
            scope = trow.get("scope", "")
            if not re.match(r"^(FINDING|REJ)", fid) or _scope_is_oos(scope, fid):
                continue
            if verdict not in {"accepted", "neutral", "rejected"}:
                continue
            matched = _lookup_jsonl_record(by_token=by_token, round_num=round_num, row_id=fid, allow_unscoped=allow_unscoped)
            if matched == "ambiguous":
                continue
            json_body_severity = ""
            if isinstance(matched, collections.abc.Mapping):
                json_body_severity = str(matched.get("body_severity") or "").strip()
            body_severity = json_body_severity or (trow.get("body_severity") or "")
            rows.append({
                "skill": "implement",
                "source": "classification-tsv",
                "run_id": run_id,
                "round": round_num,
                "round_num": round_num,
                "finding_id": fid,
                "voting_result": verdict,
                "outcome": verdict,
                "scope": scope,
                "body_severity": body_severity,
                "period": period,
                "larch_version": larch_version,
            })
    return rows


def build_impl_fn_rows(log_root, *, cutoff=None, since_version=None):
    rows = []
    impl_root = os.path.join(log_root, "implement")
    for run_dir in sorted(glob.glob(os.path.join(impl_root, "*"))):
        if not os.path.isdir(run_dir):
            continue
        rows.extend(_impl_fn_rows_from_run(run_dir, _impl_jsonl_records_by_round(run_dir), cutoff=cutoff, since_version=since_version))
    return rows

# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------
def extract(log_root, sessions_dir, include_in_progress, cutoff, inprogress_min, since_version=None, post_only_tags=False):
    records = []
    records += _extract_implement(os.path.join(log_root, "implement"), cutoff, since_version)
    records += _extract_design(os.path.join(log_root, "design"), cutoff, since_version)
    if include_in_progress and sessions_dir and os.path.isdir(sessions_dir):
        records += _extract_in_progress(sessions_dir, cutoff, inprogress_min)
    for rec in records:
        if post_only_tags and rec.get("period") != "post":
            rec["_tags"] = []
        else:
            rec["_tags"] = tags_of(rec.get("text", "") or "")
    return records


def _extract_one_implement_run(args):
    # Worker for the threaded scan; cutoff / since_version passed explicitly so
    # there is no reliance on mutated module globals.
    run_dir, cutoff, since_version = args
    records = []
    jf = os.path.join(run_dir, "review-findings-full.jsonl")
    run_id = os.path.basename(run_dir)
    started = manifest_started(run_dir)
    larch_version = manifest_larch_version(run_dir)
    period = period_of_version(since_version, larch_version) if since_version is not None else period_of(cutoff, started_at=started)
    fallback_records = _self_review_tally_records(run_dir, run_id, larch_version, period)
    round_tsv = {}
    for tsv in glob.glob(os.path.join(run_dir, "round-*", "findings-classification.tsv")):
        match = re.search(r"round-(\d+)", tsv)
        round_tsv[match.group(1) if match else ""] = parse_impl_tsv(read_text(tsv))
    malformed_jsonl = False
    if not os.path.exists(jf):
        return fallback_records
    for line in read_text(jf).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except ValueError:
            malformed_jsonl = True
            continue
        phase = data.get("phase", "")
        outcome = data.get("outcome", "") or ""
        if phase == "retroactive-backfill" or not outcome:
            continue
        fid = data.get("id", "")
        rnum = str(data.get("round_num", "") or "")
        slots = data.get("reviewer_slots")
        if not isinstance(slots, list):
            rev = data.get("reviewer")
            slots = [rev] if isinstance(rev, str) else []
        rev_str = ", ".join(s for s in slots if isinstance(s, str))
        cat = data.get("category", "") or ""
        prose = data.get("prose_body", "") or ""
        body_severity = data.get("body_severity", "") or ""
        focus_area = data.get("focus_area", "") or find_focus(prose)
        severity = normalize_severity(body_severity) if body_severity else find_severity(prose)
        title = cat
        if not title:
            hmatch = re.search(r"(?m)^#{2,4}\s+(?:(?:FINDING|OOS|REJ)[_A-Z0-9]*\d[:\s]+)?(.*)$", prose)
            title = (hmatch.group(1).strip() if hmatch else "")[:200]
        ratings = round_tsv.get(rnum, {}).get(fid, {})
        records.append({
            "skill": "implement", "source": "committed", "run_id": run_id,
            "round": rnum, "phase": phase or "code-review", "finding_id": fid,
            "larch_version": larch_version,
            "outcome": outcome, "is_oos_id": fid.startswith("OOS"),
            "title": title[:300],
            "focus_area": focus_area,
            "body_severity": body_severity,
            "scope": ratings.get("scope", ""),
            "severity": severity,
            "reviewers": rev_str, "tools": tools_from(rev_str), "is_dynamic": is_dynamic(rev_str),
            "v_severities": ratings.get("severities", []),
            "v_qualities": ratings.get("qualities", []),
            "v_correctness": ratings.get("correctness", []),
            "v_uncertain": ratings.get("uncertain", []),
            "period": period,
            "text": (title + "\n" + prose)[:2000],
        })
    if records or malformed_jsonl:
        return records
    return fallback_records


def _self_review_tally_records(run_dir, run_id, larch_version, period):
    try:
        data = json.loads(read_text(os.path.join(run_dir, "code-review-tally.json")) or "{}")
    except (ValueError, TypeError):
        return []
    rows = []
    for item in self_review_tally_items(data):
        rows.append({
            "skill": "implement", "source": "committed-self-review-tally", "run_id": run_id,
            "round": "", "phase": "code-review", "finding_id": item.finding_id,
            "larch_version": larch_version,
            "outcome": item.outcome, "is_oos_id": False,
            "title": "",
            "focus_area": "",
            "body_severity": "",
            "severity": "(none)",
            "reviewers": "", "tools": [], "is_dynamic": False,
            "v_severities": [],
            "v_qualities": [],
            "v_correctness": [],
            "v_uncertain": [],
            "period": period,
            "text": "",
        })
    return rows


def _extract_implement(impl_root, cutoff, since_version=None):
    run_dirs = sorted(glob.glob(os.path.join(impl_root, "*")))
    if not run_dirs:
        return []
    jobs = [(run_dir, cutoff, since_version) for run_dir in run_dirs]
    records = []
    # Per-run-dir work is independent and dominated by file I/O plus C-level
    # json/regex parsing (which release the GIL), so threads overlap it. Threads
    # (not processes) also keep this working when the module is imported under a
    # synthetic name in tests, where pickling a process worker by module
    # reference fails. executor.map preserves input order, so the report stays
    # byte-stable. #4439 Trick D.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for chunk in executor.map(_extract_one_implement_run, jobs):
            records.extend(chunk)
    return records


def _extract_one_design_tsv(args):
    # Worker for the threaded scan; cutoff / since_version passed explicitly so
    # there is no reliance on mutated module globals.
    tsv, design_root, cutoff, since_version = args
    records = []
    block_dir = os.path.dirname(tsv)
    rmatch = re.search(r"/design/([^/]+)/", tsv.replace(os.sep, "/"))
    run_id = rmatch.group(1) if rmatch else ""
    run_dir = os.path.join(design_root, run_id)
    started = manifest_started(run_dir)
    larch_version = manifest_larch_version(run_dir)
    period = period_of_version(since_version, larch_version) if since_version is not None else period_of(cutoff, started_at=started)
    rnmatch = re.search(r"round-(\d+)", block_dir)
    rnum = rnmatch.group(1) if rnmatch else ""
    tsv_recs = parse_design_tsv(read_text(tsv))
    content = parse_md_blocks(read_text(os.path.join(block_dir, "findings.md")))
    for fid, trec in tsv_recs.items():
        crec = content.get(fid, {})
        fields = crec.get("fields", {})
        reviewers = trec.get("reviewers", "") or fields.get("reviewer(s)", "")
        title = crec.get("title", "") or fields.get("concern", "")[:120] or fid
        body_severity = trec.get("body_severity", "") or ""
        severity = normalize_design_severity(body_severity) if body_severity else (modal(trec.get("severities", [])) or normalize_design_severity(fields.get("severity", "")))
        if severity == "":
            severity = "(none)"
        fallback_text = reviewers or fid
        records.append({
            "skill": "design", "source": "committed", "run_id": run_id,
            "round": rnum, "phase": "plan-review", "finding_id": fid,
            "larch_version": larch_version,
            "outcome": trec.get("result", ""), "is_oos_id": fid.startswith("OOS"),
            "title": title[:300],
            "focus_area": fields.get("focus area", ""),
            "body_severity": body_severity,
            "scope": trec.get("scope", ""),
            "severity": severity,
            "reviewers": reviewers,
            "tools": tools_from(reviewers),
            "is_dynamic": is_dynamic(reviewers),
            "v_severities": trec.get("severities", []),
            "v_qualities": trec.get("qualities", []),
            "v_correctness": trec.get("correctness", []),
            "v_uncertain": trec.get("uncertain", []),
            "period": period,
            "text": (title + "\n" + (fields.get("concern", "") or fallback_text) + "\n"
                     + fields.get("proposed resolution", "") + "\n" + crec.get("raw", ""))[:2000],
        })
    return records


def _extract_design(design_root, cutoff, since_version=None):
    tsvs = sorted(glob.glob(os.path.join(design_root, "*", "**", "findings-classification.tsv"), recursive=True))
    if not tsvs:
        return []
    jobs = [(tsv, design_root, cutoff, since_version) for tsv in tsvs]
    records = []
    # Threaded for the same reasons as _extract_implement (I/O- and C-parse-
    # bound, and import-safe under a synthetic module name). executor.map
    # preserves input order, so the report stays byte-stable. #4439 Trick D.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for chunk in executor.map(_extract_one_design_tsv, jobs):
            records.extend(chunk)
    return records


def _parse_started_at(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _design_run_manifest(run_dir):
    try:
        data = json.loads(read_text(os.path.join(run_dir, "manifest.json")) or "{}")
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _enumerate_design_run_dirs(design_root, cutoff, since_version):
    if not os.path.isdir(design_root):
        return []
    run_dirs = []
    for run_dir in sorted(glob.glob(os.path.join(design_root, "*"))):
        if not os.path.isdir(run_dir):
            continue
        manifest = _design_run_manifest(run_dir)
        if manifest is None:
            continue
        started_at = manifest.get("started_at")
        larch_version = manifest.get("larch_version", "")
        if since_version is not None:
            parsed = parse_larch_version(larch_version if isinstance(larch_version, str) else "")
            if parsed is None or parsed < since_version:
                continue
        elif cutoff is not None:
            started = _parse_started_at(started_at)
            if started is None:
                continue
            if cutoff.tzinfo is not None and started.tzinfo is None:
                started = started.replace(tzinfo=datetime.timezone.utc)
            if started < cutoff:
                continue
        run_dirs.append((run_dir, manifest))
    return run_dirs


def _collect_guideline_assessment_coverage(design_root, cutoff, since_version):
    coverage = []
    for run_dir, manifest in _enumerate_design_run_dirs(design_root, cutoff, since_version):
        path = os.path.join(run_dir, DESIGN_ASSESSMENT)
        has_artifact = False
        kind = "missing"
        if os.path.exists(path) or os.path.islink(path):
            regular_file = os.path.isfile(path) and not os.path.islink(path)
            body = read_text(path) if regular_file else ""
            if regular_file and body.strip():
                if body.rstrip("\n") == CLEAN_PRESENTATION_NOTE:
                    has_artifact = True
                    kind = "clean"
                else:
                    has_artifact = True
                    kind = "deviation"
        coverage.append({
            "run_id": os.path.basename(run_dir),
            "larch_version": manifest.get("larch_version", "") if isinstance(manifest.get("larch_version", ""), str) else "",
            "started_at": manifest.get("started_at", "") if isinstance(manifest.get("started_at", ""), str) else "",
            "has_artifact": has_artifact,
            "assessment_kind": kind,
        })
    return coverage


def _enumerate_implement_run_dirs(implement_root, cutoff, since_version):
    if not os.path.isdir(implement_root):
        return []
    run_dirs = []
    for run_dir in sorted(glob.glob(os.path.join(implement_root, "*"))):
        if not os.path.isdir(run_dir):
            continue
        try:
            manifest = json.loads(read_text(os.path.join(run_dir, "manifest.json")) or "{}")
        except (ValueError, TypeError):
            continue
        if not isinstance(manifest, dict):
            continue
        started_at = manifest.get("started_at")
        larch_version = manifest.get("larch_version", "")
        if since_version is not None:
            parsed = parse_larch_version(larch_version if isinstance(larch_version, str) else "")
            if parsed is None or parsed < since_version:
                continue
        elif cutoff is not None:
            started = _parse_started_at(started_at)
            if started is None:
                continue
            if cutoff.tzinfo is not None and started.tzinfo is None:
                started = started.replace(tzinfo=datetime.timezone.utc)
            if started < cutoff:
                continue
        run_dirs.append((run_dir, manifest))
    return run_dirs


def _valid_guideline_outcome(data):
    if not isinstance(data, dict):
        return False
    required = {"schema_version", "phase", "step", "outcome", "reason", "detail", "guidelines_status", "head_sha", "base_ref"}
    if not required.issubset(data):
        return False
    return (
        str(data.get("schema_version") or "") == "1"
        and str(data.get("outcome") or "") in {"pinned", "clean", "dropped"}
        and str(data.get("guidelines_status") or "") in {"present", "absent", "invalid"}
        and str(data.get("reason") or "") in GUIDELINE_SHIP_REASON_TOKENS
        and bool(str(data.get("head_sha") or "").strip())
        and bool(str(data.get("base_ref") or "").strip())
    )


def _collect_implement_guideline_outcome_coverage(implement_root, cutoff, since_version):
    coverage = []
    cutover = parse_larch_version(config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION)
    for run_dir, manifest in _enumerate_implement_run_dirs(implement_root, cutoff, since_version):
        run_path = Path(run_dir)
        version = manifest.get("larch_version", "") if isinstance(manifest.get("larch_version", ""), str) else ""
        version_tuple = parse_larch_version(version)
        step8 = implement_step8_reachable(run_path, manifest)
        at_cutover = version_tuple is not None and cutover is not None and version_tuple >= cutover
        classification = "missing-legacy"
        outcome = ""
        reason = ""
        assessment_kind = ""
        artifact = os.path.join(run_dir, GUIDELINE_SHIP_OUTCOME_SIDECAR)
        if step8 and at_cutover:
            classification = "missing-current"
        if os.path.exists(artifact) or os.path.islink(artifact):
            try:
                data = json.loads(read_text(artifact) or "{}")
            except (ValueError, TypeError):
                data = None
            if _valid_guideline_outcome(data):
                classification = "valid"
                outcome = str(data.get("outcome") or "")
                reason = str(data.get("reason") or "")
                assessment_kind = str(data.get("assessment_kind") or "")
        coverage.append({
            "run_id": os.path.basename(run_dir),
            "larch_version": version,
            "started_at": manifest.get("started_at", "") if isinstance(manifest.get("started_at", ""), str) else "",
            "classification": classification,
            "outcome": outcome,
            "reason": reason,
            "assessment_kind": assessment_kind,
        })
    return coverage


def _extract_in_progress(sessions_dir, cutoff, inprogress_min):
    records = []
    content_files = ["findings.md", "accepted-plan-findings.md", "accepted-plan-findings-all.md",
                     "rejected-findings.md", "findings-oos.md", "findings-in-scope.md"]
    for sdir in sorted(glob.glob(os.path.join(sessions_dir, "claude-design-*"))):
        vt = os.path.join(sdir, "voting-tally.md")
        if not os.path.exists(vt):
            continue
        try:
            mtime = os.path.getmtime(vt)
        except OSError:
            continue
        if inprogress_min and mtime < inprogress_min:
            continue
        tally = parse_voting_tally(read_text(vt))
        if not tally:
            continue
        content = {}
        for name in content_files:
            path = os.path.join(sdir, name)
            if os.path.exists(path):
                for fid, rec in parse_md_blocks(read_text(path)).items():
                    if fid not in content or len(rec["fields"]) > len(content[fid]["fields"]):
                        content[fid] = rec
        for fid, trec in tally.items():
            crec = content.get(fid, {})
            fields = crec.get("fields", {})
            reviewers = trec.get("reviewers", "") or fields.get("reviewer(s)", "")
            title = crec.get("title", "") or fields.get("concern", "")[:120] or fid
            body_severity = trec.get("body_severity", "") or ""
            severity = normalize_design_severity(body_severity) if body_severity else (modal(trec.get("severities", [])) or normalize_design_severity(fields.get("severity", "")))
            if severity == "":
                severity = "(none)"
            fallback_text = reviewers or fid
            records.append({
                "skill": "design", "source": "in_progress", "run_id": os.path.basename(sdir),
                "round": "", "phase": "plan-review", "finding_id": fid,
                "outcome": trec.get("result", ""), "is_oos_id": fid.startswith("OOS"),
                "title": title[:300],
                "focus_area": fields.get("focus area", ""),
                "severity": (fields.get("severity", "") or "").lower(),
                "reviewers": fields.get("reviewer(s)", ""),
                "tools": tools_from(fields.get("reviewer(s)", "")),
                "is_dynamic": is_dynamic(fields.get("reviewer(s)", "")),
                "v_severities": [], "v_qualities": [], "v_correctness": [], "v_uncertain": [],
                "period": period_of(cutoff, mtime=mtime),
                "text": (title + "\n" + (fields.get("concern", "") or fallback_text) + "\n"
                         + fields.get("proposed resolution", "") + "\n" + crec.get("raw", ""))[:2000],
            })
    return records


# --------------------------------------------------------------------------
# aggregation helpers
# --------------------------------------------------------------------------
def threeway(rows):
    total = len(rows)
    acc = sum(1 for r in rows if r["outcome"] == "accepted")
    oos = sum(1 for r in rows if r["outcome"] == "out_of_scope")
    rej = sum(1 for r in rows if r["outcome"] in ("rejected", "exonerated", "neutral"))
    return total, acc, oos, rej


def acc_rate(rows):
    total = len(rows)
    acc = sum(1 for r in rows if r["outcome"] == "accepted")
    return acc, total, pct(acc, total)


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------
def render(records, cutoff, min_group, since_version=None, assessment_coverage=None, guideline_outcome_coverage=None, i_fn_rows=None):
    assessment_coverage = assessment_coverage or []
    guideline_outcome_coverage = guideline_outcome_coverage or []
    i_fn_rows = i_fn_rows or []
    design = [r for r in records if r["skill"] == "design"]
    impl = [r for r in records if r["skill"] == "implement"]
    d_inscope = [r for r in design if not r["is_oos_id"]]
    d_fn_inscope = [
        r for r in d_inscope
        if not _scope_is_oos(r.get("scope", ""), r.get("finding_id", ""))
        and r.get("outcome") in {"accepted", "neutral", "rejected"}
    ]
    i_all = [r for r in impl if r["phase"] == "code-review"]

    out = []
    out.append("# Review Fluff Analysis")
    out.append("")
    out.append("Characterizes review suggestions that are *not accepted* or *accepted-but-low-value*, "
               "from committed larch run logs. Counts are directional (keyword tags are approximate; "
               "severity cuts are exact). See `skills/shared/review-acceptance-rubric.md` for the "
               "necessity gate this report is designed to inform.")
    out.append("")
    out.append("- Records: **%d** total (implement code-review **%d**, design in-scope **%d**)"
               % (len(records), len(i_all), len(d_inscope)))
    src = collections.Counter(r["source"] for r in records)
    out.append("- Sources: " + ", ".join("%s=%d" % (k, v) for k, v in sorted(src.items())))
    if not i_all and not d_inscope:
        out += _section_guideline_assessment_coverage(assessment_coverage)
        out += _section_implement_guideline_outcome_coverage(guideline_outcome_coverage)
        out += _section_false_negatives(i_fn_rows, d_fn_inscope, cutoff=cutoff, since_version=since_version)
        out.append("")
        out.append("> No review findings found under the log root. Nothing to analyze.")
        return "\n".join(out) + "\n"

    out += _section_baselines(i_all, d_inscope, design)
    out += _section_guideline_assessment_coverage(assessment_coverage)
    out += _section_implement_guideline_outcome_coverage(guideline_outcome_coverage)
    out += _section_groups(i_all, d_inscope, min_group)
    out += _section_testing(i_all)
    out += _section_severity(i_all, d_inscope)
    out += _section_lanes(i_all, d_inscope)
    out += _section_accepted_low_value(i_all, d_inscope)
    out += _section_false_negatives(i_fn_rows, d_fn_inscope, cutoff=cutoff, since_version=since_version)
    if cutoff is not None or since_version is not None:
        out += _section_prepost(i_all, d_inscope, since_version=since_version)
    out += _section_recommendations(i_all, min_group)
    return "\n".join(out) + "\n"


def _section_baselines(i_all, d_inscope, design):
    out = ["", "## Baselines", ""]
    total, acc, oos, rej = threeway(i_all)
    out.append("| corpus | n | accepted | OOS | rejected |")
    out.append("|---|--:|--:|--:|--:|")
    out.append("| implement code-review | %d | %.1f%% | %.1f%% | %.1f%% |"
               % (total, pct(acc, total), pct(oos, total), pct(rej, total)))
    _, dtot, drate = acc_rate(d_inscope)
    out.append("| design in-scope | %d | %.1f%% | — | %.1f%% |" % (dtot, drate, 100 - drate))
    d_oos = [r for r in design if r["is_oos_id"]]
    if d_oos:
        _, otot, orate = acc_rate(d_oos)
        out.append("| design OOS proposals | %d | %.1f%% file-worthy | | |" % (otot, orate))
    return out


def _section_guideline_assessment_coverage(assessment_coverage):
    if not assessment_coverage:
        return []
    total = len(assessment_coverage)
    with_artifact = sum(1 for row in assessment_coverage if row.get("has_artifact"))
    clean = sum(1 for row in assessment_coverage if row.get("assessment_kind") == "clean")
    deviation = sum(1 for row in assessment_coverage if row.get("assessment_kind") == "deviation")
    out = ["", "## Guideline assessment coverage", ""]
    out.append("| runs scanned | runs with assessment artifact | clean count | deviation count |")
    out.append("|--:|--:|--:|--:|")
    out.append("| %d | %d | %d | %d |" % (total, with_artifact, clean, deviation))
    out.append("")
    out.append("| run | started_at | larch_version | assessment_kind |")
    out.append("|---|---|---|---|")
    for row in assessment_coverage:
        out.append(
            "| %s | %s | %s | %s |"
            % (
                row.get("run_id", ""),
                row.get("started_at", ""),
                row.get("larch_version", ""),
                row.get("assessment_kind", "missing"),
            )
        )
    return out


def _section_implement_guideline_outcome_coverage(guideline_outcome_coverage):
    if not guideline_outcome_coverage:
        return []
    total = len(guideline_outcome_coverage)
    valid_rows = [row for row in guideline_outcome_coverage if row.get("classification") == "valid"]
    missing_current = sum(1 for row in guideline_outcome_coverage if row.get("classification") == "missing-current")
    missing_legacy = sum(1 for row in guideline_outcome_coverage if row.get("classification") == "missing-legacy")
    pinned = sum(1 for row in valid_rows if row.get("outcome") == "pinned")
    clean = sum(1 for row in valid_rows if row.get("outcome") == "clean")
    dropped = sum(1 for row in valid_rows if row.get("outcome") == "dropped")
    reasons = collections.Counter(row.get("reason", "") for row in valid_rows if row.get("outcome") == "dropped")
    out = ["", "## Implement guideline outcome coverage", ""]
    out.append("| runs scanned | valid | missing-current | missing-legacy | pinned | clean | dropped | drop rate |")
    out.append("|--:|--:|--:|--:|--:|--:|--:|--:|")
    out.append(
        "| %d | %d | %d | %d | %d | %d | %d | %.1f%% |"
        % (total, len(valid_rows), missing_current, missing_legacy, pinned, clean, dropped, pct(dropped, len(valid_rows)))
    )
    if reasons:
        out.append("")
        out.append("| dropped reason | count |")
        out.append("|---|--:|")
        for reason, count in sorted(reasons.items()):
            out.append("| %s | %d |" % (reason, count))
    return out


def _group_rows(rows, min_group, three_way):
    table = []
    for tag in TAGS:
        sub = [r for r in rows if tag in r["_tags"]]
        if len(sub) < min_group:
            continue
        if three_way:
            total, acc, oos, rej = threeway(sub)
            table.append((tag, total, pct(acc, total), pct(oos, total), pct(rej, total)))
        else:
            _, total, rate = acc_rate(sub)
            table.append((tag, total, rate, 0.0, 0.0))
    table.sort(key=lambda row: row[2])
    return table


def _section_groups(i_all, d_inscope, min_group):
    out = ["", "## Q1 — Low-acceptance semantic groups", "",
           "Multi-label tags (a finding may carry several). Groups below the corpus baseline are "
           "fluff-prone; distinguish **reject-heavy** (down-vote / suppress) from **OOS-heavy** "
           "(valid but defer).", ""]
    rows = _group_rows(i_all, min_group, True)
    if rows:
        out.append("### implement code-review (sorted by acceptance, ascending)")
        out.append("")
        out.append("| group | n | acc% | oos% | rej% |")
        out.append("|---|--:|--:|--:|--:|")
        for tag, n, a, o, rj in rows:
            out.append("| %s | %d | %.1f | %.1f | %.1f |" % (tag, n, a, o, rj))
    drows = _group_rows(d_inscope, min_group, False)
    if drows:
        out.append("")
        out.append("### design in-scope (sorted by acceptance, ascending)")
        out.append("")
        out.append("| group | n | acc% |")
        out.append("|---|--:|--:|")
        for tag, n, a, _, _ in drows:
            out.append("| %s | %d | %.1f |" % (tag, n, a))
    return out


def _section_testing(i_all):
    test = [r for r in i_all if "theme:testing" in r["_tags"]]
    if not test:
        return []
    out = ["", "## Q2 — Testing", "",
           "Testing is typically the largest waste bucket by volume. The discriminator is "
           "necessity (severity), not size:", ""]
    out.append("- testing findings: **%d** (%.1f%% of implement code-review)"
               % (len(test), pct(len(test), len(i_all))))
    by = collections.defaultdict(list)
    for rec in test:
        by[rec.get("severity") or "(none)"].append(rec)
    out.append("")
    out.append("| testing finding | n | acc% | oos% | rej% |")
    out.append("|---|--:|--:|--:|--:|")
    for sev in ["important", "latent", "nit", "(none)"]:
        sub = by.get(sev)
        if not sub:
            continue
        total, acc, oos, rej = threeway(sub)
        out.append("| testing+%s | %d | %.1f | %.1f | %.1f |"
                   % (sev, total, pct(acc, total), pct(oos, total), pct(rej, total)))
    return out


def _section_severity(i_all, d_inscope):
    out = ["", "## Q3 — Severity / quality / uncertain", ""]
    by = collections.defaultdict(list)
    for rec in i_all:
        by[rec.get("severity") or "(none)"].append(rec)
    if any(k in by for k in ("important", "nit", "latent")):
        out.append("**implement — reviewer-authored body severity → outcome**")
        out.append("")
        out.append("| severity | n | acc% | oos% | rej% |")
        out.append("|---|--:|--:|--:|--:|")
        for sev in SEV_BODY + ["(none)"]:
            sub = by.get(sev)
            if not sub:
                continue
            total, acc, oos, rej = threeway(sub)
            out.append("| %s | %d | %.1f | %.1f | %.1f |"
                       % (sev, total, pct(acc, total), pct(oos, total), pct(rej, total)))
    dby = collections.defaultdict(list)
    for rec in d_inscope:
        dby[modal(rec.get("v_severities", [])) or "(none)"].append(rec)
    if any(dby.get(k) for k in ("important", "latent", "nit")):
        out.append("")
        out.append("**design in-scope — modal voter severity → accept rate**")
        out.append("")
        out.append("| voter severity | n | acc% |")
        out.append("|---|--:|--:|")
        for sev in ["blocker", "critical", "important", "latent", "nit", "(none)"]:
            sub = dby.get(sev)
            if not sub:
                continue
            _, total, rate = acc_rate(sub)
            out.append("| %s | %d | %.1f |" % (sev, total, rate))
    return out


def _section_lanes(i_all, d_inscope):
    out = ["", "## Reviewer lane", ""]
    wrote = False
    for label, rows in [("implement", i_all), ("design in-scope", d_inscope)]:
        lines = []
        for dyn in (True, False):
            sub = [r for r in rows if bool(r.get("is_dynamic")) == dyn]
            if len(sub) < 15:
                continue
            total, acc, oos, rej = threeway(sub)
            name = "dynamic" if dyn else "base"
            lines.append("  - %s %s: n=%d acc=%.1f%% oos=%.1f%% rej=%.1f%%"
                         % (label, name, total, pct(acc, total), pct(oos, total), pct(rej, total)))
        if lines:
            wrote = True
            out += lines
    if not wrote:
        out.append("_(insufficient lane-tagged volume)_")
    return out


def _section_accepted_low_value(i_all, d_inscope):
    out = ["", "## Accepted-but-low-value proxy", ""]
    acc_impl = [r for r in i_all if r["outcome"] == "accepted"]
    low = [r for r in acc_impl if r.get("severity") in ("nit", "latent")]
    if acc_impl:
        out.append("- implement: **%.1f%%** of accepted findings were reviewer-severity nit/latent (%d/%d)"
                   % (pct(len(low), len(acc_impl)), len(low), len(acc_impl)))
    acc_d = [r for r in d_inscope if r["outcome"] == "accepted"]
    low_d = [r for r in acc_d if modal(r.get("v_severities", [])) in ("nit", "latent")]
    if acc_d:
        out.append("- design: **%.1f%%** of accepted in-scope were modal-voter nit/latent (%d/%d)"
                   % (pct(len(low_d), len(acc_d)), len(low_d), len(acc_d)))
    return out


def _section_prepost(i_all, d_inscope, since_version=None):
    out = ["", "## Pre/post comparison" if since_version is not None else "## Pre/post cutoff", ""]
    unknown = sum(1 for r in i_all + d_inscope if r.get("period") == "unknown")
    if since_version is not None and unknown:
        out.append("- unknown-version skipped: %d" % unknown)
        out.append("")
    for label, rows, three in [("implement code-review", i_all, True), ("design in-scope", d_inscope, False)]:
        out.append("**%s**" % label)
        for per in ["pre", "post"]:
            sub = [r for r in rows if r.get("period") == per]
            if not sub:
                continue
            runs = len(set(r["run_id"] for r in sub))
            if three:
                total, acc, oos, rej = threeway(sub)
                out.append("- %s: n=%d (%d runs, %.1f/run) acc=%.1f%% oos=%.1f%% rej=%.1f%%"
                           % (per, total, runs, total / runs, pct(acc, total), pct(oos, total), pct(rej, total)))
            else:
                _, total, rate = acc_rate(sub)
                out.append("- %s: n=%d (%d runs, %.1f/run) acc=%.1f%%"
                           % (per, total, runs, total / runs, rate))
        out.append("")
    if i_all:
        out.append("**implement code-review severity tiers**")
        out.append("")
        out.append("| period | severity | n | acc% | oos% | rej% |")
        out.append("|---|---|--:|--:|--:|--:|")
        for per in ["pre", "post"]:
            per_rows = [r for r in i_all if r.get("period") == per]
            if not per_rows:
                continue
            for sev in ["important", "latent", "nit", "(none)"]:
                sub = [r for r in per_rows if normalize_severity(r.get("severity")) == sev]
                total, acc, oos, rej = threeway(sub)
                out.append("| %s | %s | %d | %.1f | %.1f | %.1f |"
                           % (per, sev, total, pct(acc, total), pct(oos, total), pct(rej, total)))
        out.append("")
        for per in ["pre", "post"]:
            per_rows = [r for r in i_all if r.get("period") == per]
            if not per_rows:
                continue
            accepted = [r for r in per_rows if r.get("outcome") == "accepted"]
            low = [r for r in accepted if normalize_severity(r.get("severity")) in ("nit", "latent")]
            out.append("- %s accepted-low-value: %.1f%% (%d/%d)"
                       % (per, pct(len(low), len(accepted)), len(low), len(accepted)))
            counts = collections.Counter(normalize_severity(r.get("severity")) for r in per_rows)
            out.append("- %s tier-composition: important %.1f%% latent %.1f%% nit %.1f%% (none) %.1f%%"
                       % (per, pct(counts.get("important", 0), len(per_rows)),
                          pct(counts.get("latent", 0), len(per_rows)),
                          pct(counts.get("nit", 0), len(per_rows)),
                          pct(counts.get("(none)", 0), len(per_rows))))
    d_prepost = [r for r in d_inscope if r.get("period") in ("pre", "post")]
    if d_prepost:
        out.append("**design in-scope voter severity tiers**")
        out.append("")
        out.append("| period | voter severity | n | acc% |")
        out.append("|---|---|--:|--:|")
        for per in ["pre", "post"]:
            per_rows = [r for r in d_prepost if r.get("period") == per]
            if not per_rows:
                continue
            for sev in ["blocker", "critical", "important", "latent", "nit", "(none)"]:
                sub = [r for r in per_rows if (modal(r.get("v_severities", [])) or "(none)") == sev]
                if not sub:
                    continue
                _, total, rate = acc_rate(sub)
                out.append("| %s | %s | %d | %.1f |" % (per, sev, total, rate))
        out.append("")
    out.append("_Small post samples are directional only._")
    return out



def _false_negative_neutral_rows(i_fn_rows, d_fn_inscope, *, period=None):
    spec = [("implement false-negative", i_fn_rows, "implement"), ("design in-scope", d_fn_inscope, "design")]
    table = []
    for label, rows, corpus in spec:
        if period is not None:
            rows = [r for r in rows if r.get("period") == period]
        by_tier = collections.defaultdict(list)
        for row in rows:
            by_tier[_reviewer_claimed_tier(row.get("body_severity"), corpus=corpus)].append(row)
        for tier in ["important", "latent", "nit", "(none)"]:
            sub = by_tier.get(tier, [])
            total = len(sub)
            neutral = sum(1 for row in sub if (row.get("voting_result") or row.get("outcome")) == "neutral")
            runs = len(set(str(row.get("run_id") or "") for row in sub if row.get("run_id")))
            table.append((label, tier, neutral, total, pct(neutral, total), runs))
    return table


def _false_negative_reject_rows(i_fn_rows, d_fn_inscope, *, period=None):
    spec = [("implement false-negative", i_fn_rows, "implement"), ("design in-scope", d_fn_inscope, "design")]
    table = []
    for label, rows, corpus in spec:
        if period is not None:
            rows = [r for r in rows if r.get("period") == period]
        important = [r for r in rows if _reviewer_claimed_tier(r.get("body_severity"), corpus=corpus) == "important"]
        rejected = sum(1 for row in important if (row.get("voting_result") or row.get("outcome")) == "rejected")
        runs = len(set(str(row.get("run_id") or "") for row in important if row.get("run_id")))
        table.append((label, rejected, len(important), pct(rejected, len(important)), runs))
    return table


def _append_neutral_table(out, rows, *, include_period=False, period=""):
    if include_period:
        out.append("| period | corpus | tier | neutral | total | rate | runs |")
        out.append("|---|---|---|--:|--:|--:|--:|")
    else:
        out.append("| corpus | tier | neutral | total | rate | runs |")
        out.append("|---|---|--:|--:|--:|--:|")
    wrote = False
    for label, tier, neutral, total, rate, runs in rows:
        if not total:
            continue
        wrote = True
        if include_period:
            out.append("| %s | %s | %s | %d | %d | %.1f%% | %d |" % (period, label, tier, neutral, total, rate, runs))
        else:
            out.append("| %s | %s | %d | %d | %.1f%% | %d |" % (label, tier, neutral, total, rate, runs))
    if not wrote:
        if include_period:
            out.append("| %s | n/a | n/a | 0 | 0 | n/a | 0 |" % period)
        else:
            out.append("| n/a | n/a | 0 | 0 | n/a | 0 |")


def _append_reject_table(out, rows, *, include_period=False, period=""):
    if include_period:
        out.append("| period | corpus | rejected | reviewer-claimed-important | rate | runs |")
        out.append("|---|---|--:|--:|--:|--:|")
    else:
        out.append("| corpus | rejected | reviewer-claimed-important | rate | runs |")
        out.append("|---|--:|--:|--:|--:|")
    wrote = False
    for label, rejected, total, rate, runs in rows:
        if not total:
            continue
        wrote = True
        if include_period:
            out.append("| %s | %s | %d | %d | %.1f%% | %d |" % (period, label, rejected, total, rate, runs))
        else:
            out.append("| %s | %d | %d | %.1f%% | %d |" % (label, rejected, total, rate, runs))
    if not wrote:
        if include_period:
            out.append("| %s | n/a | 0 | 0 | n/a | 0 |" % period)
        else:
            out.append("| n/a | 0 | 0 | n/a | 0 |")


def _section_false_negatives(i_fn_rows, d_fn_inscope, cutoff=None, since_version=None):
    out = ["", "## False-negative / under-acceptance metrics", ""]
    out.append("Diagnostic-only rates over TSV panel verdicts and reviewer-claimed `body_severity` tiers.")
    out.append("")
    out.append("### Neutral-rate by severity tier")
    out.append("")
    _append_neutral_table(out, _false_negative_neutral_rows(i_fn_rows, d_fn_inscope))
    out.append("")
    out.append("### Important-reject-rate")
    out.append("")
    _append_reject_table(out, _false_negative_reject_rows(i_fn_rows, d_fn_inscope))
    if cutoff is not None or since_version is not None:
        out.append("")
        out.append("### Pre/post false-negative neutral-rate")
        out.append("")
        for idx, period in enumerate(["pre", "post"]):
            if idx:
                out.append("")
            _append_neutral_table(out, _false_negative_neutral_rows(i_fn_rows, d_fn_inscope, period=period), include_period=True, period=period)
        out.append("")
        out.append("### Pre/post false-negative important-reject-rate")
        out.append("")
        for idx, period in enumerate(["pre", "post"]):
            if idx:
                out.append("")
            _append_reject_table(out, _false_negative_reject_rows(i_fn_rows, d_fn_inscope, period=period), include_period=True, period=period)
    return out

def _section_recommendations(i_all, min_group):
    out = ["", "## Recommendations (data-driven)", ""]
    base_total, base_acc, _, _ = threeway(i_all)
    baseline = pct(base_acc, base_total)
    # reject-heavy fluff groups below baseline
    fluff = []
    for tag in TAGS:
        sub = [r for r in i_all if tag in r["_tags"]]
        if len(sub) < min_group:
            continue
        total, acc, _, rej = threeway(sub)
        if pct(acc, total) < baseline and pct(rej, total) >= baseline:
            fluff.append((tag, total, pct(acc, total), pct(rej, total)))
    fluff.sort(key=lambda row: -row[3])
    if fluff:
        out.append("1. **Add these reject-heavy groups to the rubric OOS-signal list / judge down-vote list** "
                   "(below the %.0f%% baseline acceptance, high reject rate):" % baseline)
        for tag, n, a, rj in fluff[:8]:
            out.append("   - `%s` — n=%d, acc=%.0f%%, rej=%.0f%%" % (tag, n, a, rj))
    # severity floor
    acc_impl = [r for r in i_all if r["outcome"] == "accepted"]
    low = [r for r in acc_impl if r.get("severity") in ("nit", "latent")]
    if acc_impl and pct(len(low), len(acc_impl)) >= 15:
        out.append("2. **Judge severity floor:** %.0f%% of accepted implement findings were nit/latent — "
                   "instruct voters to vote NO on in-scope nit (and latent unless a real "
                   "correctness/regression defect)." % pct(len(low), len(acc_impl)))
    # testing
    test = [r for r in i_all if "theme:testing" in r["_tags"]]
    if test and pct(len(test), len(i_all)) >= 15:
        out.append("3. **Tests default-to-OOS:** testing is %.0f%% of implement findings — a test is in-scope "
                   "only if it covers a new, uncovered, risk-bearing path this feature introduces."
                   % pct(len(test), len(i_all)))
    out.append("")
    out.append("Apply changes at `skills/shared/review-acceptance-rubric.md` and propagate via its "
               "`## Update triggers` list; run `make test-render-voter-prompt`.")
    if not fluff and not (acc_impl and pct(len(low), len(acc_impl)) >= 15):
        out.append("")
        out.append("_(No strong fluff signal at the current thresholds / sample size.)_")
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def default_log_root():
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=5, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return os.path.join(proc.stdout.strip(), "larch-logs")
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.join(os.getcwd(), "larch-logs")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze review fluff from committed larch run logs.")
    parser.add_argument("--log-root", default=None,
                        help="larch-logs directory (default: <git toplevel>/larch-logs)")
    parser.add_argument("--sessions-dir", default=os.path.expanduser("~/.cache/larch/sessions"),
                        help="larch session cache dir (for --include-in-progress)")
    parser.add_argument("--include-in-progress", action="store_true",
                        help="also read in-progress design session temp dirs (racy snapshot)")
    parser.add_argument("--inprogress-since", default=None,
                        help="ISO8601 lower bound for in-progress session mtime")
    parser.add_argument("--cutoff", default=None,
                        help="ISO8601 timestamp enabling a pre/post comparison section")
    parser.add_argument("--since-version", default=None, type=parse_since_version, metavar="X.Y.Z",
                        help="larch_version threshold enabling version-based pre/post comparison")
    parser.add_argument("--min-group", type=int, default=20,
                        help="minimum findings for a semantic group to appear (default 20)")
    parser.add_argument("--out", default=None, help="write report to FILE instead of stdout")
    parser.add_argument("--post-only-tags", action="store_true",
                        help="compute semantic tags only for post-cutoff/version records; "
                             "pre-period records get empty tags (faster corpus scans)")
    args = parser.parse_args(argv)

    log_root = args.log_root or default_log_root()
    if not os.path.isdir(log_root):
        sys.stderr.write("ERROR: log root not found: %s\n" % log_root)
        return 2

    cutoff = parse_cutoff(args.cutoff)
    inprogress_min = None
    since = parse_cutoff(args.inprogress_since)
    if since is not None:
        inprogress_min = since.timestamp()

    records = extract(log_root, args.sessions_dir, args.include_in_progress, cutoff, inprogress_min, args.since_version,
                      post_only_tags=args.post_only_tags)
    i_fn_rows = build_impl_fn_rows(log_root, cutoff=cutoff, since_version=args.since_version)
    assessment_coverage = _collect_guideline_assessment_coverage(os.path.join(log_root, "design"), cutoff, args.since_version)
    guideline_outcome_coverage = _collect_implement_guideline_outcome_coverage(os.path.join(log_root, "implement"), cutoff, args.since_version)
    report = render(
        records,
        cutoff,
        max(1, args.min_group),
        since_version=args.since_version,
        assessment_coverage=assessment_coverage,
        guideline_outcome_coverage=guideline_outcome_coverage,
        i_fn_rows=i_fn_rows,
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
        sys.stderr.write("wrote %s\n" % args.out)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
