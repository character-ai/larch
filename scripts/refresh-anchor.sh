#!/usr/bin/env bash
# refresh-anchor.sh — assemble the anchor body from local fragments and
# upsert it onto the tracking issue in a single call.
#
# Wraps the recurring two-call chain
#   scripts/assemble-anchor.sh --sections-dir … --issue … --output …
#   scripts/tracking-issue-write.sh upsert-anchor --issue … [--anchor-id …] --body-file …
# that appears at /implement Step 0.5 (Branches 2/3 seed-plant, Branch 4
# anchor seed), the Anchor-section accumulation procedure (Steps 1, 2.5, 5,
# 7a, 8, 9a.1, 11), and rebase-rebump-subprocedure step 6.
#
# Usage:
#   refresh-anchor.sh \
#       --sections-dir DIR \
#       --issue N \
#       [--anchor-id ID] \
#       [--output PATH] \
#       [--repo OWNER/REPO]
#
# Behavior:
#   1. mkdir -p the sections-dir (idempotent — covers fresh-session callers
#      that have not yet written any fragment).
#   2. Invoke scripts/assemble-anchor.sh to build the body at --output
#      (default: $(dirname "$DIR")/anchor-assembled.md).
#   3. Invoke scripts/tracking-issue-write.sh upsert-anchor with the
#      assembled body. When --anchor-id is supplied it pins the existing
#      anchor; when omitted, upsert-anchor finds the existing anchor by
#      its first-line HTML marker, or creates a new comment if absent.
#
# Output (stdout, KEY=VALUE; on success):
#   ASSEMBLED=true
#   OUTPUT=<assembled-body-path>
#   ANCHOR_COMMENT_ID=<id>
#   ANCHOR_COMMENT_URL=<url>
#   UPDATED=true|false        (UPDATED=false on first-creation by upsert-anchor)
#
# Output (stdout, KEY=VALUE; on failure):
#   FAILED=true
#   ERROR=<single-line message>
#
# Exit codes:
#   0 — success
#   1 — invocation / usage error or assemble-anchor failure
#   2 — upsert-anchor failure (e.g., gh failure, repo unresolvable)
#
# The wrapper does NOT change the contracts of assemble-anchor.sh or
# tracking-issue-write.sh; both remain callable directly from existing
# tests and from rebase-rebump-subprocedure.md fallback paths.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSEMBLE="$SCRIPT_DIR/assemble-anchor.sh"
WRITE="$SCRIPT_DIR/tracking-issue-write.sh"

fail_usage() {
    echo "FAILED=true"
    echo "ERROR=usage: $1"
    exit 1
}

SECTIONS_DIR=""
ISSUE=""
ANCHOR_ID=""
OUTPUT=""
REPO=""

while [ $# -gt 0 ]; do
    case "$1" in
        --sections-dir)
            [ $# -ge 2 ] || fail_usage "--sections-dir requires a value"
            SECTIONS_DIR="$2"; shift 2 ;;
        --issue)
            [ $# -ge 2 ] || fail_usage "--issue requires a value"
            ISSUE="$2"; shift 2 ;;
        --anchor-id)
            [ $# -ge 2 ] || fail_usage "--anchor-id requires a value"
            ANCHOR_ID="$2"; shift 2 ;;
        --output)
            [ $# -ge 2 ] || fail_usage "--output requires a value"
            OUTPUT="$2"; shift 2 ;;
        --repo)
            [ $# -ge 2 ] || fail_usage "--repo requires a value"
            REPO="$2"; shift 2 ;;
        *)
            fail_usage "unknown flag: $1" ;;
    esac
done

[ -n "$SECTIONS_DIR" ] || fail_usage "--sections-dir is required"
[ -n "$ISSUE" ]        || fail_usage "--issue is required"

if [ ! -x "$ASSEMBLE" ]; then
    echo "FAILED=true"
    echo "ERROR=missing helper: $ASSEMBLE"
    exit 1
fi
if [ ! -x "$WRITE" ]; then
    echo "FAILED=true"
    echo "ERROR=missing helper: $WRITE"
    exit 1
fi

# Default --output to a sibling of the sections directory.
if [ -z "$OUTPUT" ]; then
    OUTPUT="$(dirname "$SECTIONS_DIR")/anchor-assembled.md"
fi

mkdir -p "$SECTIONS_DIR" 2>/dev/null || {
    echo "FAILED=true"
    echo "ERROR=cannot create sections directory: $SECTIONS_DIR"
    exit 1
}

# Step 1: assemble the body. Forward stdout verbatim so callers see
# ASSEMBLED=true / OUTPUT=… on success or FAILED=true / ERROR=… on failure.
ASM_OUT="$("$ASSEMBLE" --sections-dir "$SECTIONS_DIR" --issue "$ISSUE" --output "$OUTPUT")" || {
    # assemble-anchor already emitted FAILED=true / ERROR=… on stdout (captured
    # in $ASM_OUT). Forward that envelope verbatim.
    printf '%s\n' "$ASM_OUT"
    exit 1
}

# Step 2: upsert the anchor.
WRITE_ARGS=(upsert-anchor --issue "$ISSUE" --body-file "$OUTPUT")
[ -n "$ANCHOR_ID" ] && WRITE_ARGS+=(--anchor-id "$ANCHOR_ID")
[ -n "$REPO" ]      && WRITE_ARGS+=(--repo "$REPO")

WRITE_OUT="$("$WRITE" "${WRITE_ARGS[@]}")" || {
    # upsert-anchor failure: forward its envelope verbatim. Include
    # ASSEMBLED=true so callers can observe assembly succeeded but upsert
    # did not — matches the pattern callers see today when invoking the
    # two scripts directly.
    printf '%s\n' "$ASM_OUT"
    printf '%s\n' "$WRITE_OUT"
    exit 2
}

# Success: emit the combined envelope. ASM_OUT carries ASSEMBLED=true / OUTPUT=…;
# WRITE_OUT carries ANCHOR_COMMENT_ID=… / ANCHOR_COMMENT_URL=… / UPDATED=…
printf '%s\n' "$ASM_OUT"
printf '%s\n' "$WRITE_OUT"
exit 0
