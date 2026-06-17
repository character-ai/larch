### FINDING_1: run-step3-review.sh non-preview path lacks validate-before-quiet
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-quiet-ordering, Codex-dyn-quiet-ordering
- **Severity**: blocking
- **Concern**: `run-step3-review.sh` is treated as move-only quiet-init reordering, but `validate-design-tmpdir` exists only on the `--preview-only` branch while `larch_quiet_init` runs globally near the top. On single/loop non-preview paths the script canonicalizes `DESIGN_TMPDIR`, `cd`s, and writes CAP_ENV, mkdir, or completion sentinels without an allowlist check. Moving quiet init to after the preview-only validate line leaves the main execution path able to create `larch-quiet-*.log` and write under a disallowed `DESIGN_TMPDIR`; a global first-occurrence substring ordering test can still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit non-preview validate-design-tmpdir || exit step before the first cd/export/write under DESIGN_TMPDIR, then call larch_quiet_init immediately after successful validation. Keep preview-only warning behavior unchanged. Extend the invariant test to assert validate precedes quiet on the non-preview path, not only first textual order.
  - From Codex-Arch: Revise the run-step3-review.sh step to add a hard validate-design-tmpdir call on the non-preview path before canonicalizing DESIGN_TMPDIR_ARG and before larch_quiet_init, while keeping preview-only warning behavior unchanged
  - From Cursor-Innovation: Add session validate-design-tmpdir on the non-preview path immediately after argv checks and before cd/export/writes; call larch_quiet_init only after that validate succeeds. Keep preview-only warning behavior unchanged.
  - From Codex-Innovation: Add an explicit non-preview validate-design-tmpdir step before canonicalizing/exporting DESIGN_TMPDIR and before larch_quiet_init; keep preview invalid-tmpdir warnings unchanged; update the decoded-diff/test notes to allow this third added validate
  - From Cursor-Pragmatic: Add validate on `DESIGN_TMPDIR_ARG` at the start of `run_step3_round_body`, before `cd` and before any `larch_quiet_init`; fail closed on non-zero exit
  - From Codex-Pragmatic: Add explicit validation for the non-preview single and loop paths before their first cd/write, then call larch_quiet_init only after DESIGN_TMPDIR is set to that validated path.
  - From Cursor-Requirements: Remove the top-level larch_quiet_init; on --preview-only call larch_quiet_init only after the existing validate succeeds (or omit quiet init on preview if warnings must stay on stderr); on single/loop paths add validate-design-tmpdir on DESIGN_TMPDIR_ARG before cd/canonicalize and before quiet init; update decoded-diff acceptance to allow this third added-validate script
  - From Codex-Requirements: Revise the run-step3-review.sh bullets and decoded-diff allowlist to permit the minimal validate-design-tmpdir plus larch_quiet_init placement after PLUGIN_ROOT resolution on each non-preview path, before any DESIGN_TMPDIR writes or timing exports.
  - From Cursor-dyn-quiet-ordering: In run-step3-review.sh add fail-closed python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR_ARG" immediately before non-preview work (before cd/export, sourcing review-design-step3-loop.sh, and run_step3_round_body). Call larch_quiet_init only after that validate succeeds. For --preview-only keep renderer warning behavior: remove top-level quiet init and defer larch_quiet_init until after the existing conditional validate succeeds (e.g. when _sentinel_ok) and immediately before emit, not via a shared fail-closed validate that exits before the renderer runs.
  - From Codex-dyn-quiet-ordering: Add an explicit validate-design-tmpdir step for run-step3-review.sh non-preview mode before the first cd/export/write path, then call larch_quiet_init immediately after successful validation. Keep preview warning behavior unchanged.


### FINDING_2: Decoded-diff allowlist excludes required run-step3-review.sh validate
- **Reviewer(s)**: Cursor-Requirements, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan's decoded-diff gate allows added `validate-design-tmpdir` lines only in `persist-retally` and `record-timing`, while `run-step3-review.sh` also needs a new non-preview validate insertion. An implementer following the diff checklist can reject the required `run-step3-review.sh` change as out-of-scope formatting churn even though the script currently validates only on `--preview-only`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the decoded-diff allowlist to include run-step3-review.sh non-preview validate insertion (and any minimal per-path quiet-init moves tied to it)
  - From Codex-Innovation: Add an explicit non-preview validate-design-tmpdir step before canonicalizing/exporting DESIGN_TMPDIR and before larch_quiet_init; keep preview invalid-tmpdir warnings unchanged; update the decoded-diff/test notes to allow this third added validate
  - From Codex-Requirements: Revise the run-step3-review.sh bullets and decoded-diff allowlist to permit the minimal validate-design-tmpdir plus larch_quiet_init placement after PLUGIN_ROOT resolution on each non-preview path, before any DESIGN_TMPDIR writes or timing exports.


### FINDING_4: record-plan-review-round-timing quiet init uses unbound inherited DESIGN_TMPDIR
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-blob-contract
- **Severity**: important
- **Concern**: `record-plan-review-round-timing` validates `DESIGN_TMPDIR_ARG` but the plan calls `larch_quiet_init` before assigning/exporting `DESIGN_TMPDIR`. Because `lib-quiet.sh` prefers an already-set `DESIGN_TMPDIR`, quiet logging can write under a stale inherited disallowed directory that was never validated, even when `--design-tmpdir` points at an allowed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: After validating DESIGN_TMPDIR_ARG, assign/export DESIGN_TMPDIR to the validated canonical path before larch_quiet_init.
  - From Codex-dyn-blob-contract: Keep validate before cd, but canonicalize and bind DESIGN_TMPDIR from DESIGN_TMPDIR_ARG before larch_quiet_init; apply the same ARG-variable rule to run-step3-review placements


### FINDING_5: Invariant test checks global text order, not non-preview execution branches
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-test-coverage, Codex-dyn-test-coverage
- **Severity**: important
- **Concern**: The proposed test only asserts the first textual `session validate-design-tmpdir` precedes the first `larch_quiet_init` in the decoded body. That passes when validate exists only inside the `--preview-only` branch while loop/single paths still canonicalize `DESIGN_TMPDIR` and write before any embedded validation. `plan-review run` delegates directly to the embedded script with no Python pre-validation, unlike `emit_design_plan_preview`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit non-preview validate-design-tmpdir || exit step before the first cd/export/write under DESIGN_TMPDIR, then call larch_quiet_init immediately after successful validation. Keep preview-only warning behavior unchanged. Extend the invariant test to assert validate precedes quiet on the non-preview path, not only first textual order.
  - From Cursor-dyn-test-coverage: Add an explicit session validate-design-tmpdir on run-step3-review.sh non-preview paths before the first cd/export/write and before larch_quiet_init; keep preview-only warning behavior per plan.txt:136-138. Extend the new test with a run-step3-specific assertion that the non-preview branch contains validate-design-tmpdir before larch_quiet_init, not only a global first-occurrence check.
  - From Codex-dyn-test-coverage: Require an explicit validate-design-tmpdir on the non-preview path before canonicalizing/exporting DESIGN_TMPDIR, then call larch_quiet_init after that successful validation; update the check to cover run-step3-review execution branches, not only first textual occurrence.


### FINDING_6: Waterfall raw-marker round-trip contract is untested
- **Reviewer(s)**: Cursor-dyn-blob-contract, Codex-dyn-blob-contract
- **Severity**: important
- **Concern**: `legacy_asset_bytes` returns post-`_decode_legacy_asset` substituted bodies, and the existing waterfall test asserts only the substituted agent dispatch command. Re-encoding already-substituted text into `_LEGACY_ASSETS` would still pass pytest while baking `python3 agent dispatch-waterfall` literals into the gzip blob, removing retired `dispatch-with-waterfall.sh` markers and making `_decode_legacy_asset` substitutions no-ops. The raw round-trip contract in plan lines 17-21 would be lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-blob-contract: Re-encoding substituted decoded text into _LEGACY_ASSETS still passes pytest while baking python3 agent dispatch-waterfall literals into the gzip blob and removing retired dispatch-with-waterfall.sh markers; _decode_legacy_asset substitutions become no-ops and the round-trip contract in plan lines 17-21 is lost Add a pytest that decodes with plan_review._decode_asset(plan_review._LEGACY_ASSETS[path]) for scripts/dispatch-plan-voters.sh and skills/design/scripts/dispatch-plan-review-panel.sh and asserts the retired waterfall shell token is still present (same split-string pattern as plan_review.py:871); keep test_embedded_waterfall_dispatchers_call_agent_verb on legacy_asset_bytes for runtime behavior
  - From Codex-dyn-blob-contract: Extend the existing waterfall dispatcher test with a tiny raw decode assertion for the two keys, using _decode_asset on _LEGACY_ASSETS, that the raw blobs still contain the retired waterfall marker or pre-substitution variable assignment before legacy_asset_bytes applies substitutions.



### FINDING_1: Plan omits removing entry `larch_quiet_init` for persist-retally and record-timing
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan’s Approach and per-script bullets for `persist-retally-step3-env.sh` and `record-plan-review-round-timing.sh` say to add `validate-design-tmpdir` and a late `larch_quiet_init`, but never require removing the existing top-level `larch_quiet_init`. Those decoded bodies source `lib-quiet.sh` and call `larch_quiet_init` near the top before `DESIGN_TMPDIR` is cleared or bound from `--design-tmpdir` and before validation runs. On the MAV retally path, `_run_legacy` inherits orchestrator `DESIGN_TMPDIR`; `lib-quiet.sh` can still create `larch-quiet-*.log` under a stale or disallowed inherited directory before the planned late validate block runs. `run-step3-review.sh` explicitly says to remove the top-level quiet init; these two scripts do not, so add-only bullets leave the security regression in place.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Revise persist-retally bullets to mirror emit-plan: remove the top-level larch_quiet_init; after argv checks and DESIGN_TMPDIR assignment from --design-tmpdir, call session validate-design-tmpdir on that path, then larch_quiet_init once.
  - From Cursor-Pragmatic: Extend Approach: any embedded script with entry larch_quiet_init must remove it, not only scripts that already validate. Mirror run-step3/emit-plan bullets for persist-retally and record-timing: remove top-level larch_quiet_init; bind DESIGN_TMPDIR from --design-tmpdir; validate; then call larch_quiet_init once.
  - From Cursor-Requirements: Mirror emit-plan/run-step3 wording: remove the top-level larch_quiet_init; after binding DESIGN_TMPDIR from --design-tmpdir, call session validate-design-tmpdir on that path, then call larch_quiet_init once.


### FINDING_2: New tests may embed full retired script paths and fail `make lint`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Proposed tests may add full retired script path literals. The retired-script lint scans tracked files for full repo-relative paths from `python/migrated-scripts.tsv`. Nearby tests already split these names to avoid `make lint` failures. Following the plan literally for `run-step3-review.sh` and dispatcher paths can break `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Require the new tests to assemble all retired asset paths from tuple parts or split basenames, matching the existing test pattern. Do not write full repo-relative retired script paths in python/test_plan_review.py.


