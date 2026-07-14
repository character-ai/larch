### FINDING_1: Production import guard blocks `_drafter.py` migration
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Vendor Launch Parity, Codex-dyn-Vendor Launch Parity
- **Severity**: major
- **Concern**: Importing `_vendor` from `_drafter.py` conflicts with the existing production-launcher import guard, causing CI failure unless the guard is updated in the same change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/agents/test_vendor.py: drop _drafter.py from _PRODUCTION_LAUNCHERS (or invert the test to require the import) in the same PR as the _drafter migration
  - From Cursor-dyn-Vendor Launch Parity: Add an explicit plan step to update test_vendor.py (remove _drafter.py from the no-import list or invert the assertion for migrated launchers only)
  - From Codex-dyn-Vendor Launch Parity: Add an explicit ### MAY_UPDATE: (or firm) step for `python/tests/agents/test_vendor.py` to allow `_drafter.py` to import `_vendor` after migration.


### FINDING_2: Removing `_launch_codex_exec_inprocess` breaks re-exports and test seams
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Vendor Launch Parity
- **Severity**: major
- **Concern**: Removing the in-process Codex helper while leaving the declared re-export surface and existing `test_agents.py` seams unchanged can break `agents.py` import, fail monkeypatches, or leave tests exercising obsolete launch paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either keep a thin compatibility delegate with the same signature until a later piece, or add ### UPDATED: python/larch/agents/agents.py and test_agents.py repointing to the run_vendor_launch seam
  - From Cursor-Arch: Name test_agents.py updates in the firm plan (repoint mocks to run_vendor_launch / descriptor request builders) or state that new external_dispatch parity tests supersede those cases and list deletions
  - From Codex-Arch: Update or relocate the affected test_agents drafter tests to exercise run_vendor_launch, or retain the seam until those tests are migrated
  - From Cursor-Innovation: Add ### UPDATED: python/tests/agents/test_agents.py (or ### MAY_UPDATE:) to retarget fakes at run_vendor_launch or shared hook entrypoints
  - From Codex-Innovation: Add python/tests/agents/test_agents.py to the plan and migrate these tests to the shared-runner seam, or retain an equivalent exercised compatibility seam.
  - From Cursor-Pragmatic: Add `### UPDATED:` or `### MAY_UPDATE:` for `python/tests/agents/test_agents.py` and require repointing those three codex-drafter tests to spy on `run_vendor_launch` (or an equivalent stable seam) with the same argv, sidecar, launcher-exit, and stderr-tail contracts
  - From Codex-Pragmatic: Add an `agents.py` update that removes or replaces the re-export and migrate the affected `test_agents.py` mocks to exercise `run_vendor_launch`, or retain a compatible shim if that avoids the collateral breakage
  - From Cursor-Requirements: Resolve explicitly: either keep a thin compat shim still re-exported from `agents.py`, or add `### UPDATED: python/larch/agents/agents.py` and retarget tests; do not claim the re-export surface is unchanged if the symbol is deleted.
  - From Codex-Requirements: Add the necessary `agents.py` compatibility/import change and update the affected `test_agents.py` mocks to exercise `run_vendor_launch`, or retain a compatible shim if that avoids the collateral breakage
  - From Cursor-dyn-Vendor Launch Parity: Extend the testing strategy to repoint or replace these test_agents.py cases to spy on run_vendor_launch (same contract as the new external_dispatch parity tests)


### FINDING_3: Cursor negotiation changes configuration isolation
- **Reviewer(s)**: Cursor-Arch, Codex-dyn-Vendor Launch Parity
- **Severity**: major
- **Concern**: Letting `run_vendor_launch` own Cursor configuration isolation changes negotiation behavior because the current negotiation path does not create an isolated `CURSOR_CONFIG_DIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require `use_config_context=False` for negotiation and drop the config-isolation bullet from that path.
  - From Codex-dyn-Vendor Launch Parity: Pass `use_config_context=False` for negotiation-write unless a deliberate behavior change is documented and covered by tests.


### FINDING_4: Negotiation quota mirroring must remain failure-only
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-Vendor Launch Parity, Codex-dyn-Vendor Launch Parity
- **Severity**: major
- **Concern**: `run_vendor_launch` invokes `mirror_quota` after every launch, while Codex negotiation currently mirrors quota only for non-zero exits; an unconditional hook changes successful-run sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify mirror_quota hook behavior: no-op unless process_result.exit_code != 0 for negotiation; add a parity test on the success path asserting no quota mirror
  - From Cursor-Pragmatic: Document in Edge cases that negotiation Codex `mirror_quota` must run only when `process_result.exit_code != 0`, and add a parity test in `test_external_dispatch.py` that asserts no mirror on success and mirror on failure
  - From Codex-Pragmatic: The plan should require failure-only mirroring for negotiation and test it.
  - From Cursor-dyn-Vendor Launch Parity: Keep conditional mirroring in the negotiation mirror_quota hook (mirror only when process_result.exit_code != 0)
  - From Codex-dyn-Vendor Launch Parity: The plan should require failure-only mirroring for negotiation and test it.


### FINDING_11: Event fallback must precede quota mirroring
- **Reviewer(s)**: Cursor-dyn-Vendor Launch Parity, Codex-dyn-Vendor Launch Parity
- **Severity**: major
- **Concern**: Moving missing-events fallback to `postprocess` would run it after `mirror_quota`, causing quota mirroring to inspect an empty events file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Vendor Launch Parity: Run event fallback inside mirror_quota (or an equivalent pre-quota hook) so ordering matches today's launch_codex_exec_main
  - From Codex-dyn-Vendor Launch Parity: Pin event fallback to run at the start of `mirror_quota` (or a dedicated pre-quota hook), not in `postprocess`.


### FINDING_12: Parity tests should exercise the real shared runner
- **Reviewer(s)**: Codex-dyn-Vendor Launch Parity
- **Severity**: minor
- **Concern**: Tests that only spy on `run_vendor_launch` can bypass shared preflight, configuration, hook ordering, and non-zero lifecycle behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Vendor Launch Parity: Require each representative preflight and non-zero case to delegate through the real shared runner with injected fake executors and hooks; keep spies supplemental only


### FINDING_13: Cursor model validation must precede auth refusal
- **Reviewer(s)**: Codex-dyn-Vendor Launch Parity
- **Severity**: minor
- **Concern**: Shared preflight may check auth before model validation, changing the current precedence when both the model is invalid and authentication fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Vendor Launch Parity: Resolve and validate Cursor model arguments before shared preflight, or add an ordering seam, and add a combined invalid-model/auth-refusal parity test


### FINDING_14:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_drafter.py:164-208 / python/larch/agents/_vendor.py:677-682
- **Concern**: [SCOPE-REDUCTION] Negotiation must not enable default Cursor config isolation. Scenario: run_negotiation_round has no CURSOR_CONFIG_DIR setup today; run_vendor_launch defaults use_config_context=True for cursor and wraps cursor_config_context, changing env and config copy behavior versus current negotiation
- **Proposed resolution**: Add an explicit negotiation call contract: use_config_context=False (or equivalent) for run_negotiation_round; only paths that already isolate config may opt in


### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_drafter.py:164-177
- **Concern**: [SCOPE-REDUCTION] Plan adds cursor_config_context to negotiation though current path never isolates config. Scenario: run_vendor_launch defaults use_config_context=True for cursor, introducing temp CURSOR_CONFIG_DIR setup/copy on every negotiation round
- **Proposed resolution**: Pass use_config_context=False for negotiation-write unless intentional; if intentional, name the behavior change and extend negotiation tests


### FINDING_1: Missing Codex raw-events fallback
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Direct Codex drafter launch may mirror quota data before creating the `{}` raw-events fallback, leaving quota and usage consumers empty on no-event runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the same pre-mirror fallback step to the direct Codex drafter hook wiring (or shared Codex hook helper) and assert it in `test_external_dispatch.py` drafter coverage.


### FINDING_3: Codex model-argument error regression
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Moving Codex model resolution into shared launch hooks may raise or preflight-map `ValueError` instead of preserving the existing pre-launch exit 1 with no `RESPONSE_FILE` KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Resolve Codex model args before `run_vendor_launch` (same as the Cursor model-before-runner rule) and keep the existing `_err` + `return 1` path on `ValueError`


