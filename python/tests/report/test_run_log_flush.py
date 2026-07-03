from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from larch.calibration import difficulty
from larch.report import run_log_flush


def test_refresh_difficulty_record_merges_resolution_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    record_path = run_dir / difficulty.DIFFICULTY_RECORD_BASENAME
    existing = difficulty.build_record(
        rater="implement",
        rater_tool="claude",
        rater_model="unknown",
        implement_rating=difficulty.validate_rating_object(
            {"predicted_tier": "TRIVIAL", "confidence": "high", "rationale": "bootstrap"}
        ),
        override_tier="HARD",
        audit_upgrade="true",
        escalations=(
            {"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "bulk-skip"},
        ),
        panel_tier="HARD",
        round_cap=3,
        codex_model_role="default",
        audit_evaluated=True,
        escalated_round=True,
    )
    difficulty.write_record(record_path, existing)

    monkeypatch.setattr(run_log_flush, "effective_run_id", lambda _ctx: "run-1")
    monkeypatch.setattr(run_log_flush, "_write_batch", lambda **_kwargs: None)

    def fake_run(argv: list[str], *, cwd: str | None = None, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "diff", "--name-only"]:
            assert cwd == str(tmp_path)
            return subprocess.CompletedProcess(argv, 0, "hooks/pre-tool-use.sh\n", "")
        raise AssertionError(f"unexpected command: {argv}")

    monkeypatch.setattr(run_log_flush.proc, "run", fake_run)

    run_log_flush._refresh_difficulty_record(ctx=object(), log_root=tmp_path, cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    data = json.loads(record_path.read_text(encoding="utf-8"))

    assert data["override_source"] == "operator"
    assert data["panel_tier"] == "HARD"
    assert data["round_cap"] == 3
    assert data["codex_model_role"] == "default"
    assert data["audit_evaluated"] is True
    assert data["escalated_round"] is True
    assert data["escalations"][0]["round"] == 2
