### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/scripts/render-final-summary.md:14
- **Concern**: Plan retires `cancelled-tier-gate` in `render-final-summary.sh` and `scripts/render-run-summary.md` but omits the script sibling contract doc. Scenario: Callers list still documents a Step 0b `tier-gate cancel` after the outcome and gate are removed; sibling-doc rule and the plan’s SKILL/script/doc/test enum goal are not fully met
- **Proposed resolution**: Add `### UPDATED: skills/design/scripts/render-final-summary.md` — drop `tier-gate cancel` from the Step 0b callers bullet (line 14) and align the `SUMMARY_OUTCOME` note with the retired outcome set

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:191-267
- **Concern**: Approach says tier resolves during flag parsing but Step 0b edits only replace sub-step 5 Tier resolution. Scenario: Sub-step 4 already-planned ad-hoc Q&A exits before sub-steps 5-6; run-params merges can lack design_classification even though default SIMPLE is the product intent
- **Proposed resolution**: Add to Step 0b item 1: bind design_classification to HARD when --hard is parsed else SIMPLE immediately after public flag parse; keep sub-step 5 as a no-op reaffirmation or drop redundant prose
