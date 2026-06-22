## Proposed Design Outline

### Goals
- Remove the `awk` subprocess from `python/design_oos.py` by inlining `oos-non-security-block-count.awk` as pure Python.
- Delete all 3 OOS `.awk` files; keep OOS-disposition gate output byte-identical on existing fixtures.
- Keep `make lint-retired-scripts` clean by recording the deletions in the migration manifest.

### Non-goals
- No change to `review_tally._seed_oos_seq` (already the Python home for seq-seeding).
- No shared/common block-counter abstraction between `design_oos.py` and `review_tally.py`.
- No other OOS-pipeline behavior change; no re-porting of the two orphan awk files.

### Approach sketch
- Replace `_count_non_security_blocks`'s `awk -f` call with an in-process Python parser that replicates the awk semantics exactly (OOS_ + legacy `FINDING_N ...[OUT_OF_SCOPE]` counting; security-routing exclusion via header marker or body `focus-area: security` field line).
- Delete `oos-non-security-block-count.awk`, `oos-accumulated-seq-seed.awk`, `oos-has-legacy-finding-block-opener.awk`.
- Repoint the harness check in `test-oos-disposition-gate.sh` (currently `awk -f`) to the Python path; add/extend Python unit coverage in `test_design_oos.py`.
- Update stale doc references that name the deleted files; record the 3 deletions per the migration manifest / `lint-retired-scripts` contract.

### Surfaces in scope
- `python/design_oos.py` (inline block-count, drop `subprocess`/`awk`).
- `skills/implement/scripts/oos-non-security-block-count.awk`, `oos-accumulated-seq-seed.awk`, `oos-has-legacy-finding-block-opener.awk` (delete).
- `skills/implement/scripts/test-oos-disposition-gate.sh` (harness).
- `python/test_design_oos.py` (Python coverage).
- Docs naming the files: `skills/implement/SKILL.md`, `skills/implement/scripts/oos-disposition-gate.md`, `skills/implement/references/oos-pipeline.md`.
- Migration manifest + retired-scripts inventory (`docs/python-migration.md`, `scripts/residual-bash-paths.txt` as applicable).

### Open questions
- None.
