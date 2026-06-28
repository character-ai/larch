"""Accepted-OOS filing pipeline for the Python /implement path."""

# ruff: noqa: SLF001
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from larch import io as larch_io
from typing import Literal, cast

from larch.core import config
from larch.core import proc
from larch.issue import file_oos
from larch.issue import oos_priority

_CLI = Path(__file__).resolve().parents[2] / "cli.py"
_GITHUB_URL_RE = re.compile(r"https://[^\s|)]+/issues/\d+")
_FILED_URL_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s]+/issues/\d+)", re.MULTILINE)
_INTRA_BATCH_DEP_FIELD_COUNT = 2
_BODY_PART_FOOTER = "\n\n*[Continued in a follow-up issue.]*"
_BODY_PART_HEADER = "\n\n*[Continuation of a prior out-of-scope issue.]*\n\n"


@dataclass(frozen=True)
class AcceptedBlock:
    title: str
    body: str
    stable_id: str = ""
    oos_priority: bool = False


@dataclass(frozen=True)
class FiledIssue:
    title: str
    url: str
    duplicate: bool = False
    stable_id: str = ""
    source_stable_ids: tuple[str, ...] = ()
    oos_priority: bool = False


@dataclass(frozen=True)
class BatchResult:
    filed: list[FiledIssue]
    failures: int
    failure_mode: Literal["none", "hard_create", "priority_label", "priority_provision"] = "none"


def _bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _read_kv_file(path: Path) -> dict[str, str]:
    return larch_io.read_kvs(path, cr_strip="strip")


def _run_id(*, tmpdir: Path, state: dict[str, str]) -> str:
    if state.get("RUN_ID"):
        return state["RUN_ID"]
    session_id = tmpdir / "session-id"
    if session_id.is_file():
        return session_id.read_text(encoding="utf-8").strip()
    return "unknown"


def _repo_root() -> Path:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)  # noqa: S607
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return Path.cwd()


def _run_cli(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_CLI), *args], input=input_text, text=True, capture_output=True, check=False)


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, cr_strip="strip")


def _is_security_block(block: str) -> bool:
    normalized = file_oos._strip_md_emphasis(block)  # pyright: ignore[reportPrivateUsage]
    return bool(file_oos._SECURITY_HEADER_RE.search(block) or file_oos._SECURITY_FOCUS_RE.search(normalized))  # pyright: ignore[reportPrivateUsage]


def _stable_source_key(path: Path) -> str:
    return path.stem


def _bare_oos_item_suffix(stable_id: str) -> str | None:
    match = re.fullmatch(r"(?:[^:]+:)?((?:OOS|FINDING)_\d+)", stable_id)
    return match.group(1) if match else None


def _bare_oos_suffix(stable_id: str) -> str | None:
    return _bare_oos_item_suffix(stable_id)


def _stable_identifier(title: str, body: str, *, source_key: str = "") -> str:
    header = re.search(r"^###[ \t]+OOS_(\d+):", body, re.MULTILINE)
    if header:
        bare = f"OOS_{header.group(1)}"
        return f"{source_key}:{bare}" if source_key else bare
    normalized = file_oos._normalize_title(f"{title}\n{body}").lower()  # pyright: ignore[reportPrivateUsage]
    digest = hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"{source_key}:{digest}" if source_key else digest


def _legacy_primary_oos_source() -> str:
    return "oos-accepted-main-agent"


def _normalized_title(text: str) -> str:
    return file_oos._normalize_title(text).lower()  # pyright: ignore[reportPrivateUsage]


def _issue_covers_stable_id(*, issue: FiledIssue, stable_id: str) -> bool:
    if not stable_id:
        return False
    if issue.stable_id == stable_id:
        return True
    if stable_id in issue.source_stable_ids:
        return True
    block_suffix = _bare_oos_suffix(stable_id)
    if block_suffix and block_suffix in issue.source_stable_ids:
        block_source = stable_id.rsplit(":", 1)[0] if ":" in stable_id else ""
        if not block_source or block_source == _legacy_primary_oos_source():
            return True
    issue_suffix = _bare_oos_suffix(issue.stable_id)
    if not issue_suffix or issue_suffix != block_suffix:
        return False
    issue_source = issue.stable_id.rsplit(":", 1)[0] if ":" in issue.stable_id else ""
    block_source = stable_id.rsplit(":", 1)[0] if ":" in stable_id else ""
    if issue_source and block_source:
        return issue_source == block_source
    if not issue_source and block_source:
        return block_source == _legacy_primary_oos_source()
    if issue_source and not block_source:
        return issue_source == _legacy_primary_oos_source()
    return True


def _block_has_filed_url(*, block: AcceptedBlock, url: str) -> bool:
    return bool(url and url in block.body)


def _stable_ids_by_combined_item(*, blocks: list[AcceptedBlock], combined_text: str) -> dict[int, tuple[str, ...]]:
    source_ids = tuple(block.stable_id for block in blocks if block.stable_id)
    combined_count = len(file_oos._parse_oos_blocks(combined_text))  # pyright: ignore[reportPrivateUsage]
    if combined_count <= 0:
        return {}
    if combined_count == len(blocks):
        return {index: (blocks[index - 1].stable_id,) for index in range(1, combined_count + 1) if blocks[index - 1].stable_id}
    if combined_count == 1 and source_ids:
        return {1: source_ids}
    # Combine/cap reduced the batch into fewer blocks, with the final block
    # aggregating every remaining source block. That last block must carry all
    # the tail stable IDs, or a retry matches only the first and re-files the
    # rolled-up remainder.
    mapped: dict[int, tuple[str, ...]] = {}
    for index in range(1, combined_count):
        if index <= len(blocks) and blocks[index - 1].stable_id:
            mapped[index] = (blocks[index - 1].stable_id,)
    tail = tuple(block.stable_id for block in blocks[combined_count - 1 :] if block.stable_id)
    if tail:
        mapped[combined_count] = tail
    return mapped


def _priority_by_combined_item(
    *,
    blocks: list[AcceptedBlock],
    combined_text: str,
    stable_ids_by_item: dict[int, tuple[str, ...]],
) -> dict[int, bool]:
    """Return post-cap item indices that need the high-risk OOS label."""
    combined_blocks = file_oos._parse_oos_blocks(combined_text)  # pyright: ignore[reportPrivateUsage]
    priority_by_stable_id = {block.stable_id: block.oos_priority for block in blocks if block.stable_id}
    priority: dict[int, bool] = {}
    for index, combined_block in enumerate(combined_blocks, start=1):
        source_ids = stable_ids_by_item.get(index, ())
        source_priority = any(priority_by_stable_id.get(stable_id, False) for stable_id in source_ids)
        text_priority = oos_priority.is_high_risk_oos_block(combined_block.body)
        if source_priority or text_priority:
            priority[index] = True
    return priority


def _accepted_input_paths(tmpdir: Path) -> tuple[Path, ...]:
    return (
        tmpdir / "oos-accepted-main-agent.md",
        file_oos.resolve_design_oos_path(tmpdir),
        tmpdir / "oos-accepted-review.md",
    )


def _working_batch(tmpdir: Path) -> tuple[list[AcceptedBlock], list[FiledIssue]]:
    seen: dict[str, int] = {}
    pending_priority_by_title: dict[str, bool] = {}
    blocks: list[AcceptedBlock] = []
    already: list[FiledIssue] = []
    for path in _accepted_input_paths(tmpdir):
        if not path.is_file():
            continue
        source_key = _stable_source_key(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        for item in file_oos._parse_oos_blocks(text):  # pyright: ignore[reportPrivateUsage]
            if _is_security_block(item.body):
                continue
            normalized = _normalized_title(item.title)
            stable_id = _stable_identifier(item.title, item.body, source_key=source_key)
            item_priority = oos_priority.is_high_risk_oos_block(item.body)
            filed_urls = _FILED_URL_LINE_RE.findall(item.body)
            if filed_urls:
                if normalized in seen:
                    index = seen[normalized]
                    blocks[index] = replace(blocks[index], oos_priority=blocks[index].oos_priority or item_priority)
                else:
                    pending_priority_by_title[normalized] = pending_priority_by_title.get(normalized, False) or item_priority
                already.extend(FiledIssue(item.title, url, duplicate=True, stable_id=stable_id, oos_priority=item_priority) for url in filed_urls)
                continue
            if normalized in seen:
                index = seen[normalized]
                blocks[index] = replace(blocks[index], oos_priority=blocks[index].oos_priority or item_priority)
                continue
            seen[normalized] = len(blocks)
            priority = item_priority or pending_priority_by_title.pop(normalized, False)
            blocks.append(AcceptedBlock(item.title, item.body, stable_id, priority))
    return blocks, already


def _render_blocks(blocks: list[AcceptedBlock]) -> str:
    rendered: list[str] = []
    for index, block in enumerate(blocks, start=1):
        rendered.append(re.sub(r"^### OOS_\d+:", f"### OOS_{index}:", block.body, count=1, flags=re.MULTILINE))
    return "\n\n".join(rendered).rstrip() + ("\n" if rendered else "")


def _append_tool_failure(*, tmpdir: Path, site: str, tool: str, rc: int, output: str) -> None:
    file_oos._append_failure_log(log=tmpdir / "execution-issues.md", site=site, tool=tool, rc=rc, output=output)  # pyright: ignore[reportPrivateUsage]


def _append_warning(*, tmpdir: Path, message: str) -> None:
    file_oos._append_run_log_warning(tmpdir=tmpdir, entry=f"- **oos file**: {message}")  # pyright: ignore[reportPrivateUsage]


def _sentinel_urls(tmpdir: Path) -> list[FiledIssue]:
    sentinel = tmpdir / "oos-issues-created.md"
    if not sentinel.is_file():
        return []
    text = sentinel.read_text(encoding="utf-8", errors="replace")
    issues: list[FiledIssue] = []
    stable_by_url: dict[str, str] = {}
    source_stable_ids_by_url: dict[str, tuple[str, ...]] = {}
    title_by_url: dict[str, str] = {}
    current_stable_ids: list[str] = []
    current_title = ""
    for line in text.splitlines():
        stable_match = re.match(r"^[ \t]*-[ \t]+\*\*Stable ID\*\*:[ \t]*(\S+)", line)
        if stable_match:
            current_stable_ids.append(stable_match.group(1))
            continue
        title_match = re.match(r"^[ \t]*-[ \t]+\*\*Title\*\*:[ \t]*(.+)", line)
        if title_match:
            current_title = title_match.group(1).strip()
            current_stable_ids = []
            continue
        filed_match = _FILED_URL_LINE_RE.search(line)
        if filed_match:
            url = filed_match.group(1)
            stable_by_url[url] = current_stable_ids[0] if current_stable_ids else ""
            source_stable_ids_by_url[url] = tuple(current_stable_ids)
            title_by_url[url] = current_title
            current_stable_ids = []
            continue
        table_match = re.match(r"^\|[ \t]*(.*?)[ \t]*\|[ \t]*#[0-9]+[ \t]*\|[ \t]*(https://[^|]+/issues/\d+)[ \t]*\|", line)
        if table_match and not table_match.group(1).startswith("OOS title"):
            title_by_url.setdefault(table_match.group(2).strip(), table_match.group(1).strip())
    issues = [
        FiledIssue(
            title_by_url.get(url) or "Recovered OOS disposition",
            url,
            duplicate=True,
            stable_id=stable_by_url.get(url, ""),
            source_stable_ids=source_stable_ids_by_url.get(url, ()),
        )
        for url in _GITHUB_URL_RE.findall(text)
    ]
    return _dedupe_filed(issues)


def _ndjson_filed_evidence(*, tmpdir: Path, run_id: str) -> list[FiledIssue]:
    path = tmpdir / "larch-logs" / "implement" / run_id / "oos-issues.ndjson"
    if not path.is_file():
        return []
    issues: list[FiledIssue] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            raw_item: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        item = cast("dict[str, object]", raw_item) if isinstance(raw_item, dict) else {}
        body = str(item.get("body", ""))
        urls = _FILED_URL_LINE_RE.findall(body) or _GITHUB_URL_RE.findall(body)
        title_match = re.search(r"^[ \t]*-[ \t]+\*\*Title\*\*:[ \t]*(.+)$", body, re.MULTILINE)
        stable_ids = re.findall(r"^[ \t]*-[ \t]+\*\*Stable ID\*\*:[ \t]*(\S+)", body, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Recovered OOS disposition"
        stable_id = stable_ids[0] if stable_ids else ""
        issues.extend(
            FiledIssue(title, url, duplicate=True, stable_id=stable_id, source_stable_ids=tuple(stable_ids))
            for url in urls
        )
    return _dedupe_filed(issues)


def _persisted_filed_evidence(*, tmpdir: Path, run_id: str) -> list[FiledIssue]:
    return _dedupe_filed([*_sentinel_urls(tmpdir), *_ndjson_filed_evidence(tmpdir=tmpdir, run_id=run_id)])


def _dedupe_filed(filed: list[FiledIssue]) -> list[FiledIssue]:
    seen_urls: set[str] = set()
    deduped: list[FiledIssue] = []
    for issue in filed:
        if issue.url in seen_urls:
            continue
        seen_urls.add(issue.url)
        deduped.append(issue)
    return deduped


def _issue_matches_block(issue: FiledIssue, block: AcceptedBlock, *, allow_title_match: bool = True) -> bool:
    if _issue_covers_stable_id(issue=issue, stable_id=block.stable_id):
        return True
    if _block_has_filed_url(block=block, url=issue.url):
        return True
    if not allow_title_match:
        return False
    return _normalized_title(issue.title) == _normalized_title(block.title)


def _split_persisted_matches(*, blocks: list[AcceptedBlock], persisted: list[FiledIssue]) -> tuple[list[AcceptedBlock], list[FiledIssue]]:
    title_counts: dict[str, int] = {}
    for block in blocks:
        key = _normalized_title(block.title)
        title_counts[key] = title_counts.get(key, 0) + 1
    remaining: list[AcceptedBlock] = []
    matched: list[FiledIssue] = []
    used_urls: set[str] = set()
    for block in blocks:
        allow_title_match = title_counts.get(_normalized_title(block.title), 0) == 1
        match = next(
            (
                issue
                for issue in persisted
                if (issue.url not in used_urls or _issue_covers_stable_id(issue=issue, stable_id=block.stable_id))
                and _issue_matches_block(issue, block, allow_title_match=allow_title_match)
            ),
            None,
        )
        if match is None:
            remaining.append(block)
            continue
        used_urls.add(match.url)
        matched.append(match)
    return remaining, matched


def _materialize_sentinel_recovery_evidence(*, tmpdir: Path, filed: list[FiledIssue]) -> None:
    if any(path.is_file() for path in _accepted_input_paths(tmpdir)):
        return
    path = tmpdir / "oos-accepted-main-agent.md"
    blocks: list[str] = []
    for index, issue in enumerate(filed, start=1):
        title = issue.title if issue.title and issue.title != "Recovered OOS disposition" else f"Recovered OOS disposition {index}"
        blocks.append(
            f"### OOS_{index}: {title}\n"
            "- **Description**: Recovered already filed OOS disposition from prior sentinel evidence.\n"
            f"- **Filed URL**: {issue.url}\n"
            f"- **Stable ID**: {issue.stable_id or f'OOS_{index}'}\n"
            "- **Phase**: implement\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


def _run_disposition_checkpoint(tmpdir: Path) -> subprocess.CompletedProcess[str]:
    return _run_cli(["oos", "disposition-checkpoint", "--implement-tmpdir", str(tmpdir)])


def _after_checkpoint(
    tmpdir: Path,
    run_id: str,
    filed: list[FiledIssue],
    *,
    status: str,
    accepted_count: int,
    filed_count: int | None = None,
    stamp_value: bool = True,
) -> tuple[int, dict[str, object]]:
    checkpoint = _run_disposition_checkpoint(tmpdir)
    urls = [issue.url for issue in filed]
    if checkpoint.returncode != 0:
        try:
            stamped = _stamp_manifest(tmpdir, run_id, value=False)
        except RuntimeError:
            stamped = False
        return checkpoint.returncode or 1, {
            "status": "disposition_checkpoint_failed",
            "accepted_count": accepted_count,
            "filed_count": len(filed) if filed_count is None else filed_count,
            "deduplicated_count": len([issue for issue in filed if issue.duplicate]),
            "urls": urls,
            "run_statistics_written": False,
            "step9a1_stamped": stamped,
        }
    stats = _write_run_statistics(tmpdir=tmpdir, run_id=run_id, filed_count=len(filed) if filed_count is None else filed_count)
    try:
        stamped = _stamp_manifest(tmpdir, run_id, value=stamp_value)
    except RuntimeError:
        stamped = False
    return 0, {
        "status": status,
        "accepted_count": accepted_count,
        "filed_count": len(filed) if filed_count is None else filed_count,
        "deduplicated_count": len([issue for issue in filed if issue.duplicate]),
        "urls": urls,
        "run_statistics_written": stats.is_file(),
        "step9a1_stamped": stamped,
    }


def _codex_available() -> bool:
    false_like = {"false", "0", "no"}
    for name in ("LARCH_OOS_CODEX_BINARY_FOUND", "CODEX_BINARY_FOUND"):
        raw = os.environ.get(name, "").lower()
        if raw in {"true", "1", "yes"}:
            return True
        if raw in false_like:
            return False
    return shutil.which("codex") is not None


def _valid_combined_output(*, text: str, original_count: int) -> bool:
    if not text.strip():
        return False
    try:
        file_oos._validate_issue_cap_input(text)  # pyright: ignore[reportPrivateUsage]
    except ValueError:
        return False
    count = len(file_oos._parse_oos_blocks(text))  # pyright: ignore[reportPrivateUsage]
    return 0 < count <= original_count


def _maybe_combine_with_codex(tmpdir: Path, text: str, *, codex_timeout: int) -> str:
    original_count = len(file_oos._parse_oos_blocks(text))  # pyright: ignore[reportPrivateUsage]
    if original_count <= 1:
        return text
    input_path = tmpdir / "oos-combine-input.md"
    output_path = tmpdir / "oos-combine-codex-output.md"
    prompt_path = tmpdir / "oos-combine-prompt.md"
    input_path.write_text(text, encoding="utf-8")
    prompt_path.write_text(
        "Aggressively combine accepted out-of-scope observations unless they are clearly unrelated.\n"
        "Return only valid markdown blocks shaped as `### OOS_N:` items.\n"
        "Preserve actionable details and do not increase the item count.\n\n"
        f"Input file: {input_path}\n\n"
        "## Batch markdown\n\n"
        f"{text.rstrip()}\n",
        encoding="utf-8",
    )
    if not _codex_available():
        _append_warning(tmpdir=tmpdir, message="Codex unavailable; filing the pre-combine OOS batch.")
        return text
    result = _run_cli(
        [
            "agent",
            "launch-codex-exec",
            "--output",
            str(output_path),
            "--timeout",
            str(codex_timeout),
            "--prompt-file",
            str(prompt_path),
            "--sandbox",
            "read-only",
            "--workdir",
            str(_repo_root()),
            "--add-dir",
            str(tmpdir),
        ],
    )
    if result.returncode != 0 or not output_path.is_file():
        _append_warning(tmpdir=tmpdir, message="Codex combine failed; filing the pre-combine OOS batch.")
        return text
    combined = output_path.read_text(encoding="utf-8", errors="replace")
    if not _valid_combined_output(text=combined, original_count=original_count):
        _append_warning(tmpdir=tmpdir, message="Codex combine output was invalid; filing the pre-combine OOS batch.")
        return text
    return combined


def _wrap_oos_body(body: str, *, reviewer: str, phase: str, vote: str) -> str:
    return (
        "## Out-of-Scope Observation\n\n"
        f"**Surfaced by**: {reviewer or 'N/A'}\n"
        f"**Phase**: {phase or 'implement'}\n"
        f"**Vote tally**: {vote or 'N/A'}\n\n"
        "## Description\n\n"
        f"{body.rstrip()}\n\n"
        "---\n"
        "*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*\n"
    )


def _parse_intra_batch_deps(path: Path) -> list[tuple[int, int]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    edges: list[tuple[int, int]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == _INTRA_BATCH_DEP_FIELD_COUNT and parts[0].isdigit() and parts[1].isdigit():
            edges.append((int(parts[0]), int(parts[1])))
    return edges


def _topological_create_order(*, total: int, edges: list[tuple[int, int]]) -> list[int]:
    if total <= 0:
        return []
    if not edges:
        return list(range(1, total + 1))
    blocked_by: dict[int, set[int]] = {index: set() for index in range(1, total + 1)}
    blocks: dict[int, set[int]] = {index: set() for index in range(1, total + 1)}
    for blocker, blocked in edges:
        if not (1 <= blocker <= total and 1 <= blocked <= total) or blocker == blocked:
            continue
        blocked_by[blocked].add(blocker)
        blocks[blocker].add(blocked)
    ready = sorted(index for index in range(1, total + 1) if not blocked_by[index])
    order: list[int] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for dependent in sorted(blocks[current]):
            blocked_by[dependent].discard(current)
            if not blocked_by[dependent]:
                ready.append(dependent)
        ready.sort()
    if len(order) != total:
        return list(range(1, total + 1))
    return order


def _probe_tracking_blocker(*, tmpdir: Path, repo: str, issue_number: str) -> bool:
    if not issue_number or not issue_number.isdigit():
        return True
    if not repo:
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="blocker probe", rc=1, output="missing repo for --blocked-by-issue probe")
        return False
    gh_path = shutil.which("gh")
    if gh_path is None:
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="blocker probe", rc=1, output="missing gh for --blocked-by-issue probe")
        return False
    result = subprocess.run(
        [gh_path, "api", f"/repos/{repo}/issues/{issue_number}", "--jq", ".number"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip().isdigit():
        detail = (result.stderr or result.stdout or "blocker issue probe failed").strip()
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="gh api blocker probe", rc=result.returncode, output=detail)
        return False
    return True


def _run_gh(args: list[str]) -> proc.CommandResult:
    return proc.run(args)


def _ensure_priority_label(*, tmpdir: Path, repo: str) -> bool:
    if not repo:
        _append_tool_failure(
            tmpdir=tmpdir,
            site="step-9a1-oos-file",
            tool="gh label create",
            rc=1,
            output="missing repo for oos-correctness label provisioning",
        )
        return False
    result = _run_gh(oos_priority.label_create_argv(repo=repo))
    if result.returncode == 0:
        return True
    _append_tool_failure(
        tmpdir=tmpdir,
        site="step-9a1-oos-file",
        tool="gh label create",
        rc=result.returncode or 1,
        output=result.stderr or result.stdout or "oos-correctness label provisioning failed",
    )
    return False


def _apply_priority_label(*, tmpdir: Path, url: str, repo: str) -> bool:
    number = oos_priority.issue_number_from_url(url)
    if not repo or not number:
        detail = "missing repo for oos-correctness label application" if not repo else f"could not parse issue number from {url}"
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="gh issue edit", rc=1, output=detail)
        return False
    result = _run_gh(oos_priority.label_edit_argv(number, repo=repo))
    if result.returncode == 0:
        return True
    _append_tool_failure(
        tmpdir=tmpdir,
        site="step-9a1-oos-file",
        tool="gh issue edit",
        rc=result.returncode or 1,
        output=result.stderr or result.stdout or f"oos-correctness label application failed for {url}",
    )
    return False


def _cleanup_created_issues(
    _tmpdir: Path,
    filed: list[FiledIssue],
    *,
    repo: str,
    only: Callable[[FiledIssue], bool] | None = None,
) -> None:
    for issue in filed:
        if only is not None and not only(issue):
            continue
        if issue.url.startswith("skipped://") or issue.duplicate:
            continue
        number = issue.url.rsplit("/", 1)[-1]
        if not number.isdigit():
            continue
        _ = _run_cli(["issue", "cleanup-failed", "--issue-number", number, *([] if not repo else ["--repo", repo])])


def _body_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def _truncate_utf8(*, text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _split_to_github_limit(body: str) -> list[str]:
    limit = config.GITHUB_ISSUE_BODY_MAX_BYTES
    if _body_bytes(body) <= limit:
        return [body]
    chunks: list[str] = []
    remaining = body
    while remaining:
        if not chunks:
            max_content = limit - _body_bytes(_BODY_PART_FOOTER)
            content = _truncate_utf8(text=remaining, max_bytes=max(0, max_content))
            remaining = remaining[len(content) :]
            chunk = content + (_BODY_PART_FOOTER if remaining else "")
        else:
            header_budget = _body_bytes(_BODY_PART_HEADER)
            if _body_bytes(remaining) + header_budget <= limit:
                chunk = _BODY_PART_HEADER + remaining
                remaining = ""
            else:
                footer_budget = _body_bytes(_BODY_PART_FOOTER) if remaining else 0
                max_content = limit - header_budget - footer_budget
                content = _truncate_utf8(text=remaining, max_bytes=max(0, max_content))
                remaining = remaining[len(content) :]
                chunk = _BODY_PART_HEADER + content + (_BODY_PART_FOOTER if remaining else "")
        chunks.append(chunk)
    return chunks


def _body_files_for_item(*, tmpdir: Path, item_index: int, fields: dict[str, str]) -> list[Path]:
    raw_path = Path(fields.get(f"ITEM_{item_index}_BODY_FILE", ""))
    body = raw_path.read_text(encoding="utf-8", errors="replace") if raw_path.is_file() else ""
    body = file_oos._sanitize_public_text(body)  # pyright: ignore[reportPrivateUsage]
    reviewer = file_oos._sanitize_public_text(fields.get(f"ITEM_{item_index}_REVIEWER", ""))  # pyright: ignore[reportPrivateUsage]
    phase = file_oos._sanitize_public_text(fields.get(f"ITEM_{item_index}_PHASE", "implement"))  # pyright: ignore[reportPrivateUsage]
    vote = file_oos._sanitize_public_text(fields.get(f"ITEM_{item_index}_VOTE_TALLY", "N/A"))  # pyright: ignore[reportPrivateUsage]
    if reviewer or phase or vote:
        body = _wrap_oos_body(body, reviewer=reviewer, phase=phase, vote=vote)
    out_dir = tmpdir / "oos-issue-bodies"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for part_index, part_body in enumerate(_split_to_github_limit(body), start=1):
        out = out_dir / f"oos-body-{item_index}-part{part_index}.txt"
        out.write_text(part_body, encoding="utf-8")
        paths.append(out)
    return paths


def _apply_intra_batch_edges(
    tmpdir: Path,
    item_edges: list[tuple[int, int]],
    issue_numbers: dict[int, str],
    filed: list[FiledIssue],
    *,
    repo: str,
) -> bool:
    """File intra-batch blocker edges; clean up and return False on failure."""
    for blocker_index, blocked_index in item_edges:
        blocker_number = issue_numbers.get(blocker_index, "")
        blocked_number = issue_numbers.get(blocked_index, "")
        if not blocker_number.isdigit() or not blocked_number.isdigit():
            continue
        intra = _run_cli(
            [
                "issue",
                "add-blocked-by",
                "--client-issue",
                blocked_number,
                "--blocker-issue",
                blocker_number,
                *([] if not repo else ["--repo", repo]),
            ],
        )
        intra_kv = _parse_kv(intra.stdout)
        if intra.returncode != 0 or intra_kv.get("BLOCKED_BY_FAILED") == "true":
            detail = intra_kv.get("ERROR") or intra.stderr or intra.stdout or "intra-batch add-blocked-by failed"
            _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="issue add-blocked-by", rc=intra.returncode or 1, output=detail)
            _cleanup_created_issues(tmpdir, filed, repo=repo)
            return False
    return True


def _run_issue_batch(
    tmpdir: Path,
    combined: Path,
    *,
    repo: str,
    issue_number: str,
    deps_path: Path | None = None,
    stable_ids_by_item: dict[int, tuple[str, ...]] | None = None,
    priority_by_item: dict[int, bool] | None = None,
) -> BatchResult:
    bodies_dir = tmpdir / "oos-issue-bodies"
    bodies_dir.mkdir(parents=True, exist_ok=True)
    sanitized_input = bodies_dir / "oos-combined-sanitized.md"
    sanitized_input.write_text(file_oos._sanitize_public_text(combined.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")  # pyright: ignore[reportPrivateUsage]

    parsed = _run_cli(["issue", "parse-input", "--input-file", str(sanitized_input), "--output-dir", str(bodies_dir)])
    if parsed.returncode != 0:
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="issue parse-input", rc=parsed.returncode, output=parsed.stderr or parsed.stdout)
        return BatchResult([], 1, "hard_create")
    fields = _parse_kv(parsed.stdout)
    total = int(fields.get("ITEMS_TOTAL", "0") or "0")
    if not _probe_tracking_blocker(tmpdir=tmpdir, repo=repo, issue_number=issue_number):
        return BatchResult([], 1, "hard_create")

    intra_batch_edges = _parse_intra_batch_deps(deps_path) if deps_path is not None else []
    create_order = _topological_create_order(total=total, edges=intra_batch_edges)
    issue_numbers: dict[int, str] = {}

    filed: list[FiledIssue] = []
    failures = 0
    failure_mode: Literal["none", "hard_create", "priority_label", "priority_provision"] = "none"
    priority_label_ready: bool | None = None
    for item_index in create_order:
        title = file_oos._sanitize_public_text(fields.get(f"ITEM_{item_index}_TITLE", "")).strip()  # pyright: ignore[reportPrivateUsage]
        # Never publish an empty public issue: if the parser flagged this item
        # malformed (no/empty Description body), skip filing and fail loud
        # instead of creating an issue with a blank `## Description` (#5260).
        if fields.get(f"ITEM_{item_index}_MALFORMED", "") == "true":
            detail = f"skipped malformed accepted-OOS item (empty/unparseable Description); not filing empty public issue: {title or f'item {item_index}'}"
            _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="issue create-one", rc=1, output=detail)
            continue
        item_priority = bool(priority_by_item and priority_by_item.get(item_index, False))
        if item_priority and priority_label_ready is None:
            priority_label_ready = _ensure_priority_label(tmpdir=tmpdir, repo=repo)
        if item_priority and priority_label_ready is False:
            failures += 1
            failure_mode = "priority_provision"
            continue
        body_files = _body_files_for_item(tmpdir=tmpdir, item_index=item_index, fields=fields)
        source_ids = stable_ids_by_item.get(item_index, ()) if stable_ids_by_item else ()
        primary_stable = source_ids[0] if source_ids else f"OOS_{item_index}"
        total_parts = len(body_files)
        for part_index, body_file in enumerate(body_files, start=1):
            part_title = title if total_parts == 1 else f"{title} (part {part_index}/{total_parts})"
            args = [
                "issue",
                "create-one",
                "--title",
                part_title,
                "--title-prefix",
                "[OOS]",
                "--body-file",
                str(body_file),
            ]
            if repo:
                args.extend(["--repo", repo])
            if item_priority:
                args.extend(["--label", oos_priority.OOS_CORRECTNESS_LABEL])
            created = _run_cli(args)
            kv = _parse_kv(created.stdout)
            if created.returncode != 0 or kv.get("ISSUE_FAILED") == "true":
                failures += 1
                _cleanup_created_issues(tmpdir, filed, repo=repo)
                return BatchResult(filed, failures, "hard_create")
            url = kv.get("ISSUE_URL") or kv.get(f"ISSUE_{item_index}_URL") or kv.get("ISSUE_DUPLICATE_OF_URL") or kv.get(f"ISSUE_{item_index}_DUPLICATE_OF_URL")
            duplicate = bool(kv.get("ISSUE_DUPLICATE_OF_URL") or kv.get(f"ISSUE_{item_index}_DUPLICATE_OF_URL"))
            filed_issue: FiledIssue | None = None
            if url:
                part_stable = primary_stable if part_index == 1 else f"{primary_stable}:part{part_index}"
                part_source_ids = source_ids if part_index == 1 else ()
                filed_issue = FiledIssue(part_title, url, duplicate, part_stable, part_source_ids)
                if item_priority and not _apply_priority_label(tmpdir=tmpdir, url=url, repo=repo):
                    failures += 1
                    failure_mode = "priority_label"
                    if not duplicate:
                        _cleanup_created_issues(
                            tmpdir,
                            [filed_issue],
                            repo=repo,
                            only=lambda candidate, failed_url=url: candidate.url == failed_url and not candidate.duplicate,
                        )
                    continue
                filed.append(filed_issue)
            number = kv.get("ISSUE_NUMBER") or ""
            if part_index == 1 and number.isdigit():
                issue_numbers[item_index] = number
            if issue_number and number.isdigit():
                blocked = _run_cli(["issue", "add-blocked-by", "--client-issue", number, "--blocker-issue", issue_number, *([] if not repo else ["--repo", repo])])
                blocked_kv = _parse_kv(blocked.stdout)
                if blocked.returncode != 0 or blocked_kv.get("BLOCKED_BY_FAILED") == "true":
                    detail = blocked_kv.get("ERROR") or blocked.stderr or blocked.stdout or "add-blocked-by failed"
                    _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="issue add-blocked-by", rc=blocked.returncode or 1, output=detail)
                    _cleanup_created_issues(tmpdir, filed, repo=repo)
                    return BatchResult(filed, 1, "hard_create")
        item_edges = [edge for edge in intra_batch_edges if edge[1] == item_index]
        if not _apply_intra_batch_edges(tmpdir, item_edges, issue_numbers, filed, repo=repo):
            return BatchResult(filed, 1, "hard_create")
    return BatchResult(filed, failures, failure_mode)


def _write_sentinel(*, tmpdir: Path, filed: list[FiledIssue]) -> None:
    lines = ["| OOS title | Issue | URL |", "|---|---|---|"]
    for issue in filed:
        number = issue.url.rsplit("/", 1)[-1]
        lines.append(f"| {issue.title} | #{number} | {issue.url} |")
    lines.append("")
    for issue in filed:
        lines.append(f"- **Title**: {issue.title}")
        stable_ids = issue.source_stable_ids or ((issue.stable_id,) if issue.stable_id else ())
        lines.extend(f"- **Stable ID**: {stable_id}" for stable_id in stable_ids)
        lines.append(f"- **Filed URL**: {issue.url}")
    lines.append(f"- **Filed**: {len(filed)}")
    (tmpdir / "oos-issues-created.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_oos_ndjson(tmpdir: Path, run_id: str, filed: list[FiledIssue], *, status: str = "Filed") -> Path:
    run_dir = tmpdir / "larch-logs" / "implement" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "oos-issues.ndjson"
    records: list[str] = []
    for issue in filed:
        stable_ids = issue.source_stable_ids or ((issue.stable_id,) if issue.stable_id else ())
        stable_lines = "".join(f"\n- **Stable ID**: {stable_id}" for stable_id in stable_ids)
        body = f"## Accepted / Out-of-Scope Observations\n\n- **Disposition**: {status}\n- **Filed URL**: {issue.url}\n- **Title**: {issue.title}{stable_lines}"
        record = {"phase": "implement", "step": "9a.1", "category": "OOS", "body": file_oos._sanitize_public_text(body)}  # pyright: ignore[reportPrivateUsage]
        records.append(json.dumps(record, separators=(",", ":")))
    path.write_text(("\n".join(records) + "\n") if records else "", encoding="utf-8")
    return path


def _priority_urls_from_combined_order(*, combined_path: Path, filed: list[FiledIssue]) -> set[str]:
    if not combined_path.is_file():
        return set()
    combined_text = combined_path.read_text(encoding="utf-8", errors="replace")
    combined_blocks = file_oos._parse_oos_blocks(combined_text)  # pyright: ignore[reportPrivateUsage]
    priority_indices = {
        index
        for index, block in enumerate(combined_blocks, start=1)
        if oos_priority.is_high_risk_oos_block(block.body)
    }
    if not priority_indices:
        return set()
    real_filed = [issue for issue in filed if not issue.url.startswith("skipped://")]
    if len(real_filed) == 1:
        return {real_filed[0].url}
    if len(real_filed) == len(combined_blocks):
        return {issue.url for index, issue in enumerate(real_filed, start=1) if index in priority_indices}
    return set()


def _priority_urls_from_blocks(*, filed: list[FiledIssue], blocks: list[AcceptedBlock]) -> set[str]:
    urls: set[str] = set()
    for issue in filed:
        if issue.url.startswith("skipped://"):
            continue
        if issue.oos_priority:
            urls.add(issue.url)
            continue
        for block in blocks:
            if not (block.oos_priority or oos_priority.is_high_risk_oos_block(block.body)):
                continue
            if _issue_matches_block(issue, block) or _block_has_filed_url(block=block, url=issue.url):
                urls.add(issue.url)
                break
    return urls


def _backfill_priority_labels_from_sentinel(
    *,
    tmpdir: Path,
    repo: str,
    combined_path: Path,
    persisted: list[FiledIssue],
    already: Sequence[FiledIssue] = (),
    blocks: Sequence[AcceptedBlock] = (),
) -> bool:
    filed = _dedupe_filed([*persisted, *already])
    if not filed:
        return True
    priority_urls = _priority_urls_from_blocks(filed=filed, blocks=list(blocks))
    priority_urls.update(_priority_urls_from_combined_order(combined_path=combined_path, filed=filed))
    if not priority_urls:
        return True
    if not _ensure_priority_label(tmpdir=tmpdir, repo=repo):
        return False
    ok = True
    for url in sorted(priority_urls):
        ok = _apply_priority_label(tmpdir=tmpdir, url=url, repo=repo) and ok
    return ok


def _write_run_statistics(*, tmpdir: Path, run_id: str, filed_count: int) -> Path:
    path = tmpdir / "larch-logs" / "implement" / run_id / "run-statistics.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"Run {run_id}: {filed_count} OOS issue(s) filed.\n", encoding="utf-8")
    return path


def _stamp_manifest(tmpdir: Path, run_id: str, *, value: bool) -> bool:
    manifest = tmpdir / "larch-logs" / "implement" / run_id / "manifest.json"
    if not manifest.is_file():
        return False
    result = _run_cli(
        [
            "run-log",
            "manifest",
            "--log-root",
            str(tmpdir / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            run_id,
            "--field",
            f"steps_ran.step9a1={'true' if value else 'false'}",
        ],
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "manifest update failed").strip()
        raise RuntimeError(f"run-log manifest steps_ran.step9a1 update failed: {detail[:300]}")
    return True


def _file(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    tmpdir = Path(args.implement_tmpdir)
    state = _read_kv_file(path=tmpdir / "ship-pr-state.sh")
    state = state | {k: v for k, v in {"REPO": args.repo or "", "ISSUE_NUMBER": str(args.issue_number or "")}.items() if v}
    run_id = _run_id(tmpdir=tmpdir, state=state)
    repo = str(args.repo or state.get("REPO", ""))
    issue_number = str(args.issue_number or state.get("ISSUE_NUMBER", ""))
    forked = _bool(state.get("FORKED_TARGET", "false"))
    repo_unavailable = _bool(state.get("REPO_UNAVAILABLE", "false"))
    security_sidecar = tmpdir / "security-oos-observations.md"
    if security_sidecar.is_file() and security_sidecar.stat().st_size > 0:
        msg = "security-routed OOS requires private SECURITY.md disposition before public OOS filing"
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="oos file", rc=2, output=msg)
        return 2, {"status": "security_sidecar_present", "accepted_count": 0, "filed_count": 0, "deduplicated_count": 0, "urls": [], "run_statistics_written": False, "step9a1_stamped": False}

    manifest_path = Path(state.get("MANIFEST_PATH", ""))
    if manifest_path.is_file():
        try:
            _ = file_oos.materialize_manifest_oos(manifest_path, tmpdir)
        except (TypeError, OSError, RuntimeError, ValueError) as exc:
            _append_warning(tmpdir=tmpdir, message=f"manifest OOS materialization failed: {exc}")

    all_blocks, already = _working_batch(tmpdir)
    accepted_count = len(all_blocks) + len(already)
    persisted = _persisted_filed_evidence(tmpdir=tmpdir, run_id=run_id)
    blocks, matched = _split_persisted_matches(blocks=all_blocks, persisted=persisted)
    already = _dedupe_filed([*already, *matched])
    if (persisted or already) and not forked and not repo_unavailable:
        backfilled = _backfill_priority_labels_from_sentinel(
            tmpdir=tmpdir,
            repo=repo,
            combined_path=tmpdir / "oos-combined.md",
            persisted=persisted,
            already=already,
            blocks=all_blocks,
        )
        if not backfilled:
            filed = _dedupe_filed([*persisted, *already])
            return 1, {
                "status": "priority_label_backfill_failed",
                "accepted_count": accepted_count,
                "filed_count": len(filed),
                "deduplicated_count": len([issue for issue in filed if issue.duplicate]),
                "urls": [issue.url for issue in filed],
                "run_statistics_written": False,
                "step9a1_stamped": False,
            }
    if persisted and not blocks and not already:
        filed = persisted
        _materialize_sentinel_recovery_evidence(tmpdir=tmpdir, filed=filed)
        _write_oos_ndjson(tmpdir, run_id, filed, status="Recovered from sentinel")
        return _after_checkpoint(tmpdir, run_id, filed, status="idempotent", accepted_count=max(accepted_count, len(filed)), stamp_value=True)

    if not blocks:
        filed = _dedupe_filed([*persisted, *already]) if persisted else already
        if filed:
            _write_oos_ndjson(tmpdir, run_id, filed, status="Already filed")
        return _after_checkpoint(tmpdir, run_id, filed, status="empty" if not filed else "already_filed", accepted_count=accepted_count, stamp_value=True)

    if forked or repo_unavailable:
        status = "Skipped — repo unavailable" if repo_unavailable else "Skipped — forked target"
        filed = [FiledIssue(block.title, f"skipped://oos/{index}", stable_id=block.stable_id) for index, block in enumerate(blocks, start=1)]
        _write_oos_ndjson(tmpdir, run_id, filed, status=status)
        return _after_checkpoint(tmpdir, run_id, filed, status="skipped", accepted_count=accepted_count, filed_count=0, stamp_value=True)

    combined_text = _maybe_combine_with_codex(tmpdir, _render_blocks(blocks), codex_timeout=int(args.codex_timeout))
    combined = tmpdir / "oos-combined.md"
    combined.write_text(combined_text, encoding="utf-8")
    try:
        file_oos.issue_cap(combined)
    except (OSError, RuntimeError, ValueError) as exc:
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="oos issue-cap", rc=1, output=str(exc))
        return 1, {"status": "issue_cap_failed", "accepted_count": accepted_count, "filed_count": 0, "deduplicated_count": 0, "urls": [], "run_statistics_written": False, "step9a1_stamped": False}
    deps = tmpdir / "oos-intra-batch-deps.tsv"
    deps_result = _run_cli(["oos", "file-conflict-deps", "--input-file", str(combined), "--output", str(deps)])
    deps_path: Path | None = None
    if deps_result.returncode == 0:
        if deps.is_file() and deps.stat().st_size > 0:
            deps_path = deps
    else:
        warning = (
            f"**⚠ /implement: oos-file-conflict pre-pass failed (exit {deps_result.returncode}) — "
            "proceeding without caller-supplied serialization edges; review accepted-OOS Descriptions "
            "before greenlighting parallel workers**"
        )
        _append_warning(tmpdir=tmpdir, message=warning)
        detail = deps_result.stderr or deps_result.stdout or warning
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="oos file-conflict-deps", rc=deps_result.returncode or 1, output=detail)
        if deps_result.returncode == 1:
            deps.unlink(missing_ok=True)
    # issue_cap may have rewritten `combined` in place (rolling surplus blocks
    # into one aggregate). Map stable IDs from the post-cap file the batch
    # actually files, not the pre-cap `combined_text`, so the aggregate issue
    # records every rolled-up source stable ID.
    post_cap_text = combined.read_text(encoding="utf-8", errors="replace")
    stable_ids_by_item = _stable_ids_by_combined_item(blocks=blocks, combined_text=post_cap_text)
    priority_by_item = _priority_by_combined_item(blocks=blocks, combined_text=post_cap_text, stable_ids_by_item=stable_ids_by_item)
    batch = _run_issue_batch(
        tmpdir,
        combined,
        repo=repo,
        issue_number=issue_number,
        deps_path=deps_path,
        stable_ids_by_item=stable_ids_by_item,
        priority_by_item=priority_by_item,
    )
    if batch.failures:
        _append_tool_failure(tmpdir=tmpdir, site="step-9a1-oos-file", tool="issue create-one", rc=1, output=f"ISSUES_FAILED={batch.failures}")
        if batch.failure_mode in {"priority_label", "priority_provision"} and batch.filed:
            filed = _dedupe_filed([*persisted, *already, *batch.filed])
            _write_sentinel(tmpdir=tmpdir, filed=filed)
            _write_oos_ndjson(tmpdir, run_id, filed, status="Priority label partial failure")
            return 1, {
                "status": f"{batch.failure_mode}_partial_failure",
                "accepted_count": accepted_count,
                "filed_count": len(filed),
                "deduplicated_count": len([issue for issue in filed if issue.duplicate]),
                "urls": [issue.url for issue in filed],
                "run_statistics_written": False,
                "step9a1_stamped": False,
            }
        return 1, {"status": "issue_batch_failed", "failure_mode": batch.failure_mode, "accepted_count": accepted_count, "filed_count": len(batch.filed), "deduplicated_count": len([issue for issue in batch.filed if issue.duplicate]), "urls": [issue.url for issue in batch.filed], "run_statistics_written": False, "step9a1_stamped": False}
    filed = _dedupe_filed([*persisted, *already, *batch.filed])
    _write_sentinel(tmpdir=tmpdir, filed=filed)
    _write_oos_ndjson(tmpdir, run_id, filed)
    return _after_checkpoint(tmpdir, run_id, filed, status="filed", accepted_count=accepted_count, stamp_value=True)


def cmd_file(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos file")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--repo", default="")
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--codex-timeout", default="300")
    try:
        args = parser.parse_args(argv)
        rc, payload = _file(args)
    except (OSError, RuntimeError, ValueError) as exc:
        rc = 1
        payload = {"status": "error", "error": str(exc), "accepted_count": 0, "filed_count": 0, "deduplicated_count": 0, "urls": [], "run_statistics_written": False, "step9a1_stamped": False}
    print(json.dumps(payload, separators=(",", ":")))
    return rc


if __name__ == "__main__":
    raise SystemExit(cmd_file())
