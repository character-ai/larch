### FINDING_1: code-quality: scripts/dispatch-with-waterfall.sh:96-101
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] manifest_validation_fail is defined but never called after fallback_group removal. Dead code accumulates and misleads readers about manifest validation behavior. Delete manifest_validation_fail or restore a real caller.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/references/decompose-panel.md:5-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Companion doc still describes fixed 8-slot waterfall panel per plan Companion doc sync. Operators following decompose-panel.md expect cross-tool waterfall retries that no longer exist. Rewrite for availability matrix and --no-fallback; document both-absent Claude floor.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/references/assessor.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Assessor reference not updated for availability-gated dispatch planned in issue. Step 3.6 docs still imply three externals always run through waterfall. Document slot gating --no-fallback and Claude-only floor.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/references/plan-review.md:231
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Cross-link says decompose uses three-tier waterfall like legacy review. Split-path readers believe decompose still cross-tool relaunches. Update to single-launch availability-gated behavior per decompose-panel.md.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:90-123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Both-absent branch always reports DISPATCH_OK=true without output validation. Failed or non-TSV generic output still looks like successful dispatch; downstream tally may degrade opaquely. Check launch rc and first-line/TSV shape; set DISPATCH_OK and DEGRADED_ROUND accordingly.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:238-245
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] COMBINED_FALLBACK_COUNT degradation logic is dead under --no-fallback. DEGRADED_ROUND never triggers from fallback cost even when panel is degraded. Remove fallback threshold or tie degradation to dispatch/collect outcomes only.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/dispatch-plan-voters.sh:192-193
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Claude fallback status labeling for voters cannot occur with --no-fallback. Misleading status values if code paths change later. Remove or guard fallback relabeling.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/design/scripts/dispatch-plan-assessors.sh:155-156
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Same stale claude fallback labeling for assessor externals under --no-fallback. Same as voter script. Remove or guard fallback relabeling.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:90-123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicated generic-Claude floor vs decompose-panel-dispatch.sh. Future fixes to .done shim or KV contract need two edits. Consider shared helper only if a third caller appears.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/design/scripts/plan-review-loop.sh:206 and skills/review-and-fix/scripts/review-and-fix.sh:130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicate nit-counting awk on same branch. Convergence rule changes require editing two copies. Extract one shared counter script.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: skills/design/scripts/decompose-panel-dispatch.sh:152-163
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent indentation in both-absent launch block. Readability only. Normalize indentation to surrounding file.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/design/scripts/plan-review-loop.sh:771-781
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Empty PANEL_PATHS_FILE after --no-fallback drops all slots is treated as panel-failed instead of degraded zero-findings flow required by the plan. All external plan-review slots fail under --no-fallback; paths-file is empty; loop exits panel-failed and skips tally instead of proceeding with zero findings. Treat intentional empty paths (dispatch OK, no paths) as degraded collect/tally or zero-findings short-circuit; do not use the same branch as missing dispatch failure.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/degraded-tools-gate.sh:110-120
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Degraded explanation still describes per-slot backup waterfall for /design panels after panels use --no-fallback. Operator continues expecting Codex/Cursor/Claude padding; actual run drops absent/failed slots with fewer reviewers. Rewrite DEGRADED_EXPLANATION for design to document availability-gated single launch and both-absent Claude floor; reserve waterfall prose for /review/implement paths.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/design/references/decompose-panel.md:1-68
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Companion doc sync from plan not done; still describes 8-slot three-tier waterfall and waterfall failure wording. Operators and agents following decompose-panel.md expect cross-tool/Claude fallback that decompose-panel-dispatch.sh no longer performs. Update decompose-panel.md (and assessor.md) to match availability-gated --no-fallback behavior in plan-review.md.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/design/references/plan-review.md:5,66-68,231
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Normative plan-review reference header and fallback sections still describe old 10-slot paired waterfall; contradicts updated Dispatch section and code. Readers/implementers follow stale contract and may reintroduce fallback_group or expect per-slot Claude padding. Rewrite top contract, Claude fallback section, and 2b.5 cross-reference for availability matrix and --no-fallback.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:90-123
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Both-absent generic Claude path skips --require-first-line-pattern used on the waterfall dispatch path. Generic reviewer can emit narration-first output that would fail waterfall validation but still enters collect. Apply the same first-line ERE check after launch-claude-review.sh in the both-absent branch.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/dispatch-with-waterfall.sh:403-467
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] --no-fallback reports DISPATCH_OK=true when every slot is dropped, while downstream treats empty paths as failure. Stdout says success; plan-review-loop aborts on empty paths-file; DEGRADED_ROUND stays false because FALLBACK_COUNT is 0. Emit explicit degraded KVs for dropped slots or align plan-review-loop empty-path handling with intentional drops.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/design/scripts/test-dispatch-plan-review-panel.sh:3993-4072
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Acceptance calls for plan-review-loop collect without SENTINEL_TIMEOUT on Codex-down; harness only checks manifest via stub waterfall. Codex-down could still stall collect for full timeout while manifest tests pass. Add collect integration (real or stub collector) with cursor-only paths and assert no SENTINEL_TIMEOUT under short timeout.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Grouped reuse-by-copy removed** (`reuse_slot_result`, ledger, `cp` between slot outputs). That path copied another reviewer’s file without a real `.done` sentinel (availability/DoS) and let one physical result stand in for a different slot (integrity). Deletion is a clear win; no replacement copies results between slots.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Grouped reuse-by-copy removed** (`reuse_slot_result`, ledger, `cp` between slot outputs). That path copied another reviewer’s file without a real `.done` sentinel (availability/DoS) and let one physical result stand in for a different slot (integrity). Deletion is a clear win; no replacement copies results between slots.
- **Suggested revision**: Address the concern above.

### FINDING_20: **`--no-fallback` + paths-file filtering** — Only successful slot paths are written. Downstream collection no longer blocks on phantom outputs. This closes a resource-exhaustion class (31-minute sentinel waits), not an auth bypass.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **`--no-fallback` + paths-file filtering** — Only successful slot paths are written. Downstream collection no longer blocks on phantom outputs. This closes a resource-exhaustion class (31-minute sentinel waits), not an auth bypass.
- **Suggested revision**: Address the concern above.

### FINDING_21: **Manifest construction** — Plan-review, decompose, voter, and assessor slots use `jq -nc --arg …` for NDJSON rows (safe embedding). Voter manifest still uses `printf` JSON for paths (pre-existing pattern; paths are under `$DESIGN_TMPDIR`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Manifest construction** — Plan-review, decompose, voter, and assessor slots use `jq -nc --arg …` for NDJSON rows (safe embedding). Voter manifest still uses `printf` JSON for paths (pre-existing pattern; paths are under `$DESIGN_TMPDIR`).
- **Suggested revision**: Address the concern above.

### FINDING_22: **Both-absent generic Claude paths** — Prompts are built from repo templates / `render-plan-review-prompt.sh` and validated plan paths; launches go through existing `launch-claude-review.sh` with fixed output locations under `$DESIGN_TMPDIR`. Dynamic archetype slugs remain constrained upstream by scout validation (`^[a-z][a-z0-9-]{2,40}$` in `scout-dynamic-archetypes.sh`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Both-absent generic Claude paths** — Prompts are built from repo templates / `render-plan-review-prompt.sh` and validated plan paths; launches go through existing `launch-claude-review.sh` with fixed output locations under `$DESIGN_TMPDIR`. Dynamic archetype slugs remain constrained upstream by scout validation (`^[a-z][a-z0-9-]{2,40}$` in `scout-dynamic-archetypes.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_23: **`degraded-tools-gate.sh` env fallback** — Defaults now honor `CODEX_*` / `CURSOR_*` env vars before argv overwrites. This fixes misclassification when skills export probe results (documented contract). Impact is degraded **warnings**, not permission boundaries; dispatch availability still comes from the same Step 0 flags passed to dispatchers. No new shell interpolation of untrusted input.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **`degraded-tools-gate.sh` env fallback** — Defaults now honor `CODEX_*` / `CURSOR_*` env vars before argv overwrites. This fixes misclassification when skills export probe results (documented contract). Impact is degraded **warnings**, not permission boundaries; dispatch availability still comes from the same Step 0 flags passed to dispatchers. No new shell interpolation of untrusted input.
- **Suggested revision**: Address the concern above.

### FINDING_24: **No new secrets, network calls, or auth changes** in the implementation diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **No new secrets, network calls, or auth changes** in the implementation diff. `/review` multi-phase waterfall (ungrouped phase-2/3) is unchanged except reuse removal; ReDoS/`grep -E` on caller patterns and `eval` in `collect_phase` are pre-existing. ---
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `skills/design/scripts/dispatch-plan-review-panel.sh:64-72` — `write_dynamic_prompt` still embeds scout `prompt_body` via `cat` and puts `_slug` in the prompt line. Scout validation limits slug shape; a hand-tampered `scout-plan-manifest.json` in `$DESIGN_TMPDIR` could still influence reviewer prompts (LLM prompt-injection surface). Pre-existing; not introduced by availability gating.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `scripts/dispatch-plan-voters.sh` — `printf`-built JSON for voter slots (unchanged style). Safe while paths stay under session tmpdirs; `jq` would be more robust if paths ever became externally influenced. --- **Verdict:** The branch addresses a real integrity/availability failure (missing `.done` on copied outputs, false twin reviewers) without introducing new injection, secret-handling, or trust-boundary regressions. No security blockers for merge on this lens.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/dispatch-plan-voters.sh:173-190; skills/design/scripts/dispatch-plan-assessors.sh:133-144
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Compact ALL_OUTPUT_FILES under --no-fallback breaks fixed-index mapping to Codex/Cursor paths Codex slot fails, Cursor succeeds: only Cursor path is emitted but assigned to VOTER_2/CODEX_PATH — wrong vote/assessor attribution Resolve paths by manifest output or slot, not outputs_arr index order
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: skills/design/scripts/decompose-panel-dispatch.sh:296-337
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Resolved paths indexed by manifest row while paths-file omits dropped --no-fallback slots Partial panel failure shifts _resolved_paths onto wrong archetype/vendor in panel-outputs.ndjson Match paths to manifest output/slot or keep index-aligned paths entries for failures
- **Suggested revision**: Address the concern above.

### FINDING_29: architecture: skills/design/scripts/plan-review-loop.sh:767-781
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Empty paths-file after successful --no-fallback dispatch treated as panel-failed All reviewers fail: DISPATCH_OK=true but empty paths-file → return 1 instead of degraded zero-findings per plan acceptance Treat empty paths with successful dispatch as degraded empty panel; continue to zero-findings tally
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:104-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Both-absent generic path always DISPATCH_OK without launch/structured-output checks Failed or non-TSV generic launch still publishes PANEL_PATHS_FILE; unlike decompose both-absent validation Validate launch RC and first-line/TSV contract before emitting paths; set DISPATCH_OK false on failure
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/design/scripts/dispatch-plan-review-panel.sh:90-124
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic Claude floor bypasses waterfall; hung launch can still block collect for COLLECT_TIMEOUT Long hang on launch-claude-review.sh still costs full collect timeout on floor path Document or add shorter timeout for generic floor launch
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/design/references/decompose-panel.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Companion doc not updated per plan; still describes fixed 8-slot panel and phase-2/phase-3 waterfall fallback. Operators and implementers following decompose-panel.md will expect cross-tool/Claude pad on narration-only failures; runtime uses --no-fallback and availability gating instead. Rewrite contract for availability matrix single-launch drop-on-failure and both-absent generic Claude floor; remove waterfall phase-2/phase-3 prose.
- **Suggested revision**: Address the concern above.

### FINDING_33: **architecture** `skills/design/scripts/decompose-panel-dispatch.sh:296-338` — After `--no-fallback`, `dispatch-with-waterfall.sh` writes `ALL_OUTPUT_FILES_PATH` with **only succeeded slots** (manifest order, gaps omitted; see `scripts/dispatch-with-waterfall.sh:450-478` and `scripts/dispatch-with-waterfall.md:26-32`). `decompose-panel-dispatch.sh` still walks **every** manifest row and binds `_resolved_paths[$_i]` by manifest index (`_i` increments per row). When any earlier slot is dropped (tool absent, phase-1 failure, or `--require-result-pattern` miss), every later row is paired with the wrong output path, so `panel-outputs.ndjson` can mark the wrong archetype `ok` or `missing` and the aggregator can consume mis-attributed content. **Suggested fix:** Stop index-aligned joining. Build each panel row by matching manifest `output` (and phase-2/phase-3 suffix variants if needed) against paths-file lines / `REVIEWER_FILE` realpaths, or emit only from the paths-file and derive archetype from slot/output naming; treat unmatched manifest rows as `missing`/`dropped` without shifting indices.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **architecture** `skills/design/scripts/decompose-panel-dispatch.sh:296-338` — After `--no-fallback`, `dispatch-with-waterfall.sh` writes `ALL_OUTPUT_FILES_PATH` with **only succeeded slots** (manifest order, gaps omitted; see `scripts/dispatch-with-waterfall.sh:450-478` and `scripts/dispatch-with-waterfall.md:26-32`). `decompose-panel-dispatch.sh` still walks **every** manifest row and binds `_resolved_paths[$_i]` by manifest index (`_i` increments per row). When any earlier slot is dropped (tool absent, phase-1 failure, or `--require-result-pattern` miss), every later row is paired with the wrong output path, so `panel-outputs.ndjson` can mark the wrong archetype `ok` or `missing` and the aggregator can consume mis-attributed content. **Suggested fix:** Stop index-aligned joining. Build each panel row by matching manifest `output` (and phase-2/phase-3 suffix variants if needed) against paths-file lines / `REVIEWER_FILE` realpaths, or emit only from the paths-file and derive archetype from slot/output naming; treat unmatched manifest rows as `missing`/`dropped` without shifting indices.
- **Suggested revision**: Address the concern above.

### FINDING_34: **architecture** `scripts/dispatch-plan-voters.sh:173-191` — Voter 2/3 paths are taken from `outputs_arr[$_wf_idx]` where `_wf_idx` advances once per **available** tool, assuming `ALL_OUTPUT_FILES` has one entry per manifest row in manifest order. Under `--no-fallback`, `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` are compact lists of **only successful** slots (`scripts/dispatch-with-waterfall.sh:450-463`). If Codex is manifest-first and fails while Cursor succeeds, `outputs_arr[0]` is Cursor’s file but is assigned to `VOTER_2_PATH` (Codex), so a failed external voter can inherit the sibling’s ballot path while `-s` checks may still pass on the wrong file. **Suggested fix:** Bind `VOTER_2_*` / `VOTER_3_*` by scanning paired `outputs_arr`/`tools_arr` for `tool==codex` or `tool==cursor` (or parse `ALL_OUTPUT_FILES_PATH` lines and match by slot/tool metadata), not by sequential index among “available” tools.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **architecture** `scripts/dispatch-plan-voters.sh:173-191` — Voter 2/3 paths are taken from `outputs_arr[$_wf_idx]` where `_wf_idx` advances once per **available** tool, assuming `ALL_OUTPUT_FILES` has one entry per manifest row in manifest order. Under `--no-fallback`, `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` are compact lists of **only successful** slots (`scripts/dispatch-with-waterfall.sh:450-463`). If Codex is manifest-first and fails while Cursor succeeds, `outputs_arr[0]` is Cursor’s file but is assigned to `VOTER_2_PATH` (Codex), so a failed external voter can inherit the sibling’s ballot path while `-s` checks may still pass on the wrong file. **Suggested fix:** Bind `VOTER_2_*` / `VOTER_3_*` by scanning paired `outputs_arr`/`tools_arr` for `tool==codex` or `tool==cursor` (or parse `ALL_OUTPUT_FILES_PATH` lines and match by slot/tool metadata), not by sequential index among “available” tools.
- **Suggested revision**: Address the concern above.

### FINDING_35: **architecture** `skills/design/scripts/dispatch-plan-assessors.sh:133-144` — Same positional contract as voters: `CODEX_PATH` / `CURSOR_PATH` are filled from `outputs_arr[$_wf_idx]` in manifest order, but `--no-fallback` shortens `ALL_OUTPUT_FILES` when one assessor slot fails. A failed Codex assessor can leave Cursor’s path in `outputs_arr[0]` and assign it to `CODEX_PATH`, corrupting assessor/tally inputs. **Suggested fix:** Resolve external assessor paths by `tools_arr` identity (or paths-file + tool), mirroring the voter fix.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **architecture** `skills/design/scripts/dispatch-plan-assessors.sh:133-144` — Same positional contract as voters: `CODEX_PATH` / `CURSOR_PATH` are filled from `outputs_arr[$_wf_idx]` in manifest order, but `--no-fallback` shortens `ALL_OUTPUT_FILES` when one assessor slot fails. A failed Codex assessor can leave Cursor’s path in `outputs_arr[0]` and assign it to `CODEX_PATH`, corrupting assessor/tally inputs. **Suggested fix:** Resolve external assessor paths by `tools_arr` identity (or paths-file + tool), mirroring the voter fix.
- **Suggested revision**: Address the concern above.

### FINDING_36: **architecture** `skills/design/scripts/plan-review-loop.sh:767-782` — The loop treats an empty `PANEL_PATHS_FILE` (`-s` fails) as **panel-failed**, skips collection/voting, and returns 1. That conflicts with the branch’s stated contract: `--no-fallback` with all slots dropped leaves an empty paths-file while `DISPATCH_OK=true` (`scripts/dispatch-with-waterfall.sh:360-361`, `471-479`), and the plan calls for proceeding with zero collected reviewers / zero findings (degraded, not hard failure). The loop already has a post-collect `degraded-empty-collector` path at `1325-1330`, but it is unreachable when dispatch produces an empty paths sidecar. **Suggested fix:** When `DISPATCH_OK=true` and the paths-file is empty or missing, skip the `panel-failed` gate, run collection only if there are paths (or no-op with zero records), and route to `degraded-empty-collector` / zero-finding tally instead of `LOOP_STATUS=panel-failed`.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **architecture** `skills/design/scripts/plan-review-loop.sh:767-782` — The loop treats an empty `PANEL_PATHS_FILE` (`-s` fails) as **panel-failed**, skips collection/voting, and returns 1. That conflicts with the branch’s stated contract: `--no-fallback` with all slots dropped leaves an empty paths-file while `DISPATCH_OK=true` (`scripts/dispatch-with-waterfall.sh:360-361`, `471-479`), and the plan calls for proceeding with zero collected reviewers / zero findings (degraded, not hard failure). The loop already has a post-collect `degraded-empty-collector` path at `1325-1330`, but it is unreachable when dispatch produces an empty paths sidecar. **Suggested fix:** When `DISPATCH_OK=true` and the paths-file is empty or missing, skip the `panel-failed` gate, run collection only if there are paths (or no-op with zero records), and route to `degraded-empty-collector` / zero-finding tally instead of `LOOP_STATUS=panel-failed`.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] **PHASE2_RELAUNCH_COUNT:** Removed from `scripts/dispatch-with-waterfall.sh` stdout; no production reader in `plan-review-loop.sh`, `dispatch-plan-review-panel.sh`, or `decompose-panel-dispatch.sh` (only `COMBINED_FALLBACK_COUNT` / `FALLBACK_COUNT`). Stale mentions remain in `skills/design/scripts/dispatch-plan-review-panel.md:12` and test stubs — doc/harness drift only.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **PHASE2_RELAUNCH_COUNT:** Removed from `scripts/dispatch-with-waterfall.sh` stdout; no production reader in `plan-review-loop.sh`, `dispatch-plan-review-panel.sh`, or `decompose-panel-dispatch.sh` (only `COMBINED_FALLBACK_COUNT` / `FALLBACK_COUNT`). Stale mentions remain in `skills/design/scripts/dispatch-plan-review-panel.md:12` and test stubs — doc/harness drift only.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] **Plan-review collect path:** For non-empty shortened paths-files, `plan-review-loop.sh` collects via `--paths-file` only (`790-795`) and maps reviewers by path in `plan_review_slot_for_reviewer` (`665-704`), not by manifest index — aligned with the new contract.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **Plan-review collect path:** For non-empty shortened paths-files, `plan-review-loop.sh` collects via `--paths-file` only (`790-795`) and maps reviewers by path in `plan_review_slot_for_reviewer` (`665-704`), not by manifest index — aligned with the new contract.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] **`test-decompose-panel-dispatch.sh` “resolved-paths” case (~184-255):** Stub still writes one paths-file line per manifest row (simulating pre–`--no-fallback` density); it does not exercise dropped-slot / shortened-list alignment, so the decompose index bug above is not caught there.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **`test-decompose-panel-dispatch.sh` “resolved-paths” case (~184-255):** Stub still writes one paths-file line per manifest row (simulating pre–`--no-fallback` density); it does not exercise dropped-slot / shortened-list alignment, so the decompose index bug above is not caught there.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] **`/review` panels:** `skills/review/scripts/dispatch-panel.sh` still uses legacy multi-phase waterfall without `--no-fallback`; positional `outputs_arr` indexing there is unchanged and out of scope for this issue.
- **Reviewer**: dyn-no-fallback-protocol-output.txt
- **Concern**: - **`/review` panels:** `skills/review/scripts/dispatch-panel.sh` still uses legacy multi-phase waterfall without `--no-fallback`; positional `outputs_arr` indexing there is unchanged and out of scope for this issue.
- **Suggested revision**: Address the concern above.

### FINDING_41: **correctness** `scripts/dispatch-plan-voters.sh:180-191` — `_wf_idx` advances once per *availability* flag (`CODEX_AVAILABLE` / `CURSOR_AVAILABLE`), but `dispatch-with-waterfall.sh` is invoked with `--no-fallback`, and its `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` lists include **only succeeded** slots in manifest order (`scripts/dispatch-with-waterfall.sh:452-456`). When both externals are present and Voter 2 (codex) fails while Voter 3 (cursor) succeeds, the compacted array has a single entry (the cursor path/tool). The codex branch still consumes `outputs_arr[0]` and sets `VOTER_2_STATUS=launched` if that file is non-empty, so Cursor’s ballot is attributed to Voter 2; `_wf_idx` is then 1, so Voter 3 reads `outputs_arr[1]` (empty) and falls back to the default `cursor-vote-output.txt`, which is typically empty—Voter 3 is marked failed even though Cursor succeeded. That misroutes votes into `plan_voter_coverage_compute_effective_judges` / tally and can omit a valid third judge. **Suggested fix:** Under `--no-fallback`, do not remap paths from the compacted `ALL_OUTPUT_FILES` array (manifest paths are stable: `codex-vote-output.txt` / `cursor-vote-output.txt`). Keep `VOTER_2_PATH` / `VOTER_3_PATH` at their predeclared values, set `VOTER_*_TOOL` from availability (codex/cursor), and derive `VOTER_*_STATUS` only from `-s` on those fixed paths (and optional `tools_arr` only if you add per-slot waterfall KVs). If remapping is required, increment `_wf_idx` only when a matching succeeded entry is consumed (e.g., skip the codex branch when `outputs_arr[_wf_idx]` is empty and do not advance), or have the waterfall emit slot-keyed paths instead of a compacted list.
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - **correctness** `scripts/dispatch-plan-voters.sh:180-191` — `_wf_idx` advances once per *availability* flag (`CODEX_AVAILABLE` / `CURSOR_AVAILABLE`), but `dispatch-with-waterfall.sh` is invoked with `--no-fallback`, and its `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` lists include **only succeeded** slots in manifest order (`scripts/dispatch-with-waterfall.sh:452-456`). When both externals are present and Voter 2 (codex) fails while Voter 3 (cursor) succeeds, the compacted array has a single entry (the cursor path/tool). The codex branch still consumes `outputs_arr[0]` and sets `VOTER_2_STATUS=launched` if that file is non-empty, so Cursor’s ballot is attributed to Voter 2; `_wf_idx` is then 1, so Voter 3 reads `outputs_arr[1]` (empty) and falls back to the default `cursor-vote-output.txt`, which is typically empty—Voter 3 is marked failed even though Cursor succeeded. That misroutes votes into `plan_voter_coverage_compute_effective_judges` / tally and can omit a valid third judge. **Suggested fix:** Under `--no-fallback`, do not remap paths from the compacted `ALL_OUTPUT_FILES` array (manifest paths are stable: `codex-vote-output.txt` / `cursor-vote-output.txt`). Keep `VOTER_2_PATH` / `VOTER_3_PATH` at their predeclared values, set `VOTER_*_TOOL` from availability (codex/cursor), and derive `VOTER_*_STATUS` only from `-s` on those fixed paths (and optional `tools_arr` only if you add per-slot waterfall KVs). If remapping is required, increment `_wf_idx` only when a matching succeeded entry is consumed (e.g., skip the codex branch when `outputs_arr[_wf_idx]` is empty and do not advance), or have the waterfall emit slot-keyed paths instead of a compacted list.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] `skills/design/scripts/dispatch-plan-assessors.sh:135-144` uses the same `_wf_idx` + compacted `ALL_OUTPUT_FILES` pattern with `--no-fallback`; codex-fail / cursor-ok would mis-assign `CODEX_PATH` the same way (not in the voter focus file, but same branch regression class).
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - `skills/design/scripts/dispatch-plan-assessors.sh:135-144` uses the same `_wf_idx` + compacted `ALL_OUTPUT_FILES` pattern with `--no-fallback`; codex-fail / cursor-ok would mis-assign `CODEX_PATH` the same way (not in the voter focus file, but same branch regression class).
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] `scripts/test-dispatch-plan-voters.sh` stubs `dispatch-with-waterfall.sh` to append every manifest row to `all_outputs` even when `PLAN_VOTER_SLOT_*_STATUS=failed` (`:167-168`), so the substantive-fail case does not exercise real compacted output and would not catch the misalignment above.
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - `scripts/test-dispatch-plan-voters.sh` stubs `dispatch-with-waterfall.sh` to append every manifest row to `all_outputs` even when `PLAN_VOTER_SLOT_*_STATUS=failed` (`:167-168`), so the substantive-fail case does not exercise real compacted output and would not catch the misalignment above.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] `scripts/dispatch-plan-voters.md:16-22` still documents three-phase waterfall fallback for Voters 2–3; the script now uses availability gating and `--no-fallback` (stale doc, not a runtime bug).
- **Reviewer**: dyn-voter-index-alignment-output.txt
- **Concern**: - `scripts/dispatch-plan-voters.md:16-22` still documents three-phase waterfall fallback for Voters 2–3; the script now uses availability gating and `--no-fallback` (stale doc, not a runtime bug).
- **Suggested revision**: Address the concern above.

### FINDING_45: **risk-integration** `scripts/test-degraded-tools-gate.sh:95-100` — Case 7 (“present-only wiring”) invokes the gate with only `--codex-present` / `--cursor-present` and relies on `${CODEX_BINARY_FOUND:-unknown}` for the binary keys, but it does not clear or override `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` in the child environment. Because the harness uses `bash "$GATE"` (not `env -i`), a CI job or developer shell that exports e.g. `CODEX_BINARY_FOUND=false` will make Codex classify as `binary-missing` instead of the asserted `CODEX_STATE=ok`, causing flaky failures or false confidence when the parent env happens to match. **Suggested fix:** Prefix case 7 with explicit neutral binary env (e.g. `CODEX_BINARY_FOUND= CURSOR_BINARY_FOUND=` or `env -i PATH="$PATH" HOME="$HOME" … bash "$GATE" …`) so present-only behavior is tested independent of the runner’s inherited exports; document that contract in `scripts/test-degraded-tools-gate.md`.
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **risk-integration** `scripts/test-degraded-tools-gate.sh:95-100` — Case 7 (“present-only wiring”) invokes the gate with only `--codex-present` / `--cursor-present` and relies on `${CODEX_BINARY_FOUND:-unknown}` for the binary keys, but it does not clear or override `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` in the child environment. Because the harness uses `bash "$GATE"` (not `env -i`), a CI job or developer shell that exports e.g. `CODEX_BINARY_FOUND=false` will make Codex classify as `binary-missing` instead of the asserted `CODEX_STATE=ok`, causing flaky failures or false confidence when the parent env happens to match. **Suggested fix:** Prefix case 7 with explicit neutral binary env (e.g. `CODEX_BINARY_FOUND= CURSOR_BINARY_FOUND=` or `env -i PATH="$PATH" HOME="$HOME" … bash "$GATE" …`) so present-only behavior is tested independent of the runner’s inherited exports; document that contract in `scripts/test-degraded-tools-gate.md`.
- **Suggested revision**: Address the concern above.

### FINDING_46: **risk-integration** `scripts/degraded-tools-gate.sh:36-39`, `skills/implement/SKILL.md:437-438,455`, `skills/design/SKILL.md:152-196` — Env-var initialization fixes the prior bug where exported probe keys were ignored, but it also makes the gate sensitive to **stale or foreign exports** in the long-lived orchestrator shell. `/implement` Step 0 explicitly `export`s all four keys; `/design` Step 0 parses `CODEX_PRESENT` / `CURSOR_PRESENT` in one Bash block without exporting them, and `write-design-current-env.sh` persists only presence/availability (not `*_BINARY_FOUND`). Implement run logs already show `degraded-tools-gate.sh --skill implement` with no probe flags, relying entirely on inherited env. A later `/design` or `/review` gate in the same session can therefore classify tools using another skill’s exported values unless the orchestrator passes all four `--*` flags from the **current** `session-setup.sh` parse in that same invocation. **Suggested fix:** Treat env inheritance as a fallback only: update `scripts/degraded-tools-gate.md` and `skills/shared/external-reviewers.md` to require all four flags on every invocation (canonical example already in `external-reviewers.md:29-32`); tighten `/implement` SKILL text to match; optionally have the gate warn on stderr when any probe flag is omitted and the corresponding env var is set (detect env-only/partial calls).
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **risk-integration** `scripts/degraded-tools-gate.sh:36-39`, `skills/implement/SKILL.md:437-438,455`, `skills/design/SKILL.md:152-196` — Env-var initialization fixes the prior bug where exported probe keys were ignored, but it also makes the gate sensitive to **stale or foreign exports** in the long-lived orchestrator shell. `/implement` Step 0 explicitly `export`s all four keys; `/design` Step 0 parses `CODEX_PRESENT` / `CURSOR_PRESENT` in one Bash block without exporting them, and `write-design-current-env.sh` persists only presence/availability (not `*_BINARY_FOUND`). Implement run logs already show `degraded-tools-gate.sh --skill implement` with no probe flags, relying entirely on inherited env. A later `/design` or `/review` gate in the same session can therefore classify tools using another skill’s exported values unless the orchestrator passes all four `--*` flags from the **current** `session-setup.sh` parse in that same invocation. **Suggested fix:** Treat env inheritance as a fallback only: update `scripts/degraded-tools-gate.md` and `skills/shared/external-reviewers.md` to require all four flags on every invocation (canonical example already in `external-reviewers.md:29-32`); tighten `/implement` SKILL text to match; optionally have the gate warn on stderr when any probe flag is omitted and the corresponding env var is set (detect env-only/partial calls).
- **Suggested revision**: Address the concern above.

### FINDING_47: **risk-integration** `skills/design/SKILL.md:152-163,196`, `scripts/write-design-current-env.sh:196-199` — `/design`’s Step 0 example parse loop never binds `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND`, and `source-env.sh` does not persist them. With env inheritance, a gate call that omits `--codex-binary-found` / `--cursor-binary-found` (as case 7 models) cannot recover binary-vs-probe distinction from design session artifacts—only from shell env (often `unknown` or stale). That weakens the degraded explanation (`binary-missing` vs `probe-failed`) exactly on the skill this branch changes most. **Suggested fix:** Extend the Step 0 parse in `skills/design/SKILL.md` to capture and pass through `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` from `session-setup.sh` stdout (mirror `/implement`’s `_ib_kv_scan`), and optionally add those keys to `write-design-current-env.sh` for rehydration blocks.
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:152-163,196`, `scripts/write-design-current-env.sh:196-199` — `/design`’s Step 0 example parse loop never binds `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND`, and `source-env.sh` does not persist them. With env inheritance, a gate call that omits `--codex-binary-found` / `--cursor-binary-found` (as case 7 models) cannot recover binary-vs-probe distinction from design session artifacts—only from shell env (often `unknown` or stale). That weakens the degraded explanation (`binary-missing` vs `probe-failed`) exactly on the skill this branch changes most. **Suggested fix:** Extend the Step 0 parse in `skills/design/SKILL.md` to capture and pass through `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` from `session-setup.sh` stdout (mirror `/implement`’s `_ib_kv_scan`), and optionally add those keys to `write-design-current-env.sh` for rehydration blocks.
- **Suggested revision**: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] **risk-integration (amplified, not introduced by env change alone):** `scripts/degraded-tools-gate.sh:110-117` still tells operators that reviewer/voter panels use a per-slot “backup waterfall” (Codex→Cursor→Claude). This branch removes `--no-fallback` / availability gating for `/design` plan-review, decompose, assessors, and plan voters; the gate text is now materially misleading on interactive “Continue (degraded waterfall)” prompts even when flags/env are correct.
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **risk-integration (amplified, not introduced by env change alone):** `scripts/degraded-tools-gate.sh:110-117` still tells operators that reviewer/voter panels use a per-slot “backup waterfall” (Codex→Cursor→Claude). This branch removes `--no-fallback` / availability gating for `/design` plan-review, decompose, assessors, and plan voters; the gate text is now materially misleading on interactive “Continue (degraded waterfall)” prompts even when flags/env are correct.
- **Suggested revision**: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] **correctness:** Cases 8–9 in `scripts/test-degraded-tools-gate.sh:102-116` are adequately isolated: inline `VAR=value` assignments on the `bash "$GATE"` command line override inherited env for all four probe keys. Flag-based callers that pass all four `--codex-*` / `--cursor-*` arguments remain fully protected because the argv loop overwrites env-seeded defaults (`scripts/degraded-tools-gate.sh:42-51`).
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **correctness:** Cases 8–9 in `scripts/test-degraded-tools-gate.sh:102-116` are adequately isolated: inline `VAR=value` assignments on the `bash "$GATE"` command line override inherited env for all four probe keys. Flag-based callers that pass all four `--codex-*` / `--cursor-*` arguments remain fully protected because the argv loop overwrites env-seeded defaults (`scripts/degraded-tools-gate.sh:42-51`).
- **Suggested revision**: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] **architecture:** `scripts/degraded-tools-gate.md` was not updated in the branch diff to document env-var fallback or flag-over-env precedence; only the shell init changed. That gap increases the chance of env-only invocations without a documented contract.
- **Reviewer**: dyn-env-var-inheritance-output.txt
- **Concern**: - **architecture:** `scripts/degraded-tools-gate.md` was not updated in the branch diff to document env-var fallback or flag-over-env precedence; only the shell init changed. That gap increases the chance of env-only invocations without a documented contract.
- **Suggested revision**: Address the concern above.

