# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
# ruff: noqa: B905, FURB167, PERF401, PLC0415, PLR2004, PTH123, RET504, RUF005, RUF007, RUF100, S108, S607, SLF001, UP006, UP015, UP017, UP035, UP037
# pylint: skip-file
"""Issue report generation: stats, categorization, charts, and reviewer tables."""

from __future__ import annotations

import collections
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

from larch.issue._util import (
    CATEGORY_PATTERNS,
    FILE_RE,
    STOP_WORDS,
    issue_number,
    issue_text,
    parse_iso,
    pr_ref_id,
    strip_prefixes,
)


def percentile( *,values: Sequence[float], percent: float) -> float | None:
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
        "median_close": percentile(values=close_durations, percent=50),
        "p90_close": percentile(values=close_durations, percent=90),
        "p25_close": percentile(values=close_durations, percent=25),
        "p75_close": percentile(values=close_durations, percent=75),
        "pr_closed_pct": (pr_closed / closed * 100.0) if closed else 0.0,
    }


def default_category(issue: Mapping[str, Any]) -> str:
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")
    if body.lstrip().lower().startswith("tracking issue for") and "original prompt" in body.lower():
        return "Tracking/umbrella"
    if re.match(r"^\s*(?:\[research[^\]]*\]\s*)?(?:investigate|research)\b", title, re.I):
        return "Research/investigation"
    haystack = issue_text(issue=issue)
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


def categorize( *,issues: Sequence[Mapping[str, Any]], mode: str, top_k: int) -> Dict[int, str]:
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


def category_breakdown( *,
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


def growth_chart( *,
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
    from larch.rendering import render_chart

    return render_chart


def pattern_observations( *,issues: Sequence[Mapping[str, Any]], top_k: int, stats: Mapping[str, Any]) -> str:
    daily: collections.Counter[str] = collections.Counter()
    paths: collections.Counter[str] = collections.Counter()
    auto_count = 0
    for issue in issues:
        created = parse_iso(str(issue.get("createdAt") or ""))
        if created:
            daily[created.date().isoformat()] += 1
        text = issue_text(issue=issue)
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


def wasteful_findings( *,issues: Sequence[Mapping[str, Any]], top_k: int) -> str:
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


def executive_summary( *,
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
