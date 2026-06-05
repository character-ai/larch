### OOS_1:
- **Description**: Merged/postmerge stall still writes PHASE=done on the main CI success path. Scenario: When run_postmerge_phase returns STALLED, the existing loop still calls _write_ship_state(phase="done"), which can contradict stall/finalize metadata (prior edge review); the plan only guards the new merged-resume branch
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:658-659
- **Phase**: design

