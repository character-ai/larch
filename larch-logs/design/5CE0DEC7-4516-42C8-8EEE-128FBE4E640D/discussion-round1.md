## Decision 1: Scope is mop-up/retirement, not a fresh port
- **Question**: The Python port already exists (`file_oos.py:issue_cap()`, wired as `oos issue-cap`, used by live `/implement` + `/design` OOS paths). Should #4968 build a new module or retire the orphaned Bash and reuse the existing Python?
- **Resolution**: Retire Bash, reuse the existing `file_oos.issue_cap` as canonical. No new module, no behavior change. (Recommended option 1.)
- **Source**: user

## Decision 2: Bash `oos-issue-cap.sh` is orphaned at runtime
- **Question**: Does anything still invoke the Bash helper at runtime?
- **Resolution**: No. The only references are its own test harness (`test-oos-issue-cap.sh`), its `.md` siblings, and prose in SKILL.md/docs. Live OOS capping already goes through `python/cli.py oos issue-cap` (`oos-pipeline.md`) and `file_oos.issue_cap()` (`oos_filer.py`). Safe to delete.
- **Source**: codebase

## Decision 3: Existing Python behavior is canonical (no parity reconciliation)
- **Question**: Should the migration reconcile the existing Python to byte-match the Bash original (e.g. excerpt truncation off-by-one, file-ref path-safety)?
- **Resolution**: No. The existing `file_oos.issue_cap` + `python/test_file_oos.py` define correct behavior. Do not change `issue_cap` output. (User chose option 1, not the reconcile option 2.)
- **Source**: user

## Hard constraints (binding scope for the plan)
- Do **not** change the runtime behavior of `file_oos.issue_cap` / `oos issue-cap`.
- `make lint-retired-scripts` must be clean. This requires fixing the stale retired-path string baked into `file_oos.py`'s rollup `**Description**` line (currently names `skills/implement/scripts/oos-issue-cap.sh`), since that file is scanned and the path is being retired.
- Migrate (do not merely delete) `test-oos-issue-cap.sh` fixture coverage: ensure every unique case it exercises is covered in `python/test_file_oos.py`; adapt expectations to the existing Python's actual behavior. Do not write retired-path literals in fixtures.
- Delete the three Bash/helper files **and their `.md` siblings**; remove the `make test-oos-issue-cap` Makefile target + `docs/linting.md` row; remove `test-oos-issue-cap.sh` from `scripts/residual-bash-paths.txt`; append all deleted paths to `python/migrated-scripts.tsv` with `#4968`.
- Repoint prose references in `skills/implement/SKILL.md`, `skills/design/SKILL.md`, `docs/configuration-and-permissions.md`, `docs/linting.md` away from the retired paths to `python/cli.py oos issue-cap` / `file_oos.py`.
