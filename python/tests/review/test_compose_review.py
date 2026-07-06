from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import review_test_support as rts
from larch.review import compose_review

if TYPE_CHECKING:
    import pytest

ROOT = rts.ROOT
CLI = rts.CLI


def run_review(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env)


def _record_field_by_id(jsonl_path: Path, finding_id: str, field: str) -> str:
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == finding_id:
            return str(row.get(field, ""))
    return ""


def test_compose_findings_empty_inputs_writes_jsonl(tmp_path: Path) -> None:
    impl = tmp_path / "impl"
    _ = impl.mkdir()
    output = tmp_path / "review-findings-full.jsonl"

    result = run_review(
        "compose-findings",
        "--implement-tmpdir",
        str(impl),
        "--issue",
        "0",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    assert "COMPOSED=true" in result.stdout
    assert "MODE=jsonl" in result.stdout
    assert output.exists()


def test_compose_findings_security_oos_holdback(tmp_path: Path) -> None:
    impl = tmp_path / "m-impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "oos.md").write_text(
        """### FINDING_1: [OUT_OF_SCOPE] Public follow-up
- **Reviewer**: public-reviewer.txt
- **Concern**: regular follow-up stays visible.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] Sensitive follow-up
- **Reviewer**: security-reviewer.txt
- **Concern**: focus-area = security must stay local.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted
""",
        encoding="utf-8",
    )
    output = tmp_path / "m.jsonl"

    result = run_review(
        "compose-findings",
        "--implement-tmpdir",
        str(impl),
        "--issue",
        "52",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    assert "FINDINGS_TOTAL=1" in result.stdout
    assert _record_field_by_id(output, "OOS_CR1_1", "reviewer_slots") != ""
    assert _record_field_by_id(output, "OOS_CR1_2", "reviewer_slots") == ""


def test_compose_findings_oos_missing_scratch_dir_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = tmp_path / "m-impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "oos.md").write_text(
        """### OOS_1: Missing scratch dir
- **Reviewer**: security-reviewer.txt
- **Concern**: this path should fail closed.
""",
        encoding="utf-8",
    )
    output = tmp_path / "m.jsonl"

    monkeypatch.setattr(compose_review, "_compose_scratch_dir", lambda **_kwargs: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    rc = compose_review.compose_findings(
        [
            "--implement-tmpdir",
            str(impl),
            "--issue",
            "52",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert rc == 2
    assert "FAILED=true" in text
    assert "review scratch directory is required before tempfile staging" in text


def test_compose_findings_design_gate_b_skip_and_accepted_all_precedence(tmp_path: Path) -> None:
    design = tmp_path / "design-map"
    _ = (design / "plan-review" / "round-1").mkdir(parents=True)
    _ = (design / "accepted-plan-findings.md").write_text(
        """### FINDING_OLD: Per-round file should lose to -all
- **Reviewer**: Cursor-Arch
- **Concern**: This file is not the cumulative source.
""",
        encoding="utf-8",
    )
    _ = (design / "accepted-plan-findings-all.md").write_text(
        """### FINDING_ALL: Cumulative accepted
- **Reviewer**: Cursor-Arch
- **Concern**: accepted all wins.

### FINDING_SKIP: Skipped during Gate B
- **Reviewer**: Cursor-Arch
- **Concern**: skip me.
""",
        encoding="utf-8",
    )
    _ = (design / "rejected-findings.md").write_text(
        """### FINDING_SKIP: Skipped during Gate B
- **Reviewer**: Cursor-Arch
- **Concern**: skip me.
- **Reason**: rejected by user during one-by-one review
""",
        encoding="utf-8",
    )
    output = tmp_path / "design.jsonl"

    result = run_review(
        "compose-findings",
        "--design-artifacts-dir",
        str(design),
        "--issue",
        "3776",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    assert "FINDINGS_TOTAL=1" in result.stdout
    assert _record_field_by_id(output, "FINDING_OLD", "phase") == ""
    assert _record_field_by_id(output, "FINDING_SKIP", "phase") == ""
    assert "FINDING_ALL" in output.read_text(encoding="utf-8")


def test_compose_findings_redacts_token_in_prose_body(tmp_path: Path) -> None:
    impl = tmp_path / "redact-impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "accepted-findings.md").write_text(
        """### FINDING_1: Token leak
- **Reviewer**: reviewer.txt
- **Concern**: secret sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD here
""",
        encoding="utf-8",
    )
    output = tmp_path / "redact.jsonl"

    result = run_review(
        "compose-findings",
        "--implement-tmpdir",
        str(impl),
        "--issue",
        "1",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    raw = output.read_text(encoding="utf-8")
    assert "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD" not in raw
    assert "<REDACTED-TOKEN>" in raw


def test_compose_findings_body_severity_focus_area_before_prose_truncation(tmp_path: Path) -> None:
    impl = tmp_path / "trunc-impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    pad = "x" * 2100
    _ = (round_dir / "accepted-findings.md").write_text(
        f"### FINDING_TRUNC: late markers\n"
        f"- **Concern**: {pad}\n"
        "- **Severity**: important\n"
        "- **Focus area**: security\n",
        encoding="utf-8",
    )
    output = tmp_path / "trunc.jsonl"
    result = run_review(
        "compose-findings",
        "--implement-tmpdir",
        str(impl),
        "--issue",
        "2499",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    assert _record_field_by_id(output, "FINDING_TRUNC", "body_severity") == "important"
    assert _record_field_by_id(output, "FINDING_TRUNC", "focus_area") == "security"
    prose = _record_field_by_id(output, "FINDING_TRUNC", "prose_body")
    assert len(prose) <= 2000


def test_compose_findings_rejected_full_code_review_artifact(tmp_path: Path) -> None:
    impl = tmp_path / "impl-rej"
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "rejected-findings-full.md").write_text(
        """### [rejected] FINDING_7

### FINDING_7: correctness: src/app.py:10
- **Reviewer**: Cursor-Correctness
- **Concern**: rejected prose remains available.
""",
        encoding="utf-8",
    )
    output = tmp_path / "rejected.jsonl"

    result = run_review("compose-findings", "--implement-tmpdir", str(impl), "--issue", "9", "--output", str(output))

    assert result.returncode == 0, result.stderr
    assert "FINDINGS_TOTAL=1" in result.stdout
    assert _record_field_by_id(output, "REJ_CR2_1", "outcome") == "rejected"
    assert _record_field_by_id(output, "REJ_CR2_1", "category") == "correctness"


def test_compose_findings_invalid_issue_failure_envelope(tmp_path: Path) -> None:
    output = tmp_path / "bad.jsonl"

    result = run_review("compose-findings", "--issue", "abc", "--output", str(output))

    assert result.returncode == 2
    assert "FAILED=true" in result.stdout
    assert "invalid value for --issue" in result.stdout


def test_compose_findings_strict_plan_category(tmp_path: Path) -> None:
    design = tmp_path / "design-strict"
    design.mkdir()
    _ = (design / "accepted-plan-findings.md").write_text(
        """### FINDING_1: **Important** — `not-a-real-category` — `docs/plan.md:1`
- **Reviewer**: Cursor-Arch
- **Concern**: category should be empty under strict plan mode
""",
        encoding="utf-8",
    )
    output = tmp_path / "strict-plan.jsonl"
    result = run_review(
        "compose-findings",
        "--design-artifacts-dir",
        str(design),
        "--issue",
        "1",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    assert _record_field_by_id(output, "FINDING_1", "category") == ""


def test_compose_findings_prune_label_map_normalizes_reviewer_slots(tmp_path: Path) -> None:
    design = tmp_path / "design-map"
    design.mkdir()
    output_file = design / "Cursor-Arch-output.txt"
    _ = output_file.write_text("reviewer output\n", encoding="utf-8")
    _ = (design / "plan-review-slots.ndjson").write_text(
        json.dumps({"slot": "cursor-plan-arch", "tool": "cursor", "output": str(output_file)}) + "\n",
        encoding="utf-8",
    )
    _ = (design / "plan-review-prune-label-map.tsv").write_text(
        "cursor-plan-arch\tCursor-Arch\n",
        encoding="utf-8",
    )
    _ = (design / "accepted-plan-findings.md").write_text(
        """### FINDING_1: Plan issue
- **Reviewer**: Cursor-Arch
- **Concern**: reviewer label should normalize via prune label map
""",
        encoding="utf-8",
    )
    output = tmp_path / "mapped.jsonl"
    result = run_review(
        "compose-findings",
        "--design-artifacts-dir",
        str(design),
        "--issue",
        "1",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    slots = json.loads(_record_field_by_id(output, "FINDING_1", "reviewer_slots").replace("'", '"'))
    assert slots == ["Cursor-Arch-output.txt"]


def test_compose_findings_design_reviewer_map_skips_non_dict_rows(tmp_path: Path) -> None:
    design = tmp_path / "design-map-shape"
    design.mkdir()
    output_file = design / "Cursor-Arch-output.txt"
    _ = output_file.write_text("reviewer output\n", encoding="utf-8")
    _ = (design / "plan-review-slots.ndjson").write_text(
        "\n".join(
            [
                json.dumps(["not", "a", "dict"]),
                json.dumps("not a dict"),
                json.dumps({"slot": "cursor-plan-arch", "tool": "cursor", "output": str(output_file)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _ = (design / "accepted-plan-findings.md").write_text(
        """### FINDING_1: Plan issue
- **Reviewer**: Cursor-Arch
- **Concern**: non-dict slot rows should be ignored
""",
        encoding="utf-8",
    )
    output = tmp_path / "shape.jsonl"

    result = run_review(
        "compose-findings",
        "--design-artifacts-dir",
        str(design),
        "--issue",
        "1",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    slots = json.loads(_record_field_by_id(output, "FINDING_1", "reviewer_slots").replace("'", '"'))
    assert slots == ["Cursor-Arch-output.txt"]
