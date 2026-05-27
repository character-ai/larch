# Review Round 4

- Mode: `diff`
- 9 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: Gate B degraded-path manual fallback conflicts with default auto-apply contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-plan-fidelity-manual-flag-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-session-env-manual-propagation-output.txt
- **Severity**: important
- **Concern**: Gate B currently fails closed to `manual_gate_b=true` when `run-params.json` cannot be read, `jq` is unavailable, or persisted `manual_gate_b=false` cannot be proven. Multiple surfaces say or imply default `/design` without `--manual` should auto-apply on this degraded path, so default runs can unexpectedly show the manual 3-option Gate B prompt and contradict SECURITY/plan/default behavior documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-plan-fidelity-manual-flag-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-session-env-manual-propagation-output.txt: Address the concern above.


### FINDING_12: SECURITY trust-boundary text understates indirect dry-run risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: SECURITY says auto-apply does not directly execute reviewer commands, but omits that auto-applied plan text can still reach Tier 3 dry-run validation probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_13: Step 0b does not mechanically refresh current design env before write-run-params
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-session-env-manual-propagation-output.txt
- **Severity**: important
- **Concern**: Step 0b requires refreshing `current-design-env` for `ISSUE_NUMBER` and `MANUAL_REQUESTED`, but only the `write-run-params.sh` call is fenced. If the model skips the prose-only refresh, session env may lack `MANUAL_REQUESTED=true`, reviving a silent-loss-of-`--manual` path when `write-run-params` also fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-session-env-manual-propagation-output.txt: Address the concern above.


### FINDING_19: Go-through-each option does not verbatim call shared post-apply pipeline
- **Reviewer(s)**: dyn-apply-all-body-dedup-output.txt
- **Severity**: important
- **Concern**: The manual “Go through each” AskUserQuestion option paraphrases the shared post-apply pipeline instead of saying `Execute ### Shared post-apply pipeline verbatim`, leaving a drift path where an orchestrator may re-inline dedup, emit, validation, and Step 2b.5 logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-apply-all-body-dedup-output.txt: Address the concern above.


### FINDING_2: Duplicate structural grep pins do not guard distinct Gate B invariants
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gate-b-mode-resolution-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` contains duplicate or near-duplicate grep pins for the same approval-gates sentence. The duplicated checks add CI noise but do not catch distinct regressions, such as moving zero-findings ordering or changing mode-resolution behavior while preserving the literal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gate-b-mode-resolution-output.txt: Address the concern above.


### FINDING_20: Missing structural count pin for shared post-apply pipeline call sites
- **Reviewer(s)**: dyn-apply-all-body-dedup-output.txt
- **Severity**: latent
- **Concern**: Tests pin the shared post-apply heading and count Apply-all body references, but do not count the `executes ### Shared post-apply pipeline verbatim` call sites, so future inline duplication could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-apply-all-body-dedup-output.txt: Address the concern above.


### FINDING_3: Gate B zero-findings short-circuit appears after mode and apply sections
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt
- **Severity**: latent
- **Concern**: `approval-gates.md` says Gate B mode resolution happens only after the zero-findings short-circuit, but the file presents mode, presentation, prompt, and apply-all sections before the zero-findings section. A linear executor may resolve mode or apply findings before checking whether there are any accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt: Address the concern above.


### FINDING_8: Missing executable regression for manual-only write-run-params recovery
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Router-flag jq-merge recovery is pinned mostly by prose literals, with no executable harness proving that a `--manual` run whose initial `write-run-params` fails preserves `.manual_gate_b == true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Missing structural pin for `jq -r '.manual_gate_b // false'`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: A hard constraint expects missing/null `manual_gate_b` to coerce to false, but CI lacks a direct structural pin for the jq idiom, so a future edit could drop `// false` unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


