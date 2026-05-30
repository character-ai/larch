### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/relevant-checks.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Hook and AGENTS.md edits not mapped to harness in local relevant-checks Local edits may skip harness until full make lint Pre-existing; optional mapping for hook-anti-read-poll and AGENTS.md paths
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] correctness: scripts/hook-anti-read-poll.sh:52-65
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Bash classifier may match quoted cat plus tasks path without real read echo cat tasks/foo.output twice could warn incorrectly Warn-only; acceptable per plan exotic-form scope
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: **Injection / prompt reflection:** Reminders are built from fixed templates plus numeric `count`/`age`; paths and command bodies are not echoed into `additionalContext`, consistent with the existing `SECURITY.md` “Read-poll reminder output” note (`SECURITY.md:123`). `emit_reminder` uses `jq --arg`, which is appropriate for embedding text in JSON.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Injection / prompt reflection:** Reminders are built from fixed templates plus numeric `count`/`age`; paths and command bodies are not echoed into `additionalContext`, consistent with the existing `SECURITY.md` “Read-poll reminder output” note (`SECURITY.md:123`). `emit_reminder` uses `jq --arg`, which is appropriate for embedding text in JSON.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/hook-anti-read-poll.sh:113,152` — State files are still written with `printf … > "$taskout_file"` / `> "$state_file"` without verifying the target is a regular file (no `O_NOFOLLOW` / non-symlink check). A same-UID attacker who can plant a symlink under `${TMPDIR}/larch-read-poll/` before the hook runs could redirect writes; this pattern predates #3195 and is only slightly more exercised now because Bash PostToolUse triggers more updates. **Suggested fix:** (if hardening is ever desired) open state files with a symlink-safe write helper, matching patterns used elsewhere in the repo (e.g. stall-recovery’s non-symlink path checks in `SECURITY.md:56`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] architecture: scripts/test-hook-anti-read-poll.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness checks mode 600 only on generic state file not state-taskout. New task-output state files might regress permissions unnoticed. Add find -perm 600 assertion for state-taskout files in harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_37: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** (plan-accepted) `scripts/hook-anti-read-poll.sh:52-60` — Polling via `awk`, `python -c`, process substitution, or `sed` without `-n` is still invisible to `bash_has_read_verb`; the plan explicitly treats that as acceptable for a warn-only hook.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **code-quality** `scripts/hook-anti-read-poll.sh:43-50` — `is_read_task_output_path` is end-anchored on `file_path` while `bash_has_task_output` is intentionally substring-based; suffix-appended incident commands (`2>/dev/null`, `| head`) are covered for Bash. No wrapped-grep violation in this script context.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/hook-anti-read-poll.sh:52-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Bash branch omits grep awk python and non-verb reads on task output Those poll shapes still bypass the hook entirely Accept for warn-only scope or extend verb/path detection later
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] architecture: hooks/hooks.json:37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Hook runs on every Bash PostToolUse with early exit for non-matches Extra jq/grep work per Bash call; not a functional regression Acceptable tradeoff unless perf becomes an issue
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

