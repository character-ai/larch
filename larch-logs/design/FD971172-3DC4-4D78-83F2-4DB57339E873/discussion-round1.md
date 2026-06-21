## Decision 1: Port scope — full behavioral parity with the Bash original
- **Question**: A simplified `file_conflict_deps()` already exists in `python/file_oos.py` and is the live `/implement` consumer path; the `.sh` is orphaned. Should the port achieve full parity with `oos-file-conflict-deps.sh` (union-find components, cluster-cap chain degradation, global cap, atomic output, env knobs) or keep the simplified Python and just retire the `.sh`?
- **Resolution**: Full parity with the Bash. Rewrite the Python verb to match `oos-file-conflict-deps.sh` exactly: union-find connected-components with all-pairs-within-component edges, `OOS_FILE_CONFLICT_CLUSTER_CAP` chain degradation, `OOS_FILE_CONFLICT_GLOBAL_CAP` failure (exit 1), atomic `.tmp`+rename TSV output that clears the stable output on any failure, and the existing path-safety rules. All existing `.sh` fixtures must pass (migrated to pytest). Then delete the `.sh` + harness and update `scripts/residual-bash-paths.txt` + `python/migrated-scripts.tsv`. The current simplified Python is treated as the unintended divergence; restoring the richer Bash semantics to the live pipeline is intended.
- **Source**: user

## Decision 2: In-scope / out-of-scope boundaries (hard constraints)
- **Question**: What must NOT change?
- **Resolution**: Keep the dependency-edge SEMANTICS faithful to the Bash reference (the union-find all-pairs behavior is the reference, not the current simplified Python). Do not change `/implement` SKILL.md Step 9a.1 control flow. Keep the verb name (`oos file-conflict-deps`), its CLI surface (`--input-file FILE [--output FILE]`, default `$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv`), and the output TSV grammar (`<blocker-1based>\t<blocked-1based>`, sorted) stable so no consumer control-flow edit is needed. Preserve the Bash's exit-code contract (0 success incl. empty output; 1 input/global-cap/parse failure; 2 invalid env knobs).
- **Source**: codebase + issue

## Decision 3: Record completeness
- **Question**: The issue notes the `.sh` is absent from `docs/python-migration.md`, `python/migrated-scripts.tsv`, and `scripts/residual-bash-paths.txt`. What must the migration record touch?
- **Resolution**: Add the `.sh` (and its `.md` sibling, harness `.sh`, and harness `.md`) to `python/migrated-scripts.tsv` keyed by this issue (#4967); remove `skills/implement/scripts/oos-file-conflict-deps.sh` from `scripts/residual-bash-paths.txt` and from the `python/test_residual_bash.py` fixture list. `make lint-retired-scripts` must be clean. A `docs/python-migration.md` decision-log entry is optional polish, decided at drafting time.
- **Source**: codebase + issue
