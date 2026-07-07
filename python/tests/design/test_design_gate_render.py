"""Tests for the /design approval gate renderer."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from larch import cli
from larch.review.plan_review_common import ROUND_CAP

CLI = Path(__file__).resolve().parents[2] / "cli.py"


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


def kv(stdout: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in stdout.splitlines():
        key, value = line.split("=", 1)
        rows[key] = value
    return rows


def option_labels(rows: dict[str, str]) -> list[str]:
    return [rows[f"OPTION_{index}_LABEL"] for index in range(1, int(rows["OPTION_COUNT"]) + 1)]


def option_descriptions(rows: dict[str, str]) -> list[str]:
    return [rows[f"OPTION_{index}_DESCRIPTION"] for index in range(1, int(rows["OPTION_COUNT"]) + 1)]


def test_cli_help_and_registry_smoke() -> None:
    help_result = run_cli("--help")
    assert help_result.returncode == 0
    assert "design render-gate" in help_result.stdout
    assert cli._REGISTRY[("design", "render-gate")] == (
        "larch.design.design_gate_render",
        "render_gate_main",
    )
    assert ("design", "render-gate") in cli._MACHINE_STDOUT_KEYS


def test_gate_a_default_prompt_fields() -> None:
    result = run_cli("design", "render-gate", "--gate", "A")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["GATE_RENDER_STATUS"] == "ok"
    assert rows["GATE"] == "A"
    assert rows["HEADER"] == "Design discussion"
    assert rows["QUESTION"] == (
        "All open design questions appear discussed. Ready to launch the design review, "
        "or would you like to discuss more first?"
    )
    assert option_labels(rows) == ["See full plan", "Ready for review", "Discuss more"]
    assert option_descriptions(rows) == [
        "Re-display the current plan, then return to this prompt without advancing.",
        "Launch the design review against the current plan.",
        "Continue the post-plan discussion before review.",
    ]


def test_gate_a_without_see_full_plan() -> None:
    result = run_cli("design", "render-gate", "--gate", "A", "--without-see-full-plan")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert option_labels(rows) == ["Ready for review", "Discuss more"]
    assert option_descriptions(rows) == [
        "Launch the design review against the current plan.",
        "Continue the post-plan discussion before review.",
    ]


def test_gate_b_default_auto_apply_message_with_accepted_count() -> None:
    result = run_cli(
        "design",
        "render-gate",
        "--gate",
        "B",
        "--accepted-count",
        "3",
        "--approve-requested",
        "false",
    )
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["PROMPT_REQUIRED"] == "false"
    assert rows["OPTION_COUNT"] == "0"
    assert rows["AUTO_APPLY_MESSAGE"] == "\u2139 3.5: Gate B — auto-applying 3 accepted finding(s)"


def test_gate_b_explicit_mode_does_not_render_explicit_chooser() -> None:
    result = run_cli("design", "render-gate", "--gate", "B", "--approve-requested", "true")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["PROMPT_REQUIRED"] == "true"
    assert rows["EXPLICIT_COPY_OWNER"] == "skills/design/references/approval-gates-explicit.md"
    assert rows["OPTION_COUNT"] == "0"
    assert "HEADER" not in rows
    assert "QUESTION" not in rows


def test_gate_c_below_cap_uses_imported_round_cap(tmp_path: Path) -> None:
    _ = (tmp_path / "review-round-count.txt").write_text(f"{ROUND_CAP - 1}\n", encoding="utf-8")
    result = run_cli("design", "render-gate", "--gate", "C", "--design-tmpdir", str(tmp_path))
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["GATE"] == "C"
    assert rows["HEADER"] == "Final design"
    assert rows["REVIEW_ROUND_CAP"] == str(ROUND_CAP)
    assert rows["QUESTION"] == (
        "Final design plan is ready. Approve, see the full plan, discuss further, "
        "or re-run the review panel against this plan? Use Other to request debate <decision>: "
        "<option A> vs <option B> (or debate <candidate-id> when fingerprint-valid candidates exist)."
    )
    assert option_labels(rows) == [
        "Approve final design",
        "See full plan",
        "Discuss further",
        "Re-run review panel",
    ]
    assert option_descriptions(rows) == [
        "Approve the current plan and continue immediately to finalize.",
        "Show the full current plan, then return to this prompt without advancing.",
        "Return to Gate A discussion before another review pass.",
        "Launch another review panel against the current plan.",
    ]


def test_gate_c_at_cap_uses_imported_round_cap(tmp_path: Path) -> None:
    _ = (tmp_path / "review-round-count.txt").write_text(f"{ROUND_CAP}\n", encoding="utf-8")
    result = run_cli("design", "render-gate", "--gate", "C", "--design-tmpdir", str(tmp_path))
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["REVIEW_ROUND_CAP"] == str(ROUND_CAP)
    assert rows["QUESTION"] == (
        "Final design plan is ready. Approve, see the full plan, or discuss further? "
        "Use Other to request debate <decision>: <option A> vs <option B> "
        "(or debate <candidate-id> when fingerprint-valid candidates exist)."
    )
    assert option_labels(rows) == ["Approve final design", "See full plan", "Discuss further"]
    assert option_descriptions(rows) == [
        "Approve the current plan and continue immediately to finalize.",
        "Show the full current plan, then return to this prompt without advancing.",
        "Return to Gate A discussion before another review pass.",
    ]


def test_gate_c_without_see_full_plan_below_cap_and_at_cap(tmp_path: Path) -> None:
    _ = (tmp_path / "review-round-count.txt").write_text(f"{ROUND_CAP - 1}\n", encoding="utf-8")
    below = run_cli(
        "design",
        "render-gate",
        "--gate",
        "C",
        "--design-tmpdir",
        str(tmp_path),
        "--without-see-full-plan",
    )
    assert option_labels(kv(below.stdout)) == [
        "Approve final design",
        "Discuss further",
        "Re-run review panel",
    ]
    assert option_descriptions(kv(below.stdout)) == [
        "Approve the current plan and continue immediately to finalize.",
        "Return to Gate A discussion before another review pass.",
        "Launch another review panel against the current plan.",
    ]

    _ = (tmp_path / "review-round-count.txt").write_text(f"{ROUND_CAP}\n", encoding="utf-8")
    at_cap = run_cli(
        "design",
        "render-gate",
        "--gate",
        "C",
        "--design-tmpdir",
        str(tmp_path),
        "--without-see-full-plan",
    )
    assert option_labels(kv(at_cap.stdout)) == ["Approve final design", "Discuss further"]
    assert option_descriptions(kv(at_cap.stdout)) == [
        "Approve the current plan and continue immediately to finalize.",
        "Return to Gate A discussion before another review pass.",
    ]


def test_gate_c_non_numeric_review_round_count_warns_and_falls_back_to_zero(tmp_path: Path) -> None:
    _ = (tmp_path / "review-round-count.txt").write_text("many\n", encoding="utf-8")
    result = run_cli("design", "render-gate", "--gate", "C", "--design-tmpdir", str(tmp_path))
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["REVIEW_ROUND_COUNT_WARN"] == "non-numeric"
    assert "Re-run review panel" in option_labels(rows)


@pytest.mark.parametrize("raw", ["+2", "-1", "1_000"])
def test_gate_c_digit_only_count_contract_rejects_signed_or_underscored_values(tmp_path: Path, raw: str) -> None:
    _ = (tmp_path / "review-round-count.txt").write_text(f"{raw}\n", encoding="utf-8")
    result = run_cli("design", "render-gate", "--gate", "C", "--design-tmpdir", str(tmp_path))
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["REVIEW_ROUND_COUNT_WARN"] == "non-numeric"
    assert "Re-run review panel" in option_labels(rows)


def test_gate_c_symlinked_review_round_count_fails_open(tmp_path: Path) -> None:
    real = tmp_path / "review-round-count-real.txt"
    _ = real.write_text("4\n", encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").symlink_to(real)
    result = run_cli("design", "render-gate", "--gate", "C", "--design-tmpdir", str(tmp_path))
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert "REVIEW_ROUND_COUNT_WARN" not in rows
    assert "Re-run review panel" in option_labels(rows)


def test_gate_c_unreadable_review_round_count_fails_open(tmp_path: Path) -> None:
    count_file = tmp_path / "review-round-count.txt"
    _ = count_file.write_text("8\n", encoding="utf-8")
    count_file.chmod(0)
    try:
        result = run_cli("design", "render-gate", "--gate", "C", "--design-tmpdir", str(tmp_path))
    finally:
        count_file.chmod(0o600)
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert "REVIEW_ROUND_COUNT_WARN" not in rows
    assert "Re-run review panel" in option_labels(rows)


def test_gate_c_panel_failed_relabels_approval() -> None:
    result = run_cli("design", "render-gate", "--gate", "C", "--panel-failed", "true")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert option_labels(rows)[0] == "Approve final design (acknowledge panel failure)"
    assert option_descriptions(rows)[0] == "Approve the current plan and continue immediately to finalize."


def test_gate_c_panel_failed_without_see_full_plan_relabels_approval() -> None:
    result = run_cli("design", "render-gate", "--gate", "C", "--panel-failed", "true", "--without-see-full-plan")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert option_labels(rows) == [
        "Approve final design (acknowledge panel failure)",
        "Discuss further",
        "Re-run review panel",
    ]
    assert option_descriptions(rows) == [
        "Approve the current plan and continue immediately to finalize.",
        "Return to Gate A discussion before another review pass.",
        "Launch another review panel against the current plan.",
    ]


def test_gate_c_accepted_audit_escalation_updates_approval_description() -> None:
    result = run_cli("design", "render-gate", "--gate", "C", "--accepted-audit-escalation", "true")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert option_labels(rows) == [
        "Approve final design",
        "See full plan",
        "Discuss further",
        "Re-run review panel",
    ]
    assert option_descriptions(rows)[0] == (
        "Approve despite the main-agent accepted-findings audit's strong dissent "
        "and continue immediately to finalize."
    )


def test_gate_c_accepted_audit_escalation_works_with_panel_failed() -> None:
    result = run_cli(
        "design",
        "render-gate",
        "--gate",
        "C",
        "--accepted-audit-escalation",
        "true",
        "--panel-failed",
        "true",
    )
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert option_labels(rows)[0] == "Approve final design (acknowledge panel failure)"
    assert option_descriptions(rows)[0] == (
        "Approve despite the main-agent accepted-findings audit's strong dissent "
        "and acknowledge panel failure, then continue immediately to finalize."
    )


def test_gate_c_accepted_audit_escalation_works_without_see_full_plan() -> None:
    result = run_cli(
        "design",
        "render-gate",
        "--gate",
        "C",
        "--accepted-audit-escalation",
        "true",
        "--without-see-full-plan",
    )
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert option_labels(rows) == ["Approve final design", "Discuss further", "Re-run review panel"]
    assert option_descriptions(rows)[0] == (
        "Approve despite the main-agent accepted-findings audit's strong dissent "
        "and continue immediately to finalize."
    )


def test_gate_c_accepted_audit_escalation_emits_no_crlf() -> None:
    result = run_cli("design", "render-gate", "--gate", "C", "--accepted-audit-escalation", "true")
    assert result.returncode == 0, result.stderr
    for line in result.stdout.splitlines():
        _key, value = line.split("=", 1)
        assert "\n" not in value
        assert "\r" not in value


def test_gate_c_emits_review_round_cap_matching_round_cap() -> None:
    result = run_cli("design", "render-gate", "--gate", "C")
    rows = kv(result.stdout)
    assert result.returncode == 0, result.stderr
    assert rows["REVIEW_ROUND_CAP"] == str(ROUND_CAP)


def test_invalid_gate_exits_nonzero() -> None:
    result = run_cli("design", "render-gate", "--gate", "D")
    assert result.returncode != 0
