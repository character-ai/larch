#!/usr/bin/env bash
# normalize-oos-block-header.sh — Rewrite an OOS block's line-1 header to canonical ### OOS_<seq>:.

set -euo pipefail

usage() { echo "Usage: normalize-oos-block-header.sh --seq N [--block-file FILE]" >&2; }

SEQ=""
BLOCK_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --seq) SEQ="${2:?--seq requires a value}"; shift 2 ;;
        --block-file) BLOCK_FILE="${2:?--block-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "normalize-oos-block-header.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

case "$SEQ" in
    ''|*[!0-9]*) echo "normalize-oos-block-header.sh: --seq must be a non-negative integer" >&2; exit 2 ;;
esac
if [[ -n "$BLOCK_FILE" && ! -f "$BLOCK_FILE" ]]; then
    echo "normalize-oos-block-header.sh: --block-file must name a file" >&2
    exit 2
fi

# Rewrite ONLY line 1: a leading "### <WORD>_<n>:" id token (legacy FINDING_,
# tagged or scope-drift bare, or an existing OOS_ id being renumbered) becomes
# "### OOS_<seq>:"; the title text after the colon is preserved verbatim.
# Body lines pass through untouched (NR==1 guard), so cited "### FINDING_N:"
# headings inside Concern / Suggested-revision prose are never rewritten.
# Portable awk sub() — no GNU-only sed; Bash 3.2 / BSD safe.
awk -v seq="$SEQ" 'NR==1 { sub(/^###[[:space:]]+[A-Za-z]+_[0-9]+:/, "### OOS_" seq ":") } { print }' ${BLOCK_FILE:+"$BLOCK_FILE"}
