#!/usr/bin/env bash
# file-failure-report-cross-repo.sh — exact-signature issue filing and dedup for stall reports.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
STALL_RECOVERY_CLI=(python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery)

usage() {
    echo "file-failure-report-cross-repo.sh: usage: $0 --repo OWNER/REPO --body-file PATH --title TITLE [--mutation-context PATH --run-id ID] [--dedup-only] [--attempts-file PATH] [--escalation-ledger-file PATH] [--root-cause-file PATH] [--sensitive-corpus-file PATH] [--publication-tier tier-a|tier-b] [--dry-run]" >&2
}

status_refused() { emit_kv FILE_FAILURE_REPORT_STATUS mutation-refused; emit_kv FILE_FAILURE_REPORT_FALLBACK_REASON "unauthorized-mutation:$1"; }

check_mutation_auth() {
    local context_file=$1 run_id=$2
    if [ "${LARCH_ISSUE_MUTATION_DENY:-}" = "true" ]; then
        status_refused test-denied
        return 1
    fi
    if [ -z "$context_file" ]; then
        status_refused no-context-file
        return 1
    fi
    if [ -z "$run_id" ]; then
        status_refused missing-run-id
        return 1
    fi
    if ! python3 "$PLUGIN_ROOT/python/cli.py" session check-live-mutation-auth --context-file "$context_file" --run-id "$run_id" --trusted-root "$(dirname "$context_file")" >/dev/null 2>&1; then
        status_refused invalid-context-file
        return 1
    fi
    return 0
}

emit_kv() { printf '%s=%s\n' "$1" "$2"; }
status_fallback() { emit_kv FILE_FAILURE_REPORT_STATUS fallback-print-required; emit_kv FILE_FAILURE_REPORT_FALLBACK_REASON "$1"; }
status_fail_open() { emit_kv FILE_FAILURE_REPORT_STATUS lookup-failed-open; emit_kv FILE_FAILURE_REPORT_FALLBACK_REASON "$1"; }

redact_stderr_file() {
    local file=$1
    [ -s "$file" ] || return 0
    python3 "$PLUGIN_ROOT/python/cli.py" redact secrets <"$file" >&2 || echo "file-failure-report-cross-repo.sh: stderr redaction failed" >&2
}

valid_repo() {
    printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'
}

validate_read_file() {
    local path=$1 label=$2
    case "$path" in "") echo "file-failure-report-cross-repo.sh: $label is required" >&2; return 1 ;; esac
    [ -e "$path" ] || { echo "file-failure-report-cross-repo.sh: $label missing" >&2; return 1; }
    [ -f "$path" ] || { echo "file-failure-report-cross-repo.sh: $label must be regular" >&2; return 1; }
    [ ! -L "$path" ] || { echo "file-failure-report-cross-repo.sh: $label must not be a symlink" >&2; return 1; }
    [ -r "$path" ] || { echo "file-failure-report-cross-repo.sh: $label must be readable" >&2; return 1; }
    return 0
}

extract_marker() {
    local file=$1
    LC_ALL=C grep -Eo '<!-- larch-stall:signature=[0-9a-f]{64} -->' "$file" | head -n 1 | sed 's/^<!-- larch-stall:signature=//; s/ -->$//'
}

normalize_issue_url() {
    awk '
        match($0, /https:\/\/github[.]com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/issues\/[0-9]+/) { print substr($0, RSTART, RLENGTH); exit }
    '
}

comment_url_from_json() {
    python3 -c 'import json,re,sys; data=json.load(sys.stdin); url=data.get("html_url", ""); print(url if isinstance(url, str) and re.fullmatch(r"https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[0-9]+#issuecomment-[0-9]+", url) else "")' 2>/dev/null || true
}

lookup_open_issue() {
    local repo=$1 marker=$2 out=$3 err=$4
    if ! gh api --paginate --jq '.[] | select(.pull_request|not) | {number: .number, body: (.body // "")} | @json' "repos/$repo/issues?state=open&per_page=100" >"$out" 2>"$err"; then
        return 2
    fi
    python3 - "$marker" "$out" <<'PY'
import json
import sys
marker = f"<!-- larch-stall:signature={sys.argv[1]} -->"
path = sys.argv[2]
with open(path, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if "pull_request" in data and data.get("pull_request") is not None:
            continue
        if marker in (data.get("body") or ""):
            print(data.get("number") or "")
            sys.exit(0)
sys.exit(1)
PY
}

append_slice() {
    local title=$1 file=$2
    printf '## %s\n\n' "$title"
    if [ -n "$file" ] && [ -s "$file" ]; then
        cat "$file"
        printf '\n'
    else
        printf '_No %s supplied for this occurrence._\n' "$title"
    fi
    printf '\n'
}

assemble_comment() {
    local out=$1 attempts_file=$2 escalation_file=$3 root_file=$4
    {
        printf '+1 occurrence\n\n'
        append_slice "Attempts" "$attempts_file"
        append_slice "Escalation evidence" "$escalation_file"
        append_slice "Root-cause finding" "$root_file"
    } >"$out"
}

resolve_tier_b_sensitive_corpus_file() {
    local body_file=$1
    local body_dir
    body_dir=$(dirname "$body_file")
    if [ -z "${sensitive_corpus_file:-}" ]; then
        case "$(basename "${body_file:-}")" in
            design-failure-*)
                sensitive_corpus_file="$body_dir/design-failure-sensitive-corpus.env"
                ;;
            *)
                sensitive_corpus_file="$body_dir/stall-recovery-sensitive-corpus.env"
                ;;
        esac
    fi
}

tier_b_profile_args_for_files() {
    local body_file=$1 corpus_file=$2
    TIER_B_PROFILE_ARGS=()
    case "$(basename "${corpus_file:-}")" in
        design-failure-*)
            TIER_B_PROFILE_ARGS=(--profile generic --artifact-prefix design-failure)
            ;;
    esac
    case "$(basename "${body_file:-}")" in
        design-failure-*)
            TIER_B_PROFILE_ARGS=(--profile generic --artifact-prefix design-failure)
            ;;
    esac
}

reject_tier_b_public_file_if_unsafe() {
    local body_file=$1 candidate_file=$2 err=$3 validate_tmpdir=${4:-}
    local body_dir corpus_copy
    body_dir=$(dirname "$body_file")
    [ -n "$validate_tmpdir" ] || validate_tmpdir="$body_dir"
    resolve_tier_b_sensitive_corpus_file "$body_file"
    tier_b_profile_args_for_files "$body_file" "${sensitive_corpus_file:-}"
    if [ ! -f "$PLUGIN_ROOT/python/cli.py" ]; then
        echo "file-failure-report-cross-repo.sh: tier-b public-file validator unavailable" >"$err"
        return 0
    fi
    if [ ! -f "$sensitive_corpus_file" ] || [ -L "$sensitive_corpus_file" ] || [ ! -r "$sensitive_corpus_file" ]; then
        echo "file-failure-report-cross-repo.sh: tier-b sensitive corpus unavailable" >"$err"
        return 0
    fi
    corpus_copy="$validate_tmpdir/$(basename "$sensitive_corpus_file")"
    if [ "$sensitive_corpus_file" != "$corpus_copy" ]; then
        cp "$sensitive_corpus_file" "$corpus_copy" 2>/dev/null || {
            echo "file-failure-report-cross-repo.sh: tier-b sensitive corpus unavailable" >"$err"
            return 0
        }
    fi
    if [ "${#TIER_B_PROFILE_ARGS[@]}" -gt 0 ]; then
        if ! "${STALL_RECOVERY_CLI[@]}" validate-tier-b-public-file \
            "${TIER_B_PROFILE_ARGS[@]}" \
            --implement-tmpdir "$validate_tmpdir" \
            --public-file "$candidate_file" \
            --sensitive-corpus-file "$corpus_copy" >/dev/null 2>"$err"; then
            return 0
        fi
    elif ! "${STALL_RECOVERY_CLI[@]}" validate-tier-b-public-file \
        --implement-tmpdir "$validate_tmpdir" \
        --public-file "$candidate_file" \
        --sensitive-corpus-file "$corpus_copy" >/dev/null 2>"$err"; then
        return 0
    fi
    return 1
}

reject_tier_b_comment_if_unsafe() {
    local body_file=$1 comment_file=$2 err=$3 validate_tmpdir=${4:-}
    if grep -Eq '<!-- larch-stall:signature=|^### \[(BUG|Bug)\] /(implement|design)|^## /(implement|design) .* report$|^## Report metadata$|^## Sanitized stall report$|^## Validated failure-detail log$|^## Run-log pointer$' "$comment_file"; then
        echo "file-failure-report-cross-repo.sh: tier-b comment contains raw report body section" >"$err"
        return 0
    fi
    reject_tier_b_public_file_if_unsafe "$body_file" "$comment_file" "$err" "$validate_tmpdir"
}

repo=""
body_file=""
title=""
dedup_only=false
attempts_file=""
escalation_file=""
root_file=""
sensitive_corpus_file=""
publication_tier="tier-a"
dry_run=false
mutation_context=""
run_id=""

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) [ $# -ge 2 ] || { usage; exit 2; }; repo=$2; shift 2 ;;
        --body-file) [ $# -ge 2 ] || { usage; exit 2; }; body_file=$2; shift 2 ;;
        --title) [ $# -ge 2 ] || { usage; exit 2; }; title=$2; shift 2 ;;
        --dedup-only) dedup_only=true; shift ;;
        --attempts-file) [ $# -ge 2 ] || { usage; exit 2; }; attempts_file=$2; shift 2 ;;
        --escalation-ledger-file) [ $# -ge 2 ] || { usage; exit 2; }; escalation_file=$2; shift 2 ;;
        --root-cause-file) [ $# -ge 2 ] || { usage; exit 2; }; root_file=$2; shift 2 ;;
        --sensitive-corpus-file) [ $# -ge 2 ] || { usage; exit 2; }; sensitive_corpus_file=$2; shift 2 ;;
        --publication-tier) [ $# -ge 2 ] || { usage; exit 2; }; publication_tier=$2; shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        --mutation-context) [ $# -ge 2 ] || { usage; exit 2; }; mutation_context=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || { usage; exit 2; }; run_id=$2; shift 2 ;;
        *) usage; exit 2 ;;
    esac
done

if ! valid_repo "$repo"; then
    status_fallback invalid-repo
    exit 0
fi
case "$publication_tier" in tier-a|tier-b) ;; *) status_fallback invalid-publication-tier; exit 0 ;; esac
if ! validate_read_file "$body_file" "--body-file"; then
    status_fallback invalid-body-file
    exit 0
fi
if [ -n "$attempts_file" ] && ! validate_read_file "$attempts_file" "--attempts-file"; then
    status_fallback invalid-attempts-file
    exit 0
fi
if [ -n "$escalation_file" ] && ! validate_read_file "$escalation_file" "--escalation-ledger-file"; then
    status_fallback invalid-escalation-ledger-file
    exit 0
fi
if [ -n "$root_file" ] && ! validate_read_file "$root_file" "--root-cause-file"; then
    status_fallback invalid-root-cause-file
    exit 0
fi
if [ -n "$sensitive_corpus_file" ] && ! validate_read_file "$sensitive_corpus_file" "--sensitive-corpus-file"; then
    status_fallback invalid-sensitive-corpus-file
    exit 0
fi

if [ "$dry_run" != true ]; then
    if ! check_mutation_auth "${mutation_context:-}" "${run_id:-}"; then
        exit 0
    fi
fi

marker=$(extract_marker "$body_file" || true)
if [ -z "$marker" ]; then
    if [ "$dedup_only" = true ]; then
        status_fail_open missing-marker
    else
        status_fallback missing-marker
    fi
    exit 0
fi
if [ "$dedup_only" != true ] && [ -z "$title" ]; then
    status_fallback missing-title
    exit 0
fi
if [ "$dry_run" = true ]; then
    emit_kv FILE_FAILURE_REPORT_STATUS dry-run
    exit 0
fi

tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/larch-file-failure-report.XXXXXX") || { status_fallback tempdir-failed; exit 0; }
trap 'rm -rf "$tmpdir"' EXIT
lookup_out="$tmpdir/issues.jsonl"
lookup_err="$tmpdir/lookup.err"
if issue_number=$(lookup_open_issue "$repo" "$marker" "$lookup_out" "$lookup_err"); then
    comment_file="$tmpdir/comment.md"
    comment_json="$tmpdir/comment.json"
    comment_out="$tmpdir/comment.out"
    comment_err="$tmpdir/comment.err"
    assemble_comment "$comment_file" "$attempts_file" "$escalation_file" "$root_file"
    if [ "$publication_tier" = "tier-b" ] && reject_tier_b_comment_if_unsafe "$body_file" "$comment_file" "$comment_err" "$(dirname "$body_file")"; then
        redact_stderr_file "$comment_err"
        status_fallback unsafe-tier-b-comment
        exit 0
    fi
    python3 - "$comment_file" "$comment_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    body = fh.read()
with open(sys.argv[2], "w", encoding="utf-8") as fh:
    json.dump({"body": body}, fh)
PY
    if gh api --method POST "repos/$repo/issues/$issue_number/comments" --input "$comment_json" >"$comment_out" 2>"$comment_err"; then
        comment_url=$(comment_url_from_json <"$comment_out")
        if [ -z "$comment_url" ]; then
            status_fallback comment-url-missing
            exit 0
        fi
        emit_kv FILE_FAILURE_REPORT_STATUS dedup-comment
        emit_kv FILE_FAILURE_REPORT_URL "$comment_url"
        exit 0
    fi
    redact_stderr_file "$comment_err"
    status_fallback comment-failed
    exit 0
else
    lookup_rc=$?
    if [ "$lookup_rc" -ne 1 ]; then
        redact_stderr_file "$lookup_err"
        if [ "$dedup_only" = true ]; then
            status_fail_open lookup-failed
        else
            status_fallback lookup-failed
        fi
        exit 0
    fi
fi

if [ "$dedup_only" = true ]; then
    emit_kv FILE_FAILURE_REPORT_STATUS no-match
    exit 0
fi

if [ "$publication_tier" = "tier-b" ]; then
    create_validate_err="$tmpdir/create-validate.err"
    if reject_tier_b_public_file_if_unsafe "$body_file" "$body_file" "$create_validate_err" "$(dirname "$body_file")"; then
        redact_stderr_file "$create_validate_err"
        status_fallback unsafe-tier-b-body
        exit 0
    fi
fi

create_out="$tmpdir/create.out"
create_err="$tmpdir/create.err"
if gh issue create -R "$repo" --title "$title" --body-file "$body_file" >"$create_out" 2>"$create_err"; then
    issue_url=$(normalize_issue_url <"$create_out")
    if [ -z "$issue_url" ]; then
        status_fallback create-url-missing
        exit 0
    fi
    emit_kv FILE_FAILURE_REPORT_STATUS filed
    emit_kv FILE_FAILURE_REPORT_URL "$issue_url"
    exit 0
fi
redact_stderr_file "$create_err"
status_fallback create-failed
exit 0
