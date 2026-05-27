### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1220-1258
- **Concern**: New REVIEW_CORE_STATUS=aggregator-empty-merge is not mapped to terminal complete in review-and-fix. Scenario: After Item B, review-core emits aggregator-empty-merge with exit 0; review-and-fix case * sets REVIEW_AND_FIX_STATUS=aggregator-empty-merge; review-implement-step5-loop.sh:199-203 treats unknown IRF status as stall (round-failed-aggregator-empty-merge)
- **Proposed resolution**: Extend the zero-findings|ok) arm to include aggregator-empty-merge so status=complete while still emitting REVIEW_CORE_STATUS=aggregator-empty-merge on the KV stream

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:491-503
- **Concern**: Existing agg-zero harness still expects voter dispatch and REVIEW_CORE_STATUS=ok. Scenario: Same stub (aggregate-zero-success-stub.sh) will hit the new short-circuit; assertions on VOTER_*_STATUS=launched and REVIEW_CORE_STATUS=ok will fail even if the new section passes
- **Proposed resolution**: Rewrite the agg-zero block to expect REVIEW_CORE_STATUS=aggregator-empty-merge and no dispatch-voters invocation (or fold into the planned empty-merge section and delete conflicting assertions)

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:14-18
- **Concern**: Item A jq -e pairing check can pass with zero matching rows. Scenario: Plan Failure modes #3 documents this; jq -e exits 0 on empty output, so wrong/missing slot names would not fail despite got_count==2 passing on fallback_group alone
- **Proposed resolution**: Use the plan’s length==2 and all(.fallback_group==$fg) expression from Failure modes #3 in Item A, not the bare select|== filter mirrored from test-decompose-panel-dispatch.sh

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-review-core.sh:491-495
- **Concern**: Plan adds a new empty-merge test using the same aggregate-zero-success-stub but does not retire the existing old-behavior assertions. Scenario: The suite will contain two tests for REASON=ok MERGED_COUNT=0 with incompatible expectations: one expects voter launch and REVIEW_CORE_STATUS=ok while the new behavior should skip voters and emit aggregator-empty-merge
- **Proposed resolution**: Replace this existing agg-zero block with the new skip assertions, or change it to use a MERGED_COUNT=1 aggregate stub if it is meant to keep covering the normal voter path

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:542-598
- **Concern**: Proposed MERGED_COUNT default treats a missing key as zero despite the plan's stated graceful-degrade behavior. Scenario: If an overridden or older aggregator emits REASON=ok without MERGED_COUNT, review-core will skip voter dispatch and emit an empty tally for a ballot that may still contain findings
- **Proposed resolution**: Do not default empty MERGED_COUNT to 0 for this branch; require the raw parsed value to be exactly 0 before calling emit_zero_findings_branch

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-90
- **Concern**: The Item A jq assertion shown in the concrete edit passes when the slot selector matches no rows. Scenario: A slot-name regression can preserve two rows per fallback_group while the new per-slot assertion emits no jq results and exits successfully, leaving the static pairing gap partly open
- **Proposed resolution**: Use the length-checking jq expression already described in the plan's mitigation: collect matching rows, require length == 2, and require all fallback_group values equal the expected group

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1220-1258, skills/review-and-fix/scripts/review-implement-step5-loop.sh:171-203
- **Concern**: New REVIEW_CORE_STATUS aggregator-empty-merge is not integrated into downstream status handling. Scenario: review-core exits 0 with aggregator-empty-merge, review-and-fix falls through to status=aggregator-empty-merge, then the Step 5 loop treats that unknown status as a stall via round-failed-aggregator-empty-merge
- **Proposed resolution**: Minimum-change fix: keep REVIEW_CORE_STATUS=zero-findings for this branch and assert skipped voter dispatch separately, or add aggregator-empty-merge to the complete/clean status cases in review-and-fix and Step 5 plus contract tests/docs

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-90
- **Concern**: Proposed static fallback_group jq assertion can pass when it selects zero rows. Scenario: If cursor-plan-arch/codex-plan-arch slot names drift or disappear while two renamed rows still carry fallback_group=plan-arch, jq -e with no output exits success and the harness misses the pairing break
- **Proposed resolution**: Replace the proposed selector with the length/all form from the plan failure-mode mitigation: jq -s requires exactly two matching slot rows and all fallback_group values equal the expected group

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-90
- **Concern**: Item A proposes per-archetype jq without a match-count guard; plan Failure modes #3 already notes jq -e passes on zero matches. Scenario: If slot names drift so the selector matches zero rows, the new assertion passes while got_count still passes on fallback_group alone
- **Proposed resolution**: Use the Failure modes #3 expression: length == 2 and all(.[]; .fallback_group == $fg) instead of the bare select pipeline in the Item A insertion block

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-90
- **Concern**: Proposed static-slot jq assertion can pass on zero matched slots. Scenario: The harness can still miss a slot-identity wiring regression because jq -e succeeds when the selector emits no rows, while the existing got_count check only proves two rows somewhere have fallback_group=plan-<archetype>
- **Proposed resolution**: Make Item A use a slurped length-and-all assertion, e.g. jq -s -e '[.[] | select(.slot == ("cursor-plan-" + $a) or .slot == ("codex-plan-" + $a))] | length == 2 and all(.[]; .fallback_group == $fg)'

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:491-503
- **Concern**: Existing agg-zero case still expects REVIEW_CORE_STATUS=ok and launched voters. Scenario: The stub already emits REASON=ok MERGED_COUNT=0; Item B changes production to aggregator-empty-merge and skips voters, so this test fails while the plan only adds a new section
- **Proposed resolution**: Update the agg-zero block to expect REVIEW_CORE_STATUS=aggregator-empty-merge, no voter dispatch, and the same zero-count artifacts; or split pre/post behavior explicitly

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-19
- **Concern**: Item A proposes jq -e slot filter without empty-match guard. Scenario: Plan failure modes note jq -e exits 0 on zero matching rows; wrong/missing slot names could pass alongside got_count==2, leaving the harness gap open
- **Proposed resolution**: Ship the length==2 and all(.fallback_group==$fg) jq from the plan failure-modes mitigation in Item A, not the bare select-only filter in the UPDATED block

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.md:31
- **Concern**: REVIEW_CORE_STATUS enum omits aggregator-empty-merge. Scenario: Item C extends artifact bullets only; operators and parsers reading line 31 will not see the new terminal status the harness asserts
- **Proposed resolution**: Add aggregator-empty-merge to the line 31 status union while editing review-core.md for Item C

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1220-1258; skills/review-and-fix/scripts/review-implement-step5-loop.sh:171-203
- **Concern**: Plan introduces REVIEW_CORE_STATUS=aggregator-empty-merge without downstream status handling. Scenario: review-and-fix preserves the unknown status, then Step 5 maps it through the default branch to round-failed-aggregator-empty-merge and exits 2, so a clean attestation-only merge becomes a stalled review
- **Proposed resolution**: Minimum-change fix: reuse REVIEW_CORE_STATUS=zero-findings for the new branch; if the distinct status is required, add it to the complete cases in review-and-fix and Step 5 plus matching tests/docs

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-90
- **Concern**: The proposed static-slot jq assertion does not prove both expected slots are present. Scenario: A manifest with one correct cursor/codex slot plus another unrelated row carrying the same fallback_group can satisfy got_count, and the proposed streaming jq can still emit only a truthy matched row
- **Proposed resolution**: Use the length==2 and all(.[]; .fallback_group == $fg) set assertion already sketched in the plan failure-mode mitigation

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:491-495
- **Concern**: Plan adds a new empty-merge section but leaves the existing agg-zero block asserting REVIEW_CORE_STATUS=ok and VOTER_*_STATUS=launched with the same aggregate-zero-success-stub. Scenario: After Item B the shared stub path emits aggregator-empty-merge and skips voters; make test-review-core fails on the old assertions even if the new section passes
- **Proposed resolution**: Rewrite the agg-zero block (or replace it with the planned section) to expect REVIEW_CORE_STATUS=aggregator-empty-merge and no dispatch-voters invocation; do not keep both contradictory cases on one stub

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:86-90
- **Concern**: Item A's proposed streaming jq -e assertion does not reliably close the static-slot pairing gap. Scenario: jq -e returns the status of the last output, so cursor-plan-arch can evaluate false and codex-plan-arch true while the assertion exits 0; an empty selector can also pass
- **Proposed resolution**: Make the actual planned insertion use the slurped length == 2 and all(.[]; .fallback_group == $fg) expression from the plan's mitigation

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1220-1258; skills/review-and-fix/scripts/review-implement-step5-loop.sh:171-203
- **Concern**: The new REVIEW_CORE_STATUS=aggregator-empty-merge is not mapped by downstream review wrappers. Scenario: review-core can exit 0 with aggregator-empty-merge, review-and-fix falls through to that raw status, and Step 5 treats it as unknown and stalls with round-failed-aggregator-empty-merge
- **Proposed resolution**: Either reuse REVIEW_CORE_STATUS=zero-findings for this branch or add aggregator-empty-merge to the complete/no-findings status handling in review-and-fix and Step 5, with focused wrapper test coverage

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:491-495
- **Concern**: The plan says to add empty-merge skip coverage but does not update the existing agg-zero test that asserts the old voter-launch behavior. Scenario: The same aggregate-zero-success-stub scenario will now skip dispatch-code-voters, so make test-review-core will fail on expected REVIEW_CORE_STATUS=ok and VOTER_*_STATUS=launched
- **Proposed resolution**: Revise or replace the existing agg-zero block to expect the new empty-merge branch and no voter dispatch instead of only adding a new section

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:596-598
- **Concern**: The planned MERGED_COUNT default contradicts the stated graceful-degrade edge case. Scenario: The snippet sets aggregate_merged_count="${aggregate_merged_count:-0}", so REASON=ok with a missing MERGED_COUNT takes the empty-merge skip path instead of falling through to current voter dispatch behavior
- **Proposed resolution**: Branch only when the raw MERGED_COUNT key is present and equals 0, or remove the stated absent-key graceful-degrade requirement

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-cross-ref, Codex-dyn-cross-ref
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:1332, skills/review/scripts/test-aggregate-findings.sh:1386
- **Concern**: Plan cites these lines as exercising aggregator-output-phase2.txt and aggregator-output-phase3.txt, but both current assertions only check PHASE2_SLOTS with aggregator-output-phase2.txt; no phase3 output is present at either cited line.. Scenario: An implementer following Item C may believe phase3 output already has harness evidence and may cite or test the wrong location while only phase2 is covered by the cited lines.
- **Proposed resolution**: Revise the plan text to say the cited harness lines exercise phase2 only; keep aggregate-findings.md:26 as the phase3 documentation citation or replace with an actual phase3 test citation if one exists.

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-shell-extraction, Codex-dyn-shell-extraction
- **Severity**: nit
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:95-97; skills/review/scripts/review-core.sh:453-512
- **Concern**: Plan variable inventory omits REVIEW_TMPDIR, which the extracted zero-findings block reads throughout for artifact paths and tally inputs. Scenario: No explicit passthrough is required in a regular bash function because REVIEW_TMPDIR is initialized and validated before this branch, but the plan's scope audit is not exhaustive under its own stated check
- **Proposed resolution**: Add REVIEW_TMPDIR to the extraction audit; keep the minimum-change regular function shape with only the status token argument
