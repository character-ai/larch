### FINDING_1: `plan-review-continuation.sh` deleted without a native replacement
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-wire-contract-auditor
- **Severity**: blocking
- **Concern**: The plan deletes `plan-review-continuation.sh` but does not name a native port of its `PLAN_REVIEW_CONTINUE` / `PLAN_REVIEW_CONTINUE_REASON` heuristics, stdout KV grammar, or call-site wiring. Live callers include `review-design-step3-loop.sh` (`step3_loop_run_continuation`), legacy `--mode single` Gate B continuation prose in `skills/design/SKILL.md`, and `approval-gates.md`. Deleting the helper without an equivalent `python/cli.py plan-review continuation` (or inline helper) breaks automatic multi-round continuation, ballot-items-lost / pruned-empty / degraded-panel branches, and Gate B continuation routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit port step (inline helper or plan-review continuation verb) that preserves all PLAN_REVIEW_CONTINUE and PLAN_REVIEW_CONTINUE_REASON outputs and wire run_step3_review awaiting-continuation to it; add pytest coverage migrated from test-step3-review-cap.sh
  - From Cursor-Pragmatic: Mirror `plan-review-continuation.md` in a native helper, register `python/cli.py plan-review continuation`, port the KV contract verbatim, repoint the loop and SKILL.md legacy path to that verb, then delete the script and its `.md` sibling
  - From Codex-Requirements: Add approval-gates.md to the plan and rewrite the continuation references to the native plan-review continuation or settle path
  - From Cursor-dyn-wire-contract-auditor: Specify a native continuation function with the same stdout keys and add pytest for ballot-items-lost plus at least one continue=false reason before script deletion


### FINDING_2: Continuation-decision parity tests missing before harness deletion
- **Reviewer(s)**: Codex-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: The proposed pytest list names cap short-circuit and rollback but not the representative continuation-decision cases currently pinned by `test-step3-review-cap.sh` against `plan-review-continuation.sh` (cap, explicit approve, pruned-empty, degraded, high, non-nit, structural, ballot-items-lost). Removing the shell harness before native parity exists leaves auto-continuation behavior unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-wire-contract-auditor: Add a small table-driven pytest for PLAN_REVIEW_CONTINUE and PLAN_REVIEW_CONTINUE_REASON cases, or keep the shell harness until that coverage exists.


### FINDING_3: Step 3 lint, structure, and doc surfaces omitted from the plan
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-Pragmatic, Codex-dyn-migration-scope-guard, Codex-dyn-security-env-safety
- **Severity**: blocking
- **Concern**: The plan shrinks or deletes Step 3 shell bodies and harnesses but omits tracked lint/structure/doc files that still grep for wrapper internals, retired paths, `lib-step3-prelaunch-failure.sh`, `RUN_STEP3_*` stub seams, gzip delegation strings, and helper docs. After paths are appended to `python/migrated-scripts.tsv`, `make lint`, `make lint-retired-scripts`, and `make test-design-structure` can fail on stale retired-path literals or assertions against deleted shell internals. Affected surfaces include `python/checks.py`, `scripts/test-design-structure.sh`, `scripts/test-design-multi-round-integration.sh`, `skills/design/scripts/test-step3-orchestrator-fence.sh`, `.claude/rules/launcher-argv-test-coverage.md`, `skills/design/scripts/design-step3-review.md`, `skills/design/scripts/design-step3-mav.md`, `skills/design/scripts/design-step35-settle.md`, `skills/design/scripts/review-design-step3-loop.md`, `skills/design/scripts/plan-review-continuation.md`, and `scripts/test-design-multi-round-integration.md`. Step 3b/3.5 wrapper thinning also leaves structural harness pins on Bash-owned literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these harnesses and needed sibling docs to the file list. Retarget them to the native plan_review CLI or function seams, or retarget their Makefile entries, while preserving only wrapper-owned contracts.
  - From Codex-Innovation: Add these adjacent files to the plan and minimally retarget their references/assertions to the new Python tests, pytest selectors, or retained thin wrappers
  - From Cursor-Innovation: Add these adjacent files to the plan and minimally retarget their references/assertions to the new Python tests, pytest selectors, or retained thin wrappers
  - From Codex-Pragmatic: Add these files to the plan. Retarget python/checks.py, scripts/test-design-structure.sh, approval-gates.md, and test-design-multi-round-integration.md to native Python or pytest targets. Delete or rewrite the orphan internal helper docs before adding the retired paths.
  - From Codex-Requirements: Add these files to the plan; remove retired full-path literals and retarget the harnesses to native Python seams or pytest coverage without preserving the legacy shell loop override
  - From Cursor-Pragmatic: Update the `plan-review-continuation` / `test-step3-review-cap` tuple to pytest selectors (or drop it if fully subsumed)
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-design-structure.sh` and replace embedded-delegation pins with native-preview authority checks
  - From Codex-dyn-migration-scope-guard: Add scripts/test-design-structure.sh to the plan and retarget only the affected Step 3 assertions to the new Python CLI or thin-wrapper contracts
  - From Codex-dyn-security-env-safety: Extend the plan with minimal updates to python/checks.py, scripts/test-design-structure.sh, and affected wrapper docs. Remove stale retired path references and retarget assertions to the new plan-review CLI/thin-wrapper contracts.


### FINDING_4: Synchronous prelaunch gates must remain before backgrounding `plan-review run`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan deletes `lib-step3-prelaunch-failure.sh` without requiring the wrapper to keep synchronous prelaunch gates before nested `plan-review run`. Today monitor-mode and scope-anchor validation run in `design-step3-review.sh` before backgrounding, writing `.step3-review-result.env`, staging terminal state, and exiting with `SUMMARY_OUTCOME=failed-judge-panel`. Moving that logic only into the in-process loop would delay or mis-route `panel-init-failed` relative to process-group setup and `.completed/step-3` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep monitor-mode and `scope-anchor validate` in `design-step3-review.sh` (or call a new synchronous `plan-review` prelaunch verb) before launching `plan-review run`; port only the env-write/staging helpers from `lib-step3-prelaunch-failure.sh`.


### FINDING_5: Wrapper-owned zero-round `panel-init-failed` normalization must stay outside the loop
- **Reviewer(s)**: Cursor-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: The plan ports `lib-step3-prelaunch-failure.sh` `panel-init-failed` staging but does not state that wrapper-owned zero-round `panel-failed` normalization stays outside the loop. Zero-round `panel-failed` can be misclassified as recoverable `panel-failed` instead of terminal `panel-init-failed` with `SUMMARY_OUTCOME=failed-judge-panel`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-contract-auditor: State explicitly that design-step3-review.sh retains _step3_review_zero_round_coverage_missing normalization and add pytest mirroring test-design-step3-review.sh zero-round cases


### FINDING_6: `RUN_STEP3_*` integration override env hooks not preserved in the Python port
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan omits preserving `RUN_STEP3_*` override hooks when porting the Step 3 loop from bash to native Python. Harnesses and `python/test_plan_review.py` stub loop, dedup, revise, postplan, continuation, timing, and pause boundaries via `RUN_STEP3_PLAN_REVIEW_LOOP_SH`, `RUN_STEP3_DEDUP_PLAN_SH`, `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`, `RUN_STEP3_POSTPLAN_EMIT_SH`, `RUN_STEP3_CONTINUATION_SH`, `RUN_STEP3_RECORD_TIMING_SH`, and `RUN_STEP3_DESIGN_PAUSE_SAVE_SH`. Deleting bash bodies without Python-native equivalents breaks cap, rollback, MAV, and multi-round integration tests; `docs/python-migration.md` documents at least `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document preserved env overrides (or pytest monkeypatch seams) for each subprocess boundary the port keeps, and retarget `scripts/test-design-multi-round-integration.sh` and `skills/design/scripts/test-step3-orchestrator-fence.sh`
  - From Cursor-Requirements: In the native loop add the same env-gated dispatch points (default to current cli.py targets) document the surviving overrides in docs/python-migration.md and add pytest coverage that each override is honored
  - From Codex-Requirements: In the native loop add the same env-gated dispatch points (default to current cli.py targets) document the surviving overrides in docs/python-migration.md and add pytest coverage that each override is honored


### FINDING_8: `SECURITY.md` trust-boundary update omitted for Step 3 authority move
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan omits the required `SECURITY.md` update for the Step 3 trust-boundary authority move. After removing `_LEGACY_ASSETS`, `SECURITY.md` would still say embedded plan-review bash bodies enforce tmpdir validation, despite the port moving that security-sensitive behavior into native Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add SECURITY.md to the plan and update the sentence to name the native plan_review.py/plan_review_panel.py validation path and preserved validation-before-quiet-init/error contracts


### FINDING_9: `zero-findings-degraded-panel` must leave `STEP3_REVIEW_LOOP_STATUS` unset
- **Reviewer(s)**: Cursor-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: The plan omits the zero-findings-degraded-panel legacy handoff where `STEP3_REVIEW_LOOP_STATUS` stays unset. Native loop or wrapper normalization can emit `STEP3_REVIEW_LOOP_STATUS=panel-failed` or a missing-result warning when `LOOP_STATUS=zero-findings-degraded-panel` only, breaking Gate B zero-findings and ballot-items-lost continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-contract-auditor: Add an explicit contract bullet and pytest asserting LOOP_STATUS=zero-findings-degraded-panel survives with no STEP3_REVIEW_LOOP_STATUS, matching test-design-step3-review.sh


### FINDING_10: Bail-out statuses require asymmetric `LOOP_STATUS` ↔ `STEP3_REVIEW_LOOP_STATUS` mapping
- **Reviewer(s)**: Cursor-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: The plan does not pin the asymmetric back-map for bail-out statuses: `persist_envelope` writes `LOOP_STATUS=complete` for `main-agent-apply-required`, `per-round-approval-required`, and `postplan-operator-required` while `STEP3_REVIEW_LOOP_STATUS` keeps the bail token; the wrapper repeats the mapping at `design-step3-review.sh:536-540`. A Python port that sets `LOOP_STATUS` equal to `STEP3_REVIEW_LOOP_STATUS` breaks Gate B, Step 3.5, and MAV resume routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-contract-auditor: Document the mapping table in the plan and add pytest covering each bail-out status pair in .step3-review-result.env


### FINDING_11: `panel-failed` and invalid `LOOP_STATUS` round-count consumption omitted
- **Reviewer(s)**: Cursor-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: Plan edge cases document `tally-error` and `degraded-empty-collector` rollback but omit `panel-failed` and unrecognized `LOOP_STATUS` round consumption. The port can roll back on `tally-error` yet still fail to increment `review-round-count.txt` after a launched `panel-failed` round, violating the SKILL.md cap semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-contract-auditor: Add edge-case bullets for panel-failed and invalid LOOP_STATUS consumption and port the harness cases into python/test_plan_review.py before deleting test-step3-review-cap.sh


### FINDING_12: `.step3-review-cap.env` first-entry and cap-hit parity tests missing
- **Reviewer(s)**: Cursor-dyn-wire-contract-auditor, Codex-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: Deleting `test-step3-review-cap.sh` without pytest parity for `.step3-review-cap.env` leaves `STEP3_REVIEW_CAP_REACHED` and `STEP3_REVIEW_ROUND_NUM` unguarded. `skills/design/SKILL.md` makes `python/cli.py plan-review run` the sole writer of `.step3-review-cap.env` and `review-round-count.txt`; current harness pins `STEP3_REVIEW_CAP_REACHED=false` and `STEP3_REVIEW_ROUND_NUM=1` on first entry, but the proposed pytest list only names cap short-circuit and rollback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-contract-auditor: First-entry cap metadata can drift with no failing test after harness removal Add explicit pytest for .step3-review-cap.env contents on first entry and cap-hit short-circuit, tied to make test-step3-review-cap retarget
  - From Codex-dyn-wire-contract-auditor: Add a native pytest that covers the missing-counter first entry and cap-reached .step3-review-cap.env rows before deleting skills/design/scripts/test-step3-review-cap.sh.


### FINDING_13: `design-step3-review.sh --read-result-env` recovery mode ownership unspecified
- **Reviewer(s)**: Codex-dyn-wire-contract-auditor
- **Severity**: important
- **Concern**: The plan shrinks the wrapper and deletes `test-design-step3-review.sh` but only says to preserve stdout KVs generally. `design-step3-review.sh:260-291` defines a pure recovery mode that emits `READ_RESULT_ENV_STATUS` plus loop status fields without starting bg wait or dispatch; harness cases pin that behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-wire-contract-auditor: State that --read-result-env remains wrapper-owned, or add an equivalent plan-review verb, and migrate the ok and missing-result tests into python/test_plan_review.py.


### FINDING_14: Active Makefile CI integration targets omitted from the plan
- **Reviewer(s)**: Cursor-dyn-migration-scope-guard
- **Severity**: important
- **Concern**: The plan retargets deleted Step 3 shell harnesses but omits two active integration fences still in CI shards: `make test-step3-orchestrator-fence` (harnesses-16) and `make test-design-multi-round-integration` (harnesses-8). Neither harness appears in the plan's Makefile or testing sections. Deleting/moving loop bodies without updating these targets can leave CI green on pytest while orchestrator contracts regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-migration-scope-guard: Add `### UPDATED: skills/design/scripts/test-step3-orchestrator-fence.sh` (or migrate its cases into `python/test_plan_review.py`) and `### UPDATED: scripts/test-design-multi-round-integration.sh` (or pytest equivalent). Retarget both Makefile targets in the same change set as the loop port.


### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-migration-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/cli.py:116-129
- **Concern**: [SCOPE-REDUCTION] Plan registers up to ten new plan-review verbs while four wrappers already call existing verbs.. Scenario: `design-step3-entry-preview.sh` already calls `plan-review preview --variant step3` (lines 104-106). `design-step3-continuation-entry.sh` and `design-step3-gate-b-bypass.sh` already call `plan-review step3-state` with `--auto-continuation-entry` / `--gate-b-bypass` (lines 94-97). `design-step3b-tail.sh` already calls `plan-review preview --variant gatec` (lines 115-117). Adding `step3-entry-preview`, `step3-continuation-entry`, `step3-gate-b-bypass`, and `step3b-tail` duplicates registry surface without new behavior.
- **Proposed resolution**: Drop those four proposed verbs from `### UPDATED: python/cli.py`. After shrinking wrappers, keep delegating to `preview` and `step3-state`. Add new verbs only where no registry entry exists today (`step3-entry`, `step3-mav`, `step3b-entry`, `step3b-sanitize`, `step35`, `step35-settle`).


### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-migration-scope-guard
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:32-41
- **Concern**: [SCOPE-REDUCTION] Plan adds new result-env, atomic-write, and run-params helpers inside `plan_review.py` despite existing shared implementations.. Scenario: `design_lifecycle.phase_driver_read_result_env` and `design read-result-env` already enforce allowlisted KEY=VALUE reads with symlink refusal (`python/design_lifecycle.py:27-49`, `python/cli.py:157`). `plan_review._write_atomic` already exists (`python/plan_review.py:1003-1006`). `design_postplan.py:122` already expects a shared JSON-bool reader (`plan-review json-get-bool`) that is not registered. Re-porting these in `plan_review.py` risks divergent trust boundaries.
- **Proposed resolution**: Reuse `design_lifecycle.phase_driver_read_result_env` / `design read-result-env` and `_write_atomic`. Add one shared stdlib JSON-bool helper (for example in `design_lifecycle.py`) and wire `design_postplan.py` plus Step 3.5/3b tail reads to it. Delete the duplicate-helper bullets from the plan.




### FINDING_1: Step-3 completion sentinel contract (`.completed/step-3` / `step-3.5`)
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Generic
- **Severity**: blocking
- **Concern**: The native port must preserve the split completion-sentinel contract: the wrapper EXIT trap writes only `.completed/step-3` (for the Step 3 background poll guard, #4489); the loop’s terminal success path writes both `step-3` and `step-3.5`; bail-out statuses (`main-agent-vote-required`, `main-agent-apply-required`, `per-round-approval-required`) must not write `step-3.5`. The plan cites pause/resume marker bytes but does not pin these semantics in the loop port, SKILL.md, the retained wrapper contract, or migrated tests. Dropping or collapsing write sites can leave the bg poll guard stuck, fire Step 3b/Gate C early, or skip Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin native loop completion: write `.completed/step-3` on terminal paths; preserve the existing split where bail-out statuses (`main-agent-vote-required`, `main-agent-apply-required`, `per-round-approval-required`) do not write `.completed/step-3.5`; keep wrapper `_step3_review_guarantee_completed_sentinels` writing only `step-3`
  - From Cursor-Pragmatic: A native port that drops the wrapper trap or collapses the two write sites can leave the bg poll guard stuck, fire Step 3b/Gate C early, or skip Gate B when `step-3.5` appears too soon. Spell out in `python/plan_review.py` and `design-step3-review.sh` sections: preserve wrapper EXIT trap (step-3 only, after review entry, not on `--read-result-env`/prelaunch exits); preserve loop success `step3_loop_write_completed_step3` (step-3 + step-3.5); add pytest asserting both paths.
  - From Codex-Generic: Add the sentinel guarantee to the retained wrapper contract and migrate the existing positive and --read-result-env negative assertions into the new pytest or thin-wrapper integration coverage.


### FINDING_2: RUN_STEP3 dedup/timing defaults target retired shell paths
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `RUN_STEP3_DEDUP_PLAN_SH` and `RUN_STEP3_RECORD_TIMING_SH` still default to `gate-b-dedup-plan.sh` and `record-plan-review-round-timing.sh`, which have no on-disk bodies after `_LEGACY_ASSETS` removal. Unless every caller sets overrides, the native loop hits dead paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In native loop, default unset overrides to `python3 …/cli.py plan-review gate-b-dedup` and `… plan-review record-round-timing`; document the new defaults in `docs/python-migration.md` with `RUN_STEP3_CONTINUATION_SH`


### FINDING_3: `plan-review run --mode loop` lacks validate-before-write entry guard
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Without a pinned `validate_design_tmpdir` entry contract at the top of `run_step3_review` / `run_main`, direct CLI invocation can persist `review-round-count.txt` and result-env files before allowlist validation, regressing DESIGN_TMPDIR protection when the wrapper is bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require `validate_design_tmpdir` at the top of `run_step3_review` / `run_main` before any DESIGN_TMPDIR mutation; add pytest replacing `test_embedded_run_step3_review_round_paths_validate_before_quiet`


### FINDING_4: Terminal state staging for postplan-failed and panel-init failures
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan does not call out porting `design-stage-terminal-state.sh` staging for terminal failure outcomes before deleting `lib-step3-prelaunch-failure.sh` and related shell bodies. Omitting loop `postplan-failed` staging or prelaunch/entry `panel-init-failed` staging diverges `SUMMARY_OUTCOME` routing (`failed-postplan`, `failed-judge-panel`) from today’s bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When native `emit_envelope` sees `postplan-failed`, call the same terminal-state staging helper before persisting the result env (mirror bash lines 112-114 and 41-68)
  - From Cursor-Requirements: Name and port _step3_review_stage_panel_init_failed _step3_entry_panel_init_failed_exit and step3_stage_postplan_failed before deleting the lib


### FINDING_5: `--starting-round` validation not specified for native `plan-review run`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Embedded `validate_step3_loop_starting_round` and wrapper argv checks reject empty, non-numeric, and `<=0` values. A native CLI without the same guard can start the loop with invalid cursor state and corrupt `review-round-count.txt` / phase files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port starting-round validation into `run_main` argparse (positive integer only) and add a pytest case for rejected values


### FINDING_7: `plan-review step3-entry` omits scope-anchor assembly and entry panel-init-failed exits
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The native `step3-entry` port plan omits full scope-anchor assembly (strip-body, outline, verbal fallbacks, validate) and `_step3_entry_panel_init_failed_exit`. Empty or invalid scope anchors can reach reviewers, and entry failures can skip terminal staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Port strip-body outline verbal fallbacks validate and _step3_entry_panel_init_failed_exit into native step3-entry with pytest


### FINDING_8: Collector STATUS-gating parity test removed without replacement
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Removal of the collector STATUS-gating parity test in `python/test_plan_review.py` without an explicit replacement risks regressing behavior where every collect step fails and rounds record `panel-failed` like #4417.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit port bullet and pytest for agent collect-results STATUS gating NOT_SUBSTANTIVE and COLLECT_FAILURE_COUNT


### FINDING_9: Thin-wrapper keep list omits resume argv and post-loop escalation tail
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The thin-wrapper retention plan for `design-step3-review.sh` omits resume argv handling (`--starting-round`, phase files) and the post-loop escalation / terminal Final-summary tail (`write_resume_state`, `record-report-evidence`, `SUMMARY_OUTCOME` exits). Mid-loop resume or terminal escalation paths can be lost during the shrink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: List resume validation write_resume_state record-report-evidence and SUMMARY_OUTCOME exits in wrapper contract


### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:390-461
- **Concern**: [SCOPE-REDUCTION] Retired internal docs are optional in the plan. Scenario: The plan says to delete or rewrite retired .md siblings, then says to append those .md paths to python/migrated-scripts.tsv. make lint-retired-scripts fails if a manifest path is still present in the tree.
- **Proposed resolution**: Make review-design-step3-loop.md and plan-review-continuation.md delete-only when they are added to python/migrated-scripts.tsv.




### FINDING_1: gzip-only plan-review-loop.sh omitted from port inventory
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The scope anchor lists `review-design-step3-loop.sh` and related on-disk wrappers, but not the gzip-embedded `plan-review-loop.sh` single-round body. `run_plan_review_round()` in `python/plan_review.py` still delegates to that embedded asset via `_run_legacy(_DESIGN_REVIEW_LOOP, ...)`, and `test_embedded_plan_review_loop_uses_migrated_collector` pins its collector `STATUS` / `COLLECT_FAILURE_COUNT` semantics. Porting only the on-disk loop file risks leaving the embedded round body unported or silently broken after `_LEGACY_ASSETS` removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Merge plan-review-loop.sh round-body semantics into the native run_plan_review_round (or equivalent internal entry) explicitly in the port checklist; do not rely on the on-disk review-design-step3-loop.sh file alone


### FINDING_2: post-revise write-design-round-meta.sh missing from retained-subprocess inventory
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: After a successful revise, `review-design-step3-loop.sh` invokes `scripts/write-design-round-meta.sh` (with optional `WRITE_DESIGN_ROUND_META_SH` override) to refresh `round-meta.json` with revise tier/status for Review Phase Detail and final-summary rendering. The port plan does not list this subprocess in its retained-inventory or native post-revise path, so native cutover may skip metadata refresh and lose per-round revise tier and counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `scripts/write-design-round-meta.sh` (optional `WRITE_DESIGN_ROUND_META_SH` override) to the explicit retained-subprocess inventory in `python/plan_review.py` and call it from the native post-revise path; add pytest asserting `round-meta.json` creation after a successful revise


### FINDING_3: lib-step3-prelaunch-failure.sh deletion without wrapper-callable CLI surface
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Concern**: The plan deletes `lib-step3-prelaunch-failure.sh` and routes prelaunch handling to native helpers, but does not register any `python/cli.py plan-review` verb the thin `design-step3-review.sh` / `design-step3-entry.sh` wrappers can invoke. Those wrappers currently source the library to write `.step3-review-result.env`, emit the `panel-init-failed` stdout envelope, and stage terminal state on monitor-mode or scope-anchor prelaunch failure. Without a registered CLI entry, the wrapper either calls removed shell functions or cannot stage the envelope before exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add a minimal registered plan-review prelaunch-failure or stage-panel-init-failed verb and make the wrapper call it before deleting the shell library.



### FINDING_1: Result-env writer lacks symlink refusal
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The port plans to reuse `plan_review._write_atomic` (or equivalent native persistence) for `.step3-review-result.env`, but that helper does not refuse symlink targets. Bash `phase_driver_write_result_env` refuses symlinks, and `SECURITY.md` treats result-env paths as a trust boundary. A symlinked `.step3-review-result.env` can be followed or replaced during native persist, breaking parity with the bash contract and the documented security model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use session_env._atomic_write (or add design_lifecycle.phase_driver_write_result_env with the same symlink and O_NOFOLLOW rules) for result-env writes; do not claim _write_atomic is symlink-safe
  - From Cursor-Pragmatic: Port `step3_loop_persist_envelope` merge semantics explicitly (same merge-key set and CRLF strip for `PLAN_REVIEW_CONTINUE_REASON`). Add a shared symlink-refusing atomic result-env writer in `design_lifecycle.py` (or harden `_write_atomic` with the bash-equivalent checks) and use it from the native persist path; add a pytest that pre-seeds `.step3-review-result.env` and asserts merged keys survive the next persist.


### FINDING_2: Gate B wrapper must retain `.completed/step-3` prelude
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan omits the Gate B wrapper prelude in `design-step35.sh` that writes `.completed/step-3` (never `step-3.5`) for apply-pending loop envelopes. Shrinking the wrapper to delegate-only without porting this logic leaves the background poll guard without `step-3` on `main-agent-apply-required`, `per-round-approval-required`, and `postplan-operator-required` paths, which can stall Step 3.5 / Gate B orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin explicitly: keep this prelude in the thin wrapper or port identical sentinel logic into `plan-review step35` before `APPROVE_REQUESTED=` emission; add pytest (or retain wrapper harness) asserting step-3-only writes per envelope matrix


### FINDING_3: Result-env persist must preserve merge-key semantics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Bash `step3_loop_persist_envelope` merges missing keys (`TALLY_PLAN_REVIEW_STATUS`, `IMPORTANT_ACCEPTED_COUNT`, `AGGREGATOR_STATUS`, `VOTING_TALLY_FILE`, `PANEL_PRUNED_EMPTY`, `ROUND_NUM`, `PLAN_REVIEW_CONTINUE_REASON`, `REASON`) from an existing `.step3-review-result.env` before overwrite, including CRLF stripping for `PLAN_REVIEW_CONTINUE_REASON`. A naive full replace during native persist drops tally/aggregator fields and can break Gate B and wrapper stdout normalization after mid-loop resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Port `step3_loop_persist_envelope` merge semantics explicitly (same merge-key set and CRLF strip for `PLAN_REVIEW_CONTINUE_REASON`). Add a shared symlink-refusing atomic result-env writer in `design_lifecycle.py` (or harden `_write_atomic` with the bash-equivalent checks) and use it from the native persist path; add a pytest that pre-seeds `.step3-review-result.env` and asserts merged keys survive the next persist.


### FINDING_4: Native panel dispatch omits reviewer-prune contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The native panel dispatch plan omits the `reviewer-prune.sh` contract from `plan-review.md`. Porting only static/dynamic slot generation and waterfall keeps gzip panel behavior for rounds 1–2 and 5 but drops rounds 3–4 manifest filtering, `--prune-round-num` threading, pre-prune sidecar preservation, and `PANEL_PRUNED_EMPTY` early-complete handling. That changes Step 3 panel composition despite the non-goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `plan_review_panel.py` and native `run_plan_review_round`, explicitly port prune-round forwarding, rounds 3-4 manifest filtering via `scripts/reviewer-prune.sh`, pre-prune sidecar preservation, and `PANEL_PRUNED_EMPTY` result-env fields; add pytest coverage for prune-round propagation and pruned-empty continuation (today only in `skills/design/scripts/test-step3-review-cap.sh`)


### FINDING_5: `main-agent-vote-required` must not map to `LOOP_STATUS=complete`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan includes `main-agent-vote-required` in a `LOOP_STATUS=complete` bail-out mapping. Current contracts keep `LOOP_STATUS=main-agent-vote-required` for MainAgent vote routing. Mapping it to `complete` can hide the MAV state and route legacy `LOOP_STATUS` handling through the wrong Gate B path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep LOOP_STATUS=main-agent-vote-required for main-agent-vote-required. Only map main-agent-apply-required, per-round-approval-required, and postplan-operator-required to LOOP_STATUS=complete


### FINDING_6: Step 3b tail must retain Step 4 tail side effects
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Reducing `design-step3b-tail.sh` to preview-only risks dropping Step 4 tail contracts the orchestrator depends on: `SKIP_APPROVE_REQUESTED_GATEC`, rejected-findings markers, FINALIZE compatibility, and `.completed/step-4` before Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep those side effects in the thin wrapper or add a native plan-review step3b-tail verb that performs them before delegating to preview


### FINDING_7: Round-meta refresh default must execute the bash script
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan shows the round-meta default command as `python3` applied to a bash script. When `WRITE_DESIGN_ROUND_META_SH` is unset, that refresh can fail silently and leave `round-meta.json` stale after a successful revise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Default to executing scripts/write-design-round-meta.sh directly, or via bash, and keep override behavior unchanged



### FINDING_1: Makefile loop harness still targets removed embedded pytest names
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `test-review-design-step3-loop` in the Makefile still selects pytest cases via `-k 'embedded_review or embedded_run_step3_review or embedded_waterfall or run_legacy'`. After the G3 port removes embedded-asset parity tests, that selector can collect zero tests (pytest exit 5) and break `test-harnesses-16`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin Makefile:519-520 to native loop/panel selectors (for example cap_reached or tally_error_rollback plus new native round/continuation tests) when embedded tests are removed


### FINDING_2: Step 3b-tail plan inverts step-4 sentinel vs Gate C preview ordering
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan changes when `.completed/step-4` is written relative to the Gate C preview path. Current `design-step3b-tail.sh` runs the Gate C timing mark and preview, emits `SKIP_APPROVE_REQUESTED_GATEC`, then creates `.completed/step-4`. The plan would write the sentinel before the Gate C preview. An interrupted or failed preview could leave Step 4 marked complete while Gate C was never surfaced, and resume may skip the missing Gate C surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan and tests to preserve current ordering: Gate C timing mark and preview first, then SKIP_APPROVE_REQUESTED_GATEC, then create .completed/step-4 after that path succeeds


### FINDING_3: RUN_STEP3_PLAN_REVIEW_LOOP_SH seam lacks a native default target
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan preserves the `RUN_STEP3_PLAN_REVIEW_LOOP_SH` override seam and says surviving `RUN_STEP3_*` hooks default to native CLI targets, but it does not register a single-round `plan-review` verb. After deleting `plan-review-loop.sh` and `_run_legacy`, an unset override can leave `run_step3_review` pointing at a deleted shell path or an unregistered command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Either call run_plan_review_round in process when the env override is unset and document RUN_STEP3_PLAN_REVIEW_LOOP_SH as override-only, or register a minimal native single-round plan-review verb before deleting the shell body



