### FINDING_20: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh:337-378
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] render-cache lacks the symlink sweep added for plan-review. Symlinked intermediate dirs under render-cache may still hide files from enumeration without failing publish. Mirror plan-review find -type l sweep for render-cache.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_28: [OUT_OF_SCOPE] architecture: scripts/lib-voter-parse-rate.sh:87+
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate does not require forensic axes Judges omit axes pass retry and produce all-uncertain TSV rows Extend check_voter_parse_rate when axis coverage is mandatory
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_29: [OUT_OF_SCOPE] code-quality: scripts/test-render-voter-prompt.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Render voter prompt regression only partially covers new contract Prompt drift on Output ONLY vote lines or finding-only delimiter prose may slip Add remaining plan-listed grep assertions
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_38: [OUT_OF_SCOPE] correctness: skills/design/scripts/tally-plan-review.sh:2064-2066
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Argv validation exits use code 2 not plan exit 1. Callers checking exact exit 1 would mis-handle errors. Align exit codes with plan or document exit 2 in tally-plan-review.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_39: [OUT_OF_SCOPE] architecture: scripts/test-render-voter-prompt.md:1442
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness doc shard reference may be stale relative to Makefile. Readers may look at wrong test-harnesses-N shard list. Keep test-render doc aligned with Makefile shard assignment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


