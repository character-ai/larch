#!/usr/bin/env bash
# design-pause-load.sh — restore a /design tmpdir from an issue pause marker.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-larch-log.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-larch-log.sh"

DESIGN_TMPDIR=""
ISSUE=""
REPO=""

usage() {
    larch_err "Usage: design-pause-load.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]"
}

emit_load_fail() {
    emit_kv LOAD_OK false
    emit_kv ERROR "$1"
    exit 0
}

kv_get() {
    local key="$1" file="$2"
    awk -F= -v k="$key" '$1 == k { sub(/^[^=]*=/, ""); print; exit }' "$file"
}

validate_plain_value() {
    local label="$1" value="$2"
    case "$value" in
        ""|--*|*../*|*/*|*\\*|*$'\n'*|*$'\r'*)
            emit_load_fail "invalid-$label"
            ;;
    esac
}

validate_repo_value() {
    local value="$1"
    case "$value" in
        ""|--*|*../*|*\\*|*$'\n'*|*$'\r'*|/*)
            emit_load_fail "invalid-repo"
            ;;
    esac
    [[ "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || emit_load_fail "invalid-repo"
}

resolve_repo() {
    local repo="${1:-}"
    if [[ -n "$repo" ]]; then
        printf '%s\n' "$repo"
        return 0
    fi
    "$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null
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

[[ -n "$DESIGN_TMPDIR" ]] || emit_load_fail "tmpdir-unset"
mkdir -p "$DESIGN_TMPDIR" || emit_load_fail "tmpdir-create-failed"
[[ "$ISSUE" =~ ^[1-9][0-9]*$ ]] || emit_load_fail "invalid-issue"
command -v jq >/dev/null 2>&1 || emit_load_fail "jq-missing"

gh_repo_args=()
[[ -n "$REPO" ]] && gh_repo_args+=(--repo "$REPO")
CURRENT_REPO=""
if resolved_repo=$(resolve_repo "$REPO"); then
    CURRENT_REPO="$resolved_repo"
fi

body_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-load-body.XXXXXX")
payload_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-load-payload.XXXXXX")
stripped_tmp=$(mktemp "${TMPDIR:-/tmp}/design-pause-load-stripped.XXXXXX")
delete_out=$(mktemp "${TMPDIR:-/tmp}/design-pause-load-delete-out.XXXXXX")
delete_err=$(mktemp "${TMPDIR:-/tmp}/design-pause-load-delete-err.XXXXXX")
restore_tmp=$(mktemp -d "${TMPDIR:-/tmp}/design-pause-load-restore.XXXXXX")
trap 'rm -f "$body_tmp" "$payload_tmp" "$stripped_tmp" "$delete_out" "$delete_err"; rm -rf "$restore_tmp"' EXIT

if ! gh issue view "$ISSUE" "${gh_repo_args[@]}" --json body | jq -r '.body // ""' > "$body_tmp"; then
    emit_load_fail "issue-body-read-failed"
fi

awk '
  $0 ~ /^[[:space:]]*<!--[[:space:]]+larch:design-pause:start[[:space:]]+-->[[:space:]]*$/ { if (seen_start) bad=1; in_block=1; seen_start=1; next }
  $0 ~ /^[[:space:]]*<!--[[:space:]]+larch:design-pause:end[[:space:]]+-->[[:space:]]*$/ { if (!in_block) bad=1; in_block=0; seen_end=1; next }
  in_block { print > payload }
  !in_block { print > stripped }
  END {
    if (!seen_start && !seen_end) exit 2
    if (!seen_start || !seen_end || in_block || bad) exit 3
  }
' payload="$payload_tmp" stripped="$stripped_tmp" "$body_tmp" || parse_rc=$?
case "${parse_rc:-0}" in
    0) ;;
    2) emit_load_fail "no-pause-marker" ;;
    *) emit_load_fail "malformed-pause-marker" ;;
esac

RUN_ID=$(kv_get RUN_ID "$payload_tmp")
STEP=$(kv_get STEP "$payload_tmp")
SESSION_ID=$(kv_get SESSION_ID "$payload_tmp")
TIER=$(kv_get TIER "$payload_tmp")
BRAINSTORM_DONE=$(kv_get BRAINSTORM_DONE "$payload_tmp")
BODY_HASH=$(kv_get BODY_HASH "$payload_tmp")
LOG_RECOVERY_BRANCH=$(kv_get LOG_RECOVERY_BRANCH "$payload_tmp")
MARKER_ISSUE=$(kv_get ISSUE_NUMBER "$payload_tmp")
MARKER_REPO=$(kv_get REPO "$payload_tmp")

validate_plain_value issue-number "$MARKER_ISSUE"
if [[ "$MARKER_ISSUE" != "$ISSUE" ]]; then
    emit_load_fail "issue-mismatch"
fi

if [[ -n "$MARKER_REPO" ]]; then
    validate_repo_value "$MARKER_REPO"
    [[ -n "$CURRENT_REPO" ]] || emit_load_fail "repo-unresolved"
    if [[ "$MARKER_REPO" != "$CURRENT_REPO" ]]; then
        emit_load_fail "repo-mismatch"
    fi
fi

validate_plain_value run-id "$RUN_ID"
if ! larch_log_slug_is_valid "$RUN_ID"; then
    emit_load_fail "invalid-run-id"
fi

validate_plain_value step "$STEP"
STEP_REGISTRY="$REPO_ROOT/skills/design/scripts/step-name-registry.tsv"
if ! awk -F '\t' -v step="$STEP" '$1 == step { found=1 } END { exit(found ? 0 : 1) }' "$STEP_REGISTRY"; then
    emit_load_fail "invalid-step"
fi

if [[ -n "$LOG_RECOVERY_BRANCH" ]]; then
    validate_plain_value recovery-branch "$LOG_RECOVERY_BRANCH"
    expected_recovery_branch="larch-log-design-$RUN_ID"
    [[ "$LOG_RECOVERY_BRANCH" == "$expected_recovery_branch" ]] || emit_load_fail "invalid-recovery-branch"
    if ! git check-ref-format --branch "$LOG_RECOVERY_BRANCH" >/dev/null 2>&1; then
        emit_load_fail "invalid-recovery-branch"
    fi
fi

WARN_VALUE=""
if [[ -n "$BODY_HASH" ]]; then
    if command -v shasum >/dev/null 2>&1; then
        actual_hash=$(shasum -a 256 "$stripped_tmp" | awk '{print $1}')
    else
        actual_hash=$(sha256sum "$stripped_tmp" | awk '{print $1}')
    fi
    if [[ "$actual_hash" != "$BODY_HASH" ]]; then
        WARN_VALUE="body-drift"
    fi
fi

REPO_TOP=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_TOP=""
[[ -n "$REPO_TOP" ]] || emit_load_fail "not-git-worktree"

archive_ref=""
if [[ -n "$LOG_RECOVERY_BRANCH" ]]; then
    if ! git -C "$REPO_TOP" fetch origin "$LOG_RECOVERY_BRANCH" >/dev/null 2>&1; then
        emit_load_fail "snapshot-not-found"
    fi
    archive_ref="FETCH_HEAD"
else
    ORIGIN_DEFAULT=$(
        git -C "$REPO_TOP" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
            | sed 's#^refs/remotes/origin/##'
    ) || ORIGIN_DEFAULT=""
    [[ -n "$ORIGIN_DEFAULT" ]] || ORIGIN_DEFAULT="main"
    if ! git -C "$REPO_TOP" fetch origin "$ORIGIN_DEFAULT" >/dev/null 2>&1; then
        emit_load_fail "snapshot-not-found"
    fi
    archive_ref="origin/$ORIGIN_DEFAULT"
fi

if ! git -C "$REPO_TOP" archive "$archive_ref" "larch-logs/design/$RUN_ID/" | tar -x --strip-components=3 -C "$restore_tmp"; then
    emit_load_fail "snapshot-extract-failed"
fi

for required in manifest.json plan.txt run-params.json pause-state.txt; do
    [[ -f "$restore_tmp/$required" ]] || emit_load_fail "missing-restored-artifact"
done

RESTORED_ISSUE=$(kv_get ISSUE_NUMBER "$restore_tmp/pause-state.txt")
validate_plain_value restored-issue-number "$RESTORED_ISSUE"
if [[ "$RESTORED_ISSUE" != "$ISSUE" ]]; then
    emit_load_fail "restored-issue-mismatch"
fi

RESTORED_RUN_ID=$(kv_get RUN_ID "$restore_tmp/pause-state.txt")
validate_plain_value restored-run-id "$RESTORED_RUN_ID"
if [[ "$RESTORED_RUN_ID" != "$RUN_ID" ]]; then
    emit_load_fail "restored-run-id-mismatch"
fi

RESTORED_REPO=$(kv_get REPO "$restore_tmp/pause-state.txt")
if [[ -n "$RESTORED_REPO" ]]; then
    validate_repo_value "$RESTORED_REPO"
    if [[ -n "$CURRENT_REPO" && "$RESTORED_REPO" != "$CURRENT_REPO" ]]; then
        emit_load_fail "restored-repo-mismatch"
    fi
fi

manifest_issue=$(jq -r '.issue_number // empty' "$restore_tmp/manifest.json" 2>/dev/null) || emit_load_fail "invalid-restored-manifest"
if [[ -z "$manifest_issue" || "$manifest_issue" != "$ISSUE" ]]; then
    emit_load_fail "restored-issue-mismatch"
fi

manifest_run_id=$(jq -r '.run_id // empty' "$restore_tmp/manifest.json" 2>/dev/null) || emit_load_fail "invalid-restored-manifest"
if [[ -z "$manifest_run_id" || "$manifest_run_id" != "$RUN_ID" ]]; then
    emit_load_fail "restored-run-id-mismatch"
fi

delete_args=(
    "$SCRIPT_DIR/named-block-write.sh"
    --marker design-pause
    --delete
    --issue "$ISSUE"
)
[[ -n "$REPO" ]] && delete_args+=(--repo "$REPO")
if ! "${delete_args[@]}" > "$delete_out" 2> "$delete_err"; then
    emit_load_fail "marker-delete-failed"
fi

if ! cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/; then
    emit_load_fail "restore-install-failed"
fi

emit_kv LOAD_OK true
emit_kv STEP "$STEP"
emit_kv SESSION_ID "${SESSION_ID:-$RUN_ID}"
emit_kv RUN_ID "$RUN_ID"
emit_kv TIER "${TIER:-unknown}"
emit_kv BRAINSTORM_DONE "${BRAINSTORM_DONE:-false}"
[[ -n "$CURRENT_REPO" ]] && emit_kv REPO "$CURRENT_REPO"
[[ -n "$WARN_VALUE" ]] && emit_kv WARN "$WARN_VALUE"
exit 0
