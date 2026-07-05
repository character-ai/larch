# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportArgumentType=false
# ruff: noqa: PLW2901
"""Shared utilities and data types for the review pipeline.

Imported by review_gather, review_prune, review_dispatch_panel, review_collect,
review_threshold, and review_core_body. Must not import from any of those modules.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.review.review_types import ReviewCoreStatus

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
CLI = _PLUGIN_ROOT / "python" / "cli.py"
STATIC_REVIEWERS = ("correctness", "edge-cases", "testing")
FOCUS_AREAS = {"code-quality", "risk-integration", "correctness", "architecture", "security"}
REVIEWER_PRUNE_ACCEPTANCE_FLOOR_NUMERATOR = 1
REVIEWER_PRUNE_ACCEPTANCE_FLOOR_DENOMINATOR = 2
PER_REVIEWER_OOS_PROPOSAL_CAP = 3


@dataclass(frozen=True)
class PruneRoundCounts:
    accepted: int = 0
    weighted_accepted: int = 0
    rejected: int = 0
    total: int = 0


@dataclass(frozen=True)
class PruneFilterResult:
    prune_active: str
    eligible_count: int
    pruned_count: int
    pruned_combos: str
    panel_pruned_empty: str
    prune_fail_open: str = "false"
    warn: str = ""


@dataclass(frozen=True)
class ReviewCoreResult:
    rc: int
    status: ReviewCoreStatus | str
    rows: tuple[tuple[str, object], ...]


@dataclass(frozen=True)
class ReviewCommands:
    gather: str
    dispatch: str
    collect: str
    threshold: str
    aggregate: str
    tally: str
    emit: str
    prune_nits: str
    dispatch_voters: str


@dataclass(frozen=True)
class ReviewCoreBranchContext:
    commands: ReviewCommands
    review_tmpdir: Path
    round_num: int
    mode: str
    cursor_available: str
    codex_available: str
    session_env_path: str
    panel_manifest: str
    collector_results: Path
    not_substantive: int
    panel_mode: str
    panel_shape: str
    scout_status: str
    dynamic_slots: str
    static_slot_count: str
    run_id: str
    prune_ledger: str
    site: str = ""
    diff_file: str = ""
    scope_files: str = ""
    plan_file: str = ""
    runner: proc.Runner | None = None
    rows: list[tuple[str, object]] | None = None


def _runner(runner: proc.Runner | None = None) -> proc.Runner:
    return runner or proc.ProcRunner()


def _env_with_plugin(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CLAUDE_PLUGIN_ROOT", str(_PLUGIN_ROOT))
    if extra:
        env.update(extra)
    return env


def _diag(message: str) -> None:
    logging_util.diagnostic(message)


def _usage(text: str) -> None:
    _diag(text)


def _emit_kv(*, key: str, value: object) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _emit_result(result: proc.CommandResult) -> None:
    for line in result.stdout.splitlines():
        logging_util.emit(line)
    for line in result.stderr.splitlines():
        logging_util.diagnostic(line)


def _kv_parse(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, skip_empty_key=True)


def _kv_get_file(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=True)


def _write_text(*, path: Path, text: str) -> None:
    larch_io.write_text(path=path, text=text)


def _append_text(*, path: Path, text: str) -> None:
    larch_io.append_text(path=path, text=text)


def _atomic_write(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, prefix=f"{path.name}.", suffix=".tmp")


def _run_capture(argv: Sequence[str], *, runner: proc.Runner | None = None, env: Mapping[str, str] | None = None) -> proc.CommandResult:
    return _runner(runner).run(argv, cwd=str(Path.cwd()), env=_env_with_plugin(env))


def _run_python_cli(args: Sequence[str], *, runner: proc.Runner | None = None, env: Mapping[str, str] | None = None) -> proc.CommandResult:
    return _run_capture([sys.executable, str(CLI), *args], runner=runner, env=env)


def _run_command_string(*, command: str, args: Sequence[str], runner: proc.Runner | None = None) -> proc.CommandResult:
    return _run_capture([command, *args], runner=runner)


def _call_review_command(*, name: str, args: Sequence[str], runner: proc.Runner | None = None) -> proc.CommandResult:
    return _run_python_cli(["review", name, *args], runner=runner)


def _call_maybe_override(*, command: str, review_name: str, args: Sequence[str], runner: proc.Runner | None = None) -> proc.CommandResult:
    if command:
        return _run_command_string(command=command, args=args, runner=runner)
    return _call_review_command(name=review_name, args=args, runner=runner)


def _bool_string(value: str) -> bool:
    return value == "true"


def _is_nonneg_int(value: str) -> bool:
    return value.isdigit()


def _parse_pos_int(*, value: str, label: str, usage: str) -> int | None:
    if not value.isdigit() or int(value) <= 0:
        _usage(f"{label}: {usage}")
        return None
    return int(value)


def _parse_args(*, argv: list[str], usage: str, options: set[str], list_options: set[str] | None = None) -> dict[str, str | list[str]] | None:
    if "--help" in argv:
        _usage(usage)
        return None
    list_options = list_options or set()
    parsed: dict[str, str | list[str]] = {}
    idx = 0
    while idx < len(argv):
        opt = argv[idx]
        if opt not in options and opt not in list_options:
            _usage(f"unknown option: {opt}\n{usage}")
            return {}
        if opt in list_options:
            idx += 1
            values: list[str] = []
            while idx < len(argv) and not argv[idx].startswith("--"):
                values.append(argv[idx])
                idx += 1
            parsed[opt] = values
            continue
        if idx + 1 >= len(argv):
            _usage(f"{opt} requires a value\n{usage}")
            return {}
        parsed[opt] = argv[idx + 1]
        idx += 2
    return parsed


def _get(*, parsed: Mapping[str, str | list[str]], key: str, default: str = "") -> str:
    value = parsed.get(key, default)
    return value if isinstance(value, str) else default


def _get_list(*, parsed: Mapping[str, str | list[str]], key: str) -> list[str]:
    value = parsed.get(key, [])
    return value if isinstance(value, list) else []


def _normalize_output_base(base: str) -> str:
    import re  # noqa: PLC0415
    base = Path(base).name
    stem, ext = (base[:-4], ".txt") if base.endswith(".txt") else (base, "")
    while True:
        new = re.sub(r"-(?:phase2|phase3|retry)$", "", stem)
        if new == stem:
            break
        stem = new
    return stem + ext


def _manifest_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
    return rows


def _collector_records(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    if not path.is_file():
        return records
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            current[key] = value
    if current:
        records.append(current)
    return records
