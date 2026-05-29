### FINDING_8: [OUT_OF_SCOPE] `cancelled-reentry-guard` missing from render-final-summary allowlist
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Pre-existing: `SKILL.md` emits `cancelled-reentry-guard` but `skills/design/scripts/render-final-summary.sh` (and related enums/docs) do not allow it. Re-entry guard runs the Final summary block, then the renderer rejects the unknown outcome and exits 2 instead of rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


