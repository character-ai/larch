#!/usr/bin/env bash
# compose-review-findings.sh — compose the `review-findings-full` anchor
# fragment from existing finding artifacts produced by /design and /implement.
#
# Inputs:
#   --design-artifacts-dir DIR   directory holding accepted-plan-findings.md
#                                and the plan-review entries of rejected-findings.md
#                                (typically $IMPLEMENT_TMPDIR/design-export/)
#   --implement-tmpdir DIR       directory holding rejected-findings.md
#                                with [Code Review] entries (the file
#                                accumulated by /implement Step 5)
#   --issue N                    tracking issue number (used for archive filename)
#   --output PATH                output path for the anchor fragment
#   --archive-dir DIR            directory to write the JSONL archive when
#                                inline payload exceeds the size threshold
#                                (default: docs/review-archive relative to
#                                the current working directory)
#   --archive-threshold N        composed-section byte threshold; when the
#                                inline rendering exceeds this, switch to
#                                archive-pointer mode (default: 30000)
#
# Output (KV on stdout):
#   COMPOSED=true
#   OUTPUT=<path>
#   FINDINGS_TOTAL=<N>
#   MODE=inline|archive
#   ARCHIVE_PATH=<path>          only when MODE=archive
#   ARCHIVE_BYTES=<N>            only when MODE=archive (size of the JSONL)
#
# On failure:
#   FAILED=true
#   ERROR=<single-line message>
#   exit 2
#
# The script is fail-open: missing input directories or files mean "no findings
# of that kind"; the script still writes a non-empty fragment with a header
# and a "no findings captured" line. Empty-input runs produce a small,
# stable fragment so the anchor section is always populated when /implement
# wires this in.
#
# Edit-in-sync:
#   - skills/implement/references/anchor-comment-template.md documents the
#     review-findings-full section as part of the canonical 10-slug template
#   - scripts/anchor-section-markers.sh carries the slug
#   - scripts/tracking-issue-write.sh COLLAPSE_PRIORITY carries the slug
#   - skills/implement/SKILL.md Step 5 invokes this helper after /review
#
# Requires `jq` on PATH for JSONL emission.

set -euo pipefail

DESIGN_DIR=""
IMPLEMENT_TMPDIR=""
ISSUE=""
OUTPUT=""
ARCHIVE_DIR="docs/review-archive"
ARCHIVE_THRESHOLD=30000

usage() {
    cat <<'USAGE' >&2
Usage: compose-review-findings.sh \
  --design-artifacts-dir DIR \
  --implement-tmpdir DIR \
  --issue N \
  --output PATH \
  [--archive-dir DIR] \
  [--archive-threshold N]
USAGE
}

fail() {
    echo "FAILED=true"
    echo "ERROR=$1"
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --design-artifacts-dir)
            [ $# -ge 2 ] || { usage; fail "--design-artifacts-dir requires a value"; }
            DESIGN_DIR="$2"; shift 2 ;;
        --implement-tmpdir)
            [ $# -ge 2 ] || { usage; fail "--implement-tmpdir requires a value"; }
            IMPLEMENT_TMPDIR="$2"; shift 2 ;;
        --issue)
            [ $# -ge 2 ] || { usage; fail "--issue requires a value"; }
            ISSUE="$2"; shift 2 ;;
        --output)
            [ $# -ge 2 ] || { usage; fail "--output requires a value"; }
            OUTPUT="$2"; shift 2 ;;
        --archive-dir)
            [ $# -ge 2 ] || { usage; fail "--archive-dir requires a value"; }
            ARCHIVE_DIR="$2"; shift 2 ;;
        --archive-threshold)
            [ $# -ge 2 ] || { usage; fail "--archive-threshold requires a value"; }
            ARCHIVE_THRESHOLD="$2"; shift 2 ;;
        *)
            usage; fail "unknown flag: $1" ;;
    esac
done

[ -n "$ISSUE" ]  || { usage; fail "--issue is required"; }
[ -n "$OUTPUT" ] || { usage; fail "--output is required"; }

case "$ISSUE" in
    ''|*[!0-9]*) fail "invalid value for --issue: '$ISSUE' (expected non-negative integer)" ;;
esac

case "$ARCHIVE_THRESHOLD" in
    ''|*[!0-9]*) fail "invalid value for --archive-threshold: '$ARCHIVE_THRESHOLD' (expected non-negative integer)" ;;
esac

command -v jq >/dev/null 2>&1 || fail "jq is required for compose-review-findings.sh; install via brew install jq / apt install jq"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REDACT_TMP="$SCRIPT_DIR/redact-tmpdir-paths.sh"
REDACT_SECRETS="$SCRIPT_DIR/redact-secrets.sh"
[ -x "$REDACT_TMP" ]     || fail "redaction helper not executable: $REDACT_TMP"
[ -x "$REDACT_SECRETS" ] || fail "redaction helper not executable: $REDACT_SECRETS"

redact_field() {
    # Preserve redactor stderr so PEM-truncation WARN diagnostics surface,
    # matching tracking-issue-write.sh's redact() posture.
    printf '%s' "$1" | "$REDACT_TMP" | "$REDACT_SECRETS"
}

# Map a reviewer name fragment to one of the canonical category tags.
# The tag enum (per issue #1402) is the union of the plan-review
# personalities and the code-review specialists, plus a generic / other
# catch-all. Mining tools cluster on the tag without NLP.
derive_category() {
    local name_lower
    name_lower=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
    case "$name_lower" in
        *architecture*|*standards*) echo "architecture" ;;
        *correctness*)              echo "correctness" ;;
        *structure*)                echo "structure" ;;
        *edge*|*failure*mode*) echo "edge-cases" ;;
        *innovation*|*exploration*) echo "innovation" ;;
        *pragmati*|*safety*)        echo "pragmatism" ;;
        *security*)                 echo "security" ;;
        *testing*|*tests*)          echo "testing" ;;
        *docs*|*documentation*)     echo "docs" ;;
        *generic*|*claude*|*cursor*|*codex*|*gemini*) echo "generic" ;;
        *)                          echo "other" ;;
    esac
}

# Append a finding record to the inline markdown and the JSONL stream.
emit_finding() {
    local id="$1"
    local phase="$2"
    local outcome="$3"
    local reviewer="$4"
    local category="$5"
    local body="$6"
    local body_redacted reviewer_redacted

    if ! body_redacted=$(redact_field "$body"); then
        fail "redaction failed for prose_body in $id"
    fi
    if ! reviewer_redacted=$(redact_field "$reviewer"); then
        fail "redaction failed for reviewer in $id"
    fi

    {
        printf '### %s — %s\n' "$id" "$category"
        # Use `printf '%s\n' "..."` for bullet lines so the leading `-` cannot
        # be mistaken for a printf flag (POSIX printf parses argv[1] as the
        # format string, but bash's builtin printf still scans for leading
        # options when the format starts with `-`).
        printf '%s\n' "- **Phase**: $phase"
        printf '%s\n' "- **Outcome**: $outcome"
        printf '%s\n' "- **Reviewer**: $reviewer_redacted"
        printf '%s\n' "- **Category**: $category"
        printf '%s\n\n' "- **Prose body** (verbatim from source artifact):"
        # Indent body lines with `> ` (blockquote) so the rendered section keeps
        # the verbatim payload visually separate from the structured bullets,
        # AND so the body cannot accidentally introduce a same-level `### ` that
        # would re-parse as a new finding.
        printf '%s\n' "$body_redacted" | sed 's/^/> /'
        printf '\n'
    } >> "$TMP_INLINE"

    jq -nc \
        --arg id "$id" \
        --arg phase "$phase" \
        --arg outcome "$outcome" \
        --arg reviewer "$reviewer_redacted" \
        --arg category "$category" \
        --arg body "$body_redacted" \
        '{id:$id, phase:$phase, outcome:$outcome, reviewer:$reviewer, category:$category, prose_body:$body}' \
        >> "$TMP_JSONL" || fail "failed to encode JSONL for $id"

    FINDINGS_TOTAL=$((FINDINGS_TOTAL + 1))
}

# Stream-parse a finding artifact. Reads a file line by line; whenever a
# line matches one of the section-header patterns, emit any pending finding
# and start a new one. The body is everything between successive headings.
#
# Args:
#   $1 = path to the artifact file
#   $2 = phase ("plan-review-accepted" | "plan-review-rejected" | "code-review-rejected")
parse_artifact() {
    local file="$1"
    local kind="$2"
    [ -f "$file" ] && [ -s "$file" ] || return 0

    local pending_id="" pending_reviewer="" pending_title=""
    local pending_body=""
    local counter=0
    local id_prefix=""
    local phase="" outcome=""

    case "$kind" in
        plan-review-accepted)
            phase="plan-review"; outcome="accepted" ;;
        plan-review-rejected)
            phase="plan-review"; outcome="rejected"; id_prefix="REJ_P" ;;
        code-review-rejected)
            phase="code-review"; outcome="rejected"; id_prefix="REJ_C" ;;
        *)
            fail "internal: unknown kind: $kind" ;;
    esac

    flush_pending() {
        if [ -n "$pending_id" ]; then
            local body_for_emit
            # Trim trailing blank lines.
            body_for_emit=$(printf '%s' "$pending_body" | sed -e :a -e '/^[[:space:]]*$/{$d;N;ba' -e '}')
            local effective_body
            if [ -n "$pending_title" ]; then
                effective_body="## $pending_title"$'\n\n'"$body_for_emit"
            else
                effective_body="$body_for_emit"
            fi
            local reviewer_for_emit="${pending_reviewer:-panel}"
            local category
            category=$(derive_category "$reviewer_for_emit $pending_title")
            emit_finding "$pending_id" "$phase" "$outcome" "$reviewer_for_emit" "$category" "$effective_body"
            pending_id=""
            pending_reviewer=""
            pending_title=""
            pending_body=""
        fi
    }

    while IFS= read -r line || [ -n "$line" ]; do
        case "$kind" in
            plan-review-accepted)
                # Heading shape: "### FINDING_N: <title>"
                if [[ "$line" =~ ^###[[:space:]]+(FINDING_[0-9A-Za-z_]+):[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    pending_id="${BASH_REMATCH[1]}"
                    pending_title="${BASH_REMATCH[2]}"
                    pending_reviewer=""
                    pending_body=""
                    continue
                fi
                # Any other "### " line closes the current entry without starting a new one.
                if [[ "$line" =~ ^###[[:space:]] ]]; then
                    flush_pending
                    continue
                fi
                ;;
            plan-review-rejected)
                # Heading shape: "### [Plan Review] <reviewer name>"
                if [[ "$line" =~ ^###[[:space:]]+\[Plan[[:space:]]+Review\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="${id_prefix}${counter}"
                    pending_reviewer="${BASH_REMATCH[1]}"
                    pending_title=""
                    pending_body=""
                    continue
                fi
                if [[ "$line" =~ ^###[[:space:]] ]]; then
                    flush_pending
                    continue
                fi
                ;;
            code-review-rejected)
                # Heading shape: "### [Code Review] <reviewer name>"
                if [[ "$line" =~ ^###[[:space:]]+\[Code[[:space:]]+Review\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="${id_prefix}${counter}"
                    pending_reviewer="${BASH_REMATCH[1]}"
                    pending_title=""
                    pending_body=""
                    continue
                fi
                if [[ "$line" =~ ^###[[:space:]] ]]; then
                    flush_pending
                    continue
                fi
                ;;
        esac

        if [ -n "$pending_id" ]; then
            if [ -z "$pending_body" ]; then
                pending_body="$line"
            else
                pending_body="$pending_body"$'\n'"$line"
            fi
        fi
    done < "$file"

    flush_pending
}

OUTPUT_DIR="$(dirname "$OUTPUT")"
mkdir -p "$OUTPUT_DIR" 2>/dev/null || fail "cannot create output directory: $OUTPUT_DIR"

TMP_INLINE="$(mktemp "${OUTPUT}.inline.XXXXXX")" || fail "cannot create temp inline file"
TMP_JSONL="$(mktemp "${OUTPUT}.jsonl.XXXXXX")"  || fail "cannot create temp JSONL file"
trap 'rm -f "$TMP_INLINE" "$TMP_JSONL"' EXIT

FINDINGS_TOTAL=0

# Build the inline section header.
{
    printf '## Review Findings (Full Payload)\n'
    printf '\n'
    # shellcheck disable=SC2016
    printf '_Per-finding payload for plan-review accepted, plan-review rejected, and code-review rejected entries. Existing tally tables in `plan-review-tally` and `code-review-tally` are unchanged. The accepted code-review payload is currently not captured in this format — see follow-up issue._\n'
    printf '\n'
} > "$TMP_INLINE"

# Parse each artifact in turn. Order: accepted plan-review → rejected
# plan-review → rejected code-review. Within each artifact, original input
# order is preserved (the parsers walk the file top-to-bottom).
if [ -n "$DESIGN_DIR" ]; then
    parse_artifact "$DESIGN_DIR/accepted-plan-findings.md" plan-review-accepted
    parse_artifact "$DESIGN_DIR/rejected-findings.md"      plan-review-rejected
fi
if [ -n "$IMPLEMENT_TMPDIR" ]; then
    parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings.md" code-review-rejected
fi

# If no findings at all, emit a stable empty-but-valid section so the anchor
# slot is always populated.
if [ "$FINDINGS_TOTAL" -eq 0 ]; then
    {
        printf '_No review findings captured in this run._\n'
    } >> "$TMP_INLINE"
fi

# Decide inline vs archive based on the composed inline-section size.
INLINE_BYTES=$(wc -c < "$TMP_INLINE" | tr -d ' ')

MODE="inline"
ARCHIVE_PATH=""
ARCHIVE_BYTES=0

if [ "$INLINE_BYTES" -gt "$ARCHIVE_THRESHOLD" ] && [ "$FINDINGS_TOTAL" -gt 0 ]; then
    MODE="archive"
    ARCHIVE_PATH="$ARCHIVE_DIR/issue-${ISSUE}.jsonl"
    mkdir -p "$ARCHIVE_DIR" 2>/dev/null || fail "cannot create archive directory: $ARCHIVE_DIR"
    cp "$TMP_JSONL" "$ARCHIVE_PATH" || fail "failed to write archive: $ARCHIVE_PATH"
    ARCHIVE_BYTES=$(wc -c < "$ARCHIVE_PATH" | tr -d ' ')

    # Replace the inline body with a pointer + count summary; the existing
    # tally tables in plan-review-tally / code-review-tally remain in their
    # respective sections unchanged.
    {
        printf '## Review Findings (Full Payload)\n'
        printf '\n'
        printf '_Inline payload exceeded %s bytes; full per-finding records persisted as JSONL._\n' "$ARCHIVE_THRESHOLD"
        printf '\n'
        printf '%s\n' "- **Archive path**: \`$ARCHIVE_PATH\`"
        printf '%s\n' "- **Findings total**: $FINDINGS_TOTAL"
        printf '%s\n' "- **Archive size**: $ARCHIVE_BYTES bytes"
        printf '\n'
        # shellcheck disable=SC2016
        printf 'Existing tally tables (`plan-review-tally`, `code-review-tally`) remain in their respective anchor sections unchanged.\n'
    } > "$TMP_INLINE"
fi

mv -f "$TMP_INLINE" "$OUTPUT" || fail "failed to write output: $OUTPUT"
trap - EXIT
rm -f "$TMP_JSONL"

echo "COMPOSED=true"
echo "OUTPUT=$OUTPUT"
echo "FINDINGS_TOTAL=$FINDINGS_TOTAL"
echo "MODE=$MODE"
if [ "$MODE" = "archive" ]; then
    echo "ARCHIVE_PATH=$ARCHIVE_PATH"
    echo "ARCHIVE_BYTES=$ARCHIVE_BYTES"
fi
exit 0
