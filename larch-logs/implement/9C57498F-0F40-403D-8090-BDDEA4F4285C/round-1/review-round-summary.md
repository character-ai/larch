# Review Round 1

- Mode: `diff`
- 9 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Preserve orphaned status across repeated repository checks
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-proposal-lifecycle
- **Severity**: major
- **Concern**: Repository-backed proposals whose targets remain absent are downgraded from `orphaned` back to `pending` on subsequent checks. Preserve `orphaned` while the target remains absent, while promoting to `adopted` if the target reappears.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-proposal-lifecycle: Address the concern above.


### FINDING_2: Normalize plugin-root paths when matching hook adoption
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Hook proposals using repository-relative paths do not match `hooks.json` commands containing `${CLAUDE_PLUGIN_ROOT}`, leaving adopted hook proposals pending.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_3: Preserve historical run dates during proposal reconciliation
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Re-discovered residual proposals receive the current run date, causing stable proposal-content conflicts instead of remaining pending. Preserve the historical `run_date` for matching proposals and use the current date only for new proposals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Fail closed on invalid existing proposal state
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A malformed or unsupported existing schema-v2 marker is treated as absent, allowing a later successful run to overwrite proposal history. Distinguish a missing marker from an unusable marker and raise `LearnFromBugsError` before generating outputs or writing state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_6: Prevent proposal-history loss when `--proposals-file` is omitted
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-proposal-lifecycle
- **Severity**: minor
- **Concern**: `write_state_main` writes an empty proposal list when `--proposals-file` is absent, silently erasing existing schema-v2 proposal history. Fail closed or preserve the existing proposals unless an explicit reconciled file is supplied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-proposal-lifecycle: Address the concern above.


### FINDING_7: Correct lint-registration adoption matching
- **Reviewer(s)**: dyn-dyn-proposal-lifecycle
- **Severity**: major
- **Concern**: `_lint_target_adopted` expects a three-element tuple, while actual lint registrations use two-element tuple keys, so `registration:` lint proposals remain pending after adoption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-lifecycle: Address the concern above.


### FINDING_8: Preserve lifecycle status when loading duplicate proposal IDs
- **Reviewer(s)**: dyn-dyn-proposal-lifecycle
- **Severity**: major
- **Concern**: `load_proposals_jsonl` lets a later duplicate row replace a checked lifecycle status such as `pending` with `proposed`, potentially downgrading state before persistence. Align duplicate merging with reconciliation or reject duplicate IDs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-lifecycle: Address the concern above.


### FINDING_10: Add workflow-level coverage for reconciliation and marker isolation
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Workflow-facing behavior lacks regression coverage for reconciliation, filing persistence, zero-residual filing, complete proposals-file handoff, command ordering, and mutation isolation to `ANALYSIS_ROOT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_12: Handle malformed GitHub JSON and validate response shape
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-proposal-lifecycle
- **Severity**: minor
- **Concern**: `_filed_issue_status` does not catch JSON parsing failures or validate that the payload is an object with the expected matching issue number, allowing `JSONDecodeError` or `AttributeError` instead of a fail-closed error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-proposal-lifecycle: Address the concern above.
