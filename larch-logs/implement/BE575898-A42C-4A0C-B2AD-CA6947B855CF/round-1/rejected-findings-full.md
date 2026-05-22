### [rejected] FINDING_4

### FINDING_4: Self-test fixture comments overstate “every positive marker” vs actual fixture prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Comments in [`scripts/test-quick-mode-docs-sync.sh`](scripts/test-quick-mode-docs-sync.sh) (around lines 293–304) claim the bad file contains every positive marker while fixtures still include retired unified / hard-review phrases that are not in `POS_MARKERS`, which can mislead maintainers even though CI self-tests still pass.
- **Suggested revision**: Update comments to state that fixtures must include all `POS_MARKERS` strings plus exactly one stale phrase, and that additional legacy prose is optional or explicitly non-authoritative.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

