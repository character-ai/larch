#!/usr/bin/env bash
# compose-review-findings.sh — compose review-findings-full markdown sections.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REDACT_TMP="$SCRIPT_DIR/redact-tmpdir-paths.sh"
REDACT_SECRETS="$SCRIPT_DIR/redact-secrets.sh"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

DESIGN_DIR=""
IMPLEMENT_TMPDIR=""
ISSUE=""
OUTPUT=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: compose-review-findings.sh \
  --design-artifacts-dir DIR \
  --implement-tmpdir DIR \
  --issue N \
  --output PATH
USAGE
}

fail() {
    emit_kv FAILED true
    emit_kv ERROR "$1"
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --design-artifacts-dir) DESIGN_DIR="${2:?--design-artifacts-dir requires a value}"; shift 2 ;;
        --implement-tmpdir) IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --archive-dir|--archive-threshold)
            # Backward-compatible no-op while callers migrate away from archive mode.
            shift 2 ;;
        *) usage; fail "unknown flag: $1" ;;
    esac
done

[ -n "$ISSUE" ] || { usage; fail "--issue is required"; }
[ -n "$OUTPUT" ] || { usage; fail "--output is required"; }
case "$ISSUE" in *[!0-9]*|"") fail "invalid value for --issue: '$ISSUE' (expected non-negative integer)" ;; esac
[ -x "$REDACT_TMP" ] || fail "redaction helper not executable: $REDACT_TMP"
[ -x "$REDACT_SECRETS" ] || fail "redaction helper not executable: $REDACT_SECRETS"

redact_field() {
    printf '%s' "$1" | "$REDACT_TMP" | "$REDACT_SECRETS"
}

TMP_OUT="$(mktemp "${TMPDIR:-/tmp}/review-findings-full.XXXXXX")" || fail "cannot create temp output"
trap 'rm -f "$TMP_OUT"' EXIT
FINDINGS_TOTAL=0

emit_record() {
    local id="$1" phase="$2" outcome="$3" reviewer="$4" body="$5"
    local reviewer_redacted body_redacted
    reviewer_redacted="$(redact_field "$reviewer")" || fail "redaction failed for reviewer in $id"
    body_redacted="$(redact_field "$body")" || fail "redaction failed for prose_body in $id"
    printf '### %s: %s [%s/%s]\n\n%s\n\n' "$id" "$reviewer_redacted" "$phase" "$outcome" "$body_redacted" \
        >> "$TMP_OUT" || fail "failed to write section for $id"
    FINDINGS_TOTAL=$((FINDINGS_TOTAL + 1))
}

parse_artifact() {
    local file="$1" kind="$2"
    [ -f "$file" ] && [ -s "$file" ] || return 0

    local pending_id="" pending_reviewer="" pending_title="" pending_body="" counter=0 id_prefix phase outcome
    case "$kind" in
        plan-review-accepted) phase="plan-review"; outcome="accepted"; id_prefix="" ;;
        plan-review-rejected) phase="plan-review"; outcome="rejected"; id_prefix="REJ_P" ;;
        code-review-accepted) phase="code-review"; outcome="accepted"; id_prefix="" ;;
        code-review-rejected) phase="code-review"; outcome="rejected"; id_prefix="REJ_C" ;;
        *) fail "internal: unknown kind: $kind" ;;
    esac

    flush_pending() {
        [ -n "$pending_id" ] || return 0
        local body="$pending_body"
        if [ -n "$pending_title" ]; then
            body="## $pending_title"$'\n\n'"$body"
        fi
        emit_record "$pending_id" "$phase" "$outcome" "${pending_reviewer:-panel}" "$body"
        pending_id=""; pending_reviewer=""; pending_title=""; pending_body=""
    }

    while IFS= read -r line || [ -n "$line" ]; do
        case "$kind" in
            plan-review-accepted)
                if [[ "$line" =~ ^###[[:space:]]+(FINDING_[0-9A-Za-z_]+):[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    pending_id="${BASH_REMATCH[1]}"
                    pending_title="${BASH_REMATCH[2]}"
                    continue
                fi
                ;;
            code-review-accepted)
                if [[ "$line" =~ ^###[[:space:]]+(FINDING_[0-9A-Za-z_]+):[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    pending_id="${BASH_REMATCH[1]}"
                    pending_title="${BASH_REMATCH[2]}"
                    continue
                fi
                ;;
            plan-review-rejected)
                if [[ "$line" =~ ^###[[:space:]]+\[Plan[[:space:]]+Review\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="${id_prefix}${counter}"
                    pending_reviewer="${BASH_REMATCH[1]}"
                    continue
                fi
                ;;
            code-review-rejected)
                if [[ "$line" =~ ^###[[:space:]]+\[Code[[:space:]]+Review\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="${id_prefix}${counter}"
                    pending_reviewer="${BASH_REMATCH[1]}"
                    continue
                fi
                ;;
        esac
        if [[ "$line" =~ ^###[[:space:]] ]]; then
            flush_pending
            continue
        fi
        if [ -n "$pending_id" ]; then
            pending_body="${pending_body}${pending_body:+$'\n'}$line"
        fi
    done < "$file"
    flush_pending
}

[ -n "$DESIGN_DIR" ] && parse_artifact "$DESIGN_DIR/accepted-plan-findings.md" plan-review-accepted
[ -n "$DESIGN_DIR" ] && parse_artifact "$DESIGN_DIR/rejected-findings.md" plan-review-rejected
if [ -n "$IMPLEMENT_TMPDIR" ]; then
    shopt -s nullglob
    round_dirs=( "$IMPLEMENT_TMPDIR"/round-* )
    shopt -u nullglob
    round_rejected_found=false
    for round_dir in "${round_dirs[@]+"${round_dirs[@]}"}"; do
        [ -d "$round_dir" ] || continue
        parse_artifact "$round_dir/accepted-findings.md" code-review-accepted
        if [ -s "$round_dir/rejected-findings-full.md" ]; then
            round_rejected_found=true
            parse_artifact "$round_dir/rejected-findings-full.md" code-review-rejected
        elif [ -s "$round_dir/rejected-findings.md" ]; then
            round_rejected_found=true
            parse_artifact "$round_dir/rejected-findings.md" code-review-rejected
        fi
    done
    if [ "$round_rejected_found" = false ]; then
        if [ -s "$IMPLEMENT_TMPDIR/rejected-findings-full.md" ]; then
            parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings-full.md" code-review-rejected
        else
            parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings.md" code-review-rejected
        fi
    fi
fi

mkdir -p "$(dirname "$OUTPUT")" || fail "cannot create output directory"
mv -f "$TMP_OUT" "$OUTPUT" || fail "failed to write output: $OUTPUT"
trap - EXIT

emit_kv COMPOSED true
emit_kv OUTPUT "$OUTPUT"
emit_kv FINDINGS_TOTAL "$FINDINGS_TOTAL"
emit_kv MODE markdown
