#!/usr/bin/env bash
# file-failure-report-cross-repo.sh — exact-signature issue filing and dedup for stall reports.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
STALL_RECOVERY_VALIDATE_PUBLIC_CLI=("$PLUGIN_ROOT/scripts/larch.sh" stall-recovery validate-tier-b-public-file)
PUBLIC_SNAPSHOT_FILES=()
PUBLIC_SNAPSHOT_FDS=()
PUBLIC_SNAPSHOT_PATH=""

usage() {
    echo "file-failure-report-cross-repo.sh: usage: $0 --repo OWNER/REPO --body-file PATH --title TITLE [--mutation-context PATH --run-id ID --trusted-root PATH] [--dedup-only] [--create-on-lookup-failure] [--attempts-file PATH] [--escalation-ledger-file PATH] [--root-cause-file PATH] [--sensitive-corpus-file PATH] [--publication-tier tier-a|tier-b] [--dry-run]" >&2
}

status_refused() { emit_kv FILE_FAILURE_REPORT_STATUS mutation-refused; emit_kv FILE_FAILURE_REPORT_FALLBACK_REASON "unauthorized-mutation:$1"; }

check_mutation_auth() {
    local context_file=$1 run_id=$2 trusted_root=$3
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
    if [ -z "$trusted_root" ]; then
        status_refused missing-trusted-root
        return 1
    fi
    if ! "$PLUGIN_ROOT/scripts/larch.sh" session check-live-mutation-auth --context-file "$context_file" --run-id "$run_id" --trusted-root "$trusted_root" >/dev/null 2>&1; then
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
    "$PLUGIN_ROOT/scripts/larch.sh" redact secrets <"$file" >&2 || echo "file-failure-report-cross-repo.sh: stderr redaction failed" >&2
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

absolute_path() {
    local path=$1 parent base
    parent=$(dirname "$path")
    base=$(basename "$path")
    (
        cd -P "$parent" 2>/dev/null || exit 1
        printf '%s/%s\n' "$PWD" "$base"
    )
}

extract_marker() {
    local file=$1
    LC_ALL=C grep -Eo '<!-- larch-stall:signature=[0-9a-f]{64} -->' "$file" | head -n 1 | sed 's/^<!-- larch-stall:signature=//; s/ -->$//'
}

extract_report_title() {
    local file=$1 publication=$2 title
    title=$(sed -n '1s/^### //p' "$file")
    if [ "$publication" = tier-a ]; then
        title=${title#"[BUG] "}
        title=${title#"[Bug] "} # lint-prefix-case-variant: ok legacy title normalization
    fi
    printf '%s\n' "$title"
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

tier_b_profile_for_files() {
    local body_file=$1 corpus_file=$2
    case "$(basename "${corpus_file:-}")" in
        design-failure-*)
            printf '%s\n' design
            return
            ;;
    esac
    case "$(basename "${body_file:-}")" in
        design-failure-*)
            printf '%s\n' design
            return
            ;;
    esac
    printf '%s\n' default
}

register_public_snapshot() {
    PUBLIC_SNAPSHOT_FILES[${#PUBLIC_SNAPSHOT_FILES[@]}]=$1
}

cleanup_public_snapshots() {
    local snapshot fd
    if [ "${#PUBLIC_SNAPSHOT_FDS[@]}" -gt 0 ]; then
        for fd in "${PUBLIC_SNAPSHOT_FDS[@]}"; do
            close_public_snapshot_fd "$fd"
        done
    fi
    if [ "${#PUBLIC_SNAPSHOT_FILES[@]}" -gt 0 ]; then
        for snapshot in "${PUBLIC_SNAPSHOT_FILES[@]}"; do
            [ -n "$snapshot" ] && rm -f "$snapshot" || true
        done
    fi
}

register_public_snapshot_fd() {
    PUBLIC_SNAPSHOT_FDS[${#PUBLIC_SNAPSHOT_FDS[@]}]=$1
}

close_public_snapshot_fd() {
    case "$1" in
        3) exec 3>&- ;;
        4) exec 4>&- ;;
        5) exec 5>&- ;;
        6) exec 6>&- ;;
        7) exec 7>&- ;;
        8) exec 8>&- ;;
        9) exec 9>&- ;;
    esac
}

close_public_snapshot_fds_except() {
    local keep=$1 fd
    if [ "${#PUBLIC_SNAPSHOT_FDS[@]}" -eq 0 ]; then
        return
    fi
    for fd in "${PUBLIC_SNAPSHOT_FDS[@]}"; do
        [ "$fd" = "$keep" ] || close_public_snapshot_fd "$fd"
    done
}

open_public_snapshot_fd() {
    local fd=$1 err=$2 snapshot_file
    snapshot_file=$(mktemp "$tmpdir/.larch-public-snapshot.XXXXXX") || {
        echo "file-failure-report-cross-repo.sh: public payload snapshot unavailable" >"$err"
        return 1
    }
    case "$fd" in
        3) exec 3<> "$snapshot_file" || return 1 ;;
        4) exec 4<> "$snapshot_file" || return 1 ;;
        5) exec 5<> "$snapshot_file" || return 1 ;;
        6) exec 6<> "$snapshot_file" || return 1 ;;
        7) exec 7<> "$snapshot_file" || return 1 ;;
        8) exec 8<> "$snapshot_file" || return 1 ;;
        9) exec 9<> "$snapshot_file" || return 1 ;;
        *)
            rm -f "$snapshot_file" || true
            echo "file-failure-report-cross-repo.sh: public payload snapshot unavailable" >"$err"
            return 1
            ;;
    esac
    if ! rm -f "$snapshot_file"; then
        close_public_snapshot_fd "$fd"
        echo "file-failure-report-cross-repo.sh: public payload snapshot unavailable" >"$err"
        return 1
    fi
    register_public_snapshot_fd "$fd"
}

snapshot_fd_path() {
    printf '/dev/fd/%s\n' "$1"
}

rewind_public_snapshot_fd() {
    python3 -c 'import os,sys; os.lseek(int(sys.argv[1]), 0, os.SEEK_SET)' "$1"
}

snapshot_public_file() {
    local source_file=$1 publication=$2 source_tmpdir=$3 snapshot_fd=$4 err=$5
    local tier_b_profile
    [ -d "$source_tmpdir" ] || {
        echo "file-failure-report-cross-repo.sh: public payload root unavailable" >"$err"
        return 1
    }
    if ! open_public_snapshot_fd "$snapshot_fd" "$err"; then
        return 1
    fi
    if [ "$publication" = tier-b ]; then
        resolve_tier_b_sensitive_corpus_file "$body_file"
        tier_b_profile=$(tier_b_profile_for_files "$body_file" "${sensitive_corpus_file:-}")
        if [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ]; then
            echo "file-failure-report-cross-repo.sh: tier-b public-file validator unavailable" >"$err"
            return 1
        fi
        if [ ! -f "$sensitive_corpus_file" ] || [ -L "$sensitive_corpus_file" ] || [ ! -r "$sensitive_corpus_file" ]; then
            echo "file-failure-report-cross-repo.sh: tier-b sensitive corpus unavailable" >"$err"
            return 1
        fi
        if [ "$tier_b_profile" = design ]; then
            if ! "${STALL_RECOVERY_VALIDATE_PUBLIC_CLI[@]}" \
                --profile generic --artifact-prefix design-failure \
                --publication-tier tier-b \
                --implement-tmpdir "$source_tmpdir" \
                --public-file "$source_file" \
                --sensitive-corpus-file "$sensitive_corpus_file" \
                --snapshot-fd "$snapshot_fd" >/dev/null 2>"$err"; then
                return 1
            fi
        elif ! "${STALL_RECOVERY_VALIDATE_PUBLIC_CLI[@]}" \
            --publication-tier tier-b \
            --implement-tmpdir "$source_tmpdir" \
            --public-file "$source_file" \
            --sensitive-corpus-file "$sensitive_corpus_file" \
            --snapshot-fd "$snapshot_fd" >/dev/null 2>"$err"; then
            return 1
        fi
    elif [ "$publication" = tier-a ]; then
        if ! "${STALL_RECOVERY_VALIDATE_PUBLIC_CLI[@]}" \
            --publication-tier tier-a \
            --implement-tmpdir "$source_tmpdir" \
            --public-file "$source_file" \
            --snapshot-fd "$snapshot_fd" >/dev/null 2>"$err"; then
            return 1
        fi
    else
        echo "file-failure-report-cross-repo.sh: invalid publication tier" >"$err"
        return 1
    fi
    if ! rewind_public_snapshot_fd "$snapshot_fd"; then
        echo "file-failure-report-cross-repo.sh: public payload snapshot unavailable" >"$err"
        return 1
    fi
    PUBLIC_SNAPSHOT_PATH=$(snapshot_fd_path "$snapshot_fd")
}

snapshot_public_fd() {
    local source_fd=$1 source_tmpdir=$2 snapshot_fd=$3 err=$4 tier_b_profile
    [ -d "$source_tmpdir" ] || {
        echo "file-failure-report-cross-repo.sh: public payload root unavailable" >"$err"
        return 1
    }
    if ! open_public_snapshot_fd "$snapshot_fd" "$err"; then
        return 1
    fi
    resolve_tier_b_sensitive_corpus_file "$body_file"
    tier_b_profile=$(tier_b_profile_for_files "$body_file" "${sensitive_corpus_file:-}")
    if [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ]; then
        echo "file-failure-report-cross-repo.sh: tier-b public-file validator unavailable" >"$err"
        return 1
    fi
    if [ ! -f "$sensitive_corpus_file" ] || [ -L "$sensitive_corpus_file" ] || [ ! -r "$sensitive_corpus_file" ]; then
        echo "file-failure-report-cross-repo.sh: tier-b sensitive corpus unavailable" >"$err"
        return 1
    fi
    if [ "$tier_b_profile" = design ]; then
        if ! "${STALL_RECOVERY_VALIDATE_PUBLIC_CLI[@]}" \
            --profile generic --artifact-prefix design-failure \
            --publication-tier tier-b \
            --implement-tmpdir "$source_tmpdir" \
            --public-fd "$source_fd" \
            --sensitive-corpus-file "$sensitive_corpus_file" \
            --snapshot-fd "$snapshot_fd" >/dev/null 2>"$err"; then
            return 1
        fi
    elif ! "${STALL_RECOVERY_VALIDATE_PUBLIC_CLI[@]}" \
        --publication-tier tier-b \
        --implement-tmpdir "$source_tmpdir" \
        --public-fd "$source_fd" \
        --sensitive-corpus-file "$sensitive_corpus_file" \
        --snapshot-fd "$snapshot_fd" >/dev/null 2>"$err"; then
        return 1
    fi
    if ! rewind_public_snapshot_fd "$snapshot_fd"; then
        echo "file-failure-report-cross-repo.sh: public payload snapshot unavailable" >"$err"
        return 1
    fi
    PUBLIC_SNAPSHOT_PATH=$(snapshot_fd_path "$snapshot_fd")
}

tier_b_comment_is_unsafe() {
    local comment_file=$1 err=$2
    if grep -Eq '<!-- larch-stall:signature=|^### \[(BUG|Bug)\] /(implement|design)|^## /(implement|design) .* report$|^## Report metadata$|^## Sanitized stall report$|^## Validated failure-detail log$|^## Run-log pointer$' "$comment_file"; then
        echo "file-failure-report-cross-repo.sh: tier-b comment contains raw report body section" >"$err"
        return 0
    fi
    return 1
}

repo=""
body_file=""
title=""
dedup_only=false
create_on_lookup_failure=false
attempts_file=""
escalation_file=""
root_file=""
sensitive_corpus_file=""
publication_tier="tier-a"
dry_run=false
mutation_context=""
run_id=""
trusted_root=""

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) [ $# -ge 2 ] || { usage; exit 2; }; repo=$2; shift 2 ;;
        --body-file) [ $# -ge 2 ] || { usage; exit 2; }; body_file=$2; shift 2 ;;
        --title) [ $# -ge 2 ] || { usage; exit 2; }; title=$2; shift 2 ;;
        --dedup-only) dedup_only=true; shift ;;
        --create-on-lookup-failure) create_on_lookup_failure=true; shift ;;
        --attempts-file) [ $# -ge 2 ] || { usage; exit 2; }; attempts_file=$2; shift 2 ;;
        --escalation-ledger-file) [ $# -ge 2 ] || { usage; exit 2; }; escalation_file=$2; shift 2 ;;
        --root-cause-file) [ $# -ge 2 ] || { usage; exit 2; }; root_file=$2; shift 2 ;;
        --sensitive-corpus-file) [ $# -ge 2 ] || { usage; exit 2; }; sensitive_corpus_file=$2; shift 2 ;;
        --publication-tier) [ $# -ge 2 ] || { usage; exit 2; }; publication_tier=$2; shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        --mutation-context) [ $# -ge 2 ] || { usage; exit 2; }; mutation_context=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || { usage; exit 2; }; run_id=$2; shift 2 ;;
        --trusted-root) [ $# -ge 2 ] || { usage; exit 2; }; trusted_root=$2; shift 2 ;;
        *) usage; exit 2 ;;
    esac
done

if ! valid_repo "$repo"; then
    status_fallback invalid-repo
    exit 0
fi
case "$publication_tier" in tier-a|tier-b) ;; *) status_fallback invalid-publication-tier; exit 0 ;; esac
if [ "$create_on_lookup_failure" = true ] && { [ "$dedup_only" = true ] || [ "$publication_tier" != tier-a ]; }; then
    status_fallback invalid-lookup-failure-create
    exit 0
fi
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
if ! body_file=$(absolute_path "$body_file"); then
    status_fallback invalid-body-file
    exit 0
fi
if [ -n "$attempts_file" ] && ! attempts_file=$(absolute_path "$attempts_file"); then
    status_fallback invalid-attempts-file
    exit 0
fi
if [ -n "$escalation_file" ] && ! escalation_file=$(absolute_path "$escalation_file"); then
    status_fallback invalid-escalation-ledger-file
    exit 0
fi
if [ -n "$root_file" ] && ! root_file=$(absolute_path "$root_file"); then
    status_fallback invalid-root-cause-file
    exit 0
fi
if [ -n "$sensitive_corpus_file" ] && ! sensitive_corpus_file=$(absolute_path "$sensitive_corpus_file"); then
    status_fallback invalid-sensitive-corpus-file
    exit 0
fi

if [ "$dry_run" != true ]; then
    if ! check_mutation_auth "${mutation_context:-}" "${run_id:-}" "${trusted_root:-}"; then
        exit 0
    fi
fi

body_validate_root=$(dirname "$body_file")
if [ "$dry_run" = true ]; then
    snapshot_source_root=$body_validate_root
elif ! snapshot_source_root=$(absolute_path "$trusted_root"); then
    status_fallback invalid-trusted-root
    exit 0
fi

stage_parent=${TMPDIR:-/tmp}
if ! stage_parent=$(absolute_path "$stage_parent"); then
    status_fallback tempdir-failed
    exit 0
fi
tmpdir=$(mktemp -d "$stage_parent/larch-file-failure-report.XXXXXX") || { status_fallback tempdir-failed; exit 0; }
trap 'cleanup_public_snapshots; rm -rf "$tmpdir"' EXIT
if ! chmod 700 "$tmpdir"; then
    status_fallback tempdir-private-failed
    exit 0
fi
body_snapshot_err="$tmpdir/body-snapshot.err"
if ! snapshot_public_file "$body_file" tier-a "$snapshot_source_root" 3 "$body_snapshot_err"; then
    redact_stderr_file "$body_snapshot_err"
    status_fallback invalid-body-snapshot
    exit 0
fi
body_snapshot=$PUBLIC_SNAPSHOT_PATH

marker=$(extract_marker "$body_snapshot" || true)
if ! rewind_public_snapshot_fd 3; then
    status_fallback invalid-body-snapshot
    exit 0
fi
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
if [ "$dedup_only" != true ]; then
    approved_title=$(extract_report_title "$body_snapshot" "$publication_tier")
    if ! rewind_public_snapshot_fd 3; then
        status_fallback invalid-body-snapshot
        exit 0
    fi
    if [ -z "$approved_title" ]; then
        status_fallback invalid-body-title
        exit 0
    fi
    title=$approved_title
fi
if [ "$dry_run" = true ]; then
    emit_kv FILE_FAILURE_REPORT_STATUS dry-run
    exit 0
fi

lookup_out="$tmpdir/issues.jsonl"
lookup_err="$tmpdir/lookup.err"
if issue_number=$(lookup_open_issue "$repo" "$marker" "$lookup_out" "$lookup_err" 3>&-); then
    attempts_snapshot=""
    escalation_snapshot=""
    root_snapshot=""
    if [ -n "$attempts_file" ]; then
        if ! snapshot_public_file "$attempts_file" tier-a "$snapshot_source_root" 4 "$tmpdir/attempts-snapshot.err"; then
            redact_stderr_file "$tmpdir/attempts-snapshot.err"
            status_fallback invalid-attempts-file
            exit 0
        fi
        attempts_snapshot=$PUBLIC_SNAPSHOT_PATH
    fi
    if [ -n "$escalation_file" ]; then
        if ! snapshot_public_file "$escalation_file" tier-a "$snapshot_source_root" 5 "$tmpdir/escalation-snapshot.err"; then
            redact_stderr_file "$tmpdir/escalation-snapshot.err"
            status_fallback invalid-escalation-ledger-file
            exit 0
        fi
        escalation_snapshot=$PUBLIC_SNAPSHOT_PATH
    fi
    if [ -n "$root_file" ]; then
        if ! snapshot_public_file "$root_file" tier-a "$snapshot_source_root" 6 "$tmpdir/root-snapshot.err"; then
            redact_stderr_file "$tmpdir/root-snapshot.err"
            status_fallback invalid-root-cause-file
            exit 0
        fi
        root_snapshot=$PUBLIC_SNAPSHOT_PATH
    fi
    comment_file=$(mktemp "$snapshot_source_root/.larch-public-comment.XXXXXX") || {
        status_fallback comment-snapshot-unavailable
        exit 0
    }
    register_public_snapshot "$comment_file"
    comment_out="$tmpdir/comment.out"
    comment_err="$tmpdir/comment.err"
    assemble_comment "$comment_file" "$attempts_snapshot" "$escalation_snapshot" "$root_snapshot"
    if ! snapshot_public_file "$comment_file" "$publication_tier" "$snapshot_source_root" 7 "$comment_err"; then
        redact_stderr_file "$comment_err"
        if [ "$publication_tier" = "tier-b" ]; then
            status_fallback unsafe-tier-b-comment
        else
            status_fallback invalid-tier-a-comment
        fi
        exit 0
    fi
    comment_snapshot=$PUBLIC_SNAPSHOT_PATH
    if [ "$publication_tier" = "tier-b" ] && tier_b_comment_is_unsafe "$comment_snapshot" "$comment_err"; then
        redact_stderr_file "$comment_err"
        status_fallback unsafe-tier-b-comment
        exit 0
    fi
    if ! rewind_public_snapshot_fd 7; then
        status_fallback comment-snapshot-unavailable
        exit 0
    fi
    if ! open_public_snapshot_fd 8 "$comment_err"; then
        redact_stderr_file "$comment_err"
        status_fallback comment-snapshot-unavailable
        exit 0
    fi
    if ! python3 -c 'import json,sys; json.dump({"body": open(sys.argv[1], encoding="utf-8").read()}, sys.stdout)' "$comment_snapshot" >"$(snapshot_fd_path 8)"; then
        redact_stderr_file "$comment_err"
        status_fallback comment-snapshot-unavailable
        exit 0
    fi
    if ! rewind_public_snapshot_fd 8; then
        status_fallback comment-snapshot-unavailable
        exit 0
    fi
    close_public_snapshot_fds_except 8
    if gh api --method POST "repos/$repo/issues/$issue_number/comments" --input "$(snapshot_fd_path 8)" >"$comment_out" 2>"$comment_err"; then
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
        if [ "$create_on_lookup_failure" != true ]; then
            redact_stderr_file "$lookup_err"
            if [ "$dedup_only" = true ]; then
                status_fail_open lookup-failed
            else
                status_fallback lookup-failed
            fi
            exit 0
        fi
    fi
fi

if [ "$dedup_only" = true ]; then
    emit_kv FILE_FAILURE_REPORT_STATUS no-match
    exit 0
fi

if [ "$publication_tier" = "tier-b" ]; then
    create_validate_err="$tmpdir/create-validate.err"
    if ! snapshot_public_fd 3 "$snapshot_source_root" 9 "$create_validate_err"; then
        redact_stderr_file "$create_validate_err"
        status_fallback unsafe-tier-b-body
        exit 0
    fi
    create_body_snapshot=$PUBLIC_SNAPSHOT_PATH
    create_transport_fd=9
else
    create_body_snapshot=$body_snapshot
    create_transport_fd=3
fi

create_out="$tmpdir/create.out"
create_err="$tmpdir/create.err"
close_public_snapshot_fds_except "$create_transport_fd"
if gh issue create -R "$repo" --title "$title" --body-file "$create_body_snapshot" >"$create_out" 2>"$create_err"; then
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
