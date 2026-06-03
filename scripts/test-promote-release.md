# test-promote-release.sh — harness contract

Offline PATH-shimmed coverage for `promote-release.sh`:

1. Default hub (no `--repo`).
2. Explicit `--repo OWNER/REPO`.
3. Invalid `--repo` → exit **2**.

## Run

```bash
make test-promote-release
```
