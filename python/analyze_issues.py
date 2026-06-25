# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
# ruff: noqa: B905, FURB167, PERF401, PLC0415, PLR2004, PTH123, RET504, RUF005, RUF007, S108, S607, SLF001, UP006, UP015, UP017, UP035, UP037
# pylint: skip-file
"""Analyze GitHub issue JSON for backlog and process insight."""

from __future__ import annotations

import argparse
import collections
import functools
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import oos_filer
import voting

BODY_CAP = 5 * 1024
PREFIX_RE = re.compile(r"^\s*(?:\[(?:DONE|OOS|IN PROGRESS|STALLED|URGENT)\]\s*)+", re.I)
FILE_RE = re.compile(r"\b[a-z][a-z0-9/_.-]+\.(?:sh|md)\b", re.I)

CATEGORY_RULES: Sequence[Tuple[str, Sequence[str]]] = (
    # WHY: explicit Documentation forms (`doc`/`docs`/`documentation`/`documented`/
    # `documenting`) keep `Docker`/`doctrine`/`documentary` from misclassifying as
    # Documentation, which a `doc\w*` stem would do.
    ("Documentation/contract drift", (
        "doc", "docs", "documentation", "documented", "documenting",
        "readme", "contract", "prompt", "instruction", "instructions",
        "schema", "schemas",
    )),
    # WHY: short Bug fix tokens stay strict (\bfix\b, \bbug\b, \berror\b) so they
    # cannot alias inside fixture/prefix/affix/error-prone (etc.). Plurals and
    # common inflections of fix/bug/error are enumerated explicitly so e.g. titles
    # like `Bugs in CI` or `Errors in parser` still classify as Bug fix.
    ("Bug fix", (
        "bug", "bugs",
        "fix", "fixes", "fixed", "fixing",
        "broken", "failure", "error", "errors", "crash", "regression",
    )),
    ("Test coverage", ("test", "tests", "testing", "coverage", "harness", "fixture", "fixtures", "assert")),
    ("Hardening/validation/security", ("security", "secret", "validate", "guard", "permission", "sanitize", "safe")),
    ("Refactor/code clarity", ("refactor", "cleanup", "clarity", "simplify", "rename")),
    ("Determinism/halt-prevention", ("determin", "halt", "timeout", "race", "idempotent", "retry")),
    ("New feature/new skill", ("feature", "skill", "scaffold", "add", "new")),
    ("Performance/token-cost reduction", ("performance", "token", "cost", "speed", "latency", "cache")),
)

# WHY: some CATEGORY_RULES entries are inflectional stems whose original
# substring-matching captured `doc`->"documentation", `determin`->"determinism",
# `validate`->"validation", `sanitize`->"sanitization", etc. Strict word-boundary
# matching (\bKW\b) on those keywords would regress those classifications. Mark
# stems explicitly so the compiled per-category pattern accepts trailing word
# characters (\bKW\w*) for them, while keeping short exact words like fix/add/new
# strict (\bKW\b) so they cannot alias inside fixture/prefix/affix/added/newer.
_STEM_KEYWORDS = frozenset({
    "determin",
    "validate", "sanitize", "simplify",
    "permission", "secret", "feature",
    "scaffold", "failure", "regression",
    "assert", "crash",
    "refactor", "rename",
})


def _keyword_pattern(keyword: str) -> str:
    if keyword in _STEM_KEYWORDS:
        # Trim trailing e/y so `validate`->`validat\w*`, `simplify`->`simplif\w*`.
        stem = re.sub(r"[ey]$", "", keyword)
        return re.escape(stem) + r"\w*"
    return re.escape(keyword) + r"\b"


CATEGORY_PATTERNS: Sequence[Tuple[str, "re.Pattern[str]"]] = tuple(
    (
        category,
        re.compile(
            r"\b(?:" + "|".join(_keyword_pattern(k) for k in keywords) + r")",
            re.I,
        ),
    )
    for category, keywords in CATEGORY_RULES
)

# WHY: load_issues fails the load when more than 5% of input list elements
# are unusable: non-dict elements, dicts with missing/non-numeric `number`,
# or dicts whose parsed `number` collides with a previously-retained row
# (duplicate-number skip — first-occurrence wins). --lenient suppresses only
# the threshold abort; per-element stderr WARN lines are emitted regardless.
LOAD_ISSUES_SKIP_THRESHOLD = 0.05
LOAD_ISSUES_REPR_CAP = 60
_DIGIT_RE = re.compile(r"[0-9]+")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def issue_text(issue: Mapping[str, Any], cap: int = BODY_CAP) -> str:
    return f"{issue.get('title') or ''}\n{(issue.get('body') or '')[:cap]}"


def strip_prefixes(title: str) -> str:
    return PREFIX_RE.sub("", title or "").strip()


def _parse_issue_number(value: Any) -> tuple[int | None, str | None]:
    if value is None:
        return None, "missing"
    if isinstance(value, bool):
        return None, "non-numeric"
    if isinstance(value, int):
        return (value, None) if value > 0 else (None, "non-numeric")
    if isinstance(value, str) and _DIGIT_RE.fullmatch(value):
        try:
            parsed = int(value)
        except (ValueError, OverflowError):
            return None, "non-numeric"
        return (parsed, None) if parsed > 0 else (None, "non-numeric")
    return None, "non-numeric"


def load_issues(path: str, *, lenient: bool = False) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception as exc:
        raise SystemExit(f"ERROR=Unable to parse issue JSON dump at {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise SystemExit(f"ERROR=Issue JSON dump at {path} is not a list")
    issues: List[Dict[str, Any]] = []
    skipped = 0
    number_to_index: dict[int, int] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            skipped += 1
            preview = repr(item)
            if len(preview) > LOAD_ISSUES_REPR_CAP:
                preview = preview[: LOAD_ISSUES_REPR_CAP - 3] + "..."
            print(
                f"WARN load_issues: skipping non-dict element at index {index}: {preview}",
                file=sys.stderr,
            )
            continue
        issue = dict(item)
        parsed, reason = _parse_issue_number(issue.get("number"))
        if parsed is None:
            skipped += 1
            preview = repr(issue.get("number"))
            if len(preview) > LOAD_ISSUES_REPR_CAP:
                preview = preview[: LOAD_ISSUES_REPR_CAP - 3] + "..."
            print(
                f"WARN load_issues: skipping issue with {reason} number at index {index}: {preview}",
                file=sys.stderr,
            )
            continue
        if parsed in number_to_index:
            skipped += 1
            prior_index = number_to_index[parsed]
            print(
                f"WARN load_issues: skipping duplicate parsed number {parsed} at index {index} "
                f"(first occurrence at index {prior_index} retained)",
                file=sys.stderr,
            )
            continue
        number_to_index[parsed] = index
        issue["number"] = parsed
        issue["body"] = (issue.get("body") or "")[:BODY_CAP]
        issues.append(issue)
    total = len(raw)
    if not lenient and total > 0 and skipped / total > LOAD_ISSUES_SKIP_THRESHOLD:
        raise SystemExit(
            "ERROR=load_issues skipped "
            f"{skipped}/{total} non-dict, malformed-number, or duplicate-number elements "
            f"({skipped / total * 100:.1f}% > {LOAD_ISSUES_SKIP_THRESHOLD * 100:.0f}% threshold) "
            f"in {path}; pass --lenient to suppress this check"
        )
    return issues


def percentile(values: Sequence[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percent / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def fmt_days(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}d"


def coverage_stats(issues: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    created_dates = [parse_iso(str(issue.get("createdAt") or "")) for issue in issues]
    created_dates = [date for date in created_dates if date is not None]
    close_durations: List[float] = []
    pr_closed = 0
    closed = 0
    for issue in issues:
        if str(issue.get("state") or "").upper() == "CLOSED":
            closed += 1
            refs = issue.get("closedByPullRequestsReferences") or []
            if isinstance(refs, list) and refs:
                pr_closed += 1
            created = parse_iso(str(issue.get("createdAt") or ""))
            closed_at = parse_iso(str(issue.get("closedAt") or ""))
            if created and closed_at and closed_at >= created:
                close_durations.append((closed_at - created).total_seconds() / 86400.0)
    total = len(issues)
    return {
        "total": total,
        "open": sum(1 for issue in issues if str(issue.get("state") or "").upper() == "OPEN"),
        "closed": closed,
        "oldest": min(created_dates).date().isoformat() if created_dates else "n/a",
        "newest": max(created_dates).date().isoformat() if created_dates else "n/a",
        "median_close": percentile(close_durations, 50),
        "p90_close": percentile(close_durations, 90),
        "p25_close": percentile(close_durations, 25),
        "p75_close": percentile(close_durations, 75),
        "pr_closed_pct": (pr_closed / closed * 100.0) if closed else 0.0,
    }


def default_category(issue: Mapping[str, Any]) -> str:
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")
    if body.lstrip().lower().startswith("tracking issue for") and "original prompt" in body.lower():
        return "Tracking/umbrella"
    if re.match(r"^\s*(?:\[research[^\]]*\]\s*)?(?:investigate|research)\b", title, re.I):
        return "Research/investigation"
    haystack = issue_text(issue)
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(haystack):
            return category
    return "Other"


def title_tokens(title: str) -> List[str]:
    cleaned = strip_prefixes(title).lower()
    return [
        token
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", cleaned)
        if token not in STOP_WORDS and not token.isdigit()
    ]


def categorize(issues: Sequence[Mapping[str, Any]], mode: str, top_k: int) -> Dict[int, str]:
    if mode == "default":
        return {issue_number(issue): default_category(issue) for issue in issues}

    # Auto mode strips common status prefixes, counts distinctive title tokens,
    # and assigns each issue to its highest-ranked token bucket.
    frequency: collections.Counter[str] = collections.Counter()
    issue_tokens: Dict[int, List[str]] = {}
    for issue in issues:
        number = issue_number(issue)
        tokens = title_tokens(str(issue.get("title") or ""))
        issue_tokens[number] = tokens
        frequency.update(set(tokens))
    leaders = [token for token, _count in frequency.most_common(max(top_k, 1))]
    leader_set = set(leaders)
    categories: Dict[int, str] = {}
    for issue in issues:
        number = issue_number(issue)
        bucket = next((token for token in issue_tokens.get(number, []) if token in leader_set), None)
        categories[number] = f"Auto: {bucket}" if bucket else "Other"
    return categories


def category_breakdown(
    issues: Sequence[Mapping[str, Any]], categories: Mapping[int, str]
) -> Tuple[str, collections.Counter[str]]:
    counts: collections.Counter[str] = collections.Counter()
    for issue in issues:
        counts[categories.get(issue_number(issue), "Other")] += 1
    total = max(len(issues), 1)
    lines = ["## Category Breakdown"]
    for category, count in counts.most_common():
        lines.append(f"- {category}: {count} ({count / total * 100:.1f}%)")
    return "\n".join(lines), counts


def growth_chart(
    issues: Sequence[Mapping[str, Any]], categories: Mapping[int, str], span_days: int
) -> str:
    dated = [
        (issue, parse_iso(str(issue.get("createdAt") or "")))
        for issue in issues
        if parse_iso(str(issue.get("createdAt") or "")) is not None
    ]
    if not dated:
        return "## Growth Chart\nNo growth data available."
    oldest = min(date for _issue, date in dated if date is not None)
    newest = max(date for _issue, date in dated if date is not None)
    if span_days > 0:
        oldest = newest - timedelta(days=span_days)
        dated = [(issue, date) for issue, date in dated if date and date >= oldest]
    computed_span = max((newest.date() - oldest.date()).days, 0)
    weekly = computed_span > 60
    bucket_count = computed_span // (7 if weekly else 1) + 1
    buckets = [
        (oldest + timedelta(days=index * (7 if weekly else 1))).date().isoformat()
        for index in range(bucket_count)
    ]
    category_order = sorted({categories.get(issue_number(issue), "Other") for issue, _date in dated})
    matrix: Dict[str, List[int]] = {category: [0] * bucket_count for category in category_order}
    for issue, created in sorted(dated, key=lambda pair: pair[1] or oldest):
        if created is None:
            continue
        category = categories.get(issue_number(issue), "Other")
        index = (created.date() - oldest.date()).days // (7 if weekly else 1)
        if 0 <= index < bucket_count:
            matrix[category][index] += 1
    for category in category_order:
        running = 0
        for index, value in enumerate(matrix[category]):
            running += value
            matrix[category][index] = running
    # WHY: cap legend keys at A-Z; collapse the tail into "Other (overflow)" so the
    # chart never emits non-letter symbols when the category set exceeds 26.
    if len(category_order) > 26:
        head = category_order[:25]
        tail = category_order[25:]
        overflow = [0] * bucket_count
        for category in tail:
            for index, value in enumerate(matrix[category]):
                overflow[index] += value
        category_order = head + ["Other (overflow)"]
        matrix = {**{c: matrix[c] for c in head}, "Other (overflow)": overflow}
    keys = [chr(ord("A") + index) for index in range(len(category_order))]

    chart_module = load_render_chart()
    return "## Growth Chart\n" + chart_module.render_chart(buckets=buckets, rows=[
        (key, category, matrix[category]) for key, category in zip(keys, category_order)
    ])


def load_render_chart() -> Any:
    import render_chart

    return render_chart


def pattern_observations(issues: Sequence[Mapping[str, Any]], top_k: int, stats: Mapping[str, Any]) -> str:
    daily: collections.Counter[str] = collections.Counter()
    paths: collections.Counter[str] = collections.Counter()
    auto_count = 0
    for issue in issues:
        created = parse_iso(str(issue.get("createdAt") or ""))
        if created:
            daily[created.date().isoformat()] += 1
        text = issue_text(issue)
        paths.update(match.lower() for match in FILE_RE.findall(text))
        lowered = text.lower()
        if "automatically created" in lowered or "[oos]" in str(issue.get("title") or "").lower() or "[oos]" in lowered:
            auto_count += 1

    mean_daily = (sum(daily.values()) / len(daily)) if daily else 0
    bursts = [(day, count) for day, count in daily.items() if mean_daily and count >= 2 * mean_daily]
    bursts.sort(key=lambda item: (-item[1], item[0]))

    lines = ["## Pattern Observations"]
    lines.append("- Bursty filing days:")
    if bursts:
        for day, count in bursts[:5]:
            lines.append(f"  - {day}: {count} issues ({count / mean_daily:.1f}x mean)")
    else:
        lines.append("  - None above 2x mean daily creation rate.")
    lines.append("- File-path and skill-name hot spots:")
    if paths:
        for path, count in paths.most_common(top_k):
            lines.append(f"  - {path}: {count}")
    else:
        lines.append("  - None detected.")
    total = max(len(issues), 1)
    lines.append(f"- Auto-spawned share: {auto_count}/{len(issues)} ({auto_count / total * 100:.1f}%)")
    lines.append(
        "- Closure velocity: "
        f"P25 {fmt_days(stats.get('p25_close'))}, "
        f"P50 {fmt_days(stats.get('median_close'))}, "
        f"P75 {fmt_days(stats.get('p75_close'))}, "
        f"P90 {fmt_days(stats.get('p90_close'))}"
    )
    return "\n".join(lines)


def issue_number(issue: Mapping[str, Any]) -> int:
    """Return the GitHub issue number.

    Precondition: issue was produced by load_issues, which guarantees a
    present, positive integer number field.
    """
    return int(issue["number"])


def pr_ref_id(ref: Mapping[str, Any]) -> str:
    for key in ("url", "number", "title"):
        value = ref.get(key)
        if value:
            return str(value)
    return json.dumps(ref, sort_keys=True)


def wasteful_findings(issues: Sequence[Mapping[str, Any]], top_k: int) -> str:
    by_title: MutableMapping[str, List[Mapping[str, Any]]] = collections.defaultdict(list)
    for issue in issues:
        by_title[strip_prefixes(str(issue.get("title") or "")).lower()].append(issue)

    lines = ["## Wasteful-work Findings"]
    lines.append("- W1 duplicate-titled issues opened within 7 days:")
    w1_count = 0
    for title, group in sorted(by_title.items()):
        ordered = sorted(group, key=lambda issue: parse_iso(str(issue.get("createdAt") or "")) or datetime.min.replace(tzinfo=timezone.utc))
        for left, right in zip(ordered, ordered[1:]):
            left_date = parse_iso(str(left.get("createdAt") or ""))
            right_date = parse_iso(str(right.get("createdAt") or ""))
            if left_date and right_date and right_date - left_date <= timedelta(days=7):
                lines.append(f"  - #{issue_number(left)} and #{issue_number(right)}: {title}")
                w1_count += 1
                if w1_count >= top_k:
                    break
        if w1_count >= top_k:
            break
    if not w1_count:
        lines.append("  - None detected.")

    reversal_re = re.compile(
        r"\b(revert|undo|superseded|re-introduce|re-add|closed in favor of)\b.*?(#[0-9]+|[0-9a-f]{7,40}|https?://\S+)?",
        re.I | re.S,
    )
    lines.append("- W2 reversal/supersession mentions:")
    found = 0
    for issue in issues:
        text = f"{issue.get('title') or ''}\n{(issue.get('body') or '')[:3072]}"
        match = reversal_re.search(text)
        if match:
            ref = match.group(2) or "no explicit PR/commit reference"
            lines.append(f"  - #{issue_number(issue)}: {match.group(1)} ({ref})")
            found += 1
            if found >= top_k:
                break
    if not found:
        lines.append("  - None detected.")

    stalled = [issue for issue in issues if str(issue.get("title") or "").lstrip().lower().startswith("[stalled]")]
    lines.append(f"- W3 [STALLED] issues: {len(stalled)} total")
    for issue in stalled[:top_k]:
        lines.append(f"  - #{issue_number(issue)} {issue.get('title') or ''}")

    pr_clusters: MutableMapping[str, List[int]] = collections.defaultdict(list)
    for issue in issues:
        refs = issue.get("closedByPullRequestsReferences") or []
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, dict):
                    pr_clusters[pr_ref_id(ref)].append(issue_number(issue))
    lines.append("- W4 PR-to-issue closure clusters:")
    clusters = [(pr, numbers) for pr, numbers in pr_clusters.items() if len(numbers) >= 3]
    clusters.sort(key=lambda item: (-len(item[1]), item[0]))
    if clusters:
        for pr, numbers in clusters[:top_k]:
            lines.append(f"  - {pr}: closes {len(numbers)} issues ({', '.join('#' + str(n) for n in sorted(numbers))})")
    else:
        lines.append("  - None detected.")

    lines.append("- W5 auto-loop duplicate filings:")
    duplicates = [(title, group) for title, group in by_title.items() if title and len(group) >= 2]
    duplicates.sort(key=lambda item: (-len(item[1]), item[0]))
    if duplicates:
        for title, group in duplicates[:top_k]:
            numbers = ", ".join(f"#{issue_number(issue)}" for issue in sorted(group, key=issue_number))
            lines.append(f"  - {title}: {len(group)} issues ({numbers})")
    else:
        lines.append("  - None detected.")
    return "\n".join(lines)


def normalize_tool(raw: str) -> str:
    value = raw.lower()
    if value.startswith("code,") or value == "code":
        return "claude"
    if value == "main agent":
        return "main agent"
    return value


def reviewer_effectiveness(issues: Sequence[Mapping[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    # WHY: keep codex/code alternatives longest-first so "codex" is not counted as "code".
    tool_re = re.compile(r"\b(codex|cursor|claude|main\s+agent|code,\s*claude\s+code\s+reviewer|code)\b", re.I)
    persona_re = re.compile(
        r"\b(architect|arch|correctness|edge-cases|edge|structure|testing|innovation|pragmatic|security|generic)\b",
        re.I,
    )
    pair_counts: collections.Counter[Tuple[str, str]] = collections.Counter()
    pair_done: collections.Counter[Tuple[str, str]] = collections.Counter()
    tool_counts: collections.Counter[str] = collections.Counter()
    tool_done: collections.Counter[str] = collections.Counter()
    vote_rows: List[Tuple[int, str, str, str]] = []

    # WHY: larch issues use canonical markdown fields; tolerate plain "Surfaced by:" too.
    attribution_re = re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*\s*)?(?:reviewer|surfaced\s+by)\s*(?:\*\*)?\s*[:\-]\s*(.+?)\s*$",
        re.I,
    )
    # WHY: real tallies use comma separators and may include EXONERATE; accept both.
    vote_re = re.compile(
        r"YES\s*=\s*(\d+)\s*[,\s]+\s*NO\s*=\s*(\d+)(?:\s*[,\s]+\s*EXONERATE\s*=\s*(\d+))?",
        re.I,
    )

    for issue in issues:
        body = str(issue.get("body") or "")
        attribution = ""
        for line in body.splitlines():
            match = attribution_re.match(line)
            if match:
                attribution = match.group(1)
                break
        if not attribution:
            continue
        tool_match = tool_re.search(attribution)
        persona_match = persona_re.search(attribution)
        tool = normalize_tool(tool_match.group(1).replace("  ", " ").lower()) if tool_match else "unknown"
        persona = persona_match.group(1).lower() if persona_match else "generic"
        persona = {"arch": "architect", "edge": "edge-cases"}.get(persona, persona)
        key = (tool, persona)
        done = str(issue.get("title") or "").lstrip().upper().startswith("[DONE]")
        pair_counts[key] += 1
        tool_counts[tool] += 1
        if done:
            pair_done[key] += 1
            tool_done[tool] += 1
        vote_match = vote_re.search(body)
        if vote_match:
            yes, no, exonerate = vote_match.group(1), vote_match.group(2), vote_match.group(3)
            tally = f"YES={yes} NO={no}"
            if exonerate is not None:
                tally += f" EXONERATE={exonerate}"
            vote_rows.append((issue_number(issue), tool, persona, tally))

    lines = ["## Reviewer/Persona Tables"]
    lines.append("Aggregate per tool:")
    if tool_counts:
        for tool, total in tool_counts.most_common():
            done = tool_done[tool]
            lines.append(f"- {tool}: {total} findings, {done} done ({done / total * 100:.1f}%)")
    else:
        lines.append("- No reviewer attribution lines detected.")

    lines.append("Per tool/persona:")
    for (tool, persona), total in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0])):
        done = pair_done[(tool, persona)]
        lines.append(f"- {tool} / {persona}: {total} findings, {done} done ({done / total * 100:.1f}%)")
    if not pair_counts:
        lines.append("- No tool/persona pairs detected.")

    lines.append("Design-phase vote findings:")
    if vote_rows:
        for number, tool, persona, votes in vote_rows:
            lines.append(f"- #{number}: {tool} / {persona} ({votes})")
    else:
        lines.append("- None with explicit YES=N NO=M tallies.")

    eligible = [
        (pair_done[key] / total, key, total, pair_done[key])
        for key, total in pair_counts.items()
        if total >= 10
    ]
    eligible.sort(key=lambda item: (-item[0], item[1]))
    lines.append("Top ROI reviewer/persona pairs:")
    if eligible:
        for rate, (tool, persona), total, done in eligible[:3]:
            lines.append(f"- {tool} / {persona}: {done}/{total} done ({rate * 100:.1f}%)")
    else:
        lines.append("- None with at least 10 findings.")

    best: Tuple[float, Tuple[str, str], int, int] | None = eligible[0] if eligible else None
    return "\n".join(lines), {"pair_counts": pair_counts, "pair_done": pair_done, "best": best}


_GITHUB_ISSUE_URL_RE = re.compile(r"https://[^\s|)]+/[^/\s|)]+/[^/\s|)]+/issues/(\d+)")
_COMBINED_AWAY_MARKER_RE = re.compile(r"<!--\s*larch:combined-away\s+source=#\d+\s+target=#\d+\s*-->", re.I)
_LEGACY_COMBINED_RE = re.compile(r"\bCombined\s+into\s+#\d+\b", re.I)
_OOS_HEADING_RE = re.compile(r"^###\s+((?:OOS|FINDING)_\d+):\s*(.*?)\s*$", re.MULTILINE)
_STABLE_ID_LINE_RE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Stable ID(?:\*\*)?[ \t]*:[ \t]*(\S+)", re.I | re.M)
_FILED_URL_LINE_RE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Filed[ \t]*URL(?:\*\*)?[ \t]*:[ \t]*(https://[^\s|)]+/issues/\d+)", re.I | re.M)
_FILED_AS_RE = re.compile(r"\bFiled\s+as\s+#(\d+)\b", re.I)
_FILED_AS_URL_RE = re.compile(r"\bFiled\s+as\s+(https://[^\s|)]+/issues/\d+)", re.I)
_FILED_COLON_URL_RE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Filed(?:\*\*)?[ \t]*:[ \t]*(https://[^\s|)]+/issues/\d+)", re.I | re.M)
_FILED_OOS_NUMBER_RE = re.compile(r"\bFiled\s+OOS\s+issue\s+#(\d+)\b", re.I)
_FILED_OOS_URL_RE = re.compile(r"\bFiled\s+OOS\s+issue\s*:\s*(https://[^\s|)]+/issues/\d+)", re.I)
_CAP_ROLLUP_TITLE_RE = re.compile(r"Aggregated rollup of\s+\d+\s+capped OOS items", re.I)
_OOS_TOKEN_RE = re.compile(r"\b(?:[A-Za-z0-9_.-]+:)?(?:OOS|FINDING)_\d+\b")
_FIELD_RE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?(Reviewer\(s\)|Reviewers?|Filed[ \t]*URL|Stable ID)(?:\*\*)?[ \t]*:[ \t]*(.*?)\s*$", re.I | re.M)


def extract_issue_number_from_url(url: str) -> int | None:
    match = _GITHUB_ISSUE_URL_RE.search(url or "")
    return int(match.group(1)) if match else None


def extract_repo_from_url(url: str) -> str | None:
    match = re.search(r"github\.com/([^/\s|)]+/[^/\s|)]+)/issues/", url or "", re.I)
    return match.group(1) if match else None


def _extract_filed_issue_numbers_from_text(text: str) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()

    def add(value: int | None) -> None:
        if value and value not in seen:
            seen.add(value)
            numbers.append(value)

    for match in _FILED_URL_LINE_RE.finditer(text or ""):
        add(extract_issue_number_from_url(match.group(1)))
    for match in _FILED_COLON_URL_RE.finditer(text or ""):
        add(extract_issue_number_from_url(match.group(1)))
    for pattern in (_FILED_AS_RE, _FILED_OOS_NUMBER_RE):
        for match in pattern.finditer(text or ""):
            add(int(match.group(1)))
    for match in _FILED_AS_URL_RE.finditer(text or ""):
        add(extract_issue_number_from_url(match.group(1)))
    for match in _FILED_OOS_URL_RE.finditer(text or ""):
        add(extract_issue_number_from_url(match.group(1)))
    for line in (text or "").splitlines():
        lowered = line.lower()
        if not line.lstrip().startswith("|") or not ({"filed", "oos"} & set(re.findall(r"[a-z]+", lowered))):
            continue
        for url_match in _GITHUB_ISSUE_URL_RE.finditer(line):
            add(int(url_match.group(1)))
    return numbers


def extract_filed_issue_number_from_text(text: str) -> int | None:
    numbers = _extract_filed_issue_numbers_from_text(text)
    return numbers[0] if numbers else None


def issue_labels(issue: Mapping[str, Any]) -> set[str]:
    labels: set[str] = set()
    raw = issue.get("labels") or []
    if not isinstance(raw, list):
        return labels
    for item in raw:
        value = item.get("name") if isinstance(item, Mapping) else item
        if value:
            labels.add(str(value).strip().lower())
    return labels


def issue_comments(issue: Mapping[str, Any]) -> list[str]:
    comments: list[str] = []
    raw = issue.get("comments") or []
    if not isinstance(raw, list):
        return comments
    for item in raw:
        if isinstance(item, str):
            comments.append(item)
        elif isinstance(item, Mapping):
            comments.append(str(item.get("body") or ""))
    return comments


def has_combined_away_marker(issue: Mapping[str, Any]) -> bool:
    body = str(issue.get("body") or "")
    if _COMBINED_AWAY_MARKER_RE.search(body):
        return True
    for comment in issue_comments(issue):
        if _COMBINED_AWAY_MARKER_RE.search(comment) or _LEGACY_COMBINED_RE.search(comment):
            return True
    return False


def _has_not_planned_signal(issue: Mapping[str, Any]) -> bool:
    degraded = issue.get("_larch_degraded_fields") or []
    state_reason_degraded = isinstance(degraded, list) and "stateReason" in degraded
    state_reason = str(issue.get("stateReason") or "").strip().upper()
    if state_reason == "NOT_PLANNED" and not state_reason_degraded:
        return True
    labels = issue_labels(issue)
    if labels & {"wontfix", "won't fix", "not planned", "not-planned"}:
        return True
    body = str(issue.get("body") or "").lower()
    return bool(re.search(r"\b(?:wontfix|won't fix|not[- ]planned|no plan to fix)\b", body))


def classify_oos_issue_fate(issue: Mapping[str, Any] | None) -> dict[str, Any]:
    if not issue:
        return {"bucket": "skipped missing issue", "adjusted": 0, "provisional": 0, "docked": False, "unknown": False}
    if issue.get("__fetch_failed__"):
        state = str(issue.get("state") or "").strip()
        refs = issue.get("closedByPullRequestsReferences") or []
        if not state and not (isinstance(refs, list) and refs):
            return {"bucket": "skipped missing issue", "adjusted": 0, "provisional": 0, "docked": False, "unknown": False}
    state = str(issue.get("state") or "").upper()
    if state == "OPEN":
        return {"bucket": "provisional open", "adjusted": 1, "provisional": 1, "docked": False, "unknown": False}
    refs = issue.get("closedByPullRequestsReferences") or []
    if isinstance(refs, list) and refs:
        return {"bucket": "kept by PR", "adjusted": 1, "provisional": 1, "docked": False, "unknown": False}
    if has_combined_away_marker(issue):
        return {"bucket": "docked combined-away", "adjusted": 0, "provisional": 1, "docked": True, "unknown": False}
    if state == "CLOSED" and _has_not_planned_signal(issue):
        return {"bucket": "docked closed-unfixed", "adjusted": 0, "provisional": 1, "docked": True, "unknown": False}
    if state == "CLOSED":
        return {"bucket": "provisional unknown", "adjusted": 1, "provisional": 1, "docked": False, "unknown": True}
    return {"bucket": "provisional unknown", "adjusted": 1, "provisional": 1, "docked": False, "unknown": True}


def _bare_oos_item_suffix(stable_id: str) -> str | None:
    return oos_filer._bare_oos_item_suffix(stable_id)  # pyright: ignore[reportPrivateUsage]


def _canonical_stable_id(source_key: str, bare_id: str) -> str:
    return f"{source_key}:{bare_id}" if source_key else bare_id


def _hash_stable_id(title: str, body: str, source_key: str) -> str:
    return oos_filer._stable_identifier(title, body, source_key=source_key)  # pyright: ignore[reportPrivateUsage]


def _stable_ids_cover(issue_stable_id: str, block_keys: set[Any], *, allow_main_agent_bridge: bool = False) -> bool:
    if not issue_stable_id:
        return False
    if issue_stable_id in block_keys:
        return True
    issue_suffix = _bare_oos_item_suffix(issue_stable_id)
    if not issue_suffix:
        return False
    issue_source = issue_stable_id.rsplit(":", 1)[0] if ":" in issue_stable_id else ""
    for block_key in block_keys:
        if not isinstance(block_key, str):
            continue
        block_suffix = _bare_oos_item_suffix(block_key)
        if block_suffix != issue_suffix:
            continue
        block_source = block_key.rsplit(":", 1)[0] if ":" in block_key else ""
        if not issue_source:
            continue
        if issue_source and block_source:
            if issue_source == block_source:
                return True
            if allow_main_agent_bridge and issue_source in {block_source, "oos-accepted-main-agent"}:
                return True
            continue
        if not block_source:
            if allow_main_agent_bridge and issue_source == "oos-accepted-main-agent":
                return True
            continue
    return False


def _normalize_oos_title(value: str) -> str:
    cleaned = re.sub(r"^\[(?:OUT_OF_SCOPE|OOS)\]\s*", "", value.strip(), flags=re.I)
    return cleaned.strip()


def _parse_markdown_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in _FIELD_RE.finditer(block):
        key = re.sub(r"\s+", " ", match.group(1).lower().replace(" ", ""))
        if key in {"reviewer(s)", "reviewers", "reviewer"}:
            fields["reviewer"] = match.group(2).strip()
        elif key == "filedurl":
            fields["filed_url"] = match.group(2).strip()
        elif key == "stableid":
            fields.setdefault("stable_id", match.group(2).strip())
    return fields


def _parse_oos_accepted_blocks(path: Path, *, run_dir: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(_OOS_HEADING_RE.finditer(text))
    blocks: list[dict[str, Any]] = []
    source_key = oos_filer._stable_source_key(path)  # pyright: ignore[reportPrivateUsage]
    try:
        artifact_relpath = path.relative_to(run_dir).as_posix()
    except ValueError:
        artifact_relpath = path.name
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].rstrip()
        heading_id = match.group(1)
        title = _normalize_oos_title(match.group(2))
        fields = _parse_markdown_fields(body)
        canonical = _canonical_stable_id(source_key, heading_id)
        hash_id = _hash_stable_id(title, body, source_key)
        lookup_keys = {canonical, hash_id, heading_id, (artifact_relpath, heading_id)}
        record = {
            "title": title,
            "body": body,
            "heading_id": heading_id,
            "source_key": source_key,
            "artifact_relpath": artifact_relpath,
            "canonical_stable_id": canonical,
            "hash_stable_id": hash_id,
            "stable_id": fields.get("stable_id") or canonical,
            "reviewer": fields.get("reviewer") or "unknown",
            "filed_url": fields.get("filed_url") or "",
            "lookup_keys": lookup_keys,
            "identity": (artifact_relpath, heading_id),
        }
        blocks.append(record)
    return blocks


def _index_accepted_blocks_by_stable_id(blocks: Sequence[Mapping[str, Any]]) -> dict[Any, list[dict[str, Any]]]:
    index: dict[Any, list[dict[str, Any]]] = collections.defaultdict(list)
    for block in blocks:
        block_dict = dict(block)
        for key in block.get("lookup_keys", set()):
            index[key].append(block_dict)
    return dict(index)


def _stable_ids_from_record(record: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    body = str(record.get("body") or "")
    for raw in [*(record.get("stable_ids") or [] if isinstance(record.get("stable_ids"), list) else []), str(record.get("stable_id") or "")]:
        if raw and raw not in seen:
            seen.add(raw)
            values.append(raw)
    for match in _STABLE_ID_LINE_RE.finditer(body):
        value = match.group(1).strip()
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _extract_legacy_stable_ids_from_ndjson_body(body: str) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    filed_line_re = re.compile(
        r"^.*\bFiled(?:\s+URL|\s+as|\s+OOS\s+issue).*$",
        re.I | re.M,
    )
    segments = [match.group(0) for match in filed_line_re.finditer(body or "")]
    if not segments:
        return []
    for segment in segments:
        for match in _OOS_TOKEN_RE.finditer(segment):
            value = match.group(0)
            if value not in seen:
                seen.add(value)
                values.append(value)
    return values


def _is_cap_rollup_record(record: dict[str, Any]) -> bool:
    text = f"{record.get('title') or ''}\n{record.get('body') or ''}"
    if _CAP_ROLLUP_TITLE_RE.search(text):
        return True
    return bool(re.search(r"Aggregated rollup", text, re.I))


def _resolve_blocks_for_stable_id(stable_id: str, blocks: Sequence[Mapping[str, Any]], body: str = "") -> tuple[list[dict[str, Any]], bool]:
    direct: list[dict[str, Any]] = []
    for block in blocks:
        if stable_id == block.get("hash_stable_id") or stable_id == block.get("canonical_stable_id") or stable_id in block.get("lookup_keys", set()):
            direct.append(dict(block))
    if not direct:
        issue_source = stable_id.rsplit(":", 1)[0] if ":" in stable_id else ""
        allow_bridge = issue_source == "oos-accepted-main-agent"
        direct = [
            dict(block)
            for block in blocks
            if _stable_ids_cover(stable_id, set(block.get("lookup_keys", set())), allow_main_agent_bridge=allow_bridge)
        ]
    if len(direct) <= 1:
        return direct, False
    cited = [block for block in direct if str(block.get("artifact_relpath") or "") in body]
    if len(cited) == 1:
        return cited, False
    return [], True


def _record_issue_urls(record: Mapping[str, Any]) -> list[str]:
    body = str(record.get("body") or "")
    urls: list[str] = []
    seen: set[str] = set()
    for raw in [str(record.get("url") or ""), str(record.get("issue_url") or "")]:
        if extract_issue_number_from_url(raw) and raw not in seen:
            seen.add(raw)
            urls.append(raw)
    for match in _FILED_URL_LINE_RE.finditer(body):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    for match in _FILED_COLON_URL_RE.finditer(body):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    for match in _FILED_AS_URL_RE.finditer(body):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    for match in _FILED_OOS_URL_RE.finditer(body):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    for line in body.splitlines():
        lowered = line.lower()
        if line.lstrip().startswith("|") and ({"filed", "oos"} & set(re.findall(r"[a-z]+", lowered))):
            for url_match in _GITHUB_ISSUE_URL_RE.finditer(line):
                url = url_match.group(0)
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
    return urls


def _record_issue_numbers(record: Mapping[str, Any]) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()
    for key in ("number", "issue_number"):
        parsed, _reason = _parse_issue_number(record.get(key))
        if parsed and parsed not in seen:
            seen.add(parsed)
            numbers.append(parsed)
    for url in _record_issue_urls(record):
        parsed = extract_issue_number_from_url(url)
        if parsed and parsed not in seen:
            seen.add(parsed)
            numbers.append(parsed)
    for parsed in _extract_filed_issue_numbers_from_text(str(record.get("body") or "")):
        if parsed not in seen:
            seen.add(parsed)
            numbers.append(parsed)
    return numbers


def _reviewers_from_label(label: str, known_labels: list[str] | None = None) -> list[str]:
    raw = (label or "").strip() or "unknown"
    labels = known_labels or []
    tokens = voting.tokenize_finding_reviewers(cell=raw, labels=labels)
    if not tokens:
        grown = list(labels)
        seen = set(grown)
        voting.grow_attribution_labels(grown, seen, raw)
        tokens = voting.tokenize_finding_reviewers(cell=raw, labels=grown)
    return tokens or [part.strip() for part in raw.split(",") if part.strip()] or ["unknown"]


def _row_from_block(run_id: str, block: Mapping[str, Any], record: Mapping[str, Any], issue_number: int | None, issue_url: str) -> dict[str, Any]:
    identity = (run_id, block.get("artifact_relpath") or "", block.get("heading_id") or block.get("hash_stable_id") or issue_url or issue_number)
    return {
        "run_id": run_id,
        "identity": identity,
        "stable_id": block.get("canonical_stable_id") or block.get("hash_stable_id") or "",
        "issue_number": issue_number,
        "issue_url": issue_url,
        "reviewer": block.get("reviewer") or "unknown",
        "title": block.get("title") or record.get("title") or "",
    }


_ROLLUP_EXCERPT_BULLET_RE = re.compile(r"^\s*-\s*\*\*(.+?)\*\*:\s*", re.M)


def _rollup_excerpt_titles_from_text(text: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for match in _ROLLUP_EXCERPT_BULLET_RE.finditer(text or ""):
        title = _normalize_oos_title(match.group(1))
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def _rollup_excerpt_source_texts(run_dir: Path, ndjson_record: Mapping[str, Any]) -> list[str]:
    texts = [str(ndjson_record.get("body") or "")]
    for path in sorted(run_dir.glob("**/oos-accepted-*.md")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = list(_OOS_HEADING_RE.finditer(text))
        for idx, match in enumerate(matches):
            heading = f"{match.group(1)}: {match.group(2)}"
            if not re.search(r"Aggregated rollup", heading, re.I):
                continue
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            texts.append(text[start:end])
    return texts


def _blocks_from_rollup_excerpt_titles(
    titles: Sequence[str],
    blocks: Sequence[Mapping[str, Any]],
    seen_identities: set[tuple[Any, ...]],
) -> list[dict[str, Any]]:
    if not titles:
        return []
    by_title: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for block in blocks:
        by_title[_normalize_oos_title(str(block.get("title") or ""))].append(dict(block))
    matched: list[dict[str, Any]] = []
    for title in titles:
        candidates = by_title.get(title, [])
        if len(candidates) != 1:
            continue
        block = candidates[0]
        identity = (str(block.get("artifact_relpath") or ""), str(block.get("heading_id") or ""))
        if identity in seen_identities:
            continue
        seen_identities.add(identity)
        matched.append(block)
    return matched


def _ambiguous_rollup_expansion_row(run_id: str, issue_number: int | None, issue_url: str) -> dict[str, Any]:
    return {"bucket": "ambiguous rollup expansion", "run_id": run_id, "issue_number": issue_number, "issue_url": issue_url, "reviewer": "unknown"}


def _ambiguous_stable_id_row(run_id: str, stable_id: str, issue_number: int | None, issue_url: str) -> dict[str, Any]:
    return {
        "bucket": "ambiguous stable id",
        "run_id": run_id,
        "identity": (run_id, "rollup-ambiguous", stable_id, issue_number or issue_url),
        "issue_number": issue_number,
        "issue_url": issue_url,
        "reviewer": "unknown",
    }


def _rollup_expansion_shortfall_result(run_id: str, issue_number: int | None, issue_url: str, out: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not out:
        return [_ambiguous_rollup_expansion_row(run_id, issue_number, issue_url)]
    return [*out, _ambiguous_rollup_expansion_row(run_id, issue_number, issue_url)]


def _issue_evidence_for_record(record: Mapping[str, Any]) -> tuple[int | None, str]:
    urls = _record_issue_urls(record)
    numbers = _record_issue_numbers(record)
    number = numbers[0] if numbers else None
    url = urls[0] if urls else ""
    if number is None and url:
        number = extract_issue_number_from_url(url)
    return number, url


def _expand_cap_rollup_records(run_dir: Path, ndjson_record: dict[str, Any], blocks: Sequence[Mapping[str, Any]], indexed_blocks: Mapping[Any, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    del indexed_blocks
    body = str(ndjson_record.get("body") or "")
    stable_ids = _stable_ids_from_record(ndjson_record) or _extract_legacy_stable_ids_from_ndjson_body(body)
    out: list[dict[str, Any]] = []
    issue_number, issue_url = _issue_evidence_for_record(ndjson_record)
    run_id = run_dir.name
    seen_identities: set[tuple[Any, ...]] = set()
    ambiguous = False
    for stable_id in stable_ids:
        matched, is_ambiguous = _resolve_blocks_for_stable_id(stable_id, blocks, body)
        if is_ambiguous:
            ambiguous = True
            out.append(_ambiguous_stable_id_row(run_id, stable_id, issue_number, issue_url))
            continue
        for block in matched:
            identity = (str(block.get("artifact_relpath") or ""), str(block.get("heading_id") or ""))
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            out.append(_row_from_block(run_id, block, ndjson_record, issue_number, issue_url))
    expected_match = re.search(r"Aggregated rollup of\s+(\d+)\s+capped OOS items", f"{ndjson_record.get('title') or ''}\n{body}", re.I)
    expected = int(expected_match.group(1)) if expected_match else 0
    scored_rows = [row for row in out if not row.get("bucket")]
    if expected and len(scored_rows) > expected:
        return [_ambiguous_rollup_expansion_row(run_id, issue_number, issue_url)]
    if expected and len(scored_rows) < expected:
        excerpt_titles: list[str] = []
        for text in _rollup_excerpt_source_texts(run_dir, ndjson_record):
            excerpt_titles.extend(_rollup_excerpt_titles_from_text(text))
        for block in _blocks_from_rollup_excerpt_titles(excerpt_titles, blocks, seen_identities):
            out.append(_row_from_block(run_id, block, ndjson_record, issue_number, issue_url))
    scored_rows = [row for row in out if not row.get("bucket")]
    if expected and len(scored_rows) < expected and ambiguous:
        return _rollup_expansion_shortfall_result(run_id, issue_number, issue_url, out)
    if expected and len(scored_rows) < expected:
        source_key = ""
        for stable_id in stable_ids:
            if ":" in stable_id:
                source_key = stable_id.rsplit(":", 1)[0]
                break
        candidates = [dict(block) for block in blocks if not block.get("filed_url")]
        if source_key == "oos-accepted-main-agent":
            review_candidates = sorted(
                [dict(block) for block in blocks if not block.get("filed_url") and (
                    "review" in str(block.get("artifact_relpath") or "").lower()
                    or str(block.get("source_key") or "").endswith("-review")
                )],
                key=lambda item: (str(item.get("artifact_relpath") or ""), str(item.get("heading_id") or "")),
            )
            if len(review_candidates) == expected:
                candidates = review_candidates
            else:
                candidates = [
                    block
                    for block in candidates
                    if any(_stable_ids_cover(stable_id, set(block.get("lookup_keys", set())), allow_main_agent_bridge=True) for stable_id in stable_ids)
                ]
        elif source_key:
            candidates = [block for block in candidates if block.get("source_key") == source_key]
        if len(candidates) == expected:
            for block in sorted(candidates, key=lambda item: (str(item.get("artifact_relpath") or ""), str(item.get("heading_id") or ""))):
                identity = (str(block.get("artifact_relpath") or ""), str(block.get("heading_id") or ""))
                if identity in seen_identities:
                    continue
                seen_identities.add(identity)
                out.append(_row_from_block(run_id, block, ndjson_record, issue_number, issue_url))
        else:
            return _rollup_expansion_shortfall_result(run_id, issue_number, issue_url, out)
    scored_rows = [row for row in out if not row.get("bucket")]
    if expected and len(scored_rows) < expected:
        return _rollup_expansion_shortfall_result(run_id, issue_number, issue_url, out)
    if ambiguous and not scored_rows:
        if out:
            return out
        return [_ambiguous_stable_id_row(run_id, stable_ids[0] if stable_ids else "", issue_number, issue_url)]
    return out


def _parse_oos_issues_created(path: Path, *, accepted_design_path: Path | None) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    run_dir = path.parent
    text = path.read_text(encoding="utf-8", errors="replace")
    accepted_blocks = _parse_oos_accepted_blocks(accepted_design_path, run_dir=run_dir) if accepted_design_path else []
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0] == "OOS_FILE_MAP" and parts[1].isdigit():
            heading = f"OOS_{parts[1]}"
            url = parts[2].strip()
            number = extract_issue_number_from_url(url)
            blocks_for_heading = [block for block in accepted_blocks if str(block.get("heading_id") or "") == heading]
            if len(blocks_for_heading) > 1:
                records.append({
                    "bucket": "ambiguous stable id",
                    "run_id": run_dir.name,
                    "identity": (run_dir.name, "design-map", heading, number or url),
                    "issue_number": number,
                    "issue_url": url,
                    "reviewer": "unknown",
                    "title": heading,
                })
                continue
            block = blocks_for_heading[0] if blocks_for_heading else {}
            records.append({
                "run_id": run_dir.name,
                "identity": (run_dir.name, str(block.get("artifact_relpath") or accepted_design_path.name if accepted_design_path else "oos-accepted-design.md"), heading),
                "stable_id": block.get("canonical_stable_id") or heading,
                "issue_number": number,
                "issue_url": block.get("filed_url") or url,
                "reviewer": block.get("reviewer") or "unknown",
                "title": block.get("title") or heading,
            })
    for block in accepted_blocks:
        url = str(block.get("filed_url") or "")
        if not url:
            continue
        heading = str(block.get("heading_id") or "")
        if any(row.get("stable_id") == block.get("canonical_stable_id") for row in records):
            continue
        records.append({
            "run_id": run_dir.name,
            "identity": (run_dir.name, block.get("artifact_relpath") or "", heading),
            "stable_id": block.get("canonical_stable_id") or heading,
            "issue_number": extract_issue_number_from_url(url),
            "issue_url": url,
            "reviewer": block.get("reviewer") or "unknown",
            "title": block.get("title") or heading,
        })
    if not records:
        for number in _extract_filed_issue_numbers_from_text(text):
            issue_url = ""
            for match in _FILED_URL_LINE_RE.finditer(text):
                url = match.group(1)
                if extract_issue_number_from_url(url) == number:
                    issue_url = url
                    break
            if not issue_url:
                for match in _FILED_OOS_URL_RE.finditer(text):
                    url = match.group(1)
                    if extract_issue_number_from_url(url) == number:
                        issue_url = url
                        break
            if not issue_url:
                for line in text.splitlines():
                    if not line.lstrip().startswith("|"):
                        continue
                    for url_match in _GITHUB_ISSUE_URL_RE.finditer(line):
                        if int(url_match.group(1)) == number:
                            issue_url = url_match.group(0)
                            break
                    if issue_url:
                        break
            records.append({
                "run_id": run_dir.name,
                "identity": (run_dir.name, "created", issue_url or number),
                "issue_number": number,
                "issue_url": issue_url,
                "reviewer": "unknown",
                "title": "Recovered OOS disposition",
            })
    return records


def _parse_oos_issues_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(dict(parsed))
    return records


def _join_implement_run_records(run_dir: Path) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("**/oos-accepted-*.md")):
        blocks.extend(_parse_oos_accepted_blocks(path, run_dir=run_dir))
    indexed = _index_accepted_blocks_by_stable_id(blocks)
    rows: list[dict[str, Any]] = []
    for record in _parse_oos_issues_ndjson(run_dir / "oos-issues.ndjson"):
        issue_number, issue_url = _issue_evidence_for_record(record)
        if _is_cap_rollup_record(record):
            expanded = _expand_cap_rollup_records(run_dir, record, blocks, indexed)
            if expanded:
                rows.extend(expanded)
                continue
        stable_ids = _stable_ids_from_record(record) or _extract_legacy_stable_ids_from_ndjson_body(str(record.get("body") or ""))
        matched_any = False
        ambiguous = False
        for stable_id in stable_ids:
            matched, is_ambiguous = _resolve_blocks_for_stable_id(stable_id, blocks, str(record.get("body") or ""))
            ambiguous = ambiguous or is_ambiguous
            for block in matched:
                matched_any = True
                rows.append(_row_from_block(run_dir.name, block, record, issue_number, issue_url))
        if ambiguous and not matched_any:
            rows.append({"bucket": "ambiguous stable id", "run_id": run_dir.name, "issue_number": issue_number, "issue_url": issue_url, "reviewer": "unknown"})
        elif not matched_any and (issue_number or issue_url):
            reviewer = "Main agent" if any(str(stable_id).startswith("oos-accepted-main-agent:") for stable_id in stable_ids) else "unknown"
            identity = (run_dir.name, tuple(stable_ids) or issue_url or issue_number)
            rows.append({"run_id": run_dir.name, "identity": identity, "stable_id": stable_ids[0] if stable_ids else "", "issue_number": issue_number, "issue_url": issue_url, "reviewer": reviewer, "title": record.get("title") or "Recovered OOS disposition"})
    return rows


def _fetch_filed_oos_issue_details(repo: str, issue_numbers: set[int]) -> dict[int, dict[str, Any]]:
    details: dict[int, dict[str, Any]] = {}
    fields = "number,title,body,state,url,closedAt,stateReason,labels,closedByPullRequestsReferences,comments"
    for number in sorted(issue_numbers):
        result = subprocess.run(
            ["gh", "issue", "view", str(number), "--repo", repo, "--json", fields],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            details[number] = {"number": number, "__fetch_failed__": True, "__fetch_error__": (result.stderr or result.stdout or "gh issue view failed")[:500]}
            continue
        try:
            parsed = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            details[number] = {"number": number, "__fetch_failed__": True, "__fetch_error__": "invalid gh issue view JSON"}
            continue
        if isinstance(parsed, dict):
            parsed["__targeted_fetch_ok__"] = True
            details[int(parsed.get("number") or number)] = parsed
    return details


def _load_filed_issue_details_json(path: Path | None) -> dict[int, dict[str, Any]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR=--filed-issue-details-json must contain an object: {path}")
    out: dict[int, dict[str, Any]] = {}
    for raw_key, raw_value in data.items():
        parsed, reason = _parse_issue_number(raw_key)
        if parsed is None:
            raise SystemExit(f"ERROR=invalid filed issue details key {raw_key!r}: {reason}")
        if isinstance(raw_value, dict):
            out[parsed] = dict(raw_value)
    return out


def _append_design_accepted_block_records(
    records: list[dict[str, Any]],
    run_dir: Path,
    *,
    seen_identities: set[tuple[Any, ...]],
) -> None:
    for path in sorted(run_dir.glob("**/oos-accepted-*.md")):
        for block in _parse_oos_accepted_blocks(path, run_dir=run_dir):
            url = str(block.get("filed_url") or "")
            if not url:
                continue
            identity = (run_dir.name, block.get("artifact_relpath"), block.get("heading_id"))
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            records.append({
                "run_id": run_dir.name,
                "identity": identity,
                "stable_id": block.get("canonical_stable_id"),
                "issue_number": extract_issue_number_from_url(url),
                "issue_url": url,
                "reviewer": block.get("reviewer") or "unknown",
                "title": block.get("title") or "",
            })


def iter_filed_oos_records(log_root: Path) -> list[dict[str, Any]]:
    if not log_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for run_dir in sorted((log_root / "implement").glob("*")) if (log_root / "implement").is_dir() else []:
        if run_dir.is_dir():
            records.extend(_join_implement_run_records(run_dir))
    for run_dir in sorted((log_root / "design").glob("*")) if (log_root / "design").is_dir() else []:
        if not run_dir.is_dir():
            continue
        accepted = run_dir / "oos-accepted-design.md"
        created_records = _parse_oos_issues_created(
            run_dir / "oos-issues-created.md",
            accepted_design_path=accepted if accepted.is_file() else None,
        )
        records.extend(created_records)
        seen_identities = {tuple(record.get("identity") or ()) for record in created_records}
        _append_design_accepted_block_records(records, run_dir, seen_identities=seen_identities)
    return records


def _merged_issue_index(issues: Sequence[Mapping[str, Any]], filed_issue_details: Mapping[int, Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    index = {issue_number(issue): dict(issue) for issue in issues}
    for number, detail in filed_issue_details.items():
        current = index.get(int(number), {})
        merged = {**current, **dict(detail)}
        if detail.get("__fetch_failed__") and current:
            merged["__fetch_failed__"] = True
        degraded = merged.get("_larch_degraded_fields") or []
        if isinstance(degraded, list) and detail.get("stateReason") and "stateReason" in degraded:
            merged["_larch_degraded_fields"] = [field for field in degraded if field != "stateReason"]
        index[int(number)] = merged
    return index


def fate_adjusted_oos_scoring(
    issues: Sequence[Mapping[str, Any]],
    log_root: Path,
    *,
    filed_issue_details: dict[int, dict[str, Any]],
    repo: str | None = None,
    enrichment_degraded: str | None = None,
) -> tuple[str, dict[str, Any]]:
    records = iter_filed_oos_records(log_root)
    lines = ["## Fate-adjusted OOS Scoring"]
    if enrichment_degraded:
        lines.append(
            f"- Note: GitHub issue enrichment unavailable ({enrichment_degraded}); "
            "filed OOS fate uses partial or offline data."
        )
    if not records:
        lines.append("No filed OOS run-log evidence found.")
        return "\n".join(lines), {"records": 0}
    index = _merged_issue_index(issues, filed_issue_details)
    reviewer_totals: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"provisional": 0, "adjusted": 0, "docked": 0})
    buckets: collections.Counter[str] = collections.Counter()
    seen: set[tuple[Any, str]] = set()
    seen_items: set[Any] = set()
    totals = {"provisional": 0, "adjusted": 0, "docked": 0}
    for record in records:
        explicit_bucket = str(record.get("bucket") or "")
        if explicit_bucket in {"ambiguous stable id", "ambiguous rollup expansion"}:
            identity = record.get("identity") or (record.get("run_id"), explicit_bucket, record.get("issue_number") or record.get("issue_url"))
            if identity not in seen_items:
                seen_items.add(identity)
                buckets[explicit_bucket] += 1
            continue
        number = record.get("issue_number")
        parsed_number, _reason = _parse_issue_number(number)
        issue_url = str(record.get("issue_url") or "")
        if parsed_number is None and issue_url:
            parsed_number = extract_issue_number_from_url(issue_url)
        identity = record.get("identity") or (record.get("run_id"), record.get("stable_id") or parsed_number or issue_url)
        if repo and issue_url:
            url_repo = extract_repo_from_url(issue_url)
            if url_repo and url_repo.lower() != repo.lower():
                if identity not in seen_items:
                    seen_items.add(identity)
                    buckets["skipped missing issue"] += 1
                continue
        if parsed_number is None:
            if identity not in seen_items:
                seen_items.add(identity)
                buckets["skipped missing issue"] += 1
            continue
        issue = index.get(parsed_number)
        if issue is None and enrichment_degraded and parsed_number is not None:
            fate = {
                "bucket": "enrichment unavailable",
                "adjusted": 1,
                "provisional": 1,
                "docked": False,
                "unknown": True,
            }
        else:
            fate = classify_oos_issue_fate(issue)
        if identity not in seen_items:
            seen_items.add(identity)
            if issue and issue.get("__fetch_failed__"):
                buckets["degraded comment fetch"] += 1
            buckets[str(fate["bucket"])] += 1
        if str(fate.get("bucket") or "") == "skipped missing issue":
            continue
        if not issue and not enrichment_degraded:
            continue
        for reviewer in _reviewers_from_label(str(record.get("reviewer") or "unknown")):
            key = (identity, reviewer)
            if key in seen:
                continue
            seen.add(key)
            provisional = int(fate["provisional"]) if "provisional" in fate else 1
            adjusted = int(fate.get("adjusted") or 0)
            docked = 1 if fate.get("docked") else 0
            reviewer_totals[reviewer]["provisional"] += provisional
            reviewer_totals[reviewer]["adjusted"] += adjusted
            reviewer_totals[reviewer]["docked"] += docked
            totals["provisional"] += provisional
            totals["adjusted"] += adjusted
            totals["docked"] += docked
    lines.append(f"- Overall provisional points: {totals['provisional']}")
    lines.append(f"- Overall fate-adjusted points: {totals['adjusted']}")
    lines.append(f"- Overall docked count: {totals['docked']}")
    lines.append("Reviewer rows:")
    if reviewer_totals:
        for reviewer, row in sorted(reviewer_totals.items(), key=lambda item: (-item[1]["adjusted"], item[0].lower())):
            lines.append(f"- {reviewer}: provisional {row['provisional']}, adjusted {row['adjusted']}, docked {row['docked']}")
    else:
        lines.append("- No reviewer-attributed filed OOS rows detected.")
    lines.append("Fate buckets:")
    bucket_order = [
        "kept by PR",
        "provisional open",
        "provisional unknown",
        "docked closed-unfixed",
        "docked combined-away",
        "skipped missing issue",
        "ambiguous stable id",
        "ambiguous rollup expansion",
        "degraded comment fetch",
        "enrichment unavailable",
    ]
    for bucket in bucket_order:
        lines.append(f"- {bucket}: {buckets.get(bucket, 0)}")
    return "\n".join(lines), {"totals": totals, "reviewers": reviewer_totals, "buckets": buckets, "records": len(records)}


@dataclass(frozen=True)
class GroundTruthVoter:
    voter: str
    vote: str
    missing: int


@dataclass
class GroundTruthRow:
    panel_kind: str
    path: Path
    run_dir: Path
    run_id: str
    round_num: int
    started_at: datetime | None
    raw_row: dict[str, str]
    header: list[str]
    reviewer_column: str
    voter_votes: list[tuple[str, str]]
    voters: list[GroundTruthVoter]
    is_oos: bool
    panel_verdict: str = ""
    oos_panel_verdict: str = ""
    weak_reason: str = ""
    prose_text: str = ""
    title: str = ""
    category: str = ""
    issue_number: int | None = None
    issue_url: str = ""

    @property
    def finding_id(self) -> str:
        return (self.raw_row.get("finding_id") or "").strip()


@dataclass
class GroundTruthOutcome:
    row: GroundTruthRow
    bucket: str
    decisive: bool
    direction: str
    reason: str


@dataclass
class GroundTruthMetric:
    panel: str
    voter: str
    decisive: int = 0
    aligned: int = 0
    misaligned: int = 0
    missing: int = 0
    false_positive_yes: int = 0
    false_negative_no: int = 0


@dataclass
class GroundTruthStats:
    files_seen: int = 0
    skipped_files: int = 0
    scanned_rows: int = 0
    eligible_rows: int = 0
    ineligible_rows: int = 0
    prose_rows: int = 0
    gc_slimmed_runs: int = 0
    weak_rows: int = 0
    decisive_rows: int = 0
    timestamp_degraded: int = 0
    verdict_disagreement: int = 0
    rejected_oos_panel: int = 0
    enrichment_degraded_rows: int = 0
    large_corpus_skip: bool = False
    buckets: collections.Counter[str] = field(default_factory=collections.Counter)


_GROUND_TRUTH_ROW_CACHE: dict[str, tuple[list[GroundTruthRow], GroundTruthStats]] = {}
_GROUND_TRUTH_FILED_CACHE: dict[str, list[dict[str, Any]]] = {}


def _copy_ground_truth_stats(stats: GroundTruthStats) -> GroundTruthStats:
    copied = GroundTruthStats(
        files_seen=stats.files_seen,
        skipped_files=stats.skipped_files,
        scanned_rows=stats.scanned_rows,
        eligible_rows=stats.eligible_rows,
        ineligible_rows=stats.ineligible_rows,
        prose_rows=stats.prose_rows,
        gc_slimmed_runs=stats.gc_slimmed_runs,
        weak_rows=stats.weak_rows,
        decisive_rows=stats.decisive_rows,
        timestamp_degraded=stats.timestamp_degraded,
        verdict_disagreement=stats.verdict_disagreement,
        rejected_oos_panel=stats.rejected_oos_panel,
        enrichment_degraded_rows=stats.enrichment_degraded_rows,
        large_corpus_skip=stats.large_corpus_skip,
    )
    copied.buckets = collections.Counter(stats.buckets)
    return copied


@dataclass(frozen=True)
class GroundTruthEvidence:
    source: str
    run_id: str
    round_num: int
    started_at: datetime | None
    created_at: datetime | None
    title: str
    text: str
    category: str
    issue_number: int | None = None
    not_planned: bool = False


_GT_HEADING_RE = re.compile(r"^###\s+((?:FINDING|OOS)_\d+):\s*(.*?)\s*$", re.M)
_GT_VOTE_TALLY_RESULT_RE = re.compile(r"\bResult\s*:\s*(accepted|rejected)\b", re.I)
_GT_REVERSAL_RE = re.compile(
    r"\b(revert|reverted|undo|regress|regression|superseded|re-introduce|re-add|closed in favor of)\b",
    re.I,
)


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _ground_truth_discover_classifiers(log_root: Path) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    for path in sorted(log_root.glob("design/*/plan-review/round-*/findings-classification.tsv")):
        paths.append(("design", path))
    for path in sorted(log_root.glob("implement/*/round-*/findings-classification.tsv")):
        paths.append(("code-review", path))
    for path in sorted(log_root.glob("review/*/review-findings-classification-round-*.tsv")):
        text = _safe_read_text(path)
        if voting.classification_tsv_schema_supported(text, panel_kind="code-review"):
            paths.append(("code-review", path))
    return paths


def _ground_truth_run_dir(path: Path, *, panel_kind: str) -> Path:
    parts = list(path.parts)
    if panel_kind == "design" and "plan-review" in parts:
        return path.parents[2]
    if "round-" in path.parent.name:
        return path.parents[1]
    return path.parent


def _ground_truth_round_num(path: Path) -> int:
    for part in reversed(path.parts):
        match = re.fullmatch(r"round-(\d+)", part)
        if match:
            return int(match.group(1))
    match = re.search(r"round-(\d+)", path.name)
    return int(match.group(1)) if match else 0


def _ground_truth_run_started_at(run_dir: Path) -> datetime | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            return parse_iso(str(data.get("started_at") or data.get("updated_at") or ""))
    return None


def _ground_truth_run_ended_at(run_dir: Path) -> datetime | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            ended = parse_iso(str(data.get("ended_at") or data.get("completed_at") or ""))
            if ended:
                return ended
            return parse_iso(str(data.get("updated_at") or ""))
    return None


def _run_has_round_local_jsonl(run_dir: Path) -> bool:
    return bool(
        list(run_dir.glob("round-*/review-findings-full.jsonl"))
        or list(run_dir.glob("plan-review/round-*/review-findings-full.jsonl"))
    )


def _markdown_blocks_by_heading(text: str) -> dict[str, tuple[str, str]]:
    matches = list(_GT_HEADING_RE.finditer(text or ""))
    blocks: dict[str, tuple[str, str]] = {}
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks[match.group(1)] = (match.group(2).strip(), text[start:end].strip())
    return blocks


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in _safe_read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(dict(parsed))
    return records


@functools.lru_cache(maxsize=2048)
def _cached_jsonl_records(path: Path) -> tuple[tuple[tuple[str, Any], ...], ...]:
    return tuple(tuple(record.items()) for record in _jsonl_records(path))


def _cached_jsonl_record_dicts(path: Path) -> list[dict[str, Any]]:
    return [dict(items) for items in _cached_jsonl_records(path)]


@functools.lru_cache(maxsize=512)
def _implement_prose_paths(run_dir: Path) -> tuple[Path, ...]:
    return tuple(sorted(run_dir.glob("review-findings-full.jsonl")) + sorted(run_dir.glob("round-*/review-findings-full.jsonl")))


@functools.lru_cache(maxsize=4096)
def _cached_markdown_blocks(path: Path) -> tuple[tuple[str, str, str], ...]:
    blocks = _markdown_blocks_by_heading(_safe_read_text(path))
    return tuple((key, title, body) for key, (title, body) in blocks.items())


def _cached_markdown_block_dict(path: Path) -> dict[str, tuple[str, str]]:
    return {key: (title, body) for key, title, body in _cached_markdown_blocks(path)}


def _row_finding_tokens(row: GroundTruthRow) -> set[str]:
    tokens = {row.finding_id}
    raw = row.finding_id
    if raw.startswith("FINDING_"):
        tokens.add(raw.replace("FINDING_", "REJ_CR", 1))
    if raw.startswith("OOS_"):
        tokens.add(raw)
    return {token for token in tokens if token}


_GT_FINDING_ID_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _gt_finding_id_pattern(finding_id: str) -> re.Pattern[str]:
    if finding_id not in _GT_FINDING_ID_RE_CACHE:
        _GT_FINDING_ID_RE_CACHE[finding_id] = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(finding_id) + r"(?![A-Za-z0-9_])")
    return _GT_FINDING_ID_RE_CACHE[finding_id]


def _jsonl_record_round_num(record: Mapping[str, Any]) -> int:
    try:
        return int(record.get("round_num") or 0)
    except (TypeError, ValueError):
        return 0


def _jsonl_record_round_matches_row(
    record: Mapping[str, Any],
    *,
    row: GroundTruthRow,
    path_round: int = 0,
    require_explicit_round: bool = False,
    multi_round: bool = False,
) -> bool:
    rec_round = _jsonl_record_round_num(record)
    if require_explicit_round and row.round_num and rec_round != row.round_num:
        return False
    if rec_round and row.round_num and rec_round != row.round_num:
        return False
    if path_round and not rec_round and row.round_num and path_round != row.round_num:
        return False
    return not (multi_round and row.round_num and not rec_round and path_round == 0)


def _jsonl_record_matches_row(
    record: Mapping[str, Any],
    *,
    row: GroundTruthRow,
    path_round: int = 0,
    require_explicit_round: bool = False,
) -> bool:
    if not _jsonl_record_round_matches_row(
        record,
        row=row,
        path_round=path_round,
        require_explicit_round=require_explicit_round,
        multi_round=_run_has_multiple_rounds(row.run_dir),
    ):
        return False
    pattern = _gt_finding_id_pattern(row.finding_id) if row.finding_id else None
    body = str(record.get("prose_body") or record.get("body") or "")
    rec_id = str(record.get("id") or "")
    title = str(record.get("title") or "")
    haystack = f"{rec_id}\n{title}\n{body}"
    return rec_id == row.finding_id or (pattern is not None and bool(pattern.search(haystack)))


def _design_jsonl_verdict_for_row(row: GroundTruthRow) -> str:
    outcomes: list[str] = []
    for record in _cached_jsonl_record_dicts(row.run_dir / "review-findings-full.jsonl"):
        if not _jsonl_record_matches_row(record, row=row):
            continue
        outcome = str(record.get("outcome") or "").strip().lower()
        if outcome in {"accepted", "rejected"}:
            outcomes.append(outcome)
    if not outcomes:
        return ""
    if len(set(outcomes)) == 1:
        return outcomes[0]
    return "ambiguous"


def _run_has_multiple_rounds(run_dir: Path) -> bool:
    implement_rounds = sum(1 for path in run_dir.glob("round-*") if path.is_dir())
    design_rounds = sum(1 for path in run_dir.glob("plan-review/round-*") if path.is_dir())
    return implement_rounds > 1 or design_rounds > 1


def _filed_record_round_num(record: Mapping[str, Any]) -> int:
    identity = record.get("identity")
    if isinstance(identity, tuple) and len(identity) >= 2:
        return _ground_truth_round_num(Path(str(identity[1])))
    artifact = str(record.get("artifact_relpath") or "")
    if artifact:
        return _ground_truth_round_num(Path(artifact))
    return 0


def _row_reviewer_tokens(row: GroundTruthRow) -> set[str]:
    raw = (row.raw_row.get(row.reviewer_column) or row.raw_row.get("finding_reviewers") or "").strip()
    if not raw:
        return set()
    return {token.lower() for token in _reviewers_from_label(raw)}


def _filed_record_reviewer_matches(record: Mapping[str, Any], *, row_tokens: set[str]) -> bool:
    if not row_tokens:
        return True
    rec_reviewer = str(record.get("reviewer") or "unknown").strip().lower()
    if rec_reviewer == "unknown":
        return False
    return rec_reviewer in row_tokens or any(token in rec_reviewer or rec_reviewer in token for token in row_tokens)


def _implement_prose_for_row(row: GroundTruthRow) -> dict[str, str]:
    candidates: list[dict[str, str]] = []
    pattern = _gt_finding_id_pattern(row.finding_id) if row.finding_id else None
    tokens = _row_finding_tokens(row)
    multi_round = _run_has_multiple_rounds(row.run_dir)
    require_explicit_round = row.round_num > 0 and row.path.name.startswith("review-findings-classification-round-")
    for path in _implement_prose_paths(row.run_dir):
        path_round = _ground_truth_round_num(path)
        if multi_round and row.round_num and path_round == 0 and _run_has_round_local_jsonl(row.run_dir):
            continue
        for record in _cached_jsonl_record_dicts(path):
            if not _jsonl_record_round_matches_row(
                record,
                row=row,
                path_round=path_round,
                require_explicit_round=require_explicit_round,
                multi_round=multi_round,
            ):
                continue
            body = str(record.get("prose_body") or record.get("body") or "")
            rec_id = str(record.get("id") or "")
            title = str(record.get("title") or "")
            haystack = f"{rec_id}\n{title}\n{body}"
            # F13: use word-boundary / exact matching instead of bare substring containment
            exact_match = rec_id == row.finding_id or (pattern is not None and pattern.search(haystack))
            token_match = any(_gt_finding_id_pattern(t).search(haystack) for t in tokens if t != row.finding_id)
            if exact_match or token_match:
                candidates.append({
                    "outcome": str(record.get("outcome") or ""),
                    "category": str(record.get("category") or ""),
                    "text": body or title,
                    "title": title,
                })
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        same_outcome = {item["outcome"] for item in candidates}
        if len(same_outcome) == 1:
            return candidates[0]
        return {"weak": "cross-round or multi-match ambiguity"}
    return {}


def _standalone_review_prose_for_row(row: GroundTruthRow) -> dict[str, str]:
    candidates: list[dict[str, str]] = []
    path_round = row.round_num or _ground_truth_round_num(row.path)
    require_explicit_round = row.round_num > 0 and row.path.name.startswith("review-findings-classification-round-")
    for name in ("review-findings.ndjson", "review-findings-full.jsonl"):
        record_path = row.path.with_name(name)
        for record in _cached_jsonl_record_dicts(record_path):
            if not _jsonl_record_matches_row(record, row=row, path_round=path_round, require_explicit_round=require_explicit_round):
                continue
            body = str(record.get("prose_body") or record.get("body") or "")
            candidates.append({
                "outcome": str(record.get("outcome") or ""),
                "category": str(record.get("category") or ""),
                "text": body or str(record.get("title") or ""),
                "title": str(record.get("title") or ""),
            })
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        same_outcome = {item["outcome"] for item in candidates}
        if len(same_outcome) == 1:
            return candidates[0]
        return {"weak": "cross-round or multi-match ambiguity"}
    return {}


def _design_markdown_verdict(row: GroundTruthRow) -> dict[str, str]:
    round_dir = row.path.parent
    local_accepted = _cached_markdown_block_dict(round_dir / "accepted-plan-findings.md")
    local_rejected = _cached_markdown_block_dict(round_dir / "rejected-findings.md")
    root_accepted = _cached_markdown_block_dict(row.run_dir / "accepted-plan-findings.md")
    root_rejected = _cached_markdown_block_dict(row.run_dir / "rejected-findings.md")

    def verdict_from(*, accepted: Mapping[str, tuple[str, str]], rejected: Mapping[str, tuple[str, str]]) -> tuple[str, str, str]:
        in_accepted = row.finding_id in accepted
        in_rejected = row.finding_id in rejected
        if in_accepted == in_rejected:
            return "", "", ""
        title, text = accepted[row.finding_id] if in_accepted else rejected[row.finding_id]
        return ("accepted" if in_accepted else "rejected", title, text)

    local = verdict_from(accepted=local_accepted, rejected=local_rejected)
    root = verdict_from(accepted=root_accepted, rejected=root_rejected)
    local_files_exist = (round_dir / "accepted-plan-findings.md").is_file() or (round_dir / "rejected-findings.md").is_file()

    def bind_markdown_verdict(*, outcome: str, title: str, text: str) -> dict[str, str]:
        jsonl_outcome = _design_jsonl_verdict_for_row(row)
        if jsonl_outcome == "ambiguous":
            return {"weak": "design JSONL multi-match ambiguity"}
        if jsonl_outcome and outcome and jsonl_outcome != outcome:
            return {"weak": "design markdown/JSONL verdict disagreement"}
        return {"outcome": outcome, "title": title, "text": text}

    if local[0]:
        if root[0] and root[0] != local[0]:
            return {"weak": "design round-local/run-root verdict disagreement"}
        return bind_markdown_verdict(outcome=local[0], title=local[1], text=local[2])
    if local_files_exist:
        # F12: round-local files exist but finding absent — don't fall back to run-root
        return {"weak": "round-local verdict files present but finding absent"}
    if root[0]:
        return bind_markdown_verdict(outcome=root[0], title=root[1], text=root[2])
    for record in _cached_jsonl_record_dicts(row.run_dir / "review-findings-full.jsonl"):
        if not _jsonl_record_matches_row(record, row=row):
            continue
        body = str(record.get("prose_body") or record.get("body") or "")
        return {
            "outcome": str(record.get("outcome") or ""),
            "category": str(record.get("category") or ""),
            "title": str(record.get("title") or ""),
            "text": body,
        }
    return {}


def _bind_ground_truth_prose(row: GroundTruthRow) -> None:
    prose = _design_markdown_verdict(row) if row.panel_kind == "design" else _implement_prose_for_row(row)
    if not prose and row.path.name.startswith("review-findings-classification-round-"):
        prose = _standalone_review_prose_for_row(row)
    outcome = str(prose.get("outcome") or "").strip().lower()
    row.prose_text = str(prose.get("text") or "")
    row.title = str(prose.get("title") or "") or row.finding_id
    row.category = str(prose.get("category") or "")
    if row.prose_text:
        row.prose_text = row.prose_text[:BODY_CAP]
    if row.is_oos:
        row.oos_panel_verdict = _ground_truth_oos_panel_verdict(row)
    if prose.get("weak") and not (row.is_oos and row.oos_panel_verdict in {"accepted", "rejected"}):
        row.weak_reason = str(prose["weak"])
        return
    if row.is_oos:
        pass
    elif outcome in {"accepted", "rejected"}:
        row.panel_verdict = outcome
        tsv_result = (row.raw_row.get("voting_result") or "").strip().lower()
        if tsv_result in {"accepted", "rejected"} and tsv_result != outcome:
            row.weak_reason = "TSV/prose verdict disagreement"
    elif outcome == "out_of_scope":
        row.weak_reason = "out-of-scope prose is not an in-scope verdict"
    if row.prose_text or row.panel_verdict or row.oos_panel_verdict:
        return
    row.weak_reason = "missing prose verdict"


def _parse_voting_tally_row_result(tally_text: str, *, finding_id: str) -> str:
    if not tally_text or not finding_id:
        return ""
    for line in tally_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [part.strip() for part in stripped.strip("|").split("|")]
        if not parts or parts[0] != finding_id:
            continue
        for part in reversed(parts[1:]):
            lowered = part.lower()
            if lowered in {"accepted", "rejected"}:
                return lowered
    return ""


def _ground_truth_oos_panel_verdict(row: GroundTruthRow) -> str:
    result = (row.raw_row.get("voting_result") or "").strip().lower()
    tally_result = _parse_voting_tally_row_result(_safe_read_text(row.path.with_name("voting-tally.md")), finding_id=row.finding_id)
    if not tally_result:
        tally_text = _safe_read_text(row.path.with_name("vote-tally.md"))
        tally_match = _GT_VOTE_TALLY_RESULT_RE.search(tally_text)
        tally_result = tally_match.group(1).lower() if tally_match else ""
    if result in {"accepted", "rejected"} and tally_result in {"accepted", "rejected"}:
        if result != tally_result:
            return ""  # TSV/tally disagreement → non-decisive (F18)
        return result
    if result in {"accepted", "rejected"}:
        return result
    if tally_result in {"accepted", "rejected"}:
        return tally_result
    prose_tally_match = _GT_VOTE_TALLY_RESULT_RE.search(row.prose_text)
    return prose_tally_match.group(1).lower() if prose_tally_match else ""


def _normalize_diagnostic_path(raw: str) -> str:
    value = (raw or "").strip("`*_#[](){}<>.,;:'\"")
    value = re.sub(r":\d+(?:-\d+)?$", "", value)
    value = value.lstrip("./").lower()
    if not value or ".." in value.split("/") or value.startswith(("/", "~")):
        return ""
    return value


@functools.lru_cache(maxsize=65536)
def _diagnostic_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for regex in (voting.FILE_LINE_REGEXES["any-re"], voting.FILE_LINE_REGEXES["extensionless-re"]):
        for match in re.finditer(regex, text or "", re.I):
            candidate = ""
            groups = [group for group in match.groups() if group]
            if groups:
                candidate = groups[0] if "/" in groups[0] or "." in groups[0] else match.group(0)
            candidate = _normalize_diagnostic_path(candidate or match.group(0))
            if candidate:
                paths.add(candidate)
    return paths


@functools.lru_cache(maxsize=65536)
def _distinctive_tokens(text: str) -> set[str]:
    return set(title_tokens(text))


def _strong_ground_truth_match(row: GroundTruthRow, *, evidence: GroundTruthEvidence) -> bool:
    source_text = f"{row.title}\n{row.prose_text}\n{row.finding_id}"
    source_paths = _diagnostic_paths(source_text)
    evidence_paths = _diagnostic_paths(f"{evidence.title}\n{evidence.text}")
    source_tokens = _distinctive_tokens(source_text)
    evidence_tokens = _distinctive_tokens(f"{evidence.title}\n{evidence.text}")
    overlap = source_tokens & evidence_tokens
    if source_paths & evidence_paths and len(overlap) >= 2:
        return True
    if min(len(source_tokens), len(evidence_tokens)) <= 4:
        return len(overlap) >= max(2, min(len(source_tokens), len(evidence_tokens)))
    return len(overlap) >= max(3, int(min(len(source_tokens), len(evidence_tokens)) * 0.6))


def _evidence_later_than_row(row: GroundTruthRow, *, evidence: GroundTruthEvidence) -> tuple[bool, str]:
    if evidence.run_id and evidence.run_id == row.run_id:
        if evidence.round_num > row.round_num:
            return True, ""
        return False, "same-run round ordering is not later"
    if evidence.source == "issue" and not evidence.run_id:
        if row.started_at and evidence.created_at:
            if evidence.created_at <= row.started_at:
                return False, "not later"
            if _run_has_multiple_rounds(row.run_dir):
                run_ended = _ground_truth_run_ended_at(row.run_dir)
                if run_ended and evidence.created_at > run_ended:
                    return True, ""
                return False, "same-run round ordering unproved"
            return True, ""
        return False, "timestamp-degraded"
    if row.started_at and evidence.started_at:
        return (evidence.started_at > row.started_at), "" if evidence.started_at > row.started_at else "not later"
    if row.started_at and evidence.created_at:
        return (evidence.created_at > row.started_at), "" if evidence.created_at > row.started_at else "not later"
    return False, "timestamp-degraded"


def _ground_truth_issue_evidence(issues: Sequence[Mapping[str, Any]]) -> list[GroundTruthEvidence]:
    evidence: list[GroundTruthEvidence] = []
    for issue in issues:
        title = str(issue.get("title") or "")
        text = issue_text(issue)
        evidence.append(
            GroundTruthEvidence(
                source="issue",
                run_id="",
                round_num=0,
                started_at=None,
                created_at=parse_iso(str(issue.get("createdAt") or "")),
                title=title,
                text=text,
                category=default_category(issue),
                issue_number=issue_number(issue),
                not_planned=_has_not_planned_signal(issue),  # F3
            )
        )
    return evidence


def _ground_truth_accepted_finding_evidence(rows: Sequence[GroundTruthRow]) -> list[GroundTruthEvidence]:
    out: list[GroundTruthEvidence] = []
    for row in rows:
        if row.is_oos or row.panel_verdict != "accepted" or row.weak_reason:
            continue
        out.append(
            GroundTruthEvidence(
                source="accepted-finding",
                run_id=row.run_id,
                round_num=row.round_num,
                started_at=row.started_at,
                created_at=None,
                title=row.title or row.finding_id,
                text=row.prose_text,
                category=row.category,
            )
        )
    return out


def _ground_truth_evidence_token_index(evidence: Sequence[GroundTruthEvidence]) -> dict[str, list[GroundTruthEvidence]]:
    index: dict[str, list[GroundTruthEvidence]] = collections.defaultdict(list)
    for item in evidence:
        for token in _distinctive_tokens(f"{item.title}\n{item.text}"):
            index[token].append(item)
    return dict(index)


def _candidate_evidence_for_row(
    row: GroundTruthRow,
    *,
    issue_evidence: Sequence[GroundTruthEvidence],
    accepted_evidence: Sequence[GroundTruthEvidence],
    accepted_index: Mapping[str, Sequence[GroundTruthEvidence]],
) -> list[GroundTruthEvidence]:
    source_tokens = _distinctive_tokens(f"{row.title}\n{row.prose_text}\n{row.finding_id}")
    source_paths = _diagnostic_paths(f"{row.title}\n{row.prose_text}")
    # F14: filter issue evidence by token overlap before cap rather than taking all unfiltered
    filtered_issues: list[tuple[int, GroundTruthEvidence]] = []
    for item in issue_evidence:
        item_tokens = _distinctive_tokens(f"{item.title}\n{item.text}")
        overlap = len(source_tokens & item_tokens)
        if overlap == 0:
            item_paths = _diagnostic_paths(f"{item.title}\n{item.text}")
            if not (source_paths & item_paths):
                continue
        filtered_issues.append((overlap, item))
    filtered_issues.sort(key=lambda t: t[0], reverse=True)
    if row.panel_verdict == "rejected":
        accepted_candidates: list[GroundTruthEvidence] = []
        seen: set[tuple[str, str, int]] = set()
        for token in source_tokens:
            for item in accepted_index.get(token, ()):
                key = (item.run_id, item.title, item.round_num)
                if key in seen:
                    continue
                seen.add(key)
                accepted_candidates.append(item)
        issue_candidates = [item for _, item in filtered_issues]
        return accepted_candidates + issue_candidates
    candidates: list[GroundTruthEvidence] = [item for _, item in filtered_issues]
    if len(accepted_evidence) < 50:
        candidates.extend(accepted_evidence)
    return candidates


def _ground_truth_row_title_from_oos_record(record: Mapping[str, Any]) -> str:
    return _normalize_oos_title(str(record.get("title") or ""))


def _filed_record_round_matches(row: GroundTruthRow, *, record: Mapping[str, Any]) -> bool:
    rec_round = _filed_record_round_num(record)
    if not row.round_num:
        return True
    if rec_round == row.round_num:
        return True
    if rec_round and rec_round != row.round_num:
        return False
    artifact = str(record.get("artifact_relpath") or "")
    identity = record.get("identity")
    paths: list[str] = []
    if artifact:
        paths.append(artifact)
    if isinstance(identity, tuple) and len(identity) >= 2:
        paths.append(str(identity[1]))
    return any(f"round-{row.round_num}" in path_str for path_str in paths)


def _match_oos_filed_record(row: GroundTruthRow, *, records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    row_tokens = _distinctive_tokens(f"{row.title}\n{row.prose_text}\n{row.finding_id}")
    reviewer_tokens = _row_reviewer_tokens(row)
    id_matches: list[Mapping[str, Any]] = []
    token_matches: list[Mapping[str, Any]] = []
    for record in records:
        if str(record.get("run_id") or "") != row.run_id:
            continue
        if str(record.get("bucket") or ""):
            continue
        if not _filed_record_round_matches(row, record=record):
            continue
        stable = str(record.get("stable_id") or "")
        identity = " ".join(str(part) for part in (record.get("identity") or ()))
        if row.finding_id and (stable.endswith(":" + row.finding_id) or stable == row.finding_id or _gt_finding_id_pattern(row.finding_id).search(identity)):
            id_matches.append(record)
            continue
        record_tokens = _distinctive_tokens(_ground_truth_row_title_from_oos_record(record))
        if (
            row_tokens
            and record_tokens
            and len(row_tokens & record_tokens) >= min(2, len(row_tokens), len(record_tokens))
            and _filed_record_reviewer_matches(record, row_tokens=reviewer_tokens)
        ):
            token_matches.append(record)
    if len(id_matches) == 1:
        return id_matches[0]
    if len(id_matches) > 1:
        return None
    if len(token_matches) == 1:
        return token_matches[0]
    return None


def _ground_truth_oos_outcome(
    row: GroundTruthRow,
    *,
    filed_records: Sequence[Mapping[str, Any]],
    issue_index: Mapping[int, Mapping[str, Any]],
    enrichment_degraded: str | None,
    stats: GroundTruthStats,
    repo: str | None = None,
) -> GroundTruthOutcome:
    if row.oos_panel_verdict != "accepted":
        if row.oos_panel_verdict == "rejected":
            stats.rejected_oos_panel += 1
            return GroundTruthOutcome(row=row, bucket="rejected_oos_panel", decisive=False, direction="", reason="rejected OOS panel result is non-decisive")
        return GroundTruthOutcome(row=row, bucket="weak_oos_panel_verdict", decisive=False, direction="", reason="missing or weak OOS panel verdict")
    record = _match_oos_filed_record(row, records=filed_records)
    if not record:
        return GroundTruthOutcome(row=row, bucket="missing_filed_oos_join", decisive=False, direction="", reason="no filed OOS issue join")
    issue_url = str(record.get("issue_url") or "")
    if repo and issue_url:
        url_repo = extract_repo_from_url(issue_url)
        if url_repo and url_repo.lower() != repo.lower():
            return GroundTruthOutcome(row=row, bucket="missing_filed_oos_join", decisive=False, direction="", reason="filed OOS issue repo mismatch")
    parsed_number, _reason = _parse_issue_number(record.get("issue_number"))
    if parsed_number is None:
        parsed_number = extract_issue_number_from_url(str(record.get("issue_url") or ""))
    issue = issue_index.get(parsed_number) if parsed_number else None
    if issue is None and enrichment_degraded:
        stats.enrichment_degraded_rows += 1
        return GroundTruthOutcome(row=row, bucket="enrichment unavailable", decisive=False, direction="", reason="GitHub issue enrichment unavailable")
    fate = classify_oos_issue_fate(issue)
    bucket = str(fate.get("bucket") or "provisional unknown")
    if bucket in {"docked closed-unfixed", "docked combined-away"}:
        return GroundTruthOutcome(row=row, bucket=bucket, decisive=True, direction="contradicts_acceptance", reason="accepted OOS filed issue later docked")
    return GroundTruthOutcome(row=row, bucket=bucket, decisive=False, direction="", reason="accepted OOS fate is provisional or kept")


def _ground_truth_in_scope_outcome(
    row: GroundTruthRow,
    *,
    evidence: Sequence[GroundTruthEvidence],
    enrichment_degraded: str | None,
    stats: GroundTruthStats,
) -> GroundTruthOutcome:
    if row.weak_reason:
        if "disagreement" in row.weak_reason:
            stats.verdict_disagreement += 1
        return GroundTruthOutcome(row=row, bucket="weak_prose_verdict", decisive=False, direction="", reason=row.weak_reason)
    if row.panel_verdict not in {"accepted", "rejected"}:
        return GroundTruthOutcome(row=row, bucket="weak_panel_verdict", decisive=False, direction="", reason="missing authoritative panel verdict")
    if enrichment_degraded:
        stats.enrichment_degraded_rows += 1
    for item in evidence:
        later, reason = _evidence_later_than_row(row, evidence=item)
        if not later:
            if reason == "timestamp-degraded":
                stats.timestamp_degraded += 1
            continue
        if not _strong_ground_truth_match(row, evidence=item):
            continue
        text = f"{item.title}\n{item.text}\n{item.category}"
        if row.panel_verdict == "accepted":
            if _GT_REVERSAL_RE.search(text):
                # F15: enrichment_degraded asymmetry fix — suppress issue-backed reversal when degraded
                if enrichment_degraded and item.source == "issue":
                    return GroundTruthOutcome(row=row, bucket="enrichment-degraded-reversal", decisive=False, direction="", reason="issue-backed reversal suppressed by enrichment degradation")
                return GroundTruthOutcome(row=row, bucket="accepted_reverted_or_regressed", decisive=True, direction="contradicts_acceptance", reason="later matching reversal or regression signal")
            continue
        if item.source == "accepted-finding" or item.category in {"Bug fix", "Test coverage", "Hardening/validation/security"} or CATEGORY_PATTERNS[1][1].search(text):
            if enrichment_degraded and item.source == "issue":
                return GroundTruthOutcome(row=row, bucket="enrichment-degraded-resurfacing", decisive=False, direction="", reason="issue-backed resurfacing suppressed by enrichment degradation")
            # F3: NOT_PLANNED closed issues without reversal wording are non-decisive
            if item.source == "issue" and item.not_planned and not _GT_REVERSAL_RE.search(text):
                continue
            return GroundTruthOutcome(row=row, bucket="rejected_resurfaced", decisive=True, direction="supports_acceptance", reason="later matching issue or accepted finding")
    if row.panel_verdict == "accepted":
        return GroundTruthOutcome(row=row, bucket="accepted_no_counterevidence", decisive=False, direction="", reason="no later matching reversal signal")
    return GroundTruthOutcome(row=row, bucket="rejected_not_observed", decisive=False, direction="", reason="no later strong resurfacing match")


def _ground_truth_update_metrics(metrics: dict[tuple[str, str], GroundTruthMetric], *, outcome: GroundTruthOutcome) -> None:
    if not outcome.decisive:
        return
    for voter in outcome.row.voters:
        key = (outcome.row.panel_kind, voter.voter)
        metric = metrics.setdefault(key, GroundTruthMetric(panel=outcome.row.panel_kind, voter=voter.voter))
        vote = voter.vote.strip().upper()
        if voter.missing or vote not in {"YES", "NO"}:
            metric.missing += 1
            continue
        metric.decisive += 1
        yes_aligned = outcome.direction == "supports_acceptance"
        aligned = (vote == "YES" and yes_aligned) or (vote == "NO" and not yes_aligned)
        if aligned:
            metric.aligned += 1
        else:
            metric.misaligned += 1
            if vote == "YES" and outcome.direction == "contradicts_acceptance":
                metric.false_positive_yes += 1
            if vote == "NO" and outcome.direction == "supports_acceptance":
                metric.false_negative_no += 1


def _ground_truth_rate(aligned: int, *, misaligned: int) -> str:
    denominator = aligned + misaligned
    return "n/a" if denominator == 0 else f"{aligned / denominator:.3f}"


def _render_ground_truth_report(
    *,
    log_root: Path,
    stats: GroundTruthStats,
    outcomes: Sequence[GroundTruthOutcome],
    metrics: Mapping[tuple[str, str], GroundTruthMetric],
    enrichment_degraded: str | None,
    top_k: int,
) -> str:
    lines = ["## Ground-truth Voter Calibration"]
    lines.append("")
    lines.append("Diagnostic only. This section does not change live scoring, thresholds, tokens, or reviewer points.")
    if enrichment_degraded:
        lines.append(
            f"- Note: GitHub issue enrichment unavailable ({enrichment_degraded}); "
            "in-scope realized-outcome buckets may be suppressed or partial."
        )
    if stats.large_corpus_skip:
        lines.append(
            "- Note: corpus exceeds 5000 rows; accepted-finding index disabled. "
            "OOS filed-issue join still evaluated. Per-voter rates may be incomplete."
        )
    lines.extend(
        [
            "",
            "Corpus:",
            f"- Log root: `{log_root}`",
            f"- Classification TSV files scanned: {stats.files_seen}",
            f"- Unsupported TSV files skipped: {stats.skipped_files}",
            f"- Classification rows scanned: {stats.scanned_rows}",
            f"- Eligible rows with parseable voter ballots: {stats.eligible_rows}",
            f"- Ineligible rows: {stats.ineligible_rows}",
            f"- Rows with prose evidence: {stats.prose_rows}",
            f"- GC-slimmed or missing voter TSV runs: {stats.gc_slimmed_runs}",
            f"- Decisive realized rows: {stats.decisive_rows}",
            f"- Weak/provisional/non-decisive rows: {stats.weak_rows}",
            f"- Timestamp-degraded matches: {stats.timestamp_degraded}",
            f"- Verdict-disagreement rows: {stats.verdict_disagreement}",
            f"- Rejected-OOS-panel rows: {stats.rejected_oos_panel}",
            f"- Enrichment-degraded rows: {stats.enrichment_degraded_rows}",
            "",
            "Outcome buckets:",
            "| Bucket | Rows | Decisive |",
            "|---|---:|---:|",
        ]
    )
    bucket_decisive: collections.Counter[str] = collections.Counter()
    for outcome in outcomes:
        if outcome.decisive:
            bucket_decisive[outcome.bucket] += 1
    if stats.buckets:
        for bucket, count in sorted(stats.buckets.items()):
            lines.append(f"| {bucket} | {count} | {bucket_decisive.get(bucket, 0)} |")
    else:
        lines.append("| no-evidence | 0 | 0 |")
    lines.extend(
        [
            "",
            "Per-voter realized alignment:",
            "| Panel | Voter | Decisive | Aligned | Misaligned | Missing | Realized alignment | False positive YES | False negative NO |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    if metrics:
        for (_panel, _voter), metric in sorted(metrics.items()):
            lines.append(
                f"| {metric.panel} | {metric.voter} | {metric.decisive} | {metric.aligned} | "
                f"{metric.misaligned} | {metric.missing} | {_ground_truth_rate(metric.aligned, misaligned=metric.misaligned)} | "
                f"{metric.false_positive_yes} | {metric.false_negative_no} |"
            )
    else:
        lines.append("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | 0 | 0 |")
    lines.extend(["", "Examples:"])
    examples = list(outcomes)[: max(top_k, 1)]
    if examples:
        for outcome in examples:
            lines.append(
                f"- {outcome.row.run_id} {outcome.row.finding_id}: {outcome.bucket}. {outcome.reason}"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "Notes:",
            "- Ground-truth alignment is against realized outcomes, not panel self-agreement.",
            "- Conservative matching can undercount resurfacing and reversals.",
            "- Provisional OOS fates and rejected OOS panel results are non-decisive.",
            "- `realized_alignment_rate` uses decisive aligned/misaligned ballots only.",
        ]
    )
    return "\n".join(lines)


def _ground_truth_gc_slimmed_fallback(log_root: Path, *, seen_gc: frozenset[Path]) -> int:
    """Count gc-slimmed runs not already counted during classifier discovery (F4)."""
    if not log_root.exists():
        return 0
    count = 0
    for run_dir in list((log_root / "implement").glob("*")) + list((log_root / "design").glob("*")) + list((log_root / "review").glob("*")):
        if run_dir.is_dir() and run_dir not in seen_gc and (run_dir / "gc-slimmed").exists():
            count += 1
    return count


def ground_truth_voter_calibration(
    issues: Sequence[Mapping[str, Any]],
    *,
    log_root: Path,
    filed_issue_details: dict[int, dict[str, Any]],
    repo: str | None = None,
    enrichment_degraded: str | None = None,
    top_k: int = 10,
) -> tuple[str, dict[str, Any]]:
    cache_key = str(log_root)
    cached = _GROUND_TRUTH_ROW_CACHE.get(cache_key)
    if cached:
        rows = cached[0]
        stats = _copy_ground_truth_stats(cached[1])
    else:
        stats = GroundTruthStats()
        rows = []
        seen_gc: set[Path] = set()
        discovered = _ground_truth_discover_classifiers(log_root)
        stats.files_seen = len(discovered)
        for panel_kind, path in discovered:
            run_dir = _ground_truth_run_dir(path, panel_kind=panel_kind)
            if (run_dir / "gc-slimmed").exists():
                if run_dir not in seen_gc:
                    seen_gc.add(run_dir)
                    stats.gc_slimmed_runs += 1
                continue
            text = _safe_read_text(path)
            if not voting.classification_tsv_schema_supported(text, panel_kind=panel_kind):
                stats.skipped_files += 1
                continue
            prep_rows = voting.classification_row_panel_inputs(text, panel_kind=panel_kind)
            stats.scanned_rows += len(prep_rows)
            started_at = _ground_truth_run_started_at(run_dir)
            for prep in prep_rows:
                raw = dict(prep.raw_row)
                is_oos = voting.classification_row_is_oos(raw, header=prep.header)
                agreement = voting.voter_agreement_row_from_panel(
                    voting_result=raw.get("voting_result") or "",
                    voter_votes=prep.voter_votes,
                    panel=prep.panel,
                    voter_severities=prep.voter_severities,
                )
                if agreement is None:
                    stats.ineligible_rows += 1
                    continue
                stats.eligible_rows += 1
                voters: list[GroundTruthVoter] = []
                voters_value = agreement.get("voters")
                voters_list: list[object] = voters_value if isinstance(voters_value, list) else []
                for voter_obj in voters_list:
                    if isinstance(voter_obj, Mapping):
                        voters.append(
                            GroundTruthVoter(
                                voter=str(voter_obj.get("voter") or ""),
                                vote=str(voter_obj.get("vote") or ""),
                                missing=int(voter_obj.get("missing") or 0),
                            )
                        )
                row = GroundTruthRow(
                    panel_kind=prep.panel,
                    path=path,
                    run_dir=run_dir,
                    run_id=run_dir.name,
                    round_num=_ground_truth_round_num(path),
                    started_at=started_at,
                    raw_row=raw,
                    header=list(prep.header),
                    reviewer_column=prep.reviewer_column,
                    voter_votes=list(prep.voter_votes),
                    voters=voters,
                    is_oos=is_oos,
                )
                _bind_ground_truth_prose(row)
                if row.prose_text or row.panel_verdict or row.oos_panel_verdict:
                    stats.prose_rows += 1
                rows.append(row)

        stats.gc_slimmed_runs += _ground_truth_gc_slimmed_fallback(
            log_root, seen_gc=frozenset(seen_gc)
        )
        _GROUND_TRUTH_ROW_CACHE[cache_key] = (rows, _copy_ground_truth_stats(stats))

    issue_index = _merged_issue_index(issues, filed_issue_details)
    issue_evidence = _ground_truth_issue_evidence(issues)
    large_corpus = len(rows) > 5000
    if large_corpus:
        stats.large_corpus_skip = True
    accepted_evidence = [] if large_corpus else _ground_truth_accepted_finding_evidence(rows)
    accepted_index = _ground_truth_evidence_token_index(accepted_evidence)
    filed_records = _GROUND_TRUTH_FILED_CACHE.get(cache_key)
    if filed_records is None:
        filed_records = iter_filed_oos_records(log_root)
        _GROUND_TRUTH_FILED_CACHE[cache_key] = filed_records
    filed_by_run: dict[str, list[Mapping[str, Any]]] = collections.defaultdict(list)
    for record in filed_records:
        filed_by_run[str(record.get("run_id") or "")].append(record)
    outcomes: list[GroundTruthOutcome] = []
    metrics: dict[tuple[str, str], GroundTruthMetric] = {}
    for row in rows:
        if row.is_oos:
            outcome = _ground_truth_oos_outcome(
                row,
                filed_records=filed_by_run.get(row.run_id, []),
                issue_index=issue_index,
                enrichment_degraded=enrichment_degraded,
                stats=stats,
                repo=repo,
            )
        else:
            candidates = [] if row.weak_reason or row.panel_verdict not in {"accepted", "rejected"} else _candidate_evidence_for_row(
                row,
                issue_evidence=issue_evidence,
                accepted_evidence=accepted_evidence,
                accepted_index=accepted_index,
            )
            outcome = _ground_truth_in_scope_outcome(
                row,
                evidence=candidates,
                enrichment_degraded=enrichment_degraded,
                stats=stats,
            )
        outcomes.append(outcome)
        stats.buckets[outcome.bucket] += 1
        if outcome.decisive:
            stats.decisive_rows += 1
        else:
            stats.weak_rows += 1
        _ground_truth_update_metrics(metrics, outcome=outcome)

    text = _render_ground_truth_report(
        log_root=log_root,
        stats=stats,
        outcomes=outcomes,
        metrics=metrics,
        enrichment_degraded=enrichment_degraded,
        top_k=top_k,
    )
    return text, {"stats": stats, "outcomes": outcomes, "metrics": metrics}


def _build_analyze_report(
    issues: Sequence[Mapping[str, Any]],
    *,
    log_root: Path,
    filed_issue_details: dict[int, dict[str, Any]],
    repo: str | None = None,
    enrichment_degraded: str | None = None,
    top_k: int = 10,
    categories_mode: str = "default",
    span_days: int = 0,
) -> str:
    top_k = max(top_k, 1)
    stats = coverage_stats(issues)
    categories = categorize(issues, categories_mode, top_k)
    breakdown_text, category_counts = category_breakdown(issues, categories)
    chart_text = growth_chart(issues, categories, max(span_days, 0))
    patterns_text = pattern_observations(issues, top_k, stats)
    waste_text = wasteful_findings(issues, top_k)
    reviewer_text, reviewer_stats = reviewer_effectiveness(issues)
    summary_text = executive_summary(stats, category_counts, reviewer_stats)
    sections = [
        summary_text,
        render_coverage(stats),
        breakdown_text,
        chart_text,
        patterns_text,
        waste_text,
        reviewer_text,
    ]
    try:
        fate_text, _fate_stats = fate_adjusted_oos_scoring(
            issues,
            log_root,
            filed_issue_details=filed_issue_details,
            repo=repo,
            enrichment_degraded=enrichment_degraded,
        )
        sections.append(fate_text)
    except Exception as exc:  # pragma: no cover - defensive live-report guard
        print(f"WARN fate-adjusted OOS scoring unavailable: {exc}", file=sys.stderr)
    try:
        ground_truth_text, _ground_truth_stats = ground_truth_voter_calibration(
            issues,
            log_root=log_root,
            filed_issue_details=filed_issue_details,
            repo=repo,
            enrichment_degraded=enrichment_degraded,
            top_k=top_k,
        )
        sections.append(ground_truth_text)
    except Exception as exc:  # pragma: no cover - defensive live-report guard
        print(f"WARN ground-truth voter calibration unavailable: {exc}", file=sys.stderr)
    return "\n\n".join(sections)


def executive_summary(
    stats: Mapping[str, Any],
    category_counts: Mapping[str, int],
    reviewer_stats: Mapping[str, Any],
) -> str:
    dominant = ", ".join(category for category, _count in collections.Counter(category_counts).most_common(3)) or "no dominant categories"
    best = reviewer_stats.get("best")
    if best:
        rate, (tool, persona), total, done = best
        reviewer = f"{tool} / {persona} ({done}/{total} done, {rate * 100:.1f}%)"
    else:
        reviewer = "no reviewer/persona pair with at least 10 findings"
    return (
        "## Executive Summary\n"
        f"Analyzed {stats['total']} issues across {stats['oldest']} to {stats['newest']}. "
        f"Dominant categories: {dominant}. "
        "The strongest waste signals are duplicate titles, stalled issues, reversal/supersession mentions, "
        "and PR closure clusters listed below. "
        f"Highest-ROI reviewer/persona signal: {reviewer}."
    )


def render_coverage(stats: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "## Coverage Stats",
            f"- Total issues: {stats['total']}",
            f"- Open / closed: {stats['open']} / {stats['closed']}",
            f"- Created date range: {stats['oldest']} -> {stats['newest']}",
            f"- Time to close: median {fmt_days(stats['median_close'])}, P90 {fmt_days(stats['p90_close'])}",
            f"- Closed by PR reference: {stats['pr_closed_pct']:.1f}% of closed issues",
        ]
    )


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--span-days", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--categories", choices=("auto", "default"), default="default")
    parser.add_argument("--log-root", default="larch-logs")
    parser.add_argument("--repo", default="")
    parser.add_argument("--filed-issue-details-json", default="")
    parser.add_argument(
        "--lenient",
        action="store_true",
        help=(
            "Suppress the >5%% threshold abort in load_issues for non-dict, "
            "malformed-number, or duplicate-number elements. Per-element "
            "stderr warnings are still emitted; this flag only disables the "
            "threshold check."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    issues = load_issues(args.json, lenient=args.lenient)
    if not issues:
        print("No issues to analyze.")
        return 0
    filed_details = _load_filed_issue_details_json(Path(args.filed_issue_details_json) if args.filed_issue_details_json else None)
    print(_build_analyze_report(
        issues,
        log_root=Path(args.log_root),
        filed_issue_details=filed_details,
        repo=args.repo or None,
        top_k=max(args.top_k, 1),
        categories_mode=args.categories,
        span_days=max(args.span_days, 0),
    ))
    return 0



def analyze_main(argv: Sequence[str] | None = None) -> int:
    return main(argv)


def _write_issue_dump(path: Path, text: str, *, degraded_fields: Sequence[str] = ()) -> None:
    payload = text
    if degraded_fields:
        try:
            parsed = json.loads(text or "[]")
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        item.setdefault("_larch_degraded_fields", list(degraded_fields))
                payload = json.dumps(parsed)
        except json.JSONDecodeError:
            payload = text
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    tmp.write_text(payload, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)
    path.chmod(0o600)


def fetch_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py analyze-issues fetch")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--limit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    output = Path(args.output)
    expanded_fields = "number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences,url,stateReason"
    fallback_fields = "number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences"
    tmp = output.with_name(output.name + f".tmp.{os.getpid()}")
    old_umask = os.umask(0o077)
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            tmp.chmod(0o600)
            expanded_cmd = [
                "gh", "issue", "list", "--repo", args.repo, "--state", "all", "--limit", args.limit,
                "--json", expanded_fields,
            ]
            result = subprocess.run(expanded_cmd, stdout=handle, text=True, check=False)
        degraded: tuple[str, ...] = ()
        if result.returncode != 0:
            with tmp.open("w", encoding="utf-8") as handle:
                tmp.chmod(0o600)
                result = subprocess.run([
                    "gh", "issue", "list", "--repo", args.repo, "--state", "all", "--limit", args.limit,
                    "--json", fallback_fields,
                ], stdout=handle, text=True, check=False)
            if result.returncode == 0:
                degraded = ("stateReason", "url")
        if result.returncode != 0:
            print(f"ERROR=gh issue list failed for repo {args.repo}", file=sys.stderr)
            tmp.unlink(missing_ok=True)
            return 1
        payload = tmp.read_text(encoding="utf-8")
        _write_issue_dump(output, payload, degraded_fields=degraded)
        return 0
    finally:
        os.umask(old_umask)
        tmp.unlink(missing_ok=True)


def _detect_repo() -> str:
    res = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    remote = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, check=False).stdout.strip()
    repo = re.sub(r"^git@[^:]+:", "", remote)
    repo = re.sub(r"^https?://[^/]+/", "", repo)
    repo = re.sub(r"\.git$", "", repo)
    return repo


def run_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py analyze-issues run")
    parser.add_argument("--limit", default="2000")
    parser.add_argument("--span-days", default="0")
    parser.add_argument("--top-K", "--top-k", dest="top_k", default="10")
    parser.add_argument("--categories", default="default", choices=["auto", "default"])
    parser.add_argument("--lenient", action="store_true")
    parser.add_argument("--log-root", default="larch-logs")
    parser.add_argument("--repo", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo = args.repo or _detect_repo()
    repo_valid = bool(re.fullmatch(r"[^/]+/[^/]+", repo or ""))
    if not repo_valid:
        print("WARN targeted comment fetch unavailable: unable to detect GitHub repo owner/name", file=sys.stderr)
        repo = ""
    repo_resolved = repo_valid
    enrichment_degraded: str | None = "repo_unavailable" if not repo_resolved else None
    issues: list[dict[str, Any]] = []
    if repo_resolved:
        sanitized = re.sub(r"[^A-Za-z0-9_-]", "", repo.replace("/", "-"))
        if not sanitized:
            print(f"WARN bulk issue fetch skipped: sanitized repo name is empty (REPO='{repo}')", file=sys.stderr)
            repo_resolved = False
            repo = ""
        else:
            dump = Path(os.environ.get("TMPDIR", "/tmp")) / f"{sanitized}-issues.json"
            old_umask = os.umask(0o077)
            try:
                rc = fetch_main(["--repo", repo, "--limit", args.limit, "--output", str(dump)])
            finally:
                os.umask(old_umask)
            if rc != 0:
                print("WARN bulk gh issue list failed; continuing with log-only fate scoring", file=sys.stderr)
                enrichment_degraded = enrichment_degraded or "bulk_fetch_failed"
            else:
                try:
                    issues = load_issues(str(dump), lenient=args.lenient)
                except SystemExit:
                    print("WARN corrupt issue dump; continuing with log-only fate scoring", file=sys.stderr)
                    issues = []
                    enrichment_degraded = enrichment_degraded or "bulk_fetch_failed"
    if not repo_resolved:
        repo = ""
    log_root = Path(args.log_root)
    candidate_numbers: set[int] = set()
    for record in iter_filed_oos_records(log_root):
        parsed_number, _reason = _parse_issue_number(record.get("issue_number"))
        if parsed_number is None:
            continue
        issue_url = str(record.get("issue_url") or "")
        if repo and issue_url:
            url_repo = extract_repo_from_url(issue_url)
            if url_repo and url_repo.lower() != repo.lower():
                continue
        candidate_numbers.add(int(parsed_number))
    details: dict[int, dict[str, Any]] = {}
    if candidate_numbers and repo:
        details = _fetch_filed_oos_issue_details(repo, candidate_numbers)
    print(_build_analyze_report(
        issues,
        log_root=log_root,
        filed_issue_details=details,
        repo=repo,
        enrichment_degraded=enrichment_degraded,
        top_k=max(int(args.top_k), 1) if str(args.top_k).isdigit() else 10,
        categories_mode=args.categories,
        span_days=max(int(args.span_days), 0) if str(args.span_days).isdigit() else 0,
    ))
    return 0
