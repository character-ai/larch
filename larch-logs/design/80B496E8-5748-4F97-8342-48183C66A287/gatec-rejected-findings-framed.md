---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Cursor component-cost KVs are omitted from token-cost output
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `token_cost_from_args` emits KVs according to a hardcoded order tuple that does not include `CURSOR_GROK_4_5_COST` or `CURSOR_COMPOSER_2_5_COST`. These computed component costs therefore cannot reach `final_report` or `pr_body`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the order sequence in token_cost_from_args to include CURSOR_GROK_4_5_COST and CURSOR_COMPOSER_2_5_COST immediately before CURSOR_COST, or the plan must drop those KVs entirely.


### [Plan Review] FINDING_4

### FINDING_4: Direct Step 2 dispatch may skip shared difficulty resolution
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The plan replaces `_resolve_step2_difficulty` but does not require `step2_dispatch_main` to resolve difficulty when `--difficulty` is empty. Direct `step2-dispatch` callers and tests that rely on `run-flags.sh` or `difficulty-prior.env` could launch Cursor without a tier, leaving MODERATE runs on the Composer default instead of applying `--model grok-4.5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After parsing args in `step2_dispatch_main`, set `args.difficulty = shared_resolver(tmpdir)` when empty before `_dispatch_state`, matching the run-dispatch wrapper contract.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:98-109
- **Concern**: [SCOPE-REDUCTION] Remove the firm final-report and PR-summary per-model Cursor plumbing from this feature. Scenario: The issue requires MODERATE Cursor routing and the grok-4.5 rate in report_tokens_cost.py. Extending final_report.py and pr_body.py adds new component-KV contracts, compatibility branches, render logic, and tests without being required for the requested pricing calculation. It enlarges the failure surface and can create needless report-format churn.
- **Proposed resolution**: Limit the firm scope to report_tokens_cost.py, report_tokens_models.py, and the directly required rate-display path and tests. Keep aggregate CURSOR_COST accurate there. Move final_report.py, pr_body.py, and their tests to a tracked follow-up unless the originating issue explicitly requires per-model display in those surfaces.


---LARCH-REJECTED-END---
