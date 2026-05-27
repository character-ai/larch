### FINDING_1: aggregator-empty-merge is not treated as terminal complete downstream
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: New `REVIEW_CORE_STATUS=aggregator-empty-merge` can exit review-core successfully but then fall through downstream wrappers as an unknown status, causing Step 5 to report a stalled/failed round instead of a clean no-findings completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge, Cursor-Pragmatic: Extend the zero-findings|ok) arm to include aggregator-empty-merge so status=complete while still emitting REVIEW_CORE_STATUS=aggregator-empty-merge on the KV stream
  - From Codex-Edge: Minimum-change fix: keep REVIEW_CORE_STATUS=zero-findings for this branch and assert skipped voter dispatch separately, or add aggregator-empty-merge to the complete/clean status cases in review-and-fix and Step 5 plus contract tests/docs
  - From Codex-Pragmatic: Minimum-change fix: reuse REVIEW_CORE_STATUS=zero-findings for the new branch; if the distinct status is required, add it to the complete cases in review-and-fix and Step 5 plus matching tests/docs
  - From Codex-Requirements: Either reuse REVIEW_CORE_STATUS=zero-findings for this branch or add aggregator-empty-merge to the complete/no-findings status handling in review-and-fix and Step 5, with focused wrapper test coverage

### FINDING_2: Existing agg-zero test still asserts old voter-dispatch behavior
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds new empty-merge coverage but leaves the existing `agg-zero` test using the same `aggregate-zero-success-stub.sh` scenario with incompatible expectations: `REVIEW_CORE_STATUS=ok` and launched voters instead of `aggregator-empty-merge` and skipped voter dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite the agg-zero block to expect REVIEW_CORE_STATUS=aggregator-empty-merge and no dispatch-voters invocation (or fold into the planned empty-merge section and delete conflicting assertions)
  - From Codex-Arch: Replace this existing agg-zero block with the new skip assertions, or change it to use a MERGED_COUNT=1 aggregate stub if it is meant to keep covering the normal voter path
  - From Cursor-Pragmatic: Update the agg-zero block to expect REVIEW_CORE_STATUS=aggregator-empty-merge, no voter dispatch, and the same zero-count artifacts; or split pre/post behavior explicitly
  - From Cursor-Requirements: Rewrite the agg-zero block (or replace it with the planned section) to expect REVIEW_CORE_STATUS=aggregator-empty-merge and no dispatch-voters invocation; do not keep both contradictory cases on one stub
  - From Codex-Requirements: Revise or replace the existing agg-zero block to expect the new empty-merge branch and no voter dispatch instead of only adding a new section

### FINDING_3: Static fallback_group jq assertion can pass without proving expected slots
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Item A’s proposed streaming `jq -e` slot assertion can pass when selectors match zero rows, when only the last emitted result is truthy, or when fallback-group counts are satisfied by unrelated rows, so it does not reliably prove both expected cursor/codex slots are present and paired with the intended `fallback_group`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use the plan’s length==2 and all(.fallback_group==$fg) expression from Failure modes #3 in Item A, not the bare select|== filter mirrored from test-decompose-panel-dispatch.sh
  - From Codex-Arch: Use the length-checking jq expression already described in the plan's mitigation: collect matching rows, require length == 2, and require all fallback_group values equal the expected group
  - From Codex-Edge: Replace the proposed selector with the length/all form from the plan failure-mode mitigation: jq -s requires exactly two matching slot rows and all fallback_group values equal the expected group
  - From Cursor-Innovation: Use the Failure modes #3 expression: length == 2 and all(.[]; .fallback_group == $fg) instead of the bare select pipeline in the Item A insertion block
  - From Codex-Innovation: Make Item A use a slurped length-and-all assertion, e.g. jq -s -e '[.[] | select(.slot == ("cursor-plan-" + $a) or .slot == ("codex-plan-" + $a))] | length == 2 and all(.[]; .fallback_group == $fg)'
  - From Cursor-Pragmatic: Ship the length==2 and all(.fallback_group==$fg) jq from the plan failure-modes mitigation in Item A, not the bare select-only filter in the UPDATED block
  - From Codex-Pragmatic: Use the length==2 and all(.[]; .fallback_group == $fg) set assertion already sketched in the plan failure-mode mitigation
  - From Codex-Requirements: Make the actual planned insertion use the slurped length == 2 and all(.[]; .fallback_group == $fg) expression from the plan's mitigation

### FINDING_4: Missing MERGED_COUNT is defaulted to zero instead of degrading to voter dispatch
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: latent
- **Concern**: The proposed `MERGED_COUNT` handling treats an absent key as `0`, so an overridden or older aggregator emitting `REASON=ok` without `MERGED_COUNT` would incorrectly take the empty-merge skip path rather than preserving the stated graceful-degrade behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not default empty MERGED_COUNT to 0 for this branch; require the raw parsed value to be exactly 0 before calling emit_zero_findings_branch
  - From Codex-Requirements: Branch only when the raw MERGED_COUNT key is present and equals 0, or remove the stated absent-key graceful-degrade requirement

### FINDING_5: review-core.md status enum omits aggregator-empty-merge
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Concern**: The documentation update extends artifact bullets but leaves the status enum missing the new `aggregator-empty-merge` terminal status, so operators and parsers may not see the status the harness asserts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add aggregator-empty-merge to the line 31 status union while editing review-core.md for Item C

### FINDING_6: Plan cites phase3 harness coverage that currently appears to cover only phase2
- **Reviewer(s)**: Cursor-dyn-cross-ref, Codex-dyn-cross-ref
- **Severity**: latent
- **Concern**: The plan cites `test-aggregate-findings.sh` lines as exercising both `aggregator-output-phase2.txt` and `aggregator-output-phase3.txt`, but the reviewers report both current assertions only check `PHASE2_SLOTS` with phase2 output, which can mislead implementation or verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-ref, Codex-dyn-cross-ref: Revise the plan text to say the cited harness lines exercise phase2 only; keep aggregate-findings.md:26 as the phase3 documentation citation or replace with an actual phase3 test citation if one exists.

### FINDING_7: Extraction audit omits REVIEW_TMPDIR dependency
- **Reviewer(s)**: Cursor-dyn-shell-extraction, Codex-dyn-shell-extraction
- **Severity**: nit
- **Concern**: The plan’s variable inventory for extracting the zero-findings block omits `REVIEW_TMPDIR`, which the block reads for artifact paths and tally inputs, making the scope audit incomplete even though a regular Bash function likely does not need explicit passthrough.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shell-extraction, Codex-dyn-shell-extraction: Add REVIEW_TMPDIR to the extraction audit; keep the minimum-change regular function shape with only the status token argument
