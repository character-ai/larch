### FINDING_1: Refine-loop semantics and operator literals unprotected during compression
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned whole-file density pass treats the Refine loop (lines 106–116) as compressible prose while the Approach byte-stable preserve list only freezes `AskUserQuestion` question/header/option labels (and Cancel hygiene after round 2). Load-bearing Refine-loop rules are not named in Approach or Edge cases: empty/non-actionable replies must not approve; free-form operator messages are refinement input, not implicit approve/cancel; **Refine outline** must not write `$DESIGN_TMPDIR/.outline-approved`; the loop must continue until explicit **Approve outline** or **Cancel**. Operator-visible literals at risk include the free-form refine question (`"What would you like to refine? …"`), the `## Updated Design Outline` reprint header, and the re-fire-the-same-approval-prompt rule. A ~15% cut can paraphrase or drop these while frozen `AskUserQuestion` labels and Cancel-hygiene `rg` checks still pass, letting empty refinement advance, changing refine UX/loop termination, or writing `.outline-approved` on Refine.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add Edge-case bullets (or one Approach preserve bullet) naming these Refine-loop condition/action pairs as frozen semantics; prose may tighten but the rules must remain explicit and unmerged.
  - From Cursor-Innovation: Add Refine-loop literals to the Approach byte-stable preserve list (mirror Cancel hygiene): the free-form question string, `## Updated Design Outline`, empty/non-actionable reply handling, and the re-fire-the-same-approval-prompt rule. Optionally add matching `rg -F` checks beside the Cancel hygiene gate.
  - From Cursor-Pragmatic: Add these operator-visible literals to Approach byte-stable preserve (same treatment as Cancel hygiene) and extend post-edit rg gates beyond the three Cancel lines to cover at least the skip/approve/auto-approve breadcrumbs and the Refine free-form question.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Stale Step 3 downstream reference names deleted plan-review-loop.sh
- **Description**: [OUT_OF_SCOPE] Stale Step 3 downstream reference names deleted plan-review-loop.sh. Scenario: Downstream consumer contract still says `plan-review-loop.sh` appends `design-outline.md` to the scope anchor, but that script is gone; `python/cli.py plan-review step3-entry` builds `plan-review-scope-anchor.txt` in `python/larch/review/plan_review.py`. A density pass on that section may rewrite the claim as a drive-by fix or paraphrase it into incorrect operator guidance.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/design-outline.md:134
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Downstream Step 3 still names retired `plan-review-loop.sh`
- **Description**: [OUT_OF_SCOPE] Downstream Step 3 still names retired `plan-review-loop.sh`. Scenario: Step 3 scope anchoring is implemented in `python/larch/review/plan_review.py` `step3_entry` (writes `plan-review-scope-anchor.txt` from stripped issue body plus approved outline). Line 134 still cites `plan-review-loop.sh`. Fixing the name during compression is doc accuracy only, not required for the ~15% prose gate or ratchet.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/design-outline.md:134
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

