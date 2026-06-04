# test-local-cleanup.sh contract

Regression harness for `scripts/local-cleanup.sh`. The primary contract lives in `scripts/local-cleanup.md`; this harness covers the pre-pull orphan cleanup path, the no-op path when local `main` has no ahead commits, the safety path that preserves non-flush ahead work, the `git pull --ff-only origin main` invocation shape, `--help` and `--branch main` flag-safety behavior, and the case where the bare `origin/main` advances with non-`larch-logs` paths after a flush-only-ahead local state while the clone's `origin/main` ref is still stale until `git fetch` (guards the pre-fetch SHA used for the aggregate diff predicate).

It also covers divergent local `main`: local non-flush work plus an advanced `origin/main` must report `CLEANUP_SUCCESS=false`, stay on `main`, leave `BRANCH_DELETED=false`, and avoid creating a merge commit even when plain `git pull` would be configured to merge.

Run with:

```bash
scripts/test-local-cleanup.sh
```
