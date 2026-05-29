# test-gather-branch-context.sh Contract

Offline harness for `scripts/gather-branch-context.sh` pathspec regression.

## Fixture

Creates a temporary git repository with `main` and a `feature` branch. The feature branch adds a committed `larch-logs/**` artifact and a normal `src/feature.txt` code change relative to `main`.

## Invocation

Runs `gather-branch-context.sh --output-dir <tmpdir>` from the fixture repo working tree.

## Assertions

- `diff.txt` and `file-list.txt` include `src/feature.txt`.
- Neither output file mentions `larch-logs/`.

## Makefile

Registered as `test-gather-branch-context` on shard `test-harnesses-8`.
