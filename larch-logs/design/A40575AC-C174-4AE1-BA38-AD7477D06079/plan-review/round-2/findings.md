### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-review-core.sh:535-547
- **Concern**: Proposed review-core integration test cannot exercise the real tally→emit overwrite chain. Scenario: test-review-core.sh always stubs REVIEW_CORE_TALLY_VOTES_SH and REVIEW_CORE_EMIT_TALLY_SH to $TMP/tally.sh and $TMP/emit.sh; stub emit unconditionally writes a placeholder oos-accepted-review.md and never calls oos-serialize.sh, so extending assertions there would not catch FINDING_1 regressions in production emit-tally.sh even though Failure modes §1 lists this harness as mitigation
- **Proposed resolution**: Either add a dedicated case (e.g. run_core_real_oos) that keeps upstream stubs but points REVIEW_CORE_TALLY_VOTES_SH/REVIEW_CORE_EMIT_TALLY_SH at the real scripts with minimal ballot/voter fixtures, or drop the test-review-core.sh change and rely on test-tally-code-votes.sh plus test-emit-tally.sh for FINDING_1 coverage

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-review-core.sh:312-339
- **Concern**: Planned review-core integration case cannot exercise emit-tally preservation. Scenario: REVIEW_CORE_EMIT_TALLY_SH is stubbed to emit.sh which always truncates oos-accepted-review.md to a placeholder; extending test-review-core.sh per plan would not detect FINDING_1 regressions unless the harness invokes real emit-tally.sh (and tally-code-votes.sh)
- **Proposed resolution**: Omit test-review-core.sh from this PR; test-emit-tally.sh and test-tally-code-votes.sh already cover the production overwrite chain at minimum change

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:256-339
- **Concern**: Planned review-core integration cannot exercise the emit-tally preservation chain because the harness always stubs tally-code-votes.sh and emit-tally.sh; the emit stub unconditionally overwrites oos-accepted-review.md with placeholder content. Scenario: Adding canonical-header assertions to the existing parent-run case would not detect FINDING_1 regressions (stub emit still replaces tally output), so the only named end-to-end harness gives false confidence while test-emit-tally.sh covers emit in isolation only
- **Proposed resolution**: Add one review-core case that invokes the real skills/review/scripts/tally-code-votes.sh and emit-tally.sh (omit REVIEW_CORE_TALLY_VOTES_SH / REVIEW_CORE_EMIT_TALLY_SH overrides), or extend the stubs so emit preserves a pre-written oos-accepted-review.md when OOS_ACCEPTED_COUNT>0 in review-tally.env

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-review-core.sh:256-348
- **Concern**: Plan adds review-core integration for FINDING_1 but harness always stubs REVIEW_CORE_TALLY_VOTES_SH and REVIEW_CORE_EMIT_TALLY_SH. Scenario: Failure mode 1 cites review-core as mitigation yet default run_core never invokes real emit-tally; fixture-only assertions would not catch serialize overwrite regressions
- **Proposed resolution**: Drop test-review-core.sh from this plan (test-emit-tally.sh already covers the skip guard) or add one case that overrides REVIEW_CORE_EMIT_TALLY_SH to the real emit-tally.sh with stub tally seeding review-tally.env OOS_ACCEPTED_COUNT and pre-written oos-accepted-review.md

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-script-interface-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:535-546
- **Concern**: Planned review-core integration cannot exercise the emit-tally skip guard or tally producer normalization. Scenario: run_core always sets REVIEW_CORE_TALLY_VOTES_SH and REVIEW_CORE_EMIT_TALLY_SH to stub scripts; stub emit.sh unconditionally writes # oos to oos-accepted-review.md and stub tally.sh never emits OOS_ACCEPTED_COUNT or accepted OOS blocks, so extending fixtures per the plan still will not catch FINDING_1 (emit-tally overwriting tally output before copy_to_parent)
- **Proposed resolution**: For the FINDING_1 case either wire real tally-code-votes.sh and emit-tally.sh (minimal ballot/voter/collect fixture) or drop the test-review-core extension and rely on the already-planned test-emit-tally.sh and test-tally-code-votes.sh unit coverage
