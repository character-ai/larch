### FINDING_1: **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:904`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:904`      The new scout batch flush at `skills/review-and-fix/scripts/review-and-fix.sh:1096-1140` is unreachable when `review-core.sh` exits nonzero, because the wrapper invokes it under `set -e` without capturing the status. Concrete scenario: `review-core.sh` emits `SCOUT_STATUS=ok` and then exits `2` for `REVIEW_CORE_STATUS=panel-failed` at `skills/review/scripts/review-core.sh:386-400`; `review-and-fix.sh` exits immediately at line 904, so no `review-scout-manifest.json` is written despite the feature requiring a flush after each `review-core.sh` invocation when scout status is not `na`. Wrap the `review-core.sh` call in `set +e`, capture `core_rc`, parse `core_out`, perform the scout/round log flush, then propagate the mapped failure status.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/larch-log.sh:92
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Broad output filename globs on the round allow-list pre-exist. Unrelated files matching output globs could already be staged in principle. Pre-existing pattern; scout change only adds additional explicit globs.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-and-fix.sh:71-74
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] kv_get parsing is naive for complex values. Malformed KEY=value lines could mis-parse values for any consumer of kv_get. Not introduced by this diff; broader refactor if desired.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: scripts/lib-larch-log.sh:larch_log_fail
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New tests grep stdout for errors because larch_log_fail echoes to stdout Pre-existing contract; not introduced by this diff None required for this branch
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:742-761
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] append_log_write_failure ignores helper failure via true Append helper errors can drop all flush diagnostics including scout Not introduced by this diff
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/larch-log.sh:289-313
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Duplicate basename failure mid write-round loop leaves partial round_dir After copying some artifacts duplicate basename aborts leaving earlier files without the conflicting pair Fail closed only after pre-scan or clear round_dir on this error
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/review-and-fix/scripts/review-and-fix.sh:1123-1139 scripts/lib-larch-log.sh:56-62
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Run-root review-scout-manifest.json is replace-mode without round suffix Multi-round Step 5 overwrites prior scout summary at implement run root Document or version batch per round
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: skills/review-and-fix/scripts/test-review-and-fix.sh; scripts/test-larch-log.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test count exceeds plan items 1-7 (extra test 8 and extra write-round scenarios). None unless release notes or issue #2356 must match exact test enumeration. Update issue text or accept as follow-on hardening.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/larch-log.sh:261-285
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate initialization of written/found (and related zeroing) in write-round. Minor readability churn only; no functional impact in normal runs. Keep a single initialization block before mktemp/trap.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/larch-log.sh:262-285
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Redundant written=false and found=false assignments in write-round. No functional bug; adds noise when reading the control flow. Remove the duplicate assignments after option parsing.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-larch-log.sh:241-292
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test pass messages say write-round commits scout files; write-round only stages under LARCH_LOG_ROOT without git commit in these tests. Misleading signal when triaging failures (looks like a commit-path bug). Rename pass/fail strings to staged/copied/present under round directory.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-larch-log.sh; skills/review-and-fix/scripts/test-review-and-fix.sh (scout sections)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra regression cases (duplicate basename symlink dynamic-archetypes test 8 invalid slots) beyond issue tests 1-7. Only tracking/traceability noise for reviewers expecting exactly seven tests. Update companion .md contracts or issue text to acknowledge the added cases.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says non-empty and not na but code defaults empty to na Wording implies empty skips flush differently than implemented Align prose with normalization and comparison
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc says non-empty and not na but code only implements != na after empty default. Documents a stricter contract than the shell implements (whitespace-only still flushes). Update doc or implement explicit non-empty trim check.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc claims non-empty SCOUT_STATUS guard; implementation treats empty like na via parameter expansion. Doc/implementation mismatch for edge documentation readers. Match SKILL.md wording (SCOUT_STATUS:-na and != na).
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104 area
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc says non-empty and not na while code defaults empty SCOUT_STATUS to na Readers expect different behavior for empty SCOUT_STATUS Align documentation with defaulting rules
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1073-1140
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stale or partial scout_payload could theoretically be flushed after jq failure Rare jq partial write then follow-on write with bad JSON Remove scout_payload before jq or gate write strictly on jq success and validation
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1096
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Flush guard uses -x on LARCH_LOG_SH instead of plan wording (set). If LARCH_LOG_SH is set but not executable, scout manifest flush is silently skipped. Use -n/-f as in plan or document and test the executable requirement explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1098-1100
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Whitespace-only SCOUT_STATUS is not normalized to na so scout-manifest flush still runs. review-core emits SCOUT_STATUS with only spaces; committed review-scout-manifest.json carries meaningless status and bypasses the intended na gate. Trim SCOUT_STATUS or treat whitespace-only as na; align with docs.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1104-1123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Stale round_dir/.scout-payload.json can satisfy -s after DYNAMIC_SLOTS validation fails without running jq, so larch-log write may flush an old JSON payload. Resume or repeat scout flush in the same round_dir after a partial write: invalid DYNAMIC_SLOTS skips jq but a leftover non-empty .scout-payload.json triggers review-scout-manifest write with wrong metadata in committed logs. rm -f the payload path before validation/jq (or write jq output to a fresh mktemp) so -s cannot observe stale files.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1108-1109
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Basename fields for review-scout-manifest require source files to exist (-f), unlike SKILL.md /review mirror which basenames from KV when non-empty. If SCOUT_MANIFEST or YIELD_TSV_FILE points to a path that is not a regular file at flush time, basenames are empty in the batch while /review would still record basenames; audit parity breaks. Match skills/review/SKILL.md:67-68: basename whenever KV is non-empty; drop or narrow the -f gate unless another invariant requires it.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1108-1122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-na SCOUT_STATUS still writes manifest when SCOUT_MANIFEST/YIELD paths are missing If files disappear before flush JSON shows ok with empty manifest_basename yield_tsv_basename losing audit linkage Warn or skip write when expected files absent for ok status
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/review-and-fix/scripts/review-and-fix.sh:71-75 skills/review-and-fix/scripts/review-and-fix.sh:1098-1100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] kv_get values untrimmed SCOUT_STATUS compared literally to na A value like SCOUT_STATUS=na with trailing space bypasses the na guard and triggers an unintended review-scout-manifest write Trim SCOUT_STATUS before defaulting and comparing
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/test-larch-log.sh (new write-round assertions)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test names say scout files are committed but only write-round to a temp log root is exercised Misleading failure triage when a test fails Rename pass/fail strings to reflect files written under round dir not git commit
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-larch-log.sh (plain fixture block)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan test 4 asked for same artifact set as before; test only checks a subset plus negatives An extra unintended file in round output could pass unnoticed Optionally assert full sorted basename allow-list for the fixture
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/test-larch-log.sh (plain write-round fixture block)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Regression test 4 does not assert full round directory equality to a prior baseline. An extra unexpected file could appear in round-1/ and tests might still pass. Compare full sorted file list or directory fingerprint to a frozen expected set.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1096-1100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Scout flush gated on executable LARCH_LOG_SH with no fallback warning If LARCH_LOG_SH is unset or not executable while SCOUT_STATUS is ok the manifest flush is skipped silently with no execution-issues entry Log a warning or relax gate when SCOUT_STATUS!=na after normalization
- **Suggested revision**: Address the concern above.

### FINDING_28: security: skills/review-and-fix/scripts/review-and-fix.sh:1102-1109
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] SCOUT_MANIFEST and YIELD_TSV_FILE paths are not rooted-checked before basename is logged. Malicious review-core could point at existing sensitive paths; basenames can leak into committed audit logs. Canonicalize paths and require they live under IMPLEMENT_TMPDIR or round_dir before recording.
- **Suggested revision**: Address the concern above.

