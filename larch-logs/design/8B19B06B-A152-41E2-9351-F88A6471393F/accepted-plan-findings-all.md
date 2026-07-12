### FINDING_1: Missing `--checks-site` composite routing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The Python `step5_resume_main` surface does not preserve the `--checks-site` composite route exposed by the existing Bash launcher, so Step 5 resume can run the wrong child workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add --checks-site to step5_resume_main; in child mode when set delegate to checks_step5_resume_main; add an adapt parent test that argv --checks-site step5-review-fixes reaches checks_step5_resume_main and preserves STEP5_REVIEW_STATUS in the bgjob result env


### FINDING_2: Step 5 merge-result path mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Bgjob Migration Integrity, Codex-dyn-Bgjob Migration Integrity
- **Severity**: major
- **Concern**: `bgjob adapt` uses its generic merge environment while Step 5 review-and-fix writes to `.step5-review-result.env`; without an explicit bridge, the daemon can publish an empty or incomplete result envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In dispatch_commit_route step5_review child mode after review-and-fix, copy or publish .step5-review-result.env into the adapt merge-result-env via larch.io (or extend adapt JobSpec to honor the legacy merge path); add a regression that DONE result env contains the full Step 5 KV set
  - From Cursor-Pragmatic: In `dispatch_commit_route.py` Step 5 child mode, spell out the bridge: either teach `_step5_result_env_path()` to honor `--merge-result-env`, or atomically copy/sync from `.step5-review-result.env` into the adapt merge file before child exit; add a regression that asserts `STEP5_REVIEW_*` rows land in the merged result env.
  - From Cursor-Requirements: In dispatch_commit_route.py step5_review_main parent mode, add an explicit plan step to override JobSpec.merge_result_env to IMPLEMENT_TMPDIR/.step5-review-result.env (truncate before launch) and extend bgjob adapt to honor a pre-set merge path instead of always replacing it; pin reuse in test-step-5-review.sh and test_implement_dispatch.py.
  - From Cursor-dyn-Bgjob Migration Integrity: Add ### UPDATED: python/larch/bgjob/adapt.py to honor JobSpec.merge_result_env when set (defaulting to .step5-review-result.env for implement-step5-review) or document equivalent wiring in dispatch_commit_route.py
  - From Codex-dyn-Bgjob Migration Integrity: In dispatch_commit_route.py step5_review_main parent mode, add an explicit plan step to override JobSpec.merge_result_env to IMPLEMENT_TMPDIR/.step5-review-result.env (truncate before launch) and extend bgjob adapt to honor a pre-set merge path instead of always replacing it; pin reuse in test-step-5-review.sh and test_implement_dispatch.py.


### FINDING_3: Incomplete `run-step-checks` parent routing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: `run_step_checks_main` does not preserve the existing commit-site, checkpoint, and forked-target composite arguments, so Step 3 and Step 5 checks can lose required routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend run_step_checks_main parent mode with the existing bash flags and child argv table (checks-commit-route vs run-relevant), per-site step slug and budget mapping, and identity seeding; extend test_run_step_checks.py to cover step3 commit-site and rebase-checkpoint-4r through the Python parent


### FINDING_4: CI-fixer child rejects adapt arguments
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Requirements, Codex-dyn-Bgjob Migration Integrity
- **Severity**: major
- **Concern**: `bgjob adapt` appends `--bgjob-child --merge-result-env`, but the retained CI-fixer lane accepts neither flag, causing delegated CI-fixer children to terminate with argument-parsing errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an adapter child entrypoint that consumes these flags before invoking `ci fixer-lane`, or update its parser and map the merge path to `--bgjob-result-env`; preserve and test the existing result grammar
  - From Cursor-Innovation: Add a dedicated adapt child entrypoint in `ci_fixer_adapter.py` that accepts adapt flags and forwards `--bgjob-result-env`, or teach fixer-lane to accept/alias adapt flags; keep finalize mode synchronous and outside adapt.
  - From Codex-Requirements: Add this file to the plan and accept and validate the adapter flags, including equality with `--bgjob-result-env`
  - From Codex-dyn-Bgjob Migration Integrity: Route adapt through an adapter child entrypoint that consumes those flags and forwards the existing --bgjob-result-env contract to ci fixer-lane.


### FINDING_5: Checks identity seed is erased by adapt
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic, Cursor-dyn-Bgjob Migration Integrity, Codex-dyn-Bgjob Migration Integrity
- **Severity**: major
- **Concern**: Checks parents seed `CHECKS_INPUT_*` identity rows before launch, but adapt truncates the merge environment during launch preparation, preventing live rejoin from proving identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Seed identity rows after adapt prepares the merge path (extend JobSpec/adapt with pre-launch merge rows) or re-run classify/clear before reuse; document the ordering in the Step 3/6/run-step-checks parent adapters.
  - From Codex-Pragmatic: Atomically publish identity rows after initial child validation and before checks run, then replace them with the final validated result. Exercise reattachment while child work is still running.
  - From Cursor-dyn-Bgjob Migration Integrity: Identity pre-seed is wiped at launch adapt._prepare_launch_spec atomically truncates merge env to empty; Step 6 and run-step-checks seed CHECKS_INPUT_* before start so live rejoin classify_live_seed can return matching; without seed live rejoin fails closed (checks_result_identity.py:224-232) Extend adapt or JobSpec to write launch identity rows during prepare (under the decision lock) before daemon start, and port the seed-then-start ordering from the Bash parents
  - From Codex-dyn-Bgjob Migration Integrity: Seed identity rows after initial child validation and before checks run, then replace them with the final validated result. Exercise reattachment while child work is still running.


### FINDING_6: Generic reuse bypasses Step 5 canonical validation
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Bgjob Migration Integrity, Codex-dyn-Bgjob Migration Integrity
- **Severity**: major
- **Concern**: Generic adapt reuse validates only `BGJOB_RC` and `STEP`, while Step 5 requires canonical complete/stall envelopes, required handoff keys, and stale-result clearing. Partial or stale results could be emitted as terminal success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In parent mode, run the existing classify/canonical helpers before trusting adapt reuse; on non-matching/stale/incomplete, clear result and merge env then call adapt again (or bypass adapt short-circuit until identity matches).
  - From Cursor-Pragmatic: Before calling `start_or_reattach` for Step 5 review/resume, port the existing canonical classifier into Python (required `STEP5_REVIEW_STATUS` keys, stall vs complete rules, stale clearing); keep `test-step-5-review.sh` stall/completion reuse cases and add Python coverage for the pre-adapt gate.
  - From Cursor-dyn-Bgjob Migration Integrity: Require step5_review parent mode to run step5_canonical_result_env_state (or Python equivalent) before start_or_reattach and preserve stall clearing when registry is live but envelope is non-complete
  - From Codex-dyn-Bgjob Migration Integrity: Require step5_review parent mode to run step5_canonical_result_env_state (or Python equivalent) before start_or_reattach and preserve stall clearing when registry is live but envelope is non-complete


### FINDING_7: Step 5 liveness and cleanup semantics may change
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Bgjob Migration Integrity, Codex-dyn-Bgjob Migration Integrity
- **Severity**: major
- **Concern**: Existing Step 5 recovery requires both child and daemon liveness and unlinks partial/dead state, while adapt uses a different daemon-oriented policy and can return hard errors instead of fresh-starting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Map adapt dead/ownership errors to the existing unlink-clear-fresh-start path (matching current bash), and add harness cases for child-only-live and daemon-only-live transitions.
  - From Cursor-dyn-Bgjob Migration Integrity: Step 5 treats registry live only when child AND daemon are live; adapt reattaches when daemon is live even if child is not, and unlinks expired rows differently Reconcile with acceptance behave identically: either document intentional unification in the plan or add Step-5-specific pre-adapt registry normalization that preserves AND semantics
  - From Codex-dyn-Bgjob Migration Integrity: Reconcile with acceptance “behave identically” unless the plan documents this as an intentional policy change.


### FINDING_8: Existing tier-selection regression must be retargeted
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The thin-wrapper rewrite removes inline tier-selection snippets that an existing test reads directly, so `make py-test` can fail despite correct runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add this test to the plan and retarget it to the new Python adapter while preserving tier-field coverage
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/core/test_external_role_defaults.py` (or fold the assertion into new `ci_fixer_adapter.py` tests) so tier-field drift is pinned on the Python adapter instead of deleted shell heredocs.
  - From Cursor-Requirements: Add ### UPDATED: python/tests/core/test_external_role_defaults.py to repoint the guard at ci_fixer_adapter.py tier-selection output (or a small typed helper), and list it in Testing strategy.
  - From Codex-Requirements: Add this file to the plan and accept and validate the adapter flags, including equality with `--bgjob-result-env`


### FINDING_11: CI-fixer `--start` can emit the wrong grammar
- **Reviewer(s)**: Codex-dyn-Bgjob Migration Integrity
- **Severity**: major
- **Concern**: Completed-result reuse can cause a repeated CI-fixer `--start` to emit `BGJOB_STATUS=DONE` instead of the required `STARTED` envelope, halting the caller before finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Bgjob Migration Integrity: Translate completed-result reuse into the existing --start contract or explicitly relaunch that step while preserving the dynamic STEP and later finalize behavior.


### FINDING_1: Separate Step 5 review and resume classifiers
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Step 5 review and resume have different reuse and stale-result semantics, but the plan does not preserve separate classifiers. Sharing one classifier could reject valid resume results or reuse stale review stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split validation in `dispatch_commit_route.py`: port `step5_canonical_result_env_state` for `implement-step5-review` and `step5_resume_result_env_state` for `implement-step5-resume`; call the matching classifier before `start_or_reattach` on each parent. Add resume-specific reuse/clear tests in `test_implement_dispatch.py` or a resume harness.
  - From Cursor-Requirements: Port separate reuse validators for implement-step5-review vs implement-step5-resume and add resume-specific adapter tests


### FINDING_2: Add the JobSpec model contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: `JobSpec` is defined in `python/larch/bgjob/model.py`, but the plan does not list that file while requiring `initial_merge_rows` and caller-owned merge-path data. Without the typed model update, dispatch cannot reliably pass atomic identity seeds through `adapt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/bgjob/model.py` with `initial_merge_rows` on `JobSpec` (and any validation helpers). Wire the field through `adapt._prepare_launch_spec` and parent `JobSpec` builders in `dispatch_commit_route.py`.
  - From Codex-Arch: Add initial_merge_rows to JobSpec with validated row typing, and list model.py in the plan
  - From Cursor-Innovation: Add ### UPDATED: python/larch/bgjob/model.py with merge_result_env retention and initial_merge_rows on JobSpec, plus validation helpers used by adapt launch preparation.
  - From Codex-Innovation: Add python/larch/bgjob/model.py to the firm file set and extend JobSpec, updating affected constructors and tests 1. **[correctness] `python/larch/bgjob/model.py:21-31`** The plan extends `JobSpec` with `initial_merge_rows` but does not include the file that defines it. Without that field, dispatch cannot pass atomic identity seeds to `bgjob adapt`, so checks reattachment can lose `CHECKS_INPUT_*` rows. Add the model update and affected constructor/test changes.
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/bgjob/model.py with initial_merge_rows (and any validated merge-path fields) on JobSpec, and keep adapt.py launch prep consuming that typed surface.
  - From Codex-Pragmatic: Add `python/larch/bgjob/model.py` as UPDATED and define the typed, defaulted field there
  - From Cursor-Requirements: Add ### UPDATED: python/larch/bgjob/model.py extending JobSpec with initial_merge_rows and wire adapt.py to it
  - From Codex-Requirements: Add `### UPDATED: python/larch/bgjob/model.py` and define the typed, defaulted `initial_merge_rows` field.


### FINDING_3: Add regression coverage for adapt launch preparation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Changes to caller-selected merge paths and atomic initial rows are not reflected in the firm test file list, leaving truncation, seed preservation, and child publication behavior insufficiently specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: List `python/tests/bgjob/test_bgjob_adapt.py` as updated. Add cases for caller `merge_result_env`, `initial_merge_rows` surviving launch prep, and live-reattach with only seeded identity rows.
  - From Cursor-Innovation: Add ### UPDATED: python/tests/bgjob/test_bgjob_adapt.py covering caller-selected merge_result_env, initial_merge_rows surviving truncation, child flag forwarding to the same path, and merge-row publication after child writes.
  - From Cursor-Requirements: Add ### UPDATED: python/tests/bgjob/test_bgjob_adapt.py covering caller merge paths and preserved initial_merge_rows


### FINDING_4: Specify atomic merge publication for child modes
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan does not specify how resume, checks, and Step 6 child modes capture and atomically publish worker stdout into their distinct merge-result environments. Without that contract, `bgjob wait` can miss `NEXT_ACTION`, review status, checks relays, or commit-route rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement separate resume `JobSpec.merge_result_env` and child publication: tee captured stdout into the merge env for `implement-step5-resume`, keep `.step5-review-result.env` for review only, and test `--checks-site` plus ready-to-commit commit-route relay rows in the shared merge env.
  - From Cursor-Innovation: In each child entrypoint, require an atomic merge writer around the worker: capture stdout rows or explicit KV tuples, validate launch identity when CHECKS_INPUT_* seeds exist, write integrity-failure rows on drift, and replace merge_result_env via tmp+mv before exit. State this beside the --checks-site and checks identity bullets.
  - From Cursor-Pragmatic: Specify that step5_resume_main --bgjob-child must mirror the bash tee contract: capture the full worker stdout stream (checks-site composite, ready-to-commit commit-route branch, and review-and-fix resume) into the adapter merge env before exit, and add a regression that asserts STEP5_REVIEW_STATUS and NEXT_ACTION land in implement-step5-resume.merge.env after child completion.


### FINDING_6: Forward child launch identity arguments
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Seeding `CHECKS_INPUT_*` rows alone does not satisfy the child identity contract; Step 6 and checks child commands also need the required repository, launch-head, fingerprint, schema, and original-argument flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Require parent JobSpec.command to forward launch-identity flags and Step 6 original args in addition to initial_merge_rows seeding


