# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Fail-closed native blocked-by reads for migration admission.

The `/block-issue` dependency mutations themselves moved to the Rust owner in
#8170: `crates/larch-cli/src/issue_dependency_commands.rs` runs both verbs over
the typed GitHub adapter. What stays here is the in-process read
``larch.issue.migration_governance`` still calls directly, which migrates with
its own command leaf.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from larch.core import proc
from larch.git import gh


class DependencyReadError(Exception):
    """Fail-closed dependency read failure for migration admission."""


@dataclass(frozen=True)
class BlockedByDependency:
    """Native blocked-by edge with freshness fields."""

    number: int
    state: str
    updated_at: str


def read_blocked_by_dependencies(
    runner: proc.Runner,
    issue: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> tuple[BlockedByDependency, ...]:
    """Read native blocked-by edges with state and ``updatedAt``.

    Fail closed: transport errors, malformed JSON, or missing freshness fields
    raise ``DependencyReadError``. Never treat a read failure as an empty set.
    """
    result = gh.issue_blocked_by_read(runner, str(issue), repo=repo, cwd=cwd)
    if result.returncode != 0:
        raise DependencyReadError(
            f"blocked-by read failed: {result.stderr or result.stdout}"
        )
    try:
        rows = gh.loads_json_paginated_list(result.stdout)
    except Exception as exc:
        raise DependencyReadError("blocked-by read returned malformed JSON") from exc
    numbers: list[int] = []
    for row_obj in rows:
        if not isinstance(row_obj, dict):
            raise DependencyReadError("blocked-by row is not an object")
        row = cast("dict[str, object]", row_obj)
        number = row.get("number")
        if isinstance(number, int) and number >= 1:
            numbers.append(number)
        elif isinstance(number, str) and number.isdigit() and int(number) >= 1:
            numbers.append(int(number))
        else:
            raise DependencyReadError("blocked-by row missing issue number")
    resolved: list[BlockedByDependency] = []
    for number in sorted(set(numbers)):
        view = gh.issue_view_field_read(
            runner, str(number), "number,state,updatedAt", repo=repo, cwd=cwd
        )
        if view.returncode != 0:
            raise DependencyReadError(
                f"blocked-by freshness read failed for #{number}"
            )
        try:
            payload: object = json.loads(view.stdout or "null")
        except json.JSONDecodeError as exc:
            raise DependencyReadError(
                f"blocked-by freshness JSON invalid for #{number}"
            ) from exc
        if not isinstance(payload, dict):
            raise DependencyReadError(
                f"blocked-by freshness JSON invalid for #{number}"
            )
        data = cast("dict[str, object]", payload)
        state = str(data.get("state", "")).strip().lower()
        updated_at = data.get("updatedAt")
        if not state or not isinstance(updated_at, str) or not updated_at:
            raise DependencyReadError(
                f"blocked-by freshness fields missing for #{number}"
            )
        resolved.append(
            BlockedByDependency(number=number, state=state, updated_at=updated_at)
        )
    return tuple(resolved)
