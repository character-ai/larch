### OOS_1: [OUT_OF_SCOPE] Weak structure-test ordering pin for step1d5 elision
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Plan-required ordering assertion before step1d5 entry fence is only a contains check. SKILL prose could place elision after the entry fence; orchestrator might still run the near-no-op entry turn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use check_context_before or assert_line_precedes anchoring at step1d5 --mode entry.

### OOS_2: [OUT_OF_SCOPE] Symlinked run-params.json split authority at Step 2a prep
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: risk-integration `python/larch/design/design_lifecycle.py:3172-3180` — `_folded_step2a_sentinel_prep` reads `run-params.json` without the symlink rejection in `_step1d5_brainstorm_requested`. A symlinked `run-params.json` could disagree on `brainstorm_requested` between Step 1d.7 and Step 2b repair. Pre-existing; outcomes still look safe on the brainstorm-off path because Step 1d.7 writes `step-1d.5` first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reuse `_step1d5_brainstorm_requested` in `_folded_step2a_sentinel_prep` for one authority.

### OOS_3: [OUT_OF_SCOPE] Prompt-side elision cannot block direct step1d5 entry
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: risk-integration `skills/design/SKILL.md:331-335` — Elision is prompt-side only; Python does not block a direct `step1d5 --mode entry` call. Wrong orchestrator elision on `resume@*` (mental binding vs `run-params.json`) could skip brainstorm when `brainstorm_requested: true`. The plan mitigates this with SKILL prose and structure tests; `step1d7_main` correctly avoids fabricating `step-1d.5` on brainstorm-on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optional fail-closed guard in `step1d7_main` when brainstorm is on, `.brainstorm-done` is absent, and `step-1d.5` is missing (emit a loud error instead of continuing to outline).

### OOS_4: [OUT_OF_SCOPE] Step 1d.5 timing mark omitted on brainstorm-off elision
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/design/design_lifecycle.py:2999` — Eliding the Step 1d.5 entry fence skips the `timing mark "design Step 1d.5 — brainstorm"` that `_step1d5_entry_main` still emits on the skip path. Dominant-path timing ledgers lose a Step 1d.5 mark.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accept as telemetry trade-off, or add a no-op timing mark at the elision breadcrumb if parity matters.

### OOS_5: [OUT_OF_SCOPE] chore(larch-logs) flush bundled on branch
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `42f4895bd` — chore(larch-logs) flush is out of scope for feature review; the branch otherwise matches the plan with planned lifecycle tests and structure pins present and no in-scope defects identified by the testing reviewer.

