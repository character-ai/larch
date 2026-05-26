### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:102
- **Concern**: Plan rejects shared sanitizer despite identical parsing hazard elsewhere. Scenario: scripts/sanitize-mermaid-fragment.sh:283 uses a different awk idiom for token aggregation; future REASON_TOKEN values with = will diverge across consumers
- **Proposed resolution**: [OUT_OF_SCOPE] Track aligning token extraction in scripts/sanitize-mermaid-fragment.sh:283 or extracting one portable helper


### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:125-129
- **Concern**: Untrusted job names still reach TSV and emit output unsanitized. Scenario: The audit says only the stderr larch_err path takes untrusted external input, but successful gh output is also GitHub-controlled and malformed names containing control bytes are written to OUTPUT_TSV_TMP or emit before the final sanitize_list KV summaries
- **Proposed resolution**: Sanitize or replace malformed job names before any TSV/emit contract output, for example write a fixed malformed placeholder plus reason; add a success-path fixture with control bytes in job names


### [Plan Review] FINDING_23

### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:125-128
- **Concern**: Plan audits only the stderr larch_err path but feature requires auditing other raw job-name emit sites. Scenario: A malformed gh job name with tabs or control bytes can still be written raw to TSV or direct emit output, splitting rows or confusing downstream consumers
- **Proposed resolution**: Sanitize or substitute a safe job-name value before every TSV/direct emit surface and add a regression with malformed job names containing tab/control bytes


