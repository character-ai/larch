### [Plan Review] FINDING_4

### FINDING_4: Shared scout tier raw stem can erase earlier tier diagnostics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `scout-dynamic-archetypes.sh` reuses the same `${OUTPUT}.raw` stem for Cursor and Claude tiers, so later tier cleanup/retry can overwrite or delete the earlier tier’s diagnostic carrier and history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Plan F15 tier stems is required; add explicit step: set tier_raw=${OUTPUT}.raw.cursor and ${OUTPUT}.raw.claude pass distinct --output to launch-review/subprocess and compose scout-level failure-diag from both stems on give-up


### [Plan Review] FINDING_5

### FINDING_5: launch-review Codex give-up logs only the live sidecar
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Codex give-up path in `launch-review.sh` passes the live sidecar to `append_launch_failure` even when the useful diagnostics are in `${OUTPUT}.diag` or events, reproducing empty execution-issues blocks on fast-fail paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In launch-review codex give-up replace raw $SIDECAR with resolve_failure_diagnostic_source OUTPUT --sink "$SIDECAR" (and --events for codex); remove duplicate cursor-only fallback once resolver is wired


### [Plan Review] FINDING_6

### FINDING_6: append_launch_failure cannot log REVIEW_TMPDIR-only review failures
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `append_launch_failure` still resolves execution-issues only through implement/design tempdirs, so standalone `/review` or nested review paths with only `REVIEW_TMPDIR` / `LARCH_EXECUTION_ISSUES_LOG` can compose a carrier but return without logging it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Wire append_launch_failure through the planned shared resolver (LARCH_EXECUTION_ISSUES_LOG then dirname SESSION_ENV then IMPLEMENT DESIGN REVIEW_TMPDIR) for every give-up path not only preflight F8 branches
  - From Cursor-Requirements: Replace append_launch_failure log-path logic with the shared resolver from lib-failed-agent-stderr-tail.sh on all give-up paths (~644/1102), not only auth-setup/model-args preflight; pass resolve_failure_diagnostic_source output as --output-file; extend test-launch-review.sh with a REVIEW_TMPDIR-only fixture


### [Plan Review] FINDING_8

### FINDING_8: launch-review Codex auth-setup exits without logging diagnostics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Codex auth-setup branch in `launch-review.sh` can write `${OUTPUT}.diag` and exit 0 without calling `append_launch_failure`, so the diagnostic never reaches execution-issues despite being a failure-relevant branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Explicitly list this branch in the launch-review F8 steps: `write_failure_diag` + `resolve_failure_diagnostic_source` + `append_launch_failure` before `exit 0`, and add a harness case in `scripts/test-launch-review.sh`


### [Plan Review] FINDING_11

### FINDING_11: Other direct vendor-agent consumers remain outside site-aware logging and flush
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Direct vendor-agent call sites such as `auto-fix-plan-commands.sh` and `run-negotiation-round.sh` are not routed through the same saved/logged/flushed path, so they can fail with only local diagnostics and no committed execution-issues or vendor-failure-diagnostics entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add these direct sites to the audit and either append their resolved carrier to execution-issues plus the canonical batch, or route them through an updated site-aware launcher that does so


### [Plan Review] FINDING_16

### FINDING_16:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:33-34,scripts/larch-log.sh:67-84
- **Concern**: [SCOPE-REDUCTION] Implement durable flush uses both a canonical vendor-failure-diagnostics.txt batch and a scoped *.failure-diag allowlist in round_artifact_included. Scenario: Dual paths invite double-commit or allowlist drift: the same failure could land in git twice or batch-unreachable paths miss flush when allowlist rules lag call-site changes
- **Proposed resolution**: Pick one implement durable surface: either always append redacted carrier excerpts to the batch and keep per-output *.failure-diag session-only, or commit per-output *.failure-diag only and drop the separate batch slug


