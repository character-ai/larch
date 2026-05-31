### FINDING_1: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:89-145 and skills/design/scripts/decompose-panel-dispatch.sh:136-204
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Parallel both-absent generic-Claude launch blocks with divergent prompt assembly and validation. Fixing TSV/sentinel handling on one path (e.g. plan-review validate-research-output) without updating the other leaves inconsistent degraded floors and panel contracts. Extract a shared helper or enforce one canonical pattern both scripts call.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/decompose-panel-dispatch.sh:144-148
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Generic decompose prompt uses sed anchored on "Your focus:" plus head -n 8. Template edits that move or rename that section break the combined prompt without test failure until runtime. Build generic prompt from render_prompt per archetype or add template-structure harness assertions.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/plan-review-loop.sh:813-821 and skills/design/scripts/dispatch-plan-review-panel.sh:262-268
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] COMBINED_FALLBACK_COUNT > floor_half degradation heuristic is inert for --no-fallback design panels. Operators or maintainers may believe Claude/cross-tool padding fired when only slot drops occurred. Remove or scope fallback-count degradation to legacy multi-phase callers only.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/dispatch-with-waterfall.sh:463-471
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate if/else branches when assembling ALL_OUTPUT_FILES. Minor maintenance noise; no functional regression identified. Unify loops with a single empty-path skip.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:67
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_dynamic_prompt claims Cursor + Codex when only one vendor is present. Misleading dynamic-slot instructions in single-vendor runs. Parameterize vendor wording from CODEX_PRESENT/CURSOR_PRESENT.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/dispatch-plan-voters.sh:183-203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Compact ALL_OUTPUT_FILES under --no-fallback is mapped to Voter 2/3 by sequential index over manifest rows, not by slot output path. Codex voter fails and Cursor succeeds: ALL_OUTPUT_FILES has only cursor-vote-output.txt; loop assigns it to VOTER_2_PATH (codex row) while VOTER_3 may also read the same path — double-count or wrong TOOL in tally. Match waterfall outputs to manifest .output paths (like decompose-panel-dispatch.sh) or emit per-slot path KVs; add codex-fail/cursor-ok harness assertions.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:96-102
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Both-absent generic prompt uses only head -n 1 per archetype plus one shared tail, not full per-lens render bodies. Externals both down on HARD plan: single Claude reviewer gets thinner lens guidance than five separate reviewers; may under-report findings but does not stall. Expand generic prompt to full per-archetype bodies or document compressed floor as intentional.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/design/scripts/test-dispatch-plan-assessors.sh:154-163
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Both-absent assessor test only checks empty manifest not Claude floor output. A change that skips launch-claude-review or marks CLAUDE_ASSESSOR_STATUS failed while leaving manifest empty would pass CI despite violating acceptance single-Claude-assessor floor. After both-absent run assert on $out: CLAUDE_ASSESSOR_STATUS=launched non-empty CLAUDE_ASSESSOR_PATH DISPATCH_OK=true (and degraded warning if intended).
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-dispatch-with-waterfall.sh:76-96
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dead cp stub remains after grouped-reuse tests removed. Maintainers may reintroduce or debug cp-fail reuse paths that no longer exist in production; stub adds noise with zero assertions. Remove unused cp stub and related env knobs unless a new ungrouped phase-2 test needs them.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/scripts/test-dispatch-plan-review-panel.sh:43-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stubs still emit removed PHASE2_RELAUNCH_COUNT KV. Downstream code that still requires PHASE2_RELAUNCH_COUNT will not fail harnesses that mimic production stdout shape. Align stubs with production KVs or add assertion that dispatcher omits PHASE2_RELAUNCH_COUNT.
- **Suggested revision**: Address the concern above.

### FINDING_11: **Removed `reuse_slot_result` / `cp` impersonation** — eliminates copies without `.done` sentinels (prior ~31 min `SENTINEL_TIMEOUT` stalls) and stops treating one external opinion as two independent reviewers.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Removed `reuse_slot_result` / `cp` impersonation** — eliminates copies without `.done` sentinels (prior ~31 min `SENTINEL_TIMEOUT` stalls) and stops treating one external opinion as two independent reviewers.
- **Suggested revision**: Address the concern above.

### FINDING_12: **`--no-fallback` paths-file contract** — only successful slot outputs are listed; collectors no longer wait on ghost paths. Newline checks on manifest `output` paths remain (`dispatch-with-waterfall.sh` ~117–120, 451–458).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--no-fallback` paths-file contract** — only successful slot outputs are listed; collectors no longer wait on ghost paths. Newline checks on manifest `output` paths remain (`dispatch-with-waterfall.sh` ~117–120, 451–458).
- **Suggested revision**: Address the concern above.

### FINDING_13: **Manifest construction** — plan-review/decompose use `jq -nc --arg` for NDJSON rows (safe escaping). Slot validation still restricts `tool` to `codex|cursor` and requires string-typed paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Manifest construction** — plan-review/decompose use `jq -nc --arg` for NDJSON rows (safe escaping). Slot validation still restricts `tool` to `codex|cursor` and requires string-typed paths.
- **Suggested revision**: Address the concern above.

### FINDING_14: **`degraded-tools-gate.sh` env fallback** — values pass through `norm_bool` / `norm_tristate`; flags override env; gate is a **detector only** (does not choose which tools launch). Aligns warnings with `session-setup` exports; not a bypass of `--codex-present` / `--cursor-present` on dispatchers.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`degraded-tools-gate.sh` env fallback** — values pass through `norm_bool` / `norm_tristate`; flags override env; gate is a **detector only** (does not choose which tools launch). Aligns warnings with `session-setup` exports; not a bypass of `--codex-present` / `--cursor-present` on dispatchers.
- **Suggested revision**: Address the concern above.

### FINDING_15: **`write-design-current-env.sh`** — still uses `printf '%q'` for sourced env; session-id/repo/pid validation unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`write-design-current-env.sh`** — still uses `printf '%q'` for sourced env; session-id/repo/pid validation unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_16: **No new secrets, `eval` on untrusted input, or shell-outs with unquoted external data** in the changed dispatch paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new secrets, `eval` on untrusted input, or shell-outs with unquoted external data** in the changed dispatch paths. ---
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/dispatch-plan-review-panel.sh:183-210` — Dynamic scout slugs (`_slug` from `scout-plan-manifest.json`) are interpolated into filesystem paths without a slug charset guard (e.g. `/` or `..` in `name`). `larch_design_tmpdir_validate` rejects `..` on the tmpdir root, not on slug segments, so a hostile or malformed scout manifest could write outside the intended flat naming layout. **Pre-existing**; not introduced by availability gating. **Suggested fix:** sanitize slugs (same spirit as `plan-review-loop.sh`’s `_fail_slug` python one-liner) before use in paths.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `scripts/dispatch-plan-voters.sh:139-144`, `skills/design/scripts/dispatch-plan-assessors.sh:95-100` — NDJSON rows are built with `printf '{"…":"%s",…}'` instead of `jq -nc`. Paths today live under an allowlisted `DESIGN_TMPDIR`, so practical risk is low, but `"` or `\` in a path would corrupt the manifest. **Pre-existing pattern** on this branch. **Suggested fix:** use `jq -nc` like `dispatch-plan-review-panel.sh` for defense in depth. --- **Summary:** From a security-and-trust-boundaries lens, this branch is **sound**: it removes misleading cross-slot output reuse, closes a resource-exhaustion stall, and keeps path/manifest validation. No injection, secret leakage, or auth-boundary regressions were identified in the changed code. Remaining notes are hardening opportunities outside the diff’s threat model.
- **Suggested revision**: Address the concern above.

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

### FINDING_22: architecture: scripts/dispatch-with-waterfall.sh:411-427
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] dispatch_ok not cleared when only dynamic slots exist and all fail under --no-fallback. Hypothetical dynamic-only manifest: ALL_SLOTS_DROPPED with DISPATCH_OK=true yields inconsistent soft vs hard failure vs static-only total drop. Set dispatch_ok=false whenever all_output_files is empty and slot_count > 0.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:104,226
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic and waterfall first-line ERE patterns differ. Output accepted on both-absent floor could be dropped on single-vendor waterfall for the same bytes. Unify first-line pattern constant across both paths.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] architecture: skills/design/scripts/decompose-aggregator.sh:82
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale eight-proposal header after availability-gated dispatch. Operator sees wrong slot-count expectation in merged prompt. Update header to reflect present-vendor slot count.
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

### FINDING_30: [OUT_OF_SCOPE] **Unquoted** `_wf_files=($all_output_files)` / `_wf_tools=($all_output_tools)` (`scripts/dispatch-plan-voters.sh:176-181`) follow the same space-delimited `emit_kv` contract as the rest of the waterfall stack; paths under `DESIGN_TMPDIR` are conventionally space-free, so this is consistent with repo practice rather than a new Bash 3.2 hazard.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Unquoted** `_wf_files=($all_output_files)` / `_wf_tools=($all_output_tools)` (`scripts/dispatch-plan-voters.sh:176-181`) follow the same space-delimited `emit_kv` contract as the rest of the waterfall stack; paths under `DESIGN_TMPDIR` are conventionally space-free, so this is consistent with repo practice rather than a new Bash 3.2 hazard.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **`degraded-tools-gate.sh` stderr WARNINGs** (`scripts/degraded-tools-gate.sh:57-67`) go through `larch_err` on FD 2; canonical skill callers pass explicit `--codex-*` / `--cursor-*` flags (`skills/shared/external-reviewers.md:29-32`), so production KV parsing on stdout alone is unaffected. Harness cases 8–9 intentionally use `2>&1` to assert those warnings (`scripts/test-degraded-tools-gate.sh:104-125`); merged capture only becomes risky for ad-hoc callers that omit flags, rely on env, and parse stdout without ignoring non-`KEY=value` lines (case 11 documents that posture).
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **`degraded-tools-gate.sh` stderr WARNINGs** (`scripts/degraded-tools-gate.sh:57-67`) go through `larch_err` on FD 2; canonical skill callers pass explicit `--codex-*` / `--cursor-*` flags (`skills/shared/external-reviewers.md:29-32`), so production KV parsing on stdout alone is unaffected. Harness cases 8–9 intentionally use `2>&1` to assert those warnings (`scripts/test-degraded-tools-gate.sh:104-125`); merged capture only becomes risky for ad-hoc callers that omit flags, rely on env, and parse stdout without ignoring non-`KEY=value` lines (case 11 documents that posture).
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] `scripts/dispatch-plan-voters.md:16-22` still describes the legacy three-phase waterfall; the script now passes `--no-fallback` (`scripts/dispatch-plan-voters.sh:153`). Doc drift only, not a runtime defect in the current code path.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - `scripts/dispatch-plan-voters.md:16-22` still describes the legacy three-phase waterfall; the script now passes `--no-fallback` (`scripts/dispatch-plan-voters.sh:153`). Doc drift only, not a runtime defect in the current code path.
- **Suggested revision**: Address the concern above.

### FINDING_33: **architecture** `scripts/dispatch-plan-voters.sh:183-203` — Under `--no-fallback`, `dispatch-with-waterfall.sh` emits a compact `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` pair that omits dropped slots, but voter path assignment walks the manifest in fixed codex-then-cursor order and blindly consumes `_wf_files[_wf_idx]`. When the codex row fails and the cursor row succeeds (common Codex-down / probe-failed shape), the sole surviving cursor path is bound to `VOTER_2_PATH` / `VOTER_2_TOOL` while `VOTER_3` stays on the default path and is marked `failed`, so plan-review voting can attribute the wrong vendor to slot 2 and under-count external judges even though `DISPATCH_OK=true`. **Suggested fix:** For each manifest row, select the waterfall output whose `ALL_OUTPUT_TOOLS` entry matches that row’s `.tool` (or read the compact paths-file with explicit slot/tool metadata) instead of positional `_wf_idx` advancement; add a harness case with codex phase-1 failure and cursor success asserting `VOTER_2_STATUS=failed`, `VOTER_3_STATUS=launched`, and `VOTER_3_TOOL=cursor`.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **architecture** `scripts/dispatch-plan-voters.sh:183-203` — Under `--no-fallback`, `dispatch-with-waterfall.sh` emits a compact `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` pair that omits dropped slots, but voter path assignment walks the manifest in fixed codex-then-cursor order and blindly consumes `_wf_files[_wf_idx]`. When the codex row fails and the cursor row succeeds (common Codex-down / probe-failed shape), the sole surviving cursor path is bound to `VOTER_2_PATH` / `VOTER_2_TOOL` while `VOTER_3` stays on the default path and is marked `failed`, so plan-review voting can attribute the wrong vendor to slot 2 and under-count external judges even though `DISPATCH_OK=true`. **Suggested fix:** For each manifest row, select the waterfall output whose `ALL_OUTPUT_TOOLS` entry matches that row’s `.tool` (or read the compact paths-file with explicit slot/tool metadata) instead of positional `_wf_idx` advancement; add a harness case with codex phase-1 failure and cursor success asserting `VOTER_2_STATUS=failed`, `VOTER_3_STATUS=launched`, and `VOTER_3_TOOL=cursor`.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] **`scripts/dispatch-with-waterfall.sh:411-426` + `skills/design/scripts/assess-plan-round.sh:222-232`:** The new `--no-fallback` contract treats per-slot drops as non-fatal (`DISPATCH_OK=true` when any static slot survives), but `assess-plan-round.sh` still aborts tally whenever waterfall `DISPATCH_OK=false`, including the case where Claude succeeded and both external assessor rows were dropped (`ALL_SLOTS_DROPPED`). That is outside the four callers named in the scout prompt but is the same semantic asymmetry.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **`scripts/dispatch-with-waterfall.sh:411-426` + `skills/design/scripts/assess-plan-round.sh:222-232`:** The new `--no-fallback` contract treats per-slot drops as non-fatal (`DISPATCH_OK=true` when any static slot survives), but `assess-plan-round.sh` still aborts tally whenever waterfall `DISPATCH_OK=false`, including the case where Claude succeeded and both external assessor rows were dropped (`ALL_SLOTS_DROPPED`). That is outside the four callers named in the scout prompt but is the same semantic asymmetry.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] **`scripts/dispatch-with-waterfall.sh:353-354` + `FALLBACK_COUNTER_FILE`:** Design panel/voter callers do not pass `--fallback-counter-file`; forcing `combined_fallback=0` under `--no-fallback` does not under-report in those paths. Only `/review`-style callers that opt into the counter file are affected, and none of the in-scope design dispatchers use it.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **`scripts/dispatch-with-waterfall.sh:353-354` + `FALLBACK_COUNTER_FILE`:** Design panel/voter callers do not pass `--fallback-counter-file`; forcing `combined_fallback=0` under `--no-fallback` does not under-report in those paths. Only `/review`-style callers that opt into the counter file are affected, and none of the in-scope design dispatchers use it.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] **`skills/design/scripts/plan-review-loop.sh:772-829`, `skills/design/scripts/dispatch-plan-review-panel.sh:265-280`, `skills/design/scripts/decompose-panel-dispatch.sh:299-313`:** Partial drop signaling is wired consistently via compact paths-file length vs manifest `slot_count`, `DEGRADED_ROUND` / `DEGRADED_PANEL`, `STATIC_DISPATCH_OK`, and `ALL_SLOTS_DROPPED`; `panel-failed` is gated on unreadable paths plus `DISPATCH_OK!=true`, which matches the intended degrade-vs-abort split for partial success.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **`skills/design/scripts/plan-review-loop.sh:772-829`, `skills/design/scripts/dispatch-plan-review-panel.sh:265-280`, `skills/design/scripts/decompose-panel-dispatch.sh:299-313`:** Partial drop signaling is wired consistently via compact paths-file length vs manifest `slot_count`, `DEGRADED_ROUND` / `DEGRADED_PANEL`, `STATIC_DISPATCH_OK`, and `ALL_SLOTS_DROPPED`; `panel-failed` is gated on unreadable paths plus `DISPATCH_OK!=true`, which matches the intended degrade-vs-abort split for partial success.
- **Suggested revision**: Address the concern above.

