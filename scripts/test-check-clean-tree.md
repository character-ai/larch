# scripts/test-check-clean-tree.sh contract

Regression harness for `scripts/check-clean-tree.sh`. It creates disposable git repositories and exercises the helper's clean, dirty, fail-open, fail-closed, and argument-validation paths.

## Cases

- Clean tree emits `CLEAN=true` and exits 0.
- Dirty tree in default mode emits `CLEAN=false` plus `DIRTY_OUT=` and exits 0.
- Dirty tree with `--fail-closed` still emits `CLEAN=false` plus `DIRTY_OUT=` and exits 0.
- A PATH-prepended `git` shim that fails only `git status --porcelain` causes default mode to emit `CLEAN=true` and exit 0.
- The same shim with `--fail-closed` emits `CLEAN=unknown` plus `PROBE_ERROR=` and exits 1.
- Unknown flags exit 2 with a stderr diagnostic.

## Wiring

Run directly:

```
bash scripts/test-check-clean-tree.sh
```

`make test-check-clean-tree` runs this harness and is included in the `test-harnesses-N` shard partition.

## Edit-in-sync

If `scripts/check-clean-tree.sh` changes stdout keys, exit codes, or summary sanitization, update this harness and `scripts/check-clean-tree.md` in the same PR.
