### FINDING_12: [OUT_OF_SCOPE] pr-prep disposition gate omits strict filed-URL input
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: latent
- **Concern**: The internal pr-prep disposition gate omits `--filed-urls-strict-file` used by the checkpoint/Python paths, so rare all-empty accepted-OOS cases may count filed URL evidence differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


