### FINDING_12: **correctness** `skills/review/scripts/review-core.md:19` — Companion contract still documents `--dynamic-archetypes N` as `0..4` while `skills/review/scripts/review-core.sh` on the branch accepts `0..8`, so operators reading only the `.md` file get incorrect validation semantics. **Suggested fix:** Update the flag line to `0..8` to match `review-core.sh` usage/error strings.
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **correctness** `skills/review/scripts/review-core.md:19` — Companion contract still documents `--dynamic-archetypes N` as `0..4` while `skills/review/scripts/review-core.sh` on the branch accepts `0..8`, so operators reading only the `.md` file get incorrect validation semantics. **Suggested fix:** Update the flag line to `0..8` to match `review-core.sh` usage/error strings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_14: **risk-integration** `scripts/test-session-setup-presence-defaults.sh:123` — The test harness still greps for the old invalid-cap warning text `must be 0..4`, while `scripts/session-setup.sh` now emits `must be 0..8`; the harness will report `FAIL: invalid caller dynamic archetypes warning missing` after this branch. **Suggested fix:** Update the expected warning to `0..8` and consider adding a positive `8` passthrough case so the new cap is pinned by the harness.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `scripts/test-session-setup-presence-defaults.sh:123` — The test harness still greps for the old invalid-cap warning text `must be 0..4`, while `scripts/session-setup.sh` now emits `must be 0..8`; the harness will report `FAIL: invalid caller dynamic archetypes warning missing` after this branch. **Suggested fix:** Update the expected warning to `0..8` and consider adding a positive `8` passthrough case so the new cap is pinned by the harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] **Pre-existing product issues** not introduced by this branch’s panel/cap edits (for example, historical `review-core.sh` zero-findings tally visibility called out in committed `larch-logs/**` artifacts) are unchanged by the diff under review.
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **Pre-existing product issues** not introduced by this branch’s panel/cap edits (for example, historical `review-core.sh` zero-findings tally visibility called out in committed `larch-logs/**` artifacts) are unchanged by the diff under review.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] **`queue_codex_union_slot` (`skills/review/scripts/dispatch-panel.sh:99-118`) relative to the scout directive:** The function always materializes `codex-union-agent.md` (either via `cat`/`printf` or `cp`) before appending the NDJSON manifest line at `skills/review/scripts/dispatch-panel.sh:116`; it is invoked only once per process from the `ROUND_NUM==1` gate at `skills/review/scripts/dispatch-panel.sh:412-415`, so it cannot be double-queued within a single dispatch run. The `jq` pipeline for `focus_list` filters null/empty focus areas and falls back to copying `agents/code-reviewer.md` when the enriched branch is not taken; `dispatch-with-waterfall.sh` consumes slots in file order (`scripts/dispatch-with-waterfall.sh:63-99`, `265-276`) with no requirement that Codex appear before dynamics, so placing the union slot after dynamic rows is structurally fine. Output path stability across rounds is tmpdir-scoped (`codex-union-output.txt` under `REVIEW_TMPDIR`); round-2 tests use a fresh tmpdir and assert the file is absent, which matches “no slot, no writer” behavior rather than proving deletion of leftovers from a reused directory (pre-existing operational pattern).
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **`queue_codex_union_slot` (`skills/review/scripts/dispatch-panel.sh:99-118`) relative to the scout directive:** The function always materializes `codex-union-agent.md` (either via `cat`/`printf` or `cp`) before appending the NDJSON manifest line at `skills/review/scripts/dispatch-panel.sh:116`; it is invoked only once per process from the `ROUND_NUM==1` gate at `skills/review/scripts/dispatch-panel.sh:412-415`, so it cannot be double-queued within a single dispatch run. The `jq` pipeline for `focus_list` filters null/empty focus areas and falls back to copying `agents/code-reviewer.md` when the enriched branch is not taken; `dispatch-with-waterfall.sh` consumes slots in file order (`scripts/dispatch-with-waterfall.sh:63-99`, `265-276`) with no requirement that Codex appear before dynamics, so placing the union slot after dynamic rows is structurally fine. Output path stability across rounds is tmpdir-scoped (`codex-union-output.txt` under `REVIEW_TMPDIR`); round-2 tests use a fresh tmpdir and assert the file is absent, which matches “no slot, no writer” behavior rather than proving deletion of leftovers from a reused directory (pre-existing operational pattern).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-cap-bounds-sweep-output.txt
- **Concern**: - **architecture** `skills/review/scripts/dispatch-panel.sh:333-415` runs the scout and `synthesize_dynamic_slots` before `queue_codex_union_slot`, so `DYNAMIC_SLOTS` / `SCOUT_MANIFEST` are populated when the union agent is built; no ordering defect spotted there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-cap-bounds-sweep-output.txt
- **Concern**: - **code-quality** Bash `case "$value" in [0-8])` in `dispatch-panel.sh`, `review-core.sh`, `review-and-fix.sh`, `session-setup.sh`, and `write-session-env.sh` only matches a single digit `0`–`8`, so `9`, `10`, and `80` fall through to the error or warning arms as intended; `scripts/scout-dynamic-archetypes.sh:168-170` adds `(( 10#$MAX_ARCHETYPES <= 8 ))`, which correctly bounds multi-digit numerics for the scout path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-cap-bounds-sweep-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-dispatch-panel.sh:478-493` uses `for bad in 9 -1 abc`, matching the new single-digit invalid boundary after raising the cap to 8; `scripts/test-session-env-roundtrip.sh:223-241` already rejects `--dynamic-archetypes 9` and accepts `4`, so that roundtrip script does not need a boundary change for the cap raise.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] The `<feature_description>` block in the prompt says the active panel should be **Cursor-only**, while the branch diff and current tree keep **one Codex union** reviewer on round 1 plus voting still mentioning Codex; that is a **requirements vs shipped behavior** mismatch in the prompt text, not something inferred from code alone.
- **Reviewer**: dyn-panel-unification-semantics-output.txt
- **Concern**: - The `<feature_description>` block in the prompt says the active panel should be **Cursor-only**, while the branch diff and current tree keep **one Codex union** reviewer on round 1 plus voting still mentioning Codex; that is a **requirements vs shipped behavior** mismatch in the prompt text, not something inferred from code alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] The stable topology anchor id `implement.review_and_fix.panel_hard` in `skills/shared/topology.tsv` / `docs/topology.md` still reads “hard” even though the composition column now states hard and simple share the same layout; that naming skew is longstanding pattern (id vs prose) and is only partially confusing, not a runtime defect by itself.
- **Reviewer**: dyn-panel-unification-semantics-output.txt
- **Concern**: - The stable topology anchor id `implement.review_and_fix.panel_hard` in `skills/shared/topology.tsv` / `docs/topology.md` still reads “hard” even though the composition column now states hard and simple share the same layout; that naming skew is longstanding pattern (id vs prose) and is only partially confusing, not a runtime defect by itself.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] `PANEL_SHAPE=simple|hard` remains meaningful outside static slot parity (e.g. `review-and-fix.sh` / `run-step5-review.sh` **round caps** and logging still branch on `POST_PLAN_WORKFLOW_PATH` → `--panel`); the branch does not appear to remove that signal, only the static dispatch shape.
- **Reviewer**: dyn-panel-unification-semantics-output.txt
- **Concern**: - `PANEL_SHAPE=simple|hard` remains meaningful outside static slot parity (e.g. `review-and-fix.sh` / `run-step5-review.sh` **round caps** and logging still branch on `POST_PLAN_WORKFLOW_PATH` → `--panel`); the branch does not appear to remove that signal, only the static dispatch shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] code-quality: skills/review/scripts/test-tally-code-votes.sh:444-678
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fixtures still use codex-generalist naming None for this PR File not modified; update only if harness should track new manifest
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] risk-integration: docs/workflow-lifecycle.md:193
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] External-reviewer fallback bullet unchanged while nearby quick-mode text was edited. May over-generalize Phase 3 behavior vs new slot counts; not introduced by the functional shell changes in this diff. Optional editorial pass in a separate docs-only change if you want perfect cross-doc alignment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] risk-integration: scripts/test-scout-dynamic-archetypes.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Scout tests still only exercise --max-archetypes 4 and do not assert new 0–8 boundaries. Optional gap if scout CLI regressions at 8 or >8 are a concern. Extend scout test harness when touching scout again.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] risk-integration: scripts/test-scout-dynamic-archetypes.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Scout tests still only exercise --max-archetypes 4. Optional gap for CLI max 8 behavior unless extended later. Add boundary tests when editing scout tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_3: **architecture** `skills/review/scripts/check-reviewer-failure-threshold.sh:37-47` — Round 1 still treats `--panel hard` as a **12-slot** intended static panel (`hard) STATIC_INTENDED_SLOTS=12`) while `review-core.sh` passes `--launched-slots` from `STATIC_SLOT_COUNT` emitted by `dispatch-panel.sh`, which the branch changes to **7** for round 1 hard (6 Cursor + 1 Codex union). That makes `NEVER_LAUNCHED=$((INTENDED_SLOTS - LAUNCHED_SLOTS))` add **five phantom failures** whenever Codex is available and the full static manifest launches, and it compares real failures against a **>50% of 12** threshold instead of **>50% of 7**, so HARD round 1 can **stall (`panel-failed`) too early** or report **distorted failure tallies**. **Suggested fix:** Unify round-1 intended static counts with `dispatch-panel.sh` (e.g. both `simple` and `hard` use **7** on round 1, **6** thereafter), refresh the inline threshold comment at `skills/review/scripts/check-reviewer-failure-threshold.sh:120-127`, and update `skills/review/scripts/check-reviewer-failure-threshold.md` plus `skills/review/scripts/test-check-reviewer-failure-threshold.sh` expected `INTENDED_SLOTS` / `--launched-slots` cases so `make test-check-reviewer-failure-threshold` matches the new manifest.
- **Reviewer**: dyn-panel-unification-semantics-output.txt
- **Concern**: - **architecture** `skills/review/scripts/check-reviewer-failure-threshold.sh:37-47` — Round 1 still treats `--panel hard` as a **12-slot** intended static panel (`hard) STATIC_INTENDED_SLOTS=12`) while `review-core.sh` passes `--launched-slots` from `STATIC_SLOT_COUNT` emitted by `dispatch-panel.sh`, which the branch changes to **7** for round 1 hard (6 Cursor + 1 Codex union). That makes `NEVER_LAUNCHED=$((INTENDED_SLOTS - LAUNCHED_SLOTS))` add **five phantom failures** whenever Codex is available and the full static manifest launches, and it compares real failures against a **>50% of 12** threshold instead of **>50% of 7**, so HARD round 1 can **stall (`panel-failed`) too early** or report **distorted failure tallies**. **Suggested fix:** Unify round-1 intended static counts with `dispatch-panel.sh` (e.g. both `simple` and `hard` use **7** on round 1, **6** thereafter), refresh the inline threshold comment at `skills/review/scripts/check-reviewer-failure-threshold.sh:120-127`, and update `skills/review/scripts/check-reviewer-failure-threshold.md` plus `skills/review/scripts/test-check-reviewer-failure-threshold.sh` expected `INTENDED_SLOTS` / `--launched-slots` cases so `make test-check-reviewer-failure-threshold` matches the new manifest.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: **code-quality** `skills/review/scripts/test-dispatch-panel.md:7-13` — Several contract docs remain stale after the behavior change: this file still documents the old Codex generalist/specialist counts and invalid `5`, while `scripts/scout-dynamic-archetypes.md:7`, `skills/review-and-fix/scripts/review-and-fix.md:45`, `skills/review/scripts/review-core.md:19`, and `scripts/write-session-env.md:35` still document `0..4`. These are the repo’s local contracts, so future edits/tests will be guided by the old limits and panel shape. **Suggested fix:** Update the contract docs in the same PR to `0..8` and to the final Cursor-only review panel shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-dispatch-panel.md:7-13` — Several contract docs remain stale after the behavior change: this file still documents the old Codex generalist/specialist counts and invalid `5`, while `scripts/scout-dynamic-archetypes.md:7`, `skills/review-and-fix/scripts/review-and-fix.md:45`, `skills/review/scripts/review-core.md:19`, and `scripts/write-session-env.md:35` still document `0..4`. These are the repo’s local contracts, so future edits/tests will be guided by the old limits and panel shape. **Suggested fix:** Update the contract docs in the same PR to `0..8` and to the final Cursor-only review panel shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_48: risk-integration: skills/review/scripts/tally-code-votes.sh:155-179
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] codex-union basename no longer maps to generic archetype label External greps for generic row may miss codex-union Add explicit codex-union case mirroring codex-generalist mapping
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_8: **correctness** `scripts/write-session-env.md:35` — The `.md` still says `--dynamic-archetypes` must be `0 to 4` while `scripts/write-session-env.sh` now rejects values outside `0 to 8`. **Suggested fix:** Update the sentence to `0 to 8` to match `write-session-env.sh`.
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **correctness** `scripts/write-session-env.md:35` — The `.md` still says `--dynamic-archetypes` must be `0 to 4` while `scripts/write-session-env.sh` now rejects values outside `0 to 8`. **Suggested fix:** Update the sentence to `0 to 8` to match `write-session-env.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

