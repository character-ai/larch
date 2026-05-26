#!/usr/bin/env bash
# ci-failed-jobs.sh — classify failed GitHub Actions jobs for local replay.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

RUN_ID=""
REPO=""
OUTPUT_TSV=""

usage() {
    larch_err "Usage: ci-failed-jobs.sh --run-id RUN_ID --repo OWNER/REPO [--output-tsv PATH]"
}

die() {
    larch_err "ci-failed-jobs.sh: $1"
    usage
    exit 2
}

sanitize_list() {
    tr -cd '[:alnum:]_,=:-'
}

job_class() {
    case "$1" in
        lint|lint-mermaid|shellcheck|test-harnesses|agent-lint|agnix|smoke-dialectic|agent-sync)
            printf '%s\n' fixable
            ;;
        gitleaks|trufflehog)
            printf '%s\n' no-local-equivalent
            ;;
        *)
            printf '%s\n' no-local-equivalent
            ;;
    esac
}

reason_token() {
    case "$1" in
        malformed) printf '%s\n' malformed-job-name ;;
        gitleaks|trufflehog) printf '%s\n' history-scan ;;
        *) printf '%s\n' unknown-job-name ;;
    esac
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --run-id) [ "$#" -ge 2 ] || die "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --repo) [ "$#" -ge 2 ] || die "--repo requires a value"; REPO=$2; shift 2 ;;
        --output-tsv) [ "$#" -ge 2 ] || die "--output-tsv requires a value"; OUTPUT_TSV=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
done

[ -n "$RUN_ID" ] || die "--run-id is required"
[ -n "$REPO" ] || die "--repo is required"

tmp_stdout=$(mktemp "${TMPDIR:-/tmp}/ci-failed-jobs.out.XXXXXX")
tmp_stderr=$(mktemp "${TMPDIR:-/tmp}/ci-failed-jobs.err.XXXXXX")
cleanup() {
    rm -f "$tmp_stdout" "$tmp_stderr"
}
trap cleanup EXIT

gh_rc=0
gh run view "$RUN_ID" --repo "$REPO" --json jobs --jq '.jobs[] | select(.conclusion=="failure") | .name' \
    > "$tmp_stdout" 2> "$tmp_stderr" || gh_rc=$?

if [ "$gh_rc" -ne 0 ]; then
    if grep -Fq "is still in progress; logs will be available" "$tmp_stderr" "$tmp_stdout" 2>/dev/null; then
        exit 3
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"
    done < "$tmp_stderr"
    exit 1
fi

if [ -n "$OUTPUT_TSV" ]; then
    mkdir -p "$(dirname "$OUTPUT_TSV")"
    OUTPUT_TSV_TMP="${OUTPUT_TSV}.tmp.$$"
    : > "$OUTPUT_TSV_TMP"
else
    OUTPUT_TSV_TMP=""
fi

count=0
fixable_list=""
unfixable_list=""
matrix_re='^([A-Za-z][A-Za-z0-9_-]*)[[:space:]]+\(([0-9]+)\)$'
matrix_any_re='^([A-Za-z][A-Za-z0-9_-]*)[[:space:]]+\(([^)]*)\)$'
job_re='^[A-Za-z][A-Za-z0-9_-]*$'

while IFS= read -r raw_name || [ -n "$raw_name" ]; do
    raw_name=$(printf '%s' "$raw_name" | sanitize_diagnostic_line)
    [ -n "$raw_name" ] || continue
    count=$((count + 1))

    job_name=$raw_name
    shard=""
    malformed=false

    if [[ "$raw_name" =~ $matrix_re ]]; then
        job_name=${BASH_REMATCH[1]}
        shard=${BASH_REMATCH[2]}
    elif [[ "$raw_name" =~ $matrix_any_re ]]; then
        job_name=${BASH_REMATCH[1]}
        shard=""
    fi

    if ! [[ "$job_name" =~ $job_re ]]; then
        malformed=true
        class=no-local-equivalent
        reason=$(reason_token malformed)
    else
        class=$(job_class "$job_name")
        reason=$(reason_token "$job_name")
    fi

    if [ -n "$OUTPUT_TSV_TMP" ]; then
        printf '%s\t%s\t%s\n' "$job_name" "$shard" "$class" >> "$OUTPUT_TSV_TMP"
    else
        emit "$(printf '%s\t%s\t%s' "$job_name" "$shard" "$class")"
    fi

    token=$job_name
    [ -n "$shard" ] && token="${token}:${shard}"
    if [ "$class" = "fixable" ] && [ "$malformed" = false ]; then
        if [ -n "$fixable_list" ]; then fixable_list="${fixable_list},${token}"; else fixable_list=$token; fi
    else
        tuple="${token}=${reason}"
        if [ -n "$unfixable_list" ]; then unfixable_list="${unfixable_list},${tuple}"; else unfixable_list=$tuple; fi
    fi
done < "$tmp_stdout"

if [ -n "${OUTPUT_TSV_TMP:-}" ]; then
    mv "$OUTPUT_TSV_TMP" "$OUTPUT_TSV"
fi

emit_kv FAILED_JOBS_COUNT "$count"
emit_kv FAILED_JOBS_FIXABLE "$(printf '%s' "$fixable_list" | sanitize_list)"
emit_kv FAILED_JOBS_UNFIXABLE "$(printf '%s' "$unfixable_list" | sanitize_list)"
