from __future__ import annotations

import subprocess
from pathlib import Path

import review_test_support as rts

ROOT = rts.ROOT
CLI = rts.CLI


def run_review(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env)


def _aggregate_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    return {
        "LARCH_EXECUTION_ISSUES_LOG": str(tmp_path / "execution-issues.md"),
        **extra,
    }


def test_aggregate_disabled_fast_path_preserves_findings(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    original = "### FINDING_1: keep me\n"
    _ = findings.write_text(original, encoding="utf-8")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(tmp_path),
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
        "--mode",
        "description",
        env={"LARCH_AGGREGATOR_DISABLED": "1"},
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=disabled" in result.stdout
    assert findings.read_text(encoding="utf-8") == original


def test_aggregate_merge_success(tmp_path: Path) -> None:
    findings = tmp_path / "in3-work.md"
    _ = findings.write_text(
        """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix

### FINDING_3: Dup C
- **Reviewer**: cursor-c-output.txt
- **Concern**: same bug again
- **Suggested revision**: fix

""",
        encoding="utf-8",
    )
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_aggregate_dispatch_stub(dispatch, merge_kind="merge", mode="ok")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(tmp_path),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "diff",
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=true" in result.stdout
    assert "REASON=ok" in result.stdout
    assert "MERGED_COUNT=1" in result.stdout
    assert findings.read_text(encoding="utf-8").count("### FINDING_") == 1


def test_aggregate_malformed_output_preserves_ballot(tmp_path: Path) -> None:
    findings = tmp_path / "in3-mal.md"
    original = """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix

"""
    _ = findings.write_text(original, encoding="utf-8")
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_aggregate_dispatch_stub(dispatch, merge_kind="malformed", mode="ok")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(tmp_path),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "diff",
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=validation-failed" in result.stdout
    assert findings.read_text(encoding="utf-8") == original


def test_aggregate_dispatch_failure_preserves_ballot(tmp_path: Path) -> None:
    findings = tmp_path / "in3-disp.md"
    original = """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix

"""
    _ = findings.write_text(original, encoding="utf-8")
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_aggregate_dispatch_stub(dispatch, mode="fail_dispatch")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(tmp_path),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "diff",
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=dispatch-failed" in result.stdout
    assert findings.read_text(encoding="utf-8") == original


def test_aggregate_plan_mode_preserves_scope_reduction_block(tmp_path: Path) -> None:
    findings = tmp_path / "plan-scope" / "in.md"
    findings.parent.mkdir(parents=True)
    _ = findings.write_text(
        """### FINDING_1:
- **Reviewer(s)**: scope-slot
- **Severity**: important
- **Concern**: [SCOPE-REDUCTION] remove unrelated scope. Scenario: bloat
- **Proposed resolution**: remove it

### FINDING_2:
- **Reviewer(s)**: merge-a
- **Severity**: important
- **Concern**: add missing regression test. Scenario: bug returns
- **Proposed resolution**: add test

### FINDING_3:
- **Reviewer(s)**: merge-b
- **Severity**: important
- **Concern**: add missing regression test duplicate. Scenario: bug returns
- **Proposed resolution**: add test
""",
        encoding="utf-8",
    )
    dispatch = findings.parent / "dispatch.sh"
    rts.write_executable(
        dispatch,
        """#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="$2"; shift 2 ;;
    *) shift ;;
  esac
done
out=$(jq -r '.output' "$slots")
cat >"$out" <<'OUT'
### FINDING_1:
- **Reviewer(s)**: merge-a, merge-b
- **Concern**: add missing regression test. Scenario: bug returns
- **Proposed resolution**: add test
OUT
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s.output-files\\n' "$out" "$slots"
printf '%s\\n' "$out" > "${slots}.output-files"
""",
    )
    review_tmp = findings.parent

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(review_tmp),
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--mode",
        "description",
        "--input-mode",
        "plan",
        "--allow-findings-outside-tmpdir",
        "true",
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=true" in result.stdout
    text = findings.read_text(encoding="utf-8")
    assert "[SCOPE-REDUCTION] remove unrelated scope" in text
    assert "### FINDING_2:" in text
    assert "### FINDING_3:" not in text


def test_aggregate_invalid_scope_anchor_warns_and_omits_block(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    _ = findings.write_text(
        """### FINDING_1:
- **Reviewer(s)**: merge-a
- **Severity**: important
- **Concern**: add missing regression test. Scenario: bug returns
- **Proposed resolution**: add test

### FINDING_2:
- **Reviewer(s)**: merge-b
- **Severity**: important
- **Concern**: add missing regression test duplicate. Scenario: bug returns
- **Proposed resolution**: add test
""",
        encoding="utf-8",
    )
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_executable(
        dispatch,
        """#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="$2"; shift 2 ;;
    *) shift ;;
  esac
done
out=$(jq -r '.output' "$slots")
cat >"$out" <<'OUT'
### FINDING_1:
- **Reviewer(s)**: merge-a, merge-b
- **Concern**: add missing regression test. Scenario: bug returns
- **Proposed resolution**: add test
OUT
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s.output-files\\n' "$out" "$slots"
printf '%s\\n' "$out" > "${slots}.output-files"
""",
    )
    issues = tmp_path / "execution-issues.md"
    _ = issues.write_text("", encoding="utf-8")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(tmp_path),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "description",
        "--input-mode",
        "plan",
        "--scope-anchor-file",
        "/tmp/stale-plan-scope-anchor.txt",
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=true" in result.stdout
    prompt = (tmp_path / "aggregator-prompt.md").read_text(encoding="utf-8")
    assert "plan_review_scope_anchor" not in prompt
    assert "invalid or stale scope-anchor path omitted" in issues.read_text(encoding="utf-8")


def test_aggregate_validation_exhausted_preserves_ballot(tmp_path: Path) -> None:
    findings = tmp_path / "in-exhaust.md"
    original = """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix

"""
    _ = findings.write_text(original, encoding="utf-8")
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_aggregate_dispatch_stub(dispatch, merge_kind="validation_exhausted", mode="ok")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(tmp_path),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "diff",
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=validation-exhausted" in result.stdout
    assert findings.read_text(encoding="utf-8") == original
    validate_stderr = (tmp_path / "aggregator-validate.stderr").read_text(encoding="utf-8")
    assert "AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation" in validate_stderr


def test_aggregate_session_env_failure_log_pointer(tmp_path: Path) -> None:
    session_parent = tmp_path / "session-parent"
    session_parent.mkdir()
    session_env = session_parent / "session.env"
    _ = session_env.write_text("DESIGN_TMPDIR=\n", encoding="utf-8")
    review_tmp = session_parent / "review-tmp"
    review_tmp.mkdir()
    findings = review_tmp / "findings.md"
    original = """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix

"""
    _ = findings.write_text(original, encoding="utf-8")
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_aggregate_dispatch_stub(dispatch, merge_kind="validation_exhausted", mode="ok")
    issues = session_parent / "execution-issues.md"
    _ = issues.write_text("", encoding="utf-8")

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(review_tmp),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "diff",
        "--session-env-path",
        str(session_env),
        env={"AGGREGATE_DISPATCH_SH": str(dispatch)},
    )

    assert result.returncode == 0, result.stderr
    assert "REASON=validation-exhausted" in result.stdout
    assert f"FAILURE_LOG={review_tmp}/aggregator-validate.stderr" in result.stdout
    assert "validation exhausted (narrow-trigger nonconforming pseudo-heading combined with attestation)" in issues.read_text(
        encoding="utf-8"
    )
