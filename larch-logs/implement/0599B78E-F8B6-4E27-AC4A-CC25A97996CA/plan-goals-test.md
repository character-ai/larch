## Goal
Implement issue #4589: [IMPLEMENTING] [OOS] Embedded legacy assets in plan_review.py: defer larch_quiet_init until after session validate-design-tmpdir.

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline and Round 1 decisions.
- Keep the fix narrow:
  - Do not restore retired `.sh` source files.
  - Do not port legacy scripts to Python.
  - Do not change `_materialize_legacy_root`.
  - Do not move `source` lines.
- Regenerate only the affected `_LEGACY_ASSETS` blobs in `python/plan_review.py`.
- **Quiet/validate ordering rule (all embedded scripts)**:
  - Keep `source lib-quiet.sh` (or equivalent) at the top so `larch_err` remains available on usage/argument error paths.
  - **Remove any entry-level `larch_quiet_init`** before adding or relocating a post-validate init. Add-only late init is insufficient when a top-level init remains.
  - For each embedded script that already validates on every execution path:
    - Remove the early `larch_quiet_init`.
    - Reinsert `larch_quiet_init` immediately after the successful `session validate-design-tmpdir` command on that path.
  - For embedded scripts that do not validate on every path:
    - Add `python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir ...` on each path that canonicalizes, exports, or writes under `$DESIGN_TMPDIR` before those operations.
    - Call `larch_quiet_init` only after that path's validate succeeds.
    - Assign or export `DESIGN_TMPDIR` from the validated argument variable before `larch_quiet_init` when `lib-quiet.sh` could otherwise inherit a stale unvalidated `DESIGN_TMPDIR`.
- Use raw `_decode_asset` for:
  - `scripts/dispatch-plan-voters.sh`
  - `skills/design/scripts/dispatch-plan-review-panel.sh`
- Reason: `_decode_legacy_asset` applies runtime waterfall substitutions for those assets. Re-encoding decoded substituted text would bake the shim into the blob and lose the retired marker round-trip contract.
- Preserve the runtime substitutions in `_decode_legacy_asset`.

## Files to modify/create

### UPDATED: python/plan_review.py

Regenerate the `_LEGACY_ASSETS` blobs for these 9 embedded scripts:

- `skills/design/scripts/emit-plan.sh`
- `skills/design/scripts/finalize-plan.sh`
- `skills/design/scripts/dispatch-plan-review-panel.sh`
- `skills/design/scripts/plan-review-loop.sh`
- `scripts/dispatch-plan-voters.sh`
- `skills/design/scripts/run-step3-review.sh`
- `skills/design/scripts/tally-plan-review.sh`
- `skills/design/scripts/persist-retally-step3-env.sh`
- `skills/design/scripts/record-plan-review-round-timing.sh`

Per-script edits:

- `emit-plan.sh`
  - Remove the top-level `larch_quiet_init`.
  - Reinsert `larch_quiet_init` immediately after the existing validate command.

- `finalize-plan.sh`
  - Remove the top-level `larch_quiet_init`.
  - Reinsert `larch_quiet_init` immediately after the existing validate command.
  - Preserve the existing `FINALIZE_PLAN_STATUS missing-design-tmpdir` failure branch.

- `dispatch-plan-review-panel.sh`
  - Keep `LARCH_QUIET_DISABLE=1`, `source lib-quiet.sh`, and `source lib-prune-decision.sh` where they are.
  - Remove the top-level `larch_quiet_init`.
  - Reinsert `larch_quiet_init` immediately after the existing validate command.

- `plan-review-loop.sh`
  - Keep the `source` lines at the top.
  - Remove the top-level `larch_quiet_init`.
  - Reinsert `larch_quiet_init` immediately after the existing validate command.

- `dispatch-plan-voters.sh`
  - Keep `source "$SCRIPT_DIR/lib-quiet.sh"` and `source "$SCRIPT_DIR/lib-external-launcher-common.sh"` where they are.
  - Remove the top-level `larch_quiet_init`.
  - Reinsert `larch_quiet_init` immediately after the existing validate command.

- `run-step3-review.sh`
  - Remove the top-level `larch_quiet_init` near the top.
  - Keep `source "$SCRIPT_DIR/lib-phase-driver.sh"` where it is.
  - **Non-preview paths** (`single`, `loop`, and any shared body such as `run_step3_round_body`):
    - After required argv / `PLUGIN_ROOT` resolution and before the first `cd`, `export DESIGN_TMPDIR`, `mkdir`, sentinel write, or other write under the design tmpdir, add:
      - `python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR_ARG" || exit $?`
      - assign/export `DESIGN_TMPDIR` from the validated `DESIGN_TMPDIR_ARG` (canonicalize as the script already does, but bind `DESIGN_TMPDIR` before quiet init)
      - `larch_quiet_init`
    - Fail closed on non-zero validate exit.
    - Do not rely on the `--preview-only` validate block for these paths; `python/cli.py plan-review run` delegates directly to this embedded script with no Python pre-validation.
  - **`--preview-only` path**:
    - Keep renderer warning behavior for invalid tmpdirs.
    - Do not add a shared fail-closed validate that exits before the renderer runs.
    - Defer `larch_quiet_init` until after the existing conditional validate succeeds (for example when `_sentinel_ok`) and immediately before emit/output work, not at script entry.
    - Do not add sentinel writes before validation on preview-only.

- `tally-plan-review.sh`
  - Keep `source "$PLUGIN_ROOT/scripts/lib-quiet.sh"` where it is.
  - Remove the top-level `larch_quiet_init`.
  - Reinsert `larch_quiet_init` immediately after the existing validate command.
  - Preserve the cleanup trap and `TALLY_PLAN_REVIEW_STATUS` behavior.

- `persist-retally-step3-env.sh`
  - Keep `source "$PLUGIN_ROOT/scripts/lib-quiet.sh"` and `source "$SCRIPT_DIR/lib-phase-driver.sh"` where they are.
  - **Remove the top-level `larch_quiet_init`** (mirror `emit-plan.sh` / non-preview `run-step3-review.sh`).
  - After required argument checks and binding `DESIGN_TMPDIR` from `--design-tmpdir`, and before reading or writing under `$DESIGN_TMPDIR`, add:
    - `python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit $?`
    - `larch_quiet_init` (once, only here)
  - On the MAV retally path, `_run_legacy` may inherit orchestrator `DESIGN_TMPDIR`; rebinding from `--design-tmpdir` before validate prevents quiet logging from using a stale inherited disallowed directory.

- `record-plan-review-round-timing.sh`
  - Keep `source "$PLUGIN_ROOT/scripts/lib-quiet.sh"` where it is.
  - **Remove the top-level `larch_quiet_init`** (mirror `emit-plan.sh` / non-preview `run-step3-review.sh`).
  - After `--design-tmpdir` shape checks and before canonicalizing with `cd`, add:
    - `python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR_ARG" || exit $?`
    - assign/export `DESIGN_TMPDIR` from the validated `DESIGN_TMPDIR_ARG` before `larch_quiet_init`
    - `larch_quiet_init` (once, only here)
  - Then perform existing `cd`/canonicalization if still needed for timing paths.
  - Keep the existing non-symlink directory check unless it becomes clearly redundant during implementation.

Implementation notes:

- Use an in-memory or one-off helper to:
  - decode the raw blob,
  - edit the bash text,
  - gzip and base64 encode it,
  - wrap the string literals in the existing style.
- Use `gzip.compress(..., mtime=0)` unless preserving an existing nonzero gzip header is required for test stability.
- For `scripts/dispatch-plan-voters.sh` and `skills/design/scripts/dispatch-plan-review-panel.sh`, re-encode from `_decode_asset(_LEGACY_ASSETS[path])`, never from `legacy_asset_bytes(...)`.
- After regenerating, decode every changed asset and inspect a unified diff of old decoded text vs new decoded text.
- The decoded diff must show only:
  - removed top-level `larch_quiet_init` lines,
  - moved or reinserted `larch_quiet_init` lines after validate,
  - added `validate-design-tmpdir` lines in `persist-retally-step3-env.sh`, `record-plan-review-round-timing.sh`, and the non-preview branches of `run-step3-review.sh`,
  - `DESIGN_TMPDIR` assign/export lines tied to those validate blocks where needed,
  - any minimal needed adjacency blank-line movement.
- Do not accept formatting churn inside the decoded scripts.

### UPDATED: python/test_plan_review.py

Add decoded-asset invariant tests near the existing embedded asset tests.

**Lint-safe retired path assembly (required for all new tests)**

- Do **not** write full repo-relative retired script path literals in `python/test_plan_review.py`. The retired-script lint scans tracked files for full paths from `python/migrated-scripts.tsv`.
- Assemble every retired asset key from tuple parts and/or split basenames, matching nearby patterns such as `test_embedded_plan_review_loop_uses_migrated_collector`, `test_embedded_run_step3_review_routes_from_binary_found`, and `test_embedded_waterfall_dispatchers_call_agent_verb`.
- Example shapes:
  - `"/".join(("skills", "design", "scripts", "persist-retally-step3-env.sh"))`
  - `run_step3_name = "run-" + "step3-review.sh"` then `"/".join(("skills", "design", "scripts", run_step3_name))`
  - `dispatch_voters = "dispatch-plan-" + "voters.sh"` then `f"scripts/{dispatch_voters}"`

**Global quiet/validate ordering test**

Test intent:

- For every `_LEGACY_ASSETS` entry whose decoded body contains `larch_quiet_init`:
  - assert the body also contains `session validate-design-tmpdir`;
  - assert the first `session validate-design-tmpdir` appears before the first `larch_quiet_init`.
- Iterate `plan_review._LEGACY_ASSETS` using lint-safe assembled keys (no full retired path literals in the test source).
- Decode with `plan_review.legacy_asset_bytes(rel_path)` where `rel_path` is assembled as above.
- For `scripts/dispatch-plan-voters.sh` and `skills/design/scripts/dispatch-plan-review-panel.sh`, the substituted decoded body is acceptable for this global ordering check; assemble those keys from split basename parts.
- Include the failing asset path in assertion messages.

**Branch-specific `run-step3-review.sh` test**

- Assemble the asset key from tuple parts / split basename (same pattern as `test_embedded_run_step3_review_routes_from_binary_found`).
- Decode via `legacy_asset_bytes`.
- Assert the non-preview execution region (for example the `single` / `loop` / `run_step3_round_body` path, not only the `--preview-only` branch) contains `session validate-design-tmpdir` before its first `larch_quiet_init`.
- Use a branch-local assertion, not only the global first-occurrence ordering check.
- Include the assembled asset key in assertion messages.

**Raw waterfall marker round-trip test**

- Extend coverage beside `test_embedded_waterfall_dispatchers_call_agent_verb`.
- Assemble dispatcher keys from split basename parts (same style as `test_embedded_waterfall_dispatchers_call_agent_verb`).
- For the two dispatcher assets:
  - Decode with `plan_review._decode_asset(plan_review._LEGACY_ASSETS[assembled_key])` (raw blob, no `_decode_legacy_asset` substitutions).
  - Assert the retired waterfall shell token is still present in the raw blob (same split-string pattern as `plan_review.py` around the `_decode_legacy_asset` replacements).
- For `dispatch-plan-review-panel.sh`, also assert the pre-substitution `DISPATCH_WATERFALL_SH` assignment form remains in the raw blob.
- Keep `test_embedded_waterfall_dispatchers_call_agent_verb` unchanged on `legacy_asset_bytes(...)` for runtime substituted behavior.

### UPDATED: SECURITY.md

Update the `/design --design-tmpdir allowlist` paragraph.

Add a short sentence or clause that says embedded `_LEGACY_ASSETS` plan-review bash bodies that initialize quiet logging also validate the design tmpdir first.

Keep the existing live wrapper names.

## Edge cases

- `larch_err` is used before validation in usage and argument error paths.
  - Keep `source lib-quiet.sh` at the top.
  - Remove entry-level `larch_quiet_init`; call it only after validate on each execution path that needs quiet logging.

- `persist-retally-step3-env.sh` and `record-plan-review-round-timing.sh` currently call `larch_quiet_init` near the top before `DESIGN_TMPDIR` is bound from `--design-tmpdir`.
  - Remove that entry init; otherwise inherited orchestrator `DESIGN_TMPDIR` can receive `larch-quiet-*.log` before the late validate block runs.

- `dispatch-plan-voters.sh` and `dispatch-plan-review-panel.sh` have raw blob text that differs from runtime decoded text.
  - Re-encode raw decoded blobs, not substituted decoded blobs.
  - Raw blobs must still contain retired waterfall markers; runtime substitution remains `_decode_legacy_asset` responsibility.

- `run-step3-review.sh --preview-only` has warning-oriented behavior around invalid tmpdirs.
  - Do not turn invalid tmpdirs into quiet-log writes.
  - Do not suppress intended renderer warnings.
  - Non-preview paths must not inherit preview-only validation placement.

- `record-plan-review-round-timing.sh` and non-preview `run-step3-review.sh` canonicalize tmpdir arguments with `cd`.
  - Validate the argument variable first.
  - Bind/export `DESIGN_TMPDIR` from the validated argument before `larch_quiet_init`.
  - `lib-quiet.sh` prefers an already-set `DESIGN_TMPDIR`; without rebinding, quiet logging can write under a stale inherited disallowed directory.

## Failure modes

- Re-encoding substituted waterfall text can silently remove the legacy substitution contract.
- Leaving entry-level `larch_quiet_init` in place while adding a late validate block leaves the security regression active on inherited `DESIGN_TMPDIR` paths (`persist-retally-step3-env.sh`, `record-plan-review-round-timing.sh`).
- Initializing quiet before validation can recreate `larch-quiet-*.log` under a rejected `DESIGN_TMPDIR`.
- Adding validation too early can break usage and argument-error messages that rely on `larch_err`.
- Adding validation too late in no-validate scripts can still allow pre-validation writes under `$DESIGN_TMPDIR`.
- A global first-occurrence ordering test can pass while non-preview `run-step3-review.sh` paths still write before validation if validate exists only inside `--preview-only`.
- Calling `larch_quiet_init` before assigning `DESIGN_TMPDIR` from the validated argument can leave quiet logging bound to an inherited unvalidated path.
- Writing full retired script path literals in new tests can fail `make lint` even when the embedded-asset logic is correct.

## Testing strategy

Run:

- `python3 -m pytest python/test_plan_review.py`
- `make py-test`
- `make py-lint`
- `make lint`

Add manual decoded checks before finalizing:

- Decode all changed assets.
- Confirm every decoded `larch_quiet_init` has an earlier `session validate-design-tmpdir` on its execution path.
- Confirm `persist-retally-step3-env.sh` and `record-plan-review-round-timing.sh` have no entry-level `larch_quiet_init` and exactly one post-validate init.
- Confirm non-preview `run-step3-review.sh` contains validate-before-quiet outside the preview branch.
- Confirm `record-plan-review-round-timing.sh` binds `DESIGN_TMPDIR` before `larch_quiet_init`.
- Confirm raw blobs for the two waterfall dispatchers still contain retired markers.
- Confirm `dispatch-plan-voters.sh` and `dispatch-plan-review-panel.sh` still pass the existing waterfall dispatcher assertions on substituted bodies.
- Confirm no source `.sh` files were added.
- Confirm new tests use tuple/split-basename path assembly only (no full retired path literals that trip retired-script lint).

## Acceptance

- Every embedded `_LEGACY_ASSETS` bash body that calls `larch_quiet_init` calls `session validate-design-tmpdir` first; a new decoded-asset invariant test in `python/test_plan_review.py` asserts validate-before-quiet for all such assets and fails if any future asset regresses.
- The 7 reorder scripts (`emit-plan.sh`, `finalize-plan.sh`, `dispatch-plan-review-panel.sh`, `plan-review-loop.sh`, `dispatch-plan-voters.sh`, `run-step3-review.sh`, `tally-plan-review.sh`) have the entry-level `larch_quiet_init` removed and reinserted after the validate command; `source` lines stay at the top so `larch_err` remains available on usage/error paths.
- `run-step3-review.sh` validates before quiet on the non-preview `single`/`loop` paths; the `--preview-only` path keeps its renderer-warning behavior and adds no pre-validation sentinel write. A branch-specific test asserts validate-before-quiet outside the preview branch.
- `persist-retally-step3-env.sh` and `record-plan-review-round-timing.sh` add a `validate-design-tmpdir` call, bind `DESIGN_TMPDIR` from the validated argument before `larch_quiet_init`, and have exactly one post-validate quiet init.
- `dispatch-plan-voters.sh` and `dispatch-plan-review-panel.sh` blobs are re-encoded from raw `_decode_asset`; their raw blobs still contain the retired waterfall markers, `_decode_legacy_asset` runtime substitution is unchanged, and `test_embedded_waterfall_dispatchers_call_agent_verb` still passes. A raw-blob round-trip test asserts the markers survive.
- New tests assemble retired asset keys from tuple/split-basename parts (no full retired path literals), so the retired-script lint in `make lint` passes.
- A decode-diff of each regenerated blob (old vs new decoded text) shows only the intended quiet/validate line changes; no retired source `.sh` files are added.
- `SECURITY.md` notes that embedded `_LEGACY_ASSETS` plan-review bodies validate the design tmpdir before quiet init, keeping the existing live wrapper names.
- `make py-test`, `make py-lint`, and `make lint` pass.

diff_lines: 308

## Test plan
(no test plan section in plan-file)
