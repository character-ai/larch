Normalized aggregator output from the supplied reviewer slots. Positive assessment in `dyn-caller-output-contracts-output.txt` (design `--no-fallback` paths “look correct”) is omitted — not a fixable finding.

### FINDING_1: COMBINED_FALLBACK_COUNT / DEGRADED_ROUND fallback branch dead under --no-fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Production always passes `--no-fallback`, so `COMBINED_FALLBACK_COUNT` stays 0 and the `DEGRADED_ROUND` fallback-count branch in `dispatch-plan-review-panel.sh` never fires; partial slot drops also do not set `DEGRADED_ROUND` when some reviewers succeed. Harness stubs may still exercise obsolete fallback-overload degradation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove or gate fallback-count degradation for no-fallback callers; align plan-review-loop and decompose-panel-dispatch; update stubs
  - From cursor-specialist-correctness-output.txt: Set `DEGRADED_ROUND` when succeeded path count < manifest slot count

### FINDING_2: decompose both-absent branch always reports DISPATCH_OK / STATIC_DISPATCH_OK true
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `decompose-panel-dispatch.sh` (both-absent generic Claude path), synthetic stdout always emits `DISPATCH_OK=true` and `STATIC_DISPATCH_OK=true` even when launch fails or output lacks `## Recommendation`, unlike `dispatch-plan-review-panel.sh` which derives `DISPATCH_OK` from launch/validation. Log parsers treating `DISPATCH_OK=true` as success can misread total panel failure (`PANEL_STATUS=panel-failed` is the main retry signal for Step 2b.5).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Mirror plan-review: derive `DISPATCH_OK` and `STATIC_DISPATCH_OK` from launch rc and `## Recommendation` validation
  - From cursor-specialist-edge-cases-output.txt: Set `DISPATCH_OK` / `STATIC_DISPATCH_OK` from the same `_status` / `usable` checks used for `PANEL_STATUS` (mirror `dispatch-plan-review-panel.sh`, which sets `DISPATCH_OK` from `_generic_dispatch_ok`).

### FINDING_3: decompose “resolved-paths” harness contradicts --no-fallback production
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-decompose-panel-dispatch.sh` still documents/asserts phase-2 fallback file resolution while production `decompose-panel-dispatch.sh` passes `--no-fallback` and cannot produce `-phase2.txt` recoveries. The test can pass while production behavior has changed, weakening regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace with drop-on-failure case or limit phase-2 resolution tests to legacy waterfall harness
  - From cursor-specialist-testing-output.txt: Replace D5 with a `--no-fallback`-aligned case (e.g., partial slot failure drops paths; or both-absent generic path in `panel-outputs.ndjson`), or delete it if redundant with new matrix cases.

### FINDING_4: floor_half hardcoded to 4 assumes eight-slot panel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `decompose-panel-dispatch.sh` uses `floor_half` hardcoded to 4 (8 slots). With one external tool present only four slots emit but degradation threshold still assumes an eight-slot panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Compute floor_half from manifest row count or remove obsolete fallback threshold

### FINDING_5: missing decompose availability-matrix harness (plan parity)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan requires decompose parity with plan-review availability matrix (codex-down → 4 cursor rows, cursor-down → 4 codex, both-present, both-absent → zero manifest rows + generic Claude). `test-decompose-panel-dispatch.sh` only updates both-present; no matrix or both-absent generic-Claude cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add four cases mirroring `test-dispatch-plan-review-panel.sh` (D8–D10): assert `decompose-slots.ndjson` row counts per probe, zero rows + `decomp-claude-generic-output.txt` on both-absent, and `grep -Fq -- '--no-fallback'` on the waterfall argv log.

### FINDING_6: stale phase-2/phase-3 comments and _match_resolved_output branches in decompose dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Comments and `_match_resolved_output` branches in `decompose-panel-dispatch.sh` imply cross-phase recovery still runs under `--no-fallback`; maintainers may assume phase-2/phase-3 fallback remains active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Simplify to compact paths-file matching only; update comments

### FINDING_7: stale decompose-panel-dispatch.sh file header (fixed 8-slot panel)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: File header still claims a fixed 8-slot dual-vendor panel instead of availability-gated emission and generic Claude floor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update header to describe present-vendor slots and generic Claude floor

### FINDING_8: inconsistent indentation in decompose both-absent launch block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Indentation in the both-absent launch block diverges from surrounding 4-space style and reduces readability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reindent to 4 spaces

### FINDING_9: [OUT_OF_SCOPE] dispatch-plan-review-panel.md still documents PHASE2_RELAUNCH_COUNT
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Contract/docs still reference `PHASE2_RELAUNCH_COUNT` and grouped phase-2 relaunches; not updated in branch. Operators may mis-debug degraded rounds vs `--no-fallback` / `COMBINED_FALLBACK_COUNT` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Sync with --no-fallback availability-gated behavior
  - From cursor-specialist-testing-output.txt: Sync the `.md` with `dispatch-with-waterfall.md` (`COMBINED_FALLBACK_COUNT` only, no grouped reuse).

### FINDING_10: [OUT_OF_SCOPE] decompose-panel-dispatch.md ties DEGRADED_PANEL to obsolete COMBINED_FALLBACK_COUNT rule
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Doc still ties `DEGRADED_PANEL` to `COMBINED_FALLBACK_COUNT > floor(8/2)` instead of `STATIC_DISPATCH_OK` and parse-status semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update to STATIC_DISPATCH_OK and parse-status semantics

### FINDING_11: plan-review-loop collects .tsv only; both-absent generic reviewer may emit .jsonl sidecar
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `CODEX_PRESENT=false` and `CURSOR_PRESENT=false`, generic reviewer can return valid structured output via `.jsonl` while collect reads only `${_rf}.tsv`. Missing `.tsv` yields empty round (no findings, skipped voting) despite successful collect status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Resolve sidecar via STRUCTURED_SIDECAR or try .jsonl after .tsv; add both-absent collect integration test

### FINDING_12: empty manifest on both-absent leaves unknown-slot attribution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: With no manifest rows on both-absent, slot mapping may attribute findings to `unknown-slot` in ballots if sidecar parsing is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Recognize claude-plan-generic-output.txt in slot mapping or add synthetic manifest row

### FINDING_13: no harness invokes real collect-agent-results.sh for --no-fallback ghost-slot paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Acceptance targets `collect-agent-results.sh` / `plan-review-loop.sh` stalling on paths listing outputs without `.done`. New tests use dispatcher `SENTINEL_TIMEOUT` wall-clock guards or collect stubs; a regression re-listing failed slots could still stall ~31 minutes undetected. Related panel/loop tests also stub collect instead of exercising real collection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one harness case: run `dispatch-with-waterfall.sh --no-fallback` with stub codex outputs (no `.done`), build the paths-file from `ALL_OUTPUT_FILES_PATH`, then call real `collect-agent-results.sh --timeout 5` and assert no `STATUS=SENTINEL_TIMEOUT` and elapsed time ≪ timeout.
  - From cursor-specialist-testing-output.txt: Either narrow acceptance docs to “stubbed collect contract” or add one loop/panel test that shells out to real `collect-agent-results.sh` (same as finding #2).

### FINDING_14: test-dispatch-plan-assessors narration case models obsolete multi-phase waterfall
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: “Narration-only cursor” harness still expects `phase2:codex` / `phase3:claude` trace lines and `DISPATCH_OK=false` from a stub simulating multi-phase retry, while production `dispatch-plan-assessors.sh` uses `--no-fallback` (drop-on-failure, no cross-tool pad). Test can pass without catching assessor regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rewrite the narrate case to expect a single failed cursor slot, `DISPATCH_OK=true`, and `DEGRADED_PANEL_WARNING=true` without phase-2/3 trace lines; assert `plan-assessor-slots.ndjson` has no `fallback_group` and only emits rows for present tools.
  - From cursor-specialist-plan-fidelity-output.txt: Rewrite case to assert drop-on-failure semantics and remove phase2/phase3 trace expectations

### FINDING_15: assessor harness lacks manifest row-count, --no-fallback argv, and fallback_group assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Availability cases cover status KVs but not manifest length (0 vs 1 vs 2), `--no-fallback` on waterfall argv, or `jq` “no fallback_group” on `plan-assessor-slots.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: After each availability invocation, assert manifest length and `jq -s 'all(.[]; has("fallback_group") | not)'`, and capture/log argv from a thin wrapper or `PLAN_ASSESSOR_TRACE` hook for `--no-fallback`.

### FINDING_16: test-no-grouped-reuse-guard symbol list incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Guard matches plan minimum symbols but not other removed artifacts (`waterfall-group-results`, `DEDUPE_REUSED`, `slot_fallback_groups`, `REUSED_INDICES_FILE`, `phase2_grouped`). Partial reintroduction could slip past.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend the symbol loop and add `grep -rn` bans for `waterfall-group-results` and `\.dedup` under `scripts/dispatch-with-waterfall.sh` only.

### FINDING_17: both-absent generic path does not require .tsv before dispatch OK
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-review-panel.sh` both-absent path validates only first non-blank line for schema/no_issues gate and does not require `${_generic_output}.tsv` exist/non-empty before writing `PANEL_PATHS_FILE`. Model satisfying first-line gate without TSV weakens voter/tally input until downstream WARN.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After launch, require `-s "${_generic_output}.tsv"` (and optionally a header row) before setting `_generic_dispatch_ok=true`, or run the same structured-reviewer validation used in `collect-agent-results.sh` before emitting the path.

### FINDING_18: waterfall silently drops manifest rows for absent tools under --no-fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `--no-fallback`, manifest rows whose `tool` is absent per `--codex-present` / `--cursor-present` are queued then dropped with empty `final_outputs` and no error. Caller gating is assumed; mismatch (e.g. Codex rows with `--codex-present false`) silently loses reviewers without loud failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After parsing the manifest, fail fast (exit 2) if any row’s `tool` is not `present_for_tool`, or emit an explicit `WARN=manifest-tool-absent` KV counted toward `DEGRADED_ROUND` in design dispatchers.

### FINDING_19: [OUT_OF_SCOPE] plan-review.md still documents phase-2/phase-3 paths in design paths-file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reference still states Phase 3 Claude outputs appear in paths-file alongside Phase 1/2; `/design` plan-review now uses `--no-fallback` and omits dropped slots. Phase 2/3 apply only to legacy multi-phase callers (e.g. `/review`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword to state that `/design` paths-files list only succeeded phase-1 outputs and that phase-2/phase-3 paths apply only to the legacy multi-phase waterfall (e.g. `/review` code panel).

### FINDING_20: [OUT_OF_SCOPE] decompose-aggregator still invokes waterfall without --no-fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `decompose-aggregator.sh` can still cross-tool/Claude-pad failed Codex slots per legacy waterfall, unlike decomposition panel `--no-fallback` profile (plan-intentional but different recovery behavior).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_21: [OUT_OF_SCOPE] degraded-tools-gate env fallbacks inherit stale CODEX_PRESENT / CURSOR_PRESENT
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New env fallbacks honor inherited `CODEX_PRESENT` / `CURSOR_PRESENT` when CLI flags omitted; stale exported values in long-lived shell/CI could skew degraded classification and panel sizing (stderr warnings only). Same-UID trust boundary; explicit-flag orchestrators unaffected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: If this becomes painful in shared CI, document “clear probe env between jobs” (as the new harness case does) or gate env reads behind an explicit opt-in.

### FINDING_22: [OUT_OF_SCOPE] test-no-grouped-reuse-guard REUSED_INDICES substring is brittle
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Guard greps `REUSED_INDICES`, which would also match a reintroduced `REUSED_INDICES_FILE` symbol.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_23: ALL_OUTPUT_FILES compaction vs legacy slot-index contract split
- **Reviewer(s)**: dyn-caller-output-contracts-output.txt
- **Severity**: important
- **Concern**: `dispatch-with-waterfall.sh` builds `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` only from non-empty `final_outputs` for all runs, while paths-file writer still emits blank lines per slot unless `--no-fallback`. `/design` callers migrated to named paths, but legacy consumers (e.g. `dispatch-code-voters.sh`) mapping `outputs_arr[0]`/`[1]` positionally can mis-bind when earlier manifest indices are empty and later ones succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-output-contracts-output.txt: Gate compaction: keep slot-index-aligned `ALL_OUTPUT_FILES`/`ALL_OUTPUT_TOOLS` (including empty placeholders) when `--no-fallback` is unset, and compact only under `--no-fallback`; or migrate `scripts/dispatch-code-voters.sh:201-209` to the same stable per-voter path + status model as `dispatch-plan-voters.sh` and stop parsing `ALL_OUTPUT_FILES` positionally.

### FINDING_24: [OUT_OF_SCOPE] assessor.md describes positional ALL_OUTPUT_TOOLS identity
- **Reviewer(s)**: dyn-caller-output-contracts-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/assessor.md` still describes tool identity from positional `ALL_OUTPUT_TOOLS`; `dispatch-plan-assessors.sh` now uses stable manifest paths and presence/`[[ -s ]]` checks.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_25: [OUT_OF_SCOPE] decompose-panel-dispatch.sh paths sidecar comment misdocuments compact matching
- **Reviewer(s)**: dyn-caller-output-contracts-output.txt
- **Severity**: nit
- **Concern**: Inline comment at 296–298 says paths sidecar is one-per-slot manifest order reflecting phase-2/phase-3 fallback; under `--no-fallback` it is a compact succeeded-path set matched by `_match_resolved_output`, not line index.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_26: test-degraded-tools-gate does not assert stderr WARNING contract
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: latent
- **Concern**: Cases 8–9 should emit four `larch_err` WARNINGs on env-only fallback, but harness captures stdout only without `2>&1`. Regression in `*_SET` tracking or WARNING predicates could pass while `degraded-tools-gate.md:39-41` contract is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-var-gate-safety-output.txt: Add harness cases that run the gate with `2>&1` merged (or capture stderr separately): assert cases 8–9 output contains all four WARNING strings; assert case 1 (all flags) and case 7 (present-only with cleared binary env) do not contain `WARNING:`.

### FINDING_27: degraded-tools-gate WARNINGs only on stderr; Step 0 may not persist them
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: latent
- **Concern**: WARNING diagnostics go through `larch_err` (stderr), not stdout KV contract. `/implement` Step 0 logging of `DEGRADED_EXPLANATION_*` to `execution-issues.md` may omit stale-env warnings when orchestrators use env-prefix invocation without flags. `*_SET` logic is sound; audit visibility is the gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-var-gate-safety-output.txt: Either extend the gate contract with optional stdout keys (e.g. `GATE_WARNINGS_BEGIN`…`END`) for autonomous logging, or update Step 0 procedures to require capturing gate stderr into `execution-issues.md` when `DEGRADED=true` or when any WARNING is present.

### FINDING_28: [OUT_OF_SCOPE] review/research SKILL.md gate invocation wording lags external-reviewers.md
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: nit
- **Concern**: `skills/review/SKILL.md` and `skills/research/SKILL.md` still describe env-value invocation without explicit “pass `--codex-*` / `--cursor-*` flags” wording added elsewhere; may keep agents on env-prefix calls (stderr-only warnings).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_29: [OUT_OF_SCOPE] degraded-tools-gate /design explanation else branch predates env change
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: nit
- **Concern**: `/design` branch of degraded explanation still documents backup waterfall for non-design skills in `else` branch; unrelated to env-var integration, stale operator text.
- **Suggested revisions (informational for voters; coder decides)**:
