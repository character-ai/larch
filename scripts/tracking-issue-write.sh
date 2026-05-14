#!/usr/bin/env bash
# tracking-issue-write.sh — outbound helper for the tracking-issue lifecycle.
#
# Phase 1 (umbrella #348) foundation layer. Ships narrow subcommands —
# create-issue, append-comment, rename, and mark-false-positive — that each
# perform exactly one GitHub write while sharing the same KEY=value stdout envelope and
# fail-closed redaction posture as skills/issue/scripts/create-one.sh.
#
# Subcommands:
#   create-issue   --title T --body-file F [--repo OWNER/REPO]
#   append-comment --issue N --body-file F [--lifecycle-marker ID] [--repo OWNER/REPO]
#   rename         --issue N --state in-progress|done|stalled [--round-trip BOOL] [--repo OWNER/REPO]
#   mark-false-positive --issue N [--repo OWNER/REPO]
#
# Output contract (KEY=value on stdout; warnings on stderr). NAMESPACE note:
# this script emits FAILED=true / ERROR=<msg> on failure — NOT the
# ISSUE_FAILED=true / ISSUE_ERROR=<msg> prefix used by
# skills/issue/scripts/create-one.sh. The divergence is intentional; this
# script is not an /issue layer component. Consumers must parse for the
# FAILED= / ERROR= prefix exactly. Parsers must also use the ERROR= field
# (not exit code alone) to distinguish error kinds because exit 1 covers
# both invocation-usage errors and validated-content rejections.
#
# Success keys:
#   create-issue:   ISSUE_NUMBER=<N>  ISSUE_URL=<url>
#   append-comment: COMMENT_ID=<id>   COMMENT_URL=<url>
#   rename:         RENAMED=true|false  NEW_TITLE=<title>
#                   ROUND_TRIP_APPLIED=true|false (only when --round-trip was passed)
#   mark-false-positive: MARKED=true|false  NEW_TITLE=<title>
#
# Rename semantics (tracking-issue title-prefix lifecycle):
#   Strips exactly ONE leading lifecycle prefix (anchored regex
#   ^\[(IN PROGRESS|DONE|STALLED)\] ) from the current title, preserves or
#   adds the optional strict-ASCII "[ROUND-TRIP] " marker, then prepends the
#   target-state prefix. Lifecycle prefix order is fixed: lifecycle first,
#   round-trip second. No-op when the composed title matches the current
#   canonical title (RENAMED=false). The new title is piped through
#   scripts/redact-secrets.sh before the gh call, matching the security
#   posture of create-issue. Stacked-prefix corruption (e.g., "[IN PROGRESS]
#   [DONE] Foo") is NOT healed — only one lifecycle prefix is stripped.
#   Title length: truncated to 256 chars by preserving the managed prefixes
#   and slicing only the user tail. GitHub's limit is 256 characters —
#   matching bash's native length under UTF-8 locales. Managed prefixes are
#   ASCII so truncation is stable regardless of locale.
#
# Failure keys:
#   FAILED=true  ERROR=<single-line message>
#
# Exit codes:
#   0 — success
#   1 — invocation-usage error OR validated-content rejection (disambiguate via ERROR=)
#   2 — gh failure OR fail-closed content-state error (e.g., multiple anchor
#       comments found) — FAILED=true / ERROR= already emitted on stdout
#   3 — redaction helper failure (FAILED=true / ERROR=redaction:…)
#
# Security posture (see SECURITY.md "tracking-issue-write.sh outbound path"):
#   * Structural choke point — compose full logical body in memory, pipe
#     through scripts/redact-secrets.sh, THEN apply truncation. Never the
#     reverse. Token-shaped byte sequences must not be sliced before
#     redaction. Placement mirrors create-one.sh's single-choke-point
#     comment (create-one.sh:202-208).
#   * gh-failure redaction — every gh invocation captures stdout and
#     stderr separately. On non-success paths, captured stderr is piped
#     through scripts/redact-secrets.sh before emission in ERROR=. This
#     mirrors create-one.sh:247-280's posture for /issue outbound.
#   * Summary comments are owned by tracking-issue-summary.sh; durable run
#     payloads are owned by larch-log.sh.
#
# Conventions:
#   Uses Bash 3.2-compatible constructs (indexed arrays only; no
#   associative arrays, no `mapfile`) so macOS-default bash runs match
#   Ubuntu CI. Precedent: scripts/dialectic-smoke-test.sh.
#   Truncation is intentionally not applied here anymore; bulky run payloads
#   live in committed larch-logs files rather than in GitHub comments.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"
REDACT_TMPDIR_HELPER="$REPO_ROOT/scripts/redact-tmpdir-paths.sh"

TITLE_MARKERS_HELPER="$SCRIPT_DIR/lib-title-markers.sh"

usage() {
    cat <<'USAGE' >&2
Usage:
  tracking-issue-write.sh create-issue   --title T --body-file F [--repo OWNER/REPO]
  tracking-issue-write.sh append-comment --issue N --body-file F [--lifecycle-marker ID] [--repo OWNER/REPO]
  tracking-issue-write.sh rename         --issue N --state in-progress|done|stalled [--round-trip BOOL] [--repo OWNER/REPO]
  tracking-issue-write.sh mark-false-positive --issue N [--repo OWNER/REPO]
USAGE
}

# State-to-prefix mapping for the rename subcommand. Using a function rather
# than an associative array keeps us Bash 3.2 compatible (see top-of-file
# conventions).
state_to_prefix() {
    case "$1" in
        in-progress) printf '[IN PROGRESS] ' ;;
        done)        printf '[DONE] ' ;;
        stalled)     printf '[STALLED] ' ;;
        *)           return 1 ;;
    esac
}

# strip_lifecycle_prefix <title> — prints the title with exactly ONE leading
# lifecycle prefix removed (if present). Anchored at the start; stacked
# prefixes beyond the first are preserved. Uses shell parameter expansion
# so the stripper is regex-engine-agnostic and safe for bash 3.2.
strip_lifecycle_prefix() {
    local t="$1"
    case "$t" in
        '[IN PROGRESS] '*) printf '%s' "${t#\[IN PROGRESS\] }" ;;
        '[DONE] '*)        printf '%s' "${t#\[DONE\] }" ;;
        '[STALLED] '*)     printf '%s' "${t#\[STALLED\] }" ;;
        *)                 printf '%s' "$t" ;;
    esac
}

# has_round_trip_prefix <title-after-lifecycle-strip> — true iff the title
# begins with the exact managed marker. Lowercase, Unicode-homoglyph, or
# missing-space variants are user content.
has_round_trip_prefix() {
    case "$1" in
        '[ROUND-TRIP] '*) return 0 ;;
        *)               return 1 ;;
    esac
}

# strip_round_trip_prefix <title-after-lifecycle-strip> — prints the title
# with at most one exact managed round-trip marker removed.
strip_round_trip_prefix() {
    local t="$1"
    case "$t" in
        '[ROUND-TRIP] '*) printf '%s' "${t#\[ROUND-TRIP\] }" ;;
        *)                printf '%s' "$t" ;;
    esac
}

# truncate_title_with_prefixes_to_256 <prefixes> <user-tail> —
# character-oriented truncation to 256 chars using bash string semantics
# (`${#var}` + slice). GitHub's title limit is 256 characters, matching
# bash's native string semantics under UTF-8 locales. Preserves both managed
# prefixes at the head and slices only the user tail. The optional round-trip
# marker is exactly 13 ASCII chars including the trailing space.
truncate_title_with_prefixes_to_256() {
    local prefixes="$1"
    local tail="$2"
    local budget=$((256 - ${#prefixes}))
    if (( budget < 0 )); then
        budget=0
    fi
    if (( ${#prefixes} + ${#tail} <= 256 )); then
        printf '%s%s' "$prefixes" "$tail"
    else
        printf '%s%s' "$prefixes" "${tail:0:$budget}"
    fi
}

# truncate_title_to_256 <title> — character-oriented truncation to 256
# chars using bash string semantics. Used by `mark-false-positive`, where
# the marker is inserted into the leading bracket-block sequence by
# insert_signal_marker (lib-title-markers.sh) and the resulting title is
# truncated as a whole; rename uses truncate_title_with_prefixes_to_256
# instead because it composes lifecycle + round-trip prefixes explicitly.
truncate_title_to_256() {
    local t="$1"
    if (( ${#t} <= 256 )); then
        printf '%s' "$t"
    else
        printf '%s' "${t:0:256}"
    fi
}

# emit_redaction_failure — runs outside command substitution (via `|| ...`)
# so its echo lines reach the parent's stdout for callers parsing
# ^FAILED= / ^ERROR= on stdout, then exits 3. The helper is required:
# there is no fallback to un-redacted content per the fail-closed
# defense-in-depth design.
emit_redaction_failure() {
    local rc=$?
    emit_kv FAILED "true"
    if [ "$rc" -eq 10 ]; then
        emit_kv ERROR "redaction: helper redact-tmpdir-paths.sh failed or missing"
    else
        emit_kv ERROR "redaction: helper $REDACT_HELPER failed or missing"
    fi
    exit 3
}

# redact <text> — prints redacted text on stdout, returns the helper's
# exit code. Callers MUST invoke this via command substitution combined
# with `|| emit_redaction_failure`, because inside command substitution any
# stdout emission is captured into the assigning variable rather than the
# parent's stdout. Do NOT swallow stderr: redact-secrets.sh emits a WARN on
# stderr when an unterminated PEM block forces fail-closed truncation, and
# that signal is the only log-visibility mechanism for that condition.
redact() {
    [ -x "$REDACT_TMPDIR_HELPER" ] || return 10
    [ -x "$REDACT_HELPER" ] || return 11
    printf '%s' "$1" | "$REDACT_TMPDIR_HELPER" | "$REDACT_HELPER"
}

# redact_gh_error <captured-stderr-text> — same as redact but used on gh
# failure paths to scrub 4xx API responses / token-bearing error text
# before emission in ERROR=. Flattens newlines and truncates to 500 chars
# matching create-one.sh's outbound pattern.
redact_gh_error() {
    local err_text="$1"
    local redacted
    redacted=$(redact "$err_text") || emit_redaction_failure
    printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
}

validate_lifecycle_marker() {
    local marker="$1"
    local LC_ALL=C
    # Reject empty and any byte outside the positive charset (return 1),
    # then reject the substring "--" (return 2). HTML comment data may not
    # contain consecutive hyphens — parsers may terminate the comment early
    # on the first "--" they see, even when followed by a non-">" byte. The
    # split return codes let the caller emit a precise diagnostic.
    case "$marker" in
        *[!A-Za-z0-9._:-]*|"") return 1 ;;
        *--*) return 2 ;;
        *) return 0 ;;
    esac
}

# emit_gh_failure <captured-stderr-text> — redact + emit the KEY=value
# failure envelope and exit 2.
emit_gh_failure() {
    local flat
    flat=$(redact_gh_error "$1")
    emit_kv FAILED "true"
    emit_kv ERROR "$flat"
    exit 2
}

# truncate_body <body> — payloads are no longer comment-truncated; bulky content lives in larch-logs.
truncate_body() {
    printf '%s' "$1"
}

cmd="${1:-}"
if [[ -z "$cmd" ]]; then
    usage
    exit 1
fi
shift

case "$cmd" in
    create-issue)
        TITLE=""
        BODY_FILE=""
        REPO=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --title) TITLE="${2:?--title requires a value}"; shift 2 ;;
                --body-file) BODY_FILE="${2:?--body-file requires a value}"; shift 2 ;;
                --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
                *) echo "Unknown option for create-issue: $1" >&2; usage; exit 1 ;;
            esac
        done
        if [[ -z "$TITLE" ]] || [[ -z "$BODY_FILE" ]]; then
            usage
            exit 1
        fi
        if [[ ! -f "$BODY_FILE" ]]; then
            emit_kv FAILED "true"
            emit_kv ERROR "body file not found: $BODY_FILE"
            exit 1
        fi
        if [[ -z "$REPO" ]]; then
            REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || REPO=""
            if [[ -z "$REPO" ]]; then
                emit_kv FAILED "true"
                emit_kv ERROR "could not determine repo"
                exit 2
            fi
        fi
        TITLE=$(redact "$TITLE") || emit_redaction_failure
        BODY_CONTENT=$(cat "$BODY_FILE")
        if [[ -z "$BODY_CONTENT" ]]; then
            emit_kv FAILED "true"
            emit_kv ERROR "empty body"
            exit 1
        fi
        # Single structural choke point: compose (already composed above as
        # BODY_CONTENT) → redact → truncate. Do NOT reorder: truncation
        # before redaction could slice token-shaped byte sequences.
        BODY_CONTENT=$(redact "$BODY_CONTENT") || emit_redaction_failure
        BODY_CONTENT=$(truncate_body "$BODY_CONTENT")
        BODY_TMP=$(mktemp)
        ERR_TMP=$(mktemp)
                trap 'rm -f "$BODY_TMP" "$ERR_TMP"' EXIT
        printf '%s' "$BODY_CONTENT" > "$BODY_TMP"
        if ISSUE_URL=$(gh issue create --repo "$REPO" --title "$TITLE" --body-file "$BODY_TMP" 2>"$ERR_TMP"); then
            URL_LINE=$(echo "$ISSUE_URL" | grep -oE 'https?://[^[:space:]]+/issues/[0-9]+' | tail -1 || true)
            if [[ -z "$URL_LINE" ]]; then
                ERR_CONTENT=$(cat "$ERR_TMP")
                emit_gh_failure "gh issue create did not emit a URL (stderr: $ERR_CONTENT)"
            fi
            ISSUE_NUM=$(echo "$URL_LINE" | grep -oE '[0-9]+$')
            emit_kv ISSUE_NUMBER "$ISSUE_NUM"
            emit_kv ISSUE_URL "$URL_LINE"
            exit 0
        else
            ERR_CONTENT=$(cat "$ERR_TMP")
            emit_gh_failure "$ERR_CONTENT"
        fi
        ;;

    append-comment)
        ISSUE=""
        BODY_FILE=""
        REPO=""
        LIFECYCLE_MARKER=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                --body-file) BODY_FILE="${2:?--body-file requires a value}"; shift 2 ;;
                --lifecycle-marker)
                    if [[ $# -lt 2 ]]; then
                        echo "Unknown option for append-comment: --lifecycle-marker requires a value" >&2
                        usage
                        exit 1
                    fi
                    LIFECYCLE_MARKER="${2-}"
                    shift 2
                    ;;
                --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
                *) echo "Unknown option for append-comment: $1" >&2; usage; exit 1 ;;
            esac
        done
        if [[ -z "$ISSUE" ]] || [[ -z "$BODY_FILE" ]]; then
            usage
            exit 1
        fi
        if [[ ! -f "$BODY_FILE" ]]; then
            emit_kv FAILED "true"
            emit_kv ERROR "body file not found: $BODY_FILE"
            exit 1
        fi
        if [[ -z "$REPO" ]]; then
            REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || REPO=""
            if [[ -z "$REPO" ]]; then
                emit_kv FAILED "true"
                emit_kv ERROR "could not determine repo"
                exit 2
            fi
        fi
        BODY_CONTENT=$(cat "$BODY_FILE")
        if [[ -z "$BODY_CONTENT" ]]; then
            emit_kv FAILED "true"
            emit_kv ERROR "empty body"
            exit 1
        fi
        if [[ -n "$LIFECYCLE_MARKER" ]]; then
            # Defuse set -e: capture the return code without aborting the script
            # when validate_lifecycle_marker returns non-zero (rc=1 charset
            # rejection, rc=2 "--" substring rejection).
            lifecycle_rc=0
            validate_lifecycle_marker "$LIFECYCLE_MARKER" || lifecycle_rc=$?
            case "$lifecycle_rc" in
                1)
                    emit_kv FAILED "true"
                    emit_kv ERROR "lifecycle-marker contains bytes outside [A-Za-z0-9._:-]; the synthesized HTML comment requires a positive charset to prevent comment-terminator injection. Use a marker containing only ASCII letters, digits, '.', ':', '_', or '-'."
                    exit 1
                    ;;
                2)
                    emit_kv FAILED "true"
                    emit_kv ERROR "lifecycle-marker contains the substring '--'; HTML comment data may not contain consecutive hyphens (parsers may terminate the comment early). Use a single-hyphen-delimited slug like 'pr-opened' or 'in-progress'."
                    exit 1
                    ;;
            esac
            BODY_CONTENT="<!-- larch:lifecycle-marker:${LIFECYCLE_MARKER} -->"$'\n'"$BODY_CONTENT"
        fi
        BODY_CONTENT=$(redact "$BODY_CONTENT") || emit_redaction_failure
        BODY_CONTENT=$(truncate_body "$BODY_CONTENT")
        BODY_TMP=$(mktemp)
        ERR_TMP=$(mktemp)
                trap 'rm -f "$BODY_TMP" "$ERR_TMP"' EXIT
        printf '%s' "$BODY_CONTENT" > "$BODY_TMP"
        if COMMENT_URL=$(gh issue comment "$ISSUE" --repo "$REPO" --body-file "$BODY_TMP" 2>"$ERR_TMP"); then
            URL_LINE=$(echo "$COMMENT_URL" | grep -oE 'https?://[^[:space:]]+#issuecomment-[0-9]+' | tail -1 || true)
            if [[ -z "$URL_LINE" ]]; then
                ERR_CONTENT=$(cat "$ERR_TMP")
                emit_gh_failure "gh issue comment did not emit a URL (stderr: $ERR_CONTENT)"
            fi
            CID=$(echo "$URL_LINE" | grep -oE '[0-9]+$')
            emit_kv COMMENT_ID "$CID"
            emit_kv COMMENT_URL "$URL_LINE"
            exit 0
        else
            ERR_CONTENT=$(cat "$ERR_TMP")
            emit_gh_failure "$ERR_CONTENT"
        fi
        ;;

    rename)
        ISSUE=""
        STATE=""
        REPO=""
        ROUND_TRIP=false
        ROUND_TRIP_FLAG_PASSED=false
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                --state) STATE="${2:?--state requires a value}"; shift 2 ;;
                --round-trip)
                    ROUND_TRIP="${2:?--round-trip requires a value}"
                    ROUND_TRIP_FLAG_PASSED=true
                    shift 2
                    ;;
                --repo)  REPO="${2:?--repo requires a value}"; shift 2 ;;
                *) echo "Unknown option for rename: $1" >&2; usage; exit 1 ;;
            esac
        done
        if [[ -z "$ISSUE" ]] || [[ -z "$STATE" ]]; then
            usage
            exit 1
        fi
        case "$ROUND_TRIP" in
            true|false) ;;
            *)
                emit_kv FAILED "true"
                emit_kv ERROR "invalid --round-trip: $ROUND_TRIP (expected true|false)"
                exit 1
                ;;
        esac
        TARGET_PREFIX=$(state_to_prefix "$STATE") || {
            emit_kv FAILED "true"
            emit_kv ERROR "invalid --state: $STATE (expected in-progress|done|stalled)"
            exit 1
        }
        if [[ -z "$REPO" ]]; then
            REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || REPO=""
            if [[ -z "$REPO" ]]; then
                emit_kv FAILED "true"
                emit_kv ERROR "could not determine repo"
                exit 2
            fi
        fi
        ERR_TMP=$(mktemp)
                trap 'rm -f "$ERR_TMP"' EXIT
        if ! CUR_TITLE=$(gh issue view "$ISSUE" --repo "$REPO" --json title --jq '.title' 2>"$ERR_TMP"); then
            ERR_CONTENT=$(cat "$ERR_TMP")
            emit_gh_failure "gh issue view failed: $ERR_CONTENT"
        fi
        LIFECYCLE_STRIPPED=$(strip_lifecycle_prefix "$CUR_TITLE")
        ROUND_TRIP_PRESENT=false
        if has_round_trip_prefix "$LIFECYCLE_STRIPPED"; then
            ROUND_TRIP_PRESENT=true
        fi
        USER_TAIL=$(strip_round_trip_prefix "$LIFECYCLE_STRIPPED")
        EMIT_RT=false
        if [[ "$ROUND_TRIP_PRESENT" == "true" || "$ROUND_TRIP" == "true" ]]; then
            EMIT_RT=true
        fi
        TITLE_PREFIXES="$TARGET_PREFIX"
        if [[ "$EMIT_RT" == "true" ]]; then
            TITLE_PREFIXES="${TITLE_PREFIXES}[ROUND-TRIP] "
        fi
        NEW_TITLE=$(truncate_title_with_prefixes_to_256 "$TITLE_PREFIXES" "$USER_TAIL")
        # Redact before length check: redacted content may differ in byte
        # length from input (e.g., "<REDACTED-TOKEN>" replaces a longer
        # token). Length check must be on the actual outbound title.
        NEW_TITLE=$(redact "$NEW_TITLE") || emit_redaction_failure
        # Re-run prefix-preserving truncation after redaction. The redactor
        # can change the user-tail length; managed prefixes must remain.
        REDACTED_LIFECYCLE_STRIPPED=$(strip_lifecycle_prefix "$NEW_TITLE")
        REDACTED_USER_TAIL=$(strip_round_trip_prefix "$REDACTED_LIFECYCLE_STRIPPED")
        NEW_TITLE=$(truncate_title_with_prefixes_to_256 "$TITLE_PREFIXES" "$REDACTED_USER_TAIL")
        # Idempotency comparison: compare the prospective outbound title
        # against the redacted+truncated form of the CURRENT title so a
        # title that already carries a redactable token is not spuriously
        # re-edited (which would both violate the no-op contract AND
        # rewrite the on-GitHub title to the redacted form without
        # changing the lifecycle state). CUR_TITLE is the raw GitHub
        # title; applying the same redact+truncate pipeline yields the
        # canonical "what would we emit if the state was already X?" form.
        CUR_TITLE_CANONICAL=$(redact "$CUR_TITLE") || emit_redaction_failure
        CUR_CANON_LIFECYCLE_STRIPPED=$(strip_lifecycle_prefix "$CUR_TITLE_CANONICAL")
        CUR_CANON_RT_PRESENT=false
        if has_round_trip_prefix "$CUR_CANON_LIFECYCLE_STRIPPED"; then
            CUR_CANON_RT_PRESENT=true
        fi
        CUR_CANON_USER_TAIL=$(strip_round_trip_prefix "$CUR_CANON_LIFECYCLE_STRIPPED")
        CUR_CANON_PREFIXES=""
        case "$CUR_TITLE_CANONICAL" in
            '[IN PROGRESS] '*) CUR_CANON_PREFIXES='[IN PROGRESS] ' ;;
            '[DONE] '*)        CUR_CANON_PREFIXES='[DONE] ' ;;
            '[STALLED] '*)     CUR_CANON_PREFIXES='[STALLED] ' ;;
            *)                 CUR_CANON_PREFIXES="" ;;
        esac
        if [[ "$CUR_CANON_RT_PRESENT" == "true" ]]; then
            CUR_CANON_PREFIXES="${CUR_CANON_PREFIXES}[ROUND-TRIP] "
        fi
        CUR_TITLE_CANONICAL=$(truncate_title_with_prefixes_to_256 "$CUR_CANON_PREFIXES" "$CUR_CANON_USER_TAIL")
        ROUND_TRIP_APPLIED=false
        NEW_LIFECYCLE_STRIPPED=$(strip_lifecycle_prefix "$NEW_TITLE")
        if has_round_trip_prefix "$NEW_LIFECYCLE_STRIPPED"; then
            ROUND_TRIP_APPLIED=true
        fi
        if [[ "$NEW_TITLE" == "$CUR_TITLE_CANONICAL" ]]; then
            emit_kv RENAMED "false"
            emit_kv NEW_TITLE "$NEW_TITLE"
            if [[ "$ROUND_TRIP_FLAG_PASSED" == "true" ]]; then
                emit_kv ROUND_TRIP_APPLIED "$ROUND_TRIP_APPLIED"
            fi
            exit 0
        fi
        if ! gh issue edit "$ISSUE" --repo "$REPO" --title "$NEW_TITLE" >/dev/null 2>"$ERR_TMP"; then
            ERR_CONTENT=$(cat "$ERR_TMP")
            emit_gh_failure "gh issue edit failed: $ERR_CONTENT"
        fi
        emit_kv RENAMED "true"
        emit_kv NEW_TITLE "$NEW_TITLE"
        if [[ "$ROUND_TRIP_FLAG_PASSED" == "true" ]]; then
            emit_kv ROUND_TRIP_APPLIED "$ROUND_TRIP_APPLIED"
        fi
        exit 0
        ;;

    mark-false-positive)
        ISSUE=""
        REPO=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                --repo)  REPO="${2:?--repo requires a value}"; shift 2 ;;
                *) echo "Unknown option for mark-false-positive: $1" >&2; usage; exit 1 ;;
            esac
        done
        if [[ -z "$ISSUE" ]]; then
            usage
            exit 1
        fi
        if [[ ! -f "$TITLE_MARKERS_HELPER" ]]; then
            emit_kv FAILED "true"
            emit_kv ERROR "missing helper: $TITLE_MARKERS_HELPER"
            exit 1
        fi
        # shellcheck source=scripts/lib-title-markers.sh
        # shellcheck disable=SC1091
        source "$TITLE_MARKERS_HELPER"
        if [[ -z "$REPO" ]]; then
            REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || REPO=""
            if [[ -z "$REPO" ]]; then
                emit_kv FAILED "true"
                emit_kv ERROR "could not determine repo"
                exit 2
            fi
        fi
        ERR_TMP=$(mktemp)
                trap 'rm -f "$ERR_TMP"' EXIT
        if ! CUR_TITLE=$(gh issue view "$ISSUE" --repo "$REPO" --json title --jq '.title' 2>"$ERR_TMP"); then
            ERR_CONTENT=$(cat "$ERR_TMP")
            emit_gh_failure "gh issue view failed: $ERR_CONTENT"
        fi
        CUR_TITLE_REDACTED=$(redact "$CUR_TITLE") || emit_redaction_failure
        NEW_TITLE=$(insert_signal_marker "$CUR_TITLE_REDACTED" "FALSE-POSITIVE")
        if [[ "$NEW_TITLE" == "$CUR_TITLE_REDACTED" ]]; then
            emit_kv MARKED "false"
            emit_kv NEW_TITLE "$CUR_TITLE_REDACTED"
            exit 0
        fi
        NEW_TITLE=$(truncate_title_to_256 "$NEW_TITLE")
        if ! gh issue edit "$ISSUE" --repo "$REPO" --title "$NEW_TITLE" >/dev/null 2>"$ERR_TMP"; then
            ERR_CONTENT=$(cat "$ERR_TMP")
            emit_gh_failure "gh issue edit failed: $ERR_CONTENT"
        fi
        emit_kv MARKED "true"
        emit_kv NEW_TITLE "$NEW_TITLE"
        exit 0
        ;;

    *)
        echo "Unknown subcommand: $cmd" >&2
        usage
        exit 1
        ;;
esac
