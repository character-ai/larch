### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_fixer_lane.py:893-906
- **Concern**: Crash-finalize provenance read failures are not mapped to the required bail result. Scenario: If git cannot read the commit body or ancestry, _git_read raises LaneClosedError; crash finalization emits crash-finalization-failed instead of crashed-lane-head-unverified
- **Proposed resolution**: Make the shared validator convert provenance read failures to False, so crash finalization returns the prescribed operator-bail result while normal dispatch still raises LaneClosedError

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ci.py:844-871
- **Concern**: Normal dispatch lacks a subject-only/no-trailer regression case. Scenario: A direct HEAD change or uncommitted-salvage path could accept the original spoofable subject-only commit while crash-finalize coverage passes
- **Proposed resolution**: Add subject-only cases to the normal-dispatch matrix for both direct-HEAD and uncommitted-salvage paths; assert no reship and preserved offending commit

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ci.py
- **Concern**: Dispatch `fixer-produced-change` path lacks a mandatory subject-only-without-trailer regression test. Scenario: The plan closes the `final_head != identity.starting_head` reship bypass and lists that edge case, but mandatory tests cover crash finalize (`test_crashed_lane_spoofed_subject_without_trailer_bails`), shell finalize, uncommitted salvage, wrong-step/duplicate parametrization, and a mocked post-salvage `LaneClosedError`. None require a launcher that commits a subject-only commit on the direct-HEAD-change branch, so that primary bypass can regress without a failing test.
- **Proposed resolution**: Add a dispatch test (or extend the parametrized matrix with a `missing-trailer` case on the direct-HEAD-change path) where the launcher commits `Apply CI fixer working-tree edits ({tier})` with no `Larch-Salvage-Step` trailer; assert fail-closed with no `reship` and no rounds/lineage advance.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ci.py
- **Concern**: Normal direct-HEAD dispatch lacks a subject-only negative test. Scenario: The plan adds shared provenance validation on `_dispatch` when `launcher_exit == 0` and `final_head != identity.starting_head` (`fixer-produced-change`), and lists that missing-trailer case as an edge case. Mandatory tests cover crash finalize subject-only bail (`test_crashed_lane_spoofed_subject_without_trailer_bails`) and parametrized wrong-step/duplicate trailers, but no named test requires the normal direct-HEAD path to fail closed when a launcher leaves a subject-only commit with no `Larch-Salvage-Step` trailer. An implementation could wire validation only to the uncommitted-salvage branch and still pass the listed suite.
- **Proposed resolution**: Add an explicit `_dispatch` negative test where a committing launcher advances `HEAD` with the expected subject but no trailer; assert `LaneClosedError` (or `operator-bail` if exercised through `main()`), no `reship`, and no rounds/lineage advance.
