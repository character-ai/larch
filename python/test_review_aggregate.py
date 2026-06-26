# pyright: reportPrivateUsage=false

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import review_aggregate
import review_test_support as rts
import shutil

if TYPE_CHECKING:
    import pytest

ROOT = rts.ROOT
CLI = rts.CLI


def run_review(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env)


def _aggregate_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    return {
        "LARCH_EXECUTION_ISSUES_LOG": str(tmp_path / "execution-issues.md"),
        **extra,
    }


# Issue #4868 reproduction fixtures: cursor-b-output.txt raises only an [OUT_OF_SCOPE]-tagged finding
# (it is "exclusively out of scope"); cursor-a-output.txt raises an in-scope finding.
_OOS_ATTR_INPUT = """### FINDING_1: In-scope bug
- **Reviewer**: cursor-a-output.txt
- **Severity**: important
- **Concern**: real bug needing a fix
- **Suggested revision**: fix it

### FINDING_2: [OUT_OF_SCOPE] Style nit
- **Reviewer**: cursor-b-output.txt
- **Severity**: nit
- **Concern**: unrelated style preference
- **Suggested revision**: tidy later
"""

# Promotes the exclusively-OOS reviewer (cursor-b) into a non-OOS block -> rc=2 OOS-attribution failure.
_OOS_ATTR_FAIL = """### FINDING_1: In-scope bug
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: important
- **Concern**: real bug needing a fix
- **Suggested revision**: fix it"""

# Keeps the exclusively-OOS reviewer in its own [OUT_OF_SCOPE] block -> validation passes.
_OOS_ATTR_SUCCESS = """### FINDING_1: In-scope bug
- **Reviewer(s)**: cursor-a-output.txt
- **Severity**: important
- **Concern**: real bug needing a fix
- **Suggested revision**: fix it

### FINDING_2: [OUT_OF_SCOPE] Style nit
- **Reviewer(s)**: cursor-b-output.txt
- **Severity**: nit
- **Concern**: unrelated style preference
- **Suggested revision**: tidy later"""

# Issue #4881: both inputs are in-scope (no OOS-tagged reviewers), so a merge that omits the
# required code-mode Severity line fails validation for a NON-OOS-attribution reason.
_NON_OOS_INPUT = """### FINDING_1: In-scope bug A
- **Reviewer**: cursor-a-output.txt
- **Severity**: important
- **Concern**: real bug A
- **Suggested revision**: fix A

### FINDING_2: In-scope bug B
- **Reviewer**: cursor-b-output.txt
- **Severity**: important
- **Concern**: real bug B
- **Suggested revision**: fix B
"""

# Lists both in-scope reviewers but omits "- **Severity**:" -> rc=2 non-OOS validation failure.
_NON_OOS_FAIL = """### FINDING_1: Merged in-scope
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Concern**: merged concern
- **Suggested revision**: fix"""

# Issue #5077: drops cursor-b from every reviewer line -> "input reviewers missing from merge output".
_MISSING_REVIEWER_FAIL = """### FINDING_1: Merged in-scope
- **Reviewer(s)**: cursor-a-output.txt
- **Severity**: important
- **Concern**: merged concern
- **Suggested revision**: fix"""

# Keeps both in-scope reviewers in the merged block -> validation passes.
_MISSING_REVIEWER_SUCCESS = """### FINDING_1: Merged in-scope
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: important
- **Concern**: merged concern
- **Suggested revision**: fix"""

# Issue #5222: a merged block that omits its **Reviewer(s)**: line entirely -> "block missing reviewer
# attribution line". The block is otherwise well-formed (valid heading + code-mode Severity), so the
# missing-attribution check fires before any other validation branch.
_MISSING_ATTRIBUTION_FAIL = """### FINDING_1: Merged in-scope
- **Severity**: important
- **Concern**: merged concern
- **Suggested revision**: fix"""

# Restores the reviewer-attribution line with both in-scope reviewers -> validation passes.
_MISSING_ATTRIBUTION_SUCCESS = """### FINDING_1: Merged in-scope
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: important
- **Concern**: merged concern
- **Suggested revision**: fix"""

# Issue #5503: both inputs are in-scope; the aggregator's first attempt references FINDING_N in
# narrative prose but emits no conforming `### FINDING_N:` blocks. This is the recoverable
# preamble-slip class and must re-dispatch with validator feedback (like #4868/#5077/#5222), not
# stall Step 5 after a single attempt.
_PREAMBLE_SLIP_INPUT = """### FINDING_1: In-scope bug A
- **Reviewer**: cursor-a-output.txt
- **Severity**: important
- **Concern**: real bug A
- **Suggested revision**: fix A

### FINDING_2: In-scope bug B
- **Reviewer**: cursor-b-output.txt
- **Severity**: important
- **Concern**: real bug B
- **Suggested revision**: fix B
"""

# References FINDING_1/FINDING_2 in prose but emits no conforming `### FINDING_N:` block and no
# nonconforming `### FINDING_` pseudo-heading -> rc=_PREAMBLE_SLIP_RC preamble-slip failure.
_PREAMBLE_SLIP_FAIL = """Aggregator narrative: FINDING_1 and FINDING_2 describe the same bug, so I merged them, but I forgot to emit the structured heading blocks."""

# Emits both in-scope reviewers in a conforming merged block -> validation passes.
_PREAMBLE_SLIP_SUCCESS = """### FINDING_1: Merged in-scope
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: important
- **Concern**: merged concern
- **Suggested revision**: fix"""


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


def test_aggregate_oos_attribution_failure_retries_then_succeeds(tmp_path: Path) -> None:
    findings = tmp_path / "in-retry.md"
    _ = findings.write_text(_OOS_ATTR_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=1,
        fail_body=_OOS_ATTR_FAIL,
        success_body=_OOS_ATTR_SUCCESS,
    )

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
    # First dispatch failed OOS-attribution validation; the bounded retry re-dispatched and recovered.
    assert counter.read_text(encoding="utf-8") == "2"
    merged = findings.read_text(encoding="utf-8")
    assert "### FINDING_1: In-scope bug" in merged
    assert "### FINDING_2: [OUT_OF_SCOPE] Style nit" in merged
    # The retry prompt fed the validator error back to the aggregator.
    prompt = (tmp_path / "aggregator-prompt.md").read_text(encoding="utf-8")
    assert "Previous aggregation attempt rejected by validation" in prompt
    assert "appears only on OOS-tagged input findings" in prompt
    # Issue #4881: the retry-appended OOS guidance no longer suggests dropping a reviewer slot (which
    # would re-fail the "every input reviewer must appear" check) and instead keeps all reviewers
    # present. Scope the assertion to the retry-appended section so the base aggregator template's
    # own (unchanged) wording does not mask the fix.
    retry_section = prompt.split("## Previous aggregation attempt rejected by validation", 1)[1]
    assert "omit that reviewer slot" not in retry_section
    assert "every input reviewer must still appear" in retry_section


def test_aggregate_validation_failure_exhausts_retry_budget(tmp_path: Path) -> None:
    findings = tmp_path / "in-exhaust-retry.md"
    _ = findings.write_text(_OOS_ATTR_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=99,
        fail_body=_OOS_ATTR_FAIL,
        success_body=_OOS_ATTR_SUCCESS,
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_VALIDATION_RETRIES="2"),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=validation-failed" in result.stdout
    # 1 initial dispatch + 2 retries, then a bounded degrade that preserves the original ballot.
    assert counter.read_text(encoding="utf-8") == "3"
    assert findings.read_text(encoding="utf-8") == _OOS_ATTR_INPUT


def test_aggregate_validation_retries_disabled_is_single_shot(tmp_path: Path) -> None:
    findings = tmp_path / "in-noretry.md"
    _ = findings.write_text(_OOS_ATTR_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=99,
        fail_body=_OOS_ATTR_FAIL,
        success_body=_OOS_ATTR_SUCCESS,
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_VALIDATION_RETRIES="0"),
    )

    assert result.returncode == 0, result.stderr
    assert "REASON=validation-failed" in result.stdout
    assert counter.read_text(encoding="utf-8") == "1"
    assert findings.read_text(encoding="utf-8") == _OOS_ATTR_INPUT


def test_aggregate_non_oos_validation_failure_is_single_shot(tmp_path: Path) -> None:
    # Issue #4881: a non-OOS-attribution semantic failure (here a merged block missing the required
    # code-mode Severity line) must degrade single-shot, not consume the retry budget.
    findings = tmp_path / "in-nonoos.md"
    _ = findings.write_text(_NON_OOS_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=99,
        fail_body=_NON_OOS_FAIL,
        success_body=_NON_OOS_FAIL,
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_VALIDATION_RETRIES="2"),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=validation-failed" in result.stdout
    # Single-shot despite a retry budget of 2, because this is not the OOS-attribution class.
    assert counter.read_text(encoding="utf-8") == "1"
    assert findings.read_text(encoding="utf-8") == _NON_OOS_INPUT
    validate_stderr = (tmp_path / "aggregator-validate.stderr").read_text(encoding="utf-8")
    assert "Severity" in validate_stderr
    assert "appears only on OOS-tagged input findings" not in validate_stderr


def test_aggregate_missing_reviewer_failure_retries_then_succeeds(tmp_path: Path) -> None:
    # Issue #5077: an "input reviewers missing from merge output" slip is a recoverable LLM error and
    # must re-dispatch with validator feedback (like the OOS-attribution class), not degrade single-shot.
    findings = tmp_path / "in-missing-retry.md"
    _ = findings.write_text(_NON_OOS_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=1,
        fail_body=_MISSING_REVIEWER_FAIL,
        success_body=_MISSING_REVIEWER_SUCCESS,
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_VALIDATION_RETRIES="2"),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=true" in result.stdout
    assert "REASON=ok" in result.stdout
    # First dispatch failed the missing-reviewer check; the bounded retry re-dispatched and recovered.
    assert counter.read_text(encoding="utf-8") == "2"
    merged = findings.read_text(encoding="utf-8")
    assert "cursor-a-output.txt" in merged
    assert "cursor-b-output.txt" in merged
    # The retry prompt fed the missing-reviewer validator error back with generic (non-OOS) guidance.
    prompt = (tmp_path / "aggregator-prompt.md").read_text(encoding="utf-8")
    assert "Previous aggregation attempt rejected by validation" in prompt
    assert "input reviewers missing from merge output" in prompt
    retry_section = prompt.split("## Previous aggregation attempt rejected by validation", 1)[1]
    assert "Fix exactly the error reported above" in retry_section
    assert "preserving every input reviewer slot" in retry_section
    assert "appears only on OOS-tagged input findings" not in retry_section


def test_aggregate_missing_attribution_failure_retries_then_succeeds(tmp_path: Path) -> None:
    # Issue #5222: a "block missing reviewer attribution line" slip (a merged FINDING block that omits
    # its **Reviewer(s)**: line entirely) is a recoverable LLM error and must re-dispatch with validator
    # feedback (like the OOS-attribution #4881 and missing-reviewer #5077 classes), not degrade single-shot.
    findings = tmp_path / "in-missing-attr-retry.md"
    _ = findings.write_text(_NON_OOS_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=1,
        fail_body=_MISSING_ATTRIBUTION_FAIL,
        success_body=_MISSING_ATTRIBUTION_SUCCESS,
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_VALIDATION_RETRIES="2"),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=true" in result.stdout
    assert "REASON=ok" in result.stdout
    # First dispatch failed the missing-attribution-line check; the bounded retry re-dispatched and recovered.
    assert counter.read_text(encoding="utf-8") == "2"
    merged = findings.read_text(encoding="utf-8")
    assert "cursor-a-output.txt" in merged
    assert "cursor-b-output.txt" in merged
    # The retry prompt fed the missing-attribution validator error back with generic (non-OOS) guidance.
    prompt = (tmp_path / "aggregator-prompt.md").read_text(encoding="utf-8")
    assert "Previous aggregation attempt rejected by validation" in prompt
    assert "block missing reviewer attribution line" in prompt
    retry_section = prompt.split("## Previous aggregation attempt rejected by validation", 1)[1]
    assert "Fix exactly the error reported above" in retry_section
    assert "preserving every input reviewer slot" in retry_section
    assert "appears only on OOS-tagged input findings" not in retry_section


def test_aggregate_preamble_slip_failure_retries_then_succeeds(tmp_path: Path) -> None:
    # Issue #5503: aggregator output that references FINDING_N in prose but emits no conforming
    # `### FINDING_N:` blocks is a recoverable LLM slip and must re-dispatch with validator feedback
    # (like #4868/#5077/#5222), not stall Step 5 after a single attempt.
    findings = tmp_path / "in-preamble-retry.md"
    _ = findings.write_text(_PREAMBLE_SLIP_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=1,
        fail_body=_PREAMBLE_SLIP_FAIL,
        success_body=_PREAMBLE_SLIP_SUCCESS,
    )

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
    # First dispatch failed the preamble-slip check; the bounded retry re-dispatched and recovered.
    assert counter.read_text(encoding="utf-8") == "2"
    merged = findings.read_text(encoding="utf-8")
    assert "### FINDING_1: Merged in-scope" in merged
    # The retry prompt fed the preamble-slip validator error back to the aggregator.
    prompt = (tmp_path / "aggregator-prompt.md").read_text(encoding="utf-8")
    assert "Previous aggregation attempt rejected by validation" in prompt
    assert "preamble_finding_substring" in prompt


def test_aggregate_preamble_slip_failure_exhausts_retry_budget_without_stall(tmp_path: Path) -> None:
    # Issue #5503: when the preamble-slip class never recovers, the aggregator must degrade with
    # REASON=validation-failed (graceful; continues to the pre-vote gate) rather than the old
    # REASON=validation-exhausted, which stalled Step 5 after a single attempt.
    findings = tmp_path / "in-preamble-exhaust.md"
    _ = findings.write_text(_PREAMBLE_SLIP_INPUT, encoding="utf-8")
    counter = tmp_path / "dispatch-count.txt"
    dispatch = tmp_path / "counting-dispatch.sh"
    rts.write_aggregate_counting_dispatch_stub(
        dispatch,
        counter_file=counter,
        fail_attempts=99,
        fail_body=_PREAMBLE_SLIP_FAIL,
        success_body=_PREAMBLE_SLIP_SUCCESS,
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_VALIDATION_RETRIES="2"),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    # The recoverable slip re-dispatches up to budget, then degrades gracefully (no Step 5 stall).
    assert "REASON=validation-failed" in result.stdout
    assert "REASON=validation-exhausted" not in result.stdout
    # 1 initial dispatch + 2 retries.
    assert counter.read_text(encoding="utf-8") == "3"
    assert findings.read_text(encoding="utf-8") == _PREAMBLE_SLIP_INPUT


def test_validation_retry_prompt_is_failure_class_aware() -> None:
    # Issue #4881: OOS-attribution errors get OOS-specific guidance; other semantic errors get
    # generic guidance. Neither suggests dropping a reviewer slot (which would re-fail validation).
    oos_err = (
        "merged output lacks [OUT_OF_SCOPE] while listing reviewer 'cursor-b-output.txt' "
        "that appears only on OOS-tagged input findings\n"
    )
    oos_prompt = review_aggregate._validation_retry_prompt(base_prompt="BASE", validator_error=oos_err, attempt=2, max_attempts=3)  # pyright: ignore[reportPrivateUsage]
    assert "[OUT_OF_SCOPE]" in oos_prompt
    assert "every input reviewer must still appear" in oos_prompt
    assert "omit that reviewer slot" not in oos_prompt

    generic_err = "output block missing - **Severity**: blocking|important|latent|nit line\n"
    generic_prompt = review_aggregate._validation_retry_prompt(base_prompt="BASE", validator_error=generic_err, attempt=2, max_attempts=3)  # pyright: ignore[reportPrivateUsage]
    assert "Fix exactly the error reported above" in generic_prompt
    assert "preserving every input reviewer slot" in generic_prompt
    assert "appears only on OOS-tagged input findings" not in generic_prompt


def test_normalize_slot_reconciles_output_artifact_suffix() -> None:
    # Issue #5022: reviewer attribution can carry the "-output" artifact suffix (the reviewer output
    # file basename) while the aggregator's merged output names the bare slot. _normalize_slot must
    # canonicalize the suffix family (mirroring progress_report._progress_core_from_output) so both
    # spellings reconcile to one slot key. No real reviewer slot ends in these suffixes, so this
    # cannot collapse two distinct slots.
    assert review_aggregate._normalize_slot("cursor-specialist-correctness-output") == "cursor-specialist-correctness"
    assert review_aggregate._normalize_slot("cursor-specialist-correctness") == "cursor-specialist-correctness"
    assert review_aggregate._normalize_slot("cursor-specialist-correctness-output.txt") == "cursor-specialist-correctness"
    assert review_aggregate._normalize_slot("codex-specialist-correctness-output-ns-retry") == "codex-specialist-correctness"
    # The existing trailing-parenthetical strip still applies; a non-artifact slot is unchanged.
    assert review_aggregate._normalize_slot("merge-a (cursor)") == "merge-a"
    assert review_aggregate._normalize_slot("plan-fidelity") == "plan-fidelity"


def test_validate_aggregate_output_accepts_output_suffix_variant(tmp_path: Path) -> None:
    # Issue #5022 focused unit reproduction: input attribution carries the -output suffix; the merged
    # output names the bare slot. Before the fix, _normalize_slot left them distinct and the validator
    # returned rc=2 ("unknown reviewer slot in merge output"), discarding the round's dedup/merge.
    input_path = tmp_path / "input.md"
    output_path = tmp_path / "merged.md"
    _ = input_path.write_text(
        """### FINDING_1: Dup A
- **Reviewer(s)**: cursor-specialist-correctness-output
- **Severity**: important
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer(s)**: codex-specialist-correctness-output
- **Severity**: important
- **Concern**: same bug other words
- **Suggested revision**: fix
""",
        encoding="utf-8",
    )
    _ = output_path.write_text(
        """### FINDING_1: Merged correctness bug
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: important
- **Concern**: same bug
- **Suggested revision**: fix
""",
        encoding="utf-8",
    )

    rc, err = review_aggregate._validate_aggregate_output(input_path=input_path, output_path=output_path, input_mode="code")

    assert rc == 0, err


def test_aggregate_reconciles_output_suffix_slot_mismatch(tmp_path: Path) -> None:
    # Issue #5022 end-to-end: a real /implement run logged input attribution
    # "cursor-specialist-correctness-output" while the aggregator's merged output named the bare slot
    # "cursor-specialist-correctness". The merge must be applied (dedup preserved) instead of the
    # validator returning rc=2 and the round degrading to un-deduped findings.
    findings = tmp_path / "in-suffix.md"
    _ = findings.write_text(
        """### FINDING_1: Dup A
- **Reviewer(s)**: cursor-specialist-correctness-output
- **Severity**: important
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer(s)**: codex-specialist-correctness-output
- **Severity**: important
- **Concern**: same bug other words
- **Suggested revision**: fix
""",
        encoding="utf-8",
    )
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_executable(
        path=dispatch,
        body="""#!/usr/bin/env bash
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
### FINDING_1: Merged correctness bug
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: important
- **Concern**: same bug
- **Suggested revision**: fix
OUT
printf '%s\\n' "$out" > "${slots}.output-files"
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s\\nALL_OUTPUT_TOOLS=cursor\\n' "$out" "${slots}.output-files"
""",
    )

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
        path=dispatch,
        body="""#!/usr/bin/env bash
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
        path=dispatch,
        body="""#!/usr/bin/env bash
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


def test_committed_ref_round_dir_stamps_design_path(tmp_path: Path) -> None:
    """A --round-dir under --review-tmpdir round-stamps the committed failure pointer so a /design
    early-round aggregator failure stays diagnosable after a later round overwrites the stable
    top-level stderr (issue #4996).
    """
    review_tmp = tmp_path / "design"
    round_dir = review_tmp / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    validate_log = review_tmp / "aggregator-validate.stderr"

    ref = review_aggregate._committed_ref(failure_log=validate_log, review_tmpdir=review_tmp, session_env_path="", round_dir=round_dir)
    assert ref == "plan-review/round-1/aggregator-validate.stderr"
    phrase = review_aggregate._failure_see_phrase(failure_log=validate_log, review_tmpdir=review_tmp, session_env_path="", round_dir=round_dir)
    assert phrase == "See plan-review/round-1/aggregator-validate.stderr in the committed run log."

    # No round_dir and a non-round-prefixed tmpdir keep the legacy bare-path pointer.
    assert review_aggregate._committed_ref(failure_log=validate_log, review_tmpdir=review_tmp, session_env_path="") == str(validate_log)
    # A round_dir outside --review-tmpdir fails open to the bare path.
    outside = tmp_path / "other" / "round-1"
    assert review_aggregate._committed_ref(failure_log=validate_log, review_tmpdir=review_tmp, session_env_path="", round_dir=outside) == str(validate_log)


def test_round_stamped_forensics_match_real_failure_logs() -> None:
    """ROUND_STAMPED_FORENSICS must list exactly the failure-log basenames that _apply_aggregate_candidate
    and the dispatch loop hand to _failure_see_phrase with a round_dir, so every committed pointer
    round-stamps to a snapshotted per-round copy (#5004). aggregator-strip.stderr was a phantom with no
    producer; the strip stage's real failure log is aggregator-empty-merge.stderr.
    """
    expected = {
        "aggregator-dispatch.stderr",
        "aggregator-validate.stderr",
        "aggregator-empty-merge.stderr",
        "aggregator-scope-parity.stderr",
        "aggregator-mv.stderr",
    }
    assert set(review_aggregate.ROUND_STAMPED_FORENSICS) == expected
    assert "aggregator-strip.stderr" not in review_aggregate.ROUND_STAMPED_FORENSICS


def test_committed_ref_round_stamps_empty_merge_parity_and_mv(tmp_path: Path) -> None:
    """The empty-merge, scope-parity, and mv failure pointers now round-stamp like validate/dispatch so a
    /design early-round aggregator failure stays diagnosable after a later round overwrites the stable
    top-level stderr (#5004 completing #4996).
    """
    review_tmp = tmp_path / "design"
    round_dir = review_tmp / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    for name in ("aggregator-empty-merge.stderr", "aggregator-scope-parity.stderr", "aggregator-mv.stderr"):
        log = review_tmp / name
        assert review_aggregate._committed_ref(failure_log=log, review_tmpdir=review_tmp, session_env_path="", round_dir=round_dir) == f"plan-review/round-2/{name}"


def test_aggregate_round_dir_stamps_failure_pointer(tmp_path: Path) -> None:
    """End-to-end: --round-dir makes the /design validation-failure pointer round-aware so it
    resolves to the retained per-round snapshot rather than the clobbered top-level path (#4996).
    """
    review_tmp = tmp_path / "design"
    round_dir = review_tmp / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
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
        "--round-dir",
        str(round_dir),
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch)),
    )

    assert result.returncode == 0, result.stderr
    assert "REASON=validation-exhausted" in result.stdout
    issues_text = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "See plan-review/round-1/aggregator-validate.stderr in the committed run log." in issues_text


def test_aggregate_code_mode_accepts_blocking_severity(tmp_path: Path) -> None:
    findings = tmp_path / "in-blocking.md"
    _ = findings.write_text(
        """### FINDING_1: Block A
- **Reviewer**: cursor-a-output.txt
- **Severity**: important
- **Concern**: same issue
- **Suggested revision**: fix

### FINDING_2: Block B
- **Reviewer**: cursor-b-output.txt
- **Severity**: latent
- **Concern**: same issue other words
- **Suggested revision**: fix

""",
        encoding="utf-8",
    )
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_executable(
        path=dispatch,
        body="""#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="$2"; shift 2 ;;
    *) shift ;;
  esac
done
out=$(jq -r '.output' "$slots")
cat >"$out" <<'EOF'
### FINDING_1: merged blocking
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: blocking
- **Concern**: normalized concern
- **Suggested revision**: fix

EOF
printf '%s\\n' "$out" > "${slots}.output-files"
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s\\nALL_OUTPUT_TOOLS=cursor\\n' "$out" "${slots}.output-files"
""",
    )

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
    assert "- **Severity**: blocking" in findings.read_text(encoding="utf-8")


def test_prune_nit_code_mode_marks_oos_and_preserves_ids(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    _ = findings.write_text(
        """### FINDING_1: Important
- **Severity**: important
- **Concern**: keep

### FINDING_2: Nit title
- **Severity**: nit
- **Concern**: style
""",
        encoding="utf-8",
    )

    result = run_review("prune-nit-findings", "--findings-file", str(findings), "--input-mode", "code")

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    text = findings.read_text(encoding="utf-8")
    assert "### FINDING_2: [OUT_OF_SCOPE] Nit title" in text
    assert "### FINDING_1:" in text
    assert "### FINDING_2:" in text


def test_prune_nit_disabled_is_noop(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    original = "### FINDING_1: Nit\n- **Severity**: nit\n"
    _ = findings.write_text(original, encoding="utf-8")

    result = run_review(
        "prune-nit-findings",
        "--findings-file",
        str(findings),
        "--input-mode",
        "code",
        env={"LARCH_PRUNE_NITS_DISABLED": "1"},
    )

    assert result.returncode == 0, result.stderr
    assert "STATUS=disabled" in result.stdout
    assert findings.read_text(encoding="utf-8") == original


def test_prune_nit_no_blocks_ok(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    _ = findings.write_text("no findings\n", encoding="utf-8")

    result = run_review("prune-nit-findings", "--findings-file", str(findings))

    assert result.returncode == 0, result.stderr
    assert "STATUS=ok" in result.stdout
    assert "PRUNED_COUNT=0" in result.stdout


def test_prune_nit_plan_mode_moves_to_oos_and_renumbers(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    oos = tmp_path / "oos.md"
    _ = findings.write_text(
        """### FINDING_1: Keep important
- **Severity**: important
- **Concern**: keep

### FINDING_2: Move nit
- **Severity**: nit
- **Concern**: move

### FINDING_3: Keep latent
- **Severity**: latent
- **Concern**: keep latent
""",
        encoding="utf-8",
    )
    _ = oos.write_text("### OOS_1: Existing\n- **Concern**: old\n\n", encoding="utf-8")

    result = run_review(
        "prune-nit-findings",
        "--findings-file",
        str(findings),
        "--oos-file",
        str(oos),
        "--input-mode",
        "plan",
    )

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    text = findings.read_text(encoding="utf-8")
    assert "Move nit" not in text
    assert "### FINDING_2: Keep latent" in text
    oos_text = oos.read_text(encoding="utf-8")
    assert "### OOS_1: Existing" in oos_text
    assert "### OOS_2: Move nit" in oos_text


def test_prune_nit_plan_oos_replace_failure_restores_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    findings = tmp_path / "findings.md"
    oos = tmp_path / "oos.md"
    original_findings = "### FINDING_1: Nit\n- **Severity**: nit\n- **Concern**: move\n"
    original_oos = "### OOS_1: Existing\n- **Concern**: old\n"
    _ = findings.write_text(original_findings, encoding="utf-8")
    _ = oos.write_text(original_oos, encoding="utf-8")
    real_move = shutil.move
    calls = {"count": 0}

    def flaky_move(src: str, dst: str) -> Any:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("simulated oos move failure")
        return real_move(src, dst)

    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setattr(review_aggregate.shutil, "move", flaky_move)

    rc = review_aggregate.prune_nit_findings([
        "--findings-file",
        str(findings),
        "--oos-file",
        str(oos),
        "--input-mode",
        "plan",
    ])

    stdout = capsys.readouterr().out
    assert rc == 0
    assert "STATUS=skipped" in stdout
    assert "PRUNED_COUNT=0" in stdout
    assert "INSCOPE_REMAINING=0" in stdout
    assert findings.read_text(encoding="utf-8") == original_findings
    assert oos.read_text(encoding="utf-8") == original_oos


def test_aggregate_default_dispatch_argv_uses_python_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    _ = findings.write_text(
        """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix
""",
        encoding="utf-8",
    )
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "DISPATCH_OK=false\n", "")

    monkeypatch.delenv("AGGREGATE_DISPATCH_SH", raising=False)
    monkeypatch.setattr(review_aggregate.subprocess, "run", fake_run)
    monkeypatch.setattr(review_aggregate, "_PLUGIN_ROOT", ROOT)

    _ = review_aggregate.aggregate_findings(
        [
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
        ]
    )

    assert captured
    dispatch_argv = captured[0]
    assert dispatch_argv[:4] == [sys.executable, str(ROOT / "python" / "cli.py"), "agent", "dispatch-waterfall"]


def test_aggregate_revision_traceability_strict_fails(tmp_path: Path) -> None:
    findings = tmp_path / "trace.md"
    _ = findings.write_text(
        """### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix
""",
        encoding="utf-8",
    )
    dispatch = tmp_path / "stub-dispatch.sh"
    rts.write_executable(
        path=dispatch,
        body="""#!/usr/bin/env bash
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
### FINDING_1: merged
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: important
- **Concern**: same bug
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-a-output.txt: invented fix text not in any input
OUT
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s.output-files\\n' "$out" "$slots"
printf '%s\\n' "$out" > "${slots}.output-files"
""",
    )

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
        env=_aggregate_env(tmp_path, AGGREGATE_DISPATCH_SH=str(dispatch), LARCH_AGGREGATE_REVISION_TRACE_STRICT="1"),
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=validation-exhausted" in result.stdout
    validate_stderr = (tmp_path / "aggregator-validate.stderr").read_text(encoding="utf-8")
    assert "not traceable" in validate_stderr


def test_aggregate_plan_scope_reduction_parity_rejects_accidental_merge(tmp_path: Path) -> None:
    findings = tmp_path / "plan-parity" / "in.md"
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
    original = findings.read_text(encoding="utf-8")
    dispatch = findings.parent / "dispatch.sh"
    rts.write_executable(
        path=dispatch,
        body="""#!/usr/bin/env bash
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
- **Concern**: remove unrelated scope. Scenario: bloat
- **Proposed resolution**: remove it
OUT
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s.output-files\\n' "$out" "$slots"
printf '%s\\n' "$out" > "${slots}.output-files"
""",
    )

    result = run_review(
        "aggregate-findings",
        "--findings-file",
        str(findings),
        "--review-tmpdir",
        str(findings.parent),
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
    assert "AGGREGATED=false" in result.stdout
    assert findings.read_text(encoding="utf-8") == original


def test_finding_blocks_keep_heading_and_caller_local_strip() -> None:
    blocks = review_aggregate._finding_blocks("\n### FINDING_7: title\nbody\n\n")

    assert blocks == ["### FINDING_7: title\nbody"]
    assert review_aggregate._finding_id_from_block(blocks[0]) == "FINDING_7"


def test_renumber_findings_uses_heading_inclusive_blocks() -> None:
    assert review_aggregate._renumber_findings(
        "### FINDING_9: old\nbody\n\n### FINDING_10: old\nbody\n",
    ) == "### FINDING_1: old\nbody\n\n### FINDING_2: old\nbody\n"
