### FINDING_1: Extract emergency bypass-log handling from bootstrap
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Emergency bypass validation, redaction, fallback append, and failure handling are inlined in `implement-bootstrap.sh`, expanding an already broad coordinator and making future emergency fixes riskier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Malformed-plan emergency path lacks distinct audit token and warning
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The malformed-plan emergency fallback can follow or imply the missing-plan path instead of requiring `BYPASS kind=malformed-plan` and malformed-specific warning text, so logs and tooling cannot distinguish absent plan blocks from malformed ones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: `persist_run_flags` rewrites redundantly across bootstrap phases
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `persist_run_flags` can run multiple times during tracking and plan phases without semantic changes, adding invoke-log noise and brittle harness expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Unrelated Bash prelude change is bundled with emergency work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `skills/implement/SKILL.md` Bash block prelude change is unrelated to `--emergency`, increasing merge and review noise for the emergency feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Emergency Preflight behavior is prompt-only and under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Emergency Preflight bypass behavior depends on prompt compliance rather than executable enforcement. A SKILL or orchestrator regression could omit required bypass logs, skip semantic materiality, alter refusal behavior, or persist `Emergency:true` while scripts and existing grep checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Token-report corrupt-zero change is unrelated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Token-report corrupt-zero logic was bundled into `write-final-report.sh` alongside emergency work despite being outside the emergency feature scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Branch bundles broad non-emergency diffs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The branch includes large non-emergency changes such as design readability work, merge/ship changes, logs, or harnesses, making review and CI attribution harder for the emergency feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Resume bootstrap can clear persisted emergency state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Later bootstrap snippets pass `--emergency-requested false` when `emergency_requested` is unset, which marks the argument as explicitly seen and prevents restoring persisted `EMERGENCY_REQUESTED=true` from `run-flags.sh`. Dirty-tree recovery or resume can then lose emergency metadata and skip bypass-log handling mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Non-emergency refusal text is not locked by tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Existing tests do not lock the exact legacy non-emergency refusal and audit-refuse messages, so operator-visible exit text could regress while token greps still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Bootstrap bypass-log tests cover only missing-plan
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-implement-bootstrap.sh` only exercises missing-plan bypass-log consumption, leaving malformed-plan and audit-refuse formatting/redaction regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Bootstrap lacks negative test for bypass log when emergency is false
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no first-pass test proving `emergency-bypass.log` is ignored when `--emergency-requested` is false, so normal runs could accidentally ingest bypass warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Run-summary format tests omit Emergency bullet
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The summary format/snapshot harness does not cover the optional `Emergency: true` line, so layout regressions could pass format lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Emergency raw-issue fallback lacks untrusted-data framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Emergency fallback can copy collaborator-controlled issue body text into `plan.txt` without implementer-layer untrusted-data framing, exposing downstream implementers to prompt-injection-like instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Bypass-log fallback can append unredacted content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: When `append-tool-failure.sh` fails, the valid-format bypass-log fallback append path can write content to `execution-issues.md` without running the same redaction step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Resume admission can skip design-prefix checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing resume admission semantics can skip design-prefix validation when the parent-issue sentinel matches, so resume plus emergency may proceed without re-checking `[DESIGNED]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Feature description globally exposes issue-body prompt injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `feature-description.txt` includes full issue bodies for all implement runs, exposing a pre-existing implementer prompt-injection surface beyond the emergency path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Admission blocker checks fail open on API errors
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing admission blocker reads can fail open during `gh` or API errors, and emergency runs inherit that false-negative blocker posture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Missing operator message for emergency bypass-log bootstrap failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `STEP_FAILED=emergency-bypass-log` exits through a generic bootstrap exit-2 path instead of a normalized operator-facing message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Emergency metadata can be recorded before bypass-log consumption
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tracking metadata can record `Emergency:true` before `execution-issues.md` receives the bypass log; a failure between those steps leaves inconsistent run evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Malformed-plan emergency branch may continue on empty issue body
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The malformed-plan emergency fallback does not explicitly repeat the empty or whitespace-only raw issue body abort, so it may materialize an empty `plan-from-issue.txt` and continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: `--emergency` flag is not explicitly bound to `emergency_requested`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The flags section documents `--emergency` without explicitly saying it sets the `emergency_requested` mental flag used by Preflight, so an implementer could pass the CLI flag while still hard-refusing in Preflight.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
