#!/usr/bin/env python3
"""Analyze GitHub issue JSON for backlog and process insight."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

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


def load_issues(path: str, lenient: bool = False) -> List[Dict[str, Any]]:
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
    return "## Growth Chart\n" + chart_module.render_chart(buckets, [
        (key, category, matrix[category]) for key, category in zip(keys, category_order)
    ])


def load_render_chart() -> Any:
    path = Path(__file__).with_name("render-chart.py")
    spec = importlib.util.spec_from_file_location("render_chart", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"ERROR=Unable to load chart renderer at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    best = eligible[0] if eligible else None
    return "\n".join(lines), {"pair_counts": pair_counts, "pair_done": pair_done, "best": best}


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
    top_k = max(args.top_k, 1)
    stats = coverage_stats(issues)
    categories = categorize(issues, args.categories, top_k)
    breakdown_text, category_counts = category_breakdown(issues, categories)
    chart_text = growth_chart(issues, categories, max(args.span_days, 0))
    patterns_text = pattern_observations(issues, top_k, stats)
    waste_text = wasteful_findings(issues, top_k)
    reviewer_text, reviewer_stats = reviewer_effectiveness(issues)
    summary_text = executive_summary(stats, category_counts, reviewer_stats)
    print(
        "\n\n".join(
            [
                summary_text,
                render_coverage(stats),
                breakdown_text,
                chart_text,
                patterns_text,
                waste_text,
                reviewer_text,
            ]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
