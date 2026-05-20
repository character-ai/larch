### FINDING_3: [OUT_OF_SCOPE] **Exit 6 / Exit 0 edits vs `scripts/ship-pr.sh`:** Changing Exit 6 (and the generic Exit 0 branch) away from `--resume-phase $PHASE` toward “same `Invoke:` argv, no `--resume-phase`” is consistent with `scripts/ship-pr.sh:1673-1681`, where arbitrary `PHASE` strings such as `checks` or `pr-prep` would hit `unknown --resume-phase` and abort, while `ci-initial` / `ci-merge` are legal resume tokens but are not required for a plain main-loop continuation when state already holds `PHASE`.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **Exit 6 / Exit 0 edits vs `scripts/ship-pr.sh`:** Changing Exit 6 (and the generic Exit 0 branch) away from `--resume-phase $PHASE` toward “same `Invoke:` argv, no `--resume-phase`” is consistent with `scripts/ship-pr.sh:1673-1681`, where arbitrary `PHASE` strings such as `checks` or `pr-prep` would hit `unknown --resume-phase` and abort, while `ci-initial` / `ci-merge` are legal resume tokens but are not required for a plain main-loop continuation when state already holds `PHASE`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] **Inline vs NEVER #16 token enumeration:** The blockquote at `skills/implement/SKILL.md:1727` defers to “same list as NEVER #16” instead of re-listing tokens, so there is no silent second enumeration to drift out of sync with NEVER #16.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **Inline vs NEVER #16 token enumeration:** The blockquote at `skills/implement/SKILL.md:1727` defers to “same list as NEVER #16” instead of re-listing tokens, so there is no silent second enumeration to drift out of sync with NEVER #16.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] **`--resume-phase` token list vs `scripts/ship-pr.sh`:** The explicit list in NEVER #16 (`force-push-gate`, `bump`, `pr-create`, `ci-initial`, `ci-merge`, `evaluate-failure`, `postmerge`) matches the `case "$RESUME_PHASE"` arms in `scripts/ship-pr.sh:1674-1680` (with `force-push-gate|bump` correctly represented as two accepted spellings that both enter the bump resume arm).
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **`--resume-phase` token list vs `scripts/ship-pr.sh`:** The explicit list in NEVER #16 (`force-push-gate`, `bump`, `pr-create`, `ci-initial`, `ci-merge`, `evaluate-failure`, `postmerge`) matches the `case "$RESUME_PHASE"` arms in `scripts/ship-pr.sh:1674-1680` (with `force-push-gate|bump` correctly represented as two accepted spellings that both enter the bump resume arm).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] **`skills/implement/references/rebase-rebump-subprocedure.md`:** This file does not maintain a parallel `--resume-phase` token roster (grep shows no `--resume-phase` usage); NEVER #16 points to it for long-blocking / `ci-wait.sh` guidance, not for resume-token authority, so there is no cross-doc token mismatch to flag—only a pre-existing discoverability gap if someone expects resume tokens to be documented there.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **`skills/implement/references/rebase-rebump-subprocedure.md`:** This file does not maintain a parallel `--resume-phase` token roster (grep shows no `--resume-phase` usage); NEVER #16 points to it for long-blocking / `ci-wait.sh` guidance, not for resume-token authority, so there is no cross-doc token mismatch to flag—only a pre-existing discoverability gap if someone expects resume tokens to be documented there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:9-24
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] NEVER rule numbering skips 10 (9 then 11). No impact on the ship-pr foreground feature; purely pre-existing doc structure. Leave as-is unless the project wants a editorial renumber pass unrelated to this PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:52-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] NEVER list skips number 10 (9 then 11). Pre-existing doc numbering quirk; not introduced by NEVER #16. Optional renumber or placeholder NEVER #10 in a separate editorial pass if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=rejected

