## Decision 1: Orphan awk files (seq-seed, legacy-opener)
- **Question**: How to handle `oos-accumulated-seq-seed.awk` and `oos-has-legacy-finding-block-opener.awk`, which have no live callers?
- **Resolution**: Delete both without porting into `design_oos.py`. The seq-seed logic already exists as `review_tally._seed_oos_seq`; the legacy-opener detector has no caller anywhere. Inline ONLY `oos-non-security-block-count.awk` into `design_oos.py`. Fix the stale `skills/implement/SKILL.md:830` prose. Record all 3 deletions in the migration manifest.
- **Source**: user

## Decision 2: Scope boundaries
- **Question**: What is in-scope vs out-of-scope?
- **Resolution**: IN: replace the `awk -f oos-non-security-block-count.awk` subprocess in `design_oos.py` with pure Python; delete all 3 `.awk` files; update stale doc references that name the deleted files (`skills/implement/SKILL.md:830`, and any others such as `oos-disposition-gate.md` / `oos-pipeline.md` that name `oos-non-security-block-count.awk`); update/port harness coverage (`test-oos-disposition-gate.sh`); record the 3 deletions in the `docs/python-migration.md` manifest so `make lint-retired-scripts` stays clean. OUT: refactoring or touching `review_tally._seed_oos_seq`; introducing a shared block-counter between `design_oos.py` and `review_tally.py`; any other OOS-pipeline behavior change.
- **Source**: codebase + user

## Decision 3: Hard constraints (must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**: OOS-disposition gate output must stay byte-identical on existing fixtures. The Python port must replicate the awk semantics exactly: count `### OOS_` blocks plus legacy `### FINDING_N: ...[OUT_OF_SCOPE]` headers, and exclude security-routed blocks (header `[security]`/`<security>` marker OR a body `- **focus-area**: security...` field line, case-folded, allowing backtick wrapping; prose `focus-area = security` inside a `**Description**` line does NOT security-route). No `awk` subprocess may remain in `design_oos.py`. `make lint-retired-scripts` must pass. The implement/review OOS pipeline (`review_tally._seed_oos_seq`, header normalization) must remain untouched.
- **Source**: codebase
