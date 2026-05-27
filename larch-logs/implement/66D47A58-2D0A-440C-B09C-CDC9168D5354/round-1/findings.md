### FINDING_1: Auto-apply Gate B duplicates findings presentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Auto-apply Gate B presents both the full Presentation table and a compact findings list, including duplicate rejected/OOS output, creating contradictory/noisy operator output before apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Gate contract still says every gate prompts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` still says each gate uses `AskUserQuestion`, contradicting the new default Gate B auto-apply path when `manual_gate_b=false`; an orchestrator may still prompt or hesitate at Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prose-stale-output.txt: Address the concern above.

### FINDING_3: Quick review output header implies premature plan revision
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `plan-review-quick.md` still references plan revision during quick-mode Step 3, which can make implementers revise `plan.txt` before Gate B instead of only collecting review findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Gate C entry conditions omit default auto-apply path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: Gate C’s “When” paragraph lists manual settled paths but omits the default auto-apply Gate B path, making the Gate C flow incomplete or misleading after auto-apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-prose-stale-output.txt: Address the concern above.

### FINDING_5: Gate C re-review prose omits auto-applied feedback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: Gate C re-review prose says the plan reflects only user-approved prior feedback, which is stale when Gate B findings were auto-applied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-prose-stale-output.txt: Address the concern above.

### FINDING_6: Cross-tier Gate B invariant is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The cross-tier paragraph duplicates tier-uniform Gate B content, increasing the chance future edits update one copy but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Tier flag table implies tier-specific Gate B auto-apply
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `--simple` tier row still implies auto-applied findings despite uniform Gate B mode being controlled by `--manual` / `manual_gate_b`, creating inconsistent flag semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Per-finding manual path can drift from apply-all pipeline
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: “Go through each” keeps inline dedup/EMIT_PLAN handling separate from Apply-all, so the two revision pipelines can drift over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Gate B manual-mode read failures fail open to auto-apply
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `manual_gate_b` cannot be read or persisted, including missing `jq`, corrupt `run-params.json`, or disk/session failures, Gate B can default to auto-apply even when the operator passed `--manual`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Step 3.5 says auto-apply is silent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` says Step 3.5 silently revises in auto-apply mode, while `approval-gates.md` requires visible breadcrumb/findings output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Gate B boolean parsing does not coerce corrupt values
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `jq -r '.manual_gate_b // false'` does not coerce non-boolean JSON, so corrupt `run-params.json` can route Gate B to the wrong mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Gate B branching lacks automated coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No automated test exercises Gate B auto-apply versus manual branching, so string pins and manual smoke may miss regressions in the default mode flip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Missing structural pin for defensive manual_gate_b read
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` lacks a structural pin for the defensive `manual_gate_b` read idiom, so future edits can weaken the read without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Apply-all merges reviewer prose without untrusted-data handling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Apply-all merges `accepted-plan-findings.md` into `plan.txt` without the same untrusted-data handling as `ballot.txt`, so instruction-like reviewer prose could steer downstream implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: SECURITY.md lacks Gate B auto-apply trust-boundary documentation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Gate B auto-apply default and fail-open degradation are security-relevant behavior changes but are not documented in `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Gate C summary mode may hide auto-applied changes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: For large plans, Gate C may show only an outline after auto-apply has revised `plan.txt`, so the operator can approve without seeing applied finding changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] run-params.json shares same-UID trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `run-params.json` uses the same same-UID writable session-artifact trust model as other router flags, so a local same-UID process could tamper `manual_gate_b`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Discussion rollback lacks artifact cleanup steps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If a user discusses further and rejects an auto-applied finding, stale `accepted-plan-findings.md` state can cause the next Gate B auto-apply to apply it again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Plan acceptance blocker wiring is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance requires issue `#2667` to be blocked by `#2930` after PR open, but the diff has no blocker wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: Step 4b re-run handler omits auto-applied feedback
- **Reviewer(s)**: dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` Step 4b says reviewers see all approved-by-user prior feedback applied, but default Gate B may have auto-applied feedback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prose-stale-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Approval-gates prompt source wording is stale
- **Reviewer(s)**: dyn-prose-stale-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` still calls itself the single normative source for the three gate prompts, although Gate B’s default path no longer has a prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prose-stale-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Gate B chooser labels are stale
- **Reviewer(s)**: dyn-prose-stale-output.txt
- **Severity**: nit
- **Concern**: Cross-references still label Gate B as “Post-Review Chooser,” which is misleading when `manual_gate_b=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prose-stale-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] No stale Gate B contradictions found outside skills/design
- **Reviewer(s)**: dyn-prose-stale-output.txt
- **Severity**: nit
- **Concern**: A search of docs, README, SECURITY, workflows, and rules found no Gate B contradictions outside `skills/design/`; `SECURITY.md` has no Gate B apply-contract prose to reconcile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prose-stale-output.txt: Address the concern above.
