"""Resolvers for per-role external tool defaults."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from larch.core import config

VALID_TOOLS = frozenset({"cursor", "codex", "claude"})
SCOUT_ROLE_IDS = frozenset({"review.dynamic_archetype_scout", "design.plan_archetype_scout"})


@dataclass(frozen=True)
class ResolveResult:
    vendor: str
    skip_reason: str = ""


class ExternalDefaultError(ValueError):
    """Resolver contract error."""


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


def _bool_arg(value: str, *, flag: str) -> bool:
    if value not in {"true", "false"}:
        raise ExternalDefaultError(f"{flag} must be true or false")
    return value == "true"


def role_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py external-defaults role")
    _ = parser.add_argument("--role", required=True)
    args = parser.parse_args(argv)
    try:
        role = role_default(args.role)
    except ExternalDefaultError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 2
    print(f"ROLE={role.role_id}")
    print(f"KIND={role.kind}")
    if role.order:
        print(f"ORDER={','.join(role.order)}")
    if role.env_override:
        print(f"ENV_OVERRIDE={role.env_override}")
    if role.slots:
        print(f"SLOT_COUNT={len(role.slots)}")
    if role.voter_policies:
        print(f"VOTER_COUNT={len(role.voter_policies)}")
    return 0


def resolve_vendor_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py external-defaults resolve-vendor")
    _ = parser.add_argument("--role", required=True)
    _ = parser.add_argument("--codex-present", default="false")
    _ = parser.add_argument("--cursor-present", default="false")
    args = parser.parse_args(argv)
    try:
        result = resolve_vendor(
            args.role,
            codex_present=_bool_arg(args.codex_present, flag="--codex-present"),
            cursor_present=_bool_arg(args.cursor_present, flag="--cursor-present"),
        )
    except ExternalDefaultError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 2
    print(f"ROLE={args.role}")
    print(f"VENDOR={result.vendor}")
    if result.skip_reason:
        print(f"SKIP_REASON={result.skip_reason}")
    return 0


def docs_main(argv: list[str]) -> int:
    if argv:
        print("external-defaults docs: no arguments expected", file=sys.stderr)
        return 2
    rows = doc_rows()
    print(f"DOC_ROW_COUNT={len(rows)}")
    for role in rows:
        print(f"DOC_ROW={role.role_id}\t{role.doc_phase}\t{role.doc_role}\t{role.doc_skills}\t{role.doc_fallback}")
    return 0
