### FINDING_1: correctness: skills/design/references/approval-gates.md:89-91
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Gate B passive-summary offers Continue to Gate C without routing through Step 3.6. On LOOP_STATUS=converged|cap-hit with manual_gate_b=false, operator selects Continue to Gate C and may jump to Step 4b, never running the HARD assessor even when round cursor is >= 2. Reword passive-summary to proceed Step 3.6 then 3b before Gate C; update assessor.md cross-refs.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/test-assess-plan-round.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Missing FINDING_18 test for absent plan.txt-original and append-tool-failure.sh. Regression could drop append_warning on missing original snapshot without CI catching it. Add harness case removing plan.txt-original; assert missing-snapshot KV and execution-issues Warnings entry.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-design-structure.sh:827-846
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No structural pin that all Gate B settled paths reference Step 3.6 (FINDING_5). Passive-summary Gate C jump can reappear in future edits without structural test failure. Grep approval-gates for Step 3.6 on zero-findings, apply-all, go-through-each, and passive-summary branches.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/SKILL.md:1055-1160
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate ROUND_CURSOR parse loops in Step 3 and Step 3.6. Future KV contract change might be updated in one fence only. Document single read-cursor contract or deduplicate parsing guidance.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/shared/scripts/render-assessor-prompt.sh:1-75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] render-assessor-prompt.sh omits lib-quiet conventions used by sibling scripts. Quiet mode / stderr routing may differ from voter and design scripts under automation. Adopt lib-quiet.sh and larch_err like render-voter-prompt.sh.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/scripts/test-snapshot-plan-round.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Harness omits FINDING_12 interrupt or partial temp-file atomicity check. Temp+rename regression might not be caught until production disk edge cases. Add simulated failed rename test or document deferral in test md.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/SKILL.md:1161-1186
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 3.6 writes plan-after-round-N before assess-plan-round; missing-snapshot still leaves snapshot and cursor advances on next Step 3. HARD round 2 with missing plan.txt-original: assessor skipped, plan-after-round-2 written, next re-entry advances cursor without ever running assessor for round 2. Preflight inputs before write-after, or only advance cursor when assessor completes (not on missing-snapshot).
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/design/scripts/test-assess-plan-round.sh:76-80
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required FINDING_18 coverage for missing plan snapshots and append-tool-failure is absent. Round-2 missing plan.txt-original or plan-after-round-1 could skip without logging Warnings; harness would still pass. Add fixtures per missing file; assert missing-snapshot KV, no verdict file, and execution-issues.md append (or mock append script).
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/design/scripts/test-tally-plan-assessor.sh:50-74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] FINDING_8 tuple (2,1,0) and case-insensitive parsing are not tested. Tally logic could regress on (2 BETTER, 1 TIE) or lowercase assessment lines without CI failure. Add assert_verdict for (2,1,0) and a lowercase assessor output case.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/scripts/test-snapshot-plan-round.sh:1-61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Atomic mktemp+rename under failure/interrupt (FINDING_12) is not exercised. Failed write-after could leave corrupt snapshots; next-round assessor compares wrong plans. Simulate mv/cp failure; assert destination absent and cursor unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-design-structure.sh:791-810
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing FINDING_5 Gate-B→3.6 forward-ref pin and render-final-summary.md outcome pin. Structure test passes while Gate B docs omit 3.6 links or final-summary.md omits new outcome. Grep approval-gates/SKILL for Step 3.6 forward refs; contains render-final-summary.md cancelled-assessor-worse.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/design/references/approval-gates.md:154
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Gate C section still says zero-findings goes to Step 3b; Gate B section says 3.6 first. Operators following Gate C prose may skip assessor on zero-findings HARD runs. Update Gate C When bullet to Step 3.6 → 3b; add structure pin for consistency.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/relevant-checks.sh:61-84
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Assessor script edits do not trigger dedicated test-* targets in relevant-checks. Implement Step 3 relevant-checks after assessor-only fix may skip five new harnesses until full lint. Add case patterns for assessor scripts → test-snapshot-plan-round test-dispatch-plan-assessors etc.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/design/scripts/test-dispatch-plan-assessors.sh:159-179
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No combined codex-present=false cursor-present=false waterfall test. Dual Claude replacement manifest/regression would not fail CI. Add one invocation with both externals false; assert fallback statuses.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/shared/scripts/test-render-assessor-prompt.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing test-render-assessor-prompt.md sibling per plan/script-md-siblings. Harness contract undocumented vs other four new tests. Add minimal .md sibling documenting argv and assertions.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: skills/design/references/approval-gates.md:89-91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Passive-summary Gate B path does not reference Step 3.6; unclear if assessor should run there. If required by product, converged/cap-hit HARD runs could skip quality gate with no test. Clarify intent; if in scope, update docs/SKILL and add integration test.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No direct publish test for top-level assessor verdict/snapshot files. Harvester regression might only surface in multi-round integration or E2E. Optional focused test-design-log-publish cases for assessor artifacts at tmpdir root.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: skills/design/scripts/assess-plan-round.sh:204-213
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Dispatch KV paths override tally input paths without DESIGN_TMPDIR re-anchoring. Same-UID tampering of assessor-round-N.dispatch.kv could make tally read arbitrary local files. Ignore KV path overrides or canonicalize paths under validated DESIGN_TMPDIR before tally.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/design/SKILL.md:1189
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Full assessor verdict file is printed without the untrusted-data guard used for QUALIFICATIONS_SUMMARY. External assessor REASONING in WORSE verdict could prompt-inject the orchestrating agent at Continue/Stop. Label verdict text untrusted; prefer bounded WORSE line plus QUALIFICATIONS_SUMMARY only.
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/design-log-publish.sh:239-244
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New top-level assessor artifacts are published to larch-logs with full inlined plans and assessor prose. Secrets in plans may reach committed design logs if redact-secrets misses a pattern. Exclude assessor-prompt from publish or add redaction regression tests for new basenames.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/design/scripts/assess-plan-round.sh:215-226
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fail-open degradation proceeds on panel-wide failure with only a chat warning. Operator may believe round-over-round quality was checked when EFFECTIVE_ASSESSORS=0. Keep fail-open but make 0/3 banner hard to miss or document as explicit integrity tradeoff.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/scripts/dispatch-plan-assessors.sh:148-158
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] DISPATCH_OK ignores Claude slot failure unlike plan-voters dispatch. Claude assessor fails but waterfall succeeds; tally can emit worse-majority with ASSESSOR_STATUS=ok and no degraded UX because Step 3.6 does not parse DEGRADED_PANEL_WARNING. Set dispatch_ok=false when CLAUDE_STATUS=failed and/or forward degraded panel into assessor KVs; tighten worse-majority prompt preconditions.
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/design/SKILL.md:1103-1104,1119-1121
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 3 short-circuits skip Gate B and Step 3.6 so plan-after-round snapshots and cursor advancement never occur for that pass. degraded-empty-collector or panel-failed on round 1 delays assessor until a later full Gate B settle; operators may think quality gate ran. Document in assessor.md or add best-effort write-after on HARD short-circuit paths when plan.txt exists.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/design/SKILL.md:1161-1164
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 3.6 exits 1 on write-after failure while assessor paths are otherwise fail-open. Disk or permission error after Gate B aborts the Step 3.6 fence with no assessor KVs. Warn append execution-issues skip assessor and continue to Step 3b instead of exit 1.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/design/SKILL.md:823-827
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] HARD snapshot and cursor gates use jq only; assess-plan-round has sed fallback but plan.txt-original is never written without jq. HARD run without jq never creates plan.txt-original; round 2 assessor permanently missing-snapshot skips. Share read_workflow_path sed fallback in Step 2b/3/3.6 or require jq for HARD up front.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/design/SKILL.md:1189 + skills/design/references/approval-gates.md:115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Gate B switch-to-discussion bypasses Step 3.6 and write-after. Post-review discussion re-entry keeps cursor at 1 and skips assessor for that cycle. Document contract or snapshot before switch on HARD settled plans.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: skills/design/scripts/tally-plan-assessor.sh:126-129
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Single parseable WORSE assessor yields worse-majority and operator Continue/Stop. Only one of three models returns parseable WORSE; operator sees full gate UX from 1/3 panel. Require successful>=2 for worse-majority or show explicit 1/3 banner before AskUserQuestion.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: skills/design/scripts/snapshot-plan-round.sh:86-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write-after write-once preserves first snapshot if same round re-enters Step 3.6. Resume or abnormal re-entry compares stale plan-after-round-N to updated plan.txt. Allow refresh when plan.txt is newer and no verdict exists yet.
- **Suggested revision**: Address the concern above.

### FINDING_29: code-quality: skills/design/scripts/assess-plan-round.sh:74-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] write_default_verdict QUALIFICATIONS_SUMMARY misstates dispatch/tally failures as no WORSE consensus. Operator opens assessor-verdict-round-N.env after infrastructure failure and reads misleading summary. Use explicit degraded-panel-unavailable summary text.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/references/approval-gates.md:154
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Gate C When paragraph still routes Gate B settled paths directly to Step 3b without mentioning Step 3.6. Operators maintaining approval flow from Gate C only may omit the HARD assessor between Gate B and arch diagram despite other sections requiring it. Rewrite Gate C When bullets to include Step 3.6 on HARD settled paths; document explicit bypasses (cap-reached, tally-error, etc.).
- **Suggested revision**: Address the concern above.

### FINDING_31: architecture: scripts/test-design-structure.sh:791-810
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Missing structural pin for FINDING_5 Gate B forward-references to Step 3.6 in approval-gates.md. A regression could remove Step 3.6 forward-links from Gate B prose while structure tests still pass. Add grep/contains pins on approval-gates.md for Step 3.6 on zero-findings, shared post-apply step 8, and apply settled paths.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/design/SKILL.md:1139
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] skills/design/references/approval-gates.md:89-91 SKILL.md lists only auto-apply/Apply-all/go-through-each as pre-3.6 settlements; passive-summary offers Continue to Gate C without mentioning Step 3.6. On converged/cap-hit then Gate C re-run (round >= 2), an orchestrator may skip Step 3.6 and lose write-after plus assessor dispatch. Update passive-summary and SKILL.md to require Step 3.6 before 3b for all Gate B terminal paths except Switch-to-discussion-mode.
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: skills/design/SKILL.md:1189-1210
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] QUALIFICATIONS_SUMMARY is prose-only; Step 3.6 Bash does not read the .env sidecar. WORSE-majority AskUserQuestion may omit assessor qualifications if the orchestrator skips prose instructions. Parse QUALIFICATIONS_SUMMARY from ASSESSOR_VERDICT_ENV in the Step 3.6 fence before AskUserQuestion.
- **Suggested revision**: Address the concern above.

### FINDING_34: **correctness** `skills/design/scripts/tally-plan-assessor.sh:98-105` — `add_distinct_qualification` iterates with `"${qual_worse_list[@]:-}"` under `set -euo pipefail`. That is not the repo’s Bash 3.2–safe empty-array idiom: peer scripts (`skills/design/scripts/tally-plan-review.sh:316`, `scripts/dispatch-with-waterfall.sh:355`) and regressions such as `scripts/test-collect-agent-bash32.sh` / `scripts/test-render-final-summary-bash32.sh` standardize on `"${arr[@]+"${arr[@]}"}"` because plain `"${arr[@]}"` (and, on some macOS `/bin/bash` 3.2 builds, `${arr[@]:-}`) can abort with `arr[@]: unbound variable` or `bad substitution` when the array is declared but empty. The first WORSE vote hits this loop on every run, so a portability failure kills tally before verdict files are written. **Suggested fix:** Replace the loop header with `for existing in ${qual_worse_list[@]+"${qual_worse_list[@]}"}; do` (or guard the loop with `if ((${#qual_worse_list[@]} > 0)); then … fi`), matching `tally-plan-review.sh`. Add a static grep pin and/or a `test-tally-plan-assessor-bash32` dynamic case under `/bin/bash` &lt; 4.4 mirroring `test-render-final-summary-bash32.sh`.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **correctness** `skills/design/scripts/tally-plan-assessor.sh:98-105` — `add_distinct_qualification` iterates with `"${qual_worse_list[@]:-}"` under `set -euo pipefail`. That is not the repo’s Bash 3.2–safe empty-array idiom: peer scripts (`skills/design/scripts/tally-plan-review.sh:316`, `scripts/dispatch-with-waterfall.sh:355`) and regressions such as `scripts/test-collect-agent-bash32.sh` / `scripts/test-render-final-summary-bash32.sh` standardize on `"${arr[@]+"${arr[@]}"}"` because plain `"${arr[@]}"` (and, on some macOS `/bin/bash` 3.2 builds, `${arr[@]:-}`) can abort with `arr[@]: unbound variable` or `bad substitution` when the array is declared but empty. The first WORSE vote hits this loop on every run, so a portability failure kills tally before verdict files are written. **Suggested fix:** Replace the loop header with `for existing in ${qual_worse_list[@]+"${qual_worse_list[@]}"}; do` (or guard the loop with `if ((${#qual_worse_list[@]} > 0)); then … fi`), matching `tally-plan-review.sh`. Add a static grep pin and/or a `test-tally-plan-assessor-bash32` dynamic case under `/bin/bash` &lt; 4.4 mirroring `test-render-final-summary-bash32.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] The plan calls for a Bash 3.2 portability spot-check in `skills/design/scripts/test-snapshot-plan-round.sh`, but that harness only runs `bash -n`; none of the five new assessor harnesses (`test-tally-plan-assessor.sh`, etc.) have a dedicated bash32 target like `test-render-final-summary-bash32` / `test-collect-agent-bash32`, so the `[@]:-` hazard above would not be caught on Linux CI (bash 5.x) alone.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - The plan calls for a Bash 3.2 portability spot-check in `skills/design/scripts/test-snapshot-plan-round.sh`, but that harness only runs `bash -n`; none of the five new assessor harnesses (`test-tally-plan-assessor.sh`, etc.) have a dedicated bash32 target like `test-render-final-summary-bash32` / `test-collect-agent-bash32`, so the `[@]:-` hazard above would not be caught on Linux CI (bash 5.x) alone.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] `skills/design/scripts/dispatch-plan-assessors.sh:127-130` uses `read -r -a outputs_arr <<< "$all_outputs"`; when `ALL_OUTPUT_FILES` is empty, Bash often leaves a one-element array containing `""`, so `${outputs_arr[0]:-$CODEX_PATH}` does not fall back (empty string is “set”). Downstream `-s` checks mark the slot failed, so this is degraded-path behavior rather than a Bash 4+ syntax issue, but it differs from an unset index.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - `skills/design/scripts/dispatch-plan-assessors.sh:127-130` uses `read -r -a outputs_arr <<< "$all_outputs"`; when `ALL_OUTPUT_FILES` is empty, Bash often leaves a one-element array containing `""`, so `${outputs_arr[0]:-$CODEX_PATH}` does not fall back (empty string is “set”). Downstream `-s` checks mark the slot failed, so this is degraded-path behavior rather than a Bash 4+ syntax issue, but it differs from an unset index.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] `shopt -s nocasematch` + `[[ =~ ]]` + `${BASH_REMATCH}` in `parse_assessment` (`tally-plan-assessor.sh:34-67`) matches existing repo patterns and is restored with `shopt -u` on all exit paths; `((${#qual_worse_list[@]} > 0))` and the indexed accumulation loop are safe for an empty array on Bash 3.2 once iteration uses the `+` idiom.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - `shopt -s nocasematch` + `[[ =~ ]]` + `${BASH_REMATCH}` in `parse_assessment` (`tally-plan-assessor.sh:34-67`) matches existing repo patterns and is restored with `shopt -u` on all exit paths; `((${#qual_worse_list[@]} > 0))` and the indexed accumulation loop are safe for an empty array on Bash 3.2 once iteration uses the `+` idiom.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] `snapshot-plan-round.sh`, `render-assessor-prompt.sh`, and `assess-plan-round.sh` avoid Bash 4+ constructs (`mapfile`, `declare -A`, `${var^^}`, `&>>`, namerefs) and align with `scripts/lint-bash32.sh` scope.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - `snapshot-plan-round.sh`, `render-assessor-prompt.sh`, and `assess-plan-round.sh` avoid Bash 4+ constructs (`mapfile`, `declare -A`, `${var^^}`, `&>>`, namerefs) and align with `scripts/lint-bash32.sh` scope. **Branch commits (since merge-base with `main`):** `46d880a70` Add HARD plan-quality assessor…; `45d5f575d` chore(larch-logs)…; `ad7890c72` relevant-checks fixes; `d8f1b7ce2` / `b432abe91` review feedback rounds 1–2.
- **Suggested revision**: Address the concern above.

### FINDING_39: **architecture** `skills/design/SKILL.md:1189-1195` — The Stop branch tells the orchestrator to `export ASSESSOR_ROUND_NUM="${ROUND_NUM:-}"` before the Final summary block, but `ROUND_NUM` is only set inside the Step 3.6 Bash fence (lines 1154–1160) and is not exported or persisted. `assess-plan-round.sh` emits `ROUND_NUM=N` on stdout, yet the Step 3.6 KV parse loop (lines 1172–1180) never captures it, so a separate Bash invocation for Stop + Final summary will usually see an empty `ROUND_NUM` and `patch_assessor_worse_title` will render `(round ?)` unless the agent guesses from chat context. **Suggested fix:** Extend the Step 3.6 parse loop to capture `ROUND_NUM=*`, persist it (e.g. `$DESIGN_TMPDIR/.step3.6-assessor.env`), and document a single Stop Bash block that sources that file (or re-reads the cursor) before `export ASSESSOR_ROUND_NUM=...` and the Final summary fence—matching the mechanical KV contract the plan already specifies for `assess-plan-round.sh`.
- **Reviewer**: dyn-assessor-stop-path-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:1189-1195` — The Stop branch tells the orchestrator to `export ASSESSOR_ROUND_NUM="${ROUND_NUM:-}"` before the Final summary block, but `ROUND_NUM` is only set inside the Step 3.6 Bash fence (lines 1154–1160) and is not exported or persisted. `assess-plan-round.sh` emits `ROUND_NUM=N` on stdout, yet the Step 3.6 KV parse loop (lines 1172–1180) never captures it, so a separate Bash invocation for Stop + Final summary will usually see an empty `ROUND_NUM` and `patch_assessor_worse_title` will render `(round ?)` unless the agent guesses from chat context. **Suggested fix:** Extend the Step 3.6 parse loop to capture `ROUND_NUM=*`, persist it (e.g. `$DESIGN_TMPDIR/.step3.6-assessor.env`), and document a single Stop Bash block that sources that file (or re-reads the cursor) before `export ASSESSOR_ROUND_NUM=...` and the Final summary fence—matching the mechanical KV contract the plan already specifies for `assess-plan-round.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_40: **architecture** `skills/design/SKILL.md:1189-1195` — Step 3.6’s success boundary (`mkdir … step-3.6` then “entering Step 3b”) has no “non-exiting path only” guard, unlike Step 2b.5 (line 901). It sits after the Stop prose (`exit 0`, skip cleanup/publish) but before Step 3b, while the global anti-halt rule still mandates `3.6→3b` continuation (line 30). An agent can reasonably mark Step 3.6 complete and advance to 3b/arch/Gate C after the operator chose Stop, undoing the intended early-exit architecture (no `[DESIGNED]`, no publish, preserved tmpdir). **Suggested fix:** Mirror Step 2b.5: qualify the success boundary as “on non-exiting paths (Continue, skip, or degraded-default-open)”; add an explicit Stop directive—“do not run the Step 3.6 success marker or any Step 3b+ work”; and optionally carve `3.6→Stop→Final summary` out of the anti-halt `3.6→3b` chain in line 30.
- **Reviewer**: dyn-assessor-stop-path-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:1189-1195` — Step 3.6’s success boundary (`mkdir … step-3.6` then “entering Step 3b”) has no “non-exiting path only” guard, unlike Step 2b.5 (line 901). It sits after the Stop prose (`exit 0`, skip cleanup/publish) but before Step 3b, while the global anti-halt rule still mandates `3.6→3b` continuation (line 30). An agent can reasonably mark Step 3.6 complete and advance to 3b/arch/Gate C after the operator chose Stop, undoing the intended early-exit architecture (no `[DESIGNED]`, no publish, preserved tmpdir). **Suggested fix:** Mirror Step 2b.5: qualify the success boundary as “on non-exiting paths (Continue, skip, or degraded-default-open)”; add an explicit Stop directive—“do not run the Step 3.6 success marker or any Step 3b+ work”; and optionally carve `3.6→Stop→Final summary` out of the anti-halt `3.6→3b` chain in line 30.
- **Suggested revision**: Address the concern above.

### FINDING_41: **architecture** `skills/design/SKILL.md:1161-1164` — `write-after` failure uses `exit 1` inside the Step 3.6 fence, which aborts `/design` without running the assessor fail-open path, the worse-majority Continue/Stop UX, or a cancellation Final summary. That conflicts with the assessor-as-circuit-breaker model used elsewhere (`missing-snapshot` → `ASSESSOR_STATUS=missing-snapshot`, exit 0) and leaves the operator in a hard-error state rather than a controlled Continue/Stop or skip-to-3b path. **Suggested fix:** Treat `write-after` failure like other assessor infrastructure gaps: log a Warning, emit skip/degraded KVs, and continue to Step 3b (or a documented operator prompt), reserving `exit 1` only for unrecoverable invariant violations.
- **Reviewer**: dyn-assessor-stop-path-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:1161-1164` — `write-after` failure uses `exit 1` inside the Step 3.6 fence, which aborts `/design` without running the assessor fail-open path, the worse-majority Continue/Stop UX, or a cancellation Final summary. That conflicts with the assessor-as-circuit-breaker model used elsewhere (`missing-snapshot` → `ASSESSOR_STATUS=missing-snapshot`, exit 0) and leaves the operator in a hard-error state rather than a controlled Continue/Stop or skip-to-3b path. **Suggested fix:** Treat `write-after` failure like other assessor infrastructure gaps: log a Warning, emit skip/degraded KVs, and continue to Step 3b (or a documented operator prompt), reserving `exit 1` only for unrecoverable invariant violations.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] **`render-final-summary.sh` `patch_assessor_worse_title` (lines 439–473):** Replacing line 1 of `final-summary.md` is intentional, not destructive—`render-run-summary.sh` still emits `## /design run <RUN_ID> — cancelled-assessor-worse`, and the patch swaps in the acceptance-criteria title using `$ASSESSOR_ROUND_NUM`. The main gap is upstream env handoff (first finding), not the awk rewrite itself.
- **Reviewer**: dyn-assessor-stop-path-output.txt
- **Concern**: - **`render-final-summary.sh` `patch_assessor_worse_title` (lines 439–473):** Replacing line 1 of `final-summary.md` is intentional, not destructive—`render-run-summary.sh` still emits `## /design run <RUN_ID> — cancelled-assessor-worse`, and the patch swaps in the acceptance-criteria title using `$ASSESSOR_ROUND_NUM`. The main gap is upstream env handoff (first finding), not the awk rewrite itself.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] **`render-final-summary.md` (lines 15–16):** Lists `cancelled-assessor-worse` under Step 2b.5 callers; the live Stop path is Step 3.6. Documentation drift only.
- **Reviewer**: dyn-assessor-stop-path-output.txt
- **Concern**: - **`render-final-summary.md` (lines 15–16):** Lists `cancelled-assessor-worse` under Step 2b.5 callers; the live Stop path is Step 3.6. Documentation drift only.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] **`ASSESSOR_STATUS=degraded-default-open`:** Not named in the Step 3.6 prose alongside `skipped` / `missing-snapshot`, but `assess-plan-round.sh` always pairs it with `ASSESSOR_VERDICT=not-worse`, so it cannot spuriously trigger the worse-majority prompt; a one-line prose mention would still reduce maintainer confusion.
- **Reviewer**: dyn-assessor-stop-path-output.txt
- **Concern**: - **`ASSESSOR_STATUS=degraded-default-open`:** Not named in the Step 3.6 prose alongside `skipped` / `missing-snapshot`, but `assess-plan-round.sh` always pairs it with `ASSESSOR_VERDICT=not-worse`, so it cannot spuriously trigger the worse-majority prompt; a one-line prose mention would still reduce maintainer confusion.
- **Suggested revision**: Address the concern above.

