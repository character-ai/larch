### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:1107-1182; python/larch/agents/_vendor.py:637-682
- **Concern**: Plan preserves Cursor configuration isolation/cleanup and parity tests require it, but _run_cursor today uses auth export plus run-external-agent only; run_vendor_launch defaults use_config_context=True for cursor.. Scenario: Adopting the descriptor lifecycle without use_config_context=False adds cursor_config_context mkdtemp/copy behavior that is absent today, changing auth/runtime and preflight artifacts despite argv parity (G-Py-5, G-Py-13).
- **Proposed resolution**: Pin lint-fix Cursor launches to use_config_context=False; replace configuration isolation/cleanup preserve language and tests with auth-export, startup-lock, run-external-agent capture, and wrapper-log cleanup that match current _run_cursor.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:1008-1047
- **Concern**: Plan says reuse established Codex lifecycle helpers but does not bound allowed helper sources for the implement lane.. Scenario: Reusing _drafter or _ci_launcher private execute helpers couples implement lint-fix to launcher modules and invites drift when those launchers change (G-Py-12, G-Wire-3).
- **Proposed resolution**: Name allowed sources (_run_external, _auth, launch-codex-exec-equivalent hooks already used by launch_codex_exec_main) and forbid implement imports of _drafter/_ci_launcher execute bodies; lane adapters stay in checks_lint_fix or shared _run_external helpers only.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1107-1182
- **Concern**: Pin `use_config_context=False` for lint-fix Cursor `run_vendor_launch` calls.. Scenario: `run_vendor_launch` defaults Cursor launches into `cursor_config_context()` when the flag is omitted; current `_run_cursor` uses `cursor_auth_export_env()` only. Descriptor adoption with the plan's "configuration isolation/cleanup" wording can silently add mkdtemp config copying that does not exist today.
- **Proposed resolution**: Add an explicit plan step and test that lint-fix passes `use_config_context=False` and still runs the existing auth-export plus preflight path.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_lint_fix.py:1158-1182
- **Concern**: Preserve Cursor execution through `agent run-external-agent`, not negotiation-style direct subprocess.. Scenario: Current lint-fix wraps the leaf `cursor agent` argv in `run-external-agent` with `FIXER_LANE_TIMEOUT_SEC`, `--capture-stdout`, startup locking, and bash redirection to `cursor.wrapper.log`. A descriptor execute hook that runs leaf argv directly (as negotiation does) loses timeout exit `124`, stall handling, and failure diag/stderr-tail behavior that `_classify_attempt_issue` depends on.
- **Proposed resolution**: State in the plan that the Cursor execute hook must still invoke `run-external-agent` (or byte-equivalent helper) around the `lint-fix-write` leaf argv, and keep an integration test asserting that wrapper remains in injected-runner calls.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_lint_fix.py:1107-1182
- **Concern**: Cursor execute contract must keep run-external-agent and wrap-prompt transport, not only lint-fix-write argv. Scenario: The plan's Cursor parity tests target the inner cursor agent argv. Current lane code builds run-external-agent with --timeout 1800, --capture-stdout, and --output, runs cursor-wrap-prompt first, then bash exec redirect under startup lock. test_run_lint_fix_cursor_argv_and_wrap_cwd guards that stack. Descriptor-only argv tests can pass while dropping timeout, capture, wrap, or follow-up runner observability.
- **Proposed resolution**: Name the outer execute stack explicitly in checks_lint_fix.py and add parity tests for run-external-agent envelope, cursor-wrap-prompt follow-up, startup lock, and wrapper-log capture alongside lint-fix-write exact-argv assertions. ### 1. **correctness** — `python/larch/agents/_vendor.py:677-682` The updated plan tells implementers to preserve Cursor "configuration isolation/cleanup," but the live lint-fix lane never uses `cursor_config_context()`. It only calls `cursor_auth_export_env()` after preflight (`checks_lint_fix.py:915-925`, `1107-1128`). `run_vendor_launch` turns config context on by default for Cursor (`_vendor.py:677-682`), which would add temp-dir config copying that is absent today. **Suggested revision:** Require `use_config_context=False` on lint-fix Cursor launches and align the plan language with auth-export parity. Drop "configuration isolation/cleanup" unless you can point at current behavior that actually does it. ### 2. **risk-integration** — `python/larch/implement/checks_lint_fix.py:1107-1182` The dedicated `lint-fix-write` profile correctly targets the inner `cursor agent -p --trust` leaf argv, but the lane's real contract is larger. `_run_cursor` wraps that leaf in `run-external-agent` with timeout and capture (`929-961`), runs `cursor-wrap-prompt` first (`1130-1148`), then launches through bash redirect plus startup lock (`1158-1172`). `test_run_lint_fix_cursor_argv_and_wrap_cwd` locks this down (`test_checks.py:2814-2887`). The plan's Cursor test bullets do not name that outer transport, so a descriptor migration can pass while losing timeout enforcement or runner-visible follow-up commands. **Suggested revision:** Add explicit plan steps and tests for the `run-external-agent` envelope, `cursor-wrap-prompt` follow-up, startup lock, and wrapper-log capture. Keep inner `lint-fix-write` exact-argv tests, but do not retire `test_run_lint_fix_cursor_argv_and_wrap_cwd` without equivalent coverage. --- **Ledger note:** Prior accepted items (Codex hook bundle, `lint-fix-write`, Claude timing, `codex_lint_fix` label, site appendix) look addressed in the current plan text. Prior rejected/OOS items (`test_external_dispatch.py`, exit-code parsing, timeout-as-OOS, reuse-migrated-launcher-only) were not re-raised without new evidence.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1107-1182
- **Concern**: Pin lint-fix Cursor launches to use_config_context=false. Scenario: run_vendor_launch defaults cursor to cursor_config_context() when use_config_context is omitted; ci-write uses True but today's _run_cursor only calls cursor_auth_export_env() and never mkdtemp/copies a config dir
- **Proposed resolution**: Pass use_config_context=False on every lint-fix Cursor run_vendor_launch call and add a parity test that no config-context temp dir is created

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:872-1182
- **Concern**: Execute hooks must stay on the injected Runner seam, not in-process run_external_agent. Scenario: Copying ci_launcher _execute_*_vendor bodies calls _run_external_agent_with_auth_retries in-process and bypasses runner.run, breaking acceptance that injected-launcher seams remain available and the runner-call tests in test_checks.py
- **Proposed resolution**: Require lane execute hooks to invoke runner.run (or an equivalent runner-visible wrapper such as run-external-agent) and map CommandResult to VendorProcessResult; forbid in-process subprocess helpers in this lane

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1008-1048
- **Concern**: Resolve Codex with the current default role, not fix-role model arguments. Scenario: The current wrapper invokes launch-codex-exec without --model-role or --with-effort; resolving as fix changes the model source and produced argv despite the required exact parity
- **Proposed resolution**: Specify codex_role="default" and with_effort=False, and assert descriptor argv parity under distinct default and fix-model environment values
