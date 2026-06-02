# test-release-finish.sh — harness contract

Offline PATH-shimmed coverage for `release-finish.sh`:

1. Create release + promote success KV order.
2. Version mismatch at `TARGET_OID` → exit **1**.
3. Remote tag on wrong OID (peeled `^{}` ref) → exit **1**.
4. Existing release → `RELEASE_ACTION=edit`.
5. Empty `mergeCommit.oid` with `origin/main` version mismatch → exit **1**, `ERROR=merge-commit-missing`.
6. Local tag on wrong OID → exit **1**.
7. Empty `mergeCommit.oid` but `origin/main` `plugin.json` matches `--version` → success via `origin/main` fallback.

## Run

```bash
make test-release-finish
```
