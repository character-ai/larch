### FINDING_1: design-step3-state.sh not committed to plugin package
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step3-state.sh` is referenced by `SKILL.md` Gate-B-bypass and direct-review paths and required executable by `test-design-structure.sh`, but remains untracked / absent from HEAD. Fresh checkout or CI: `test-design-structure` fails; live `/design` Step 3 bypass and direct-review entry try to exec a missing script and cannot write `step-3` / `step-3.5` / `step-3.6` sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Commit design-step3-state.sh with executable permissions and add a focused harness for gate-b-bypass refused-partial and direct-review-entry paths.
  - From cursor-specialist-correctness-output.txt: Add and commit design-step3-state.sh (executable) so shipped plugin matches SKILL and harness pins.
  - From cursor-specialist-testing-output.txt: Add test-design-step3-state.sh for gate-b-bypass, refused-partial, and direct-review-entry branches; wire into Makefile.
  - From cursor-specialist-plan-fidelity-output.txt: git add skills/design/scripts/design-step3-state.sh; chmod +x; add contract doc and optional harness.


### FINDING_10: Direct-review pause harness does not exercise unconsumed-marker snapshot
- **Reviewer(s)**: dyn-pause-resume-sentinel-output.txt
- **Severity**: latent
- **Concern**: `test-design-pause-resume.sh:1037-1058` duplicates `design-step3-state.sh` logic inline and consumes `.step3-reentry` before `design-pause-save.sh` runs, so it never exercises the branch at `design-pause-save.sh:171-172` (unconsumed marker + stale downstream markers coexisting in the published snapshot).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-sentinel-output.txt: Add a case that writes `.step3-reentry`, leaves prior `step-3`/`step-3.5` markers in place, pauses **without** consuming the marker, asserts `STEP=3` and that the published snapshot still contains `.step3-reentry`, then on load invokes `design-step3-state.sh --direct-review-entry` (not inline bash) and asserts downstream clears + marker consumption.


### FINDING_11: SKILL.md sentinel table overstates Step 3 step-1e writes
- **Reviewer(s)**: dyn-pause-resume-sentinel-output.txt
- **Severity**: latent
- **Concern**: The completion-sentinel table and Step 1e prose (`SKILL.md:103,638`) say `.completed/step-1e` is batch-written on every Step 3 entry, but the Step 3 fence only calls `design-step3-state.sh --direct-review-entry`, which is a no-op unless `.step3-reentry` is present (`design-step3-state.sh:61-63`). Line 1092 correctly gates hygiene on the marker; lines 103 and 638 do not. Maintainers following the table may add an unconditional `step-1e` write, masking backward-loop clears and shifting pause registry detection toward `STEP=3` even when Gate A discussion has not finished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-sentinel-output.txt: Align the sentinel table row and line 638 with line 1092: Step 3 entry writes `step-1e` and the bypass package only when `design-step3-state.sh --direct-review-entry` runs with the marker present; first-time Step 3 entry remains env + pause-check + timing only.


### FINDING_16: assert_always_emitted_keys omits drift/baseline keys
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `assert_always_emitted_keys` in `test-check-plan-size.sh:39-45` does not require `DRIFT_*` and `BASELINE_*` keys on every success path. Drift KV emission could regress on non-drift cases while cases 34-38 still pass in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend assert_always_emitted_keys to pin all six drift/baseline keys on every run_ok call.


### FINDING_18: REVISE_WINNING_TIER written but never populated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `REVISE_WINNING_TIER` still written to `round-summary.env` (`plan-review-loop.sh:495`) but never populated after revise waterfall removal. Downstream log parsers or debugging harnesses may expect a meaningful tier string and always see empty values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the key or document it as deprecated unused in plan-review-loop.md and tests.


### FINDING_2: Duplicate drift-baseline write logic across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh:305-316` duplicates write-once drift-baseline logic with `check-plan-size.sh:187-223`, using inconsistent file guards (`-f` symlink-aware vs `-e`). Future edits may update seeding in one script only; symlink or partial-write edge cases diverge; operators see inconsistent baseline behavior between Step 2b snapshot and Override seed paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract one shared baseline writer with unified guard and warning semantics; call it from both scripts.


### FINDING_3: Unreadable drift-baseline re-anchors to inflated current size
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-drift-baseline-guard-output.txt
- **Severity**: important
- **Concern**: When `drift-baseline.env` is unreadable, corrupt, or a symlink (`check-plan-size.sh:199-220`), the helper re-seeds the baseline from the **current** plan size and forces `DRIFT_TRIGGER_FIRED=false`. After Gate B or discussion growth (e.g. baseline `10/10`, current `21/10` at 2.1×), tmpdir corruption or a symlink resets the anchor to the bloated plan and permanently suppresses drift that should have fired (`test-check-plan-size.sh` case 36 encodes this). Same-UID actors or races that corrupt the file after plan growth can bypass the drift Continue/Cancel prompt until further growth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed on corrupt baseline (drift fired or hard abort) or require explicit operator re-baseline; do not silently re-anchor to current size when corruption is detected.
  - From cursor-specialist-edge-cases-output.txt: Re-seed from plan.txt-original or fail closed with operator Continue/Cancel; do not anchor to current metrics on corruption recovery.
  - From dyn-drift-baseline-guard-output.txt: On unreadable baseline, either fail closed (treat as drift trigger / require operator Continue) or re-seed from the last known-good baseline if recoverable; do not re-anchor to an already-inflated current size without at least surfacing a drift prompt when the pre-reset comparison would have fired.


### FINDING_4: defects-found path bypasses drift/hard/partition precedence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-drift-baseline-guard-output.txt
- **Severity**: important
- **Concern**: On the `VALIDATE_STATUS=defects-found` branch (`design-postplan-emit.sh:560-570`), the driver may run `_postplan_run_plan_size` (when `--snapshot-original` is set) and even write `drift-baseline.env` from pre-fix metrics, but always flushes and exits **10** without calling `_postplan_finish_merged_plan_size`. Step 2b fix-and-retry loops with validator defects never surface drift (exit **14**) or hard/partition triggers (exits **12**/**13**), even when the plan has already grown past the write-once baseline. Baseline may capture pre-Override line/diff counts while the post-Override plan differs, so drift either fires too early or compares against the wrong anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Defer baseline write until first validate pass succeeds, or refresh baseline once after successful Override re-emit.
  - From dyn-drift-baseline-guard-output.txt: After a successful plan-size parse on the defects-found path, route through the same precedence logic as `_postplan_finish_merged_plan_size` (hard → partition → drift) before returning exit **10**; or exit **14**/**12**/**13** when those triggers fire and reserve exit **10** for defect-only outcomes. Add a regression in `test-design-postplan-emit.sh` that seeds a baseline, re-enters with `defects-found` plus an over-threshold plan, and asserts exit **14** (not **10**).


### FINDING_5: plan-size helper rc 2/3 skips drift guard on merged emit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh:323-349` — when `check-plan-size.sh` returns rc 2/3, the driver appends a warning and merged emit continues at exit 0 without drift or hard-size evaluation. Helper argv/IO failure during Gate B or discussion re-emit skips the drift guard entirely while the orchestrator auto-continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail closed or require explicit operator acknowledgment when plan-size helper fails on merged emit paths.


### FINDING_6: Missing test for session-root artifact clearing before single-pass review
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required test for `_clear_session_root_review_artifacts` before single-pass review is missing (`test-plan-review-loop.sh:1421-1463`). Gate-C re-entry could reuse stale `accepted-plan-findings.md` or `ballot.txt`; regression would only surface in live multi-entry Step 3 runs, not CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a harness case seeding stale session-root artifacts, run one single-pass round, assert stale content is cleared/truncated before fresh round output.


### FINDING_7: Missing OOS save/restore tests after single-pass refactor
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required OOS save/restore tests for panel-failed and tally-error paths are missing after multi-round cumulative tests were deleted (`test-plan-review-loop.sh:1451-1463`). A failed single-pass round could corrupt or drop prior `oos-accepted-design.md` cumulative state without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Seed known prior OOS content, force panel-failed or fatal tally-error, assert oos-accepted-design.md is restored unchanged.


### FINDING_8: manual_gate_b removal not pinned in test-write-run-params.sh
- **Reviewer(s)**: dyn-manual-flag-removal-output.txt
- **Severity**: important
- **Concern**: The branch removes `manual_gate_b` / `--manual-gate-b` from `write-run-params.sh`, and `test-step0b-router-flag-recovery.sh` asserts fresh `run-params.json` files omit `manual_gate_b`, but `test-write-run-params.sh` never pins the removal. It has a symmetric `assert_rejected_with` case for retired `--review-budget` but its primary jq schema check does not assert `has("manual_gate_b") == false`. A partial reintroduction of the CLI flag or JSON field could slip through `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manual-flag-removal-output.txt: Add `assert_rejected_with removed-manual-gate-b 'unknown flag: --manual-gate-b' …` mirroring the `--review-budget` case, and extend the v3 jq assertions to require `has("manual_gate_b") == false` on successful writes.


### FINDING_9: Pause snapshot may co-publish unconsumed .step3-reentry with stale sentinels
- **Reviewer(s)**: dyn-pause-resume-sentinel-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh:171-189` — `.step3-reentry` priority forces `STEP=3` whenever the marker exists, but pause publish stages the tmpdir as-is without the sentinel hygiene that `design-step3-state.sh:60-72` performs. After Gate A "Ready for review" or Gate C "Re-run review panel", a pause between marker write and Step 3 entry can snapshot both an unconsumed `.step3-reentry` and stale `.completed/step-3`…`step-4b` markers. `design-pause-load.sh` strips only `.pause-requested`; correct resume depends entirely on `resume@3` always executing `design-step3-state.sh --direct-review-entry`. Skipped entry leaves the marker unconsumed (infinite Step 3 re-review risk) while stale `step-3.5`/`step-3.6` markers can confuse Gate B routing (`refused-partial-gate-b-bypass`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-sentinel-output.txt: Either (a) call `design-step3-state.sh --direct-review-entry` from `design-pause-save.sh` before `design-log-publish.sh` when `.step3-reentry` is present (producing a self-consistent snapshot and consuming the marker before publish), or (b) split the helper into "clear downstream + restore bypass package" vs "consume marker" and run the clear/restore half at save time while keeping the marker for `STEP=3` until Step 3 entry. Document the chosen contract in `design-pause-load.md` alongside the `.pause-requested` rule.


