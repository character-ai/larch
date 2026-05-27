#!/usr/bin/env bash
# design-pause-save.sh — publish a /design snapshot and write the resume marker.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

DESIGN_TMPDIR=""
ISSUE=""
REPO=""

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
    emit_kv PAUSE_OK false
    emit_kv ERROR "$1"
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

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" ]] || emit_fail "tmpdir-unset"
[[ -d "$DESIGN_TMPDIR" ]] || emit_fail "tmpdir-missing"
[[ "$ISSUE" =~ ^[1-9][0-9]*$ ]] || emit_fail "invalid-issue"

if [[ -f "$DESIGN_TMPDIR/source-env.sh" ]]; then
    # shellcheck disable=SC1090
    # shellcheck disable=SC1091
    source "$DESIGN_TMPDIR/source-env.sh" || true
fi

RUN_ID="${SESSION_ID:-}"
[[ -n "$RUN_ID" ]] || emit_fail "run-id-unset"

STEP_REGISTRY="$REPO_ROOT/skills/design/scripts/step-name-registry.tsv"
[[ -f "$STEP_REGISTRY" ]] || emit_fail "missing-step-registry"

STEP=""
while IFS=$'\t' read -r step_id _step_name || [[ -n "$step_id" ]]; do
    [[ -z "$step_id" || "$step_id" == "step" || "$step_id" == "0" || "$step_id" == "5" ]] && continue
    if [[ ! -f "$DESIGN_TMPDIR/.completed/step-$step_id" ]]; then
        STEP="$step_id"
        break
    fi
done < "$STEP_REGISTRY"
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

if [[ "$publish_rc" -ne 0 && -z "$PUBLISH_OK" ]]; then
    log_failure "design-log-publish.sh" "$publish_err"
    emit_fail "publish-failed"
fi

if [[ "$PUBLISH_OK" != "true" ]]; then
    log_failure "design-log-publish.sh" "$publish_err"
    if [[ -n "$RECOVERY_BRANCH" ]]; then
        printf 'LOG_RECOVERY_BRANCH=%s\n' "$RECOVERY_BRANCH" >> "$state_tmp"
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

emit_kv PAUSE_OK true
emit_kv STEP "$STEP"
emit_kv RUN_ID "$RUN_ID"
exit 0
