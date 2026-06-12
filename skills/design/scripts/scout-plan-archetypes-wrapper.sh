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
    larch_err "       scout-plan-archetypes-wrapper.sh --filter-manifest INPUT OUTPUT [--max-archetypes N]"
}

PLAN_FILE=""
DESCRIPTION_FILE=""
OUTPUT=""
FILTER_INPUT=""
FILTER_OUTPUT=""
FILTER_MODE="false"
MAX_ARCHETYPES="3"
SESSION_ENV_FILE=""
CODEX_PRESENT="false"
CURSOR_PRESENT="false"
PROMPT_TEMPLATE="${PLUGIN_ROOT}/skills/design/scripts/scout-plan-archetypes-prompt.txt"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --filter-manifest) FILTER_INPUT="${2:?}"; FILTER_OUTPUT="${3:?}"; FILTER_MODE="true"; shift 3 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --description-file) DESCRIPTION_FILE="${2:?}"; shift 2 ;;
        --output) OUTPUT="${2:?}"; shift 2 ;;
        --max-archetypes) MAX_ARCHETYPES="${2:?}"; shift 2 ;;
        --session-env-path) SESSION_ENV_FILE="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
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

[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || fail "--codex-present must be true or false"
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || fail "--cursor-present must be true or false"

case "$MAX_ARCHETYPES" in ''|*[!0-9]*) fail "--max-archetypes must be an integer 0-3" ;; esac
(( 10#$MAX_ARCHETYPES <= 3 )) || fail "--max-archetypes must be 0-3 for plan scout"

write_empty_manifest() {
    local target="$1" tmp
    mkdir -p "$(dirname "$target")"
    tmp=$(mktemp "${target}.tmp.XXXXXX") || exit 1
    printf '{"archetypes":[]}\n' >"$tmp"
    mv -f "$tmp" "$target"
}

filter_and_cap_manifest() {
    local input="$1" output="$2" cap="$3"
    local before after tmp warnings_file
    [[ -s "$input" ]] || return 1
    mkdir -p "$(dirname "$output")"
    before=$(jq -r 'if (.archetypes | type) == "array" then (.archetypes | length) else 0 end' "$input" 2>/dev/null | tr -d '[:space:]' || printf '0')
    tmp=$(mktemp "${output}.filter.XXXXXX") || return 1
    warnings_file=$(mktemp "${output}.warnings.XXXXXX") || { rm -f "$tmp"; return 1; }
    if ! jq -c --argjson cap "$cap" '
      def reserved:
        ["generic","structure","correctness","testing","security","edge-cases","plan-fidelity",
         "code-reviewer","reviewer-structure","reviewer-correctness","reviewer-testing",
         "reviewer-security","reviewer-edge-cases","reviewer-plan-fidelity",
         "arch","edge","innovation","pragmatic","requirements"];
      def has_unsafe_wrapper_tag:
        (ascii_downcase
         | contains("</scout_notes>")
           or contains("</reviewer_feature_description>")
           or contains("</plan_review_scope_anchor>")
           or contains("</feature>"));
      def has_unsafe_plan_delimiter:
        test("<implementation_plan")
        or test("<feature_description")
        or test("<reviewer_feature_description")
        or test("<plan_review_scope_anchor")
        or test("<feature[ >]");
      def has_unsafe_rationale:
        has_unsafe_wrapper_tag
        or has_unsafe_plan_delimiter
        or test("\n")
        or test("(?m)^---$");
      if ((.archetypes | type) != "array") then
        error("invalid_archetypes_shape")
      else reduce .archetypes[]? as $a
        ({seen:{}, archetypes:[], warns:[], valid_total:0};
         ($a.name // "") as $name
         | if (($a | type) != "object") then
             .warns += ["invalid archetype object"]
           elif (($name | type) != "string") or (($name | test("^[a-z][a-z0-9-]{2,40}$")) | not) then
             .warns += ["invalid archetype name: \($name)"]
           elif (reserved | index($name)) then
             .warns += ["reserved archetype name: \($name)"]
           elif (.seen[$name] // false) then
             .warns += ["duplicate archetype name: \($name)"]
           elif ((["code-quality","risk-integration","correctness","architecture","security"] | index($a.focus_area)) | not) then
             .warns += ["invalid focus_area for \($name)"]
           elif (($a.weight | type) != "number") or (($a.weight % 1) != 0) or ($a.weight < 1) or ($a.weight > 8) then
             .warns += ["invalid weight for \($name)"]
           elif (($a.rationale | type) != "string") or (($a.rationale | length) == 0) then
             .warns += ["empty rationale for \($name)"]
           elif ($a.rationale | has_unsafe_rationale) then
             .warns += ["unsafe rationale for \($name)"]
           elif (($a.prompt_body | type) != "string") or (($a.prompt_body | length) == 0) then
             .warns += ["empty prompt_body for \($name)"]
           elif (($a.prompt_body | test("(?m)^---$"))
                 or ($a.prompt_body | ascii_downcase | contains("</reviewer_"))
                 or ($a.prompt_body | has_unsafe_wrapper_tag)
                 or ($a.prompt_body | has_unsafe_plan_delimiter)) then
             .warns += ["unsafe prompt_body for \($name)"]
           else
             .seen[$name] = true
             | .valid_total += 1
             | if (.archetypes | length) < $cap then
                 (if ($a.prompt_body | test("Cite specific file paths and line ranges for any issues found, and follow the output-format rules from your outer wrapper exactly\\.?$"))
                  then $a.prompt_body
                  else ($a.prompt_body | rtrimstr(" ") | rtrimstr(".")) + " Cite specific file paths and line ranges for any issues found, and follow the output-format rules from your outer wrapper exactly."
                  end) as $repaired_body
                 | .archetypes += [{
                   name:$name,
                   focus_area:$a.focus_area,
                   weight:($a.weight | floor),
                   rationale:$a.rationale,
                   prompt_body:$repaired_body
                 }]
               else . end
           end)
      | if .valid_total > $cap then
          .warns += ["validated archetypes exceed max cap: \(.valid_total) > \($cap); truncating"]
        else . end
      | {archetypes, warns}
      end
    ' "$input" >"$tmp"; then
        rm -f "$tmp" "$warnings_file"
        return 1
    fi
    jq -r '.warns[]?' "$tmp" >"$warnings_file"
    jq -c '{archetypes}' "$tmp" >"${tmp}.manifest" || { rm -f "$tmp" "$warnings_file" "${tmp}.manifest"; return 1; }
    after=$(jq -r '.archetypes | length' "${tmp}.manifest" | tr -d '[:space:]')
    if [[ "$before" =~ ^[0-9]+$ && "$after" =~ ^[0-9]+$ && "$before" -gt "$after" ]]; then
        emit_kv WARN "scout-plan-archetypes-wrapper: filtered archetypes from ${before} to ${after} (reserved slugs and/or cap)"
    fi
    while IFS= read -r warning || [[ -n "$warning" ]]; do
        [[ -n "$warning" ]] && emit_kv WARN "$warning"
    done <"$warnings_file"
    mv -f "${tmp}.manifest" "$output"
    rm -f "$tmp" "$warnings_file"
}

if [[ "$FILTER_MODE" == "true" ]]; then
    [[ -n "$FILTER_INPUT" ]] || fail "--filter-manifest input is required"
    [[ -n "$FILTER_OUTPUT" ]] || fail "--filter-manifest output is required"
    if filter_and_cap_manifest "$FILTER_INPUT" "$FILTER_OUTPUT" "$MAX_ARCHETYPES"; then
        final_count=$(jq '.archetypes | length' "$FILTER_OUTPUT" 2>/dev/null || printf '0')
        if [[ "$final_count" == "0" ]]; then
            emit_kv SCOUT_STATUS empty
        else
            emit_kv SCOUT_STATUS ok
        fi
        emit_kv SCOUT_MANIFEST "$FILTER_OUTPUT"
        emit_kv SCOUT_ARCHETYPE_COUNT "$final_count"
    else
        write_empty_manifest "$FILTER_OUTPUT"
        emit_kv SCOUT_STATUS parse-failed
        emit_kv SCOUT_MANIFEST "$FILTER_OUTPUT"
        emit_kv SCOUT_ARCHETYPE_COUNT 0
    fi
    exit 0
fi

[[ -n "$PLAN_FILE" ]] || fail "--plan-file is required"
[[ -n "$DESCRIPTION_FILE" ]] || fail "--description-file is required"
[[ -n "$OUTPUT" ]] || fail "--output is required"
[[ -n "$SESSION_ENV_FILE" ]] || fail "--session-env-path is required"

PLAN_CANON=$(validate_under_allowed_roots "plan-file" "$PLAN_FILE")
DESC_CANON=$(validate_under_allowed_roots "description-file" "$DESCRIPTION_FILE")

DESIGN_TMPDIR=$(canonical_existing_dir "$(dirname "$PLAN_CANON")" || true)
[[ -n "$DESIGN_TMPDIR" ]] || fail "cannot resolve DESIGN_TMPDIR from plan path"

SCOPE_LIST="$DESIGN_TMPDIR/scout-plan-scope-files.txt"
write_scope_files() {
    local plan="$1" target="$2"
    mkdir -p "$(dirname "$target")"
    python3 "$PLUGIN_ROOT/python/cli.py" plan scope-paths --plan-file "$plan" >"${target}.tmp" || return 1
    mv -f "${target}.tmp" "$target"
}
write_scope_files "$PLAN_CANON" "$SCOPE_LIST" || fail "scope-files derivation failed"

mkdir -p "$(dirname "$OUTPUT")"
SCOUT_ARGS=(
    --mode description
    --description-file "$DESC_CANON"
    --plan-file "$PLAN_CANON"
    --scope-files "$SCOPE_LIST"
    --max-archetypes "$MAX_ARCHETYPES"
    --output "$OUTPUT"
    --session-env-path "$SESSION_ENV_FILE"
    --codex-present "$CODEX_PRESENT"
    --cursor-present "$CURSOR_PRESENT"
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

filter_input="$OUTPUT"
filter_tmp=$(mktemp "${OUTPUT}.filter-out.XXXXXX") || exit 1
filter_and_cap_manifest "$filter_input" "$filter_tmp" "$MAX_ARCHETYPES" || {
    rm -f "$filter_tmp"
    write_empty_manifest "$OUTPUT"
    emit_kv SCOUT_STATUS validation-failed
    emit_kv SCOUT_MANIFEST "$OUTPUT"
    emit_kv SCOUT_ARCHETYPE_COUNT 0
    exit 0
}
mv -f "$filter_tmp" "$OUTPUT"

final_count=$(jq '.archetypes | length' "$OUTPUT")
emit_kv SCOUT_STATUS "$SCOUT_STATUS"
emit_kv SCOUT_MANIFEST "$OUTPUT"
emit_kv SCOUT_ARCHETYPE_COUNT "$final_count"
exit 0
