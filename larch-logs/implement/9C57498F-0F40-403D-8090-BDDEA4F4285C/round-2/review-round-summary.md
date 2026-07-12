# Review Round 2

- Mode: `diff`
- 6 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Hook command normalization misses wrapped or argument-bearing scripts
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Hook adoption currently matches only the first shell token or normalizes before parsing. Commands wrapped with `bash`, `${CLAUDE_PLUGIN_ROOT}`, or additional arguments can remain pending even when the target script is present. Normalize the parsed script-path argument rather than relying only on `argv[0]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_3: Missing regression for adopted targets becoming orphaned
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: There is no regression test for a target that is adopted and later removed. Add a two-pass fixture-backed test asserting the status transitions from adopted to orphaned rather than regressing to pending.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_4: Missing workflow coverage for reconciliation, filing, zero residuals, and analysis-root isolation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Plan-required workflow-facing coverage is absent for reconciliation, complete proposals-file persistence, issue-number attachment, zero-residual filing, command sequencing, and marker mutations when `PWD` differs from `ANALYSIS_ROOT`. Add targeted integration or fixture-harness coverage for these paths, including a two-repository isolation check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Same-ID proposals do not validate the stable original `run_date`
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Duplicate loading and reconciliation compare same-ID proposals only by type and target. A changed original `run_date` is silently merged and persisted, allowing proposal history and lifecycle meaning to be altered. Normalize rediscovered residuals to the historical date and require type, target, and `run_date` equality in both duplicate paths; add rejection tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: Regex matching can mistake comments or strings for lint registrations
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Raw regex matching can mark a removed lint registration as adopted when its name remains in a comment or string. Parse the CLI registry structure and match only a real lint registration entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_12: Filed issue lookups do not validate the durable repository
- **Reviewer(s)**: dyn-dyn-proposal-lifecycle
- **Severity**: minor
- **Concern**: `check_proposals_main` uses the caller-supplied `--repo` for filed-issue lookups without comparing it with the marker's durable `state.repo`. A later repository mismatch can query issue numbers against the wrong repository and write incorrect adoption statuses. Require a match or derive the lookup repository from durable state and fail closed on mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-lifecycle: Address the concern above.
