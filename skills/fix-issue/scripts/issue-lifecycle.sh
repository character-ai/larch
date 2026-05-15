#!/usr/bin/env bash
# issue-lifecycle.sh — GitHub issue lifecycle operations.
#
# Subcommand-based script for commenting on, closing, and updating issues.
#
# Usage:
#   issue-lifecycle.sh comment --issue NUMBER --body TEXT [--lock]
#   issue-lifecycle.sh comment --issue NUMBER --body TEXT --lock-no-go
#   issue-lifecycle.sh close   --issue NUMBER [--comment TEXT] [--pr-url URL] [--close-class CLASS] [--mark-false-positive-if-keyword]
#   issue-lifecycle.sh update-body --issue NUMBER --pr-url URL
#
# Subcommands:
#   comment    — Post a comment on an issue.
#                With --lock: verify last comment is "GO", DELETE that GO
#                comment, then post the new comment (typically "IN PROGRESS").
#                Re-reads afterward to detect concurrent duplicate locks via
#                "IN PROGRESS" comments created after the deleted GO timestamp.
#                Called by `find-lock-issue.sh` at /fix-issue Step 0 for
#                the existing GO-tail leaf-issue path.
#                With --lock-no-go: lock without requiring a GO comment in
#                the tail. Used for umbrella-dispatched children (which
#                inherit approval from the umbrella's own existence as the
#                approval signal — no per-child GO required). Refuses if the
#                tail is already "IN PROGRESS"; snapshots the last comment's
#                created_at as the duplicate-detection anchor (or the issue's
#                own createdAt when the issue has zero comments — a no-comment
#                safe fallback, FINDING_4 from the umbrella-PR plan review);
#                posts "IN PROGRESS"; post-checks for OTHER "IN PROGRESS"
#                comments (excluding the runner's own just-posted comment by
#                id) created at >= snapshot_ts. The two flags are mutually
#                exclusive. Called by `find-lock-issue.sh` for the umbrella
#                child-dispatch path.
#   close      — Close an issue. Optionally post a comment first.
#                With --pr-url: update the issue body with the PR link before closing.
#                With --close-class CLASS (one of false-positive|duplicate|
#                superseded|done): after CLOSED=true, deterministically decide
#                the [FALSE-POSITIVE] title marker — mark on false-positive,
#                duplicate, superseded; skip on done. The closing comment is
#                NOT scanned. When --close-class is also paired with
#                --mark-false-positive-if-keyword, the enum wins silently.
#                With --mark-false-positive-if-keyword (legacy fallback for
#                unstructured-prose closes): after CLOSED=true, scan the
#                closing comment and best-effort add [FALSE-POSITIVE] to the
#                issue title on keyword match.
#                Called by /fix-issue Step 3 (not-material close — passes
#                --close-class) and Step 6b (NON_PR DONE close — passes
#                --close-class done; Step 6a PR path omits this call since
#                GitHub auto-closes the issue on PR merge).
#   update-body — Append a PR link to the issue body (idempotent).
#
# Exit codes:
#   0 — success
#   1 — lock verification failed, state changed, or API error
#   2 — usage error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

TRACKING_WRITE="${LARCH_TEST_TRACKING_WRITE_PATH:-${SCRIPT_DIR}/../../../scripts/tracking-issue-write.sh}"
FALSE_POSITIVE_KEYWORDS_LIB="${SCRIPT_DIR}/../../../scripts/false-positive-keywords.sh"
RESOLVE_REPO="${SCRIPT_DIR}/../../../scripts/resolve-repo.sh"

# Propagation pause (seconds) between posting a lock comment and re-fetching
# the comment list to verify no duplicate-runner race. Default 1s gives
# GitHub time to make the new comment visible via the API. Test harnesses
# that stub `gh` set this to 0 because the stub returns synthetic state
# instantly. Accepts integer or decimal seconds.
ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS="${ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS:-1}"
case "$ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS" in
    ''|*[!0-9.]*|.) larch_err "ERROR=ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS must be a non-negative number, got '$ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS'"; exit 2 ;;
esac
case "$ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS" in
    *.*.*) larch_err "ERROR=ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS must be a non-negative number, got '$ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS'"; exit 2 ;;
esac

# ---------------------------------------------------------------------------
# Resolve repo identity (shared across subcommands)
# ---------------------------------------------------------------------------
REPO=$("$RESOLVE_REPO" 2>/dev/null) || {
    larch_err "ERROR=Failed to resolve repository name"
    exit 1
}
GH_ISSUE_REPO_ARGS=(--repo "$REPO")

# ---------------------------------------------------------------------------
# Subcommand: comment
# ---------------------------------------------------------------------------
cmd_comment() {
    local issue="" body="" lock=false lock_no_go=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --issue) issue="${2:?--issue requires a value}"; shift 2 ;;
            --body) body="${2:?--body requires a value}"; shift 2 ;;
            --lock) lock=true; shift ;;
            --lock-no-go) lock_no_go=true; shift ;;
            *) larch_err "Unknown option for comment: $1"; exit 2 ;;
        esac
    done

    if [[ -z "$issue" ]] || [[ -z "$body" ]]; then
        larch_err "Usage: issue-lifecycle.sh comment --issue N --body TEXT [--lock | --lock-no-go]"
        exit 2
    fi

    if [ "$lock" = true ] && [ "$lock_no_go" = true ]; then
        emit_kv LOCK_ACQUIRED false
        emit_kv ERROR "--lock and --lock-no-go are mutually exclusive"
        exit 1
    fi

    local go_ts=""
    local snapshot_ts=""
    local just_posted_id=""

    # --lock: verify last comment is "GO", capture its id + timestamp, then
    # delete it so the GO sentinel does not remain on the issue after locking.
    if [ "$lock" = true ]; then
        local comments_json
        comments_json=$(gh api --paginate --slurp "repos/${REPO}/issues/${issue}/comments" 2>/dev/null | jq 'add // []') || {
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to read comments for lock verification"
            exit 1
        }

        local last_body last_id
        last_body=$(echo "$comments_json" | jq -r '.[-1].body // empty')
        last_id=$(echo "$comments_json" | jq -r '.[-1].id // empty')
        go_ts=$(echo "$comments_json" | jq -r '.[-1].created_at // empty')

        local trimmed
        trimmed=$(echo "$last_body" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        if [ "$trimmed" != "GO" ]; then
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Last comment is no longer GO (found: ${trimmed:-empty})"
            exit 1
        fi

        if [[ -z "$last_id" ]] || [[ -z "$go_ts" ]]; then
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to extract GO comment id/timestamp for deletion"
            exit 1
        fi

        # Delete the GO comment. The post-check below uses $go_ts (captured
        # above) as the duplicate-detection sentinel in place of a surviving
        # GO anchor.
        gh api -X DELETE "repos/${REPO}/issues/comments/${last_id}" >/dev/null 2>&1 || {
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to delete GO comment on issue #$issue"
            exit 1
        }
    fi

    # --lock-no-go: lock without requiring or deleting a GO comment. Refuse
    # if the tail is already "IN PROGRESS" (would conflict with a concurrent
    # /fix-issue runner already holding the lock). Snapshot the duplicate-
    # detection anchor BEFORE posting: prefer the last comment's created_at;
    # fall back to the issue's own createdAt when the issue has zero comments
    # (FINDING_4 — a no-comment-safe anchor for fresh /umbrella batch-created
    # children). The runner's own just-posted comment id is captured after
    # posting so the post-check can exclude it via id mismatch.
    if [ "$lock_no_go" = true ]; then
        local comments_json
        comments_json=$(gh api --paginate --slurp "repos/${REPO}/issues/${issue}/comments" 2>/dev/null | jq 'add // []') || {
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to read comments for lock-no-go pre-check"
            exit 1
        }

        local n_comments
        n_comments=$(echo "$comments_json" | jq 'length')

        if [[ "$n_comments" -gt 0 ]]; then
            local last_body
            last_body=$(echo "$comments_json" | jq -r '.[-1].body // empty')
            local trimmed
            trimmed=$(echo "$last_body" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [ "$trimmed" = "IN PROGRESS" ]; then
                emit_kv LOCK_ACQUIRED false
                emit_kv ERROR "Issue #$issue is already locked (last comment: IN PROGRESS)"
                exit 1
            fi
            snapshot_ts=$(echo "$comments_json" | jq -r '.[-1].created_at // empty')
        fi

        if [[ -z "$snapshot_ts" ]]; then
            # No-comment-safe fallback (FINDING_4): use the issue's own createdAt.
            snapshot_ts=$(gh issue view "$issue" "${GH_ISSUE_REPO_ARGS[@]}" --json createdAt --jq '.createdAt // empty' 2>/dev/null) || {
                emit_kv LOCK_ACQUIRED false
                emit_kv ERROR "Failed to read issue #$issue createdAt for snapshot anchor"
                exit 1
            }
            if [[ -z "$snapshot_ts" ]]; then
                emit_kv LOCK_ACQUIRED false
                emit_kv ERROR "Failed to determine snapshot anchor timestamp for issue #$issue"
                exit 1
            fi
        fi
    fi

    # Post the comment
    gh issue comment "$issue" "${GH_ISSUE_REPO_ARGS[@]}" --body "$body" >/dev/null 2>&1 || {
        emit_kv LOCK_ACQUIRED false
        emit_kv ERROR "Failed to post comment on issue #$issue"
        exit 1
    }

    # Capture the just-posted comment's id for --lock-no-go post-check
    # (FINDING_4: explicit id exclusion makes the >= snapshot_ts comparator
    # safe even when same-second timestamps tie). `gh issue comment` does NOT
    # print the comment id, so we re-fetch the most recent comment whose body
    # matches the posted body — its id is the runner's own. If multiple
    # matches exist (a duplicate race), this pick matches the most recent
    # one; the post-check below will still detect duplicates because both
    # IN PROGRESS comments will have created_at >= snapshot_ts and only ONE
    # will be excluded by id, leaving the other to trigger the >0 race count.
    if [ "$lock_no_go" = true ]; then
        # Brief pause to let GitHub propagate
        sleep "$ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS"
        local refresh_json
        refresh_json=$(gh api --paginate --slurp "repos/${REPO}/issues/${issue}/comments" 2>/dev/null | jq 'add // []') || {
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to refresh comments for lock-no-go id capture"
            exit 1
        }
        just_posted_id=$(echo "$refresh_json" | jq --arg b "$body" --arg ts "$snapshot_ts" '
            [.[] | select(.body == $b and .created_at >= $ts)] | sort_by(.created_at) | (.[-1].id // empty)' \
            | tr -d '"')
        # Fail closed if id capture returned empty: the post-check below
        # excludes the runner's own comment via `(.id | tostring) != $self`,
        # and an empty $self would never match, so the runner's own IN PROGRESS
        # would be counted in race_count and produce a spurious duplicate-
        # detection failure. An empty id here is unrecoverable — the post-
        # check's exclusion semantics are not defensible — so surface the
        # condition explicitly rather than letting the lock surface a mis-
        # diagnosed "Duplicate IN PROGRESS" error a few lines down.
        if [[ -z "$just_posted_id" ]]; then
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to identify just-posted IN PROGRESS comment id for lock-no-go duplicate check"
            exit 1
        fi
    fi

    # --lock post-check: verify no duplicate lock comment
    if [ "$lock" = true ]; then
        # Brief pause to let GitHub propagate
        sleep "$ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS"

        local comments_json
        comments_json=$(gh api --paginate --slurp "repos/${REPO}/issues/${issue}/comments" 2>/dev/null | jq 'add // []') || {
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to re-read comments for duplicate check"
            exit 1
        }

        # Count IN PROGRESS comments created strictly after the deleted GO's
        # timestamp. Two concurrent runners that both raced the pre-check will
        # see count > 1 here.
        local lock_count
        lock_count=$(echo "$comments_json" | jq --arg ts "$go_ts" '
            [.[] | select(.body == "IN PROGRESS" and .created_at > $ts)] | length')

        if [ "$lock_count" -gt 1 ]; then
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Duplicate IN PROGRESS detected ($lock_count found) — concurrent lock race"
            exit 1
        fi

        emit_kv LOCK_ACQUIRED true
    fi

    # --lock-no-go post-check: count OTHER IN PROGRESS comments with
    # created_at >= snapshot_ts (excluding the runner's own just-posted id).
    # `>0` means another runner won the race. The comparator is `>=`
    # (inclusive) — distinct from `--lock`'s strict `>` because the snapshot
    # anchor itself remains in the comment stream (whereas --lock deletes the
    # GO comment, making strict `>` correct there). The runner's own comment
    # is excluded by id, so >= can never count this runner's own post.
    if [ "$lock_no_go" = true ]; then
        local refresh_json
        refresh_json=$(gh api --paginate --slurp "repos/${REPO}/issues/${issue}/comments" 2>/dev/null | jq 'add // []') || {
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Failed to re-read comments for lock-no-go duplicate check"
            exit 1
        }

        local race_count
        race_count=$(echo "$refresh_json" | jq --arg ts "$snapshot_ts" --arg self "$just_posted_id" '
            [.[] | select(.body == "IN PROGRESS" and .created_at >= $ts and ((.id | tostring) != $self))] | length')

        if [ "$race_count" -gt 0 ]; then
            emit_kv LOCK_ACQUIRED false
            emit_kv ERROR "Duplicate IN PROGRESS detected ($race_count concurrent) — lock-no-go race"
            exit 1
        fi

        emit_kv LOCK_ACQUIRED true
    fi

    emit_kv COMMENTED true
}

# ---------------------------------------------------------------------------
# Subcommand: close
# ---------------------------------------------------------------------------
cmd_close() {
    local issue="" comment="" pr_url="" mark_false_positive=false close_class=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --issue) issue="${2:?--issue requires a value}"; shift 2 ;;
            --comment) comment="${2:?--comment requires a value}"; shift 2 ;;
            --pr-url) pr_url="${2:?--pr-url requires a value}"; shift 2 ;;
            --close-class) close_class="${2:?--close-class requires a value}"; shift 2 ;;
            --mark-false-positive-if-keyword) mark_false_positive=true; shift ;;
            *) larch_err "Unknown option for close: $1"; exit 2 ;;
        esac
    done

    if [[ -z "$issue" ]]; then
        larch_err "Usage: issue-lifecycle.sh close --issue N [--comment TEXT] [--pr-url URL] [--close-class false-positive|duplicate|superseded|done] [--mark-false-positive-if-keyword]"
        exit 2
    fi

    if [[ -n "$close_class" ]]; then
        case "$close_class" in
            false-positive|duplicate|superseded|done) ;;
            *)
                larch_err "Usage: issue-lifecycle.sh close --close-class must be one of: false-positive, duplicate, superseded, done (got '$close_class')"
                exit 2
                ;;
        esac
    fi

    # Update body with PR link if provided (idempotent). Suppress stdout so
    # cmd_update_body's UPDATED=/SKIPPED= keys never leak into cmd_close's
    # stdout — the caller-visible contract is CLOSED=true (or CLOSED=false + ERROR=).
    if [[ -n "$pr_url" ]]; then
        cmd_update_body --issue "$issue" --pr-url "$pr_url" >/dev/null 3>/dev/null || {
            emit_kv CLOSED false
            emit_kv ERROR "Failed to update issue #$issue body with PR link"
            exit 1
        }
    fi

    # Post comment first if provided
    if [[ -n "$comment" ]]; then
        gh issue comment "$issue" "${GH_ISSUE_REPO_ARGS[@]}" --body "$comment" >/dev/null 2>&1 || {
            emit_kv CLOSED false
            emit_kv ERROR "Failed to post closing comment on issue #$issue"
            exit 1
        }
    fi

    # Idempotency guard: probe current state before attempting close. If the
    # issue is already CLOSED (e.g., GitHub auto-closed it via `Closes #<N>`
    # on PR merge), skip the `gh issue close` call but still emit CLOSED=true
    # on stdout so /fix-issue Step 6b's stdout parser cannot distinguish the
    # paths (stderr carries an INFO note; stdout contract is byte-stable).
    # On probe failure, log a WARNING to stderr and fall through to the
    # existing close path rather than hard-failing — this preserves the
    # pre-PR OPEN-path reliability (a transient `gh issue view` blip must
    # not abort a close that would otherwise have succeeded).
    # Exact match on "CLOSED": /fix-issue only ever passes issue numbers
    # (never PR numbers), so MERGED and other PR-state values never appear here.
    local current_state probe_ok=1
    current_state=$(gh issue view "$issue" "${GH_ISSUE_REPO_ARGS[@]}" --json state --jq '.state' 2>/dev/null) || probe_ok=0

    if (( probe_ok )) && [ "$current_state" = "CLOSED" ]; then
        larch_err "INFO: issue #$issue already closed; backfilling DONE metadata only"
    else
        if (( ! probe_ok )); then
            larch_err "WARNING: failed to probe state for issue #$issue; attempting close anyway"
        fi
        gh issue close "$issue" "${GH_ISSUE_REPO_ARGS[@]}" >/dev/null 2>&1 || {
            emit_kv CLOSED false
            emit_kv ERROR "Failed to close issue #$issue"
            exit 1
        }
    fi

    emit_kv CLOSED true

    # Marker decision. Precedence: --close-class wins over the legacy
    # --mark-false-positive-if-keyword keyword scan. The enum drives the
    # decision deterministically at decision time; the closing comment is
    # never inspected.
    local should_mark=false
    if [[ -n "$close_class" ]]; then
        case "$close_class" in
            false-positive|duplicate|superseded) should_mark=true ;;
            done) should_mark=false ;;
        esac
        if [ "$should_mark" = true ]; then
            _run_false_positive_marker "$issue"
        fi
    elif [ "$mark_false_positive" = true ] && [[ -n "$comment" ]]; then
        # shellcheck source=scripts/false-positive-keywords.sh
        # shellcheck disable=SC1090
        source "$FALSE_POSITIVE_KEYWORDS_LIB"
        local keyword_rc=0
        matches_false_positive_keywords "$comment" || keyword_rc=$?
        if [ "$keyword_rc" -eq 0 ]; then
            _run_false_positive_marker "$issue"
        elif [ "$keyword_rc" -ge 2 ]; then
            larch_err "WARNING: false-positive keyword scan failed for issue #$issue"
        fi
    fi
}

# _run_false_positive_marker — best-effort invocation of
# `tracking-issue-write.sh mark-false-positive`. Failure never changes
# stdout or exit status after a successful close; emits a redacted
# WARNING on stderr. Shared between the --close-class enum path and
# the legacy keyword path.
_run_false_positive_marker() {
    local issue="$1"
    local mark_out mark_stderr mark_exit=0 err_value
    mark_stderr=$(mktemp)
    mark_out=$("$TRACKING_WRITE" mark-false-positive --issue "$issue" --repo "$REPO" 2>"$mark_stderr") || mark_exit=$?
    if [ "$mark_exit" -ne 0 ] || printf '%s\n' "$mark_out" | grep -q '^FAILED=true'; then
        err_value=$(printf '%s\n' "$mark_out" | grep -oE '^ERROR=.*' | head -1 | sed 's/^ERROR=//')
        larch_err "WARNING: mark-false-positive failed for issue #$issue: ${err_value:-unknown}"
    fi
    # SECURITY.md (Phase 1 helper paragraph) declares that raw marker stderr
    # is discarded unless a complete redactor pass succeeds. Buffer first so a
    # crashing redactor cannot leak partial token-bearing output to stderr.
    if [ -s "$mark_stderr" ]; then
        local redactor="${LARCH_TEST_REDACTOR_PATH:-$SCRIPT_DIR/../../../scripts/redact-secrets.sh}"
        local mark_redacted_tmp
        mark_redacted_tmp=$(mktemp "${TMPDIR:-/tmp}/mark-redacted.XXXXXX") || mark_redacted_tmp=""
        local _redactor_exit=127
        if [ -n "$mark_redacted_tmp" ] && [ -x "$redactor" ]; then
            if "$redactor" < "$mark_stderr" > "$mark_redacted_tmp" 2>/dev/null; then
                _redactor_exit=0
            else
                _redactor_exit=$?
            fi
        fi
        local _stderr_size
        _stderr_size=$(wc -c < "$mark_stderr" 2>/dev/null | tr -d ' ')
        _stderr_size="${_stderr_size:-0}"
        if [ "$_redactor_exit" -eq 0 ] && [ -s "$mark_redacted_tmp" ]; then
            while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$mark_redacted_tmp"
        elif [ "$_redactor_exit" -eq 0 ]; then
            # Redactor ran successfully but produced no output — the input
            # was entirely sensitive content the scrubber consumed. Emit a
            # neutral INFO line so operators don't interpret a clean redaction
            # as a failure (round-5 review FINDING_1).
            larch_err "INFO: mark-false-positive stderr fully redacted (${_stderr_size} bytes consumed, no surviving output)"
        else
            larch_err "WARNING: mark-false-positive stderr suppressed: redactor exit=${_redactor_exit} (${_stderr_size} bytes discarded)"
        fi
        [ -n "$mark_redacted_tmp" ] && rm -f "$mark_redacted_tmp"
    fi
    rm -f "$mark_stderr"
}

# ---------------------------------------------------------------------------
# Subcommand: update-body
# ---------------------------------------------------------------------------
cmd_update_body() {
    local issue="" pr_url=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --issue) issue="${2:?--issue requires a value}"; shift 2 ;;
            --pr-url) pr_url="${2:?--pr-url requires a value}"; shift 2 ;;
            *) larch_err "Unknown option for update-body: $1"; return 2 ;;
        esac
    done

    if [[ -z "$issue" ]] || [[ -z "$pr_url" ]]; then
        larch_err "Usage: issue-lifecycle.sh update-body --issue N --pr-url URL"
        return 2
    fi

    # Read current body
    local current_body
    current_body=$(gh issue view "$issue" "${GH_ISSUE_REPO_ARGS[@]}" --json body --jq '.body // ""' 2>/dev/null) || {
        emit_kv UPDATED false
        emit_kv ERROR "Failed to read issue #$issue body"
        return 1
    }

    # Idempotency check: skip if PR URL already present
    if echo "$current_body" | grep -qF "$pr_url"; then
        emit_kv UPDATED true
        emit_kv SKIPPED already_present
        return 0
    fi

    # Append PR link
    local new_body="${current_body}

**PR**: ${pr_url}"

    gh issue edit "$issue" "${GH_ISSUE_REPO_ARGS[@]}" --body "$new_body" >/dev/null 2>&1 || {
        emit_kv UPDATED false
        emit_kv ERROR "Failed to update issue #$issue body"
        return 1
    }

    emit_kv UPDATED true
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    larch_err "Usage: issue-lifecycle.sh <comment|close|update-body> [options]"
    exit 2
fi

SUBCOMMAND="$1"
shift

case "$SUBCOMMAND" in
    comment) cmd_comment "$@" ;;
    close) cmd_close "$@" ;;
    update-body) cmd_update_body "$@" ;;
    *) larch_err "Unknown subcommand: $SUBCOMMAND"; exit 2 ;;
esac
