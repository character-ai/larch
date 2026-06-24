"""Post-ship OOS detection and idempotency support.

Responsibilities:
1. Detect accepted, non-security OOS blocks across upstream inputs.
2. Enforce idempotency via the oos-issues-created.md sentinel.
3. Classify carve-outs (forked, repo_unavailable, security).

The actual GitHub issue creation and semantic dedup remain with the /issue
pipeline (LLM) invoked by the orchestrator.  This module prepares the
to-file set and exposes the sentinel-based idempotency check so the
orchestrator can avoid re-filing across same-session retries.
"""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
from itertools import pairwise
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NamedTuple, cast

import larch_io
import config
import run_logs
import voting
from issue_create import ParsedItem, parse_issue_input
from redact import redact


# ---------------------------------------------------------------------------
# Constants (moved from config to keep OOS-specific tunables here)
# ---------------------------------------------------------------------------
INLINE_TRIAGE_MARKER: str = config.INLINE_TRIAGE_MARKER
OOS_FILED_URL_FIELD: str = config.OOS_FILED_URL_FIELD


class IssueCapInvalidEnv(ValueError):
    """Raised when issue-cap environment knobs are invalid."""

# ---------------------------------------------------------------------------
# Regexes (ported from oos.py)
# ---------------------------------------------------------------------------
_OOS_HEADER_RE = re.compile(
    r"^###\s+(?:OOS_|FINDING_\d+:.*\[(?:OUT_OF_SCOPE|OOS)\])",
    re.MULTILINE,
)
_FOCUS_AREA_LINE_RE = re.compile(
    r"^[ \t-]*(?:[-*][ \t]*)?(?:\*\*)?focus[- \t]*area(?:\*\*)?[ \t]*[:=][ \t]*"
    r"security([-a-zA-Z0-9 _]*)(\s|$|\(|#|\.|,)",
    re.IGNORECASE | re.MULTILINE,
)
_SECURITY_FOCUS_RE = _FOCUS_AREA_LINE_RE
_SECURITY_HEADER_RE = re.compile(
    r"^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*"
    r"(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
    r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# GitHub URL helper
# ---------------------------------------------------------------------------
def _github_issue_url_pattern() -> re.Pattern[str]:
    gh_host = os.environ.get("GH_HOST", "github.com")
    if gh_host and gh_host != "github.com":
        esc = re.escape(gh_host)
        host = f"(?:{esc}|github\\.com)"
    else:
        host = r"github\.com"
    return re.compile(
        rf"https://{host}/[^/\s]+/[^/\s]+/issues/\d+",
    )


# ---------------------------------------------------------------------------
# Block-counting (ported from oos.py; includes #3550 legacy-header support)
# ---------------------------------------------------------------------------
def _count_non_security_markdown(text: str) -> int:
    """Count non-security accepted OOS blocks in markdown text.

    Blocks start on canonical ``### OOS_`` headers and on legacy tagged
    ``### FINDING_N: [OUT_OF_SCOPE]`` headers (tag required — bare
    ``### FINDING_N:`` stays in-scope; #3550).
    """
    count = 0
    in_block = False
    security = False
    for line in text.splitlines():
        if _OOS_HEADER_RE.match(line):
            if in_block and not security:
                count += 1
            in_block = True
            security = bool(_SECURITY_HEADER_RE.match(line))
            continue
        normalized = line.replace("`", "").replace("*", "")
        if in_block and _SECURITY_FOCUS_RE.match(normalized):
            security = True
    if in_block and not security:
        count += 1
    return count


def count_non_security(accepted_paths: tuple[str, ...]) -> int:
    """Count non-security accepted OOS blocks across markdown files."""
    total = 0
    for path in accepted_paths:
        file_path = Path(path)
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        if _OOS_HEADER_RE.search(text):
            total += _count_non_security_markdown(text)
    return total


# ---------------------------------------------------------------------------
# Idempotency: sentinel-based URL recovery
# ---------------------------------------------------------------------------
def read_filed_urls_from_sentinel(sentinel_path: str | None) -> list[str]:
    """Return GitHub issue URLs already recorded in the sentinel file."""
    if not sentinel_path or not Path(sentinel_path).is_file():
        return []
    url_re = _github_issue_url_pattern()
    text = Path(sentinel_path).read_text(encoding="utf-8")
    return url_re.findall(text)


# ---------------------------------------------------------------------------
# Accepted-OOS path resolution (bash checkpoint order)
# ---------------------------------------------------------------------------
def resolve_design_oos_path(tmpdir: Path) -> Path:
    """Resolve accepted design OOS path in bash checkpoint order."""
    design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
    if design_tmpdir:
        design_path = Path(design_tmpdir) / "oos-accepted-design.md"
        if design_path.is_file():
            return design_path
    exported = tmpdir / "design-export" / "oos-accepted-design.md"
    if exported.is_file():
        return exported
    return tmpdir / "oos-accepted-design.md"


def accepted_oos_paths(tmpdir: Path) -> tuple[str, ...]:
    """Return the canonical accepted-OOS file paths for the given tmpdir."""
    design_path = resolve_design_oos_path(tmpdir)
    return tuple(
        str(p)
        for p in (
            tmpdir / "oos-accepted-review.md",
            tmpdir / "oos-accepted-main-agent.md",
            design_path,
        )
    )


# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------
class OosStatus(NamedTuple):
    non_security_count: int
    already_filed: bool
    carve_out: bool
    security_present: bool


def detect(
    tmpdir: Path,
    *,
    forked: bool = False,
    repo_unavailable: bool = False,
) -> OosStatus:
    """Return OOS detection status for the current run."""
    if forked or repo_unavailable:
        return OosStatus(
            non_security_count=0,
            already_filed=False,
            carve_out=True,
            security_present=False,
        )

    sentinel = tmpdir / "oos-issues-created.md"
    already_filed = bool(read_filed_urls_from_sentinel(str(sentinel)))

    security_oos = tmpdir / "security-oos-observations.md"
    security_present = security_oos.is_file() and security_oos.stat().st_size > 0

    paths = accepted_oos_paths(tmpdir)
    non_sec = count_non_security(paths)

    return OosStatus(
        non_security_count=non_sec,
        already_filed=already_filed,
        carve_out=False,
        security_present=security_present,
    )



# ---------------------------------------------------------------------------
# C4c OOS helper ports
# ---------------------------------------------------------------------------

_INTERNAL_URL_RE = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|"
    r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|"
    r"\[?(?:fc[0-9a-f]{2}:|fd[0-9a-f]{2}:|fe80:)|"
    r"[^\s/]+\.(?:internal|local|corp|lan|intranet|test|example|invalid))[^\s]*"
    r"|\b(?:localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|"
    r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|"
    r"[^\s/]+\.(?:internal|local|corp|lan|intranet))\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-]?[0-9]{3}[ .-]?[0-9]{4}")
_SSN_RE = re.compile(r"[0-9]{3}-[0-9]{2}-[0-9]{4}")
_ACCOUNT_RE = re.compile(r"\b(?:account|user|customer|employee|tenant|org)[_-]?[A-Za-z0-9]{8,}\b", re.IGNORECASE)
_OOS_BLOCK_RE = re.compile(r"(?ms)^###\s+OOS_(\d+):\s*(.*?)$(.*?)(?=^###\s+OOS_\d+:|\Z)")
_STRICT_FILED_RE = re.compile(r"^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s]+/issues/\d+)(?:[ \t].*)?$", re.MULTILINE)
_REJECTED_MARKER_RE = re.compile(r"OOS_\d+")
_INLINE_TRIAGE_RE = re.compile(r"Inline-triage rule")
_FILE_REF_RE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?)"
    r"(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?"
)


def _strip_md_emphasis(text: str) -> str:
    return text.replace("`", "").replace("*", "")


def _sanitize_public_text(text: str) -> str:
    text = redact(text)
    text = _INTERNAL_URL_RE.sub("<INTERNAL-URL>", text)
    text = _EMAIL_RE.sub("<REDACTED-PII>", text)
    text = _SSN_RE.sub("<REDACTED-PII>", text)
    text = _PHONE_RE.sub("<REDACTED-PII>", text)
    return _ACCOUNT_RE.sub("<REDACTED-PII>", text)


def _normalize_title(text: object) -> str:
    cleaned = _sanitize_public_text(str(text or ""))
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _write_description_lines(description: object) -> list[str]:
    sanitized = _sanitize_public_text(str(description or ""))
    lines = sanitized.splitlines() or [""]
    out: list[str] = []
    for index, line in enumerate(lines):
        if index == 0:
            out.append(f"- **Description**: {line}")
        else:
            out.append(f"  {line}")
    return out


def _security_signal(description: object, focus_area: object = "") -> bool:
    if focus_area and _FOCUS_AREA_LINE_RE.search(f"- **focus-area**: {focus_area}\n"):
        return True
    return bool(_FOCUS_AREA_LINE_RE.search(_strip_md_emphasis(str(description or ""))))


def _load_manifest_observations(path: Path, *, count_only: bool = False) -> list[dict[str, object]]:
    try:
        raw_data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest must be readable JSON: {exc}") from exc
    if not isinstance(raw_data, dict):
        raise TypeError("manifest must be a JSON object")
    data = cast("dict[str, object]", raw_data)
    observations = data.get("oos_observations", [])
    if observations is None:
        observations = []
    if not isinstance(observations, list):
        raise TypeError("oos_observations must be an array")
    observations = cast("list[object]", observations)
    if count_only:
        return cast("list[dict[str, object]]", observations)
    out: list[dict[str, object]] = []
    for index, item in enumerate(observations, start=1):
        if not isinstance(item, dict):
            raise TypeError(f"oos_observations[{index}] must be a JSON object")
        out.append(cast("dict[str, object]", item))
    return out


def _existing_oos_titles(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    titles: set[str] = set()
    for match in re.finditer(r"^### OOS_\d+:[ \t]*(.*?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE):
        titles.add(_normalize_title(match.group(1)).lower())
    return titles


def _next_oos_number(path: Path) -> int:
    if not path.is_file():
        return 1
    max_n = 0
    for match in re.finditer(r"^### OOS_(\d+):", path.read_text(encoding="utf-8"), re.MULTILINE):
        max_n = max(max_n, int(match.group(1)))
    return max_n + 1


def _append_run_log_warning(tmpdir: Path, entry: str) -> None:
    log = tmpdir / "execution-issues.md"
    try:
        run_logs.append_execution_issue(log, "Warnings", entry)
        return
    except Exception as exc:
        _ = exc
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    if entry in text:
        return
    if "### Warnings" not in text:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + "### Warnings\n"
    text = text.rstrip() + f"\n{entry}\n"
    log.write_text(text, encoding="utf-8")


def _security_audit_has_title(path: Path, title: str) -> bool:
    if not path.is_file():
        return False
    wanted = f"### Security OOS: {title}"
    return any(line == wanted for line in path.read_text(encoding="utf-8").splitlines())


def materialize_manifest_oos(manifest_path: Path, implement_tmpdir: Path, *, count_only: bool = False) -> int:
    observations = _load_manifest_observations(manifest_path, count_only=count_only)
    if count_only:
        return len(observations)
    if not observations:
        return 0
    if os.environ.get("LARCH_TEST_MATERIALIZE_FORCE_FAIL") == "true":
        raise RuntimeError("LARCH_TEST_MATERIALIZE_FORCE_FAIL")
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    cli_path = plugin_root / "python" / "cli.py"
    if not cli_path.is_file():
        raise RuntimeError(f"redact secrets missing or not executable: {cli_path}")
    out = implement_tmpdir / "oos-accepted-main-agent.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.touch(exist_ok=True)
    titles = _existing_oos_titles(out)
    next_n = _next_oos_number(out)
    blocks: list[str] = []
    audit = implement_tmpdir / "security-oos-observations.md"
    for index, item in enumerate(observations, start=1):
        title = _normalize_title(item.get("title", ""))
        description = item.get("description", "")
        phase = _normalize_title(item.get("phase", "implement")) or "implement"
        focus_area = item.get("Focus area", item.get("focus-area", item.get("focus_area", "")))
        focus_area_s = _normalize_title(focus_area)
        if not title:
            title = f"Untitled external implementer OOS {index}"
        if _security_signal(description, focus_area_s):
            if not _security_audit_has_title(audit, title):
                had = audit.exists() and audit.stat().st_size > 0
                lines = ([""] if had else []) + [f"### Security OOS: {title}"]
                lines.extend(_write_description_lines(description))
                lines.append(f"- **Phase**: {phase}")
                if focus_area_s:
                    lines.append(f"- **focus-area**: {focus_area_s}")
                lines.append("- **Disposition**: security-routed; not materialized for public OOS filing")
                audit.write_text((audit.read_text(encoding="utf-8") if audit.exists() else "") + "\n".join(lines) + "\n", encoding="utf-8")
                _append_run_log_warning(implement_tmpdir, "- **cli.py oos materialize-manifest**: security-routed manifest OOS retained in security-oos-observations.md")
            continue
        key = title.lower()
        if key in titles:
            continue
        lines = [f"### OOS_{next_n}: {title}"]
        lines.extend(_write_description_lines(description))
        lines.append("- **Reviewer**: External implementer")
        lines.append("- **Vote tally**: N/A — auto-filed per policy")
        lines.append(f"- **Phase**: {phase}")
        if focus_area_s:
            lines.append(f"- **focus-area**: {focus_area_s}")
        blocks.append("\n".join(lines))
        titles.add(key)
        next_n += 1
    if blocks:
        existing = out.read_text(encoding="utf-8")
        sep = "\n\n" if existing.strip() else ""
        out.write_text(existing.rstrip() + sep + "\n\n".join(blocks) + "\n", encoding="utf-8")
    return len(observations)


def materialize_manifest_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos materialize-manifest")
    parser.add_argument("--count-only", action="store_true")
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--implement-tmpdir", required=True)
    try:
        args = parser.parse_args(argv)
        count = materialize_manifest_oos(Path(args.manifest_path), Path(args.implement_tmpdir), count_only=args.count_only)
    except (TypeError, ValueError, RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.count_only:
        print(count)
    return 0


def _github_urls(text: str) -> set[str]:
    return set(_github_issue_url_pattern().findall(text))


def _count_urls_in_files(paths: Iterable[Path], *, strict: bool = False) -> int:
    urls: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if strict:
            urls.update(match.group(1) for match in _STRICT_FILED_RE.finditer(text))
        else:
            urls.update(_github_urls(text))
    return len(urls)


def _count_rejected_from_ndjson(path: Path) -> int:
    if not path.is_file() or path.stat().st_size == 0:
        return 0
    markers: set[str] = set()
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            raw_item: object = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("jq parse failure while reading oos-issues.ndjson; refusing disposition") from exc
        item = cast("dict[str, object]", raw_item) if isinstance(raw_item, dict) else {}
        body = str(item.get("body", ""))
        lower = body.lower()
        if "rejected / out-of-scope" not in lower and "## rejected" not in lower:
            continue
        in_rejected = False
        tail: list[str] = []
        for line in body.splitlines():
            l = line.lower()
            is_rej = bool(re.match(r"^##\s*rejected", l) or "rejected / out-of-scope" in l)
            if is_rej:
                in_rejected = True
                continue
            if in_rejected and line.startswith("##") and not is_rej:
                break
            if in_rejected:
                tail.append(line)
        markers.update(_REJECTED_MARKER_RE.findall("\n".join(tail)))
    return len(markers)


def _count_inline_triage(commit_range: str) -> int:
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)  # noqa: S607
    if repo.returncode != 0:
        raise ValueError("not inside a git work tree (need commit-range scan)")
    root = repo.stdout.strip()
    ok = subprocess.run(["git", "-C", root, "rev-list", "-1", commit_range], text=True, capture_output=True, check=False)  # noqa: S607
    if ok.returncode != 0:
        raise ValueError(f"invalid commit-range: {commit_range}")
    log = subprocess.run(["git", "-C", root, "log", "--format=%B", commit_range], text=True, capture_output=True, check=False)  # noqa: S607
    if log.returncode != 0:
        raise ValueError(f"invalid commit-range: {commit_range}")
    return len(_INLINE_TRIAGE_RE.findall(log.stdout))


def disposition_gate(*, accepted_files: list[Path], filed_url_files: list[Path], filed_url_strict_files: list[Path], commit_range: str, oos_issues_ndjson: Path | None = None, fork_mode: bool = False, repo_unavailable: bool = False) -> int:
    if fork_mode or repo_unavailable:
        return 0
    for path in accepted_files:
        if path.exists() and (not path.is_file() or not os.access(path, os.R_OK)):
            raise ValueError(f"accepted file path is not a readable regular file: {path}")
    if (
        oos_issues_ndjson
        and oos_issues_ndjson.is_file()
        and oos_issues_ndjson.stat().st_size > 0
        and not any(p.is_file() for p in accepted_files)
        and _count_urls_in_files([oos_issues_ndjson]) > 0
    ):
        raise ValueError("oos-issues.ndjson lists filed GitHub issue URLs but no --accepted-files paths exist as regular files (check CSV path list)")
    non_sec = count_non_security(tuple(str(p) for p in accepted_files))
    filed = _count_urls_in_files(filed_url_files + ([oos_issues_ndjson] if oos_issues_ndjson else [])) + _count_urls_in_files(filed_url_strict_files, strict=True)
    rejected = _count_rejected_from_ndjson(oos_issues_ndjson) if oos_issues_ndjson else 0
    inline = _count_inline_triage(commit_range)
    if non_sec == 0 or filed > 0 or inline >= non_sec or rejected >= non_sec:
        return 0
    print(f"oos-disposition-gate: FAIL non_security_oos={non_sec} filed_urls={filed} inline_triage_lines={inline} rejected_oos_markers={rejected} (commit-range {commit_range})", file=sys.stderr)
    return 1


def disposition_gate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos disposition-gate")
    parser.add_argument("--fork-mode", action="store_true")
    parser.add_argument("--repo-unavailable", action="store_true")
    parser.add_argument("--accepted-files")
    parser.add_argument("--filed-urls-file", action="append", default=[])
    parser.add_argument("--filed-urls-strict-file", action="append", default=[])
    parser.add_argument("--oos-issues-ndjson")
    parser.add_argument("--commit-range")
    try:
        args = parser.parse_args(argv)
        if args.fork_mode or args.repo_unavailable:
            return 0
        if not args.accepted_files or not args.commit_range or (not args.filed_urls_file and not args.filed_urls_strict_file):
            parser.print_usage(sys.stderr)
            return 2
        return disposition_gate(
            accepted_files=[Path(p) for p in args.accepted_files.split(",") if p],
            filed_url_files=[Path(p) for p in args.filed_urls_file],
            filed_url_strict_files=[Path(p) for p in args.filed_urls_strict_file],
            oos_issues_ndjson=Path(args.oos_issues_ndjson) if args.oos_issues_ndjson else None,
            commit_range=args.commit_range,
            fork_mode=args.fork_mode,
            repo_unavailable=args.repo_unavailable,
        )
    except ValueError as exc:
        print(f"oos-disposition-gate: {exc}", file=sys.stderr)
        return 2


def _read_kv_file(path: Path) -> dict[str, str]:
    return larch_io.read_kvs(path, default={}, cr_strip="strip")


def resolve_implement_run_id(tmpdir: Path, *, state: dict[str, str] | None = None) -> str:
    if state is None:
        state = _read_kv_file(tmpdir / "ship-pr-state.sh") | _read_kv_file(tmpdir / "finalize-state.sh")
    run_id = state.get("RUN_ID", "")
    if run_id:
        return run_id
    log_root = tmpdir / "larch-logs" / "implement"
    if log_root.is_dir():
        matches = sorted(log_root.glob("*/oos-issues.ndjson"))
        if len(matches) == 1:
            return matches[0].parent.name
    return ""


def resolve_implement_run_id_for_disposition(tmpdir: Path, *, state: dict[str, str] | None = None) -> str:
    run_id = resolve_implement_run_id(tmpdir, state=state)
    if run_id:
        return run_id
    session_id = tmpdir / "session-id"
    if session_id.is_file():
        return session_id.read_text(encoding="utf-8").strip()
    return ""


def _append_failure_log(log: Path, site: str, tool: str, rc: int, output: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"\n### Tool Failures\n- **{site}**: {tool} exited {rc}\n")
        if output:
            handle.write(output.rstrip() + "\n")


def disposition_checkpoint_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos disposition-checkpoint")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--design-tmpdir")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.exists():
        print("oos-disposition-checkpoint: --implement-tmpdir not found", file=sys.stderr)
        return 2
    state = _read_kv_file(tmpdir / "ship-pr-state.sh") | _read_kv_file(tmpdir / "finalize-state.sh")
    forked = state.get("FORKED_TARGET", "false") == "true"
    repo_unavailable = state.get("REPO_UNAVAILABLE", "false") == "true"
    merge_base = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], text=True, capture_output=True, check=False)  # noqa: S607
    if merge_base.returncode == 0 and merge_base.stdout.strip():
        commit_range = f"{merge_base.stdout.strip()}..HEAD"
    else:
        origin_main = subprocess.run(["git", "rev-parse", "--verify", "origin/main"], text=True, capture_output=True, check=False)  # noqa: S607
        if origin_main.returncode == 0:
            commit_range = "origin/main..HEAD"
        else:
            parent = subprocess.run(["git", "rev-parse", "--verify", "HEAD^"], text=True, capture_output=True, check=False)  # noqa: S607
            commit_range = "HEAD^..HEAD" if parent.returncode == 0 else "HEAD"
    run_id = resolve_implement_run_id_for_disposition(tmpdir, state=state)
    ndjson: Path | None = None
    if run_id:
        candidate = tmpdir / "larch-logs" / "implement" / run_id / "oos-issues.ndjson"
        if candidate.is_file():
            ndjson = candidate
    else:
        matches = sorted((tmpdir / "larch-logs" / "implement").glob("*/oos-issues.ndjson"))
        if len(matches) == 1:
            ndjson = matches[0]
        elif len(matches) > 1:
            msg = "implement: ambiguous oos-issues.ndjson without session-id; cannot pass --oos-issues-ndjson"
            (tmpdir / "oos-disposition-checkpoint.stderr.log").write_text(msg + "\n", encoding="utf-8")
            _append_failure_log(tmpdir / "execution-issues.md", "step-8-oos-checkpoint-validation", "oos-disposition-checkpoint", 2, msg)
            return 2
    design = Path(args.design_tmpdir) if args.design_tmpdir else Path(os.environ.get("DESIGN_TMPDIR", "")) if os.environ.get("DESIGN_TMPDIR") else None
    design_path = tmpdir / "oos-accepted-design.md"
    if design and (design / "oos-accepted-design.md").is_file():
        design_path = design / "oos-accepted-design.md"
    elif (tmpdir / "design-export" / "oos-accepted-design.md").is_file():
        design_path = tmpdir / "design-export" / "oos-accepted-design.md"
    accepted = [tmpdir / "oos-accepted-main-agent.md", design_path, tmpdir / "oos-accepted-review.md"]
    filed = [tmpdir / "oos-issues-created.md"]
    strict = [tmpdir / "oos-accepted-main-agent.md", design_path, tmpdir / "oos-accepted-review.md"]
    if not forked and not repo_unavailable:
        security_sidecar = tmpdir / "security-oos-observations.md"
        if security_sidecar.is_file() and security_sidecar.stat().st_size > 0:
            msg = "implement: security-routed manifest OOS requires private SECURITY.md disposition; refusing all-clear checkpoint"
            (tmpdir / "oos-disposition-checkpoint.stderr.log").write_text(msg + "\n", encoding="utf-8")
            _append_failure_log(tmpdir / "execution-issues.md", "step-8-oos-checkpoint-validation", "oos-disposition-checkpoint", 2, msg)
            return 2
        non_sec = count_non_security(tuple(str(p) for p in accepted if p.is_file()))
        if non_sec > 0 and (ndjson is None or not ndjson.is_file()):
            msg = "implement: non-security accepted OOS requires a resolved oos-issues.ndjson path for disposition gate (--oos-issues-ndjson); batch missing or undiscoverable"
            (tmpdir / "oos-disposition-checkpoint.stderr.log").write_text(msg + "\n", encoding="utf-8")
            _append_failure_log(tmpdir / "execution-issues.md", "step-8-oos-checkpoint-validation", "oos-disposition-checkpoint", 2, msg)
            return 2
    try:
        rc = disposition_gate(accepted_files=accepted, filed_url_files=filed, filed_url_strict_files=strict, oos_issues_ndjson=ndjson, commit_range=commit_range, fork_mode=forked, repo_unavailable=repo_unavailable)
    except ValueError as exc:
        msg = str(exc)
        (tmpdir / "oos-disposition-checkpoint.stderr.log").write_text(msg + "\n", encoding="utf-8")
        _append_failure_log(tmpdir / "execution-issues.md", "step-8-oos-checkpoint-validation", "oos-disposition-checkpoint", 2, msg)
        return 2
    if rc != 0:
        _append_failure_log(tmpdir / "execution-issues.md", "step-8-oos-checkpoint", "oos-disposition-gate", rc, "")
    return rc


@dataclass(frozen=True)
class OosItem:
    number: int
    title: str
    body: str


def _parse_oos_blocks(text: str) -> list[OosItem]:
    matches = list(_OOS_BLOCK_RE.finditer(text))
    return [OosItem(int(match.group(1)), match.group(2).strip(), match.group(0).rstrip()) for match in matches]


def _normalize_rollup_text(text: str) -> str:
    cleaned = re.sub(r"[\000-\010\013\014\016-\037\177]", "", text)
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    cleaned = re.sub(r"^[ *_#`]+", "", cleaned)
    cleaned = re.sub(r"[*`]+", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _file_refs_from_body(body: str) -> str:
    refs: list[str] = []
    seen: set[str] = set()
    for match in _FILE_REF_RE.finditer(body):
        candidate = match.group(0).lstrip("*_#` ").rstrip("*_#` ")
        if candidate and candidate not in seen:
            seen.add(candidate)
            refs.append(candidate)
    return " ".join(refs)


def _renumber_oos_headings(text: str) -> str:
    idx = 0
    out: list[str] = []
    for line in text.splitlines():
        if re.match(r"^### OOS_\d+:", line):
            idx += 1
            out.append(re.sub(r"^### OOS_\d+:", f"### OOS_{idx}:", line))
        else:
            out.append(line)
    rendered = "\n".join(out)
    return rendered + ("\n" if text.endswith("\n") else "")


# Embedded rolled-up bodies are indented so their lines never match the
# ^-anchored heading/field regexes in `parse_issue_input` (DESC/REVIEWER/VOTE/
# PHASE and `### OOS_<N>:`), keeping the aggregate one parseable block while
# preserving each combined item's full body verbatim.
_ROLLED_BODY_INDENT = "    "


def _indent_rolled_body(body: str) -> str:
    return "\n".join(f"{_ROLLED_BODY_INDENT}{line}" if line.strip() else "" for line in body.splitlines())


def _aggregate_block(seq: int, items: list[OosItem], *, cap: int) -> str:
    surplus = len(items)
    lines = [
        f"### OOS_{seq}: Aggregated rollup of {surplus} capped OOS items",
        (
            f"- **Description**: Cap {cap} (OOS_ISSUES_PER_RUN_CAP) exceeded; the following {surplus} "
            "items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is "
            "preserved verbatim below:"
        ),
    ]
    for item in items:
        title = _normalize_rollup_text(item.title) or "(no title)"
        file_refs = _file_refs_from_body(item.body)
        lines.append(f"  - **{title}**:" + (f" [Files: {file_refs}]" if file_refs else ""))
        body = item.body.rstrip()
        lines.append(_indent_rolled_body(body) if body.strip() else f"{_ROLLED_BODY_INDENT}(body unavailable)")
    lines.extend(
        [
            "- **Reviewer**: Combined: capped per-run rollup",
            f"- **Vote tally**: N/A — capped rollup of {surplus} entries",
            "- **Phase**: implement",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_issue_cap_input(text: str) -> list[ParsedItem]:
    if not text.strip():
        return []
    items, _mode = parse_issue_input(text)
    if items and not re.search(r"^### OOS_\d+:", text, re.MULTILINE):
        msg = "input is not OOS-shaped (no '### OOS_<N>:' headings)"
        raise ValueError(msg)
    heading_count = len(re.findall(r"^### OOS_\d+:", text, re.MULTILINE))
    if heading_count and len(items) != heading_count:
        msg = f"ITEMS_TOTAL ({len(items)}) != raw '### OOS_<N>:' heading count ({heading_count})"
        raise ValueError(msg)
    return items


def issue_cap(input_file: Path, output: Path | None = None, *, cap: int | None = None) -> None:
    if not input_file.is_file():
        raise FileNotFoundError(f"input file not found: {input_file}")
    if output is not None and input_file.resolve(strict=False) == output.resolve(strict=False):
        raise ValueError("--input-file and --output resolve to the same path")
    if cap is None:
        raw = os.environ.get("OOS_ISSUES_PER_RUN_CAP", "1")
        if not raw.isdigit() or int(raw) <= 0:
            raise IssueCapInvalidEnv("OOS_ISSUES_PER_RUN_CAP must be a positive integer")
        cap = int(raw)
    text = input_file.read_text(encoding="utf-8")
    parsed_items = _validate_issue_cap_input(text)
    raw_items = _parse_oos_blocks(text)
    target = output or input_file
    if not raw_items or len(raw_items) <= cap:
        if output:
            tmp = target.with_suffix(target.suffix + ".tmp")
            try:
                tmp.write_text(text, encoding="utf-8")
                tmp.replace(target)
            finally:
                with contextlib.suppress(FileNotFoundError):
                    tmp.unlink()
        return
    keep_count = max(cap - 1, 0)
    keep = raw_items[:keep_count]
    parsed_roll = parsed_items[keep_count:]
    raw_roll = raw_items[keep_count:]
    roll: list[OosItem] = []
    for index, raw in enumerate(raw_roll):
        parsed = parsed_roll[index] if index < len(parsed_roll) else None
        # Preserve the full raw block (heading + all fields) so the rollup never
        # strips detail; an empty parsed body must not mask the real content.
        roll.append(OosItem(raw.number, parsed.title if parsed else raw.title, raw.body))
    blocks = [item.body for item in keep]
    blocks.append(_aggregate_block(len(blocks) + 1, roll, cap=cap))
    rendered = _renumber_oos_headings("\n\n".join(blocks).rstrip() + "\n")
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        tmp.write_text(rendered, encoding="utf-8")
        tmp.replace(target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


def _unlink_issue_cap_output_on_failure(parser: argparse.ArgumentParser, argv: list[str] | None) -> None:
    if argv is None:
        return
    with contextlib.suppress(SystemExit, FileNotFoundError):
        parsed = parser.parse_args(argv)
        if parsed.output and Path(parsed.input_file).resolve(strict=False) != Path(parsed.output).resolve(strict=False):
            Path(parsed.output).unlink(missing_ok=True)


def issue_cap_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos issue-cap")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output")
    try:
        args = parser.parse_args(argv)
        issue_cap(Path(args.input_file), Path(args.output) if args.output else None)
    except IssueCapInvalidEnv as exc:
        _unlink_issue_cap_output_on_failure(parser, argv)
        print(f"oos-issue-cap: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        _unlink_issue_cap_output_on_failure(parser, argv)
        print(f"oos-issue-cap: {exc}", file=sys.stderr)
        return 1
    return 0


@dataclass(frozen=True)
class FileConflictRecord:
    path: str
    start: int
    end: int
    whole: bool


@dataclass(frozen=True)
class FileConflictEdge:
    left: int
    right: int
    basename: str


class FileConflictGlobalCapExceeded(ValueError):
    """Raised when planned file-conflict TSV rows exceed the global cap."""


class FileConflictInvalidCap(ValueError):
    """Raised when OOS_FILE_CONFLICT_* env values are invalid."""


_FILE_CONFLICT_DEFAULT_CLUSTER_CAP = 200
_FILE_CONFLICT_DEFAULT_GLOBAL_CAP = 500
_FILE_CONFLICT_MIN_COMPONENT_NODES = 2
_FILE_CONFLICT_RANGE_RE = re.compile(r"^(.+):([0-9]+)(-([0-9]+))?$")
_FILE_CONFLICT_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
_FILE_CONFLICT_ANY_RE = re.compile(
    f"(?:{voting.FILE_LINE_REGEXES['any-re']})|(?:{voting.FILE_LINE_REGEXES['extensionless-re']})",
)


def _file_conflict_cap(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    if not raw.isdigit() or int(raw) <= 0:
        raise FileConflictInvalidCap(f"ERROR: {name} must be a positive integer (got: '{raw}')")
    return int(raw)


def _file_conflict_caps() -> tuple[int, int]:
    return (
        _file_conflict_cap("OOS_FILE_CONFLICT_CLUSTER_CAP", _FILE_CONFLICT_DEFAULT_CLUSTER_CAP),
        _file_conflict_cap("OOS_FILE_CONFLICT_GLOBAL_CAP", _FILE_CONFLICT_DEFAULT_GLOBAL_CAP),
    )


def _file_conflict_usage() -> None:
    print("Usage: cli.py oos file-conflict-deps --input-file FILE [--output FILE]", file=sys.stderr)
    print("  When --output is omitted and IMPLEMENT_TMPDIR is set, the output", file=sys.stderr)
    print("  defaults to $IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv.", file=sys.stderr)


def _parse_file_conflict_args(argv: list[str]) -> tuple[Path | None, Path | None, bool]:
    input_file = ""
    output_file = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--input-file" and index + 1 < len(argv):
            input_file = argv[index + 1]
            index += 2
        elif arg == "--output" and index + 1 < len(argv):
            output_file = argv[index + 1]
            index += 2
        else:
            if arg in {"--input-file", "--output"}:
                print(f"ERROR: {arg} requires a value", file=sys.stderr)
            else:
                print(f"Unknown option: {arg}", file=sys.stderr)
            _file_conflict_usage()
            return None, None, False
    if input_file and not output_file and os.environ.get("IMPLEMENT_TMPDIR"):
        output_file = str(Path(os.environ["IMPLEMENT_TMPDIR"]) / "oos-intra-batch-deps.tsv")
    if not input_file or not output_file:
        _file_conflict_usage()
        return None, None, False
    return Path(input_file), Path(output_file), True


def _clean_file_conflict_match(raw: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z.]+", "", raw)
    cleaned = re.sub(r"[^A-Za-z0-9_./:-]+$", "", cleaned)
    return cleaned.removeprefix("./")


def _raw_file_conflict_match_is_unsafe(line: str, match: re.Match[str]) -> bool:
    """Reject traversal syntax the file-line regex can drop via sub-matches."""
    if line[: match.start()].endswith(".."):
        return True
    return ".." in match.group(0)


_TRAVERSAL_DOTDOT_PLACEHOLDER = "\x1e"


def _normalize_file_conflict_body(body: str) -> str:
    protected = body.replace("..", _TRAVERSAL_DOTDOT_PLACEHOLDER)
    normalized = re.sub(r"(^|[^A-Za-z0-9])\./", r"\1", protected)
    normalized = re.sub(r"[,;]", "\n", normalized)
    return normalized.replace(_TRAVERSAL_DOTDOT_PLACEHOLDER, "..")


def _file_conflict_path_is_safe(path: str) -> bool:
    if not path:
        return False
    if path.startswith(("/", "-")):
        return False
    if ".." in path or ":" in path:
        return False
    return bool(_FILE_CONFLICT_SAFE_PATH_RE.fullmatch(path))


def _file_conflict_record(candidate: str) -> FileConflictRecord | None:
    path = candidate
    start = 0
    end = 0
    whole = True
    if match := _FILE_CONFLICT_RANGE_RE.match(candidate):
        path = match.group(1)
        parsed_start = int(match.group(2))
        parsed_end = int(match.group(4) or match.group(2))
        if 0 < parsed_start <= parsed_end:
            start = parsed_start
            end = parsed_end
            whole = False
    path = path.removeprefix("./")
    if not _file_conflict_path_is_safe(path):
        return None
    return FileConflictRecord(path, start, end, whole)


def _item_file_records(item: ParsedItem) -> list[FileConflictRecord]:
    records: set[FileConflictRecord] = set()
    normalized = _normalize_file_conflict_body(item.body)
    for line in normalized.splitlines():
        for match in _FILE_CONFLICT_ANY_RE.finditer(line):
            if _raw_file_conflict_match_is_unsafe(line, match):
                continue
            candidate = _clean_file_conflict_match(match.group(0))
            if not candidate:
                continue
            record = _file_conflict_record(candidate)
            if record is not None:
                records.add(record)
    return sorted(records, key=lambda r: (r.path, r.start, r.end, int(r.whole)))


def _ranges_conflict(left: FileConflictRecord, right: FileConflictRecord) -> bool:
    if left.path != right.path:
        return False
    if left.whole or right.whole:
        return True
    return not (left.start > right.end or right.start > left.end)


def _path_conflicts(left_records: list[FileConflictRecord], right_records: list[FileConflictRecord], path: str) -> bool:
    left_for_path = [record for record in left_records if record.path == path]
    right_for_path = [record for record in right_records if record.path == path]
    if any(record.whole for record in left_for_path) or any(record.whole for record in right_for_path):
        return True
    return any(_ranges_conflict(left, right) for left in left_for_path for right in right_for_path)


def _find_parent(parent: list[int], node: int) -> int:
    root = node
    while parent[root] != root:
        root = parent[root]
    while parent[node] != node:
        next_node = parent[node]
        parent[node] = root
        node = next_node
    return root


def _union_nodes(parent: list[int], left: int, right: int) -> None:
    left_root = _find_parent(parent, left)
    right_root = _find_parent(parent, right)
    if left_root == right_root:
        return
    keep = min(left_root, right_root)
    drop = max(left_root, right_root)
    for node in range(1, len(parent)):
        if _find_parent(parent, node) == drop:
            parent[node] = keep


def _candidate_file_conflict_edges(items: list[ParsedItem]) -> tuple[list[FileConflictEdge], list[int]]:
    records: dict[int, list[FileConflictRecord]] = {}
    for index, item in enumerate(items, start=1):
        records[index] = [] if item.malformed else _item_file_records(item)
    parent = list(range(len(items) + 1))
    candidates: list[FileConflictEdge] = []
    for left in range(1, len(items) + 1):
        for right in range(left + 1, len(items) + 1):
            shared_paths = sorted({record.path for record in records[left]} & {record.path for record in records[right]})
            for path in shared_paths:
                if _path_conflicts(records[left], records[right], path):
                    candidates.append(FileConflictEdge(left, right, PurePosixPath(path).name))
                    _union_nodes(parent, left, right)
                    break
    roots = [_find_parent(parent, index) for index in range(len(parent))]
    return candidates, roots


def _planned_file_conflict_deps(
    items: list[ParsedItem],
    *,
    cluster_cap: int,
    global_cap: int,
) -> list[tuple[int, int]]:
    candidates, roots = _candidate_file_conflict_edges(items)
    nodes_by_root: dict[int, list[int]] = {}
    for index in range(1, len(items) + 1):
        nodes_by_root.setdefault(roots[index], []).append(index)

    planned: list[tuple[int, int]] = []
    for root in sorted(nodes_by_root):
        nodes = sorted(nodes_by_root[root])
        if len(nodes) < _FILE_CONFLICT_MIN_COMPONENT_NODES:
            continue
        node_set = set(nodes)
        cluster_edges = [edge for edge in candidates if edge.left in node_set and edge.right in node_set]
        if len(cluster_edges) > cluster_cap:
            basename_hint = cluster_edges[0].basename if cluster_edges else "unknown"
            print(
                f"**⚠ /implement: oos-file-conflict-deps cluster on {basename_hint} would emit "
                f"{len(cluster_edges)} dependency rows (cap {cluster_cap}, N={len(nodes)}); emitting chain "
                "instead of all-pairs (lower robustness under SCC pruning).**",
                file=sys.stderr,
            )
            planned.extend(pairwise(nodes))
        else:
            planned.extend((edge.left, edge.right) for edge in cluster_edges)
    planned = sorted(set(planned))
    if len(planned) > global_cap:
        raise FileConflictGlobalCapExceeded(
            f"ERROR: oos-file-conflict-deps would emit {len(planned)} rows, exceeding the "
            f"{global_cap}-row --intra-batch-deps-file cap; split the OOS batch",
        )
    return planned


def file_conflict_deps(input_file: Path, *, cluster_cap: int | None = None, global_cap: int | None = None) -> list[tuple[int, int]]:
    if not input_file.is_file():
        raise FileNotFoundError(f"input file not found: {input_file}")
    if cluster_cap is None or global_cap is None:
        env_cluster_cap, env_global_cap = _file_conflict_caps()
        cluster_cap = env_cluster_cap if cluster_cap is None else cluster_cap
        global_cap = env_global_cap if global_cap is None else global_cap
    text = input_file.read_text(encoding="utf-8")
    items, _mode = parse_issue_input(text)
    return _planned_file_conflict_deps(items, cluster_cap=cluster_cap, global_cap=global_cap)


def _write_file_conflict_deps(input_file: Path, output_file: Path, *, cluster_cap: int, global_cap: int) -> None:
    if not input_file.is_file():
        raise FileNotFoundError(f"ERROR: input file not found: {input_file}")
    deps = file_conflict_deps(input_file, cluster_cap=cluster_cap, global_cap=global_cap)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(output_file) + ".tmp")
    tmp.write_text("".join(f"{left}\t{right}\n" for left, right in deps), encoding="utf-8")
    tmp.replace(output_file)


def file_conflict_deps_main(argv: list[str] | None = None) -> int:
    try:
        cluster_cap, global_cap = _file_conflict_caps()
    except FileConflictInvalidCap as exc:
        print(str(exc), file=sys.stderr)
        return 2

    input_file, output_file, ok = _parse_file_conflict_args(list(argv or []))
    if not ok or input_file is None or output_file is None:
        return 1

    tmp = Path(str(output_file) + ".tmp")
    try:
        _write_file_conflict_deps(input_file, output_file, cluster_cap=cluster_cap, global_cap=global_cap)
    except (FileConflictGlobalCapExceeded, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        with contextlib.suppress(OSError):
            tmp.unlink()
        with contextlib.suppress(OSError):
            output_file.unlink()
        return 1
    with contextlib.suppress(OSError):
        tmp.unlink()
    return 0

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="file_oos.py",
        description="Detect accepted non-security OOS blocks for post-ship filing.",
    )
    _ = p.add_argument("--tmpdir", required=True, help="IMPLEMENT_TMPDIR path")
    _ = p.add_argument("--forked", action="store_true", default=False)
    _ = p.add_argument("--repo-unavailable", action="store_true", default=False)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    tmpdir = Path(args.tmpdir)
    status = detect(tmpdir, forked=args.forked, repo_unavailable=args.repo_unavailable)
    result = {
        "non_security_count": status.non_security_count,
        "already_filed": status.already_filed,
        "carve_out": status.carve_out,
        "security_present": status.security_present,
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
