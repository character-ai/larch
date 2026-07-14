### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_drafter.py:708-852
- **Concern**: Direct Codex drafter migration must create the raw events fallback before quota mirroring. Scenario: Plan pins missing-events fallback only under `launch_codex_exec_main` quota hook. Today `launch_codex_drafter` inherits that ordering via `_launch_codex_exec_inprocess`; a direct `run_vendor_launch` path that mirrors quota on `raw.events.jsonl` without the `{}` fallback first can leave quota/usage consumers empty on no-event runs.
- **Proposed resolution**: Add the same pre-mirror fallback step to the direct Codex drafter hook wiring (or shared Codex hook helper) and assert it in `test_external_dispatch.py` drafter coverage.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_drafter.py:683-800
- **Concern**: Direct Codex drafter must preserve `resolve_launcher_exit` return semantics. Scenario: Removing `_launch_codex_exec_inprocess` drops the launcher-stdout `LAUNCHER_EXIT` capture and the `resolve_launcher_exit(captured_text, raw, wrapper_rc)` call that maps wrapper rc 0 plus `.done`/sidecar data into the public drafter return and `status.txt.done`. A bare `VendorProcessResult.exit_code` mapping can change failure rc values and quiet-mode contracts.
- **Proposed resolution**: After `run_vendor_launch`, call `resolve_launcher_exit` against the raw output path (and any retained capture text), write `.done` from the resolved exit, and return that launcher exit; add parity tests for non-zero `.done` and sidecar-preferred failure tails.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_drafter.py:110-114
- **Concern**: Codex negotiation model-arg failures must stay pre-launch return 1 without RESPONSE_FILE. Scenario: `run_vendor_launch` calls `resolve_model` without catching `ValueError`; moving `resolve_model_args("codex")` into a shared `resolve_model` hook would raise or map through `preflight_refused` instead of today’s exit 1 and no `RESPONSE_FILE` KV
- **Proposed resolution**: Resolve Codex model args before `run_vendor_launch` (same as the Cursor model-before-runner rule) and keep the existing `_err` + `return 1` path on `ValueError`



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_drafter.py:102-160
- **Concern**: Codex negotiation `CODEX_HOME` teardown is not a `VendorFamilyHooks` hook. Scenario: Plan assigns negotiation cleanup to family hooks, but `VendorFamilyHooks` has no cleanup slot; auth `preflight_refused` inside `run_vendor_launch` can skip caller `finally` and leak `larch-codex-negotiation-home-*` dirs
- **Proposed resolution**: Pin negotiation migration to caller-side `mkdtemp` + `try/finally shutil.rmtree` around the whole launch (including shared preflight refusal), or an equivalent explicit cleanup contract in `run_negotiation_round`



