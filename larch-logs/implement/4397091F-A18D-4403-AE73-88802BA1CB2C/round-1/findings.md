### FINDING_1: **Important** `architecture` `skills/review-and-fix/scripts/review-and-fix.sh:1101-1110`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `architecture` `skills/review-and-fix/scripts/review-and-fix.sh:1101-1110`      The new `/implement` `review-scout-manifest.json` payload omits `yield_tsv_basename`, even though the shared batch schema requires it (`scripts/larch-log-batches.md:56-68`) and the `/review` path writes it (`skills/review/SKILL.md:59-78`). Concrete scenario: when `review-core.sh` emits `YIELD_TSV_FILE=/.../scout-archetype-yield.tsv`, standalone `/review` logs the basename, but `/implement` drops it, so committed implement logs cannot audit per-archetype yield data for the same batch contract. Fix by reading `YIELD_TSV_FILE` from `core_out`, basenaming it, adding `--arg yield_tsv_basename`, and asserting it in `test-review-and-fix.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says non-empty SCOUT_STATUS but code defaults empty to na. Slight prose imprecision vs defaulting; aligns with SKILL.md pattern. Align wording with ${VAR:-na} defaulting in doc if desired.
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: scripts/larch-log.sh:119-125
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Flattening root and dynamic-archetypes/ by basename can silently overwrite on basename collision. Same basename in round root and dynamic-archetypes/ yields one arbitrary winner in round-N. Detect duplicates and fail closed or disambiguate names.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: scripts/larch-log.sh:299-304
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write-round merges two finds sorted by path then flattens by basename; duplicate basenames silently pick last sorted path. Two different reviewer-dyn-X.md files at round root vs dynamic-archetypes with same basename commit wrong content without error. Detect basename collision or define and enforce precedence (e.g. subdirectory wins).
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: skills/review-and-fix/scripts/review-and-fix.sh:1094-1167; skills/review/SKILL.md:57-86
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Implement-path review-scout-manifest flush runs before flush_review_batches (tally / review-findings-full), whereas SKILL.md specifies scout manifest after the tally batch for /review. A consumer that assumes identical inter-batch ordering between standalone /review logs and /implement Step 5 logs could mis-order or mis-interpret batched events. If parity is required, relocate the flush to after tally (or document intentional ordering difference).
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-larch-log.sh:219-245; skills/review-and-fix/scripts/test-review-and-fix.sh:1032-1073
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test pass strings say committed while only filesystem placement under tmp log root is asserted. Operators misread failures as git staging/commit problems. Use wording like written or present under larch-logs.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says non-empty and not na; code does not mention whitespace-only SCOUT_STATUS. Readers assume stronger validation than implemented. Align documentation with guard or tighten guard.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc claims non-empty and not na; implementation maps empty to na. Readers may expect different gating than the shell default. Update prose to match scout_status_val=${scout_status_val:-na} and != na.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Documents a three-field scout payload that does not match scripts/larch-log-batches.md schema (four fields). Doc drift until yield field is implemented. Update after aligning implement flush with canonical schema.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1096-1130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implement-path review-scout-manifest JSON omits yield_tsv_basename despite review-core emitting YIELD_TSV_FILE and SKILL/schema expecting basename-only yield linkage. Committed implement run-logs cannot correlate scout batches to scout-archetype-yield.tsv the same way /review logs do; contradicts SECURITY.md basename contract for review-scout-manifest. Read YIELD_TSV_FILE from core_out; basename when file exists; extend jq payload and tests per skills/review/SKILL.md:59-79.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:1032-1039
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test pass strings say review-scout-manifest.json committed but only file existence under tmp log root is checked. Misleading signal when triaging test failures vs real git commits. Reword assertions to written or present at log root.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-larch-log.sh:194-252
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan asked for a clean no-scout fixture for no-regression; tests use one combined fixture. Regression affecting only no-scout rounds might slip past test 4. Add a minimal second write-round fixture without scout/dynamic files.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-larch-log.sh:421-479
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned regression test 4 (clean fixture, baseline file set unchanged without scout artifacts) is not implemented as specified; only findings.md is asserted inside a combined fixture. A scout-only regression in write-round behavior for classic-only rounds could ship undetected because the no-scout path is never exercised in the new section. Add a dedicated minimal source-dir fixture without scout/dynamic files, run write-round, and assert the expected baseline artifacts (and absence of unintended files) per the plan.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1096-1129
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Implement-path review-scout-manifest JSON omits yield_tsv_basename though schema and /review wrapper include it and review-core emits YIELD_TSV_FILE. A scout run with a real yield TSV leaves no basename reference in implement/<RUN_ID>/review-scout-manifest.json; audit/compare tooling expecting the documented four-key object loses the yield link. Read YIELD_TSV_FILE from core_out; set yield_tsv_basename like skills/review/SKILL.md:66-78; extend test 6 accordingly.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1098-1100
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] SCOUT_STATUS check is case-sensitive for na only. Emitters using NA would trigger a scout manifest flush contrary to na semantics. Normalize SCOUT_STATUS before comparison or document case-sensitive contract.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1098-1101
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] SCOUT_STATUS guard is only != na after :-na default; does not trim. Malformed SCOUT_STATUS value that is only whitespace still flushes a misleading status string. Trim/normalize empty-after-trim to na or add explicit -n check on the final value.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1106-1128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq failure is swallowed (|| true) and empty payload skips larch-log write without append_log_write_failure. SCOUT_STATUS != na but malformed DYNAMIC_SLOTS yields no review-scout-manifest.json and no execution-issues warning—silent loss of auditable scout flush. Log jq failure to execution-issues or validate numeric DYNAMIC_SLOTS before jq.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1115-1120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Replace-mode review-scout-manifest at run root overwrites prior rounds. Multi-round run: only latest round summary in flat batch; earlier round summaries lost at run root (round-N dirs may still hold per-round scout files). Document latest-only semantics or add round-scoped batch if flat history is required.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1096-1128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Implement flush omits yield_tsv_basename from review-scout-manifest JSON despite canonical schema and YIELD_TSV_FILE from review-core.env. Implement run logs lack yield basename audit parity with /review and documented four-field batch shape when tally emits YIELD_TSV_FILE. Mirror SKILL.md: read YIELD_TSV_FILE via kv_get; add yield_tsv_basename to jq payload and update review-and-fix.md.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1106-1111
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] jq --argjson on DYNAMIC_SLOTS is combined with || true; invalid non-JSON values make jq fail and skip writing review-scout-manifest. SCOUT_STATUS is non-na but audit batch is missing with no hard failure; auditable trail gaps under malformed or adversarial KV output. Constrain DYNAMIC_SLOTS to an integer (regex) and build JSON without swallowing jq errors or log append_log_write_failure on jq failure.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1106-1112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq payload build uses || true; invalid DYNAMIC_SLOTS yields no flush and no execution-issues entry while SCOUT_STATUS != na. Non-integer or corrupted DYNAMIC_SLOTS makes jq fail; scout summary batch silently absent from larch-logs. Validate DYNAMIC_SLOTS as integer before jq or handle jq failure with append_log_write_failure or emit_breadcrumb.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1106-1129
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] jq failure is masked by || true; empty payload skips flush without logging. Non-numeric DYNAMIC_SLOTS makes jq fail; SCOUT_STATUS != na but no batch and no execution-issues warning. Log append_log_write_failure or emit_breadcrumb on jq failure; avoid || true without handling.
- **Suggested revision**: Address the concern above.

### FINDING_23: security: scripts/larch-log.sh:301-303
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] write-round traverses dynamic-archetypes with find after only a directory test; subdirectory may be a symlink so find can list files outside SOURCE_DIR. Matching basenames under the symlink target can be staged and committed into round-N larch-logs without placing them directly under the round source dir. Reject symlinked dynamic-archetypes (e.g. [ ! -L ... ]) or resolve/list only under a physical path bounded by SOURCE_DIR.
- **Suggested revision**: Address the concern above.

