#!/usr/bin/env bash
# create-pr.sh — Push branch and create a GitHub PR.
#
# Checks for an existing open PR on the current branch first.
# If none exists, pushes the branch and creates a new PR.
#
# Usage:
#   create-pr.sh --title TEXT --body-file FILE [--draft] [--repo OWNER/REPO] [--base BASE_REF]
#
# Arguments:
#   --title     — PR title (under 70 chars recommended)
#   --body-file — Path to a file containing the PR body (markdown)
#   --draft     — Create the PR in draft state (optional)
#   --base      — Base branch for new PRs (optional; defaults to repo default branch, then main)
#
# Outputs (key=value to stdout):
#   PR_NUMBER=<N>
#   PR_URL=<url>
#   PR_TITLE=<title>
#   PR_STATUS=created|existing
#
# Exit codes:
#   0 — success (PR created or already exists)
#   1 — push failed or dirty-tree guard aborted before push
#   2 — guard/setup/PR creation failed

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REDACT_TMPDIR_HELPER="$REPO_ROOT/scripts/redact-tmpdir-paths.sh"
REDACT_SECRETS_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

GIT_STATUS_STDERR=""
PR_STDERR_FILE=""
PR_STDOUT_FILE=""
REDACTED_BODY_FILE=""
NET_FAIL_FILES=()
cleanup() {
    rm -f "${NET_FAIL_FILES[@]}" "$GIT_STATUS_STDERR" "$PR_STDERR_FILE" "$PR_STDOUT_FILE" "$REDACTED_BODY_FILE"
}
trap cleanup EXIT

usage() { larch_err "Usage: create-pr.sh --title TEXT --body-file FILE [--draft] [--repo OWNER/REPO] [--base BASE_REF]"; }

redact_diagnostic() {
    local text="$1"
    local redacted
    local status=0
    if [[ ! -x "$REDACT_TMPDIR_HELPER" ]] || [[ ! -x "$REDACT_SECRETS_HELPER" ]]; then
        printf '%s' 'diagnostic redaction unavailable'
        return 0
    fi
    redacted=$(printf '%s' "$text" | "$REDACT_TMPDIR_HELPER" | "$REDACT_SECRETS_HELPER") || status=$?
    if [[ "$status" -ne 0 ]]; then
        printf '%s' 'diagnostic redaction unavailable'
        return 0
    fi
    case "$redacted" in
        *'[content truncated'*)
            printf '%s' 'diagnostic redaction unavailable'
            return 0
            ;;
    esac
    printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
}

TITLE=""
BODY_FILE=""
DRAFT=false
TARGET_REPO=""
BASE_REF=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --title) TITLE="${2:?--title requires a value}"; shift 2 ;;
        --body-file) BODY_FILE="${2:?--body-file requires a value}"; shift 2 ;;
        --draft) DRAFT=true; shift ;;
        --repo) TARGET_REPO="${2:?--repo requires a value}"; shift 2 ;;
        --base) BASE_REF="${2:?--base requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 2 ;;
    esac
done

if [[ -z "$TITLE" ]] || [[ -z "$BODY_FILE" ]]; then
    larch_err "ERROR: --title and --body-file are required"
    usage; exit 2
fi

if [[ ! -f "$BODY_FILE" ]]; then
    larch_err "ERROR: Body file not found: $BODY_FILE"
    exit 2
fi

GH_REPO_ARGS=()
if [[ -z "$TARGET_REPO" ]]; then
    TARGET_REPO=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null) || TARGET_REPO=""
fi
if [[ -n "$TARGET_REPO" ]]; then
    if [[ ! "$TARGET_REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
        larch_err "ERROR: --repo must be OWNER/REPO using GitHub owner/repo characters"
        exit 2
    fi
    GH_REPO_ARGS=(--repo "$TARGET_REPO")
fi

if [[ ! -x "$REDACT_TMPDIR_HELPER" ]]; then
    larch_err "ERROR: Redaction helper missing or not executable: redact-tmpdir-paths.sh"
    exit 2
fi
REDACTED_BODY_FILE=$(mktemp)
if ! "$REDACT_TMPDIR_HELPER" < "$BODY_FILE" > "$REDACTED_BODY_FILE"; then
    larch_err "ERROR: Failed to redact PR body tmpdir paths"
    exit 2
fi

# Pre-push clean-tree guard: uncommitted working-tree changes are silently
# excluded from a push, causing data loss (issue #2434).
GIT_STATUS_STDERR=$(mktemp)
if ! DIRTY_FILES=$(git status --porcelain 2>"$GIT_STATUS_STDERR"); then
    larch_err "ERROR: Failed to inspect working tree before push: $(cat "$GIT_STATUS_STDERR")"
    exit 2
fi
if [[ -n "$DIRTY_FILES" ]]; then
    larch_err "ERROR: Uncommitted working-tree changes detected before push. These will NOT be included in the merged PR. Stage and commit them, or discard them, before pushing."
    larch_err "$DIRTY_FILES"
    exit 1
fi

# --- Get current branch ---
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
if [[ -z "$BRANCH" ]]; then
    larch_err "ERROR: Not on a branch (detached HEAD)"
    exit 2
fi

# --- Check for existing open PR ---
EXISTING_PR=$(gh pr view ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} --json number,url,state,title 2>/dev/null || echo "")
if [[ -n "$EXISTING_PR" ]]; then
    PR_STATE=$(echo "$EXISTING_PR" | jq -r '.state // empty' 2>/dev/null || echo "")
    if [[ "$PR_STATE" == "OPEN" ]]; then
        PR_NUMBER=$(echo "$EXISTING_PR" | jq -r '.number // empty' 2>/dev/null || echo "")
        PR_URL=$(echo "$EXISTING_PR" | jq -r '.url // empty' 2>/dev/null || echo "")
        if [[ -n "$PR_NUMBER" ]] && [[ -n "$PR_URL" ]]; then
            # Push any new local commits before returning. Fail closed on real
            # push errors rather than swallowing them — a stale remote on an
            # OPEN PR is exactly the silent-failure mode this branch must avoid.
            push_fail_file=$(mktemp "${TMPDIR:-/tmp}/create-pr-push.XXXXXX")
            NET_FAIL_FILES+=("$push_fail_file")
            if with_transient_retry transient_envelope_predicate_none "$push_fail_file" \
                git push -u origin HEAD; then
                push_rc=0
            else
                push_rc=$_WTR_RC
            fi
            if [[ "$push_rc" -ne 0 ]]; then
                # Plain push failed — commonly non-fast-forward after history
                # rewrite (e.g., /implement Step 12 rebase + re-bump). Escalate
                # to force-with-lease via the shared helper, which encodes
                # lease + race-recovery + single retry.
                # The helper does `git push --force-with-lease` with no refspec
                # and requires upstream tracking + a populated origin/$BRANCH ref:
                git fetch origin "$BRANCH" 2>/dev/null || true
                git branch --set-upstream-to="origin/$BRANCH" "$BRANCH" >/dev/null 2>&1 || true
                # Suppress helper stdout (BRANCH=/PUSHED=/STATUS= keys) so the
                # PR_* stdout contract this script publishes stays intact;
                # capture helper stderr to surface on real failure.
                if ! "$SCRIPT_DIR/git-force-push.sh" >/dev/null 2>>"$push_fail_file"; then
                    larch_err "ERROR: Failed to push branch on existing-PR fast-path: $(redact_diagnostic "$(cat "$push_fail_file" 2>/dev/null || true)")"
                    exit 1
                fi
            fi
            # Fetch the existing PR title
            PR_TITLE=$(echo "$EXISTING_PR" | jq -r '.title // empty' 2>/dev/null || echo "")
            if [[ -z "$PR_TITLE" ]]; then
                PR_TITLE=$(gh pr view "$PR_NUMBER" ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} --json title -q '.title' 2>/dev/null || echo "")
            fi
            emit_kv PR_NUMBER "$PR_NUMBER"
            emit_kv PR_URL "$PR_URL"
            emit_kv PR_TITLE "$PR_TITLE"
            emit_kv PR_STATUS "existing"
            exit 0
        fi
    fi
fi

recover_existing_pr_after_create_conflict() {
    local conflict_text="$1"
    local pr_json pr_number pr_url pr_title

    case "$conflict_text" in
        *"pull request for branch"*"already exists"*) ;;
        *) return 1 ;;
    esac

    pr_json=$(gh pr list \
        ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} \
        --head "$BRANCH" \
        --state open \
        --json number,url,title \
        --limit 1 \
        2>/dev/null || echo "")
    pr_number=$(printf '%s\n' "$pr_json" | jq -r '.[0].number // empty' 2>/dev/null || echo "")
    pr_url=$(printf '%s\n' "$pr_json" | jq -r '.[0].url // empty' 2>/dev/null || echo "")
    pr_title=$(printf '%s\n' "$pr_json" | jq -r '.[0].title // empty' 2>/dev/null || echo "")

    if [[ -z "$pr_number" || -z "$pr_url" ]]; then
        pr_url=$(printf '%s\n' "$conflict_text" | grep -oE 'https?://[^[:space:]]+/pull/[0-9]+' | tail -1 || echo "")
        pr_number=$(printf '%s\n' "$pr_url" | grep -oE '[0-9]+$' || echo "")
        pr_title="$TITLE"
    fi

    if [[ -z "$pr_number" || -z "$pr_url" ]]; then
        return 1
    fi

    emit_kv PR_NUMBER "$pr_number"
    emit_kv PR_URL "$pr_url"
    emit_kv PR_TITLE "$pr_title"
    emit_kv PR_STATUS "existing"
    return 0
}

# --- Push branch ---
push_fail_file=$(mktemp "${TMPDIR:-/tmp}/create-pr-push-new.XXXXXX")
NET_FAIL_FILES+=("$push_fail_file")
if with_transient_retry transient_envelope_predicate_none "$push_fail_file" \
    git push -u origin HEAD; then
    push_rc=0
else
    push_rc=$_WTR_RC
fi
if [[ "$push_rc" -ne 0 ]]; then
    larch_err "ERROR: Failed to push branch: $(redact_diagnostic "$(cat "$push_fail_file" 2>/dev/null || true)")"
    exit 1
fi

# --- Create PR ---
PR_STDERR_FILE=$(mktemp)
PR_STDOUT_FILE=$(mktemp)
GH_DRAFT_ARGS=()
if [[ "$DRAFT" == "true" ]]; then
    GH_DRAFT_ARGS+=(--draft)
fi

if [[ -z "$BASE_REF" ]]; then
    BASE_REF=$(gh repo view ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null) || BASE_REF=""
    if [[ -z "$BASE_REF" ]]; then
        BASE_REF="main"
    fi
fi

# Build the argv for diagnostic purposes (redact title/body values, keep flags),
# then pass it through the shared tmpdir redactor before logging it.
GH_CREATE_ARGV="gh pr create ${GH_REPO_ARGS[*]+${GH_REPO_ARGS[*]}} --assignee @me --head $BRANCH --base $BASE_REF --title <redacted> --body-file <redacted> ${GH_DRAFT_ARGS[*]+${GH_DRAFT_ARGS[*]}}"
GH_CREATE_ARGV=$(printf '%s\n' "$GH_CREATE_ARGV" | "$REDACT_TMPDIR_HELPER")

create_fail_file=$(mktemp "${TMPDIR:-/tmp}/create-pr-gh-create.XXXXXX")
NET_FAIL_FILES+=("$create_fail_file")
if with_transient_retry transient_envelope_predicate_none "$create_fail_file" \
    gh pr create \
    ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} \
    --assignee @me \
    --head "$BRANCH" \
    --base "$BASE_REF" \
    --title "$TITLE" \
    --body-file "$REDACTED_BODY_FILE" \
    ${GH_DRAFT_ARGS[@]+"${GH_DRAFT_ARGS[@]}"}; then
    create_rc=0
else
    create_rc=$_WTR_RC
fi
PR_OUTPUT=$_WTR_OUT
PR_EXIT=$create_rc
printf '%s\n' "$PR_OUTPUT" > "$PR_STDOUT_FILE"
printf '%s\n' "$(cat "$create_fail_file" 2>/dev/null || true)" > "$PR_STDERR_FILE"

if [[ $PR_EXIT -ne 0 ]]; then
    PR_STDERR=$(cat "$PR_STDERR_FILE" 2>/dev/null || true)
    PR_STDOUT_TAIL=$(tail -10 "$PR_STDOUT_FILE" 2>/dev/null || true)
    if recover_existing_pr_after_create_conflict "$PR_STDERR"$'\n'"$PR_STDOUT_TAIL"; then
        exit 0
    fi
    if [[ -z "$PR_STDERR" && -z "$PR_STDOUT_TAIL" ]]; then
        larch_err "ERROR: Failed to create PR (exit $PR_EXIT): (no diagnostic captured; gh pr create exited $PR_EXIT with no output. Manual investigation required.) argv: $GH_CREATE_ARGV"
    else
        larch_err "ERROR: Failed to create PR (exit $PR_EXIT): stderr=$PR_STDERR stdout_tail=$PR_STDOUT_TAIL argv=$GH_CREATE_ARGV"
    fi
    exit 2
fi

# --- Extract PR number and URL ---
# gh pr create outputs the PR URL on success
PR_URL="$PR_OUTPUT"

# Parse PR number from URL first (avoids extra API call)
# URL format: https://github.com/owner/repo/pull/N
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$' || echo "")

if [[ -z "$PR_NUMBER" ]]; then
    # Fallback: fetch via gh pr view if URL parsing failed
    PR_NUMBER=$(gh pr view ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} --json number -q '.number' 2>/dev/null || echo "")
fi

if [[ -z "$PR_NUMBER" ]] || [[ -z "$PR_URL" ]]; then
    larch_err "ERROR: Could not extract PR number/URL from output: $PR_OUTPUT"
    exit 2
fi

emit_kv PR_NUMBER "$PR_NUMBER"
emit_kv PR_URL "$PR_URL"
emit_kv PR_TITLE "$TITLE"
emit_kv PR_STATUS "created"
