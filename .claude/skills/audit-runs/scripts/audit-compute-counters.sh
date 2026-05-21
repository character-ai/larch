#!/usr/bin/env bash
# audit-compute-counters.sh — Sum scan-result deltas across PRs, add to prior totals.
#
# Reads all audit-scan-run.sh NDJSON outputs from --scan-results-dir,
# plus the prior report's YAML frontmatter block from --prior-frontmatter.
#
# Output KV (stdout): counters with deltas vs prior report.
#
# Usage:
#   audit-compute-counters.sh --scan-results-dir DIR [--prior-frontmatter FILE]

set -euo pipefail

SCAN_RESULTS_DIR=""
PRIOR_FRONTMATTER=""

while [ $# -gt 0 ]; do
    case "$1" in
        --scan-results-dir) SCAN_RESULTS_DIR="$2"; shift 2 ;;
        --prior-frontmatter) PRIOR_FRONTMATTER="$2"; shift 2 ;;
        *)
            printf 'audit-compute-counters.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if [ -z "$SCAN_RESULTS_DIR" ]; then
    printf 'audit-compute-counters.sh: --scan-results-dir is required\n' >&2
    exit 1
fi

if [ ! -d "$SCAN_RESULTS_DIR" ]; then
    printf 'audit-compute-counters.sh: directory not found: %s\n' "$SCAN_RESULTS_DIR" >&2
    exit 1
fi

# ---- Read prior frontmatter ----
prior_exon=0
prior_oos_mangled=0
prior_oos_clean=0
prior_oos_blank=0
prior_ns_retries=0
prior_changelog=0

parse_prior() {
    local key="$1" default="${2:-0}"
    if [ -z "$PRIOR_FRONTMATTER" ] || [ ! -f "$PRIOR_FRONTMATTER" ]; then
        printf '%s' "$default"
        return
    fi
    awk -v key="$key" \
        '/^---$/{f=!f;next} f && index($0,key":"){gsub(/.*:/,""); gsub(/[[:space:]]/,""); print; exit}' \
        "$PRIOR_FRONTMATTER" 2>/dev/null || printf '%s' "$default"
}

prior_exon=$(parse_prior "exon_misclassifications" 0)
prior_oos_mangled=$(parse_prior "oos_categories_mangled" 0)
prior_oos_clean=$(parse_prior "oos_categories_clean" 0)
prior_oos_blank=$(parse_prior "oos_categories_blank" 0)
prior_ns_retries=$(parse_prior "ns_retries_cursor_specialist" 0)
prior_ns_legacy=$(parse_prior "ns_retries_cursor_specialist_launches" 0)
prior_changelog=$(parse_prior "changelog_rebase_conflicts" 0)

# Default to 0 for any non-numeric prior
num_or_zero() { printf '%s' "$1" | grep -oE '^[0-9]+$' || echo 0; }
prior_exon=$(num_or_zero "$prior_exon")
prior_oos_mangled=$(num_or_zero "$prior_oos_mangled")
prior_oos_clean=$(num_or_zero "$prior_oos_clean")
prior_oos_blank=$(num_or_zero "$prior_oos_blank")
prior_ns_retries=$(num_or_zero "$prior_ns_retries")
prior_ns_legacy=$(num_or_zero "$prior_ns_legacy")
if [ "$prior_ns_legacy" -gt "$prior_ns_retries" ]; then
    prior_ns_retries=$prior_ns_legacy
fi
prior_changelog=$(num_or_zero "$prior_changelog")

# ---- Sum deltas from NDJSON files ----
delta_exon=0
delta_oos_mangled=0
delta_oos_clean=0
delta_oos_blank=0
delta_ns_retries=0
delta_changelog=0
category_stats_partial_any=false
scan_files_found=0

for ndjson_file in "$SCAN_RESULTS_DIR"/scan-results-*.ndjson; do
    [ -f "$ndjson_file" ] || continue
    scan_files_found=$((scan_files_found + 1))

    # exon-misclassification count
    val=$(jq -r 'select(.scan=="exon-misclassification") | .count // 0' "$ndjson_file" 2>/dev/null | head -1 || echo 0)
    val=$(num_or_zero "${val:-0}")
    delta_exon=$((delta_exon + val))

    # oos-category-mangle count
    val=$(jq -r 'select(.scan=="oos-category-mangle") | .count // 0' "$ndjson_file" 2>/dev/null | head -1 || echo 0)
    val=$(num_or_zero "${val:-0}")
    delta_oos_mangled=$((delta_oos_mangled + val))

    partial_flag=$(jq -r 'select(.scan=="category-stats") | .partial_data // false' "$ndjson_file" 2>/dev/null | head -1 || echo false)
    partial_detail=$(jq -r 'select(.scan=="category-stats") | .detail // ""' "$ndjson_file" 2>/dev/null | head -1 || echo "")
    if [ "$partial_flag" = "true" ]; then
        category_stats_partial_any=true
    fi
    # Skip clean/blank deltas only when the partial is specifically because
    # review-findings-full.jsonl was missing (all counts are zero placeholders).
    # Other partial_data:true rows (e.g. jq/mangle errors) still carry measured values.
    skip_cs_clean_blank=false
    if [ "$partial_flag" = "true" ] && printf '%s' "$partial_detail" | grep -q "review-findings-full.jsonl not found"; then
        skip_cs_clean_blank=true
    fi
    if [ "$skip_cs_clean_blank" != true ]; then
        val=$(jq -r 'select(.scan=="category-stats") | .canonical // 0' "$ndjson_file" 2>/dev/null | head -1 || echo 0)
        val=$(num_or_zero "${val:-0}")
        delta_oos_clean=$((delta_oos_clean + val))

        val=$(jq -r 'select(.scan=="category-stats") | .oos_blank // 0' "$ndjson_file" 2>/dev/null | head -1 || echo 0)
        val=$(num_or_zero "${val:-0}")
        delta_oos_blank=$((delta_oos_blank + val))
    fi

    # ns-retry-sidecars count
    val=$(jq -r 'select(.scan=="ns-retry-sidecars") | .count // 0' "$ndjson_file" 2>/dev/null | head -1 || echo 0)
    val=$(num_or_zero "${val:-0}")
    delta_ns_retries=$((delta_ns_retries + val))

    # changelog-rebase-conflicts count (from audit-scan-run NDJSON)
    val=$(jq -r 'select(.scan=="changelog-rebase-conflicts") | .count // 0' "$ndjson_file" 2>/dev/null | head -1 || echo 0)
    val=$(num_or_zero "${val:-0}")
    delta_changelog=$((delta_changelog + val))
done

# Compute cumulative totals
total_exon=$((prior_exon + delta_exon))
total_oos_mangled=$((prior_oos_mangled + delta_oos_mangled))
total_oos_clean=$((prior_oos_clean + delta_oos_clean))
total_oos_blank=$((prior_oos_blank + delta_oos_blank))
total_ns_retries=$((prior_ns_retries + delta_ns_retries))
total_changelog=$((prior_changelog + delta_changelog))

printf 'SCAN_FILES_FOUND=%s\n' "$scan_files_found"
printf 'EXON_MISCLASSIFICATIONS=%s\n' "$total_exon"
printf 'EXON_DELTA=%s\n' "$delta_exon"
printf 'OOS_CATEGORIES_MANGLED=%s\n' "$total_oos_mangled"
printf 'OOS_MANGLED_DELTA=%s\n' "$delta_oos_mangled"
printf 'OOS_CATEGORIES_CLEAN=%s\n' "$total_oos_clean"
printf 'OOS_CLEAN_DELTA=%s\n' "$delta_oos_clean"
printf 'OOS_CATEGORIES_BLANK=%s\n' "$total_oos_blank"
printf 'OOS_BLANK_DELTA=%s\n' "$delta_oos_blank"
printf 'NS_RETRIES_CURSOR_SPECIALIST=%s\n' "$total_ns_retries"
printf 'NS_RETRIES_DELTA=%s\n' "$delta_ns_retries"
printf 'CHANGELOG_REBASE_CONFLICTS=%s\n' "$total_changelog"
printf 'CHANGELOG_DELTA=%s\n' "$delta_changelog"
if [ "$category_stats_partial_any" = true ]; then
    printf 'CATEGORY_STATS_PARTIAL=true\n'
else
    printf 'CATEGORY_STATS_PARTIAL=false\n'
fi
