"""Frozen run context passed through ship-pr phases."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace


@dataclass(frozen=True)
class RunContext:
    branch: str
    issue: str
    repo: str
    run_id: str
    tmpdir: str
    merge: bool
    draft: bool
    forked: bool
    manifest_path: str
    tool_label: str
    no_admin_fallback: bool
    repo_unavailable: bool
    pr_number: int | None = None
    state_file: str | None = None

    def with_(self, **changes: object) -> RunContext:
        known = {f.name for f in fields(self)}
        unknown = set(changes) - known
        if unknown:
            msg = f"unknown RunContext fields: {sorted(unknown)}"
            raise TypeError(msg)
        return replace(self, **changes)
