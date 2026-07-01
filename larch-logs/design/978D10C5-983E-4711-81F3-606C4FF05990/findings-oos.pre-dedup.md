### OOS_1: [OUT_OF_SCOPE] Stale Step 3 downstream reference names deleted plan-review-loop.sh
- **Description**: [OUT_OF_SCOPE] Stale Step 3 downstream reference names deleted plan-review-loop.sh. Scenario: Downstream consumer contract still says `plan-review-loop.sh` appends `design-outline.md` to the scope anchor, but that script is gone; `python/cli.py plan-review step3-entry` builds `plan-review-scope-anchor.txt` in `python/larch/review/plan_review.py`. A density pass on that section may rewrite the claim as a drive-by fix or paraphrase it into incorrect operator guidance.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/design-outline.md:134
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Downstream Step 3 still names retired `plan-review-loop.sh`
- **Description**: [OUT_OF_SCOPE] Downstream Step 3 still names retired `plan-review-loop.sh`. Scenario: Step 3 scope anchoring is implemented in `python/larch/review/plan_review.py` `step3_entry` (writes `plan-review-scope-anchor.txt` from stripped issue body plus approved outline). Line 134 still cites `plan-review-loop.sh`. Fixing the name during compression is doc accuracy only, not required for the ~15% prose gate or ratchet.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/design-outline.md:134
- **Phase**: design



