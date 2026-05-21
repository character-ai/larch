### FINDING_19: [OUT_OF_SCOPE] architecture: larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/plan-goals-test.md:~1299-1306
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Embedded plan snapshot still says classify with --state open while shipped SKILL uses --state all for C.2 Frozen run-log text can mislead if mistaken for current SOT None for merge; treat as historical unless editing the log for clarity
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: **correctness** `audit-scan-run-mangled-rows.jq:9-13` — The pipeline ends with `) | .id`, so rows that satisfy the plan-review/accepted/non-canonical predicate still contribute a line when `.id` is missing, JSON `null`, or non-string (for example an object), because `jq -r` will still print a line per match (`null`, JSON, etc.) and `audit-scan-run.sh` turns that into a count via `wc -l`, inflating `oos-category-mangle` and `category-stats.mangled` relative to “one accepted finding row” semantics and risking false positives if upstream ever emits accepted rows without a string `id`. **Suggested fix:** Narrow the emitted stream to stable string ids (for example `select(...) | .id | strings` or `select((.id|type)=="string")`) and treat anything else as malformed (skip, `error`, or a dedicated validation scan), plus add a regression fixture where a matching row has `id: null` to lock the intended behavior.
- **Reviewer**: dyn-jq-filter-semantics-output.txt
- **Concern**: - **correctness** `audit-scan-run-mangled-rows.jq:9-13` — The pipeline ends with `) | .id`, so rows that satisfy the plan-review/accepted/non-canonical predicate still contribute a line when `.id` is missing, JSON `null`, or non-string (for example an object), because `jq -r` will still print a line per match (`null`, JSON, etc.) and `audit-scan-run.sh` turns that into a count via `wc -l`, inflating `oos-category-mangle` and `category-stats.mangled` relative to “one accepted finding row” semantics and risking false positives if upstream ever emits accepted rows without a string `id`. **Suggested fix:** Narrow the emitted stream to stable string ids (for example `select(...) | .id | strings` or `select((.id|type)=="string")`) and treat anything else as malformed (skip, `error`, or a dedicated validation scan), plus add a regression fixture where a matching row has `id: null` to lock the intended behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] The diff also adds committed `larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/` artifacts (including `plan-goals-test.md` that still echoes the older “search `--state open`” wording from the original plan); that is orthogonal to jq semantics but may be undesirable PR surface area compared to the audit-runs script/doc changes alone.
- **Reviewer**: dyn-jq-filter-semantics-output.txt
- **Concern**: - The diff also adds committed `larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/` artifacts (including `plan-goals-test.md` that still echoes the older “search `--state open`” wording from the original plan); that is orthogonal to jq semantics but may be undesirable PR surface area compared to the audit-runs script/doc changes alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] For the checklist items you cared about: `catstr` maps JSON `null`/non-scalar categories to an empty string, so those rows drop out of the mangled predicate (no silent “null category” false positive); strict `.phase == "plan-review"` / `.outcome == "accepted"` comparisons fail closed on missing/null fields without jq errors; and for normal rows with string canonical `category`, plan-review+accepted rows are excluded from `mangled` while remaining eligible for the separate `canonical` counter, so those two buckets are disjoint in the intended data shape.
- **Reviewer**: dyn-jq-filter-semantics-output.txt
- **Concern**: - For the checklist items you cared about: `catstr` maps JSON `null`/non-scalar categories to an empty string, so those rows drop out of the mangled predicate (no silent “null category” false positive); strict `.phase == "plan-review"` / `.outcome == "accepted"` comparisons fail closed on missing/null fields without jq errors; and for normal rows with string canonical `category`, plan-review+accepted rows are excluded from `mangled` while remaining eligible for the separate `canonical` counter, so those two buckets are disjoint in the intended data shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] **Partial-data routing verification (scout checklist):** `audit-scan-run.sh:467` emits `detail` exactly as `review-findings-full.jsonl not found`, matching `audit-compute-counters.sh:110`; the mangled/jq partial strings (`audit-scan-run.sh:437-451`) do not contain that substring, so there is no false positive on the skip gate; `detail_val` empty yields `skip_cs_clean_blank=false` (`audit-compute-counters.sh:103-112`), so clean/blank deltas are not dropped solely for a missing `detail` key; **test 34c** in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1023-1035` feeds `partial_data:true` with non-zero `canonical`/`oos_blank` and the missing-file detail and asserts both deltas are `0`, so the skip path is exercised.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **Partial-data routing verification (scout checklist):** `audit-scan-run.sh:467` emits `detail` exactly as `review-findings-full.jsonl not found`, matching `audit-compute-counters.sh:110`; the mangled/jq partial strings (`audit-scan-run.sh:437-451`) do not contain that substring, so there is no false positive on the skip gate; `detail_val` empty yields `skip_cs_clean_blank=false` (`audit-compute-counters.sh:103-112`), so clean/blank deltas are not dropped solely for a missing `detail` key; **test 34c** in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1023-1035` feeds `partial_data:true` with non-zero `canonical`/`oos_blank` and the missing-file detail and asserts both deltas are `0`, so the skip path is exercised.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] **Branch commits (since merge-base with `main`):** `0f47381e` fix(audit-runs)…, `4dedd457` chore(larch-logs)…, then four “Address code review feedback” commits, then `ceaac648`.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **Branch commits (since merge-base with `main`):** `0f47381e` fix(audit-runs)…, `4dedd457` chore(larch-logs)…, then four “Address code review feedback” commits, then `ceaac648`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] **Housekeeping:** `.claude/skills/audit-runs/scripts/test-audit-runs.sh` reuses the `[34c]` assertion tag for both `SCAN_FILES_FOUND` and the new missing-file delta test (`~995` vs `~1034`), which only hurts failure triage, not counter math.
- **Reviewer**: dyn-partial-data-routing-output.txt
- **Concern**: - **Housekeeping:** `.claude/skills/audit-runs/scripts/test-audit-runs.sh` reuses the `[34c]` assertion tag for both `SCAN_FILES_FOUND` and the new missing-file delta test (`~995` vs `~1034`), which only hurts failure triage, not counter math.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] code-quality: larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/*
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large committed run-log flush accompanies the feature branch. Not introduced as a logic defect of audit-runs; policy explicitly allows shipped implement logs. No change required for the audit-runs code review scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] architecture: larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/plan-goals-test.md:1-210
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Flushed plan still mentions --state open for C.1 while SKILL uses --state all Misleading only as historical log text; no executable impact None required for merge; optional log hygiene only
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

