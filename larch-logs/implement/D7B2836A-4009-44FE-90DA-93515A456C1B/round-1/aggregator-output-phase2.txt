Verifying key overlap areas in the codebase so merged findings reflect the same behavioral risks.
Normalized aggregator output from the 43 raw inputs. Positive OOS attestations (inputs 27–28, 35–36, 42–43, 30) are omitted—they do not describe a fixable defect. Overlapping harness/runtime/doc items are merged by behavioral risk.

### FINDING_1: Thin-fence CI coverage limited to Step 2b only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-rc-fence-integrity-output.txt
- **Severity**: important
- **Concern**: `assert_postplan_thin_fence` in `scripts/test-design-structure.sh` runs only on the `<!-- step:2b -->` … `### Step 2b.5` region of `skills/design/SKILL.md`. Gate B (`approval-gates.md` §Shared post-apply), discussion-round2 (`discussion-rounds.md`), and Step 1e optional-trailer guard are covered at best by weak substring pins (`--with-plan-size`, delegate-to-SKILL prose), not the full mechanical contract (`set +e`, `printf '%s\n' "${_postplan_out:-}"`, `case "${_postplan_rc:-1}" in` with arms `0`/`10`/`11`/`12`/`13`/`2`/`1`/`*`, result-env reads, no `<<<` stdout KV merge). Only Step 2b embeds a complete fence; merged sites depend on cross-file stitching, so a dropped `*)` default-abort arm, missing rc arm, or wrong post-`esac` routing can pass CI while breaking runtime orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Scope `assert_postplan_thin_fence` to Gate B and discussion regions or add a shared canonical fence snippet; add negative self-test for missing case arm.
  - From cursor-specialist-edge-cases-output.txt: Add `assert_postplan_thin_fence` (or equivalent) for Gate B shared post-apply and discussion-round2 regions; add negative fixture missing `*)` that must fail.
  - From cursor-specialist-plan-fidelity-output.txt: Extend `assert_postplan_thin_fence` to Gate B and discussion-round2 regions; add negative fixture test.
  - From dyn-rc-fence-integrity-output.txt: Add a site-scoped thin fence (or a shared include block) in each merged caller with the full `case` dispatch and site-specific post-`esac` routing; pin all three sites with `assert_postplan_thin_fence`, not only the Step 2b region in `scripts/test-design-structure.sh`.
  - From dyn-rc-fence-integrity-output.txt: Extend `assert_postplan_thin_fence` (or add scoped variants) for `approval-gates.md` §Shared post-apply, `discussion-rounds.md` Round 2 re-emit, and Step 1e optional-trailer guard; add a negative fixture missing `*)` or an arm, per the plan’s structure-test intent.

### FINDING_2: Retained Step 2b.5 hard prompt missing Override (site-aware contract)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retained Step 2b.5 step 4 (`skills/design/SKILL.md` ~966–967) offers only Split/Cancel on `HARD_TRIGGER_FIRED=true`, while `check-plan-size.md`, `flags.md`, and plan acceptance require Split/**Override**/Cancel for Gate B Step 3, `LOOP_STATUS=plan-size-trigger`, and `plan-review-loop.sh`. After plan-review-loop returns `plan-size-trigger` on a hard-sized revised plan, the operator cannot choose Override and must Split or Cancel contrary to the documented site-aware contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Branch Step 2b.5 step 4 by caller site: initial/discussion Split/Cancel only; retained callers Split/Override/Cancel.
  - From cursor-specialist-plan-fidelity-output.txt: Branch Step 2b.5 step 4 on caller site; document site tokens in SKILL and approval-gates.
  - From cursor-specialist-testing-output.txt: Add grep pins for Split/Override/Cancel in approval-gates.md and retained Step 2b.5/plan-review-loop docs.

### FINDING_3: Unconditional validation contract drift (quick-skip, --force-validate, stale pins)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Three-way drift: `flags.md` (~76) states validation is unconditional with no quick-skip and no force flag; `design-postplan-emit.sh` still sets `VALIDATE_STATUS=skipped-quick` for `review_budget=quick` (~92–94, ~501–502) and accepts `--force-validate`; `test-design-postplan-emit.sh` case #4 expects validator on legacy `review_budget=quick` but gets `skipped-quick`; `scripts/test-design-structure.sh` (~388–389) still requires `skipped-quick` and `--force-validate` in `flags.md`; test #12 expects `--force-validate` exit 2 while the script accepts the flag; `discussion-rounds.md` (~126) and `design-postplan-emit.md` still document `--force-validate`/quick-skip; Step 2a prose (`SKILL.md` ~651) still documents validator skip on `review_budget=quick`. CI and operator docs disagree on the Phase 4 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Align `design-postplan-emit.sh` quick-skip with `flags.md` unconditional validation OR revert test #4; re-run harness until green.
  - From cursor-specialist-testing-output.txt: Update structure pins to match `flags.md` or restore the documented quick-skip/force-validate contract in `flags.md`.
  - From cursor-specialist-testing-output.txt: Remove `--force-validate` end-to-end or keep it everywhere; sync test #12, `flags.md`, Step 1e, and discussion-round2 argv.
  - From cursor-specialist-testing-output.txt: Update Step 2a and related prose to match unconditional validation contract.

### FINDING_4: Missing / failing postplan-emit harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-quiet-kv-discipline-output.txt
- **Severity**: important
- **Concern**: Plan-required cases are absent or red: `test-design-postplan-emit.sh` lacks D27+ coverage for plan-size rc3 append-helper failure and merged rc1 `snapshot-failed`/`validate-driver-failed` subfailure messaging (`test-design-postplan-emit.md` ~887); case #4 fails (`expected VALIDATE_STATUS=ok got skipped-quick`). Nonfatal rc3 and append-failure paths, plus merged rc1 subfailure messaging, can regress without CI signal. Documented “nonfatal even when `append-tool-failure.sh` itself fails” is not implemented in the shell harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add D27+ cases for rc3 append stub failure and merged snapshot-failed/validate-driver-failed rc1.
  - From cursor-specialist-plan-fidelity-output.txt: Stub failing append helper; assert exit 0 WARN display and no helper KV leakage.

### FINDING_5: Step 3 `plan-size-trigger` routing, Refine, and completion sentinels
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-sentinel-state-machine-output.txt
- **Severity**: important
- **Concern**: `LOOP_STATUS=plan-size-trigger` (`skills/design/SKILL.md` ~1087) runs the Step 2b.5 Split-path handler then unconditionally short-circuits to Step 3b with only Gate-B-bypass sentinels (`step-3`, `step-3.5`, `step-3.6`). It omits Refine → Gate A (or documented pause/refine re-entry) required by `decompose-panel.md` (~195), never writes `.completed/step-2b.5` (or `step-2b`) after retained handler completion, and steers **Refine plan myself** during retained hard/partition Split to diagram generation instead of Gate A. Merged rc 12/13 paths enter Split from `--with-plan-size` without running Step 2b.5 steps 1–6, so the success boundary at `SKILL.md` ~985 may never run; `decompose-panel.md` §4 Refine and §6 Continue still “return to caller” without mandatory sentinel writes at the decision point.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Rewrite Step 3 branch to run full retained Step 2b.5 with decompose-panel non-exiting return and Refine routing rules.
  - From dyn-sentinel-state-machine-output.txt: Extend the `plan-size-trigger` branch (and shared `apply_gate_b_bypass_sentinels` helpers in `test-step3-orchestrator-fence.sh` / `test-design-pause-resume.sh`) so that, after the Step 2b.5 handler finishes on any non-exiting path, the orchestrator always `mkdir -p`s and touches `step-2b.5` (and `step-2b` when the initial-site contract applies) before writing the `step-3*` bypass sentinels and continuing.
  - From dyn-sentinel-state-machine-output.txt: Split the `plan-size-trigger` handler outcome: Refine / no-split **Continue** → write `step-2b`/`step-2b.5` per site, then return to Gate A (or the documented pause/refine re-entry); Override / clean proceed → write sentinels, then Step 3b with the triple bypass.
  - From dyn-sentinel-state-machine-output.txt: At §4 Refine and §6 Continue, add mandatory `mkdir -p` + `: > .completed/step-2b.5` (and `: > .completed/step-2b` for initial-site merged callers), with site-specific return targets: initial → Step 3; Gate B → continue toward Step 3.6; discussion / Step 1e → Gate A; `plan-size-trigger` Refine → Gate A per above.

### FINDING_6: Sentinel and site-aware prompt structure-test gaps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sentinel-state-machine-output.txt
- **Severity**: important
- **Concern**: Structure tests do not pin the implementation plan’s sentinel matrix or site-aware hard prompts: no pins for rc 12/13 `step-2b`, post-Split Refine/Continue dual sentinels, Gate B Override `step-2b.5`, `decompose-panel.md` non-exiting contract (~195 vs `test-design-structure.sh` ~1247–1252), or Split/Override/Cancel vs Split/Cancel-only sites. `scripts/test-design-structure.sh` (~747–748) only requires `step-2b.5` on initial Step 2b rc 0 inside `<!-- step:2b -->`. Docs can claim Override at Gate B while `SKILL.md` Step 2b.5 stays Split/Cancel-only and CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add structure-test pins for step-2b/step-2b.5 sentinel rules in decompose-panel.md.
  - From cursor-specialist-plan-fidelity-output.txt: Add pins for Split/Override/Cancel vs Split/Cancel-only sites and decompose-panel non-exiting return block.
  - From dyn-sentinel-state-machine-output.txt: Add grep pins (or extend `assert_postplan_thin_fence`) for rc 12/13 `step-2b`, post-Split Refine/Continue dual sentinels, Gate B Override `step-2b.5`, `decompose-panel.md` non-exiting contract text, and `plan-size-trigger` `step-2b.5` writes so doc drift is caught in CI.

### FINDING_7: Quiet/KV discipline gaps in retained paths and plan-review-loop
- **Reviewer(s)**: dyn-quiet-kv-discipline-output.txt
- **Severity**: important
- **Concern**: (1) Step 2b.5 step 2 requires `LARCH_QUIET_DISABLE=1` and stdout-only capture, but the fenced example (`SKILL.md` ~6150–6151) calls `check-plan-size.sh` without `env LARCH_QUIET_DISABLE=1`, risking missed verdict KVs under quiet mode. (2) Retained Step 2b.5 rc2/rc3 handling runs `append-tool-failure.sh` without stdout/stderr suppression while `design-postplan-emit.sh` (~333–340) and `plan-review-loop.sh` (~624–631) redirect to `/dev/null`, so `APPENDED=`/`LOG=` helper KVs can leak on Override-after-defects paths. (3) `plan-review-loop.sh` (~614–618) writes only `size_out` into `check-plan-size.validation.log` while `design-postplan-emit.sh` (~321–324) merges stdout+stderr, dropping stderr diagnostics under quiet mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-kv-discipline-output.txt: Add `env LARCH_QUIET_DISABLE=1` to the example invocation so it matches step 2 prose and the merged driver.
  - From dyn-quiet-kv-discipline-output.txt: Align retained Step 2b.5 prose with the merged/loop pattern: redirect `append-tool-failure.sh` stdout/stderr to `/dev/null` (with `|| true`) and keep only the human-readable `**⚠ 2b.5: ...**` line as display output.
  - From dyn-quiet-kv-discipline-output.txt: Mirror `_postplan_append_plan_size_warning`: capture stderr to a sidecar during the nested call, merge stdout+stderr into `check-plan-size.validation.log`, and still parse KVs from stdout only.

### FINDING_8: Site-specific `design-postplan-emit.sh` argv not pinned per merged caller
- **Reviewer(s)**: dyn-rc-fence-integrity-output.txt
- **Severity**: important
- **Concern**: Initial Step 2b hardcodes `--with-plan-size --snapshot-original` (`SKILL.md` ~882–885); Gate B requires `--with-plan-size` with snapshot suppressed (`approval-gates.md` ~157); discussion-round2 requires `--with-plan-size --force-validate` (`discussion-rounds.md` ~126). Prose to “run the Step 2b thin-fence `case` arms” without site-specific argv invites copying the initial fence on Gate B/discussion re-emits, changing snapshot/validation behavior every review round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rc-fence-integrity-output.txt: Document three explicit invocation shapes (initial, Gate B, discussion) adjacent to each fence, or factor argv into variables (`_postplan_extra_flags`) before the shared `case`, and add structure-test pins that forbid `--snapshot-original` outside the initial Step 2b region and require `--force-validate` in discussion/Step 1e blocks.

### FINDING_9: Plan validator Fix-and-retry splits authority from merged thin fence
- **Reviewer(s)**: dyn-rc-fence-integrity-output.txt
- **Severity**: important
- **Concern**: Step 2b rc10 **Fix-and-retry** re-enters the merged `--with-plan-size --snapshot-original` fence (`SKILL.md` ~939), and Gate B/discussion prose say the same for their sites, but **### Plan command validator failure (shared)** (`SKILL.md` ~1545–1550) still loops on raw `ACTION=EMIT_PLAN` and `ACTION=VALIDATE_PLAN_COMMANDS`. That splits rc10 re-entry across two incompatible authorities and can bypass plan-size mapping (rc 12/13) and result-env reads on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rc-fence-integrity-output.txt: Update the shared Fix-and-retry bullet to re-enter the site’s merged `design-postplan-emit.sh --with-plan-size …` fence (with site flags), reserving raw emit/validate for Step 5c composed-plan only, matching the plan’s thin-fence contract.

### FINDING_10: Stale Gate B prose still pairs every re-emit with standalone Step 2b.5
- **Reviewer(s)**: dyn-rc-fence-integrity-output.txt
- **Severity**: latent
- **Concern**: Step 3.5 and `approval-gates.md` (~122, 157–163) still say Gate B “requires **Step 2b.5** immediately after each settled `design-postplan-emit.sh` re-emit” while the merged path folds plan-size into the driver and clean rc0 should go straight to Step 3.6 after sentinel writes. Stale pairing encourages a second standalone `check-plan-size.sh` pass after every Gate B apply, undoing turn savings and risking divergent rc12/13 handling (display + prompts twice).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rc-fence-integrity-output.txt: Reword Gate B and Step 3.5 so merged rc0/12/13 use only the driver fence; restrict standalone Step 2b.5 to Override-after-defects, `LOOP_STATUS=plan-size-trigger`, and other retained callers explicitly named in Step 2b.5.

### FINDING_11: Gate B delegates thin-fence arms without embedded fence
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gate B merged post-apply (`approval-gates.md` ~158) delegates thin-fence `case` arms to `SKILL.md` instead of embedding a fence. An orchestrator following only `approval-gates.md` may omit mandatory case arms or echo discipline even when Step 2b’s fence is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Duplicate minimal fence skeleton in reference or pin delegation completeness in structure test.

### FINDING_12: Result-env KV values not newline-sanitized
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: WARN and other KV values written to `.design-postplan-emit-result.env` are not newline-sanitized on write (`design-postplan-emit.sh` ~195–236). A WARN value containing an embedded newline plus a forged `VALIDATE_STATUS=ok` line can pollute the result env; thin-fence allowlist reads may honor the forged key on rc 10.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject or escape CR/LF in all values at write time in `_postplan_build_kvs` and `phase_driver_write_result_env`.

### FINDING_13: Manifest author can stall PR via security OOS sidecar
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest author can mark observations as security to fill `security-oos-observations.md` (`materialize-manifest-oos.sh` ~127–133). `ship-pr.sh` blocks PR creation while that sidecar is non-empty, letting an external implementer stall shipping without completing private disclosure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document recovery; consider gating block on operator acknowledgment or tightening security_signal false-positive rules.

### FINDING_14: Plan-size validation log written before redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Plan-size rc2/3 writes combined stdout+stderr to `check-plan-size.validation.log` before redacted append (`design-postplan-emit.sh` ~313–357). Failed check output may leave secrets or internal URLs in the session tmpdir until cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact the combined capture before writing the validation log file.

### FINDING_15: Plan-size checker rc2/3 nonfatal continues as under-threshold
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Plan-size checker rc2/3 is nonfatal and continues as under-threshold (`design-postplan-emit.sh` ~376–384). Misconfigured checker allows oversized plans into full review, increasing cost and DoS surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Keep as monitored degradation or fail closed on HARD tier unless operator overrides.

### OOS_1: [OUT_OF_SCOPE] PR branch includes non–Phase-4 commits
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Diff includes multiple non-Phase-4 commits increasing CI blast radius. Unrelated harness failures could block merge of Phase 4 work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Consider scoping PR or verifying full-branch lint independently of Phase 4 acceptance.

### OOS_2: [OUT_OF_SCOPE] `design-postplan-emit.md` conflicts with `flags.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `design-postplan-emit.md` (~13–24) still documents `--force-validate`/quick-skip while `flags.md` (~76) says both removed. Operator reads conflicting authority docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Sync `design-postplan-emit.md` with `flags.md` when contract is finalized.
