## Decision 1: Tightening direction
- **Question**: Should this resolve the asymmetry by expanding `require_key`'s list, removing keys from `write_initial_state`, or a mixed approach?
- **Resolution**: Add the missing keys to `require_key`'s enforced list (standard tightening direction).
- **Source**: user

## Decision 2: Which keys to add
- **Question**: Which of the emitted-but-not-required keys should `require_key` enforce?
- **Resolution**: All 7 emitted-but-not-required keys: `BAIL_REASON`, `BAIL_FAILURE_DETAIL_LOG`, `DESIGN_ONLY_DONE`, `EXPECTED_SESSION_ID`, `EXPECTED_TMPDIR_BASENAME_PREFIX`, `NO_LOGS_COMMIT`, `IMPLEMENT_TMPDIR`.
- **Source**: user

## Decision 3: Value-type validation scope
- **Question**: Should value-type validation (`is_bool`, etc.) be added for any of the newly-required keys?
- **Resolution**: Add `is_bool` checks for `DESIGN_ONLY_DONE` and `NO_LOGS_COMMIT` only — mirror the existing `is_bool` loop at lines 2524-2526. No other type validators (out of scope).
- **Source**: user

## Decision 4: Backward compatibility for in-progress state files
- **Question**: State files are session-scoped (created fresh in `$IMPLEMENT_TMPDIR` per run), so a mid-run upgrade is the only risk vector. Should the change preserve compatibility with pre-existing state files written by an older `ship-pr.sh`?
- **Resolution**: Not required. State files are written by `write_initial_state` in the same run that later calls `require_key`; no cross-version state-file format is maintained between `ship-pr.sh` upgrades. The `--force-init-state` flag is already available for any explicit re-init need.
- **Source**: codebase
