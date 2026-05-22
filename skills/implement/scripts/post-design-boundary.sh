#!/usr/bin/env bash
# post-design-boundary.sh — DEPRECATED (issue #2485 Decision 2).
#
# Physical deletion is deferred; callers must not rely on this script.
# Issue-anchored /implement materializes the plan from the GitHub issue body
# and does not invoke this wrapper on the happy path.
#
# Contract: always exit 0. Emit a single-line deprecation warning to stderr.
# Do not read manifests, mutate session-env, write .boundary-gate-passed, or
# touch design-export/manifest.env.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
QUIET_LIB="$PLUGIN_ROOT/scripts/lib-quiet.sh"
[[ -f "$QUIET_LIB" ]] || QUIET_LIB="$REPO_ROOT/scripts/lib-quiet.sh"
# shellcheck source=scripts/lib-quiet.sh
source "$QUIET_LIB"
larch_quiet_init

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir) shift 2 ;;
        --session-env) shift 2 ;;
        --design-only) shift 2 ;;
        --hook-mode) shift 2 ;;
        *) shift ;;
    esac
done

larch_err "post-design-boundary.sh: deprecated no-op (issue #2485); remove stray invocations."
exit 0
