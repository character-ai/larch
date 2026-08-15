# ruff: noqa: PLC0415, N801, S108, FURB162, PLR1714, PLR2004, E702
# pylint: disable=all
"""Token scraping, ledgers, reports, and cost helpers."""

from __future__ import annotations

import csv
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
from typing import Any, Literal, cast
from collections.abc import Mapping, Sequence

from larch import io as larch_io
from larch.core import config
from larch.core import proc
from larch.core.repo_roots import RepoRootProbeOptions, repo_root_probe
from larch.git import gh
from larch.report import markdown_block

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


@dataclass(frozen=True)
class TokenMarkResult:
    """Outcome of recording a token-ledger step mark."""

    ledger_path: Path | None
    marked: bool


@dataclass(frozen=True)
class BudgetCheckResult:
    """Current token usage since the last mark and its configured cap."""

    status: Literal["cap_hit", "under_cap"]
    total: int
    cap: int
    step: str


@dataclass(frozen=True)
class ClaudeSourceResult:
    """Validated Claude transcript source, or its unavailable reason."""

    transcript_path: Path | None
    session_dir: Path | None
    session_uuid: str
    reason: str = ""

    @property
    def available(self) -> bool:
        return self.transcript_path is not None


@dataclass(frozen=True)
class PrLineCountResult:
    """PR file-line totals, split between code and committed run logs."""

    status: Literal["ok", "skipped", "unavailable"]
    code_added: int | None = None
    code_deleted: int | None = None
    logs_added: int | None = None
    logs_deleted: int | None = None
    reason: str = ""

    def kv_items(self) -> tuple[tuple[str, str], ...]:
        items: list[tuple[str, str]] = [("LINES_STATUS", self.status)]
        if self.status == "ok":
            items.extend((
                ("CODE_ADDED", str(self.code_added)),
                ("CODE_DELETED", str(self.code_deleted)),
                ("LOGS_ADDED", str(self.logs_added)),
                ("LOGS_DELETED", str(self.logs_deleted)),
            ))
        else:
            items.append(("REASON", self.reason))
        return tuple(items)


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
_PANEL_SPECIALIST_SLOT_NAMES = frozenset(
    {"correctness", "edge-cases", "testing", "architectural-compliance", "generalist"}
)
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

    def mark(self, step: str) -> bool:
        try:
            self._append({"type": "mark", "step": step, "ts": _timestamp_utc()})
        except OSError as exc:
            print(f"token mark: write skipped: {exc}", file=sys.stderr)
            return False
        return True

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
            payload["model"] = config.normalize_claude_ledger_model(model) if vendor == "claude_sub" else model
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
    env_map: Mapping[str, str] = os.environ if env is None else env
    root = _tmp_root(env_map)
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
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"):
        workflow_root: Path | None = _canonical_dir(env_map.get(key, ""))
        if workflow_root is not None:
            allowed.append(workflow_root)
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
        return config.normalize_claude_ledger_model(model)
    return config.claude_sub_default_model(str(row.get("raw") or ""))


def _explicit_step_for_vendor_row(*, name: str, row: Mapping[str, Any]) -> str:
    raw = str(row.get("raw") or "")
    if name == "codex" and raw == config.CODEX_IMPLEMENT_RAW_LABEL:
        return config.IMPLEMENT_STEP2_LABEL
    if name == "cursor" and raw == config.CURSOR_IMPLEMENT_RAW_LABEL:
        return config.IMPLEMENT_STEP2_LABEL
    return ""


def _should_reroute_vendor_row(*, name: str, marks: list[dict[str, Any]], row: dict[str, Any], first: float) -> bool:
    explicit_step = _explicit_step_for_vendor_row(name=name, row=row)
    if explicit_step != config.IMPLEMENT_STEP2_LABEL:
        return False
    ts = _epoch(row.get("ts"))
    if ts is None or ts < first:
        return False
    enclosing = _enclosing_step(marks=marks, ts=ts) or ""
    return not enclosing.startswith(config.IMPLEMENT_STEP2_PREFIX)


def _add_totals(left: Mapping[str, int], right: Mapping[str, int]) -> dict[str, int]:
    keys = set(left) | set(right)
    return {key: int(left.get(key, 0)) + int(right.get(key, 0)) for key in keys}


def _per_step_json(*, name: str, marks: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = cast("float", marks[0]["ts"])
    filtered = [row for row in rows if name == "claude" or row.get("vendor") == name]
    total_rows = filtered
    rerouted = [
        row
        for row in filtered
        if name != "claude" and _should_reroute_vendor_row(name=name, marks=marks, row=row, first=first)
    ]
    if rerouted:
        rerouted_ids = {id(row) for row in rerouted}
        filtered = [row for row in filtered if id(row) not in rerouted_ids]
    per_step: list[dict[str, Any]] = []
    for idx, mark in enumerate(marks):
        start = cast("float", mark["ts"])
        end = cast("float | None", marks[idx + 1]["ts"] if idx + 1 < len(marks) else None)
        sl = _slice(rows=filtered, start=start, end=end)
        per_step.append({"step": mark["step"], "totals": _totals(sl)})
    if rerouted:
        synthetic_totals = _totals(rerouted)
        step2_idx = next(
            (idx for idx, item in enumerate(per_step) if str(item.get("step") or "").startswith(config.IMPLEMENT_STEP2_PREFIX)),
            None,
        )
        if step2_idx is None:
            per_step.append({"step": config.IMPLEMENT_STEP2_LABEL, "totals": synthetic_totals})
        else:
            existing_totals = cast("Mapping[str, int]", per_step[step2_idx]["totals"])
            per_step[step2_idx]["totals"] = _add_totals(existing_totals, synthetic_totals)
    return {"per_step": per_step, "totals": _totals(_slice(rows=total_rows, start=first, end=None))}


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
            # review lane can mix default and mini-class Codex models in one round (issue #5321).
            # Model-less legacy rows default to gpt-5.6-sol. BUCKETS_codex stays the sum.
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
            # field default to composer-2.5, matching pre-recording behavior.
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


def _replace_block(*, target: Path, block: str, begin: str, end: str) -> None:
    markdown_block.replace_markdown_block(
        target=target,
        block=block,
        markers=markdown_block.BlockMarkers(begin=begin, end=end),
        label="token report",
    )


def _transcript_sources(
    *, transcript_path: Path | None,
    session_dir: Path | None,
    env: Mapping[str, str] | None = None,
) -> list[Path]:
    if transcript_path is None:
        source = token_claude_source(env=env)
        if source.transcript_path is None:
            msg = source.reason or "Claude transcript source unavailable"
            raise ValueError(msg)
        transcript_path = source.transcript_path
        session_dir = source.session_dir
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


def check_step_token_budget(*, cap: int, step: str = "unknown", env: Mapping[str, str] | None = None) -> BudgetCheckResult:
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
    return BudgetCheckResult(status="cap_hit" if total >= cap else "under_cap", total=total, cap=cap, step=step)


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
        repo_root = repo_root_probe(options=RepoRootProbeOptions(check=True)).stdout.strip()
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
) -> ClaudeSourceResult:
    env_map = os.environ if env is None else env
    replay = _cached_claude_source_replay(claude_source_file=claude_source_file, env_map=env_map)
    data = replay if replay is not None else _resolve_claude_source_from_project(env_map)
    transcript = data.get("TRANSCRIPT_PATH", "")
    if transcript:
        return ClaudeSourceResult(
            transcript_path=Path(transcript),
            session_dir=Path(data["SESSION_DIR"]) if data.get("SESSION_DIR") else None,
            session_uuid=data.get("SESSION_UUID", ""),
        )
    return ClaudeSourceResult(transcript_path=None, session_dir=None, session_uuid="", reason=data.get("REASON", ""))


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
    if source.transcript_path is None:
        return ""
    path = source.transcript_path
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
        repo_root = repo_root_probe(options=RepoRootProbeOptions(check=True)).stdout.strip()
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
        payload["model"] = config.normalize_claude_ledger_model(model) if tool in {"claude", "claude_sub"} else model
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


def compute_pr_line_counts(*, pr_number: int, repo: str | None = None) -> PrLineCountResult:
    if pr_number < 1:
        return PrLineCountResult(status="skipped", reason="no-pr")
    if repo is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return PrLineCountResult(status="skipped", reason="invalid-repo")
    endpoint = f"repos/{repo}/pulls/{pr_number}/files" if repo else f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files"
    try:
        result = gh.command(
            proc, ["api", "--paginate", endpoint, "--jq", ".[] | [.filename, .additions, .deletions] | @tsv"]
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, result.argv, output=result.stdout, stderr=result.stderr
            )
        out = result.stdout
    except (OSError, subprocess.CalledProcessError):
        return PrLineCountResult(status="unavailable", reason="gh-failed")
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
    return PrLineCountResult(
        status="ok",
        code_added=code_added,
        code_deleted=code_deleted,
        logs_added=logs_added,
        logs_deleted=logs_deleted,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


_REPORT_FORMATS = frozenset({"json", "markdown"})


def _validate_report_format(fmt: str) -> None:
    if fmt not in _REPORT_FORMATS:
        msg = f"unknown format: {fmt}"
        raise ValueError(msg)



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


def token_mark(
    *,
    step: str,
    ledger: str | None = None,
    env: Mapping[str, str] | None = None,
) -> TokenMarkResult:
    """Record one token mark, returning a typed skipped or recorded outcome."""
    path = resolve_token_ledger_path(ledger=ledger, env=env)
    if path is None:
        return TokenMarkResult(ledger_path=None, marked=False)
    marked = TokenLedger(path).mark(step)
    return TokenMarkResult(ledger_path=path, marked=marked)


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
    print(f"STATUS={result.status} TOTAL={result.total} CAP={result.cap} STEP={result.step}")
    return 0


def token_cost_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    from larch.report.report_tokens_cost import token_cost_from_args as main
    return main(argv, env=env)


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
    for key, value in result.kv_items():
        print(f"{key}={value}")
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
