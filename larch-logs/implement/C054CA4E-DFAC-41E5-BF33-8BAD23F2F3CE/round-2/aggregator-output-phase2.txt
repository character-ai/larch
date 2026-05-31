Normalized aggregator output from the supplied reviewer slots (merged by shared behavioral risk; severity uses **important** > **latent** > **nit**).

### FINDING_1: `plan_block_present` duplicates `plan-block-read.sh` pairing logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `plan_block_present()` in `skills/design/scripts/design-route.sh` (38–58) reimplements marker pairing logic from `scripts/plan-block-read.sh`. If `plan-block-read.sh` gains new malformed-body handling, `design-route.sh` may route `already-planned` / `proceed` differently on edge-case bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helper or call `plan-block-read` in a presence-only mode.

### FINDING_2: `validate_plain_scalar` / `validate_repo` duplicated across Step 0b drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_plain_scalar` / `validate_repo` are duplicated in `design-route.sh` (23–36) and `design-init-runparams.sh` (20–41). Future argv validation changes require two edits and can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move validators into `lib-phase-driver.sh` and source from both drivers.

### FINDING_3: Step 0b WARN/ERROR harness scope and deferred vs immediate handoff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-kv-protocol-output.txt
- **Severity**: important
- **Concern**: (1) `scripts/test-design-structure.sh` (~786–787) greps `WARN)` / `ERROR)` across all of `SKILL.md` (and Step 3 satisfies it), so Step 0b can regress to array-only deferred handling while CI stays green. (2) Step 0b (`SKILL.md` 247–270) appends file-first `WARN`/`ERROR` into arrays and prints after stdout merge, diverging from Step 3 immediate `printf` precedent, Round 5 handoff wording, and `design-route.md:58` (“immediately”). Behavior may still surface pause-load messages before `ROUTE` when stdout is empty, but the three-way contract (`.md`, SKILL, Step 3) disagrees on mechanism and test precision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Scope grep/awk to ### 0b block and require immediate printf in file-first loop.
  - From cursor-specialist-correctness-output.txt: Print WARN/ERROR in file-first case branches like Step 3.
  - From cursor-specialist-testing-output.txt: Scope grep to Step 0b awk block only.
  - From cursor-specialist-edge-cases-output.txt: Scope grep to Step 0b section; require printf in .design-route-result.env loop.
  - From cursor-specialist-plan-fidelity-output.txt: Optional inline printf in WARN|ERROR case branches
  - From dyn-kv-protocol-output.txt: Update `design-route.md` to describe the deferred dedupe-and-print handoff (or change the SKILL file-first branches to immediate `printf 'WARN=%s\n'` / `printf 'ERROR=%s\n'` if immediate emission is normative).

### FINDING_4: Structure tests do not pin orchestrator fetch vs route vs clarify order or driver internal step order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-regression-output.txt
- **Severity**: important
- **Concern**: Check 24 and related greps pin orchestrator cancel-branch order and driver symbol names, not (a) orchestrator order (`issue-body.txt` fetch before `design-route.sh` before clarify), or (b) driver execution order inside `design-route.sh` (resume → title-eligibility → re-entry → verdict). Reordering pause/title/reentry/verdict or invoking the route driver before body fetch may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add line-order asserts on design-route.sh comment anchors.
  - From cursor-specialist-testing-output.txt: Add awk line-order assert on design-route.sh section comments.
  - From dyn-harness-regression-output.txt: Add awk line-order asserts: in SKILL Step 0b, `^2\. \*\*Fetch issue` before `design-route.sh` / `2.5. **Route driver**` before `^3\. \*\*Clarify loop`; in `design-route.sh`, `title_has_lifecycle_reject_prefix` / `# 2. Title` before `design_reentry_marker_hit` / `# 3. Re-entry` before `# 4. Verdict`.

### FINDING_5: Rename stdout parsing can flip `RENAMED=true` on normal two-line output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-compat-output.txt
- **Severity**: important
- **Concern**: `design-init-runparams.sh` (188–193) matches `_rename_out` with a single-line `case` while `tracking-issue-write.sh rename` emits two `emit_kv` lines (`RENAMED=…` and `NEW_TITLE=…`). A normal `RENAMED=false\nNEW_TITLE=…` response does not match `RENAMED=false)` and falls through to `*) RENAMED=true`, misreporting a no-op rename. Merging stderr via `2>&1` can worsen non-matching output. `test-step0b-router-flag-recovery.sh` case 8 stub prints only one line and does not catch this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Default to RENAMED=false with WARN= on non-matching output.
  - From dyn-bash-compat-output.txt: Parse rename stdout line-by-line (same KV loop used elsewhere), or match with a multiline-safe test (e.g. `grep -q '^RENAMED=false$'` on each line) and default to `RENAMED=false` on unknown output instead of `RENAMED=true`.

### FINDING_6: Pause-load non-zero exit hard-aborts via `cancel-pause-load` instead of soft fallthrough
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: When the issue body has a pause marker but `design-pause-load.sh` exits non-zero (crash/usage), `design-route.sh` (217–221) routes `cancel-pause-load` instead of `LOAD_OK=false` fallthrough. Operators may lose clarify / already-planned routing that older inline behavior allowed after breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat non-zero rc like soft failure (emit ERROR, continue steps 2-4) or document cancel-pause-load in acceptance.
  - From cursor-specialist-testing-output.txt: Stub-test pause marker with LOAD_OK=false and non-zero rc expects proceed/clarify; or make loader exit 0 on soft failure.

### FINDING_7: Missing `MARKER_AGE` / `MARKER_TTL` orchestrator defaults before reentry guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `MARKER_AGE=0` / `MARKER_TTL=300` orchestrator defaults were removed from `SKILL.md` (235–236, 296–297). With missing KVs, arithmetic uses 0 and banners show empty age/TTL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore defaults before route case or fail closed when age/TTL unset.

### FINDING_8: `cancel-pause-load` ROUTE value missing from plan acceptance / allowlists
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Driver and SKILL implement `ROUTE=cancel-pause-load`, but plan acceptance and harnesses keyed to the original six-value enum do not list it, so acceptance audits fail despite matching `design-route.md` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update acceptance and allowlists to include cancel-pause-load.
  - From cursor-specialist-plan-fidelity-output.txt: Update acceptance and structure tests or fold behavior into a documented enum value

### FINDING_9: Missing structure-test pin for resume-path `write-design-current-env.sh` `${REPO:+--repo}`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required grep for resume-path `write-design-current-env.sh ${REPO:+--repo}` is absent though SKILL implements it. Fork/multi-remote resume env refresh can regress to hub-default `gh` remote without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Step-0b-scoped grep for _wdce_resume_args and ${REPO:+--repo on write-design-current-env.sh.

### FINDING_10: Missing CI pins for pre-`ROUTE` WARN/ERROR re-emit and `LOAD_OK=false` fallthrough prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned greps for pre-`ROUTE` WARN/ERROR breadcrumbs and `LOAD_OK=false` fallthrough prose were not added. Orchestrator could stop re-emitting pause-load warnings before `case ROUTE`, leaving corrupt-pause clarify/plan gates untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep Step 0b for fallthrough prose and _route_warn_lines/_route_error_lines emit before case ROUTE.
  - From cursor-specialist-plan-fidelity-output.txt: Add grep for pre-branch ERROR/WARN prose in Step 0b block

### FINDING_11: No behavioral tests for `plan_block_present` routing logic
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `plan_block_present` (38–51, 271–278) has only `MARK_START`/`MARK_END` string pins, not stub-body table tests. Malformed `larch:plan` bodies could route `already-planned` incorrectly; `test-plan-block.sh` does not cover `design-route.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-body table tests invoking design-route.sh for absent/malformed/well-formed plan markers.

### FINDING_12: No offline harness for full `design-route.sh` routing matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No offline harness executes the routing matrix per plan Decision 2. Routing-order or plan-detection regressions can ship until manual `/design` smoke.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal stub-harness or document mandatory smoke matrix in PR test plan.

### FINDING_13: `test-step0b-router-flag-recovery.sh` cases 1–7 duplicate merge logic without calling driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cases 1–7 replicate jq-merge guard logic; only case 8 runs `design-init-runparams.sh`. Driver jq-merge guard or warning strings can drift from harness replica while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend harness to call design-init-runparams.sh for missing-file and jq-unavailable cases.

### FINDING_14: Pause-load output captured with `2>&1` enables spoofed `LOAD_OK` / `STEP` on merged stream
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `design-route.sh:198` captures pause-load machine output with `2>&1` and parses line-by-line into `LOAD_OK`, `STEP`, `SESSION_ID`, etc., without re-validating `STEP` in the driver. Diagnostic or subprocess lines resembling `LOAD_OK=true` / `STEP=…` can override earlier fields and yield `ROUTE=resume@…`, skipping title/reentry/clarify/plan gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Capture pause-load contract output on stdout only (no `2>&1`), or parse only an allowlisted key set and re-validate `STEP` against `step-name-registry.tsv` (and treat `LOAD_OK` as authoritative only from a single terminal line) before emitting `resume@`.

### FINDING_15: Sub-step 6 lacks `ROUTE=proceed` guard; resume skip is prose-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` sub-step 6 (334–345) has no `ROUTE=proceed` guard. On `resume@STEP`, orchestrator can run `design-init-runparams` and overwrite run-params/env contrary to the resume contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add (only when ROUTE=proceed) to sub-step 6 and/or a structure-test ordering pin for resume skip vs init invocation.

### FINDING_16: Unquoted `$_value` in WARN/ERROR dedup uses pathname expansion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unquoted `$_value` in WARN/ERROR dedup `[[ ]]` at `SKILL.md` 250–262 uses pathname expansion; glob characters in pause-load tokens can suppress or corrupt breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Quote values; use exact-match dedup instead of glob substring test.

### FINDING_17: Cached `issue-body.txt` vs `gh` re-fetch in pause-load can diverge
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Cached `issue-body.txt` vs `gh` re-fetch inside `design-pause-load` (`design-route.sh` 196–232) can disagree after mid-run issue edits, causing resume vs already-planned mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Thread body file into pause-load or single-source body reads.

### FINDING_18: Resume env refresh has no failure handling after `write-design-current-env`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Resume env refresh (`SKILL.md` 314–330) does not handle `write-design-current-env` failure; orchestrator may still print resumed banner while `/larch:pause` misses `ISSUE_NUMBER`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Capture rc after set +e; abort or warn-and-fall-back on non-zero refresh.

### FINDING_19: `emit_route_result` may print `ROUTE` on stdout when result-env write fails (exit 1)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `emit_route_result` (`design-route.sh` 185–191) emits `ROUTE` via `emit_kv` before result-env write; plan forbids `ROUTE` on exit 1. Write refusal yields exit 1 but stdout may still contain `ROUTE`, so orchestrator may branch on partial handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Write result env first or skip routing keys on stdout when write fails

### FINDING_20: `INIT_STATUS=env-refresh-failed` underdocumented vs acceptance and operator messaging
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-kv-protocol-output.txt
- **Severity**: latent
- **Concern**: `design-init-runparams.sh` emits `INIT_STATUS=env-refresh-failed` on `write-design-current-env.sh` failure (177–184), but plan acceptance lists only `{ok, contract-drift}` and `design-init-runparams.md:53` documents only `contract-drift` for `_init_rc=1`. Orchestrator aborts generically (395–397), not with contract-drift-class remediation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Extend acceptance and add orchestrator handling or document generic path
  - From dyn-kv-protocol-output.txt: Extend `design-init-runparams.md` orchestrator handoff to list both `contract-drift` and `env-refresh-failed`; add a dedicated SKILL banner for `env-refresh-failed` pointing at `write-design-current-env.sh` / `source-env.sh` diagnostics.

### FINDING_21: Init handoff prints duplicate `WARN` without route-style deduplication
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: latent
- **Concern**: Post-gate init handoff (`SKILL.md` 378–388) prints `WARN` on every file-first and stdout hit without deduplication, while route handoff dedupes then prints once (247–270). Same `WARN` from result env and `_init_out` (e.g. rename failure) can duplicate breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-protocol-output.txt: Reuse the route pattern (accumulate `WARN` lines, print once after merge) or gate stdout `WARN` printing when the value was already consumed from the file.

### FINDING_22: OR-form structure checks allow driver-only regression if literals remain in SKILL prose
- **Reviewer(s)**: dyn-harness-regression-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` (41–43, 110–112, 122–124) OR-checks fail only when literals are missing from **both** `SKILL.md` and `design-init-runparams.sh`. CI can stay green if strings remain in SKILL but are removed from the driver, weakening the “driver is authority” guarantee for `write-run-params.sh` / jq-merge warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-regression-output.txt: Split each check into a driver-required `grep` on `design-init-runparams.sh` (like the existing pins at `645-648`) plus an optional `absent "$SKILL_MD" …` guard for stale inline copies, or use `&&` so both locations must match during a transition window you explicitly want to enforce.

---

### OOS_1: [OUT_OF_SCOPE] Clarify path re-resolves `REPO` after sub-step 2
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Clarify path re-resolves `REPO` after sub-step 2 resolve (`SKILL.md` ~338). Extra `gh` resolution on clarify-only runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse sub-step 2 REPO in clarify sub-step 3.2.

### OOS_2: [OUT_OF_SCOPE] Unrelated `test-plan-review-loop.sh` poll interval change
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unrelated poll interval change bundled on branch (`skills/design/scripts/test-plan-review-loop.sh` 4–6). May alter CI duration for plan-review-loop tests only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: No action for #3245 unless CI flakes; note in PR test plan.

### OOS_3: [OUT_OF_SCOPE] `larch-logs` excluded from markdown literal-count lint
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-literal-counts.py:56` excludes `larch-logs` from markdown literal-count lint (reduces false positives from committed run logs). No action for Step 0b review.

### OOS_4: [OUT_OF_SCOPE] Reentry `for _rkv in $_reentry_out` word-splitting brittleness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `design-route.sh:258` — `for _rkv in $_reentry_out` relies on word-splitting; safe for current `MARKER_HIT=true MARKER_AGE=…` output but brittle if `REASON=` values gain spaces. Same pattern existed pre-refactor in `SKILL.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse with a `while IFS= read -r` loop or strict `MARKER_HIT=*` case on whole lines.

### OOS_5: [OUT_OF_SCOPE] File-first `printf -v` allowlist does not reject newlines in values
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SKILL.md` 245–264 file-first / stdout merge uses allowlisted `case` keys before `printf -v` (blocks arbitrary assignment) but does not reject `\n`/`\r` in values unlike `phase_driver_read_result_env`. Tmpdir trust model unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse `phase_driver_read_result_env` allowlists or reject `\n`/`\r` in values when sourcing result env.

### OOS_6: [OUT_OF_SCOPE] Rename stderr merge / pre-existing behavior class
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Rename stderr merged via `2>&1`; non-`RENAMED=*` output falls through to `RENAMED=true` — pre-existing class, not introduced by routing extraction. No hard-coded secrets, unsafe `eval`, or path traversal in changed driver `--repo` handling. `larch-logs/` churn out of scope per review instructions.

### OOS_7: [OUT_OF_SCOPE] Empty-array `[@]+` idiom in drivers
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `${WARN_LINES[@]+"${WARN_LINES[@]}"}` in `design-route.sh` and `design-init-runparams.sh` matches existing empty-array / `set -u` idiom (e.g. `scripts/launch-review.sh`).

### OOS_8: [OUT_OF_SCOPE] `local -a kvs` in `emit_route_result` on Bash 3.2
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `local -a kvs=(…)` with conditional `kvs+=()` in `emit_route_result` is valid on macOS Bash 3.2.

### OOS_9: [OUT_OF_SCOPE] `printf -v` in Step 0b fences
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `printf -v` in `skills/design/SKILL.md` Step 0b fences is available in Bash 3.1+.

### OOS_10: [OUT_OF_SCOPE] `validate_repo` regex matches existing helpers
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `[[ … =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]` in `validate_repo` matches existing repo helpers (`design-pause-load.sh`, `write-design-current-env.sh`).

### OOS_11: [OUT_OF_SCOPE] `${REPO:+--repo "$REPO"}` quoting pattern
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `${REPO:+--repo "$REPO"}` in drivers and SKILL fences correctly omits `--repo` when `REPO` is empty and quotes it when set.

### OOS_12: [OUT_OF_SCOPE] `plan_block_present` grep count / orchestrator array usage (portability OK)
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `start_count=$(grep -c …) || start_count=0` in `plan_block_present` mirrors `plan-block-read.sh:113-114` and is safe under `set -euo pipefail`. `SKILL.md` uses `for _w in "${_route_warn_lines[@]}"` without `[@]+` guard but arrays are initialized with `=()` first — safe on Bash 3.2 with `set -u`.

### OOS_13: [OUT_OF_SCOPE] Route KV key parity between driver and orchestrator
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: `emit_route_result` and SKILL `case` lists cover the same routing keys; `WARN`/`ERROR` intentionally not stored via `printf -v`. No missing driver↔orchestrator routing keys found.

### OOS_14: [OUT_OF_SCOPE] `cancel-pause-load` present in branch; not a silent protocol gap
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: `cancel-pause-load` emitted by driver and handled in orchestrator `case` with abort banner — present in diff though absent from plan acceptance ROUTE enum; reviewer treats as documentation/acceptance gap, not missing protocol wiring.

### OOS_15: [OUT_OF_SCOPE] `env-refresh-failed` KV is read before abort
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: Orchestrator reads merged `INIT_STATUS` before abort; issue is contract documentation and operator messaging, not silent KV drop (overlaps in-scope FINDING_20 for actionable doc/acceptance work).

### OOS_16: [OUT_OF_SCOPE] Harness does not assert immediate vs deferred WARN print timing
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh:786-787` only checks `WARN)`/`ERROR)` presence in `SKILL.md`, not immediate vs deferred printing — weak relative to Round 5 wording; pre-existing test precision limit (related to in-scope FINDING_3).

### OOS_17: [OUT_OF_SCOPE] Case 8 stub path adequately exercises jq-failure spy
- **Reviewer(s)**: dyn-harness-regression-output.txt
- **Severity**: nit
- **Concern**: `test-step0b-router-flag-recovery.sh` case 8 stubs are sufficient for `design-init-runparams.sh` to reach jq-merge block; `grep -Fq '--tool jq(router-flags-merge)'` on spy proves failure path despite `-s "$SPY8"` alone being insufficient.

### OOS_18: [OUT_OF_SCOPE] OR check at 122–124 largely redundant with driver pin 645–646
- **Reviewer(s)**: dyn-harness-regression-output.txt
- **Severity**: nit
- **Concern**: OR at `test-design-structure.sh:122-124` adds little beyond stricter driver-only grep at 645–646 (related to in-scope FINDING_22).
