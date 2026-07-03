# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_4: Regression coverage is still too thin
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The offline regression suite does not cover the plan-listed report, ledger, resume, PR fallback, deep ingest, and CLI edge cases, so several `analyze_bugs` regressions could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add plan-listed pytest cases especially render_report and ledger resume paths.
  - From cursor-specialist-edge-cases: Add offline tests for render_report, load_ledger quarantine, and mechanical verdict matrix.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_5: Large BUG corpora can underfill requests
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `fetch_bug_issues` can return fewer than requested rows because it stops at the 3200-row corpus cap and refetches larger slices instead of doing real pagination.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: fetch_bug_issues refetches larger first-page windows instead of paginating, so it can under-fill the requested BUG window. -n 200 returns fewer than 200 when the 200th newest BUG issue is past position 3200 even though more matches exist. Implement real cursor/page pagination until N prefix matches are collected or the corpus is exhausted.


### FINDING_6: Unverified fix SHAs can produce empty-diff false fixed
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: PR fallback and git evidence handling can accept a fix SHA that is absent or unreadable locally, leaving an empty diff that still flows into fixed verdicts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Escalate to mechanical NEEDS_DEEP when git show/log fails for a resolved fix_sha; surface stderr.
  - From codex-specialist-testing: Verify PR fallback SHAs with local git, for example `git cat-file -e <sha>^{commit}` or a checked `git show`, and mark `NEEDS_DEEP` when the commit is absent or unreadable.


### FINDING_7: Refresh can keep stale deep verdicts
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-cache-ledger
- **Severity**: important
- **Concern**: Refresh and lifecycle changes do not clear cached deep state, so older deep verdicts can survive new triage and hide current-run mechanical state, especially when `fix_sha` is empty or `state` / `stateReason` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: On refresh, append a current-key row that clears prior deep state until deep verification reruns, or make report/ingest distinguish current-run stage output from cached ledger rows.
  - From codex-specialist-edge-cases: Do not honor cached deep completion for `bundle.mechanical_verdict == "NEEDS_DEEP"` when `bundle.fix_sha` is empty; always requeue or mark it pending until fix resolution succeeds.
  - From dyn-dyn-cache-ledger: Treat terminal mechanical verdicts (`NOT_FIXED`, `WONTFIX`) as overriding cached agent verdicts in `_final_verdict`, or extend the cache key (and `_record_for_bundle`) with normalized `state` / `state_reason` so lifecycle changes invalidate cached rows.
  - From dyn-dyn-cache-ledger: Thread `refresh` into ingest (or detect a new `run_id`) and reset deep fields (and optionally triage fields) before merge; alternatively skip `ledger.get()` as the merge base when `refresh` is set.
  - From dyn-dyn-cache-ledger: In `_priority_deep_candidates` and `_complete`, treat deep as incomplete when `not bundle.fix_sha`, and in `_final_verdict` prefer mechanical `NEEDS_DEEP` over cached deep when `fix_sha` is empty.


### FINDING_10: Bug triage task cannot read its evidence
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Stage 1 hands the triage task only file paths, but the triage agent has no `Read` tool, so it cannot inspect the batch JSONL or bundle evidence and cannot emit evidence-based output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Inline each capped bundle into the Task prompt for the no-tool triage agent, or intentionally grant `Read` and update the prompt contract.
  - From codex-specialist-testing: Inline the batch rows and capped bundle contents into the Task prompt, or give the triage agent `Read` and update the prompt/tests accordingly.


