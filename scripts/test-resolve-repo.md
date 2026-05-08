# scripts/test-resolve-repo.sh contract

`scripts/test-resolve-repo.sh` is the offline regression harness for `scripts/resolve-repo.sh`. It creates a temporary git repository, PATH-stubs `gh`, and verifies three cases:

- `gh repo view` succeeds and wins over the remote fallback.
- `gh repo view` fails and `git remote get-url origin` supplies `OWNER/REPO`.
- both sources fail and the resolver exits non-zero with an `ERROR=` diagnostic.

The harness is wired through `make test-resolve-repo` and the `test-harnesses-6` shard.
