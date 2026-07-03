### OOS_1: [OUT_OF_SCOPE] Gate C lettering mismatch
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: The state-invariant wording in `approval-gates.md` still uses older Gate C lettering, which can confuse operators even though the underlying behavior predates this compression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Normalize Gate C option letters in a follow-up doc pass if operator confusion is observed; no runtime change required.

### OOS_2: [OUT_OF_SCOPE] Non-numeric warning text not pinned
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The `REVIEW_ROUND_COUNT_WARN=non-numeric` path no longer pins exact warning prose, so byte-stable logging can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: If byte-stable logging matters, pin the warning string in `design_gate_render.py` docs or a one-line literal here; otherwise rely on the existing KV contract.
  - From cursor-specialist-edge-cases: Pin the exact `execution-issues.md` line in the renderer contract or emit it from a Python helper so logging cannot drift.

### OOS_3: [OUT_OF_SCOPE] Large-plan summary cross-ref is stale
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The large-plan summary pointer now relies on thinner preview-only prose and no longer carries the invocation/harness details that keep the eager-load cross-reference aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Optional SKILL one-liner update in a separate doc PR; behavior is owned by the preview CLI and tests in `python/test_plan_review.py`.
  - From cursor-specialist-edge-cases: Repoint the SKILL.md cross-ref to the preview script or `python/test_plan_review.py` contract to avoid a stale eager-load pointer.
  - From cursor-specialist-testing: Optional: add a structure test that approval-gates references plan-review preview for summary mode and omits inline LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD defaults.

### OOS_4: [OUT_OF_SCOPE] Zero-findings continuation carve-out missing
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-gate-contract
- **Severity**: important
- **Concern**: Gate C no longer spells out that zero-findings / degraded-panel paths may continue through the script-internal continuation helper before reaching Step 3b finalize → Step 4 → Gate C, so the eager prose reads more forward-moving than the actual control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Only restore a one-line pointer if prompt-side debugging of auto-continuation is a recurring operator need.
  - From dyn-dyn-gate-contract: Add back a short carve-out that zero-findings / degraded-panel paths continue via the script-internal continuation helper until it stops, and only then reach Step 3b → Step 4 → Gate C.

### OOS_5: [OUT_OF_SCOPE] Missing grep pins for routing literals
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The design-structure harness does not pin the required `FINDING_IDS` and Gate A missing-plan literals, so prose edits could loosen those routing contracts without a failing check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add contains checks for both verbatim strings to scripts/test-design-structure.sh.

### OOS_6: [OUT_OF_SCOPE] Missing negative pins for cap prose
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The structure test does not block reintroducing renderer-owned cap math or the Gate C tier cap prose, so duplicated cap wording could creep back in.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add not_contains pins for _gate_c_options, effective_authorized_cap, and ### Gate C tier cap.

### OOS_7: [OUT_OF_SCOPE] Step 3 cap-hit breadcrumb removed
- **Reviewer(s)**: dyn-dyn-gate-contract
- **Severity**: latent
- **Concern**: The eager gate reference no longer includes the step-3 cap-hit breadcrumb / short-circuit chain, so operator-visible cap-routing prose can drift away from the actual behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-contract: Address the concern above.

