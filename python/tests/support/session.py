"""Deterministic implement/design session and tmpdir fixture writers."""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Collection, Mapping
from pathlib import Path

from larch.state.session_env import WRITE_DESIGN_ENV_KEYS

from tests.support.repo_contract import ROOT

_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

IMPLEMENT_SESSION_ENV_NAME = "session-env.sh"
DESIGN_SOURCE_ENV_NAME = "source-env.sh"

# Exact baseline order matching the former dispatch ``_session`` fixture.
_IMPLEMENT_BASELINE_ORDER: tuple[str, ...] = (
    "CURSOR_PRESENT",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_CLAUDE_PLUGIN_ROOT",
    "REPO_ROOT",
)

IMPLEMENT_BASELINE_KEYS: frozenset[str] = frozenset(_IMPLEMENT_BASELINE_ORDER)

_DESIGN_BASELINE_ORDER: tuple[str, ...] = (
    "DESIGN_TMPDIR",
    "SESSION_TMPDIR",
    "SESSION_ID",
    "REPO_ROOT",
    "CLAUDE_PLUGIN_ROOT",
)

DESIGN_BASELINE_KEYS: frozenset[str] = frozenset(_DESIGN_BASELINE_ORDER)

_DEFAULT_PLAN = "## Plan\n"
_DEFAULT_FEATURE = "feature\n"
_DEFAULT_DESIGN_SESSION_ID = "test-session"

_RUN_PARAMS_SCHEMA_V3: dict[str, object] = {
    "schema_version": 3,
    "partition_requested": False,
    "brainstorm_requested": False,
    "approve_requested": False,
    "skip_approve_requested": False,
    "difficulty_override": "",
}


def _validate_env_key(key: str) -> None:
    if not _KEY_RE.fullmatch(key):
        msg = f"invalid environment key name: {key!r}"
        raise ValueError(msg)


def _validate_env_value(key: str, value: str) -> None:
    if "\n" in value or "\r" in value or "\x00" in value:
        msg = f"unsafe environment value for {key}: contains newline, CR, or NUL"
        raise ValueError(msg)


def _reject_override_omit_conflict(
    *,
    overrides: Mapping[str, str],
    omit: Collection[str],
) -> None:
    conflict = sorted(set(overrides) & set(omit))
    if conflict:
        msg = f"override/omit conflict for keys: {', '.join(conflict)}"
        raise ValueError(msg)


def _merge_env_entries(
    *,
    baseline: Mapping[str, str],
    baseline_order: tuple[str, ...],
    overrides: Mapping[str, str] | None,
    omit: Collection[str] | None,
    allowed_keys: frozenset[str] | None,
) -> list[tuple[str, str]]:
    override_map = dict(overrides or {})
    omit_set = set(omit or ())
    _reject_override_omit_conflict(overrides=override_map, omit=omit_set)

    for key in (*baseline_order, *override_map, *omit_set):
        _validate_env_key(key)
    for key, value in override_map.items():
        _validate_env_value(key, value)
        if allowed_keys is not None and key not in allowed_keys:
            msg = f"key not allowed for this writer: {key}"
            raise ValueError(msg)

    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key in baseline_order:
        if key in omit_set:
            continue
        value = override_map[key] if key in override_map else baseline[key]
        entries.append((key, value))
        seen.add(key)

    for key in sorted(override_map):
        if key in seen:
            continue
        entries.append((key, override_map[key]))
        seen.add(key)
    return entries


def write_session_env(
    implement_tmpdir: Path | str,
    *,
    overrides: Mapping[str, str] | None = None,
    omit: Collection[str] | None = None,
) -> Path:
    """Write a plain ``session-env.sh`` KEY=value fixture under *implement_tmpdir*."""
    tmpdir = Path(implement_tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    root = str(ROOT)
    baseline = {
        "CURSOR_PRESENT": "false",
        "CODEX_BINARY_FOUND": "true",
        "CURSOR_BINARY_FOUND": "true",
        "LARCH_CLAUDE_PLUGIN_ROOT": root,
        "REPO_ROOT": root,
    }
    entries = _merge_env_entries(
        baseline=baseline,
        baseline_order=_IMPLEMENT_BASELINE_ORDER,
        overrides=overrides,
        omit=omit,
        allowed_keys=None,
    )
    path = tmpdir / IMPLEMENT_SESSION_ENV_NAME
    text = "".join(f"{key}={value}\n" for key, value in entries)
    _ = path.write_text(text, encoding="utf-8")
    return path


def write_design_source_env(
    design_tmpdir: Path | str,
    *,
    overrides: Mapping[str, str] | None = None,
    omit: Collection[str] | None = None,
    session_id: str = _DEFAULT_DESIGN_SESSION_ID,
) -> Path:
    """Write a production-style ``source-env.sh`` under *design_tmpdir*."""
    tmpdir = Path(design_tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    root = str(ROOT)
    design_path = str(tmpdir)
    baseline = {
        "DESIGN_TMPDIR": design_path,
        "SESSION_TMPDIR": design_path,
        "SESSION_ID": session_id,
        "REPO_ROOT": root,
        "CLAUDE_PLUGIN_ROOT": root,
    }
    entries = _merge_env_entries(
        baseline=baseline,
        baseline_order=_DESIGN_BASELINE_ORDER,
        overrides=overrides,
        omit=omit,
        allowed_keys=WRITE_DESIGN_ENV_KEYS,
    )
    path = tmpdir / DESIGN_SOURCE_ENV_NAME
    lines = [
        "#!/usr/bin/env bash\n",
        "# /design session env — generated by session_env.py. Do not edit.\n",
    ]
    for key, value in entries:
        lines.append(f"export {key}={shlex.quote(value)}\n")
    _ = path.write_text("".join(lines), encoding="utf-8")
    return path


def seed_plan(tmpdir: Path | str, content: str = _DEFAULT_PLAN) -> Path:
    """Write ``plan.txt`` under *tmpdir* and return its path."""
    path = Path(tmpdir) / "plan.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")
    return path


def seed_feature_description(
    tmpdir: Path | str,
    content: str = _DEFAULT_FEATURE,
) -> Path:
    """Write ``feature-description.txt`` under *tmpdir* and return its path."""
    path = Path(tmpdir) / "feature-description.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")
    return path


def run_params_text(*, overrides: Mapping[str, object] | None = None) -> str:
    """Return schema-v3 ``run-params.json`` text matching ``write_run_params_main`` defaults."""
    payload: dict[str, object] = dict(_RUN_PARAMS_SCHEMA_V3)
    if overrides:
        payload.update(overrides)
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def seed_run_params(
    tmpdir: Path | str,
    *,
    overrides: Mapping[str, object] | None = None,
) -> Path:
    """Write schema-v3 ``run-params.json`` matching ``write_run_params_main`` defaults."""
    path = Path(tmpdir) / "run-params.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(run_params_text(overrides=overrides), encoding="utf-8")
    return path


def make_implement_tmpdir(  # noqa: PLR0913 - plan/feature/omit/overrides/run_params are the fixture contract
    tmp_path: Path,
    *,
    plan: str = _DEFAULT_PLAN,
    feature: str = _DEFAULT_FEATURE,
    overrides: Mapping[str, str] | None = None,
    omit: Collection[str] | None = None,
    run_params: bool = False,
) -> Path:
    """Create ``tmp_path / "impl"`` with plan, feature, and session-env fixtures."""
    impl = tmp_path / "impl"
    impl.mkdir(parents=True, exist_ok=True)
    _ = seed_plan(impl, plan)
    _ = seed_feature_description(impl, feature)
    _ = write_session_env(impl, overrides=overrides, omit=omit)
    if run_params:
        _ = seed_run_params(impl)
    return impl


def make_design_tmpdir(
    tmp_path: Path,
    *,
    session_id: str = _DEFAULT_DESIGN_SESSION_ID,
    overrides: Mapping[str, str] | None = None,
    omit: Collection[str] | None = None,
    run_params: bool = False,
) -> Path:
    """Create ``tmp_path / "design"`` with a design ``source-env.sh`` fixture."""
    design = tmp_path / "design"
    design.mkdir(parents=True, exist_ok=True)
    _ = write_design_source_env(
        design,
        overrides=overrides,
        omit=omit,
        session_id=session_id,
    )
    if run_params:
        _ = seed_run_params(design)
    return design
