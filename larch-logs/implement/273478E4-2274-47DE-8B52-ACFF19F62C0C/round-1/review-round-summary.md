# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Canonical OOS headings are not recognized as OOS
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Canonical `### OOS_N:` / `### OOS_` blocks are iterated but `_is_oos_block` still rejects them unless legacy scope markers are present, so accepted fileable OOS items can be skipped during emit-tally and the accepted sink can end up empty or mismatched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Treat OOS_ headers as OOS or combine header prefix with Fileable gate
  - From codex-specialist-testing: Treat ### OOS_ headings as OOS and add serialize coverage for canonical OOS_ input without bracket markers.


### FINDING_2: Zero-ballot short-circuit still depends on fail_count
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The all-dropped zero-ballot path still requires `fail_count == 0`, so when one reviewer fails and the surviving reviewers emit only nit rows, pruning empties the ballot but voters are still dispatched against an empty ballot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Remove the fail_count == 0 guard while preserving the ok_count > 0 check.
  - From cursor-specialist-testing: Short-circuit on empty post-prune ballot independent of fail_count
  - From codex-specialist-testing: Remove the fail_count == 0 gate or branch on ok_count > 0 plus empty ballot, and add a regression test for ok_count > 0, fail_count > 0, all-nit input.


### FINDING_3: Research-eval fixtures still use retired severity labels
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The research-eval tests still expect retired `Important` / `Blocking` severities even though the validator now accepts only `major`, `minor`, and `nit`, so the focused suite can fail on fixtures and normalized output that use the old vocabulary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Update fixtures/assertions to major|minor|nit; assert retired labels reject
  - From codex-specialist-testing: Update fixtures and expected normalized output to major, minor, and nit; keep old labels only in explicit rejection or legacy-analysis tests.


### FINDING_5: Missing regression for security/public nit-drop audit split
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no regression test proving that security-tagged nit drops stay in the sidecar audit instead of leaking into the committed public `oos-dropped-before-vote.md` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add prune test asserting sidecar vs public audit split


### FINDING_6: Missing serialize coverage for canonical OOS inputs
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no serialize test covering canonical `### OOS_` blocks or `Fileable=false`, so accepted-but-non-fileable OOS items are not guarded by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add OOS_ heading and Fileable=false serialize cases


### FINDING_7: Missing end-to-end tally test for accepted OOS split votes
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The tally path lacks an end-to-end regression for accepted OOS items where YES votes split across major and minor severities, so the strict-majority file gate could regress without a focused failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add tally-code-votes test; assert empty accepted sink


### FINDING_8: Missing accepted-major convergence regression
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The review-and-fix flow does not have a regression proving that accepted-major-only rounds do not converge too early when high-severity detections remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test for - **Severity**: major high-severity detection


### FINDING_9: Missing plan-review integration coverage for prune/empty-ballot paths
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan-review integration tests are missing for prune-audit handling, OOS-stream behavior, and empty-ballot handling, so design-path regressions can ship without a focused failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add plan-review integration tests for prune audit and empty ballot
