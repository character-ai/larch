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

### FINDING_5: Preserve the owner-PID fallback
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The planned adapter-spec construction may omit the existing `LARCH_CLAUDE_PID`/`CLAUDE_PID`/PPID fallback, causing launches to fail when those environment variables are absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Derive the owner identity with the existing LARCH_CLAUDE_PID-or-PPID policy and test the missing-environment fallback

### FINDING_6: Forward child launch identity arguments
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Seeding `CHECKS_INPUT_*` rows alone does not satisfy the child identity contract; Step 6 and checks child commands also need the required repository, launch-head, fingerprint, schema, and original-argument flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Require parent JobSpec.command to forward launch-identity flags and Step 6 original args in addition to initial_merge_rows seeding
