#!/usr/bin/env bash
# design-log-publish.sh — flush $DESIGN_TMPDIR into committed larch-logs/design/<run-id>/
# via a disposable git worktree, push, PR, squash-merge with --admin, and worktree cleanup.
#
# Output (stdout KEY=value lines; diagnostics on stderr):
#   PUBLISH_OK=true|false
#   PR_NUMBER=<digits or empty>
#   PR_URL=<url or empty>
#
# Usage:
#   design-log-publish.sh --design-tmpdir PATH --run-id ID --issue N [--repo OWNER/REPO] [--dry-run]
#
# Non-zero exits are reserved for unexpected shell failures; expected operational
# failures still emit PUBLISH_OK=false and exit 0 so callers can parse stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-larch-log.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-larch-log.sh"
# shellcheck source=scripts/lib-redact.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-redact.sh"

DESIGN_TMPDIR=""
RUN_ID=""
ISSUE=""
REPO=""
DRY_RUN=false

usage() {
    larch_err "Usage:"
    larch_err "  design-log-publish.sh --design-tmpdir PATH --run-id ID --issue N [--repo OWNER/REPO] [--dry-run]"
    larch_err "Writes trimmed + redacted design tmpdir artifacts into a disposable worktree, commits with [skip ci], pushes, opens/merges a PR."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done

emit_publish_result() {
    emit_kv PUBLISH_OK "$1"
    emit_kv PR_NUMBER "${2:-}"
    emit_kv PR_URL "${3:-}"
}

if [[ -z "$DESIGN_TMPDIR" || -z "$RUN_ID" || -z "$ISSUE" ]]; then
    usage
    exit 1
fi

case "$ISSUE" in
    ''|*[!0-9]*)
        larch_err "design-log-publish: invalid --issue (expected positive integer)"
        emit_publish_result false
        exit 0
        ;;
esac

case "$RUN_ID" in
    ""|*[!A-Za-z0-9._-]*|.*|*..*|*/*|*\\*)
        larch_err "design-log-publish: invalid --run-id slug"
        emit_publish_result false
        exit 0
        ;;
esac

if [[ ! -d "$DESIGN_TMPDIR" ]]; then
    larch_err "design-log-publish: design tmpdir not found: $DESIGN_TMPDIR"
    emit_publish_result false
    exit 0
fi

if [[ "$DRY_RUN" == true ]]; then
    emit_publish_result true "" ""
    exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
    larch_err "design-log-publish: jq is required"
    emit_publish_result false
    exit 0
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT=""
if [[ -z "$REPO_ROOT" ]]; then
    larch_err "design-log-publish: not inside a git worktree"
    emit_publish_result false
    exit 0
fi

ORIGIN_DEFAULT=$(
    git -C "$REPO_ROOT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
        | sed 's#^refs/remotes/origin/##'
) || ORIGIN_DEFAULT=""
if [[ -z "$ORIGIN_DEFAULT" ]]; then
    larch_err "design-log-publish: cannot resolve origin/HEAD default branch"
    emit_publish_result false
    exit 0
fi

WT_BRANCH="larch-log-design-${RUN_ID}"
WT_DIR=""
# shellcheck disable=SC2317
wt_cleanup() {
    if [[ -n "${WT_DIR:-}" ]]; then
        git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" 2>/dev/null || true
    fi
}
trap wt_cleanup EXIT

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$WT_BRANCH"; then
    git -C "$REPO_ROOT" branch -D "$WT_BRANCH" >/dev/null 2>&1 || true
fi

WT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/design-log-publish.XXXXXX")/wt-checkout
mkdir -p "$(dirname "$WT_DIR")"
git -C "$REPO_ROOT" worktree add -b "$WT_BRANCH" "$WT_DIR" "origin/$ORIGIN_DEFAULT" >/dev/null 2>&1

LOG_ROOT_ABS=$(cd "$WT_DIR" && pwd)/larch-logs
mkdir -p "$LOG_ROOT_ABS"

if ! (cd "$WT_DIR" && "$SCRIPT_DIR/larch-log.sh" init \
    --log-root "$LOG_ROOT_ABS" --skill design --run-id "$RUN_ID" --issue "$ISSUE" >/dev/null); then
    larch_err "design-log-publish: larch-log.sh init failed"
    emit_publish_result false
    exit 0
fi

design_publish_stage_file() {
    local src="$1"
    local dest="$2"
    local name trim_tmp
    name=$(basename "$src")
    if [[ -L "$src" ]]; then
        return 0
    fi
    if [[ ! -f "$src" ]]; then
        return 0
    fi
    trim_tmp=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-trim.XXXXXX") || return 1
    case "$name" in
        *.meta)
            larch_redact_strip_meta_cmd_json "$src" "$trim_tmp" || {
                rm -f "$trim_tmp"
                return 1
            }
            ;;
        *-output*.json)
            larch_redact_strip_json_result "$src" "$trim_tmp" || {
                rm -f "$trim_tmp"
                return 1
            }
            ;;
        *)
            cp "$src" "$trim_tmp" || {
                rm -f "$trim_tmp"
                return 1
            }
            ;;
    esac
    mkdir -p "$(dirname "$dest")"
    if ! larch_log_redact_file "$trim_tmp" "$dest"; then
        rm -f "$trim_tmp"
        return 1
    fi
    rm -f "$trim_tmp"
    return 0
}

RUN_DEST="$WT_DIR/larch-logs/design/$RUN_ID"
mkdir -p "$RUN_DEST/render-cache"

while IFS= read -r f || [[ -n "$f" ]]; do
    [[ -z "$f" ]] && continue
    b=$(basename "$f")
    design_publish_stage_file "$f" "$RUN_DEST/$b" || {
        larch_err "design-log-publish: staging failed for $f"
        emit_publish_result false
        exit 0
    }
done < <(find "$DESIGN_TMPDIR" -maxdepth 1 -type f 2>/dev/null | LC_ALL=C sort || true)

if [[ -d "$DESIGN_TMPDIR/render-cache" ]]; then
    while IFS= read -r f || [[ -n "$f" ]]; do
        [[ -z "$f" ]] && continue
        rel=${f#"$DESIGN_TMPDIR/render-cache/"}
        design_publish_stage_file "$f" "$RUN_DEST/render-cache/$rel" || {
            larch_err "design-log-publish: staging failed for $f"
            emit_publish_result false
            exit 0
        }
    done < <(find "$DESIGN_TMPDIR/render-cache" -type f 2>/dev/null | LC_ALL=C sort || true)
fi

MF="$RUN_DEST/manifest.json"
ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
mf_tmp=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-mf.XXXXXX")
if ! jq --arg ts "$ts" '.updated_at = $ts' "$MF" >"$mf_tmp"; then
    rm -f "$mf_tmp"
    larch_err "design-log-publish: manifest refresh failed"
    emit_publish_result false
    exit 0
fi
mv -f "$mf_tmp" "$MF"

rel="larch-logs/design/$RUN_ID"
if ! git -C "$WT_DIR" status --porcelain -- "$rel" | grep -q .; then
    emit_publish_result true "" ""
    exit 0
fi

git -C "$WT_DIR" add -- "$rel"
if ! git -C "$WT_DIR" commit -m "chore(larch-logs): flush design run ${RUN_ID} [skip ci]" -- "$rel" >/dev/null; then
    larch_err "design-log-publish: git commit failed"
    emit_publish_result false
    exit 0
fi

gh_repo_args=()
if [[ -n "$REPO" ]]; then
    gh_repo_args+=(--repo "$REPO")
fi

if ! git -C "$WT_DIR" push -u origin "$WT_BRANCH" >/dev/null 2>&1; then
    larch_err "design-log-publish: git push failed"
    emit_publish_result false
    exit 0
fi

create_rc=0
create_out=""
create_out=$(
    gh pr create "${gh_repo_args[@]}" --head "$WT_BRANCH" --base "$ORIGIN_DEFAULT" \
        --title "chore(larch-logs): design run ${RUN_ID}" \
        --body "Automated design log directory for run ${RUN_ID}. Commit uses [skip ci]." 2>&1
) || create_rc=$?

PR_NUM=""
PR_URL=""
if [[ "$create_rc" -eq 0 ]]; then
    PR_URL=$(printf '%s\n' "$create_out" | grep -oE 'https://[^[:space:]]+/pull/[0-9]+' | tail -1 || true)
    if [[ -n "$PR_URL" ]]; then
        PR_NUM=$(printf '%s\n' "$PR_URL" | sed -n 's|.*/pull/\([0-9][0-9]*\).*|\1|p')
    fi
fi

if [[ -z "$PR_NUM" ]]; then
    PR_NUM=$(gh pr list "${gh_repo_args[@]}" --head "$WT_BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || true)
    if [[ -z "$PR_NUM" || "$PR_NUM" == "null" ]]; then
        larch_err "design-log-publish: gh pr create failed: ${create_out:-unknown}"
        emit_publish_result false
        exit 0
    fi
    PR_URL=$(gh pr view "${gh_repo_args[@]}" "$PR_NUM" --json url --jq '.url' 2>/dev/null || true)
fi

merge_rc=0
gh pr merge "${gh_repo_args[@]}" "$PR_NUM" --squash --admin --delete-branch >/dev/null 2>&1 || merge_rc=$?

git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" 2>/dev/null || true
WT_DIR=""
trap - EXIT

git -C "$REPO_ROOT" branch -D "$WT_BRANCH" >/dev/null 2>&1 || true

if [[ "$merge_rc" -ne 0 ]]; then
    emit_publish_result false "$PR_NUM" "${PR_URL:-}"
    exit 0
fi

emit_publish_result true "$PR_NUM" "${PR_URL:-}"
exit 0
