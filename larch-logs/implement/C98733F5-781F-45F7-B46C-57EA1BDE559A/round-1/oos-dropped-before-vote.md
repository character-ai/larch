### OOS_1: [OUT_OF_SCOPE] Step 1.r folded-relay sentence violates plan pin
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: At `skills/implement/SKILL.md:261`, the plan-required byte-stable folded-relay sentence was extended with an unpinned parenthetical summarizing `CHECKPOINT_NEXT` routing. Structural require still passes via substring match, but the edit violates the approved plan pin and slightly increases tokens on a target shrink line. Remove the parenthetical and restore the exact pinned folded-relay sentence; macro text already covers the semantics.

### OOS_2: [OUT_OF_SCOPE] Step 8+ pre-driver vs matrix read ordering
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-routing-pins
- **Severity**: latent
- **Concern**: Step 8+ still says “Run `ship pre-driver` before reading the Step 8+ matrix” above the mandatory matrix read, while the `ship pre-driver` fence appears later. That ordering contradiction predates this branch; the diff did not introduce or amplify it.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none with actionable fix text beyond scope acknowledgment)

### OOS_3: [OUT_OF_SCOPE] Absorbed `1.r` scoping moved to Step 1.r routing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Absorbed-`1.r` “In that branch” scoping now lives mainly in **Step 1.r routing**, not the macro paragraph. Redundant but harmless; intentional density trade-off with duplicate guard still present elsewhere.

### OOS_4: [OUT_OF_SCOPE] Baseline density measurement / ROI notes
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-routing-pins
- **Severity**: nit
- **Concern**: `python/skill-closure-baseline.json` reflects modest token reduction (~142 tokens, `28374` → `28232`) with unchanged `skill_md_lines` (789), so further gains may need reflow rather than sentence trims alone. Baseline regeneration matches the intended reduction; acceptance is met but ROI is small relative to the ~28k-token surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: none required for this PR; track follow-on density targets separately if needed.

### OOS_5: [OUT_OF_SCOPE] Step 1.r parenthetical drift on pinned sentence
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: At `skills/implement/SKILL.md:261`, the folded-relay sentence gained a parenthetical (`continue` skips / `load-routing` or missing/malformed loads) beyond the plan’s byte-stable pin. Harnesses still pass, but additive drift on pinned sentences makes future density edits harder to audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: keep macro authority in the Rebase Checkpoint Macro block only, or extend the structure test if the parenthetical is intentional.

### OOS_6: [OUT_OF_SCOPE] Step 1.r parenthetical ambiguity (pre-existing)
- **Reviewer(s)**: dyn-dyn-routing-pins
- **Severity**: nit
- **Concern**: At `skills/implement/SKILL.md:261`, the Step 1.r parenthetical ``(`continue` skips the reference; `load-routing` or missing/malformed values load it)`` softens the macro’s explicit `Missing or malformed CHECKPOINT_NEXT fails closed` contract. This text is unchanged on this branch versus `origin/main`; pre-existing ambiguity, not introduced here.

---

**Merge notes (non-output):**
- **Subsumed:** Testing findings 6–14 (commit summary, scope statement, and `make test-*` PASS lines) are attestation, not distinct actionable risks; `cursor-specialist-testing` is attributed via FINDING_6 and FINDING_7.
- **Not merged across scope:** FINDING_3 (in-scope nit on line 261) stays separate from OOS parenthetical notes (FINDING_7/8) and from in-scope macro guards (FINDING_1/2).
- **Slot coverage:** All four inventory slots appear in at least one `- **Reviewer(s)**:` line; `cursor-specialist-edge-cases` appears only in `[OUT_OF_SCOPE]` blocks.

