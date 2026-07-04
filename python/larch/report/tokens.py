# ruff: noqa: PLC0415, N801, S108, FURB162, PLR1714, S607, PLR2004, DTZ005, E702
# pylint: disable=all
"""Token scraping, ledgers, reports, and cost helpers."""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Literal, cast
from collections.abc import Mapping, Sequence

from larch import io as larch_io
from larch.core import config
from larch.errors import ShipError
from larch.report import run_log_corpus
from larch.report.report_tokens_models import RunRecord, Skill, VendorTotals, safe_int
from larch.rendering.render_session_transcript import strip_plugin_cache_read_suffix

_TOKEN_FIELDS = ("input", "output", "cache_read", "cache_create", "total")
TOKEN_LOCK_TIMEOUT_S = 5.0
_SAFE_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_UINT_RE = re.compile(r"^[0-9]+$")
_SIGNED_INT_RE = re.compile(r"^-?[0-9]+$")
CHECKS_DIGEST_SIZE_BASENAME = "checks-digest-sizes.tsv"
_CHECKS_DIGEST_MIN_SAMPLES = 5
_CHECKS_DIGEST_UNSIGNED_FIELDS = ("redacted_bytes", "digest_bytes", "redacted_tokens", "digest_tokens")
_CHECKS_DIGEST_SIGNED_FIELDS = ("saved_bytes", "saved_tokens")
_CHECKS_DIGEST_SIZE_FIELDS = (
    "site",
    "attempt",
    *_CHECKS_DIGEST_UNSIGNED_FIELDS,
    *_CHECKS_DIGEST_SIGNED_FIELDS,
    "digest_truncated",
)
_CHECKS_DIGEST_SAVINGS_REPORT_FIELDS = (
    "status",
    "recommendation",
    "valid_rows",
    "files_observed",
    "rows_seen",
    "rows_skipped",
    "redacted_bytes",
    "digest_bytes",
    "redacted_tokens",
    "digest_tokens",
    "saved_bytes",
    "saved_tokens",
)


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


PANEL_PROMPT_SIZE_BASENAME = "panel-prompt-sizes.tsv"
_PANEL_PROMPT_SIZE_FIELDS = (
    "site",
    "phase",
    "round_num",
    "slot",
    "slot_kind",
    "tool",
    "output",
    "prompt_bytes",
    "prompt_tokens",
    "scaffold_bytes",
    "scaffold_tokens",
    "payload_bytes",
    "payload_tokens",
    "agent_file",
    "agent_bytes",
    "agent_tokens",
)
_PANEL_PROMPT_SIZE_LEGACY_FIELDS = (
    "site",
    "phase",
    "round_num",
    "slot",
    "slot_kind",
    "tool",
    "output",
    "prompt_bytes",
    "prompt_tokens",
    "agent_file",
    "agent_bytes",
    "agent_tokens",
)
_PANEL_SLOT_KINDS = frozenset({"specialist", "plan-review", "voter", "aggregator", "implementer"})
_PANEL_SPECIALIST_SLOT_NAMES = frozenset({"correctness", "edge-cases", "testing", "generalist"})
_PANEL_ROUND_RE = re.compile(r"^round-([0-9]+)$")


@dataclass(frozen=True)
class PanelPromptSizeRow:
    site: str
    phase: str
    round_num: str
    slot: str
    slot_kind: str
    tool: str
    output: str
    prompt_bytes: int
    prompt_tokens: int
    scaffold_bytes: int = 0
    scaffold_tokens: int = 0
    payload_bytes: int = 0
    payload_tokens: int = 0
    agent_file: str = ""
    agent_bytes: int = 0
    agent_tokens: int = 0

    def as_tsv_row(self) -> list[str]:
        return [
            self.site,
            self.phase,
            self.round_num,
            self.slot,
            self.slot_kind,
            self.tool,
            self.output,
            str(self.prompt_bytes),
            str(self.prompt_tokens),
            str(self.scaffold_bytes),
            str(self.scaffold_tokens),
            str(self.payload_bytes),
            str(self.payload_tokens),
            self.agent_file,
            str(self.agent_bytes),
            str(self.agent_tokens),
        ]


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



def _estimate_tokens_for_bytes(byte_count: int) -> int:
    return (max(0, byte_count) + 3) // 4


def _path_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except (OSError, ValueError):
        return False
    return True


def _repo_relative_agent_path(raw: str | Path | None) -> tuple[str, int, int]:
    if raw is None or str(raw) == "":
        return "", 0, 0
    repo = _repo_root()
    path = Path(raw)
    if not path.is_absolute():
        path = repo / path
    try:
        if path.is_symlink():
            return "", 0, 0
        resolved = path.resolve(strict=True)
    except OSError:
        return "", 0, 0
    if not _path_under(resolved, repo) or not resolved.is_file():
        return "", 0, 0
    try:
        data = resolved.read_bytes()
    except OSError:
        return "", 0, 0
    rel = resolved.relative_to(repo.resolve()).as_posix()
    return rel, len(data), _estimate_tokens_for_bytes(len(data))


def _panel_slot_kind_from_env(env: Mapping[str, str] | None = None, *, slot_kind: str = "") -> str:
    if slot_kind in _PANEL_SLOT_KINDS:
        return slot_kind
    env_map = os.environ if env is None else env
    slot = (env_map.get("LARCH_PANEL_SLOT") or "").strip()
    phase = (env_map.get("LARCH_PANEL_PHASE") or "").strip().lower()
    site = (env_map.get("LARCH_PANEL_SITE") or "").strip().lower()
    task = (env_map.get("LARCH_TIMING_TASK_KIND") or "").strip().lower()
    if not slot:
        return ""
    lowered = slot.lower()
    if lowered == "implementer":
        return "implementer"
    if lowered == "aggregator" or "aggregator" in phase:
        return "aggregator"
    if "voter" in lowered or "vote" in lowered or "voter" in phase or "voter" in task:
        return "voter"
    if "plan-review" in phase or "design" in site:
        return "plan-review"
    if "specialist" in lowered or lowered.startswith("dyn-") or lowered in _PANEL_SPECIALIST_SLOT_NAMES:
        return "specialist"
    if "-plan-" in lowered:
        return "plan-review"
    return ""


def _panel_logging_enabled(env: Mapping[str, str] | None = None) -> bool:
    return _panel_slot_kind_from_env(env) in _PANEL_SLOT_KINDS


def _round_num_from_path(path: Path | None) -> int | None:
    if path is None:
        return None
    for part in reversed(path.parts):
        match = _PANEL_ROUND_RE.fullmatch(part)
        if match:
            return int(match.group(1))
    return None


def _round_dir_from_output(output: Path) -> Path | None:
    for parent in (output.parent, *output.parents):
        if _PANEL_ROUND_RE.fullmatch(parent.name):
            return parent
    return None


def _valid_panel_artifact_dir(raw: str) -> Path | None:
    if not raw or "\x00" in raw:
        return None
    try:
        path = Path(raw)
    except (OSError, ValueError):
        return None
    return path if str(path) else None


def panel_prompt_size_artifact_for_output(*, output: Path, site: str = "", round_dir: Path | None = None) -> Path:
    env_dir = _valid_panel_artifact_dir(os.environ.get("LARCH_PANEL_ARTIFACT_DIR", ""))
    if env_dir is not None:
        return env_dir / PANEL_PROMPT_SIZE_BASENAME
    if round_dir is not None:
        return round_dir / PANEL_PROMPT_SIZE_BASENAME
    env_round = _valid_panel_artifact_dir(os.environ.get("LARCH_PANEL_ROUND_DIR", ""))
    if env_round is not None and _PANEL_ROUND_RE.fullmatch(env_round.name):
        return env_round / PANEL_PROMPT_SIZE_BASENAME
    output_round = _round_dir_from_output(output)
    if output_round is not None:
        return output_round / PANEL_PROMPT_SIZE_BASENAME
    _ = site
    return output.parent / PANEL_PROMPT_SIZE_BASENAME


def resolve_panel_artifact_dir(*, review_tmpdir: Path, round_num: int | None = None) -> tuple[Path, Path | None]:
    if _PANEL_ROUND_RE.fullmatch(review_tmpdir.name):
        return review_tmpdir, review_tmpdir
    if round_num is not None:
        round_subdir = review_tmpdir / f"round-{round_num}"
        if round_subdir.is_dir():
            return round_subdir, round_subdir
    return review_tmpdir, None


def build_panel_dispatch_env(
    *,
    artifact_dir: Path,
    site: str,
    round_num: int | None = None,
    round_dir: Path | None = None,
    slot: str = "",
    phase: str = "",
    primary_tool: str = "",
    source_agent_file: str = "",
    payload_bytes: int | str | None = None,
) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("LARCH_PANEL_PAYLOAD_BYTES", None)
    env["LARCH_PANEL_ARTIFACT_DIR"] = str(artifact_dir)
    env["LARCH_PANEL_SITE"] = site
    env["LARCH_PANEL_SLOT"] = slot
    env["LARCH_PANEL_PHASE"] = phase
    env["LARCH_PANEL_PRIMARY_TOOL"] = primary_tool
    env["LARCH_PANEL_SOURCE_AGENT_FILE"] = source_agent_file
    effective_round_dir = round_dir
    if effective_round_dir is None and _PANEL_ROUND_RE.fullmatch(artifact_dir.name):
        effective_round_dir = artifact_dir
    if effective_round_dir is not None:
        env["LARCH_PANEL_ROUND_DIR"] = str(effective_round_dir)
    effective_round_num = round_num if round_num is not None else _round_num_from_path(effective_round_dir or artifact_dir)
    if effective_round_num is not None:
        env["LARCH_PANEL_ROUND_NUM"] = str(effective_round_num)
    parsed_payload = _parse_panel_payload_bytes(payload_bytes)
    if parsed_payload is not None:
        env["LARCH_PANEL_PAYLOAD_BYTES"] = str(parsed_payload)
    return env


def _locked_tsv_append(path: Path, write_fn: Any) -> None:
    _ensure_regular_file(path)
    try:
        import fcntl
    except ImportError:  # pragma: no cover
        with path.open("a", encoding="utf-8", newline="") as handle:
            write_fn(handle, path.stat().st_size == 0)
    else:
        deadline = time.monotonic() + TOKEN_LOCK_TIMEOUT_S
        with path.open("a+", encoding="utf-8", newline="") as handle:
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        print(
                            f"locked tsv append: WARNING: flock lock acquisition failed; skipping append for {path}",
                            file=sys.stderr,
                        )
                        return
                    time.sleep(0.05)
            try:
                handle.seek(0)
                text = handle.read()
                if _migrate_panel_prompt_size_legacy_header(handle, text):
                    handle.seek(0, os.SEEK_END)
                handle.seek(0, os.SEEK_END)
                write_fn(handle, handle.tell() == 0)
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    with contextlib_suppress_oserror():
        path.chmod(0o600)


def _migrate_panel_prompt_size_legacy_header(handle: Any, text: str) -> bool:
    if not text:
        return False
    lines = text.splitlines()
    if not lines:
        return False
    if tuple(lines[0].split("\t")) != _PANEL_PROMPT_SIZE_LEGACY_FIELDS:
        return False
    migrated_lines = ["\t".join(_PANEL_PROMPT_SIZE_FIELDS)]
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) < len(_PANEL_PROMPT_SIZE_LEGACY_FIELDS):
            cells.extend([""] * (len(_PANEL_PROMPT_SIZE_LEGACY_FIELDS) - len(cells)))
        migrated_lines.append(
            "\t".join(
                [
                    cells[0],
                    cells[1],
                    cells[2],
                    cells[3],
                    cells[4],
                    cells[5],
                    cells[6],
                    cells[7],
                    cells[8],
                    cells[7],
                    cells[8],
                    "0",
                    "0",
                    cells[9],
                    cells[10],
                    cells[11],
                ]
            )
        )
    handle.seek(0)
    handle.truncate()
    handle.write("\n".join(migrated_lines) + "\n")
    handle.flush()
    return True


def _parse_panel_payload_bytes(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    text = str(value).strip()
    if not text or not _UINT_RE.fullmatch(text):
        return None
    return int(text)


def _panel_payload_bytes(explicit: object = None) -> int:
    if explicit is not None:
        parsed = _parse_panel_payload_bytes(explicit)
        return parsed if parsed is not None else 0
    parsed = _parse_panel_payload_bytes(os.environ.get("LARCH_PANEL_PAYLOAD_BYTES"))
    return parsed if parsed is not None else 0


def read_panel_payload_bytes(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return 0
    parsed = _parse_panel_payload_bytes(text)
    return parsed if parsed is not None else 0


def _write_panel_prompt_row(path: Path, row: PanelPromptSizeRow) -> None:
    def _write(handle: Any, needs_header: object) -> None:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        if needs_header:
            writer.writerow(_PANEL_PROMPT_SIZE_FIELDS)
        writer.writerow(row.as_tsv_row())

    _locked_tsv_append(path, _write)


def append_panel_prompt_size(
    *,
    artifact_path: Path,
    output: Path | str = "",
    tool: str = "",
    prompt: str | None = None,
    prompt_file: Path | str | None = None,
    agent_file: Path | str | None = None,
    slot_kind: str = "",
    site: str = "",
    round_num: int | str | None = None,
    slot: str = "",
    phase: str = "",
    payload_bytes: int | str | None = None,
) -> None:
    try:
        inferred_kind = _panel_slot_kind_from_env(slot_kind=slot_kind)
        if inferred_kind not in _PANEL_SLOT_KINDS:
            return
        prompt_text = prompt
        if prompt_text is None:
            if prompt_file is None or str(prompt_file) == "":
                return
            prompt_text = Path(prompt_file).read_text(encoding="utf-8", errors="replace")
        prompt_bytes = len(prompt_text.encode("utf-8"))
        effective_payload_bytes = _panel_payload_bytes(payload_bytes)
        scaffold_bytes = max(0, prompt_bytes - effective_payload_bytes)
        env_agent = os.environ.get("LARCH_PANEL_SOURCE_AGENT_FILE", "")
        source_agent = str(agent_file or env_agent or "")
        agent_rel, agent_bytes, agent_tokens = _repo_relative_agent_path(source_agent)
        env_round = os.environ.get("LARCH_PANEL_ROUND_NUM", "")
        effective_round = str(round_num if round_num is not None else env_round)
        if effective_round and not _UINT_RE.fullmatch(effective_round):
            effective_round = ""
        output_name = Path(str(output)).name if output else ""
        row = PanelPromptSizeRow(
            site=site or os.environ.get("LARCH_PANEL_SITE", ""),
            phase=phase or os.environ.get("LARCH_PANEL_PHASE", ""),
            round_num=effective_round,
            slot=slot or os.environ.get("LARCH_PANEL_SLOT", ""),
            slot_kind=inferred_kind,
            tool=tool or os.environ.get("LARCH_PANEL_PRIMARY_TOOL", ""),
            output=output_name,
            prompt_bytes=prompt_bytes,
            prompt_tokens=_estimate_tokens_for_bytes(prompt_bytes),
            scaffold_bytes=scaffold_bytes,
            scaffold_tokens=_estimate_tokens_for_bytes(scaffold_bytes),
            payload_bytes=effective_payload_bytes,
            payload_tokens=_estimate_tokens_for_bytes(effective_payload_bytes),
            agent_file=agent_rel,
            agent_bytes=agent_bytes,
            agent_tokens=agent_tokens,
        )
        _write_panel_prompt_row(artifact_path, row)
    except Exception as exc:  # best-effort telemetry must not interrupt dispatch
        print(f"panel prompt size: write skipped: {exc}", file=sys.stderr)


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


def _claude_sub_model(row: Mapping[str, Any]) -> str:
    model = str(row.get("model") or "")
    if model:
        return model
    return config.claude_sub_default_model(str(row.get("raw") or ""))


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
            # Per-model split so pricing keys on (vendor, model). Group strictly by
            # the per-row `model` value, independent of step/round/raw label; the
            # review lane can mix gpt-5.5 and gpt-5.4-mini in one round (issue #5321).
            # Model-less legacy rows default to gpt-5.5. BUCKETS_codex stays the sum.
            by_model: dict[str, dict[str, int]] = {}
            for row in rows:
                model = str(row.get("model") or "") or config.CODEX_DEFAULT_MODEL
                mt = by_model.setdefault(model, {"input": 0, "cached_input": 0, "output": 0, "total": 0})
                mt["input"] += _int_field(data=row, key="input")
                mt["cached_input"] += _int_field(data=row, key="cache_read")
                mt["output"] += _int_field(data=row, key="output")
                mt["total"] += _int_field(data=row, key="total")
            data["BUCKETS_codex_by_model"] = by_model
        elif name == "cursor":
            data["BUCKETS_cursor"] = {"input": totals["input"], "cache_read": totals["cache_read"], "output": totals["output"], "total": totals["total"]}
            # Per-model split so pricing keys on (vendor, model). Rows without a model
            # field default to composer-2.5 (non-auto), matching pre-recording behavior.
            # BUCKETS_cursor_by_model is parallel to BUCKETS_codex_by_model.
            by_model_cursor: dict[str, dict[str, int]] = {}
            for row in rows:
                model = str(row.get("model") or "") or config.CURSOR_DEFAULT_MODEL
                mt = by_model_cursor.setdefault(model, {"input": 0, "cache_read": 0, "output": 0, "total": 0})
                mt["input"] += _int_field(data=row, key="input")
                mt["cache_read"] += _int_field(data=row, key="cache_read")
                mt["output"] += _int_field(data=row, key="output")
                mt["total"] += _int_field(data=row, key="total")
            data["BUCKETS_cursor_by_model"] = by_model_cursor
        else:
            data["BUCKETS_claude_sub"] = {"input": totals["input"], "cache_read": totals["cache_read"], "cache_create_5m": totals["cache_create"], "cache_create_1h": 0, "output": totals["output"], "total": totals["total"]}
            by_model: dict[str, dict[str, int]] = {}
            for row in rows:
                model = _claude_sub_model(row)
                mt = by_model.setdefault(model, {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0, "total": 0})
                mt["input"] += _int_field(data=row, key="input")
                mt["cache_read"] += _int_field(data=row, key="cache_read")
                mt["cache_create_5m"] += _int_field(data=row, key="cache_create")
                mt["output"] += _int_field(data=row, key="output")
                mt["total"] += _int_field(data=row, key="total")
            data["BUCKETS_claude_sub_by_model"] = by_model
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


def run_log_ledger_path(run_dir: Path) -> Path | None:
    """Resolve the committed token ledger for a run-log directory."""
    session_id_path = run_dir / "session-id"
    if session_id_path.is_file() and not session_id_path.is_symlink():
        try:
            session_id = session_id_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            session_id = ""
        if session_id:
            slug = hashlib.sha256(session_id.encode("utf-8", errors="replace")).hexdigest()
            ledger = run_dir / f"larch-tokens-{slug}.jsonl"
            if ledger.is_file() and not ledger.is_symlink():
                return ledger
    ledgers = sorted(
        path
        for path in run_dir.glob("larch-tokens-*.jsonl")
        if path.is_file() and not path.is_symlink()
    )
    return ledgers[0] if len(ledgers) == 1 else None


def enrich_codex_by_model(report: dict[str, Any], *, run_dir: Path) -> dict[str, Any]:
    """Merge ``BUCKETS_codex_by_model`` from the run ledger when the report lacks it."""
    if _as_map(report.get("BUCKETS_codex_by_model")):
        return report
    ledger = run_log_ledger_path(run_dir)
    if ledger is None:
        return report
    try:
        ledger_report = build_report_from_ledgers([ledger])
    except (ValueError, OSError):
        return report
    by_model = ledger_report.get("BUCKETS_codex_by_model")
    if not isinstance(by_model, dict) or not by_model:
        return report
    enriched = dict(report)
    enriched["BUCKETS_codex_by_model"] = by_model
    return enriched


def enrich_claude_sub_by_model(report: dict[str, Any], *, run_dir: Path) -> dict[str, Any]:
    """Merge ``BUCKETS_claude_sub_by_model`` from the run ledger when absent."""
    if _as_map(report.get("BUCKETS_claude_sub_by_model")):
        return report
    ledger = run_log_ledger_path(run_dir)
    if ledger is None:
        return report
    try:
        ledger_report = build_report_from_ledgers([ledger])
    except (ValueError, OSError):
        return report
    by_model = ledger_report.get("BUCKETS_claude_sub_by_model")
    if not isinstance(by_model, dict) or not by_model:
        return report
    enriched = dict(report)
    enriched["BUCKETS_claude_sub_by_model"] = by_model
    return enriched


def _as_map(value: object) -> dict[str, Any]:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


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
        return f"Tokens: {_tok_k(data['token_total'])}k, Claude: {_tok_k(c_raw)}k | Codex: {_tok_k(d_raw)}k | Cursor: {_tok_k(u_raw)}k | Claude (subprocess): {_tok_k(cs_raw)}k"
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


def _cached_claude_source_replay(
    *,
    claude_source_file: Path | None,
    env_map: Mapping[str, str],
) -> dict[str, str] | None:
    snap = claude_source_file or (Path(env_map["LARCH_CLAUDE_SOURCE_FILE"]) if env_map.get("LARCH_CLAUDE_SOURCE_FILE") else None)
    if snap is None or not snap.is_file():
        return None
    data = larch_io.parse_kv(
        larch_io.read_text(snap, errors="replace"),
        allowed_keys={"TRANSCRIPT_PATH", "SESSION_DIR", "SESSION_UUID"},
    )
    if data.get("TRANSCRIPT_PATH") and data.get("SESSION_DIR") and data.get("SESSION_UUID"):
        return _validate_snapshot_replay(data, env=env_map)
    return None


def _requested_claude_session_id(env_map: Mapping[str, str]) -> str:
    for key in ("LARCH_CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        sid = env_map.get(key, "")
        if sid and _SAFE_SESSION_RE.fullmatch(sid):
            return sid
    return ""


def _find_latest_claude_transcript(*, project_dir: Path, env_map: Mapping[str, str]) -> tuple[Path | None, str]:
    latest: Path | None = None
    requested_sid = _requested_claude_session_id(env_map)
    if requested_sid:
        candidate = project_dir / f"{requested_sid}.jsonl"
        if candidate.is_file():
            latest = candidate
    if latest is None and not requested_sid:
        files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        latest = files[0] if files else None
    return latest, requested_sid


def _resolve_claude_source_from_project(env_map: Mapping[str, str]) -> dict[str, str]:
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
    latest, requested_sid = _find_latest_claude_transcript(project_dir=project_dir, env_map=env_map)
    if requested_sid and latest is None:
        return {"STATUS": "unavailable", "REASON": f"Claude transcript for session {requested_sid} not found"}
    if latest is None:
        return {"STATUS": "unavailable", "REASON": "no Claude transcript jsonl files found"}
    uuid = latest.stem
    return {"TRANSCRIPT_PATH": str(latest), "SESSION_DIR": str(project_dir / uuid), "SESSION_UUID": uuid}


def token_claude_source(
    *,
    claude_source_file: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env_map = os.environ if env is None else env
    replay = _cached_claude_source_replay(claude_source_file=claude_source_file, env_map=env_map)
    if replay is not None:
        return replay
    return _resolve_claude_source_from_project(env_map)


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
    return larch_io.kv_value(text=larch_io.read_text(input_path, errors="replace"), key="TOOL", default="")


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
            return "\n".join([*lines, "_(no measurements available: Claude inline only, no measurable subagent invocations)_"])
        rate_raw = os.environ.get("LARCH_TOKEN_RATE_PER_M", "")
        try:
            rate = float(rate_raw)
        except ValueError:
            rate = 0.0
        def row(*, label: str, phase: str) -> str:
            if not lanes[phase]:
                suffix = "(4 lanes, Codex-first with per-lane Claude fallback): not measured" if phase == "research" else "(3 reviewers, Code|Cursor|Codex): not measured"
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
    return Path(__file__).resolve().parents[3]


_REPORT_FORMATS = frozenset({"json", "markdown"})


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
    redacted_prefix = f"{config.REDACTED_OPERATOR_REPO}/"
    if path.startswith(redacted_prefix):
        path = path[len(redacted_prefix) :]
    elif path == config.REDACTED_OPERATOR_REPO:
        return None
    if path.startswith("<"):
        return None
    repo_prefix = f"{repo}/"
    if path.startswith(repo_prefix):
        path = path[len(repo_prefix) :]
    else:
        stripped = strip_plugin_cache_read_suffix(path)
        if stripped is not None:
            path = stripped
        elif path.startswith("/"):
            return None
    if path.startswith(("/", "../")) or "/../" in path or path == "..":
        return None
    return path


def is_in_scope_reference_path(rel: str) -> bool:
    path = Path(rel)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    if path.suffix != ".md":
        return False
    if len(parts) == 3 and parts[0] == "skills" and parts[1] == "shared":
        return True
    return len(parts) == 4 and parts[0] == "skills" and parts[2] == "references"


def _normalize_reference_read_path(*, raw: object, repo: Path) -> str | None:
    rel = _normalize_read_path(raw=raw, repo=repo)
    if rel is None or not is_in_scope_reference_path(rel):
        return None
    return rel


@dataclass(frozen=True)
class ObservedReferenceRead:
    skill: str
    run_id: str
    run_dir: Path
    reference_path: str


def _read_tool_paths_from_obj(obj: object) -> list[object]:
    if not isinstance(obj, dict):
        return []
    record = cast("dict[str, Any]", obj)
    paths: list[object] = []
    paths.extend(_read_tool_paths_from_blocks(record.get("blocks"), allowed_types={"tool_call", "tool_use"}))
    message_raw = record.get("message")
    message = cast("dict[str, Any]", message_raw) if isinstance(message_raw, dict) else None
    content = message.get("content") if message is not None else None
    paths.extend(_read_tool_paths_from_blocks(content, allowed_types={"tool_use"}))
    return paths


def _read_tool_paths_from_blocks(blocks_raw: object, *, allowed_types: set[str]) -> list[object]:
    if not isinstance(blocks_raw, list):
        return []
    paths: list[object] = []
    for item in cast("list[Any]", blocks_raw):
        if not isinstance(item, dict):
            continue
        block = cast("dict[str, Any]", item)
        if block.get("type") not in allowed_types or block.get("name") != "Read":
            continue
        tool_input = block.get("input")
        if isinstance(tool_input, dict):
            paths.append(cast("dict[str, Any]", tool_input).get("file_path"))
    return paths


def _reference_reads_for_run(*, repo: Path, skill: str, run_dir: Path) -> list[ObservedReferenceRead]:
    transcript = run_log_corpus.safe_transcript_path(run_dir)
    if transcript is None:
        return []
    reads: list[ObservedReferenceRead] = []
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        for raw_path in _read_tool_paths_from_obj(obj):
            rel = _normalize_reference_read_path(raw=raw_path, repo=repo)
            if rel is not None:
                reads.append(ObservedReferenceRead(skill=skill, run_id=run_dir.name, run_dir=run_dir, reference_path=rel))
    return reads


def _skill_run_dirs(repo: Path) -> dict[str, list[Path]]:
    root = repo / "larch-logs"
    by_skill: dict[str, list[Path]] = {}
    if not root.is_dir():
        return by_skill
    for skill_dir in sorted(root.iterdir()):
        if skill_dir.is_symlink() or not skill_dir.is_dir():
            continue
        runs = list(run_log_corpus.run_dirs(skill_dir))
        if skill_dir.name == "review":
            seen = {path.resolve() for path in runs}
            for path in run_log_corpus.review_transcript_dirs(skill_dir):
                resolved = path.resolve()
                if resolved not in seen:
                    runs.append(path)
                    seen.add(resolved)
            runs.sort(key=lambda path: path.name)
        if runs:
            by_skill[skill_dir.name] = runs
    return by_skill


def _token_counts_for_repo_paths(*, repo: Path, rels: list[str]) -> dict[str, tuple[int, int]]:
    unique = sorted(set(rels))
    texts: list[str] = []
    present: list[str] = []
    sizes: dict[str, int] = {}
    for rel in unique:
        path = repo / rel
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            sizes[rel] = len(data)
            texts.append(data.decode("utf-8", errors="replace"))
            present.append(rel)
        else:
            sizes[rel] = 0
    token_values = _tiktoken_count_texts(texts) if texts else []
    tokens_by_rel = dict(zip(present, token_values, strict=False))
    return {rel: (sizes[rel], tokens_by_rel.get(rel, 0)) for rel in unique}


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
    run_dirs_by_skill = _skill_run_dirs(repo)
    reads: list[ObservedReferenceRead] = []
    coverage_rows: list[tuple[str, int, int, int, float, str]] = []
    for skill, dirs in run_dirs_by_skill.items():
        transcript_runs = sum(1 for run_dir in dirs if run_log_corpus.safe_transcript_path(run_dir) is not None)
        runs_observed = len(dirs)
        missing_transcripts = runs_observed - transcript_runs
        ratio = transcript_runs / runs_observed if runs_observed else 0.0
        capture_status = "measured" if transcript_runs else "not-yet-measured"
        coverage_rows.append((skill, runs_observed, transcript_runs, missing_transcripts, ratio, capture_status))
        for run_dir in dirs:
            reads.extend(_reference_reads_for_run(repo=repo, skill=skill, run_dir=run_dir))
    counts: collections.Counter[tuple[str, str]] = collections.Counter((read.skill, read.reference_path) for read in reads)
    token_info = _token_counts_for_repo_paths(repo=repo, rels=[ref for _, ref in counts])
    rows: list[tuple[str, str, int, int, float, int, int]] = []
    for (skill, rel), read_count in counts.items():
        runs_observed = len(run_dirs_by_skill.get(skill, []))
        loads_per_run = read_count / runs_observed if runs_observed else 0.0
        byte_count, token_count = token_info.get(rel, (0, 0))
        rows.append((skill, rel, read_count, runs_observed, loads_per_run, byte_count, token_count))
    coverage_rows.sort(key=lambda row: row[0])
    rows.sort(key=lambda row: (row[0], -row[2], row[1]))
    _atomic_text(
        path=out_path,
        text=(
            "# transcript_coverage\n"
            "skill\truns_observed\ttranscript_runs_observed\tmissing_transcript_runs\ttranscript_coverage_ratio\treference_capture_status\n"
            + "".join(
                f"{skill}\t{runs_count}\t{transcript_count}\t{missing_count}\t{ratio:.6f}\t{capture_status}\n"
                for skill, runs_count, transcript_count, missing_count, ratio, capture_status in coverage_rows
            )
            + "# reference_heatmap\n"
            "skill\treference_path\treads_observed\truns_observed\tloads_per_run\tbytes\ttokens\n"
            + "".join(
                f"{skill}\t{rel}\t{reads_count}\t{runs_count}\t{loads:.6f}\t{byte_count}\t{token_count}\n"
                for skill, rel, reads_count, runs_count, loads, byte_count, token_count in rows
            )
        ),
    )
    return out_path


def measure_realized_cost() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-realized-cost" / f"{_measure_stamp()}.tsv"
    run_dirs_by_skill = _skill_run_dirs(repo)
    skill_paths: dict[str, str] = {}
    skill_texts: list[str] = []
    for skill in sorted(run_dirs_by_skill):
        path = _skill_md_path(repo=repo, skill=skill)
        if path is None:
            continue
        rel = path.relative_to(repo).as_posix()
        skill_paths[skill] = rel
        skill_texts.append(path.read_text(encoding="utf-8", errors="replace"))
    skill_token_values = _tiktoken_count_texts(skill_texts) if skill_texts else []
    skill_tokens = dict(zip(sorted(skill_paths), skill_token_values, strict=False))
    reads_by_skill: dict[str, list[ObservedReferenceRead]] = {}
    all_refs: list[str] = []
    for skill, dirs in run_dirs_by_skill.items():
        skill_reads: list[ObservedReferenceRead] = []
        for run_dir in dirs:
            run_reads = _reference_reads_for_run(repo=repo, skill=skill, run_dir=run_dir)
            skill_reads.extend(run_reads)
            all_refs.extend(read.reference_path for read in run_reads)
        reads_by_skill[skill] = skill_reads
    ref_info = _token_counts_for_repo_paths(repo=repo, rels=all_refs)
    rows: list[tuple[str, int, int, str, int, str, int, int, str]] = []
    for skill, dirs in run_dirs_by_skill.items():
        if skill not in skill_tokens:
            continue
        invocations = len(dirs)
        issues = {str(manifest.get("issue_number")) for run_dir in dirs if (manifest := run_log_corpus.load_run_manifest(run_dir))}
        skill_md_tokens = skill_tokens[skill]
        reference_tokens_total = sum(ref_info.get(read.reference_path, (0, 0))[1] for read in reads_by_skill.get(skill, []))
        reference_reads = len(reads_by_skill.get(skill, []))
        realized_tokens = invocations * skill_md_tokens + reference_tokens_total
        tokens_per_invocation = realized_tokens / invocations if invocations else 0.0
        reference_tokens_per_invocation = reference_tokens_total / invocations if invocations else 0.0
        # A skill with zero observed reference reads is indistinguishable from a
        # skill with no transcript capture at all unless we report which case it
        # is: distinguish a real, measured zero from "no data yet".
        has_capture = any(run_log_corpus.safe_transcript_path(run_dir) is not None for run_dir in dirs)
        capture_status = "measured" if has_capture else "not-yet-measured"
        rows.append((
            skill,
            invocations,
            len(issues),
            f"{tokens_per_invocation:.2f}",
            realized_tokens,
            f"{reference_tokens_per_invocation:.2f}",
            skill_md_tokens,
            reference_reads,
            capture_status,
        ))
    rows.sort(key=lambda row: (-row[4], row[0]))
    _atomic_text(
        path=out_path,
        text=(
            "skill\tinvocations\tissues_observed\ttokens_per_invocation\trealized_tokens\t"
            "skill_md_tokens\treference_tokens_per_invocation\treference_reads_observed\t"
            "reference_capture_status\n"
            + "".join(
                f"{skill}\t{count}\t{issue_count}\t{tokens_per_invocation}\t{realized}\t{skill_md_tokens}\t{ref_tokens_per_invocation}\t{ref_reads}\t{capture_status}\n"
                for skill, count, issue_count, tokens_per_invocation, realized, ref_tokens_per_invocation, skill_md_tokens, ref_reads, capture_status in rows
            )
        ),
    )
    return out_path


CacheEfficiencyLane = Literal["claude", "claude_sub"]


@dataclass(frozen=True)
class CacheEfficiencyTotals:
    cache_create: int
    cache_create_5m: int
    cache_create_1h: int
    cache_read: int
    effective_cache_create: int


@dataclass(frozen=True)
class CacheEfficiencyRunRow:
    skill: Skill
    issue: int
    started_at: str
    lane: CacheEfficiencyLane
    title: str
    totals: CacheEfficiencyTotals


@dataclass(frozen=True)
class CacheEfficiencyStepRow:
    skill: Skill
    step: str
    lane: CacheEfficiencyLane
    runs: int
    totals: CacheEfficiencyTotals


def _cache_create_effective(*, cache_create: int, cache_create_5m: int, cache_create_1h: int) -> int:
    split_sum = cache_create_5m + cache_create_1h
    return split_sum if split_sum > 0 else cache_create


def _cache_totals_from_vendor(totals: VendorTotals) -> CacheEfficiencyTotals:
    effective = _cache_create_effective(
        cache_create=totals.cache_create,
        cache_create_5m=totals.cache_create_5m,
        cache_create_1h=totals.cache_create_1h,
    )
    return CacheEfficiencyTotals(
        cache_create=totals.cache_create,
        cache_create_5m=totals.cache_create_5m,
        cache_create_1h=totals.cache_create_1h,
        cache_read=totals.cache_read,
        effective_cache_create=effective,
    )


def _cache_lane_totals_from_mapping(totals: Mapping[str, object]) -> CacheEfficiencyTotals:
    cache_create = safe_int(value=totals.get("cache_create"))
    cache_create_5m = safe_int(value=totals.get("cache_create_5m"))
    cache_create_1h = safe_int(value=totals.get("cache_create_1h"))
    effective = _cache_create_effective(
        cache_create=cache_create,
        cache_create_5m=cache_create_5m,
        cache_create_1h=cache_create_1h,
    )
    return CacheEfficiencyTotals(
        cache_create=cache_create,
        cache_create_5m=cache_create_5m,
        cache_create_1h=cache_create_1h,
        cache_read=safe_int(value=totals.get("cache_read")),
        effective_cache_create=effective,
    )


def _cache_ratio_value(*, effective_cache_create: int, cache_read: int) -> float:
    if effective_cache_create > 0 and cache_read == 0:
        return float("inf")
    if cache_read > 0:
        return effective_cache_create / cache_read
    return 0.0


def _cache_ratio_sort_key(
    *,
    effective_cache_create: int,
    cache_read: int,
    labels: tuple[str, ...],
) -> tuple[int, float, int, int, tuple[str, ...]]:
    zero_read_outlier = effective_cache_create > 0 and cache_read == 0
    ratio = _cache_ratio_value(effective_cache_create=effective_cache_create, cache_read=cache_read)
    return (
        0 if zero_read_outlier else 1,
        -ratio,
        -effective_cache_create,
        -cache_read,
        labels,
    )


def _cache_ratio_text(*, effective_cache_create: int, cache_read: int) -> str:
    ratio = _cache_ratio_value(effective_cache_create=effective_cache_create, cache_read=cache_read)
    if ratio == float("inf"):
        return "inf"
    return f"{ratio:.6f}"


def _cache_efficiency_step_rows_for_record(
    *,
    skill: Skill,
    record: RunRecord,
    lane: CacheEfficiencyLane,
) -> tuple[CacheEfficiencyStepRow, ...]:
    lane_obj = _as_map(record.raw_report.get(lane))
    per_step = lane_obj.get("per_step")
    if not isinstance(per_step, list):
        return ()
    rows: list[CacheEfficiencyStepRow] = []
    for item in cast("list[object]", per_step):
        item_map = _as_map(item)
        totals_obj = item_map.get("totals")
        if not isinstance(totals_obj, dict):
            continue
        totals = _cache_lane_totals_from_mapping(cast("Mapping[str, object]", totals_obj))
        rows.append(
            CacheEfficiencyStepRow(
                skill=skill,
                step=str(item_map.get("step") or "unknown"),
                lane=lane,
                runs=1,
                totals=totals,
            )
        )
    return tuple(rows)


def _measure_cache_efficiency_records(
    *,
    tagged_records: Sequence[tuple[Skill, RunRecord]],
) -> tuple[tuple[CacheEfficiencyRunRow, ...], tuple[CacheEfficiencyStepRow, ...]]:
    per_run: list[CacheEfficiencyRunRow] = []
    step_groups: dict[tuple[Skill, str, CacheEfficiencyLane], dict[str, int]] = {}
    for skill, record in tagged_records:
        for lane in ("claude", "claude_sub"):
            lane_totals = _cache_totals_from_vendor(getattr(record, lane))
            per_run.append(
                CacheEfficiencyRunRow(
                    skill=skill,
                    issue=record.number,
                    started_at=record.started_at,
                    lane=lane,
                    title=record.title,
                    totals=lane_totals,
                )
            )
            for step_row in _cache_efficiency_step_rows_for_record(skill=skill, record=record, lane=lane):
                key = (step_row.skill, step_row.step, step_row.lane)
                group = step_groups.setdefault(
                    key,
                    {
                        "runs": 0,
                        "cache_create": 0,
                        "cache_create_5m": 0,
                        "cache_create_1h": 0,
                        "cache_read": 0,
                        "effective_cache_create": 0,
                    },
                )
                group["runs"] += 1
                group["cache_create"] += step_row.totals.cache_create
                group["cache_create_5m"] += step_row.totals.cache_create_5m
                group["cache_create_1h"] += step_row.totals.cache_create_1h
                group["cache_read"] += step_row.totals.cache_read
                group["effective_cache_create"] += step_row.totals.effective_cache_create
    per_step: list[CacheEfficiencyStepRow] = []
    for (skill, step, lane), group in step_groups.items():
        per_step.append(
            CacheEfficiencyStepRow(
                skill=skill,
                step=step,
                lane=lane,
                runs=group["runs"],
                totals=CacheEfficiencyTotals(
                    cache_create=group["cache_create"],
                    cache_create_5m=group["cache_create_5m"],
                    cache_create_1h=group["cache_create_1h"],
                    cache_read=group["cache_read"],
                    effective_cache_create=group["effective_cache_create"],
                ),
            )
        )
    return tuple(per_run), tuple(per_step)


def _cache_tsv_cell(value: object) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _ranked_cache_run_rows(rows: Sequence[CacheEfficiencyRunRow]) -> list[CacheEfficiencyRunRow]:
    included = [row for row in rows if not (row.totals.effective_cache_create == 0 and row.totals.cache_read == 0)]
    return sorted(
        included,
        key=lambda row: _cache_ratio_sort_key(
            effective_cache_create=row.totals.effective_cache_create,
            cache_read=row.totals.cache_read,
            labels=(row.skill, str(row.issue), row.started_at, row.lane, row.title),
        ),
    )


def _ranked_cache_step_rows(rows: Sequence[CacheEfficiencyStepRow]) -> list[CacheEfficiencyStepRow]:
    included = [row for row in rows if not (row.totals.effective_cache_create == 0 and row.totals.cache_read == 0)]
    return sorted(
        included,
        key=lambda row: _cache_ratio_sort_key(
            effective_cache_create=row.totals.effective_cache_create,
            cache_read=row.totals.cache_read,
            labels=(row.skill, row.step, row.lane),
        ),
    )


def _render_cache_efficiency_tsv(
    *,
    per_run: Sequence[CacheEfficiencyRunRow],
    per_step: Sequence[CacheEfficiencyStepRow],
) -> str:
    lines = [
        "# per_run\n",
        "rank\tskill\tissue\tstarted_at\tlane\tcache_create\tcache_create_5m\tcache_create_1h\tcache_read\tratio\ttitle\n",
    ]
    for rank, row in enumerate(_ranked_cache_run_rows(per_run), start=1):
        totals = row.totals
        lines.append(
            "\t".join(
                (
                    str(rank),
                    row.skill,
                    str(row.issue),
                    _cache_tsv_cell(row.started_at),
                    row.lane,
                    str(totals.cache_create),
                    str(totals.cache_create_5m),
                    str(totals.cache_create_1h),
                    str(totals.cache_read),
                    _cache_ratio_text(effective_cache_create=totals.effective_cache_create, cache_read=totals.cache_read),
                    _cache_tsv_cell(row.title),
                )
            )
            + "\n"
        )
    lines.extend(
        [
            "\n",
            "# per_step\n",
            "rank\tskill\tstep\tlane\truns\tcache_create\tcache_create_5m\tcache_create_1h\tcache_read\tratio\n",
        ]
    )
    for rank, row in enumerate(_ranked_cache_step_rows(per_step), start=1):
        totals = row.totals
        lines.append(
            "\t".join(
                (
                    str(rank),
                    row.skill,
                    _cache_tsv_cell(row.step),
                    row.lane,
                    str(row.runs),
                    str(totals.cache_create),
                    str(totals.cache_create_5m),
                    str(totals.cache_create_1h),
                    str(totals.cache_read),
                    _cache_ratio_text(effective_cache_create=totals.effective_cache_create, cache_read=totals.cache_read),
                )
            )
            + "\n"
        )
    return "".join(lines)


def measure_cache_efficiency() -> Path:
    from larch.core.proc import ProcRunner
    from larch.report import report_tokens_scan

    runner = ProcRunner()
    tagged_records: list[tuple[Skill, RunRecord]] = []
    repo_root: Path | None = None
    for skill in ("design", "implement"):
        scan_result = report_tokens_scan.scan(runner, skill=skill, resolve_repo=False)
        if repo_root is None:
            repo_root = scan_result.repo_root
        tagged_records.extend((skill, record) for record in scan_result.records)
    out_path = repo_root / "larch-logs" / "measure-cache-efficiency" / f"{_measure_stamp()}.tsv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_run, per_step = _measure_cache_efficiency_records(tagged_records=tagged_records)
    _atomic_text(path=out_path, text=_render_cache_efficiency_tsv(per_run=per_run, per_step=per_step))
    return out_path


def _measure_repo_root_from_larch_logs_path(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == "larch-logs":
            return parent.parent
    return path.parent


@dataclass
class _PanelCostAggregate:
    dispatch_count: int = 0
    prompt_bytes: int = 0
    prompt_tokens: int = 0
    scaffold_bytes: int = 0
    scaffold_tokens: int = 0
    payload_bytes: int = 0
    payload_tokens: int = 0
    agent_bytes: int = 0
    agent_tokens: int = 0
    runs: set[tuple[str, str]] = dataclass_field(default_factory=set)


def _panel_context_from_tsv(path: Path, repo: Path) -> tuple[str, str] | None:
    try:
        rel = path.relative_to(repo / "larch-logs")
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 3:
        return None
    skill, run_id = parts[0], parts[1]
    if skill == "design":
        # Only plan-review/round-N panel logs are valid design panel telemetry.
        if len(parts) != 5 or parts[2] != "plan-review" or not _PANEL_ROUND_RE.fullmatch(parts[3]):
            return None
    elif skill == "implement":
        if len(parts) != 4 or not _PANEL_ROUND_RE.fullmatch(parts[2]):
            return None
    elif skill == "review":
        if not (len(parts) == 3 or (len(parts) == 4 and _PANEL_ROUND_RE.fullmatch(parts[2]))):
            return None
    else:
        return None
    return skill, run_id


def _iter_panel_prompt_size_files(repo: Path) -> list[Path]:
    root = repo / "larch-logs"
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.glob(f"**/{PANEL_PROMPT_SIZE_BASENAME}")
        if path.is_file() and not path.is_symlink() and _panel_context_from_tsv(path, repo) is not None
    )


def _uint_cell(row: Mapping[str, str], key: str) -> int:
    raw = row.get(key, "")
    return int(raw) if _UINT_RE.fullmatch(str(raw)) else 0


@dataclass
class ChecksDigestSavingsAggregate:
    valid_rows: int = 0
    files_observed: int = 0
    rows_seen: int = 0
    rows_skipped: int = 0
    redacted_bytes: int = 0
    digest_bytes: int = 0
    redacted_tokens: int = 0
    digest_tokens: int = 0
    saved_bytes: int = 0
    saved_tokens: int = 0

    def add_row(self, values: Mapping[str, int]) -> None:
        self.valid_rows += 1
        self.redacted_bytes += values["redacted_bytes"]
        self.digest_bytes += values["digest_bytes"]
        self.redacted_tokens += values["redacted_tokens"]
        self.digest_tokens += values["digest_tokens"]
        self.saved_bytes += values["saved_bytes"]
        self.saved_tokens += values["saved_tokens"]


def _signed_int_cell(row: Mapping[str, str], key: str) -> int | None:
    raw = (row.get(key) or "").strip()
    return int(raw) if _SIGNED_INT_RE.fullmatch(raw) else None


def _unsigned_int_cell(row: Mapping[str, str], key: str) -> int | None:
    raw = (row.get(key) or "").strip()
    return int(raw) if _UINT_RE.fullmatch(raw) else None


def _checks_digest_size_row_values(row: Mapping[str, str]) -> dict[str, int] | None:
    values: dict[str, int] = {}
    for field in _CHECKS_DIGEST_UNSIGNED_FIELDS:
        value = _unsigned_int_cell(row, field)
        if value is None:
            return None
        values[field] = value
    for field in _CHECKS_DIGEST_SIGNED_FIELDS:
        value = _signed_int_cell(row, field)
        if value is None:
            return None
        values[field] = value
    return values


def _iter_checks_digest_size_files(repo: Path) -> list[Path]:
    root = repo / "larch-logs"
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for skill in ("implement", "review"):
        paths.extend(root.glob(f"{skill}/*/{CHECKS_DIGEST_SIZE_BASENAME}"))
    return sorted(path for path in paths if path.is_file() and not path.is_symlink())


def _read_checks_digest_size_file(path: Path) -> tuple[bool, int, int, list[dict[str, int]]]:
    rows_seen = 0
    rows_skipped = 0
    parsed: list[dict[str, int]] = []
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = tuple(reader.fieldnames or ())
            if any(field not in fieldnames for field in _CHECKS_DIGEST_SIZE_FIELDS):
                return False, 0, 0, []
            for row in reader:
                rows_seen += 1
                values = _checks_digest_size_row_values(row)
                if values is None:
                    rows_skipped += 1
                    continue
                parsed.append(values)
    except OSError:
        return False, 0, 0, []
    return True, rows_seen, rows_skipped, parsed


def _render_checks_digest_savings_report(aggregate: ChecksDigestSavingsAggregate) -> str:
    if aggregate.valid_rows < _CHECKS_DIGEST_MIN_SAMPLES:
        status = "insufficient-data"
        recommendation = ""
    else:
        status = "sufficient-data"
        recommendation = (
            "go-design-validator-extension"
            if aggregate.saved_tokens > 0
            else "no-go-design-validator-extension"
        )
    row = {
        "status": status,
        "recommendation": recommendation,
        "valid_rows": str(aggregate.valid_rows),
        "files_observed": str(aggregate.files_observed),
        "rows_seen": str(aggregate.rows_seen),
        "rows_skipped": str(aggregate.rows_skipped),
        "redacted_bytes": str(aggregate.redacted_bytes),
        "digest_bytes": str(aggregate.digest_bytes),
        "redacted_tokens": str(aggregate.redacted_tokens),
        "digest_tokens": str(aggregate.digest_tokens),
        "saved_bytes": str(aggregate.saved_bytes),
        "saved_tokens": str(aggregate.saved_tokens),
    }
    return "\t".join(_CHECKS_DIGEST_SAVINGS_REPORT_FIELDS) + "\n" + "\t".join(
        row[field] for field in _CHECKS_DIGEST_SAVINGS_REPORT_FIELDS
    ) + "\n"


def measure_checks_digest_savings() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-checks-digest-savings" / f"{_measure_stamp()}.tsv"
    aggregate = ChecksDigestSavingsAggregate()
    for tsv in _iter_checks_digest_size_files(repo):
        has_header, rows_seen, rows_skipped, rows = _read_checks_digest_size_file(tsv)
        if not has_header:
            continue
        aggregate.files_observed += 1
        aggregate.rows_seen += rows_seen
        aggregate.rows_skipped += rows_skipped
        for row in rows:
            aggregate.add_row(row)
    _atomic_text(path=out_path, text=_render_checks_digest_savings_report(aggregate))
    return out_path


def measure_panel_cost() -> Path:
    repo = _repo_root()
    out_path = repo / "larch-logs" / "measure-panel-cost" / f"{_measure_stamp()}.tsv"
    aggregates: dict[tuple[str, str, str], _PanelCostAggregate] = {}
    for tsv in _iter_panel_prompt_size_files(repo):
        context = _panel_context_from_tsv(tsv, repo)
        if context is None:
            continue
        skill, run_id = context
        try:
            with tsv.open(encoding="utf-8", errors="replace", newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if not reader.fieldnames or "slot_kind" not in reader.fieldnames:
                    continue
                for row in reader:
                    slot_kind = (row.get("slot_kind") or "").strip()
                    if slot_kind not in _PANEL_SLOT_KINDS:
                        continue
                    agent_file = (row.get("agent_file") or "").strip() or f"generated/no-agent:{slot_kind}"
                    key = (skill, agent_file, slot_kind)
                    agg = aggregates.setdefault(key, _PanelCostAggregate())
                    agg.dispatch_count += 1
                    prompt_bytes = _uint_cell(row, "prompt_bytes")
                    prompt_tokens = _uint_cell(row, "prompt_tokens")
                    has_scaffold = "scaffold_bytes" in row and "payload_bytes" in row
                    scaffold_bytes = _uint_cell(row, "scaffold_bytes") if has_scaffold else prompt_bytes
                    scaffold_tokens = _uint_cell(row, "scaffold_tokens") if has_scaffold else prompt_tokens
                    payload_bytes = _uint_cell(row, "payload_bytes") if has_scaffold else 0
                    payload_tokens = _uint_cell(row, "payload_tokens") if has_scaffold else 0
                    agg.prompt_bytes += prompt_bytes
                    agg.prompt_tokens += prompt_tokens
                    agg.scaffold_bytes += scaffold_bytes
                    agg.scaffold_tokens += scaffold_tokens
                    agg.payload_bytes += payload_bytes
                    agg.payload_tokens += payload_tokens
                    agg.agent_bytes += _uint_cell(row, "agent_bytes")
                    agg.agent_tokens += _uint_cell(row, "agent_tokens")
                    agg.runs.add((skill, run_id))
        except OSError:
            continue
    rows: list[tuple[int, int, str, str, str, _PanelCostAggregate]] = []
    for (skill, agent_file, slot_kind), agg in aggregates.items():
        realized = agg.prompt_bytes + agg.agent_bytes
        rows.append((agg.scaffold_bytes, realized, skill, agent_file, slot_kind, agg))
    rows.sort(key=lambda item: (-item[0], -item[1], item[3], item[4], item[2]))
    lines = [
        "skill\tagent_file\tslot_kind\tdispatch_count\truns_observed\tloads_per_run\t"
        "prompt_bytes\tprompt_tokens\tscaffold_bytes\tscaffold_tokens\tpayload_bytes\tpayload_tokens\t"
        "agent_bytes\tagent_tokens\trealized_bytes\trealized_tokens\n"
    ]
    for _scaffold_sort, realized, skill, agent_file, slot_kind, agg in rows:
        runs_observed = len(agg.runs)
        loads_per_run = agg.dispatch_count / runs_observed if runs_observed else 0.0
        realized_tokens = agg.prompt_tokens + agg.agent_tokens
        lines.append(
            f"{skill}\t{agent_file}\t{slot_kind}\t{agg.dispatch_count}\t{runs_observed}\t{loads_per_run:.6f}\t"
            f"{agg.prompt_bytes}\t{agg.prompt_tokens}\t{agg.scaffold_bytes}\t{agg.scaffold_tokens}\t"
            f"{agg.payload_bytes}\t{agg.payload_tokens}\t{agg.agent_bytes}\t{agg.agent_tokens}\t{realized}\t{realized_tokens}\n"
        )
    _atomic_text(path=out_path, text="".join(lines))
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
    from larch.report.report_tokens_cost import token_cost_main as main
    return main(argv)


def token_cost_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    from larch.report.report_tokens_cost import token_cost_from_args as main
    return main(argv, env=env)


def token_render_cost_line_main(argv: list[str] | None = None) -> int:
    from larch.report.report_tokens_cost import render_cost_line_main as main
    return main(argv)


def render_cost_line_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    from larch.report.report_tokens_cost import render_cost_line_from_args as main
    return main(argv, env=env)


def _cost_breakdown_type() -> type[Any]:
    from larch.report.report_tokens_cost import CostBreakdown as CostBreakdownType
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



def measure_checks_digest_savings_main(argv: list[str] | None = None) -> int:
    _ = argv
    path = measure_checks_digest_savings()
    print(f"WROTE\t{path.relative_to(_repo_root())}")
    return 0


def measure_panel_cost_main(argv: list[str] | None = None) -> int:
    _ = argv
    path = measure_panel_cost()
    try:
        rel = path.relative_to(_repo_root()).as_posix()
    except ValueError:
        rel = str(path)
    print(f"WROTE\t{rel}")
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


def measure_cache_efficiency_main(argv: list[str] | None = None) -> int:
    _ = argv
    try:
        path = measure_cache_efficiency()
    except ShipError as exc:
        print(str(exc), file=sys.stderr)
        return config.EXIT_BAIL
    repo_root = _measure_repo_root_from_larch_logs_path(path)
    print(f"WROTE\t{path.relative_to(repo_root)}")
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
# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnknownVariableType=false
