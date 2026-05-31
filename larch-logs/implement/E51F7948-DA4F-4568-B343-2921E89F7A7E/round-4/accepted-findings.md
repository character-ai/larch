### FINDING_19: correctness: skills/design/scripts/plan-review-loop.sh:772-782
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] All-static drop under --no-fallback sets DISPATCH_OK=false so empty paths trigger panel-failed instead of degraded zero-findings. Every reviewer fails first-line/validation with one vendor present: waterfall emits ALL_SLOTS_DROPPED and empty paths-file; loop returns panel-failed (exit 1) despite plan requiring degraded tally with zero findings. Treat ALL_SLOTS_DROPPED or empty paths + DEGRADED_ROUND as graceful: skip collect, skipped-empty-findings, LOOP_STATUS=complete; or keep DISPATCH_OK=true for expected all-drop under --no-fallback.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:133-145
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Both-absent generic path clears PANEL_PATHS_FILE and sets DISPATCH_OK=false when structured validation fails. Claude returns usable prose but fails validate-research-output or first-line ERE: plan-review-loop panel-fails the whole round instead of degrading. Keep output path in PANEL_PATHS_FILE with DEGRADED_ROUND=true on validation miss; reserve panel-failed for launch hard-failure.
- **Suggested revision**: Address the concern above.


### FINDING_21: architecture: skills/design/scripts/decompose-panel-dispatch.sh:354-360
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Empty ALL_OUTPUT_FILES_PATH falls back to manifest output paths for all rows. All --no-fallback slots fail: panel-outputs.ndjson lists manifest paths as missing/unparsed though nothing should be collected. When _resolved_paths is empty skip manifest fallback rows or emit a single explicit degraded row.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/dispatch-with-waterfall.sh:411-426 + skills/design/scripts/plan-review-loop.sh:772-782
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] All slots dropped under --no-fallback sets DISPATCH_OK=false; plan-review-loop treats empty paths + DISPATCH_OK!=true as panel-failed. Every external reviewer fails or is absent: waterfall emits DISPATCH_OK=false and an empty paths-file; plan-review-loop returns panel-failed instead of degraded zero-findings tally per plan edge case and test-plan-review-loop.sh:846-861. Keep DISPATCH_OK=true for intentional --no-fallback drops (use ALL_SLOTS_DROPPED/DEGRADED_ROUND), or branch plan-review-loop on DEGRADED_ROUND/ALL_SLOTS_DROPPED for empty paths.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/dispatch-with-waterfall.sh:411-426
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan Step 3 says dispatch_ok stays true for dropped --no-fallback slots; all-static-empty sets dispatch_ok=false. Same all-failed scenario: contradicts plan Step 3 and couples to panel-failed in plan-review-loop. Remove or narrow the all-static-empty dispatch_ok=false block under NO_FALLBACK unless panel-failed is an explicit new requirement.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: skills/design/scripts/test-dispatch-plan-assessors.sh:154-163
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Both-absent assessor harness only checks empty manifest, not Claude assessor floor. Regression could break Claude launch while manifest stays empty; plan acceptance for single-Claude assessor would not be caught. Assert CLAUDE_ASSESSOR_STATUS=launched and non-empty Claude assessor output on both-absent.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:106-111
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan says generic Claude (Opus); implementation uses default launch-claude-review without Opus pin. Both-absent floor may run a non-Opus model while plan/docs promise Opus. Pin model for claude-plan-generic or drop Opus from plan/docs.
- **Suggested revision**: Address the concern above.


### FINDING_29: **correctness** `scripts/dispatch-plan-voters.sh:173-218` — Under `--no-fallback`, `dispatch-with-waterfall.sh` emits a **compact** `ALL_OUTPUT_FILES` list that omits dropped slots while preserving manifest slot order for survivors only (`scripts/dispatch-with-waterfall.sh:463-471`). The new `_wf_idx` loop still walks **every** manifest row (codex before cursor) and advances the index whenever it handles an available tool, without checking whether that slot actually succeeded. If Voter 2 (codex) fails and Voter 3 (cursor) succeeds, `_wf_files[0]` is the cursor output but the codex branch assigns it to `VOTER_2_PATH`/`VOTER_2_TOOL`, so slot 2 is credited with the wrong vendor’s ballot while slot 3 may stay on the default path and show `failed`. That mis-tally is a regression versus the old `read -r -a outputs_arr <<< "$all_outputs"` mapping, which kept positional alignment because the waterfall always emitted one entry per manifest slot (including empties). **Suggested fix:** Drop the index-based re-map for plan voters under `--no-fallback` and mirror `skills/design/scripts/dispatch-plan-assessors.sh:129-145`: keep stable manifest paths (`$DESIGN_TMPDIR/codex-vote-output.txt` / `cursor-vote-output.txt`), derive `VOTER_*_STATUS` from non-empty output (and parse-rate), and only read `ALL_OUTPUT_TOOLS` if you still need tool identity. If alternate paths must be supported, match by manifest `.output` or basename like `skills/design/scripts/decompose-panel-dispatch.sh:328-337`, advancing `_wf_idx` only when a resolved path is bound.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **correctness** `scripts/dispatch-plan-voters.sh:173-218` — Under `--no-fallback`, `dispatch-with-waterfall.sh` emits a **compact** `ALL_OUTPUT_FILES` list that omits dropped slots while preserving manifest slot order for survivors only (`scripts/dispatch-with-waterfall.sh:463-471`). The new `_wf_idx` loop still walks **every** manifest row (codex before cursor) and advances the index whenever it handles an available tool, without checking whether that slot actually succeeded. If Voter 2 (codex) fails and Voter 3 (cursor) succeeds, `_wf_files[0]` is the cursor output but the codex branch assigns it to `VOTER_2_PATH`/`VOTER_2_TOOL`, so slot 2 is credited with the wrong vendor’s ballot while slot 3 may stay on the default path and show `failed`. That mis-tally is a regression versus the old `read -r -a outputs_arr <<< "$all_outputs"` mapping, which kept positional alignment because the waterfall always emitted one entry per manifest slot (including empties). **Suggested fix:** Drop the index-based re-map for plan voters under `--no-fallback` and mirror `skills/design/scripts/dispatch-plan-assessors.sh:129-145`: keep stable manifest paths (`$DESIGN_TMPDIR/codex-vote-output.txt` / `cursor-vote-output.txt`), derive `VOTER_*_STATUS` from non-empty output (and parse-rate), and only read `ALL_OUTPUT_TOOLS` if you still need tool identity. If alternate paths must be supported, match by manifest `.output` or basename like `skills/design/scripts/decompose-panel-dispatch.sh:328-337`, advancing `_wf_idx` only when a resolved path is bound.
- **Suggested revision**: Address the concern above.


### FINDING_33: **architecture** `scripts/dispatch-plan-voters.sh:183-203` — Under `--no-fallback`, `dispatch-with-waterfall.sh` emits a compact `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` pair that omits dropped slots, but voter path assignment walks the manifest in fixed codex-then-cursor order and blindly consumes `_wf_files[_wf_idx]`. When the codex row fails and the cursor row succeeds (common Codex-down / probe-failed shape), the sole surviving cursor path is bound to `VOTER_2_PATH` / `VOTER_2_TOOL` while `VOTER_3` stays on the default path and is marked `failed`, so plan-review voting can attribute the wrong vendor to slot 2 and under-count external judges even though `DISPATCH_OK=true`. **Suggested fix:** For each manifest row, select the waterfall output whose `ALL_OUTPUT_TOOLS` entry matches that row’s `.tool` (or read the compact paths-file with explicit slot/tool metadata) instead of positional `_wf_idx` advancement; add a harness case with codex phase-1 failure and cursor success asserting `VOTER_2_STATUS=failed`, `VOTER_3_STATUS=launched`, and `VOTER_3_TOOL=cursor`.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **architecture** `scripts/dispatch-plan-voters.sh:183-203` — Under `--no-fallback`, `dispatch-with-waterfall.sh` emits a compact `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` pair that omits dropped slots, but voter path assignment walks the manifest in fixed codex-then-cursor order and blindly consumes `_wf_files[_wf_idx]`. When the codex row fails and the cursor row succeeds (common Codex-down / probe-failed shape), the sole surviving cursor path is bound to `VOTER_2_PATH` / `VOTER_2_TOOL` while `VOTER_3` stays on the default path and is marked `failed`, so plan-review voting can attribute the wrong vendor to slot 2 and under-count external judges even though `DISPATCH_OK=true`. **Suggested fix:** For each manifest row, select the waterfall output whose `ALL_OUTPUT_TOOLS` entry matches that row’s `.tool` (or read the compact paths-file with explicit slot/tool metadata) instead of positional `_wf_idx` advancement; add a harness case with codex phase-1 failure and cursor success asserting `VOTER_2_STATUS=failed`, `VOTER_3_STATUS=launched`, and `VOTER_3_TOOL=cursor`.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:67
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_dynamic_prompt claims Cursor + Codex when only one vendor is present. Misleading dynamic-slot instructions in single-vendor runs. Parameterize vendor wording from CODEX_PRESENT/CURSOR_PRESENT.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/dispatch-plan-voters.sh:183-203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Compact ALL_OUTPUT_FILES under --no-fallback is mapped to Voter 2/3 by sequential index over manifest rows, not by slot output path. Codex voter fails and Cursor succeeds: ALL_OUTPUT_FILES has only cursor-vote-output.txt; loop assigns it to VOTER_2_PATH (codex row) while VOTER_3 may also read the same path — double-count or wrong TOOL in tally. Match waterfall outputs to manifest .output paths (like decompose-panel-dispatch.sh) or emit per-slot path KVs; add codex-fail/cursor-ok harness assertions.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/design/scripts/test-dispatch-plan-assessors.sh:154-163
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Both-absent assessor test only checks empty manifest not Claude floor output. A change that skips launch-claude-review or marks CLAUDE_ASSESSOR_STATUS failed while leaving manifest empty would pass CI despite violating acceptance single-Claude-assessor floor. After both-absent run assert on $out: CLAUDE_ASSESSOR_STATUS=launched non-empty CLAUDE_ASSESSOR_PATH DISPATCH_OK=true (and degraded warning if intended).
- **Suggested revision**: Address the concern above.


