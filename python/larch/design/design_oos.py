"""Python CLI entrypoints for /design OOS filing helpers."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence

from larch.issue import file_oos

OOS_ISSUE_STDOUT_FILE = "oos-issue.stdout.txt"
_GH_ISSUE_URL_RE = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/issues/\d+")
_FILED_URL_LINE_RE = re.compile(r"(?m)^\s*-\s*\*\*Filed[ \t]*URL\*\*[ \t]*:")
_OOS_HEADER_RE = re.compile(r"^###\s+OOS_(\d+):[^\n]*\n", re.MULTILINE)
_ISSUE_URL_KV_RE = re.compile(r"^ISSUE_(\d+)_(URL|DUPLICATE_OF_URL)=(.*)$")
_ISSUE_FAILED_KV_RE = re.compile(r"^ISSUE_(\d+)_FAILED=true$")


def _emit_kv(*, key: str, value: str) -> None:
    print(f"{key}={value}")


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


def _run_cli(*args: str, capture: bool = False, stderr_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    root = _plugin_root()
    command = [sys.executable, str(root / "python" / "cli.py"), *args]
    if capture:
        return subprocess.run(command, capture_output=True, text=True, check=False)
    if stderr_path:
        with stderr_path.open("w", encoding="utf-8") as stderr_handle:
            return subprocess.run(command, text=True, stdout=subprocess.DEVNULL, stderr=stderr_handle, check=False)
    return subprocess.run(command, text=True, check=False)


def _require_design_tmpdir(argv: Sequence[str], *, prog: str) -> Path | None:
    parser = argparse.ArgumentParser(prog=prog, add_help=False)
    _ = parser.add_argument("--design-tmpdir")
    _ = parser.add_argument("--issue-number")
    _ = parser.add_argument("--issue-stdout-file")
    _ = parser.add_argument("--clear-cross-session-cache", action="store_true")
    try:
        args, _extra = parser.parse_known_args(list(argv))
    except SystemExit:
        return None
    design_tmpdir_str = args.design_tmpdir or os.environ.get("DESIGN_TMPDIR", "")
    if not design_tmpdir_str:
        print(f"{prog}: DESIGN_TMPDIR unset", file=sys.stderr)
        return None
    design_tmpdir = Path(design_tmpdir_str)
    if not design_tmpdir.is_dir():
        print(f"{prog}: DESIGN_TMPDIR not a directory", file=sys.stderr)
        return None
    return design_tmpdir


def _extract_unfiled_blocks(text: str) -> str:
    indices: list[int] = [match.start() for match in _OOS_HEADER_RE.finditer(text)]
    if not indices:
        return ""
    blocks: list[str] = []
    for index, start in enumerate(indices):
        end = indices[index + 1] if index + 1 < len(indices) else len(text)
        block = text[start:end]
        if _FILED_URL_LINE_RE.search(block):
            continue
        blocks.append(block.rstrip("\n"))
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n"


def _count_non_security_blocks(text: str) -> int:
    if not text.strip():
        return 0
    return file_oos._count_non_security_markdown(text)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


def _issue_number_from(args_issue_number: str | None) -> str:
    raw = args_issue_number or os.environ.get("ISSUE_NUMBER", "")
    raw = raw.strip()
    if raw.isdigit():
        return raw
    return ""


def _cross_session_cache_path(issue_number: str) -> Path | None:
    if not issue_number:
        return None
    return Path.home() / ".cache" / "larch" / "design-oos-filed" / f"{issue_number}.md"


def _append_warning_log(*, design_tmpdir: Path, site: str, tool: str, detail: str) -> None:
    log = design_tmpdir / "execution-issues.md"
    heading = "### Warnings\n"
    entry = f"- **Step {site} — {tool} failed (exit 1)**:\n  ```\n{detail.rstrip()}\n  ```\n"
    existing = log.read_text(encoding="utf-8") if log.exists() else ""
    if heading not in existing:
        existing = existing.rstrip() + ("\n\n" if existing.strip() else "") + heading
    _ = log.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")


def _load_issue_sentinel_status(design_tmpdir: Path) -> tuple[int, int, int]:
    sentinel = design_tmpdir / "oos-issue-sentinel"
    if not sentinel.is_file():
        return 0, 0, 0
    created = 0
    failed = 0
    deduped = 0
    for line in sentinel.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("ISSUES_CREATED="):
            value = line.split("=", 1)[1].strip()
            created = int(value) if value.isdigit() else 0
        elif line.startswith("ISSUES_FAILED="):
            value = line.split("=", 1)[1].strip()
            failed = int(value) if value.isdigit() else 0
        elif line.startswith("ISSUES_DEDUPLICATED="):
            value = line.split("=", 1)[1].strip()
            deduped = int(value) if value.isdigit() else 0
    return created, failed, deduped


def _block_range(*, text: str, os_number: str) -> tuple[int, int] | None:
    pattern = re.compile(
        rf"(^###\s+OOS_{re.escape(os_number)}:[^\n]*\n)([\s\S]*?)(?=^###\s+OOS_|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return match.start(), match.end()


def _recover_accepted_from_sentinel(*, accepted_text: str, sentinel_text: str) -> tuple[bool, str]:
    maps: list[tuple[str, str]] = []
    plain_urls: list[str] = []
    for line in sentinel_text.splitlines():
        if line.startswith("OOS_FILE_MAP\t"):
            parts = line.split("\t", 2)
            _MIN_MAP_PARTS = 3
            if len(parts) >= _MIN_MAP_PARTS and parts[1].strip() and parts[2].strip():
                maps.append((parts[1].strip(), parts[2].strip()))
            continue
        token = line.strip()
        if token.startswith("http"):
            plain_urls.append(token)
    text = accepted_text
    if maps:
        for os_number, url in maps:
            span = _block_range(text=text, os_number=os_number)
            if span is None:
                return False, accepted_text
            block = text[span[0]:span[1]]
            if _FILED_URL_LINE_RE.search(block):
                continue
            new_block = block.rstrip("\n") + f"\n- **Filed URL**: {url}\n"
            text = text[:span[0]] + new_block + text[span[1]:]
        return True, text
    if not plain_urls:
        return True, text
    blocks = [match.group(0) for match in re.finditer(r"(?ms)^###\s+OOS_(\d+):[^\n]*\n.*?(?=^###\s+OOS_|\Z)", text)]
    unfiled = [block for block in blocks if not _FILED_URL_LINE_RE.search(block)]
    if len(plain_urls) > 1 or len(unfiled) > 1:
        return False, accepted_text
    for url in plain_urls:
        for match in re.finditer(r"(?ms)^###\s+OOS_(\d+):[^\n]*\n.*?(?=^###\s+OOS_|\Z)", text):
            block = match.group(0)
            if _FILED_URL_LINE_RE.search(block):
                continue
            new_block = block.rstrip("\n") + f"\n- **Filed URL**: {url}\n"
            text = text[:match.start()] + new_block + text[match.end():]
            break
    return True, text


def _sync_cross_session_cache(*, design_tmpdir: Path, sentinel: Path, issue_number: str) -> None:
    cache_path = _cross_session_cache_path(issue_number)
    if cache_path is None:
        return
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        _ = tmp.write_text(sentinel.read_text(encoding="utf-8"), encoding="utf-8")
        _ = tmp.replace(cache_path)
    except OSError as exc:
        _append_warning_log(
            design_tmpdir=design_tmpdir,
            site="design file-design-oos cache",
            tool="python/cli.py design file-oos-annotate",
            detail=f"cross-session cache sync failed: {exc}",
        )


def file_oos_prepare_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="design file-oos-prepare", add_help=False)
    _ = parser.add_argument("--design-tmpdir")
    _ = parser.add_argument("--issue-number")
    _ = parser.add_argument("--clear-cross-session-cache", action="store_true")
    try:
        args = parser.parse_args(list(argv))
    except SystemExit:
        return 2
    design_tmpdir = _require_design_tmpdir(argv, prog="design file-oos-prepare")
    if design_tmpdir is None:
        return 2
    accepted = design_tmpdir / "oos-accepted-design.md"
    sentinel = design_tmpdir / "oos-issues-created.md"
    combined = design_tmpdir / "oos-combined.md"
    deps_tsv = design_tmpdir / "oos-intra-batch-deps.tsv"
    order_file = design_tmpdir / "oos-design-filing-order.txt"
    issue_number = _issue_number_from(args.issue_number)
    cache_path = _cross_session_cache_path(issue_number)
    if args.clear_cross_session_cache and cache_path is not None:
        with contextlib.suppress(OSError):
            cache_path.unlink(missing_ok=True)
    if sentinel.is_file() and sentinel.stat().st_size > 0:
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-sentinel")
        return 0
    created, failed, deduped = _load_issue_sentinel_status(design_tmpdir)
    if failed == 0 and (created + deduped) > 0:
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-already-filed-sentinel")
        _emit_kv(
            key="WARN",
            value="file-design-oos prepare: oos-issue-sentinel present "
            f"(ISSUES_CREATED={created} ISSUES_DEDUPLICATED={deduped}) but "
            "oos-issues-created.md absent; skipping re-file",
        )
        return 0
    if cache_path and cache_path.is_file() and cache_path.stat().st_size > 0 and accepted.is_file():
        try:
            sentinel_text = cache_path.read_text(encoding="utf-8")
            _ = sentinel.write_text(sentinel_text, encoding="utf-8")
            ok, recovered = _recover_accepted_from_sentinel(
                accepted_text=accepted.read_text(encoding="utf-8"),
                sentinel_text=sentinel_text,
            )
            if ok:
                _ = accepted.write_text(recovered, encoding="utf-8")
                _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-sentinel")
                return 0
            sentinel.unlink(missing_ok=True)
            _append_warning_log(
                design_tmpdir=design_tmpdir,
                site="design file-design-oos cross-session",
                tool="python/cli.py design file-oos-prepare",
                detail="recover_oos_accepted_from_sentinel_urls failed",
            )
        except OSError as exc:
            _append_warning_log(
                design_tmpdir=design_tmpdir,
                site="design file-design-oos cross-session",
                tool="python/cli.py design file-oos-prepare",
                detail=f"cross-session cache restore failed: {exc}",
            )
    if not accepted.is_file() or accepted.stat().st_size == 0:
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-no-items")
        return 0
    for path in (combined, deps_tsv, order_file):
        path.unlink(missing_ok=True)
    unfiled = _extract_unfiled_blocks(accepted.read_text(encoding="utf-8"))
    if not unfiled.strip():
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-no-items")
        return 0
    _ = combined.write_text(unfiled, encoding="utf-8")
    headers = [match.group(1) for match in _OOS_HEADER_RE.finditer(unfiled)]
    if not headers:
        combined.unlink(missing_ok=True)
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-no-items")
        return 0
    if _count_non_security_blocks(unfiled) == 0:
        combined.unlink(missing_ok=True)
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="skip-all-security")
        return 0
    _ = order_file.write_text("\n".join(headers) + "\n", encoding="utf-8")
    capped = combined.with_suffix(".md.capped.tmp")
    cap_result = _run_cli(
        "oos",
        "issue-cap",
        "--input-file",
        str(combined),
        "--output",
        str(capped),
        capture=True,
    )
    if cap_result.returncode != 0:
        print("file-design-oos: python/cli.py oos issue-cap failed", file=sys.stderr)
        if cap_result.stderr:
            print(cap_result.stderr, end="", file=sys.stderr)
        capped.unlink(missing_ok=True)
        return 2
    _ = capped.replace(combined)
    deps_result = _run_cli(
        "oos",
        "file-conflict-deps",
        "--input-file",
        str(combined),
        "--output",
        str(deps_tsv),
        capture=True,
    )
    deps_available = deps_result.returncode == 0 and deps_tsv.is_file() and deps_tsv.stat().st_size > 0
    if not deps_available:
        deps_tsv.unlink(missing_ok=True)
        print(
            f"file-design-oos: python/cli.py oos file-conflict-deps exit {deps_result.returncode} — graceful-degrade (no caller TSV)",
            file=sys.stderr,
        )
    _emit_kv(key="FILE_DESIGN_OOS_DEPS_AVAILABLE", value="true" if deps_available else "false")
    _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="ready")
    _emit_kv(key="FILE_DESIGN_OOS_COMBINED", value=str(combined))
    _emit_kv(key="FILE_DESIGN_OOS_DEPS_TSV", value=str(deps_tsv))
    _emit_kv(key="FILE_DESIGN_OOS_ORDER", value=str(order_file))
    return 0


def _parse_order(order_file: Path) -> list[str]:
    return [line.strip() for line in order_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse_issue_stdout(stdout_text: str) -> tuple[dict[str, str], dict[str, str], set[str], int]:
    url_by_idx: dict[str, str] = {}
    dup_by_idx: dict[str, str] = {}
    failed: set[str] = set()
    issues_failed_count = 0
    for line in stdout_text.splitlines():
        kv = _ISSUE_URL_KV_RE.match(line)
        if kv:
            idx, kind, value = kv.group(1), kv.group(2), kv.group(3).strip()
            if not value:
                continue
            if kind == "URL":
                url_by_idx[idx] = value
            else:
                dup_by_idx[idx] = value
            continue
        fail = _ISSUE_FAILED_KV_RE.match(line)
        if fail:
            failed.add(fail.group(1))
            continue
        if line.startswith("ISSUES_FAILED="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                issues_failed_count = int(value)
    return url_by_idx, dup_by_idx, failed, issues_failed_count


def file_oos_annotate_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="design file-oos-annotate", add_help=False)
    _ = parser.add_argument("--design-tmpdir")
    _ = parser.add_argument("--issue-stdout-file")
    _ = parser.add_argument("--issue-number")
    try:
        args = parser.parse_args(list(argv))
    except SystemExit:
        return 2
    design_tmpdir = _require_design_tmpdir(argv, prog="design file-oos-annotate")
    if design_tmpdir is None:
        return 2
    issue_stdout_file = args.issue_stdout_file or str(design_tmpdir / OOS_ISSUE_STDOUT_FILE)
    stdout_path = Path(issue_stdout_file)
    if not stdout_path.is_file() or stdout_path.stat().st_size == 0:
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-failed-empty-stdout")
        _emit_kv(
            key="WARN",
            value=f"file-design-oos annotate: issue-stdout-file empty or missing ({issue_stdout_file}); oos-issues-created.md not written",
        )
        print(f"design file-oos-annotate: issue-stdout-file empty or missing ({issue_stdout_file})", file=sys.stderr)
        return 1
    accepted = design_tmpdir / "oos-accepted-design.md"
    order_file = design_tmpdir / "oos-design-filing-order.txt"
    if not order_file.is_file():
        print(f"file-design-oos: missing {order_file} (run prepare first)", file=sys.stderr)
        return 2
    if not accepted.is_file():
        print(f"file-design-oos: missing {accepted}", file=sys.stderr)
        return 2
    order = _parse_order(order_file)
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    url_by_idx, dup_by_idx, failed_indices, issues_failed_count = _parse_issue_stdout(stdout_text)
    accepted_text = accepted.read_text(encoding="utf-8")
    map_lines: list[str] = []
    gh_urls: set[str] = set()
    for index, os_number in enumerate(order, start=1):
        key = str(index)
        if key in failed_indices:
            continue
        url = url_by_idx.get(key) or dup_by_idx.get(key)
        if not url:
            continue
        span = _block_range(text=accepted_text, os_number=os_number)
        if span is None:
            continue
        block = accepted_text[span[0]:span[1]]
        if _FILED_URL_LINE_RE.search(block):
            continue
        new_block = block.rstrip("\n") + f"\n- **Filed URL**: {url}\n"
        accepted_text = accepted_text[:span[0]] + new_block + accepted_text[span[1]:]
        map_lines.append(f"OOS_FILE_MAP\t{os_number}\t{url}")
        gh = _GH_ISSUE_URL_RE.search(url)
        if gh:
            gh_urls.add(gh.group(0))
    _ = accepted.write_text(accepted_text, encoding="utf-8")
    sentinel_lines = [*map_lines, *sorted(gh_urls)]
    sentinel_body = "\n".join(sentinel_lines) + ("\n" if sentinel_lines else "")
    if issues_failed_count > 0:
        _ = (design_tmpdir / "oos-issues-created.partial.md").write_text(sentinel_body, encoding="utf-8")
        (design_tmpdir / "oos-issues-created.md").unlink(missing_ok=True)
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-partial-failed")
        return 1
    complete_sentinel = design_tmpdir / "oos-issues-created.md"
    _ = complete_sentinel.write_text(sentinel_body, encoding="utf-8")
    (design_tmpdir / "oos-issues-created.partial.md").unlink(missing_ok=True)
    _sync_cross_session_cache(design_tmpdir=design_tmpdir, sentinel=complete_sentinel, issue_number=_issue_number_from(args.issue_number))
    _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-complete")
    return 0
