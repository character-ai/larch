"""Shared exec-issue and warning detail parsing/rendering."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.core import config
from larch.core import redact

EXEC_CATEGORIES = frozenset({"Tool Failures", "External Reviewer Issues"})
WARN_CATEGORY = "Warnings"
MAX_DISPLAY_LEN = 200
MAX_DEDUPE_KEY_LEN = 500
ASSESSMENT_TIMEOUT_SECONDS = 12
DEFAULT_ASSESSMENT_MODEL = config.EXEC_ISSUE_ASSESSMENT_MODEL_DEFAULT

_SECTION_NONE = "none"
_SECTION_EXEC = "exec"
_SECTION_WARN = "warn"
_BOLD_BULLET_RE = re.compile(r"^- \*\*([^*]+)\*\*:?(.*)$")
_SECTION_HEADING_RE = re.compile(r"^### (Tool Failures|External Reviewer Issues|Warnings)$", re.MULTILINE)


@dataclass(frozen=True)
class IssueEvent:
    label: str
    description: str
    display_text: str
    dedupe_key: str


@dataclass(frozen=True)
class IssueDetail:
    label: str
    description: str
    display_text: str
    count: int


@dataclass(frozen=True)
class IssueDetailGroups:
    exec_issues: tuple[IssueDetail, ...]
    warnings: tuple[IssueDetail, ...]


EMPTY_GROUPS = IssueDetailGroups((), ())


@dataclass(frozen=True)
class LoadResult:
    groups: IssueDetailGroups
    listing_degraded: bool
    degraded_totals: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.degraded_totals is not None and not self.listing_degraded:
            raise ValueError("degraded_totals requires listing_degraded")
        if self.listing_degraded and self.degraded_totals is not None and (self.groups.exec_issues or self.groups.warnings):
            raise ValueError("degraded listings with totals must not carry detail rows")


def _truncate(text: str, limit: int = MAX_DISPLAY_LEN) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _display_from_raw(raw: str) -> str:
    return _truncate(redact.redact_outbound(raw))


def _normalize_key(text: str) -> str:
    return " ".join(text.strip().split())


def _dedupe_key_from_body(body: str) -> str:
    normalized = _normalize_key(body.strip())
    if len(normalized) <= MAX_DEDUPE_KEY_LEN:
        return normalized
    return normalized[: max(0, MAX_DEDUPE_KEY_LEN - 3)].rstrip() + "..."


def _dedupe_key_from_raw(raw: str) -> str:
    return _dedupe_key_from_body(redact.redact_outbound(raw))


def _split_issue_section_lines(text: str) -> tuple[list[str], list[str]]:
    exec_lines: list[str] = []
    warn_lines: list[str] = []
    section = _SECTION_NONE
    in_fence = False
    for line in text.splitlines():
        heading = line[4:].strip() if line.startswith("### ") else ""
        if heading in EXEC_CATEGORIES:
            section = _SECTION_EXEC
            in_fence = False
            continue
        if heading == WARN_CATEGORY:
            section = _SECTION_WARN
            in_fence = False
            continue
        if line.startswith("### "):
            section = _SECTION_NONE
            in_fence = False
            continue
        if line.lstrip().startswith("```"):
            if section == _SECTION_EXEC:
                exec_lines.append(line)
            elif section == _SECTION_WARN:
                warn_lines.append(line)
            in_fence = not in_fence
            continue
        if section == _SECTION_EXEC:
            exec_lines.append(line)
        elif section == _SECTION_WARN:
            warn_lines.append(line)
    return exec_lines, warn_lines


def _count_bullets_outside_fences(section_text: str) -> int:
    in_fence = False
    count = 0
    for line in section_text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith("- "):
            count += 1
    return count


def _parse_bullet_line(line: str) -> IssueEvent | None:
    if not line.startswith("- "):
        return None
    bold = _BOLD_BULLET_RE.match(line)
    if bold:
        label = bold.group(1).strip().rstrip(":").strip()
        description = bold.group(2).strip()
        if description.startswith(":"):
            description = description[1:].strip()
        if not label and not description:
            return None
        raw_display = f"{label}: {description}" if label and description else label or description
        display_text = _display_from_raw(raw_display)
        return IssueEvent(
            label=label,
            description=_display_from_raw(description) if description else "",
            display_text=display_text,
            dedupe_key=_dedupe_key_from_raw(raw_display),
        )
    body = line[2:].strip()
    if not body:
        return None
    display_text = _display_from_raw(body)
    return IssueEvent(label="", description=display_text, display_text=display_text, dedupe_key=_dedupe_key_from_raw(body))


def _parse_section_events(section_text: str) -> list[IssueEvent]:
    events: list[IssueEvent] = []
    in_fence = False
    for line in section_text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        event = _parse_bullet_line(line)
        if event is not None:
            events.append(event)
    return events


def _collapse_events(events: list[IssueEvent]) -> tuple[IssueDetail, ...]:
    order: list[str] = []
    values: dict[str, IssueDetail] = {}
    for event in events:
        existing = values.get(event.dedupe_key)
        if existing is None:
            order.append(event.dedupe_key)
            values[event.dedupe_key] = IssueDetail(event.label, event.description, event.display_text, 1)
        else:
            values[event.dedupe_key] = IssueDetail(
                existing.label,
                existing.description,
                existing.display_text,
                existing.count + 1,
            )
    return tuple(values[key] for key in order)


def parse_markdown_execution_issues(text: str) -> IssueDetailGroups:
    exec_lines, warn_lines = _split_issue_section_lines(text)
    return IssueDetailGroups(
        _collapse_events(_parse_section_events("\n".join(exec_lines))),
        _collapse_events(_parse_section_events("\n".join(warn_lines))),
    )


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _fallback_event(body: str, category: str) -> IssueEvent:
    raw_display = _first_nonempty_line(body) or category
    display_text = _display_from_raw(raw_display)
    return IssueEvent(
        label="",
        description=display_text,
        display_text=display_text,
        dedupe_key=_dedupe_key_from_body(body),
    )


def _events_from_structured_body(body: str, category: str) -> list[IssueEvent]:
    events = _parse_section_events(body)
    if events:
        return events
    return [_fallback_event(body, category)]


def _parse_ndjson_structured_rows(rows: list[dict[str, object]]) -> IssueDetailGroups:
    exec_events: list[IssueEvent] = []
    warn_events: list[IssueEvent] = []
    for row in rows:
        category_obj = row.get("category")
        body_obj = row.get("body")
        category = category_obj if isinstance(category_obj, str) else ""
        body = body_obj if isinstance(body_obj, str) else ""
        if category in EXEC_CATEGORIES:
            exec_events.extend(_events_from_structured_body(body, category))
        elif category == WARN_CATEGORY:
            warn_events.extend(_events_from_structured_body(body, category))
    return IssueDetailGroups(_collapse_events(exec_events), _collapse_events(warn_events))


def legacy_category_string_totals(body_text: str) -> tuple[int, int]:
    exec_n = body_text.count('"category":"Tool Failures"') + body_text.count('"category":"External Reviewer Issues"')
    warn_n = body_text.count('"category":"Warnings"')
    return exec_n, warn_n


def _parse_ndjson_legacy(path: Path) -> LoadResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    parsed: list[object] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError:
            parsed.append(None)
    dict_rows = [cast("dict[str, object]", row) for row in parsed if isinstance(row, dict)]
    all_dicts = bool(parsed) and len(dict_rows) == len(parsed)
    all_categorized = bool(dict_rows) and all(isinstance(row.get("category"), str) for row in dict_rows)
    structured_rows = [row for row in dict_rows if isinstance(row.get("category"), str)]
    if all_dicts and all_categorized:
        return LoadResult(_parse_ndjson_structured_rows(dict_rows), listing_degraded=False)

    body_parts = [
        str(cast("dict[str, object]", row).get("body", ""))
        for row in parsed
        if isinstance(row, dict)
    ]
    body_text = "\n".join(body_parts)
    if _SECTION_HEADING_RE.search(body_text):
        return LoadResult(parse_markdown_execution_issues(body_text), listing_degraded=False)
    if structured_rows:
        return LoadResult(_parse_ndjson_structured_rows(structured_rows), listing_degraded=False)
    return LoadResult(EMPTY_GROUPS, listing_degraded=True, degraded_totals=legacy_category_string_totals(body_text))


def load_issue_detail_groups(tmpdir: Path, *, run_dir: Path | None) -> LoadResult:
    issue_log = tmpdir / "execution-issues.md"
    if issue_log.is_file() and issue_log.stat().st_size > 0:
        return LoadResult(
            parse_markdown_execution_issues(issue_log.read_text(encoding="utf-8", errors="replace")),
            listing_degraded=False,
        )
    if run_dir is not None:
        ndjson = run_dir / "execution-issues.ndjson"
        if ndjson.is_file():
            return _parse_ndjson_legacy(ndjson)
    return LoadResult(EMPTY_GROUPS, listing_degraded=False)


def count_issue_groups(groups: IssueDetailGroups) -> tuple[int, int]:
    return sum(detail.count for detail in groups.exec_issues), sum(detail.count for detail in groups.warnings)


def count_load_result(load_result: LoadResult) -> tuple[int, int]:
    if load_result.listing_degraded and load_result.degraded_totals is not None:
        return load_result.degraded_totals
    return count_issue_groups(load_result.groups)


def _unwrap_claude_json_result(stdout: str) -> str | None:
    try:
        obj: object = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    obj_map = cast("dict[str, object]", obj)
    if obj_map.get("is_error"):
        return None
    value = obj_map.get("result")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _parse_assessments_payload(inner_text: str) -> dict[str, str]:
    try:
        obj: object = json.loads(inner_text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    obj_map = cast("dict[str, object]", obj)
    assessments = obj_map.get("assessments")
    if not isinstance(assessments, list):
        return {}
    parsed: dict[str, str] = {}
    assessment_items = cast("list[object]", assessments)
    for item_obj in assessment_items:
        item = cast("dict[str, object]", item_obj) if isinstance(item_obj, dict) else None
        if item is None:
            continue
        item_id = item.get("id")
        assessment = item.get("assessment")
        if not isinstance(item_id, str) or not isinstance(assessment, str):
            continue
        cleaned = _truncate(assessment, 260)
        if cleaned:
            parsed[item_id] = cleaned
    return parsed


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def _assessment_model() -> str:
    return os.environ.get(config.ENV_LARCH_EXEC_ISSUE_ASSESSMENT_MODEL, DEFAULT_ASSESSMENT_MODEL).strip() or DEFAULT_ASSESSMENT_MODEL


def assess_issue_details(category: str, details: tuple[IssueDetail, ...]) -> dict[str, str]:
    if not details:
        return {}
    rows = [
        {"id": str(index), "display_text": _truncate(redact.redact_outbound(detail.display_text)), "count": detail.count}
        for index, detail in enumerate(details)
    ]
    prompt = (
        "You assess execution-issue materiality for a larch run final summary.\n"
        f"Category: {category}\n"
        "For each item, write one short sentence (max 25 words) on materiality/impact for operators.\n"
        "Return ONLY valid JSON matching this schema:\n"
        '{"assessments": [{"id": "<same id from input>", "assessment": "<one sentence>"}]}\n'
        "Include an assessment entry for every input id. No markdown fences. No extra keys.\n"
        "Input:\n"
        f"{json.dumps(rows, ensure_ascii=False)}\n"
    )
    try:
        with tempfile.TemporaryDirectory() as work_dir:
            work = Path(work_dir)
            prompt_file = work / "prompt.txt"
            output_file = work / "output.txt"
            _ = prompt_file.write_text(prompt, encoding="utf-8")
            cli = _plugin_root() / "python" / "cli.py"
            completed = subprocess.run(
                [
                    sys.executable, str(cli),
                    "agent", "launch-claude-subprocess",
                    "--prompt-file", str(prompt_file),
                    "--output-file", str(output_file),
                    "--timeout", str(ASSESSMENT_TIMEOUT_SECONDS),
                    "--model", _assessment_model(),
                    "--timing-task-kind", "exec-issue-assessment",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=ASSESSMENT_TIMEOUT_SECONDS + 10,
            )
            if completed.returncode != 0 or not output_file.is_file():
                return {}
            inner = output_file.read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if not inner:
        return {}
    return _parse_assessments_payload(inner)


def _render_category(title: str, total: int, details: tuple[IssueDetail, ...], *, assess: bool) -> list[str]:
    lines = [f"{title} ({total}):"]
    assessments = assess_issue_details(title, details) if assess and details else {}
    for index, detail in enumerate(details):
        suffix = f" \u00d7{detail.count}" if detail.count > 1 else ""
        lines.append(f"  {index + 1}. {detail.display_text}{suffix}")
        assessment = assessments.get(str(index), "").strip()
        if assessment:
            lines.append(f"    {assessment}")
    return lines


def render_issue_detail_block(load_result: LoadResult, *, assess: bool = True) -> str:
    exec_total, warning_total = count_load_result(load_result)
    groups = load_result.groups
    if exec_total == 0 and warning_total == 0 and not groups.exec_issues and not groups.warnings:
        return ""
    lines = ["## Exec Issues and Warnings"]
    if load_result.listing_degraded and not groups.exec_issues and not groups.warnings:
        lines.extend([f"Exec Issues ({exec_total}):", f"Warnings ({warning_total}):"])
        return redact.redact_outbound("\n".join(lines).rstrip() + "\n")
    lines.extend(_render_category("Exec Issues", exec_total, groups.exec_issues, assess=assess))
    lines.extend(_render_category("Warnings", warning_total, groups.warnings, assess=assess))
    return redact.redact_outbound("\n".join(lines).rstrip() + "\n")


def build_issue_detail_section(load_result: LoadResult) -> str:
    return render_issue_detail_block(load_result, assess=True)
