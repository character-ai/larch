### FINDING_1: [OUT_OF_SCOPE] Structure harness does not pin all implement timing-skill call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-timing-env-output.txt, dyn-presence-gate-output.txt
- **Severity**: important
- **Concern**: The structure harness only checks some timing marks by label or covers only a subset of production timing callers, so removing `LARCH_TIMING_SKILL=implement` from Step 2, Step 3/6 checks, Step 5 review/resume, bootstrap coder-select, helper-based marks, or related bootstrap mark sites may pass CI while polluted design env misattributes implement telemetry. Some sources mark related bootstrap substring-only coverage as out of scope/pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-timing-env-output.txt: Address the concern above.
  - From dyn-presence-gate-output.txt: Address the concern above.

### FINDING_2: `step-telemetry-mark.sh` unknown-flag behavior differs from docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The markdown says unknown flags are ignored, but the script exits 0 immediately on the first unknown flag without consuming the remaining argv, silently dropping telemetry work in cases operators may expect to continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Shell timing-report callers duplicate implement env prelude
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple shell callers manually duplicate `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` while Python centralizes the contract, making future shell timing-report additions likely to miss one of the pollution defenses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Report-token table rendering duplicates branch-specific table logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_top_runs` and `_phase_breakdown` duplicate table header/row logic across skill branches, increasing drift risk for future output-column changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Degraded-tools gate defaults and empty-input handling can diverge from actual availability
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-presence-gate-output.txt
- **Severity**: latent
- **Concern**: Implement degraded-tools gate rehydration uses empty defaults differently from bootstrap/design. Missing presence keys can trigger a false both-tools-down prompt, while missing binary-found keys can be treated as `unknown`/healthy even when bootstrap later treats the tool as unavailable, causing inconsistent or misleading Step 0 degraded-tool notices.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-presence-gate-output.txt: Address the concern above.

### FINDING_6: Missing design CLI test for `post_issue` skill forwarding
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI only asserts `post_issue` forwarding for `--skill implement`; removing `skill=` from the design posting path would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Security reviewer surfaced no-action hardening observations
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The security output lists observed hardening/no-regression properties rather than a concrete defect: implement workflow short-circuiting narrows parse surface, workflow fallback is design-only, implement timing/report callers are pinned, adjacent validation exists, public implement surfaces omit workflow path, and no new injection/auth/deserialization issue was identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Plan scope expanded beyond approved file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch modifies `skills/design/` and other files that the plan reportedly listed as untouched or did not enumerate, making the implement-only workflow-removal scope harder to verify and potentially mixing unrelated fixes into one merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: Run-log docs do not explicitly state Path bullet is design-only
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Documentation mentions workflow-path removal but does not add the requested operator-facing note that implement `final-summary.md` omits `- **Path**:` and that the Path bullet is design-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Vendor timing rows can inherit polluted timing skill
- **Reviewer(s)**: dyn-timing-env-output.txt
- **Severity**: latent
- **Concern**: Pre-existing vendor task recorders in launch scripts call `timing-ledger.sh record-vendor-task` without forcing `LARCH_TIMING_SKILL=implement`, so rows can be tagged as design under a polluted shell, though this is reported as outside the plan and not affecting implement workflow path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-env-output.txt: Address the concern above.

### FINDING_11: Step 2 workflow-free contract lacks negative structure pins on real dispatcher implementation
- **Reviewer(s)**: dyn-step2-contract-output.txt
- **Severity**: latent
- **Concern**: The structure harness checks negative workflow pins only on bootstrap/thin dispatch surfaces, not `skills/implement/scripts/step2-implement.sh`, so reintroducing `--workflow`, `WORKFLOW_PATH`, SIMPLE/HARD timeout branching, or non-fixed timeout behavior in the real Step 2 implementation may pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step2-contract-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Step 2 contract and doc layering look coherent
- **Reviewer(s)**: dyn-step2-contract-output.txt
- **Severity**: nit
- **Concern**: The reviewer reported out-of-scope positive observations that production Step 2 dispatch is workflow-free, timeout behavior is fixed, stale workflow path values are ignored, and related docs/plugin metadata mostly align.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step2-contract-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Minor Step 2/render-summary harness gaps
- **Reviewer(s)**: dyn-step2-contract-output.txt
- **Severity**: nit
- **Concern**: Out-of-scope minor harness gaps remain: one timeout test exercises Codex only though Cursor shares the constant, and render-run-summary fixtures still pass `--workflow-path N/A` in some implement cases without asserting Path omission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step2-contract-output.txt: Address the concern above.

### FINDING_14: Design current-env recovery can preserve stale binary-found values
- **Reviewer(s)**: dyn-presence-gate-output.txt
- **Severity**: latent
- **Concern**: Partial `write-design-current-env.sh` re-invocations can recover prior `*_BINARY_FOUND=true` values when new probe calls omit binary-found flags, letting design degraded-tools classification report a tool as healthy after the CLI disappeared from PATH.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-presence-gate-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Test-only Step 5 review fixture lacks implement timing-report pin
- **Reviewer(s)**: dyn-presence-gate-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-step5-review.sh` invokes `timing-report.sh` without `LARCH_TIMING_SKILL=implement` in test fixtures only; production callers reportedly pin the environment, making this a pre-existing test-only surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-presence-gate-output.txt: Address the concern above.
