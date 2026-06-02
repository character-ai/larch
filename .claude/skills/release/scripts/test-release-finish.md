# test-release-finish.sh — harness contract

Offline PATH-shimmed coverage for `release-finish.sh`:

1. Create release + promote success KV order.
2. Version mismatch at `TARGET_OID` → exit **1**.
3. Remote tag on wrong OID (peeled `^{}` ref) → exit **1**.
4. Existing release → `RELEASE_ACTION=edit`.
5. Empty `mergeCommit.oid` after poll → exit **1**, `ERROR=merge-commit-missing`.
6. Local tag on wrong OID → exit **1**.

## Run

```bash
make test-release-finish
```
