#!/usr/bin/env bash
# step-7a.sh — consolidated /implement Step 7a diagram + pre-bump flush helper.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: step-7a.sh --implement-tmpdir PATH [--issue-number N] [--run-id ID] [--no-logs-commit BOOL] [--forked-target BOOL]"
}

emit_tail() {
    emit_kv DIAGRAM_STATUS "${DIAGRAM_STATUS:-}"
    emit_kv DIAGRAM_PATH "${DIAGRAM_PATH:-}"
    emit_kv COMMENT_URL "${COMMENT_URL:-}"
    emit_kv LOG_FLUSH_STATUS "${LOG_FLUSH_STATUS:-}"
    emit_kv STEP_7A_BAIL_REASON "${STEP_7A_BAIL_REASON:-}"
}

fail_usage() {
    STEP_7A_BAIL_REASON=argv
    usage
    emit_tail
    exit 2
}

read_session_key() {
    local key=$1 default_value=$2 script
    script="$PLUGIN_ROOT/scripts/read-session-env-key.sh"
    if [ -n "${SESSION_ENV_FILE:-}" ] && [ -f "$SESSION_ENV_FILE" ] && [ -f "$script" ]; then
        bash "$script" --file "$SESSION_ENV_FILE" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

append_failure() {
    local category=$1 site=$2 tool=$3 exit_code=$4 output_file=$5
    [ -f "$output_file" ] || : > "$output_file" 2>/dev/null || true
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$exit_code" \
        --category "$category" \
        --output-file "$output_file" \
        --redact >/dev/null 2>&1 || true
}

append_best_effort_failure() {
    local site=$1 tool=$2 exit_code=$3 output_file=$4
    append_failure "Tool Failures" "$site" "$tool" "$exit_code" "$output_file"
}

kv_value() {
    local key=$1 file=$2
    awk -F= -v key="$key" '$1==key{print substr($0, index($0, "=") + 1); exit}' "$file" 2>/dev/null
}

is_non_runtime_path() {
    local path=$1 base ext
    case "$path" in
        docs/*) return 0 ;;
    esac
    base=${path##*/}
    case "$base" in
        CHANGELOG|CHANGELOG.md) return 0 ;;
    esac
    ext=${path##*.}
    case "$ext" in
        txt|tsv) return 0 ;;
    esac
    return 1
}

is_small_non_runtime_change() {
    local merge_base changed_files changed_count path
    merge_base=$(git merge-base HEAD "${base_remote}/${base_ref}" 2>/dev/null) || merge_base=""
    if [ -n "$merge_base" ]; then
        changed_files=$(git diff --name-only "${merge_base}..HEAD" 2>/dev/null)
    else
        changed_files=""
    fi
    changed_count=$(printf '%s\n' "$changed_files" | grep -c . 2>/dev/null || echo 0)
    if [ -z "$merge_base" ] || [ "$changed_count" -eq 0 ]; then
        return 1
    fi
    if [ "$changed_count" -gt 2 ]; then
        return 1
    fi
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        is_non_runtime_path "$path" || return 1
    done <<EOF
$changed_files
EOF
    return 0
}

compose_summary_diagrams() {
    rm -f "$IMPLEMENT_TMPDIR/code-flow-section.md" 2>/dev/null || true
    if [ "${DIAGRAM_STATUS:-}" = "ok" ] && [ -f "$IMPLEMENT_TMPDIR/code-flow-diagram.md" ]; then
        cat "$IMPLEMENT_TMPDIR/code-flow-diagram.md" > "$IMPLEMENT_TMPDIR/code-flow-section.md"
    else
        rm -f "$IMPLEMENT_TMPDIR/code-flow-diagram.md" 2>/dev/null || true
    fi
}

run_larch_log_write() {
    local batch=$1 input_file=$2 out_file rc
    out_file="$IMPLEMENT_TMPDIR/larch-log-write-${batch}.log"
    set +e
    "$PLUGIN_ROOT/scripts/larch-log.sh" write \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --batch "$batch" \
        --input-file "$input_file" >"$out_file" 2>&1
    rc=$?
    set +e
    if [ "$rc" -ne 0 ]; then
        append_best_effort_failure "step-7a" "larch-log.sh write ${batch}" "$rc" "$out_file"
    fi
}

run_log_flush() {
    local rc out_file status_file
    LOG_FLUSH_STATUS=ok

    "$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 8 — version bump" || true
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 8 — version bump" || true

    out_file="$IMPLEMENT_TMPDIR/pre-bump-flush-execution-issues.log"
    set +e
    "$PLUGIN_ROOT/skills/implement/scripts/flush-execution-issues.sh" \
        --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --run-id "$RUN_ID" 2>"$out_file"
    rc=$?
    set +e
    if [ "$rc" -ne 0 ]; then
        LOG_FLUSH_STATUS=degraded
        append_best_effort_failure "step-7a" "flush-execution-issues.sh" "$rc" "$out_file"
    fi

    "$PLUGIN_ROOT/scripts/token-report.sh" --full --format json --output "$IMPLEMENT_TMPDIR/token-report-rendered.json" || true
    "$PLUGIN_ROOT/scripts/timing-report.sh" --full --format json --output "$IMPLEMENT_TMPDIR/timing-report-rendered.json" || true

    run_larch_log_write token-report "$IMPLEMENT_TMPDIR/token-report-rendered.json"
    run_larch_log_write timing-report "$IMPLEMENT_TMPDIR/timing-report-rendered.json"
    [ -f "$IMPLEMENT_TMPDIR/parent-issue.md" ] && run_larch_log_write parent-issue "$IMPLEMENT_TMPDIR/parent-issue.md"
    [ -f "$IMPLEMENT_TMPDIR/pre-review-head.txt" ] && run_larch_log_write pre-review-head "$IMPLEMENT_TMPDIR/pre-review-head.txt"
    [ -f "$IMPLEMENT_TMPDIR/pre-review-untracked.txt" ] && run_larch_log_write pre-review-untracked "$IMPLEMENT_TMPDIR/pre-review-untracked.txt"
    [ -f "$IMPLEMENT_TMPDIR/codex-impl-transcript.txt" ] && run_larch_log_write codex-impl-transcript "$IMPLEMENT_TMPDIR/codex-impl-transcript.txt"
    if [ -f "$IMPLEMENT_TMPDIR/codex-impl-transcript.txt.meta" ]; then
        set +e
        bash -lc 'set -euo pipefail; source "$1/scripts/lib-redact.sh"; larch_redact_strip_meta_cmd_json "$2/codex-impl-transcript.txt.meta" "$2/codex-impl-transcript.txt.meta.trimmed"' _ "$PLUGIN_ROOT" "$IMPLEMENT_TMPDIR"
        rc=$?
        set +e
        [ "$rc" -eq 0 ] && run_larch_log_write codex-impl-transcript-meta "$IMPLEMENT_TMPDIR/codex-impl-transcript.txt.meta.trimmed"
    fi
    [ -f "$IMPLEMENT_TMPDIR/codex-impl-transcript.txt.prompt" ] && run_larch_log_write codex-impl-transcript-prompt "$IMPLEMENT_TMPDIR/codex-impl-transcript.txt.prompt"
    [ -f "$IMPLEMENT_TMPDIR/codex-commit-message.txt" ] && run_larch_log_write codex-commit-message "$IMPLEMENT_TMPDIR/codex-commit-message.txt"
    [ -f "$IMPLEMENT_TMPDIR/manifest-raw.json" ] && run_larch_log_write codex-impl-manifest-raw "$IMPLEMENT_TMPDIR/manifest-raw.json"

    out_file="$IMPLEMENT_TMPDIR/capture-session-transcript.log"
    status_file="$IMPLEMENT_TMPDIR/capture-session-transcript.stdout"
    set +e
    LARCH_QUIET_DISABLE=1 "$PLUGIN_ROOT/scripts/capture-session-transcript.sh" \
        --source-file "$LARCH_CLAUDE_SOURCE_FILE" \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --no-logs-commit "${no_logs_commit:-false}" \
        --defer-commit "true" \
        --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md" >"$status_file" 2>"$out_file"
    rc=$?
    set +e
    if [ -f "$status_file" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] || continue
            emit "$line"
        done <"$status_file"
    fi
    if [ "$rc" -ne 0 ]; then
        LOG_FLUSH_STATUS=degraded
        append_best_effort_failure "step-7a" "capture-session-transcript.sh" "$rc" "$out_file"
    fi

    out_file="$IMPLEMENT_TMPDIR/pre-bump-flush-execution-issues-post-transcript.log"
    set +e
    "$PLUGIN_ROOT/skills/implement/scripts/flush-execution-issues.sh" \
        --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --run-id "$RUN_ID" \
        --step-label 7a-post-transcript \
        --source-label "execution-issues.md post-transcript refresh" \
        2>"$out_file"
    rc=$?
    set +e
    if [ "$rc" -ne 0 ]; then
        LOG_FLUSH_STATUS=degraded
        append_best_effort_failure "step-7a" "flush-execution-issues.sh" "$rc" "$out_file"
    fi

    if [ "${no_logs_commit:-false}" != "true" ]; then
        out_file="$IMPLEMENT_TMPDIR/pre-bump-larch-log-commit.log"
        set +e
        "$PLUGIN_ROOT/scripts/larch-log.sh" commit \
            --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
            --skill implement \
            --run-id "$RUN_ID" >"$out_file" 2>&1
        rc=$?
        set +e
        if [ "$rc" -ne 0 ]; then
            LOG_FLUSH_STATUS=degraded
            append_best_effort_failure "step-7a" "larch-log.sh commit" "$rc" "$out_file"
        fi
    elif [ "$LOG_FLUSH_STATUS" = "ok" ]; then
        LOG_FLUSH_STATUS=skipped-no-logs-commit
    fi
}

IMPLEMENT_TMPDIR=""
ISSUE_NUMBER=""
ISSUE_NUMBER_SET=false
RUN_ID=""
RUN_ID_SET=false
no_logs_commit=""
NO_LOGS_COMMIT_SET=false
forked_target=""
FORKED_TARGET_SET=false

DIAGRAM_STATUS=""
DIAGRAM_PATH=""
COMMENT_URL=""
LOG_FLUSH_STATUS=""
STEP_7A_BAIL_REASON=""

while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir)
            [ $# -ge 2 ] || fail_usage
            IMPLEMENT_TMPDIR=$2
            shift 2
            ;;
        --issue-number)
            [ $# -ge 2 ] || fail_usage
            ISSUE_NUMBER=$2
            ISSUE_NUMBER_SET=true
            shift 2
            ;;
        --run-id)
            [ $# -ge 2 ] || fail_usage
            RUN_ID=$2
            RUN_ID_SET=true
            shift 2
            ;;
        --no-logs-commit)
            [ $# -ge 2 ] || fail_usage
            no_logs_commit=$2
            NO_LOGS_COMMIT_SET=true
            shift 2
            ;;
        --forked-target)
            [ $# -ge 2 ] || fail_usage
            forked_target=$2
            FORKED_TARGET_SET=true
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            fail_usage
            ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage
case "$IMPLEMENT_TMPDIR" in
    /*) ;;
    *) fail_usage ;;
esac
mkdir -p "$IMPLEMENT_TMPDIR" 2>/dev/null || true
export IMPLEMENT_TMPDIR

SESSION_ENV_FILE="$IMPLEMENT_TMPDIR/session-env.sh"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT=$(read_session_key LARCH_CLAUDE_PLUGIN_ROOT "$PLUGIN_ROOT")
fi
if [ -n "$CLAUDE_PLUGIN_ROOT" ]; then
    PLUGIN_ROOT=$CLAUDE_PLUGIN_ROOT
fi
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

if [ -z "${LARCH_TOKEN_SESSION_ID:-}" ]; then
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "")
fi
if [ -z "${LARCH_CLAUDE_SOURCE_FILE:-}" ]; then
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "")
fi
if [ -z "${LARCH_TIMING_LEDGER:-}" ]; then
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "")
fi
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER

if [ "$ISSUE_NUMBER_SET" != "true" ]; then
    ISSUE_NUMBER=$(read_session_key LARCH_ISSUE_NUMBER "")
fi
if [ "$RUN_ID_SET" != "true" ]; then
    RUN_ID=$(read_session_key LARCH_RUN_ID "")
fi
if [ "$NO_LOGS_COMMIT_SET" != "true" ]; then
    no_logs_commit=$(read_session_key LARCH_NO_LOGS_COMMIT false)
fi
if [ "$FORKED_TARGET_SET" != "true" ]; then
    forked_target=$(read_session_key LARCH_FORKED_TARGET false)
fi
export ISSUE_NUMBER RUN_ID

REPO=""
if [ -f "${SESSION_ENV_FILE:-/dev/null}" ]; then
    if [ "${forked_target:-false}" = "true" ]; then
        REPO=$(awk -F= '/^UPSTREAM_REPO=/{print substr($0, index($0,"=")+1); exit}' "$SESSION_ENV_FILE" 2>/dev/null || true)
    fi
    if [ -z "$REPO" ]; then
        REPO=$(awk -F= '/^REPO=/{print substr($0, index($0,"=")+1); exit}' "$SESSION_ENV_FILE" 2>/dev/null || true)
    fi
    if [ -z "$REPO" ]; then
        REPO=$(awk -F= '/^UPSTREAM_REPO=/{print substr($0, index($0,"=")+1); exit}' "$SESSION_ENV_FILE" 2>/dev/null || true)
    fi
fi
export REPO

base_remote=origin
base_ref=main
if [ "${forked_target:-false}" = "true" ]; then
    base_remote=upstream
fi

"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 7a — code flow diagram" || true
"$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7a — code flow diagram" || true

if is_small_non_runtime_change; then
    DIAGRAM_STATUS=skip
    DIAGRAM_PATH=""
    emit "⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=0s"
else
    gen_out="$IMPLEMENT_TMPDIR/code-flow-diagram.stdout"
    gen_err="$IMPLEMENT_TMPDIR/code-flow-diagram.stderr"
    set +e
    "$PLUGIN_ROOT/skills/implement/scripts/generate-code-flow-diagram.sh" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" \
        --base-remote "$base_remote" \
        --base-ref "$base_ref" >"$gen_out" 2>"$gen_err"
    gen_rc=$?
    set +e
    gen_status=$(kv_value STATUS "$gen_out")
    case "$gen_status" in
        ok)
            DIAGRAM_STATUS=ok
            DIAGRAM_PATH="$IMPLEMENT_TMPDIR/code-flow-diagram.md"
            ;;
        skipped)
            DIAGRAM_STATUS=skipped
            DIAGRAM_PATH=""
            ;;
        failed)
            DIAGRAM_STATUS=failed
            DIAGRAM_PATH=""
            append_failure "Warnings" "step-7a" "generate-code-flow-diagram.sh" "$gen_rc" "$gen_err"
            ;;
        *)
            DIAGRAM_STATUS=failed
            DIAGRAM_PATH=""
            append_failure "Warnings" "step-7a" "generate-code-flow-diagram.sh" "$gen_rc" "$gen_err"
            ;;
    esac
fi

compose_summary_diagrams

if [ -n "$ISSUE_NUMBER" ] && [ -s "$IMPLEMENT_TMPDIR/code-flow-section.md" ]; then
    upsert_out="$IMPLEMENT_TMPDIR/code-flow-section-upsert.stdout"
    upsert_err="$IMPLEMENT_TMPDIR/code-flow-section-upsert.stderr"
    upsert_args=(--issue "$ISSUE_NUMBER")
    if [ -n "$REPO" ]; then
        upsert_args+=(--repo "$REPO")
    fi
    upsert_args+=(--code-flow-file "$IMPLEMENT_TMPDIR/code-flow-section.md")
    set +e
    "$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh" "${upsert_args[@]}" >"$upsert_out" 2>"$upsert_err"
    upsert_rc=$?
    set +e
    upsert_status=$(kv_value UPSERT_STATUS "$upsert_out")
    if [ "$upsert_rc" -eq 0 ] && [ "$upsert_status" != "failed" ]; then
        COMMENT_URL=$(kv_value COMMENT_URL "$upsert_out")
    else
        COMMENT_URL=""
        append_best_effort_failure "step-7a" "larch:diagrams upsert" "$upsert_rc" "$upsert_err"
    fi
fi

BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref")
export LARCH_QUIET_BREADCRUMBS=1
set +e
rebase_out="$IMPLEMENT_TMPDIR/rebase-checkpoint-probe.stdout"
"$PLUGIN_ROOT/scripts/rebase-checkpoint-probe.sh" 7a.r 'diagrams' "${BASE_ARGS[@]+"${BASE_ARGS[@]}"}" >"$rebase_out"
rebase_rc=$?
while IFS= read -r line; do
    [ -n "$line" ] || continue
    emit "$line"
done <"$rebase_out"
if [ "$rebase_rc" -ne 0 ]; then
    LOG_FLUSH_STATUS=skipped-rebase-checkpoint
    emit_tail
    exit "$rebase_rc"
fi

run_log_flush
emit_tail
exit 0
