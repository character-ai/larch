#!/usr/bin/env bash
# cursor-auth-flags.sh — Print conditional --api-key argv elements one per line.
#
# Used by runtime skill markdown templates that copy `cursor agent` Bash blocks
# verbatim into running shell, where direct `source` of a library is awkward
# (skills/shared/voting-protocol.md, skills/shared/dialectic-protocol.md,
# skills/research/references/validation-phase.md). The markdown blocks pipe
# stdout through a `while IFS= read` loop into a local array; this helper
# is the single source of truth for the conditional --api-key argv shape.
#
# Output: zero lines when CURSOR_API_KEY is empty/unset (caller's array stays
# empty); two lines (--api-key, then the trimmed key) when CURSOR_API_KEY is
# non-empty after whitespace trim. Prints nothing to stdout on any error path
# and never echoes the key on stderr; on source failure exits 1 with a
# one-line generic error to stderr.
#
# Bash 3.2-safe: no Bash 4+ features.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the lib. Hard fail (exit 1) on missing/unsourceable library — the
# runtime markdown blocks rely on this argv being correct; degrading silently
# would reintroduce the keychain bug at exactly the call sites this script
# was added to fix.
# shellcheck source=scripts/lib-cursor-auth.sh
if ! . "$SCRIPT_DIR/lib-cursor-auth.sh" 2>/dev/null; then
    echo "cursor-auth-flags.sh: failed to source lib-cursor-auth.sh" >&2
    exit 1
fi

CURSOR_AUTH_ARGS=()
cursor_auth_argv

# Print one element per physical line so the markdown-block reader loop
# (`while IFS= read -r line; do CURSOR_AUTH_FLAGS+=("$line"); done`) gets
# faithful argv elements. Empty array → zero lines printed (caller's
# CURSOR_AUTH_FLAGS stays empty, no --api-key in cursor argv).
for arg in "${CURSOR_AUTH_ARGS[@]:-}"; do
    # The :- guard keeps `set -u` happy when the array is empty.
    [ -n "$arg" ] || continue
    printf '%s\n' "$arg"
done
