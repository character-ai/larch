### FINDING_3: [OUT_OF_SCOPE] **Latent** `correctness` `scripts/git-force-push.sh:65-90` — The pre-existing force-push helper has the same lease-refresh retry shape: after a failed force-with-lease it fetches the branch, then retries with the refreshed default lease. This predates the current PR, but the same concrete overwrite path applies if another writer advanced the remote branch between the local lease snapshot and the retry. Use an explicit expected remote OID across retries or fail when refreshed remote differs from local `HEAD`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Latent** `correctness` `scripts/git-force-push.sh:65-90` — The pre-existing force-push helper has the same lease-refresh retry shape: after a failed force-with-lease it fetches the branch, then retries with the refreshed default lease. This predates the current PR, but the same concrete overwrite path applies if another writer advanced the remote branch between the local lease snapshot and the retry. Use an explicit expected remote OID across retries or fail when refreshed remote differs from local `HEAD`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh (misc exit_stall sites)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Many historical bare numeric stall codes predate this change. Not introduced here; full stall vocabulary cleanup would be a separate project. Defer unless standardizing all exit_stall tokens is explicitly in scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:188-199
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Missing or corrupted REBASE_COUNT in a hand-edited state file can make shell numeric tests error. Not introduced solely by this diff; same empty-key hazard exists for other arithmetic on read_state. Keep state file integrity guarantees; treat as operational hygiene.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Operator-facing SKILL examples for STALL_STEP do not list the new hyphenated stall tokens. Confusion when comparing live STALL_STEP values to SKILL prose; file not part of this feature diff. Follow-up documentation outside this PR if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 NEUTRAL=0 Result=exonerated

