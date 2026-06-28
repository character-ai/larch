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

from larch.core import config
from larch.core import proc
from larch.issue import file_oos
from larch.issue import oos_priority

OOS_ISSUE_STDOUT_FILE = "oos-issue.stdout.txt"
_GH_ISSUE_URL_RE = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/issues/\d+")
_FILED_URL_LINE_RE = re.compile(r"(?m)^\s*-\s*\*\*Filed[ \t]*URL\*\*[ \t]*:")
_OOS_HEADER_RE = re.compile(r"^###\s+OOS_(\d+):[^\n]*\n", re.MULTILINE)
_ISSUE_URL_KV_RE = re.compile(r"^ISSUE_(\d+)_(URL|DUPLICATE_OF_URL)=(.*)$")
_ISSUE_FAILED_KV_RE = re.compile(r"^ISSUE_(\d+)_FAILED=true$")
_PRIORITY_PENDING = ".oos-priority-label-pending"
_OOS_FILE_MAP_FIELD_COUNT = 3


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
    _ = parser.add_argument("--repo")
    _ = parser.add_argument("--label-only", action="store_true")
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


def _cross_session_sibling(issue_number: str, suffix: str) -> Path | None:
    cache_path = _cross_session_cache_path(issue_number)
    if cache_path is None:
        return None
    return cache_path.with_name(f"{cache_path.stem}.{suffix}")


def _cross_session_priority_pending_path(issue_number: str) -> Path | None:
    return _cross_session_sibling(issue_number, "priority-pending")


def _cross_session_combined_path(issue_number: str) -> Path | None:
    return _cross_session_sibling(issue_number, "combined.md")


def _cross_session_filing_order_path(issue_number: str) -> Path | None:
    return _cross_session_sibling(issue_number, "filing-order.txt")


def _cross_session_accepted_path(issue_number: str) -> Path | None:
    return _cross_session_sibling(issue_number, "accepted-design.md")


def _atomic_copy_text(*, source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.tmp")
    _ = tmp.write_text(source.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    _ = tmp.replace(dest)


def _write_pending_marker(path: Path) -> None:
    _ = path.write_text("pending\n", encoding="utf-8")


def _sync_label_retry_sidecars(  # noqa: PLR0913
    *,
    design_tmpdir: Path,
    issue_number: str,
    sentinel: Path,
    combined_path: Path,
    order_file: Path | None,
    pending: bool,
    accepted_path: Path | None = None,
) -> None:
    cache_path = _cross_session_cache_path(issue_number)
    pending_path = _cross_session_priority_pending_path(issue_number)
    combined_cache = _cross_session_combined_path(issue_number)
    order_cache = _cross_session_filing_order_path(issue_number)
    accepted_cache = _cross_session_accepted_path(issue_number)
    if cache_path is None:
        return
    try:
        if sentinel.is_file():
            _atomic_copy_text(source=sentinel, dest=cache_path)
        if combined_cache is not None and combined_path.is_file():
            _atomic_copy_text(source=combined_path, dest=combined_cache)
        if order_cache is not None and order_file is not None and order_file.is_file():
            _atomic_copy_text(source=order_file, dest=order_cache)
        if accepted_cache is not None and accepted_path is not None and accepted_path.is_file():
            _atomic_copy_text(source=accepted_path, dest=accepted_cache)
        if pending_path is not None:
            if pending:
                pending_path.parent.mkdir(parents=True, exist_ok=True)
                _write_pending_marker(pending_path)
            else:
                pending_path.unlink(missing_ok=True)
    except OSError as exc:
        _append_warning_log(
            design_tmpdir=design_tmpdir,
            site="design file-design-oos label-retry cache",
            tool="python/cli.py design file-oos-annotate",
            detail=f"label retry sidecar sync failed: {exc}",
        )


def _restore_label_retry_sidecars(*, design_tmpdir: Path, issue_number: str) -> bool:
    cache_path = _cross_session_cache_path(issue_number)
    pending_path = _cross_session_priority_pending_path(issue_number)
    combined_cache = _cross_session_combined_path(issue_number)
    order_cache = _cross_session_filing_order_path(issue_number)
    if cache_path is None or pending_path is None or not pending_path.is_file() or not cache_path.is_file():
        return False
    try:
        _atomic_copy_text(source=cache_path, dest=design_tmpdir / "oos-issues-created.md")
        if combined_cache is not None and combined_cache.is_file():
            _atomic_copy_text(source=combined_cache, dest=design_tmpdir / "oos-combined.md")
        if order_cache is not None and order_cache.is_file():
            _atomic_copy_text(source=order_cache, dest=design_tmpdir / "oos-design-filing-order.txt")
        _write_pending_marker(design_tmpdir / _PRIORITY_PENDING)
        return True
    except OSError as exc:
        _append_warning_log(
            design_tmpdir=design_tmpdir,
            site="design file-design-oos label-retry cache",
            tool="python/cli.py design file-oos-prepare",
            detail=f"label retry sidecar restore failed: {exc}",
        )
        return False


def _clear_label_retry_pending(*, design_tmpdir: Path, issue_number: str) -> None:
    (design_tmpdir / _PRIORITY_PENDING).unlink(missing_ok=True)
    pending_path = _cross_session_priority_pending_path(issue_number)
    if pending_path is not None:
        pending_path.unlink(missing_ok=True)


def _read_simple_env_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for raw in text.splitlines():
        if raw.startswith(f"{key}="):
            return raw.split("=", 1)[1].strip().strip("'\"")
    return ""


def _resolve_filing_repo(*, design_tmpdir: Path, issue_number: str | None) -> str:
    _ = issue_number
    for path in (
        design_tmpdir / "oos-filing-prepare.env",
        design_tmpdir / "session-env.sh",
        design_tmpdir / ".design-step0-route-state.env",
    ):
        value = _read_simple_env_value(path, "REPO")
        if value:
            return value
    return os.environ.get(config.ENV_REPO, "").strip()


def _run_gh(*, repo: str, argv: list[str]) -> proc.CommandResult:
    command = [*argv]
    if repo and "--repo" not in command:
        command.extend(["--repo", repo])
    return proc.run(command)


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
    _ = parser.add_argument("--repo")
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
        for path in (
            cache_path,
            _cross_session_priority_pending_path(issue_number),
            _cross_session_combined_path(issue_number),
            _cross_session_filing_order_path(issue_number),
            _cross_session_accepted_path(issue_number),
        ):
            if path is not None:
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
    if _label_retry_pending(design_tmpdir=design_tmpdir, issue_number=issue_number):
        _ = _restore_label_retry_sidecars(design_tmpdir=design_tmpdir, issue_number=issue_number)
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="label-only-retry")
        _emit_kv(key="NEXT_ACTION", value="label-only")
        _emit_kv(key="STEP5B_NEEDS_ANNOTATE", value="true")
        if args.repo:
            _emit_kv(key="REPO", value=args.repo)
        return 0
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
    if args.repo:
        _emit_kv(key="REPO", value=args.repo)
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


def _parse_post_cap_combined_blocks(combined_path: Path) -> list[str]:
    if not combined_path.is_file():
        return []
    text = combined_path.read_text(encoding="utf-8", errors="replace")
    blocks = file_oos._parse_oos_blocks(text)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    return [block.body for block in blocks]


def _priority_indices_from_combined(combined_path: Path) -> set[int]:
    return {
        index
        for index, block_text in enumerate(_parse_post_cap_combined_blocks(combined_path), start=1)
        if oos_priority.is_high_risk_oos_block(block_text)
    }


def _urls_from_sentinel(sentinel_path: Path) -> list[str]:
    if not sentinel_path.is_file():
        return []
    text = sentinel_path.read_text(encoding="utf-8", errors="replace")
    urls: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        url = ""
        if line.startswith("OOS_FILE_MAP\t"):
            parts = line.split("\t")
            if len(parts) >= _OOS_FILE_MAP_FIELD_COUNT:
                url = parts[2].strip()
        elif _GH_ISSUE_URL_RE.fullmatch(line.strip()):
            url = line.strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _parse_issue_stdout_slots(stdout_text: str) -> dict[int, str | None]:
    url_by_idx, dup_by_idx, failed_indices, _issues_failed_count = _parse_issue_stdout(stdout_text)
    slots: dict[int, str | None] = {}
    all_indices = {int(index) for index in [*url_by_idx, *dup_by_idx, *failed_indices] if index.isdigit()}
    for index in sorted(all_indices):
        key = str(index)
        slots[index] = None if key in failed_indices else (url_by_idx.get(key) or dup_by_idx.get(key))
    return slots


def _parse_oos_file_map(sentinel_text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in sentinel_text.splitlines():
        if not line.startswith("OOS_FILE_MAP\t"):
            continue
        parts = line.split("\t")
        if len(parts) >= _OOS_FILE_MAP_FIELD_COUNT:
            os_number = parts[1].strip()
            url = parts[2].strip()
            if os_number and url:
                mapping[os_number] = url
    return mapping


def _filing_slot_urls_from_sidecars(
    *,
    sentinel_path: Path,
    order_file: Path | None,
) -> dict[int, str]:
    if not sentinel_path.is_file():
        return {}
    os_to_url = _parse_oos_file_map(sentinel_path.read_text(encoding="utf-8", errors="replace"))
    if not os_to_url:
        return {}
    if order_file is not None and order_file.is_file():
        slots: dict[int, str] = {}
        for slot_index, os_number in enumerate(_parse_order(order_file), start=1):
            url = os_to_url.get(os_number)
            if url:
                slots[slot_index] = url
        return slots
    return {int(os_number): url for os_number, url in os_to_url.items() if os_number.isdigit()}


def _is_priority_for_slot(slot_index: int, combined_count: int, priority_indices: set[int]) -> bool:
    if combined_count == 1:
        return bool(priority_indices)
    return slot_index in priority_indices


def _read_stdout_slots(issue_stdout_path: Path | None) -> dict[int, str | None]:
    if issue_stdout_path is None or not issue_stdout_path.is_file() or not issue_stdout_path.stat().st_size:
        return {}
    return _parse_issue_stdout_slots(issue_stdout_path.read_text(encoding="utf-8", errors="replace"))


def _map_stdout_slots_to_priority(
    *,
    stdout_slots: dict[int, str | None],
    combined_count: int,
    priority_indices: set[int],
    order_file: Path | None,
) -> dict[str, bool]:
    slot_count = max(combined_count, *stdout_slots)
    if order_file is not None and order_file.is_file():
        slot_count = max(slot_count, len(_parse_order(order_file)))
    mapping: dict[str, bool] = {}
    for index in range(1, slot_count + 1):
        url = stdout_slots.get(index)
        if url:
            mapping[url] = _is_priority_for_slot(index, combined_count, priority_indices)
    return mapping


def _label_only_url_priority_map(
    *,
    sentinel_path: Path,
    combined_path: Path,
    order_file: Path | None,
    issue_stdout_path: Path | None = None,
) -> dict[str, bool]:
    combined_blocks = _parse_post_cap_combined_blocks(combined_path)
    priority_indices = _priority_indices_from_combined(combined_path)
    sentinel_urls = _urls_from_sentinel(sentinel_path)
    if not sentinel_urls or not combined_blocks:
        return {}
    combined_count = len(combined_blocks)
    stdout_slots = _read_stdout_slots(issue_stdout_path)
    if stdout_slots:
        return _map_stdout_slots_to_priority(
            stdout_slots=stdout_slots,
            combined_count=combined_count,
            priority_indices=priority_indices,
            order_file=order_file,
        )
    slot_urls = _filing_slot_urls_from_sidecars(sentinel_path=sentinel_path, order_file=order_file)
    if slot_urls:
        return {url: _is_priority_for_slot(idx, combined_count, priority_indices) for idx, url in slot_urls.items()}
    if combined_count == 1:
        return {url: bool(priority_indices) for url in sentinel_urls}
    if len(sentinel_urls) != combined_count:
        return {}
    return {url: _is_priority_for_slot(idx, combined_count, priority_indices) for idx, url in enumerate(sentinel_urls, start=1)}


def _ensure_oos_correctness_label(*, repo: str) -> bool:
    if not repo:
        return False
    result = _run_gh(repo=repo, argv=oos_priority.label_create_argv())
    return result.returncode == 0


def _apply_oos_correctness_label(*, url: str, repo: str) -> bool:
    number = oos_priority.issue_number_from_url(url)
    if not repo or not number:
        return False
    result = _run_gh(repo=repo, argv=oos_priority.label_edit_argv(number))
    return result.returncode == 0


def _apply_priority_labels_only(  # noqa: PLR0913
    *,
    design_tmpdir: Path,
    combined_path: Path,
    sentinel_path: Path,
    order_file: Path | None,
    repo: str,
    issue_stdout_path: Path | None = None,
    issue_number: str = "",
) -> int:
    url_priority = _label_only_url_priority_map(
        sentinel_path=sentinel_path,
        combined_path=combined_path,
        order_file=order_file,
        issue_stdout_path=issue_stdout_path,
    )
    priority_indices = _priority_indices_from_combined(combined_path)
    sentinel_urls = _urls_from_sentinel(sentinel_path)
    if priority_indices and sentinel_urls and not url_priority:
        pending_marker = design_tmpdir / _PRIORITY_PENDING
        _write_pending_marker(pending_marker)
        print("design file-oos-annotate: ambiguous priority label slot mapping", file=sys.stderr)
        return 1
    priority_urls = [url for url, priority in url_priority.items() if priority]
    if not priority_urls:
        _clear_label_retry_pending(design_tmpdir=design_tmpdir, issue_number=issue_number)
        return 0
    pending_marker = design_tmpdir / _PRIORITY_PENDING
    _write_pending_marker(pending_marker)
    _sync_label_retry_sidecars(
        design_tmpdir=design_tmpdir,
        issue_number=issue_number,
        sentinel=sentinel_path,
        combined_path=combined_path,
        order_file=order_file,
        pending=True,
        accepted_path=design_tmpdir / "oos-accepted-design.md",
    )
    if not repo or not _ensure_oos_correctness_label(repo=repo):
        print("design file-oos-annotate: priority label provisioning failed", file=sys.stderr)
        return 1
    for url in priority_urls:
        if not _apply_oos_correctness_label(url=url, repo=repo):
            print(f"design file-oos-annotate: priority label application failed for {url}", file=sys.stderr)
            return 1
    _clear_label_retry_pending(design_tmpdir=design_tmpdir, issue_number=issue_number)
    _sync_label_retry_sidecars(
        design_tmpdir=design_tmpdir,
        issue_number=issue_number,
        sentinel=sentinel_path,
        combined_path=combined_path,
        order_file=order_file,
        pending=False,
        accepted_path=design_tmpdir / "oos-accepted-design.md",
    )
    return 0


def _label_retry_pending(*, design_tmpdir: Path, issue_number: str) -> bool:
    if (design_tmpdir / _PRIORITY_PENDING).is_file():
        return True
    pending_path = _cross_session_priority_pending_path(issue_number)
    if pending_path is not None and pending_path.is_file():
        return True
    for path in (design_tmpdir / "oos-filing-prepare.env", design_tmpdir / "oos-filing-annotate.stdout.txt"):
        status = _read_simple_env_value(path, "FILE_DESIGN_OOS_STATUS")
        if status == "annotate-label-failed":
            return True
    return False


def file_oos_annotate_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="design file-oos-annotate", add_help=False)
    _ = parser.add_argument("--design-tmpdir")
    _ = parser.add_argument("--issue-stdout-file")
    _ = parser.add_argument("--issue-number")
    _ = parser.add_argument("--repo")
    _ = parser.add_argument("--label-only", action="store_true")
    try:
        args = parser.parse_args(list(argv))
    except SystemExit:
        return 2
    design_tmpdir = _require_design_tmpdir(argv, prog="design file-oos-annotate")
    if design_tmpdir is None:
        return 2
    issue_number = _issue_number_from(args.issue_number)
    prepare_status = _read_simple_env_value(design_tmpdir / "oos-filing-prepare.env", "FILE_DESIGN_OOS_STATUS")
    prepare_next_action = _read_simple_env_value(design_tmpdir / "oos-filing-prepare.env", "NEXT_ACTION")
    label_only = bool(args.label_only or prepare_status == "label-only-retry" or prepare_next_action == "label-only")
    repo = (args.repo or _resolve_filing_repo(design_tmpdir=design_tmpdir, issue_number=issue_number)).strip()
    issue_stdout_file = args.issue_stdout_file or str(design_tmpdir / OOS_ISSUE_STDOUT_FILE)
    stdout_path = Path(issue_stdout_file)
    if label_only:
        sentinel = design_tmpdir / "oos-issues-created.md"
        combined = design_tmpdir / "oos-combined.md"
        order_file = design_tmpdir / "oos-design-filing-order.txt"
        if not sentinel.is_file() or not combined.is_file():
            _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-label-failed")
            print("design file-oos-annotate: label-only retry missing sentinel or combined OOS file", file=sys.stderr)
            return 1
        rc = _apply_priority_labels_only(
            design_tmpdir=design_tmpdir,
            combined_path=combined,
            sentinel_path=sentinel,
            order_file=order_file if order_file.is_file() else None,
            repo=repo,
            issue_stdout_path=stdout_path if stdout_path.is_file() else None,
            issue_number=issue_number,
        )
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-label-complete" if rc == 0 else "annotate-label-failed")
        return rc
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
    _ = accepted.write_text(accepted_text, encoding="utf-8")
    sentinel_body = "\n".join(map_lines) + ("\n" if map_lines else "")
    complete_sentinel = design_tmpdir / "oos-issues-created.md"
    _ = complete_sentinel.write_text(sentinel_body, encoding="utf-8")
    combined_path = design_tmpdir / "oos-combined.md"
    label_rc = _apply_priority_labels_only(
        design_tmpdir=design_tmpdir,
        combined_path=combined_path,
        sentinel_path=complete_sentinel,
        order_file=order_file,
        repo=repo,
        issue_stdout_path=stdout_path,
        issue_number=issue_number,
    )
    if label_rc != 0:
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-label-failed")
        return 1
    if issues_failed_count > 0:
        _ = (design_tmpdir / "oos-issues-created.partial.md").write_text(sentinel_body, encoding="utf-8")
        (design_tmpdir / "oos-issues-created.md").unlink(missing_ok=True)
        _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-partial-failed")
        return 1
    (design_tmpdir / "oos-issues-created.partial.md").unlink(missing_ok=True)
    _sync_cross_session_cache(design_tmpdir=design_tmpdir, sentinel=complete_sentinel, issue_number=issue_number)
    _emit_kv(key="FILE_DESIGN_OOS_STATUS", value="annotate-complete")
    return 0
