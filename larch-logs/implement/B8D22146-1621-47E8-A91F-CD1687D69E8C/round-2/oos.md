### FINDING_28: risk-integration: skills/review/scripts/tally-code-votes.md:37-69
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] tally-code-votes.md still defines VOTER_COUNT as voter file count and describes quorum as ELIGIBLE file count without parse-rate exceptions. Consumers of the doc or of VOTER_COUNT alone believe the panel is still a 3-file quorum while classify_result uses EFFECTIVE_VOTERS; acceptance tier and NEUT semantics diverge from documentation. Update markdown: document VOTER_COUNT vs ELIGIBLE_VOTER_COUNT; revise threshold section for parse-rate-degraded quorum.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_29: risk-integration: skills/review/scripts/tally-code-votes.md:58-69
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Documentation still describes VOTER_COUNT as raw voter file count and quorum based only on eligible files; code uses EFFECTIVE_VOTERS for classify_result and banners and emits ELIGIBLE_VOTER_COUNT. Operator follows docs and misconfigures automation or misreads quorum vs parse-rate degradation. Update tally-code-votes.md table and Threshold section for effective vs eligible and new key.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_3: **Nit** (`risk-integration`) — `skills/review/scripts/tally-code-votes.md:58`: the stdout contract still says `VOTER_COUNT` is the raw voter-file count, but the code now emits effective voter count and adds undocumented `ELIGIBLE_VOTER_COUNT`. Update the docs so downstream consumers know which count is raw vs degraded.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** (`risk-integration`) — `skills/review/scripts/tally-code-votes.md:58`: the stdout contract still says `VOTER_COUNT` is the raw voter-file count, but the code now emits effective voter count and adds undocumented `ELIGIBLE_VOTER_COUNT`. Update the docs so downstream consumers know which count is raw vs degraded.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_31: risk-integration: skills/review/scripts/tally-code-votes.md:58-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] tally-code-votes.md still documents VOTER_COUNT as raw voter file count and describes quorum without parse-rate effective voters. Readers apply wrong acceptance rules after parse-rate degradation. Update stdout table (ELIGIBLE_VOTER_COUNT + VOTER_COUNT semantics) and threshold narrative for EFFECTIVE_VOTERS / parse-rate diag.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_35: risk-integration: skills/review/scripts/test-tally-code-votes.md; skills/review/scripts/tally-code-votes.md:77
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness docs not updated for new tally test cases. Future contributors miss documented coverage expectations. Extend harness documentation bullets.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 NEUTRAL=0 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] architecture: larch-logs/implement/B8D22146-1621-47E8-A91F-CD1687D69E8C/*
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Committed implement session metadata under larch-logs. Intentional per repo run-log policy. No action.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/dispatch-with-waterfall.sh:163-167
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Waterfall Claude prompt launches omit --role voter. File unchanged by this branch; ROLE may be inert for prompt-file path. Consider --role voter for clarity if subprocess ever keys off role.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] code-quality: larch-logs/implement/B8D22146-1621-47E8-A91F-CD1687D69E8C/manifest.json:16
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Implement run manifest status remains in-progress in committed log. Minor metadata inconsistency in shipped run log only. Accept as run-log policy or refresh manifest when flushing logs if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/B8D22146-1621-47E8-A91F-CD1687D69E8C/
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Committed implement run metadata ships with the branch. Intentional per repo run-log policy; not a functional regression in voter/tally logic. N/A (policy-driven).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] security: scripts/dispatch-code-voters.sh:52-53,71-72
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] User-controlled ballot path is embedded in voter prompts and concatenated into retry prompts; same class of trust as before the change. Pre-existing prompt injection / path-leak surface relative to caller-supplied --ballot-file. No change required for this branch scope; harden separately if threat model demands.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

