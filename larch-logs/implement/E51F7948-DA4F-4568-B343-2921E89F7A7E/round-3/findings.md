Normalizing the supplied reviewer findings into merged in-scope `FINDING_*` blocks and separate `OOS_*` blocks, with severity merged per your rules.
### FINDING_1: Both-absent generic path leaves DEGRADED_PANEL=false on failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Both-absent generic path hardcodes `DEGRADED_PANEL=false` on failure. When both externals are absent and the generic Claude launch fails, stdout emits `PANEL_STATUS=panel-failed` and `DISPATCH_OK=false` but `DEGRADED_PANEL=false`, unlike partial-drop paths and plan-review's `DEGRADED_ROUND=true` on generic failure; downstream may under-report degradation. Set `DEGRADED_PANEL` from outcome (true when usable==0 or dispatch failed); add a both-absent failure harness case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: COMBINED_FALLBACK_COUNT degradation dead under --no-fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `COMBINED_FALLBACK_COUNT > floor_half` checks are dead under `--no-fallback`. Design panels always pass `--no-fallback` so `COMBINED_FALLBACK_COUNT` is 0; operators may think fallback volume drives `DEGRADED_*` when only path-count logic matters. Remove or gate fallback-count degradation behind non-no-fallback dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: ALL_SLOTS_DROPPED KV emitted but never consumed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ALL_SLOTS_DROPPED` is emitted by `dispatch-with-waterfall.sh` but has no consumers. Callers detect all slots dropped only via empty paths-file/WARN, not the explicit KV. New dispatchers may ignore empty paths-file and assume `DISPATCH_OK=true` means at least one reviewer succeeded. Wire `ALL_SLOTS_DROPPED` into plan-review-loop/decompose (and panel) callers to set degraded flags, or remove the KV until used; alternatively document and test the empty-path contract explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Parse `ALL_SLOTS_DROPPED` in `dispatch-plan-review-panel.sh` and `decompose-panel-dispatch.sh` to set degraded flags, or document and test the empty-path contract explicitly.

### FINDING_4: Inconsistent indent in both-absent exit block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Inconsistent 2-space indent in both-absent exit block (`decompose-panel-dispatch.sh` ~197–201). Hurts readability and diverges from file style; easy to miss in review. Re-indent to 4 spaces to match the rest of the script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Unused _panel_paths on waterfall path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_panel_paths` is unused on the waterfall code path in `dispatch-plan-review-panel.sh` (~88). Dead assignment adds noise when tracing `PANEL_PATHS_FILE` wiring. Remove `_panel_paths` or use it consistently for the paths sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Unreachable CODEX/CURSOR fallback status branches on assessors
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: CODEX/CURSOR fallback status branches in `dispatch-plan-assessors.sh` (~142–143) are unreachable under `--no-fallback`. `*_TOOL` never becomes claude; fallback status labels confuse readers auditing assessor flow. Remove dead branches or restrict to legacy multi-phase paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Both-absent generic dispatch fails on missing sidecar despite valid inline output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Both-absent generic dispatch requires a `.tsv`/`.jsonl` sidecar file but `launch-claude-review` only writes inline structured text to the output file. Step 0 both externals absent; Claude returns valid inline TSV or JSON sentinel in `claude-plan-generic-output.txt` with no sidecar file; dispatch sets `DISPATCH_OK=false` and plan-review-loop panel-fails despite a valid review. After launch run `validate-research-output --write-structured` to create the sidecar or remove the sidecar-file gate and rely on collect-agent-results in Step 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Stale PHASE2_RELAUNCH_COUNT and fallback-count semantics in panel dispatch docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-review-panel.md` (and related operator docs) still reference `PHASE2_RELAUNCH_COUNT`, grouped phase-2 relaunch metering, and fallback-count-driven `DEGRADED_ROUND` after implementation moved to paths-file partial success and `--no-fallback` panels without grouped reuse. Operators, harness authors, and implementers following the doc will expect KVs and cost semantics that are never emitted, causing confusion when debugging `DEGRADED_ROUND` or WARN keys. Align with `dispatch-with-waterfall.md` and `plan-review.md`: document paths-file-based degradation, `COMBINED_FALLBACK_COUNT` and `ALL_SLOTS_DROPPED` where applicable, and remove `PHASE2_RELAUNCH_COUNT` / grouped-relaunch wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Update doc to paths-file-based degradation and remove `PHASE2_RELAUNCH_COUNT` references.
  - From cursor-specialist-plan-fidelity-output.txt: Align the doc with `dispatch-with-waterfall.md` and `plan-review.md`: --no-fallback panel, no `PHASE2_RELAUNCH_COUNT`, no grouped-relaunch wording.

### FINDING_9: Plan-review-loop harness stubs dispatch/collect; misses production regression class
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires real panel dispatch plus full plan-review-loop collect without `SENTINEL_TIMEOUT` on codex-down; harnesses stub dispatch and/or collect. A regression in production paths-file or `.done` handling could pass unit harnesses yet stall ~31 min per round in real `/design` runs. Add one integration case using real `dispatch-plan-review-panel.sh` and `collect-agent-results.sh` with stubbed external tools only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Assessor harness lacks availability-matrix and --no-fallback assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Assessor harness lacks availability-matrix and `--no-fallback` assertions required by the plan (unlike decompose/panel tests). Wrong manifest emission or missing `--no-fallback` on assessors could regress without CI failure. Mirror panel/decompose tests: manifest row counts per tool matrix, grep `--no-fallback`, empty manifest when both externals absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Absent-slot --no-fallback timing case does not exercise collect-agent-results
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Absent-slot `--no-fallback` timing case in `test-dispatch-with-waterfall.sh` (~2130–2163) does not exercise `collect-agent-results.sh`—only dispatch timing/stdout. The original bug was collector sentinel wait; this case is weaker than the keep case that runs real collect. After absent dispatch invoke `collect-agent-results.sh` on paths-file with short timeout and assert no `STATUS=SENTINEL_TIMEOUT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Reduced multi-vendor security review when externals absent or down
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Availability-gated panels and the both-absent generic Claude floor reduce independent multi-vendor security review before implement. Codex or Cursor down (or both absent) can let security archetype feedback come from one model family; correlated blind spots or prompt-influenced omissions may reach implement without a second vendor on the same lens. Keep as accepted policy but surface reduced review depth clearly at Step 0 and treat degraded panel / empty collector exits as high-risk for security-sensitive plans unless the operator explicitly continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Dropped waterfall slots can be marked ok via manifest output-path fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `--no-fallback`, a slot fails pattern/status and is omitted from `ALL_OUTPUT_FILES_PATH`, but `panel-outputs` still read the manifest output file; if that file contains `## Recommendation` the row becomes `status=ok` and usable increments, contradicting the drop. Treat slots not present in `ALL_OUTPUT_FILES_PATH` as missing/dropped; only validate `## Recommendation` for paths listed in the compact paths-file; remove manifest-path fallback when paths-file is non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: STATIC_DISPATCH_OK stays true when all --no-fallback static slots fail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `STATIC_DISPATCH_OK` stays true when all `--no-fallback` phase-1 slots fail (`dispatch-with-waterfall.sh` ~396–408). Consumers checking only `STATIC_DISPATCH_OK` may treat a fully failed static panel as healthy even though `final_outputs` are all empty. After `NO_FALLBACK` collection, set `static_dispatch_ok=false` when every static-index slot has empty `final_outputs` (align with `DEGRADED_ROUND` path-count logic).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Step 0 Continue option mislabels degraded waterfall vs availability-gated drop
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0 `AskUserQuestion` still offers Continue (degraded waterfall) while `degraded-tools-gate.sh` explains `/design` uses availability-gated `--no-fallback` without cross-tool or Claude padding. Interactive operators may believe they are opting into per-slot backup waterfall on plan-review/decompose/voter paths that no longer perform it. Rename the continue option for design (and mirror in `external-reviewers.md` design branch) to match the gate explanation (reduced panel / single-launch drop).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Both-absent generic Claude may not use Opus tier per plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan specifies generic Claude (Opus) for both-absent floor; implementation uses `launch-claude-review.sh` without an Opus-specific agent or model flag. If the session default model is not Opus, the both-absent reviewer floor does not match the plan’s stated model tier. Pass explicit Opus agent/model args consistent with other plan-review Claude launches, or update plan/docs to session-default Claude.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_17: Voter 2/3 success inferred only from fixed manifest paths, not collector final paths
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: important
- **Concern**: Voter 2/3 success is inferred only from `[[ -s "$VOTER_2_PATH" ]]` / `[[ -s "$VOTER_3_PATH" ]]` on the fixed manifest paths (`codex-vote-output.txt`, `cursor-vote-output.txt`). The branch removed parsing of `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` from `waterfall_output`, but `dispatch-with-waterfall.sh` still records the collector’s final path in those keys (e.g. when `collect-agent-results.sh` empty-output retry succeeds with `REVIEWER_FILE=<orig>-retry.txt` while the manifest path stays empty). In that case the waterfall run can succeed while this script marks the slot `failed`, omits it from `plan-voter-paths.txt`, and under-counts judges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Restore availability-indexed parsing of `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` (or read `ALL_OUTPUT_FILES_PATH`) to set `VOTER_*_PATH` and tool before the `-s` guards; keep `--no-fallback` on the waterfall invocation.

### FINDING_18: Voter harness still expects fallback status that implementation cannot emit
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: important
- **Concern**: The `status2`/`status3` matrix in `test-dispatch-plan-voters.sh` (~362–368) still requires `VOTER_2_STATUS=fallback` / `VOTER_3_STATUS=fallback`, but `dispatch-plan-voters.sh` (~169–180) hardcodes `VOTER_2_TOOL=codex` and `VOTER_3_TOOL=cursor`, so the `VOTER_*_TOOL == claude` → `fallback` promotion can never run; a stub “fallback” run will emit `launched` instead and the harness should fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Drop `fallback` from that matrix (expect `launched` when the stub writes substantive output) or reintroduce tool attribution from waterfall stdout before status derivation; sync `scripts/dispatch-plan-voters.md` and `skills/design/references/plan-review.md` with the no-Claude-pad voter contract.

### FINDING_19: Multi-round integration fixture weakly pins convergence KV contract
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: important
- **Concern**: The canonical cross-script multi-round fixture in `test-design-multi-round-integration.sh` (round 1: six `latent` TSV rows; round 2: one `nit` row) is the main integration proof that streak/two-round threshold logic is gone, but it only checks that `.step3-plan-review-result.env` contains `NIT_ACCEPTED_COUNT` and `NON_NIT_ACCEPTED_COUNT` keys, not their values or `REASON=converged`. A regression that converged on the wrong round or still counted six non-nit on round 2 would keep `LOOP_STATUS=converged` and `ROUNDS_COMPLETED=2` while breaking the new nit-exclusion contract. The stub still sets `COMBINED_FALLBACK_COUNT=1` on round 1 and requires `DEGRADED_PANEL=1` in round-1 `round-summary.env`, even though six accepted latent findings already yield `NON_NIT_ACCEPTED_COUNT > 5` and would force a second round without panel degradation—so the harness validates convergence mostly through a legacy degradation signal, not the non-nit cap that replaced `LARCH_DESIGN_CONVERGENCE_THRESHOLD` under post-`--no-fallback` production panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: After the main `run_loop_fixture` call, assert final stdout or `.step3-plan-review-result.env` has `REASON=converged`, `NIT_ACCEPTED_COUNT=1`, `NON_NIT_ACCEPTED_COUNT=0`, and round-2 `round-summary.env` matches; optionally assert round-1 summary has `NON_NIT_ACCEPTED_COUNT` above 5 (or `LOOP_STATUS` empty / non-converged) so the “six latent blocks, one nit converges” architecture is pinned at the integration layer, mirroring `skills/design/scripts/test-plan-review-loop.sh:2091-2092` and `7015-7018` in the diff.
  - From dyn-convergence-threshold-removal-output.txt: Add a variant (or simplify the primary case) with `COMBINED_FALLBACK_COUNT=0`, assert round-1 does not converge with six latent (`NON_NIT_ACCEPTED_COUNT=6`, no terminal `LOOP_STATUS=converged` in round-1 summary), then assert round-2 nit convergence with the KV values above—aligning the integration architecture with post-`--no-fallback` behavior.

### FINDING_20: No harness for rejected --convergence-threshold flag on plan-review-loop
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: important
- **Concern**: Removal of `--convergence-threshold` is enforced only by an `absent` check on `skills/design/SKILL.md`; the diff drops the old invalid-flag harness case from `test-plan-review-loop.sh` without replacing it. `plan-review-loop.sh` now rejects the flag via the generic unknown-option path (~89), but CI does not document that migration surface for forked callers or wrappers still passing the flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Add a small harness case (design structure or `test-plan-review-loop.sh`) that invokes `plan-review-loop.sh` with minimal required args plus `--convergence-threshold 3` and expects exit `2`, matching the prior fail-closed pin noted in implement review logs.

### FINDING_21: /review and /research gate skills allow stale env when flags omitted
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: important
- **Concern**: The branch makes `scripts/degraded-tools-gate.sh` honor `CODEX_*` / `CURSOR_*` from the environment when argv flags are omitted (lines 36–68), while `skills/shared/external-reviewers.md` and `/design` / `/implement` Step 0 were tightened to require explicit `--codex-binary-found` / `--codex-present` / etc. `/review` and `/research` still tell the orchestrator to invoke the gate “with the … values from the session-setup output” without the same “do not omit flags” wording. In a long-lived shell where Step 0 exports linger, a follow-up `/review` or `/research` run that calls the gate with only `--skill` can classify from stale env (false `DEGRADED=false` or false `DEGRADED=true`). Warnings go through `larch_err` to stderr; agents that only parse stdout KV never see them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Mirror the `/design` / `/implement` gate bullet in `skills/review/SKILL.md` and `skills/research/SKILL.md` (explicit four flags from the current Step 0 parse in the same Bash block, no env-only inheritance), and add a harness case that simulates stale exports plus flag omission to lock the failure mode.

### FINDING_22: Missing flag-over-env precedence regression in degraded-tools-gate harness
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: important
- **Concern**: `test-degraded-tools-gate.sh` cases 8–9 cover env-only invocation and cases 7/7b cover present-only + cleared binary env, but there is no regression for flag-over-env precedence: env `CODEX_PRESENT=false` with `--codex-present true` should yield `CODEX_STATE=ok` and no env-inheritance WARNING. Without that case, a future argv-order or `_SET` regression could reintroduce silent misclassification on the path `/design` and `/implement` now depend on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Add a case that exports contradictory env, passes explicit flags matching the intended probe, captures `2>&1`, asserts the flag-side states and `assert_not_contains` for all four WARNING lines.

### OOS_1: [OUT_OF_SCOPE] Branch bundles #3265 convergence work with #3266 panel availability work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-convergence-threshold-removal-output.txt
- **Severity**: latent
- **Concern**: Branch bundles unrelated design-loop changes: convergence-threshold/streak removal and `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` (#3265) with availability-gated panels and `fallback_group` removal (#3266). Large unrelated diff surface in shared design CI shards (`plan-review-loop.sh`, `review-and-fix.sh`) increases merge/review risk, splits review accountability, and makes it easy to ship a partial revert of one policy while believing the plan is satisfied. The attached `larch:plan` covers only panel availability work, not the convergence migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-convergence-threshold-removal-output.txt: Split into separate PRs or extend the plan/acceptance block to include the convergence migration explicitly (caller sweep, docs, harnesses, CHANGELOG) so architecture review and release notes treat both as in-scope.

### OOS_2: [OUT_OF_SCOPE] Unused cp failure stub in waterfall harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `cp` failure stub in `scripts/test-dispatch-with-waterfall.sh` (~76–96) is unused after grouped-reuse test removal. Dead code only; no CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Voter fallback status branch is dead after hardcoded vendor tools
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: nit
- **Concern**: `fallback` status can never be set in `dispatch-plan-voters.sh` (~179–180) after hardcoding vendor tools; harmless at runtime but contradicts docs that still describe waterfall Claude fallback for voters 2/3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Voter harness effective_paths loop does not read statuses from output
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: nit
- **Concern**: The healthy-path `effective_paths` loop in `test-dispatch-plan-voters.sh` (~334–336) uses `$VOTER_1_STATUS` / `$VOTER_2_STATUS` / `$VOTER_3_STATUS` shell variables that are never populated from `$out`, so the assertion does not actually validate path-file line count against emitted statuses (it often passes with `effective_paths=3` by accident).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] dispatch-plan-voters.md documents obsolete three-phase waterfall
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: nit
- **Concern**: `scripts/dispatch-plan-voters.md` (~14–22) still documents three-phase waterfall and reading `ALL_OUTPUT_FILES` for externals; implementation now uses availability-gated manifest + `--no-fallback` and no longer reads those keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Runtime convergence-threshold removal appears complete (informational)
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: nit
- **Concern**: Runtime removal looks complete for the scout’s sweep: no `--convergence-threshold`, `LARCH_DESIGN_CONVERGENCE_THRESHOLD`, or `CONVERGENCE_STREAK` under `skills/` or `scripts/` (excluding tests); `skills/design/SKILL.md:941-948` passes only `--round-cap`; `plan-review-loop.sh` exports `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT`; `docs/configuration-and-permissions.md:250` describes hardcoded ≤5 non-nit convergence without streak prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Design vs implement degraded-panel gate on convergence (pre-existing policy)
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: nit
- **Concern**: `/design` convergence requires a non-degraded round (`DEGRADED_PANEL != 1`); `/implement` Step 5 in `review-and-fix.sh` applies the same `CONVERGENCE_NON_NIT_MAX=5` without a degraded-panel gate. That policy split predates this branch’s availability work and is intentional surface area, not introduced by the panel changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] Unit convergence algebra coverage is strong; gap is integration-only
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: nit
- **Concern**: Unit coverage for the new convergence algebra is strong in `test-plan-review-loop.sh` (six latent cap-hit, five non-nit one-round converge, nit-only, many-nits-plus-three-latent with explicit KV assertions); the gap is specifically the integration fixture’s value-level contract, not absence of unit tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] Verified OK: degraded-tools-gate _SET and flag-over-env behavior
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: Verified OK (no issue): `_SET` distinguishes omitted flags from explicit empty values; case 7b is consistent; cases 8–9 correctly use `2>&1` and assert WARNING substrings; flag parsing runs after env init so explicit flags win when both are supplied; `larch_err` WARNINGs go to stderr (and FD 4 under quiet init).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] Case 7 omits stderr capture; covered by 7b
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: Case 7 still omits `2>&1` and does not assert absence of WARNING; case 7b covers that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] test-degraded-tools-gate.md doc drift for cases 8–9 / 7b
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-degraded-tools-gate.md` does not yet document cases 8–9 / 7b (doc-only drift).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.

### OOS_12: [OUT_OF_SCOPE] Pre-branch run logs used env-only gate invocations
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: Pre-branch run logs show env-only `degraded-tools-gate.sh --skill implement` invocations; that pattern is now intentional for harnesses but remains risky for production orchestrators that skip explicit flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.
