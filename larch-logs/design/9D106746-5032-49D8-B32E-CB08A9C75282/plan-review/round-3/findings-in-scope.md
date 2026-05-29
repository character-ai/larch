Reviewing the cited locations to confirm the two findings are distinct and to normalize titles and concerns.
Two independent risks: documentation drift after retiring `cancelled-tier-gate`, and `design_classification` not bound before Step 0b sub-step 4 early exits. No merge.

### FINDING_1: Sibling doc still lists retired tier-gate cancel
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Concern**: Plan retires `cancelled-tier-gate` in `render-final-summary.sh` and `scripts/render-run-summary.md` but omits the script sibling contract doc. Callers list still documents a Step 0b `tier-gate cancel` after the outcome and gate are removed; sibling-doc rule and the plan’s SKILL/script/doc/test enum goal are not fully met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/scripts/render-final-summary.md` — drop `tier-gate cancel` from the Step 0b callers bullet (line 14) and align the `SUMMARY_OUTCOME` note with the retired outcome set

### FINDING_2: design_classification bound too late for early Step 0b exits
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Approach says tier resolves during flag parsing but Step 0b edits only replace sub-step 5 Tier resolution. Sub-step 4 already-planned ad-hoc Q&A exits before sub-steps 5–6; run-params merges can lack `design_classification` even though default SIMPLE is the product intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add to Step 0b item 1: bind design_classification to HARD when --hard is parsed else SIMPLE immediately after public flag parse; keep sub-step 5 as a no-op reaffirmation or drop redundant prose
