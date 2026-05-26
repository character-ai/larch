# Review Round 1

- Mode: `diff`
- 12 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: correctness: skills/review/scripts/tally-code-votes.sh:70-74
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Flat findings-classification.tsv is selected whenever SESSION_ENV_PATH is set, not only for /implement round-isolated tmpdirs. Standalone /review --diff with --session-env runs multiple rounds in one REVIEW_TMPDIR; each round overwrites the same flat TSV while Step 4 publishes review-findings-classification-round-N slugs with stale/wrong payload. Key off implement nesting (REVIEW_TMPDIR under IMPLEMENT_TMPDIR/round-*) or an explicit flag; do not use SESSION_ENV_PATH alone.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/review/scripts/test-tally-code-votes.sh:325-337
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] JUDGE_ERROR case lacks classification TSV assertions. vN_vote empty vs JUDGE_ERROR semantics could drift from tally scoreboard. Add rated/JUDGE_ERROR fixtures and assert classification columns and FINDINGS_CLASSIFICATION_TSV_FILE.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: Makefile:412-417
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Review findings-classification harness runs in both shard 8 and shard 9. Full make lint doubles runtime for that script without extra coverage. Register the review harness in only one shard/target.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/review/scripts/test-tally-code-votes.sh:42-45
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No OOS_N ballot-id unit case in tally harness. OOS_1_* tally env key prefix change lacks regression in main tally suite. Add OOS_N ballot block case with OOS_1_OUTCOME and classification row checks.
- **Suggested revision**: Address the concern above.


### FINDING_15: security: skills/review/scripts/test-findings-classification.sh:1-146
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] No fixture asserts enum-only TSV cells under adversarial voter input. A future refactor could reintroduce raw voter substrings into committed TSV without CI catching it. Add a fixture with malicious voter tokens and assert all cells match allowed enums.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/review/SKILL.md:61-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 4 runs after the multi-round loop but only binds the last round's FINDINGS_CLASSIFICATION_TSV_FILE, so earlier per-round TSVs are not published to larch-logs. A 3-round /review --diff run writes findings-classification-round-1/2/3.tsv in tmpdir but Step 4 log-phase only commits round 3 (or none) under larch-logs/review/RUN_ID/. Log classification inside the Step 3 per-round loop or at Step 4 iterate r=1..round_num with explicit payload paths per round; update heavy-worker parent binding the same way.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: larch-logs/implement/C9050C89-2197-45B9-AE3E-D30BDA147780/round-1/
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Flushed implement Step 5 round lacks findings-classification.tsv despite rated voter outputs and completed tally. Acceptance requires the forensic TSV under larch-logs/implement/<RUN_ID>/round-<N>/; this branch's chore flush does not include it anywhere under larch-logs/implement/, so downstream consumers cannot rely on committed run logs for the new artifact. Re-run a minimal implement review round post-c8599546; verify the TSV exists in round tmpdir before write-round; re-flush or fix write-round staging if the file is present locally but omitted from logs.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/review/scripts/tally-code-votes.sh:70-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Ambient IMPLEMENT_TMPDIR selects implement TSV basename for standalone /review. Standalone multi-round review with IMPLEMENT_TMPDIR still exported overwrites findings-classification.tsv each round and publishes under wrong batch slug. Key path selection off --session-env-path only; clear IMPLEMENT_TMPDIR in standalone wrapper or add explicit --classification-path-mode.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/review/scripts/review-core.sh:439-449
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Zero-findings tally omits --session-env-path. /implement zero-finding round may write findings-classification-round-N.tsv that write-round does not publish. Pass --session-env-path in zero_tally_args same as main tally path.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/shared/voting-protocol.md:240
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] OOS-on-ballot section contradicts updated vote-line rules. Voters/operators follow stale doc and omit OOS_N vote lines on OOS_N headings. Align section 240 with finding-oos grammar and tally-code-votes.sh.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/review/scripts/tally-code-votes.md:13-14,34
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sibling doc stale on OOS_N headings and review-tally.env keys. Downstream consumers misread env/artifact contract. Update tally-code-votes.md to match implementation.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/review/scripts/tally-code-votes.sh:139-224
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No review-side malicious/invalid-axis sanitization test (design harness has one). Non-enum or tabbed axis tokens could land in committed TSV files. Port design stub-parser sanitization case to review test-findings-classification or test-tally-code-votes.
- **Suggested revision**: Address the concern above.


