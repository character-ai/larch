### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1246-1256
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Other postmerge transitions (e.g. REPO_UNAVAILABLE, merge-skips) do not clear stall/bail keys. Rare combination of prior stall keys with these paths could still leave stale state for postmerge; unchanged by this branch. Consider a separate change if that scenario is realistic.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:1246-1256
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Skip-merge paths call advance_phase postmerge without clearing BAIL_REASON/STALL_TRACKING/STALL_STEP. Operator resumes ci-merge after a prior ci-merge stall; configuration forces early postmerge (e.g. MERGE=false or FORKED_TARGET=true). Stale bail/stall keys remain and can still flow into finalize artifacts and downstream bail checks like the bug fixed on merge-success paths. If parity is required, clear those keys on all transitions to postmerge or factor a single helper used by every postmerge entry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

