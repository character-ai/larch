## Proposed Design Outline

### Goals
- Bring the Python `oos file-conflict-deps` verb to full behavioral parity with the Bash `oos-file-conflict-deps.sh`: union-find connected-components (all-pairs-within-component edges), cluster-cap chain degradation, global cap, atomic output, `OOS_FILE_CONFLICT_*` env knobs, path-safety.
- Make every existing `.sh` fixture pass against the Python verb, migrated to colocated pytest.
- Retire the now-orphaned Bash `.sh` + harness and record the migration so `make lint-retired-scripts` is clean.

### Non-goals
- Changing dependency-edge semantics away from the Bash reference.
- Changing `/implement` SKILL.md Step 9a.1 control flow, the verb name, its CLI surface, or the output TSV grammar.
- Touching the `/issue` `--intra-batch-deps-file` merge or `oos-issue-cap` logic.

### Approach sketch
- Replace the simplified body behind the existing `oos file-conflict-deps` verb with a faithful port of the Bash algorithm (the verb already routes to `file_oos`).
- Port record extraction + path-safety, candidate-edge conflict detection, union-find components, per-component all-pairs vs chain at `OOS_FILE_CONFLICT_CLUSTER_CAP`, `OOS_FILE_CONFLICT_GLOBAL_CAP` failure, atomic `.tmp`+rename write.
- Reuse existing Python surfaces (`issue parse-input` outputs, file-line regexes) where the Bash shelled out.
- Migrate `test-oos-file-conflict-deps.sh` fixtures to pytest exercising the verb end-to-end.
- Delete the `.sh`/`.md` + harness and update all migration ledgers and the SKILL.md machine-reachability list.

### Surfaces in scope
- `python/file_oos.py` (or a new `python/oos_file_conflict.py`) and `python/cli.py` routing.
- New pytest file under `python/`.
- `skills/implement/scripts/oos-file-conflict-deps.{sh,md}` + `test-oos-file-conflict-deps.{sh,md}` (delete).
- `python/migrated-scripts.tsv`, `scripts/residual-bash-paths.txt`, `python/test_residual_bash.py`, `skills/implement/SKILL.md` S030 list, Makefile target.

### Open questions
- Module placement (expand `file_oos.py` in place vs. extract a dedicated `oos_file_conflict.py`) — resolved at drafting; leaning toward a dedicated module for the self-contained algorithm and its testability.
