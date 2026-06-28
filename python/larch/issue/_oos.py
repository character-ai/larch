# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
# ruff: noqa: B905, FURB167, PERF401, PLC0415, PLR2004, PTH123, RET504, RUF005, RUF007, RUF100, S108, S607, SLF001, UP006, UP015, UP017, UP035, UP037
# pylint: skip-file
"""OOS tracking, parsing, and fate-adjusted scoring helpers."""

from __future__ import annotations

import collections
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from larch.issue import oos_filer
from larch.issue import oos_priority
from larch.issue._util import (
    GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER,
    _parse_issue_number,
    issue_number,
    parse_iso,
)
from larch.review import voting

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
_ROLLUP_EXCERPT_BULLET_RE = re.compile(r"^\s*-\s*\*\*(.+?)\*\*:\s*", re.M)


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


def is_open_high_risk_oos_issue(issue: Mapping[str, Any]) -> bool:
    title = str(issue.get("title") or "").strip()
    state = str(issue.get("state") or "").upper()
    return (
        state == "OPEN"
        and title.lower().startswith("[oos]")
        and oos_priority.OOS_CORRECTNESS_LABEL in issue_labels(issue)
    )


def created_at_sort_key(issue: Mapping[str, Any]) -> tuple[datetime, int]:
    created = parse_iso(str(issue.get("createdAt") or ""))
    fallback = datetime.max.replace(tzinfo=timezone.utc)
    return (created or fallback, issue_number(issue))


def render_high_risk_oos_backlog(
    issues: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
    top_k: int = 10,
) -> str:
    current = now or datetime.now(timezone.utc)
    rows = sorted(
        [issue for issue in issues if is_open_high_risk_oos_issue(issue)],
        key=created_at_sort_key,
    )
    lines = ["## High-risk OOS Backlog"]
    if not rows:
        lines.append("No open high-risk OOS issues found.")
        return "\n".join(lines)
    for issue in rows[: max(top_k, 1)]:
        created = parse_iso(str(issue.get("createdAt") or ""))
        created_text = created.date().isoformat() if created else "unknown"
        age_text = "unknown"
        if created:
            age_text = str(max((current.date() - created.date()).days, 0))
        url = str(issue.get("url") or "")
        suffix = f" — {url}" if url else ""
        lines.append(f"- #{issue_number(issue)} ({age_text}d, {created_text}): {issue.get('title') or ''}{suffix}")
    return "\n".join(lines)


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


def _canonical_stable_id( *,source_key: str, bare_id: str) -> str:
    return f"{source_key}:{bare_id}" if source_key else bare_id


def _hash_stable_id( *,title: str, body: str, source_key: str) -> str:
    return oos_filer._stable_identifier(title, body, source_key=source_key)  # pyright: ignore[reportPrivateUsage]


def _stable_ids_cover( *,issue_stable_id: str, block_keys: set[Any], allow_main_agent_bridge: bool = False) -> bool:
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
        canonical = _canonical_stable_id(source_key=source_key, bare_id=heading_id)
        hash_id = _hash_stable_id(title=title, body=body, source_key=source_key)
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


def _resolve_blocks_for_stable_id( *,stable_id: str, blocks: Sequence[Mapping[str, Any]], body: str = "") -> tuple[list[dict[str, Any]], bool]:
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
            if _stable_ids_cover(issue_stable_id=stable_id, block_keys=set(block.get("lookup_keys", set())), allow_main_agent_bridge=allow_bridge)
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


def _reviewers_from_label( *,label: str, known_labels: list[str] | None = None) -> list[str]:
    raw = (label or "").strip() or "unknown"
    labels = known_labels or []
    tokens = voting.tokenize_finding_reviewers(cell=raw, labels=labels)
    if not tokens:
        grown = list(labels)
        seen = set(grown)
        voting.grow_attribution_labels(grown, seen, raw)
        tokens = voting.tokenize_finding_reviewers(cell=raw, labels=grown)
    return tokens or [part.strip() for part in raw.split(",") if part.strip()] or ["unknown"]


def _row_from_block( *,run_id: str, block: Mapping[str, Any], record: Mapping[str, Any], issue_number: int | None, issue_url: str, run_dir_key: str = "") -> dict[str, Any]:
    run_key = run_dir_key or run_id
    identity = (run_key, block.get("artifact_relpath") or "", block.get("heading_id") or block.get("hash_stable_id") or issue_url or issue_number)
    return {
        "run_id": run_id,
        "run_dir_key": run_dir_key or run_id,
        "identity": identity,
        "stable_id": block.get("canonical_stable_id") or block.get("hash_stable_id") or "",
        "issue_number": issue_number,
        "issue_url": issue_url,
        "reviewer": block.get("reviewer") or "unknown",
        "title": block.get("title") or record.get("title") or "",
    }


def _rollup_excerpt_titles_from_text(text: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for match in _ROLLUP_EXCERPT_BULLET_RE.finditer(text or ""):
        title = _normalize_oos_title(match.group(1))
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def _rollup_excerpt_source_texts( *,run_dir: Path, ndjson_record: Mapping[str, Any]) -> list[str]:
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


def _blocks_from_rollup_excerpt_titles( *,
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


def _ambiguous_rollup_expansion_row( *,run_id: str, issue_number: int | None, issue_url: str, run_dir_key: str = "") -> dict[str, Any]:
    run_key = run_dir_key or run_id
    return {
        "bucket": "ambiguous rollup expansion",
        "run_id": run_id,
        "run_dir_key": run_key,
        "identity": (run_key, "rollup-ambiguous-expansion", issue_number or issue_url),
        "issue_number": issue_number,
        "issue_url": issue_url,
        "reviewer": "unknown",
    }


def _ambiguous_stable_id_row( *,run_id: str, stable_id: str, issue_number: int | None, issue_url: str, run_dir_key: str = "") -> dict[str, Any]:
    run_key = run_dir_key or run_id
    return {
        "bucket": "ambiguous stable id",
        "run_id": run_id,
        "run_dir_key": run_key,
        "identity": (run_key, "rollup-ambiguous", stable_id, issue_number or issue_url),
        "issue_number": issue_number,
        "issue_url": issue_url,
        "reviewer": "unknown",
    }


def _rollup_expansion_shortfall_result( *,run_id: str, issue_number: int | None, issue_url: str, out: list[dict[str, Any]], run_dir_key: str = "") -> list[dict[str, Any]]:
    if not out:
        return [_ambiguous_rollup_expansion_row(run_id=run_id, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key)]
    return [*out, _ambiguous_rollup_expansion_row(run_id=run_id, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key)]


def _issue_evidence_for_record(record: Mapping[str, Any]) -> tuple[int | None, str]:
    urls = _record_issue_urls(record)
    numbers = _record_issue_numbers(record)
    number = numbers[0] if numbers else None
    url = urls[0] if urls else ""
    if number is None and url:
        number = extract_issue_number_from_url(url)
    return number, url


def _expand_cap_rollup_records( *,run_dir: Path, ndjson_record: dict[str, Any], blocks: Sequence[Mapping[str, Any]], indexed_blocks: Mapping[Any, list[dict[str, Any]]], log_root: Path | None = None) -> list[dict[str, Any]]:
    del indexed_blocks
    body = str(ndjson_record.get("body") or "")
    stable_ids = _stable_ids_from_record(ndjson_record) or _extract_legacy_stable_ids_from_ndjson_body(body)
    out: list[dict[str, Any]] = []
    issue_number, issue_url = _issue_evidence_for_record(ndjson_record)
    run_id = run_dir.name
    run_dir_key = _resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)
    if log_root and run_dir_key is None:
        return []
    seen_identities: set[tuple[Any, ...]] = set()
    ambiguous = False
    for stable_id in stable_ids:
        matched, is_ambiguous = _resolve_blocks_for_stable_id(stable_id=stable_id, blocks=blocks, body=body)
        if is_ambiguous:
            ambiguous = True
            out.append(_ambiguous_stable_id_row(run_id=run_id, stable_id=stable_id, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key))
            continue
        for block in matched:
            identity = (str(block.get("artifact_relpath") or ""), str(block.get("heading_id") or ""))
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            out.append(_row_from_block(run_id=run_id, block=block, record=ndjson_record, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key))
    expected_match = re.search(r"Aggregated rollup of\s+(\d+)\s+capped OOS items", f"{ndjson_record.get('title') or ''}\n{body}", re.I)
    expected = int(expected_match.group(1)) if expected_match else 0
    scored_rows = [row for row in out if not row.get("bucket")]
    if expected and len(scored_rows) > expected:
        return [_ambiguous_rollup_expansion_row(run_id=run_id, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key)]
    if expected and len(scored_rows) < expected:
        excerpt_titles: list[str] = []
        for text in _rollup_excerpt_source_texts(run_dir=run_dir, ndjson_record=ndjson_record):
            excerpt_titles.extend(_rollup_excerpt_titles_from_text(text))
        for block in _blocks_from_rollup_excerpt_titles(titles=excerpt_titles, blocks=blocks, seen_identities=seen_identities):
            out.append(_row_from_block(run_id=run_id, block=block, record=ndjson_record, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key))
    scored_rows = [row for row in out if not row.get("bucket")]
    if expected and len(scored_rows) < expected and ambiguous:
        return _rollup_expansion_shortfall_result(run_id=run_id, issue_number=issue_number, issue_url=issue_url, out=out, run_dir_key=run_dir_key)
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
                    if any(_stable_ids_cover(issue_stable_id=stable_id, block_keys=set(block.get("lookup_keys", set())), allow_main_agent_bridge=True) for stable_id in stable_ids)
                ]
        elif source_key:
            candidates = [block for block in candidates if block.get("source_key") == source_key]
        if len(candidates) == expected:
            for block in sorted(candidates, key=lambda item: (str(item.get("artifact_relpath") or ""), str(item.get("heading_id") or ""))):
                identity = (str(block.get("artifact_relpath") or ""), str(block.get("heading_id") or ""))
                if identity in seen_identities:
                    continue
                seen_identities.add(identity)
                out.append(_row_from_block(run_id=run_id, block=block, record=ndjson_record, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key))
        else:
            return _rollup_expansion_shortfall_result(run_id=run_id, issue_number=issue_number, issue_url=issue_url, out=out, run_dir_key=run_dir_key)
    scored_rows = [row for row in out if not row.get("bucket")]
    if expected and len(scored_rows) < expected:
        return _rollup_expansion_shortfall_result(run_id=run_id, issue_number=issue_number, issue_url=issue_url, out=out, run_dir_key=run_dir_key)
    if ambiguous and not scored_rows:
        if out:
            return out
        return [_ambiguous_stable_id_row(run_id=run_id, stable_id=stable_ids[0] if stable_ids else "", issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key)]
    return out


def _parse_oos_issues_created(path: Path, *, accepted_design_path: Path | None, log_root: Path | None = None) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    run_dir = path.parent
    run_dir_key = _resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)
    if log_root and run_dir_key is None:
        return []
    run_key = run_dir_key or run_dir.name
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
                    "run_dir_key": run_dir_key,
                    "identity": (run_key, "design-map", heading, number or url),
                    "issue_number": number,
                    "issue_url": url,
                    "reviewer": "unknown",
                    "title": heading,
                })
                continue
            block = blocks_for_heading[0] if blocks_for_heading else {}
            records.append({
                "run_id": run_dir.name,
                "run_dir_key": run_dir_key,
                "identity": (run_key, str(block.get("artifact_relpath") or accepted_design_path.name if accepted_design_path else "oos-accepted-design.md"), heading),
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
            "run_dir_key": run_dir_key,
            "identity": (run_key, block.get("artifact_relpath") or "", heading),
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
                "run_dir_key": run_dir_key,
                "identity": (run_key, "created", issue_url or number),
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


def _join_implement_run_records(run_dir: Path, *, log_root: Path | None = None) -> list[dict[str, Any]]:
    run_dir_key = _resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)
    if log_root and run_dir_key is None:
        return []
    blocks: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("**/oos-accepted-*.md")):
        blocks.extend(_parse_oos_accepted_blocks(path, run_dir=run_dir))
    indexed = _index_accepted_blocks_by_stable_id(blocks)
    rows: list[dict[str, Any]] = []
    for record in _parse_oos_issues_ndjson(run_dir / "oos-issues.ndjson"):
        issue_number, issue_url = _issue_evidence_for_record(record)
        if _is_cap_rollup_record(record):
            expanded = _expand_cap_rollup_records(run_dir=run_dir, ndjson_record=record, blocks=blocks, indexed_blocks=indexed, log_root=log_root)
            if expanded:
                rows.extend(expanded)
                continue
        stable_ids = _stable_ids_from_record(record) or _extract_legacy_stable_ids_from_ndjson_body(str(record.get("body") or ""))
        matched_any = False
        ambiguous = False
        for stable_id in stable_ids:
            matched, is_ambiguous = _resolve_blocks_for_stable_id(stable_id=stable_id, blocks=blocks, body=str(record.get("body") or ""))
            ambiguous = ambiguous or is_ambiguous
            for block in matched:
                matched_any = True
                rows.append(_row_from_block(run_id=run_dir.name, block=block, record=record, issue_number=issue_number, issue_url=issue_url, run_dir_key=run_dir_key))
        if ambiguous and not matched_any:
            rows.append({"bucket": "ambiguous stable id", "run_id": run_dir.name, "run_dir_key": run_dir_key, "issue_number": issue_number, "issue_url": issue_url, "reviewer": "unknown"})
        elif not matched_any and (issue_number or issue_url):
            reviewer = "Main agent" if any(str(stable_id).startswith("oos-accepted-main-agent:") for stable_id in stable_ids) else "unknown"
            run_key = run_dir_key or run_dir.name
            identity = (run_key, tuple(stable_ids) or issue_url or issue_number)
            rows.append({"run_id": run_dir.name, "run_dir_key": run_dir_key, "identity": identity, "stable_id": stable_ids[0] if stable_ids else "", "issue_number": issue_number, "issue_url": issue_url, "reviewer": reviewer, "title": record.get("title") or "Recovered OOS disposition"})
    return rows


def _fetch_filed_oos_issue_details( *,repo: str, issue_numbers: set[int]) -> dict[int, dict[str, Any]]:
    details: dict[int, dict[str, Any]] = {}
    fields = "number,title,body,state,url,closedAt,stateReason,labels,closedByPullRequestsReferences,comments"
    for number in sorted(issue_numbers):
        result = subprocess.run(  # lint-subprocess-via-runner: ok mirrors existing gh issue view helper in this module
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


def _ground_truth_targeted_fetch_degraded(filed_issue_details: Mapping[int, Mapping[str, Any]]) -> str | None:
    return "targeted_fetch_degraded" if any(detail.get("__fetch_failed__") for detail in filed_issue_details.values()) else None


def _ground_truth_issue_enrichment_degraded(issues: Sequence[Mapping[str, Any]]) -> str | None:
    degraded: set[str] = set()
    for issue in issues:
        fields = issue.get("_larch_degraded_fields") or []
        if isinstance(fields, list):
            for field in fields:
                text = str(field).strip()
                if text:
                    degraded.add(text)
    if not degraded:
        return None
    return "bulk_issue_fields_degraded:" + ",".join(sorted(degraded))


def _incentive_issue_from_sources(
    *,
    issues: Sequence[Mapping[str, Any]],
    filed_issue_details: Mapping[int, Mapping[str, Any]] | None,
) -> Mapping[str, Any] | None:
    index = _merged_issue_index(issues=issues, filed_issue_details=filed_issue_details or {})
    issue = index.get(GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER)
    if issue is None:
        return None
    if issue.get("__fetch_failed__") and not any(
        issue_number(bulk_issue) == GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER for bulk_issue in issues
    ):
        return None
    return issue


def _incentive_issue_from_gh(*, repo: str) -> Mapping[str, Any] | None:
    result = subprocess.run(  # lint-subprocess-via-runner: ok mirrors existing gh issue view helper in this module
        [
            "gh",
            "issue",
            "view",
            str(GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER),
            "--repo",
            repo,
            "--json",
            "state,stateReason,closedByPullRequestsReferences",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        parsed = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _ground_truth_calibration_incentive_shipped(
    *,
    issues: Sequence[Mapping[str, Any]],
    filed_issue_details: Mapping[int, Mapping[str, Any]] | None = None,
    repo: str | None = None,
) -> tuple[bool, str]:
    issue = _incentive_issue_from_sources(issues=issues, filed_issue_details=filed_issue_details)
    if issue is None and repo:
        issue = _incentive_issue_from_gh(repo=repo)
    if issue is None:
        return False, "calibration_incentive_check_unavailable"
    closed = str(issue.get("state") or "").upper() == "CLOSED"
    refs = issue.get("closedByPullRequestsReferences") or []
    has_pr_refs = isinstance(refs, list) and bool(refs)
    if closed and has_pr_refs and not _has_not_planned_signal(issue):
        return True, ""
    return False, "calibration_incentive_not_shipped"


def _append_design_accepted_block_records( *,
    records: list[dict[str, Any]],
    run_dir: Path,
    log_root: Path | None = None,
    seen_identities: set[tuple[Any, ...]],
) -> None:
    run_dir_key = _resolve_ground_truth_run_dir_key(run_dir, log_root=log_root)
    if log_root and run_dir_key is None:
        return
    run_key = run_dir_key or run_dir.name
    for path in sorted(run_dir.glob("**/oos-accepted-*.md")):
        for block in _parse_oos_accepted_blocks(path, run_dir=run_dir):
            url = str(block.get("filed_url") or "")
            if not url:
                continue
            identity = (run_key, block.get("artifact_relpath"), block.get("heading_id"))
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            records.append({
                "run_id": run_dir.name,
                "run_dir_key": run_dir_key,
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
            records.extend(_join_implement_run_records(run_dir, log_root=log_root))
    for run_dir in sorted((log_root / "design").glob("*")) if (log_root / "design").is_dir() else []:
        if not run_dir.is_dir():
            continue
        accepted = run_dir / "oos-accepted-design.md"
        created_records = _parse_oos_issues_created(
            run_dir / "oos-issues-created.md",
            accepted_design_path=accepted if accepted.is_file() else None,
            log_root=log_root,
        )
        records.extend(created_records)
        seen_identities = {tuple(record.get("identity") or ()) for record in created_records}
        _append_design_accepted_block_records(records=records, run_dir=run_dir, log_root=log_root, seen_identities=seen_identities)
    return records


def _merged_issue_index( *,issues: Sequence[Mapping[str, Any]], filed_issue_details: Mapping[int, Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
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


def fate_adjusted_oos_scoring( *,
    issues: Sequence[Mapping[str, Any]],
    log_root: Path,
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
    index = _merged_issue_index(issues=issues, filed_issue_details=filed_issue_details)
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
        for reviewer in _reviewers_from_label(label=str(record.get("reviewer") or "unknown")):
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


def _ground_truth_run_dir_key(run_dir: Path, *, log_root: Path) -> str | None:
    try:
        return run_dir.relative_to(log_root).as_posix()
    except ValueError:
        return None


def _resolve_ground_truth_run_dir_key(run_dir: Path, *, log_root: Path | None) -> str | None:
    if log_root is None:
        return run_dir.name
    return _ground_truth_run_dir_key(run_dir, log_root=log_root)
