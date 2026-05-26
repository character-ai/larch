### OOS_1:
- **Description**: Per-call-site tr -d [:cntrl:] duplicates policy and leaves other larch_err passthrough sites unprotected. Scenario: Future scripts forwarding external stderr verbatim remain injectable unless each adds its own helper
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-quiet.sh:97-103
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Another REASON_TOKEN parser still assumes tokens cannot contain equals. Scenario: If this PR makes embedded equals a supported REASON_TOKEN value across the Mermaid sanitizer contract, the warnings-log aggregation still truncates at the first equals/space
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/sanitize-mermaid-fragment.sh:283-285
- **Phase**: design

### OOS_3:
- **Description**: Issue #2798 suggested auditing any site that emits raw job names; plan audits only the line-80 larch_err path. Scenario: TSV rows and quiet emit at line 128 still carry raw job_name values from gh stdout (pre-existing); out of Step 1c stderr scope but not recorded as deferred
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:125-128
- **Phase**: design

