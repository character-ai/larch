"""Unit coverage for the final-summary library helpers relocated into
``design_core`` when the ``design render-final-summary`` verb migrated to Rust
(#8581). The migrated verb behavior itself is proven by the Rust parity harness
``crates/larch-cli/tests/design_gate_summary_migrated_parity.rs``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from larch.design import design_core

if TYPE_CHECKING:
    import pytest


def test_resolve_summary_mode_prefers_run_params(tmp_path: Path) -> None:
    _ = (tmp_path / "run-params.json").write_text('{"mode": "quick"}', encoding="utf-8")
    assert design_core.resolve_summary_mode(tmp_path) == "quick"


def test_resolve_summary_mode_falls_back_to_source_env(tmp_path: Path) -> None:
    _ = (tmp_path / "source-env.sh").write_text('export MODE="deep"\n', encoding="utf-8")
    assert design_core.resolve_summary_mode(tmp_path) == "deep"


def test_resolve_summary_mode_defaults_to_na(tmp_path: Path) -> None:
    assert design_core.resolve_summary_mode(tmp_path) == "N/A"


def test_final_summary_request_skips_upsert_and_forces_post_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_captured(*, verb: str, args: Sequence[str], stdout_path: Path, stderr_path: Path, plugin_root: Path | None = None) -> int:
        assert verb == "render-final-summary"
        del stdout_path, stderr_path, plugin_root
        calls.append(list(args))
        _ = (tmp_path / "final-summary.md").write_text("enriched\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(design_core, "run_design_verb_captured", fake_captured)

    ok = design_core.render_final_summary_for_request(
        design_core.FinalSummaryRenderRequest(
            design_tmpdir=tmp_path,
            outcome="approved",
            mode="design",
            issue_number="42",
            session_id="RUN1",
            repo="owner/repo",
            upsert_summary_comment=False,
            stdout_log_path=tmp_path / "summary.stdout.log",
        )
    )

    assert ok
    assert calls == [
        [
            "--outcome",
            "approved",
            "--mode",
            "design",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "RUN1",
            "--post-publish-only",
            "--repo",
            "owner/repo",
            "--skip-summary-upsert",
        ]
    ]
    assert "--pre-publish-only" not in calls[0]
    assert (tmp_path / "final-summary.md").read_text(encoding="utf-8") == "enriched\n"


def test_final_summary_request_unlinks_stale_file_on_failed_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = tmp_path / "final-summary.md"
    _ = stale.write_text("stale\n", encoding="utf-8")

    def fake_captured(*, verb: str, args: Sequence[str], stdout_path: Path, stderr_path: Path, plugin_root: Path | None = None) -> int:
        del verb, args, stdout_path, stderr_path, plugin_root
        assert not stale.exists()
        _ = stale.write_text("partial\n", encoding="utf-8")
        return 1

    monkeypatch.setattr(design_core, "run_design_verb_captured", fake_captured)

    ok = design_core.render_final_summary_for_request(
        design_core.FinalSummaryRenderRequest(
            design_tmpdir=tmp_path,
            outcome="approved",
            mode="N/A",
            issue_number="0",
            session_id="RUN1",
            repo="",
            upsert_summary_comment=True,
            stdout_log_path=tmp_path / "summary.stdout.log",
        )
    )

    assert not ok
    assert not stale.exists()


def test_upsert_final_summary_from_disk_guards_missing_and_zero_issue(tmp_path: Path) -> None:
    # Missing summary file fails closed before any subprocess.
    assert not design_core.upsert_final_summary_from_disk(
        design_tmpdir=tmp_path, issue="42", session_id="RUN1"
    )
    summary = tmp_path / "final-summary.md"
    _ = summary.write_text("body\n", encoding="utf-8")
    # Present file but a placeholder issue number fails closed too.
    assert not design_core.upsert_final_summary_from_disk(
        design_tmpdir=tmp_path, issue="0", session_id="RUN1"
    )
