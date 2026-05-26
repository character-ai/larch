### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: architecture: skills/implement/SKILL.md:412-426,579-594
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Bail routing case block is comment-only; later Bash blocks are not shell-gated. Orchestrator executing all fenced blocks may ledger-mark and continue Step 0 after adopted-issue-closed bail. Wrap post-bootstrap Step 0 bash in a shell case guard on IMPLEMENT_BAIL_REASON and STALL_TRACKING.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: scripts/implement-bootstrap.sh:392-404
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork tracking skips hard-fail on upstream context fetch failure. /implement --forked can continue after gh/jq failure with no upstream title/body files while plan preflight already ran; agent may implement against incomplete fork context. Restore fail-closed on get-issue-context failure or set a bail when upstream context files are missing after fork skip.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: security: scripts/implement-bootstrap.sh:407-433
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] rm -f on parent-issue.md is symlink-unsafe under tmpdir swap attacks. Writer in shared or compromised tmpdir can cause rm -f to delete arbitrary user-writable paths. Verify regular file under IMPLEMENT_TMPDIR before rm or use hardened sentinel creation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: risk-integration: scripts/implement-bootstrap.sh:392-402
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork mode does not require --upstream-repo at bootstrap argv layer. Orchestrator misconfiguration skips get-issue-context silently while fork flow continues. die_usage or bail when FORKED_TARGET=true and UPSTREAM_REPO_OPT is empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: risk-integration: skills/implement/SKILL.md:412-426
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Routing guard case is comment-only Agent may run tracking/plan bash after adopted-issue-closed bail Emit and gate on a machine SKIP flag from bootstrap KV
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: risk-integration: scripts/implement-bootstrap.sh:462-488
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] DEFERRED path keeps BRANCH_SELECTED=branch-2-adopt and ISSUE_NUMBER set Parser treats adopt complete despite missing sentinel and DEFERRED=true Use branch-2-deferred token or adjust ISSUE_NUMBER tail when deferred without sentinel
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: architecture: skills/implement/SKILL.md:412-417
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] tracking-init-failed shares routing case arm with non-stall bails Future edit to STALL_TRACKING default could affect wrong bail class Split case arms per bail reason
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_38: **correctness** `skills/implement/scripts/test-implement-bootstrap.sh:238-242,475-478` — The `post-tracking-issue.sh` stub’s failure mode (`exit 1` plus `POSTED=false` on stdout) aligns with `phase_tracking`’s `if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]` branch (`scripts/implement-bootstrap.sh:482-488`): command substitution still captures stdout on non-zero exit, so B4 correctly exercises DECISION_1 deferred behavior rather than `tracking-init-failed`. No change required for that pairing; the gap above is missing negative setup, not stub/production divergence on exit code.
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-implement-bootstrap.sh:238-242,475-478` — The `post-tracking-issue.sh` stub’s failure mode (`exit 1` plus `POSTED=false` on stdout) aligns with `phase_tracking`’s `if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]` branch (`scripts/implement-bootstrap.sh:482-488`): command substitution still captures stdout on non-zero exit, so B4 correctly exercises DECISION_1 deferred behavior rather than `tracking-init-failed`. No change required for that pairing; the gap above is missing negative setup, not stub/production divergence on exit code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: architecture: skills/implement/SKILL.md:412-427
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Mandatory routing guard is comment-only case. Agents can run tracking ledger and later Step 0 blocks after bail. Add enforceable skip/exit or mirror plan-materialization skip guards before tracking block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

