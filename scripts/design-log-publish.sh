#!/usr/bin/env bash
# design-log-publish.sh — flush $DESIGN_TMPDIR into committed larch-logs/design/<run-id>/
# via a disposable git worktree, push, PR, wait for required CI, squash --admin merge on green, and worktree cleanup.
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
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/lib-design-tmpdir.sh"
# shellcheck source=scripts/lib-design-round-artifacts.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-design-round-artifacts.sh"
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh" || { larch_err "design-log-publish: failed to source lib-net.sh"; exit 1; }

DESIGN_TMPDIR=""
RUN_ID=""
ISSUE=""
REPO=""
DRY_RUN=false
REASON="final"

usage() {
    larch_err "Usage:"
    larch_err "  design-log-publish.sh --design-tmpdir PATH --run-id ID --issue N [--repo OWNER/REPO] [--reason final|pause] [--dry-run]"
    larch_err "Writes trimmed + redacted design tmpdir artifacts into a disposable worktree, commits, pushes, opens a PR, waits for required CI checks, then squash-merges with --admin once they pass."
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

emit_publish_failure() {
    emit_publish_result false "${1:-}" "${2:-}"
    if [[ "${PUSH_DONE:-false}" == true ]]; then
        emit_kv RECOVERY_BRANCH "$WT_BRANCH"
    fi
}

redact_diagnostic() {
    local text=$1 redacted=""
    if [ -x "$SCRIPT_DIR/redact-tmpdir-paths.sh" ] && [ -x "$SCRIPT_DIR/redact-secrets.sh" ]; then
        redacted=$(printf '%s' "$text" | "$SCRIPT_DIR/redact-tmpdir-paths.sh" | "$SCRIPT_DIR/redact-secrets.sh" 2>/dev/null || true)
        case "$redacted" in
            *'[content truncated'*) redacted="" ;;
        esac
    fi
    if [ -n "$redacted" ]; then
        printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
    else
        printf '%s' 'diagnostic redaction unavailable'
    fi
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

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || { emit_publish_result false; exit 0; }

if [[ ! -d "$DESIGN_TMPDIR" ]]; then
    larch_err "design-log-publish: design tmpdir not found: $DESIGN_TMPDIR"
    emit_publish_result false
    exit 0
fi

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
reg_checks_err_file=""
reg_view_fail_file=""
# shellcheck disable=SC2317
wt_cleanup() {
    rm -f "${ENUM_TOP_TMP:-}" "${ENUM_RC_TMP:-}" "${ENUM_PR_TMP:-}" \
        "${push_fail_file:-}" "${create_fail_file:-}" "${merge_fail_file:-}" \
        "${list_fail_file:-}" "${view_fail_file:-}" \
        "${reg_checks_err_file:-}" "${reg_view_fail_file:-}" 2>/dev/null || true
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

design_publish_ancestor_within_root() {
    local _root="$1" _file="$2" _parent
    _parent=$(cd "$(dirname "$_file")" 2>/dev/null && pwd -P) || return 1
    case "$_parent" in
        "$_root"|"$_root"/*) return 0 ;;
        *) return 1 ;;
    esac
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
        if [[ "$rel" =~ ^round-[1-9][0-9]*/revise/[A-Za-z0-9._+-]+$ ]]; then
            _base=$(basename "$rel")
            if design_round_revise_artifact_included "$_base"; then
                :
            else
                larch_err "design-log-publish: unexpected file under plan-review (see scripts/lib-design-round-artifacts.md): $rel"
                emit_publish_result false
                exit 0
            fi
        elif [[ "$rel" =~ ^round-[1-9][0-9]*/[A-Za-z0-9._+-]+$ ]]; then
            _base=$(basename "$rel")
            if design_round_artifact_included "$_base"; then
                :
            else
                larch_err "design-log-publish: unexpected file under plan-review (see scripts/lib-design-round-artifacts.md): $rel"
                emit_publish_result false
                exit 0
            fi
        else
            larch_err "design-log-publish: unexpected path under plan-review (see scripts/lib-design-round-artifacts.md): $rel"
            emit_publish_result false
            exit 0
        fi
        if [[ -L "$f" ]]; then
            larch_err "design-log-publish: plan-review file became a symlink before staging: $f"
            emit_publish_result false
            exit 0
        fi
        if ! design_publish_ancestor_within_root "$pr_root" "$f"; then
            larch_err "design-log-publish: plan-review ancestor became a symlink before staging: $f"
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
        if ! design_publish_ancestor_within_root "$rc_root" "$f"; then
            larch_err "design-log-publish: render-cache ancestor became a symlink before staging: $f"
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
        if ! design_publish_ancestor_within_root "$completed_root" "$f"; then
            larch_err "design-log-publish: .completed ancestor became a symlink before staging: $f"
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

# Pre-flush secret gate: scrub secret-shaped values (Cursor keys et al.) from
# the staged run tree before commit. Fail-closed on scrub failure. On a real
# redaction, propagate the count via emit_kv SECRET_SCRUB_VIOLATIONS so the
# /design report can warn the operator to rotate the exposed credential.
scrub_gate="$SCRIPT_DIR/scrub-log-secrets.sh"
if [[ ! -x "$scrub_gate" ]]; then
    larch_err "design-log-publish: secret scrub gate missing: $scrub_gate"
    emit_publish_result false
    exit 0
fi
set +e
scrub_out="$("$scrub_gate" "$RUN_DEST")"
scrub_rc=$?
set -e
if [[ "$scrub_rc" -ne 0 ]]; then
    larch_err "design-log-publish: secret scrub gate failed (rc=$scrub_rc) for $RUN_DEST; refusing to flush"
    emit_publish_result false
    exit 0
fi
scrub_n="$(printf '%s\n' "$scrub_out" | sed -n 's/^LARCH_SECRET_SCRUB_VIOLATIONS=//p' | tail -1)"
case "${scrub_n:-}" in ''|*[!0-9]*) scrub_n=0 ;; esac
if [[ "$scrub_n" -gt 0 ]]; then
    larch_err "design-log-publish: WARNING — redacted $scrub_n secret-shaped value(s) from design run $RUN_ID logs before flush; ROTATE the affected credential(s)"
    emit_kv SECRET_SCRUB_VIOLATIONS "$scrub_n"
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
    if git -C "$REPO_ROOT" ls-tree -r --name-only "origin/$ORIGIN_DEFAULT" -- "$rel" | grep -q .; then
        emit_publish_result true "" ""
    else
        larch_err "design-log-publish: final publish produced no new snapshot delta and origin/$ORIGIN_DEFAULT does not contain $rel"
        emit_publish_result false
    fi
    exit 0
fi

if ! git -C "$WT_DIR" add -- "$rel"; then
    larch_err "design-log-publish: git add failed"
    emit_publish_result false
    exit 0
fi
if [[ "$REASON" == "pause" ]]; then
    commit_subject="chore(larch-logs): pause design run ${RUN_ID}"
else
    commit_subject="chore(larch-logs): flush design run ${RUN_ID}"
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
    emit_publish_failure
    [[ "$PUSH_DONE" == true ]] && exit 1
    exit 0
}
printf 'Automated design log directory for run %s. Merged once required CI checks pass.' "$RUN_ID" >"$PR_BODY_TMP"

push_args=(-u origin "$WT_BRANCH")
if [[ "$REASON" == "pause" ]]; then
    push_args=(--force-with-lease -u origin "$WT_BRANCH")
fi
push_fail_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-push.XXXXXX") || {
    larch_err "design-log-publish: mktemp failed for push capture"
    emit_publish_result false
    exit 0
}
if with_transient_retry transient_envelope_predicate_none "$push_fail_file" \
    git -C "$WT_DIR" push "${push_args[@]}"; then
    push_rc=0
else
    push_rc=$_WTR_RC
fi
push_out=$_WTR_OUT
if [[ "$push_rc" -ne 0 ]]; then
    larch_err "design-log-publish: git push failed: $(redact_diagnostic "${push_out:-unknown}")"
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
PUSH_HEAD_SHA=$(git -C "$WT_DIR" rev-parse HEAD 2>/dev/null || true)

create_fail_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-create.XXXXXX") || {
    larch_err "design-log-publish: mktemp failed for pr-create capture"
    emit_publish_failure
    [[ "$PUSH_DONE" == true ]] && exit 1
    exit 0
}
if with_transient_retry transient_envelope_predicate_none "$create_fail_file" \
    gh pr create "${gh_repo_args[@]}" --head "$WT_BRANCH" --base "$ORIGIN_DEFAULT" \
        --title "chore(larch-logs): design run ${RUN_ID}" \
        --body-file "$PR_BODY_TMP"; then
    create_rc=0
else
    create_rc=$_WTR_RC
fi
create_out=$_WTR_OUT
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
    list_rc=1
    list_fail_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-list.XXXXXX") || {
        larch_err "design-log-publish: mktemp failed for pr-list capture"
        emit_publish_failure "$PR_NUM" "${PR_URL:-}"
        exit 1
    }
    if with_transient_retry transient_envelope_predicate_none "$list_fail_file" \
        gh pr list "${gh_repo_args[@]}" --head "$WT_BRANCH" --state open --json number --jq '.[0].number'; then
        list_rc=0
    else
        list_rc=${_WTR_RC:-1}
    fi
    PR_NUM=$_WTR_OUT
    if [[ -z "$PR_NUM" || "$PR_NUM" == "null" ]]; then
        if [[ "$create_rc" -eq 0 ]]; then
            larch_err "design-log-publish: gh pr create returned success but PR recovery found no open PR: $(redact_diagnostic "${create_out:-unknown}")"
        else
            larch_err "design-log-publish: gh pr create failed: $(redact_diagnostic "${create_out:-unknown}")"
        fi
        if [[ "$list_rc" -ne 0 ]]; then
            larch_err "design-log-publish: gh pr list recovery was inconclusive; preserving pushed branch ${WT_BRANCH}"
        elif [[ "$create_rc" -ne 0 ]]; then
            git -C "$WT_DIR" push origin --delete "$WT_BRANCH" >/dev/null 2>&1 || true
        fi
        rm -f "$list_fail_file"
        emit_publish_result false
        [[ "$PUSH_DONE" == true ]] && emit_kv RECOVERY_BRANCH "$WT_BRANCH"
        exit 1
    fi
    rm -f "$list_fail_file"
    view_fail_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-view.XXXXXX") || {
        larch_err "design-log-publish: mktemp failed for pr-view capture"
        emit_publish_failure "$PR_NUM" "${PR_URL:-}"
        exit 1
    }
    if with_transient_retry transient_envelope_predicate_none "$view_fail_file" \
        gh pr view "${gh_repo_args[@]}" "$PR_NUM" --json url --jq '.url'; then
        PR_URL=$_WTR_OUT
    else
        PR_URL=""
    fi
    rm -f "$view_fail_file"
fi

# Trigger CI by committing without a [skip ci] marker, then wait for the PR's
# required status checks to register for the just-pushed head before watching
# them. --admin (not --auto) is deliberate: this repo's review ruleset has no
# bot reviewer, so a server-side --auto merge would enable but never complete.
# --admin still bypasses the review gate, but CI gates the merge because we
# refuse to merge on registration timeout, head mismatch, or required-check
# failure. The registration probe is bounded to avoid the #3413 check
# registration race; the +1 covers the inclusive t=0 probe (Codex-Pragmatic
# off-by-one). The completion watch remains unbounded and relies on GitHub's
# per-job timeouts for the realistic wait.
REG_TIMEOUT=300
REG_INTERVAL=10
REG_MAX_PROBES=$(( (REG_TIMEOUT + REG_INTERVAL - 1) / REG_INTERVAL + 1 ))
REG_DEADLINE=$((SECONDS + REG_TIMEOUT))
checks_registered=false
last_checks_out=""
last_checks_err=""
last_view_out=""
last_view_err=""
reg_probe=1
non_array_checks_json_logged=false

if [[ -z "${PUSH_HEAD_SHA:-}" ]]; then
    larch_err "design-log-publish: required CI checks did not register within ${REG_TIMEOUT}s (0/${REG_MAX_PROBES} probes; pushed head SHA unavailable) for PR $PR_NUM; refusing to merge"
    merge_rc=1
else
    reg_checks_err_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-checks.XXXXXX") || {
        larch_err "design-log-publish: mktemp failed for checks-registration capture"
        emit_publish_failure "$PR_NUM" "${PR_URL:-}"
        exit 1
    }
    reg_view_fail_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-head.XXXXXX") || {
        larch_err "design-log-publish: mktemp failed for pr-head capture"
        emit_publish_failure "$PR_NUM" "${PR_URL:-}"
        exit 1
    }
    while [[ "$reg_probe" -le "$REG_MAX_PROBES" && "$SECONDS" -le "$REG_DEADLINE" ]]; do
        : >"$reg_checks_err_file"
        set +e
        reg_checks_out=$(gh pr checks "$PR_NUM" "${gh_repo_args[@]}" --required --json bucket 2>"$reg_checks_err_file")
        reg_checks_rc=$?
        set -e
        last_checks_out="$reg_checks_out"
        last_checks_err=$(cat "$reg_checks_err_file" 2>/dev/null || true)
        checks_json_nonempty=false
        if printf '%s\n' "${reg_checks_out:-}" | jq -e 'type == "array"' >/dev/null 2>&1; then
            if printf '%s\n' "${reg_checks_out:-}" | jq -e 'length > 0' >/dev/null 2>&1; then
                checks_json_nonempty=true
            fi
        elif printf '%s\n' "${reg_checks_out:-}" | jq -e '.' >/dev/null 2>&1 && [[ "$non_array_checks_json_logged" != true ]]; then
            larch_err "design-log-publish: gh pr checks returned non-array JSON during registration for PR $PR_NUM; treating as not registered yet: $(redact_diagnostic "${reg_checks_out:-unknown}")"
            non_array_checks_json_logged=true
        fi
        if [[ "$checks_json_nonempty" == true ]]; then
            : >"$reg_view_fail_file"
            if with_transient_retry transient_envelope_predicate_none "$reg_view_fail_file" \
                gh pr view "$PR_NUM" "${gh_repo_args[@]}" --json headRefOid; then
                view_rc=0
            else
                view_rc=$_WTR_RC
            fi
            last_view_out=$_WTR_OUT
            last_view_err=$(cat "$reg_view_fail_file" 2>/dev/null || true)
            pr_head_oid=""
            if [[ "$view_rc" -eq 0 ]]; then
                pr_head_oid=$(printf '%s\n' "${last_view_out:-}" | jq -r '.headRefOid // empty' 2>/dev/null || true)
            fi
            if [[ -n "$pr_head_oid" && "$pr_head_oid" == "$PUSH_HEAD_SHA" ]]; then
                checks_registered=true
                break
            fi
        fi
        if [[ "$reg_probe" -lt "$REG_MAX_PROBES" ]]; then
            reg_remaining=$((REG_DEADLINE - SECONDS))
            if [[ "$reg_remaining" -le 0 ]]; then
                break
            fi
            reg_sleep="$REG_INTERVAL"
            if [[ "$reg_sleep" -gt "$reg_remaining" ]]; then
                reg_sleep="$reg_remaining"
            fi
            "${SLEEP_SCRIPT_DIR:-$SCRIPT_DIR}/sleep-seconds.sh" "$reg_sleep" >/dev/null 2>&1 || sleep "$reg_sleep"
        fi
        reg_probe=$((reg_probe + 1))
        : "$reg_checks_rc"
    done
    rm -f "$reg_checks_err_file" "$reg_view_fail_file"
    reg_checks_err_file=""
    reg_view_fail_file=""

    if [[ "$checks_registered" != true ]]; then
        reg_stop_reason="deadline"
        if [[ "$reg_probe" -ge "$REG_MAX_PROBES" ]]; then
            reg_stop_reason="probe-budget"
        fi
        larch_err "design-log-publish: required CI checks did not register within ${REG_TIMEOUT}s (probe ${reg_probe}/${REG_MAX_PROBES}; stop=${reg_stop_reason}; pushed head ${PUSH_HEAD_SHA}) for PR $PR_NUM; refusing to merge: checks=$(redact_diagnostic "${last_checks_out:-${last_checks_err:-unknown}}") head=$(redact_diagnostic "${last_view_out:-${last_view_err:-unknown}}")"
        merge_rc=1
    else
        set +e
        ci_wait_out=$(gh pr checks "$PR_NUM" "${gh_repo_args[@]}" --required --watch --fail-fast 2>&1)
        ci_rc=$?
        set -e
        if [[ "$ci_rc" -ne 0 ]]; then
            larch_err "design-log-publish: required CI checks did not pass (rc=$ci_rc) for PR $PR_NUM; refusing to merge: $(redact_diagnostic "${ci_wait_out:-unknown}")"
            merge_rc="$ci_rc"
        else
            merge_fail_file=$(mktemp "${TMPDIR:-/tmp}/design-log-publish-merge.XXXXXX") || {
                larch_err "design-log-publish: mktemp failed for merge capture"
                emit_publish_failure "$PR_NUM" "${PR_URL:-}"
                exit 1
            }
            if with_transient_retry transient_envelope_predicate_none "$merge_fail_file" \
                gh pr merge "${gh_repo_args[@]}" "$PR_NUM" --squash --admin --delete-branch; then
                merge_rc=0
            else
                merge_rc=$_WTR_RC
            fi
        fi
    fi
fi

git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" 2>/dev/null || true
rm -rf "${WT_PARENT:-}" 2>/dev/null || true
WT_DIR=""
WT_PARENT=""
rm -f "${push_fail_file:-}" "${create_fail_file:-}" "${merge_fail_file:-}" 2>/dev/null || true
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
