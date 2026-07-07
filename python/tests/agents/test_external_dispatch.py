# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from larch.agents import agent_voters
from larch.agents import _ci_launcher
from larch.agents import agent_waterfall
from larch.agents import agents
from larch.calibration import difficulty
from larch.state import bootstrap
from larch.implement import checks
from larch.implement import checks_lint_fix as _clf
from larch.implement import ci_monitor
from larch.design import decompose
from larch.core import external_defaults
from larch.review import plan_review_panel
from larch.design import plan_scout
from larch.git import rebase
from larch.review import review_aggregate
from larch.review import review_and_fix
from larch.review import coder_runner
from larch.review import review_pipeline
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

    monkeypatch.setattr(_clf, "_agent_cli", lambda: agent_cli)
    monkeypatch.setattr(_clf, "plugin_scripts_dir", lambda: tmp_path)
    monkeypatch.setattr(_clf, "_capture_tracked_paths", lambda *_args, **_kwargs: frozenset())
    monkeypatch.setattr(_clf, "_capture_untracked_paths", lambda *_args, **_kwargs: frozenset())
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

    assert seen == ["implement.lint_fix_coder"]
    assert run_calls == ["cursor"]
    assert outcome.coder_tool == "cursor"


def test_review_fix_coder_uses_review_fix_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, review_and_fix, "review.fix_coder", ("codex", "cursor", "claude"))
    accepted = tmp_path / "accepted.md"
    accepted.write_text("### FINDING_1: fix\nBody\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    result_file = tmp_path / "coder.env"
    run_calls: list[str] = []

    def fake_ensure(target: Path) -> None:
        snap = review_and_fix.pre_coder_snapshot_dir(target)
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "pre-coder-head.txt").write_text("HEAD\n", encoding="utf-8")

    def fake_coder(name: str) -> Any:
        def _inner(**_kwargs: object) -> bool:
            run_calls.append(name)
            return True
        return _inner

    stage_calls = [[], ["changed.py"]]

    def fake_collect_stage_paths(*_args: object, **_kwargs: object) -> list[str]:
        return stage_calls.pop(0)

    def fake_commit(*_args: object, **_kwargs: object) -> coder_runner.RoundCommitResult:
        return coder_runner.RoundCommitResult(sha="abc123")

    def fake_cleanup(_round_dir: Path) -> bool:
        return True

    def fake_scrub_findings(*, input_file: Path, output_file: Path, log_file: Path) -> tuple[bool, int]:
        _ = log_file
        output_file.write_text(input_file.read_text(encoding="utf-8"), encoding="utf-8")
        return True, 0

    monkeypatch.setattr(coder_runner, "_scrub_findings", fake_scrub_findings)
    monkeypatch.setattr(coder_runner, "_submodule_paths", lambda: ())
    monkeypatch.setattr(coder_runner, "_compose_coder_prompt", lambda **_kwargs: "prompt")
    monkeypatch.setattr(coder_runner, "_ensure_pre_coder_snapshot", fake_ensure)
    monkeypatch.setattr(coder_runner, "_snapshot_mode", lambda _round_dir: "full")
    monkeypatch.setattr(coder_runner, "_git_head", lambda: "HEAD")
    monkeypatch.setattr(coder_runner, "_run_coder_codex", fake_coder("codex"))
    monkeypatch.setattr(coder_runner, "_run_coder_cursor", fake_coder("cursor"))
    monkeypatch.setattr(coder_runner, "_run_coder_claude", fake_coder("claude"))
    monkeypatch.setattr(coder_runner, "_post_dispatch_submodule_revert", lambda **_kwargs: 0)
    monkeypatch.setattr(coder_runner, "_collect_round_stage_paths", fake_collect_stage_paths)
    monkeypatch.setattr(coder_runner, "_cleanup_failed_coder_attempt", fake_cleanup)
    monkeypatch.setattr(coder_runner, "_stage_and_commit_round", fake_commit)

    result = review_and_fix.apply_findings_with_coder(input_file=accepted, round_dir=round_dir, result_file=result_file, round_num=1)

    assert seen == ["review.fix_coder"]
    assert run_calls == ["codex", "cursor"]
    assert result.tool == "cursor"
    assert result.status == "applied"


def test_review_fix_coder_prompt_size_telemetry_allows_claude_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _tool_order_probe(monkeypatch, review_and_fix, "review.fix_coder", ("claude", "codex", "cursor"))
    accepted = tmp_path / "accepted.md"
    accepted.write_text("### FINDING_1: fix\nBody\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    result_file = tmp_path / "coder.env"
    telemetry_tools: list[str] = []

    def fake_ensure(target: Path) -> None:
        snap = review_and_fix.pre_coder_snapshot_dir(target)
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "pre-coder-head.txt").write_text("HEAD\n", encoding="utf-8")

    def fake_append_panel_prompt_size(**kwargs: object) -> None:
        telemetry_tools.append(str(kwargs["tool"]))

    def fake_scrub_findings(*, input_file: Path, output_file: Path, log_file: Path) -> tuple[bool, int]:
        _ = log_file
        output_file.write_text(input_file.read_text(encoding="utf-8"), encoding="utf-8")
        return True, 0

    monkeypatch.setattr(coder_runner, "_scrub_findings", fake_scrub_findings)
    monkeypatch.setattr(coder_runner, "_submodule_paths", lambda: ())
    monkeypatch.setattr(coder_runner, "_compose_coder_prompt", lambda **_kwargs: "prompt")
    monkeypatch.setattr(coder_runner, "_ensure_pre_coder_snapshot", fake_ensure)
    monkeypatch.setattr(coder_runner, "_snapshot_mode", lambda _round_dir: "full")
    monkeypatch.setattr(coder_runner, "_git_head", lambda: "HEAD")
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda **_kwargs: False)
    monkeypatch.setattr(coder_runner, "_run_coder_cursor", lambda **_kwargs: False)
    monkeypatch.setattr(coder_runner, "_run_coder_claude", lambda **_kwargs: True)
    monkeypatch.setattr(coder_runner, "_post_dispatch_submodule_revert", lambda **_kwargs: 0)
    monkeypatch.setattr(coder_runner, "_collect_round_stage_paths", lambda *_args, **_kwargs: ["changed.py"])
    monkeypatch.setattr(coder_runner, "append_panel_prompt_size", fake_append_panel_prompt_size)

    result = review_and_fix.apply_findings_with_coder(input_file=accepted, round_dir=round_dir, result_file=result_file)

    assert seen == ["review.fix_coder"]
    assert telemetry_tools == ["claude"]
    assert result.tool == "claude"
    assert result.status == "applied"


def test_review_fix_coder_attempts_claude_before_main_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _tool_order_probe(monkeypatch, review_and_fix, "review.fix_coder", ("codex", "cursor", "claude"))
    accepted = tmp_path / "accepted.md"
    accepted.write_text("### FINDING_1: fix\nBody\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    result_file = tmp_path / "coder.env"
    run_calls: list[str] = []

    def fake_ensure(target: Path) -> None:
        snap = review_and_fix.pre_coder_snapshot_dir(target)
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "pre-coder-head.txt").write_text("HEAD\n", encoding="utf-8")

    def fake_coder(name: str) -> Any:
        def _inner(**_kwargs: object) -> bool:
            run_calls.append(name)
            return True
        return _inner

    def fake_scrub_findings(*, input_file: Path, output_file: Path, log_file: Path) -> tuple[bool, int]:
        _ = log_file
        output_file.write_text(input_file.read_text(encoding="utf-8"), encoding="utf-8")
        return True, 0

    monkeypatch.setattr(coder_runner, "_scrub_findings", fake_scrub_findings)
    monkeypatch.setattr(coder_runner, "_submodule_paths", lambda: ())
    monkeypatch.setattr(coder_runner, "_compose_coder_prompt", lambda **_kwargs: "prompt")
    monkeypatch.setattr(coder_runner, "_ensure_pre_coder_snapshot", fake_ensure)
    monkeypatch.setattr(coder_runner, "_snapshot_mode", lambda _round_dir: "full")
    monkeypatch.setattr(coder_runner, "_git_head", lambda: "HEAD")
    monkeypatch.setattr(coder_runner, "_run_coder_codex", fake_coder("codex"))
    monkeypatch.setattr(coder_runner, "_run_coder_cursor", fake_coder("cursor"))
    monkeypatch.setattr(coder_runner, "_run_coder_claude", fake_coder("claude"))
    monkeypatch.setattr(coder_runner, "_post_dispatch_submodule_revert", lambda **_kwargs: 0)
    monkeypatch.setattr(coder_runner, "_collect_round_stage_paths", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(coder_runner, "_cleanup_failed_coder_attempt", lambda _round_dir: True)
    monkeypatch.setattr(coder_runner, "_record_main_agent_required_vendor_task", lambda _round_dir: tmp_path / "main-agent.log")

    result = review_and_fix.apply_findings_with_coder(input_file=accepted, round_dir=round_dir, result_file=result_file)

    assert seen == ["review.fix_coder"]
    assert run_calls == ["codex", "cursor", "claude"]
    assert result.tool == "none"
    assert result.status == "main-agent-required"


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
        return config.PanelDispatchPolicy()

    monkeypatch.setattr(review_pipeline.external_defaults, "slot_defaults", fake_slot_defaults)
    monkeypatch.setattr(review_pipeline.external_defaults, "panel_dispatch_policy", fake_panel_policy)

    manifest = tmp_path / "manifest.ndjson"
    review_pipeline._append_static_specialist_rows(manifest=manifest, review_tmpdir=tmp_path, codex_slots_available=False, cursor_slots_available=True, tier=difficulty.MODERATE)
    review_pipeline._append_round_generic_codex_row(manifest=manifest, review_tmpdir=tmp_path, round_num=4, codex_slots_available=True)

    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert [row["slot"] for row in rows] == ["sentinel"]
    assert seen_slots == ["review.panel"]
    assert seen_policy == ["review.panel"]


def test_agent_waterfall_cursor_model_row_validation_and_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cursor_row = json.dumps(
        {
            "slot": "plan-fidelity-auto",
            "tool": "cursor",
            "output": str(tmp_path / "out.txt"),
            "prompt_file": str(tmp_path / "prompt.txt"),
            "cursor_model": "auto",
        }
    )
    slot = agent_waterfall._parse_slot_row(cursor_row)  # pyright: ignore[reportPrivateUsage]
    assert slot.cursor_model == "auto"
    assert slot.tool == "cursor"

    for invalid_row in (
        {**json.loads(cursor_row), "cursor_model": ""},
        {**json.loads(cursor_row), "cursor_model": "bad\nmodel"},
        {**json.loads(cursor_row), "tool": "codex", "cursor_model": "auto"},
    ):
        with pytest.raises(agent_waterfall.ValidationError):
            agent_waterfall._parse_slot_row(json.dumps(invalid_row))  # pyright: ignore[reportPrivateUsage]

    captured_argv: list[str] = []

    class _FakePopen:
        def __init__(self, argv: list[str], **_kwargs: object) -> None:
            captured_argv.extend(argv)
            self.pid = 1234

    prompt = tmp_path / "prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(agent_waterfall, "_ACTIVE_LAUNCHES", [])
    monkeypatch.setattr(agent_waterfall, "_DISPATCH_LAUNCHES", [])
    opts = agent_waterfall.Options(
        slots_file=str(tmp_path / "slots.ndjson"),
        codex_present=True,
        cursor_present=True,
        mode="diff",
    )

    agent_waterfall._launch_slot(  # pyright: ignore[reportPrivateUsage]
        idx=0,
        phase="phase1",
        tool="cursor",
        output=str(tmp_path / "out.txt"),
        slots=[slot],
        opts=opts,
    )

    assert captured_argv[captured_argv.index("--cursor-model") + 1] == "auto"


def test_agent_voters_reload_consumes_review_voters_policies(monkeypatch: pytest.MonkeyPatch) -> None:
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
        state = reloaded._state_from_bindings(
            bindings={
                "voter-2": agent_waterfall.SlotOutputBinding(path="v2.txt", tool="cursor"),
                "voter-3": agent_waterfall.SlotOutputBinding(path="v3.txt", tool="codex"),
            },
            launched_policies=reloaded.VOTER_SLOT_POLICIES,
        )
        assert (state.voter_2_path, state.voter_3_path, state.voter_2_tool, state.voter_3_tool) == ("v2.txt", "v3.txt", "sentinel-v2", "sentinel-v3")
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
        return config.PanelDispatchPolicy()

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

    assert [row["slot"] for row in rows] == ["cursor-plan-sentinel"]
    assert seen_slots == ["design.plan_review_panel"]
    assert seen_policy == ["design.plan_review_panel"]


def test_plan_review_panel_static_rows_zero_payload_on_render_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slots = (
        config.SlotDefault(slot="cursor-plan-sentinel", tool="cursor", output="cursor-sentinel.out", focus_area="sentinel", archetype="sentinel"),
    )
    calls = {"count": 0}

    def fake_slot_defaults(role_id: str, *_args: object, **_kwargs: object) -> tuple[config.SlotDefault, ...]:
        assert role_id == "design.plan_review_panel"
        return slots

    def fake_panel_policy(role_id: str) -> config.PanelDispatchPolicy:
        assert role_id == "design.plan_review_panel"
        return config.PanelDispatchPolicy()

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        payload_sidecar = Path(argv[argv.index("--payload-bytes-output") + 1])
        calls["count"] += 1
        if calls["count"] == 1:
            payload_sidecar.write_text("41\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "prompt", "")
        return subprocess.CompletedProcess(argv, 1, "", "render failed")

    monkeypatch.setattr(plan_review_panel.external_defaults, "slot_defaults", fake_slot_defaults)
    monkeypatch.setattr(plan_review_panel.external_defaults, "panel_dispatch_policy", fake_panel_policy)
    monkeypatch.setattr(plan_review_panel.subprocess, "run", fake_run)

    first = plan_review_panel._static_slot_rows(  # pyright: ignore[reportPrivateUsage]
        design=tmp_path,
        round_dir=tmp_path,
        round_num=3,
        codex_present="false",
        cursor_present="true",
        plan_file=str(tmp_path / "plan.txt"),
        feature_file=str(tmp_path / "feature.txt"),
    )
    second = plan_review_panel._static_slot_rows(  # pyright: ignore[reportPrivateUsage]
        design=tmp_path,
        round_dir=tmp_path,
        round_num=3,
        codex_present="false",
        cursor_present="true",
        plan_file=str(tmp_path / "plan.txt"),
        feature_file=str(tmp_path / "feature.txt"),
    )

    assert first[0]["payload_bytes"] == 41
    assert second[0].get("payload_bytes", 0) == 0
    assert (tmp_path / "render-plan-cursor-sentinel.prompt").read_text(encoding="utf-8") == (
        "Review the design plan with a sentinel lens."
    )


def test_plan_review_voter_dispatch_uses_plan_voter_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policies = (
        config.VoterPolicyDefault("1", "voter-1", "codex", "codex-validity", "validity-correctness", "validity", "codex-validity-custom.txt", (("codex", "codex-validity"), ("cursor", "cursor-validity"), ("claude", "claude"))),
        config.VoterPolicyDefault("2", "voter-2", "codex", "codex-plan-fidelity", "plan-fidelity-completeness", "plan-fidelity", "codex-plan-fidelity-custom.txt", (("codex", "codex-plan-fidelity"), ("cursor", "cursor-plan-fidelity"), ("claude", "claude"))),
        config.VoterPolicyDefault("3", "voter-3", "codex", "codex-pragmatism", "pragmatism-cost", "pragmatism", "codex-pragmatism-custom.txt", (("codex", "codex-pragmatism"), ("cursor", "cursor-pragmatism"), ("claude", "claude"))),
    )
    seen_policies: list[str] = []
    run_commands: list[list[str]] = []

    def fake_voter_policies(role_id: str) -> tuple[config.VoterPolicyDefault, ...]:
        seen_policies.append(role_id)
        assert role_id == "design.plan_voters"
        return policies

    class FakePopen:
        def __init__(self, cmd: list[str], **_kwargs: object) -> None:
            output = Path(cmd[cmd.index("--output") + 1])
            output.write_text("FINDING_1: YES\n", encoding="utf-8")
            Path(f"{output}.done").write_text("0\n", encoding="utf-8")

        def wait(self) -> int:
            return 0

    def fake_prompt(*, design: Path, tool: str, **_kwargs: object) -> plan_review_panel.VoterPromptResult:
        path = design / f"{tool}.prompt"
        path.write_text("prompt\n", encoding="utf-8")
        return plan_review_panel.VoterPromptResult(prompt_file=path)

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
            "--round-num",
            "1",
        ]
    )

    manifest = tmp_path / "plan-voter-slots.ndjson"
    manifest_rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert rc == 0
    assert [row["output"] for row in manifest_rows] == [
        str(tmp_path / "codex-validity-custom.txt"),
        str(tmp_path / "codex-plan-fidelity-custom.txt"),
        str(tmp_path / "codex-pragmatism-custom.txt"),
    ]
    # issue #5817: plan voters waterfall fully; the dispatch no longer injects --no-fallback.
    assert not any("--no-fallback" in cmd for cmd in run_commands if "dispatch-waterfall" in cmd)
    assert seen_policies == ["design.plan_voters"]


def test_review_aggregate_selects_code_and_plan_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    slot_rows: list[dict[str, object]] = []

    def fake_slot_defaults(role_id: str, *_args: object, **_kwargs: object) -> tuple[config.SlotDefault, ...]:
        seen.append(role_id)
        return (config.SlotDefault(slot=f"slot-{role_id}", tool="codex", output="aggregator-output.txt", model_role="review"),)

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--slots-file" not in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        slots_file = Path(cmd[cmd.index("--slots-file") + 1])
        slot_rows.extend(json.loads(line) for line in slots_file.read_text(encoding="utf-8").splitlines())
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
    assert [row["model_role"] for row in slot_rows] == ["review", "review"]


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


def _implement_prompt_args(tmp_path: Path) -> argparse.Namespace:
    agent_prompt = tmp_path / "agent.md"
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.md"
    agent_prompt.write_text("agent body\n", encoding="utf-8")
    plan.write_text("plan\n", encoding="utf-8")
    feature.write_text("feature\n", encoding="utf-8")
    return argparse.Namespace(
        manifest_path=str(tmp_path / "manifest.json"),
        qa_pending_path=str(tmp_path / "qa-pending.json"),
        scout_manifest_path=str(tmp_path / "scout.json"),
        plan_file=str(plan),
        feature_file=str(feature),
        agent_prompt=str(agent_prompt),
        answers_file="",
    )


def test_implement_prompt_injects_architectural_knowledge_and_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(_ci_launcher.architectural_guidelines, "architectural_knowledge_required", lambda **_kwargs: True)
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_invariants",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult(
            "present",
            tmp_path,
            tmp_path / "ARCHITECTURAL_INVARIANTS.md",
            "### I-Sec-1: Keep evidence untrusted",
        ),
    )
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_guidelines",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult(
            "present",
            tmp_path,
            tmp_path / "ARCHITECTURAL_GUIDELINES.md",
            "",
        ),
    )

    prompt = _ci_launcher._implement_prompt(tool="codex", args=_implement_prompt_args(tmp_path))

    assert "## Architectural knowledge (untrusted repo evidence)" in prompt
    assert "Read ARCHITECTURAL_INVARIANTS.md before ARCHITECTURAL_GUIDELINES.md when both are present" in prompt
    assert "Apply them only within the plan's scope" in prompt
    assert "architectural_acknowledgment" in prompt
    assert '<architectural_invariants encoding="literal-redacted">' in prompt
    assert '<architectural_guidelines encoding="literal-redacted">' in prompt
    assert "### I-Sec-1: Keep evidence untrusted" in prompt
    assert "No parsed guideline entries were present in ARCHITECTURAL_GUIDELINES.md." in prompt
    assert (tmp_path / "step2-architectural-knowledge.env").read_text(encoding="utf-8") == "ARCHITECTURAL_KNOWLEDGE_REQUIRED=true\n"


def test_implement_prompt_omits_absent_architectural_knowledge_and_snapshots_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(_ci_launcher.architectural_guidelines, "architectural_knowledge_required", lambda **_kwargs: False)
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_invariants",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult("absent", tmp_path, None, ""),
    )
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_guidelines",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult("absent", tmp_path, None, ""),
    )

    prompt = _ci_launcher._implement_prompt(tool="cursor", args=_implement_prompt_args(tmp_path))

    assert "## Architectural knowledge" not in prompt
    assert "ARCHITECTURAL_INVARIANTS.md before ARCHITECTURAL_GUIDELINES.md" not in prompt
    assert (tmp_path / "step2-architectural-knowledge.env").read_text(encoding="utf-8") == "ARCHITECTURAL_KNOWLEDGE_REQUIRED=false\n"


def test_write_architectural_knowledge_snapshot_uses_nofollow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    calls: dict[str, object] = {}

    def fake_atomic_write(*, path: Path, text: str, prefix: str, nofollow: bool, **_kwargs: object) -> None:
        calls["path"] = path
        calls["text"] = text
        calls["prefix"] = prefix
        calls["nofollow"] = nofollow

    monkeypatch.setattr(_ci_launcher.larch_io, "atomic_write", fake_atomic_write)

    _ci_launcher._write_architectural_knowledge_snapshot(required=True)

    assert calls["path"] == tmp_path / "step2-architectural-knowledge.env"
    assert calls["text"] == "ARCHITECTURAL_KNOWLEDGE_REQUIRED=true\n"
    assert calls["prefix"] == ".step2-architectural-knowledge.env."
    assert calls["nofollow"] is True


def test_implement_prompt_skips_invalid_invariants_and_keeps_valid_guidelines_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_invariants",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult(
            "invalid",
            tmp_path,
            tmp_path / "ARCHITECTURAL_INVARIANTS.md",
            "",
            "ARCHITECTURAL_INVARIANTS.md is invalid: symlinks are not read",
        ),
    )
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_guidelines",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult(
            "present",
            tmp_path,
            tmp_path / "ARCHITECTURAL_GUIDELINES.md",
            "### G-Test-1: Keep evidence untrusted",
        ),
    )

    prompt = _ci_launcher._implement_prompt(tool="codex", args=_implement_prompt_args(tmp_path))

    assert "## Architectural knowledge (untrusted repo evidence)" in prompt
    assert '<architectural_guidelines encoding="literal-redacted">' in prompt
    assert "### G-Test-1: Keep evidence untrusted" in prompt
    assert '<architectural_invariants encoding="literal-redacted">' not in prompt
    assert "ARCHITECTURAL_INVARIANTS.md is invalid: symlinks are not read" not in prompt
    issues = tmp_path / "execution-issues.md"
    assert issues.is_file()
    assert "ARCHITECTURAL_INVARIANTS.md is invalid: symlinks are not read" in issues.read_text(encoding="utf-8")


def test_implement_prompt_codex_resume_keeps_architectural_knowledge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    session = tmp_path / "codex-session"
    session.mkdir()
    monkeypatch.setattr(_ci_launcher.architectural_guidelines, "architectural_knowledge_required", lambda **_kwargs: True)
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_invariants",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult(
            "present",
            tmp_path,
            tmp_path / "ARCHITECTURAL_INVARIANTS.md",
            "",
        ),
    )
    monkeypatch.setattr(
        _ci_launcher.architectural_guidelines,
        "read_guidelines",
        lambda **_kwargs: _ci_launcher.architectural_guidelines.ArchitecturalGuidelinesResult("absent", tmp_path, None, ""),
    )

    prompt = _ci_launcher._implement_prompt(tool="codex", args=_implement_prompt_args(tmp_path), codex_session=session)

    assert "agent body" not in prompt
    assert "## Architectural knowledge (untrusted repo evidence)" in prompt
    assert "No parsed invariant entries were present in ARCHITECTURAL_INVARIANTS.md." in prompt
