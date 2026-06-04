# shellcheck shell=bash

# Top-level repo directories shipped to consumers via the plugin install:
# every top-level tracked directory EXCEPT larch-logs/ (committed run logs,
# ~317 MB, never read from the install at runtime) and mermaid-lint/ (dev-only
# Mermaid lint toolchain — excluded so the installed plugin has no package.json
# and the installer runs no npm install). Passed to
# `claude plugin marketplace add --sparse` (git sparse-checkout, cone mode);
# cone mode always keeps top-level files, so root markdown imports ship anyway.
# MAINTENANCE: if a new top-level directory is added to the repo and must ship,
# add it here; larch-logs/ and mermaid-lint/ must NOT be added.
LARCH_SPARSE_DIRS=".claude .claude-plugin .gemini .github agents docs hooks python scripts skills tests"

normalize_sparse_dirs() {
    tr ' ' '\n' <<< "$LARCH_SPARSE_DIRS" | sed '/^$/d' | sort
}
