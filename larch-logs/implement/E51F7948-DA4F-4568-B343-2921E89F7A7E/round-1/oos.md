### FINDING_11: [OUT_OF_SCOPE] code-quality: skills/design/scripts/decompose-panel-dispatch.sh:152-163
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent indentation in both-absent launch block. Readability only. Normalize indentation to surrounding file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `skills/design/scripts/dispatch-plan-review-panel.sh:64-72` — `write_dynamic_prompt` still embeds scout `prompt_body` via `cat` and puts `_slug` in the prompt line. Scout validation limits slug shape; a hand-tampered `scout-plan-manifest.json` in `$DESIGN_TMPDIR` could still influence reviewer prompts (LLM prompt-injection surface). Pre-existing; not introduced by availability gating.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `scripts/dispatch-plan-voters.sh` — `printf`-built JSON for voter slots (unchanged style). Safe while paths stay under session tmpdirs; `jq` would be more robust if paths ever became externally influenced. --- **Verdict:** The branch addresses a real integrity/availability failure (missing `.done` on copied outputs, false twin reviewers) without introducing new injection, secret-handling, or trust-boundary regressions. No security blockers for merge on this lens.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_37: [OUT_OF_SCOPE] **PHASE2_RELAUNCH_COUNT:** Removed from `scripts/dispatch-with-waterfall.sh` stdout; no production reader in `plan-review-loop.sh`, `dispatch-plan-review-panel.sh`, or `decompose-panel-dispatch.sh` (only `COMBINED_FALLBACK_COUNT` / `FALLBACK_COUNT`). Stale mentions remain in `skills/design/scripts/dispatch-plan-review-panel.md:12` and test stubs — doc/harness drift only.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **PHASE2_RELAUNCH_COUNT:** Removed from `scripts/dispatch-with-waterfall.sh` stdout; no production reader in `plan-review-loop.sh`, `dispatch-plan-review-panel.sh`, or `decompose-panel-dispatch.sh` (only `COMBINED_FALLBACK_COUNT` / `FALLBACK_COUNT`). Stale mentions remain in `skills/design/scripts/dispatch-plan-review-panel.md:12` and test stubs — doc/harness drift only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_38: [OUT_OF_SCOPE] **Plan-review collect path:** For non-empty shortened paths-files, `plan-review-loop.sh` collects via `--paths-file` only (`790-795`) and maps reviewers by path in `plan_review_slot_for_reviewer` (`665-704`), not by manifest index — aligned with the new contract.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **Plan-review collect path:** For non-empty shortened paths-files, `plan-review-loop.sh` collects via `--paths-file` only (`790-795`) and maps reviewers by path in `plan_review_slot_for_reviewer` (`665-704`), not by manifest index — aligned with the new contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] **`test-decompose-panel-dispatch.sh` “resolved-paths” case (~184-255):** Stub still writes one paths-file line per manifest row (simulating pre–`--no-fallback` density); it does not exercise dropped-slot / shortened-list alignment, so the decompose index bug above is not caught there.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **`test-decompose-panel-dispatch.sh` “resolved-paths” case (~184-255):** Stub still writes one paths-file line per manifest row (simulating pre–`--no-fallback` density); it does not exercise dropped-slot / shortened-list alignment, so the decompose index bug above is not caught there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_40: [OUT_OF_SCOPE] **`/review` panels:** `skills/review/scripts/dispatch-panel.sh` still uses legacy multi-phase waterfall without `--no-fallback`; positional `outputs_arr` indexing there is unchanged and out of scope for this issue.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **`/review` panels:** `skills/review/scripts/dispatch-panel.sh` still uses legacy multi-phase waterfall without `--no-fallback`; positional `outputs_arr` indexing there is unchanged and out of scope for this issue.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_42: [OUT_OF_SCOPE] `skills/design/scripts/dispatch-plan-assessors.sh:135-144` uses the same `_wf_idx` + compacted `ALL_OUTPUT_FILES` pattern with `--no-fallback`; codex-fail / cursor-ok would mis-assign `CODEX_PATH` the same way (not in the voter focus file, but same branch regression class).
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - `skills/design/scripts/dispatch-plan-assessors.sh:135-144` uses the same `_wf_idx` + compacted `ALL_OUTPUT_FILES` pattern with `--no-fallback`; codex-fail / cursor-ok would mis-assign `CODEX_PATH` the same way (not in the voter focus file, but same branch regression class).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] `scripts/test-dispatch-plan-voters.sh` stubs `dispatch-with-waterfall.sh` to append every manifest row to `all_outputs` even when `PLAN_VOTER_SLOT_*_STATUS=failed` (`:167-168`), so the substantive-fail case does not exercise real compacted output and would not catch the misalignment above.
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - `scripts/test-dispatch-plan-voters.sh` stubs `dispatch-with-waterfall.sh` to append every manifest row to `all_outputs` even when `PLAN_VOTER_SLOT_*_STATUS=failed` (`:167-168`), so the substantive-fail case does not exercise real compacted output and would not catch the misalignment above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_44: [OUT_OF_SCOPE] `scripts/dispatch-plan-voters.md:16-22` still documents three-phase waterfall fallback for Voters 2–3; the script now uses availability gating and `--no-fallback` (stale doc, not a runtime bug).
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - `scripts/dispatch-plan-voters.md:16-22` still documents three-phase waterfall fallback for Voters 2–3; the script now uses availability gating and `--no-fallback` (stale doc, not a runtime bug).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_48: [OUT_OF_SCOPE] **risk-integration (amplified, not introduced by env change alone):** `scripts/degraded-tools-gate.sh:110-117` still tells operators that reviewer/voter panels use a per-slot “backup waterfall” (Codex→Cursor→Claude). This branch removes `--no-fallback` / availability gating for `/design` plan-review, decompose, assessors, and plan voters; the gate text is now materially misleading on interactive “Continue (degraded waterfall)” prompts even when flags/env are correct.
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **risk-integration (amplified, not introduced by env change alone):** `scripts/degraded-tools-gate.sh:110-117` still tells operators that reviewer/voter panels use a per-slot “backup waterfall” (Codex→Cursor→Claude). This branch removes `--no-fallback` / availability gating for `/design` plan-review, decompose, assessors, and plan voters; the gate text is now materially misleading on interactive “Continue (degraded waterfall)” prompts even when flags/env are correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_49: [OUT_OF_SCOPE] **correctness:** Cases 8–9 in `scripts/test-degraded-tools-gate.sh:102-116` are adequately isolated: inline `VAR=value` assignments on the `bash "$GATE"` command line override inherited env for all four probe keys. Flag-based callers that pass all four `--codex-*` / `--cursor-*` arguments remain fully protected because the argv loop overwrites env-seeded defaults (`scripts/degraded-tools-gate.sh:42-51`).
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **correctness:** Cases 8–9 in `scripts/test-degraded-tools-gate.sh:102-116` are adequately isolated: inline `VAR=value` assignments on the `bash "$GATE"` command line override inherited env for all four probe keys. Flag-based callers that pass all four `--codex-*` / `--cursor-*` arguments remain fully protected because the argv loop overwrites env-seeded defaults (`scripts/degraded-tools-gate.sh:42-51`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_50: [OUT_OF_SCOPE] **architecture:** `scripts/degraded-tools-gate.md` was not updated in the branch diff to document env-var fallback or flag-over-env precedence; only the shell init changed. That gap increases the chance of env-only invocations without a documented contract.
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **architecture:** `scripts/degraded-tools-gate.md` was not updated in the branch diff to document env-var fallback or flag-over-env precedence; only the shell init changed. That gap increases the chance of env-only invocations without a documented contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

