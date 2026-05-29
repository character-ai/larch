### FINDING_16: [OUT_OF_SCOPE] risk-integration: skills/design/references/approval-gates.md:89-91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Passive-summary Gate B path does not reference Step 3.6; unclear if assessor should run there. If required by product, converged/cap-hit HARD runs could skip quality gate with no test. Clarify intent; if in scope, update docs/SKILL and add integration test.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No direct publish test for top-level assessor verdict/snapshot files. Harvester regression might only surface in multi-round integration or E2E. Optional focused test-design-log-publish cases for assessor artifacts at tmpdir root.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_35: [OUT_OF_SCOPE] The plan calls for a Bash 3.2 portability spot-check in `skills/design/scripts/test-snapshot-plan-round.sh`, but that harness only runs `bash -n`; none of the five new assessor harnesses (`test-tally-plan-assessor.sh`, etc.) have a dedicated bash32 target like `test-render-final-summary-bash32` / `test-collect-agent-bash32`, so the `[@]:-` hazard above would not be caught on Linux CI (bash 5.x) alone.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - The plan calls for a Bash 3.2 portability spot-check in `skills/design/scripts/test-snapshot-plan-round.sh`, but that harness only runs `bash -n`; none of the five new assessor harnesses (`test-tally-plan-assessor.sh`, etc.) have a dedicated bash32 target like `test-render-final-summary-bash32` / `test-collect-agent-bash32`, so the `[@]:-` hazard above would not be caught on Linux CI (bash 5.x) alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


