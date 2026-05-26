### [Plan Review] FINDING_21

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scout-dynamic-archetypes-prompt.md:46-49 vs plan.txt:48-52
- **Concern**: No harness case for ISSUE_NUMBER with embedded newline / no-echo invariant. Scenario: Item B cites ISSUE_NUMBER newline KV-parser confusion; plan only exercises RUN_ID newline-injected (case 3)
- **Proposed resolution**: Add ISSUE_NUMBER newline-injected fixture expecting exit 1, fixed-token ERROR, and assert stdout does not contain the injected payload verbatim


### [Plan Review] FINDING_30

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-case-pattern-charset
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/tracking-issue-read.sh:262-270; scripts/test-tracking-issue-read-sentinel.sh:112-246
- **Concern**: Plan does not explicitly cover tab 0x09 or carriage-return 0x0D sentinel RUN_ID corruption in the harness. Scenario: The case pattern in the plan has the hyphen safely at the end and would reject tab and embedded CR, but the planned tests only name space, slash, and newline; current extraction also strips a trailing CR before validation, so CR behavior remains unpinned
- **Proposed resolution**: Add explicit RUN_ID fixtures for tab and embedded CR expecting exit 1 and no verbatim echo; separately document or test CRLF/trailing-CR tolerance if that remains intentional


### [Plan Review] FINDING_31

### FINDING_31:
- **Reviewer(s)**: Codex-dyn-case-pattern-charset
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/tracking-issue-read.sh:262-267; scripts/test-tracking-issue-read-sentinel.sh:112-246
- **Concern**: Planned newline-injected RUN_ID rejection is incompatible with the current line-oriented extractor. Scenario: grep -m1 plus sed extracts only the RUN_ID line; a literal newline after a valid RUN_ID prefix becomes a separate line rather than part of RUN_ID_VAL, so the proposed rejection case can silently pass as a truncated valid value
- **Proposed resolution**: Revise the test to target representable invalid bytes such as tab and embedded CR, or change extraction to reject malformed continuation/extra lines before reducing to a single value


### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-case-pattern-charset
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/test-tracking-issue-read-sentinel.md:7-18; scripts/tracking-issue-read.md:143-152
- **Concern**: Plan updates sentinel harness cases but omits the companion harness contract document. Scenario: tracking-issue-read.md says behavior changes in the sentinel branch require harness/doc assertions to stay in sync, while the current harness contract still describes the older ADOPTED-focused shape and will be further stale after RUN_ID validation cases land
- **Proposed resolution**: Add scripts/test-tracking-issue-read-sentinel.md to the plan and update its invariants, table, stdout shape, and Makefile wiring notes for ISSUE_NUMBER/RUN_ID validation


