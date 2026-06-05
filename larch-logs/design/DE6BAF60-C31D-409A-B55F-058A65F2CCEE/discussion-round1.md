# Discussion Round 1 — Issue #3476

## Decision 1: Stale-gap handling
- **Question**: The issue's gap list is partially stale (strip-failure fail-closed already covered at scripts/test-lib-external-launcher-common.sh:168-187). Audit-first and add only missing assertions, or add all listed cases verbatim?
- **Resolution**: Audit-first. Verify each listed gap against current HEAD; add assertions only where genuinely missing; strengthen defective ones (e.g. the trivially-passing post-table needle at test-lib-external-launcher-common.sh:162).
- **Source**: user

## Decision 2: Harness file scope
- **Question**: Keep to the 3 files named in the issue Description, or also include skills/implement/scripts/test-codex-implementer.sh (flagged by source finding r3 FINDING_11)?
- **Resolution**: Include test-codex-implementer.sh as a 4th harness. Audit shows its login-mode auth-prep failure case (4h) is already covered; remaining gaps there: env-key-mode auth-prep failure breadcrumb (codex-env-key-failure) and temp-home cleanup assertions.
- **Source**: user

## Decision 3: Test infrastructure constraints
- **Question**: What hard constraints bind the new tests?
- **Resolution**: All tests stay offline/hermetic (stub codex/cursor binaries, fixture HOME dirs, no network). Bash 3.2 compatible (BASH_AUTHORING.md §3; run make lint-bash32). All 4 harnesses are already wired into Makefile + CI shards — extend files in place, no new files, no Makefile wiring changes.
- **Source**: codebase

## Decision 4: Placement of new review-and-fix tests
- **Question**: Where do new Codex auth dispatch tests go inside test-review-and-fix.sh?
- **Resolution**: Inside the existing `dispatch` section (`if section_runs dispatch;` blocks) so the CI shard target test-review-and-fix-dispatch picks them up.
- **Source**: codebase
