### [rejected] FINDING_12

### FINDING_12: correctness: skills/design/scripts/tally-plan-review.md:19
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Quorum bullet uses phrase not the per-finding non-JUDGE_ERROR response count. Readers may misunderstand whether tier/quorum is derived from per-finding vote tallies vs panel eligible count; weakens the contract doc introduced in this branch. Rewrite to explicitly restate panel-level eligible basis without ambiguous non-JUDGE_ERROR phrasing; keep JUDGE_ERROR does not reduce tier as a separate clear sentence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_13

### FINDING_13: risk-integration: Branch commits 924f1395 80baaf78 ffba6966 vs main
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unrelated #2381 vocabulary sweep and larch-logs flush ride with #2373 scout sidecar work in one diff range. Revert/bisect/cherry-pick for one concern affects unrelated tally and committed run-log surfaces. Split merges or use a stacked branch/PR sequence per issue.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_14

### FINDING_14: risk-integration: branch vs main (merge-base 7ee70f61; commits ffba6966 80baaf78 924f1395)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Multiple independent change themes ship in one branch diff (scout raw logging, tally rename, larch-logs flush). CI or local failures become harder to attribute and revert surgically; bisect points to a large commit set. Split PRs by concern or document/execute a full combined test matrix before merge.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

