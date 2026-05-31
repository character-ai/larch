### FINDING_10: [OUT_OF_SCOPE] decompose-panel-dispatch.md ties DEGRADED_PANEL to obsolete COMBINED_FALLBACK_COUNT rule
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Doc still ties `DEGRADED_PANEL` to `COMBINED_FALLBACK_COUNT > floor(8/2)` instead of `STATIC_DISPATCH_OK` and parse-status semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update to STATIC_DISPATCH_OK and parse-status semantics


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] plan-review.md still documents phase-2/phase-3 paths in design paths-file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reference still states Phase 3 Claude outputs appear in paths-file alongside Phase 1/2; `/design` plan-review now uses `--no-fallback` and omits dropped slots. Phase 2/3 apply only to legacy multi-phase callers (e.g. `/review`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword to state that `/design` paths-files list only succeeded phase-1 outputs and that phase-2/phase-3 paths apply only to the legacy multi-phase waterfall (e.g. `/review` code panel).


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] decompose-aggregator still invokes waterfall without --no-fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `decompose-aggregator.sh` can still cross-tool/Claude-pad failed Codex slots per legacy waterfall, unlike decomposition panel `--no-fallback` profile (plan-intentional but different recovery behavior).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


