#!/usr/bin/env bash
# write-design-manifest.sh — Export /design artifacts for /implement without
# relying on conversation context.

set -euo pipefail

DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        --implement-tmpdir)
            IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"
            shift 2
            ;;
        *)
            echo "write-design-manifest.sh: unknown flag: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" || -z "$IMPLEMENT_TMPDIR" ]]; then
    echo "write-design-manifest.sh: --design-tmpdir and --implement-tmpdir are required" >&2
    exit 2
fi

if [[ ! -d "$DESIGN_TMPDIR" ]]; then
    echo "write-design-manifest.sh: design tmpdir not found: $DESIGN_TMPDIR" >&2
    exit 1
fi

EXPORT_DIR="$IMPLEMENT_TMPDIR/design-export"
mkdir -p "$EXPORT_DIR"

copy_required_nonempty() {
    local src="$1"
    local dest="$2"
    if [[ ! -f "$src" || ! -s "$src" ]]; then
        echo "write-design-manifest.sh: required non-empty artifact missing: $src" >&2
        exit 1
    fi
    cp "$src" "$dest"
    if [[ ! -s "$dest" ]]; then
        echo "write-design-manifest.sh: copied artifact is empty: $dest" >&2
        exit 1
    fi
}

copy_required_may_be_empty() {
    local src="$1"
    local dest="$2"
    if [[ ! -f "$src" ]]; then
        echo "write-design-manifest.sh: required artifact missing: $src" >&2
        exit 1
    fi
    cp "$src" "$dest"
}

copy_optional() {
    local src="$1"
    local dest="$2"
    if [[ -f "$src" ]]; then
        cp "$src" "$dest"
        printf '%s\n' "$dest"
    fi
    return 0
}

copy_required_nonempty "$DESIGN_TMPDIR/plan.txt" "$EXPORT_DIR/plan.txt"
copy_required_nonempty "$DESIGN_TMPDIR/voting-tally.md" "$EXPORT_DIR/voting-tally.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/contested-decisions.md" "$EXPORT_DIR/contested-decisions.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/oos.md" "$EXPORT_DIR/oos.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/rejected-findings.md" "$EXPORT_DIR/rejected-findings.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/accepted-plan-findings.md" "$EXPORT_DIR/accepted-plan-findings.md"
ARCHITECTURE_DIAGRAM_FILE=$(copy_optional "$DESIGN_TMPDIR/architecture-diagram.md" "$EXPORT_DIR/architecture-diagram.md")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_ID="${SESSION_ID:-}"
if [[ -z "$SESSION_ID" && -f "$IMPLEMENT_TMPDIR/session-id" ]]; then
    SESSION_ID=$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id")
fi
if [[ -z "$SESSION_ID" ]]; then
    SESSION_ID=$(basename "$IMPLEMENT_TMPDIR")
fi
# Defense-in-depth (Round 2 FINDING_F): the reader rejects values containing
# any C0/DEL control character. Strip the same set at write time so we never
# emit a manifest the reader must reject.
SESSION_ID=$(printf '%s' "$SESSION_ID" | tr -d '\000-\037\177')
if [[ -z "$SESSION_ID" ]]; then
    echo "write-design-manifest.sh: SESSION_ID empty after control-char strip" >&2
    exit 1
fi

MANIFEST="$EXPORT_DIR/manifest.env"
TMP=$(mktemp "${MANIFEST}.tmp.XXXXXX")
cleanup() {
    rm -f "$TMP"
}
trap cleanup EXIT

{
    printf 'MANIFEST_VERSION=1\n'
    printf 'PLAN_FILE=%s/plan.txt\n' "$EXPORT_DIR"
    printf 'PLAN_REVIEW_TALLY_FILE=%s/voting-tally.md\n' "$EXPORT_DIR"
    printf 'CONTESTED_CRITERIA_FILE=%s/contested-decisions.md\n' "$EXPORT_DIR"
    printf 'OOS_FILE=%s/oos.md\n' "$EXPORT_DIR"
    printf 'REJECTED_FINDINGS_FILE=%s/rejected-findings.md\n' "$EXPORT_DIR"
    printf 'ACCEPTED_PLAN_FINDINGS_FILE=%s/accepted-plan-findings.md\n' "$EXPORT_DIR"
    if [[ -n "$ARCHITECTURE_DIAGRAM_FILE" ]]; then
        printf 'ARCHITECTURE_DIAGRAM_FILE=%s\n' "$ARCHITECTURE_DIAGRAM_FILE"
    fi
    printf 'TIMESTAMP=%s\n' "$TIMESTAMP"
    printf 'SESSION_ID=%s\n' "$SESSION_ID"
} > "$TMP"

mv "$TMP" "$MANIFEST"
trap - EXIT
printf 'MANIFEST_WRITTEN=%s\n' "$MANIFEST"
