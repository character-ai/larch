#!/usr/bin/env bash
# launch-review.sh - Unified external reviewer launcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-codex-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-codex-launcher-common.sh"
# shellcheck source=scripts/lib-cursor-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-cursor-launcher-common.sh"
# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"
# shellcheck source=scripts/lib-dirty-tree-sidecar.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-dirty-tree-sidecar.sh"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: launch-review.sh --tool codex|cursor|gemini --output FILE --timeout SECS [review flags]"
}

TOOL=""
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool)
            TOOL="${2:?--tool requires a value}"
            case "$TOOL" in
                codex|cursor|gemini) ;;
                *) larch_err "launch-review.sh: unknown tool: '$TOOL'; expected codex, cursor, or gemini"; exit 2 ;;
            esac
            shift 2
            ;;
        --help) usage; exit 0 ;;
        --output|--timeout|--prompt|--prompt-file|--agent-file|--mode|--description-text|--scope-files|--diff-file|--timing-task-kind|--token-budget-cap|--risk|--plan-file|--feature-file)
            ARGS+=("$1")
            if [[ $# -gt 1 ]]; then
                ARGS+=("$2")
                shift 2
            else
                shift
            fi
            ;;
        *) ARGS+=("$1"); shift ;;
    esac
done

if [[ -z "$TOOL" ]]; then
    larch_err "launch-review.sh: --tool is required (codex|cursor|gemini)"
    exit 2
fi

append_launch_failure() {
    local site="$1" tool_label="$2" rc="$3" diag_file="$4" verdict="${5:-}" retry_count="${6:-}"
    [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]] || return 0
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] || return 0
    local _args=()
    [[ -n "$verdict" ]] && _args+=(--verdict "$verdict")
    [[ -n "$retry_count" ]] && _args+=(--retry-count "$retry_count")
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
        --site "$site" --tool "$tool_label" --exit-code "$rc" \
        --category "External Reviewer Issues" --output-file "$diag_file" \
        "${_args[@]}" --redact >/dev/null 2>&1 || true
}

if [[ "$TOOL" == "gemini" ]]; then
    for _arg in "${ARGS[@]+"${ARGS[@]}"}"; do
        case "$_arg" in
            --agent-file|--mode|--description-text|--scope-files|--competition-notice|--diff-file|--prompt-file|--plan-file|--feature-file)
                larch_err "launch-review.sh: $_arg is not supported for --tool gemini"
                exit 2
                ;;
        esac
    done
    unset _arg
fi

_launch_codex() {
# shellcheck disable=SC2317,SC2329 # invoked indirectly by the EXIT trap.
_emit_timing_record() {
    local rc=${1:-$?}
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    [[ -n "${TIMING_START_S:-}" && -n "${OUTPUT:-}" ]] || return 0
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor codex \
        --task-kind "${TIMING_TASK_KIND:-codex-review}" \
        --start-s "$TIMING_START_S" \
        --end-s "$end_s" \
        --output "$OUTPUT" \
        --exit-code "$rc" \
        --status "$status" \
        >/dev/null 2>&1 || true
}

OUTPUT=""
TIMEOUT=""
PROMPT=""
PROMPT_FILE=""
AGENT_FILE=""
MODE=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
COMPETITION_NOTICE=false
DIFF_FILE=""
COMMIT_COUNT=""
PLAN_FILE=""
FEATURE_FILE=""
TIMING_TASK_KIND="${LARCH_TIMING_TASK_KIND:-}"
TOKEN_BUDGET_CAP=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --agent-file) AGENT_FILE="${2:?--agent-file requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --competition-notice) COMPETITION_NOTICE=true; shift ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { larch_err "launch-review.sh: --timing-task-kind requires a non-empty, non-flag-like value"; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) larch_err "launch-review.sh: --token-budget-cap requires a positive integer"; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { larch_err "launch-review.sh: --token-budget-cap requires a positive integer"; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
        --risk) [[ -n "${2:-}" ]] || { larch_err "launch-review.sh: --risk requires a value"; exit 2; }; shift 2 ;;
        *) larch_err "launch-review.sh: unknown flag: $1"; exit 2 ;;
    esac
done

if [[ -z "$OUTPUT" ]]; then
    larch_err "launch-review.sh: --output is required"; exit 2
fi
if [[ -z "$TIMEOUT" ]]; then
    larch_err "launch-review.sh: --timeout is required"; exit 2
fi

# Validate --output BEFORE installing traps/sidecars so the same byte-exact
# .meta-sidecar contract enforced for the Cursor review launcher applies on
# the Codex path too. Mirrors scripts/launch-review.sh:60-62.
# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"
validate_meta_scalar_path --output "$OUTPUT" || exit 1

case "$TIMEOUT" in
    ''|*[!0-9]*|0) larch_err "launch-review.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    larch_err "launch-review.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"
    exit 2
fi

if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
fi
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="${IMPLEMENT_TMPDIR}/claude-source.env"
fi

# Apply env-var cap when --token-budget-cap was not passed explicitly; validate
# the value (invalid values silently disable the cap rather than exit 2).
if [[ -z "$TOKEN_BUDGET_CAP" && -n "${LARCH_TOKEN_BUDGET_CAP_REVIEW:-}" ]]; then
    case "$LARCH_TOKEN_BUDGET_CAP_REVIEW" in
        ''|*[!0-9]*) ;;
        *) (( 10#${LARCH_TOKEN_BUDGET_CAP_REVIEW} >= 1 )) && TOKEN_BUDGET_CAP="$LARCH_TOKEN_BUDGET_CAP_REVIEW" ;;
    esac
fi

# Per-step token budget cap: short-circuit before spawning Codex when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-codex-review}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        larch_errf '⚠ launch-review.sh: step token budget cap of %s tokens exceeded (%s combined vendor tokens); external reviewer fan-out skipped\n' \
            "$TOKEN_BUDGET_CAP" "$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^TOTAL=/){print substr($i,7);exit}}}')"
        printf 'STATUS=cap_hit\n' > "$OUTPUT"
        printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${OUTPUT}.cap-hit"
        if [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
            printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${IMPLEMENT_TMPDIR}/step-budget-cap-hit.env"
        fi
        printf '%s\n' "0" > "${OUTPUT}.done" 2>/dev/null || true
        exit 0
    fi
    unset _budget_out _budget_status
fi

_src_count=0
[[ -n "$PROMPT" ]] && _src_count=$((_src_count + 1))
[[ -n "$AGENT_FILE" ]] && _src_count=$((_src_count + 1))
[[ -n "$PROMPT_FILE" ]] && _src_count=$((_src_count + 1))
if [[ "$_src_count" -gt 1 ]]; then
    larch_err "launch-review.sh: --prompt, --agent-file, and --prompt-file are mutually exclusive"
    exit 2
fi
if [[ "$_src_count" -eq 0 ]]; then
    larch_err "launch-review.sh: one of --prompt, --agent-file, --prompt-file is required"
    exit 2
fi

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="codex-review"
fi
: "${TIMING_TASK_KIND:=codex-review}"
TIMING_START_S=$(date +%s)

# Propagate render-specialist-prompt.sh cache dir from session context when not
# already set. All reviewer launchers in the same Bash invocation inherit this,
# enabling within-session cache sharing across parallel specialist launches.
if [[ -z "${LARCH_RENDER_CACHE_DIR:-}" ]] && [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
    export LARCH_RENDER_CACHE_DIR="$IMPLEMENT_TMPDIR/render-cache"
fi

MODEL_ARGS_TMP=""
CODEX_HOME_DIR=""
DIRTY_TREE_WRITTEN=false
UNTRACKED_BASELINE="${OUTPUT}.untracked-baseline"
DIRTY_TREE_SIDECAR="${OUTPUT}.dirty-tree"
CODEX_SANDBOX_MODE=read-only

# _write_dirty_tree_sidecar is provided by lib-dirty-tree-sidecar.sh
# (sourced above) and reads/writes the OUTPUT, DIRTY_TREE_WRITTEN,
# UNTRACKED_BASELINE, DIRTY_TREE_SIDECAR, SCRIPT_DIR globals declared
# above.

# shellcheck disable=SC2329,SC2317 # body invoked indirectly by the EXIT trap below.
_codex_exit_dispatcher() {
    local rc=${1:-$?}
    _emit_timing_record "$rc"
    [[ -n "$MODEL_ARGS_TMP" ]] && rm -f "$MODEL_ARGS_TMP"
    [[ -n "$CODEX_HOME_DIR" ]] && rm -rf "$CODEX_HOME_DIR"
    # When sandbox is read-only the syscall block prevents writes, so emit a
    # static clean sidecar (maintains consumer contract) without scanning.
    if [[ "${CODEX_SANDBOX_MODE:-}" == "read-only" ]]; then
        if [[ -n "${DIRTY_TREE_SIDECAR:-}" && "$DIRTY_TREE_WRITTEN" == "false" ]]; then
            printf 'STATUS=clean\nMODE=baseline\nREASON=codex-sandbox-read-only\n' \
                > "$DIRTY_TREE_SIDECAR" 2>/dev/null || true
            DIRTY_TREE_WRITTEN=true
        fi
    else
        _write_dirty_tree_sidecar
    fi
    codex_launcher_promote_inner_done "$OUTPUT"
    exit "$rc"
}
# shellcheck disable=SC2154 # _rc is assigned inside the trap string at runtime.
trap '_rc=$?; _codex_exit_dispatcher "$_rc"' EXIT

if [[ -n "$PROMPT_FILE" ]]; then
    _pf_first_line=$(head -1 -- "$PROMPT_FILE" 2>/dev/null || true)
    if [[ "$_pf_first_line" == "LARCH_PROMPT_SENTINEL=1" ]]; then
        # Hash+kind sentinel written by the non-retry (happy) path for --agent-file
        # launches. Reconstruct the full prompt via render-specialist-prompt.sh and
        # verify the SHA-256 hash to catch renderer changes between launch and retry.
        _s_kind="" _s_hash="" _s_agent_file="" _s_mode="" _s_scope="" _s_comp=false _s_diff="" _s_commit_count="" _s_plan_file="" _s_feature_file=""
        while read -r _s_line; do
            _s_k="${_s_line%%=*}"
            _s_v="${_s_line#*=}"
            case "$_s_k" in
                KIND)              _s_kind="$_s_v" ;;
                HASH)              _s_hash="$_s_v" ;;
                AGENT_FILE)        _s_agent_file="$_s_v" ;;
                MODE)              _s_mode="$_s_v" ;;
                SCOPE_FILES)       _s_scope="$_s_v" ;;
                COMPETITION_NOTICE) [[ "$_s_v" == "true" ]] && _s_comp=true ;;
                DIFF_FILE)         _s_diff="$_s_v" ;;
                COMMIT_COUNT)      _s_commit_count="$_s_v" ;;
                PLAN_FILE)         _s_plan_file="$_s_v" ;;
                FEATURE_FILE)      _s_feature_file="$_s_v" ;;
            esac
        done < "$PROMPT_FILE"
        if [[ "$_s_kind" != "specialist" || -z "$_s_agent_file" || -z "$_s_mode" || -z "$_s_hash" ]]; then
            larch_err "launch-review.sh: malformed prompt sentinel in $PROMPT_FILE (missing or empty KIND/AGENT_FILE/MODE/HASH)"
            exit 1
        fi
        _s_render_args=(--agent-file "$_s_agent_file" --mode "$_s_mode")
        [[ -n "$_s_scope" ]] && _s_render_args+=(--scope-files "$_s_scope")
        [[ "$_s_comp" == "true" ]] && _s_render_args+=(--competition-notice)
        [[ -n "$_s_diff" ]] && _s_render_args+=(--diff-file "$_s_diff")
        [[ -n "$_s_commit_count" ]] && _s_render_args+=(--commit-count "$_s_commit_count")
        [[ -n "$_s_plan_file" ]] && _s_render_args+=(--plan-file "$_s_plan_file")
        [[ -n "$_s_feature_file" ]] && _s_render_args+=(--feature-file "$_s_feature_file")
        PROMPT=$("$SCRIPT_DIR/render-specialist-prompt.sh" "${_s_render_args[@]}")
        _s_reconstructed_hash=""
        if command -v shasum >/dev/null 2>&1; then
            _s_reconstructed_hash=$(printf '%s' "$PROMPT" | LC_ALL=C shasum -a 256 | awk '{print $1}')
        elif command -v sha256sum >/dev/null 2>&1; then
            _s_reconstructed_hash=$(printf '%s' "$PROMPT" | sha256sum | awk '{print $1}')
        fi
        if [[ -z "$_s_reconstructed_hash" ]]; then
            # No SHA-256 tool on this host; cannot verify reconstruction against stored HASH.
            # Fail closed — sentinel replay requires integrity verification.
            larch_err "launch-review.sh: no SHA-256 tool (shasum/sha256sum) available; cannot verify sentinel reconstruction"
            exit 1
        fi
        if [[ "$_s_reconstructed_hash" != "$_s_hash" ]]; then
            larch_err "launch-review.sh: prompt reconstruction hash mismatch (sentinel=$_s_hash reconstructed=$_s_reconstructed_hash)"
            exit 1
        fi
        unset _s_kind _s_hash _s_agent_file _s_mode _s_scope _s_comp _s_diff _s_commit_count _s_plan_file _s_feature_file _s_render_args \
              _s_reconstructed_hash _s_line _s_k _s_v
    else
        if ! PROMPT=$({ cat -- "$PROMPT_FILE"; _cat_status=$?; printf X; exit "$_cat_status"; }); then
            larch_err "launch-review.sh: failed to read --prompt-file $PROMPT_FILE"
            exit 1
        fi
        PROMPT=${PROMPT%X}
    fi
    unset _pf_first_line
fi

if [[ -n "$AGENT_FILE" ]]; then
    RENDER_ARGS=(--agent-file "$AGENT_FILE" --mode "$MODE")
    [[ -n "$DESCRIPTION_TEXT" ]] && RENDER_ARGS+=(--description-text "$DESCRIPTION_TEXT")
    [[ -n "$SCOPE_FILES" ]] && RENDER_ARGS+=(--scope-files "$SCOPE_FILES")
    [[ "$COMPETITION_NOTICE" == "true" ]] && RENDER_ARGS+=(--competition-notice)
    [[ -n "$DIFF_FILE" ]] && RENDER_ARGS+=(--diff-file "$DIFF_FILE")
    [[ -n "$COMMIT_COUNT" ]] && RENDER_ARGS+=(--commit-count "$COMMIT_COUNT")
    [[ -n "$PLAN_FILE" ]] && RENDER_ARGS+=(--plan-file "$PLAN_FILE")
    [[ -n "$FEATURE_FILE" ]] && RENDER_ARGS+=(--feature-file "$FEATURE_FILE")
    PROMPT=$("$SCRIPT_DIR/render-specialist-prompt.sh" "${RENDER_ARGS[@]}")
fi

# Issue #1529: deliver the HARD-CONSTRAINTS read-only preamble through
# CODEX_HOME/config.toml as the Codex `instructions` field for every
# review prompt (specialist or generic, --prompt or --prompt-file or
# --agent-file). Mirrors the GEMINI_REVIEW_HARDENING_PREAMBLE in
# scripts/launch-review.sh. The codex argv below also passes
# `--sandbox read-only` (replacing the prior `--full-auto`'s workspace-write)
# so the CLI itself rejects model-issued shell writes; the instructions
# field is the prompt-level reinforcement so the model also reasons about
# its read-only role. The dirty-tree-sidecar EXIT trap still emits a sidecar
# for Codex, but writes a static STATUS=clean record instead of running the
# scan — --sandbox read-only enforces write isolation at the syscall level.
#
# Retry-replay safety: ${OUTPUT}.prompt is consumed by collect-agent-results.sh
# empty-output retries via `--prompt-file`. Because the static hardening
# preamble lives in CODEX_HOME config instead of PROMPT, the sidecar stores
# the rendered dynamic prompt directly and replay receives the same outgoing
# prompt plus a fresh CODEX_HOME.
CODEX_REVIEW_HARDENING_PREAMBLE=$(cat <<'EOF'
HARD CONSTRAINTS — your role is read-only review. Do not create, edit, delete, or overwrite files, and do not run mutating shell or git commands. The launcher enforces this with --sandbox read-only (CLI rejects writes).
EOF
)
if grep -Fq "'''" <<< "$CODEX_REVIEW_HARDENING_PREAMBLE"; then
    larch_err "launch-review.sh: hardening preamble contains TOML triple-single-quote delimiter"
    exit 2
fi

OUTPUT_DIR=$(dirname -- "$OUTPUT")
CANON_OUTPUT_DIR=$(cd "$OUTPUT_DIR" && pwd -P)
CODEX_HOME_DIR=$(mktemp -d /tmp/larch-codex-review-home-XXXXXX)
PROJECT_KEY=${PWD//\\/\\\\}
PROJECT_KEY=${PROJECT_KEY//\"/\\\"}
TRUST_CONFIG_ARG="projects.\"$PROJECT_KEY\".trust_level=\"trusted\""
{
    printf "instructions = '''\n%s\n'''\n\n" "$CODEX_REVIEW_HARDENING_PREAMBLE"
    if [[ -f ~/.codex/config.toml ]]; then
        # Strip any existing top-level `instructions` assignment to avoid duplicate
        # keys — TOML parsers treat duplicate top-level keys as an error or silently
        # drop the second value, either of which breaks the launch.
        # Handles: triple-single-quote blocks ('''...'''), triple-double-quote blocks
        # ("""..."""), and single-line string forms ("..." or '...').
        awk "
            /^[[:space:]]*instructions[[:space:]]*=[[:space:]]*'''/ { skip=1; block_end=\"'''\"; next }
            /^[[:space:]]*instructions[[:space:]]*=[[:space:]]*\"\"\"/ { skip=1; block_end=\"\\\"\\\"\\\"\"; next }
            skip && index(\$0, block_end) { skip=0; next }
            skip { next }
            /^[[:space:]]*instructions[[:space:]]*=/ { next }
            { print }
        " ~/.codex/config.toml
        printf '\n'
    fi
} > "$CODEX_HOME_DIR/config.toml"
if [[ -f ~/.codex/auth.json ]]; then
    ln -sf "$(cd ~/.codex && pwd)/auth.json" "$CODEX_HOME_DIR/auth.json"
fi
MODEL_ARGS_TMP=$(mktemp)
PROMPT_FILE_SIDECAR="${OUTPUT}.prompt"
# Retry-safe: for specialist (--agent-file) launches without free-form
# --description-text, write a compact hash+kind sentinel instead of the full
# prompt body to reduce sidecar I/O on the happy path. On retry the launcher
# reads the sentinel and reconstructs via render-specialist-prompt.sh.
# For generic (--prompt / --prompt-file) and description-mode paths, write the
# full prompt verbatim so retry replay always has the text available.
if [[ -n "$AGENT_FILE" && -z "$DESCRIPTION_TEXT" ]]; then
    _ps_hash=""
    if command -v shasum >/dev/null 2>&1; then
        _ps_hash=$(printf '%s' "$PROMPT" | LC_ALL=C shasum -a 256 | awk '{print $1}')
    elif command -v sha256sum >/dev/null 2>&1; then
        _ps_hash=$(printf '%s' "$PROMPT" | sha256sum | awk '{print $1}')
    fi
    if [[ -n "$_ps_hash" ]]; then
        {
            printf 'LARCH_PROMPT_SENTINEL=1\n'
            printf 'KIND=specialist\n'
            printf 'HASH=%s\n' "$_ps_hash"
            printf 'AGENT_FILE=%s\n' "$AGENT_FILE"
            printf 'MODE=%s\n' "$MODE"
            [[ -n "$SCOPE_FILES" ]] && printf 'SCOPE_FILES=%s\n' "$SCOPE_FILES"
            [[ "$COMPETITION_NOTICE" == "true" ]] && printf 'COMPETITION_NOTICE=true\n'
            [[ -n "$DIFF_FILE" ]] && printf 'DIFF_FILE=%s\n' "$DIFF_FILE"
            # Only write COMMIT_COUNT when it is a non-negative integer; reject
            # multi-line or non-numeric values to keep the sentinel line-oriented.
            [[ "$COMMIT_COUNT" =~ ^[0-9]+$ ]] && printf 'COMMIT_COUNT=%s\n' "$COMMIT_COUNT"
            # Only write PLAN_FILE/FEATURE_FILE when they contain no newlines or control characters;
            # the sentinel is line-oriented and a path with embedded newlines would corrupt replay parsing.
            [[ -n "$PLAN_FILE" && "$PLAN_FILE" == "${PLAN_FILE//$'\n'/}" ]] && printf 'PLAN_FILE=%s\n' "$PLAN_FILE"
            [[ -n "$FEATURE_FILE" && "$FEATURE_FILE" == "${FEATURE_FILE//$'\n'/}" ]] && printf 'FEATURE_FILE=%s\n' "$FEATURE_FILE"
        } > "$PROMPT_FILE_SIDECAR"
    else
        printf '%s' "$PROMPT" > "$PROMPT_FILE_SIDECAR"
    fi
    unset _ps_hash
else
    printf '%s' "$PROMPT" > "$PROMPT_FILE_SIDECAR"
fi
rm -f "$DIRTY_TREE_SIDECAR" "$UNTRACKED_BASELINE" "${DIRTY_TREE_SIDECAR}.tracked-paths" "${DIRTY_TREE_SIDECAR}.new-untracked-paths"
"$SCRIPT_DIR/snapshot-untracked.sh" --output "$UNTRACKED_BASELINE" --nul
MODEL_ARGS_ERR=$(mktemp)
if "$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort > "$MODEL_ARGS_TMP" 2> "$MODEL_ARGS_ERR"; then
    :
else
    rc=$?
    _emit_timing_record "$rc"
    rm -f "$MODEL_ARGS_TMP"
    _codex_ma_dts_tmp="${OUTPUT}.dirty-tree.tmp.$$"
    printf 'STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=model-args-preflight-no-agent-ran\n' \
        > "$_codex_ma_dts_tmp" 2>/dev/null && \
        mv -f "$_codex_ma_dts_tmp" "${OUTPUT}.dirty-tree" 2>/dev/null || \
        rm -f "$_codex_ma_dts_tmp" 2>/dev/null || true
    : > "$OUTPUT" 2>/dev/null || true
    {
        printf 'STATUS=FAILED\n'
        printf 'FAILURE_REASON=agent-model-args.sh failed (exit %s): %s\n' \
            "$rc" "$(head -1 "$MODEL_ARGS_ERR" 2>/dev/null | tr '\n' ' ')"
    } > "${OUTPUT}.diag" 2>/dev/null || true
    rm -f "$MODEL_ARGS_ERR"
    {
        printf 'TOOL=codex\n'
        printf 'TIMEOUT=%s\n' "$TIMEOUT"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'OUTPUT_FILE=%s\n' "$OUTPUT"
        printf 'CMD_JSON=[]\n'
    } > "${OUTPUT}.meta" 2>/dev/null || true
    printf '%s\n' "$rc" > "${OUTPUT}.done" 2>/dev/null || true
    trap - EXIT
    exit "$rc"
fi
rm -f "$MODEL_ARGS_ERR"
MODEL_ARGS=()
while IFS= read -r arg; do
    MODEL_ARGS+=("$arg")
done < "$MODEL_ARGS_TMP"
RUN_EXTERNAL="$SCRIPT_DIR/run-external-agent.sh"
SIDECAR="${OUTPUT}.sidecar"

EXIT_CODE=0
if : > "$SIDECAR" 2>/dev/null; then
    :
else
    SIDECAR=/dev/null
fi
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "codex"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    EXIT_CODE=0
    if [[ "$SIDECAR" != "/dev/null" ]]; then
        CODEX_HOME="$CODEX_HOME_DIR" \
        RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
        "$RUN_EXTERNAL" \
            --tool codex \
            --output "$OUTPUT" \
            --timeout "$TIMEOUT" \
            -- \
            codex exec --sandbox read-only -C "$PWD" \
            --add-dir "$CANON_OUTPUT_DIR" \
            ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
            -c "$TRUST_CONFIG_ARG" \
            --output-last-message "$OUTPUT" \
            -- \
            "$PROMPT" \
            >>"$SIDECAR" 2>&1 || EXIT_CODE=$?
    else
        CODEX_HOME="$CODEX_HOME_DIR" \
        RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
        "$RUN_EXTERNAL" \
            --tool codex \
            --output "$OUTPUT" \
            --timeout "$TIMEOUT" \
            -- \
            codex exec --sandbox read-only -C "$PWD" \
            --add-dir "$CANON_OUTPUT_DIR" \
            ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
            -c "$TRUST_CONFIG_ARG" \
            --output-last-message "$OUTPUT" \
            -- \
            "$PROMPT" \
            >/dev/null 2>&1 || EXIT_CODE=$?
    fi
    if (( EXIT_CODE != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) && external_is_auth_failure "codex" "$SIDECAR"; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR" 2>/dev/null || true
        continue
    fi
    break
done

if (( EXIT_CODE != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "codex" "$SIDECAR")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    append_launch_failure "review Step 2" "codex-review" "$EXIT_CODE" "$SIDECAR" "$_VERDICT" "$AUTH_ATTEMPT"
fi

codex_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-review.sh" "$PROMPT_FILE_SIDECAR" "$PWD"

N=$(awk '/^tokens used$/ { getline n; gsub(",","",n); last=n } END { print last }' "$SIDECAR" 2>/dev/null || true)
if [[ "$N" =~ ^[0-9]+$ ]]; then
    "$PLUGIN_ROOT/scripts/token-ledger.sh" record-vendor codex total="$N" raw="codex_review" >/dev/null 2>&1 || true
fi

exit "$EXIT_CODE"

}

_launch_cursor() {
# Prevent any inherited CURSOR_CONFIG_DIR_TMP from triggering spurious
# rm -rf in the EXIT trap before cursor_launcher_setup_private_config_dir runs.
unset CURSOR_CONFIG_DIR_TMP CURSOR_CONFIG_DIR
# shellcheck disable=SC2329 # invoked indirectly by the EXIT trap.
_emit_timing_record() {
    local rc=${1:-$?}
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    [[ -n "${TIMING_START_S:-}" && -n "${OUTPUT:-}" ]] || return 0
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor cursor \
        --task-kind "${TIMING_TASK_KIND:-cursor-review}" \
        --start-s "$TIMING_START_S" \
        --end-s "$end_s" \
        --output "$OUTPUT" \
        --exit-code "$rc" \
        --status "$status" \
        >/dev/null 2>&1 || true
}

OUTPUT=""
TIMEOUT=""
PROMPT=""
PROMPT_FILE=""
AGENT_FILE=""
MODE=""
DESCRIPTION_TEXT=""
SCOPE_FILES=""
COMPETITION_NOTICE=false
DIFF_FILE=""
COMMIT_COUNT=""
PLAN_FILE=""
FEATURE_FILE=""
TIMING_TASK_KIND="${LARCH_TIMING_TASK_KIND:-}"
TOKEN_BUDGET_CAP=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?--prompt-file requires a value}"; shift 2 ;;
        --agent-file) AGENT_FILE="${2:?--agent-file requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --description-text) DESCRIPTION_TEXT="${2:?--description-text requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --competition-notice) COMPETITION_NOTICE=true; shift ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --commit-count) COMMIT_COUNT="${2:?--commit-count requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { larch_err "launch-review.sh: --timing-task-kind requires a non-empty, non-flag-like value"; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) larch_err "launch-review.sh: --token-budget-cap requires a positive integer"; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { larch_err "launch-review.sh: --token-budget-cap requires a positive integer"; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
        --risk) [[ -n "${2:-}" ]] || { larch_err "launch-review.sh: --risk requires a value"; exit 2; }; shift 2 ;;
        *) larch_err "launch-review.sh: unknown flag: $1"; exit 2 ;;
    esac
done

if [[ -z "$OUTPUT" ]]; then
    larch_err "launch-review.sh: --output is required"; exit 2
fi
if [[ -z "$TIMEOUT" ]]; then
    larch_err "launch-review.sh: --timeout is required"; exit 2
fi

# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"
validate_meta_scalar_path --output "$OUTPUT" || exit 1
case "$TIMEOUT" in
    ''|*[!0-9]*) larch_err "launch-review.sh: --timeout must be a positive integer"; exit 2 ;;
esac
# Reject zero-padded zero values (e.g., 00, 000) that would pass the digit-only
# case above but fail the wrapper's arithmetic floor check at run-external-agent.sh
# AFTER the launcher has installed its EXIT trap and written sidecars. Keeps
# validate-before-side-effects intact (per FINDING_5 of the design plan review)
# and matches the floor used by launch-cursor-implement.sh / launch-review.sh.
if (( 10#$TIMEOUT < 1 )); then
    larch_err "launch-review.sh: --timeout must be >= 1"
    exit 2
fi

if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
fi
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="${IMPLEMENT_TMPDIR}/claude-source.env"
fi

# Apply env-var cap when --token-budget-cap was not passed explicitly; validate
# the value (invalid values silently disable the cap rather than exit 2).
if [[ -z "$TOKEN_BUDGET_CAP" && -n "${LARCH_TOKEN_BUDGET_CAP_REVIEW:-}" ]]; then
    case "$LARCH_TOKEN_BUDGET_CAP_REVIEW" in
        ''|*[!0-9]*) ;;
        *) (( 10#${LARCH_TOKEN_BUDGET_CAP_REVIEW} >= 1 )) && TOKEN_BUDGET_CAP="$LARCH_TOKEN_BUDGET_CAP_REVIEW" ;;
    esac
fi

# Per-step token budget cap: short-circuit before spawning Cursor when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-cursor-review}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        larch_errf '⚠ launch-review.sh: step token budget cap of %s tokens exceeded (%s combined vendor tokens); external reviewer fan-out skipped\n' \
            "$TOKEN_BUDGET_CAP" "$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^TOTAL=/){print substr($i,7);exit}}}')"
        printf 'STATUS=cap_hit\n' > "$OUTPUT"
        printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${OUTPUT}.cap-hit"
        if [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
            printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${IMPLEMENT_TMPDIR}/step-budget-cap-hit.env"
        fi
        printf '%s\n' "0" > "${OUTPUT}.done" 2>/dev/null || true
        exit 0
    fi
    unset _budget_out _budget_status
fi

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="cursor-review"
fi
: "${TIMING_TASK_KIND:=cursor-review}"
TIMING_START_S=$(date +%s)

_src_count=0
[[ -n "$PROMPT" ]] && _src_count=$((_src_count + 1))
[[ -n "$AGENT_FILE" ]] && _src_count=$((_src_count + 1))
[[ -n "$PROMPT_FILE" ]] && _src_count=$((_src_count + 1))
if [[ "$_src_count" -gt 1 ]]; then
    larch_err "launch-review.sh: --prompt, --agent-file, and --prompt-file are mutually exclusive"
    exit 2
fi
if [[ "$_src_count" -eq 0 ]]; then
    larch_err "launch-review.sh: one of --prompt, --agent-file, --prompt-file is required"
    exit 2
fi

MODEL_ARGS_ERR=$(mktemp)
if cursor_launcher_load_model_args 2> "$MODEL_ARGS_ERR"; then
    :
else
    rc=$?
    _emit_timing_record "$rc"
    : > "$OUTPUT" 2>/dev/null || true
    {
        printf 'STATUS=FAILED\n'
        printf 'FAILURE_REASON=cursor_launcher_load_model_args failed (exit %s): %s\n' \
            "$rc" "$(head -1 "$MODEL_ARGS_ERR" 2>/dev/null | tr '\n' ' ')"
    } > "${OUTPUT}.diag" 2>/dev/null || true
    rm -f "$MODEL_ARGS_ERR"
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=%s\n' "$TIMEOUT"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=true\n'
        printf 'OUTPUT_FILE=%s\n' "$OUTPUT"
        printf 'CMD_JSON=[]\n'
    } > "${OUTPUT}.meta" 2>/dev/null || true
    _ma_dts_tmp="${OUTPUT}.dirty-tree.tmp.$$"
    printf 'STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=model-args-preflight-no-agent-ran\n' \
        > "$_ma_dts_tmp" 2>/dev/null && \
        mv -f "$_ma_dts_tmp" "${OUTPUT}.dirty-tree" 2>/dev/null || \
        rm -f "$_ma_dts_tmp" 2>/dev/null || true
    printf '%s\n' "$rc" > "${OUTPUT}.done" 2>/dev/null || true
    exit "$rc"
fi
rm -f "$MODEL_ARGS_ERR"

WRAPPER_PID=""
DIRTY_TREE_WRITTEN=false
UNTRACKED_BASELINE="${OUTPUT}.untracked-baseline"
DIRTY_TREE_SIDECAR="${OUTPUT}.dirty-tree"

# _write_dirty_tree_sidecar is provided by lib-dirty-tree-sidecar.sh
# (sourced above) and reads/writes the OUTPUT, DIRTY_TREE_WRITTEN,
# UNTRACKED_BASELINE, DIRTY_TREE_SIDECAR, SCRIPT_DIR globals declared
# above. _write_unknown_dirty_tree_sidecar below is cursor-only and
# stays inline.

_write_unknown_dirty_tree_sidecar() {
    # Used by the auth-preflight short-circuit when no agent ran. We have
    # NOT probed the working tree (no `check-mid-run-dirty-tree.sh` call),
    # so emit STATUS=unknown rather than STATUS=clean. Pre-launch tracked
    # or staged edits would otherwise be silently masked when consumers
    # treat a present sidecar with STATUS=clean as "launcher proved the
    # tree clean." STATUS=unknown routes consumers through the same
    # recovery-safe path as a real detector failure.
    local reason="$1"
    local tmp="${DIRTY_TREE_SIDECAR}.tmp.$$"
    {
        printf 'STATUS=unknown\n'
        printf 'MODE=baseline\n'
        if [[ -r "$UNTRACKED_BASELINE" ]]; then
            printf 'UNTRACKED_BASELINE=present\n'
        else
            printf 'UNTRACKED_BASELINE=missing\n'
        fi
        printf 'REASON=%s\n' "$reason"
    } > "$tmp" 2>/dev/null && mv -f "$tmp" "$DIRTY_TREE_SIDECAR" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
    DIRTY_TREE_WRITTEN=true
}

# shellcheck disable=SC2329,SC2317  # body invoked indirectly by the EXIT trap below.
_publish_done_on_exit() {
    # The shell exit status is fixed at trap entry; this trap only publishes sidecars.
    if [[ -z "$OUTPUT" || -f "${OUTPUT}.done" ]]; then
        cursor_launcher_cleanup_private_config_dir
        return
    fi
    if [[ -n "$WRAPPER_PID" ]] && kill -0 "$WRAPPER_PID" 2>/dev/null; then
        kill "$WRAPPER_PID" 2>/dev/null || true
        wait "$WRAPPER_PID" 2>/dev/null || true
    fi
    # Clean up the private config dir only after the wrapper has stopped so the
    # cursor agent process no longer needs the directory.
    cursor_launcher_cleanup_private_config_dir
    _write_dirty_tree_sidecar
    if [[ -f "${OUTPUT}.inner.done" ]]; then
        mv -f "${OUTPUT}.inner.done" "${OUTPUT}.done" 2>/dev/null || true
    else
        echo "99" > "${OUTPUT}.done" 2>/dev/null || true
    fi
    return 0
}
# shellcheck disable=SC2154 # _rc is assigned inside the trap string at runtime.
trap '_rc=$?; _emit_timing_record "$_rc"; _publish_done_on_exit; exit "$_rc"' EXIT

if [[ -n "$PROMPT_FILE" ]]; then
    if ! PROMPT=$({ cat -- "$PROMPT_FILE"; _cat_status=$?; printf X; exit "$_cat_status"; }); then
        larch_err "launch-review.sh: failed to read --prompt-file $PROMPT_FILE"
        exit 1
    fi
    PROMPT=${PROMPT%X}
fi

if [[ -n "$AGENT_FILE" ]]; then
    RENDER_ARGS=(--agent-file "$AGENT_FILE" --mode "$MODE")
    [[ -n "$DESCRIPTION_TEXT" ]] && RENDER_ARGS+=(--description-text "$DESCRIPTION_TEXT")
    [[ -n "$SCOPE_FILES" ]] && RENDER_ARGS+=(--scope-files "$SCOPE_FILES")
    [[ "$COMPETITION_NOTICE" == "true" ]] && RENDER_ARGS+=(--competition-notice)
    [[ -n "$DIFF_FILE" ]] && RENDER_ARGS+=(--diff-file "$DIFF_FILE")
    [[ -n "$COMMIT_COUNT" ]] && RENDER_ARGS+=(--commit-count "$COMMIT_COUNT")
    [[ -n "$PLAN_FILE" ]] && RENDER_ARGS+=(--plan-file "$PLAN_FILE")
    [[ -n "$FEATURE_FILE" ]] && RENDER_ARGS+=(--feature-file "$FEATURE_FILE")
    PROMPT=$("$SCRIPT_DIR/render-specialist-prompt.sh" "${RENDER_ARGS[@]}")
fi

# Issue #1529: prepend a HARD-CONSTRAINTS read-only preamble to every Cursor
# review prompt (specialist or generic, --prompt or --prompt-file or
# --agent-file). Mirrors the GEMINI_REVIEW_HARDENING_PREAMBLE in
# scripts/launch-review.sh. The cursor argv below passes `--mode plan`
# so the CLI itself disables the agent's write tools; the preamble is the
# prompt-level reinforcement so the model also reasons about its read-only
# role. The launcher's existing dirty-tree-sidecar machinery
# (snapshot-untracked.sh untracked-files baseline + _write_dirty_tree_sidecar
# EXIT trap) remains the after-the-fact detector.
#
# Retry-replay safety: ${OUTPUT}.prompt is consumed by collect-agent-results.sh
# empty-output retries via `--prompt-file`. To keep that replay idempotent
# (one preamble, not N), the sidecar is written from $ORIGINAL_PROMPT
# (the user/specialist-rendered body BEFORE prepending the preamble) so that
# on retry the launcher reads the body, prepends the preamble exactly once,
# and produces an identical outgoing PROMPT — no preamble stacking.
CURSOR_SANDBOX_ENFORCEMENT_LINE="The launcher passes --mode plan to the cursor CLI. Any post-run mutation will be detected by the dirty-tree sidecar."
CURSOR_REVIEW_HARDENING_PREAMBLE=$(cat <<EOF
HARD CONSTRAINTS — your role is read-only review. Do not create, edit, delete, or overwrite files, and do not run mutating shell or git commands.
${CURSOR_SANDBOX_ENFORCEMENT_LINE}
EOF
)
ORIGINAL_PROMPT="$PROMPT"
PROMPT="${CURSOR_REVIEW_HARDENING_PREAMBLE}"$'\n\n'"${PROMPT}"

WRAPPED_PROMPT=$({ "$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT"; _wrap_status=$?; printf X; exit "$_wrap_status"; })
WRAPPED_PROMPT=${WRAPPED_PROMPT%X}
RUN_EXTERNAL="$SCRIPT_DIR/run-external-agent.sh"
SIDECAR="${OUTPUT}.sidecar"
PROMPT_FILE_SIDECAR="${OUTPUT}.prompt"
# Retry-safe: store the user-original (pre-preamble) bytes so
# collect-agent-results.sh `--prompt-file` replay re-prepends the preamble
# exactly once. See ORIGINAL_PROMPT comment above.
printf '%s' "$ORIGINAL_PROMPT" > "$PROMPT_FILE_SIDECAR"
rm -f "$DIRTY_TREE_SIDECAR" "$UNTRACKED_BASELINE" "${DIRTY_TREE_SIDECAR}.tracked-paths" "${DIRTY_TREE_SIDECAR}.new-untracked-paths"
"$SCRIPT_DIR/snapshot-untracked.sh" --output "$UNTRACKED_BASELINE" --nul

# Run Cursor auth preflight. On preflight failure (Darwin + empty
# CURSOR_API_KEY + missing `cursor-user` keychain entry), synthesize the
# sentinel/diag artifacts that `run-external-agent.sh` would have written so
# backgrounded callers see STATUS=FAILED with the actionable reason within
# seconds rather than SENTINEL_TIMEOUT after the full collector timeout.
PREFLIGHT_RC=0
cursor_launcher_setup_auth_argv || PREFLIGHT_RC=$?
if [[ "$PREFLIGHT_RC" != "0" ]]; then
    : > "$OUTPUT" 2>/dev/null || true
    {
        printf 'STATUS=FAILED\n'
        printf 'FAILURE_REASON=cursor-auth-preflight: CURSOR_API_KEY unset/empty and cursor-user keychain entry missing on Darwin; see docs/installation-and-setup.md (Cursor section)\n'
    } > "${OUTPUT}.diag" 2>/dev/null || true
    # Stub .meta so collect-agent-results.sh's parser does not regress on a
    # missing file (TOOL/TIMEOUT keys keep its retry classifier sane; CMD_JSON
    # is intentionally an empty array because no child was launched, so the
    # collector's retry path will see CMD_JSON=[] and skip retry).
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=%s\n' "$TIMEOUT"
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=true\n'
        printf 'OUTPUT_FILE=%s\n' "$OUTPUT"
        printf 'CMD_JSON=[]\n'
    } > "${OUTPUT}.meta" 2>/dev/null || true
    _write_unknown_dirty_tree_sidecar "preflight-short-circuit-no-agent-ran"
    # `.done` is the last artifact written so polling collectors see all
    # other sidecars in place once they observe `.done`. The wrapper's trap
    # writes the EXIT_CODE; we mirror that by writing the preflight RC.
    printf '%s\n' "$PREFLIGHT_RC" > "${OUTPUT}.done" 2>/dev/null || true
    exit "$PREFLIGHT_RC"
fi

# shellcheck disable=SC2086
EXIT_CODE=0
if : > "$SIDECAR" 2>/dev/null; then
    _STDERR_TARGET="$SIDECAR"
else
    SIDECAR=/dev/null
    _STDERR_TARGET=/dev/null
fi

cursor_launcher_setup_private_config_dir
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "cursor"
    RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
    "$RUN_EXTERNAL" \
            --tool cursor \
            --output "$OUTPUT" \
            --timeout "$TIMEOUT" \
            --capture-stdout-only \
            -- \
            cursor agent -p --trust --mode plan \
            --output-format json \
            ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
            ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} \
            --workspace "$PWD" \
            "$WRAPPED_PROMPT" \
            2>>"$_STDERR_TARGET" &
    WRAPPER_PID=$!
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    wait "$WRAPPER_PID" && EXIT_CODE=0 || EXIT_CODE=$?
    WRAPPER_PID=""
    if (( EXIT_CODE != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) \
        && { external_is_auth_failure "cursor" "$SIDECAR" || external_is_auth_failure "cursor" "${OUTPUT}.diag"; }; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR" 2>/dev/null || true
        : > "${OUTPUT}.diag" 2>/dev/null || true
        continue
    fi
    break
done

if (( EXIT_CODE != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "cursor" "$SIDECAR" "${OUTPUT}.diag")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    _FAILURE_OUTPUT="$SIDECAR"
    if [[ ! -s "$_FAILURE_OUTPUT" && -s "${OUTPUT}.diag" ]]; then
        _FAILURE_OUTPUT="${OUTPUT}.diag"
    fi
    append_launch_failure "review Step 2" "cursor-review" "$EXIT_CODE" "$_FAILURE_OUTPUT" "$_VERDICT" "$AUTH_ATTEMPT"
fi

cursor_launcher_append_outer_meta "${OUTPUT}.meta" "$SCRIPT_DIR/launch-review.sh" "$PROMPT_FILE_SIDECAR" "$PWD"

# Test-only deterministic hook (FINDING_1 of /review round 1 hardening): the
# legacy `eval "$LARCH_TEST_TRAP_AFTER_INNER_DONE"` was an env-var → arbitrary-
# shell channel in shipped runtime code. Replaced with a strictly-gated
# source-file pattern that requires:
#   1. LARCH_ALLOW_TEST_HOOKS=1 (exact match; production callers must NOT set this).
#   2. LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE points at a regular non-symlink file
#      that the test harness wrote under its own tmpdir.
# A production attacker would need to set TWO env vars AND control a writable
# filesystem path the launcher will source, which is a much higher bar than
# leaking one env var. The harness still controls deterministic post-wrapper
# trap behavior by writing shell snippets to a path inside its session tmpdir.
# The legacy env var name (LARCH_TEST_TRAP_AFTER_INNER_DONE without _FILE) is
# intentionally NOT honored — silent fallback would defeat the gating.
if [[ "${LARCH_ALLOW_TEST_HOOKS:-}" == "1" && -n "${LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE:-}" ]]; then
    if [[ -f "$LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE" && ! -L "$LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE"
    fi
fi

# Atomic-or-bust JSON-extraction pattern: keep $OUTPUT pointing at usable
# bytes for downstream collectors at every step. The previous shape
# (`mv $OUTPUT $OUTPUT.json` then guarded jq) destroyed $OUTPUT before
# proving the jq extraction would succeed — if jq was missing or extraction
# failed, $OUTPUT ended up empty/missing while the only copy of the run
# output sat unreachable at $OUTPUT.json. Fix:
#   1. Copy (not move) bytes to $OUTPUT.json sidecar.
#   2. Try to extract .result via jq into a temp file.
#   3. ONLY install the temp file over $OUTPUT after jq succeeds with
#      non-empty content — else leave the original bytes at $OUTPUT
#      unchanged so collectors still see prose.
if [[ -s "$OUTPUT" ]]; then
    # Remove any stale ${OUTPUT}.json from a prior run BEFORE the cp. If cp
    # then fails (full disk, permission, transient I/O), the launcher must not
    # silently fall through to a state where the prior-run JSON is treated as
    # this run's bytes — that would let jq promote the wrong .result into
    # $OUTPUT and record-vendor log the wrong token totals (FINDING_3 of
    # /review round 1). run-external-agent.sh's pre-launch stale cleanup at
    # line ~144 does NOT include .json (the launcher owns that sidecar), so
    # the launcher must clear it itself.
    rm -f "${OUTPUT}.json"
    if ! cp "$OUTPUT" "${OUTPUT}.json" 2>/dev/null; then
        # cp failed — leave $OUTPUT as the wrapper-provided bytes (raw JSON or
        # prose) and skip the post-processing block. Collectors will still see
        # bounded content, just without launcher-extracted .result and without
        # token-ledger updates for this run. Better than silently reading a
        # stale prior-run .json.
        :
    elif command -v jq >/dev/null 2>&1 && [[ -s "${OUTPUT}.json" ]]; then
        EXTRACT_TMP="${OUTPUT}.extract.$$"
        if jq -re '.result // ""' "${OUTPUT}.json" > "$EXTRACT_TMP" 2>/dev/null && [[ -s "$EXTRACT_TMP" ]]; then
            mv "$EXTRACT_TMP" "$OUTPUT"
        else
            rm -f "$EXTRACT_TMP"
            # jq missing, JSON malformed, or empty .result — leave $OUTPUT as
            # raw JSON bytes; collectors that prefer prose will see literal
            # JSON, which is still bounded content and not an empty file.
        fi
        read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "${OUTPUT}.json" 2>/dev/null || echo "0 0 0 0")
        if [[ "$INP" =~ ^[0-9]+$ && "$OUT" =~ ^[0-9]+$ && "$CR" =~ ^[0-9]+$ && "$CW" =~ ^[0-9]+$ ]]; then
            TOT=$((INP + OUT + CR + CW))
            "$PLUGIN_ROOT/scripts/token-ledger.sh" record-vendor cursor input="$INP" output="$OUT" cache_read="$CR" cache_create="$CW" total="$TOT" raw="cursor_review" >/dev/null 2>&1 || true
        fi
        # Distinguish Cursor's empty .result envelope from malformed JSON or
        # generic empty output so the collector can report the backend failure
        # mode directly. Use (.result // "") == "" so that null and absent
        # .result are treated identically to an explicit empty string.
        if jq -e '(.result // "") == ""' "${OUTPUT}.json" >/dev/null 2>&1; then
            printf 'CURSOR_EMPTY_RESPONSE\n' > "$OUTPUT"
        fi
    fi
fi

_write_dirty_tree_sidecar
cursor_launcher_promote_inner_done "$OUTPUT"
exit "$EXIT_CODE"

}

case "$TOOL" in
    codex) _launch_codex "${ARGS[@]+"${ARGS[@]}"}" ;;
    cursor) _launch_cursor "${ARGS[@]+"${ARGS[@]}"}" ;;
    gemini)
        # shellcheck source=scripts/lib-gemini-launcher-review.sh
        # shellcheck disable=SC1091
        source "$SCRIPT_DIR/lib-gemini-launcher-review.sh"
        _launch_gemini "${ARGS[@]+"${ARGS[@]}"}"
        ;;
esac
