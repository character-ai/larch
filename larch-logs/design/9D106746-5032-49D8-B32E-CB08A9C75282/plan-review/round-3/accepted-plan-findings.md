### FINDING_1: Sibling doc still lists retired tier-gate cancel
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Concern**: Plan retires `cancelled-tier-gate` in `render-final-summary.sh` and `scripts/render-run-summary.md` but omits the script sibling contract doc. Callers list still documents a Step 0b `tier-gate cancel` after the outcome and gate are removed; sibling-doc rule and the plan’s SKILL/script/doc/test enum goal are not fully met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/scripts/render-final-summary.md` — drop `tier-gate cancel` from the Step 0b callers bullet (line 14) and align the `SUMMARY_OUTCOME` note with the retired outcome set


