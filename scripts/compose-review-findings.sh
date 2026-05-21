#!/usr/bin/env bash
# compose-review-findings.sh — compose review-findings-full JSONL records.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REDACT_TMP="$SCRIPT_DIR/redact-tmpdir-paths.sh"
REDACT_SECRETS="$SCRIPT_DIR/redact-secrets.sh"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-vote-tally.sh
source "$SCRIPT_DIR/lib-vote-tally.sh"

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

# Extract the category from a finding body. Bodies typically open with a
# '## <category>: …' line or '## **<category>** — …'. Rejected findings may instead
# lead with a triple-hash inner line '### FINDING_<id>: <category>: …' (no synthetic
# '## ' prefix). If absent, returns the empty string.
# For out_of_scope (strict=1), the extracted token must be one of the five focus-area tags
# or the result is treated as unknown and the empty string is returned (prevents bogus OOS
# headings from populating category). For other outcomes (strict=0), '## …' lines still
# return any non-empty parsed label; triple-hash '### FINDING_<id>: …' lines only populate
# category for canonical focus-area tags or true '<tag>: <location>' shapes (two colons).
extract_category() {
    local body="$1" strict="${2:-0}"
    LC_ALL=C awk -v strict="$strict" '
        function is_canonical(c) {
            return (c == "code-quality" || c == "risk-integration" ||
                c == "correctness" || c == "architecture" || c == "security")
        }
        /^###[[:space:]]+FINDING_[0-9A-Za-z_]+:/ {
            if (!sub(/^###[[:space:]]+FINDING_[0-9A-Za-z_]+:[[:space:]]*/, "")) {
                next
            }
            sub(/^[[:space:]]+/, "", $0)
            rest = $0
            n1 = index(rest, ":")
            if (n1 == 0) {
                candidate = rest
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
                if (candidate == "" || !is_canonical(candidate)) {
                    next
                }
                print candidate
                exit
            }
            seg1 = substr(rest, 1, n1 - 1)
            after1 = substr(rest, n1 + 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", seg1)
            n2 = index(after1, ":")
            if (n2 > 0) {
                candidate = seg1
            } else if (is_canonical(seg1)) {
                candidate = seg1
            } else {
                next
            }
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
            if (candidate == "") {
                next
            }
            if (strict == 1) {
                if (is_canonical(candidate)) {
                    print candidate
                }
            } else if (candidate != "") {
                print candidate
            }
            exit
        }
        /^## / {
            sub(/^## /, "")
            if (substr($0, 1, 2) == "**") {
                sub(/^\*\*/, "")
                n = index($0, "**")
                if (n > 0) {
                    candidate = substr($0, 1, n - 1)
                } else {
                    candidate = $0
                }
            } else {
                n = index($0, ":")
                if (n > 0) {
                    candidate = substr($0, 1, n - 1)
                } else {
                    candidate = $0
                }
            }
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
            if (strict == 1) {
                if (candidate == "code-quality" || candidate == "risk-integration" ||
                    candidate == "correctness" || candidate == "architecture" ||
                    candidate == "security") {
                    print candidate
                }
            } else if (candidate != "") {
                print candidate
            }
            exit
        }
    ' <<<"$body"
}

extract_reviewer_from_body() {
    LC_ALL=C awk -F: '
        /^[[:space:]-]*\*\*Reviewers?\*\*:/ || /^[[:space:]-]*Reviewers?:/ {
            sub(/^[[:space:]-]*/, "", $1)
            $1=""
            sub(/^:[[:space:]]*/, "", $0)
            gsub(/\*/, "", $0)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
            print
            exit
        }
    ' <<<"$1"
}

TMP_OUT="$(mktemp "${TMPDIR:-/tmp}/review-findings-full.XXXXXX")" || fail "cannot create temp output"
trap 'rm -f "$TMP_OUT"' EXIT
FINDINGS_TOTAL=0

emit_record() {
    local id="$1" phase="$2" outcome="$3" reviewer="$4" body="$5" round_num="$6"
    local reviewer_redacted body_redacted category strict_cat=0
    reviewer_redacted="$(redact_field "$reviewer")" || fail "redaction failed for reviewer in $id"
    body_redacted="$(redact_field "$body")" || fail "redaction failed for prose_body in $id"
    [[ "$outcome" == "out_of_scope" ]] && strict_cat=1
    category="$(extract_category "$body_redacted" "$strict_cat")"
    # JSONL: one compact JSON object per line. jq handles string escaping.
    jq -nc \
        --arg id "$id" \
        --arg issue_number "$ISSUE" \
        --arg phase "$phase" \
        --arg outcome "$outcome" \
        --arg reviewer "$reviewer_redacted" \
        --arg round_num "$round_num" \
        --arg category "$category" \
        --arg prose_body "$body_redacted" \
        '{id: $id, issue_number: $issue_number, phase: $phase, outcome: $outcome, reviewer: $reviewer, round_num: $round_num, category: $category, prose_body: $prose_body}' \
        >> "$TMP_OUT" || fail "failed to write JSONL record for $id"
    FINDINGS_TOTAL=$((FINDINGS_TOTAL + 1))
}

parse_artifact() {
    local file="$1" kind="$2" round_num="${3:-}"
    [ -f "$file" ] && [ -s "$file" ] || return 0

    local pending_id="" pending_reviewer="" pending_title="" pending_body="" counter=0 id_prefix phase outcome
    case "$kind" in
        plan-review-accepted) phase="plan-review"; outcome="accepted"; id_prefix="" ;;
        plan-review-rejected) phase="plan-review"; outcome="rejected"; id_prefix="REJ_P" ;;
        code-review-accepted) phase="code-review"; outcome="accepted"; id_prefix="" ;;
        code-review-rejected) phase="code-review"; outcome="rejected"; id_prefix="REJ_C" ;;
        code-review-oos) phase="code-review"; outcome="out_of_scope"; id_prefix="OOS_C" ;;
        *) fail "internal: unknown kind: $kind" ;;
    esac

    synthetic_id() {
        local prefix="$1" num="$2" round="$3"
        if [ -n "$round" ]; then
            printf '%sR%s_%s' "$prefix" "$round" "$num"
        else
            printf '%s%s' "$prefix" "$num"
        fi
    }

    flush_pending() {
        [ -n "$pending_id" ] || return 0
        local reviewer="$pending_reviewer"
        local body="$pending_body"
        if [ -n "$pending_title" ]; then
            body="## $pending_title"$'\n\n'"$body"
        fi
        if [ -z "$reviewer" ]; then
            reviewer="$(extract_reviewer_from_body "$pending_body")"
        fi
        if [[ "$kind" == "code-review-oos" ]] && is_security_block <(printf '%s\n' "$body") 2>/dev/null; then
            pending_id=""; pending_reviewer=""; pending_title=""; pending_body=""
            return 0
        fi
        emit_record "$pending_id" "$phase" "$outcome" "${reviewer:-panel}" "$body" "$round_num"
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
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    pending_reviewer="${BASH_REMATCH[1]}"
                    continue
                fi
                ;;
            code-review-rejected)
                if [[ "$line" =~ ^###[[:space:]]+\[(rejected|Code[[:space:]]+Review)\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    if [ "${BASH_REMATCH[1]}" = "Code Review" ]; then
                        pending_reviewer="${BASH_REMATCH[2]}"
                    fi
                    continue
                fi
                # Inner headings inside a rejected block belong to that block's body.
                if [[ -n "$pending_id" && "$line" =~ ^###[[:space:]] ]]; then
                    pending_body="${pending_body}${pending_body:+$'\n'}$line"
                    continue
                fi
                ;;
            code-review-oos)
                if [[ "$line" =~ ^###[[:space:]]+OOS_[0-9A-Za-z_]+:[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    pending_title="${BASH_REMATCH[1]}"
                    continue
                fi
                if [[ "$line" =~ ^###[[:space:]]+FINDING_[0-9A-Za-z_]+:[[:space:]]*\[OUT_OF_SCOPE\][[:space:]]*(.*)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    pending_title="${BASH_REMATCH[1]}"
                    continue
                fi
                # Inner headings inside an OOS block belong to that block's body.
                if [[ -n "$pending_id" && "$line" =~ ^###[[:space:]] ]]; then
                    pending_body="${pending_body}${pending_body:+$'\n'}$line"
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

[ -n "$DESIGN_DIR" ] && parse_artifact "$DESIGN_DIR/accepted-plan-findings.md" plan-review-accepted ""
[ -n "$DESIGN_DIR" ] && parse_artifact "$DESIGN_DIR/rejected-findings.md" plan-review-rejected ""
if [ -n "$IMPLEMENT_TMPDIR" ]; then
    shopt -s nullglob
    round_dirs=( "$IMPLEMENT_TMPDIR"/round-* )
    shopt -u nullglob
    round_rejected_found=false
    for round_dir in "${round_dirs[@]+"${round_dirs[@]}"}"; do
        [ -d "$round_dir" ] || continue
        round_num="$(basename "$round_dir" | sed 's/^round-//')"
        parse_artifact "$round_dir/accepted-findings.md" code-review-accepted "$round_num"
        parse_artifact "$round_dir/oos.md" code-review-oos "$round_num"
        if [ -s "$round_dir/rejected-findings-full.md" ]; then
            round_rejected_found=true
            parse_artifact "$round_dir/rejected-findings-full.md" code-review-rejected "$round_num"
        elif [ -s "$round_dir/rejected-findings.md" ]; then
            round_rejected_found=true
            parse_artifact "$round_dir/rejected-findings.md" code-review-rejected "$round_num"
        fi
    done
    if [ "$round_rejected_found" = false ]; then
        if [ -s "$IMPLEMENT_TMPDIR/rejected-findings-full.md" ]; then
            parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings-full.md" code-review-rejected ""
        else
            parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings.md" code-review-rejected ""
        fi
    fi
fi

mkdir -p "$(dirname "$OUTPUT")" || fail "cannot create output directory"
mv -f "$TMP_OUT" "$OUTPUT" || fail "failed to write output: $OUTPUT"
trap - EXIT

emit_kv COMPOSED true
emit_kv OUTPUT "$OUTPUT"
emit_kv FINDINGS_TOTAL "$FINDINGS_TOTAL"
emit_kv MODE jsonl
