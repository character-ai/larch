
Merging the supplied reviewer findings into one structured list (read-only; no file or repo changes).

### FINDING_1: Rename failure — contract drift and hard abort vs best-effort
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-rename-fail-behavior-output.txt
- **Severity**: important
- **Concern**: `design-init-runparams.sh` treats rename failure as a hard stop (`INIT_STATUS=rename-failed`, exit 1) before `write-run-params.sh`, while `design-init-runparams.md` still documents rename failure as `WARN=` and continue, omits `rename-failed` from the allowlist/exit table, and the #3245 plan / pre-refactor Step 0b expected best-effort rename (log warning, continue with `run-params.json`). `SKILL.md` matches the driver’s abort path, so orchestrator and script agree with each other but not with the sibling contract or prior observable behavior; transient `gh`/API rename failures can abort all of Step 0b without `run-params.json` where the old path continued with a warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rename-fail-behavior-output.txt: Align with the plan: on rename failure, `add_warn` (and optionally `append-tool-failure.sh` to `execution-issues.md` like old 5.5), keep `INIT_STATUS=ok`, emit `RENAMED=false` if unknown, and proceed to run-params; reserve exit **1** only for `env-refresh-failed` / `contract-drift`. If hard abort is intentional, update the plan, `design-init-runparams.md`, and acceptance text so they match the implementation.
  - From dyn-rename-fail-behavior-output.txt: If rename stays best-effort, drop the `rename-failed` branch and log driver `WARN=` breadcrumbs after `_init_rc=0`; if rename stays fatal, document that explicitly in Step 0b prose and drop “best-effort” wording elsewhere (e.g. clarify sub-step 5 still says best-effort for a different rename callsite).
  - From dyn-rename-fail-behavior-output.txt: Either update the `.md` to document `rename-failed` + abort semantics and drop the `WARN=` rename line, or change the script to match the current `.md` (WARN + continue, no `rename-failed`).

### FINDING_2: Partial state when rename succeeds but run-params write fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Rename runs before `write-run-params.sh`. If rename succeeds and `write-run-params` fails with `contract-drift`, the issue may already show `[DESIGNING]` without a fresh `run-params.json`. Retries can hit wrong tier/flag routing or inconsistent clarify/plan gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document the partial-state retry contract in the `.md` sibling and SKILL banner, or reorder so rename is best-effort only after run-params is written if policy allows.

### FINDING_3: Step 0b router harness does not exercise production driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-step0b-router-flag-recovery.sh` duplicates jq-merge logic instead of invoking `design-init-runparams.sh` while `relevant-checks` maps driver edits to this test. Driver-only changes (e.g. `append-tool-failure` on jq failure, jq-unavailable warnings) can pass all replica cases while production merge/logging diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend the existing harness with stubbed dependencies and invoke `design-init-runparams.sh`; add cases for jq failure logging and jq-unavailable warnings.

### FINDING_4: WARN/ERROR substring dedup can suppress distinct messages
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: important
- **Concern**: In `skills/design/SKILL.md`, WARN/ERROR de-duplication uses a space-padded substring test on joined prior messages (`[[ " ${_route_warn_lines[*]} " != *" $_value "* ]]`). A later message that is a proper substring of an earlier one (e.g. `invalid-step` after `pause-load-invalid-step`) is dropped even when strings differ. Operators can miss real breadcrumbs on `LOAD_OK=false` fallthrough and other file-first + stdout merge paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-parse-safety-output.txt: De-dupe with exact membership only (e.g. loop `"${_route_warn_lines[@]}"` and `[[ "$_w" == "$_value" ]]`, or an associative array keyed by the full message). Keep `=${_line#*=}` splitting so values may contain `=`; do not use substring globbing on joined text.

### FINDING_5: Collected route WARN/ERROR arrays never re-emitted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_route_warn_lines` and `_route_error_lines` are populated during merge but not consumed afterward; there is no pre-`ROUTE` loop to print stored lines. If `result-env` read is skipped (e.g. symlink refusal) and stdout capture is empty, pause-load WARN/ERROR may not appear before ROUTE branching despite the arrays holding them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a pre-case loop printing stored WARN/ERROR lines, or remove the unused arrays.
  - From cursor-specialist-correctness-output.txt: Add explicit post-merge re-emit loop over arrays before ROUTE case, or remove unused arrays.

### FINDING_6: Re-entry guard failures lack operator-visible diagnostic
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Re-entry guard helper return 2 no longer surfaces a diagnostic WARN breadcrumb (old inline Step 0b 2.6 printed helper KV). Invalid-input reentry guard failures can fall through silently to clarify/plan routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit helper stdout as WARN on non-zero rc (especially rc 2) into route result env or orchestrator breadcrumbs.

### FINDING_7: Embedded newlines in result-env WARN/ERROR could forge ROUTE lines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: WARN/ERROR from pause-load are written to `.design-route-result.env` without newline rejection; Step 0b parses line-by-line without `phase_driver_read_result_env` sanitization on that path. An embedded newline in a value could make the orchestrator treat a forged `ROUTE=` line as a separate record and mis-route. Current pause-load tokens are fixed and safe; risk is latent if values change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate all KV values for newline/CR before `phase_driver_write_result_env`; consider enforcing the same in `phase_driver_write_result_env` globally.

### FINDING_8: Pause-marker pre-check stricter than pause loader
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` uses `grep -Fq` on a literal substring for pause pre-check while `design-pause-load.sh` uses a strict line regex. A body with a valid pause block using non-canonical whitespace may load in pause-load but be skipped by route, so `/design` runs fresh routing while the pause marker remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse the loader's marker regex or a shared helper for the route driver's resume gate.

### FINDING_9: Duplicate `validate_plain_scalar` / `validate_repo` in both drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_plain_scalar` and `validate_repo` are duplicated in `design-init-runparams.sh` and `design-route.sh`. Future argv rule changes need two edits and can diverge silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor validators into `lib-phase-driver.sh` and source from both drivers.

### FINDING_10: `plan_block_present` duplicates plan-block-read marker logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan_block_present` in `design-route.sh` duplicates marker logic from `plan-block-read.sh`. Fixes to malformed-marker handling in `plan-block-read.sh` may not reach design-route already-planned routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share one helper or call `plan-block-read.sh` for body-file presence checks.

### FINDING_11: Dual large Step 0b handoff fences in orchestrator prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two large Step 3-style handoff fences in `SKILL.md` (route and init). KV allowlist or merge-loop changes require duplicate edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider a follow-up shared snippet/helper after allowlists stabilize.

### FINDING_12: Plan acceptance enums lag landed drivers
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Acceptance `ROUTE` and `INIT_STATUS` enums omit `cancel-pause-load`, `env-refresh-failed`, `rename-failed`. Future plan-fidelity passes may treat intentional review deltas as missing work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Refresh acceptance bullets to match `design-route.md` and landed drivers.

### OOS_1: [OUT_OF_SCOPE] Fast poll exports in plan-review-loop test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` fast poll interval exports are unrelated to Step 0b extraction; no breakage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Keep or split to separate PR for clarity.

### OOS_2: [OUT_OF_SCOPE] `larch-logs` markdown lint exclusion bundled in branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-literal-counts.py` exclusion change is unrelated to Step 0b; no action required for this review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: No action required for Step 0b review.

### OOS_3: [OUT_OF_SCOPE] CI structure test pins hard-abort `rename-failed` in SKILL
- **Reviewer(s)**: dyn-rename-fail-behavior-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh:871-872` pins the `rename-failed` abort branch in `SKILL.md`, so CI encodes hard-abort rather than #3245 warn-and-continue; fixing regression requires updating that grep as well as driver/orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no separate fix bullet beyond concern; reviewer tied fix to FINDING_1 cluster)

### OOS_4: [OUT_OF_SCOPE] `_rename_seen` guard unlikely under current `tracking-issue-write.sh`
- **Reviewer(s)**: dyn-rename-fail-behavior-output.txt
- **Severity**: nit
- **Concern**: `scripts/tracking-issue-write.sh:490-508` always emits `RENAMED=true|false` on success, so the `_rename_seen` guard in `design-init-runparams.sh:196-203` is unlikely to fire in normal operation; spurious `rename-failed` would imply a broken quiet/capture contract, not missing helper KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)

### OOS_5: [OUT_OF_SCOPE] Step 0b `printf -v` only in allowlisted `case` arms — no regression
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: File-first and stdout-merge loops only call `printf -v` inside explicit `case` arms for routing keys; tampered lines like `PATH=evil` are ignored. Matches Step 3 handoff pattern; not worsened by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)

### OOS_6: [OUT_OF_SCOPE] `phase_driver_write_result_env` lacks write-side allowlist/newline checks
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: Only `phase_driver_read_result_env` filters; orchestrator does not call it on the Step 0b path. Safety relies on driver-known KVs and SKILL `case` at read time — same tradeoff as Step 3 (related to in-scope FINDING_7 for pause-load values).
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)

### OOS_7: [OUT_OF_SCOPE] Values containing `=` handled correctly
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: `${_line#*=}` / `${_pline#*=}` preserve everything after the first `=`; no defect found.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)

### OOS_8: [OUT_OF_SCOPE] `design-route.sh` pause-load parse uses fixed `case` on `_pkey`
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: No dynamic `printf -v`; only allowlisted pause-load keys applied. Driver ERROR tokens are single-token today; SKILL dedup (FINDING_4) is the main correctness risk for surfaced breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)

### OOS_9: [OUT_OF_SCOPE] Init handoff prints WARN without dedup (duplicate lines possible)
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:385-399` may print duplicate file+stdout WARNs; inconsistent with route path but lower severity and outside scout dedup focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)
