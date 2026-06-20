## Decision 1: Share `_consumer_repo_root()` via a shared module
- **Question**: One shared definition imported by both modules, or a local copy in `design_publish.py`?
- **Resolution**: Extract `_consumer_repo_root()` to a shared module. Both `design_postplan.py` and `design_publish.py` import it. Prevents the two-site drift that caused this recurrence.
- **Source**: user

## Decision 2: Audit and harmonize all `--repo-root` callers
- **Question**: Include a grep sweep for other `plan validate` / `validate-commands` callers passing the plugin root as `--repo-root`?
- **Resolution**: Yes. Audit and harmonize every same-class site, not only `design_publish.py`, so a third-site recurrence cannot reappear.
- **Source**: user

## Decision 3: Step 5c operator message distinguishes `missing-script`
- **Question**: Distinguish `missing-script` (often a root-resolution false positive) from genuinely unsafe tokens in the Step 5c validator-defect message?
- **Resolution**: Yes. Include the message improvement in this fix so operators are not nudged toward destructive auto-repair on false positives.
- **Source**: user

## Hard constraints (must not break)
- Preserve the dual-root existence check: plugin-only scripts must still validate using the plugin cache as the secondary root.
- Preserve the `--skip-validate` Override path and the existing Step 5c result-env / exit-code contract (`PLAN_WRITE_OK`, `PUBLISH_RC`, `VALIDATE_STATUS`).
- Step 2b postplan behavior (`design_postplan.py`) must remain `VALIDATE_STATUS=ok` for consumer-repo scripts; the fix only brings Step 5c into parity.
