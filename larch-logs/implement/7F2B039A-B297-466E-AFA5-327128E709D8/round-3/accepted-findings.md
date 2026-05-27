### FINDING_1: Emergency resume can downgrade persisted flag
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Resume persistence can overwrite a previously true `EMERGENCY_REQUESTED` value with the argv default `false`, causing run flags, metadata, and final summaries to lose emergency state after dirty-tree recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


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


### FINDING_2: Dirty-tree resume prose omits emergency arg
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 0 dirty-tree recovery prose omits `--emergency-requested`, so operators following the prose instead of the bash block may resume without the emergency flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


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


### FINDING_27: Bootstrap stdout parser drops EMERGENCY_REQUESTED
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0 says to parse `EMERGENCY_REQUESTED` from bootstrap stdout, but `_ib_kv_scan` lacks a matching case arm, so later prompt-side logic may see an empty or stale variable even when run flags and metadata show emergency true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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


