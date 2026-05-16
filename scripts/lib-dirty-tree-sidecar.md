# lib-dirty-tree-sidecar.sh

Exposes:

- `_write_dirty_tree_sidecar` — single-shot baseline emission via `scripts/check-mid-run-dirty-tree.sh --mode baseline`. The function reads and mutates caller-scope globals — `OUTPUT`, `DIRTY_TREE_WRITTEN`, `UNTRACKED_BASELINE`, `DIRTY_TREE_SIDECAR`, `SCRIPT_DIR` — exactly as the pre-extraction implementations in the three review launchers did. Callers are expected to declare and initialize those globals before invoking. The function returns 0 (no-op) when any of `OUTPUT` or `DIRTY_TREE_SIDECAR` is empty, or when `DIRTY_TREE_WRITTEN` is already `true`.

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_DIRTY_TREE_SIDECAR_LOADED` guard.
