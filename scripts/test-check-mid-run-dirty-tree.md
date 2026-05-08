# test-check-mid-run-dirty-tree.sh

Offline regression harness for `scripts/check-mid-run-dirty-tree.sh`.

It creates isolated git repositories under `/tmp`, exercises checkpoint and baseline modes, and pins dirty, clean, and unknown outcomes. The harness also verifies NUL-delimited path files for tracked changes, staged changes, new untracked files, filenames containing newlines, git-probe failure reasons, missing-baseline ambiguity, bad CLI degradation, pre-existing untracked baseline behavior, deterministic sidecar bytes, and atomic sidecar publication.

Run with:

```bash
bash scripts/test-check-mid-run-dirty-tree.sh
```

Wired by `make test-check-mid-run-dirty-tree` and assigned to a `test-harnesses-N` shard.

**Edit-in-sync**: `scripts/check-mid-run-dirty-tree.sh`, `scripts/check-mid-run-dirty-tree.md`, `Makefile`, `docs/linting.md`, and launcher harnesses that assert `${OUTPUT}.dirty-tree` behavior.
