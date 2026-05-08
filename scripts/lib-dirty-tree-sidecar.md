# lib-dirty-tree-sidecar.sh

Sourced-only helper carrying the canonical `_write_dirty_tree_sidecar` implementation shared between `scripts/launch-codex-review.sh` and `scripts/launch-cursor-review.sh`. Resolves the byte-equivalent duplication that previously lived in both review-launch wrappers (issue #1502).

Exposes:

- `_write_dirty_tree_sidecar` — single-shot baseline emission via `scripts/check-mid-run-dirty-tree.sh --mode baseline`. The function reads and mutates caller-scope globals — `OUTPUT`, `DIRTY_TREE_WRITTEN`, `UNTRACKED_BASELINE`, `DIRTY_TREE_SIDECAR`, `SCRIPT_DIR` — exactly as the pre-extraction implementations in both review launchers did. Callers are expected to declare and initialize those globals before invoking.

The cursor-only `_write_unknown_dirty_tree_sidecar` (used by the Cursor review wrapper's auth-preflight short-circuit) is intentionally NOT extracted: it has no Codex counterpart and is not duplicated.

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_DIRTY_TREE_SIDECAR_LOADED` guard.

**Edit-in-sync**: `scripts/launch-codex-review.sh`, `scripts/launch-cursor-review.sh`, `scripts/check-mid-run-dirty-tree.sh`.
