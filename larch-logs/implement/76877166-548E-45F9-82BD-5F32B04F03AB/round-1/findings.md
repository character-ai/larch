### FINDING_1: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:1223
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Pre-existing duplicated word unavailable in Cursor fallback bullet. Not changed by this diff. Fix in a separate edit if desired.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/references/discussion-rounds.md:15-23
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicates the Step 1c intro sentence about highest-value question point and reshaping sketches. Longer spec with no behavioral contradiction; slightly weaker skimmability. Keep rationale in either L15 or the guideline bullet, not both in full.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/references/discussion-rounds.md:15-23
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicated highest-value / reshape-sketches rhetoric between the Step 1c intro and the first guideline bullet. Longer prompt with no new mechanical rule. Keep the motivational sentence in only one place.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/references/discussion-rounds.md:15-23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate prose: intro and new Step 1c guideline both assert highest-value question point and reshaping sketches. Step 1c body is longer with repeated messaging; no extra behavioral constraint. Keep one occurrence (intro or guideline); trim the other to doubt/cost/suppress-only wording only.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/design/references/discussion-rounds.md:15-23
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Repeated “highest-value question point” messaging in adjacent lines. Slightly higher token cost and no functional failure. Keep one emphatic sentence; trim the duplicate in the guideline bullet or the lead paragraph.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/SKILL.md:1229
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Opportunistic questions no longer explicitly require resolving ambiguity against CLAUDE.md before AskUserQuestion (unlike prior text and unlike auto_mode=true Q/A derivation in §2.3). auto_mode=false run asks the user about something already answered in CLAUDE.md because the model did not consult it first. Add a soft clause to consult CLAUDE.md when it may resolve the interpretation, without restoring strict suppression.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/design/references/discussion-rounds.md:22-25 and skills/implement/SKILL.md:1229
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No CI or shell harness asserts the new AskUserQuestion policy wording. A future revert to stricter suppression copy could merge undetected until operators notice behavior. Optional: pin a short distinctive substring per file in scripts/test-implement-structure.sh or test-implement-anti-halt.sh.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/implement/SKILL.md:1229
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Opportunistic-question trigger no longer explicitly defers to CLAUDE.md before asking (plan-intentional vs prior text). Ambiguity resolvable from CLAUDE.md but not plan/code could still produce a batched AskUserQuestion. If redundant pings appear, add after consulting CLAUDE.md to the ambiguity check without restoring strong suppression.
- **Suggested revision**: Address the concern above.

