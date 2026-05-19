# Review Round 2

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 13
- Exonerated findings: 3
- Neutral findings: 4

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:904`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:904`      The new scout batch flush at `skills/review-and-fix/scripts/review-and-fix.sh:1096-1140` is unreachable when `review-core.sh` exits nonzero, because the wrapper invokes it under `set -e` without capturing the status. Concrete scenario: `review-core.sh` emits `SCOUT_STATUS=ok` and then exits `2` for `REVIEW_CORE_STATUS=panel-failed` at `skills/review/scripts/review-core.sh:386-400`; `review-and-fix.sh` exits immediately at line 904, so no `review-scout-manifest.json` is written despite the feature requiring a flush after each `review-core.sh` invocation when scout status is not `na`. Wrap the `review-core.sh` call in `set +e`, capture `core_rc`, parse `core_out`, perform the scout/round log flush, then propagate the mapped failure status.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-larch-log.sh:241-292
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test pass messages say write-round commits scout files; write-round only stages under LARCH_LOG_ROOT without git commit in these tests. Misleading signal when triaging failures (looks like a commit-path bug). Rename pass/fail strings to staged/copied/present under round directory.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1104-1123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Stale round_dir/.scout-payload.json can satisfy -s after DYNAMIC_SLOTS validation fails without running jq, so larch-log write may flush an old JSON payload. Resume or repeat scout flush in the same round_dir after a partial write: invalid DYNAMIC_SLOTS skips jq but a leftover non-empty .scout-payload.json triggers review-scout-manifest write with wrong metadata in committed logs. rm -f the payload path before validation/jq (or write jq output to a fresh mktemp) so -s cannot observe stale files.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1108-1109
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Basename fields for review-scout-manifest require source files to exist (-f), unlike SKILL.md /review mirror which basenames from KV when non-empty. If SCOUT_MANIFEST or YIELD_TSV_FILE points to a path that is not a regular file at flush time, basenames are empty in the batch while /review would still record basenames; audit parity breaks. Match skills/review/SKILL.md:67-68: basename whenever KV is non-empty; drop or narrow the -f gate unless another invariant requires it.
- **Suggested revision**: Address the concern above.


