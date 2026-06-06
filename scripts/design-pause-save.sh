#!/usr/bin/env bash
# design-pause-save.sh — publish a /design snapshot and write the resume marker.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/lib-design-tmpdir.sh"
# shellcheck source=scripts/lib-larch-log.sh
source "$SCRIPT_DIR/lib-larch-log.sh"

DESIGN_TMPDIR=""
ISSUE=""
REPO=""

validate_repo() {
    local value="$1"
    case "$value" in
        '' | --* | *$'\n'* | *$'\r'* | /* | *../* | *\\*) return 1 ;;
    esac
    [[ "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]
}

source_env_get() {
    local key="$1" file="$2"
    awk -v k="$key" '
      BEGIN { q=sprintf("%c", 39) }
      $1 == "export" {
        v=$0
        sub(/^[[:space:]]*export[[:space:]]+/, "", v)
        if (index(v, k "=") != 1) next
        sub("^[^=]*=", "", v)
        if ((substr(v, 1, 1) == q && substr(v, length(v), 1) == q) ||
            (substr(v, 1, 1) == "\"" && substr(v, length(v), 1) == "\"")) {
          v=substr(v, 2, length(v)-2)
        }
        print v
        exit
      }
    ' "$file"
}

resolve_repo() {
    local repo="${1:-}"
    if [[ -n "$repo" ]]; then
        printf '%s\n' "$repo"
        return 0
    fi
    "$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null
}

usage() {
    larch_err "Usage: design-pause-save.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]"
}

emit_fail() {
    local reason="${1:-}"
    if [[ "$reason" != invalid-repo ]] \
        && [[ -n "${DESIGN_TMPDIR:-}" && -d "$DESIGN_TMPDIR" ]] \
        && larch_design_tmpdir_validate "$DESIGN_TMPDIR" >/dev/null 2>&1; then
        rm -f "$DESIGN_TMPDIR/.pause-requested" 2>/dev/null || true
    fi
    emit_kv PAUSE_OK false
    emit_kv ERROR "$reason"
    if [[ "${LARCH_PAUSE_REQUIRE_SUCCESS:-0}" == "1" ]]; then
        exit 1
    fi
    exit 0
}

log_failure() {
    local reason="$1" output_file="$2"
    if [[ -n "$DESIGN_TMPDIR" && -d "$DESIGN_TMPDIR" && -f "$output_file" ]]; then
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design pause save" \
            --tool "$reason" \
            --exit-code 1 \
            --category "Tool Failures" \
            --output-file "$output_file" \
            --redact >/dev/null 2>&1 || true
    fi
}

render_fresh_timing_report_for_pause_publish() {
    local tmp_dir tmp_json tmp_stderr render_rc=0 existing
    for existing in "$DESIGN_TMPDIR"/timing-report-final.*; do
        [[ -e "$existing" ]] || continue
        rm -f "$existing" 2>/dev/null || true
    done
    tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/larch-design-pause-timing.XXXXXX") || {
        : >"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        printf '%s\n' "mktemp failed while preparing timing-report-final.json" >"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        log_failure "timing-report.sh" "$DESIGN_TMPDIR/timing-report-final.failure.log"
        rm -f "$DESIGN_TMPDIR"/timing-report-final.* 2>/dev/null || true
        return 0
    }
    tmp_json="$tmp_dir/timing-report-final.json"
    tmp_stderr="$tmp_dir/timing-report-final.stderr.log"
    if ! command -v jq >/dev/null 2>&1; then
        printf '%s\n' "jq is required to validate timing-report-final.json before pause publish" >"$tmp_stderr" 2>/dev/null || true
        log_failure "jq" "$tmp_stderr"
        rm -rf "$tmp_dir"
        rm -f "$DESIGN_TMPDIR"/timing-report-final.* 2>/dev/null || true
        return 0
    fi
    set +e
    env -u IMPLEMENT_TMPDIR \
        LARCH_TIMING_SKILL=design DESIGN_TMPDIR="$DESIGN_TMPDIR" LARCH_TIMING_LEDGER="$DESIGN_TMPDIR/timing-ledger.tsv" \
        "$SCRIPT_DIR/timing-report.sh" --full --format json --output "$tmp_json" > /dev/null 2>"$tmp_stderr"
    render_rc=$?
    set -e
    if [[ "$render_rc" -eq 0 && -s "$tmp_json" ]] && jq -e . "$tmp_json" >/dev/null 2>>"$tmp_stderr"; then
        mv -f "$tmp_json" "$DESIGN_TMPDIR/timing-report-final.json"
        rm -rf "$tmp_dir"
        return 0
    fi
    rm -f "$DESIGN_TMPDIR"/timing-report-final.* 2>/dev/null || true
    log_failure "timing-report.sh" "$tmp_stderr"
    rm -rf "$tmp_dir"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done

REPO_ARG="${REPO:-}"
if [[ -n "$REPO_ARG" ]] && ! validate_repo "$REPO_ARG"; then
    emit_fail "invalid-repo"
fi

[[ -n "$DESIGN_TMPDIR" ]] || emit_fail "tmpdir-unset"
[[ -d "$DESIGN_TMPDIR" ]] || emit_fail "tmpdir-missing"
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || emit_fail "tmpdir-invalid"
[[ "$ISSUE" =~ ^[1-9][0-9]*$ ]] || emit_fail "invalid-issue"

if [[ -f "$DESIGN_TMPDIR/source-env.sh" ]]; then
    _source_session_id=$(source_env_get SESSION_ID "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
    [[ -n "${SESSION_ID:-}" || -z "$_source_session_id" ]] || SESSION_ID="$_source_session_id"
    if [[ -z "$REPO_ARG" ]]; then
        _source_repo=$(source_env_get REPO "$DESIGN_TMPDIR/source-env.sh" 2>/dev/null || true)
        if [[ -n "$_source_repo" ]]; then
            validate_repo "$_source_repo" || emit_fail "invalid-repo"
            REPO="$_source_repo"
        fi
    fi
fi
if [[ -n "$REPO_ARG" ]]; then
    REPO="$REPO_ARG"
fi

RUN_ID="${SESSION_ID:-}"
[[ -n "$RUN_ID" ]] || emit_fail "run-id-unset"
case "$RUN_ID" in *$'\n'*|*$'\r'*) emit_fail "invalid-run-id" ;; esac
larch_log_slug_is_valid "$RUN_ID" || emit_fail "invalid-run-id"

STEP_REGISTRY="$REPO_ROOT/skills/design/scripts/step-name-registry.tsv"
[[ -f "$STEP_REGISTRY" ]] || emit_fail "missing-step-registry"

STEP=""
if [[ -f "$DESIGN_TMPDIR/.step3-reentry" ]]; then
    STEP="3"
elif [[ -f "$DESIGN_TMPDIR/.completed/step-3" && -f "$DESIGN_TMPDIR/.completed/step-3.5" && -f "$DESIGN_TMPDIR/.completed/step-3.6" && ! -f "$DESIGN_TMPDIR/.completed/step-3b" ]]; then
    STEP="3b"
elif [[ -f "$DESIGN_TMPDIR/.completed/step-3" && -f "$DESIGN_TMPDIR/.completed/step-3.5" && ! -f "$DESIGN_TMPDIR/.completed/step-3.6" ]]; then
    STEP="3.6"
elif [[ -f "$DESIGN_TMPDIR/.completed/step-3" && ! -f "$DESIGN_TMPDIR/.completed/step-3.5" ]]; then
    STEP="3.5"
elif [[ -f "$DESIGN_TMPDIR/.completed/step-5b" && ! -f "$DESIGN_TMPDIR/.completed/step-5c" ]]; then
    STEP="5c"
else
    while IFS=$'\t' read -r step_id _step_name || [[ -n "$step_id" ]]; do
        [[ -z "$step_id" || "$step_id" == "step" || "$step_id" == "0" || "$step_id" == "5" ]] && continue
        if [[ ! -f "$DESIGN_TMPDIR/.completed/step-$step_id" ]]; then
            STEP="$step_id"
            break
        fi
    done < "$STEP_REGISTRY"
fi
[[ -n "$STEP" ]] || STEP="6"

TIER="unknown"
if [[ -f "$DESIGN_TMPDIR/run-params.json" ]] && command -v jq >/dev/null 2>&1; then
    TIER=$(jq -r '.design_classification // "unknown"' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || printf 'unknown')
fi
BRAINSTORM_DONE=false
[[ -f "$DESIGN_TMPDIR/.brainstorm-done" ]] && BRAINSTORM_DONE=true

if resolved_repo=$(resolve_repo "$REPO"); then
    REPO="$resolved_repo"
fi
if [[ -n "$REPO" ]] && ! validate_repo "$REPO"; then
    emit_fail "invalid-repo"
fi

gh_repo_args=()
[[ -n "$REPO" ]] && gh_repo_args+=(--repo "$REPO")

body_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-body.XXXXXX")
stripped_body_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-body-stripped.XXXXXX")
state_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-state.XXXXXX")
redacted_state_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-state-redacted.XXXXXX")
publish_out=$(mktemp "${TMPDIR:-/tmp}/design-pause-publish-out.XXXXXX")
publish_err=$(mktemp "${TMPDIR:-/tmp}/design-pause-publish-err.XXXXXX")
marker_out=$(mktemp "${TMPDIR:-/tmp}/design-pause-marker-out.XXXXXX")
marker_err=$(mktemp "${TMPDIR:-/tmp}/design-pause-marker-err.XXXXXX")
trap 'rm -f "$body_tmp" "$stripped_body_tmp" "$state_tmp" "$redacted_state_tmp" "$publish_out" "$publish_err" "$marker_out" "$marker_err"' EXIT

if ! gh issue view "$ISSUE" "${gh_repo_args[@]}" --json body | jq -r '.body // ""' > "$body_tmp"; then
    log_failure "gh issue view" "$body_tmp"
    emit_fail "issue-body-read-failed"
fi

awk '
  $0 ~ /^[[:space:]]*<!--[[:space:]]+larch:design-pause:start[[:space:]]+-->[[:space:]]*$/ { in_block=1; next }
  $0 ~ /^[[:space:]]*<!--[[:space:]]+larch:design-pause:end[[:space:]]+-->[[:space:]]*$/ { in_block=0; next }
  !in_block { print }
' "$body_tmp" > "$stripped_body_tmp"
if command -v shasum >/dev/null 2>&1; then
    BODY_HASH=$(shasum -a 256 "$stripped_body_tmp" | awk '{print $1}')
else
    BODY_HASH=$(sha256sum "$stripped_body_tmp" | awk '{print $1}')
fi

{
    printf 'STEP=%s\n' "$STEP"
    printf 'ISSUE_NUMBER=%s\n' "$ISSUE"
    printf 'SESSION_ID=%s\n' "$RUN_ID"
    printf 'RUN_ID=%s\n' "$RUN_ID"
    [[ -n "$REPO" ]] && printf 'REPO=%s\n' "$REPO"
    printf 'TIER=%s\n' "$TIER"
    printf 'BRAINSTORM_DONE=%s\n' "$BRAINSTORM_DONE"
    printf 'BODY_HASH=%s\n' "$BODY_HASH"
    printf 'PAUSED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$state_tmp"

if ! "$SCRIPT_DIR/redact-secrets.sh" < "$state_tmp" > "$redacted_state_tmp"; then
    log_failure "redact-secrets.sh" "$state_tmp"
    emit_fail "pause-state-redaction-failed"
fi
cp "$redacted_state_tmp" "$DESIGN_TMPDIR/pause-state.txt"

publish_cmd="${LARCH_DESIGN_LOG_PUBLISH:-$SCRIPT_DIR/design-log-publish.sh}"
render_fresh_timing_report_for_pause_publish
publish_args=(
    "$publish_cmd"
    --reason pause
    --design-tmpdir "$DESIGN_TMPDIR"
    --run-id "$RUN_ID"
    --issue "$ISSUE"
)
[[ -n "$REPO" ]] && publish_args+=(--repo "$REPO")

set +e
"${publish_args[@]}" > "$publish_out" 2> "$publish_err"
publish_rc=$?
set -e

PUBLISH_OK=$(awk -F= '$1=="PUBLISH_OK"{print $2}' "$publish_out" | tail -1)
RECOVERY_BRANCH=$(awk -F= '$1=="RECOVERY_BRANCH"{print $2}' "$publish_out" | tail -1)
publish_failure_logged=false

if [[ "$publish_rc" -ne 0 && -z "$PUBLISH_OK" ]]; then
    log_failure "design-log-publish.sh" "$publish_err"
    emit_fail "publish-failed"
fi
if [[ "$publish_rc" -ne 0 && "$PUBLISH_OK" == "true" ]]; then
    log_failure "design-log-publish.sh" "$publish_err"
    publish_failure_logged=true
    PUBLISH_OK=false
fi

if [[ "$PUBLISH_OK" != "true" ]]; then
    [[ "$publish_failure_logged" == true ]] || log_failure "design-log-publish.sh" "$publish_err"
    if [[ -n "$RECOVERY_BRANCH" ]]; then
        if [[ "$RECOVERY_BRANCH" == "larch-log-design-$RUN_ID" || "$RECOVERY_BRANCH" == "larch-log-design-recovery-$RUN_ID" ]]; then
            printf 'LOG_RECOVERY_BRANCH=%s\n' "$RECOVERY_BRANCH" >> "$state_tmp"
        else
            emit_kv LOG_RECOVERY_BRANCH "$RECOVERY_BRANCH"
            emit_fail "publish-local-recovery-only"
        fi
    else
        emit_fail "publish-and-recovery-failed"
    fi
fi

if ! "$SCRIPT_DIR/redact-secrets.sh" < "$state_tmp" > "$redacted_state_tmp"; then
    log_failure "redact-secrets.sh" "$state_tmp"
    emit_fail "pause-state-redaction-failed"
fi
cp "$redacted_state_tmp" "$DESIGN_TMPDIR/pause-state.txt"

marker_args=(
    "$SCRIPT_DIR/named-block-write.sh"
    --marker design-pause
    --content-file "$redacted_state_tmp"
    --issue "$ISSUE"
)
[[ -n "$REPO" ]] && marker_args+=(--repo "$REPO")

set +e
"${marker_args[@]}" > "$marker_out" 2> "$marker_err"
marker_rc=$?
set -e
if [[ "$marker_rc" -ne 0 ]]; then
    log_failure "named-block-write.sh" "$marker_err"
    emit_fail "marker-write-failed"
fi

rm -f "$DESIGN_TMPDIR/.pause-requested"

if [[ -n "$RECOVERY_BRANCH" ]]; then
    emit_kv WARN recovery-branch-only
    emit_kv LOG_RECOVERY_BRANCH "$RECOVERY_BRANCH"
fi
emit_kv PAUSE_OK true
emit_kv STEP "$STEP"
emit_kv RUN_ID "$RUN_ID"
exit 0
