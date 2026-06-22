## Goal
Implement issue #5006: [IMPLEMENTING] [OOS] correctness: `python/file_oos.py:829-881`, `python/test_file_oos.py:371-380`.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: code review (run `8E694A92-A2C8-4A62-9A7C-15095E2F52A3`, round 1)
**Phase**: implement

**Vote tally**: accepted-OOS (3 observations, same root cause)

## Description

**correctness: Bash-parity divergence in file-conflict dependency detection** (`python/file_oos.py:829-881`, `python/test_file_oos.py:371-380`).

The Python port of the file-conflict pre-pass added `_raw_file_conflict_match_is_unsafe()` (`python/file_oos.py:829-831`), which drops any regex match whose leading character is `/` or `-` **before** the cleaning pipeline runs. The retired Bash helper always ran `clean_match` **first** (`sed -E 's/^[^A-Za-z.]+//; …'`), stripping a leading `/`, then accepted the path via `path_is_safe`.

**Consequence:** for a description like `Mentions /skills/foo/bar.sh`, the regex capture is `/skills/foo/bar.sh`. Bash normalizes that to `skills/foo/bar.sh` and emits a `1\t2` serialization edge when two items cite the same path. Python drops both records and emits an empty TSV, so Step 9a.1 can allow **parallel OOS workers** to edit a path the Bash pre-pass would have serialized. The same drop affects repo-relative extensionless paths in subdirectories (e.g. `tools/Dockerfile`, `src/Makefile`).

**Test gap** (`python/test_file_oos.py:371-380`): the migrated `case-g` fixture (`test_file_conflict_deps_rejects_absolute_paths`) puts the same leading-slash path on both items and expects an empty TSV, encoding the new Python-only rejection rather than guarding Bash parity.

### Suggested fix

- Remove `_raw_file_conflict_match_is_unsafe()` and rely on the Bash-parity `_clean_file_conflict_match()` + `_file_conflict_path_is_safe()` pipeline only. Traversal (`..`) and `:` remain rejected by `_file_conflict_path_is_safe()`.
- Restore the original cross-item shape for the absolute-path test and add a same-path leading-slash parity test asserting the `1\t2` edge Bash would emit.
- Add a regression test for two items citing the same extensionless repo-relative path (e.g. `tools/Dockerfile`).

### Acceptance criteria

- Two OOS items citing the same leading-slash path (e.g. `/skills/foo/bar.sh`) produce a `1\t2` dependency edge.
- Two OOS items citing the same extensionless repo-relative path (e.g. `tools/Dockerfile`) produce a `1\t2` edge.
- Traversal paths (`../../etc/passwd`) remain rejected; absolute paths still normalize to repo-relative.
- `make py-test` and `make py-lint` pass.

---
*Body backfilled by `/implement --emergency` from run-log `8E694A92-A2C8-4A62-9A7C-15095E2F52A3` (round-1 accepted-OOS observations OOS_1/OOS_2/OOS_3); the original auto-created OOS body was empty.*

## Test plan
(no test plan section in plan-file)
