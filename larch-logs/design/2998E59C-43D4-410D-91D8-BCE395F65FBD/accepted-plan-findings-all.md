### FINDING_1: Shard inventory omits non-test-prefixed Bash leaves
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Harness Partition Auditor
- **Severity**: major
- **Concern**: The shard partition guard inventories only `test-*` recipes, so valid non-`test-*` Bash leaves such as `write-final-report-bash-harness` are reported as orphaned. The guard, `.PHONY` checks, and self-tests must consistently recognize shard-bound direct-Bash leaves while excluding aggregates and pytest recipes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin Makefile work: each of the four smokes gets a `test-*` target whose recipe is one `bash …/test-*.sh` line; shards reference only those leaves; developer aggregates (`test-write-final-report`, `test-step-7a`, etc.) stay off shards and out of the Bash inventory
  - From Cursor-Arch: Add a `--self-test` fixture that places a non-`test-*` prerequisite in a shard and expects `orphan in shards`, alongside the planned mixed pytest/Bash aggregate cases
  - From Cursor-Innovation: Extend inventory/phony validation to every shard-bound direct Bash recipe target (including *-bash-harness leaves); add self-test fixture proving a non-test-* bash leaf is required and sufficient
  - From Cursor-Pragmatic: Extend scripts/test-harness-shards-coverage.sh: inventory shard-bound bash-only leaves whether or not they carry the test- prefix (or require a single test-* smoke name for all four families); update orphan/missing logic and add a self-test happy path with a *-bash-harness shard member.
  - From Cursor-Requirements: Under ### UPDATED: scripts/test-harness-shards-coverage.sh, require a unified bash-leaf inventory that unions test-* bash-only recipes with non-test-* targets whose recipes invoke bash only (e.g. *-bash-harness), excludes recipe-less aggregates and pytest recipes, and drives missing/orphan/unknown shard-member checks plus a self-test happy-path fixture containing such a leaf.
  - From Cursor-dyn-Harness Partition Auditor: In the Makefile and coverage-script sections, pin one contract: either rename all shard bash leaves to `test-*` smokes, or extend inventory discovery beyond `^test[^[:space:]:]*:` to include explicit bash-only leaf rules (and `.PHONY` / self-test coverage for them)


