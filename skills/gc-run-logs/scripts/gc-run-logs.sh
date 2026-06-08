#!/usr/bin/env bash
# gc-run-logs.sh — Age-based retention for committed larch run-log directories.
#
# Slims or deletes run dirs in larch-logs/{design,implement,review}/ whose run
# date is older than --older-than DAYS (default 90). On the non-dry-run path,
# creates a branch, commits the changes, pushes, and creates a PR for operator
# review and merge.
#
# Outputs (KEY=value on stdout):
#   DIRS_SCANNED=<N>    Total run dirs examined.
#   DIRS_QUALIFYING=<N> Dirs old enough to process.
#   DIRS_SLIMMED=<N>    Dirs slimmed (non-delete mode).
#   DIRS_DELETED=<N>    Dirs fully deleted (--delete mode).
#   DIRS_SKIPPED=<N>    Dirs skipped (guard matched, or already slimmed).
#   BYTES_FREED=<N>     Approximate bytes freed (0 in dry-run).
#   DRY_RUN=true|false
#   PR_URL=<url>        PR URL (empty when --dry-run or no qualifying dirs).
#   STATUS=ok|error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

# ---------------------------------------------------------------------------
# Flag parsing
# ---------------------------------------------------------------------------
OLDER_THAN=90
DELETE=false
DRY_RUN=false
PARSE_ERROR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --older-than)
            if [ $# -lt 2 ]; then PARSE_ERROR="older-than-missing-value"; break; fi
            OLDER_THAN="$2"; shift 2 ;;
        --delete)
            DELETE=true; shift ;;
        --dry-run)
            DRY_RUN=true; shift ;;
        *)
            PARSE_ERROR="unknown-flag: $1"; break ;;
    esac
done

if [ -n "$PARSE_ERROR" ]; then
    larch_err "gc-run-logs: flag error: $PARSE_ERROR"
    emit_kv STATUS "error"
    exit 2
fi

case "$OLDER_THAN" in
    ''|*[!0-9]*)
        larch_err "gc-run-logs: --older-than must be a positive integer (got: $OLDER_THAN)"
        emit_kv STATUS "error"
        exit 2
        ;;
esac
if [ "$OLDER_THAN" -lt 1 ]; then
    larch_err "gc-run-logs: --older-than must be >= 1"
    emit_kv STATUS "error"
    exit 2
fi

# ---------------------------------------------------------------------------
# Locate repo root
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    larch_err "gc-run-logs: not inside a git repository"
    emit_kv STATUS "error"
    exit 2
}

LOGS_ROOT="$REPO_ROOT/larch-logs"
if [ ! -d "$LOGS_ROOT" ]; then
    larch_err "gc-run-logs: larch-logs/ not found at $REPO_ROOT"
    emit_kv STATUS "error"
    exit 2
fi

# ---------------------------------------------------------------------------
# Single-runner guard: refuse when the working tree is dirty
# ---------------------------------------------------------------------------
if [ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)" ]; then
    larch_err "gc-run-logs: working tree is dirty — ensure no /implement or /design session is active before running GC"
    emit_kv STATUS "error"
    exit 2
fi

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)" || CURRENT_BRANCH=""
if [ "$CURRENT_BRANCH" != "main" ]; then
    larch_err "gc-run-logs: must be run from the main branch (currently on: ${CURRENT_BRANCH:-detached})"
    emit_kv STATUS "error"
    exit 2
fi

# ---------------------------------------------------------------------------
# Compute cutoff datetime string (ISO 8601, UTC)
# ---------------------------------------------------------------------------
CUTOFF_DT="$(python3 <<PY
import datetime
d = datetime.datetime.utcnow() - datetime.timedelta(days=${OLDER_THAN})
print(d.strftime('%Y-%m-%dT%H:%M:%SZ'))
PY
)" || {
    larch_err "gc-run-logs: failed to compute cutoff date"
    emit_kv STATUS "error"
    exit 2
}

larch_err "Cutoff date: $CUTOFF_DT (runs started before this are qualifying)"

# ---------------------------------------------------------------------------
# Keep-set helpers
# ---------------------------------------------------------------------------

# Returns 0 if the filename is in the keep set for the given skill.
is_kept() {
    local filename="$1" skill="$2"
    # Common keep files (both skills)
    case "$filename" in
        manifest.json|final-summary.md|gc-slimmed) return 0 ;;
    esac
    case "$skill" in
        implement)
            case "$filename" in
                token-report.json|timing-report.json|review-findings-full.jsonl|execution-issues.ndjson|run-statistics.md) return 0 ;;
            esac ;;
        design)
            case "$filename" in
                token-report-final.json|timing-report-final.json|run-params.json|plan.txt) return 0 ;;
            esac ;;
    esac
    return 1
}

# ---------------------------------------------------------------------------
# Date resolution for a run dir
# Returns the started_at string, or empty on failure.
# ---------------------------------------------------------------------------
resolve_run_date() {
    local dir="$1"
    local manifest="$dir/manifest.json"
    local started_at=""

    if [ -f "$manifest" ]; then
        started_at="$(awk -F'"' '/started_at/{print $4; exit}' "$manifest" 2>/dev/null || true)"
    fi

    if [ -n "$started_at" ]; then
        printf '%s\n' "$started_at"
        return 0
    fi

    # Fallback: first-commit date for any file in this dir
    local first_commit
    first_commit="$(git -C "$REPO_ROOT" log --diff-filter=A --format="%aI" -- "$dir/" 2>/dev/null | tail -1 || true)"
    if [ -n "$first_commit" ]; then
        printf '%s\n' "$first_commit"
        return 0
    fi

    return 1
}

# Returns 0 if run_date < cutoff_dt (string comparison on ISO 8601 sorts correctly)
is_older_than_cutoff() {
    local run_date="$1"
    [ "$run_date" \< "$CUTOFF_DT" ]
}

# ---------------------------------------------------------------------------
# Enumerate run dirs
# ---------------------------------------------------------------------------
DIRS_SCANNED=0
DIRS_QUALIFYING=0
DIRS_SLIMMED=0
DIRS_DELETED=0
DIRS_SKIPPED=0
BYTES_FREED=0

# Collect qualifying dirs (skill:path pairs) into a temp file (Bash 3.2 compat)
TMPWORK="$(mktemp -d "${TMPDIR:-/tmp}/gc-run-logs.XXXXXX")"
PLAN_FILE="$TMPWORK/plan.txt"
: > "$PLAN_FILE"

cleanup_tmpwork() {
    rm -rf "$TMPWORK"
}
trap cleanup_tmpwork EXIT

for skill in design implement review; do
    skill_dir="$LOGS_ROOT/$skill"
    [ -d "$skill_dir" ] || continue

    while IFS= read -r -d $'\0' run_dir; do
        [ -d "$run_dir" ] || continue
        DIRS_SCANNED=$((DIRS_SCANNED + 1))
        run_name="$(basename "$run_dir")"

        # Guard: skip dirs with pause-state.txt (resumable design sessions)
        if [ -f "$run_dir/pause-state.txt" ]; then
            DIRS_SKIPPED=$((DIRS_SKIPPED + 1))
            larch_err "  skip (paused): $skill/$run_name"
            continue
        fi

        # Guard: already slimmed
        if [ -f "$run_dir/gc-slimmed" ]; then
            DIRS_SKIPPED=$((DIRS_SKIPPED + 1))
            larch_err "  skip (already-slimmed): $skill/$run_name"
            continue
        fi

        # Resolve run date
        run_date="$(resolve_run_date "$run_dir")" || {
            DIRS_SKIPPED=$((DIRS_SKIPPED + 1))
            larch_err "  skip (no-date): $skill/$run_name"
            continue
        }

        if [ -z "$run_date" ]; then
            DIRS_SKIPPED=$((DIRS_SKIPPED + 1))
            larch_err "  skip (no-date): $skill/$run_name"
            continue
        fi

        if ! is_older_than_cutoff "$run_date"; then
            continue
        fi

        DIRS_QUALIFYING=$((DIRS_QUALIFYING + 1))
        printf '%s\t%s\t%s\n' "$skill" "$run_dir" "$run_date" >> "$PLAN_FILE"

        if [ "$DELETE" = "true" ]; then
            larch_err "  plan delete: $skill/$run_name (date: $run_date)"
        else
            larch_err "  plan slim:   $skill/$run_name (date: $run_date)"
        fi

    done < <(find "$skill_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null) || true
done

larch_err ""
larch_err "Scan complete: $DIRS_SCANNED scanned, $DIRS_QUALIFYING qualifying, $DIRS_SKIPPED skipped"

emit_kv DIRS_SCANNED "$DIRS_SCANNED"
emit_kv DIRS_QUALIFYING "$DIRS_QUALIFYING"
emit_kv DIRS_SKIPPED "$DIRS_SKIPPED"
emit_kv DRY_RUN "$DRY_RUN"

if [ "$DIRS_QUALIFYING" -eq 0 ]; then
    larch_err "No run dirs qualify for GC. Nothing to do."
    emit_kv DIRS_SLIMMED 0
    emit_kv DIRS_DELETED 0
    emit_kv BYTES_FREED 0
    emit_kv PR_URL ""
    emit_kv STATUS "ok"
    exit 0
fi

if [ "$DRY_RUN" = "true" ]; then
    larch_err ""
    larch_err "Dry-run complete. Pass without --dry-run to apply changes."
    emit_kv DIRS_SLIMMED 0
    emit_kv DIRS_DELETED 0
    emit_kv BYTES_FREED 0
    emit_kv PR_URL ""
    emit_kv STATUS "ok"
    exit 0
fi

# ---------------------------------------------------------------------------
# Apply changes on a dedicated branch
# ---------------------------------------------------------------------------
BRANCH_DATE="$(date '+%Y%m%d')"
GC_BRANCH="gc-run-logs/slim-${BRANCH_DATE}"

larch_err ""
larch_err "Creating branch: $GC_BRANCH"
git -C "$REPO_ROOT" checkout -b "$GC_BRANCH" 2>/dev/null || {
    larch_err "gc-run-logs: failed to create branch $GC_BRANCH"
    emit_kv STATUS "error"
    exit 2
}

apply_error() {
    larch_err "gc-run-logs: error during apply — aborting. Run 'git checkout main' to recover."
    emit_kv STATUS "error"
    exit 2
}
trap apply_error ERR

while IFS=$'\t' read -r skill run_dir run_date; do
    [ -d "$run_dir" ] || continue
    run_name="$(basename "$run_dir")"

    if [ "$DELETE" = "true" ]; then
        # Compute bytes freed before deletion
        dir_bytes="$(du -sk "$run_dir" 2>/dev/null | awk '{print $1}' || echo 0)"
        BYTES_FREED=$((BYTES_FREED + dir_bytes * 1024))
        rm -rf "$run_dir"
        DIRS_DELETED=$((DIRS_DELETED + 1))
        larch_err "  deleted: $skill/$run_name"
    else
        # Slim: remove all items not in the keep set
        dir_bytes_before="$(du -sk "$run_dir" 2>/dev/null | awk '{print $1}' || echo 0)"

        # Remove subdirectories
        while IFS= read -r -d $'\0' subdir; do
            rm -rf "$subdir"
        done < <(find "$run_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null) || true

        # Remove files not in the keep set
        while IFS= read -r -d $'\0' entry; do
            fname="$(basename "$entry")"
            if ! is_kept "$fname" "$skill"; then
                rm -f "$entry"
            fi
        done < <(find "$run_dir" -mindepth 1 -maxdepth 1 -type f -print0 2>/dev/null) || true

        # Write gc-slimmed marker
        printf '%s\n' "$run_date" > "$run_dir/gc-slimmed"

        dir_bytes_after="$(du -sk "$run_dir" 2>/dev/null | awk '{print $1}' || echo 0)"
        freed=$((( dir_bytes_before - dir_bytes_after ) * 1024))
        [ "$freed" -gt 0 ] && BYTES_FREED=$((BYTES_FREED + freed)) || true

        DIRS_SLIMMED=$((DIRS_SLIMMED + 1))
        larch_err "  slimmed: $skill/$run_name"
    fi
done < "$PLAN_FILE"

# Restore normal error trap
trap - ERR

# Stage and commit
larch_err ""
larch_err "Staging changes..."
git -C "$REPO_ROOT" add -A -- "$LOGS_ROOT/" 2>/dev/null

if [ "$DELETE" = "true" ]; then
    COMMIT_MSG="gc-run-logs: delete run dirs older than ${OLDER_THAN}d (${DIRS_DELETED} dirs)"
else
    COMMIT_MSG="gc-run-logs: slim run dirs older than ${OLDER_THAN}d to consumer core (${DIRS_SLIMMED} dirs)"
fi

git -C "$REPO_ROOT" commit -m "$COMMIT_MSG" 2>/dev/null

larch_err "Pushing branch..."
git -C "$REPO_ROOT" push -u origin "$GC_BRANCH" 2>/dev/null

larch_err "Creating PR..."
if [ "$DELETE" = "true" ]; then
    PR_TITLE="gc-run-logs: delete run dirs older than ${OLDER_THAN}d"
    PR_BODY="Log-only maintenance PR created by \`/gc-run-logs --delete --older-than $OLDER_THAN\`.

**Dirs deleted**: $DIRS_DELETED (fully removed from working tree; content recoverable via git history)
**Threshold**: $OLDER_THAN days (cutoff: $CUTOFF_DT)

Operator must review and merge. See \`docs/run-logs.md\` Retention section for policy."
else
    PR_TITLE="gc-run-logs: slim run dirs older than ${OLDER_THAN}d to consumer core"
    PR_BODY="Log-only maintenance PR created by \`/gc-run-logs --older-than $OLDER_THAN\`.

**Dirs slimmed**: $DIRS_SLIMMED (consumer-core files preserved; round-level forensic detail removed)
**Threshold**: $OLDER_THAN days (cutoff: $CUTOFF_DT)
**Bytes freed (approx)**: $BYTES_FREED

Consumer-core keep set preserved per \`docs/run-logs.md\` Retention section. Slimmed dirs carry a \`gc-slimmed\` marker. Operator must review and merge."
fi

PR_URL="$(gh pr create \
    --title "$PR_TITLE" \
    --body "$PR_BODY" \
    --base main \
    --head "$GC_BRANCH" 2>/dev/null)" || {
    larch_err "gc-run-logs: failed to create PR"
    emit_kv STATUS "error"
    exit 2
}

larch_err "PR created: $PR_URL"

emit_kv DIRS_SLIMMED "$DIRS_SLIMMED"
emit_kv DIRS_DELETED "$DIRS_DELETED"
emit_kv BYTES_FREED "$BYTES_FREED"
emit_kv PR_URL "$PR_URL"
emit_kv STATUS "ok"
