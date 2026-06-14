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
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, cast

import config
import run_logs
from issue_create import parse_issue_input
from redact import redact


# ---------------------------------------------------------------------------
# Constants (moved from config to keep OOS-specific tunables here)
# ---------------------------------------------------------------------------
INLINE_TRIAGE_MARKER: str = config.INLINE_TRIAGE_MARKER
OOS_FILED_URL_FIELD: str = config.OOS_FILED_URL_FIELD
OOS_EXCERPT_MAX_CHARS = 800

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
    with contextlib.suppress(Exception):
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


def _load_manifest_observations(path: Path) -> list[dict[str, object]]:
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
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
    return [cast("dict[str, object]", item) if isinstance(item, dict) else {} for item in observations]


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
    return path.is_file() and f"### Security OOS: {title}" in path.read_text(encoding="utf-8")


def materialize_manifest_oos(manifest_path: Path, implement_tmpdir: Path, *, count_only: bool = False) -> int:
    observations = _load_manifest_observations(manifest_path)
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
                _append_run_log_warning(implement_tmpdir, "- **materialize-manifest-oos.sh**: security-routed manifest OOS retained in security-oos-observations.md")
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
    except (ValueError, RuntimeError, OSError) as exc:
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
            raw_item = json.loads(raw)
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
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value.strip("\r")
    return out


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
    run_id = state.get("RUN_ID", "")
    if not run_id and (tmpdir / "session-id").is_file():
        run_id = (tmpdir / "session-id").read_text(encoding="utf-8").strip()
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


def _aggregate_block(seq: int, items: list[OosItem]) -> str:
    title = f"Aggregated rollup of {len(items)} capped OOS items"
    lines = [f"### OOS_{seq}: {title}", "- **Description**: Multiple OOS items were grouped because this run exceeded the per-run filing cap.", "", "  Rolled-up items:"]
    for item in items:
        excerpt = re.sub(r"\s+", " ", item.body).strip()
        if len(excerpt) > OOS_EXCERPT_MAX_CHARS:
            excerpt = excerpt[: OOS_EXCERPT_MAX_CHARS - 3] + "..."
        lines.append(f"  - OOS_{item.number}: {item.title} — {excerpt}")
    lines.extend(["- **Reviewer**: Combined: capped per-run rollup", "- **Vote tally**: N/A — capped per-run rollup", "- **Phase**: implement"])
    return "\n".join(lines)


def _validate_issue_cap_input(text: str) -> None:
    if not text.strip():
        return
    items, _mode = parse_issue_input(text)
    if items and not re.search(r"^### OOS_\d+:", text, re.MULTILINE):
        msg = "input is not OOS-shaped (no '### OOS_<N>:' headings)"
        raise ValueError(msg)
    heading_count = len(re.findall(r"^### OOS_\d+:", text, re.MULTILINE))
    if items and len(items) != heading_count:
        msg = f"parsed item count ({len(items)}) != raw '### OOS_<N>:' heading count ({heading_count})"
        raise ValueError(msg)


def issue_cap(input_file: Path, output: Path | None = None, *, cap: int | None = None) -> None:
    if cap is None:
        raw = os.environ.get("OOS_ISSUES_PER_RUN_CAP", "1")
        if not raw.isdigit() or int(raw) <= 0:
            raise ValueError("OOS_ISSUES_PER_RUN_CAP must be a positive integer")
        cap = int(raw)
    text = input_file.read_text(encoding="utf-8") if input_file.exists() else ""
    _validate_issue_cap_input(text)
    items = _parse_oos_blocks(text)
    target = output or input_file
    if not items or len(items) <= cap:
        if output:
            target.write_text(text, encoding="utf-8")
        return
    keep = items[: max(cap - 1, 0)]
    roll = items[max(cap - 1, 0):]
    blocks = [item.body for item in keep]
    blocks.append(_aggregate_block(len(blocks) + 1, roll))
    rendered = "\n\n".join(blocks).rstrip() + "\n"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.replace(target)


def issue_cap_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos issue-cap")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output")
    try:
        args = parser.parse_args(argv)
        issue_cap(Path(args.input_file), Path(args.output) if args.output else None)
    except (ValueError, OSError) as exc:
        print(f"oos-issue-cap: {exc}", file=sys.stderr)
        return 1
    return 0


def _item_file_records(item: OosItem) -> list[tuple[str, int, int, bool]]:
    records: list[tuple[str, int, int, bool]] = []
    for match in _FILE_REF_RE.finditer(item.body):
        path = match.group("path")
        if path.startswith(("http/", "https/")):
            continue
        start_s = match.group("start")
        end_s = match.group("end")
        if start_s:
            start = int(start_s)
            end = int(end_s or start_s)
            whole = False
        else:
            start = 1
            end = 10**9
            whole = True
        records.append((path, start, end, whole))
    return records


def _ranges_conflict(left: tuple[str, int, int, bool], right: tuple[str, int, int, bool]) -> bool:
    if left[0] != right[0]:
        return False
    if left[3] or right[3]:
        return True
    return not (left[1] > right[2] or right[1] > left[2])


def file_conflict_deps(input_file: Path) -> list[tuple[int, int]]:
    items = _parse_oos_blocks(input_file.read_text(encoding="utf-8") if input_file.exists() else "")
    records = {item.number: _item_file_records(item) for item in items}
    deps: set[tuple[int, int]] = set()
    for i, left in enumerate(items):
        for right in items[i + 1:]:
            if any(_ranges_conflict(a, b) for a in records[left.number] for b in records[right.number]):
                deps.add((left.number, right.number))
    return sorted(deps)


def file_conflict_deps_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py oos file-conflict-deps")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output")
    try:
        args = parser.parse_args(argv)
        deps = file_conflict_deps(Path(args.input_file))
        text = "".join(f"{a}\t{b}\n" for a, b in deps)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    except OSError as exc:
        print(f"oos-file-conflict-deps: {exc}", file=sys.stderr)
        return 1
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
