# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

from larch.agents import agents
from larch.core import config, external_defaults
from larch.git import rebase


def _tool_order_probe(monkeypatch: pytest.MonkeyPatch, module: Any, expected_role: str, order: tuple[str, ...]) -> list[str]:
    seen: list[str] = []

    def fake_tool_order(role_id: str, *_args: object, **_kwargs: object) -> tuple[str, ...]:
        seen.append(role_id)
        assert role_id == expected_role
        return order

    monkeypatch.setattr(module.external_defaults, "tool_order", fake_tool_order)
    return seen


def test_rebase_conflict_loop_uses_rebase_conflict_fixer_role(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, rebase, "implement.rebase_conflict_fixer", ("cursor", "codex"))
    launch_calls: list[str] = []
    unmerged_calls = [("conflicted.txt",), (), ()]

    def fake_unmerged(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return unmerged_calls.pop(0)

    def fake_launch(tier: str, _conflict_csv: str) -> agents.TierAttempt:
        launch_calls.append(tier)
        return agents.TierAttempt(tier=tier, wrapper_rc=0, launcher_exit=0, failure=agents.LaunchFailure("", ""))

    runner = SimpleNamespace(run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(rebase, "_unmerged_paths", fake_unmerged)
    monkeypatch.setattr(rebase.git, "tracked_dirty_paths", lambda *_args, **_kwargs: frozenset())
    monkeypatch.setattr(rebase.git, "untracked_dirty_paths", lambda *_args, **_kwargs: frozenset())
    monkeypatch.setattr(rebase.coder_delta_guards, "staged_dirty_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(rebase.coder_delta_guards, "coder_forbidden_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(rebase.coder_delta_guards, "revert_forbidden_paths", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(rebase, "_stage_resolved_conflict_files", lambda *_args, **_kwargs: (["conflicted.txt"], []))
    monkeypatch.setattr(rebase, "_path_has_conflict_markers", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(rebase, "_reset_conflict_paths", lambda **_kwargs: None)
    monkeypatch.setattr(rebase.git, "paths_delta_revert", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(rebase.git, "rebase_continue", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))

    rebase._resolve_conflicts(runner=runner, launch_fn=fake_launch, repo="repo", run_id="run", cwd="repo")

    assert seen == ["implement.rebase_conflict_fixer"]
    assert launch_calls == ["cursor"]


def test_debate_roles_do_not_alter_existing_panels() -> None:
    review_slots = external_defaults.slot_defaults("review.panel")
    assert all(slot.slot in {"correctness", "edge-cases", "testing"} for slot in review_slots)
    assert "debate.panel" in config.ROLE_DEFAULTS
    assert "debate.synthesizer" in config.ROLE_DEFAULTS
    # Existing panels remain unchanged in size/shape after debate registration.
    assert len(review_slots) == 6
    assert external_defaults.tool_order("implement.step2_coder") == ("codex", "cursor", "claude")
