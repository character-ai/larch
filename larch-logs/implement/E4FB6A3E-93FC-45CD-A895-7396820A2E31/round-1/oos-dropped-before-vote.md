### OOS_1: [OUT_OF_SCOPE] Conditional path extraction silently skips unresolvable markdown
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Conditional path extraction uses `strict=False` and silently skips unresolvable markdown operands, so a typo in a conditional-only reference would disappear from both report sections without a `ScanError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accept as an intentional tradeoff per the plan, or add optional warn-only diagnostics when a conditional directive mentions `.md` but yields zero resolved paths.

### OOS_2: [OUT_OF_SCOPE] CONDITIONAL_SUFFIX_RE over-matches incidental `(if …)` parentheticals
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `CONDITIONAL_SUFFIX_RE` treats any post-directive `(if …)` parenthetical as conditional. That matches current `settle-rc-dispatch.md` / `approval-gates.md` re-entry lines, but a future eager `MANDATORY READ` with an incidental `(if …)` clause on the same line would be misclassified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Tighten the suffix pattern (for example require `(if not already loaded`) or add a regression fixture if prose style drifts.

### OOS_3: [OUT_OF_SCOPE] Hardcoded CONDITIONAL_DESIGN_SECTIONS maintenance drift
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Design conditional sections are a hardcoded `CONDITIONAL_DESIGN_SECTIONS` frozenset, similar to implement macro suppression. New branch-only design sections would stay eager until the set is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document the maintenance contract in a module comment, or extend tests to assert the four known conditional design files stay out of the eager baseline.

### OOS_4: [OUT_OF_SCOPE] Validator-failure test scope closes on fictional heading
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `test_design_validator_failure_section_is_conditional_until_next_peer_heading` closes scope with a fictional `### Plan helper contracts` heading, while real `skills/design/SKILL.md` uses bold `**Plan helper contracts**` at line 679 and has no later `###` peer. Behavior is correct today (only one MANDATORY READ in that section, at line 665), but a future eager read after line 665 could be misclassified as conditional-only until a real heading boundary exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: optional hardening later: close validator-failure scope at the bold contracts line or EOF guard; not required for current acceptance.

### OOS_5: [OUT_OF_SCOPE] Unbraced CLAUDE_PLUGIN_ROOT paths silently dropped
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_is_runtime_markdown_operand` treats unbraced `$CLAUDE_PLUGIN_ROOT/...` as runtime and skips it. Current skills use `${CLAUDE_PLUGIN_ROOT}/...` for markdown operands, so CI passes, but unbraced plugin-root paths would be silently dropped from both closures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: exclude `CLAUDE_PLUGIN_ROOT` from the bare `$VAR/` runtime pattern if unbraced plugin paths are ever introduced.

### OOS_6: [OUT_OF_SCOPE] Implement scan test omits content-token baseline assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `test_real_implement_scan_keeps_eager_baseline_unchanged` asserts `closure_lines` and `closure_estimated_tokens` but not `closure_content_estimated_tokens`, leaving a narrow metric drift undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: add the content-token equality assertion for symmetry with the baseline row.

---

**Merge notes (brief):** Input FINDING_6 and FINDING_7 from `cursor-specialist-testing` are positive plan-traceability and coverage acknowledgments with no actionable defect; they are omitted as findings. `cursor-specialist-testing` attribution is preserved via FINDING_6–8 above (its three `[OUT_OF_SCOPE]` items). No other input findings were duplicate merges.

