### FINDING_1: Gate B degraded-path manual fallback conflicts with default auto-apply contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-plan-fidelity-manual-flag-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-session-env-manual-propagation-output.txt
- **Severity**: important
- **Concern**: Gate B currently fails closed to `manual_gate_b=true` when `run-params.json` cannot be read, `jq` is unavailable, or persisted `manual_gate_b=false` cannot be proven. Multiple surfaces say or imply default `/design` without `--manual` should auto-apply on this degraded path, so default runs can unexpectedly show the manual 3-option Gate B prompt and contradict SECURITY/plan/default behavior documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-plan-fidelity-manual-flag-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-session-env-manual-propagation-output.txt: Address the concern above.

### FINDING_2: Duplicate structural grep pins do not guard distinct Gate B invariants
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gate-b-mode-resolution-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` contains duplicate or near-duplicate grep pins for the same approval-gates sentence. The duplicated checks add CI noise but do not catch distinct regressions, such as moving zero-findings ordering or changing mode-resolution behavior while preserving the literal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gate-b-mode-resolution-output.txt: Address the concern above.

### FINDING_3: Gate B zero-findings short-circuit appears after mode and apply sections
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt
- **Severity**: latent
- **Concern**: `approval-gates.md` says Gate B mode resolution happens only after the zero-findings short-circuit, but the file presents mode, presentation, prompt, and apply-all sections before the zero-findings section. A linear executor may resolve mode or apply findings before checking whether there are any accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt: Address the concern above.

### FINDING_4: Gate B mode precedence is spread across three layers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Gate B mode resolution depends on session env, in-memory `manual_requested`, and `run-params.json`, making behavior harder to predict across subshell re-entry and doc surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Router-flag recovery overwrites `manual_gate_b` instead of sticky OR merge
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt, dyn-session-env-manual-propagation-output.txt
- **Severity**: latent
- **Concern**: Step 0b jq recovery assigns `.manual_gate_b = $merge_m` while partition/brainstorm use OR semantics and some plan text expected `(.manual_gate_b == true or $merge_m)`. Depending on intended semantics, recovery can clear a previously persisted manual mode or documentation/tests can misrepresent the intended argv-authoritative overwrite behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt, dyn-session-env-manual-propagation-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Writer accepts explicit `--manual-requested false`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write-design-current-env.sh` accepts `--manual-requested false` even though SKILL guidance says to omit the flag when non-manual, which may encourage future readers to export `MANUAL_REQUESTED=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: MANUAL_REQUESTED precedence is not mechanically enforced in Step 3.5
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate B precedence says `MANUAL_REQUESTED=true` wins, but Step 3.5 relies on prose rather than a mechanical mode resolver. A `/design --manual` run with failed `run-params` persistence or skipped env sourcing could auto-apply if the orchestrator only reads `run-params.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_10: `manual_gate_b` jq read does not coerce non-boolean JSON
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `jq -r '.manual_gate_b // false'` can return non-boolean strings or other corrupt values, routing unpredictably between auto and manual Gate B branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Gate B auto-apply trust boundary may allow untrusted reviewer prose to affect validation probes
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Default Gate B auto-apply can merge accepted reviewer findings into `plan.txt` without per-finding consent and then run `EMIT_PLAN` plus full-budget `VALIDATE_PLAN_COMMANDS`. Compromised or mistaken reviewer prose can therefore indirectly influence allowlisted dry-run probes before Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_14: Plan acceptance blocked-by edge is not verifiable from branch diff
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Acceptance lists native GitHub blocked-by edge `#2667 blocked-by #2930`, but that relationship is not verifiable from the branch diff. Dependent work may proceed before #2930 lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Step 0b router-flag recovery is complete
- **Reviewer(s)**: dyn-plan-fidelity-manual-flag-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports Step 0b’s four-arm router-flag recovery already covers the load-bearing `--manual`-only write-failure case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-fidelity-manual-flag-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] `manual_gate_b = $merge_m` is intentional argv-authoritative behavior
- **Reviewer(s)**: dyn-plan-fidelity-manual-flag-output.txt
- **Severity**: nit
- **Concern**: The reviewer treats the overwrite form as an intentional architectural asymmetry because `manual_gate_b` is argv-only, unlike sticky partition/brainstorm state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-fidelity-manual-flag-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] `write-design-current-env.sh` and Step 0b manual omission are consistent
- **Reviewer(s)**: dyn-plan-fidelity-manual-flag-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports the writer only exports `MANUAL_REQUESTED` when non-empty and Step 0b appends `--manual-requested true` only for manual runs, matching Gate B precedence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-fidelity-manual-flag-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Triple-layer Gate B resolution is coherent
- **Reviewer(s)**: dyn-plan-fidelity-manual-flag-output.txt
- **Severity**: nit
- **Concern**: The reviewer considers session env, in-memory `manual_requested`, and `run-params.json` coherent for `/design`’s inline orchestrator model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-fidelity-manual-flag-output.txt: Address the concern above.

### FINDING_19: Go-through-each option does not verbatim call shared post-apply pipeline
- **Reviewer(s)**: dyn-apply-all-body-dedup-output.txt
- **Severity**: important
- **Concern**: The manual “Go through each” AskUserQuestion option paraphrases the shared post-apply pipeline instead of saying `Execute ### Shared post-apply pipeline verbatim`, leaving a drift path where an orchestrator may re-inline dedup, emit, validation, and Step 2b.5 logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-apply-all-body-dedup-output.txt: Address the concern above.

### FINDING_20: Missing structural count pin for shared post-apply pipeline call sites
- **Reviewer(s)**: dyn-apply-all-body-dedup-output.txt
- **Severity**: latent
- **Concern**: Tests pin the shared post-apply heading and count Apply-all body references, but do not count the `executes ### Shared post-apply pipeline verbatim` call sites, so future inline duplication could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-apply-all-body-dedup-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Apply-all factoring is structurally sound
- **Reviewer(s)**: dyn-apply-all-body-dedup-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports the two-level factoring between `### Apply-all body` and `### Shared post-apply pipeline` is sound and no orphaned inline dedup copy remains in `approval-gates.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-apply-all-body-dedup-output.txt: Address the concern above.

### FINDING_22: Same-shell re-source can leave stale `MANUAL_REQUESTED=true`
- **Reviewer(s)**: dyn-session-env-manual-propagation-output.txt
- **Severity**: latent
- **Concern**: `write-design-current-env.sh` omits `MANUAL_REQUESTED` when the flag is absent but does not write `unset MANUAL_REQUESTED`. Re-sourcing the rewritten file in the same shell after a previous true value can leave stale manual mode active, while existing tests only validate fresh-subshell behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-session-env-manual-propagation-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] write-design-current-env contract file omits implemented cases
- **Reviewer(s)**: dyn-session-env-manual-propagation-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-write-design-current-env.md` documents cases 1-8, but implemented cases 9-12 are not reflected in the sibling contract file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-session-env-manual-propagation-output.txt: Address the concern above.
