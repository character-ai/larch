#!/usr/bin/env bash
# write-design-manifest.sh — Export /design artifacts for /implement without
# relying on conversation context.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

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
if [[ ! -d "$IMPLEMENT_TMPDIR" ]]; then
    echo "write-design-manifest.sh: implement tmpdir not found: $IMPLEMENT_TMPDIR" >&2
    exit 1
fi

# Round 3 FINDING_R3_D: canonicalize both tmpdirs to absolute paths so the
# manifest never contains relative paths the reader would reject with
# ERROR=path-not-absolute.
DESIGN_TMPDIR=$(cd -P "$DESIGN_TMPDIR" && pwd -P)
IMPLEMENT_TMPDIR=$(cd -P "$IMPLEMENT_TMPDIR" && pwd -P)

EXPORT_DIR="$IMPLEMENT_TMPDIR/design-export"
mkdir -p "$EXPORT_DIR"

# Round 3 FINDING_R3_B: stage everything into a fresh sibling staging dir.
# We previously copied files directly into the live $EXPORT_DIR while the
# old manifest.env remained valid until the final mv, so a partial-rerun
# failure could leave MANIFEST_OK=true over a mixed-vintage artifact bundle
# (new plan + old tally). Stage to STAGE_DIR; on success poison the live
# manifest then mv each staged file into place + mv the new manifest; on
# failure leave the live $EXPORT_DIR + manifest untouched.
STAGE_DIR=$(mktemp -d "${EXPORT_DIR}.stage.XXXXXX")
stage_cleanup() {
    rm -rf "$STAGE_DIR"
}
trap stage_cleanup EXIT

# Round 3 FINDING_R3_A: reject symlinked source artifacts. cp follows symlinks
# and produces a regular destination file, which then bypasses the reader's
# destination symlink check — letting a symlinked source leak content from
# outside $DESIGN_TMPDIR into design-export.
reject_symlink_source() {
    local src="$1"
    if [[ -L "$src" ]]; then
        echo "write-design-manifest.sh: source artifact is a symlink (rejected): $src" >&2
        exit 1
    fi
}

# Defense-in-depth: also require source artifacts to canonically resolve under
# canonical $DESIGN_TMPDIR. A symlink-free source can still be a hard link or
# bind-mount sneaking in an outside file; the realpath check catches those.
require_inside_design_tmpdir() {
    local src="$1"
    local canon
    if ! canon=$(cd -P "$(dirname "$src")" 2>/dev/null && pwd -P); then
        echo "write-design-manifest.sh: cannot resolve source path: $src" >&2
        exit 1
    fi
    canon="$canon/$(basename "$src")"
    case "$canon" in
        "$DESIGN_TMPDIR"/*) ;;
        *)
            echo "write-design-manifest.sh: source artifact escapes design tmpdir: $src -> $canon" >&2
            exit 1
            ;;
    esac
}

copy_required_nonempty() {
    local src="$1"
    local dest="$2"
    reject_symlink_source "$src"
    if [[ ! -f "$src" || ! -s "$src" ]]; then
        echo "write-design-manifest.sh: required non-empty artifact missing: $src" >&2
        exit 1
    fi
    require_inside_design_tmpdir "$src"
    cp "$src" "$dest"
    if [[ ! -s "$dest" ]]; then
        echo "write-design-manifest.sh: copied artifact is empty: $dest" >&2
        exit 1
    fi
}

copy_required_may_be_empty() {
    local src="$1"
    local dest="$2"
    reject_symlink_source "$src"
    if [[ ! -f "$src" ]]; then
        echo "write-design-manifest.sh: required artifact missing: $src" >&2
        exit 1
    fi
    require_inside_design_tmpdir "$src"
    cp "$src" "$dest"
}

# Stage all artifacts to $STAGE_DIR (under their final basenames). Path
# variables in the manifest still use $EXPORT_DIR — the rename below makes
# those paths valid only after every copy succeeds.
copy_required_nonempty "$DESIGN_TMPDIR/plan.txt" "$STAGE_DIR/plan.txt"
copy_required_nonempty "$DESIGN_TMPDIR/diff-lines.txt" "$STAGE_DIR/diff-lines.txt"
copy_required_nonempty "$DESIGN_TMPDIR/voting-tally.md" "$STAGE_DIR/voting-tally.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/contested-decisions.md" "$STAGE_DIR/contested-decisions.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/oos.md" "$STAGE_DIR/oos.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/rejected-findings.md" "$STAGE_DIR/rejected-findings.md"
copy_required_may_be_empty "$DESIGN_TMPDIR/accepted-plan-findings.md" "$STAGE_DIR/accepted-plan-findings.md"
ARCHITECTURE_DIAGRAM_FILE=""
if [[ -f "$DESIGN_TMPDIR/architecture-diagram.md" ]]; then
    if [[ -L "$DESIGN_TMPDIR/architecture-diagram.md" ]]; then
        echo "write-design-manifest.sh: optional source artifact is a symlink (rejected): $DESIGN_TMPDIR/architecture-diagram.md" >&2
        exit 1
    fi
    require_inside_design_tmpdir "$DESIGN_TMPDIR/architecture-diagram.md"
    cp "$DESIGN_TMPDIR/architecture-diagram.md" "$STAGE_DIR/architecture-diagram.md"
    ARCHITECTURE_DIAGRAM_FILE="$EXPORT_DIR/architecture-diagram.md"
fi

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
manifest_cleanup() {
    rm -f "$TMP"
    rm -rf "$STAGE_DIR"
}
trap manifest_cleanup EXIT

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

# Round 3 FINDING_R3_B: poison the live manifest BEFORE swapping artifacts so
# the reader fails closed during the brief window between artifact swap and
# manifest swap. Then atomically replace the artifacts and finally the
# manifest. On failure mid-swap, the absent manifest forces /implement to
# rerun /design rather than read mixed-vintage artifacts.
rm -f "$MANIFEST"
# Move staged artifacts into place, overwriting any previous bundle. We use
# explicit per-file mv to keep permissions/atomicity simple; cp -p was already
# the existing semantic for content and rename-into-place gives us atomic
# per-file replacement.
for f in "$STAGE_DIR"/*; do
    base=$(basename "$f")
    mv -f "$f" "$EXPORT_DIR/$base"
done
mv "$TMP" "$MANIFEST"
trap - EXIT
rm -rf "$STAGE_DIR"
emit_kv MANIFEST_WRITTEN "$MANIFEST"
