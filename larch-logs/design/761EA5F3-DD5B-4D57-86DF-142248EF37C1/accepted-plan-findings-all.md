### FINDING_2: Preserve the site-scoped Codex prompt appendix
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Descriptor-built Codex prompts may omit the site-specific appendix that enforces sandbox and verification-split behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name _codex_lint_fix_prompt_appendix(site) preservation in the UPDATED checks_lint_fix.py steps and add a parity test that the Codex prompt includes the site-scoped appendix
  - From Cursor-Requirements: Add an explicit checks_lint_fix.py step to append the site appendix to the Codex prompt (or equivalent pre-launch hook) and add a parity test in test_checks.py


### FINDING_4: Preserve Codex isolated home, auth preflight, and refusal artifacts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Cursor-dyn-Descriptor Lane Integration, Codex-dyn-Descriptor Lane Integration
- **Severity**: major
- **Concern**: Direct descriptor execution may bypass temporary `CODEX_HOME` setup, sanitized configuration, model resolution, authentication preparation, and failure artifacts currently provided by `launch-codex-exec`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Name the temporary CODEX_HOME context, _prepare_codex_home preflight, resolved model args, authenticated executor, and parity tests for refusal and sanitized config behavior.
  - From Codex-Innovation: Add a firm `_vendor.py` descriptor-managed Codex home/config context and preflight, then test that lint-fix preserves isolated `CODEX_HOME` and its failure artifacts.
  - From Cursor-Requirements: In the Codex execute hook, mirror launch_codex_exec_main TemporaryDirectory CODEX_HOME plus _prepare_codex_home; add a refusal parity test matching current failed-attempt artifacts
  - From Cursor-dyn-Descriptor Lane Integration: _run_codex still shells out to launch-codex-exec, which wraps run_vendor_launch inside a temp CODEX_HOME and _prepare_codex_home. Direct descriptor calls that only build workspace-write argv will skip that auth setup and fail or drift Add an explicit Codex hook contract: temp CODEX_HOME, _prepare_codex_home, model_args resolution before run_vendor_launch, events/sidecar paths, promote_completion writing .done, and usage-label codex_lint_fix; reuse _drafter/_ci_launcher execute helpers where possible
  - From Codex-dyn-Descriptor Lane Integration: Specify a local Codex preflight/config hook that prepares and cleans the temporary CODEX_HOME, resolves model args, emits equivalent refusal artifacts, and add runner-seam tests for refusal and cleanup


### FINDING_5: Add a dedicated Cursor lint-fix profile
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-Descriptor Lane Integration
- **Severity**: major
- **Concern**: No existing Cursor profile reproduces the lint-fix argv, so descriptor adoption without a dedicated profile changes flags, mode, or output behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make _vendor.py and its focused profile test firm updates; add a narrow lint-fix write profile with the current --trust, model, --workspace, and prompt argv.
  - From Cursor-Innovation: Add a narrowly named lint-fix write profile to `_vendor.py` as a firm plan file, assert exact argv in `test_vendor.py`, and bind lint-fix to that profile only
  - From Cursor-Pragmatic: Promote a firm ### UPDATED: python/larch/agents/_vendor.py entry for a lint-fix-write profile and register it in _CURSOR_PROFILES; keep test_vendor.py profile-set assertion in firm scope.
  - From Cursor-Pragmatic: Promote a firm `_vendor.py` update and profile registration.
  - From Codex-Requirements: Promote _vendor.py to UPDATED and add a firm narrow lint-fix Cursor profile with only --trust, resolved model args, --workspace, and the wrapped prompt; make its focused parity test firm.
  - From Cursor-dyn-Descriptor Lane Integration: Reusing ci-write or implement-write adds --force and --output-format json; negotiation-write adds --force; review-ask adds --mode ask. test_run_lint_fix_cursor_argv_and_wrap_cwd expects cursor agent -p --trust only Promote a dedicated lint-fix-write profile from MAY_UPDATE to a firm UPDATED _vendor.py change and lock exact argv in test_vendor.py plus test_checks.py


### FINDING_6: Preserve Claude lint-fix timing ownership
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Descriptor Lane Integration
- **Severity**: major
- **Concern**: Removing `launch-claude-lint-fix` can lose Claude timing data or double-record it because outer timing is intentionally skipped for Claude outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a plan bullet: Claude execute/post hooks must emit the same `claude-lint-fix` `record-vendor-task` the wrapper writes today (or document an intentional timing contract change and update tests)
  - From Cursor-Pragmatic: Add an explicit Claude bullet: wire record_timing (record-vendor-task, task_kind claude-lint-fix, output claude-lint-fix.txt) via VendorFamilyHooks; add a test that successful Claude tier records timing without outer duplicate.
  - From Cursor-Pragmatic: Add a plan bullet: Claude execute/post hooks must emit the same `claude-lint-fix` `record-vendor-task` the wrapper writes today (or document an intentional timing contract change and update tests)
  - From Cursor-Requirements: State that successful Claude tiers record timing inside the lane (task_kind claude-lint-fix) and run_lint_fix keeps skipping outer timing when outcome.coder_tool == claude; retain both timing tests
  - From Cursor-dyn-Descriptor Lane Integration: Preserve per-attempt record-vendor-task inside Claude hooks (task_kind claude-lint-fix) and keep the run_lint_fix outer-timing skip; retain test_run_lint_fix_skips_outer_timing_for_claude_outcome


### FINDING_7: Preserve the `codex_lint_fix` usage label
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Direct descriptor execution may record Codex usage under `codex_exec` instead of the lint-fix-specific `codex_lint_fix` label.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Wire the Codex usage hook to record with label codex_lint_fix and assert the label in hook or argv parity tests


### FINDING_11:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1008-1047
- **Concern**: [SCOPE-REDUCTION] Firm Codex steps omit the launch-codex-exec hook bundle beyond argv shape. Scenario: Collapsing wrappers without naming temp CODEX_HOME auth prep events/sidecar/token-record paths timing_task_kind and usage_label codex_lint_fix drops auth isolation token ingestion or timeout mapping that argv-only parity tests will not catch
- **Proposed resolution**: Add a firm step to wire Codex through run_vendor_launch hooks that reuse launch_codex_exec_main helpers such as _codex_external_agent_execute _codex_record_vendor_usage and _codex_exec_promote or document byte-equivalent lane hooks plus hook-order parity tests


### FINDING_4: Resolve Codex using the current default role and effort settings
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Resolving Codex with fix-role model arguments could change the model source and generated argv, violating exact parity with the current wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify codex_role="default" and with_effort=False, and assert descriptor argv parity under distinct default and fix-model environment values.


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:872-899
- **Concern**: [SCOPE-REDUCTION] Plan requires resolving Codex fix-model arguments, but today's lint-fix path calls launch-codex-exec without --model-role fix (default role).. Scenario: Implementing fix-model resolution changes which Codex model runs versus the current wrapper path and breaks the acceptance bar for unchanged waterfall behavior (G-Py-3).
- **Proposed resolution**: Resolve Codex model args with the same default-role path launch-codex-exec uses today (no fix role); drop fix-model wording from firm steps and parity tests unless issue scope explicitly changes model policy.


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:872-899
- **Concern**: [SCOPE-REDUCTION] Plan requires resolving Codex fix-model arguments, but today's lint-fix path never passes `--model-role fix` to `launch-codex-exec` (default role is `default`).. Scenario: Implementing fix-role resolution changes Codex model selection and token/timing labels without any current-lane trigger; parity tests that only compare argv shape will miss the regression.
- **Proposed resolution**: Change the Codex step to resolve the existing default-role model args (same as current `launch-codex-exec` defaults) and add an explicit parity test that model args match today's wrapper-launched path.


### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:872-899
- **Concern**: [SCOPE-REDUCTION] Preserve default Codex model role, not fix role. Scenario: Plan text says resolve Codex fix-model arguments but _build_codex_argv never passes --model-role and launch-codex-exec defaults to codex_role=default; switching to fix role changes the selected model without issue scope
- **Proposed resolution**: Resolve model args with the same codex_role the wrapper uses today (default) and add an exact parity test on the resolved -m value ### 1. Pin `use_config_context=false` for lint-fix Cursor (correctness) Today's `_run_cursor` uses export-only auth (`cursor_auth_export_env`) and never enters `cursor_config_context()`. `run_vendor_launch` defaults Cursor to config-context mode when the flag is omitted, and `ci-write` intentionally uses `use_config_context=True`. The plan lists "exported auth state" but also "configuration isolation/cleanup", which can steer implementers toward the ci-write pattern and change preflight artifacts. ### 2. Keep execute hooks on the injected `Runner` seam (architecture) Acceptance requires injected-launcher seams to remain available, and `test_checks.py` asserts `runner.calls` for `launch-codex-exec`, `run-external-agent`, `cursor-wrap-prompt`, and token follow-ups. Reusing ci_launcher-style `_execute_*_vendor` hooks would run vendors in-process and skip `runner.run`. The plan should require runner-visible launches and mapping `CommandResult` to `VendorProcessResult`. ### 3. Preserve default Codex model role ([SCOPE-REDUCTION], correctness) The plan says "resolve Codex fix-model arguments," but the current wrapper never passes `--model-role` and `launch-codex-exec` defaults to `codex_role=default`. Resolving with `codex_role=fix` would change the model without scope approval. Match today's default-role resolution and lock it with an exact `-m` parity test.


