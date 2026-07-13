"""Focused contracts for shared panel and voter dispatch helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from collections.abc import Sequence

import pytest

from larch.agents import _launch_failure, agent_voters, agent_waterfall
from larch.core import config, proc
from larch.review import _voting_calibration, dispatch_shared, plan_review_panel, voting


def _result(argv: Sequence[str], returncode: int = 0, stdout: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, "", 0.0)


def test_model_resolution_normalizes_roles_and_preserves_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_resolve(tool: str, *, with_effort: bool, default_model: str, codex_role: str) -> SimpleNamespace:
        assert with_effort is (tool == "codex")
        calls.append((tool, codex_role, default_model))
        flag = "--model" if tool == "cursor" else "-m"
        return SimpleNamespace(argv=(flag, default_model or f"{tool}-{codex_role}"))

    monkeypatch.setattr(_launch_failure, "resolve_model_args", fake_resolve)
    assert dispatch_shared.resolved_model_for_row("cursor") == "cursor-default"
    for role in ("default", "review", "vote", "fix"):
        assert dispatch_shared.resolved_model_for_row("codex", role) == f"codex-{role}"
    assert dispatch_shared.resolved_model_for_row("codex", "unsupported") == "codex-default"
    assert dispatch_shared.resolved_model_for_row("codex", "vote", "tier-model") == "tier-model"
    assert calls[-1] == ("codex", "vote", "tier-model")


def test_model_resolution_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise ValueError("bad role")

    monkeypatch.setattr(_launch_failure, "resolve_model_args", fail_resolve)
    assert dispatch_shared.resolved_model_for_row("codex", "vote") == "unknown"


def test_topology_builders_preserve_slot_and_policy_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    slot = config.SlotDefault(slot="slot", tool="cursor", output="out", focus_area="correctness", weight=2)
    policy = config.VoterPolicyDefault(
        "1",
        "voter-1",
        "codex",
        "validity",
        "validity-correctness",
        "validity",
        "vote.txt",
        (("codex", "codex-validity"),),
    )
    def fake_slots(key: str) -> tuple[config.SlotDefault, ...]:
        return (slot,) if key == "review.panel" else ()

    def fake_policies(key: str) -> tuple[config.VoterPolicyDefault, ...]:
        return (policy,) if key == "review.voters" else ()

    monkeypatch.setattr(dispatch_shared.external_defaults, "slot_defaults", fake_slots)
    monkeypatch.setattr(dispatch_shared.external_defaults, "voter_policies", fake_policies)
    assert dispatch_shared.topology_slots("review.panel") == (slot,)
    built = dispatch_shared.topology_voter_policies("review.voters")
    assert built[0].slot_name == "voter-1"
    assert built[0].semantic_labels == (("codex", "codex-validity"),)


def test_dispatch_state_and_path_wire_preserve_absence(tmp_path: Path) -> None:
    vote = tmp_path / "vote.txt"
    state = dispatch_shared.DispatchState(voter_1_path=vote, voter_2_path=None)
    assert state.voter_1_path == vote
    assert dispatch_shared.path_for_wire(state.voter_2_path) == ""
    assert dispatch_shared.path_for_wire(None) != "."


def test_code_review_binding_absence_is_none() -> None:
    policies = agent_voters.VOTER_SLOT_POLICIES
    state = agent_voters._state_from_bindings(  # pyright: ignore[reportPrivateUsage]
        bindings={"voter-1": agent_waterfall.SlotOutputBinding(dropped=True)},
        launched_policies=policies[:1],
    )
    assert state.voter_1_path is None
    assert state.voter_2_path is None
    assert state.voter_3_path is None
    assert state.voter_2_status == "skipped"


def test_plan_review_binding_absence_keeps_placeholder_paths(tmp_path: Path) -> None:
    policies = dispatch_shared.topology_voter_policies("design.plan_voters")
    state = plan_review_panel._state_from_bindings(  # pyright: ignore[reportPrivateUsage]
        design=tmp_path,
        policies=policies,
        bindings={},
        launched_policies=policies[:1],
    )
    assert state.voter_1_path == tmp_path / policies[0].output_name
    assert state.voter_2_path == tmp_path / policies[1].output_name
    assert state.voter_1_status == "failed"
    assert state.voter_2_status == "skipped"


def test_manifest_attribution_uses_explicit_role_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str, str]] = []

    def fake_model(tool: str, model_role: str = "", default_model: str = "") -> str:
        seen.append((tool, model_role, default_model))
        return "resolved"

    monkeypatch.setattr(dispatch_shared, "_resolved_model_for_row", fake_model)  # pyright: ignore[reportPrivateUsage]  # exercises the canonical resolver seam
    row = dispatch_shared.with_manifest_attribution(
        {"tool": "codex", "slot": "arch"},
        model_role="review",
        default_model="tier-model",
    )
    assert row["vendor"] == "codex"
    assert row["model_role"] == "review"
    assert row["resolved_model"] == "resolved"
    assert seen == [("codex", "review", "tier-model")]


def test_calibration_snapshot_opt_out_removes_stale_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "voter-calibration-stats.tsv"
    _ = target.write_text("stale\n", encoding="utf-8")
    monkeypatch.setenv(config.ENV_LARCH_VOTER_CALIBRATION_FEEDBACK, "0")
    called = False

    def runner(_argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        nonlocal called
        called = True
        return _result(())

    assert dispatch_shared.fresh_calibration_snapshot(
        work_dir=tmp_path,
        snapshot_argv=["snapshot"],
        runner=runner,
        review_tmpdir=tmp_path,
    ) is None
    assert not target.exists()
    assert not called


@pytest.mark.parametrize(("family", "expected_arg"), [("design", "design_tmpdir"), ("review", "review_tmpdir")])
def test_calibration_snapshot_forwards_family_log_root_and_replaces_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    expected_arg: str,
) -> None:
    captured: dict[str, Path | None] = {}

    def resolve_root(*, design_tmpdir: Path | None, review_tmpdir: Path | None) -> Path:
        captured["design_tmpdir"] = design_tmpdir
        captured["review_tmpdir"] = review_tmpdir
        return tmp_path / "logs"

    def runner(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        _ = Path(argv[argv.index("--out") + 1]).write_text("tool\tyes\n", encoding="utf-8")
        assert argv[argv.index("--log-root") + 1] == str(tmp_path / "logs")
        return _result(argv)

    monkeypatch.setenv(config.ENV_LARCH_VOTER_CALIBRATION_FEEDBACK, "1")
    monkeypatch.setattr(_voting_calibration, "_resolve_voter_calibration_log_root", resolve_root)
    if family == "design":
        result = dispatch_shared.fresh_calibration_snapshot(
            work_dir=tmp_path,
            snapshot_argv=["snapshot"],
            runner=runner,
            design_tmpdir=tmp_path,
        )
    else:
        result = dispatch_shared.fresh_calibration_snapshot(
            work_dir=tmp_path,
            snapshot_argv=["snapshot"],
            runner=runner,
            review_tmpdir=tmp_path,
        )
    assert result == str(tmp_path / "voter-calibration-stats.tsv")
    assert captured[expected_arg] == tmp_path
    assert not list(tmp_path.glob(".voter-calibration-stats.*"))


@pytest.mark.parametrize(("returncode", "write_text"), [(1, "data\n"), (0, "")])
def test_calibration_snapshot_failure_or_empty_cleans_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    write_text: str,
) -> None:
    monkeypatch.setenv(config.ENV_LARCH_VOTER_CALIBRATION_FEEDBACK, "1")
    def resolve_root(**_kwargs: Path | None) -> Path:
        return tmp_path / "logs"

    monkeypatch.setattr(_voting_calibration, "_resolve_voter_calibration_log_root", resolve_root)

    def runner(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        _ = Path(argv[argv.index("--out") + 1]).write_text(write_text, encoding="utf-8")
        return _result(argv, returncode)

    assert dispatch_shared.fresh_calibration_snapshot(
        work_dir=tmp_path,
        snapshot_argv=["snapshot"],
        runner=runner,
        review_tmpdir=tmp_path,
    ) is None
    assert not list(tmp_path.glob(".voter-calibration-stats.*"))


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [
        (0, "OK\n", "OK"),
        (0, "diagnostic\nNOT_SUBSTANTIVE\n", "NOT_SUBSTANTIVE"),
        (0, "", "NOT_SUBSTANTIVE"),
        (0, "UNKNOWN\n", "NOT_SUBSTANTIVE"),
        (1, "OK\n", "NOT_SUBSTANTIVE"),
    ],
)
def test_parse_rate_validation_uses_final_nonempty_line(
    returncode: int,
    stdout: str,
    expected: str,
) -> None:
    def runner(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        return _result(argv, returncode, stdout)

    assert dispatch_shared.validate_parse_rate_result(["parse"], runner=runner) == expected


def _state(tmp_path: Path) -> dispatch_shared.DispatchState:
    return dispatch_shared.DispatchState(
        voter_1_path=tmp_path / "one",
        voter_2_path=None,
        voter_3_path=tmp_path / "three",
        voter_1_tool="one-tool",
        voter_2_tool="two-tool",
        voter_3_tool="three-tool",
    )


def test_final_emitter_uses_logging_and_code_review_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []

    def capture(*, key: str, value: str) -> None:
        emitted.append((key, value))

    monkeypatch.setattr(dispatch_shared.logging_util, "emit_kv", capture)
    dispatch_shared.emit_final_voter_kvs(
        state=_state(tmp_path),
        voter_paths_file=tmp_path / "missing-paths",
        dispatch_ok="true",
        row_layout="code_review_sequential",
        paths_file_policy="always",
    )
    assert [key for key, _value in emitted] == [
        "VOTER_1_PATH", "VOTER_1_TOOL", "VOTER_1_STATUS", "VOTER_1_PARSE_RATE_STATUS",
        "VOTER_2_PATH", "VOTER_2_TOOL", "VOTER_2_STATUS", "VOTER_2_PARSE_RATE_STATUS",
        "VOTER_3_PATH", "VOTER_3_TOOL", "VOTER_3_STATUS", "VOTER_3_PARSE_RATE_STATUS",
        "VOTER_PATHS_FILE", "DISPATCH_OK",
    ]
    assert dict(emitted)["VOTER_2_PATH"] == ""


def test_plan_review_interleaved_order_omits_empty_paths_file(tmp_path: Path) -> None:
    paths_file = tmp_path / "paths"
    _ = paths_file.write_text("", encoding="utf-8")
    rows = voting.build_voter_status_rows(
        voters=(("one", "one-tool", "launched", "OK"), ("two", "two-tool", "failed", "SKIPPED"), ("three", "three-tool", "launched", "OK")),
        voter_paths_file=str(paths_file),
        row_layout="plan_review_interleaved",
        paths_file_policy="nonempty",
    )
    assert [key for key, _value in rows] == [
        "VOTER_1_PATH", "VOTER_1_TOOL", "VOTER_1_STATUS", "VOTER_1_PARSE_RATE_STATUS",
        "VOTER_2_PATH", "VOTER_3_PATH", "VOTER_2_TOOL", "VOTER_3_TOOL",
        "VOTER_2_STATUS", "VOTER_3_STATUS", "VOTER_2_PARSE_RATE_STATUS", "VOTER_3_PARSE_RATE_STATUS",
    ]


def test_plan_trailing_kvs_use_logging_contract_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []

    def capture(*, key: str, value: str) -> None:
        emitted.append((key, value))

    monkeypatch.setattr(plan_review_panel.logging_util, "emit_kv", capture)
    plan_review_panel._emit(key="VOTER_1_RETRIED", value="false")  # pyright: ignore[reportPrivateUsage]
    plan_review_panel._emit(key="DEGRADED_PANEL", value="1")  # pyright: ignore[reportPrivateUsage]
    assert emitted == [("VOTER_1_RETRIED", "false"), ("DEGRADED_PANEL", "1")]
