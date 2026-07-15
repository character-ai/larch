### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:872-899
- **Concern**: [SCOPE-REDUCTION] Plan requires resolving Codex fix-model arguments, but today's lint-fix path calls launch-codex-exec without --model-role fix (default role).. Scenario: Implementing fix-model resolution changes which Codex model runs versus the current wrapper path and breaks the acceptance bar for unchanged waterfall behavior (G-Py-3).
- **Proposed resolution**: Resolve Codex model args with the same default-role path launch-codex-exec uses today (no fix role); drop fix-model wording from firm steps and parity tests unless issue scope explicitly changes model policy.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:872-899
- **Concern**: [SCOPE-REDUCTION] Plan requires resolving Codex fix-model arguments, but today's lint-fix path never passes `--model-role fix` to `launch-codex-exec` (default role is `default`).. Scenario: Implementing fix-role resolution changes Codex model selection and token/timing labels without any current-lane trigger; parity tests that only compare argv shape will miss the regression.
- **Proposed resolution**: Change the Codex step to resolve the existing default-role model args (same as current `launch-codex-exec` defaults) and add an explicit parity test that model args match today's wrapper-launched path.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/_vendor.py:270-283
- **Concern**: [SCOPE-REDUCTION] Reuse the existing Claude `workspace-write` profile instead of adding a lint-fix-specific Claude profile.. Scenario: `launch-claude-lint-fix` already uses `claude -p --output-format json --model <CLAUDE_CI_FIX_MODEL> --add-dir <repo> --allowedTools Read,Edit,Write`, which matches `workspace-write`; a new profile adds surface area with no argv delta.
- **Proposed resolution**: Plan Claude adoption as `CLAUDE_DESCRIPTOR`/`workspace-write` plus lane-owned lint-fix preamble/postprocess hooks only; skip a new Claude argv profile unless a byte diff is documented.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py:677-682
- **Concern**: [SCOPE-REDUCTION] Pin use_config_context=false for lint-fix Cursor run_vendor_launch calls. Scenario: The plan says configuration isolation/cleanup but today's _run_cursor only runs cursor_auth_export_env and never enters cursor_config_context. run_vendor_launch defaults use_config_context to true for Cursor, which mkdtemp-copies cli-config and changes auth/preflight behavior versus the export-only path.
- **Proposed resolution**: Pass use_config_context=False on every lint-fix Cursor launch and replace configuration isolation/cleanup wording with auth-export parity. Do not enable cursor_config_context unless a measured behavior gap requires it.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:872-899
- **Concern**: [SCOPE-REDUCTION] Preserve default Codex model role, not fix role. Scenario: Plan text says resolve Codex fix-model arguments but _build_codex_argv never passes --model-role and launch-codex-exec defaults to codex_role=default; switching to fix role changes the selected model without issue scope
- **Proposed resolution**: Resolve model args with the same codex_role the wrapper uses today (default) and add an exact parity test on the resolved -m value ### 1. Pin `use_config_context=false` for lint-fix Cursor (correctness) Today's `_run_cursor` uses export-only auth (`cursor_auth_export_env`) and never enters `cursor_config_context()`. `run_vendor_launch` defaults Cursor to config-context mode when the flag is omitted, and `ci-write` intentionally uses `use_config_context=True`. The plan lists "exported auth state" but also "configuration isolation/cleanup", which can steer implementers toward the ci-write pattern and change preflight artifacts. ### 2. Keep execute hooks on the injected `Runner` seam (architecture) Acceptance requires injected-launcher seams to remain available, and `test_checks.py` asserts `runner.calls` for `launch-codex-exec`, `run-external-agent`, `cursor-wrap-prompt`, and token follow-ups. Reusing ci_launcher-style `_execute_*_vendor` hooks would run vendors in-process and skip `runner.run`. The plan should require runner-visible launches and mapping `CommandResult` to `VendorProcessResult`. ### 3. Preserve default Codex model role ([SCOPE-REDUCTION], correctness) The plan says "resolve Codex fix-model arguments," but the current wrapper never passes `--model-role` and `launch-codex-exec` defaults to `codex_role=default`. Resolving with `codex_role=fix` would change the model without scope approval. Match today's default-role resolution and lock it with an exact `-m` parity test.
