# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportArgumentType=false
"""Shared utilities and data types for the review pipeline."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
@dataclass(frozen=True)
class CodeReviewTallyRequest:
    """Stable Rust tally argv shared by review-core and targeted retries."""

    ballot_file: str
    review_tmpdir: str
    voter_files: tuple[str, ...]
    voter_tools: tuple[str, ...] = ()
    session_env_path: str = ""
    scope_files: str = ""
    plan_file: str = ""
    manifest_file: str = ""
    collector_results_file: str = ""
    not_substantive_count: str = "0"
    cursor_available: str = ""
    codex_available: str = ""
    round_num: str = "1"
    both_down: str = "false"
    proposer_map_file: str = ""

    def to_argv(self) -> list[str]:
        argv = [
            "--ballot-file", self.ballot_file,
            "--review-tmpdir", self.review_tmpdir,
            "--cursor-available", self.cursor_available,
            "--codex-available", self.codex_available,
            "--round-num", self.round_num,
        ]
        if self.proposer_map_file:
            argv.extend(["--proposer-map-file", self.proposer_map_file])
        for flag, value in (
            ("--session-env-path", self.session_env_path),
            ("--scope-files", self.scope_files),
            ("--plan-file", self.plan_file),
            ("--manifest-file", self.manifest_file),
            ("--collector-results-file", self.collector_results_file),
        ):
            if value:
                argv.extend([flag, value])
        if self.not_substantive_count != "0":
            argv.extend(["--not-substantive-count", self.not_substantive_count])
        if self.both_down != "false":
            argv.extend(["--both-down", self.both_down])
        argv.extend(["--voter-files", *self.voter_files])
        if self.voter_tools:
            argv.extend(["--voter-tools", *self.voter_tools])
        return argv

def _diag(message: str) -> None:
    logging_util.diagnostic(message)


def _usage(text: str) -> None:
    _diag(text)


def _emit_kv(*, key: str, value: object) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _append_text(*, path: Path, text: str) -> None:
    larch_io.append_text(path=path, text=text)


def run_larch(args: list[str], *, runner: proc.Runner | None = None, env: Mapping[str, str] | None = None) -> proc.CommandResult:
    """Run one Rust-owned command through the verified bootstrap script."""
    command = [str(larch_entrypoint(_PLUGIN_ROOT)), *args]
    return (runner or proc.ProcRunner()).run(
        command,
        cwd=str(Path.cwd()),
        env=larch_entrypoint_env(_PLUGIN_ROOT, base=env),
    )


def surface_warning(*, session_env_path: str, entry: str) -> None:
    """Best-effort operator-visible warning surface retained outside tally ownership."""
    log = ""
    if os.environ.get("LARCH_EXECUTION_ISSUES_LOG"):
        log = os.environ["LARCH_EXECUTION_ISSUES_LOG"]
    elif session_env_path:
        log = str(Path(session_env_path).parent / "execution-issues.md")
    elif os.environ.get("IMPLEMENT_TMPDIR"):
        log = str(Path(os.environ["IMPLEMENT_TMPDIR"]) / "execution-issues.md")
    if not log:
        return
    try:
        _ = run_larch([
            "run-log", "append-entry", "--log", log,
            "--category", "Warnings", "--entry", entry,
        ])
    except OSError:
        return


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


def parse_collector_records(text: str) -> list[dict[str, str]]:
    r"""Parse `agent collect-results` stdout / ``collector-results.env`` into per-reviewer dicts.

    The collector emits one ``KEY=VALUE`` per line, with records separated by a
    blank line. Records are anchored on ``REVIEWER_FILE``: diagnostic
    ``KEY=VALUE`` lines emitted before the first record are ignored, a new
    ``REVIEWER_FILE`` opens the next record, and a blank line closes the current
    one.

    This is the single reader for that wire format. Consumers must not
    re-implement delimiter parsing: a stale ``\x1f`` split here silently dropped
    every reviewer finding (issue #4790).
    """
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if "=" not in line:
            if not line.strip() and current is not None:
                records.append(current)
                current = None
            continue
        parsed = larch_io.parse_kv(line, duplicate_policy="first")
        if not parsed:
            continue
        key, value = next(iter(parsed.items()))
        if key == "REVIEWER_FILE":
            if current is not None:
                records.append(current)
            current = {key: value}
        elif current is not None:
            current[key] = value
    if current is not None:
        records.append(current)
    return records


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
            parsed = larch_io.parse_kv(line, duplicate_policy="first")
            if not parsed:
                continue
            key, value = next(iter(parsed.items()))
            current[key] = value
    if current:
        records.append(current)
    return records
