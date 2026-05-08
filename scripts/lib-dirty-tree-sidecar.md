# lib-dirty-tree-sidecar.sh

Sourced-only helper carrying the canonical `_write_dirty_tree_sidecar` implementation shared between `scripts/launch-codex-review.sh`, `scripts/launch-cursor-review.sh`, and `scripts/launch-gemini-review.sh`. Resolves the byte-equivalent duplication that previously lived in each review-launch wrapper (issue #1502).

Exposes:

- `_write_dirty_tree_sidecar` — single-shot baseline emission via `scripts/check-mid-run-dirty-tree.sh --mode baseline`. The function reads and mutates caller-scope globals — `OUTPUT`, `DIRTY_TREE_WRITTEN`, `UNTRACKED_BASELINE`, `DIRTY_TREE_SIDECAR`, `SCRIPT_DIR` — exactly as the pre-extraction implementations in the three review launchers did. Callers are expected to declare and initialize those globals before invoking. The function returns 0 (no-op) when any of `OUTPUT` or `DIRTY_TREE_SIDECAR` is empty, or when `DIRTY_TREE_WRITTEN` is already `true`.

`_write_unknown_dirty_tree_sidecar` (used by the Cursor and Gemini review wrappers' auth-preflight / setup short-circuits) is intentionally NOT extracted: Codex has no counterpart, and the Cursor / Gemini bodies share most lines but live in different trap-ordering contexts; consolidation would be a separate refactor.

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_DIRTY_TREE_SIDECAR_LOADED` guard.

**Edit-in-sync**: `scripts/launch-codex-review.sh`, `scripts/launch-cursor-review.sh`, `scripts/launch-gemini-review.sh`, `scripts/check-mid-run-dirty-tree.sh`.
