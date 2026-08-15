# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

from larch.agents import agents
from larch.implement import checks
from larch.implement import checks_lint_fix as _clf
from larch.implement import ci_monitor
from larch.design import decompose
from larch.core import external_defaults
from larch.design import plan_scout
from larch.git import rebase

from larch.core import config


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


def test_checks_lint_fix_uses_lint_fix_coder_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, checks, "implement.lint_fix_coder", ("cursor", "codex", "claude"))
    run_parent = tmp_path / "lint-fix-loop"
    run_parent.mkdir()
    log = tmp_path / "checks.log"
    log.write_text("failure\n", encoding="utf-8")
    agent_cli = tmp_path / "cli.py"
    agent_cli.write_text("# cli\n", encoding="utf-8")
    run_calls: list[str] = []
    runner = SimpleNamespace(run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))

    def fake_cursor(*_args: object, **_kwargs: object) -> int:
        run_calls.append("cursor")
        return 0

    # The waterfall harness calls _capture_tracked_paths: (0) baseline, (1) per-attempt
    # baseline before cursor, (2) post-dispatch current (needs useful delta).
    capture_count: list[int] = [0]
    def tracked_with_useful_delta(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        n = capture_count[0]
        capture_count[0] += 1
        # Calls 0 and 1 are pre-dispatch; call 2+ is post-dispatch for cursor.
        return ("fixed.py",) if n >= 2 else ()  # type: ignore[return-value]

    monkeypatch.setattr(_clf, "_agent_cli", lambda: agent_cli)
    monkeypatch.setattr(_clf, "plugin_scripts_dir", lambda: tmp_path)
    monkeypatch.setattr(_clf, "_capture_tracked_paths", tracked_with_useful_delta)
    monkeypatch.setattr(_clf, "_capture_untracked_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(checks.git, "rev_parse", lambda *_args, **_kwargs: "HEAD")
    monkeypatch.setattr(checks.git, "current_branch", lambda *_args, **_kwargs: "feature")
    monkeypatch.setattr(_clf, "_submodule_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(checks.coder_delta_guards, "coder_forbidden_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(_clf, "_run_cursor", fake_cursor)
    monkeypatch.setattr(_clf, "_post_dispatch_forbidden_revert", lambda *_args, **_kwargs: 0)

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(tmp_path),
        codex_present=True,
        cursor_present=True,
        run_parent=str(run_parent),
        allowed_tmpdir=str(tmp_path),
        claude_present=True,
    )

    # The waterfall harness calls tool_order multiple times (once for budget calculation,
    # once per tier selection). Verify all calls use the correct role_id.
    assert seen
    assert all(s == "implement.lint_fix_coder" for s in seen)
    assert run_calls == ["cursor"]
    assert outcome.coder_tool == "cursor"



def test_ci_monitor_available_tiers_uses_ci_recovery_role(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, ci_monitor, "implement.ci_recovery_fixer", ("codex", "claude"))

    assert ci_monitor._available_tiers() == ("codex", "claude")
    assert seen == ["implement.ci_recovery_fixer"]


def test_plan_scout_uses_dynamic_and_plan_role_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, plan_scout, "review.dynamic_archetype_scout", ("claude",))
    plan_scout.scout_dynamic_archetypes(mode="diff", max_archetypes=0, output=tmp_path / "dynamic.json")
    assert seen == ["review.dynamic_archetype_scout"]

    plan = tmp_path / "plan.txt"
    desc = tmp_path / "feature-description.txt"
    plan.write_text("plan\n", encoding="utf-8")
    desc.write_text("feature\n", encoding="utf-8")
    scout_commands: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[Any]:
        if "scope-paths" in cmd:
            stdout = kwargs.get("stdout")
            if stdout is not None:
                stdout.write("README.md\n")
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        scout_commands.append(cmd)
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text('{"archetypes":[]}\n', encoding="utf-8")
        stdout = kwargs.get("stdout")
        if stdout is not None:
            stdout.write("SCOUT_STATUS=empty\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(plan_scout.subprocess, "run", fake_run)

    plan_scout.scout_plan_archetypes(
        role_id="design.plan_archetype_scout",
        plan_file=plan,
        description_file=desc,
        output=tmp_path / "plan-scout.json",
        max_archetypes=3,
        session_env_path="",
        codex_present=False,
        cursor_present=True,
    )

    assert scout_commands
    assert scout_commands[-1][scout_commands[-1].index("--role-id") + 1] == "design.plan_archetype_scout"




def test_decompose_panel_and_aggregator_use_decompose_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen_role_default: list[str] = []
    seen_slots: list[str] = []
    plan = tmp_path / "plan.txt"
    feature = tmp_path / "feature-description.txt"
    plan.write_text("plan\n", encoding="utf-8")
    feature.write_text("feature\n", encoding="utf-8")

    def fake_role_default(role_id: str, *_args: object, **_kwargs: object) -> config.RoleDefault:
        seen_role_default.append(role_id)
        assert role_id == "design.decompose_panel"
        return config.RoleDefault(
            role_id=role_id,
            kind="slot_panel",
            decompose_panel_policy=config.DecomposePanelPolicy(parallel_tools=("cursor",), panel_no_fallback=True, archetypes=decompose.DECOMPOSE_ARCHETYPES),
        )

    def fake_slot_defaults(role_id: str, *_args: object, **_kwargs: object) -> tuple[config.SlotDefault, ...]:
        seen_slots.append(role_id)
        if role_id == "design.decompose_panel":
            return tuple(
                config.SlotDefault(slot=f"sentinel-{arch}", tool="cursor", output=f"sentinel-{arch}.out", archetype=arch)
                for arch in decompose.DECOMPOSE_ARCHETYPES
            )
        if role_id == "design.decompose_aggregator":
            return (config.SlotDefault(slot="sentinel-aggregator", tool="codex", output="agg.out"),)
        raise AssertionError(role_id)

    def fake_render(_archetype: str, *, out: Path, **_kwargs: object) -> None:
        out.write_text("prompt\n", encoding="utf-8")

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        slots_file = Path(cmd[cmd.index("--slots-file") + 1])
        outputs = []
        for line in slots_file.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            output = Path(row["output"])
            output.write_text("## Recommendation\nsplit\n", encoding="utf-8")
            outputs.append(str(output))
        paths = tmp_path / "resolved-paths.txt"
        paths.write_text("".join(f"{path}\n" for path in outputs), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, f"DISPATCH_OK=true\nSTATIC_DISPATCH_OK=true\nALL_OUTPUT_FILES_PATH={paths}\nFALLBACK_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\n", "")

    monkeypatch.setattr(decompose.external_defaults, "role_default", fake_role_default)
    monkeypatch.setattr(decompose.external_defaults, "slot_defaults", fake_slot_defaults)
    monkeypatch.setattr(decompose, "_render_decompose_prompt", fake_render)
    monkeypatch.setattr(decompose.subprocess, "run", fake_run)

    decompose.dispatch_panel(design_tmpdir=tmp_path, codex_present=False, cursor_present=True, mode="plan", plan_file=plan, feature_file=feature)
    panel_outputs = tmp_path / "decompose" / "panel-outputs.ndjson"
    status = decompose.aggregate_partition(design_tmpdir=tmp_path, panel_outputs_file=panel_outputs, codex_present=True, cursor_present=True, output=tmp_path / "partition.md")

    assert status == "ok"
    assert seen_role_default == ["design.decompose_panel"]
    assert "design.decompose_panel" in seen_slots
    assert "design.decompose_aggregator" in seen_slots
















def test_debate_roles_do_not_alter_existing_panels() -> None:
    review_slots = external_defaults.slot_defaults("review.panel")
    assert all(slot.slot in {"correctness", "edge-cases", "testing"} for slot in review_slots)
    assert "debate.panel" in config.ROLE_DEFAULTS
    assert "debate.synthesizer" in config.ROLE_DEFAULTS
    # Existing panels remain unchanged in size/shape after debate registration.
    assert len(review_slots) == 6
    assert external_defaults.tool_order("implement.step2_coder") == ("codex", "cursor", "claude")
