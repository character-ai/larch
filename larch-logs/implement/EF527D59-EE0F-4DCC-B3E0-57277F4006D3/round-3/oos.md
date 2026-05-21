### FINDING_10: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:100-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] split_ballot_to_blocks last-wins on duplicate headings unchanged by this PR. Any pre-existing duplicate-heading ballot could truncate earlier blocks; not introduced here. Future hardening belongs in lib-vote-tally or tally stage if desired globally.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_11: [OUT_OF_SCOPE] risk-integration: scripts/test-lib-vote-tally.sh (unchanged in diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No direct unit assertion added for Reviewer(s) spellings on reviewer_for_block despite lib change. Regression in reviewer_for_block could slip until higher-level tally tests fail. Add a small harness case mirroring the new tally-code-votes comma-reviewer fixture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: **correctness** `skills/review/scripts/aggregate-findings.sh:258-306` — `only_oos_reviewer_slots` labels a reviewer slot as “OOS-only” using set difference `oos - in_scope`, so any slot that appears on at least one in-scope input block is never treated as OOS-only. If an OOS-tagged input finding shares that slot with an in-scope finding, the LLM can merge everything into a single `### FINDING_N:` heading **without** `[OUT_OF_SCOPE]`, attribute only that shared slot, and still pass validation (no slot in `only_oos`, no missing-slot failure), even though `agents/orchestrator-aggregator.md` requires retaining `[OUT_OF_SCOPE]` when an OOS-tagged source is merged with in-scope text. **Suggested fix:** Track OOS at the finding-block level (or merge provenance), and reject in-scope-tagged merged output whenever any OOS-tagged input block was collapsed into it unless the output heading still carries `[OUT_OF_SCOPE]` (or the OOS input remains a separate `FINDING_N` block), instead of keying this solely on “reviewer appears only on OOS-tagged inputs.”
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:258-306` — `only_oos_reviewer_slots` labels a reviewer slot as “OOS-only” using set difference `oos - in_scope`, so any slot that appears on at least one in-scope input block is never treated as OOS-only. If an OOS-tagged input finding shares that slot with an in-scope finding, the LLM can merge everything into a single `### FINDING_N:` heading **without** `[OUT_OF_SCOPE]`, attribute only that shared slot, and still pass validation (no slot in `only_oos`, no missing-slot failure), even though `agents/orchestrator-aggregator.md` requires retaining `[OUT_OF_SCOPE]` when an OOS-tagged source is merged with in-scope text. **Suggested fix:** Track OOS at the finding-block level (or merge provenance), and reject in-scope-tagged merged output whenever any OOS-tagged input block was collapsed into it unless the output heading still carries `[OUT_OF_SCOPE]` (or the OOS input remains a separate `FINDING_N` block), instead of keying this solely on “reviewer appears only on OOS-tagged inputs.”
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: risk-integration: scripts/test-lib-vote-tally.sh:89-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] reviewer_for_block lacks a direct **Reviewer(s)** fixture after regex broadening. Regression in lib-vote-tally would only be caught indirectly via tally harnesses. Add one reviewer_for_block case for **Reviewer(s)** spelling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] In-repo shell consumers of committed `review-findings-full.jsonl` were checked for `.reviewer` / `has("reviewer")`-style access: there are no remaining jq/bash readers of a JSONL `.reviewer` field, and `derive_code_review_tally_from_composed_findings` in `skills/review-and-fix/scripts/review-and-fix.sh:514-527` only filters on `phase`/`outcome`, so the runtime tally path is not coupled to the renamed field.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - In-repo shell consumers of committed `review-findings-full.jsonl` were checked for `.reviewer` / `has("reviewer")`-style access: there are no remaining jq/bash readers of a JSONL `.reviewer` field, and `derive_code_review_tally_from_composed_findings` in `skills/review-and-fix/scripts/review-and-fix.sh:514-527` only filters on `phase`/`outcome`, so the runtime tally path is not coupled to the renamed field.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Large `larch-logs/implement/EF527D59-…` artifacts appearing in the branch diff are operational run-log noise relative to schema-compat auditing, not a consumer contract bug.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - Large `larch-logs/implement/EF527D59-…` artifacts appearing in the branch diff are operational run-log noise relative to schema-compat auditing, not a consumer contract bug.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] The `only_oos` / `oos - in_scope` classification for slots that appear **only** on OOS-tagged inputs matches the intended “not only-OOS” behavior when a slot also appears in-scope; the `oos_drop_tag` test correctly exercises rejection for a strictly-OOS-only reviewer on an untagged merged block.
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - The `only_oos` / `oos - in_scope` classification for slots that appear **only** on OOS-tagged inputs matches the intended “not only-OOS” behavior when a slot also appears in-scope; the `oos_drop_tag` test correctly exercises rejection for a strictly-OOS-only reviewer on an untagged merged block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] `LARCH_AGGREGATOR_DISABLED=1` forces `INPUT_COUNT=0` / `MERGED_COUNT=0` in `aggregate-findings.sh:112-117`, which misreports real findings counts on the KV stream (behavior adjacent to this script but outside the OOS-invariant scout scope).
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - `LARCH_AGGREGATOR_DISABLED=1` forces `INPUT_COUNT=0` / `MERGED_COUNT=0` in `aggregate-findings.sh:112-117`, which misreports real findings counts on the KV stream (behavior adjacent to this script but outside the OOS-invariant scout scope).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] `SECURITY.md:58` still lists only `id`, `phase`, `outcome`, `round_num` as “script-derived” bounded fields and omits the new literal `schema_version` / structured `reviewer_slots` envelope; that is documentation drift around the new batch shape, not a functional regression in the diff itself.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - `SECURITY.md:58` still lists only `id`, `phase`, `outcome`, `round_num` as “script-derived” bounded fields and omits the new literal `schema_version` / structured `reviewer_slots` envelope; that is documentation drift around the new batch shape, not a functional regression in the diff itself.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

