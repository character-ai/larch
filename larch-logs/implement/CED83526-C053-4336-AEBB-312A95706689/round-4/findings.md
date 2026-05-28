### FINDING_1: Step 3.6 duplicates assessor preflight and KV handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Step 3.6 duplicates `assess-plan-round.sh` preflight/KV behavior in SKILL prose, creating drift risk when assessor semantics change in one path but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Missing-snapshot preflight skips execution-issues audit trail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Step 3.6 missing-snapshot branch bypasses `assess-plan-round.sh` and does not call `append-tool-failure.sh`, so round-2 missing `plan.txt-original` can warn in chat while leaving `execution-issues.md` and published design logs without the required audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Snapshot write-after failures use misleading degraded-default-open artifacts/status
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Snapshot write-after failure is represented as degraded-default-open with no matching verdict sidecar files and may show a misleading 0/3 effective-assessor banner even though no assessor panel ran, obscuring a snapshot infrastructure failure in logs and operator UX.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Assessor script markdown contracts are underspecified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: New assessor `.md` script siblings, especially `dispatch-plan-assessors.md`, are too thin compared with the expected script contract depth, leaving argv, KV schema, slots rows, fail-open behavior, and artifact names discoverable only from shell source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: workflow_path extraction is duplicated across SKILL fences
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `workflow_path` jq/sed block is copied across Steps 2b, 3, and 3.6, so a run-params schema change could leave assessor gating inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: render-assessor-prompt diagnostics bypass lib-quiet conventions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `render-assessor-prompt.sh` emits plain stderr diagnostics instead of using the repo’s `lib-quiet`/`larch_err` conventions used by sibling design scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: assess-plan-round and SKILL degraded artifact behavior diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Degraded paths in `assess-plan-round.sh` write default verdict artifacts while the SKILL write-after failure path does not, producing inconsistent artifact sets for similar degraded-default-open UX.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Assessor and voter dispatch diagnostics may diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The voter dispatcher has richer diagnostics than the assessor dispatcher, creating future reimplementation risk if assessor hardening grows independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Claude slot failure discards valid external assessor outputs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A Claude slot failure forces `DISPATCH_OK=false`, causing `assess-plan-round` to skip tallying existing Codex/Cursor outputs and fail open to `NOT_WORSE` even when successful external assessors form a WORSE consensus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Snapshot atomic rename interrupt coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-snapshot-plan-round.sh` lacks the plan-required interrupt or failed-rename simulation, so partial snapshot writes or temp-file leaks could corrupt plan-after snapshots without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: render-final-summary structural pins miss cancelled-assessor-worse
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Structure checks do not pin `render-final-summary.md` for `cancelled-assessor-worse` and `ASSESSOR_ROUND_NUM`, so required summary tokens could disappear without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Dispatch breadcrumb stream coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The dispatch harness does not assert breadcrumb stream emission, so monitor or stream wiring regressions may only appear in live `/design` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Tally case for two TIE votes plus one failure is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-tally-plan-assessor.sh` does not cover the `(0,2,0)` NOT_WORSE cell, leaving a two-TIE plus failed-assessor regression undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Trivial-tier harness uses non-production workflow_path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-assess-plan-round.sh` uses `workflow_path=TRIVIAL` for the trivial-tier skip case, while production `--trivial` uses `workflow_path=SIMPLE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Phase2 plan-assessor timing slugs are not structurally pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Phase2 plan-assessor timing kinds are allowlisted but not pinned in structure checks, so phase2 dispatch slugs could be removed accidentally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Assessor publish parity tests omit key top-level artifacts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Multi-round publish parity only hand-seeds cursor and plan-after files, so harvester gaps for artifacts such as `plan.txt-original` or assessor verdict files would not fail integration tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: relevant-checks misses render-final-summary-only edits
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh` does not map `render-final-summary` path edits to `test-render-final-summary`, allowing local relevant checks to miss summary regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: Assessor verdict text can inject multiline .env keys
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` and WORSE justification are written without first normalizing control characters and newlines, allowing assessor output to spoof additional `KEY=value` lines and violate the single-line contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Stop path shell-sources untrusted assessor env file
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The Stop path sources `.step3.6-assessor.env`, allowing same-UID tampering or shell metacharacters in values to execute code during cancellation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Dispatch KV output paths are not confined to DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` trusts output paths from `dispatch.kv` without validating they remain under `DESIGN_TMPDIR` with expected assessor basenames, so tampered paths can feed unexpected files into tally and published artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: External assessor prompts may leak sensitive plan content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Assessor prompts inline full plans and feature text to external vendors, so secrets or private URLs in plan markdown may leave the operator machine without sufficient operator-facing hygiene guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: WORSE-majority UX exposes assessor-generated text before operator decision
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The WORSE-majority path may surface assessor-generated reasoning or qualifications in chat before `AskUserQuestion`, creating prompt-injection or operator-bias risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_23: SECURITY.md change conflicts with deferred scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` was changed even though the plan deferred that work to `OOS_2`, creating mismatch between implementation scope and review expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_24: tally-plan-assessor.md omits required worked examples
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `tally-plan-assessor.md` lacks the required FINDING_8 worked-examples table and majority boundaries, leaving strict-majority semantics documented only in tests or issue prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_25: Monitor failure suppresses valid assessor tally
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A non-zero breadcrumb monitor exit forces degraded-default-open even when dispatch produced parseable assessor files, allowing monitor failure to suppress a valid WORSE-majority verdict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: Single successful WORSE assessor can trigger WORSE-majority
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: With two failed assessors, one successful WORSE vote can trigger Continue/Stop semantics; this needs either explicit operator-facing documentation or stricter majority rules for panels with fewer than three successful assessors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: Multiple ASSESSMENT lines allow last-line outcome override
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `tally-plan-assessor.sh` lets the last valid `ASSESSMENT` line win, so narrated or repeated lines can flip the gate outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
