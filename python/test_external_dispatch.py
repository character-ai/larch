# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

from larch.agents import agent_voters
from larch.agents import agent_waterfall
from larch.agents import agents
from larch.state import bootstrap
from larch.implement import checks
from larch.implement import ci_monitor
from larch.design import decompose
import external_defaults
import plan_review_panel
from larch.design import plan_scout
from larch.git import rebase
import review_aggregate
import review_and_fix
import review_pipeline
from larch.core import config


def _tool_order_probe(monkeypatch: pytest.MonkeyPatch, module: Any, expected_role: str, order: tuple[str, ...]) -> list[str]:
    seen: list[str] = []

    def fake_tool_order(role_id: str, *_args: object, **_kwargs: object) -> tuple[str, ...]:
        seen.append(role_id)
        assert role_id == expected_role
        return order

    monkeypatch.setattr(module.external_defaults, "tool_order", fake_tool_order)
    return seen


def test_bootstrap_phase_coder_uses_step2_coder_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, bootstrap, "implement.step2_coder", ("cursor", "codex", "claude"))
    plan = tmp_path / "plan.txt"
    plan.write_text("plan\n", encoding="utf-8")
    (tmp_path / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    state = bootstrap.BootstrapState(
        opts=bootstrap.BootstrapOptions(up_to_phase="all"),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        codex_available="true",
        cursor_available="true",
        plan_file=str(plan),
    )

    bootstrap._phase_coder(state)

    assert seen == ["implement.step2_coder"]
    assert state.coder == "cursor"


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

    monkeypatch.setattr(checks, "_agent_cli", lambda: agent_cli)
    monkeypatch.setattr(checks, "_plugin_scripts_dir", lambda: tmp_path)
    monkeypatch.setattr(checks, "_capture_tracked_paths", lambda *_args, **_kwargs: frozenset())
    monkeypatch.setattr(checks, "_capture_untracked_paths", lambda *_args, **_kwargs: frozenset())
    monkeypatch.setattr(checks.git, "rev_parse", lambda *_args, **_kwargs: "HEAD")
    monkeypatch.setattr(checks.git, "current_branch", lambda *_args, **_kwargs: "feature")
    monkeypatch.setattr(checks, "_submodule_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(checks.coder_delta_guards, "coder_forbidden_paths", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(checks, "_run_cursor", fake_cursor)
    monkeypatch.setattr(checks, "_post_dispatch_forbidden_revert", lambda *_args, **_kwargs: 0)

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

    assert seen == ["implement.lint_fix_coder"]
    assert run_calls == ["cursor"]
    assert outcome.coder_tool == "cursor"


def test_review_fix_coder_uses_review_fix_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, review_and_fix, "review.fix_coder", ("codex", "cursor"))
    accepted = tmp_path / "accepted.md"
    accepted.write_text("### FINDING_1: fix\nBody\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    result_file = tmp_path / "coder.env"
    run_calls: list[str] = []

    def fake_ensure(target: Path) -> None:
        snap = review_and_fix.pre_coder_snapshot_dir(target)
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "pre-coder-head.txt").write_text("HEAD\n", encoding="utf-8")

    def fake_codex(**_kwargs: object) -> bool:
        run_calls.append("codex")
        return True

    def fake_scrub_findings(*, input_file: Path, output_file: Path, log_file: Path) -> tuple[bool, int]:
        _ = log_file
        output_file.write_text(input_file.read_text(encoding="utf-8"), encoding="utf-8")
        return True, 0

    monkeypatch.setattr(review_and_fix, "_scrub_findings", fake_scrub_findings)
    monkeypatch.setattr(review_and_fix, "_submodule_paths", lambda: ())
    monkeypatch.setattr(review_and_fix, "_compose_coder_prompt", lambda **_kwargs: "prompt")
    monkeypatch.setattr(review_and_fix, "_ensure_pre_coder_snapshot", fake_ensure)
    monkeypatch.setattr(review_and_fix, "_snapshot_mode", lambda _round_dir: "full")
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "HEAD")
    monkeypatch.setattr(review_and_fix, "_run_coder_codex", fake_codex)
    monkeypatch.setattr(review_and_fix, "_post_dispatch_submodule_revert", lambda **_kwargs: 0)
    monkeypatch.setattr(review_and_fix, "_collect_round_stage_paths", lambda *_args, **_kwargs: [])

    result = review_and_fix.apply_findings_with_coder(input_file=accepted, round_dir=round_dir, result_file=result_file)

    assert seen == ["review.fix_coder"]
    assert run_calls == ["codex"]
    assert result.tool == "codex"
    assert result.status == "no-changes"


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


def test_review_pipeline_panel_helpers_use_review_panel_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slots = (
        config.SlotDefault(slot="sentinel", tool="cursor", agent="agents/reviewer-testing.md", output="sentinel.out", archetype="testing"),
        config.SlotDefault(slot="generalist", tool="codex", agent="agents/code-reviewer.md", output="generic.out", focus_area="focus", weight=7, model_role="review", archetype="generic"),
    )
    seen_slots: list[str] = []
    seen_policy: list[str] = []

    def fake_slot_defaults(role_id: str, *_args: object, **_kwargs: object) -> tuple[config.SlotDefault, ...]:
        seen_slots.append(role_id)
        assert role_id == "review.panel"
        return slots

    def fake_panel_policy(role_id: str) -> config.PanelDispatchPolicy:
        seen_policy.append(role_id)
        assert role_id == "review.panel"
        return config.PanelDispatchPolicy(no_fallback_when_both_present_round_lt=9, generic_codex_rounds=frozenset({4}))

    monkeypatch.setattr(review_pipeline.external_defaults, "slot_defaults", fake_slot_defaults)
    monkeypatch.setattr(review_pipeline.external_defaults, "panel_dispatch_policy", fake_panel_policy)

    manifest = tmp_path / "manifest.ndjson"
    review_pipeline._append_static_specialist_rows(manifest=manifest, review_tmpdir=tmp_path, codex_slots_available=False)
    review_pipeline._append_round_generic_codex_row(manifest=manifest, review_tmpdir=tmp_path, round_num=4, codex_slots_available=True)

    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["slot"] == "sentinel"
    assert rows[1]["slot"] == "generalist"
    assert seen_slots == ["review.panel", "review.panel"]
    assert seen_policy == ["review.panel"]


def test_agent_voters_reload_consumes_review_voters_policies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = external_defaults.voter_policies

    def fake_voter_policies(role_id: str) -> tuple[config.VoterPolicyDefault, ...]:
        assert role_id == "review.voters"
        return (
            config.VoterPolicyDefault("1", "voter-1", "cursor", "sentinel-v1", "validity-correctness", "validity", "v1.out", (("cursor", "sentinel-v1"),)),
            config.VoterPolicyDefault("2", "voter-2", "cursor", "sentinel-v2", "plan-fidelity-completeness", "plan", "v2.out", (("cursor", "sentinel-v2"),)),
            config.VoterPolicyDefault("3", "voter-3", "codex", "sentinel-v3", "pragmatism-cost", "prag", "v3.out", (("codex", "sentinel-v3"),)),
        )

    monkeypatch.setattr(external_defaults, "voter_policies", fake_voter_policies)
    try:
        reloaded = importlib.reload(agent_voters)
        path2, path3, tool2, tool3 = reloaded._state_from_voter23_bindings(
            review_tmpdir=tmp_path,
            bindings={
                "voter-2": agent_waterfall.SlotOutputBinding(path="v2.txt", tool="cursor"),
                "voter-3": agent_waterfall.SlotOutputBinding(path="v3.txt", tool="codex"),
            },
        )
        assert (path2, path3, tool2, tool3) == ("v2.txt", "v3.txt", "sentinel-v2", "sentinel-v3")
    finally:
        monkeypatch.setattr(external_defaults, "voter_policies", original)
        importlib.reload(agent_voters)


def test_plan_review_panel_static_and_voter_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slots = (
        config.SlotDefault(slot="cursor-plan-sentinel", tool="cursor", output="cursor-sentinel.out", focus_area="sentinel", archetype="sentinel"),
        config.SlotDefault(slot="codex-plan-generic", tool="codex", output="generic.out", focus_area="generic", archetype="generic"),
    )
    seen_slots: list[str] = []
    seen_policy: list[str] = []

    def fake_slot_defaults(role_id: str, *_args: object, **_kwargs: object) -> tuple[config.SlotDefault, ...]:
        seen_slots.append(role_id)
        assert role_id == "design.plan_review_panel"
        return slots

    def fake_panel_policy(role_id: str) -> config.PanelDispatchPolicy:
        seen_policy.append(role_id)
        assert role_id == "design.plan_review_panel"
        return config.PanelDispatchPolicy(generic_codex_rounds=frozenset({3}))

    monkeypatch.setattr(plan_review_panel.external_defaults, "slot_defaults", fake_slot_defaults)
    monkeypatch.setattr(plan_review_panel.external_defaults, "panel_dispatch_policy", fake_panel_policy)
    monkeypatch.setattr(plan_review_panel.subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "prompt", ""))

    rows = plan_review_panel._static_slot_rows(
        design=tmp_path,
        round_dir=tmp_path,
        round_num=3,
        codex_present="false",
        cursor_present="true",
        plan_file=str(tmp_path / "plan.txt"),
        feature_file=str(tmp_path / "feature.txt"),
    )

    assert [row["slot"] for row in rows] == ["cursor-plan-sentinel", "codex-plan-generic"]
    assert seen_slots == ["design.plan_review_panel", "design.plan_review_panel"]
    assert seen_policy == ["design.plan_review_panel"]


def test_plan_review_voter_dispatch_uses_plan_voter_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policies = (
        config.VoterPolicyDefault("1", "voter-1", "claude", "claude", "validity-correctness", "claude", "claude-custom.txt", (("claude", "claude"),)),
        config.VoterPolicyDefault("2", "voter-2", "codex", "codex", "plan-fidelity-completeness", "codex", "codex-custom.txt", (("codex", "codex"),)),
        config.VoterPolicyDefault("3", "voter-3", "cursor", "cursor", "pragmatism-cost", "cursor", "cursor-custom.txt", (("cursor", "cursor"),)),
    )
    seen_policies: list[str] = []
    seen_dispatch: list[str] = []
    run_commands: list[list[str]] = []

    def fake_voter_policies(role_id: str) -> tuple[config.VoterPolicyDefault, ...]:
        seen_policies.append(role_id)
        assert role_id == "design.plan_voters"
        return policies

    def fake_dispatch_policy(role_id: str) -> config.VoterDispatchPolicy:
        seen_dispatch.append(role_id)
        assert role_id == "design.plan_voters"
        return config.VoterDispatchPolicy(voter_waterfall_no_fallback=True)

    class FakePopen:
        def __init__(self, cmd: list[str], **_kwargs: object) -> None:
            output = Path(cmd[cmd.index("--output") + 1])
            output.write_text("FINDING_1: YES\n", encoding="utf-8")
            Path(f"{output}.done").write_text("0\n", encoding="utf-8")

        def wait(self) -> int:
            return 0

    def fake_prompt(*, design: Path, tool: str, **_kwargs: object) -> Path:
        path = design / f"{tool}.prompt"
        path.write_text("prompt\n", encoding="utf-8")
        return path

    def fake_parse_rate(**_kwargs: object) -> str:
        return "OK"

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        run_commands.append(cmd)
        if "dispatch-waterfall" in cmd:
            manifest = Path(cmd[cmd.index("--slots-file") + 1])
            outputs = []
            tools = []
            for line in manifest.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                output = Path(row["output"])
                output.write_text("FINDING_1: YES\n", encoding="utf-8")
                outputs.append(str(output))
                tools.append(str(row["tool"]))
            return subprocess.CompletedProcess(cmd, 0, f"DISPATCH_OK=true\nALL_OUTPUT_FILES={' '.join(outputs)}\nALL_OUTPUT_TOOLS={' '.join(tools)}\n", "")
        if "effective-judges" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "3\n", "")
        if "voter-status-block" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "STATUS=ok\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: x\n", encoding="utf-8")
    monkeypatch.setattr(plan_review_panel.external_defaults, "voter_policies", fake_voter_policies)
    monkeypatch.setattr(plan_review_panel.external_defaults, "voter_dispatch_policy", fake_dispatch_policy)
    monkeypatch.setattr(plan_review_panel, "_make_voter_prompt", fake_prompt)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", fake_parse_rate)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(plan_review_panel.subprocess, "run", fake_run)

    rc = plan_review_panel.dispatch_voters(
        [
            "--ballot-file",
            str(ballot),
            "--design-tmpdir",
            str(tmp_path),
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
        ]
    )

    manifest = tmp_path / "plan-voter-slots.ndjson"
    manifest_rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert rc == 0
    assert [row["output"] for row in manifest_rows] == [str(tmp_path / "codex-custom.txt"), str(tmp_path / "cursor-custom.txt")]
    assert any("--no-fallback" in cmd for cmd in run_commands if "dispatch-waterfall" in cmd)
    assert seen_policies == ["design.plan_voters"]
    assert seen_dispatch == ["design.plan_voters"]


def test_review_aggregate_selects_code_and_plan_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_slot_defaults(role_id: str, *_args: object, **_kwargs: object) -> tuple[config.SlotDefault, ...]:
        seen.append(role_id)
        return (config.SlotDefault(slot=f"slot-{role_id}", tool="cursor", output="aggregator-output.txt"),)

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--slots-file" not in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        output = tmp_path / "aggregator-output.txt"
        output.write_text("### FINDING_1: merged\nBody\n\n### FINDING_2: merged\nBody\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, f"DISPATCH_OK=true\nALL_OUTPUT_FILES={output}\n", "")

    findings = tmp_path / "findings.md"
    findings.write_text("### FINDING_1: a\nBody\n\n### FINDING_2: b\nBody\n", encoding="utf-8")
    monkeypatch.setattr(review_aggregate.external_defaults, "slot_defaults", fake_slot_defaults)
    monkeypatch.setattr(review_aggregate.subprocess, "run", fake_run)
    monkeypatch.setattr(review_aggregate, "_apply_aggregate_candidate", lambda **_kwargs: (0, ""))
    monkeypatch.setattr(review_aggregate, "_split_plan_scope_blocks", lambda **_kwargs: (findings, None, 0))

    assert review_aggregate.aggregate_findings([
        "--findings-file", str(findings), "--review-tmpdir", str(tmp_path), "--codex-present", "true", "--cursor-present", "true", "--mode", "description", "--input-mode", "code",
    ]) == 0
    findings.write_text("### FINDING_1: a\nBody\n\n### FINDING_2: b\nBody\n", encoding="utf-8")
    assert review_aggregate.aggregate_findings([
        "--findings-file", str(findings), "--review-tmpdir", str(tmp_path), "--codex-present", "true", "--cursor-present", "true", "--mode", "description", "--input-mode", "plan",
    ]) == 0

    assert seen == ["review.findings_aggregator", "design.plan_findings_aggregator"]


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
