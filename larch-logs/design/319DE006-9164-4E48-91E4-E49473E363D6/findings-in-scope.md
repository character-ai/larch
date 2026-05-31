### FINDING_1: Multi-round integration test still asserts round-3 convergence
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The first integration case in `scripts/test-design-multi-round-integration.sh` (lines 204–210) still requires a round-3 directory and terminal convergence on round 3. After single-round convergence, a degraded round 1 followed by a nit-only round 2 (collect stub emits only nit severity) yields `NON_NIT_ACCEPTED_COUNT=0` and should exit converged at round 2. Round-3 assertions and `cmp` against `round-3/plan.txt` will fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Relax the fixture to expect convergence at round 2 (`REASON=converged`, `ROUNDS_COMPLETED=2`) or change the round-2 stub to emit 6+ latent accepted findings so the loop still runs three rounds

### FINDING_2: `approval-gates.md` still names removed env var but is out of plan scope
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: `skills/design/references/approval-gates.md` line 209 references `LARCH_DESIGN_CONVERGENCE_THRESHOLD` in Gate B apply-contract prose (“bounded by `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`”), but the file is absent from the plan scope list. The plan removes the env var elsewhere and its Testing Strategy expects zero runtime (non-`larch-logs`) hits for `LARCH_DESIGN_CONVERGENCE_THRESHOLD`. Because `approval-gates.md` will not be touched, the grep-sweep verification step may find a live reference and fail, or leave a silent divergence from the new convergence semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add `### UPDATED: skills/design/references/approval-gates.md` to the scope list. At line 209 drop "and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`" from the Gate B apply-contract invariant sentence, leaving only `LARCH_DESIGN_ROUND_CAP` as the bound.
  - From unknown-slot: Add `skills/design/references/approval-gates.md` to the scope; in item 4 (line 209), replace "and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`" with nothing (leave only `LARCH_DESIGN_ROUND_CAP`) and update the convergence-bound description to match the new hardcoded-5 semantics.

### FINDING_3: `test-step3-review-cap.sh` stub fixtures omit explicit `REASON=streak` updates
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Concern**: Plan guidance (“Remove/adjust any `CONVERGENCE_STREAK` references”) does not cite the specific stub payload lines and misses co-located `REASON=streak` on line 184. Lines 184 and 192 embed `CONVERGENCE_STREAK=2` / `CONVERGENCE_STREAK=1` inside `printf` stub strings; line 184 also contains `REASON=streak`. After the change the real loop emits `REASON=converged`. SKILL.md Step 3 does not branch on `REASON`, so there is no functional breakage today, but without explicit line citations the `REASON=streak` → `REASON=converged` rename is easily overlooked, leaving stale stubs that diverge from the new invariant and may mislead future harness authors or fail if assertions later surface `REASON`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Tighten the plan guidance to cite lines 184 and 192; at line 184 also update `REASON=streak` → `REASON=converged` alongside the `CONVERGENCE_STREAK=2` removal, so the stub matches the new convergence token.
  - From unknown-slot: Extend plan guidance for this file to cite lines 184 and 192 explicitly; specify that both `CONVERGENCE_STREAK=N` and `REASON=streak` must be updated to `REASON=converged` (and `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` zero values added if the new KV surface includes them) in each stub's printf string.
