#!/usr/bin/env bash
# design-log-publish.sh — flush $DESIGN_TMPDIR into committed larch-logs/design/<run-id>/
# via a disposable git worktree, push, PR, squash-merge with --admin, and worktree cleanup.
#
# Output (stdout KEY=value lines; diagnostics on stderr):
#   PUBLISH_OK=true|false
#   PR_NUMBER=<digits or empty>
#   PR_URL=<url or empty>
#   RECOVERY_BRANCH=<branch name> (only when PUBLISH_OK=false after a successful git push)
#
# Usage:
#   design-log-publish.sh --design-tmpdir PATH --run-id ID --issue N [--repo OWNER/REPO] [--reason final|pause] [--dry-run]
#
# Expected operational failures emit PUBLISH_OK=false on stdout. Pre-validation and
# pre-push failures exit 0 so callers can parse stdout. Post-push failures (git push,
# gh pr create after push, gh pr merge) exit 1 while preserving PUBLISH_OK=false.
# Per-script larch-quiet-*-*.log files are excluded from top-level staging; they are
# published only under breadcrumbs/ via larch_log_publish_breadcrumbs_shared.

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
REASON="final"

usage() {
    larch_err "Usage:"
    larch_err "  design-log-publish.sh --design-tmpdir PATH --run-id ID --issue N [--repo OWNER/REPO] [--reason final|pause] [--dry-run]"
    larch_err "Writes trimmed + redacted design tmpdir artifacts into a disposable worktree, commits with [skip ci], pushes, opens/merges a PR."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --reason) REASON="${2:?--reason requires a value}"; shift 2 ;;
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

case "$REASON" in
    final|pause) ;;
    *) larch_err "design-log-publish: invalid --reason (expected final or pause)"; emit_publish_result false; exit 0 ;;
esac

if ! [[ "$ISSUE" =~ ^[1-9][0-9]*$ ]]; then
    larch_err "design-log-publish: invalid --issue (expected positive integer)"
    emit_publish_result false
    exit 0
fi

if ! larch_log_slug_is_valid "$RUN_ID"; then
    larch_err "design-log-publish: invalid --run-id slug"
    emit_publish_result false
    exit 0
fi

if [[ ! -d "$DESIGN_TMPDIR" ]]; then
    larch_err "design-log-publish: design tmpdir not found: $DESIGN_TMPDIR"
    emit_publish_result false
    exit 0
fi
export DESIGN_TMPDIR

if [[ "$DRY_RUN" == true ]]; then
    if ! command -v git >/dev/null 2>&1; then
        larch_err "design-log-publish: git is required"
        emit_publish_result false
        exit 0
    fi
    if ! command -v gh >/dev/null 2>&1; then
        larch_err "design-log-publish: gh is required"
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
WT_PARENT=""
PUSH_DONE=false
ENUM_TOP_TMP=""
ENUM_RC_TMP=""
ENUM_PR_TMP=""
PR_BODY_TMP=""
# shellcheck disable=SC2317
wt_cleanup() {
    rm -f "${ENUM_TOP_TMP:-}" "${ENUM_RC_TMP:-}" "${ENUM_PR_TMP:-}" 2>/dev/null || true
    if [ -n "${PR_BODY_TMP:-}" ]; then
        rm -f "$PR_BODY_TMP" 2>/dev/null || true
    fi
    if [[ -n "${WT_DIR:-}" ]]; then
        git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" 2>/dev/null || true
    fi
    if [[ -n "${WT_PARENT:-}" ]]; then
        rm -rf "$WT_PARENT" 2>/dev/null || true
    fi
}
trap wt_cleanup EXIT

REMOTE_BRANCH_EXISTS=false
if [[ "$REASON" == "pause" ]]; then
    git -C "$REPO_ROOT" fetch origin "$WT_BRANCH:refs/remotes/origin/$WT_BRANCH" >/dev/null 2>&1 || true
    if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$WT_BRANCH"; then
        REMOTE_BRANCH_EXISTS=true
    fi
fi
if git -C "$REPO_ROOT" worktree list | grep -Fq " [$WT_BRANCH]"; then
    larch_err "design-log-publish: branch $WT_BRANCH is already checked out in another worktree; concurrent or stale publish for this RUN_ID"
    emit_publish_result false
    if [[ "$REASON" == "pause" && "$REMOTE_BRANCH_EXISTS" == true ]]; then
        emit_kv RECOVERY_BRANCH "$WT_BRANCH"
    fi
    exit 0
fi
if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$WT_BRANCH"; then
    if ! git -C "$REPO_ROOT" branch -D "$WT_BRANCH" >/dev/null 2>&1; then
        larch_err "design-log-publish: cannot delete existing local branch $WT_BRANCH (still in use?)"
        emit_publish_result false
        exit 0
    fi
fi

if ! WT_PARENT=$(mktemp -d "${TMPDIR:-/tmp}/design-log-publish.XXXXXX"); then
    larch_err "design-log-publish: cannot allocate worktree tempdir"
    emit_publish_result false
    exit 0
fi
WT_DIR="$WT_PARENT/wt-checkout"
if ! mkdir -p "$WT_DIR"; then
    larch_err "design-log-publish: cannot create worktree checkout directory"
    emit_publish_result false
    exit 0
fi
WT_BASE_REF="origin/$ORIGIN_DEFAULT"
if [[ "$REMOTE_BRANCH_EXISTS" == true ]]; then
    WT_BASE_REF="origin/$WT_BRANCH"
fi
if ! git -C "$REPO_ROOT" worktree add -b "$WT_BRANCH" "$WT_DIR" "$WT_BASE_REF" >/dev/null 2>&1; then
    larch_err "design-log-publish: git worktree add failed"
    emit_publish_result false
    exit 0
fi

LOG_ROOT_ABS=$(cd "$WT_DIR" && pwd)/larch-logs
mkdir -p "$LOG_ROOT_ABS"

if ! (cd "$WT_DIR" && "$SCRIPT_DIR/larch-log.sh" init \
    --log-root "$LOG_ROOT_ABS" --skill design --run-id "$RUN_ID" --issue "$ISSUE" >/dev/null); then
    larch_err "design-log-publish: larch-log.sh init failed"
    emit_publish_result false
    exit 0
fi

design_artifact_excluded() {
    local name="$1"
    if [[ "$REASON" != "pause" ]]; then
        case "$name" in
            .pause-requested|pause-save.out|pause-state.txt)
                return 0
                ;;
        esac
    fi
    case "$name" in
        larch-quiet-*-*.log|*.sidecar|*.dirty-tree|*.untracked-baseline|*.done|*.diag|*.events.jsonl|*-output.txt.prompt|*-output-*.txt.prompt)
            return 0
            ;;
    esac
    return 1
}

design_publish_stage_file() {
    local src="$1"
    local dest="$2"
    local name trim_tmp redact_tmp redact_secrets
    name=$(basename "$src")
    if [[ -L "$src" ]]; then
        return 0
    fi
    if [[ ! -f "$src" ]]; then
        return 0
    fi
    if design_artifact_excluded "$name"; then
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
    redact_tmp="$SCRIPT_DIR/redact-tmpdir-paths.sh"
    redact_secrets="$SCRIPT_DIR/redact-secrets.sh"
    if [[ ! -x "$redact_tmp" || ! -x "$redact_secrets" ]]; then
        rm -f "$trim_tmp"
        return 1
    fi
    if ! "$redact_tmp" <"$trim_tmp" | "$redact_secrets" >"$dest"; then
        rm -f "$trim_tmp"
        return 1
    fi
    rm -f "$trim_tmp"
    return 0
}

design_publish_breadcrumbs() {
    local source_dir="$1" dest_dir="$2"
    larch_log_publish_breadcrumbs_shared "$source_dir" "$dest_dir" design_publish_breadcrumbs_error
}

# shellcheck disable=SC2317 # invoked indirectly via larch_log_publish_breadcrumbs_shared callback name
design_publish_breadcrumbs_error() {
    larch_err "design-log-publish: $1"
}

RUN_DEST="$WT_DIR/larch-logs/design/$RUN_ID"
mkdir -p "$RUN_DEST/render-cache"

_top_files=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-files.XXXXXX")
ENUM_TOP_TMP="$_top_files"
if ! find "$DESIGN_TMPDIR" -maxdepth 1 -type f | LC_ALL=C sort >"$_top_files"; then
    rm -f "$_top_files"
    ENUM_TOP_TMP=""
    larch_err "design-log-publish: failed to enumerate design tmpdir files"
    emit_publish_result false
    exit 0
fi
while IFS= read -r f || [[ -n "$f" ]]; do
    [[ -z "$f" ]] && continue
    b=$(basename "$f")
    design_publish_stage_file "$f" "$RUN_DEST/$b" || {
        larch_err "design-log-publish: staging failed for $f"
        emit_publish_result false
        exit 0
    }
done <"$_top_files"
rm -f "$_top_files"
ENUM_TOP_TMP=""

if [[ -e "$DESIGN_TMPDIR/plan-review" || -L "$DESIGN_TMPDIR/plan-review" ]]; then
    if [[ -L "$DESIGN_TMPDIR/plan-review" ]]; then
        larch_err "design-log-publish: plan-review must not be a symlink"
        emit_publish_result false
        exit 0
    fi
    if [[ ! -d "$DESIGN_TMPDIR/plan-review" ]]; then
        larch_err "design-log-publish: plan-review exists but is not a directory"
        emit_publish_result false
        exit 0
    fi
    pr_root=$(cd "$DESIGN_TMPDIR/plan-review" && pwd -P) || {
        larch_err "design-log-publish: cannot resolve plan-review directory"
        emit_publish_result false
        exit 0
    }
    _sym_check=$(find "$pr_root" -type l -print -quit 2>/dev/null || true)
    if [[ -n "$_sym_check" ]]; then
        larch_err "design-log-publish: plan-review tree must not contain symlinks (found: $_sym_check)"
        emit_publish_result false
        exit 0
    fi
    _pr_files=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-pr.XXXXXX")
    ENUM_PR_TMP="$_pr_files"
    if ! find "$pr_root" -type f | LC_ALL=C sort >"$_pr_files"; then
        rm -f "$_pr_files"
        ENUM_PR_TMP=""
        larch_err "design-log-publish: failed to enumerate plan-review files"
        emit_publish_result false
        exit 0
    fi
    while IFS= read -r f || [[ -n "$f" ]]; do
        [[ -z "$f" ]] && continue
        case "$f" in
            "$pr_root"/*) ;;
            *)
                larch_err "design-log-publish: path escapes plan-review root: $f"
                emit_publish_result false
                exit 0
                ;;
        esac
        rel=${f#"$pr_root/"}
        if ! [[ "$rel" =~ ^round-[1-9][0-9]*/findings-classification\.tsv$ ]]; then
            larch_err "design-log-publish: unexpected file under plan-review: $rel"
            emit_publish_result false
            exit 0
        fi
        if [[ -L "$f" ]]; then
            larch_err "design-log-publish: plan-review file became a symlink before staging: $f"
            emit_publish_result false
            exit 0
        fi
        mkdir -p "$RUN_DEST/plan-review/$(dirname "$rel")"
        design_publish_stage_file "$f" "$RUN_DEST/plan-review/$rel" || {
            larch_err "design-log-publish: staging failed for $f"
            emit_publish_result false
            exit 0
        }
    done <"$_pr_files"
    rm -f "$_pr_files"
    ENUM_PR_TMP=""
fi

if [[ -e "$DESIGN_TMPDIR/render-cache" || -L "$DESIGN_TMPDIR/render-cache" ]]; then
    if [[ -L "$DESIGN_TMPDIR/render-cache" ]]; then
        larch_err "design-log-publish: render-cache must not be a symlink"
        emit_publish_result false
        exit 0
    fi
    if [[ ! -d "$DESIGN_TMPDIR/render-cache" ]]; then
        larch_err "design-log-publish: render-cache exists but is not a directory"
        emit_publish_result false
        exit 0
    fi
    rc_root=$(cd "$DESIGN_TMPDIR/render-cache" && pwd -P) || {
        larch_err "design-log-publish: cannot resolve render-cache directory"
        emit_publish_result false
        exit 0
    }
    _sym_check=$(find "$rc_root" -type l -print -quit 2>/dev/null || true)
    if [[ -n "$_sym_check" ]]; then
        larch_err "design-log-publish: render-cache tree must not contain symlinks (found: $_sym_check)"
        emit_publish_result false
        exit 0
    fi
    _rc_files=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-rc.XXXXXX")
    ENUM_RC_TMP="$_rc_files"
    if ! find "$rc_root" -type f | LC_ALL=C sort >"$_rc_files"; then
        rm -f "$_rc_files"
        ENUM_RC_TMP=""
        larch_err "design-log-publish: failed to enumerate render-cache files"
        emit_publish_result false
        exit 0
    fi
    while IFS= read -r f || [[ -n "$f" ]]; do
        [[ -z "$f" ]] && continue
        case "$f" in
            "$rc_root"/*) ;;
            *)
                larch_err "design-log-publish: render-cache path outside resolved root: $f"
                emit_publish_result false
                exit 0
                ;;
        esac
        rel=${f#"$rc_root/"}
        if [[ -L "$f" ]]; then
            larch_err "design-log-publish: render-cache file became a symlink before staging: $f"
            emit_publish_result false
            exit 0
        fi
        design_publish_stage_file "$f" "$RUN_DEST/render-cache/$rel" || {
            larch_err "design-log-publish: staging failed for $f"
            emit_publish_result false
            exit 0
        }
    done <"$_rc_files"
    rm -f "$_rc_files"
    ENUM_RC_TMP=""
fi

if [[ "$REASON" == "pause" && ( -e "$DESIGN_TMPDIR/.completed" || -L "$DESIGN_TMPDIR/.completed" ) ]]; then
    if [[ -L "$DESIGN_TMPDIR/.completed" ]]; then
        larch_err "design-log-publish: .completed must not be a symlink"
        emit_publish_result false
        exit 0
    fi
    if [[ ! -d "$DESIGN_TMPDIR/.completed" ]]; then
        larch_err "design-log-publish: .completed exists but is not a directory"
        emit_publish_result false
        exit 0
    fi
    completed_root=$(cd "$DESIGN_TMPDIR/.completed" && pwd -P) || {
        larch_err "design-log-publish: cannot resolve .completed directory"
        emit_publish_result false
        exit 0
    }
    _sym_check=$(find "$completed_root" -type l -print -quit 2>/dev/null || true)
    if [[ -n "$_sym_check" ]]; then
        larch_err "design-log-publish: .completed tree must not contain symlinks (found: $_sym_check)"
        emit_publish_result false
        exit 0
    fi
    mkdir -p "$RUN_DEST/.completed"
    while IFS= read -r f || [[ -n "$f" ]]; do
        [[ -z "$f" ]] && continue
        case "$f" in
            "$completed_root"/*) ;;
            *)
                larch_err "design-log-publish: .completed path outside resolved root: $f"
                emit_publish_result false
                exit 0
                ;;
        esac
        rel=${f#"$completed_root/"}
        if [[ ! "$rel" =~ ^step-[A-Za-z0-9._-]+$ ]]; then
            larch_err "design-log-publish: unexpected file under .completed: $rel"
            emit_publish_result false
            exit 0
        fi
        if [[ -L "$f" ]]; then
            larch_err "design-log-publish: .completed file became a symlink before staging: $f"
            emit_publish_result false
            exit 0
        fi
        design_publish_stage_file "$f" "$RUN_DEST/.completed/$rel" || {
            larch_err "design-log-publish: staging failed for $f"
            emit_publish_result false
            exit 0
        }
    done < <(find "$completed_root" -type f | LC_ALL=C sort)
fi

if ! design_publish_breadcrumbs "$DESIGN_TMPDIR/breadcrumbs" "$RUN_DEST/breadcrumbs"; then
    emit_publish_result false
    exit 0
fi

MF="$RUN_DEST/manifest.json"
ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
mf_tmp=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-mf.XXXXXX")
if [[ "$REASON" == "pause" ]]; then
    # shellcheck disable=SC2016 # jq variable $ts is supplied by --arg below.
    jq_expr='.updated_at = $ts | .paused = true'
else
    # shellcheck disable=SC2016 # jq variable $ts is supplied by --arg below.
    jq_expr='.updated_at = $ts'
fi
if ! jq --arg ts "$ts" "$jq_expr" "$MF" >"$mf_tmp"; then
    rm -f "$mf_tmp"
    larch_err "design-log-publish: manifest refresh failed"
    emit_publish_result false
    exit 0
fi
if ! mv -f "$mf_tmp" "$MF"; then
    rm -f "$mf_tmp"
    larch_err "design-log-publish: manifest install failed"
    emit_publish_result false
    exit 0
fi

rel="larch-logs/design/$RUN_ID"
_porcelain=""
if ! _porcelain=$(git -C "$WT_DIR" status --porcelain -- "$rel" 2>&1); then
    larch_err "design-log-publish: git status failed for $rel"
    emit_publish_result false
    exit 0
fi
if [[ -z "$_porcelain" ]]; then
    if [[ "$REASON" == "pause" ]]; then
        if [[ "$REMOTE_BRANCH_EXISTS" == true ]]; then
            if git -C "$REPO_ROOT" diff --quiet "origin/$WT_BRANCH" "origin/$ORIGIN_DEFAULT" -- "larch-logs/design/$RUN_ID" >/dev/null 2>&1; then
                # No new delta; snapshot already on default branch. Fail closed so
                # callers get a RECOVERY_BRANCH pointer rather than a silent success.
                emit_publish_result false
                emit_kv RECOVERY_BRANCH "$WT_BRANCH"
                exit 0
            fi
            emit_publish_result false
            emit_kv RECOVERY_BRANCH "$WT_BRANCH"
            exit 0
        fi
        larch_err "design-log-publish: pause publish produced no new snapshot delta"
        emit_publish_result false
        exit 0
    fi
    emit_publish_result true "" ""
    exit 0
fi

if ! git -C "$WT_DIR" add -- "$rel"; then
    larch_err "design-log-publish: git add failed"
    emit_publish_result false
    exit 0
fi
if [[ "$REASON" == "pause" ]]; then
    commit_subject="chore(larch-logs): pause design run ${RUN_ID} [skip ci]"
else
    commit_subject="chore(larch-logs): flush design run ${RUN_ID} [skip ci]"
fi
if ! git -C "$WT_DIR" commit -m "$commit_subject" -- "$rel" >/dev/null; then
    larch_err "design-log-publish: git commit failed"
    emit_publish_result false
    exit 0
fi

gh_repo_args=()
if [[ -n "$REPO" ]]; then
    gh_repo_args+=(--repo "$REPO")
fi

PR_BODY_TMP=$(mktemp "${TMPDIR:-/tmp}/larch-design-log-pr-body.XXXXXX") || {
    larch_err "design-log-publish: mktemp failed for PR body"
    emit_publish_result false
    exit 0
}
printf 'Automated design log directory for run %s. Commit uses [skip ci].' "$RUN_ID" >"$PR_BODY_TMP"

push_args=(-u origin "$WT_BRANCH")
if [[ "$REASON" == "pause" ]]; then
    push_args=(--force-with-lease -u origin "$WT_BRANCH")
fi
if ! git -C "$WT_DIR" push "${push_args[@]}" >/dev/null 2>&1; then
    larch_err "design-log-publish: git push failed"
    if commit_sha=$(git -C "$WT_DIR" rev-parse HEAD 2>/dev/null); then
        local_recovery_branch="larch-log-design-recovery-${RUN_ID}"
        git -C "$REPO_ROOT" branch -f "$local_recovery_branch" "$commit_sha" >/dev/null 2>&1 || true
        larch_err "design-log-publish: local commit preserved on ref ${local_recovery_branch} ($commit_sha)"
        emit_publish_result false
        emit_kv RECOVERY_BRANCH "$local_recovery_branch"
        exit 1
    fi
    emit_publish_result false
    exit 1
fi
PUSH_DONE=true

create_rc=0
create_out=""
create_out=$(
    gh pr create "${gh_repo_args[@]}" --head "$WT_BRANCH" --base "$ORIGIN_DEFAULT" \
        --title "chore(larch-logs): design run ${RUN_ID}" \
        --body-file "$PR_BODY_TMP" 2>&1
) || create_rc=$?
rm -f "$PR_BODY_TMP" 2>/dev/null || true
PR_BODY_TMP=""

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
        larch_err "design-log-publish: remote branch may need manual cleanup: $WT_BRANCH"
        emit_publish_result false
        [[ "$PUSH_DONE" == true ]] && emit_kv RECOVERY_BRANCH "$WT_BRANCH"
        exit 1
    fi
    PR_URL=$(gh pr view "${gh_repo_args[@]}" "$PR_NUM" --json url --jq '.url' 2>/dev/null || true)
fi

merge_rc=0
gh pr merge "${gh_repo_args[@]}" "$PR_NUM" --squash --admin --delete-branch >/dev/null || merge_rc=$?

git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" 2>/dev/null || true
rm -rf "${WT_PARENT:-}" 2>/dev/null || true
WT_DIR=""
WT_PARENT=""
trap - EXIT

git -C "$REPO_ROOT" branch -D "$WT_BRANCH" >/dev/null 2>&1 || true
git -C "$REPO_ROOT" branch -D "larch-log-design-recovery-${RUN_ID}" >/dev/null 2>&1 || true

if [[ "$merge_rc" -ne 0 ]]; then
    emit_publish_result false "$PR_NUM" "${PR_URL:-}"
    [[ "$PUSH_DONE" == true ]] && emit_kv RECOVERY_BRANCH "$WT_BRANCH"
    exit 1
fi

emit_publish_result true "$PR_NUM" "${PR_URL:-}"
exit 0
