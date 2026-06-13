### FINDING_1: Production callers still invoke retired `invoke-plan-validator.sh`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-parity-guardian, Codex-dyn-cutover-risk, Codex-dyn-scope-control, Cursor-dyn-cutover-risk
- **Severity**: important
- **Concern**: The plan retires `invoke-plan-validator.sh` but does not cut over its live production callers. After the wrapper is deleted, Step 2b/Gate B post-plan validation (`design-postplan-emit.sh` ~492) and Step 5c composed-plan publish validation (`design-publish.sh` ~343) still execute the missing script, so validation or publish fails before the design flow can complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: direct call python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file "$DESIGN_TMPDIR/composed-plan.md" under set +e with existing VALIDATE_STATUS branching; update design-publish.md and test-design-publish.sh stubs
  - From Codex-Arch: Add explicit UPDATED steps for design-postplan-emit.sh and design-publish.sh to call python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file ... directly, preserving existing KV parsing and composed-plan source-kind inference
  - From Cursor-Innovation: Add ### UPDATED: skills/design/scripts/design-publish.sh (and design-publish.md) replacing invoke-plan-validator.sh with python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file "$DESIGN_TMPDIR/composed-plan.md"; preserve set +e capture, VALIDATE_STATUS=defects-found → exit 4, and infra-fail branches
  - From Codex-Innovation: Add explicit plan steps to replace both invoke-plan-validator.sh calls with python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file ... while preserving KV parsing and composed-plan source-kind behavior; remove or retarget test-invoke-plan-validator with the retired harness
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/scripts/design-publish.sh replacing invoke-plan-validator.sh with python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file "$DESIGN_TMPDIR/composed-plan.md" (preserve set +e, VALIDATE_* KV parse, exit 4 on defects-found, and infrastructure-fail branches). Update design-publish.md and test-design-publish.sh stubs accordingly.
  - From Codex-Pragmatic: Add UPDATED steps for both callers to invoke python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file ... directly, preserving existing KV parsing, rc handling, DESIGN_TMPDIR log copy, and defects-found behavior
  - From Cursor-Requirements: Add ### UPDATED: skills/design/scripts/design-publish.sh replacing invoke-plan-validator with python3 cli.py plan validate --plan-file and update design-publish.md test-design-publish.sh scripts/test-design-structure.sh
  - From Codex-Requirements: Add design-postplan-emit.sh, design-publish.sh, their docs/tests, and test-invoke-plan-validator Makefile handling to the cutover. Call python3 "$PLUGIN_ROOT/python/cli.py" plan validate directly, preserving VALIDATE_* KVs, log copy behavior, defects-found handling, and composed-plan Tier 3 skip.
  - From Codex-dyn-parity-guardian: Add explicit updates for design-postplan-emit.sh and design-publish.sh to call python3 "$PLUGIN_ROOT/python/cli.py" plan validate directly or pipe the same ACTION through design-driver without the wrapper; update or remove the invoke-plan-validator harness and Makefile target before deleting the wrapper
  - From Cursor-dyn-cutover-risk: Add UPDATED design-publish.sh to call python3 cli.py plan validate on composed-plan.md; update design-publish.md and test-design-publish.sh
  - From Cursor-dyn-cutover-risk: Replace line 492 with python3 plan validate (or design-driver VALIDATE_PLAN_COMMANDS via updated driver); update design-postplan-emit.md
  - From Codex-dyn-cutover-risk: Add UPDATED steps for design-publish.sh and design-postplan-emit.sh to call python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file ... directly, preserving VALIDATE_* parsing and VALIDATE_LOG_FILE behavior; update their md/tests
  - From Codex-dyn-scope-control: Add design-postplan-emit.sh and design-publish.sh validation call-site cutovers to python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file ... while preserving set +e capture and VALIDATE_* parsing


### FINDING_2: Surviving harnesses and Makefile targets still reference retired shell surfaces
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-dyn-cutover-risk, Codex-dyn-cutover-risk, Codex-dyn-scope-control
- **Severity**: important
- **Concern**: After absorbed bash scripts and their harnesses are deleted and callers move to `python/cli.py`, existing integration harness stubs/assertions and Makefile shard targets still invoke or assert retired shell paths (`invoke-plan-validator.sh`, `check-plan-size.sh`, `test-invoke-plan-validator.sh`, `test-auto-fix-plan-commands.sh`, and related surfaces in `test-design-postplan-emit.sh`, `test-design-publish.sh`, `test-design-driver.sh`). Required `make lint` verification then fails stale-reference lint or loses control of plan-size/validator branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update only the affected survivor harness stubs/assertions to intercept python/cli.py plan check-size or plan validate, and remove the obsolete helper target or retarget it to the new pytest coverage
  - From Codex-Pragmatic: Retarget these Makefile targets to focused pytest selections in python/test_plan_quality.py, or remove them from shards consistently if the project accepts target removal
  - From Cursor-dyn-cutover-risk: Rewrite harness to stub plan check-size/validate via fake CLI dispatcher; add explicit UPDATED test-design-postplan-emit.sh
  - From Cursor-dyn-cutover-risk: Update harness stubs for python3 plan validate; add to plan UPDATED surfaces
  - From Cursor-dyn-cutover-risk: Retarget or remove those Makefile targets; align with pytest selections in test_plan_quality.py
  - From Codex-dyn-cutover-risk: Add both targets to the Makefile affected-target list; preferably keep target names and retarget them to focused python/test_plan_quality.py selections, or remove them and update PHONY plus shard memberships
  - From Codex-dyn-scope-control: Add test-invoke-plan-validator and test-auto-fix-plan-commands to the Makefile retarget or removal plan, with shard updates if any target is removed


### FINDING_3: Topology authority not updated for `validate-plan.sh` retirement
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan retires `validate-plan.sh` without updating the topology authority source. Once the script enters `python/migrated-scripts.tsv`, `lint-retired-scripts` flags the topology rule, topology TSV, and generated docs, and topology generation still points the plan-command validator at a deleted runtime authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an UPDATED section for skills/shared/topology.tsv, change design.plan_commands.validate authority to the new Python plan-quality surface, update .claude/rules/topology-generation.md paths if the authority changes, and regenerate docs/topology.md


### FINDING_4: `_postplan_run_plan_size` executable guard blocks Python `plan check-size` cutover
- **Reviewer(s)**: Cursor-dyn-parity-guardian
- **Severity**: important
- **Concern**: `_postplan_run_plan_size` still requires an executable `check-plan-size.sh` via `[[ -x "$_check_sh" ]]`. If the plan only swaps the invocation string but leaves the `-x` guard on the retired shell path, postplan plan-size validation fails before Python `plan check-size` can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-parity-guardian: Rewrite _postplan_run_plan_size to invoke `python3 "$PLUGIN_ROOT/python/cli.py" plan check-size` (with the same `LARCH_QUIET_DISABLE=1`, stderr capture, and rc 0/2/3 branches) and drop the `-x` guard on the retired script


### FINDING_7: Testing strategy treats `make lint` as optional despite definition of done
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Concern**: The plan makes full `make lint` optional ("if time permits") although the scope definition of done requires `make lint` green. The migration can pass focused pytest, py-lint, py-test, and relevant checks while still failing the repo lint target that includes harnesses, retired-script lint, and pre-commit checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-scope-control: Change the testing strategy so make lint is required, not if-time-permits, matching the definition of done


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:339-357
- **Concern**: [SCOPE-REDUCTION] Plan omits design-publish.sh validator cutover while retiring invoke-plan-validator.sh. Scenario: Step 5c composed-plan validation still shells out to invoke-plan-validator.sh after deletion; publish fails or skips Tier-3 skip for composed-plan.md
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-publish.sh: replace invoke-plan-validator.sh with python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file "$DESIGN_TMPDIR/composed-plan.md" under the existing set +e / VALIDATE_STATUS parse block only




### FINDING_1: `snapshot-trailers` cutover omits `.values` companion snapshot
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: A `--snapshot-trailers` cutover that only calls `plan optional-trailers snapshot-keys` (keys file) without also writing `.gate-b-optional-trailer-keys.values` breaks the harness contract. Today `snapshot_optional_trailer_keys` in bash writes keys and values together; `test-gate-b-dedup-plan.sh` expects the values sibling immediately after `--snapshot-trailers`, so trailer preservation assumptions fail before `--dedup` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `--snapshot-trailers` mode, mirror bash composite behavior: either make `snapshot-keys` also emit the `.values` sibling, or chain `snapshot-keys` then `snapshot-values` to the keys-derived path before exit 0.


### FINDING_2: Deleting `lib-plan-optional-trailers.sh` without rehoming Gate B dedup orchestration
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan retires `lib-plan-optional-trailers.sh` (and its awk helpers) but only lists Python CLI replacements for snapshot-keys/validate-keys, not the full dedup preserve/restore path. Today `gate-b-dedup-plan.sh` calls `dedup_plan_preserve_optional_trailers` from that library (pre-dedup snapshot, `dedup-plan-lines.py`, restore on failure, validate-values). Removing the lib without reimplementing that sequence breaks Gate B dedup, `test-gate-b-dedup-plan.sh`, and auto-fix trailer guards; dedup may fail or silently drop optional trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Rewrite the --dedup branch to keep dedup-plan-lines.py plus restore logic in bash but replace awk validation with plan optional-trailers validate-values (or inline the dedup function into gate-b-dedup-plan.sh using only Python CLI calls). State explicitly that dedup_plan_preserve_optional_trailers moves or is reimplemented before lib-plan-optional-trailers.sh is deleted.
  - From Cursor-Pragmatic: Keep dedup orchestration in gate-b-dedup-plan.sh: snapshot via plan optional-trailers CLI, run dedup-plan-lines.py, validate via CLI, preserve restore/breadcrumb/exit 1|2 semantics from dedup_plan_preserve_optional_trailers.


### FINDING_3: `plan validate` cutover omits `LARCH_QUIET_DISABLE` under quiet parents
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `design-postplan-emit.sh` and `design-publish.sh` call `larch_quiet_init` before capturing validator stdout. Today `validate-plan.sh` runs in a fresh bash with its own quiet init. A direct `python3 cli.py plan validate` inherits `LARCH_QUIET_ACTIVE`, so `VALIDATE_*` KVs may emit on fd 3 only; `parse_kv_from_output` on captured stdout sees empty/missing keys and treats validation as infrastructure failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Wrap every plan validate invocation from quiet parents with env LARCH_QUIET_DISABLE=1 (same pattern as current check-size capture). Register plan validate (and other contract verbs) in python/cli.py _MACHINE_STDOUT_KEYS per python-migration.md.


### FINDING_4: Python auto-fix port may drop gate-b-dedup trailer snapshot/dedup coupling
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `auto-fix-plan-commands.sh` calls `gate-b-dedup-plan.sh --snapshot-trailers` and `--dedup` for `plan.txt` targets before and after vendor edits. The plan ports auto-fix into `plan_quality.py` but does not require the Python path to keep those gate-b-dedup subprocess calls (or an equivalent CLI sequence). Auto-fix can pass revalidation while losing optional trailers or skipping dedup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document in plan auto-fix section: for plan.txt targets subprocess gate-b-dedup-plan.sh unchanged (minimum change) or call plan optional-trailers plus the same dedup bash sequence gate-b uses after Python snapshot/validate cutover.


### FINDING_5: `agent-lint.toml` S030 pins absent from migration surface
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `agent-lint.toml` still pins absorbed scripts (`compose-plan-goals-test.sh`, `revise-plan-with-waterfall.sh`, `scripts/test-revise-plan-with-waterfall.sh`, `test-parse-plan-commands.sh`, `test-validate-plan-commands.sh`, and related paths). After deletion/retarget without updating pins, `make agent-lint` fails even when pytest and `make lint` pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add agent-lint.toml to UPDATED surfaces: repoint pins to python/plan_quality.py python/test_plan_quality.py and surviving integration harnesses or drop retired harness pins when targets are deleted.


### FINDING_6: Drift-baseline delegation underspecified for Python check-size
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `check-plan-size.sh` sources `lib-drift-baseline.sh` for all `DRIFT_*` and baseline seed behavior. The plan delegates to surviving bash without specifying how under the no-shims rule. Subprocess-sourcing bash from Python is a hidden shim; re-porting full drift logic expands deferred scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Python check-size should inline only drift-baseline.env read/write/unreadable-marker semantics (lib-drift-baseline.sh is ~40 lines) matching existing KV output. Do not subprocess lib-drift-baseline.sh and do not expand into a full drift-baseline port.


### FINDING_8: Plan omits `SECURITY.md` update for migrated validator surfaces
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: After deleting retired scripts, `SECURITY.md` would still describe `validate-plan-commands.sh`, `auto-fix-plan-commands.sh`, `validate-plan.sh`, and Bash-process Tier 2 behavior. That violates the repo security-doc constraint and can fail stale-reference validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add an UPDATED SECURITY.md step with minimal replacements for the new python/cli.py plan verbs and Python process wording while preserving the existing trust-boundary semantics

**Merge note**: Nine reviewer slots collapsed to eight findings. **FINDING_2** and **FINDING_7** from the input (Cursor-Innovation and Cursor-Pragmatic on `lib-plan-optional-trailers.sh` deletion) describe the same behavioral risk and were merged. All other input findings remain distinct because they target different code paths, contracts, or surfaces.




### FINDING_1: plan validate omits validate-plan.sh log-copy and VALIDATE_LOG_FILE contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed `plan validate` Python verb does not reproduce `validate-plan.sh` log-handling: when `DESIGN_TMPDIR` is set, the bash driver copies the validator log to `$DESIGN_TMPDIR/validate-plan-commands.log` and emits `VALIDATE_LOG_FILE` pointing there; when `DESIGN_TMPDIR` is unset, it emits a stable temp log path so post-run readers are not racing `EXIT` cleanup. Downstream postplan publish and auto-fix read `VALIDATE_LOG_FILE`, and auto-fix copies from `ORIGINAL_VALIDATE_LOG_FILE` under `DESIGN_TMPDIR`. A Python implementation that only writes a scratch temp log (or prints KVs without the copy/stable-path contract) breaks validator log evidence and auto-fix log preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add --design-tmpdir (or document inherited DESIGN_TMPDIR env) to plan validate; copy the log to $DESIGN_TMPDIR/validate-plan-commands.log and emit the same VALIDATE_* KVs and exit-0-on-defects-found semantics as validate-plan.md.
  - From Cursor-Innovation: Document and implement: read DESIGN_TMPDIR from the environment (not only argv), copy the full validator log to $DESIGN_TMPDIR/validate-plan-commands.log when that directory exists, else emit a stable temp VALIDATE_LOG_FILE path matching validate-plan.sh.


### FINDING_3: Step 3 loop cutover must preserve RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH override
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan replaces the revise waterfall bash script with a Python CLI default, but does not explicitly preserve the `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` override contract. `review-design-step3-loop.sh` hardcodes `revise_sh="${RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH:-…}"`; `test-review-design-step3-loop.sh`, `test-design-pause-resume.sh`, and `scripts/test-design-multi-round-integration.sh` stub that env var. Deleting the bash script and switching the default to Python without keeping the override path breaks Step 3 loop harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Keep revise_sh="${RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH:-python3 $PLUGIN_ROOT/python/cli.py plan revise-waterfall ...}" (or equivalent) and add test-review-design-step3-loop.sh, test-design-pause-resume.sh, and test-design-multi-round-integration.sh to the survivor harness update list.
```



### FINDING_1: `design-driver.sh` lacks `PLUGIN_ROOT` bootstrap for plan-validation cutover
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `VALIDATE_PLAN_COMMANDS` cutover will call `python3 "$PLUGIN_ROOT/python/cli.py" plan validate`, but `design-driver.sh` never defines `PLUGIN_ROOT` (unlike `gate-b-dedup-plan.sh`, which bootstraps `REPO_ROOT` / `PLUGIN_ROOT` and falls back when `CLAUDE_PLUGIN_ROOT` is unset). If `CLAUDE_PLUGIN_ROOT` is empty, validation can fail or target the wrong tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the same `REPO_ROOT` / `PLUGIN_ROOT` bootstrap used in `gate-b-dedup-plan.sh` (and export `CLAUDE_PLUGIN_ROOT` when needed) before the `VALIDATE_PLAN_COMMANDS` branch




### FINDING_2: run-step1-plan-log still guards retired compose shell script
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: After deletion of `compose-plan-goals-test.sh`, the default `COMPOSE_SH` path and `[[ -x "$COMPOSE_SH" ]]` guard still target the retired shell script and Step 1 plan-log fails before Python runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit run-step1-plan-log.sh step mirroring design-postplan-emit.sh: drop the -x guard invoke python3 "$PLUGIN_ROOT/python/cli.py" plan compose-goals-test directly and only keep a RUN_STEP1 override if harnesses still need injection


### FINDING_4: normative Gate B/C docs still cite absorbed script basenames
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Normative Gate B/C reference still names `revise-plan-with-waterfall.sh` by basename only; not on plan UPDATED list. `migration_lint` matches full repo-relative retired paths only (`python/migration_lint.py`), so basename-only mentions survive script deletion and `/design` still loads `approval-gates.md` for Gate B apply semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: skills/design/references/approval-gates.md (and plan-review.md, design-driver.md) replacing absorbed script basenames with python/cli.py plan revise-waterfall / plan validate / plan check-size; extend stale-reference sweep to basename-only absorbed script names


### FINDING_5: check-plan-size.md authority not migrated with script deletion
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Authoritative plan-size contract doc not assigned migration when `check-plan-size.sh` is deleted. `approval-gates.md` cites `check-plan-size.md` as the machine contract; deleting the shell script without rewriting or retiring the doc leaves Gate B size-brake docs describing a removed runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: skills/design/scripts/check-plan-size.md repointing authority to python/plan_quality.py and plan check-size CLI semantics, or retire the doc and update approval-gates.md to the new authority in the same change



