### OOS_1: Retiring `step2_entry_main` without baseline row cleanup
- **Description**: Retiring `step2_entry_main` without baseline row cleanup. Scenario: Removing `implement step-2-entry` drops the `step2_entry_main` qualified_symbol row while telemetry subprocess moves under `run_dispatch_main` (already baselined). Stale baseline rows can confuse `make regen-subprocess-via-runner-baseline` / lint hygiene on the same PR.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/subprocess-via-runner-baseline.json:921
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

