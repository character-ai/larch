### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/test-dispatch-code-voters.sh:223-221
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate retry tests always run even when --section selects a subset. Using --section does not limit wall-clock to the named scenarios; pre-existing structure. Document in harness header or nest retries inside sections if that is the desired contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

