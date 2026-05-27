### FINDING_1: [OUT_OF_SCOPE] Gate B degraded-mode policy is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-flag-state-layering-output.txt, dyn-rollback-unspecified-output.txt
- **Severity**: important
- **Concern**: Gate B degraded-mode resolution is inconsistent across approval-gates, SECURITY, write-run-params, and the plan contract. Several reviewers observed that jq/run-params failure can force legacy manual prompting on default non-manual runs, while other prose says missing/null/unreadable mode should default to auto-apply unless manual intent is known. The merged risk is that orchestrators choose different Gate B modes in degraded paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-flag-state-layering-output.txt: Address the concern above.
  - From dyn-rollback-unspecified-output.txt: Address the concern above.

### FINDING_2: Zero-findings short-circuit can run after Gate B mode handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 3.5 and approval-gates ordering allow Gate B mode resolution, auto-apply, or manual prompting before checking whether accepted-plan-findings.md is empty. Zero-finding runs should short-circuit to Step 3b before mode-specific Gate B behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Per-finding apply path can drift from Apply-all
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Go-through-each manual path duplicates the Apply-all pipeline instead of sharing or explicitly referencing the same post-apply steps. Future edits may update Apply-all while leaving the per-finding path stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: MANUAL_REQUESTED env writer coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flag-state-layering-output.txt
- **Severity**: nit
- **Concern**: test-write-design-current-env.sh does not fully cover omitted manual-requested state, explicit false handling, invalid enum rejection, and stale true clearing. Regressions in session env export or rewrite behavior could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-flag-state-layering-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Native blocked-by edge may be missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The #2667 blocked-by #2930 dependency is acceptance-listed but not evidenced in the diff, so post-PR dependency wiring may be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Plan-review dual-mode Gate B prose is not pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: plan-review.md and plan-review-quick.md contain dual-mode Gate B semantics that are not structurally pinned, so stale explicit-user-choice-only text could return without lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Step 3 dual-mode SKILL prose is not pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 3’s manual_gate_b=false auto-apply guidance in SKILL.md lacks a structural lint pin, so SKILL.md could drift from Gate B docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Stale Gate B prose grep is not encoded in CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A repo-wide stale-prose grep for old Gate B contract strings is not part of CI, so unpinned docs could regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] No harness covers write-run-params failure plus jq recovery
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: There is no fixture simulating write-run-params failure plus jq merge recovery for manual-only argv, leaving recovery expression behavior untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Auto-apply may merge untrusted reviewer content into plan scope
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Default auto-apply merges accepted reviewer findings into plan.txt before Gate C without per-finding human consent. Malicious, compromised, or scope-expanding reviewer content could influence the plan while compact Gate C summaries may not expose the full change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Security-tagged in-scope findings can be auto-applied and published
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Accepted in-scope security-tagged findings are eligible for default auto-apply and later public issue publication, while SECURITY.md only protects security OOS findings from public artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: State invariant disagrees with Gate B mode precedence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-flag-state-layering-output.txt
- **Severity**: important
- **Concern**: approval-gates State Invariant #4 says mode is read from run-params.json, while the Gate B mode subsection also uses session env and in-memory argv. This can mislead orchestrators or future edits about the actual precedence chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-flag-state-layering-output.txt: Address the concern above.

### FINDING_13: Rollback procedure is underspecified and conflicts with Gate flow
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-rollback-unspecified-output.txt
- **Severity**: important
- **Concern**: The rollback procedure for prior auto-apply text is prose-only, appears outside the original plan scope, conflicts with Gate A re-entry timing, can be undone by the following auto-apply, lacks schema/pins, and leaves multiple authorities for mutating plan.txt after discussion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-rollback-unspecified-output.txt: Address the concern above.

### FINDING_14: Router recovery OR can preserve stale manual mode
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: SKILL.md router jq recovery ORs manual_gate_b true and cannot clear a stale true when the current argv omits --manual, preserving manual mode on a default run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Corrupt non-boolean manual_gate_b values are not rejected
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gate B uses jq fallback semantics that may not strictly reject corrupt non-boolean manual_gate_b values, allowing malformed run-params to mis-route mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Step 0b stamps MANUAL_REQUESTED=false into non-manual session env
- **Reviewer(s)**: dyn-flag-state-layering-output.txt
- **Severity**: important
- **Concern**: Step 0b always passes --manual-requested "$manual_requested", causing non-manual runs to export MANUAL_REQUESTED=false. This contradicts the writer’s omission contract and creates a future footgun if Gate B treats any set session value as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-state-layering-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Stale MANUAL_REQUESTED=true is lower impact than degraded-mode failure
- **Reviewer(s)**: dyn-flag-state-layering-output.txt
- **Severity**: nit
- **Concern**: Stale MANUAL_REQUESTED=true in the PID-keyed symlink is mitigated by Step 0b rewrite in the happy path; the more significant stale-state risk is the degraded-mode fail-closed behavior covered separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-state-layering-output.txt: Address the concern above.
