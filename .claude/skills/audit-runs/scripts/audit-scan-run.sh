#!/usr/bin/env bash
# audit-scan-run.sh — Run all scans from scans.tsv against one run-log directory.
#
# Emits NDJSON (one compact JSON object per scan per line) to stdout.
# Also emits category-stats and cross-cutting metadata objects.
#
# Usage:
#   audit-scan-run.sh --run-dir PATH --pr N \
#     --scans-tsv PATH --required-files-tsv PATH --current-version VER

set -euo pipefail

_audit_scan_run_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.claude/skills/audit-runs/scripts/audit-scan-run-jstr.inc.bash
. "$_audit_scan_run_self_dir/audit-scan-run-jstr.inc.bash"

# Set to 1 when mangled-category jq on review-findings-full.jsonl fails (oos-category-mangle scan).
_audit_scan_mangled_jq_failed=0
# When oos-category-mangle jq succeeds, path to its temp output (mangled rows) for category-stats reuse.
_audit_mangled_jq_cache_file=""

_audit_cleanup_mangled_jq_cache() {
    if [ -n "${_audit_mangled_jq_cache_file:-}" ]; then
        rm -f "$_audit_mangled_jq_cache_file"
        _audit_mangled_jq_cache_file=""
    fi
}
trap '_audit_cleanup_mangled_jq_cache' EXIT

RUN_DIR=""
PR_NUM=""
SCANS_TSV=""
REQUIRED_FILES_TSV=""
CURRENT_VERSION=""

while [ $# -gt 0 ]; do
    case "$1" in
        --run-dir) RUN_DIR="$2"; shift 2 ;;
        --pr) PR_NUM="$2"; shift 2 ;;
        --scans-tsv) SCANS_TSV="$2"; shift 2 ;;
        --required-files-tsv) REQUIRED_FILES_TSV="$2"; shift 2 ;;
        --current-version) CURRENT_VERSION="$2"; shift 2 ;;
        *)
            printf 'audit-scan-run.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

for arg in RUN_DIR PR_NUM SCANS_TSV; do
    eval "val=\$$arg"
    if [ -z "$val" ]; then
        printf 'audit-scan-run.sh: --%s is required\n' "$(printf '%s' "$arg" | tr '_' '-' | tr '[:upper:]' '[:lower:]')" >&2
        exit 1
    fi
done

case "$PR_NUM" in
    *[!0-9]*|'')
        jq -nc --arg bad "$PR_NUM" \
            '{scan:"audit-scan-run-args",pr:null,result:"error",detail:("--pr must be a non-empty decimal integer: " + $bad)}'
        exit 1
        ;;
esac

if [ ! -d "$RUN_DIR" ]; then
    jq -nc --argjson pr "$PR_NUM" --arg rd "$RUN_DIR" \
        '{scan:"run-dir-missing",pr:$pr,"incomplete":true,result:"error",detail:("run-dir not found: "+$rd)}'
    exit 1
fi

if [ ! -f "$SCANS_TSV" ]; then
    jq -nc --argjson pr "$PR_NUM" --arg sp "$SCANS_TSV" \
        '{scan:"scans-registry",pr:$pr,result:"error",detail:("scans-tsv not found: "+$sp)}'
    exit 1
fi

# ---- Helpers ----
emit() { printf '%s\n' "$1"; }

# Map a raw NS_RETRY_REASON value from .meta to a JSON-safe audit token (unknown → UNKNOWN).
_audit_normalize_ns_retry_reason_token() {
    local raw="$1"
    case "$raw" in
        NO_ISSUES_FOUND_TOO_THIN|OUTPUT_EMPTY|JSON_PARSE_FAIL|UNKNOWN) printf '%s' "$raw" ;;
        *) printf 'UNKNOWN' ;;
    esac
}

# ---- Scan: required-file-presence ----
scan_required_file_presence() {
    if [ -z "$REQUIRED_FILES_TSV" ] || [ ! -f "$REQUIRED_FILES_TSV" ]; then
        emit "{\"scan\":\"required-file-presence\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"required-files-tsv not provided\"}"
        return
    fi
    local missing="" mf="$RUN_DIR/manifest.json"
    local steps_ran_obj="{}"
    if [ -f "$mf" ]; then
        steps_ran_obj=$(jq -c '.steps_ran // {}' "$mf" 2>/dev/null || echo "{}")
    fi

    _rf_has_file() { [ -f "$RUN_DIR/$1" ]; }

    # _rf_steps_ran_false: return 0 (true) when manifest explicitly records
    # that the step did NOT run; otherwise return 1 so heuristics can decide.
    _rf_steps_ran_false() {
        jq -ne --arg c "$1" --argjson sr "$steps_ran_obj" '($sr[$c] == false)' >/dev/null 2>&1
    }

    _rf_condition_met() {
        local c="$1"
        case "$c" in
            always)
                return 0
                ;;
            step5)
                _rf_steps_ran_false step5 && return 1
                _rf_has_file code-review-tally.json || _rf_has_file review-findings-full.jsonl || _rf_condition_met step7a
                ;;
            step7a)
                _rf_steps_ran_false step7a && return 1
                _rf_has_file token-report.json || _rf_has_file timing-report.json || _rf_has_file execution-issues.ndjson || _rf_has_file session-transcript.jsonl || _rf_condition_met step8
                ;;
            step8)
                _rf_steps_ran_false step8 && return 1
                _rf_has_file version-bump-reasoning.md || _rf_has_file final-summary.md || _RF_STEP9A1_MODE=chain _rf_condition_met step9a1
                ;;
            step9a1)
                _rf_steps_ran_false step9a1 && return 1
                # Direct required-file rows: default to "step ran" unless manifest says false.
                # When invoked from step8's chain (_RF_STEP9A1_MODE=chain), keep the file
                # heuristics so step8 does not widen solely from an empty run directory.
                if [ "${_RF_STEP9A1_MODE:-}" = chain ]; then
                    _rf_has_file run-statistics.md || _rf_has_file oos-issues.ndjson
                else
                    return 0
                fi
                ;;
            exn-agg-validate-fail)
                [ -f "$RUN_DIR/execution-issues.ndjson" ] && grep -Fq 'merged output failed validation' "$RUN_DIR/execution-issues.ndjson" 2>/dev/null
                ;;
            exn-agg-dispatch-fail)
                [ -f "$RUN_DIR/execution-issues.ndjson" ] && {
                    grep -Fq 'dispatch-with-waterfall exited non-zero' "$RUN_DIR/execution-issues.ndjson" 2>/dev/null ||
                        grep -Fq 'DISPATCH_OK=false' "$RUN_DIR/execution-issues.ndjson" 2>/dev/null
                }
                ;;
            *)
                return 1
                ;;
        esac
    }

    local missing_piece found_glob
    # Read TSV (skip comment lines and header)
    while IFS=$'\t' read -r rel_path req_condition _rest; do
        [ -z "$rel_path" ] && continue
        printf '%s' "$rel_path" | grep -q '^#' && continue
        [ "$rel_path" = "relative_path" ] && continue
        case "$req_condition" in
            always | step5 | step7a | step8 | step9a1 | exn-agg-validate-fail | exn-agg-dispatch-fail) ;;
            *)
                emit "{\"scan\":\"required-file-presence\",\"pr\":$PR_NUM,\"result\":\"error\",\"detail\":\"unsupported required-files condition (registry drift): $(jstr "$req_condition")\"}"
                exit 1
                ;;
        esac
        # Reject absolute paths and ".." segments (path escape / out-of-subtree probes)
        if [ "${rel_path#/}" != "$rel_path" ] || printf '%s' "$rel_path" | grep -qF '..'; then
            local invalid_detail
            invalid_detail=$(jstr "$rel_path (invalid path)")
            if [ -z "$missing" ]; then
                missing="\"$invalid_detail\""
            else
                missing="$missing,\"$invalid_detail\""
            fi
            continue
        fi
        _rf_condition_met "$req_condition" || continue
        missing_piece=1
        if printf '%s' "$rel_path" | grep -q '\*'; then
            found_glob=0
            shopt -s nullglob
            for _gf in "$RUN_DIR"/$rel_path; do
                if [ -f "$_gf" ]; then
                    found_glob=1
                    break
                fi
            done
            shopt -u nullglob
            [ "$found_glob" -eq 1 ] && missing_piece=0
        elif [ -f "$RUN_DIR/$rel_path" ]; then
            missing_piece=0
        fi
        if [ "$missing_piece" -eq 1 ]; then
            if [ -z "$missing" ]; then
                missing="\"$(jstr "$rel_path")\""
            else
                missing="$missing,\"$(jstr "$rel_path")\""
            fi
        fi
    done < "$REQUIRED_FILES_TSV"

    if [ -z "$missing" ]; then
        emit "{\"scan\":\"required-file-presence\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        emit "{\"scan\":\"required-file-presence\",\"pr\":$PR_NUM,\"result\":\"fail\",\"missing\":[$missing]}"
    fi
}

# ---- Scan: exon-misclassification ----
scan_exon_misclassification() {
    local count=0
    for f in "$RUN_DIR"/round-*/voting-tally.md; do
        [ -f "$f" ] || continue
        local n
        n=$(grep -cE '\| FINDING_.* \| 0 \| 0 \| [1-9][0-9]* \|.*\| rejected \|' "$f" 2>/dev/null || true)
        count=$((count + n))
    done
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"exon-misclassification\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        emit "{\"scan\":\"exon-misclassification\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count}"
    fi
}

# ---- Scan: oos-category-mangle ----
scan_oos_category_mangle() {
    local jsonl="$RUN_DIR/review-findings-full.jsonl"
    if [ ! -f "$jsonl" ]; then
        emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"review-findings-full.jsonl not found\"}"
        return
    fi
    local count detail jq_out jq_err
    jq_out=$(mktemp "${TMPDIR:-/tmp}/audit-scan-oos-out-XXXXXX")
    jq_err=$(mktemp "${TMPDIR:-/tmp}/audit-scan-oos-err-XXXXXX")
    if jq -r -f "$_audit_scan_run_self_dir/audit-scan-run-mangled-rows.jq" "$jsonl" >"$jq_out" 2>"$jq_err"; then
        count=$(wc -l <"$jq_out" | tr -d '[:space:]')
        rm -f "$jq_err"
        _audit_mangled_jq_cache_file="$jq_out"
    else
        _audit_scan_mangled_jq_failed=1
        _audit_mangled_jq_cache_file=""
        detail=$(head -c 400 "$jq_err" 2>/dev/null | tr -d '\r' || true)
        rm -f "$jq_out" "$jq_err"
        emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"error\",\"detail\":\"$(jstr "jq failed (oos-category-mangle): ${detail:-unknown}")\"}"
        return
    fi
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        detail="$count plan-review accepted rows with prose category (not canonical)"
        emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count,\"detail\":\"$(jstr "$detail")\"}"
    fi
}

# ---- Scan: rej-category-blank ----
scan_rej_category_blank() {
    local jsonl="$RUN_DIR/review-findings-full.jsonl"
    if [ ! -f "$jsonl" ]; then
        emit "{\"scan\":\"rej-category-blank\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"review-findings-full.jsonl not found\"}"
        return
    fi
    local count
    count=$(jq -r 'select(
        (.id // "" | type == "string" and startswith("REJ_")) and
        ((.category // "") == "") and
        ((.prose_body // "") | type == "string") and
        ((.prose_body // "") | test("###[[:space:]]+FINDING_[0-9A-Za-z_]+:[[:space:]]*(code-quality|risk-integration|correctness|architecture|security)(:|\\n|$)"))
    ) | .id' "$jsonl" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"rej-category-blank\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        emit "{\"scan\":\"rej-category-blank\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count,\"rej_blank_with_cat_in_prose\":$count}"
    fi
}

# ---- Scan: ns-retry-sidecars ----
scan_ns_retry_sidecars() {
    local count=0
    local reasons_json
    local _reasons_list=""
    local reason meta raw_line
    for f in "$RUN_DIR"/round-*/*-ns-retry*.txt; do
        [ -f "$f" ] || continue
        count=$((count + 1))
        meta="${f}.meta"
        reason=""
        if [ -f "$meta" ]; then
            # Last matching line wins (collector may append); strip fixed prefix so '=' in values is preserved.
            raw_line=$(grep -E '^NS_RETRY_REASON=' "$meta" 2>/dev/null | tail -n 1 || true)
            reason="${raw_line#NS_RETRY_REASON=}"
            reason=$(printf '%s' "$reason" | tr -d '\r')
        fi
        [ -z "$reason" ] && reason="UNKNOWN"
        reason=$(_audit_normalize_ns_retry_reason_token "$reason")
        _reasons_list="${_reasons_list}${reason}"$'\n'
    done
    # Build reasons JSON via jq so keys/values are always JSON-safe and keys sort for stable NDJSON.
    reasons_json=$(printf '%s' "$_reasons_list" | jq -Rs '
        split("\n")
        | map(select(length > 0))
        | reduce .[] as $t ({}; .[$t] += 1)
        | to_entries
        | sort_by(.key)
        | from_entries
    ' -c 2>/dev/null || printf '{}')
    [ -z "$reasons_json" ] && reasons_json="{}"
    local reasons_detail_kv=""
    # If jq failed (or produced an empty object) while files were counted, roll up so count matches reasons.
    if [ "$count" -gt 0 ] && [ "$reasons_json" = "{}" ]; then
        reasons_json=$(jq -nc --argjson n "$count" '{"UNKNOWN":$n}' 2>/dev/null || true)
        [ -z "$reasons_json" ] && reasons_json=$(printf '{"UNKNOWN":%s}' "$count")
        reasons_detail_kv=",\"reasons_detail\":\"$(jstr 'reasons histogram unavailable (jq failed or empty output); rolled up to UNKNOWN')\""
    fi
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"ns-retry-sidecars\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0,\"reasons\":{}}"
    else
        emit "{\"scan\":\"ns-retry-sidecars\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count,\"reasons\":$reasons_json$reasons_detail_kv}"
    fi
}

# ---- Scan: codex-round1-adherence ----
scan_codex_round1_adherence() {
    local found=0
    for f in "$RUN_DIR"/round-*/panel-manifest.ndjson; do
        [ -f "$f" ] || continue
        round_dir=$(dirname "$f")
        round_num=$(basename "$round_dir" | grep -oE '[0-9]+$' || echo 0)
        if [ "$round_num" -ge 2 ] 2>/dev/null; then
            if grep -q '"tool":"codex"' "$f" 2>/dev/null || grep -q '"tool": "codex"' "$f" 2>/dev/null; then
                found=$((found + 1))
            fi
        fi
    done
    if [ "$found" -eq 0 ]; then
        emit "{\"scan\":\"codex-round1-adherence\",\"pr\":$PR_NUM,\"result\":\"pass\"}"
    else
        emit "{\"scan\":\"codex-round1-adherence\",\"pr\":$PR_NUM,\"result\":\"fail\",\"rounds_with_codex\":$found}"
    fi
}

# ---- Scan: codex-generalist-waste ----
scan_codex_generalist_waste() {
    local f="$RUN_DIR/round-1/codex-generalist-output.txt"
    if [ ! -f "$f" ]; then
        emit "{\"scan\":\"codex-generalist-waste\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"no round-1/codex-generalist-output.txt\"}"
        return
    fi
    local content
    content=$(head -n 1 "$f" 2>/dev/null | tr -d '\r' | sed 's/[[:space:]]*$//' || true)
    if [ "$content" = "NO_ISSUES_FOUND" ]; then
        # Check timing
        local timing_f="$RUN_DIR/timing-report.json"
        local duration=0
        if [ -f "$timing_f" ]; then
            duration=$(jq '[.steps[]? | select(.name | test("round-1.*codex")) | .duration_s // 0] | add // 0' "$timing_f" 2>/dev/null || echo 0)
        fi
        if [ "${duration:-0}" -gt 120 ] 2>/dev/null; then
            emit "{\"scan\":\"codex-generalist-waste\",\"pr\":$PR_NUM,\"result\":\"fail\",\"detail\":\"NO_ISSUES_FOUND but took ${duration}s\"}"
        else
            emit "{\"scan\":\"codex-generalist-waste\",\"pr\":$PR_NUM,\"result\":\"pass\"}"
        fi
    else
        emit "{\"scan\":\"codex-generalist-waste\",\"pr\":$PR_NUM,\"result\":\"pass\"}"
    fi
}

# ---- Scan: execution-issues-categories ----
scan_execution_issues_categories() {
    local ndjson="$RUN_DIR/execution-issues.ndjson"
    if [ ! -f "$ndjson" ]; then
        emit "{\"scan\":\"execution-issues-categories\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"execution-issues.ndjson not found\"}"
        return
    fi
    local non_warnings warnings
    non_warnings=$(jq -r 'select((.category|type)=="string" and .category != "Warnings") | .category' "$ndjson" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    warnings=$(jq -r 'select(.category == "Warnings") | .category' "$ndjson" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    if [ "$non_warnings" -eq 0 ]; then
        emit "{\"scan\":\"execution-issues-categories\",\"pr\":$PR_NUM,\"result\":\"pass\",\"non_warnings\":0,\"warnings\":$warnings}"
    else
        emit "{\"scan\":\"execution-issues-categories\",\"pr\":$PR_NUM,\"result\":\"fail\",\"non_warnings\":$non_warnings,\"warnings\":$warnings}"
    fi
}

# ---- Scan: cache-freshness ----
scan_cache_freshness() {
    local manifest="$RUN_DIR/manifest.json"
    if [ ! -f "$manifest" ]; then
        emit "{\"scan\":\"cache-freshness\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"manifest.json not found\"}"
        return
    fi
    local run_version
    run_version=$(jq -r '.larch_version // empty' "$manifest" 2>/dev/null || true)
    if [ -z "${CURRENT_VERSION:-}" ] || [ "$CURRENT_VERSION" = "unknown" ]; then
        emit "{\"scan\":\"cache-freshness\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"current-version unset\",\"run_version\":\"$(jstr "$run_version")\"}"
        return
    fi
    if [ -z "$run_version" ]; then
        emit "{\"scan\":\"cache-freshness\",\"pr\":$PR_NUM,\"result\":\"fail\",\"detail\":\"manifest larch_version empty\",\"current_version\":\"$(jstr "$CURRENT_VERSION")\"}"
        return
    fi
    local older
    older=$(printf '%s\n' "$run_version" "$CURRENT_VERSION" | sort -V | head -1)
    if [ "$older" = "$run_version" ] && [ "$run_version" != "$CURRENT_VERSION" ]; then
        emit "{\"scan\":\"cache-freshness\",\"pr\":$PR_NUM,\"result\":\"informational\",\"run_version\":\"$(jstr "$run_version")\",\"current_version\":\"$(jstr "$CURRENT_VERSION")\",\"detail\":\"run plugin version behind current\"}"
    else
        emit "{\"scan\":\"cache-freshness\",\"pr\":$PR_NUM,\"result\":\"pass\",\"run_version\":\"$(jstr "$run_version")\",\"current_version\":\"$(jstr "$CURRENT_VERSION")\"}"
    fi
}

# ---- Scan: coder-tool ----
scan_coder_tool() {
    local by_round="{}"
    for f in "$RUN_DIR"/round-*/coder.env; do
        [ -f "$f" ] || continue
        round_dir=$(dirname "$f")
        round_name=$(basename "$round_dir")
        tool=$(grep -oE 'CODER_TOOL=[^[:space:]]+' "$f" 2>/dev/null | grep -oE '[^=]+$' || true)
        if [ -n "$tool" ]; then
            by_round=$(printf '%s' "$by_round" | jq --arg k "$round_name" --arg v "$tool" '. + {($k): $v}' 2>/dev/null || true)
        fi
    done
    emit "{\"scan\":\"coder-tool\",\"pr\":$PR_NUM,\"result\":\"pass\",\"by_round\":$by_round}"
}

# ---- Scan: trailing-content-no-issues-found ----
scan_trailing_content_no_issues_found() {
    local count=0
    for f in "$RUN_DIR"/round-*/*-first-pass.txt; do
        [ -f "$f" ] || continue
        local first
        first=$(head -n 1 "$f" 2>/dev/null | tr -d '\r' | sed 's/[[:space:]]*$//' || true)
        [ "$first" = "NO_ISSUES_FOUND" ] || continue
        if tail -n +2 "$f" 2>/dev/null | grep -qE '[^[:space:]]' 2>/dev/null; then
            count=$((count + 1))
        fi
    done
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"trailing-content-no-issues-found\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        emit "{\"scan\":\"trailing-content-no-issues-found\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count}"
    fi
}

# ---- Scan: changelog-rebase-conflicts (heuristic; feeds CHANGELOG_DELTA) ----
scan_changelog_rebase_conflicts() {
    local f="$RUN_DIR/execution-issues.ndjson"
    if [ ! -f "$f" ]; then
        emit "{\"scan\":\"changelog-rebase-conflicts\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"execution-issues.ndjson not found\"}"
        return
    fi
    local count
    count=$(jq -s '[.[] | select(type == "object") | select(
        ((.body // "") | ascii_downcase | contains("changelog"))
        and (
            ((.body // "") | ascii_downcase | contains("rebase"))
            or ((.body // "") | ascii_downcase | contains("conflict"))
        )
    )] | length' "$f" 2>/dev/null || echo 0)
    if [ "${count:-0}" -eq 0 ]; then
        emit "{\"scan\":\"changelog-rebase-conflicts\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        emit "{\"scan\":\"changelog-rebase-conflicts\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count}"
    fi
}

# ---- Run all scans in registry order ----
while IFS=$'\t' read -r scan_name _scan_type _rest; do
    [ -z "$scan_name" ] && continue
    printf '%s' "$scan_name" | grep -q '^#' && continue
    [ "$scan_name" = "name" ] && continue  # header

    case "$scan_name" in
        required-file-presence)     scan_required_file_presence ;;
        exon-misclassification)     scan_exon_misclassification ;;
        oos-category-mangle)        scan_oos_category_mangle ;;
        rej-category-blank)         scan_rej_category_blank ;;
        ns-retry-sidecars)          scan_ns_retry_sidecars ;;
        codex-round1-adherence)     scan_codex_round1_adherence ;;
        codex-generalist-waste)     scan_codex_generalist_waste ;;
        execution-issues-categories) scan_execution_issues_categories ;;
        cache-freshness)            scan_cache_freshness ;;
        changelog-rebase-conflicts) scan_changelog_rebase_conflicts ;;
        coder-tool)                 scan_coder_tool ;;
        trailing-content-no-issues-found) scan_trailing_content_no_issues_found ;;
        *)
            emit "{\"scan\":\"$(jstr "$scan_name")\",\"pr\":$PR_NUM,\"result\":\"error\",\"detail\":\"unknown scan name in scans.tsv (registry drift vs audit-scan-run.sh)\"}"
            exit 1
            ;;
    esac
done < "$SCANS_TSV"

# ---- Category stats (summary object) ----
JSONL="$RUN_DIR/review-findings-full.jsonl"
if [ -f "$JSONL" ]; then
    category_stats_partial=false
    category_stats_detail=""
    canonical_count=$(jq -r 'select((.category|type)=="string" and (.category | test("^(code-quality|risk-integration|correctness|architecture|security)$"))) | .category' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    blank_count=$(jq -r 'select((.category // "") == "") | .category' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    mangled_count=0
    if [ "$_audit_scan_mangled_jq_failed" -eq 1 ]; then
        category_stats_partial=true
        category_stats_detail="mangled-category aggregate unavailable after oos-category-mangle jq error"
    elif [ -n "${_audit_mangled_jq_cache_file:-}" ] && [ -f "$_audit_mangled_jq_cache_file" ]; then
        mangled_count=$(wc -l <"$_audit_mangled_jq_cache_file" | tr -d '[:space:]')
        rm -f "$_audit_mangled_jq_cache_file"
        _audit_mangled_jq_cache_file=""
    else
        mangled_jq_out=$(mktemp "${TMPDIR:-/tmp}/audit-scan-cs-mangled-out-XXXXXX")
        mangled_jq_err=$(mktemp "${TMPDIR:-/tmp}/audit-scan-cs-mangled-err-XXXXXX")
        if jq -r -f "$_audit_scan_run_self_dir/audit-scan-run-mangled-rows.jq" "$JSONL" >"$mangled_jq_out" 2>"$mangled_jq_err"; then
            mangled_count=$(wc -l <"$mangled_jq_out" | tr -d '[:space:]')
        else
            category_stats_partial=true
            mj_err=$(head -c 400 "$mangled_jq_err" 2>/dev/null | tr -d '\r' || true)
            category_stats_detail="jq failed (category-stats mangled): ${mj_err:-unknown}"
        fi
        rm -f "$mangled_jq_out" "$mangled_jq_err"
    fi
    oos_blank=$(jq -r 'select((.id // "" | startswith("OOS_")) and ((.category // "") == "")) | .id' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    rej_blank=$(jq -r 'select((.id // "" | startswith("REJ_")) and ((.category // "") == "")) | .id' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    if [ "$category_stats_partial" = true ]; then
        if [ -n "$category_stats_detail" ]; then
            emit "{\"scan\":\"category-stats\",\"pr\":$PR_NUM,\"partial_data\":true,\"detail\":\"$(jstr "$category_stats_detail")\",\"canonical\":${canonical_count:-0},\"blank\":${blank_count:-0},\"mangled\":${mangled_count:-0},\"oos_blank\":${oos_blank:-0},\"rej_blank\":${rej_blank:-0}}"
        else
            emit "{\"scan\":\"category-stats\",\"pr\":$PR_NUM,\"partial_data\":true,\"canonical\":${canonical_count:-0},\"blank\":${blank_count:-0},\"mangled\":${mangled_count:-0},\"oos_blank\":${oos_blank:-0},\"rej_blank\":${rej_blank:-0}}"
        fi
    else
        emit "{\"scan\":\"category-stats\",\"pr\":$PR_NUM,\"partial_data\":false,\"canonical\":${canonical_count:-0},\"blank\":${blank_count:-0},\"mangled\":${mangled_count:-0},\"oos_blank\":${oos_blank:-0},\"rej_blank\":${rej_blank:-0}}"
    fi
else
    emit "{\"scan\":\"category-stats\",\"pr\":$PR_NUM,\"partial_data\":true,\"partial_reason\":\"missing_review_findings_jsonl\",\"detail\":\"review-findings-full.jsonl not found\",\"canonical\":0,\"blank\":0,\"mangled\":0,\"oos_blank\":0,\"rej_blank\":0}"
fi

# ---- Cross-cutting metadata ----
MANIFEST="$RUN_DIR/manifest.json"
ended_at_null=false
pr_number_null=false
self_deploying_gap=false
if [ -f "$MANIFEST" ]; then
    # schema_version >= 2 omits pr_number/ended_at in normal manifests; only treat
    # *_null as integrity signals when the key exists (legacy v1 uses empty-as-null).
    read -r ended_at_null pr_number_null self_deploying_gap <<EOF
$(jq -r --argjson audited_pr "$PR_NUM" '
  def is_v2: ((.schema_version | type) == "number") and .schema_version >= 2;
  (if is_v2 then
     (has("ended_at") and (.ended_at == null or .ended_at == ""))
   else
     ((.ended_at // "") | tostring) == ""
   end) as $ea
  | (if is_v2 then
       (has("pr_number") and (.pr_number == null))
     else
       (.pr_number == null) or ((.pr_number | tostring) == "")
     end) as $pn
  | ((.pr_number != null) and ((.pr_number | tostring) != "")
     and ((.pr_number | tostring) != ($audited_pr | tostring))) as $gap
  | [ (if $ea then "true" else "false" end),
      (if $pn then "true" else "false" end),
      (if $gap then "true" else "false" end) ]
  | @tsv
' "$MANIFEST" 2>/dev/null || printf 'false\tfalse\tfalse\n')
EOF
fi
ended_json=false
pr_number_json=false
gap_json=false
[ "$ended_at_null" = true ] && ended_json=true
[ "$pr_number_null" = true ] && pr_number_json=true
[ "$self_deploying_gap" = true ] && gap_json=true
emit "$(jq -nc \
    --argjson pr "$PR_NUM" \
    --argjson ended "$ended_json" \
    --argjson pr_null "$pr_number_json" \
    --argjson gap "$gap_json" \
    '{scan:"cross-cutting",pr:$pr,ended_at_null:$ended,pr_number_null:$pr_null,manifest_pr_number_mismatch_with_audited_pr:$gap,self_deploying_gap:$gap}')"
