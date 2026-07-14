## Proposed Design Outline

### Goals
- Migrate the subprocess launch mechanics in `run_negotiation_round`, `launch_codex_exec_main`, `launch_codex_drafter`, and `launch_claude_drafter` to use `run_vendor_launch` from `_vendor.py`.
- Add parity tests in `test_external_dispatch.py` covering Codex, Cursor, and Claude drafter/negotiation paths before removing inline mechanics.
- Eliminate duplicated argv assembly, model scanning, config setup, and Claude JSON unwrapping from `_drafter.py`.

### Non-goals
- Migrating `_ci_launcher.py` or `_review_launcher.py` (other partition pieces).
- Changing public CLI interfaces, `launch_*_main` adapters, or the `agents.py` re-export surface.
- Modifying plan parsing, scout/dialectic logic, or dirty-tree reporting.

### Approach sketch
- Wire `VendorFamilyHooks` for each of the four functions: Codex negotiation/drafter, Cursor negotiation, and Claude drafter.
- Replace inline subprocess creation in each function with `run_vendor_launch(descriptor, profile, request, hooks=...)`.
- Keep prompt construction, plan parsing, dirty-tree reporting, status file writes, and sentinel management local.
- Add `test_external_dispatch.py` parity cases; verify argv, timing labels, status files, token records, sidecars, exit codes, and `LAUNCHER_EXIT` envelopes match the pre-migration shape.

### Surfaces in scope
- `python/larch/agents/_drafter.py`
- `python/tests/agents/test_external_dispatch.py`

### Open questions
- None.
