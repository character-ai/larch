"""Resolvers for per-role external tool defaults."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import config

VALID_TOOLS = frozenset({"cursor", "codex", "claude"})
SCOUT_ROLE_IDS = frozenset({"review.dynamic_archetype_scout", "design.plan_archetype_scout"})


@dataclass(frozen=True)
class ResolveResult:
    vendor: str
    skip_reason: str = ""


@dataclass(frozen=True)
class TierSelectResult:
    action: str
    selected_tier: str
    failure_reason: str


class ExternalDefaultError(ValueError):
    """Resolver contract error."""


def binary_available(*, name: str, implement_tmpdir: Path, binary: str) -> bool:
    """Resolve recorded tool availability before consulting the live PATH."""
    value = os.environ.get(name, "")
    if value in {"true", "false"}:
        return value == "true"
    session_env = implement_tmpdir / "session-env.sh"
    if session_env.is_file():
        values = larch_io.read_kvs(
            session_env,
            duplicate_policy="all",
            cr_strip="suffix",
            on_error_default=True,
        )
        for recorded in values.get(name, []):
            if recorded in {"true", "false"}:
                return recorded == "true"
    return shutil.which(binary) is not None


def _env_mapping(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def _validate_tool(tool: str, *, role_id: str) -> None:
    if tool not in VALID_TOOLS:
        raise ExternalDefaultError(f"{role_id}: invalid tool {tool!r}")


def _validate_role(role: config.RoleDefault) -> None:
    for tool in role.order:
        _validate_tool(tool, role_id=role.role_id)
    for slot in role.slots:
        _validate_tool(slot.tool, role_id=role.role_id)
    for policy in role.voter_policies:
        _validate_tool(policy.primary_tool, role_id=role.role_id)
        for tool, _label in policy.semantic_labels:
            _validate_tool(tool, role_id=role.role_id)
    if role.decompose_panel_policy:
        for tool in role.decompose_panel_policy.parallel_tools:
            _validate_tool(tool, role_id=role.role_id)


def role_default(role_id: str, env: Mapping[str, str] | None = None) -> config.RoleDefault:  # lint-keyword-only: ok public resolver signature keeps env positional parity
    del env
    role = config.ROLE_DEFAULTS.get(role_id)
    if role is None:
        raise ExternalDefaultError(f"unknown role: {role_id}")
    _validate_role(role)
    return role


def tool_order(role_id: str, env: Mapping[str, str] | None = None) -> tuple[str, ...]:  # lint-keyword-only: ok public resolver signature keeps env positional parity
    role = role_default(role_id, env=env)
    if role.kind != "waterfall":
        raise ExternalDefaultError(f"{role_id}: tool_order requires kind=waterfall")
    return tuple(role.order)


def _available(tool: str, *, codex_present: bool, cursor_present: bool) -> bool:
    if tool == "codex":
        return codex_present
    if tool == "cursor":
        return cursor_present
    if tool == "claude":
        return True
    raise ExternalDefaultError(f"invalid tool {tool!r}")


def next_untried_tier(
    role_id: str,
    attempted_tiers: Iterable[str],
    *,
    codex_present: bool = False,
    cursor_present: bool = False,
    claude_present: bool = True,
) -> TierSelectResult:
    """Select the next available tier that has not already been dispatched.

    ``attempted_tiers`` contains launched or dispatched tiers regardless of
    success, failure, or timeout. Tiers skipped only because their executable
    was unavailable are excluded.
    """
    configured_tiers: tuple[str, ...] = tool_order(role_id)
    attempted: frozenset[str] = frozenset(attempted_tiers)
    invalid_tiers: frozenset[str] = attempted.difference(configured_tiers)
    if invalid_tiers:
        invalid: str = sorted(invalid_tiers)[0]
        raise ExternalDefaultError(f"{role_id}: invalid attempted tier {invalid!r}")

    if len(attempted) == len(configured_tiers):
        return TierSelectResult(
            config.FIXER_TIER_ACTION_EXHAUSTED,
            "",
            config.FIXER_TIER_FAIL_REASON_EXHAUSTED,
        )

    availability: dict[str, bool] = {
        "codex": codex_present,
        "cursor": cursor_present,
        "claude": claude_present,
    }
    for tier in configured_tiers:
        if tier not in attempted and availability[tier]:
            return TierSelectResult(config.FIXER_TIER_ACTION_SELECTED, tier, "")
    return TierSelectResult(
        config.FIXER_TIER_ACTION_UNAVAILABLE,
        "",
        config.FIXER_TIER_FAIL_REASON_UNAVAILABLE,
    )


def fixer_lane_budget_sec(role_id: str) -> int:
    """Return the total budget that reserves one full timeout per tier."""
    return len(tool_order(role_id)) * config.FIXER_LANE_TIMEOUT_SEC


def _override_result(raw: str) -> ResolveResult | None:
    if raw == "":
        return None
    if any(ch.isspace() for ch in raw):
        return ResolveResult("", "invalid-vendor")
    if raw not in {"codex", "claude"}:
        return ResolveResult("", "unknown-vendor")
    return ResolveResult(raw, "")


def resolve_vendor(  # lint-keyword-only: ok public resolver signature keeps env positional parity
    role_id: str,
    env: Mapping[str, str] | None = None,
    *,
    codex_present: bool = False,
    cursor_present: bool = False,
) -> ResolveResult:
    role = role_default(role_id, env=env)
    if role.kind != "first_available":
        raise ExternalDefaultError(f"{role_id}: resolve_vendor requires kind=first_available")
    env_map = _env_mapping(env)
    if role.env_override:
        override = _override_result(env_map.get(role.env_override, ""))
        if override is not None:
            return override
    for tool in role.order:
        if _available(tool, codex_present=codex_present, cursor_present=cursor_present):
            return ResolveResult(tool, "")
    return ResolveResult("", "no-vendor")


def slot_defaults(role_id: str, env: Mapping[str, str] | None = None) -> tuple[config.SlotDefault, ...]:  # lint-keyword-only: ok public resolver signature keeps env positional parity
    role = role_default(role_id, env=env)
    if role.kind not in {"slot_panel", "single_slot"}:
        raise ExternalDefaultError(f"{role_id}: slot_defaults requires a slot-shaped role")
    return tuple(role.slots)


def voter_policies(role_id: str) -> tuple[config.VoterPolicyDefault, ...]:
    role = role_default(role_id)
    if role.kind != "voter_policies":
        raise ExternalDefaultError(f"{role_id}: voter_policies requires kind=voter_policies")
    return tuple(role.voter_policies)


def panel_dispatch_policy(role_id: str) -> config.PanelDispatchPolicy | None:
    role = role_default(role_id)
    if role.kind != "slot_panel":
        raise ExternalDefaultError(f"{role_id}: panel_dispatch_policy requires kind=slot_panel")
    return role.dispatch_policy


def voter_dispatch_policy(role_id: str) -> config.VoterDispatchPolicy | None:
    role = role_default(role_id)
    if role.kind != "voter_policies":
        raise ExternalDefaultError(f"{role_id}: voter_dispatch_policy requires kind=voter_policies")
    return role.voter_dispatch_policy


def doc_rows() -> tuple[config.RoleDefault, ...]:
    return tuple(role for role in config.ROLE_DEFAULTS.values() if role.doc_phase)
