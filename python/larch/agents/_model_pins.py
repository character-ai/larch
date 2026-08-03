"""Resolve config-pinned vendor model ids against live vendor model lists.

Used by `/status` (`status check`) when a vendor probe reports `ok`. Cursor pins
are checked via `cursor agent models`; Codex has no model-list surface and is
reported as unverifiable rather than silently skipped (G-Ext-5).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from larch.core import config
from larch.core.proc import CommandResult, Runner

_CURSOR_MODEL_LINE_RE = re.compile(config.CURSOR_MODEL_LIST_LINE_RE)


@dataclass(frozen=True)
class PinnedModel:
    constant_name: str
    model_id: str


@dataclass(frozen=True)
class VendorModelPinResult:
    vendor: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class ModelPinsReport:
    cursor: VendorModelPinResult
    codex: VendorModelPinResult


def cursor_pinned_model_declarations() -> tuple[PinnedModel, ...]:
    """All named Cursor pin declarations, retaining duplicate model IDs for diagnostics."""
    declarations: list[PinnedModel] = []
    seen_impl: set[str] = set()
    for model_id in config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY.values():
        if model_id in seen_impl:
            continue
        seen_impl.add(model_id)
        declarations.append(
            PinnedModel(constant_name="CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY", model_id=model_id)
        )
    declarations.append(
        PinnedModel(constant_name="DEBATE_CURSOR_MODEL", model_id=config.DEBATE_CURSOR_MODEL)
    )
    return tuple(declarations)


def cursor_pinned_models() -> tuple[PinnedModel, ...]:
    """Unique Cursor pins from implement-lane and debate inventories."""
    by_id: dict[str, str] = {}
    for pin in cursor_pinned_model_declarations():
        by_id.setdefault(pin.model_id, pin.constant_name)
    return tuple(
        PinnedModel(constant_name=constant_name, model_id=model_id)
        for model_id, constant_name in sorted(by_id.items())
    )


def codex_pinned_model_declarations() -> tuple[PinnedModel, ...]:
    """All named Codex pin declarations, retaining duplicate model IDs for diagnostics."""
    return (
        PinnedModel(constant_name="CODEX_DEFAULT_MODEL", model_id=config.CODEX_DEFAULT_MODEL),
        PinnedModel(
            constant_name="CODEX_REVIEW_MODEL_DEFAULT",
            model_id=config.CODEX_REVIEW_MODEL_DEFAULT,
        ),
        PinnedModel(
            constant_name="CODEX_VOTE_MODEL_DEFAULT",
            model_id=config.CODEX_VOTE_MODEL_DEFAULT,
        ),
        PinnedModel(constant_name="DEBATE_CODEX_MODEL", model_id=config.DEBATE_CODEX_MODEL),
    )


def codex_pinned_models() -> tuple[PinnedModel, ...]:
    """Codex pins that /status resolves (unverifiable until a list surface exists)."""
    by_id: dict[str, str] = {}
    for pin in codex_pinned_model_declarations():
        by_id.setdefault(pin.model_id, pin.constant_name)
    return tuple(
        PinnedModel(constant_name=constant_name, model_id=model_id)
        for model_id, constant_name in sorted(by_id.items())
    )


def parse_cursor_model_list(stdout: str) -> frozenset[str] | None:
    """Parse `cursor agent models` stdout with a pinned grammar.

    Returns the set of model ids, or None when the output is unparseable
    (fail closed: empty, header-only, or any non-matching non-blank line).
    """
    ids: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == config.CURSOR_MODEL_LIST_HEADER:
            continue
        match = _CURSOR_MODEL_LINE_RE.fullmatch(line)
        if match is None:
            return None
        ids.add(match.group(1))
    if not ids:
        return None
    return frozenset(ids)


def _sanitize_detail(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ").strip()


def _format_unknown_detail(unknown: tuple[PinnedModel, ...]) -> str:
    return "; ".join(f"{pin.constant_name}={pin.model_id}" for pin in unknown)


def _list_failed_detail(result: CommandResult) -> str:
    if result.returncode == config.PROC_TIMEOUT_EXIT_CODE:
        return "cursor agent models timed out"
    stderr = _sanitize_detail(result.stderr)
    if stderr:
        return f"cursor agent models exited {result.returncode}: {stderr}"
    return f"cursor agent models exited {result.returncode}"


def _model_list_timeout_seconds() -> float:
    raw = os.environ.get(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, "").strip()
    if raw:
        try:
            value = float(raw)
        except ValueError:
            value = float(config.EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC)
        else:
            if value <= 0:
                value = float(config.EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC)
        return value
    return float(config.EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC)


def resolve_cursor_model_pins(*, runner: Runner, vendor_state: str) -> VendorModelPinResult:
    """Resolve Cursor pins against the live model list when the vendor probe is ok."""
    if vendor_state != "ok":
        return VendorModelPinResult(
            vendor="cursor",
            status=config.MODEL_PINS_STATUS_SKIPPED,
            detail="vendor probe not ok",
        )
    timeout = _model_list_timeout_seconds()
    result = runner.run(config.CURSOR_MODEL_LIST_ARGV, timeout=timeout)
    if result.returncode != 0:
        return VendorModelPinResult(
            vendor="cursor",
            status=config.MODEL_PINS_STATUS_LIST_FAILED,
            detail=_list_failed_detail(result),
        )
    live_ids = parse_cursor_model_list(result.stdout)
    if live_ids is None:
        return VendorModelPinResult(
            vendor="cursor",
            status=config.MODEL_PINS_STATUS_UNPARSEABLE,
            detail="cursor agent models output unparseable",
        )
    unknown_ids = {pin.model_id for pin in cursor_pinned_models() if pin.model_id not in live_ids}
    if unknown_ids:
        unknown = tuple(
            pin for pin in cursor_pinned_model_declarations() if pin.model_id in unknown_ids
        )
        return VendorModelPinResult(
            vendor="cursor",
            status=config.MODEL_PINS_STATUS_UNKNOWN_ID,
            detail=_format_unknown_detail(unknown),
        )
    return VendorModelPinResult(vendor="cursor", status=config.MODEL_PINS_STATUS_OK)


def resolve_codex_model_pins(*, vendor_state: str) -> VendorModelPinResult:
    """Report Codex pins as unverifiable; Codex has no model-list CLI surface."""
    if vendor_state != "ok":
        return VendorModelPinResult(
            vendor="codex",
            status=config.MODEL_PINS_STATUS_SKIPPED,
            detail="vendor probe not ok",
        )
    pin_summary = ", ".join(
        f"{pin.constant_name}={pin.model_id}" for pin in codex_pinned_model_declarations()
    )
    return VendorModelPinResult(
        vendor="codex",
        status=config.MODEL_PINS_STATUS_UNVERIFIABLE,
        detail=f"codex has no model-list surface ({pin_summary})",
    )


def resolve_model_pins(*, runner: Runner, codex_state: str, cursor_state: str) -> ModelPinsReport:
    """Resolve per-vendor model pins for /status when each vendor probe is ok."""
    return ModelPinsReport(
        cursor=resolve_cursor_model_pins(runner=runner, vendor_state=cursor_state),
        codex=resolve_codex_model_pins(vendor_state=codex_state),
    )
