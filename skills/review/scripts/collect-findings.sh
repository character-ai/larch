#!/usr/bin/env bash
# collect-findings.sh — Collect reviewer outputs and write ballot findings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: collect-findings.sh --mode diff|description --findings-file FILE --oos-file FILE [--external-output-files FILE...] [--claude-output-files FILE...] [--timeout SECONDS]"; }

MODE=""
TIMEOUT="1860"
SESSION_ENV_PATH=""
FINDINGS_FILE=""
OOS_FILE=""
EXTERNAL_OUTPUT_FILES=()
CLAUDE_OUTPUT_FILES=()
EXTERNAL_COUNT=0
CLAUDE_COUNT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --external-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do EXTERNAL_OUTPUT_FILES+=("$1"); EXTERNAL_COUNT=$((EXTERNAL_COUNT + 1)); shift; done ;;
        --claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do CLAUDE_OUTPUT_FILES+=("$1"); CLAUDE_COUNT=$((CLAUDE_COUNT + 1)); shift; done ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --oos-file) OOS_FILE="${2:?--oos-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "collect-findings.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$MODE" == "diff" || "$MODE" == "description" ]] || { larch_err "collect-findings.sh: --mode must be diff or description"; exit 2; }
[[ -n "$FINDINGS_FILE" ]] || { larch_err "collect-findings.sh: --findings-file is required"; exit 2; }
[[ -n "$OOS_FILE" ]] || { larch_err "collect-findings.sh: --oos-file is required"; exit 2; }
mkdir -p "$(dirname "$FINDINGS_FILE")" "$(dirname "$OOS_FILE")"
REVIEW_TMPDIR="$(dirname "$FINDINGS_FILE")"

execution_issue_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s' "$LARCH_EXECUTION_ISSUES_LOG"
        return
    fi
    if [[ -n "$SESSION_ENV_PATH" ]]; then
        printf '%s/execution-issues.md' "$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        printf '%s/execution-issues.md' "$IMPLEMENT_TMPDIR"
    else
        printf '%s/execution-issues.md' "$REVIEW_TMPDIR"
    fi
}

append_review_failure() {
    local site="$1" tool="$2" rc="$3" output_file="$4" status_label="${5:-failed}"
    [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]] || return 0
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$(execution_issue_log)" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$rc" \
        --status-label "$status_label" \
        --category "External Reviewer Issues" \
        --output-file "$output_file" \
        --redact >/dev/null 2>&1 || true
}

file_has_no_findings_sentinel() {
    local file="$1"
    [[ -s "$file" ]] || return 1
    if grep -Fxq 'NO_ISSUES_FOUND' "$file"; then
        return 0
    fi
    if command -v jq >/dev/null 2>&1; then
        local _trimmed
        _trimmed=$(awk '
            { lines[++count]=$0 }
            END {
                first=0
                last=0
                for (i = 1; i <= count; i++) {
                    line=lines[i]
                    sub(/^[[:space:]]+/, "", line)
                    sub(/[[:space:]]+$/, "", line)
                    if (line != "") { first=i; break }
                }
                for (i = count; i >= 1; i--) {
                    line=lines[i]
                    sub(/^[[:space:]]+/, "", line)
                    sub(/[[:space:]]+$/, "", line)
                    if (line != "") { last=i; break }
                }
                if (first == 0) { exit }
                for (i = first; i <= last; i++) {
                    line=lines[i]
                    sub(/^[[:space:]]+/, "", line)
                    sub(/[[:space:]]+$/, "", line)
                    print line
                }
            }
        ' "$file" 2>/dev/null)
        jq -e 'type == "object" and .no_issues_found == true' <<<"$_trimmed" >/dev/null 2>&1 && return 0
    fi
    return 1
}

record_claude_non_substantive() {
    local file="$1" label="$2" combined
    {
        printf 'REVIEWER_FILE=%s\n' "$file"
        printf 'TOOL=claude\n'
        printf 'STATUS=NOT_SUBSTANTIVE\n'
        printf 'EXIT_CODE=0\n'
        printf '\n'
    } >> "$collector_results_file"

    combined=$(mktemp "${TMPDIR:-/tmp}/review-claude-non-substantive.XXXXXX") || return 0
    {
        printf 'COLLECTOR_STATUS=NOT_SUBSTANTIVE\n'
        printf 'REVIEWER_FILE=%s\n' "$file"
        printf 'TOOL=claude\n'
        printf 'EXIT_CODE=0\n\n'
        printf -- '--- reviewer output ---\n'
        cat "$file"
        printf '\n'
    } > "$combined"
    larch_err "**⚠ Reviewer ${label}: non-substantive output produced no prose or TSV findings**"
    append_review_failure "review Step 3a" \
        "collect-findings.sh claude NOT_SUBSTANTIVE" \
        0 "$combined" "warning"
    rm -f "$combined"
}

append_non_ok_collector_results_from_file() {
    local collector_results_file="$1" reviewer_file="" tool="" status="" exit_code="" line combined
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            # STATUS=cap_hit is a deliberate slot-skip (reviewer's budget cap;
            # NOT a failure — don't
            # log it as External Reviewer Issues.
            if [[ -n "$reviewer_file" && "$status" != "" && "$status" != "OK" && "$status" != "cap_hit" ]]; then
                combined=$(mktemp "${TMPDIR:-/tmp}/review-collector-failure.XXXXXX")
                {
                    printf 'COLLECTOR_STATUS=%s\n' "$status"
                    printf 'REVIEWER_FILE=%s\n' "$reviewer_file"
                    printf 'TOOL=%s\n' "${tool:-unknown}"
                    printf 'EXIT_CODE=%s\n\n' "${exit_code:-0}"
                    if [[ -f "$reviewer_file" ]]; then
                        printf -- '--- reviewer output ---\n'
                        cat "$reviewer_file"
                        printf '\n'
                    fi
                    if [[ -f "${reviewer_file}.diag" ]]; then
                        printf -- '\n--- diagnostic sidecar ---\n'
                        cat "${reviewer_file}.diag"
                        printf '\n'
                    fi
                } > "$combined"
                append_review_failure "review Step 3a" "collect-agent-results.sh ${tool:-unknown} $status" "${exit_code:-1}" "$combined"
                rm -f "$combined"
            fi
            reviewer_file=""; tool=""; status=""; exit_code=""
            continue
        fi
        case "$line" in
            REVIEWER_FILE=*) reviewer_file="${line#REVIEWER_FILE=}" ;;
            TOOL=*) tool="${line#TOOL=}" ;;
            STATUS=*) status="${line#STATUS=}" ;;
            EXIT_CODE=*) exit_code="${line#EXIT_CODE=}" ;;
        esac
    done < "$collector_results_file"
    # STATUS=cap_hit is a deliberate slot-skip (reviewer's budget cap;
    # NOT a failure.
    if [[ -n "$reviewer_file" && "$status" != "" && "$status" != "OK" && "$status" != "cap_hit" ]]; then
        combined=$(mktemp "${TMPDIR:-/tmp}/review-collector-failure.XXXXXX")
        {
            printf 'COLLECTOR_STATUS=%s\n' "$status"
            printf 'REVIEWER_FILE=%s\n' "$reviewer_file"
            printf 'TOOL=%s\n' "${tool:-unknown}"
            printf 'EXIT_CODE=%s\n\n' "${exit_code:-0}"
            if [[ -f "$reviewer_file" ]]; then
                printf -- '--- reviewer output ---\n'
                cat "$reviewer_file"
                printf '\n'
            fi
            if [[ -f "${reviewer_file}.diag" ]]; then
                printf -- '\n--- diagnostic sidecar ---\n'
                cat "${reviewer_file}.diag"
                printf '\n'
            fi
        } > "$combined"
        append_review_failure "review Step 3a" "collect-agent-results.sh ${tool:-unknown} $status" "${exit_code:-1}" "$combined"
        rm -f "$combined"
    fi
}

collector_results_file="$REVIEW_TMPDIR/collector-results.env"
: > "$collector_results_file"
if [[ "$EXTERNAL_COUNT" -gt 0 ]]; then
    # Pin: collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode
    args=(--timeout "$TIMEOUT" --substantive-validation --validation-mode)
    collector_log="$REVIEW_TMPDIR/collect-agent-results.log"
    set +e
    "$PLUGIN_ROOT/scripts/collect-agent-results.sh" "${args[@]}" "${EXTERNAL_OUTPUT_FILES[@]}" > "$collector_results_file" 2>"$collector_log"
    collector_rc=$?
    set -e
    cat "$collector_results_file" >> "$collector_log"
    if [[ "$collector_rc" -ne 0 ]]; then
        append_review_failure "review Step 3a" "collect-agent-results.sh" "$collector_rc" "$collector_log"
        # Redact stderr replay; the unredacted file is already captured in
        # the verbatim execution-issues entry via --redact above.
        if [[ -x "$PLUGIN_ROOT/scripts/redact-secrets.sh" ]]; then
            "$PLUGIN_ROOT/scripts/redact-secrets.sh" < "$collector_log" | while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done || \
                while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$collector_log"
        else
            while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$collector_log"
        fi
        exit "$collector_rc"
    fi
    append_non_ok_collector_results_from_file "$collector_results_file"
fi

if [[ "$CLAUDE_COUNT" -gt 0 ]]; then
    sentinels=()
    for f in "${CLAUDE_OUTPUT_FILES[@]}"; do sentinels+=("${f}.done"); done
    wait_log="$REVIEW_TMPDIR/wait-for-claude-reviewers.log"
    set +e
    WAIT_FOR_REVIEWERS_POLL_INTERVAL="${WAIT_FOR_REVIEWERS_POLL_INTERVAL:-1}" "$PLUGIN_ROOT/scripts/wait-for-reviewers.sh" --timeout "$TIMEOUT" "${sentinels[@]}" > "$wait_log" 2>&1
    wait_rc=$?
    set -e
    if [[ "$wait_rc" -ne 0 ]]; then
        append_review_failure "review Step 3a" "wait-for-reviewers.sh" "$wait_rc" "$wait_log"
        # Redact stderr replay; the unredacted file is already captured in
        # the verbatim execution-issues entry via --redact above.
        if [[ -x "$PLUGIN_ROOT/scripts/redact-secrets.sh" ]]; then
            "$PLUGIN_ROOT/scripts/redact-secrets.sh" < "$wait_log" | while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done || \
                while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$wait_log"
        else
            while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$wait_log"
        fi
        exit "$wait_rc"
    fi
fi

DIRTY_DETECTED=false
for f in "${EXTERNAL_OUTPUT_FILES[@]+"${EXTERNAL_OUTPUT_FILES[@]}"}" "${CLAUDE_OUTPUT_FILES[@]+"${CLAUDE_OUTPUT_FILES[@]}"}"; do
    sidecar="${f}.dirty-tree"
    if [[ ! -s "$sidecar" ]] || ! grep -Fq 'STATUS=clean' "$sidecar"; then
        DIRTY_DETECTED=true
    fi
done

tmp=$(mktemp "${TMPDIR:-/tmp}/review-findings.XXXXXX") || exit 1
per_tmp=""
trap 'rm -f "$tmp" "${per_tmp:-}"' EXIT

parse_output() {
    local file="$1" label="$2"
    [[ -s "$file" ]] || return 0
    if file_has_no_findings_sentinel "$file"; then
        return 0
    fi
    # In description mode dual-list output: split on ### In-Scope Findings vs ### Out-of-Scope Observations (#659). In diff mode single-list output: preserve entire output when headers absent. Both modes: awk handles dual-section with fail-open. Specialist dual-section format matches description headers. Claude generic produces single-list output; [OUT_OF_SCOPE] prefix routes OOS. Only the known merge-base preamble heading activates skip mode so noncanonical ##/### reviewer headings still fail open instead of silently dropping findings.
    awk -v label="$label" -v mode="$MODE" '
    BEGIN { oos=0; body=""; title=""; skip=0 }
    function flush() {
        if (body != "" && title != "") {
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", body)
            gsub(/\r/, "", body)
            gsub(/\n/, " ", body)
            gsub(/\t/, " ", title)
            prefix=oos ? "[OUT_OF_SCOPE] " : ""
            printf("%s%s\t%s\t%s\n", prefix, title, label, body)
        }
        body=""; title=""
    }
    /^### Out-of-Scope Observations/ { flush(); oos=1; skip=0; next }
    /^### In-Scope Findings/ { flush(); oos=0; skip=0; next }
    /^## Commits since merge-base/ { flush(); skip=1; next }
    skip && (/^###[[:space:]]/ || /^##[[:space:]]/) { skip=0; next }
    skip { next }
    /^[-*] / || /^[0-9]+\./ {
        flush()
        title=$0
        sub(/^[-*][[:space:]]*/, "", title)
        sub(/^[0-9]+\.[[:space:]]*/, "", title)
        body=$0
        next
    }
    NF { body = body "\n" $0 }
    END { flush() }
    ' "$file"
}

# parse_output_tsv: extracts inline TSV records from reviewer responses.
# Inline embedding is now the primary TSV delivery protocol for session-
# constrained reviewers (e.g. Cursor no-file-write sessions); the sidecar
# write is an optional supplement when the session allows file writes.
# Extracts structured records via validate-research-output.sh --structured-
# reviewer-mode, then converts each TSV row to the title\tlabel\tbody format
# expected by the main findings loop.
parse_output_tsv() {
    local file="$1" label="$2" tsv_tmp vrc
    [[ -s "$file" ]] || return 0
    tsv_tmp=$(mktemp "${TMPDIR:-/tmp}/collect-tsv.XXXXXX") || return 1
    set +e
    "$PLUGIN_ROOT/scripts/validate-research-output.sh" \
        --structured-reviewer-mode --write-structured "$tsv_tmp" "$file" \
        >/dev/null 2>&1
    vrc=$?
    set -e
    if [[ "$vrc" -ne 0 || ! -s "$tsv_tmp" ]]; then
        rm -f "$tsv_tmp"
        return 0
    fi
    awk -F '\t' -v label="$label" '
        NR == 1 && $1 == "schema_version" { next }
        NF >= 8 {
            scope=$2; sev=$3; focus=$4; loc=$5; what=$6; scenario=$7; fix=$8
            prefix=(scope == "out_of_scope") ? "[OUT_OF_SCOPE] " : ""
            title=prefix focus ": " loc
            body="[" sev "] " what " " scenario " " fix
            printf "%s\t%s\t%s\n", title, label, body
        }
    ' "$tsv_tmp"
    rm -f "$tsv_tmp"
}

normalize_reviewer_label() {
    local label="$1" stem ext
    case "$label" in
        *.txt) stem="${label%.txt}"; ext=".txt" ;;
        *) stem="$label"; ext="" ;;
    esac
    while [[ "$stem" == *-phase2 || "$stem" == *-phase3 || "$stem" == *-retry ]]; do
        case "$stem" in
            *-phase2) stem="${stem%-phase2}" ;;
            *-phase3) stem="${stem%-phase3}" ;;
            *-retry) stem="${stem%-retry}" ;;
        esac
    done
    printf '%s%s\n' "$stem" "$ext"
}

per_tmp=$(mktemp "${TMPDIR:-/tmp}/review-per-file.XXXXXX") || exit 1
for f in "${EXTERNAL_OUTPUT_FILES[@]+"${EXTERNAL_OUTPUT_FILES[@]}"}"; do
    : > "$per_tmp"
    parse_output_tsv "$f" "$(basename "$f")" > "$per_tmp"
    if [[ ! -s "$per_tmp" ]]; then
        parse_output "$f" "$(basename "$f")" > "$per_tmp"
    fi
    cat "$per_tmp" >> "$tmp"
done

for f in "${CLAUDE_OUTPUT_FILES[@]+"${CLAUDE_OUTPUT_FILES[@]}"}"; do
    : > "$per_tmp"
    parse_output "$f" "$(basename "$f")" > "$per_tmp"
    if [[ ! -s "$per_tmp" ]]; then
        parse_output_tsv "$f" "$(basename "$f")" > "$per_tmp"
    fi
    if [[ ! -s "$per_tmp" && -s "$f" ]] && ! file_has_no_findings_sentinel "$f"; then
        record_claude_non_substantive "$f" "$(basename "$f")"
    fi
    cat "$per_tmp" >> "$tmp"
done

# Preserve duplicate TSV rows (including identical title/label/body) so the
# downstream aggregator can apply merge-time dedup; row-level awk dedup was
# removed in favor of that contract.
cp "$tmp" "$tmp.sorted"
: > "$FINDINGS_FILE"
: > "$OOS_FILE"
count=0
oos_count=0
while IFS=$'\t' read -r title label body || [[ -n "${title:-}" ]]; do
    [[ -n "$title" ]] || continue
    label=$(normalize_reviewer_label "$label")
    # Validate reviewer column: must end in -output.txt (any recognized reviewer filename).
    # A corrupted label (e.g., from tab characters in a finding title shifting TSV columns)
    # would be a prose fragment — skip the row and log a Warning.
    if [[ ! "$label" =~ -output\.txt$ ]]; then
        _bad_label="${label:0:100}"
        "$PLUGIN_ROOT/scripts/append-execution-issue.sh" \
            --log "$(execution_issue_log)" \
            --category Warnings \
            --entry "- **Step 3a — invalid reviewer column**: expected '*-output.txt', got '${_bad_label}' (finding title: '${title:0:80}'). Row skipped." 2>/dev/null || true
        unset _bad_label
        continue
    fi
    count=$((count + 1))
    if [[ "$title" == "[OUT_OF_SCOPE] **"* ]]; then
        oos_body="${title#\[OUT_OF_SCOPE\] \*\*}"
        category="${oos_body%%\*\**}"
        case "$category" in
            code-quality|risk-integration|correctness|architecture|security)
                fileref=""
                if [[ "$title" =~ \[\`([^\`]+)\`\] ]]; then
                    fileref="${BASH_REMATCH[1]}"
                fi
                if [[ -n "$fileref" ]]; then
                    title="[OUT_OF_SCOPE] $category: $fileref"
                else
                    title="[OUT_OF_SCOPE] $category"
                fi
                ;;
        esac
    fi
    {
        printf '### FINDING_%s: %s\n' "$count" "$title"
        printf -- '- **Reviewer**: %s\n' "$label"
        printf -- '- **Concern**: %s\n' "$body"
        printf -- '- **Suggested revision**: Address the concern above.\n\n'
    } >> "$FINDINGS_FILE"
    if [[ "$title" == \[OUT_OF_SCOPE\]* ]]; then
        oos_count=$((oos_count + 1))
        printf '### FINDING_%s: %s\n%s\n\n' "$count" "$title" "$body" >> "$OOS_FILE"
    fi
done < "$tmp.sorted"

emit_kv FINDINGS_COUNT "$count"
emit_kv OOS_COUNT "$oos_count"
emit_kv DIRTY_DETECTED "$DIRTY_DETECTED"
emit_kv COLLECT_OK true
emit_kv COLLECTOR_OUTPUT_FILE "$collector_results_file"
