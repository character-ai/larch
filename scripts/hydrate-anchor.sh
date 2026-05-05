#!/usr/bin/env bash
# hydrate-anchor.sh — fetch a tracking-issue anchor comment by ID and split
# it back into per-section fragment files.
#
# Wraps the recurring inline pattern at /implement Step 0.5 (Branches 1, 2,
# and 3 hydration paths):
#   mkdir -p $TMPDIR/anchor-hydrate $TMPDIR/anchor-sections
#   gh api /repos/$REPO/issues/comments/$ID --jq '.body' > anchor-body.md
#   awk … extract <!-- section:<slug> --> … <!-- section-end:<slug> --> …
#       writing each section interior to $TMPDIR/anchor-sections/<slug>.md
#
# Usage:
#   hydrate-anchor.sh --anchor-id ID --tmpdir DIR [--repo OWNER/REPO]
#
# Output (stdout, KEY=VALUE):
#   On success:
#     HYDRATED=true
#     SECTIONS=<count>          (number of slugs that received content)
#   On failure (best-effort — script always exits 0):
#     HYDRATED=false
#     ERROR=<single-line message>
#
# Best-effort contract: SKILL.md treats hydration failure as non-fatal and
# logs to Warnings. The script therefore always exits 0; callers branch on
# HYDRATED= rather than $?.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/anchor-section-markers.sh
# shellcheck disable=SC1091
if ! . "$SCRIPT_DIR/anchor-section-markers.sh"; then
    echo "HYDRATED=false"
    echo "ERROR=missing helper: $SCRIPT_DIR/anchor-section-markers.sh"
    exit 0
fi
ALLOWED_SLUGS=" ${SECTION_MARKERS[*]} "

ANCHOR_ID=""
TMPDIR_ARG=""
REPO=""

while [ $# -gt 0 ]; do
    case "$1" in
        --anchor-id) ANCHOR_ID="${2:-}"; shift 2 ;;
        --tmpdir)    TMPDIR_ARG="${2:-}"; shift 2 ;;
        --repo)      REPO="${2:-}"; shift 2 ;;
        *)
            echo "HYDRATED=false"
            echo "ERROR=unknown flag: $1"
            exit 0 ;;
    esac
done

if [ -z "$TMPDIR_ARG" ]; then
    echo "HYDRATED=false"
    echo "ERROR=--tmpdir is required"
    exit 0
fi

if [ -z "$ANCHOR_ID" ]; then
    echo "HYDRATED=false"
    echo "ERROR=anchor-id-empty"
    exit 0
fi

if [ -z "$REPO" ]; then
    REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)
    if [ -z "$REPO" ]; then
        echo "HYDRATED=false"
        echo "ERROR=could not resolve repo (--repo not set and gh repo view failed)"
        exit 0
    fi
fi

HYDRATE_DIR="$TMPDIR_ARG/anchor-hydrate"
SECTIONS_DIR="$TMPDIR_ARG/anchor-sections"
BODY_FILE="$HYDRATE_DIR/anchor-body.md"

mkdir -p "$HYDRATE_DIR" "$SECTIONS_DIR" 2>/dev/null || {
    echo "HYDRATED=false"
    echo "ERROR=cannot create hydrate/sections directories under $TMPDIR_ARG"
    exit 0
}

if ! gh api "/repos/$REPO/issues/comments/$ANCHOR_ID" --jq '.body' > "$BODY_FILE" 2>/dev/null; then
    echo "HYDRATED=false"
    echo "ERROR=gh api fetch failed for comment $ANCHOR_ID"
    exit 0
fi

if [ ! -s "$BODY_FILE" ]; then
    echo "HYDRATED=false"
    echo "ERROR=empty anchor body"
    exit 0
fi

# Extract <!-- section:<slug> --> … <!-- section-end:<slug> --> ranges.
# Write each section's interior (lines strictly between the markers) to
# $SECTIONS_DIR/<slug>.md. Empty sections produce empty files (overwrite
# any pre-existing fragment with the remote content — hydration is the
# source of truth on resume).
SECTIONS_COUNT=$(awk -v outdir="$SECTIONS_DIR" -v allowed="$ALLOWED_SLUGS" '
    function extract_slug(line, prefix,    s) {
        s = line
        sub("^" prefix, "", s)
        sub(" -->$", "", s)
        return s
    }
    function slug_ok(s) {
        if (s == "") return 0
        if (index(s, "/") || index(s, "\\") || index(s, "..")) return 0
        if (index(allowed, " " s " ") == 0) return 0
        return 1
    }
    BEGIN { in_section=0; slug=""; outpath=""; count=0 }
    /^<!-- section:[^ ]+ -->$/ {
        nextslug = extract_slug($0, "<!-- section:")
        if (slug_ok(nextslug)) {
            slug = nextslug
            in_section = 1
            outpath = outdir "/" slug ".md"
            printf "" > outpath
            close(outpath)
        }
        next
    }
    /^<!-- section-end:[^ ]+ -->$/ {
        endslug = extract_slug($0, "<!-- section-end:")
        if (slug_ok(endslug) && endslug == slug) {
            in_section = 0
            slug = ""
            count++
        }
        next
    }
    {
        if (in_section) {
            print $0 >> outpath
        }
    }
    END { print count+0 }
' "$BODY_FILE" 2>/dev/null) || {
    echo "HYDRATED=false"
    echo "ERROR=awk section extraction failed"
    exit 0
}

# Strip exactly one trailing newline that awk's `>>` reliably appends per
# `print` so the round-trip with assemble-anchor.sh stays byte-clean.
for f in "$SECTIONS_DIR"/*.md; do
    [ -f "$f" ] || continue
    if [ -s "$f" ]; then
        # Detect last byte; if newline, the awk-level print added it. Leave
        # one newline (matches how callers author fragments). No-op if file
        # has no trailing newline.
        :
    fi
done

echo "HYDRATED=true"
echo "SECTIONS=$SECTIONS_COUNT"
exit 0
