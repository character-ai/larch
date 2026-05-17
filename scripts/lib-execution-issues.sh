#!/usr/bin/env bash
# Shared execution-issues record helpers. Sourced-only; no top-level main.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"

_lib_warn_line() {
    larch_err "lib-execution-issues: $*" || true
}

sha256_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        sha256sum "$1" | awk '{print $1}'
    fi
}

sha256_stream() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        sha256sum | awk '{print $1}'
    fi
}

normalize_body_for_hash() {
    # Strip leading '### Category' header line, strip leading/trailing blank lines.
    # Internal content (including code fences) is preserved verbatim.
    awk '
        NR == 1 && /^### / { next }
        { lines[++n] = $0 }
        END {
            s = 1; while (s <= n && lines[s] ~ /^[[:space:]]*$/) s++
            e = n; while (e >= s && lines[e] ~ /^[[:space:]]*$/) e--
            for (i = s; i <= e; i++) print lines[i]
        }
    '
}

json_escape_stream_python() {
    # python3 JSON-escape fallback when jq is absent. Handles full string
    # contract (control chars, \r, \b, \f, NUL, surrogate-safe). Returns
    # non-zero if python3 is unavailable; caller routes to a loud failure.
    command -v python3 >/dev/null 2>&1 || return 2
    python3 -c '
import json, sys
sys.stdout.write(json.dumps(sys.stdin.read()))
' || return 1
}

write_execution_issues_records() {
    local input_file=$1 record_file=$2 sha=$3 batch_path=${4:-}
    local step_label=${5:-18} source_label=${6:-execution-issues.md safety-net}
    local current_cat body_file line rc=0 norm_sha rec_sha skip_section body_json
    : > "$record_file"
    if command -v jq >/dev/null 2>&1; then
        body_file=$(mktemp "${TMPDIR:-/tmp}/exec-issue-section.XXXXXX") || return 1
        current_cat="Tool Failures"
        : > "$body_file"
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in
                '### '*)
                    if [ -s "$body_file" ]; then
                        norm_sha=$(normalize_body_for_hash < "$body_file" | sha256_stream 2>/dev/null || true)
                        skip_section=false
                        if [ -n "$norm_sha" ] && [ -n "$batch_path" ] && [ -f "$batch_path" ] && \
                           grep -Fq '"source_sha256":"'"$norm_sha"'"' "$batch_path" 2>/dev/null; then
                            skip_section=true
                        fi
                        if [ "$skip_section" = "false" ]; then
                            rec_sha="${norm_sha:-$sha}"
                            jq -c -Rs \
                                --arg sha "$rec_sha" \
                                --arg cat "$current_cat" \
                                --arg step "$step_label" \
                                --arg source "$source_label" '{
                                phase: "implement", step: $step, category: $cat,
                                source: $source,
                                source_sha256: $sha, body: .
                            }' "$body_file" >> "$record_file" || rc=1
                        fi
                    fi
                    current_cat="${line#'### '}"
                    : > "$body_file"
                    ;;
                *)
                    printf '%s\n' "$line" >> "$body_file"
                    ;;
            esac
        done < "$input_file"
        if [ -s "$body_file" ]; then
            norm_sha=$(normalize_body_for_hash < "$body_file" | sha256_stream 2>/dev/null || true)
            skip_section=false
            if [ -n "$norm_sha" ] && [ -n "$batch_path" ] && [ -f "$batch_path" ] && \
               grep -Fq '"source_sha256":"'"$norm_sha"'"' "$batch_path" 2>/dev/null; then
                skip_section=true
            fi
            if [ "$skip_section" = "false" ]; then
                rec_sha="${norm_sha:-$sha}"
                jq -c -Rs \
                    --arg sha "$rec_sha" \
                    --arg cat "$current_cat" \
                    --arg step "$step_label" \
                    --arg source "$source_label" '{
                    phase: "implement", step: $step, category: $cat,
                    source: $source,
                    source_sha256: $sha, body: .
                }' "$body_file" >> "$record_file" || rc=1
            fi
        fi
        rm -f "$body_file"
        return $rc
    fi
    # No jq: fall back to python3. Refuse to write malformed NDJSON.
    # python3 fallback emits one record for the whole file.
    if ! body_json=$(json_escape_stream_python < "$input_file"); then
        _lib_warn_line '**⚠ 18: execution-issues safety-net needs jq or python3 to compose NDJSON. Neither found. Skipping safety-net flush.**'
        return 1
    fi
    {
        printf '{"phase":"implement","step":"%s","category":"Tool Failures",' "$step_label"
        printf '"source":"%s","source_sha256":"%s","body":%s}\n' "$source_label" "$sha" "$body_json"
    } > "$record_file"
}
