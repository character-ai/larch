## Proposed Design Outline

### Goals
- Retire the orphaned Bash `oos-issue-cap.sh`, its sub-helper `oos-issue-cap-excerpt.py`, and harness `test-oos-issue-cap.sh`. The live cap path is already `python/cli.py oos issue-cap` / `file_oos.issue_cap`.
- Migrate the Bash harness's fixture coverage into `python/test_file_oos.py`.
- Keep `make lint-retired-scripts` and `make lint` clean.

### Non-goals
- No new `python/` module. Reuse the existing `file_oos.py`.
- No behavior change to `issue_cap` output; no Bash-vs-Python parity reconciliation (existing Python is canonical).
- No change to `OOS_ISSUES_PER_RUN_CAP` / `OOS_ISSUE_CAP_EXCERPT_MAX` semantics.

### Approach sketch
- Delete the 3 Bash/py files plus their 3 `.md` siblings.
- Fix the stale retired-path string baked into `file_oos.py`'s rollup `**Description**` line (it names `oos-issue-cap.sh`).
- Port any uncovered `test-oos-issue-cap.sh` cases into `python/test_file_oos.py`, adapting expectations to current Python behavior.
- Remove the `make test-oos-issue-cap` target + `docs/linting.md` row; drop the `scripts/residual-bash-paths.txt` entry; append deletions to `python/migrated-scripts.tsv` with `#4968`.
- Repoint prose references in `skills/implement/SKILL.md`, `skills/design/SKILL.md`, `docs/configuration-and-permissions.md`.

### Surfaces in scope
- Delete: `skills/implement/scripts/oos-issue-cap.sh` + `.md`, `oos-issue-cap-excerpt.py` + `.md`, `test-oos-issue-cap.sh` + `.md`.
- Edit: `python/file_oos.py`, `python/test_file_oos.py`, `python/migrated-scripts.tsv`, `scripts/residual-bash-paths.txt`, `Makefile`, `docs/linting.md`, `docs/configuration-and-permissions.md`, `skills/implement/SKILL.md`, `skills/design/SKILL.md`.

### Open questions
- Replacement wording for the user-facing rollup `**Description**` string: drop the path to "rolled up by the per-run OOS issue cap". Minor; will pick in the plan unless you object.
