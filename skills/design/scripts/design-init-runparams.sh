#!/usr/bin/env bash
# design-init-runparams.sh — /design Step 0b post-gate phase driver (tier, env, rename, run-params).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
larch_quiet_init

fail() {
    larch_err "design-init-runparams.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: design-init-runparams.sh --design-tmpdir PATH --issue N --session-id STR --claude-pid N --classification SIMPLE|HARD --partition-requested true|false --brainstorm-requested true|false --manual-requested true|false [--repo OWNER/REPO]'
}

validate_plain_scalar() {
    local label="$1" value="$2"
    case "$value" in
        '' | *$'\n'* | *$'\r'*) fail "invalid $label" ;;
    esac
}

validate_repo() {
    local value="$1"
    case "$value" in
        '' | *$'\n'* | *$'\r'* | /* | *../*) fail 'invalid --repo' ;;
    esac
    [[ "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || fail 'invalid --repo'
}

validate_bool_flag() {
    local label="$1" value="$2"
    case "$value" in
        true | false) ;;
        *) fail "$label must be true or false" ;;
    esac
}

DESIGN_TMPDIR_ARG=""
ISSUE=""
SESSION_ID=""
CLAUDE_PID=""
CLASSIFICATION=""
PARTITION_REQUESTED=""
BRAINSTORM_REQUESTED=""
MANUAL_REQUESTED=""
REPO=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
            shift 2
            ;;
        --issue)
            [[ $# -ge 2 ]] || fail '--issue requires a value'
            ISSUE="$2"
            shift 2
            ;;
        --session-id)
            [[ $# -ge 2 ]] || fail '--session-id requires a value'
            SESSION_ID="$2"
            shift 2
            ;;
        --claude-pid)
            [[ $# -ge 2 ]] || fail '--claude-pid requires a value'
            CLAUDE_PID="$2"
            shift 2
            ;;
        --classification)
            [[ $# -ge 2 ]] || fail '--classification requires a value'
            CLASSIFICATION="$2"
            shift 2
            ;;
        --partition-requested)
            [[ $# -ge 2 ]] || fail '--partition-requested requires a value'
            PARTITION_REQUESTED="$2"
            shift 2
            ;;
        --brainstorm-requested)
            [[ $# -ge 2 ]] || fail '--brainstorm-requested requires a value'
            BRAINSTORM_REQUESTED="$2"
            shift 2
            ;;
        --manual-requested)
            [[ $# -ge 2 ]] || fail '--manual-requested requires a value'
            MANUAL_REQUESTED="$2"
            shift 2
            ;;
        --repo)
            [[ $# -ge 2 ]] || fail '--repo requires a value'
            REPO="$2"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$DESIGN_TMPDIR_ARG" ]] || { usage; fail '--design-tmpdir is required'; }
[[ -n "$ISSUE" ]] || { usage; fail '--issue is required'; }
[[ -n "$SESSION_ID" ]] || { usage; fail '--session-id is required'; }
[[ -n "$CLAUDE_PID" ]] || { usage; fail '--claude-pid is required'; }
[[ -n "$CLASSIFICATION" ]] || { usage; fail '--classification is required'; }

case "$ISSUE" in
    '' | *[!0-9]*) fail '--issue must be a positive integer' ;;
esac
[[ "$ISSUE" != "0" ]] || fail '--issue must be a positive integer'
case "$CLAUDE_PID" in
    '' | *[!0-9]*) fail '--claude-pid must be a positive integer' ;;
esac
case "$CLASSIFICATION" in
    SIMPLE | HARD) ;;
    *) fail '--classification must be SIMPLE or HARD' ;;
esac
validate_bool_flag --partition-requested "$PARTITION_REQUESTED"
validate_bool_flag --brainstorm-requested "$BRAINSTORM_REQUESTED"
validate_bool_flag --manual-requested "$MANUAL_REQUESTED"
validate_plain_scalar session-id "$SESSION_ID"
[[ -n "$REPO" ]] && validate_repo "$REPO"

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR
SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

RESULT_ENV="$DESIGN_TMPDIR/.design-init-runparams-result.env"
RUN_PARAMS_PATH="$DESIGN_TMPDIR/run-params.json"
INIT_STATUS=ok
RENAMED=false
DESIGN_CLASSIFICATION="$CLASSIFICATION"
WARN_LINES=()

add_warn() {
    WARN_LINES+=("$1")
}

if [[ "$CLASSIFICATION" == SIMPLE ]]; then
    design_classification_reason='default tier: SIMPLE (no --hard)'
    sketch_budget=0
    review_budget=full
    workflow_path=SIMPLE
else
    design_classification_reason='argv tier: --hard'
    sketch_budget=4
    review_budget=full
    workflow_path=HARD
fi
design_classification_source=caller-forwarded

# 2. Env refresh before rename
_wdce_args=(
    "$PLUGIN_ROOT/scripts/write-design-current-env.sh"
    --output "$DESIGN_TMPDIR/source-env.sh"
    --design-tmpdir "$DESIGN_TMPDIR"
    --session-id "$SESSION_ID"
    --issue-number "$ISSUE"
    --claude-pid "$CLAUDE_PID"
)
if [[ "$MANUAL_REQUESTED" == true ]]; then
    _wdce_args+=(--manual-requested true)
fi
if ! "${_wdce_args[@]}"; then
    INIT_STATUS=env-refresh-failed
    emit_kv INIT_STATUS "$INIT_STATUS"
    phase_driver_write_result_env "$RESULT_ENV" \
        "INIT_STATUS=$INIT_STATUS" \
        "RUN_PARAMS_PATH=$RUN_PARAMS_PATH" \
        "DESIGN_CLASSIFICATION=$DESIGN_CLASSIFICATION" || exit 1
    exit 1
fi

# 3. [DESIGNING] rename (best-effort; run-params write follows)
if _rename_out=$("$PLUGIN_ROOT/scripts/tracking-issue-write.sh" rename --issue "$ISSUE" --state designing ${REPO:+--repo "$REPO"}); then
    _rename_seen=false
    while IFS= read -r _rename_line || [[ -n "$_rename_line" ]]; do
        case "$_rename_line" in
            RENAMED=true) RENAMED=true; _rename_seen=true ;;
            RENAMED=false) RENAMED=false; _rename_seen=true ;;
        esac
    done <<<"${_rename_out:-}"
    if [[ "$_rename_seen" != true ]]; then
        add_warn "**⚠ 0b: tracking-issue-write.sh rename succeeded but omitted RENAMED= line; treating rename outcome as unknown.**"
    fi
else
    add_warn "**⚠ 0b: [DESIGNING] rename failed (tracking-issue-write.sh); continuing with run-params write. Re-invoke /design or rename manually if the title is still wrong.**"
fi

# 4. write-run-params.sh
if ! "$PLUGIN_ROOT/scripts/write-run-params.sh" \
    --classification "$CLASSIFICATION" \
    --reason "$design_classification_reason" \
    --source "$design_classification_source" \
    --sketch-budget "$sketch_budget" \
    --review-budget "$review_budget" \
    --workflow-path "$workflow_path" \
    --partition-requested "$PARTITION_REQUESTED" \
    --brainstorm-requested "$BRAINSTORM_REQUESTED" \
    --manual-gate-b "$MANUAL_REQUESTED" \
    --output "$RUN_PARAMS_PATH"; then
    INIT_STATUS=contract-drift
    emit_kv INIT_STATUS contract-drift
    phase_driver_write_result_env "$RESULT_ENV" \
        "INIT_STATUS=contract-drift" \
        "RUN_PARAMS_PATH=$RUN_PARAMS_PATH" \
        "DESIGN_CLASSIFICATION=$DESIGN_CLASSIFICATION" || exit 1
    exit 1
fi

# 5. Router-flag jq-merge (verbatim from SKILL.md Step 0b)
if [[ "$PARTITION_REQUESTED" == true || "$BRAINSTORM_REQUESTED" == true || "$MANUAL_REQUESTED" == true ]] && command -v jq >/dev/null 2>&1; then
    if [[ -f "$RUN_PARAMS_PATH" ]]; then
        _rp_merge=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge.XXXXXX")
        _rp_err=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge-err.XXXXXX")
        if jq -c \
            --argjson merge_p "$([[ "$PARTITION_REQUESTED" == true ]] && echo true || echo false)" \
            --argjson merge_b "$([[ "$BRAINSTORM_REQUESTED" == true ]] && echo true || echo false)" \
            --argjson merge_m "$([[ "$MANUAL_REQUESTED" == true ]] && echo true || echo false)" \
            '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' \
            "$RUN_PARAMS_PATH" >"$_rp_merge" 2>"$_rp_err"; then
            mv -f "$_rp_merge" "$RUN_PARAMS_PATH"
            rm -f "$_rp_err"
        else
            "$PLUGIN_ROOT/scripts/append-tool-failure.sh" --log "$DESIGN_TMPDIR/execution-issues.md" --site "design Step 0b" --tool "jq(router-flags-merge)" --exit-code 1 --category Warnings --output-file "$_rp_err" >/dev/null 2>&1 || true
            rm -f "$_rp_merge" "$_rp_err"
        fi
    else
        add_warn "**⚠ 0b: run-params.json missing after write-run-params.sh; refusing to recreate it with fallback defaults. Re-run \`bash scripts/test-write-run-params.sh\` and fix the Step 0b contract drift first.**"
    fi
elif [[ "$PARTITION_REQUESTED" == true || "$BRAINSTORM_REQUESTED" == true || "$MANUAL_REQUESTED" == true ]]; then
    add_warn '**⚠ 0b: partition, brainstorm, and/or manual requested but jq is unavailable — flags may not persist across subshell boundaries; install jq or re-supply flags after subshell boundaries.**'
fi

_init_kvs=(
    "INIT_STATUS=$INIT_STATUS"
    "RENAMED=$RENAMED"
    "RUN_PARAMS_PATH=$RUN_PARAMS_PATH"
    "DESIGN_CLASSIFICATION=$DESIGN_CLASSIFICATION"
)
for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
    _init_kvs+=("WARN=$_warn")
done
if ! phase_driver_write_result_env "$RESULT_ENV" "${_init_kvs[@]}"; then
    exit 1
fi
emit_kv INIT_STATUS "$INIT_STATUS"
emit_kv RENAMED "$RENAMED"
emit_kv RUN_PARAMS_PATH "$RUN_PARAMS_PATH"
emit_kv DESIGN_CLASSIFICATION "$DESIGN_CLASSIFICATION"
for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
    emit_kv WARN "$_warn"
done
exit 0
