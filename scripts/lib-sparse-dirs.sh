# shellcheck shell=bash

# Top-level repo directories shipped to consumers via the plugin install. The
# cone excludes dev-only .claude/, .github/, .gemini/, the nonexistent tests/,
# committed larch-logs/, and the dev-only mermaid-lint/ toolchain. Git cone mode
# still includes root files; /upgrade-larch performs post-install cleanup for
# root files, nested test infrastructure, and dropped dev top-level directories
# left in older caches.
LARCH_SPARSE_DIRS=".claude-plugin agents docs hooks python scripts skills"

normalize_sparse_dirs() {
    tr ' ' '\n' <<< "$LARCH_SPARSE_DIRS" | sed '/^$/d' | sort
}
