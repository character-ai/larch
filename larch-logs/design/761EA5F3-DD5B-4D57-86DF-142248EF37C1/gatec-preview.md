## Final Design Plan

## Plan

Adopt the shared vendor launch lifecycle in the checks lint-fix lane without moving lint-fix policy out of its lane. Preserve the injected `Runner`, waterfall order, tier ledger, classification, token ingestion, timing, failure routing, and persistence.

Re-verify the consumer inventory before editing. Confirm `ci_fixer_lane.py` remains deleted and that no surviving caller depends on the private lint-fix argv builders.

### UPDATED: python/larch/implement/checks_lint_fix.py

- Import the Codex, Cursor, and Claude descriptors; launch request/result and hook types; and `run_vendor_launch`.
- Replace `_run_codex`, `_run_cursor`, and `_run_claude` wrapper-command dispatch with descriptor requests and lane-owned injected execute hooks. Keep the existing `Runner` seam: vendor launches and lane follow-up commands must call the supplied runner and map its `CommandResult` into `VendorProcessResult`; do not substitute in-process launcher execution.
- Preserve the full Codex launch contract, not only its argv:
  - Build the Codex prompt with `_codex_lint_fix_prompt_appendix(site)` and retain the site-specific sandbox and verification-split instructions.
  - Create and clean an isolated temporary `CODEX_HOME`; run `_prepare_codex_home` before launch; resolve Codex model arguments with the current default-role path (`codex_role="default"`, `with_effort=False`) before descriptor argv construction; and pass the prepared environment to the authenticated executor.
  - Use `workspace-write`, the repository workdir, and only the run directory and repository as allowed directories.
  - Preserve events, sidecar, prompt, completion, timeout/auth-retry, quota, and failed-attempt artifact behavior, including `.done` promotion and refusal/preflight bundles equivalent to `launch-codex-exec`.
  - Reuse the established Codex lifecycle helpers where import boundaries permit; otherwise add narrowly scoped lane adapters with byte-equivalent artifact and failure behavior.
  - Keep token-record ingestion local to the lane, including fail-soft warnings, and record usage with the `codex_lint_fix` label rather than the generic `codex_exec` label.
- Preserve the full Cursor contract through the dedicated descriptor profile: model resolution, auth preflight and exported auth state, service-token preread, wrapped prompt, startup locking, captured output, and repository workspace access.
  - Set `use_config_context=False` explicitly. Match the current export-only authentication path: do not create, copy, isolate, or clean up a Cursor configuration directory for lint-fix, including on refusal or exception paths.
- Preserve the full Claude contract through descriptor hooks: lint-fix preamble, configured model, repository write tools, stdin prompt delivery, JSON-envelope parsing, diagnostics, exit mapping, output and `.done` artifacts, and usage recording.
- Record Claude timing from its descriptor hook with `record-vendor-task`, vendor `claude`, task kind `claude-lint-fix`, and output `claude-lint-fix.txt`. Keep `run_lint_fix`’s outer-timing skip for Claude outcomes so a Claude attempt is not recorded twice.
- Keep failure-tail selection and output artifact handling local to each lane.
- Remove `_build_codex_argv`, `_build_cursor_argv`, and obsolete wrapper-only helpers only after parity coverage passes.
- Do not move tier selection, delta classification, ledger writes, failure routing, or persistence into `_vendor.py`.

### UPDATED: python/larch/agents/_vendor.py

- Add and register a narrow `lint-fix-write` Cursor profile.
- Make its argv exactly the existing lint-fix shape: `cursor agent -p --trust`, resolved model and auth arguments, `--workspace <repo>`, and the wrapped prompt.
- Do not inherit unrelated `ci-write`, `implement-write`, or negotiation flags such as `--force`, `--output-format json`, or ask mode.
- Do not add lint-fix policy, persistence, token ingestion, or lane-specific artifact decisions to the descriptor module.

### UPDATED: python/tests/implement/test_checks.py

- Replace retired wrapper-command assertions with descriptor-built argv and injected execute-hook assertions.
- Assert runner-visible launches and follow-up commands, including the existing `launch-codex-exec`, `run-external-agent`, `cursor-wrap-prompt`, and token-record command paths, with hook results mapped back to descriptor process results.
- Add exact Codex parity coverage for workspace-write permissions, repository workdir, only the run directory and repository as allowed directories, default-role model resolution with `with_effort=False`, and the prompt containing the site-scoped `_codex_lint_fix_prompt_appendix(site)`.
- Set distinct default-role and fix-role model environment values in a parity test, then prove the descriptor argv uses the exact current wrapper `-m` value from the default role rather than the fix-role value.
- Add Codex hook-contract tests for isolated `CODEX_HOME`, sanitized/prepared configuration, auth-preflight refusal artifacts, model-resolution failure artifacts, events/sidecar paths, `.done` promotion, cleanup, and the `codex_lint_fix` usage label.
- Preserve Codex success and failure token-ingestion tests, including fail-soft token-command warnings and no behavior change when the token record is absent.
- Add exact Cursor parity coverage for the dedicated `lint-fix-write` profile, wrapped prompt shape, repository workspace, model/auth arguments, export-only auth state, preflight refusal, startup locking, and captured output.
- Assert the lint-fix Cursor request pins `use_config_context=False` and that no Cursor configuration directory is created, copied, or cleaned up on success, refusal, or exceptions.
- Add exact Claude parity coverage for stdin transport, configured model, repository write tools, and lint-fix preamble.
- Cover Claude valid envelopes, malformed JSON, error responses, empty results, stderr capture, nonzero exits, diagnostic fallback, `.done` output, and per-attempt timing. Retain the regression proving a Claude outcome skips outer timing.
- Retain waterfall tests proving Claude, Codex, and Cursor tier order, useful-delta handling, tier-ledger rows, classification, persistence, and failure routing remain unchanged.

### UPDATED: python/tests/agents/test_vendor.py

- Update the registered-profile assertion for `lint-fix-write`.
- Add a focused exact-argv test for the profile, including the absence of unrelated Cursor flags.
- Confirm all pre-existing descriptor profiles remain byte-compatible.

### MAY_UPDATE: python/larch/agents/_vendor.py

- If the descriptor request type lacks a narrowly typed field needed to carry the existing lint-fix authentication arguments or explicit `use_config_context=False` setting without changing another profile’s argv, add only that transport field and cover its default behavior. Do not encode lint-fix policy in the descriptor layer.

## Edge cases

- Codex auth/config/model preflight refusal must produce the same failed-attempt artifacts and classification as the current lane.
- Distinct default and fix Codex model settings must still select the default-role model used by the current wrapper.
- Missing or malformed completion output remains a failed launch.
- Token-record absence remains harmless; token-record command failures warn without changing the fixer result.
- Cursor configuration state does not leak because lint-fix never enters a Cursor configuration context.
- Vendor success without a useful repository delta continues through the existing waterfall.
- Claude timing is recorded once per launch attempt and never duplicated by outer timing.

## Failure modes

- Reusing an existing Cursor profile changes lint-fix flags or output behavior; bind the lane only to `lint-fix-write`.
- Omitting `use_config_context=False` changes lint-fix from export-only authentication to the `ci-write` configuration-context behavior; pin and test the flag.
- Direct Codex descriptor execution can bypass isolated home setup, auth preparation, default-role model resolution, sidecars, completion promotion, or usage labeling; lock the complete hook contract with runner-seam and artifact tests.
- In-process execute hooks can bypass the injected runner and invalidate existing observability; retain runner-backed hooks and assert their command results are adapted to descriptor results.
- Hook ordering can change timing, token handling, completion, or diagnostics; assert required post-execution effects on both successful and failed launches.
- Direct Claude execution can lose wrapper-owned timing or double-record it; retain the inner timing hook and outer Claude skip.

## Testing strategy

- Run focused checks tests in `python/tests/implement/test_checks.py`.
- Run `python/tests/agents/test_vendor.py`.
- Run changed-file Python formatting, lint, type checks, and complexity checks documented in `docs/linting.md`.
- Compare all three descriptor-built argv lists with explicit expected lists; do not rely on substring assertions.
- Run the existing lint-fix waterfall, tier-ledger, token, timing, classification, and persistence regressions.

difficulty: MODERATE
diff_lines: 490
