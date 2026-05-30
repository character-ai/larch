## Proposed Design Outline

### Goals
- Add a comprehensive, focused unit harness that exercises `lib-plan-optional-trailers.awk` directly across all four modes (`keys`/`values`/`parse`/`has_key`).
- Add a regression guard so the already-wired Gate A/B `--snapshot-trailers`/`--dedup` (claim #1) cannot silently regress.
- Backfill the missing sibling `.md` docs for the trailer-script set (existing + new).

### Non-goals
- No change to runtime trailer-guard wiring — claim #1 is already resolved in current HEAD.
- No behavioral change to `lib-plan-optional-trailers.awk` / `.sh` (unit-under-test stays byte-stable).
- No `.md` backfill outside the trailer-script set.

### Approach sketch
- New self-contained harness `skills/design/scripts/test-trailer-awk.sh` runs `awk -f lib-plan-optional-trailers.awk` with a fixture battery and its own assertions (PASS/FAIL).
- Edge cases: last-match-wins on duplicate trailer keys, `0[89]` octal guard, `mechanical_churn` true/false, `diff_deleted`, empty/missing trailers, block-boundary break.
- Wire it by having existing `test-trailer-helpers.sh` invoke it — reuses Makefile target `test-trailer-helpers` + shard `test-harnesses-12` (no new shard/target).
- Regression pin: add a check to `scripts/test-design-structure.sh` asserting Gate A/B trailer-guard anchors stay present.

### Surfaces in scope
- `skills/design/scripts/test-trailer-awk.sh` (new) + sibling `.md`
- `skills/design/scripts/test-trailer-helpers.sh` (one wiring line)
- `scripts/test-design-structure.sh` (regression pin)
- `.md` backfill: `lib-plan-optional-trailers.{sh,awk}` + four `test-trailer-*.sh`

### Open questions
- None.
