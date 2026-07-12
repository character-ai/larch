# pyright: reportPrivateUsage=false
from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.implement import ci_fixer_adapter

if TYPE_CHECKING:
    from larch.bgjob import model


def _fixed_launch(
    launch: ci_fixer_adapter.Launch,
) -> Callable[[ci_fixer_adapter.Context], ci_fixer_adapter.Launch]:
    def fake_new_launch(_context: ci_fixer_adapter.Context) -> ci_fixer_adapter.Launch:
        return launch

    return fake_new_launch


def _fixed_head(
    _context: ci_fixer_adapter.Context,
    *_args: str,
    reason: str,
) -> str:
    _ = reason
    return "c" * 40


def _context(tmp_path: Path) -> ci_fixer_adapter.Context:
    impl = tmp_path / "impl"
    impl.mkdir()
    handoff = impl / "ci-fixer"
    handoff.mkdir()
    bgjob = impl / "bgjob"
    bgjob.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    return ci_fixer_adapter.Context(impl, handoff, bgjob, repo, "owner/repo")


def _launch(context: ci_fixer_adapter.Context) -> ci_fixer_adapter.Launch:
    return ci_fixer_adapter.Launch(
        mode="ci",
        run_id="42",
        starting_head="a" * 40,
        input_fingerprint="b" * 64,
        tier="codex",
        attempt=1,
        step="implement-step8-ci-fixer-1-codex-deadbeefdeadbeef",
        lineage=context.handoff_dir / "lineage.tsv",
    )


def _write_launch(context: ci_fixer_adapter.Context, launch: ci_fixer_adapter.Launch) -> None:
    _ = (context.handoff_dir / f"launch-{launch.step}.env").write_text(
        "".join(f"{key}={value}\n" for key, value in launch.rows()),
        encoding="utf-8",
    )


def _fixed_identity(_context: ci_fixer_adapter.Context) -> tuple[str, str]:
    return "a" * 40, "b" * 64


def _fixed_route(_context: ci_fixer_adapter.Context) -> tuple[str, str]:
    return "ci", "42"


def _tool_path(_tool: str) -> str:
    return "/bin/tool"


def test_invalid_mode_keeps_operator_bail_grammar(capsys: pytest.CaptureFixture[str]) -> None:
    assert ci_fixer_adapter.main(["--unknown"]) == 0
    assert capsys.readouterr().out == "RESULT=operator-bail\nREASON=invalid-mode\n"


def test_child_rejects_disagreeing_result_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _ = (impl / "session-env.sh").write_text(f"REPO_ROOT={repo}\n", encoding="utf-8")
    _ = (impl / "ship-pr-state.sh").write_text("REPO=owner/repo\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    assert ci_fixer_adapter.main([
        "--start",
        "--step", "implement-step8-ci-fixer-1-codex-deadbeefdeadbeef",
        "--bgjob-child",
        "--merge-result-env", str(impl / "bgjob" / "left.env"),
        "--bgjob-result-env", str(impl / "bgjob" / "right.env"),
    ]) == 0
    assert "RESULT=operator-bail" in capsys.readouterr().out


def test_start_translates_adapter_done_to_legacy_started(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    context = _context(tmp_path)
    launch = _launch(context)
    captured: list[model.JobSpec] = []
    monkeypatch.delenv("LARCH_CLAUDE_PID", raising=False)
    monkeypatch.setattr(ci_fixer_adapter, "_new_launch", _fixed_launch(launch))

    def fake_adapt(spec: model.JobSpec) -> int:
        captured.append(spec)
        print("BGJOB_STATUS=DONE")
        return 0

    monkeypatch.setattr(ci_fixer_adapter.adapt, "start_or_reattach", fake_adapt)

    assert ci_fixer_adapter._start(context) == 0
    out = capsys.readouterr().out
    assert out.startswith("BGJOB_STATUS=STARTED\n")
    assert "BGJOB_STATUS=DONE" not in out
    assert captured[0].merge_result_env == context.bgjob_dir / f"{launch.step}.merge.env"


def test_finalize_records_lineage_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    launch = _launch(context)
    _write_launch(context, launch)
    _ = (context.bgjob_dir / f"{launch.step}.result.env").write_text(
        f"STEP={launch.step}\nBGJOB_RC=0\nBGJOB_ELAPSED_S=3\n",
        encoding="utf-8",
    )
    final_rows = {
        **dict(launch.rows()),
        "RESULT": "retry-next-tool",
        "REASON": "no-progress",
        "FINAL_HEAD": "c" * 40,
    }
    final_text = "".join(f"{key}={value}\n" for key, value in final_rows.items())
    _ = (context.bgjob_dir / f"{launch.step}.merge.env").write_text(final_text, encoding="utf-8")
    _ = (context.handoff_dir / "fixer-status.env").write_text(final_text, encoding="utf-8")
    monkeypatch.setattr(ci_fixer_adapter, "_git_text", _fixed_head)

    assert ci_fixer_adapter._finalize(context, launch.step) == 0
    assert ci_fixer_adapter._finalize(context, launch.step) == 0
    assert len(launch.lineage.read_text(encoding="utf-8").splitlines()) == 1


def test_child_accepts_matching_result_path_and_forwards_lane_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    launch = _launch(context)
    _write_launch(context, launch)
    merge = context.bgjob_dir / f"{launch.step}.merge.env"
    captured: list[list[str]] = []

    def fake_lane(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    monkeypatch.setattr(ci_fixer_adapter.ci_fixer_lane, "main", fake_lane)
    args = argparse.Namespace(
        step=launch.step,
        merge_result_env=str(merge),
        bgjob_result_env=str(merge),
    )

    assert ci_fixer_adapter._child(context, args) == 0
    assert captured[0][captured[0].index("--bgjob-result-env") + 1] == str(merge)


def test_finalize_missing_result_fails_closed(tmp_path: Path) -> None:
    context = _context(tmp_path)
    launch = _launch(context)
    _write_launch(context, launch)

    with pytest.raises(ci_fixer_adapter.CiFixerAdapterError, match="missing-bgjob-result"):
        _ = ci_fixer_adapter._finalize(context, launch.step)


def test_finalize_rejects_final_head_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    launch = _launch(context)
    _write_launch(context, launch)
    _ = (context.bgjob_dir / f"{launch.step}.result.env").write_text(
        f"STEP={launch.step}\nBGJOB_RC=0\nBGJOB_ELAPSED_S=3\n",
        encoding="utf-8",
    )
    rows = {
        **dict(launch.rows()),
        "RESULT": "retry-next-tool",
        "REASON": "no-progress",
        "FINAL_HEAD": "c" * 40,
    }
    text = "".join(f"{key}={value}\n" for key, value in rows.items())
    _ = (context.bgjob_dir / f"{launch.step}.merge.env").write_text(text, encoding="utf-8")
    _ = (context.handoff_dir / "fixer-status.env").write_text(text, encoding="utf-8")

    def live_head(
        _context: ci_fixer_adapter.Context,
        *_args: str,
        reason: str,
    ) -> str:
        _ = reason
        return "d" * 40

    monkeypatch.setattr(ci_fixer_adapter, "_git_text", live_head)

    with pytest.raises(ci_fixer_adapter.CiFixerAdapterError, match="final-head-drift"):
        _ = ci_fixer_adapter._finalize(context, launch.step)


def test_launch_envelope_under_symlink_is_rejected(tmp_path: Path) -> None:
    context = _context(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = context.handoff_dir / "nested"
    _ = linked.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ci_fixer_adapter.CiFixerAdapterError, match="unsafe-launch-envelope"):
        _ = ci_fixer_adapter._safe_file(
            linked / "launch.env",
            root=context.handoff_dir,
            reason="unsafe-launch-envelope",
        )


def test_duplicate_uppercase_env_key_routes_to_operator_bail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _ = (impl / "session-env.sh").write_text(
        f"REPO_ROOT={repo}\nREPO_ROOT={repo}\n",
        encoding="utf-8",
    )
    _ = (impl / "ship-pr-state.sh").write_text("REPO=owner/repo\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    assert ci_fixer_adapter.main(["--start"]) == 0
    assert "REASON=invalid-env-file" in capsys.readouterr().out


def test_new_launch_selects_tier_and_hashes_dynamic_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    monkeypatch.setattr(ci_fixer_adapter, "_start_identity", _fixed_identity)
    monkeypatch.setattr(ci_fixer_adapter, "_select_route", _fixed_route)
    monkeypatch.setattr(ci_fixer_adapter.shutil, "which", _tool_path)

    launch = ci_fixer_adapter._new_launch(context)

    assert launch.attempt == 1
    assert launch.tier in ci_fixer_adapter.external_defaults.tool_order("implement.ci_recovery_fixer")
    assert launch.step.startswith(f"implement-step8-ci-fixer-1-{launch.tier}-")
    assert (context.handoff_dir / f"launch-{launch.step}.env").is_file()


def test_new_launch_reports_tier_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    mode = "ci"
    run_id = "42"
    key = ci_fixer_adapter.hashlib.sha256(f"{mode}\0{run_id}".encode()).hexdigest()[:20]
    lineage = context.handoff_dir / f"lineage-{key}.tsv"
    tiers = ci_fixer_adapter.external_defaults.tool_order("implement.ci_recovery_fixer")
    _ = lineage.write_text(
        "".join(f"{index}\t{tier}\t{'a' * 40}\t{'b' * 64}\tretry-next-tool\t{'c' * 40}\n" for index, tier in enumerate(tiers, 1)),
        encoding="utf-8",
    )
    monkeypatch.setattr(ci_fixer_adapter, "_start_identity", _fixed_identity)
    monkeypatch.setattr(ci_fixer_adapter, "_select_route", _fixed_route)
    monkeypatch.setattr(ci_fixer_adapter.shutil, "which", _tool_path)

    with pytest.raises(ci_fixer_adapter.CiFixerAdapterError, match="ci-fix-exhausted"):
        _ = ci_fixer_adapter._new_launch(context)
