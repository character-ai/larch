### FINDING_1: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:200-442
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Mangled-row jq output cached to a temp path is only deleted in the category-stats block; early exit 1 after oos-category-mangle skips that block. A custom scans.tsv with oos-category-mangle followed by an unknown scan name hits exit 1 after mktemp; the jq_out temp file is left in TMPDIR (same class of leak if required-file-presence exits after oos when scans order is customized). Use an EXIT trap to rm the cache file whenever set, or clear the cache on every exit path before leaving the scan loop.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: .claude/skills/audit-runs/scripts/audit-scan-run-mangled-rows.jq:8-12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Strict string equality on .phase and .outcome. Non-canonical casing in JSONL rows would be ignored and oos-category-mangle could report pass while prose categories persist. Normalize phase/outcome (e.g. ascii_downcase) or document and enforce the exact string contract at the producer.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: .claude/skills/audit-runs/scripts/audit-compute-counters.sh:107-111
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Missing-jsonl detection uses a grep substring on category-stats detail. If detail wording changes, partial missing-file rows might be misclassified and clean/blank deltas could be summed when they should be skipped (or vice versa). Add a structured partial_reason field or a stable sentinel instead of free-text substring matching.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:952-1218
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test numbering diverges from the written implementation plan (55–60 vs 56–63). Reviewers linking issue checklist to test names may look for the wrong test labels. Align test banner numbering with the plan or document the mapping explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/*
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large committed run-log flush accompanies the feature branch. Not introduced as a logic defect of audit-runs; policy explicitly allows shipped implement logs. No change required for the audit-runs code review scope.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:200-442
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] oos-category-mangle leaves mktemp cache file; unknown-scan exit 1 before category-stats skips cleanup Custom scans.tsv with oos-category-mangle before an unknown scan name: jq succeeds, then exit 1 leaks ${TMPDIR:-/tmp}/audit-scan-oos-out-* each run Add EXIT trap or explicit cleanup on all exit paths before category-stats
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: .claude/skills/audit-runs/scripts/audit-compute-counters.sh:417-429
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] OOS clean/blank skip tied to substring in detail Future change to missing-file detail text could break skip detection and mis-aggregate deltas Use structured flag or stable reason code instead of grep on prose
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: .claude/skills/audit-runs/SKILL.md:211-246
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] version_window_checks YAML template includes # comment example lines Strict YAML consumers may reject pasted frontmatter Move examples out of literal YAML template
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] architecture: larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/plan-goals-test.md:1-210
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Flushed plan still mentions --state open for C.1 while SKILL uses --state all Misleading only as historical log text; no executable impact None required for merge; optional log hygiene only
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: .claude/skills/audit-runs/SKILL.md:248-258
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] YAML example uses bare union tokens with pipe characters inside a fenced yaml block Copy-paste into a real audit-report issue could yield ambiguous or invalid YAML for automated frontmatter consumers Use quoted scalars and/or comments for alternatives instead of inline `a | b` placeholder values in the example block
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: .claude/skills/audit-runs/scripts/audit-compute-counters.sh:102-111
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] OOS clean/blank delta skipping depends on grepping a human-readable detail substring Rewording the missing-jsonl detail string or an unrelated detail containing the same phrase changes whether placeholder partial rows contribute to cumulative counters, corrupting audit deltas without loud failure Add a stable partial_reason code emitted by audit-scan-run.sh and key off that in audit-compute-counters.sh
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:428-462
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Partial category-stats can coexist with silently zeroed canonical/blank/oos_blank counts on corrupt JSONL jq errors are swallowed for non-mangled aggregates; partial_data warns about mangled but numeric fields can look measured when they are not Mark non-mangled counters as unmeasured on jq failure or stop emitting numeric placeholders
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: .claude/skills/audit-runs/scripts/audit-scan-run-mangled-rows.jq:8-12
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Case-sensitive accepted/outcome matching Producer casing drift makes real plan-review accepted prose categories invisible to the scan, yielding false pass Normalize outcome strings or enforce producer contract plus a regression fixture
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: .claude/skills/audit-runs/scripts/audit-scan-run.sh:200-214,402-426
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Temp mangled output can leak and stdout can be truncated on mid-script exit Registry drift exit after oos success leaves temp files and partial NDJSON that downstream may mis-handle Add EXIT trap cleanup and/or a structured incomplete-scan marker before non-zero exit
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: .claude/skills/audit-runs/SKILL.md:248-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] YAML examples include # comment lines Naive copy-paste into strict YAML consumers may break or drop fields Keep examples outside the copyable YAML template or label as illustrative only
- **Suggested revision**: Address the concern above.

### FINDING_16: architecture: .claude/skills/audit-runs/ (plan §Files to modify vs branch)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan listed five touched files; branch also edits audit-compute-counters.{sh,md} and adds audit-scan-run-mangled-rows.jq Checklist-only reviewers may miss coordinated counter and shared-filter updates Call out expanded paths in PR/issue narrative or extend the planning template for coupled scan/category-stats changes
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:~977-1218
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan referenced tests 55-60 after test 54; harness uses 56-63 plus extra inserted tests Weaker 1:1 traceability from written plan test matrix to assertion labels Add a short plan-to-test mapping comment or align issue text with final test IDs
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: .claude/skills/audit-runs/scripts/audit-compute-counters.sh:~417-439
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Clean/blank deltas now skip category-stats only when partial detail mentions missing JSONL; other partial rows contribute Non-canonical handcrafted scan NDJSON with partial_data true and odd detail could change deltas vs old always-skip-partial rule Prefer an explicit omit flag from emitters or document that only audit-scan-run NDJSON shapes are supported inputs
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] architecture: larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/plan-goals-test.md:~1299-1306
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Embedded plan snapshot still says classify with --state open while shipped SKILL uses --state all for C.2 Frozen run-log text can mislead if mistaken for current SOT None for merge; treat as historical unless editing the log for clarity
- **Suggested revision**: Address the concern above.

### FINDING_20: **correctness** `audit-scan-run-mangled-rows.jq:9-13` — The pipeline ends with `) | .id`, so rows that satisfy the plan-review/accepted/non-canonical predicate still contribute a line when `.id` is missing, JSON `null`, or non-string (for example an object), because `jq -r` will still print a line per match (`null`, JSON, etc.) and `audit-scan-run.sh` turns that into a count via `wc -l`, inflating `oos-category-mangle` and `category-stats.mangled` relative to “one accepted finding row” semantics and risking false positives if upstream ever emits accepted rows without a string `id`. **Suggested fix:** Narrow the emitted stream to stable string ids (for example `select(...) | .id | strings` or `select((.id|type)=="string")`) and treat anything else as malformed (skip, `error`, or a dedicated validation scan), plus add a regression fixture where a matching row has `id: null` to lock the intended behavior.
- **Reviewer**: dyn-jq-filter-semantics-output.txt
- **Concern**: - **correctness** `audit-scan-run-mangled-rows.jq:9-13` — The pipeline ends with `) | .id`, so rows that satisfy the plan-review/accepted/non-canonical predicate still contribute a line when `.id` is missing, JSON `null`, or non-string (for example an object), because `jq -r` will still print a line per match (`null`, JSON, etc.) and `audit-scan-run.sh` turns that into a count via `wc -l`, inflating `oos-category-mangle` and `category-stats.mangled` relative to “one accepted finding row” semantics and risking false positives if upstream ever emits accepted rows without a string `id`. **Suggested fix:** Narrow the emitted stream to stable string ids (for example `select(...) | .id | strings` or `select((.id|type)=="string")`) and treat anything else as malformed (skip, `error`, or a dedicated validation scan), plus add a regression fixture where a matching row has `id: null` to lock the intended behavior.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] The diff also adds committed `larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/` artifacts (including `plan-goals-test.md` that still echoes the older “search `--state open`” wording from the original plan); that is orthogonal to jq semantics but may be undesirable PR surface area compared to the audit-runs script/doc changes alone.
- **Reviewer**: dyn-jq-filter-semantics-output.txt
- **Concern**: - The diff also adds committed `larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/` artifacts (including `plan-goals-test.md` that still echoes the older “search `--state open`” wording from the original plan); that is orthogonal to jq semantics but may be undesirable PR surface area compared to the audit-runs script/doc changes alone.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] For the checklist items you cared about: `catstr` maps JSON `null`/non-scalar categories to an empty string, so those rows drop out of the mangled predicate (no silent “null category” false positive); strict `.phase == "plan-review"` / `.outcome == "accepted"` comparisons fail closed on missing/null fields without jq errors; and for normal rows with string canonical `category`, plan-review+accepted rows are excluded from `mangled` while remaining eligible for the separate `canonical` counter, so those two buckets are disjoint in the intended data shape.
- **Reviewer**: dyn-jq-filter-semantics-output.txt
- **Concern**: - For the checklist items you cared about: `catstr` maps JSON `null`/non-scalar categories to an empty string, so those rows drop out of the mangled predicate (no silent “null category” false positive); strict `.phase == "plan-review"` / `.outcome == "accepted"` comparisons fail closed on missing/null fields without jq errors; and for normal rows with string canonical `category`, plan-review+accepted rows are excluded from `mangled` while remaining eligible for the separate `canonical` counter, so those two buckets are disjoint in the intended data shape.
- **Suggested revision**: Address the concern above.

### FINDING_23: **architecture** `.claude/skills/audit-runs/scripts/audit-compute-counters.sh:102-111` and `.claude/skills/audit-runs/scripts/audit-scan-run.sh:467` — `OOS_CLEAN_DELTA` / `OOS_BLANK_DELTA` suppression is keyed off a substring `grep -Fq "review-findings-full.jsonl not found"` on `category-stats.detail`, while the jq-failure partial path uses details such as `mangled-category aggregate unavailable after oos-category-mangle jq error` (see `audit-scan-run.sh:437-451`), which correctly avoids that substring; there is still no compile-time or test-enforced link between the emitted missing-file copy and the grep needle, so a wording-only change on either side could silently re-enable counting placeholder `canonical` / `oos_blank` as real deltas. **Suggested fix:** add a small stable field on the `category-stats` NDJSON (for example `partial_reason: missing_jsonl` vs `mangled_unavailable`) and branch `skip_cs_clean_blank` on that field instead of grepping prose.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/scripts/audit-compute-counters.sh:102-111` and `.claude/skills/audit-runs/scripts/audit-scan-run.sh:467` — `OOS_CLEAN_DELTA` / `OOS_BLANK_DELTA` suppression is keyed off a substring `grep -Fq "review-findings-full.jsonl not found"` on `category-stats.detail`, while the jq-failure partial path uses details such as `mangled-category aggregate unavailable after oos-category-mangle jq error` (see `audit-scan-run.sh:437-451`), which correctly avoids that substring; there is still no compile-time or test-enforced link between the emitted missing-file copy and the grep needle, so a wording-only change on either side could silently re-enable counting placeholder `canonical` / `oos_blank` as real deltas. **Suggested fix:** add a small stable field on the `category-stats` NDJSON (for example `partial_reason: missing_jsonl` vs `mangled_unavailable`) and branch `skip_cs_clean_blank` on that field instead of grepping prose.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] **Partial-data routing verification (scout checklist):** `audit-scan-run.sh:467` emits `detail` exactly as `review-findings-full.jsonl not found`, matching `audit-compute-counters.sh:110`; the mangled/jq partial strings (`audit-scan-run.sh:437-451`) do not contain that substring, so there is no false positive on the skip gate; `detail_val` empty yields `skip_cs_clean_blank=false` (`audit-compute-counters.sh:103-112`), so clean/blank deltas are not dropped solely for a missing `detail` key; **test 34c** in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1023-1035` feeds `partial_data:true` with non-zero `canonical`/`oos_blank` and the missing-file detail and asserts both deltas are `0`, so the skip path is exercised.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **Partial-data routing verification (scout checklist):** `audit-scan-run.sh:467` emits `detail` exactly as `review-findings-full.jsonl not found`, matching `audit-compute-counters.sh:110`; the mangled/jq partial strings (`audit-scan-run.sh:437-451`) do not contain that substring, so there is no false positive on the skip gate; `detail_val` empty yields `skip_cs_clean_blank=false` (`audit-compute-counters.sh:103-112`), so clean/blank deltas are not dropped solely for a missing `detail` key; **test 34c** in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1023-1035` feeds `partial_data:true` with non-zero `canonical`/`oos_blank` and the missing-file detail and asserts both deltas are `0`, so the skip path is exercised.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] **Branch commits (since merge-base with `main`):** `0f47381e` fix(audit-runs)…, `4dedd457` chore(larch-logs)…, then four “Address code review feedback” commits, then `ceaac648`.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **Branch commits (since merge-base with `main`):** `0f47381e` fix(audit-runs)…, `4dedd457` chore(larch-logs)…, then four “Address code review feedback” commits, then `ceaac648`.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **Housekeeping:** `.claude/skills/audit-runs/scripts/test-audit-runs.sh` reuses the `[34c]` assertion tag for both `SCAN_FILES_FOUND` and the new missing-file delta test (`~995` vs `~1034`), which only hurts failure triage, not counter math.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **Housekeeping:** `.claude/skills/audit-runs/scripts/test-audit-runs.sh` reuses the `[34c]` assertion tag for both `SCAN_FILES_FOUND` and the new missing-file delta test (`~995` vs `~1034`), which only hurts failure triage, not counter math.
- **Suggested revision**: Address the concern above.

