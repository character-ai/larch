### FINDING_1: code-quality: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2a claims review_budget=quick skips Step 2b plan-command validation but design-postplan-emit.sh always runs invoke-plan-validator.sh. Orchestrator following SKILL may skip validation mentally or mis-debug quick runs while the driver always validates. Update Step 2a prose to match flags.md unconditional validation; scope quick to Step 3 panel only if still accurate.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: scripts/test-design-structure.sh:89-96
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan acceptance requires a negative thin-fence fixture for missing case arms; only positive assert_postplan_thin_fence on SKILL.md exists. Regressions that delete the *) default-abort arm may not fail CI until runtime. Add self-test temp fixture missing an arm or *) and assert assert_postplan_thin_fence fails.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/plan-review-loop.sh:845-862
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] partition_requested parsing duplicates json_boolean_or_sed in design-postplan-emit.sh. Future jq/sed or quoted-boolean handling may diverge between merged driver and plan-review-loop. Extract shared json_boolean_or_sed helper and source from both scripts.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/plan-review-loop.sh:847-849
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] skills/design/scripts/design-postplan-emit.sh:297-322 Nonfatal check-plan-size rc 2/3 warn/log/append path is copy-pasted between driver and plan-review-loop. One site may change suppression or log paths without the other. Extract shared nonfatal plan-size warning helper used by both call sites.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/design/SKILL.md:874
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Intermediate prose still references completing standalone Step 2b.5 after plan write on the merged clean path. Operators may search for Step 2b.5 steps that no longer run after a clean merged emit. Reword to merged driver completion; reserve Step 2b.5 for retained callers only.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] skills/design/scripts/design-postplan-emit.sh Unconditional validator is intentional per flags.md and tests but contradicts long-standing SKILL quick-skip guidance. Unexpected validator latency or behavior change on SIMPLE/quick design runs without doc update. Confirm product intent; document behavior change or restore quick skip in driver if required.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/SKILL.md:1124
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 3.5 still requires standalone Step 2b.5 after every design-postplan-emit re-emit and Step 2b.5 return before Step 3.6, contradicting merged --with-plan-size Gate B flow in approval-gates.md. On Gate B clean rc 0 or post-display rc 12/13, orchestrator may run standalone Step 2b.5 again, duplicating plan-size checks and hard/partition prompts. Rewrite Step 3.5 and related Step 3 bullets to match approval-gates.md: merged --with-plan-size fence owns clean/hard/partition; standalone Step 2b.5 only on Override/retained paths.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/SKILL.md:1096
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 3 prose says Gate B runs design-postplan-emit.sh without --with-plan-size after plan revision. Orchestrator runs legacy emit, misses rc 10/12/13 mapping and merged plan-size integration after Gate B edits. Change prose to design-postplan-emit.sh --with-plan-size and reference the Step 2b thin-fence rc case arms.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/design/SKILL.md:874
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Step 2b intro still says to continue after standalone Step 2b.5 completes, but initial clean path completes sentinels inside merged rc 0 without calling Step 2b.5 procedure. Agent may invoke standalone Step 2b.5 before Step 3 on every run, duplicating work. Reword to continue after merged driver fence settles (rc 0 or non-exiting Split/Override completion).
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-design-structure.sh:89-126
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan requested postplan thin-fence negative fixture for missing *) arm; only Step 2b gets full assert_postplan_thin_fence, Gate B/discussion get partial contains pins. Future regression dropping rc 11 or *) on a merged site may slip through CI. Add run_postplan_thin_fence_self_tests negative cases and optionally scope assert_postplan_thin_fence to Gate B/discussion regions.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/design/scripts/design-postplan-emit.sh:492-518
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Legacy non-flag mode now always validates; review_budget=quick skip and --force-validate were removed (test case 4). Quick-tier runs always validate plan commands, changing behavior vs main and vs plan acceptance wording about unchanged legacy contract. Document as intentional in acceptance, or restore quick-skip for non--with-plan-size callers only.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-design-structure.sh:89-129
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required negative self-test for assert_postplan_thin_fence is missing. Helper can regress (e.g., drop mandatory 10) or accept fixtures missing *) without CI failure, unlike Step 3.6 thin-fence self-tests. Add run_postplan_thin_fence_self_tests with fixtures missing one rc arm and missing *) ; expect failure.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-design-structure.sh:560-627
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Full assert_postplan_thin_fence runs only on Step 2b; Gate B/discussion pins are prose substring checks. Harness passes when approval-gates/discussion only mention case arms in narrative, even if orchestrator never implements merged fences at those sites. Scope assert_postplan_thin_fence to each merged site region or add exhaustive site-specific structural pins.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-design-structure.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Site-aware hard prompts and decompose-panel non-exiting Split-return sentinel rules are not structurally pinned per plan. Prompt edits could drop Override at Gate B or omit step-2b.5 writes on Refine/Continue without failing make test-design-structure. Grep-pin Split/Cancel vs Split/Override/Cancel per site and decompose-panel Non-exiting Split returns block.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/design/scripts/test-design-postplan-emit.sh:973-984
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Merged-mode harness tests plan-size rc2 nonfatality but not rc3. rc3 handling in design-postplan-emit/plan-review-loop is untested though plan treats rc2/rc3 symmetrically. Add stubbed rc3 cases mirroring D22/plan-review-loop rc2 coverage.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/test-design-postplan-emit.sh:973-984
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] D22 does not assert execution-issues.md append on plan-size rc2. Regression could drop execution-issues logging while still passing harness via validation log + WARN display only. Assert append-tool-failure invocation or execution-issues.md Warnings content after rc2.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/design/references/approval-gates.md:157-158
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Prose delegates to Step 2b case arms despite different rc0/rc12 site semantics. Orchestrator copying Step 2b fence at Gate B/discussion can write wrong sentinels or route to Step 3 instead of Gate A/3.6. Pin site-specific rc arms in structure tests or duplicate scoped fences per site.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-design-structure.md:3831-3833
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc omits assert_postplan_thin_fence coverage. Contributors may not know postplan thin-fence pins exist or lack self-tests. Document assert_postplan_thin_fence and planned negative fixtures in test-design-structure.md.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/design/SKILL.md:1124
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 3.5 Gate B prose still mandates standalone Step 2b.5 after every design-postplan-emit re-emit, contradicting merged --with-plan-size contract in approval-gates.md and Step 2b.5. Gate B Apply-all re-emit runs design-postplan-emit --with-plan-size (rc 0/12/13 handled), then orchestrator reads Step 3.5 and runs standalone Step 2b.5 again—duplicate plan-size work, wrong sentinel order, or Override/hard prompt at wrong site. Rewrite Step 3.5 to match approval-gates §Shared post-apply: merged fence + Step 2b case arms; standalone Step 2b.5 only on Override-after-defects; rc 0 → step-2b.5 sentinel → Step 3.6.
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 2a still documents review_budget quick-skip for Step 2b validation, but run-params no longer carries review_budget and design-postplan-emit always validates. Orchestrator treats SIMPLE/quick runs as validation-skipped; plan proceeds to review with unvalidated plan commands, or operator debugs nonexistent quick path. Remove review_budget gating prose from Step 2a; document unconditional validation via merged driver; align Step 5c references.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/design/references/approval-gates.md:157-158
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Gate B merged post-plan flow is prose-only (delegate Step 2b case arms); no structure-test thin-fence pin on that region. Gate B re-emit omits rc 10 handler or default-abort * arm; defects-found or unexpected rc silently continues toward Step 3.6 with bad plan.txt. Add region-scoped assert_postplan_thin_fence for Gate B/discussion or a shared fenced snippet duplicated in references.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/scripts/design-postplan-emit.sh:47-58
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Partition flag parsing in merged mode differs from plan-review-loop.sh partition parsing. Corrupt/hand-edited run-params with string "true" triggers LOOP_STATUS=plan-size-trigger in review loop but not rc 13 in merged Gate B path—--partition behavior inconsistent. Extract shared json_boolean_or_sed helper and use in plan-review-loop.sh.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/design/SKILL.md:889-936
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 2b thin-fence case arms for rc 10/12/13 do not stop shell flow; continuation relies on prose after the fence. Anti-halt continuation after fence with _postplan_rc=10 jumps to Step 3 without Fix/Override/Cancel validator handling. Add explicit "halt unless rc 0 or completed Split/Override" guard prose, or separate fenced handlers per rc class.
- **Suggested revision**: Address the concern above.

### FINDING_24: code-quality: skills/design/SKILL.md:1096
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Gate B summary line references design-postplan-emit.sh without --with-plan-size. Minor orchestrator confusion on Gate B re-emit argv. Change to design-postplan-emit.sh --with-plan-size.
- **Suggested revision**: Address the concern above.

### FINDING_25: **correctness** `skills/design/references/decompose-panel.md:119-125` — Section 6’s unanimous **Continue** path says only “return to the caller (no filing)” and never writes `.completed/step-2b.5` (or initial-site `.completed/step-2b`), yet §9 (line 195) and `skills/design/SKILL.md:941` require no-split **Continue** to update those sentinels before resuming. An orchestrator that follows §6 literally will leave Step 2b.5 incomplete and can replay plan-size work on pause/resume. **Suggested fix:** In §6, mirror §9/Refine: on **Continue**, `mkdir -p "$DESIGN_TMPDIR/.completed"`, write/update `: > "$DESIGN_TMPDIR/.completed/step-2b.5"`, and for initial-site callers also `: > "$DESIGN_TMPDIR/.completed/step-2b"`, then return to the caller.
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - **correctness** `skills/design/references/decompose-panel.md:119-125` — Section 6’s unanimous **Continue** path says only “return to the caller (no filing)” and never writes `.completed/step-2b.5` (or initial-site `.completed/step-2b`), yet §9 (line 195) and `skills/design/SKILL.md:941` require no-split **Continue** to update those sentinels before resuming. An orchestrator that follows §6 literally will leave Step 2b.5 incomplete and can replay plan-size work on pause/resume. **Suggested fix:** In §6, mirror §9/Refine: on **Continue**, `mkdir -p "$DESIGN_TMPDIR/.completed"`, write/update `: > "$DESIGN_TMPDIR/.completed/step-2b.5"`, and for initial-site callers also `: > "$DESIGN_TMPDIR/.completed/step-2b"`, then return to the caller.
- **Suggested revision**: Address the concern above.

### FINDING_26: **correctness** `skills/design/SKILL.md:636` — The Step 1e Gate A optional-trailer re-emit contract documents only `_postplan_rc=10`, Override→retained Step 2b.5, and `_postplan_rc=0`→`step-2b.5`. It omits `_postplan_rc=12`/`13` Split handling and non-exiting Split-return sentinel writes that `skills/design/references/discussion-rounds.md:126` specifies for the same `--with-plan-size` fence. Step 1e is a separate entry point after discussion rewrites; abbreviated prose here can drop Split sentinels even though discussion-round2 is complete elsewhere. **Suggested fix:** Extend line 636 to match discussion-round2: rc12/13→Split-path (site-aware hard prompt), non-exiting Refine/no-split Continue→write/update `step-2b.5` (and initial-site `step-2b` where applicable), then return to Gate A.
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:636` — The Step 1e Gate A optional-trailer re-emit contract documents only `_postplan_rc=10`, Override→retained Step 2b.5, and `_postplan_rc=0`→`step-2b.5`. It omits `_postplan_rc=12`/`13` Split handling and non-exiting Split-return sentinel writes that `skills/design/references/discussion-rounds.md:126` specifies for the same `--with-plan-size` fence. Step 1e is a separate entry point after discussion rewrites; abbreviated prose here can drop Split sentinels even though discussion-round2 is complete elsewhere. **Suggested fix:** Extend line 636 to match discussion-round2: rc12/13→Split-path (site-aware hard prompt), non-exiting Refine/no-split Continue→write/update `step-2b.5` (and initial-site `step-2b` where applicable), then return to Gate A.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `skills/design/SKILL.md:1087` — The retained `LOOP_STATUS=plan-size-trigger` branch writes `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` on Refine/no-split Continue and Override/clean, but never writes initial-site `.completed/step-2b` before entering Split or on non-exiting return, despite the plan acceptance criteria and `skills/design/references/decompose-panel.md:195` (“retained Step 3 `LOOP_STATUS=plan-size-trigger` paths”). Retained Step 2b.5 hard/partition Split entry also lacks a pre-Split `step-2b` write for this caller. After Step 3 triggers plan-size from `plan-review-loop.sh`, only `step-2b.5` may be touched while `step-2b` stays stale/missing, so resume can replay Step 2b. **Suggested fix:** In the Step 3 branch matrix and retained Step 2b.5 Split entry prose, require initial-site `plan-size-trigger` paths to write `: > "$DESIGN_TMPDIR/.completed/step-2b"` before Split handling and again with `step-2b.5` on Refine/no-split Continue (matching initial merged rc12/rc13 semantics).
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1087` — The retained `LOOP_STATUS=plan-size-trigger` branch writes `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` on Refine/no-split Continue and Override/clean, but never writes initial-site `.completed/step-2b` before entering Split or on non-exiting return, despite the plan acceptance criteria and `skills/design/references/decompose-panel.md:195` (“retained Step 3 `LOOP_STATUS=plan-size-trigger` paths”). Retained Step 2b.5 hard/partition Split entry also lacks a pre-Split `step-2b` write for this caller. After Step 3 triggers plan-size from `plan-review-loop.sh`, only `step-2b.5` may be touched while `step-2b` stays stale/missing, so resume can replay Step 2b. **Suggested fix:** In the Step 3 branch matrix and retained Step 2b.5 Split entry prose, require initial-site `plan-size-trigger` paths to write `: > "$DESIGN_TMPDIR/.completed/step-2b"` before Split handling and again with `step-2b.5` on Refine/no-split Continue (matching initial merged rc12/rc13 semantics).
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `skills/design/SKILL.md:941-943` — Merged initial `_postplan_rc=12` documents Split and non-exiting Split returns but not **Cancel**. The bash fence already writes `.completed/step-2b` (lines 916-918) without `step-2b.5`; line 943 then says continue to Step 3 after “non-exiting Split/Override paths,” with no terminal Cancel arm. Cancel should mirror retained Step 2b.5 hard-branch semantics (`SUMMARY_OUTCOME=cancelled-plan-size-hard`, Final summary, exit 0) and must not fall through toward Step 3 with only `step-2b` set. Gate B merged rc12 in `skills/design/references/approval-gates.md:158` has the same Cancel gap. **Suggested fix:** Add explicit Cancel arms for merged rc12 (initial, discussion, Gate B): export `SUMMARY_OUTCOME=cancelled-plan-size-hard`, run Final summary, exit 0; do not proceed to Step 3/3.6. Optionally touch `step-2b.5` on terminal Cancel for sentinel symmetry.
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:941-943` — Merged initial `_postplan_rc=12` documents Split and non-exiting Split returns but not **Cancel**. The bash fence already writes `.completed/step-2b` (lines 916-918) without `step-2b.5`; line 943 then says continue to Step 3 after “non-exiting Split/Override paths,” with no terminal Cancel arm. Cancel should mirror retained Step 2b.5 hard-branch semantics (`SUMMARY_OUTCOME=cancelled-plan-size-hard`, Final summary, exit 0) and must not fall through toward Step 3 with only `step-2b` set. Gate B merged rc12 in `skills/design/references/approval-gates.md:158` has the same Cancel gap. **Suggested fix:** Add explicit Cancel arms for merged rc12 (initial, discussion, Gate B): export `SUMMARY_OUTCOME=cancelled-plan-size-hard`, run Final summary, exit 0; do not proceed to Step 3/3.6. Optionally touch `step-2b.5` on terminal Cancel for sentinel symmetry.
- **Suggested revision**: Address the concern above.

### FINDING_29: **correctness** `skills/design/SKILL.md:978-985` — Refine sentinel prose limits the extra `.completed/step-2b` write to “initial-site **merged** Split returns,” excluding retained Step 3 `plan-size-trigger` Refine (see finding above). Line 985 then says write `step-2b.5` “before entering Step 3” on **any** non-exiting return, while line 984 routes Gate B returns to Step 3.6. That wording can send Gate B Split Refine/no-split Continue to Step 3 instead of 3.6 after sentinel writes. **Suggested fix:** Scope line 985 by caller (initial→Step 3, Gate B→Step 3.6, Step 3 plan-size-trigger Refine→Gate A). Extend line 978’s `step-2b` rule to retained initial-site `plan-size-trigger` Refine/Continue, not only merged callers.
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:978-985` — Refine sentinel prose limits the extra `.completed/step-2b` write to “initial-site **merged** Split returns,” excluding retained Step 3 `plan-size-trigger` Refine (see finding above). Line 985 then says write `step-2b.5` “before entering Step 3” on **any** non-exiting return, while line 984 routes Gate B returns to Step 3.6. That wording can send Gate B Split Refine/no-split Continue to Step 3 instead of 3.6 after sentinel writes. **Suggested fix:** Scope line 985 by caller (initial→Step 3, Gate B→Step 3.6, Step 3 plan-size-trigger Refine→Gate A). Extend line 978’s `step-2b` rule to retained initial-site `plan-size-trigger` Refine/Continue, not only merged callers.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] `scripts/test-design-structure.sh` adds `assert_postplan_thin_fence` for Step 2b and pins rc0 `step-2b.5`, but the plan’s broader sentinel pins (initial rc12 Split entry `step-2b`, Refine/no-split Continue pairs, Gate B Override, decompose-panel §6 Continue, Step 1e rc12/13) are not structurally enforced—only dispatch anchors in decompose-panel are checked (~lines 1262-1267). Regression risk for the gaps above remains prompt-side only.
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - `scripts/test-design-structure.sh` adds `assert_postplan_thin_fence` for Step 2b and pins rc0 `step-2b.5`, but the plan’s broader sentinel pins (initial rc12 Split entry `step-2b`, Refine/no-split Continue pairs, Gate B Override, decompose-panel §6 Continue, Step 1e rc12/13) are not structurally enforced—only dispatch anchors in decompose-panel are checked (~lines 1262-1267). Regression risk for the gaps above remains prompt-side only.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Initial Step 2b’s inline bash fence correctly writes both sentinels on rc0 and `step-2b` on rc12/rc13 before Split; rc10 Fix-and-retry and rc11 pause-save paths look consistent with the thin-fence contract.
- **Reviewer**: dyn-sentinel-state-machine-output.txt
- **Concern**: - Initial Step 2b’s inline bash fence correctly writes both sentinels on rc0 and `step-2b` on rc12/rc13 before Split; rc10 Fix-and-retry and rc11 pause-save paths look consistent with the thin-fence contract.
- **Suggested revision**: Address the concern above.

### FINDING_32: **architecture** `skills/design/scripts/design-postplan-emit.sh:281-294` — In `--with-plan-size` mode, hard/partition handling uses `emit()` to print standalone `KEY=value` lines (`PLAN_LINES=…`, `DIFF_LINES=…`, `DIFF_ADDED=…`, `DIFF_DELETED=…`, `trigger=partition-flag …`) onto FD 3, which becomes orchestrator `_postplan_out` via command substitution. Contract KVs are written only to `.design-postplan-emit-result.env`, but the display stream is KV-isomorphic for the same key names. `test-design-postplan-emit.sh` only asserts absence of `POSTPLAN_EMIT_STATUS=` and `WARN=` on stdout (e.g. D13–D14), not `PLAN_LINES=`, `HARD_TRIGGER_FIRED=`, etc., so a revived `awk -F=` / grep parse of `_postplan_out` could treat display echoes as authoritative. **Suggested fix:** Emit human-readable plan-size sections without standalone contract-key lines (or prefix with a non-machine marker), and extend harness/structure pins to forbid allowlisted contract keys on merged stdout.
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-postplan-emit.sh:281-294` — In `--with-plan-size` mode, hard/partition handling uses `emit()` to print standalone `KEY=value` lines (`PLAN_LINES=…`, `DIFF_LINES=…`, `DIFF_ADDED=…`, `DIFF_DELETED=…`, `trigger=partition-flag …`) onto FD 3, which becomes orchestrator `_postplan_out` via command substitution. Contract KVs are written only to `.design-postplan-emit-result.env`, but the display stream is KV-isomorphic for the same key names. `test-design-postplan-emit.sh` only asserts absence of `POSTPLAN_EMIT_STATUS=` and `WARN=` on stdout (e.g. D13–D14), not `PLAN_LINES=`, `HARD_TRIGGER_FIRED=`, etc., so a revived `awk -F=` / grep parse of `_postplan_out` could treat display echoes as authoritative. **Suggested fix:** Emit human-readable plan-size sections without standalone contract-key lines (or prefix with a non-machine marker), and extend harness/structure pins to forbid allowlisted contract keys on merged stdout.
- **Suggested revision**: Address the concern above.

### FINDING_33: **architecture** `skills/design/scripts/design-postplan-emit.sh:522-525` with `skills/design/SKILL.md:895-911` — On `VALIDATE_STATUS=defects-found`, merged mode writes validator fields only into `.design-postplan-emit-result.env` (`_postplan_flush` then `exit 10`) and does not emit validator defect context on FD 3. The Step 2b thin fence loads `VALIDATE_*` from the result env inside the `10)` arm; if that read is skipped or the file is missing, **### Plan command validator failure (shared)** can run with empty validator state while `_postplan_out` has no machine validator payload. **Suggested fix:** Before `exit 10`, emit a fixed-path operator summary on FD 3 (e.g. defect count + log path) while keeping authoritative KVs in the result env only; pin the allowlisted read loop in every merged site, not only Step 2b.
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-postplan-emit.sh:522-525` with `skills/design/SKILL.md:895-911` — On `VALIDATE_STATUS=defects-found`, merged mode writes validator fields only into `.design-postplan-emit-result.env` (`_postplan_flush` then `exit 10`) and does not emit validator defect context on FD 3. The Step 2b thin fence loads `VALIDATE_*` from the result env inside the `10)` arm; if that read is skipped or the file is missing, **### Plan command validator failure (shared)** can run with empty validator state while `_postplan_out` has no machine validator payload. **Suggested fix:** Before `exit 10`, emit a fixed-path operator summary on FD 3 (e.g. defect count + log path) while keeping authoritative KVs in the result env only; pin the allowlisted read loop in every merged site, not only Step 2b.
- **Suggested revision**: Address the concern above.

### FINDING_34: **architecture** `skills/design/references/approval-gates.md:157-158` and `scripts/test-design-structure.sh:560-566` — Gate B prose delegates to “the same `case` arms as `SKILL.md` Step 2b” but does not inline the Step 2b allowlisted `.design-postplan-emit-result.env` read block; structure pins `case "${_postplan_rc:-1}" in` in `approval-gates.md` but not a `VALIDATE_STATUS` env read inside that fence region (discussion-round2 is similar). That splits machine state (result env at Step 2b only) from control flow (Gate B case arms), which is fragile for rc 10. **Suggested fix:** Duplicate the Step 2b rc `10)` allowlisted env-read snippet in Gate B / discussion fences, or reference a single shared fenced fragment; extend `assert_postplan_thin_fence` to require that read loop wherever `--with-plan-size` + `case "${_postplan_rc:-1}"` appear.
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **architecture** `skills/design/references/approval-gates.md:157-158` and `scripts/test-design-structure.sh:560-566` — Gate B prose delegates to “the same `case` arms as `SKILL.md` Step 2b” but does not inline the Step 2b allowlisted `.design-postplan-emit-result.env` read block; structure pins `case "${_postplan_rc:-1}" in` in `approval-gates.md` but not a `VALIDATE_STATUS` env read inside that fence region (discussion-round2 is similar). That splits machine state (result env at Step 2b only) from control flow (Gate B case arms), which is fragile for rc 10. **Suggested fix:** Duplicate the Step 2b rc `10)` allowlisted env-read snippet in Gate B / discussion fences, or reference a single shared fenced fragment; extend `assert_postplan_thin_fence` to require that read loop wherever `--with-plan-size` + `case "${_postplan_rc:-1}"` appear.
- **Suggested revision**: Address the concern above.

### FINDING_35: **architecture** `skills/design/scripts/design-postplan-emit.sh:408-413` — Merged invalid-repo pause emits `PAUSE_OK=false` and `ERROR=invalid-repo` via `emit()` on FD 3 but does not write those keys to `.design-postplan-emit-result.env` (only `POSTPLAN_EMIT_STATUS=pause-failed` is flushed). Legacy mode uses `emit_kv` for the same fields. Display and machine channels disagree for pause failure. **Suggested fix:** Either write `PAUSE_OK` / `ERROR` into the result env in merged mode and keep display prose-only, or drop KV-shaped pause lines from FD 3 and rely on exit `1` + env status; add a merged `--with-plan-size` harness case for invalid `REPO`.
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-postplan-emit.sh:408-413` — Merged invalid-repo pause emits `PAUSE_OK=false` and `ERROR=invalid-repo` via `emit()` on FD 3 but does not write those keys to `.design-postplan-emit-result.env` (only `POSTPLAN_EMIT_STATUS=pause-failed` is flushed). Legacy mode uses `emit_kv` for the same fields. Display and machine channels disagree for pause failure. **Suggested fix:** Either write `PAUSE_OK` / `ERROR` into the result env in merged mode and keep display prose-only, or drop KV-shaped pause lines from FD 3 and rely on exit `1` + env status; add a merged `--with-plan-size` harness case for invalid `REPO`.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] **Correct core split:** Legacy `_postplan_write_result_and_emit` still mirrors contract KVs to FD 3 via `emit_kv`; merged `_postplan_write_result_merged` does not call `emit_kv`, fails closed on result-env write failure without stdout-KV fallback (D26), captures nested `check-plan-size.sh` stdout only for internal `parse_kv_from_output`, routes stderr to a sidecar on nonzero plan-size exits, and suppresses `append-tool-failure.sh` helper KVs (D22, D27).
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **Correct core split:** Legacy `_postplan_write_result_and_emit` still mirrors contract KVs to FD 3 via `emit_kv`; merged `_postplan_write_result_merged` does not call `emit_kv`, fails closed on result-env write failure without stdout-KV fallback (D26), captures nested `check-plan-size.sh` stdout only for internal `parse_kv_from_output`, routes stderr to a sidecar on nonzero plan-size exits, and suppresses `append-tool-failure.sh` helper KVs (D22, D27).
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] **Thin-fence hygiene:** `SKILL.md` Step 2b drops the old stdout-KV merge / symlink “stdout fallback” block; `assert_postplan_thin_fence` forbids `<<<"${_postplan_out:-}"` heredoc parsing; orchestrator uses allowlisted line reads, not `source`.
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **Thin-fence hygiene:** `SKILL.md` Step 2b drops the old stdout-KV merge / symlink “stdout fallback” block; `assert_postplan_thin_fence` forbids `<<<"${_postplan_out:-}"` heredoc parsing; orchestrator uses allowlisted line reads, not `source`.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] **Harness gap vs plan:** Structure pins do not yet enforce the full “no contract keys on merged stdout” set promised in the plan (only `POSTPLAN_EMIT_STATUS=` / `WARN=`).
- **Reviewer**: dyn-kv-output-isolation-output.txt
- **Concern**: - **Harness gap vs plan:** Structure pins do not yet enforce the full “no contract keys on merged stdout” set promised in the plan (only `POSTPLAN_EMIT_STATUS=` / `WARN=`).
- **Suggested revision**: Address the concern above.

