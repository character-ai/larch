# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportUnusedFunction=false
"""Usage parsing and failure diagnostics for agent launchers."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
from pathlib import Path

from larch.core import logging_util
from larch.core import redact

from larch.agents._types import (
    _err,
    _emit_kv,
    _write,
    _append,
    _parse_positive_or_zero_int,
    UsageTotals,
    LauncherPaths,
    _env_int,
)

def _num(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
        return int(value.strip(), 10)
    raise ValueError("usage token value is not numeric")


def _dig(obj: object, *keys: str) -> object:
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _first_not_none(*values: object | None) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def _has_tokenish(obj: object) -> bool:
    if not isinstance(obj, dict):
        return False
    paths = (
        ("input_tokens",),
        ("cached_input_tokens",),
        ("output_tokens",),
        ("input_tokens_details", "cached_tokens"),
        ("msg", "input_tokens"),
        ("msg", "cached_input_tokens"),
        ("msg", "output_tokens"),
        ("msg", "input_tokens_details", "cached_tokens"),
    )
    return any(_dig(obj, *path) is not None for path in paths)


def _usage_row(obj: dict[str, object]) -> UsageTotals:
    msg_usage = _dig(obj, "msg", "usage")
    usage = _dig(obj, "usage")
    ignore_msg = False
    if _has_tokenish(msg_usage) and isinstance(usage, dict) and _has_tokenish(usage):
        ignore_msg = (
            _num(_dig(msg_usage, "input_tokens")) == 0
            and _num(_first_not_none(_dig(msg_usage, "cached_input_tokens"), _dig(msg_usage, "input_tokens_details", "cached_tokens"))) == 0
            and _num(_dig(msg_usage, "output_tokens")) == 0
        )
    input_tokens = _num(
        _first_not_none(
            None if ignore_msg else _dig(msg_usage, "input_tokens"),
            _dig(obj, "msg", "input_tokens"),
            _dig(usage, "input_tokens"),
            _dig(obj, "input_tokens"),
            0,
        )
    )
    cached = _num(
        _first_not_none(
            None if ignore_msg else _dig(msg_usage, "cached_input_tokens"),
            None if ignore_msg else _dig(msg_usage, "input_tokens_details", "cached_tokens"),
            _dig(obj, "msg", "cached_input_tokens"),
            _dig(obj, "msg", "input_tokens_details", "cached_tokens"),
            _dig(usage, "cached_input_tokens"),
            _dig(usage, "input_tokens_details", "cached_tokens"),
            _dig(obj, "cached_input_tokens"),
            _dig(obj, "input_tokens_details", "cached_tokens"),
            0,
        )
    )
    output = _num(
        _first_not_none(
            None if ignore_msg else _dig(msg_usage, "output_tokens"),
            _dig(obj, "msg", "output_tokens"),
            _dig(usage, "output_tokens"),
            _dig(obj, "output_tokens"),
            0,
        )
    )
    if cached > input_tokens:
        raise ValueError("cached_tokens exceeds input_tokens; fail-closed")
    return UsageTotals(input_tokens, cached, output)


def parse_codex_usage_file(events_file: str | Path) -> UsageTotals:
    path = Path(events_file)
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError("events file missing")
    total = UsageTotals(0, 0, 0)
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith(("{", "[")):
            continue  # skip non-JSON noise lines (e.g. wrapper banners)
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed usage event") from exc
        if not isinstance(obj, dict):
            continue
        selected = _has_tokenish(_dig(obj, "msg", "usage")) or _has_tokenish(_dig(obj, "usage")) or (obj.get("type") == "token_usage" and _has_tokenish(obj))
        if not selected:
            continue
        row = _usage_row(obj)
        total = UsageTotals(total.input_tokens + row.input_tokens, total.cached_input_tokens + row.cached_input_tokens, total.output_tokens + row.output_tokens)
        count += 1
    if count == 0 or total.total_tokens == 0:
        raise ValueError("no usage events")
    return total


def parse_codex_usage_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent parse-codex-usage")
    parser.add_argument("events_jsonl")
    args = parser.parse_args(argv)
    try:
        totals = parse_codex_usage_file(args.events_jsonl)
    except FileNotFoundError:
        _err("agent parse-codex-usage: events file missing")
        return 1
    except ValueError as exc:
        if "cached_tokens" in str(exc):
            _err("agent parse-codex-usage: cached_tokens exceeds input_tokens; fail-closed")
        elif "malformed" in str(exc):
            _err("agent parse-codex-usage: malformed usage event; fail-closed")
        else:
            _err("agent parse-codex-usage: no usage events")
        return 1
    _emit_kv(key="INPUT", value=totals.uncached_input_tokens)
    _emit_kv(key="CACHED_INPUT", value=totals.cached_input_tokens)
    _emit_kv(key="OUTPUT", value=totals.output_tokens)
    _emit_kv(key="TOTAL", value=totals.total_tokens)
    return 0


def select_failed_agent_stderr_source(
    output: Path,
    *,
    capture_stdout: bool,
    capture_stdout_only: bool,
    stderr_sink: str,
) -> Path | None:
    candidates: list[Path]
    if capture_stdout:
        candidates = [output, output.with_suffix(output.suffix + ".diag")]
    elif capture_stdout_only:
        candidates = [output.with_suffix(output.suffix + ".diag"), output]
    else:
        candidates = []
        if stderr_sink:
            candidates.append(Path(stderr_sink))
        candidates.extend([output.with_suffix(output.suffix + ".sidecar"), output, output.with_suffix(output.suffix + ".diag")])
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _truncate_utf8_bytes(*, text: str, cap: int) -> str:
    data = text.encode("utf-8")[:max(cap, 0)]
    while data:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            data = data[:-1]
    return ""


def _failed_agent_tail_lines_default() -> int:
    raw = os.environ.get("LARCH_FAILED_AGENT_STDERR_TAIL_LINES", "30")
    parsed = _parse_positive_or_zero_int(raw)
    return 30 if parsed is None else parsed


def render_failed_agent_stderr_tail(source: Path, *, lines: int | None = None, cap: int | None = None) -> str:
    tail_lines = _failed_agent_tail_lines_default() if lines is None else max(lines, 0)
    byte_cap = 5120 if cap is None else max(cap, 0)
    if tail_lines == 0 or byte_cap == 0 or not source.is_file() or source.stat().st_size == 0:
        return ""
    body_lines = source.read_text(encoding="utf-8", errors="replace").splitlines()[-tail_lines:]
    if not body_lines:
        return ""
    content = "\n".join(body_lines) + "\n"
    redacted = redact.redact_secrets_only(redact.redact_tmpdir_paths(content))
    return _truncate_utf8_bytes(text=redacted, cap=byte_cap)


def write_failed_agent_stderr_tail(*, source: Path, output: Path, lines: int | None = None, cap: int | None = None) -> bool:
    rendered = render_failed_agent_stderr_tail(source, lines=lines, cap=cap)
    tail = output.with_suffix(output.suffix + ".stderr-tail")
    if rendered:
        _write(path=tail, text=rendered)
        return True
    with contextlib.suppress(FileNotFoundError):
        tail.unlink()
    return False


def _tail_redacted(path: Path, *, lines: int = 30, cap: int = 5120) -> str:
    return render_failed_agent_stderr_tail(path, lines=lines, cap=cap)


def _write_stderr_tail(*, source: Path, output: Path) -> None:
    write_failed_agent_stderr_tail(source=source, output=output)


_FAILURE_EVENT_RE = re.compile(
    r"error|fail|quota|usage[ _-]?limit|rate[ _-]?limit|turn\.failed|unauthor|"
    r"forbidden|denied|timed?[ _-]?out|exception|panic|fatal|unhealthy|exit[ _-]?code",
    re.IGNORECASE,
)


def vendor_failure_diag_byte_cap() -> int:
    return 16384


def vendor_failure_diag_section_lines() -> int:
    return _env_int(name="LARCH_VENDOR_FAILURE_DIAG_SECTION_LINES", default=120)


def _vendor_failure_diag_cap() -> int:
    return _env_int(name="LARCH_VENDOR_FAILURE_DIAG_BYTES", default=vendor_failure_diag_byte_cap())


def _failure_diag_section_body(path: Path, *, filtered: bool) -> str:
    if not path.is_file() or path.stat().st_size == 0 or str(path) == "/dev/null":
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if filtered:
        lines = [line for line in lines if _FAILURE_EVENT_RE.search(line)]
    lines = lines[-vendor_failure_diag_section_lines():]
    return "\n".join(lines).rstrip("\n")


def _compose_failure_diag(output: Path, *, sink: str = "", history: str = "", events: str = "") -> None:
    paths = LauncherPaths.from_output(output)
    carrier = paths.failure_diag
    history_path = Path(history) if history else paths.sidecar_history
    events_path = Path(events) if events else paths.events
    sections: list[str] = []
    ordered: list[tuple[str, Path | None, bool]] = [
        ("sidecar.history", history_path, False),
        ("events.history (filtered)", paths.events_history, True),
    ]
    sink_path = Path(sink) if sink else None
    if sink_path is not None and sink_path not in {events_path, paths.sidecar, paths.diag}:
        ordered.append(("sink", sink_path, False))
    ordered.extend(
        [
            ("sidecar", paths.sidecar, False),
            ("diag", paths.diag, False),
            ("events.jsonl (filtered)", events_path, True),
            ("stderr", paths.stderr, False),
            ("launch-stderr", paths.launch_stderr, False),
            ("launcher-stderr", paths.launcher_stderr, False),
        ]
    )
    for label, path, filtered in ordered:
        if path is None:
            continue
        body = _failure_diag_section_body(path, filtered=filtered)
        if body:
            sections.append(f"===== {label} =====\n{body}")
    if not sections:
        return
    capped = _truncate_utf8_bytes(text="\n".join(sections) + "\n", cap=_vendor_failure_diag_cap())
    if carrier.is_file() and carrier.stat().st_size > 0:
        _append(path=carrier, text="\n===== additional failure diagnostics =====\n" + capped)
    else:
        _write(path=carrier, text=capped)


def _review_failure_auth_paths(*, output: Path, source: Path, stderr_sink: str = "") -> tuple[Path | str, ...]:
    launcher_paths = LauncherPaths.from_output(output)
    stem = str(output).removesuffix(".txt")
    paths: list[Path | str] = [
        source,
        Path(stderr_sink) if stderr_sink else "",
        launcher_paths.failure_diag,
        Path(f"{stem}-retry.txt.failure-diag"),
        Path(f"{stem}-ns-retry.txt.failure-diag"),
        launcher_paths.diag,
        launcher_paths.sidecar,
        launcher_paths.events,
        output,
    ]
    return tuple(path for path in paths if path)


def _implement_failure_auth_paths(*, tool: str, output: Path, sidecar: Path, source: Path) -> tuple[Path | str, ...]:
    paths = LauncherPaths.from_output(output)
    stem = str(output).removesuffix(".txt")
    auth_paths: list[Path | str] = [
        source,
        sidecar,
        paths.failure_diag,
        Path(f"{stem}-retry.txt.failure-diag"),
        Path(f"{stem}-ns-retry.txt.failure-diag"),
        paths.diag,
    ]
    if tool == "codex":
        auth_paths.append(paths.events)
    auth_paths.append(output)
    return tuple(path for path in auth_paths if path)


def external_stream_reset(*, target: Path, history: Path | None = None, label: str = "attempt") -> None:
    if str(target) == "/dev/null":
        return
    if history is not None and target.is_file() and target.stat().st_size > 0:
        body = "\n".join(target.read_text(encoding="utf-8", errors="replace").splitlines()[-(vendor_failure_diag_section_lines() * 2):])
        if body:
            _append(path=history, text=f"===== {label} =====\n{body}\n\n")
    with contextlib.suppress(OSError):
        _write(path=target, text="")


def _failure_diagnostic_source_candidates(output: Path, *, sink: str = "", history: str = "", events: str = "") -> list[Path]:
    paths = LauncherPaths.from_output(output)
    stem = str(output).removesuffix(".txt")
    ordered: list[Path | None] = [
        paths.failure_diag,
        Path(f"{stem}-retry.txt.failure-diag"),
        Path(f"{stem}-ns-retry.txt.failure-diag"),
        Path(sink) if sink else None,
        paths.sidecar_history,
        Path(history) if history else None,
        paths.sidecar,
        paths.diag,
        Path(events) if events else None,
        paths.events,
        paths.stderr,
        paths.launch_stderr,
        paths.launcher_stderr,
        paths.output,
    ]
    return [candidate for candidate in ordered if candidate is not None]


def resolve_failure_diagnostic_source(output: Path, *, sink: str = "", history: str = "", events: str = "") -> Path | None:
    for candidate in _failure_diagnostic_source_candidates(output, sink=sink, history=history, events=events):
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _stderr_tail_from_less_specific_carrier(*, output: Path, existing: str, source: Path, sink: str = "") -> bool:
    candidates = _failure_diagnostic_source_candidates(output, sink=sink)
    try:
        source_idx = candidates.index(source)
    except ValueError:
        return True
    for candidate in candidates[source_idx + 1 :]:
        if candidate.is_file() and candidate.stat().st_size > 0 and existing == render_failed_agent_stderr_tail(candidate):
            return True
    return False
