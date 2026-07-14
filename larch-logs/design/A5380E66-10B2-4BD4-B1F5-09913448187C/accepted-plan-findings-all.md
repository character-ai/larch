### FINDING_1: Ship-path readers remain outside the KV migration
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Step 8 Bash readers and related ship-path readers retain bespoke first/last-wins parsing with potentially divergent CR and empty-value behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/scripts/step-8-ship.sh and skills/implement/scripts/step-8-seed-initial.sh (first-wins reads at :56-66) using kv get --match first|last; extend testing strategy with step-8 shell harness coverage
  - From Cursor-Pragmatic: Add ### UPDATED rows for run_context.py, ship_state.py, ship.py, step-8-ship.sh, and step-8-seed-initial.sh; pin duplicate-policy fixtures for ship state reads


### FINDING_2: Boolean emit formatting is unspecified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Widening `emit_kv` without specifying boolean serialization can produce `True`/`False` instead of the lowercase wire values expected by consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify in logging_util.py and test_logging_util.py that bool renders as lowercase true/false (and int as decimal digits) before the newline/CR rejection check


### FINDING_5: Run-context and ship-state readers are omitted
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Wire Compatibility Auditor, Codex-dyn-Wire Compatibility Auditor
- **Severity**: major
- **Concern**: Active run-context and ship-state readers retain independent last-wins scans, allowlist validation, and fallback behavior outside the unified codec.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these modules to the firm migration. Put the export and allowlisted shell-token grammar behind a policy-aware larch.io helper, then migrate the raw state and session readers without weakening their existing validation or fallback contracts.
  - From Cursor-Innovation: Add ### UPDATED entries for ship_state.py and run_context.py (or an explicit baseline row per symbol with a no-migrate reason). Pin last-wins plus allowlist behavior with fixtures before deleting the hand-rolled loops
  - From Cursor-Pragmatic: Add ### UPDATED rows for run_context.py, ship_state.py, ship.py, step-8-ship.sh, and step-8-seed-initial.sh; pin duplicate-policy fixtures for ship state reads
  - From Codex-Pragmatic: Add both modules and focused tests to the plan; route their reads through the codec while preserving ship-state allowlist validation, last-wins behavior, and existing read-error fallbacks.
  - From Cursor-Requirements: Add ### UPDATED: python/larch/core/run_context.py to migrate _state_value through read_kv with explicit last policy and pin duplicate-key behavior in python/tests/core/test_run_context.py.
  - From Cursor-Requirements: Add ### UPDATED: python/larch/implement/ship_state.py plus python/tests/implement/test_ship_state.py to route reads through read_kvs with allowed_keys and explicit last policy while preserving validation and patch semantics.
  - From Codex-Requirements: Add both modules to the firm updates, route their raw KEY=value reads through the codec with their existing allowed-key and fallback policies, and add focused tests in their existing test modules
  - From Cursor-dyn-Wire Compatibility Auditor: Add python/larch/core/run_context.py and focused tests, preserving last-wins, empty values, CR line handling, strict-decode fallback, and read-error fallback
  - From Cursor-dyn-Wire Compatibility Auditor: Add python/larch/implement/ship_state.py and focused tests with explicit last policy, allowlist filtering, embedded-equals preservation, and ShipError failure wrapping
  - From Codex-dyn-Wire Compatibility Auditor: Add deprecated compatibility adapters mapping existing boolean keywords to explicit policies, or list and migrate every caller; test both true and false compatibility paths


### FINDING_9: Boolean duplicate-policy API compatibility is unspecified
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-Wire Compatibility Auditor
- **Severity**: major
- **Concern**: Replacing existing `first_wins`/`first_match` keyword parameters without compatibility handling can raise `TypeError` for unlisted callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Retain compatibility aliases with conflict validation, or list and migrate every remaining boolean-argument caller
  - From Codex-dyn-Wire Compatibility Auditor: Add deprecated compatibility adapters mapping existing boolean keywords to explicit policies, or list and migrate every caller; test both true and false compatibility paths


### FINDING_10: All-values router migration lacks caller tests
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements
- **Severity**: minor
- **Concern**: Generic codec tests do not pin ordered repeated-key behavior at the design-router call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a router regression fixture with repeated keys and assert ordered WARN collection plus last-value routing semantics
  - From Cursor-Requirements: Add a firm ### UPDATED: python/tests/design/test_design_router.py (or equivalent) with duplicate-key fixtures that assert preserved list order for _parse_stdout_kv call sites at lines 92 and 115.


### FINDING_11: Design session reader remains unowned
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: `design_step_log._session_get` remains a duplicate first-match reader outside the migration set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these modules to the firm migration. Put the export and allowlisted shell-token grammar behind a policy-aware larch.io helper, then migrate the raw state and session readers without weakening their existing validation or fallback contracts.
  - From Cursor-Requirements: Add ### UPDATED: python/larch/design/design_step_log.py to replace _session_get with read_kv using the same first-match and empty-value defaults, and extend the existing plan-log tests to pin behavior.


### FINDING_4: Hook `kv get` failure can bypass active-bgjob denial
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: Missing fail-closed `kv get` failure coverage. After the planned replacement, a broken or unavailable Python CLI can yield no `CLONE_PATH`; treating that as no matching registry permits a background Bash despite an active same-clone daemon. A missing Python or failed `kv get` can bypass the active-bgjob denial when registry entries exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the hook harness to the plan and assert that a failing `kv get` with a valid matching registry still exits 0 and emits a denial.
  - From Codex-Requirements: Add fail-closed handling for CLI resolution or read failure when registry entries exist, and extend `scripts/test-hook-deny-run-in-background.sh` with a missing-Python or failing-`kv get` case that asserts exit-0 denial.


