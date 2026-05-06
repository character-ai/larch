# lib-gemini-tool-drift.sh — Gemini reviewer tool-catalog drift checks.
#
# Sourced by scripts/check-reviewers.sh. No shebang: this is a library, not a
# standalone executable.
#
# shellcheck shell=bash

gemini_tool_checksum() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    else
        return 1
    fi
}

sanitize_gemini_tool_name() {
    printf '%s' "$1" | tr -cd '[:print:]' | head -c 64
}

sanitize_gemini_probe_text() {
    printf '%s' "$1" | tr -cd '[:print:] ' | head -c 200
}

normalize_gemini_tool_names() {
    tr '[:upper:]' '[:lower:]' \
        | awk '/^[a-z][a-z0-9_]*$/ {print}' \
        | sort -u
}

normalize_gemini_tools_from_raw() {
    normalize_gemini_tool_names
}

parse_gemini_policy_deny_list() {
    local policy_file="$1"
    [[ -r "$policy_file" ]] || return 1
    awk '
        /^[[:space:]]*toolName[[:space:]]*=[[:space:]]*\[/ {in_arr=1}
        in_arr {
            has_close = ($0 ~ /\]/)
            line = $0
            gsub(/[\[\]"'\''"]/, "", line)
            sub(/^[[:space:]]*toolName[[:space:]]*=[[:space:]]*/, "", line)
            n = split(line, parts, ",")
            for (i=1; i<=n; i++) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", parts[i])
                if (parts[i] ~ /^[a-z][a-z0-9_]*$/) print tolower(parts[i])
            }
            if (has_close) {in_arr=0}
        }
        END { if (in_arr) exit 1 }
    ' "$policy_file" | sort -u
}

verify_gemini_fixture_checksum() {
    local fixture_file="$1"
    local expected actual
    [[ -r "$fixture_file" ]] || return 1
    expected=$(awk '/^# checksum:[[:space:]]*/ {print $3; exit}' "$fixture_file")
    [[ -n "$expected" ]] || return 1
    actual=$(grep -v '^#' "$fixture_file" | gemini_tool_checksum) || return 1
    [[ "$actual" == "$expected" ]]
}

read_gemini_fixture_tools() {
    local fixture_file="$1"
    grep -v '^#' "$fixture_file" | grep -v '^$' | normalize_gemini_tool_names
}

discover_gemini_tools_raw_from_probe() {
    local probe_output="$1"
    [[ -r "$probe_output" ]] || return 0
    command -v jq >/dev/null 2>&1 || return 0
    jq -r '
        [
            .metadata.tools?,
            .metadata.availableTools?,
            .tools?,
            .availableTools?,
            .toolCatalog?
        ] | flatten | .[]? |
        if type == "string" then .
        elif type == "object" then (.name? // .toolName? // .id? // empty)
        else empty end
    ' "$probe_output" 2>/dev/null \
        | while IFS= read -r tool; do
            tool=$(sanitize_gemini_tool_name "$tool")
            [[ -n "$tool" ]] && printf '%s\n' "$tool"
        done \
        | sort -u
}

discover_gemini_tools_raw_from_slash_command() {
    local output tmp pid watchdog
    # Test seam: harnesses can shorten the discovery watchdog (default 5s)
    # to avoid paying full 5s on every "hung Gemini" stub. Production callers
    # leave it unset and inherit the 5s default. Validated as a positive
    # integer; empty / non-numeric / padded-zero (0, 00, 000, ...) values fall
    # back to 5. The "*[1-9]*" probe rejects padded-zero forms that the
    # initial digit-character check would accept.
    local discovery_timeout="${LARCH_GEMINI_TOOL_DISCOVERY_TIMEOUT:-5}"
    case "$discovery_timeout" in ''|*[!0-9]*) discovery_timeout=5 ;; esac
    case "$discovery_timeout" in *[1-9]*) : ;; *) discovery_timeout=5 ;; esac
    if command -v gtimeout >/dev/null 2>&1; then
        output=$(gtimeout "$discovery_timeout" gemini /tools </dev/null 2>/dev/null) || true
    elif command -v timeout >/dev/null 2>&1; then
        output=$(timeout "$discovery_timeout" gemini /tools </dev/null 2>/dev/null) || true
    else
        tmp=$(mktemp "${TMPDIR:-/tmp}/gemini-tools.XXXXXX") || return 0
        if command -v perl >/dev/null 2>&1; then
            perl -e 'setpgrp(0, 0); exec @ARGV' gemini /tools </dev/null >"$tmp" 2>/dev/null &
        else
            gemini /tools </dev/null >"$tmp" 2>/dev/null &
        fi
        pid=$!
        (
            sleep "$discovery_timeout"
            kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
        ) &
        watchdog=$!
        wait "$pid" 2>/dev/null || true
        kill "$watchdog" 2>/dev/null || true
        wait "$watchdog" 2>/dev/null || true
        output=$(cat "$tmp" 2>/dev/null || true)
        rm -f "$tmp"
    fi
    printf '%s\n' "$output" \
        | sed -E 's/^[[:space:]]*[-*]?[[:space:]]*//; s/[[:space:]].*$//' \
        | while IFS= read -r tool; do
            tool=$(sanitize_gemini_tool_name "$tool")
            [[ -n "$tool" ]] && printf '%s\n' "$tool"
        done \
        | sort -u
}

discover_gemini_tools_raw() {
    local probe_output="$1"
    local live_catalog
    live_catalog=$(discover_gemini_tools_raw_from_probe "$probe_output" || true)
    if [[ -z "$live_catalog" ]]; then
        live_catalog=$(discover_gemini_tools_raw_from_slash_command || true)
    fi
    printf '%s\n' "$live_catalog"
}

gemini_tool_list_contains() {
    local list="$1"
    local needle="$2"
    printf '%s\n' "$list" | grep -qx "$needle"
}

gemini_tool_is_write_style() {
    local tokenized kw
    tokenized=$(gemini_tool_tokenize_for_write_style "$1")
    for kw in write edit delete replace create modify save put post remove; do
        if [[ "$tokenized" =~ (^| )${kw}( |$) ]]; then
            return 0
        fi
    done
    return 1
}

gemini_tool_tokenize_for_write_style() {
    printf '%s' "$1" \
        | sed -E 's/([[:lower:]])([[:upper:]])/\1 \2/g; s/[_\.-]/ /g' \
        | tr '[:upper:]' '[:lower:]' \
        | awk '{$1=$1; print}'
}

write_gemini_drift_artifact() {
    local artifact="$1" deny_list="$2" expected="$3" observed="$4" unknowns="$5" fixture_trusted="$6" live_catalog="$7" write_style_uncovered="$8"
    local tmp
    tmp=$(mktemp "${artifact}.tmp.XXXXXX") || return 1
    {
        echo "==GEMINI-TOOL-DRIFT=="
        if [[ -z "$live_catalog" ]]; then
            echo "status=discovery unavailable; fixture-only check passed"
        elif [[ -z "$unknowns" && -z "$write_style_uncovered" ]]; then
            echo "status=no drift"
        else
            echo "status=drift detected"
        fi
        echo "fixture_trusted=$fixture_trusted"
        echo
        echo "[deny-list]"
        printf '%s\n' "$deny_list"
        echo
        echo "[expected]"
        printf '%s\n' "$expected"
        echo
        echo "[observed]"
        printf '%s\n' "$observed"
        echo
        echo "[unknown]"
        printf '%s\n' "$unknowns"
        echo
        echo "[write-style-uncovered]"
        printf '%s\n' "$write_style_uncovered"
    } > "$tmp" || { rm -f "$tmp"; return 1; }
    mv "$tmp" "$artifact"
}

emit_gemini_tool_drift_warning() {
    local message="$1"
    echo "GEMINI_TOOL_DRIFT_WARNING=$message"
    echo "WARN: gemini-tool-drift: $message" >&2
}

check_gemini_tool_drift() {
    local probe_output="$1"
    local policy_file="${LARCH_TEST_GEMINI_POLICY_PATH:-$SCRIPT_DIR/gemini-reviewer-policy.toml}"
    local fixture_file="${LARCH_TEST_GEMINI_FIXTURE_PATH:-$SCRIPT_DIR/gemini-known-tools.txt}"
    local artifact_dir="${ARTIFACT_DIR:-$PROBE_DIR}"
    local artifact deny_list parser_sample fixture_lines fixture_trusted live_catalog_raw expected observed unknowns warning_unknowns write_style_uncovered strict_tool

    if ! mkdir -p "$artifact_dir" 2>/dev/null; then
        GEMINI_HEALTHY=false
        set_probe_error gemini "gemini-tool-drift: failed to mkdir artifact dir: $(sanitize_gemini_probe_text "$artifact_dir")"
        return
    fi
    artifact="$artifact_dir/gemini-tool-drift.txt"

    if ! deny_list=$(parse_gemini_policy_deny_list "$policy_file") || [[ -z "$deny_list" ]]; then
        GEMINI_HEALTHY=false
        set_probe_error gemini "gemini-tool-drift: policy parser failed for $(sanitize_gemini_probe_text "$policy_file")"
        return
    fi
    for needed in write_file replace edit edit_file delete_file; do
        if ! gemini_tool_list_contains "$deny_list" "$needed"; then
            parser_sample=$(sanitize_gemini_probe_text "$deny_list")
            GEMINI_HEALTHY=false
            set_probe_error gemini "gemini-tool-drift: policy parser produced unexpected output (missing $needed; output: $parser_sample)"
            return
        fi
    done

    fixture_lines=""
    fixture_trusted=true
    if verify_gemini_fixture_checksum "$fixture_file"; then
        fixture_lines=$(read_gemini_fixture_tools "$fixture_file")
    else
        fixture_trusted=false
        emit_gemini_tool_drift_warning "fixture checksum mismatch - fixture untrusted"
    fi

    live_catalog_raw=$(discover_gemini_tools_raw "$probe_output" || true)

    expected=$(printf '%s\n%s\n' "$deny_list" "$fixture_lines" | normalize_gemini_tool_names)
    observed=$(printf '%s\n%s\n' "$live_catalog_raw" "$fixture_lines" | normalize_gemini_tools_from_raw)
    unknowns=$(comm -23 <(printf '%s\n' "$observed") <(printf '%s\n' "$expected") | grep -v '^$' || true)

    warning_unknowns=""
    while IFS= read -r tool; do
        [[ -z "$tool" ]] && continue
        strict_tool=$(printf '%s\n' "$tool" | normalize_gemini_tools_from_raw)
        if [[ -z "$strict_tool" ]] || ! gemini_tool_list_contains "$expected" "$strict_tool"; then
            warning_unknowns="${warning_unknowns}${warning_unknowns:+
}$tool"
        fi
    done <<< "$live_catalog_raw"

    write_style_uncovered=""
    while IFS= read -r tool; do
        [[ -z "$tool" ]] && continue
        if gemini_tool_is_write_style "$tool" && ! gemini_tool_list_contains "$deny_list" "$tool"; then
            write_style_uncovered="${write_style_uncovered}${write_style_uncovered:+
}$tool"
        fi
    done <<< "$(printf '%s\n%s\n' "$live_catalog_raw" "$fixture_lines" | sort -u)"

    if ! write_gemini_drift_artifact "$artifact" "$deny_list" "$expected" "$observed" "$unknowns" "$fixture_trusted" "$live_catalog_raw" "$write_style_uncovered"; then
        GEMINI_HEALTHY=false
        set_probe_error gemini "gemini-tool-drift: failed to write artifact dir: $(sanitize_gemini_probe_text "$artifact_dir")"
        return
    fi
    echo "GEMINI_TOOL_DRIFT_ARTIFACT=$artifact"

    if [[ -n "$warning_unknowns" ]]; then
        while IFS= read -r tool; do
            [[ -z "$tool" ]] && continue
            emit_gemini_tool_drift_warning "unknown tool '$(sanitize_gemini_tool_name "$tool")' not in deny list"
        done <<< "$warning_unknowns"
    fi

    if [[ -n "$write_style_uncovered" ]]; then
        local sanitized_list err
        # shellcheck disable=SC2034 # check-reviewers.sh reads this sourced-library side effect.
        GEMINI_HEALTHY=false
        sanitized_list=$(sanitize_gemini_probe_text "$(printf '%s' "$write_style_uncovered" | tr '\n' ' ')")
        err=$(get_probe_error gemini)
        set_probe_error gemini "${err}${err:+; }gemini-tool-drift: write-style tool(s) [${sanitized_list% }] not in deny list"
    fi
}
