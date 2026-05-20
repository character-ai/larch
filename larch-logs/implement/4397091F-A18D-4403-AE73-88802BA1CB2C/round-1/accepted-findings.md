### FINDING_1: **Important** `architecture` `skills/review-and-fix/scripts/review-and-fix.sh:1101-1110`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `architecture` `skills/review-and-fix/scripts/review-and-fix.sh:1101-1110`      The new `/implement` `review-scout-manifest.json` payload omits `yield_tsv_basename`, even though the shared batch schema requires it (`scripts/larch-log-batches.md:56-68`) and the `/review` path writes it (`skills/review/SKILL.md:59-78`). Concrete scenario: when `review-core.sh` emits `YIELD_TSV_FILE=/.../scout-archetype-yield.tsv`, standalone `/review` logs the basename, but `/implement` drops it, so committed implement logs cannot audit per-archetype yield data for the same batch contract. Fix by reading `YIELD_TSV_FILE` from `core_out`, basenaming it, adding `--arg yield_tsv_basename`, and asserting it in `test-review-and-fix.sh`.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1096-1130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implement-path review-scout-manifest JSON omits yield_tsv_basename despite review-core emitting YIELD_TSV_FILE and SKILL/schema expecting basename-only yield linkage. Committed implement run-logs cannot correlate scout batches to scout-archetype-yield.tsv the same way /review logs do; contradicts SECURITY.md basename contract for review-scout-manifest. Read YIELD_TSV_FILE from core_out; basename when file exists; extend jq payload and tests per skills/review/SKILL.md:59-79.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: scripts/test-larch-log.sh:421-479
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned regression test 4 (clean fixture, baseline file set unchanged without scout artifacts) is not implemented as specified; only findings.md is asserted inside a combined fixture. A scout-only regression in write-round behavior for classic-only rounds could ship undetected because the no-scout path is never exercised in the new section. Add a dedicated minimal source-dir fixture without scout/dynamic files, run write-round, and assert the expected baseline artifacts (and absence of unintended files) per the plan.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1096-1129
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Implement-path review-scout-manifest JSON omits yield_tsv_basename though schema and /review wrapper include it and review-core emits YIELD_TSV_FILE. A scout run with a real yield TSV leaves no basename reference in implement/<RUN_ID>/review-scout-manifest.json; audit/compare tooling expecting the documented four-key object loses the yield link. Read YIELD_TSV_FILE from core_out; set yield_tsv_basename like skills/review/SKILL.md:66-78; extend test 6 accordingly.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1106-1128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq failure is swallowed (|| true) and empty payload skips larch-log write without append_log_write_failure. SCOUT_STATUS != na but malformed DYNAMIC_SLOTS yields no review-scout-manifest.json and no execution-issues warning—silent loss of auditable scout flush. Log jq failure to execution-issues or validate numeric DYNAMIC_SLOTS before jq.
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


### FINDING_3: architecture: scripts/larch-log.sh:119-125
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Flattening root and dynamic-archetypes/ by basename can silently overwrite on basename collision. Same basename in round root and dynamic-archetypes/ yields one arbitrary winner in round-N. Detect duplicates and fail closed or disambiguate names.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Documents a three-field scout payload that does not match scripts/larch-log-batches.md schema (four fields). Doc drift until yield field is implemented. Update after aligning implement flush with canonical schema.
- **Suggested revision**: Address the concern above.


