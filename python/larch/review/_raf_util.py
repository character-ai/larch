"""Shared utilities for the review-and-fix subsystem.

Internal helpers only — not part of the larch public API.
"""
# ruff: noqa: SIM108, FURB110

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path

from larch import io as larch_io
from larch.core import config
from larch.core import logging_util
from larch.core import proc
from larch.review import review_pipeline
from larch.review.review_types import parse_findings, read_finding_text

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_PY_CLI = _PLUGIN_ROOT / "python" / "cli.py"


def _plugin_root() -> Path:
    return Path(os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, str(_PLUGIN_ROOT))).resolve()


def _emit_kv(*, key: str, value: str | int | bool) -> None:
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    logging_util.emit_kv(key=key, value=text)


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> proc.CommandResult:
    return proc.run(argv, cwd=str(cwd) if cwd else None, env=env)


def _read_text(path: Path) -> str:
    return read_finding_text(path)


def _write_text(*, path: Path, text: str) -> None:
    larch_io.write_text(path=path, text=text)


def _append_text(*, path: Path, text: str) -> None:
    larch_io.append_text(path=path, text=text)


def _parse_env_lines(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, skip_empty_key=True)


def _parse_env_file(path: Path) -> dict[str, str]:
    return larch_io.parse_kv(larch_io.read_text(path, default=""), skip_empty_key=True)


def _core_round_state(*, core: dict[str, str], round_dir: Path) -> tuple[str, int, int, int, int, Path, Path]:
    def count(key: str) -> int:
        value = core.get(key, "0") or "0"
        return int(value) if value.isdigit() else 0

    return (
        core.get("REVIEW_CORE_STATUS", "unknown"),
        count("ACCEPTED_COUNT"),
        count("REJECTED_COUNT"),
        count("EXONERATED_COUNT"),
        count("NEUTRAL_COUNT"),
        Path(core.get("ACCEPTED_FINDINGS_FILE", str(round_dir / "accepted-findings.md"))),
        Path(core.get("REJECTED_FINDINGS_FILE", str(round_dir / "rejected-findings.md"))),
    )


def _env_get(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.parse_kv(larch_io.read_text(path, default=""), skip_empty_key=True).get(key, default)


def _session_get(*, session_env_path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=session_env_path, key=key, default=default, first_match=True, cr_strip="none")


def _rehydrate_session_env(session_env_path: Path) -> None:
    if not session_env_path.is_file():
        return
    for key, default in (
        ("LARCH_TOKEN_SESSION_ID", ""),
        ("LARCH_CLAUDE_SOURCE_FILE", os.environ.get("LARCH_CLAUDE_SOURCE_FILE", "")),
        ("LARCH_TIMING_LEDGER", os.environ.get("LARCH_TIMING_LEDGER", "")),
        ("LARCH_TIMING_SKILL", os.environ.get("LARCH_TIMING_SKILL", "")),
    ):
        value = _session_get(session_env_path=session_env_path, key=key, default=default)
        if value:
            os.environ[key] = value
    for key in ("CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND"):
        value = _session_get(session_env_path=session_env_path, key=key, default="")
        if value in {"true", "false"}:
            os.environ[key] = value


def _prior_summary_counts(*, implement_tmpdir: Path, round_num: int) -> tuple[int, int, int, int]:
    prior_summary = implement_tmpdir / "review-and-fix-summary.json"
    if not prior_summary.is_file():
        return 0, 0, 0, 0
    try:
        data = json.loads(_read_text(prior_summary))
    except json.JSONDecodeError:
        return 0, 0, 0, 0
    if data.get("schema_version") not in {2, 3}:
        return 0, 0, 0, 0
    prior_rounds = int(data.get("rounds_completed", 0) or 0)
    if prior_rounds >= round_num:
        return 0, 0, 0, 0
    return (
        int(data.get("accepted_count", 0) or 0),
        int(data.get("rejected_count", 0) or 0),
        int(data.get("exonerated_count", 0) or 0),
        int(data.get("neutral_count", 0) or 0),
    )


def _positive_int(*, value: str, label: str) -> int:
    if not value.isdigit() or int(value) <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return int(value)


def _non_negative_int(*, value: str, label: str) -> int:
    if not value.isdigit():
        raise ValueError(f"{label} must be a non-negative integer")
    return int(value)


def _count_findings(path: Path) -> int:
    return len(parse_findings(path, boundary="finding_heading"))


def _count_matching_lines(path: Path, *, pattern: str) -> int:
    if not path.is_file() or not path.stat().st_size:
        return 0
    return len(re.findall(pattern, _read_text(path), flags=re.MULTILINE))


def _count_rejected_lines(path: Path) -> int:
    if not path.is_file() or not path.stat().st_size:
        return 0
    text = _read_text(path)
    count = len(re.findall(r"^###\s+\[(?:rejected|Code Review)\]\s+", text, flags=re.MULTILINE))
    if count:
        return count
    count = len(re.findall(r"^(?:[0-9]+:FINDING_[A-Za-z0-9_]+_OUTCOME=rejected|\[[^]]+\]|- )", text, flags=re.MULTILINE))
    return count if count else 1


def _write_env(*, path: Path, values: dict[str, str | int | bool]) -> None:
    lines: list[str] = []
    for key, value in values.items():
        if isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        if "\n" in text or "\r" in text:
            text = text.replace("\r", " ").replace("\n", " ")
        lines.append(f"{key}={text}")
    _write_text(path=path, text="\n".join(lines) + "\n")


def _git_output(args: list[str]) -> str:
    result = _run(["git", *args])
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_stdout(args: list[str]) -> str:
    result = _run(["git", *args])
    return result.stdout if result.returncode == 0 else ""


def _git_status_porcelain() -> str:
    return _git_output(["status", "--porcelain"])


def _git_status_porcelain_or_fail() -> tuple[str, bool]:
    result = _run(["git", "status", "--porcelain"])
    return result.stdout, result.returncode == 0


def _git_head() -> str:
    return _git_output(["rev-parse", "HEAD"])


def _resolve_run_id(*, session_env_path: Path, implement_tmpdir: Path, session_id_file: Path) -> str:
    run_id = _session_get(session_env_path=session_env_path, key="RUN_ID", default="")
    if run_id:
        return run_id
    parent_issue = implement_tmpdir / "parent-issue.md"
    run_id = _session_get(session_env_path=parent_issue, key="RUN_ID", default="")
    if run_id:
        return run_id
    manifest_root = implement_tmpdir / "larch-logs" / "implement"
    if manifest_root.is_dir():
        manifests = list(manifest_root.glob("*/manifest.json"))
        if len(manifests) == 1:
            return manifests[0].parent.name
    if session_id_file.is_file() and session_id_file.stat().st_size:
        return _read_text(session_id_file).strip()
    return ""


def _step5_repo_root() -> str:
    raw = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if raw:
        result = _run(["git", "-C", raw, "rev-parse", "--show-toplevel"])
        top = result.stdout.strip()
        if result.returncode == 0 and top:
            return top
    result = _run(["git", "rev-parse", "--show-toplevel"])
    return result.stdout.strip() if result.returncode == 0 else ""


@contextlib.contextmanager
def _temporary_env(*, name: str, value: str | None):
    old = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


@contextlib.contextmanager
def _capture_emit_to(buffer: io.StringIO):
    original_emit = logging_util.emit
    original_stdout = sys.stdout

    def capture_emit(text: str) -> None:
        buffer.write(text if text.endswith("\n") else text + "\n")

    logging_util.emit = capture_emit  # type: ignore[method-assign]
    if getattr(review_pipeline, "logging_util", None) is logging_util:
        review_pipeline.logging_util.emit = capture_emit  # type: ignore[method-assign]
    sys.stdout = buffer
    try:
        yield
    finally:
        sys.stdout = original_stdout
        logging_util.emit = original_emit  # type: ignore[method-assign]
        if getattr(review_pipeline, "logging_util", None) is logging_util:
            review_pipeline.logging_util.emit = original_emit  # type: ignore[method-assign]
# pyright: reportUnusedFunction=false, reportUnusedCallResult=false
