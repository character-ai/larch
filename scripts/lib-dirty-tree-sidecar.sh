# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_DIRTY_TREE_SIDECAR_LOADED:-}" ]]; then
    return 0
fi

# _write_dirty_tree_sidecar — emit (once) the dirty-tree sidecar via
# scripts/check-mid-run-dirty-tree.sh in baseline mode. Reads/writes
# caller-scope globals: OUTPUT, DIRTY_TREE_WRITTEN, UNTRACKED_BASELINE,
# DIRTY_TREE_SIDECAR, SCRIPT_DIR. The single-shot guard via
# DIRTY_TREE_WRITTEN matches the pre-extraction contract used by both
# launch-codex-review.sh and launch-cursor-review.sh.
# shellcheck disable=SC2329,SC2317  # callers invoke this from EXIT traps.
_write_dirty_tree_sidecar() {
    [[ -n "$OUTPUT" ]] || return 0
    [[ "$DIRTY_TREE_WRITTEN" == "false" ]] || return 0
    [[ -n "$DIRTY_TREE_SIDECAR" ]] || return 0
    if [[ -x "$SCRIPT_DIR/check-mid-run-dirty-tree.sh" ]]; then
        "$SCRIPT_DIR/check-mid-run-dirty-tree.sh" --mode baseline --baseline "$UNTRACKED_BASELINE" --sidecar "$DIRTY_TREE_SIDECAR" >/dev/null 2>&1 || true
    fi
    DIRTY_TREE_WRITTEN=true
}

LARCH_LIB_DIRTY_TREE_SIDECAR_LOADED=1
