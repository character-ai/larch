# Review Round 1

- Mode: `diff`
- 4 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: security OOS sidecar is written under the round directory instead of the session root
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Security OOS from code review is being written under the round-N review directory instead of the session-root sidecar that ship, disposition checkpoint, and oos-pipeline inspect, so private SECURITY.md disposition can be skipped and the observation can be lost on cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Append security OOS to the implement session parent (match oos_accepted_out / _aggregate_parent), not review_tmpdir; add nested-round test for parent sidecar and clean public oos.md.
  - From codex-specialist-correctness: Route code-review security OOS to the aggregate parent/session tmpdir sidecar, or copy the round sidecar to $IMPLEMENT_TMPDIR/security-oos-observations.md before checkpoints and cleanup.
  - From cursor-specialist-edge-cases: Append via _aggregate_parent(session root) and test nested round-N layout.
  - From codex-specialist-edge-cases: Write security OOS to the aggregate/session parent sidecar and test that checkpoint stalls on the root sidecar.
  - From cursor-specialist-testing: Assert sensitive text is absent from oos.md and present only in security-oos-observations.md.
  - From codex-specialist-testing: Route security OOS to the aggregate parent, matching oos_accepted_out.parent, or pass an explicit security_sidecar path into _record_public_oos_artifact. Add a regression test with --session-env-path that asserts the parent sidecar is populated and public oos.md remains clean.


### FINDING_2: aggregate OOS pool is ignored, making pool writes effectively dead state
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-oos-routing
- **Severity**: important
- **Concern**: _promote_aggregate_oos_pool ignores oos-aggregate-pool.md, so vote-accepted review OOS from earlier rounds can be lost before Step 9a.1 and the pool becomes write-only dead state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Read pool, filter to non-security blocks with Result=accepted, dedupe against the sink and main-agent blocks, and promote those accepted pool blocks into oos-accepted-review.md.
  - From dyn-dyn-oos-routing: Either remove implement pool writes when emit no longer consumes the pool, or restore pool promotion with the same Result=accepted filter and tests design uses, so both skills share one aggregate contract.


### FINDING_3: rejected OOS audit skips legacy FINDING_N headings without an OOS tag
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: Rejected-OOS auditing skips legacy FINDING_N blocks that lack an OOS tag in the heading, so scope-drift or neutral-rescued items in oos.md never show up in the final audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Treat non-accepted oos.md blocks with Vote tally footers as audit rows regardless of heading prefix when scope is oos.
  - From cursor-specialist-testing: Add one test with ### FINDING_N: [OUT_OF_SCOPE] and Result=rejected in round-*/oos.md.


### FINDING_6: direct OOS_N ballots are still counted as empty
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing, cursor-specialist-testing
- **Severity**: important
- **Concern**: _ballot_block_count counts only FINDING_N headings, so pruned or aggregated ballots containing only direct OOS_N blocks are treated as empty and skip voters; related all-OOS branch coverage is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Count both FINDING_N and OOS_N headings, for example with voting.BALLOT_HEADING_RE or the same split logic used by tally. Add an all-direct-OOS ballot test, including the normal path and the validation-exhausted / empty-merge branches named in the plan.
  - From codex-specialist-testing: Count both FINDING_N and OOS_N headings, for example with voting.BALLOT_HEADING_RE or the same split logic used by tally. Add an all-direct-OOS ballot test, including the normal path and the validation-exhausted / empty-merge branches named in the plan.
  - From cursor-specialist-testing: Add branch-specific tests with all-OOS ballots asserting voter rows plus review-tally.env and oos-accepted-review.md when votes pass.
  - From cursor-specialist-testing: Invoke _prune_nits_for_ballot or a minimal review-core path and assert OOS blocks remain in findings.md.


