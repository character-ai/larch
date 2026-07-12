### FINDING_1: Invalid token-cap handling
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Invalid or non-positive caps must be treated as absent; invoking `check-budget` for them changes existing launcher behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse _is_positive_int from python/larch/agents/_types.py before invoking check-budget; treat absent, zero, and non-numeric caps as no-cap. Add tests mirroring test_invalid_token_budget_cap_zero_still_runs_vendor and test_invalid_token_budget_cap_abc_still_runs_vendor proving preflight and execution hooks still run.
  - From Cursor-Innovation: Implementer may call check-budget with cap=0 and get CLI rc 1 instead of launching; treat invalid caps like absent caps and add a no-invoke test
  - From Cursor-Requirements: Match production: skip `check-budget` unless the cap is a positive integer; add tests for absent, invalid, zero, and valid caps.


### FINDING_2: Cursor argv profiles
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Vendor Lifecycle Contract
- **Severity**: major
- **Concern**: Cursor read-only, CI workspace-write, implement workspace-write, and negotiation launches have distinct flags and argument ordering; one generic builder cannot preserve all production shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a third Cursor profile (or a request flag such as model_args_after_output_format) for implement vs ci workspace-write orderings; keep read-only --mode ask separate. Extend full-list argv tests to cover all three production shapes.
  - From Cursor-Innovation: Cursor CI places model args before --output-format while implement places them after; negotiation omits --output-format json entirely A single workspace-write builder cannot satisfy later launcher migration without reintroducing drift; name distinct Cursor argv variants (review-ask, ci-write, implement-write, negotiation-write) and require full-list tests per variant
  - From Cursor-Pragmatic: Add explicit Approach bullets and full-list tests: read-only includes `--mode ask` and omits `--force`; workspace-write includes `--force` and omits `--mode ask`.
  - From Cursor-Requirements: Add explicit Cursor argv profiles (review read-only, CI workspace-write, implement workspace-write) or a request field for model-placement/order; cover each with full-list argv assertions.
  - From Cursor-dyn-Vendor Lifecycle Contract: Name explicit Cursor read-only (`--mode ask`) and workspace-write (`--force`) argv builders in the plan and pin full-list tests for both shapes including `--trust`, `--output-format json`, model placement, and prompt position.


### FINDING_3: Claude argv profiles
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Vendor Lifecycle Contract
- **Severity**: major
- **Concern**: Claude review, drafter, and workspace-write launches differ in flags, ordering, and tool grants; a single read-only/workspace-write abstraction is insufficient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Parameterize allowed_tools, permission_mode, and print-flag style on the launch request (or add explicit read-only variants). Test at least the drafter, runner-read-only, and workspace-write grant sets with exact argv assertions.
  - From Cursor-Innovation: Production uses --print with --permission-mode plan and Read-only tools for review, but -p with Read,Edit,Write for CI/implement/fix paths without permission-mode Locking only two Claude modes loses --print vs -p and tool-grant differences; add explicit Claude argv profiles and golden tests for review-subprocess, drafter-read, and workspace-write shapes
  - From Cursor-Pragmatic: Add a `profile` (or equivalent) dimension to the Claude argv builder and tests, e.g. `read_only_review` vs `read_only_plan_draft` vs `workspace_write`, with separate golden argv vectors per profile.
  - From Cursor-Requirements: Spell out all three argv profiles in `_vendor.py` and add full-list tests for each, including `--print` vs `-p` and the distinct `--allowedTools` strings.
  - From Cursor-dyn-Vendor Lifecycle Contract: Split Claude read-only vs workspace-write argv builders in the plan and require full-list tests for each production shape (flag choice, order, allowedTools, add-dir, stdin prompt).


### FINDING_5: Codex argv configuration arguments
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Codex argv coverage must include trust, effort, and authentication `-c` configuration arguments, not only model and directory arguments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Production Codex argv always includes trust -c plus optional effort -c and up to five OPENAI_API_KEY auth -c pairs, not just -m and --add-dir Tests that cover only model and add-dir miss the highest-drift tokens; extend argv builders/tests for with_effort -c tokens and empty-vs-populated _codex_auth_args() branches


### FINDING_10: Retry policy
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The shared lifecycle must preserve existing authentication, transient, and empty-response retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify shared retry policy or a descriptor retry hook, and test retry success and exhaustion.


### FINDING_11: Launcher import boundary
- **Reviewer(s)**: Cursor-dyn-Vendor Lifecycle Contract, Codex-dyn-Vendor Lifecycle Contract
- **Severity**: major
- **Concern**: Direct import bans are insufficient if `_vendor.py` can transitively load launcher modules and create future import cycles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Vendor Lifecycle Contract: Extend the plan import ban and disconnection tests to forbid `agents.py`, `_claude_runner.py`, and any module that transitively imports launcher families; keep allowed imports to `_types`, `_launch_failure`, `_failure_diag`, `_run_external`, and `_auth` only.
  - From Codex-dyn-Vendor Lifecycle Contract: Enumerate allowed imports whose transitive closure excludes launcher modules, or move shared Claude helpers lower; test the import graph.


### FINDING_12: Postprocessing before usage
- **Reviewer(s)**: Cursor-dyn-Vendor Lifecycle Contract
- **Severity**: major
- **Concern**: Cursor usage is recorded from normalized postprocessed output, so usage must not run before family postprocessing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Vendor Lifecycle Contract: Reorder the shared lifecycle to run family postprocessing before usage (or make per-descriptor hook order explicit) and extend ordered-hook tests to assert postprocess precedes usage for Cursor-shaped hooks.


### FINDING_14: Failure-result lifecycle ordering
- **Reviewer(s)**: Codex-dyn-Vendor Lifecycle Contract
- **Severity**: minor
- **Concern**: Lifecycle ordering and completion suppression must be tested for both successful and nonzero process results, including hook failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Vendor Lifecycle Contract: Run ordered probes for both zero and nonzero process results and assert quota, timing/usage, postprocessing, and promotion ordering, including no promotion after hook exceptions.


### FINDING_1: Cursor argv profiles omit required subcommand and prompt flag
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Cursor production launches require `cursor agent -p ...`, but the proposed profiles and tests omit both `agent` and `-p`, allowing incompatible argv to ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `agent` and `-p` immediately after `cursor` in all four Cursor profile specs, and extend the Cursor full-list argv tests to assert both on every profile.


### FINDING_2: Codex argv profiles omit `exec`
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Production Codex launches require the `codex exec` command shape, but the proposed profiles and tests omit `exec`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: A builder or test written only from the plan can emit `codex --sandbox ...`, which is not the production command shape later pieces must match. Prefix both Codex profiles with `codex exec` in the Approach and add `exec` to the Codex full-list argv assertions.


### FINDING_3: Claude profiles lack the no-read-tools review shape
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `launch_claude_review` may omit `--read-tools-add-dir`, but the proposed profiles provide no exact Claude argv profile for that base shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a no-read-tools Claude review profile and test its exact argv and stdin behavior


### FINDING_6: Token-cap checks omit the timing step
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: Launchers pass `--step <timing_task_kind>` to `token check-budget`, but the proposed request and tests do not require this, risking incompatible cap-hit sidecars with `STEP=unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a `timing_task_kind` (or equivalent) field on the frozen launch request, pass it as `--step` in the cap-check argv, and extend the cap-command tests to pin the full argv including `--step`.


### FINDING_7: Retry exhaustion may suppress completion promotion
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The proposed lifecycle may fail to promote the terminal `.inner.done` marker after retries end with a nonzero result, even when postprocessing and accounting succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Promote completion after a terminal nonzero result when all hooks succeed. Suppress promotion only when timing, postprocessing, or usage raises. Test promotion and hook-failure suppression for both zero and nonzero results.


