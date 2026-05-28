### FINDING_1: Emergency resume can downgrade persisted flag
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Resume persistence can overwrite a previously true `EMERGENCY_REQUESTED` value with the argv default `false`, causing run flags, metadata, and final summaries to lose emergency state after dirty-tree recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Dirty-tree resume prose omits emergency arg
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 0 dirty-tree recovery prose omits `--emergency-requested`, so operators following the prose instead of the bash block may resume without the emergency flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Emergency bypass kind tokens are underspecified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The prompt docs do not specify canonical `BYPASS kind=` values for all emergency preflight gates, especially `audit-refuse`, so operators may write syntactically valid but semantically inconsistent bypass logs that fall into invalid-format handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Bypass log append helper is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `append_emergency_bypass_log_if_present` contains large inline validation and fallback logic, making bootstrap plan materialization harder to maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Collateral changes are bundled with emergency work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Unrelated merge, ship, and design changes are bundled with the emergency feature, increasing review and CI risk for changes outside the plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Post-tracking metadata can miss emergency state from argv-only callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `post-tracking-issue.sh` relies on argv for the emergency boolean, so a future caller could omit the flag and post metadata without `Emergency: true` even when `run-flags.sh` says true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Invalid emergency flag is silently coerced in final report
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` treats invalid `EMERGENCY_REQUESTED` values as false, so corrupted run flags can silently drop emergency state from summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Resume-plan-tail can leave stale tracking metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The `--resume-plan-tail` sentinel path skips `post_tracking_metadata`, so reused tmpdirs may show emergency state in final summary while the GitHub metadata comment remains stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Emergency metadata upsert failures are hidden on resume
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Branch-1 resume masks `post_tracking_metadata` failures with `|| true`, allowing emergency runs to proceed without a correct `larch:metadata` comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Prompt-only emergency preflight lacks executable coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Emergency preflight bypass control flow lives in prompt text while CI relies on literal greps, so regressions in audit refusal, bypass handling, or non-emergency exits could pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Clean emergency plan acceptance is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bootstrap tests cover emergency plan materialization mostly with seeded bypass logs, but not a valid-plan emergency run with no bypass log, leaving room for spurious execution issues or metadata regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Bootstrap docs misstate invalid bypass-log behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/implement-bootstrap.md` says invalid emergency bypass logs fail closed, but current code and tests warn, continue, and reserve hard failure for append failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Bootstrap emergency argv validation lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Invalid `--emergency-requested` parsing in bootstrap is not covered by the bootstrap harness, so argv validation could regress while lower-level persist tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Missing-plan refusal text lacks regression guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The plan adequacy audit tests do not grep for the legacy non-emergency missing-plan refusal string, so accidental edits to default refusal text may pass lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Emergency issue-body plan lacks trust-boundary framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `--emergency` can copy collaborator-controlled issue body text into `plan.txt` while bypassing adequacy and clarification gates, and downstream implementers may treat instruction-like issue content as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Bypass-log fallback append skips redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The fallback path for malformed or verbose emergency bypass logs appends to execution issues without the redaction used on the happy path, risking token or PII leakage into artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: Emergency can proceed with pending clarifications
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Emergency mode skips clarify-state checks, including `awaiting-response`, so implementation can proceed while clarification threads are still open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Admission blockers fail open on API errors
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing admission blocker checks can fail open on API or `gh` read errors, potentially starting runs with incomplete dependency or design checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Feature description includes raw issue content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bootstrap always includes full issue title and body in `feature-description.txt`, creating a pre-existing prompt-injection surface for all implement runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: SECURITY.md misstates invalid bypass-log behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` says invalid bypass-log lines fail closed, but implemented behavior is warn-and-continue invalid-format handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Persisting run flags before metadata can create inconsistent artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Adopt/resume persists `EMERGENCY_REQUESTED` before posting tracking metadata, so a post failure can leave run flags and final summary showing emergency while `larch:metadata` omits it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: Copy-plan failure can skip bypass-log artifacting
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If copying `plan-from-issue.txt` fails, bootstrap exits before appending the emergency bypass log, leaving execution artifacts without the bypass record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Malformed emergency path does not restate empty-body abort
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The malformed-plan emergency prompt path does not explicitly repeat the empty or whitespace-only issue body abort, so a prompt-driven implementer may proceed with an empty plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: Bypass log issue number is not matched to current issue
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bypass log `issue=` values are syntax-validated but not checked against the resolved current issue, so reused tmpdirs can append misleading issue numbers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: Dirty-tree emergency resume duplicates bypass warnings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree emergency resume replays the bypass log, causing duplicate identical bypass warnings in `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Early bootstrap bail can drop bypass log from artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bootstrap failures before plan materialization can leave bypass warnings only in chat and absent from artifacts, a pre-existing documented failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: Bootstrap stdout parser drops EMERGENCY_REQUESTED
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0 says to parse `EMERGENCY_REQUESTED` from bootstrap stdout, but `_ib_kv_scan` lacks a matching case arm, so later prompt-side logic may see an empty or stale variable even when run flags and metadata show emergency true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
