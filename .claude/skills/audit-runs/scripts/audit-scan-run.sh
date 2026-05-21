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

if [ ! -d "$RUN_DIR" ]; then
    jq -nc --argjson pr "$PR_NUM" --arg rd "$RUN_DIR" \
        '{scan:"setup",pr:$pr,result:"error",detail:("run-dir not found: "+$rd)}'
    exit 1
fi

if [ ! -f "$SCANS_TSV" ]; then
    jq -nc --argjson pr "$PR_NUM" --arg sp "$SCANS_TSV" \
        '{scan:"setup",pr:$pr,result:"error",detail:("scans-tsv not found: "+$sp)}'
    exit 1
fi

# ---- Helpers ----
emit() { printf '%s\n' "$1"; }

jstr() {
    # Escape a string for embedding in JSON (handles backslash and double-quote)
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# ---- Scan: required-file-presence ----
scan_required_file_presence() {
    if [ -z "$REQUIRED_FILES_TSV" ] || [ ! -f "$REQUIRED_FILES_TSV" ]; then
        emit "{\"scan\":\"required-file-presence\",\"pr\":$PR_NUM,\"result\":\"skip\",\"detail\":\"required-files-tsv not provided\"}"
        return
    fi
    local missing=""
    # Read TSV (skip comment lines and header)
    while IFS=$'\t' read -r rel_path _condition _rest; do
        [ -z "$rel_path" ] && continue
        printf '%s' "$rel_path" | grep -q '^#' && continue
        [ "$rel_path" = "relative_path" ] && continue
        if [ ! -f "$RUN_DIR/$rel_path" ]; then
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
    local count detail
    count=$(jq -r 'select(.category != null) | .category' "$jsonl" 2>/dev/null \
        | grep -cvE '^(code-quality|risk-integration|correctness|architecture|security)$' || true)
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        detail="$count plan-review-phase rows with prose category"
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
    for f in "$RUN_DIR"/round-*/*-ns-retry*.txt; do
        [ -f "$f" ] && count=$((count + 1))
    done
    if [ "$count" -eq 0 ]; then
        emit "{\"scan\":\"ns-retry-sidecars\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
    else
        emit "{\"scan\":\"ns-retry-sidecars\",\"pr\":$PR_NUM,\"result\":\"fail\",\"count\":$count}"
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
        emit "{\"scan\":\"cache-freshness\",\"pr\":$PR_NUM,\"result\":\"fail\",\"run_version\":\"$(jstr "$run_version")\",\"current_version\":\"$(jstr "$CURRENT_VERSION")\",\"detail\":\"run plugin version behind current\"}"
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
    emit "{\"scan\":\"changelog-rebase-conflicts\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":$count}"
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
    canonical_count=$(jq -r 'select((.category|type)=="string" and (.category | test("^(code-quality|risk-integration|correctness|architecture|security)$"))) | .category' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    blank_count=$(jq -r 'select((.category // "") == "") | .category' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    mangled_count=$(jq -r 'select((.category|type)=="string" and (.category != "") and (.category | test("^(code-quality|risk-integration|correctness|architecture|security)$") | not)) | .category' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    oos_blank=$(jq -r 'select((.id // "" | startswith("OOS_")) and ((.category // "") == "")) | .id' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    rej_blank=$(jq -r 'select((.id // "" | startswith("REJ_")) and ((.category // "") == "")) | .id' "$JSONL" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
    emit "{\"scan\":\"category-stats\",\"pr\":$PR_NUM,\"partial_data\":false,\"canonical\":${canonical_count:-0},\"blank\":${blank_count:-0},\"mangled\":${mangled_count:-0},\"oos_blank\":${oos_blank:-0},\"rej_blank\":${rej_blank:-0}}"
else
    emit "{\"scan\":\"category-stats\",\"pr\":$PR_NUM,\"partial_data\":true,\"detail\":\"review-findings-full.jsonl not found\",\"canonical\":0,\"blank\":0,\"mangled\":0,\"oos_blank\":0,\"rej_blank\":0}"
fi

# ---- Cross-cutting metadata ----
MANIFEST="$RUN_DIR/manifest.json"
ended_at_null=false
pr_number_null=false
self_deploying_gap=false
if [ -f "$MANIFEST" ]; then
    ea=$(jq -r '.ended_at // empty' "$MANIFEST" 2>/dev/null || true)
    [ -z "$ea" ] && ended_at_null=true
    pn=$(jq -r '.pr_number // empty' "$MANIFEST" 2>/dev/null || true)
    [ -z "$pn" ] && pr_number_null=true
    if [ -n "$pn" ] && [ "$pn" != "$PR_NUM" ]; then
        self_deploying_gap=true
    fi
fi
emit "{\"scan\":\"cross-cutting\",\"pr\":$PR_NUM,\"ended_at_null\":$ended_at_null,\"pr_number_null\":$pr_number_null,\"self_deploying_gap\":$self_deploying_gap}"
