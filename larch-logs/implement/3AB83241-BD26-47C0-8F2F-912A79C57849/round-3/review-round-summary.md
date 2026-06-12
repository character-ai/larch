# Review Round 3

- Mode: `diff`
- 5 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: close eligibility treats retried inherited-safe writes as failed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `close_eligible` can keep a source open when an earlier failed `inherited_safe` write is followed by a successful retry for the same edge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use last-write-wins per (edge phase) or ignore failed rows when a later written/already_present exists; add regression test.


### FINDING_11: metadata-refresh reclassification test is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the two-pass metadata refresh path where an initially unknown plan-inherited edge becomes classifiable after issue metadata is refreshed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a two-pass plan-inherited test: first with missing open metadata, second with issue #9 present; assert edge reclassification and eligibility change.


### FINDING_2: blocker negation scope suppresses real dependencies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `parse_prose_blockers` scans too much preceding text for negation, so unrelated earlier negation can suppress a later valid blocker reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict negation to phrases directly negating the dependency keyword; add parametrized tests.
  - From cursor-specialist-edge-cases-output.txt: Limit negation to same clause/sentence; add test_blocker.py coverage


### FINDING_4: multi-host source closure uses only the first combined host
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A source mapped to multiple combined issues is closed under `combined_hosts[0]`, which can produce the wrong closure comment or close a source that still belongs to another combined issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document constraint or derive host from apply metadata.
  - From cursor-specialist-edge-cases-output.txt: Emit under each mapped host with correct partitioning rules or mark multi-host sources ineligible until canonical host is chosen; add test


### FINDING_5: close-sources partial outcomes have an unsafe exit and summary contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-exit-contract-output.txt
- **Severity**: important
- **Concern**: `close_sources_main` reports partial skips or failures inconsistently. This can undercount sources left open, abort the workflow under non-zero exit handling, or let the OOS flow continue without reconciling skipped sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit structured skip list or merge close-sources warnings into final summary.
  - From cursor-specialist-edge-cases-output.txt: Return structured per-source results; treat partial close as blocking or re-run eligibility before audit
  - From dyn-exit-contract-output.txt: Split outcomes: return `0` when the command completed and emitted `CLOSED_ISSUES` (reserve `1` for argument/repo errors only), or add explicit `PARTIAL=true` / `STATUS=partial` KV output; update `.claude/skills/combine-issues/SKILL.md` oos-7 to require parsing `CLOSED_ISSUES` and `WARNING=` stderr, continuing through remaining combined hosts and always reaching oos-10.
  - From dyn-exit-contract-output.txt: Add oos-7 prose: always run all partitioned `close-sources` calls regardless of exit code; parse stdout/stderr for tallies; treat non-zero as a warning path unless `ERROR=` indicates hard failure; mandate oos-10 even after partial closure.


