# ruff: noqa: PLC0415, N801, S108, FURB162, PLR1714, S607, PLR2004, DTZ005, E702
# pylint: disable=all
"""Token scraping, ledgers, reports, and cost helpers."""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, cast
from collections.abc import Mapping, Sequence

import larch_io
import config

_TOKEN_FIELDS = ("input", "output", "cache_read", "cache_create", "total")
TOKEN_LOCK_TIMEOUT_S = 5.0
_SAFE_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_UINT_RE = re.compile(r"^[0-9]+$")


@dataclass(frozen=True)
class TokenRecord:
    tool: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    model: str = ""


@dataclass(frozen=True)
class TimingRecord:
    tool: str
    duration_ms: int


# Mutable accumulator: add() sums token counts into the fields in place.
@dataclass
class TokenLedgerTally:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_create: int = 0
    total: int = 0

    def add(self, row: Mapping[str, object]) -> None:
        self.input += _int_field(data=row, key="input")
        self.output += _int_field(data=row, key="output")
        self.cache_read += _int_field(data=row, key="cache_read")
        self.cache_create += _int_field(data=row, key="cache_create")
        total = _int_field(data=row, key="total")
        if total == 0:
            total = (
                _int_field(data=row, key="input")
                + _int_field(data=row, key="output")
                + _int_field(data=row, key="cache_read")
                + _int_field(data=row, key="cache_create")
            )
        self.total += total

    def to_dict(self) -> dict[str, int]:
        return {
            "input": self.input,
            "output": self.output,
            "cache_read": self.cache_read,
            "cache_create": self.cache_create,
            "total": self.total,
        }


@dataclass(frozen=True)
class TokenLedger:
    path: Path
    session_id: str | None = None

    def mark(self, step: str) -> None:
        try:
            self._append({"type": "mark", "step": step, "ts": _timestamp_utc()})
        except OSError as exc:
            print(f"token mark: write skipped: {exc}", file=sys.stderr)

    def record_vendor(
        self,
        vendor: str,
        *,
        input: int = 0,  # noqa: A002 - CLI field name.
        output: int = 0,
        cache_read: int = 0,
        cache_create: int = 0,
        total: int = 0,
        raw: str = "",
        model: str = "",
    ) -> None:
        if vendor == "claude":
            msg = "vendor 'claude' is reserved; use 'claude_sub' for spawned-process Claude"
            raise ValueError(msg)
        payload = {
            "type": "vendor",
            "vendor": vendor,
            "input": input,
            "output": output,
            "cache_read": cache_read,
            "cache_create": cache_create,
            "total": total,
            "raw": raw,
            "ts": _timestamp_utc(),
        }
        if model:
            payload["model"] = model
        try:
            self._append(payload)
        except OSError as exc:
            print(f"token record-vendor: write skipped: {exc}", file=sys.stderr)

    def dump(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.is_file() else ""

    def _append(self, payload: Mapping[str, object]) -> None:
        _ensure_regular_file(self.path)
        line = json.dumps(dict(payload), sort_keys=False, separators=(",", ":")) + "\n"
        try:
            import fcntl
        except ImportError:  # pragma: no cover
            with self.path.open("a", encoding="utf-8") as handle:
                _ = handle.write(line)
        else:
            deadline = time.monotonic() + TOKEN_LOCK_TIMEOUT_S
            with self.path.open("a", encoding="utf-8") as handle:
                while True:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            print(
                                f"token: WARNING: flock lock acquisition failed; skipping append for {self.path}",
                                file=sys.stderr,
                            )
                            return
                        time.sleep(0.05)
                try:
                    _ = handle.write(line)
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        with contextlib_suppress_oserror():
            self.path.chmod(0o600)


class contextlib_suppress_oserror:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return isinstance(exc, OSError)


def _int_field(*, data: Mapping[str, Any], key: str) -> int:
    value = data.get(key, 0)
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def normalize_sidecar(data: dict[str, Any], *, tool: str) -> TokenRecord | None:
    """Normalize codex/cursor sidecar payloads into a TokenRecord."""
    if not data:
        return None
    total = _int_field(data=data, key="total_tokens")
    if total == 0:
        total = (
            _int_field(data=data, key="input_tokens")
            + _int_field(data=data, key="output_tokens")
            + _int_field(data=data, key="cache_read_tokens")
            + _int_field(data=data, key="cache_create_tokens")
        )
    if total == 0 and not any(key in data for key in config.TOKEN_SIDECAR_KEYS):
        return None
    return TokenRecord(
        tool=tool,
        total_tokens=total,
        input_tokens=_int_field(data=data, key="input_tokens"),
        output_tokens=_int_field(data=data, key="output_tokens"),
        cache_read_tokens=_int_field(data=data, key="cache_read_tokens"),
        cache_create_tokens=_int_field(data=data, key="cache_create_tokens"),
        model=str(data.get("model") or ""),
    )


def append_token_record(*, path: Path, record: TokenRecord) -> None:
    """Append one typed NDJSON line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tool": record.tool,
        "total_tokens": record.total_tokens,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "cache_read_tokens": record.cache_read_tokens,
        "cache_create_tokens": record.cache_create_tokens,
    }
    if record.model:
        payload["model"] = record.model
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(payload, sort_keys=True) + "\n")


def normalize_timing_sidecar(data: dict[str, Any], *, tool: str) -> TimingRecord | None:
    duration = data.get("duration_ms", data.get("elapsed_ms", 0))
    try:
        duration_ms = int(duration)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if duration_ms <= 0:
        return None
    return TimingRecord(tool=tool, duration_ms=duration_ms)


def scrape_run(
    *,
    sidecar_paths: tuple[tuple[str, Path], ...] = (),
    timing_sidecar_paths: tuple[tuple[str, Path], ...] = (),
    output_path: Path | None = None,
    timing_output_path: Path | None = None,
) -> tuple[TokenRecord, ...]:
    """Aggregate token (and optional timing) records from sidecar JSON files."""
    records: list[TokenRecord] = []
    for tool, path in sidecar_paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        record = normalize_sidecar(cast("dict[str, Any]", data), tool=tool)
        if record is None:
            continue
        records.append(record)
        if output_path is not None:
            append_token_record(path=output_path, record=record)
    if timing_output_path is not None:
        timing_output_path.parent.mkdir(parents=True, exist_ok=True)
        timing_lines: list[str] = []
        for tool, path in timing_sidecar_paths:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            timing = normalize_timing_sidecar(cast("dict[str, Any]", data), tool=tool)
            if timing is None:
                continue
            timing_lines.append(json.dumps({"tool": timing.tool, "duration_ms": timing.duration_ms}, sort_keys=True))
        if timing_lines:
            _ = timing_output_path.write_text("\n".join(timing_lines) + "\n", encoding="utf-8")
    return tuple(records)


def _timestamp_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _tmp_root(env: Mapping[str, str] | None = None) -> Path | None:
    raw = (env or os.environ).get("TMPDIR") or "/tmp"
    try:
        return Path(raw).resolve(strict=True)
    except OSError:
        return None


def _canonical_dir(path: str | Path) -> Path | None:
    try:
        p = Path(path)
        if not p.parts:  # empty path ("") resolves to cwd — reject it
            return None
        if p.is_dir():
            return p.resolve(strict=True)
    except OSError:
        return None
    return None


def _validate_under_tmp(raw: str, *, env: Mapping[str, str] | None = None) -> Path:
    root = _tmp_root(env)
    if root is None:
        msg = "cannot canonicalize TMPDIR"
        raise ValueError(msg)
    if not raw or ".." in Path(raw).parts:
        msg = f"ledger must not be empty or contain '..': {raw}"
        raise ValueError(msg)
    candidate = Path(raw) if Path(raw).is_absolute() else root / raw
    candidate.parent.mkdir(parents=True, exist_ok=True)
    parent = candidate.parent.resolve(strict=True)
    resolved = parent / candidate.name
    allowed = [root]
    private = _canonical_dir("/private/tmp")
    if private is not None:
        allowed.append(private)
    if not any(resolved == base or base in resolved.parents for base in allowed):
        msg = f"ledger must resolve under TMPDIR: {raw}"
        raise ValueError(msg)
    return resolved


def resolve_session_id(*, env: Mapping[str, str] | None = None) -> str:
    env_map = os.environ if env is None else env
    if env_map.get("LARCH_TOKEN_SESSION_ID"):
        return str(env_map["LARCH_TOKEN_SESSION_ID"])
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"):
        root = env_map.get(key, "")
        candidate = Path(root) / "session-id" if root else None
        if candidate and candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace").strip()
    return _sha256_hex(str(Path.cwd().resolve()))


def resolve_token_ledger_path(
    *,
    ledger: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    env_map = os.environ if env is None else env
    if ledger:
        return _validate_under_tmp(ledger, env=env_map)
    if env_map.get("LARCH_TOKEN_LEDGER"):
        try:
            return _validate_under_tmp(str(env_map["LARCH_TOKEN_LEDGER"]), env=env_map)
        except ValueError:
            pass
    slug = _sha256_hex(resolve_session_id(env=env_map))
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"):
        root = _canonical_dir(env_map.get(key, ""))
        if root is not None:
            return root / f"larch-tokens-{slug}.jsonl"
    session_env = env_map.get("SESSION_ENV_PATH", "")
    if session_env:
        root = _canonical_dir(Path(session_env).parent)
        if root is not None:
            return root / f"larch-tokens-{slug}.jsonl"
    return None


def _ensure_regular_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        msg = f"ledger is a symlink: {path}"
        raise ValueError(msg)
    if path.exists() and not path.is_file():
        msg = f"ledger exists but is not a regular file: {path}"
        raise ValueError(msg)
    path.touch(mode=0o600, exist_ok=True)


def _parse_ledger(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(cast("dict[str, Any]", obj))
    return rows


def _epoch(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, int | float):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _usage_obj(row: Mapping[str, Any]) -> Mapping[str, Any]:
    msg = row.get("message")
    if isinstance(msg, dict):
        msg_d = cast("dict[str, Any]", msg)
        usage = msg_d.get("usage")
        if isinstance(usage, dict):
            return cast("Mapping[str, Any]", usage)
    usage = row.get("usage")
    if isinstance(usage, dict):
        return cast("Mapping[str, Any]", usage)
    return {}


def _cache_create_parts(usage: Mapping[str, Any]) -> tuple[int, int]:
    cache_creation = usage.get("cache_creation")
    if isinstance(cache_creation, dict):
        return (
            _int_field(data=cast("Mapping[str, Any]", cache_creation), key="ephemeral_5m_input_tokens")
            + _int_field(data=cast("Mapping[str, Any]", cache_creation), key="5m"),
            _int_field(data=cast("Mapping[str, Any]", cache_creation), key="ephemeral_1h_input_tokens"),
        )
    return _int_field(data=usage, key="cache_creation_input_tokens"), 0


def _md_cell(value: object) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    tally = TokenLedgerTally()
    cc5 = cc1 = cached_input = 0
    for row in rows:
        tally.add(row)
        cc5 += _int_field(data=row, key="cache_create_5m")
        cc1 += _int_field(data=row, key="cache_create_1h")
        cached_input += _int_field(data=row, key="cached_input")
    data: dict[str, int] = tally.to_dict()
    data["cache_create_5m"] = cc5
    data["cache_create_1h"] = cc1
    data["cached_input"] = cached_input
    return data


def _slice(*, rows: list[dict[str, Any]], start: float, end: float | None) -> list[dict[str, Any]]:
    return [row for row in rows if (ts := _epoch(row.get("ts"))) is not None and ts >= start and (end is None or ts < end)]


def _read_transcript_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(cast("dict[str, Any]", obj))
    return rows


def _enclosing_step(*, marks: list[dict[str, Any]], ts: float | None) -> str | None:
    if ts is None:
        return None
    for idx, mark in enumerate(marks):
        start = cast("float", mark["ts"])
        end = cast("float | None", marks[idx + 1]["ts"] if idx + 1 < len(marks) else None)
        if start <= ts and (end is None or ts < end):
            return str(mark["step"])
    return None


def _claude_rows(*, transcript_rows: list[dict[str, Any]], marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dedup: dict[str, dict[str, Any]] = {}
    first_ts: float | None = cast("float", marks[0]["ts"]) if marks else None
    for row in transcript_rows:
        if row.get("type") != "assistant" and not _usage_obj(row):
            continue
        usage = _usage_obj(row)
        if not usage:
            continue
        ts = _epoch(row.get("timestamp")) or first_ts
        cache5, cache1 = _cache_create_parts(usage)
        cache_create = cache5 + cache1
        inp = _int_field(data=usage, key="input_tokens")
        cr = _int_field(data=usage, key="cache_read_input_tokens")
        oup = _int_field(data=usage, key="output_tokens")
        out: dict[str, Any] = {
            "rid": row.get("requestId"),
            "mid": cast("dict[str, Any]", row.get("message")).get("id") if isinstance(row.get("message"), dict) else None,
            "ts": ts,
            "skill": row.get("attributionSkill") or (f"inferred:{_enclosing_step(marks=marks, ts=ts)}" if _enclosing_step(marks=marks, ts=ts) else "unattributed"),
            "input": inp,
            "cache_read": cr,
            "cache_create": cache_create,
            "cache_create_5m": cache5,
            "cache_create_1h": cache1,
            "output": oup,
            "total": inp + cr + cache_create + oup,
        }
        rid = str(out["rid"] or "")
        mid = str(out["mid"] or "")
        fingerprint = (
            ""
            if rid or mid
            else f"{out['input']}/{out['cache_read']}/{out['cache_create_5m']}/{out['cache_create_1h']}/{out['output']}"
        )
        dedup[f"{rid}|{mid}|{fingerprint}"] = out
    return list(dedup.values())


def _vendor_rows(ledger_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in ledger_rows:
        if row.get("type") != "vendor":
            continue
        ts = _epoch(row.get("ts"))
        if ts is None:
            continue
        out: dict[str, Any] = {"ts": ts, "vendor": str(row.get("vendor") or "unknown")}
        for field in _TOKEN_FIELDS:
            out[field] = _int_field(data=row, key=field)
        if out["total"] == 0:
            out["total"] = out["input"] + out["output"] + out["cache_read"] + out["cache_create"]
        if row.get("raw"):
            out["raw"] = str(row.get("raw"))
        if row.get("model"):
            out["model"] = str(row.get("model"))
        rows.append(out)
    return rows


def _report_data(*, ledger_path: Path, transcript_paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ledger_rows = _parse_ledger(ledger_path)
    marks = [
        {"step": str(row.get("step") or ""), "ts": ts}
        for row in ledger_rows
        if row.get("type") == "mark" and (ts := _epoch(row.get("ts"))) is not None
    ]
    if not marks:
        msg = "no step marks in ledger"
        raise ValueError(msg)
    return marks, _claude_rows(transcript_rows=_read_transcript_rows(transcript_paths), marks=marks), _vendor_rows(ledger_rows)


def _vendor_names(*, marks: list[dict[str, Any]], vendor: list[dict[str, Any]]) -> list[str]:
    first = cast("float", marks[0]["ts"])
    present = sorted({row["vendor"] for row in vendor if cast("float", row["ts"]) >= first})
    ordered = [name for name in ("codex", "cursor", "claude_sub") if name in present]
    return ordered + [name for name in present if name not in {"codex", "cursor", "claude_sub"}]


def _per_step_json(*, name: str, marks: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = cast("float", marks[0]["ts"])
    filtered = [row for row in rows if name == "claude" or row.get("vendor") == name]
    per_step: list[dict[str, Any]] = []
    for idx, mark in enumerate(marks):
        start = cast("float", mark["ts"])
        end = cast("float | None", marks[idx + 1]["ts"] if idx + 1 < len(marks) else None)
        sl = _slice(rows=filtered, start=start, end=end)
        per_step.append({"step": mark["step"], "totals": _totals(sl)})
    return {"per_step": per_step, "totals": _totals(_slice(rows=filtered, start=first, end=None))}


def _full_json(*, marks: list[dict[str, Any]], claude: list[dict[str, Any]], vendor: list[dict[str, Any]]) -> dict[str, Any]:
    names = _vendor_names(marks=marks, vendor=vendor)
    data: dict[str, Any] = {"vendors": ["claude", *names], "claude": _per_step_json(name="claude", marks=marks, rows=claude)}
    for name in names:
        data[name] = _per_step_json(name=name, marks=marks, rows=vendor)
    ct = data["claude"]["totals"]
    first = cast("float", marks[0]["ts"])
    vin = [row for row in vendor if cast("float", row["ts"]) >= first]
    data["BUCKETS_claude"] = {
        "input": ct.get("input", 0),
        "cache_read": ct.get("cache_read", 0),
        "cache_create_5m": ct.get("cache_create_5m", 0),
        "cache_create_1h": ct.get("cache_create_1h", 0),
        "output": ct.get("output", 0),
        "total": ct.get("total", 0),
    }
    for name in ("codex", "cursor", "claude_sub"):
        rows = [row for row in vin if row.get("vendor") == name]
        totals = _totals(rows)
        if name == "codex":
            data["BUCKETS_codex"] = {"input": totals["input"], "cached_input": totals["cache_read"], "output": totals["output"], "total": totals["total"]}
        elif name == "cursor":
            data["BUCKETS_cursor"] = {"input": totals["input"], "cache_read": totals["cache_read"], "output": totals["output"], "total": totals["total"]}
        else:
            data["BUCKETS_claude_sub"] = {"input": totals["input"], "cache_read": totals["cache_read"], "cache_create_5m": totals["cache_create"], "cache_create_1h": 0, "output": totals["output"], "total": totals["total"]}
    return data


def build_report_from_ledgers(ledger_paths: Sequence[Path]) -> dict[str, Any]:
    """Aggregate committed token ledger(s) into the canonical full-report dict.

    This recovers the cost of a run from its committed `larch-tokens-*.jsonl`
    ledger(s) when the canonical `token-report{,-final}.json` is absent — e.g. a
    design run that flushed its log tree before finalizing (issue #5133). It
    recovers the committed vendor lanes (codex/cursor/claude_sub); the main-agent
    `claude` lane is intentionally omitted because the session transcript is not
    committed to the run-log tree and cannot be recovered after the fact. Rows
    from multiple ledgers are merged. Raises `ValueError` when no step marks are
    present (matching `_report_data`), since per-step slicing needs a first mark.
    """
    ledger_rows: list[dict[str, Any]] = []
    for path in ledger_paths:
        ledger_rows.extend(_parse_ledger(path))
    marks: list[dict[str, Any]] = sorted(
        (
            {"step": str(row.get("step") or ""), "ts": ts}
            for row in ledger_rows
            if row.get("type") == "mark" and (ts := _epoch(row.get("ts"))) is not None
        ),
        key=lambda mark: cast("float", mark["ts"]),
    )
    if not marks:
        msg = "no step marks in ledger"
        raise ValueError(msg)
    return _full_json(marks=marks, claude=[], vendor=_vendor_rows(ledger_rows))


def _summary_json(*, marks: list[dict[str, Any]], claude: list[dict[str, Any]], vendor: list[dict[str, Any]]) -> dict[str, Any]:
    first = cast("float", marks[0]["ts"])
    ct = _totals(_slice(rows=claude, start=first, end=None))
    vrows = [row for row in vendor if cast("float", row["ts"]) >= first]
    def vt(name: str) -> dict[str, int]:
        return _totals([row for row in vrows if row.get("vendor") == name])
    codex = vt("codex")
    cursor = vt("cursor")
    cs = vt("claude_sub")
    return {
        "claude": {"input": ct["input"], "cache_read": ct["cache_read"], "cache_write_5m": ct["cache_create_5m"], "cache_write_1h": ct["cache_create_1h"], "output": ct["output"]},
        "codex": {"input": codex["input"], "cached_input": codex["cache_read"], "output": codex["output"]},
        "cursor": {"input": cursor["input"], "cache_read": cursor["cache_read"], "output": cursor["output"]},
        "claude_sub": {"input": cs["input"], "cache_read": cs["cache_read"], "cache_write_5m": cs["cache_create"], "cache_write_1h": 0, "output": cs["output"]},
        "codex_ledger_total": codex["total"],
        "cursor_ledger_total": cursor["total"],
        "claude_sub_ledger_total": cs["total"],
        "token_total": ct["total"] + sum(_int_field(data=row, key="total") for row in vrows),
    }


def _tok_k(value: int) -> int:
    return int((value + 500) / 1000)


def _markdown(*, marks: list[dict[str, Any]], claude: list[dict[str, Any]], vendor: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    parts.append("### Claude\n\n| Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output |\n| --- | --- | ---: | ---: | ---: | ---: |")
    for idx, mark in enumerate(marks):
        start = cast("float", mark["ts"])
        end = cast("float | None", marks[idx + 1]["ts"] if idx + 1 < len(marks) else None)
        rows = _slice(rows=claude, start=start, end=end)
        totals = _totals(rows)
        parts.append(f"| {_md_cell(mark['step'])} | **step total** | {totals['input']} | {totals['cache_read']} | {totals['cache_create']} | {totals['output']} |")
    gt = _totals(_slice(rows=claude, start=cast("float", marks[0]["ts"]), end=None))
    parts.append(f"| **Grand total** |  | {gt['input']} | {gt['cache_read']} | {gt['cache_create']} | {gt['output']} |")
    label = {"codex": "Codex", "cursor": "Cursor", "claude_sub": "Claude (subprocess)"}
    for name in _vendor_names(marks=marks, vendor=vendor):
        rows = [row for row in vendor if row.get("vendor") == name]
        parts.append(f"\n### {_md_cell(label.get(name, name))}\n\n| Step | Skill | Input | Output | Total |\n| --- | --- | ---: | ---: | ---: |")
        for idx, mark in enumerate(marks):
            start = cast("float", mark["ts"])
            end = cast("float | None", marks[idx + 1]["ts"] if idx + 1 < len(marks) else None)
            totals = _totals(_slice(rows=rows, start=start, end=end))
            parts.append(f"| {_md_cell(mark['step'])} | **step total** | {totals['input']} | {totals['output']} | {totals['total']} |")
        totals = _totals(_slice(rows=rows, start=cast("float", marks[0]["ts"]), end=None))
        parts.append(f"| **Grand total** |  | {totals['input']} | {totals['output']} | {totals['total']} |")
    return "\n".join(parts)


def _marker_line_re(marker: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*<!-- {re.escape(marker)} -->\s*$")


def _replace_block(*, target: Path, block: str, begin: str, end: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    begin_re = _marker_line_re(begin)
    end_re = _marker_line_re(end)
    lines = existing.splitlines(keepends=True)
    begin_idx: int | None = None
    end_idx: int | None = None
    has_begin = False
    has_end = False
    for idx, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if begin_re.match(stripped):
            has_begin = True
            if begin_idx is None:
                begin_idx = idx
        if end_re.match(stripped):
            has_end = True
            if begin_idx is not None and end_idx is None:
                end_idx = idx
    if has_begin and has_end and begin_idx is not None and end_idx is not None:
        text = "".join(lines[:begin_idx]) + block + "".join(lines[end_idx + 1 :])
    elif has_begin and not has_end:
        print(
            f"token report: warning: {target} has lone <!-- {begin} --> marker; truncating from marker and rewriting block",
            file=sys.stderr,
        )
        kept: list[str] = []
        for line in lines:
            if begin_re.match(line.rstrip("\r\n")):
                break
            kept.append(line)
        text = "".join(kept)
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
    elif has_end and not has_begin:
        print(
            f"token report: warning: {target} has lone <!-- {end} --> marker; dropping head through marker and rewriting block",
            file=sys.stderr,
        )
        kept_tail: list[str] = []
        past = False
        for line in lines:
            if end_re.match(line.rstrip("\r\n")):
                past = True
                continue
            if past:
                kept_tail.append(line)
        text = "".join(kept_tail)
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
    else:
        text = existing + ("\n" if existing else "") + block
    tmp = target.with_name(target.name + ".tmp")
    _ = tmp.write_text(text, encoding="utf-8")
    _ = tmp.replace(target)


def _transcript_sources(
    *, transcript_path: Path | None,
    session_dir: Path | None,
    env: Mapping[str, str] | None = None,
) -> list[Path]:
    if transcript_path is None:
        source = token_claude_source(env=env)
        if not source.get("TRANSCRIPT_PATH"):
            msg = str(source.get("REASON") or "Claude transcript source unavailable")
            raise ValueError(msg)
        transcript_path = Path(str(source["TRANSCRIPT_PATH"]))
        session_dir = Path(str(source.get("SESSION_DIR") or "")) if source.get("SESSION_DIR") else None
    if not transcript_path.is_file():
        msg = "transcript not found"
        raise ValueError(msg)
    paths = [transcript_path]
    sub = session_dir / "subagents" if session_dir is not None else None
    if sub is not None and sub.is_dir():
        paths.extend(sorted(sub.glob("*.jsonl")))
    return paths


def token_report(
    *,
    ledger_path: Path | None = None,
    transcript_path: Path | None = None,
    session_dir: Path | None = None,
    mode: str = "full",
    fmt: str = "markdown",
    since_last_mark: bool = False,
    append_token_report: Path | None = None,
    buckets: bool = False,
    vendor: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str | dict[str, Any]:
    if since_last_mark:
        mode = "terse"
    ledger = ledger_path or resolve_token_ledger_path(env=env)
    if ledger is None:
        msg = "ledger path unavailable"
        raise ValueError(msg)
    sources = _transcript_sources(transcript_path=transcript_path, session_dir=session_dir, env=env)
    marks, claude, vendor_rows = _report_data(ledger_path=ledger, transcript_paths=sources)
    if buckets:
        if vendor not in {"claude", "codex", "cursor", "claude_sub"}:
            msg = "unknown vendor"
            raise ValueError(msg)
        data = _full_json(marks=marks, claude=claude, vendor=vendor_rows)
        key = f"BUCKETS_{vendor}"
        bucket = data.get(key, {})
        if vendor == "claude" or vendor == "claude_sub":
            return f"INPUT={bucket.get('input', 0)} CACHE_READ={bucket.get('cache_read', 0)} CACHE_WRITE_5M={bucket.get('cache_create_5m', 0)} CACHE_WRITE_1H={bucket.get('cache_create_1h', 0)} OUTPUT={bucket.get('output', 0)}"
        if vendor == "codex":
            return f"INPUT={bucket.get('input', 0)} CACHED_INPUT={bucket.get('cached_input', 0)} OUTPUT={bucket.get('output', 0)}"
        return f"INPUT={bucket.get('input', 0)} CACHE_READ={bucket.get('cache_read', 0)} OUTPUT={bucket.get('output', 0)}"
    _validate_report_format(fmt)
    if mode == "summary":
        data = _summary_json(marks=marks, claude=claude, vendor=vendor_rows)
        if fmt == "json":
            return data
        c_raw = sum(data["claude"].values())
        d_raw = sum(data["codex"].values())
        u_raw = sum(data["cursor"].values())
        cs_raw = sum(data["claude_sub"].values())
        return f"Tokens: {_tok_k(data['token_total'])}k — Claude: {_tok_k(c_raw)}k | Codex: {_tok_k(d_raw)}k | Cursor: {_tok_k(u_raw)}k | Claude (subprocess): {_tok_k(cs_raw)}k"
    if mode == "terse":
        last = marks[-1]
        start = cast("float", last["ts"])
        ctot = _totals(_slice(rows=claude, start=start, end=None))
        vrows: list[dict[str, Any]] = _slice(rows=vendor_rows, start=start, end=None)
        vt = sum(_int_field(data=row, key="total") for row in vrows)
        return f"{last['step']}: claude={ctot['total']} tokens; vendor={vt}"
    data = _full_json(marks=marks, claude=claude, vendor=vendor_rows)
    rendered: str | dict[str, Any] = data if fmt == "json" else _markdown(marks=marks, claude=claude, vendor=vendor_rows)
    if append_token_report is not None:
        body = json.dumps(rendered, sort_keys=True) if fmt == "json" else str(rendered)
        block = f"<!-- token-report-begin -->\n## Token Report\n\n{body}\n<!-- token-report-end -->\n"
        _replace_block(target=append_token_report, block=block, begin="token-report-begin", end="token-report-end")
    return rendered


def check_step_token_budget(*, cap: int, step: str = "unknown", env: Mapping[str, str] | None = None) -> dict[str, object]:
    total = 0
    try:
        ledger = resolve_token_ledger_path(env=env)
        for row in _parse_ledger(ledger):
            if row.get("type") == "mark":
                total = 0
            elif row.get("type") == "vendor":
                total += _int_field(data=row, key="total")
    except (OSError, ValueError):
        total = 0
    return {"status": "cap_hit" if total >= cap else "under_cap", "total": total, "cap": cap, "step": step}


def token_claude_source(
    *,
    claude_source_file: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env_map = os.environ if env is None else env
    snap = claude_source_file or (Path(env_map["LARCH_CLAUDE_SOURCE_FILE"]) if env_map.get("LARCH_CLAUDE_SOURCE_FILE") else None)
    if snap is not None and snap.is_file():
        data = larch_io.parse_kv(
            larch_io.read_text(snap, errors="replace"),
            allowed_keys={"TRANSCRIPT_PATH", "SESSION_DIR", "SESSION_UUID"},
        )
        if data.get("TRANSCRIPT_PATH") and data.get("SESSION_DIR") and data.get("SESSION_UUID"):
            replay = _validate_snapshot_replay(data, env=env_map)
            if replay is not None:
                return replay
    try:
        repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL).strip()
        repo_root = str(Path(repo_root).resolve(strict=True))
    except (OSError, subprocess.SubprocessError):
        return {"STATUS": "unavailable", "REASON": "not inside a git repository"}
    home = env_map.get("HOME", "")
    if not home:
        return {"STATUS": "unavailable", "REASON": "HOME is not set"}
    project_dir = Path(home) / ".claude" / "projects" / repo_root.replace("/", "-")
    if not project_dir.is_dir():
        return {"STATUS": "unavailable", "REASON": "Claude project directory not found"}
    latest: Path | None = None
    for key in ("LARCH_CLAUDE_SESSION_ID", "LARCH_TOKEN_SESSION_ID"):
        sid = env_map.get(key, "")
        if sid and _SAFE_SESSION_RE.fullmatch(sid):
            candidate = project_dir / f"{sid}.jsonl"
            if candidate.is_file():
                latest = candidate
                break
    if latest is None:
        files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        latest = files[0] if files else None
    if latest is None:
        return {"STATUS": "unavailable", "REASON": "no Claude transcript jsonl files found"}
    uuid = latest.stem
    return {"TRANSCRIPT_PATH": str(latest), "SESSION_DIR": str(project_dir / uuid), "SESSION_UUID": uuid}


def _assistant_model_from_line(raw: str) -> str:
    if '"assistant"' not in raw:
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(parsed, dict):
        return ""
    obj = cast("dict[str, Any]", parsed)
    if obj.get("type") != "assistant":
        return ""
    message = obj.get("message")
    if not isinstance(message, dict):
        return ""
    model = cast("dict[str, Any]", message).get("model", "")
    return model if isinstance(model, str) else ""


def read_main_model(
    *,
    claude_source_file: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Best-effort main-agent model id from the active Claude session transcript.

    Locates the transcript via token_claude_source and returns the first assistant
    turn's message.model. Returns "" when the transcript or model is unavailable.
    Resolved at run-log init, before any subagents spawn, so the newest transcript
    is the orchestrator session rather than a spawned reviewer/voter.
    """
    source = token_claude_source(claude_source_file=claude_source_file, env=env)
    transcript = source.get("TRANSCRIPT_PATH", "")
    if not transcript:
        return ""
    path = Path(transcript)
    if not path.is_file():
        return ""
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            model = _assistant_model_from_line(raw)
            if model:
                return model
    except OSError:
        return ""
    return ""


def _path_is_under(*, child: Path, parent: Path) -> bool:
    try:
        _ = child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _claude_project_dir(*, env: Mapping[str, str]) -> Path | None:
    home = env.get("HOME", "")
    if not home:
        return None
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        repo_root = str(Path(repo_root).resolve(strict=True))
    except (OSError, subprocess.SubprocessError):
        return None
    project_dir = Path(home) / ".claude" / "projects" / repo_root.replace("/", "-")
    return project_dir if project_dir.is_dir() else None


def _validate_snapshot_replay(data: Mapping[str, str], *, env: Mapping[str, str]) -> dict[str, str] | None:
    session_uuid = data.get("SESSION_UUID", "")
    if not _SAFE_SESSION_RE.fullmatch(session_uuid):
        return None
    transcript = Path(data["TRANSCRIPT_PATH"]).resolve()
    session_dir = Path(data["SESSION_DIR"]).resolve()
    if not transcript.is_file():
        return None
    allowed_roots = [session_dir]
    project_dir = _claude_project_dir(env=env)
    if project_dir is not None:
        allowed_roots.append(project_dir)
    if not any(_path_is_under(child=transcript, parent=root) for root in allowed_roots):
        return None
    return {
        "TRANSCRIPT_PATH": str(transcript),
        "SESSION_DIR": str(session_dir),
        "SESSION_UUID": session_uuid,
    }


def parse_token_record_sidecar(input_path: Path | None) -> dict[str, Any] | None:
    if input_path is None:
        return None
    if not input_path.is_file() or input_path.stat().st_size == 0:
        return None
    kv = larch_io.parse_kv(larch_io.read_text(input_path, errors="replace"))
    tool = kv.get("TOOL", "unknown")
    if tool not in {"codex", "cursor", "claude", "claude_sub"}:
        tool = "unknown"
    def uint_key(key: str) -> int:
        raw = kv.get(key, "")
        return int(raw) if _UINT_RE.fullmatch(raw) else 0
    total = uint_key("TOTAL")
    if total == 0:
        total = uint_key("INPUT") + uint_key("OUTPUT") + uint_key("CACHE_READ") + uint_key("CACHE_CREATE")
    if total == 0:
        return None
    payload = {
        "tool": tool,
        "raw": kv.get("RAW") or f"{tool}_ci_fix",
        "input": uint_key("INPUT"),
        "output": uint_key("OUTPUT"),
        "cache_read": uint_key("CACHE_READ"),
        "cache_create": uint_key("CACHE_CREATE"),
        "total": total,
    }
    model = kv.get("MODEL", "")
    if model:
        payload["model"] = model
    return payload


def append_token_record_from_sidecar(*, input_path: Path | None, tmpdir: Path) -> None:
    if not tmpdir.is_dir():
        msg = "--tmpdir must exist"
        raise ValueError(msg)
    if input_path is None:
        return
    payload = parse_token_record_sidecar(input_path)
    if payload is None:
        if (not input_path.is_file() or input_path.stat().st_size == 0) and not (tmpdir / "execution-issues.md").exists():
            print(f"append token record: token sidecar absent: {input_path}", file=sys.stderr)
        return
    with (tmpdir / "token-report.ndjson").open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def _raw_tool_from_sidecar(input_path: Path | None) -> str:
    if input_path is None or not input_path.is_file():
        return ""
    return larch_io.kv_value(larch_io.read_text(input_path, errors="replace"), "TOOL", default="")


def record_vendor_from_sidecar(*, input_path: Path | None, ledger: str | None = None) -> None:
    payload = parse_token_record_sidecar(input_path)
    if payload is None:
        return
    vendor = str(payload.get("tool") or "unknown")
    if vendor == "claude":
        vendor = "claude_sub"
    if vendor not in {"codex", "cursor", "claude_sub"}:
        raw_tool = _raw_tool_from_sidecar(input_path)
        raw_note = f" (raw TOOL={raw_tool})" if raw_tool and raw_tool != vendor else ""
        print(
            f"token record-vendor-sidecar: unsupported TOOL={vendor}{raw_note}; active-ledger append skipped for {input_path}",
            file=sys.stderr,
        )
        return
    ledger_path = resolve_token_ledger_path(ledger=ledger)
    if ledger_path is None:
        return
    TokenLedger(ledger_path).record_vendor(
        vendor,
        input=_int_field(data=payload, key="input"),
        output=_int_field(data=payload, key="output"),
        cache_read=_int_field(data=payload, key="cache_read"),
        cache_create=_int_field(data=payload, key="cache_create"),
        total=_int_field(data=payload, key="total"),
        raw=str(payload.get("raw") or ""),
        model=str(payload.get("model") or ""),
    )


@dataclass(frozen=True)
class ResearchLaneTally:
    root: Path

    def _validate_root(self) -> None:
        validate_research_dir(self.root)

    def write(self, *, phase: str, lane: str, tool: str, total_tokens: str) -> None:
        self._validate_root()
        if phase not in {"research", "validation"}:
            msg = "--phase must be research or validation"
            raise ValueError(msg)
        if total_tokens != "unknown" and not _UINT_RE.fullmatch(total_tokens):
            msg = "--total-tokens must be a non-negative integer or 'unknown'"
            raise ValueError(msg)
        self.root.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^a-z0-9]", "-", lane.lower())
        _ = (self.root / f"lane-tokens-{phase}-{safe}.txt").write_text(
            f"PHASE={phase}\nLANE={lane}\nTOOL={tool}\nTOTAL_TOKENS={total_tokens}\n",
            encoding="utf-8",
        )

    def report(self) -> str:
        self._validate_root()
        lines = ["## Token Spend (Claude tokens only; external lanes excluded)", ""]
        if not self.root.is_dir():
            return "\n".join([*lines, "_(token telemetry unavailable: $RESEARCH_TMPDIR was already removed)_"])
        totals = {"research": 0, "validation": 0}
        measured = {"research": 0, "validation": 0}
        unknown = {"research": 0, "validation": 0}
        lanes: dict[str, list[str]] = {"research": [], "validation": []}
        for sidecar in sorted(self.root.glob("lane-tokens-*.txt")):
            kv = larch_io.parse_kv(larch_io.read_text(sidecar, errors="replace"))
            phase = kv.get("PHASE", "")
            if phase not in lanes:
                continue
            lanes[phase].append(kv.get("LANE", ""))
            total = kv.get("TOTAL_TOKENS", "")
            if _UINT_RE.fullmatch(total):
                totals[phase] += int(total)
                measured[phase] += 1
            else:
                unknown[phase] += 1
        if not lanes["research"] and not lanes["validation"]:
            return "\n".join([*lines, "_(no measurements available — Claude inline only, no measurable subagent invocations)_"])
        rate_raw = os.environ.get("LARCH_TOKEN_RATE_PER_M", "")
        try:
            rate = float(rate_raw)
        except ValueError:
            rate = 0.0
        def row(*, label: str, phase: str) -> str:
            if not lanes[phase]:
                suffix = "(4 lanes — Codex-first with per-lane Claude fallback): not measured" if phase == "research" else "(3 reviewers — Code|Cursor|Codex): not measured"
                return f"  {label:<22} {suffix}"
            count = measured[phase] + unknown[phase]
            cov = f"({count} lanes, {measured[phase]} measured" + (f", {unknown[phase]} unmeasurable)" if unknown[phase] else ")")
            cost = f"  ${(totals[phase] * rate) / 1_000_000:.4f}" if rate > 0 and totals[phase] > 0 else ""
            return f"  {label:<22}{cov}: total={totals[phase]}{cost}"
        lines.extend([row(label="Research phase", phase="research"), row(label="Validation phase", phase="validation")])
        grand = totals["research"] + totals["validation"]
        total_measured = measured["research"] + measured["validation"]
        total_unknown = unknown["research"] + unknown["validation"]
        total_lanes = total_measured + total_unknown
        cov = f"({total_lanes} lanes, {total_measured} measured" + (f", {total_unknown} unmeasurable)" if total_unknown else ")")
        cost = f"  ${(grand * rate) / 1_000_000:.4f}" if rate > 0 and grand > 0 else ""
        lines.extend([f"  {'Total':<22} {cov}: total={grand}{cost}", "", "_Note: only Claude subagent (Agent-tool) invocations report token counts. Claude inline (orchestrator) and external lanes (Cursor/Codex) are excluded from the totals above._"])
        return "\n".join(lines)


def validate_research_dir(path: Path) -> None:
    raw = str(path)
    if not raw or ".." in path.parts:
        msg = f"--dir must not contain '..' segments (got: {path})"
        raise ValueError(msg)
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "larch" / "sessions"
    prefixes = [Path("/tmp"), Path("/private/tmp"), cache_root]
    if not any(raw.startswith(str(prefix) + "/") or raw == str(prefix) for prefix in prefixes):
        msg = f"--dir must be under /tmp/, /private/tmp/, or {cache_root}/ (got: {path})"
        raise ValueError(msg)
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if not probe.exists() or probe.is_file():
        msg = f"--dir nearest existing ancestor is not a directory: {probe}"
        raise ValueError(msg)
    resolved = probe.resolve(strict=True)
    allowed = [p.resolve() for p in prefixes if p.exists()]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        msg = f"--dir resolves outside allowed roots: {resolved}"
        raise ValueError(msg)


def compute_pr_line_counts(*, pr_number: int, repo: str | None = None) -> dict[str, int | str]:
    if pr_number < 1:
        return {"LINES_STATUS": "skipped", "REASON": "no-pr"}
    if repo is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return {"LINES_STATUS": "skipped", "REASON": "invalid-repo"}
    endpoint = f"repos/{repo}/pulls/{pr_number}/files" if repo else f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files"
    try:
        out = subprocess.check_output(["gh", "api", "--paginate", endpoint, "--jq", ".[] | [.filename, .additions, .deletions] | @tsv"], text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return {"LINES_STATUS": "unavailable", "REASON": "gh-failed"}
    code_added = code_deleted = logs_added = logs_deleted = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added = int(parts[1] or 0)
        deleted = int(parts[2] or 0)
        if parts[0].startswith("larch-logs/"):
            logs_added += added
            logs_deleted += deleted
        else:
            code_added += added
            code_deleted += deleted
    return {"LINES_STATUS": "ok", "CODE_ADDED": code_added, "CODE_DELETED": code_deleted, "LOGS_ADDED": logs_added, "LOGS_DELETED": logs_deleted}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


_REPORT_FORMATS = frozenset({"json", "markdown"})
_CACHE_READ_PATH_RE = re.compile(r"/larch/[^/]+/(.+)$")


def _validate_report_format(fmt: str) -> None:
    if fmt not in _REPORT_FORMATS:
        msg = f"unknown format: {fmt}"
        raise ValueError(msg)


def _claude_root_imports(repo: Path) -> set[str]:
    imports: set[str] = set()
    claude = repo / "CLAUDE.md"
    if not claude.is_file():
        return imports
    for line in claude.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            target = stripped[1:].split()[0]
            if target.endswith(".md") and not target.startswith("/"):
                imports.add(target)
    return imports


def _classify_md_tier(*, rel: str, tier1_imports: set[str]) -> str:
    if rel == "CLAUDE.md":
        return "tier-1a-claude-root"
    if rel in tier1_imports:
        return "tier-1a-claude-import"
    if rel.startswith("skills/") and rel.endswith("/SKILL.md"):
        return "tier-1b-runtime-skill"
    if rel.startswith(".claude/skills/") and rel.endswith("/SKILL.md"):
        return "tier-1b-dev-skill"
    if rel.startswith(".claude/rules/") and rel.endswith(".md"):
        return "tier-1c-claude-rule"
    if rel.startswith("skills/shared/"):
        return "tier-2-shared-reference"
    if "/references/" in rel:
        return "tier-2-skill-reference"
    if rel.startswith("scripts/"):
        return "tier-2-script-doc"
    if rel.startswith("docs/"):
        return "tier-3-doc"
    if rel.startswith("larch-logs/"):
        return "tier-4-run-log"
    return "tier-3-other"


def _normalize_read_path(*, raw: object, repo: Path) -> str | None:
    if not isinstance(raw, str) or not raw.endswith(".md"):
        return None
    path = raw
    if path.startswith("<"):
        return None
    repo_prefix = f"{repo}/"
    if path.startswith(repo_prefix):
        path = path[len(repo_prefix) :]
    else:
        match = _CACHE_READ_PATH_RE.search(path)
        if match:
            path = match.group(1)
    if path.startswith(("/", "../")) or "/../" in path:
        return None
    return path


def _normalize_realized_skill(raw: object) -> str:
    if not raw:
        return ""
    skill = str(raw)
    if skill.startswith("larch:"):
        skill = skill.split(":", 1)[1]
    if skill.startswith("inferred:"):
        return ""
    return skill


def _manifest_issue(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    data_d = cast("dict[str, Any]", data) if isinstance(data, dict) else None
    issue = data_d.get("issue_number") if data_d is not None else None
    if isinstance(issue, int):
        return str(issue)
    if isinstance(issue, str) and issue:
        return issue
    return None


def _skill_md_path(*, repo: Path, skill: str) -> Path | None:
    for candidate in (repo / "skills" / skill / "SKILL.md", repo / ".claude" / "skills" / skill / "SKILL.md"):
        if candidate.is_file():
            return candidate
    return None


def _ngram_source_files(repo: Path) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    for rel in ("CLAUDE.md", *_claude_root_imports(repo)):
        if rel not in seen and (repo / rel).is_file():
            seen.add(rel)
            files.append(rel)
    for pattern in ("skills/*/SKILL.md", ".claude/skills/*/SKILL.md"):
        tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z", pattern]).split(b"\0")
        for raw in tracked:
            if not raw:
                continue
            rel = raw.decode()
            if rel not in seen and (repo / rel).is_file():
                seen.add(rel)
                files.append(rel)
    return files


def _measure_stamp() -> str:
    return os.environ.get("LARCH_MEASURE_DATE", datetime.now().strftime("%Y-%m-%d"))


# Subprocess-isolated tiktoken encoder: the string literal below is not an AST Import
# node, so test_stdlib_only.py does not flag tokens.py for a tiktoken dependency.
_TIKTOKEN_ENCODE_SCRIPT = (
    "import sys, json, tiktoken; "
    "enc = tiktoken.get_encoding('cl100k_base'); "
    "print(json.dumps([len(enc.encode(t)) for t in json.loads(sys.stdin.read())]))"
)


def _tiktoken_count_texts(texts: list[str]) -> list[int]:
    """Run tiktoken in a subprocess and return per-text token counts."""
    result = subprocess.run(
        ["python3", "-c", _TIKTOKEN_ENCODE_SCRIPT],
        input=json.dumps(texts).encode(),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover
        msg = result.stderr.decode(errors="replace").strip()
        raise SystemExit(f"tiktoken required: {msg}")
    return cast("list[int]", json.loads(result.stdout.decode()))


def measure_md_cost() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-md-cost" / f"{_measure_stamp()}.tsv"
    files = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z", "*.md"], stderr=subprocess.DEVNULL).split(b"\0")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tier1_imports = _claude_root_imports(repo)
    entries: list[tuple[str, str, int, str, int, int]] = []
    texts: list[str] = []
    for raw in files:
        if not raw:
            continue
        rel = raw.decode()
        path = repo / rel
        if not path.is_file():
            continue
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        tier = _classify_md_tier(rel=rel, tier1_imports=tier1_imports)
        line_count = text.count(chr(10)) + (0 if text.endswith(chr(10)) or text == "" else 1)
        h2_count = sum(1 for line in text.splitlines() if line.startswith("## "))
        entries.append((rel, tier, len(data), text, line_count, h2_count))
        texts.append(text)
    entries.sort(key=lambda row: (row[1], row[0]))
    token_counts = _tiktoken_count_texts(texts)
    rows = ["path\ttier\tbytes\ttokens\tlines\th2_count\n"]
    for (rel, tier, byte_count, _text, line_count, h2_count), tok in zip(entries, token_counts, strict=False):
        rows.append(f"{rel}\t{tier}\t{byte_count}\t{tok}\t{line_count}\t{h2_count}\n")
    _atomic_text(path=out_path, text="".join(rows))
    return out_path


def measure_ngram_duplication() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-ngram-duplication" / f"{_measure_stamp()}.txt"
    size = int(os.environ.get("LARCH_MEASURE_NGRAM_SIZE", "6"))
    min_files = int(os.environ.get("LARCH_MEASURE_NGRAM_MIN_FILES", "3"))
    limit = int(os.environ.get("LARCH_MEASURE_NGRAM_LIMIT", "50"))
    word_re = re.compile(r"[A-Za-z0-9_./$:-]+")
    occurrences: collections.Counter[str] = collections.Counter()
    file_hits: dict[str, set[str]] = collections.defaultdict(set)
    for rel in _ngram_source_files(repo):
        path = repo / rel
        words = word_re.findall(path.read_text(encoding="utf-8", errors="replace").lower())
        for idx in range(max(0, len(words) - size + 1)):
            shingle = " ".join(words[idx : idx + size])
            occurrences[shingle] += 1
            file_hits[shingle].add(rel)
    ranked = sorted(((count * size, count, len(file_hits[shingle]), shingle) for shingle, count in occurrences.items() if len(file_hits[shingle]) >= min_files), key=lambda row: (-row[0], -row[1], row[3]))
    lines = ["score\toccurrences\tfiles\tshingle\n", *[f"{score}\t{count}\t{files}\t{shingle}\n" for score, count, files, shingle in ranked[:limit]]]
    _atomic_text(path=out_path, text="".join(lines))
    return out_path


def measure_references_heatmap() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-references-heatmap" / f"{_measure_stamp()}.tsv"
    counts: collections.Counter[str] = collections.Counter()
    for transcript in sorted((repo / "larch-logs").glob("*/*/session-transcript.jsonl")):
        for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            obj_d = cast("dict[str, Any]", obj) if isinstance(obj, dict) else None
            message_raw = obj_d.get("message") if obj_d is not None else None
            message = cast("dict[str, Any]", message_raw) if isinstance(message_raw, dict) else None
            content = message.get("content") if message is not None else None
            if not isinstance(content, list):
                continue
            for item_raw in cast("list[Any]", content):
                item = cast("dict[str, Any]", item_raw) if isinstance(item_raw, dict) else None
                if item is not None and item.get("type") == "tool_use" and item.get("name") == "Read":
                    tool_input_raw = item.get("input")
                    tool_input = cast("dict[str, Any]", tool_input_raw) if isinstance(tool_input_raw, dict) else None
                    rel = _normalize_read_path(raw=tool_input.get("file_path") if tool_input is not None else None, repo=repo)
                    if rel:
                        counts[rel] += 1
    rows = [(rel, count, (repo / rel).stat().st_size if (repo / rel).is_file() else 0) for rel, count in counts.items()]
    rows.sort(key=lambda row: (-row[1], -row[2], row[0]))
    _atomic_text(path=out_path, text="references_path\treads_observed\tbytes\n" + "".join(f"{rel}\t{count}\t{size}\n" for rel, count, size in rows))
    return out_path


def measure_realized_cost() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-realized-cost" / f"{_measure_stamp()}.tsv"
    invocations: collections.Counter[str] = collections.Counter()
    issues_by_skill: dict[str, set[str]] = collections.defaultdict(set)
    for run_dir in sorted((repo / "larch-logs").glob("*/*")):
        if not run_dir.is_dir():
            continue
        issue = _manifest_issue(run_dir / "manifest.json")
        skills_in_run: set[str] = set()
        timing_json = run_dir / "timing-report.json"
        timing_md = run_dir / "timing-report.md"
        if timing_json.is_file():
            try:
                data = json.loads(timing_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            if isinstance(data, dict):
                data_typed = cast("dict[str, Any]", data)
                for row in cast("list[Any]", data_typed.get("per_step", [])):
                    if isinstance(row, dict):
                        row_d = cast("dict[str, Any]", row)
                        skill = _normalize_realized_skill(str(row_d.get("skill") or ""))
                        if skill:
                            skills_in_run.add(skill)
        if timing_md.is_file():
            for line in timing_md.read_text(encoding="utf-8", errors="replace").splitlines():
                match = re.match(r"^\|\s*([^|*][^|]*?)\s*\|\s*Step\b", line)
                if match:
                    skill = _normalize_realized_skill(match.group(1).strip())
                    if skill and skill.lower() not in {"skill", "---"}:
                        skills_in_run.add(skill)
        if not skills_in_run:
            manifest_path = run_dir / "manifest.json"
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    manifest = {}
                if isinstance(manifest, dict):
                    manifest_d = cast("dict[str, Any]", manifest)
                    skill = _normalize_realized_skill(str(manifest_d.get("skill") or ""))
                    if skill:
                        skills_in_run.add(skill)
        for skill in skills_in_run:
            invocations[skill] += 1
            if issue:
                issues_by_skill[skill].add(issue)
    skill_texts: list[tuple[str, int, int, str]] = []
    for skill, count in invocations.items():
        path = _skill_md_path(repo=repo, skill=skill)
        if path is not None:
            skill_texts.append((skill, count, len(issues_by_skill[skill]), path.read_text(encoding="utf-8", errors="replace")))
    token_counts = _tiktoken_count_texts([text for _, _, _, text in skill_texts])
    rows = [
        (skill, count, issue_count, tok, count * tok)
        for (skill, count, issue_count, _), tok in zip(skill_texts, token_counts, strict=False)
    ]
    rows.sort(key=lambda row: (-row[4], row[0]))
    _atomic_text(
        path=out_path,
        text="skill\tinvocations\tissues_observed\ttokens_per_invocation\trealized_tokens\n"
        + "".join(f"{skill}\t{count}\t{issue_count}\t{tokens_count}\t{realized}\n" for skill, count, issue_count, tokens_count, realized in rows),
    )
    return out_path


def _atomic_text(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path, text, prefix=f".{path.name}.", nofollow=True, newline="\n")


def _pop_ledger(argv: list[str]) -> tuple[list[str], str | None]:
    out: list[str] = []
    ledger: str | None = None
    idx = 0
    while idx < len(argv):
        if argv[idx] == "--ledger":
            if idx + 1 >= len(argv):
                raise ValueError("--ledger requires a value")
            ledger = argv[idx + 1]
            idx += 2
        else:
            out.append(argv[idx])
            idx += 1
    return out, ledger


def token_mark_main(argv: list[str] | None = None) -> int:
    args, ledger_override = _pop_ledger(list(argv if argv is not None else sys.argv[1:]))
    if not args:
        print("token mark requires <step>", file=sys.stderr)
        return 1
    try:
        ledger = resolve_token_ledger_path(ledger=ledger_override)
    except ValueError as exc:
        print(f"token mark: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    try:
        TokenLedger(ledger).mark(args[0])
    except (OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            print(f"token mark: {exc}", file=sys.stderr)
            return 1
        print(f"token mark: write skipped: {exc}", file=sys.stderr)
    return 0


def token_record_vendor_main(argv: list[str] | None = None) -> int:
    args, ledger_override = _pop_ledger(list(argv if argv is not None else sys.argv[1:]))
    if not args:
        print("token record-vendor requires <vendor>", file=sys.stderr)
        return 1
    vendor = args[0]
    vals: dict[str, Any] = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "total": 0, "raw": "", "model": ""}
    for kv in args[1:]:
        key, sep, value = kv.partition("=")
        if not sep or key not in vals:
            print(f"token record-vendor: unknown argument: {kv}", file=sys.stderr)
            return 1
        if key in {"raw", "model"}:
            vals[key] = value
        elif _UINT_RE.fullmatch(value):
            vals[key] = int(value)
        else:
            print(f"token record-vendor: {key} must be a non-negative integer", file=sys.stderr)
            return 1
    try:
        ledger = resolve_token_ledger_path(ledger=ledger_override)
    except ValueError as exc:
        print(f"token record-vendor: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    try:
        TokenLedger(ledger).record_vendor(vendor, **vals)
    except (OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            print(f"token record-vendor: {exc}", file=sys.stderr)
            return 1
        print(f"token record-vendor: write skipped: {exc}", file=sys.stderr)
    return 0


def token_record_vendor_sidecar_main(argv: list[str] | None = None) -> int:
    args, ledger_override = _pop_ledger(list(argv if argv is not None else sys.argv[1:]))
    opts = _flag_map(args)
    try:
        input_path = Path(opts["--input"]) if opts.get("--input") else None
        record_vendor_from_sidecar(input_path=input_path, ledger=ledger_override)
    except (KeyError, ValueError) as exc:
        print(f"token record-vendor-sidecar: {exc}", file=sys.stderr)
        return 2
    return 0


def token_dump_main(argv: list[str] | None = None) -> int:
    _, ledger_override = _pop_ledger(list(argv if argv is not None else sys.argv[1:]))
    try:
        ledger = resolve_token_ledger_path(ledger=ledger_override)
    except ValueError as exc:
        print(f"token dump: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    print(ledger)
    if ledger.is_file() and ledger.stat().st_size > 0:
        _ = sys.stdout.write(ledger.read_text(encoding="utf-8"))
    return 0


def token_report_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    mode = ""
    fmt = "markdown"
    output: Path | None = None
    ledger: Path | None = None
    transcript: Path | None = None
    session_dir: Path | None = None
    append: Path | None = None
    buckets = False
    vendor: str | None = None
    idx = 0
    try:
        while idx < len(args):
            arg = args[idx]
            if arg in ("--since-last-mark", "--terse"):
                mode = "terse"; idx += 1
            elif arg == "--summary":
                mode = "summary"; idx += 1
            elif arg == "--full":
                mode = "full"; idx += 1
            elif arg == "--markdown":
                fmt = "markdown"; idx += 1
            elif arg == "--format":
                fmt = args[idx + 1]; idx += 2
            elif arg == "--output":
                output = Path(args[idx + 1]); idx += 2
            elif arg == "--ledger":
                ledger = _validate_under_tmp(args[idx + 1]); idx += 2
            elif arg == "--transcript":
                transcript = Path(args[idx + 1]); idx += 2
            elif arg == "--session-dir":
                session_dir = Path(args[idx + 1]); idx += 2
            elif arg == "--append-token-report":
                append = Path(args[idx + 1]); mode = "full"; idx += 2
            elif arg == "--buckets":
                buckets = True; idx += 1
            elif arg == "--vendor":
                vendor = args[idx + 1]; idx += 2
            else:
                raise ValueError(f"unknown flag: {arg}")
        if buckets:
            rendered = token_report(ledger_path=ledger, transcript_path=transcript, session_dir=session_dir, buckets=True, vendor=vendor)
            print(rendered)
            return 0
        if not mode:
            raise ValueError("missing report mode")
        _validate_report_format(fmt)
        rendered = token_report(ledger_path=ledger, transcript_path=transcript, session_dir=session_dir, mode=mode, fmt=fmt, append_token_report=append)
        text = json.dumps(rendered, sort_keys=True) + "\n" if isinstance(rendered, dict) else str(rendered) + "\n"
        if mode == "full" and output is not None:
            tmp = output.with_name(output.name + ".tmp")
            _ = tmp.write_text(text, encoding="utf-8")
            _ = tmp.replace(output)
        elif append is None:
            _ = sys.stdout.write(text)
    except (IndexError, OSError, ValueError) as exc:
        print(f"Token report unavailable: {exc}", file=sys.stderr)
        return 0
    return 0


def token_check_budget_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    cap: int | None = None
    step = "unknown"
    idx = 0
    while idx < len(args):
        if args[idx] == "--cap":
            cap = int(args[idx + 1]); idx += 2
        elif args[idx] == "--step":
            step = args[idx + 1]; idx += 2
        else:
            print(f"token check-budget: unknown flag: {args[idx]}", file=sys.stderr)
            return 1
    if cap is None or cap < 1:
        print("token check-budget: --cap must be >= 1", file=sys.stderr)
        return 1
    result = check_step_token_budget(cap=cap, step=step)
    print(f"STATUS={result['status']} TOTAL={result['total']} CAP={result['cap']} STEP={result['step']}")
    return 0


def token_claude_source_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    snap = Path(args[0]) if args else None
    result = token_claude_source(claude_source_file=snap)
    for key in ("TRANSCRIPT_PATH", "SESSION_DIR", "SESSION_UUID", "STATUS", "REASON"):
        if key in result:
            print(f"{key}={result[key]}")
    return 0 if "TRANSCRIPT_PATH" in result else 1


def token_lane_write_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    opts = _flag_map(args)
    try:
        ResearchLaneTally(Path(opts["--dir"])).write(phase=opts["--phase"], lane=opts["--lane"], tool=opts["--tool"], total_tokens=opts["--total-tokens"])
    except (KeyError, ValueError) as exc:
        print(f"token lane-write: {exc}", file=sys.stderr)
        return 1
    return 0


def token_lane_report_main(argv: list[str] | None = None) -> int:
    opts = _flag_map(list(argv if argv is not None else sys.argv[1:]))
    try:
        print(ResearchLaneTally(Path(opts["--dir"])).report())
    except (KeyError, ValueError) as exc:
        print(f"token lane-report: {exc}", file=sys.stderr)
        return 1
    return 0


def token_append_record_main(argv: list[str] | None = None) -> int:
    opts = _flag_map(list(argv if argv is not None else sys.argv[1:]))
    try:
        tmpdir = Path(opts["--tmpdir"])
        input_path = Path(opts["--input"]) if opts.get("--input") else None
        append_token_record_from_sidecar(input_path=input_path, tmpdir=tmpdir)
    except (KeyError, ValueError) as exc:
        print(f"token append-record: {exc}", file=sys.stderr)
        return 2
    return 0


def token_cost_main(argv: list[str] | None = None) -> int:
    from report_tokens_cost import token_cost_main as main
    return main(argv)


def token_cost_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    from report_tokens_cost import token_cost_from_args as main
    return main(argv, env=env)


def token_render_cost_line_main(argv: list[str] | None = None) -> int:
    from report_tokens_cost import render_cost_line_main as main
    return main(argv)


def render_cost_line_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    from report_tokens_cost import render_cost_line_from_args as main
    return main(argv, env=env)


def _cost_breakdown_type() -> type[Any]:
    from report_tokens_cost import CostBreakdown as CostBreakdownType
    return CostBreakdownType


CostBreakdown = _cost_breakdown_type()


def compute_pr_lines_main(argv: list[str] | None = None) -> int:
    return compute_pr_line_counts_main(argv)


def compute_pr_line_counts_main(argv: list[str] | None = None) -> int:
    opts = _flag_map(list(argv if argv is not None else sys.argv[1:]))
    pr_raw = opts.get("--pr-number", "")
    if not _UINT_RE.fullmatch(pr_raw or "") or int(pr_raw) == 0:
        print("LINES_STATUS=skipped\nREASON=no-pr")
        return 0
    result = compute_pr_line_counts(pr_number=int(pr_raw), repo=opts.get("--repo") or None)
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


def measure_md_cost_main(argv: list[str] | None = None) -> int:
    _ = argv
    path = measure_md_cost()
    print(f"WROTE\t{path.relative_to(_repo_root())}")
    return 0


def measure_ngram_duplication_main(argv: list[str] | None = None) -> int:
    _ = argv
    path = measure_ngram_duplication()
    print(f"WROTE\t{path.relative_to(_repo_root())}")
    return 0


def measure_references_heatmap_main(argv: list[str] | None = None) -> int:
    _ = argv
    path = measure_references_heatmap()
    print(f"WROTE\t{path.relative_to(_repo_root())}")
    return 0


def measure_realized_cost_main(argv: list[str] | None = None) -> int:
    _ = argv
    path = measure_realized_cost()
    print(f"WROTE\t{path.relative_to(_repo_root())}")
    return 0


def _flag_map(args: list[str]) -> dict[str, str]:
    opts: dict[str, str] = {}
    idx = 0
    while idx < len(args):
        if not args[idx].startswith("--"):
            idx += 1
            continue
        if idx + 1 >= len(args) or args[idx + 1].startswith("--"):
            opts[args[idx]] = ""
            idx += 1
        else:
            opts[args[idx]] = args[idx + 1]
            idx += 2
    return opts
