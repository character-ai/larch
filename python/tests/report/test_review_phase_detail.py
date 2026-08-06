"""Coverage for the Python final-report wrapper around the Rust phase renderer."""

# Rust-wrapper coverage intentionally replaces the renderer and redactor with
# test doubles, including private wrapper paths and ignored fixture writes.
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

from pathlib import Path

import pytest  # noqa: TC002

from larch.core import rust_runtime
from larch.report import review_phase_detail


def test_invoke_renderer_suppresses_an_empty_or_failed_rust_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds = tmp_path / "rounds"
    rounds.mkdir()

    monkeypatch.setattr(rust_runtime, "render_phase_detail", lambda *_args, **_kwargs: "")
    assert review_phase_detail._invoke_renderer(rounds, skill="implement") == ""

    def fail(*_args: object, **_kwargs: object) -> str:
        raise TimeoutError("renderer timed out")

    monkeypatch.setattr(rust_runtime, "render_phase_detail", fail)
    assert review_phase_detail._invoke_renderer(rounds, skill="implement") == ""


def test_invoke_renderer_redacts_rust_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    monkeypatch.setattr(
        rust_runtime,
        "render_phase_detail",
        lambda *_args, **_kwargs: "## Review Phase Detail\nsecret\n",
    )
    monkeypatch.setattr(
        review_phase_detail.redact,
        "redact_outbound",
        lambda text: text.replace("secret", "<redacted>"),
    )

    assert review_phase_detail._invoke_renderer(rounds, skill="implement") == "## Review Phase Detail\n<redacted>\n"


def test_invoke_renderer_rejects_post_redaction_truncation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    monkeypatch.setattr(rust_runtime, "render_phase_detail", lambda *_args, **_kwargs: "detail")
    monkeypatch.setattr(review_phase_detail.redact, "redact_outbound", lambda _text: "[content truncated]")

    assert review_phase_detail._invoke_renderer(rounds, skill="implement") == ""


def test_render_design_review_detail_passes_the_expected_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds = tmp_path / "plan-review"
    rounds.mkdir()
    timing = tmp_path / "timing-ledger.tsv"
    timing.write_text("v1\tround\n", encoding="utf-8")
    findings = tmp_path / "review-findings-full.jsonl"
    findings.write_text("{}\n", encoding="utf-8")
    tokens = tmp_path / "larch-tokens-1.jsonl"
    tokens.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def render(*_args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return "## Review Phase Detail\n"

    monkeypatch.setattr(rust_runtime, "render_phase_detail", render)

    assert review_phase_detail.render_design_review_detail(tmp_path) == "## Review Phase Detail\n"
    assert captured["rounds_root"] == str(rounds)
    assert captured["skill"] == "design"
    assert captured["timing_ledger"] == str(timing)
    assert captured["findings_file"] == str(findings)
    assert captured["token_ledger"] == str(tokens)


def _write_rejected_oos(
    path: Path,
    *,
    title: str,
    severity: str = "minor",
    concern: str = "Needs a follow-up.",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"### OOS_1: {title}\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        f"- **Severity**: {severity}\n"
        f"- **Concern**: {concern}\n"
        "- **Suggested revisions (informational for voters; coder decides)**:\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n",
        encoding="utf-8",
    )


def _write_classification(path: Path, *, finding_id: str = "OOS_1", result: str = "rejected") -> None:
    path.write_text(
        "finding_id\treviewer_slots\tvoting_result\tscope\n"
        f"{finding_id}\tcodex-specialist-correctness\t{result}\toos\n",
        encoding="utf-8",
    )


def test_render_rejected_oos_audit_section_lists_public_candidates(tmp_path: Path) -> None:
    _write_rejected_oos(
        tmp_path / "round-1" / "oos.md",
        title="[OUT_OF_SCOPE] retry gap",
        severity="major",
        concern="`python/example.py:10` misses the retry branch. It predates this diff.",
    )

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "## Rejected OOS audit" in section
    assert "These OOS observations reached the vote but were not accepted for filing." in section
    assert "Round 1 OOS_1" in section
    assert "retry gap" in section
    assert "Concern: `python/example.py:10` misses the retry branch." in section


def test_render_rejected_oos_audit_section_prefers_tsv_without_footer(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] retry gap\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: major\n"
        "- **Concern**: footer drift removed the result line.\n",
        encoding="utf-8",
    )
    _write_classification(round_dir / "findings-classification.tsv", result="rejected")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "- **Round 1 OOS_1** (rejected, major): retry gap." in section


def test_render_rejected_oos_audit_section_tsv_accepted_beats_footer(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    _write_rejected_oos(round_dir / "oos.md", title="[OUT_OF_SCOPE] stale rejected footer")
    _write_classification(round_dir / "findings-classification.tsv", result="accepted")

    assert review_phase_detail.render_rejected_oos_audit_section(tmp_path) == ""


def test_render_rejected_oos_audit_section_falls_back_on_malformed_tsv(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] fallback candidate\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: major\n"
        "- **Concern**: footer fallback remains available.\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n",
        encoding="utf-8",
    )
    _ = (round_dir / "findings-classification.tsv").write_bytes(b"\xff\xfe\x80")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "- **Round 1 OOS_1** (rejected, major): fallback candidate." in section


def test_render_rejected_oos_audit_section_skips_security_candidates(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] [security] token leak\n"
        "- **Reviewer(s)**: codex-specialist-security\n"
        "- **Severity**: major\n"
        "- **Concern**: private detail.\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n\n"
        "### OOS_2: [OUT_OF_SCOPE] public follow-up\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: minor\n"
        "- **Concern**: public detail.\n"
        "Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral\n",
        encoding="utf-8",
    )
    _write_classification(round_dir / "findings-classification.tsv", finding_id="OOS_1", result="rejected")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "public follow-up" in section
    assert "private detail" not in section
    assert "Round 1 OOS_1" not in section


def test_render_rejected_oos_audit_section_keeps_security_md_titled_public_candidates(tmp_path: Path) -> None:
    _write_rejected_oos(
        tmp_path / "round-1" / "oos.md",
        title="[OUT_OF_SCOPE] SECURITY.md still documents REDACTED_LOG_FILE-only failure consumption",
        severity="major",
        concern="docs/linting.md moved to DIGEST_FILE-first consumption but SECURITY.md was not updated.",
    )

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "SECURITY.md still documents REDACTED_LOG_FILE-only failure consumption" in section


def test_render_rejected_oos_audit_section_lists_legacy_finding_block(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### FINDING_1: legacy scope drift\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: minor\n"
        "- **Concern**: moved into oos.md without an OOS tag.\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n",
        encoding="utf-8",
    )

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "Round 1 FINDING_1" in section
    assert "legacy scope drift" in section


def test_render_rejected_oos_audit_section_caps_candidates(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    blocks: list[str] = []
    for idx in range(review_phase_detail.REJECTED_OOS_AUDIT_LIMIT + 1):
        blocks.append(
            f"### OOS_{idx + 1}: [OUT_OF_SCOPE] item {idx + 1}\n"
            "- **Reviewer(s)**: codex-specialist-correctness\n"
            "- **Severity**: nit\n"
            f"- **Concern**: concern {idx + 1}.\n"
            "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n"
        )
    _ = (round_dir / "oos.md").write_text("\n".join(blocks), encoding="utf-8")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert f"Round 1 OOS_{review_phase_detail.REJECTED_OOS_AUDIT_LIMIT}" in section
    assert f"Round 1 OOS_{review_phase_detail.REJECTED_OOS_AUDIT_LIMIT + 1}" not in section
    assert "- **Additional audit rows**: 1 omitted by the final-summary cap." in section


def test_render_implement_review_detail_omits_rejected_oos_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-3794"
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    _write_rejected_oos(run_dir / "round-1" / "oos.md", title="[OUT_OF_SCOPE] closeout gap")
    monkeypatch.setattr(
        rust_runtime,
        "render_phase_detail",
        lambda *_args, **_kwargs: "## Review Phase Detail\nreview detail\n",
    )

    detail = review_phase_detail.render_implement_review_detail(implement_tmpdir=tmp_path, run_id=run_id)

    assert detail == "## Review Phase Detail\nreview detail\n"
    assert "Rejected OOS audit" not in detail
    assert "closeout gap" not in detail


def test_append_review_phase_detail_normalizes_spacing() -> None:
    assert review_phase_detail.append_review_phase_detail(body="body\n", detail="detail\n") == "body\n\ndetail\n"
    assert review_phase_detail.append_review_phase_detail(body="body\n", detail="") == "body\n"
