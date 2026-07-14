## Final Design Plan

## Plan

### UPDATED: python/larch/agents/_drafter.py

- Import `CODEX_DESCRIPTOR`, `CURSOR_DESCRIPTOR`, `CLAUDE_DESCRIPTOR`, `VendorLaunchRequest`, `VendorProcessResult`, `VendorFamilyHooks`, `parse_claude_envelope`, and `run_vendor_launch`.
- Migrate `run_negotiation_round`:
  - Build descriptor requests for Codex and Cursor without changing prompt text, workspace selection, output paths, model resolution, capture modes, or `RESPONSE_FILE`.
  - Resolve Codex and Cursor model arguments before invoking the shared runner. Preserve each existing `ValueError` path as `_err` plus return `1`; Codex model failures must not emit a `RESPONSE_FILE` KV.
  - Keep Codex auth setup, stdin capture, startup locking, usage recording, cleanup, and failure mapping in Codex family hooks.
  - Make the Codex negotiation `mirror_quota` hook a no-op on success and mirror only when `result.exit_code != 0`.
  - Keep Cursor auth preflight, environment export, merged output capture, and startup locking in Cursor hooks, and call `run_vendor_launch(..., use_config_context=False)` for negotiation so it does not create or export an isolated `CURSOR_CONFIG_DIR`.
  - Map shared preflight refusal and process results back to existing return codes and `RESPONSE_FILE` output.
- Migrate `launch_codex_exec_main`:
  - Preserve argument parsing, default workdir resolution, prompt sidecars, trusted-instruction handling, and the wrapper’s exit-zero contract.
  - Resolve Codex model arguments before `run_vendor_launch`; preserve the existing `_err` plus return-`1` `ValueError` path rather than translating it through shared preflight.
  - Build the Codex request with the current sandbox, add directories, resolved model arguments, prompt transport, usage label, and timing kind.
  - Use hooks for auth preparation, `_run_external_agent_with_auth_retries`, timing, usage recording, metadata append, and done-file promotion.
  - In the quota hook, create the missing-events fallback before `_mirror_codex_quota_from_events` so quota consumers retain the current ordering.
  - Preserve `LAUNCHER_EXIT`, `OUTPUT`, preflight bundles, failure diagnostics, retry behavior, capture files, and model attribution.
- Migrate `launch_codex_drafter` directly to the Codex descriptor and shared runner rather than routing its production path through `_launch_codex_exec_inprocess`.
  - Resolve Codex model arguments before `run_vendor_launch`; retain the existing `_err` plus return-`1` `ValueError` behavior rather than allowing shared hooks to remap the error.
  - Preserve trusted prompt construction, read-only sandboxing, token-record copying, launcher failure mapping, delimiter parsing, plan and summary promotion, scout filtering, dialectic pending data, status files, completion files, dirty-tree reporting, and temporary artifact cleanup.
  - Create the missing raw-events `{}` fallback before direct-drafter quota mirroring, including no-event runs, so quota and usage consumers retain stable ordering and input.
  - Retain `_launch_codex_exec_inprocess` as a thin compatibility delegate with its existing signature and `agents.py` re-export; do not use it as the migrated drafter execution seam.
- Migrate `launch_claude_drafter`:
  - Build a `drafter-read` request with the existing model, repository access, stdin prompt, timeout execution shape, and capture files.
  - Use `parse_claude_envelope` in postprocessing instead of local JSON-envelope unwrapping.
  - Keep Claude usage recording, plan parsing, status and timing output, failure diagnostics, dirty-tree reporting, completion files, and cleanup local.
- Remove superseded local argv builders, generic model scans, Cursor configuration setup, Claude envelope parsing, and imports that become unused; retain only the explicit pre-run Codex and Cursor model validation required for their existing error behavior and Cursor precedence.
- Keep `run_negotiation_round_main`, `launch_codex_exec_main`, `launch_codex_drafter_main`, `launch_claude_drafter_main`, their CLI arguments, and the `agents.py` re-export surface unchanged.

### UPDATED: python/tests/agents/test_external_dispatch.py

- Add parity tests that exercise the real `run_vendor_launch` lifecycle with injected fake executors and family hooks; use direct spies only as supplemental request-construction assertions.
- Cover Codex negotiation success, auth refusal, invalid model, and non-zero execution. Assert exact argv, stdin prompt, workspace, events, sidecar, usage label, response KV, cleanup, and exit code.
- Assert Codex invalid-model handling logs the existing error and returns `1` before the shared runner without emitting `RESPONSE_FILE`.
- Assert Codex negotiation does not mirror quota on success and mirrors it on non-zero execution.
- Cover Cursor negotiation success, auth refusal, non-zero execution, and simultaneous invalid-model/auth-refusal input. Assert max-mode prompt, exact argv, merged capture, no configuration-context creation or `CURSOR_CONFIG_DIR` mutation, response KV, model-before-auth precedence, and exit code.
- Cover `launch_codex_exec_main` with representative prompt-file and direct-prompt cases. Assert sandbox and add-dir argv, workdir resolution, model attribution, retries, timing arguments, event fallback before quota mirroring, quota and token records, metadata, done promotion, and `LAUNCHER_EXIT`.
- Cover Codex exec invalid-model handling. Assert the existing `_err` plus return-`1` path occurs before shared-runner execution and preserves its existing public output contract.
- Cover Codex preflight refusal and non-zero execution through the real shared runner. Assert their existing outer return code, diagnostic bundle, completion file, and envelope.
- Cover Codex drafter success, invalid model, and failure. Assert trusted instructions, read-only request, prompt preservation, token sidecar copying, missing raw-events fallback before quota mirroring, parsed plan artifacts, scout and dialectic status, dirty-tree sidecar, completion file, cleanup, and emitted KVs.
- Assert Codex-drafter invalid-model handling returns through its existing pre-run `_err` plus return-`1` path without calling the shared runner.
- Cover Claude drafter success, timeout, non-zero execution, and malformed envelope. Assert exact argv, stdin capture, shared envelope parsing, usage recording, timing label, status and completion files, diagnostics, exit codes, and parsed plan artifacts.
- Retain explicit adapter checks so CLI arguments and wrapper-only flag rejection remain unchanged.

### UPDATED: python/tests/agents/test_agents.py

- Retarget the Codex-drafter tests that monkeypatch `_launch_codex_exec_inprocess` or `launch_codex_exec_main` to the shared-runner seam.
- Preserve assertions for the read-only argv contract, trusted-instructions contents, token sidecar copying, launcher-exit mapping, sidecar-preferred stderr tail, quiet-mode KVs, parsed plan output, and cleanup.
- Keep a focused compatibility test for `_launch_codex_exec_inprocess` if needed to preserve its re-exported delegate contract, while ensuring migrated drafter coverage does not exercise it as the launch path.

### UPDATED: python/tests/agents/test_vendor.py

- Update the production-launcher import guard so `_drafter.py` is an explicitly migrated launcher allowed to import `larch.agents._vendor`, while every remaining un-migrated production launcher remains prohibited.
- Retain the vendor direct-import allowlist and transitive graph checks so `_vendor.py` cannot import launcher families.

## Edge cases

- Preserve missing prompt, invalid model, invalid timeout, unsafe path, symlink, and out-of-root refusals.
- Keep Codex invalid-model failures on their existing pre-run `_err` plus return-`1` paths, before shared lifecycle execution; negotiation must not emit `RESPONSE_FILE` for that failure.
- Keep Cursor invalid-model refusal ahead of authentication refusal when both conditions apply.
- Keep Codex trusted-instruction preflight failures inside the existing successful outer wrapper envelope.
- Preserve Cursor auth refusal separately from a non-zero Cursor execution, without introducing Cursor configuration isolation to negotiation.
- Keep Codex negotiation quota mirroring failure-only.
- Create the Codex exec and direct-drafter raw-events fallback before quota mirroring so quota, usage, and stderr-tail consumers retain stable event and sidecar behavior.
- Preserve timeout status only when the timeout wrapper returns `config.EXIT_TIMEOUT`.
- Treat malformed, error, missing, non-string, or empty Claude results as the existing parse failure.
- Do not promote plan, summary, scout, dialectic, or completion artifacts after a failed lifecycle stage.

## Failure modes

- A hook-order change can record usage before postprocessing, create the event fallback too late for quota mirroring, or promote completion after a failed hook.
- A descriptor request mismatch can alter vendor argv, prompt transport, sandbox mode, or capture mode.
- Resolving Codex model arguments inside shared hooks can change the existing pre-launch error path, public return code, or negotiation `RESPONSE_FILE` behavior.
- Incorrect outcome translation can change public exit codes or omit `LAUNCHER_EXIT` and status KVs.
- Allowing default Cursor configuration isolation in negotiation can change environment and configuration-copy behavior.
- Moving Cursor model resolution behind shared preflight can change invalid-model/auth-refusal precedence.
- Removing the compatibility delegate or leaving stale `test_agents.py` seams can break the `agents.py` re-export or leave migrated behavior untested.
- Moving cleanup into hooks can leak temporary Codex homes or Cursor configuration after preflight or execution failures.

## Testing strategy

- Run `python3 -m pytest python/tests/agents/test_external_dispatch.py`.
- Run the affected drafter and negotiation coverage in `python/tests/agents/test_agents.py`.
- Run `python3 -m pytest python/tests/agents/test_vendor.py`.
- Run Python lint and type checks only for the changed Python files.
- Confirm tests use fake executors and filesystem fixtures. They must not require live vendor credentials or network access.

difficulty: HARD
diff_lines: 1275
