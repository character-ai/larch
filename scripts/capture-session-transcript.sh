#!/usr/bin/env bash
# capture-session-transcript.sh — best-effort session transcript capture.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

usage() {
    cat <<'USAGE' >&2
Usage:
  capture-session-transcript.sh --source-file PATH --log-root DIR --skill S --run-id R --no-logs-commit true|false --execution-issues-log PATH
USAGE
}

SOURCE_FILE=""
LOG_ROOT=""
SKILL=""
RUN_ID=""
NO_LOGS_COMMIT=""
EXECUTION_ISSUES_LOG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --source-file)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            SOURCE_FILE="$2"; shift 2 ;;
        --log-root)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            LOG_ROOT="$2"; shift 2 ;;
        --skill)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            SKILL="$2"; shift 2 ;;
        --run-id)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            RUN_ID="$2"; shift 2 ;;
        --no-logs-commit)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            NO_LOGS_COMMIT="$2"; shift 2 ;;
        --execution-issues-log)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            EXECUTION_ISSUES_LOG="$2"; shift 2 ;;
        *) usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0 ;;
    esac
done

if [ -z "$LOG_ROOT" ] || [ -z "$SKILL" ] || [ -z "$RUN_ID" ]; then
    echo "SESSION_TRANSCRIPT_STATUS=usage-error" >&1
    usage
    exit 0
fi
case "${NO_LOGS_COMMIT:-}" in
    true|false) ;;
    *) echo "SESSION_TRANSCRIPT_STATUS=usage-error" >&1; usage; exit 0 ;;
esac

append_warning() {
    local status="$1"
    local message="$2"

    [ -n "$EXECUTION_ISSUES_LOG" ] || return 0
    "$SCRIPT_DIR/append-execution-issue.sh" \
        --log "$EXECUTION_ISSUES_LOG" \
        --category Warnings \
        --entry "- **Step 18 — session-transcript status=$status:** $message" \
        >/dev/null 2>&1 || true
}

emit_status() {
    local status="$1"
    local message="$2"

    append_warning "$status" "$message"
    echo "SESSION_TRANSCRIPT_STATUS=$status"
    exit 0
}

TRANSCRIPT_PATH=""
if [ -z "$SOURCE_FILE" ] || [ ! -f "$SOURCE_FILE" ] || [ ! -s "$SOURCE_FILE" ]; then
    recovered=""
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -d "$IMPLEMENT_TMPDIR" ] && [ -n "${HOME:-}" ]; then
        # Narrow search to the encoded project dir for the current git repo, mirroring
        # token-claude-source.sh. Falls back to the broader projects root if git is
        # unavailable or the project dir doesn't exist yet.
        repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || repo_root=""
        if [ -n "$repo_root" ]; then
            repo_root=$(cd "$repo_root" && pwd -P 2>/dev/null) || repo_root=""
        fi
        if [ -n "$repo_root" ]; then
            encoded=$(printf '%s' "$repo_root" | sed 's#/#-#g')
            project_search_dir="$HOME/.claude/projects/$encoded"
        else
            project_search_dir="$HOME/.claude/projects"
        fi
        # Use session-id file as a stable time reference (written once at Step 0, never
        # modified). The IMPLEMENT_TMPDIR directory itself is unsuitable because its mtime
        # advances with every log/artifact write during the run, and can end up newer than
        # an idle transcript file.
        ref_file="$IMPLEMENT_TMPDIR/session-id"
        [ -f "$ref_file" ] || ref_file="$IMPLEMENT_TMPDIR"
        if [ -d "$project_search_dir" ]; then
            recovered=$(
                find "$project_search_dir" -name '*.jsonl' ! -type l -newer "$ref_file" 2>/dev/null \
                    | while IFS= read -r f; do
                        stat_mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || printf '0')
                        printf '%s\t%s\n' "$stat_mtime" "$f"
                    done \
                    | sort -rn \
                    | awk -F'\t' 'NR==1 { print $2 }'
            ) || true
        fi
    fi
    if [ -n "$recovered" ] && [ -f "$recovered" ]; then
        TRANSCRIPT_PATH="$recovered"
        append_warning "source-file-recovered-via-discovery" \
            "Original snapshot was missing; recovered transcript via project-dir probe: $recovered"
    else
        emit_status "source-file-missing" "Claude source file was empty or not a regular file; transcript capture skipped."
    fi
else
    TRANSCRIPT_PATH="$(awk 'BEGIN{prefix="TRANSCRIPT_PATH="} index($0, prefix) == 1 {print substr($0, length(prefix) + 1); exit}' "$SOURCE_FILE" 2>/dev/null || true)"
    if [ -z "$TRANSCRIPT_PATH" ]; then
        emit_status "transcript-path-missing" "Claude source file did not contain a TRANSCRIPT_PATH entry; transcript capture skipped."
    fi
fi

if [ ! -f "$TRANSCRIPT_PATH" ]; then
    emit_status "transcript-file-missing" "TRANSCRIPT_PATH target was missing or not a regular file; transcript capture skipped."
fi

if ! "$SCRIPT_DIR/larch-log.sh" write \
    --log-root "$LOG_ROOT" \
    --skill "$SKILL" \
    --run-id "$RUN_ID" \
    --batch session-transcript \
    --input-file "$TRANSCRIPT_PATH" \
    >/dev/null 2>&1; then
    emit_status "write-failed" "larch-log write failed; transcript was not captured."
fi

if [ "$NO_LOGS_COMMIT" = "true" ]; then
    emit_status "suppressed-no-logs-commit" "--no-logs-commit was set; transcript was written under the staging log root but not committed."
fi

if ! "$SCRIPT_DIR/larch-log.sh" commit \
    --log-root "$LOG_ROOT" \
    --skill "$SKILL" \
    --run-id "$RUN_ID" \
    >/dev/null 2>&1; then
    emit_status "commit-failed" "write succeeded but git commit failed; transcript remains under the staging log root."
fi

current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || true)
if [ "$current_branch" = "main" ]; then
    ahead=$(git rev-list --count "origin/main..HEAD" 2>/dev/null || echo 0)
    if [ "${ahead:-0}" -gt 0 ]; then
        git push origin main >/dev/null 2>&1 || true
    fi
fi

emit_status "captured" "session transcript was written and committed."
