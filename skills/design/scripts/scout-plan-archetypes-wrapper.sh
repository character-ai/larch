#!/usr/bin/env bash
# scout-plan-archetypes-wrapper.sh — /design Step 3 scout for dynamic plan-review archetypes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: scout-plan-archetypes-wrapper.sh --plan-file PATH --description-file PATH --output PATH --max-archetypes N --session-env-path PATH"
}

PLAN_FILE=""
DESCRIPTION_FILE=""
OUTPUT=""
MAX_ARCHETYPES="6"
SESSION_ENV_FILE=""
PROMPT_TEMPLATE="${PLUGIN_ROOT}/skills/design/scripts/scout-plan-archetypes-prompt.txt"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --description-file) DESCRIPTION_FILE="${2:?}"; shift 2 ;;
        --output) OUTPUT="${2:?}"; shift 2 ;;
        --max-archetypes) MAX_ARCHETYPES="${2:?}"; shift 2 ;;
        --session-env-path) SESSION_ENV_FILE="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "scout-plan-archetypes-wrapper.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

fail() {
    larch_err "scout-plan-archetypes-wrapper.sh: $1"
    exit 2
}

has_control_chars() {
    printf '%s' "$1" | LC_ALL=C grep -q '[[:cntrl:]]'
}

canonical_existing_file() {
    local p="$1" dir base
    [[ -n "$p" ]] || return 1
    has_control_chars "$p" && return 1
    [[ "$p" != *..* ]] || return 1
    [[ -f "$p" ]] || return 1
    [[ ! -L "$p" ]] || return 1
    dir=$(cd "$(dirname "$p")" && pwd -P) || return 1
    base=$(basename "$p")
    printf '%s/%s\n' "$dir" "$base"
}

canonical_existing_dir() {
    local p="$1"
    [[ -n "$p" ]] || return 1
    has_control_chars "$p" && return 1
    [[ "$p" != *..* ]] || return 1
    [[ -d "$p" ]] || return 1
    [[ ! -L "$p" ]] || return 1
    (cd "$p" && pwd -P) || return 1
}

under_root() {
    local path="$1" root="$2"
    [[ "$path" == "$root" || "$path" == "$root/"* ]]
}

allowed_input_roots() {
    local roots=() r=""
    r=$(canonical_existing_dir "$(dirname "$PLAN_FILE")" || true)
    [[ -n "$r" ]] && roots+=("$r")
    if [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        r=$(canonical_existing_dir "$IMPLEMENT_TMPDIR" || true)
        [[ -n "$r" ]] && roots+=("$r")
    fi
    if [[ -n "$SESSION_ENV_FILE" && -f "$SESSION_ENV_FILE" && ! -L "$SESSION_ENV_FILE" ]]; then
        r=$(canonical_existing_dir "$(dirname "$SESSION_ENV_FILE")" || true)
        [[ -n "$r" ]] && roots+=("$r")
    fi
    printf '%s\n' "${roots[@]}"
}

validate_under_allowed_roots() {
    local label="$1" path="$2" canon root matched=0
    canon=$(canonical_existing_file "$path") || fail "invalid $label: $path"
    while IFS= read -r root || [[ -n "$root" ]]; do
        [[ -n "$root" ]] || continue
        if under_root "$canon" "$root"; then
            matched=1
            break
        fi
    done < <(allowed_input_roots)
    (( matched )) || fail "$label outside allowed DESIGN_TMPDIR / IMPLEMENT_TMPDIR / session roots: $path"
    printf '%s\n' "$canon"
}

[[ -n "$PLAN_FILE" ]] || fail "--plan-file is required"
[[ -n "$DESCRIPTION_FILE" ]] || fail "--description-file is required"
[[ -n "$OUTPUT" ]] || fail "--output is required"
[[ -n "$SESSION_ENV_FILE" ]] || fail "--session-env-path is required"

case "$MAX_ARCHETYPES" in ''|*[!0-9]*) fail "--max-archetypes must be an integer 0-6" ;; esac
(( 10#$MAX_ARCHETYPES <= 6 )) || fail "--max-archetypes must be 0-6 for plan scout"

PLAN_CANON=$(validate_under_allowed_roots "plan-file" "$PLAN_FILE")
DESC_CANON=$(validate_under_allowed_roots "description-file" "$DESCRIPTION_FILE")

DESIGN_TMPDIR=$(canonical_existing_dir "$(dirname "$PLAN_CANON")" || true)
[[ -n "$DESIGN_TMPDIR" ]] || fail "cannot resolve DESIGN_TMPDIR from plan path"

SCOPE_LIST="$DESIGN_TMPDIR/scout-plan-scope-files.txt"
write_scope_files() {
    local plan="$1" target="$2"
    mkdir -p "$(dirname "$target")"
    "$PLUGIN_ROOT/scripts/extract-plan-scope-paths.sh" --plan-file "$plan" >"${target}.tmp" || return 1
    mv -f "${target}.tmp" "$target"
}
write_scope_files "$PLAN_CANON" "$SCOPE_LIST" || fail "scope-files derivation failed"

mkdir -p "$(dirname "$OUTPUT")"
write_empty_manifest() {
    local target="$1" tmp
    tmp=$(mktemp "${target}.tmp.XXXXXX") || exit 1
    printf '{"archetypes":[]}\n' >"$tmp"
    mv -f "$tmp" "$target"
}

filter_and_cap_manifest() {
    local path="$1" cap="$2"
    local before after tmp
    before=$(jq -r '.archetypes | length' "$path" | tr -d '[:space:]')
    tmp=$(mktemp "${path}.filter.XXXXXX") || return 1
    if ! jq -c --argjson cap "$cap" '
      ["arch","edge","innovation","pragmatic","requirements"] as $r
      | [.archetypes[]? | select((.name | ascii_downcase) as $n | ($r | index($n) | not))]
      | if length > $cap then .[0:$cap] else . end
      | {archetypes: .}
    ' "$path" >"$tmp"; then
        rm -f "$tmp"
        return 1
    fi
    after=$(jq -r '.archetypes | length' "$tmp" | tr -d '[:space:]')
    if [[ "$before" =~ ^[0-9]+$ && "$after" =~ ^[0-9]+$ && "$before" -gt "$after" ]]; then
        emit_kv WARN "scout-plan-archetypes-wrapper: filtered archetypes from ${before} to ${after} (reserved slugs and/or cap)"
    fi
    mv -f "$tmp" "$path"
}

SCOUT_ARGS=(
    --mode description
    --description-file "$DESC_CANON"
    --plan-file "$PLAN_CANON"
    --scope-files "$SCOPE_LIST"
    --max-archetypes "$MAX_ARCHETYPES"
    --output "$OUTPUT"
    --session-env-path "$SESSION_ENV_FILE"
)

PROMPT_FLAG=()
if [[ -r "$PROMPT_TEMPLATE" && -f "$PROMPT_TEMPLATE" && ! -L "$PROMPT_TEMPLATE" ]]; then
    PROMPT_FLAG=(--prompt-override-file "$PROMPT_TEMPLATE")
else
    larch_err "WARN scout-plan-archetypes-wrapper: plan-review prompt template missing; using built-in scout prompt"
fi

SCOUT_DYNAMIC_BIN="${SCOUT_PLAN_ARCHETYPES_SCOUT_SH:-$PLUGIN_ROOT/scripts/scout-dynamic-archetypes.sh}"

run_scout() {
    "$SCOUT_DYNAMIC_BIN" "${SCOUT_ARGS[@]+"${SCOUT_ARGS[@]}"}" "$@"
}

scout_tmp="$(mktemp "${TMPDIR:-/tmp}/scout-plan-wrapper.XXXXXX")"
trap 'rm -f "$scout_tmp"' EXIT
set +e
run_scout "${PROMPT_FLAG[@]+"${PROMPT_FLAG[@]}"}" >"$scout_tmp"
scout_rc=$?
set -e

SCOUT_STATUS=$(awk -F= '$1=="SCOUT_STATUS"{print $2; exit}' "$scout_tmp" || true)
[[ -n "$SCOUT_STATUS" ]] || SCOUT_STATUS="validation-failed"

if [[ "$scout_rc" -ne 0 ]]; then
    if grep -Fq 'FAILURE_REASON=prompt-override-invalid' "$scout_tmp" 2>/dev/null; then
        larch_err "WARN scout-plan-archetypes-wrapper: prompt override rejected; retrying without override"
        set +e
        run_scout >"$scout_tmp"
        scout_rc=$?
        set -e
        SCOUT_STATUS=$(awk -F= '$1=="SCOUT_STATUS"{print $2; exit}' "$scout_tmp" || true)
        [[ -n "$SCOUT_STATUS" ]] || SCOUT_STATUS="validation-failed"
    fi
fi

if [[ "$scout_rc" -ne 0 ]] || [[ "$SCOUT_STATUS" != "ok" && "$SCOUT_STATUS" != "empty" ]]; then
    write_empty_manifest "$OUTPUT"
    emit_kv SCOUT_STATUS "${SCOUT_STATUS:-validation-failed}"
    emit_kv SCOUT_MANIFEST "$OUTPUT"
    emit_kv SCOUT_ARCHETYPE_COUNT 0
    exit 0
fi

if ! jq -e '.archetypes | type == "array"' "$OUTPUT" >/dev/null 2>&1; then
    write_empty_manifest "$OUTPUT"
    emit_kv SCOUT_STATUS parse-failed
    emit_kv SCOUT_MANIFEST "$OUTPUT"
    emit_kv SCOUT_ARCHETYPE_COUNT 0
    exit 0
fi

filter_and_cap_manifest "$OUTPUT" "$MAX_ARCHETYPES" || {
    write_empty_manifest "$OUTPUT"
    emit_kv SCOUT_STATUS validation-failed
    emit_kv SCOUT_MANIFEST "$OUTPUT"
    emit_kv SCOUT_ARCHETYPE_COUNT 0
    exit 0
}

final_count=$(jq '.archetypes | length' "$OUTPUT")
emit_kv SCOUT_STATUS "$SCOUT_STATUS"
emit_kv SCOUT_MANIFEST "$OUTPUT"
emit_kv SCOUT_ARCHETYPE_COUNT "$final_count"
exit 0
