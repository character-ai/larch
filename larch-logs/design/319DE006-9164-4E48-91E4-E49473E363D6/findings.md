### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-multi-round-integration.sh:204-210
- **Concern**: First integration case still requires round-3 directory and terminal converged on round 3. Scenario: After single-round convergence, degraded round 1 then a nit-only round 2 (collect stub emits only nit severity) yields NON_NIT_ACCEPTED_COUNT=0 and should exit converged at round 2; round-3 assertions and cmp against round-3/plan.txt fail
- **Proposed resolution**: Relax the fixture to expect convergence at round 2 (REASON=converged, ROUNDS_COMPLETED=2) or change the round-2 stub to emit 6+ latent accepted findings so the loop still runs three rounds

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:209
- **Concern**: File references `LARCH_DESIGN_CONVERGENCE_THRESHOLD` but is absent from the plan scope list. Scenario: The plan's Testing Strategy says "zero runtime (non-`larch-logs`) hits for … `LARCH_DESIGN_CONVERGENCE_THRESHOLD`" after the change. Line 209 of approval-gates.md (Gate B apply contract prose) still names the env var as one of two bounds on the loop-internal revision: "bounded by `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`". Because the file is not in scope, it will not be touched, so the grep-sweep verification step will find a live runtime hit and fail.
- **Proposed resolution**: Add `### UPDATED: skills/design/references/approval-gates.md` to the scope list. At line 209 drop "and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`" from the Gate B apply-contract invariant sentence, leaving only `LARCH_DESIGN_ROUND_CAP` as the bound.

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-step3-review-cap.sh:184,192
- **Concern**: Vague plan guidance ("Remove/adjust any `CONVERGENCE_STREAK` references") does not cite the specific stub payload lines, and misses the co-located `REASON=streak` on line 184. Scenario: Lines 184 and 192 embed `CONVERGENCE_STREAK=2` / `CONVERGENCE_STREAK=1` inside `printf` stub strings. Line 184 also contains `REASON=streak`; after the change the real loop emits `REASON=converged`. SKILL.md Step 3 does not branch on the `REASON` value, so there is no functional breakage, but the stub becomes a stale fixture that would no longer reflect any code path the loop can produce.
- **Proposed resolution**: Tighten the plan guidance to cite lines 184 and 192; at line 184 also update `REASON=streak` → `REASON=converged` alongside the `CONVERGENCE_STREAK=2` removal, so the stub matches the new convergence token.

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:209
- **Concern**: `LARCH_DESIGN_CONVERGENCE_THRESHOLD` referenced in prose but file is not in plan scope. Scenario: Plan removes the env var and updates four other `skills/design/references/*.md` files (flags.md, plan-review.md) plus two `docs/*.md` files; `approval-gates.md:209` says "bounded by `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`" and will remain stale post-merge. The plan's grep-sweep post-condition ("zero runtime (non-larch-logs) hits") may not catch this doc reference, leaving a silent divergence.
- **Proposed resolution**: Add `skills/design/references/approval-gates.md` to the scope; in item 4 (line 209), replace "and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`" with nothing (leave only `LARCH_DESIGN_ROUND_CAP`) and update the convergence-bound description to match the new hardcoded-5 semantics.

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-step3-review-cap.sh:184,192
- **Concern**: Plan guidance says "Remove/adjust any `CONVERGENCE_STREAK` references" with no cited lines; embedded stub strings at lines 184 and 192 contain both `CONVERGENCE_STREAK=2` / `CONVERGENCE_STREAK=1` AND `REASON=streak` that must also change to `REASON=converged`. Scenario: Without explicit line citations, the `REASON=streak` → `REASON=converged` rename in the stub printf strings (same lines as the `CONVERGENCE_STREAK` removals) is easily overlooked. If SKILL.md surfaces REASON in any status output that the test subsequently checks, the test will pass a stale reason value; even if no assertion fires today, the stub diverges from the new invariant and will mislead future harness authors.
- **Proposed resolution**: Extend plan guidance for this file to cite lines 184 and 192 explicitly; specify that both `CONVERGENCE_STREAK=N` and `REASON=streak` must be updated to `REASON=converged` (and `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` zero values added if the new KV surface includes them) in each stub's printf string.
