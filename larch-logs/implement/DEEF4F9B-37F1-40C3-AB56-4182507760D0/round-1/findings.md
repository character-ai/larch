Omitted affirmative security observations that did not identify a behavioral risk.

### FINDING_1: [OUT_OF_SCOPE] Plan-review zero-finding/all-rejected routes omit the Step 3b completion boundary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `skills/design/references/plan-review.md` still routes zero-findings/all-rejected flows to Step 3b without explicitly naming the Step 3b completion boundary before Step 4, so an orchestrator following that surface alone may skip FINALIZE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_2: Duplicate FINALIZE fences may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 3b boundary and Step 4 compatibility guard duplicate FINALIZE bash blocks, creating a maintenance risk if future failure-handling edits update only one copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Routing guard exemption is too broad
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` exempts any line mentioning the Step 3b completion boundary, even if that line does not require the actual FINALIZE fence, allowing prose-only mentions to satisfy CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Pause/resume fixtures do not execute compatibility guards
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-resume-legacy-output.txt
- **Severity**: important
- **Concern**: Legacy pause/resume tests verify STEP routing but not execution of the Step 4 FINALIZE guard or Step 2a.5 marker/artifact repair, so guard removal or broken runtime recovery could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-resume-legacy-output.txt: Address the concern above.

### FINDING_5: FINALIZE failure warning text is not pinned
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structure tests assert non-zero FINALIZE failure but not the operator-visible repair warning, so the breadcrumb required by FM6 could disappear while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Step 4 marker needles are inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 4 marker assertions use inconsistent marker strings, so a marker format change could break one slice while others still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Step 2a.5 SIMPLE skip can bypass the compatibility fence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 2a.5 SIMPLE skip prose appears before the resume-compatibility fence, allowing an orchestrator to proceed directly to Step 2b without writing `.completed/step-2a.5` for legacy SIMPLE resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Step 2a.2 sentinel-based skip is too permissive
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2a.2 treats the SIMPLE sentinel in `approach-synthesis.txt` as sufficient skip evidence, which can let stale HARD artifacts or partial SIMPLE entry-fence writes skip sketch launch/synthesis without complete markers and artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Harness ordering failure message is inverted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: A guard-line ordering assertion in `scripts/test-design-structure.sh` reports the wrong ordering expectation, which would misdirect debugging when CI fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Step 3b FINALIZE ordering is not pinned inside the fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Step 3b boundary structure check verifies substring presence but not that FINALIZE completes before `.completed/step-3b` is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: No executable test covers Step 3b FINALIZE on empty review state
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Driver behavior at the new Step 3b FINALIZE call site is prose-pinned but not exercised with an empty review-state tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Pre-existing `eval` in design-driver ARGS parsing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `design-driver.sh` has a pre-existing `eval "action_args=( $args_text )"` path for `ARGS`, not introduced by this diff, which would be risky if fed untrusted input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Gate-B bypass routes omit the Step 3b completion boundary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate-B-bypass branch bullets route to Step 3b without naming the completion boundary, risking skipped FINALIZE before Step 4 artifact reads on panel-failed/tally-error paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Legacy SIMPLE compatibility guard does not verify or restore sentinel artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-resume-legacy-output.txt
- **Severity**: latent
- **Concern**: The Step 2a.5 compatibility guard backfills only `.completed/step-2a.5`; legacy or corrupted SIMPLE resumes with missing sentinel artifacts can proceed to Step 2b with incomplete sketch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-resume-legacy-output.txt: Address the concern above.

### FINDING_15: Missing pause/resume fixture for finalize-present but step-3b-absent state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: There is no fixture for `.completed/finalize` present while `.completed/step-3b` is absent, so regressions in resume-at-3b boundary rerun behavior could go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] HARD zero-sketch path may omit `.completed/step-2a`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The pre-existing HARD zero-sketch path can skip the Step 2a success-boundary marker write, leaving both-tools-down HARD runs without `.completed/step-2a`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Step 2a.5 compatibility guard ignores SIMPLE pause metadata when classification defaults HARD
- **Reviewer(s)**: dyn-resume-legacy-output.txt
- **Severity**: latent
- **Concern**: The guard repairs `.completed/step-2a.5` only when `read-design-classification.sh` returns `SIMPLE`; legacy snapshots with SIMPLE pause metadata but missing/invalid classification can default to HARD and skip repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-legacy-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Step 2a success-boundary prose is ambiguous or stale
- **Reviewer(s)**: dyn-resume-legacy-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Step 2a success-boundary prose still implies zero-sketch paths write `.completed/step-2a` there, while SIMPLE and HARD zero-sketch paths now use or skip different write sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-legacy-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_19: Collaborative sketch docs do not identify the Step 2a entry fence as the SIMPLE write site
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `docs/collaborative-sketches.md` still describes SIMPLE sentinel writes without naming the Step 2a entry fence as the sole write site, conflicting with updated normative surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_20: run-step3-review contract doc omits cap-reached boundary-qualified routing
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/run-step3-review.md` does not document the updated cap-reached stdout breadcrumb or its Step 3b completion boundary → Step 4 → Gate C routing chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_21: Pause/resume harness contract markdown omits new legacy fixtures
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-design-pause-resume.md` was not updated to document the new legacy compatibility fixture expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_22: SIMPLE anti-pattern text does not locate sentinel writes in the entry fence
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` anti-pattern guidance still says to write the SIMPLE sentinel without clarifying that sentinel and marker writes occur only in the Step 2a entry fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Routing guard does not scan several stale-prose surfaces
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: The line-scoped routing guard does not scan several docs/contracts, so stale routing prose in those surfaces will not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_24: AWK `IGNORECASE` use is not portable to BSD awk
- **Reviewer(s)**: dyn-bash-fences-output.txt
- **Severity**: latent
- **Concern**: `assert_no_direct_step3b_step4_routes` relies on `IGNORECASE`, a gawk extension ignored by BSD awk, making the routing-verb catch case-sensitive on macOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-fences-output.txt: Address the concern above.

### FINDING_25: Step 2a entry fence may leak `errexit` into later bash fences
- **Reviewer(s)**: dyn-bash-fences-output.txt
- **Severity**: latent
- **Concern**: `set -e` is enabled inside the SIMPLE branch but not reset, so a reused shell session could inherit `errexit` and unexpectedly abort later unrelated commands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-fences-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Harness temp file can leak on assertion failure
- **Reviewer(s)**: dyn-bash-fences-output.txt
- **Severity**: nit
- **Concern**: `assert_step2a_entry_simple_guard` removes its `mktemp` file only on normal function completion; early `fail` exits leak the temp file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-fences-output.txt: Address the concern above.
