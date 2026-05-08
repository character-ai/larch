#!/usr/bin/env bash
# launch-gemini-review.sh — Launch a generic Gemini code review and normalize JSON output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"
# shellcheck source=scripts/lib-gemini-model-resolver.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-gemini-model-resolver.sh"

ORIGINAL_ARGS=("$@")
OUTPUT=""
TIMEOUT=""
PROMPT=""
TIMING_TASK_KIND="${LARCH_TIMING_TASK_KIND:-}"
SNAPSHOT_GUARD_STATE="uninitialized"
SNAPSHOT_GUARD_NOTICE=""
SNAPSHOT_GUARD_MESSAGE=""
SNAPSHOT_PRE=""
SNAPSHOT_POST=""
SNAPSHOT_BACKUP=""
SNAPSHOT_REPO_ROOT=""
SNAPSHOT_STATUS=0
SNAPSHOT_ARTIFACT_EXACT=()
SNAPSHOT_ARTIFACT_PREFIX=()
DIRTY_TREE_WRITTEN=false
UNTRACKED_BASELINE=""
DIRTY_TREE_SIDECAR=""
AGENT_RAN=false

# Build a redacted copy of ORIGINAL_ARGS for write_meta() so the full --prompt
# body (review instructions and any caller-provided context) is not duplicated
# to ${OUTPUT}.meta. .meta CMD_JSON= replays the launcher
# invocation as a single-line JSON array, not raw Gemini, so the actual prompt
# content is unnecessary for retry semantics. On the missing-jq fail-closed
# path, write_meta() omits CMD_JSON so write_done() can still run.
REDACTED_ARGS=()
_skip_next=0
for _arg in "${ORIGINAL_ARGS[@]}"; do
    if (( _skip_next == 1 )); then
        _hash="<unhashed>"
        if command -v shasum >/dev/null 2>&1; then
            _hash=$(printf '%s' "$_arg" | LC_ALL=C shasum -a 256 2>/dev/null | awk '{print $1}')
        elif command -v sha256sum >/dev/null 2>&1; then
            _hash=$(printf '%s' "$_arg" | sha256sum | awk '{print $1}')
        fi
        REDACTED_ARGS+=("<REDACTED:sha256=${_hash:0:16},len=${#_arg}>")
        _skip_next=0
        continue
    fi
    REDACTED_ARGS+=("$_arg")
    if [[ "$_arg" == "--prompt" ]]; then
        _skip_next=1
    fi
done
unset _arg _skip_next _hash

usage() {
    echo "Usage: launch-gemini-review.sh --output FILE --timeout SECS --prompt TEXT" >&2
}

# shellcheck disable=SC2317,SC2329 # invoked indirectly by EXIT traps.
_emit_timing_record() {
    local rc=${1:-$?}
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    [[ -n "${TIMING_START_S:-}" && -n "${OUTPUT:-}" ]] || return 0
    "$SCRIPT_DIR/timing-ledger.sh" record-vendor-task \
        --vendor gemini \
        --task-kind "${TIMING_TASK_KIND:-gemini-review}" \
        --start-s "$TIMING_START_S" \
        --end-s "$end_s" \
        --output "$OUTPUT" \
        --exit-code "$rc" \
        --status "$status" \
        >/dev/null 2>&1 || true
}

write_empty_output() {
    local tmp
    tmp=$(mktemp "${OUTPUT}.tmp.XXXXXX")
    : > "$tmp"
    mv "$tmp" "$OUTPUT"
}

write_done() {
    local code="$1"
    local tmp
    tmp=$(mktemp "${OUTPUT}.done.tmp.XXXXXX")
    printf '%s\n' "$code" > "$tmp"
    mv "$tmp" "${OUTPUT}.done"
}

# shellcheck disable=SC2329 # invoked from fail_closed, success tail, and exit trap.
_write_dirty_tree_sidecar() {
    [[ -n "$OUTPUT" ]] || return 0
    [[ "$DIRTY_TREE_WRITTEN" == "false" ]] || return 0
    [[ -n "$DIRTY_TREE_SIDECAR" ]] || return 0
    if [[ -x "$SCRIPT_DIR/check-mid-run-dirty-tree.sh" ]]; then
        "$SCRIPT_DIR/check-mid-run-dirty-tree.sh" --mode baseline --baseline "$UNTRACKED_BASELINE" --sidecar "$DIRTY_TREE_SIDECAR" >/dev/null 2>&1 || true
    fi
    DIRTY_TREE_WRITTEN=true
}

# shellcheck disable=SC2329 # invoked from fail_closed and exit trap on early-short-circuit paths.
_write_unknown_dirty_tree_sidecar() {
    # Used when no detector probe ran (e.g., MISSING_JQ / model-resolve /
    # snapshot-guard setup failure short-circuited before run-external-agent).
    # STATUS=unknown routes consumers through the same recovery-safe path as a
    # real detector failure, rather than letting them treat a present sidecar
    # with STATUS=clean as "launcher proved the tree clean."
    [[ -n "$OUTPUT" ]] || return 0
    [[ "$DIRTY_TREE_WRITTEN" == "false" ]] || return 0
    [[ -n "$DIRTY_TREE_SIDECAR" ]] || return 0
    local reason="$1"
    local tmp="${DIRTY_TREE_SIDECAR}.tmp.$$"
    {
        printf 'STATUS=unknown\n'
        printf 'MODE=baseline\n'
        if [[ -r "$UNTRACKED_BASELINE" ]]; then
            printf 'UNTRACKED_BASELINE=present\n'
        else
            printf 'UNTRACKED_BASELINE=missing\n'
        fi
        printf 'REASON=%s\n' "$reason"
    } > "$tmp" 2>/dev/null && mv -f "$tmp" "$DIRTY_TREE_SIDECAR" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
    DIRTY_TREE_WRITTEN=true
}

# shellcheck disable=SC2317,SC2329 # invoked indirectly by EXIT trap.
_publish_dirty_tree_on_exit() {
    [[ "$DIRTY_TREE_WRITTEN" == "false" ]] || return 0
    if [[ "$AGENT_RAN" == "true" ]]; then
        _write_dirty_tree_sidecar
    else
        _write_unknown_dirty_tree_sidecar "exit-trap-no-agent-ran"
    fi
}

write_meta() {
    local tmp
    tmp=$(mktemp "${OUTPUT}.meta.tmp.XXXXXX")
    {
        echo "TOOL=gemini"
        echo "TIMEOUT=$EFFECTIVE_TIMEOUT"
        echo "CAPTURE_STDOUT=false"
        # The inner run-external-agent invocation uses --capture-stdout-only;
        # record the actual capture mode here so collector retry paths that
        # rebuild flags from .meta do not silently drop --capture-stdout-only.
        echo "CAPTURE_STDOUT_ONLY=true"
        echo "OUTPUT_FILE=$OUTPUT"
        # CMD_JSON replays the LAUNCHER (not raw gemini) so retry re-runs
        # JSON normalization. The --prompt body is already redacted to a
        # sha256 prefix + byte length in REDACTED_ARGS to avoid persisting
        # prompt content into the session tmpdir's .meta artifact.
        # If jq is unavailable (the LARCH_TEST_FORCE_MISSING_JQ /
        # MISSING_JQ fail_closed path), omit CMD_JSON entirely; the collector
        # treats missing CMD_JSON as fail-closed while write_done() still runs.
        if command -v jq >/dev/null 2>&1 && [[ "${LARCH_TEST_FORCE_MISSING_JQ:-}" != "true" ]]; then
            if META_CMD_JSON=$(jq -cn --args '$ARGS.positional' -- "$0" "${REDACTED_ARGS[@]}"); then
                printf 'CMD_JSON=%s\n' "$META_CMD_JSON"
            fi
        fi
    } > "$tmp"
    mv "$tmp" "${OUTPUT}.meta"
}

fail_closed() {
    local code="$1"
    local reason="$2"
    local guard_code=0
    if [[ "$SNAPSHOT_GUARD_STATE" == "armed" ]]; then
        run_snapshot_guard || guard_code=$?
        if [[ -n "$SNAPSHOT_GUARD_MESSAGE" ]]; then
            reason="${reason}"$'\n'"${SNAPSHOT_GUARD_MESSAGE}"
        fi
        if [[ "$guard_code" -eq 99 ]]; then
            code=99
        fi
    fi
    write_empty_output
    {
        [[ -n "$reason" ]] && printf '%s\n' "$reason"
        [[ -n "$SNAPSHOT_GUARD_NOTICE" ]] && printf '%s\n' "$SNAPSHOT_GUARD_NOTICE"
        [[ -f "$RAW_OUTPUT.diag" ]] && cat "$RAW_OUTPUT.diag"
    } >> "${OUTPUT}.diag"
    if [[ "$AGENT_RAN" == "true" ]]; then
        _write_dirty_tree_sidecar
    else
        _write_unknown_dirty_tree_sidecar "fail-closed-no-agent-ran"
    fi
    write_meta
    write_done "$code"
    exit "$code"
}

sha256_file() {
    local path="$1"
    if [[ -L "$path" ]]; then
        if command -v shasum >/dev/null 2>&1; then
            readlink "$path" | LC_ALL=C shasum -a 256 2>/dev/null | awk '{print $1}'
        else
            readlink "$path" | sha256sum | awk '{print $1}'
        fi
    elif command -v shasum >/dev/null 2>&1; then
        LC_ALL=C shasum -a 256 "$path" 2>/dev/null | awk '{print $1}'
    else
        sha256sum "$path" | awk '{print $1}'
    fi
}

resolve_existing_parent_path() {
    local path="$1"
    local dir base
    case "$path" in
        /*) ;;
        *) path="$PWD/$path" ;;
    esac
    dir=$(dirname "$path")
    base=$(basename "$path")
    if [[ -d "$dir" ]]; then
        (cd "$dir" && printf '%s/%s\n' "$(pwd -P)" "$base")
    fi
}

repo_relative_if_inside() {
    local abs="$1"
    case "$abs" in
        "$SNAPSHOT_REPO_ROOT"/*) printf '%s\n' "${abs#"$SNAPSHOT_REPO_ROOT"/}" ;;
        "$SNAPSHOT_REPO_ROOT") printf '.\n' ;;
    esac
}

add_snapshot_artifact_path() {
    local path="$1"
    local abs rel
    abs=$(resolve_existing_parent_path "$path" || true)
    [[ -n "$abs" ]] || return 0
    rel=$(repo_relative_if_inside "$abs")
    [[ -n "$rel" && "$rel" != "." ]] || return 0
    SNAPSHOT_ARTIFACT_EXACT+=("$rel")
}

add_snapshot_artifact_prefix() {
    local path="$1"
    local abs rel
    abs=$(resolve_existing_parent_path "$path" || true)
    [[ -n "$abs" ]] || return 0
    rel=$(repo_relative_if_inside "$abs")
    [[ -n "$rel" && "$rel" != "." ]] || return 0
    SNAPSHOT_ARTIFACT_PREFIX+=("$rel")
}

snapshot_path_is_artifact() {
    local path="$1"
    local artifact
    for artifact in "${SNAPSHOT_ARTIFACT_EXACT[@]+"${SNAPSHOT_ARTIFACT_EXACT[@]}"}"; do
        [[ "$path" == "$artifact" ]] && return 0
    done
    for artifact in "${SNAPSHOT_ARTIFACT_PREFIX[@]+"${SNAPSHOT_ARTIFACT_PREFIX[@]}"}"; do
        [[ "$path" == "$artifact"* ]] && return 0
    done
    return 1
}

snapshot_timeout_seconds() {
    # Returns the snapshot timeout cap in canonical decimal seconds.
    # Falls back to default 30 on: empty, non-digit, or non-positive
    # (`0`, `00`, ...). Forces base-10 so leading-zero values like `010`
    # are interpreted as 10s, not octal 8s. Non-positive values are
    # rejected rather than treated as "disable timeout" — disabling is
    # not a supported mode (see launch-gemini-review.md).
    local value="${LARCH_GEMINI_SNAPSHOT_TIMEOUT:-30}"
    local decimal
    case "$value" in
        ''|*[!0-9]*) printf '30\n'; return ;;
    esac
    decimal=$((10#$value))
    if (( decimal < 1 )); then
        printf '30\n'
    else
        printf '%s\n' "$decimal"
    fi
}

snapshot_timed_out() {
    local start="$1"
    local cap="$2"
    (( cap > 0 && SECONDS - start >= cap ))
}

backup_snapshot_path() {
    local path="$1"
    local dest="$SNAPSHOT_BACKUP/$path"
    mkdir -p "$(dirname "$dest")"
    cp -pP "$SNAPSHOT_REPO_ROOT/$path" "$dest"
}

snapshot_status_file_mentions_path() {
    local status_file="$1"
    local path="$2"
    grep -q -F " $path" "$status_file" 2>/dev/null
}

snapshot_pre_status_mentions_path() {
    local path="$1"
    snapshot_status_file_mentions_path "${SNAPSHOT_PRE}.status" "$path"
}

snapshot_pre_index_mentions_path() {
    # True iff the pre-launch snapshot records carried an `I\t-\t<path>`
    # entry for this path — i.e. operator already had something staged
    # for this path before Gemini ran. Used by snapshot_restore_path to
    # decide whether `git reset -q HEAD -- <path>` is safe to call after
    # restoring worktree content from backup. When operator had no pre
    # index entry, reset clears any reviewer-added index changes (the
    # `git add` mutation case from FINDING_7). When operator had a pre
    # index entry, reset would clobber operator state — skip it.
    local path="$1"
    [[ -f "${SNAPSHOT_PRE}.records" ]] || return 1
    awk -v p="$path" -F'\t' '$1=="I" && $3==p { found=1; exit } END { exit !found }' \
        "${SNAPSHOT_PRE}.records" 2>/dev/null
}

tracked_snapshot_hash() {
    local path="$1"
    local status_file="$2"
    local clean_oid="$3"
    if snapshot_status_file_mentions_path "$status_file" "$path"; then
        if [[ -e "$SNAPSHOT_REPO_ROOT/$path" || -L "$SNAPSHOT_REPO_ROOT/$path" ]]; then
            sha256_file "$SNAPSHOT_REPO_ROOT/$path"
        else
            printf 'MISSING\n'
        fi
        return 0
    fi
    printf '%s\n' "$clean_oid"
}

capture_snapshot() {
    local out="$1"
    local mode="${2:-post}"
    local head_sha start cap path hash body status_file entry meta clean_oid
    body="${out}.body"
    status_file="${out}.status"
    start=$SECONDS
    cap=$(snapshot_timeout_seconds)
    head_sha=$(git -C "$SNAPSHOT_REPO_ROOT" rev-parse HEAD 2>/dev/null) || return 1
    printf 'HEAD_SHA=%s\n' "$head_sha" > "$out"
    git -C "$SNAPSHOT_REPO_ROOT" status --porcelain > "$status_file"
    : > "$body"

    while IFS= read -r -d '' entry; do
        meta="${entry%%$'\t'*}"
        path="${entry#*$'\t'}"
        clean_oid="${meta#* }"
        clean_oid="${clean_oid%% *}"
        snapshot_path_is_artifact "$path" && continue
        if snapshot_timed_out "$start" "$cap"; then
            rm -f "$body"
            return 124
        fi
        hash=$(tracked_snapshot_hash "$path" "$status_file" "$clean_oid") || return 1
        printf 'T\t%s\t%s\n' "$hash" "$path" >> "$body"
        [[ "$mode" == "pre" && "$hash" != "MISSING" && -n "$SNAPSHOT_BACKUP" && ! -e "$SNAPSHOT_BACKUP/$path" && ! -L "$SNAPSHOT_BACKUP/$path" ]] \
            && snapshot_pre_status_mentions_path "$path" \
            && backup_snapshot_path "$path"
    done < <(git -C "$SNAPSHOT_REPO_ROOT" ls-files -s -z)

    while IFS= read -r -d '' path; do
        snapshot_path_is_artifact "$path" && continue
        if snapshot_timed_out "$start" "$cap"; then
            rm -f "$body"
            return 124
        fi
        if [[ -e "$SNAPSHOT_REPO_ROOT/$path" || -L "$SNAPSHOT_REPO_ROOT/$path" ]]; then
            hash=$(sha256_file "$SNAPSHOT_REPO_ROOT/$path") || return 1
            printf 'U\t%s\t%s\n' "$hash" "$path" >> "$body"
            [[ "$mode" == "pre" && -n "$SNAPSHOT_BACKUP" && ! -e "$SNAPSHOT_BACKUP/$path" && ! -L "$SNAPSHOT_BACKUP/$path" ]] \
                && backup_snapshot_path "$path"
        fi
    done < <(git -C "$SNAPSHOT_REPO_ROOT" ls-files --others --exclude-standard -z)

    # Capture index state so reviewer mutations that change ONLY the index
    # (e.g. `git add` of an already-modified tracked file) are detected.
    # On-disk content hashes alone miss these — pre and post hashes are
    # identical, but the index has new content. The 3-field schema
    # (`I\t-\t<path>`) keeps `cut -f3-` semantics uniform with T/U records
    # so run_snapshot_guard's delta_paths extraction stays correct.
    while IFS= read -r -d '' path; do
        snapshot_path_is_artifact "$path" && continue
        if snapshot_timed_out "$start" "$cap"; then
            rm -f "$body"
            return 124
        fi
        printf 'I\t-\t%s\n' "$path" >> "$body"
    done < <(git -C "$SNAPSHOT_REPO_ROOT" diff --cached --name-only -z HEAD 2>/dev/null)

    LC_ALL=C sort "$body" >> "$out"
    rm -f "$body"
}

# shellcheck disable=SC2317,SC2329 # invoked via `trap ... EXIT` after setup_snapshot_guard
snapshot_cleanup_on_exit() {
    # Best-effort removal of snapshot temp resources at process exit.
    # Registered via `trap` once setup_snapshot_guard has populated the
    # SNAPSHOT_PRE / SNAPSHOT_POST / SNAPSHOT_BACKUP variables. Avoids
    # leaving copies of tracked/untracked working-tree contents under
    # ${TMPDIR:-/tmp} indefinitely (relevant when IMPLEMENT_TMPDIR is
    # unset, e.g. ad-hoc or test runs).
    if [[ -n "${SNAPSHOT_PRE:-}" ]]; then
        rm -f -- \
            "$SNAPSHOT_PRE" \
            "${SNAPSHOT_PRE}.body" \
            "${SNAPSHOT_PRE}.records" \
            "${SNAPSHOT_PRE}.status" 2>/dev/null || true
    fi
    if [[ -n "${SNAPSHOT_POST:-}" ]]; then
        rm -f -- \
            "$SNAPSHOT_POST" \
            "${SNAPSHOT_POST}.body" \
            "${SNAPSHOT_POST}.records" \
            "${SNAPSHOT_POST}.added" \
            "${SNAPSHOT_POST}.removed" \
            "${SNAPSHOT_POST}.paths" \
            "${SNAPSHOT_POST}.status" 2>/dev/null || true
    fi
    if [[ -n "${SNAPSHOT_BACKUP:-}" && -d "$SNAPSHOT_BACKUP" ]]; then
        rm -rf -- "$SNAPSHOT_BACKUP" 2>/dev/null || true
    fi
}

setup_snapshot_guard() {
    local tmp_parent
    if ! SNAPSHOT_REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
        SNAPSHOT_GUARD_STATE="skipped"
        SNAPSHOT_GUARD_NOTICE="snapshot guard skipped: not inside a git working tree"
        return 0
    fi
    if ! git -C "$SNAPSHOT_REPO_ROOT" rev-parse HEAD >/dev/null 2>&1; then
        SNAPSHOT_GUARD_STATE="skipped"
        SNAPSHOT_GUARD_NOTICE="snapshot guard skipped: not inside a git working tree"
        return 0
    fi

    add_snapshot_artifact_path "$OUTPUT"
    add_snapshot_artifact_path "${OUTPUT}.done"
    add_snapshot_artifact_path "${OUTPUT}.meta"
    add_snapshot_artifact_path "${OUTPUT}.diag"
    add_snapshot_artifact_path "$RAW_OUTPUT"
    add_snapshot_artifact_path "${RAW_OUTPUT}.done"
    add_snapshot_artifact_path "${RAW_OUTPUT}.meta"
    add_snapshot_artifact_path "${RAW_OUTPUT}.diag"
    add_snapshot_artifact_prefix "${OUTPUT}.tmp."
    add_snapshot_artifact_prefix "${OUTPUT}.done.tmp."
    add_snapshot_artifact_prefix "${OUTPUT}.meta.tmp."
    add_snapshot_artifact_prefix "${RAW_OUTPUT}.tmp."
    add_snapshot_artifact_prefix "${RAW_OUTPUT}.done.tmp."
    add_snapshot_artifact_prefix "${RAW_OUTPUT}.meta.tmp."

    tmp_parent="${IMPLEMENT_TMPDIR:-${TMPDIR:-/tmp}}"
    [[ -d "$tmp_parent" ]] || tmp_parent="${TMPDIR:-/tmp}"
    SNAPSHOT_PRE=$(mktemp "$tmp_parent/gemini-review-snapshot-pre.XXXXXX")
    SNAPSHOT_POST=$(mktemp "$tmp_parent/gemini-review-snapshot-post.XXXXXX")
    SNAPSHOT_BACKUP=$(mktemp -d "$tmp_parent/gemini-review-snapshot-backup.XXXXXX")
    # Register cleanup AFTER mktemp so a setup-stage capture failure still
    # unlinks the temp files. Cleanup is idempotent and tolerates partial state.
    # _publish_dirty_tree_on_exit runs BEFORE snapshot_cleanup_on_exit so the
    # dirty-tree sidecar is emitted before snapshot temps are removed. The
    # sidecar lives at ${OUTPUT}.dirty-tree, separate from snapshot temps under
    # $SNAPSHOT_BACKUP, so ordering is defensive but not strictly required.
    trap '_emit_timing_record $?; _publish_dirty_tree_on_exit; snapshot_cleanup_on_exit' EXIT

    capture_snapshot "$SNAPSHOT_PRE" pre
    SNAPSHOT_STATUS=$?
    if [[ "$SNAPSHOT_STATUS" -ne 0 ]]; then
        case "$SNAPSHOT_STATUS" in
            124)
                SNAPSHOT_GUARD_STATE="skipped"
                SNAPSHOT_GUARD_NOTICE="SNAPSHOT_GUARD_TIMEOUT: snapshot guard skipped after ${LARCH_GEMINI_SNAPSHOT_TIMEOUT:-30}s"
                return 0
                ;;
            *)
                SNAPSHOT_GUARD_STATE="failed"
                SNAPSHOT_GUARD_MESSAGE="SNAPSHOT_GUARD_FAILED: could not capture pre-launch snapshot"
                return 99
                ;;
        esac
    fi
    SNAPSHOT_GUARD_STATE="armed"
}

snapshot_line_for_path() {
    local file="$1"
    local path="$2"
    local line line_path
    while IFS= read -r line; do
        line_path=$(printf '%s\n' "$line" | cut -f3-)
        if [[ "$line_path" == "$path" ]]; then
            printf '%s\n' "$line"
            return 0
        fi
    done < "$file"
    return 0
}

snapshot_restore_path() {
    local path="$1"
    local pre_line="$2"
    local pre_kind pre_hash backup_path
    pre_kind="${pre_line%%$'\t'*}"
    pre_hash="${pre_line#*$'\t'}"
    pre_hash="${pre_hash%%$'\t'*}"
    backup_path="$SNAPSHOT_BACKUP/$path"

    if [[ -z "$pre_line" ]]; then
        rm -f -- "$SNAPSHOT_REPO_ROOT/$path"
        git -C "$SNAPSHOT_REPO_ROOT" reset -q HEAD -- "$path" >/dev/null 2>&1 || true
        return 0
    fi

    if [[ "$pre_hash" == "MISSING" ]]; then
        rm -f -- "$SNAPSHOT_REPO_ROOT/$path"
        git -C "$SNAPSHOT_REPO_ROOT" reset -q HEAD -- "$path" >/dev/null 2>&1 || true
        return 0
    fi

    if [[ -e "$backup_path" || -L "$backup_path" ]]; then
        mkdir -p "$(dirname "$SNAPSHOT_REPO_ROOT/$path")"
        cp -pP "$backup_path" "$SNAPSHOT_REPO_ROOT/$path"
        # Reset the index entry to HEAD for this path UNLESS operator had
        # a pre-existing index entry we must preserve. The pre I-record
        # check is the precise signal: presence ⇒ operator staged it pre-launch
        # (don't touch); absence ⇒ any post index entry is reviewer-introduced
        # and must be cleared. This subsumes the older
        # `pre_kind=T && !pre-status-mentioned` heuristic, which silently
        # missed the FINDING_7 case where operator had worktree-mod (status
        # mentioned, no index) and reviewer ran `git add`.
        if ! snapshot_pre_index_mentions_path "$path"; then
            git -C "$SNAPSHOT_REPO_ROOT" reset -q HEAD -- "$path" >/dev/null 2>&1 || true
        fi
        return 0
    fi

    if [[ "$pre_kind" == "T" ]]; then
        git -C "$SNAPSHOT_REPO_ROOT" checkout -q HEAD -- "$path" || return 1
        git -C "$SNAPSHOT_REPO_ROOT" reset -q HEAD -- "$path" >/dev/null 2>&1 || true
        return 0
    fi

    return 1
}

run_snapshot_guard() {
    local pre_body post_body added removed delta_paths path pre_line guard_status pre_head post_head
    local recovered_paths=()
    local unrecoverable_paths=()
    [[ "$SNAPSHOT_GUARD_STATE" == "armed" ]] || return 0

    capture_snapshot "$SNAPSHOT_POST" post
    SNAPSHOT_STATUS=$?
    if [[ "$SNAPSHOT_STATUS" -ne 0 ]]; then
        case "$SNAPSHOT_STATUS" in
            124)
                SNAPSHOT_GUARD_NOTICE="SNAPSHOT_GUARD_TIMEOUT: snapshot guard skipped after ${LARCH_GEMINI_SNAPSHOT_TIMEOUT:-30}s"
                return 0
                ;;
            *)
                SNAPSHOT_GUARD_MESSAGE="SNAPSHOT_GUARD_FAILED: could not capture post-launch snapshot"
                return 99
                ;;
        esac
    fi

    if cmp -s "$SNAPSHOT_PRE" "$SNAPSHOT_POST"; then
        return 0
    fi

    pre_head=$(head -n 1 "$SNAPSHOT_PRE")
    post_head=$(head -n 1 "$SNAPSHOT_POST")
    pre_body="${SNAPSHOT_PRE}.records"
    post_body="${SNAPSHOT_POST}.records"
    added="${SNAPSHOT_POST}.added"
    removed="${SNAPSHOT_POST}.removed"
    delta_paths="${SNAPSHOT_POST}.paths"
    tail -n +2 "$SNAPSHOT_PRE" > "$pre_body"
    tail -n +2 "$SNAPSHOT_POST" > "$post_body"
    comm -13 "$pre_body" "$post_body" > "$added"
    comm -23 "$pre_body" "$post_body" > "$removed"
    { cut -f3- "$added"; cut -f3- "$removed"; } | LC_ALL=C sort -u > "$delta_paths"

    guard_status=0
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        pre_line=$(snapshot_line_for_path "$pre_body" "$path")
        if snapshot_restore_path "$path" "$pre_line"; then
            recovered_paths+=("$path")
        else
            unrecoverable_paths+=("$path")
            guard_status=1
        fi
    done < "$delta_paths"

    if [[ "$pre_head" != "$post_head" ]]; then
        unrecoverable_paths+=("HEAD")
        guard_status=1
    fi

    if (( ${#unrecoverable_paths[@]} > 0 )); then
        SNAPSHOT_GUARD_MESSAGE="UNRECOVERABLE_DELTA: Gemini reviewer mutated repo paths that could not be restored: ${unrecoverable_paths[*]}"
        return 1
    fi
    if (( ${#recovered_paths[@]} > 0 )); then
        SNAPSHOT_GUARD_MESSAGE="SNAPSHOT_GUARD_TRIGGERED: Gemini reviewer mutated repo paths; reverted: ${recovered_paths[*]}"
        return 1
    fi

    return "$guard_status"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { echo "launch-gemini-review.sh: --timing-task-kind requires a non-empty, non-flag-like value" >&2; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --agent-file|--mode|--description-text|--scope-files|--competition-notice)
            echo "launch-gemini-review.sh: specialist mode is not supported in v1" >&2
            exit 2 ;;
        --help) usage; exit 0 ;;
        *) echo "launch-gemini-review.sh: unknown flag: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$OUTPUT" || -z "$TIMEOUT" || -z "$PROMPT" ]]; then
    echo "launch-gemini-review.sh: --output, --timeout, and --prompt are required" >&2
    usage
    exit 2
fi

validate_meta_scalar_path --output "$OUTPUT" || exit 2

case "$TIMEOUT" in
    ''|*[!0-9]*|0) echo "launch-gemini-review.sh: --timeout must be a positive integer, got '$TIMEOUT'" >&2; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    echo "launch-gemini-review.sh: --timeout must be a positive integer, got '$TIMEOUT'" >&2
    exit 2
fi
# Normalize to canonical decimal so downstream arithmetic (the > 600 clamp
# below) does not interpret leading-zero values as octal: e.g. `0601` would
# otherwise become 385, silently bypassing the clamp; `08`/`09` would abort
# under `set -e` with "value too great for base".
TIMEOUT=$((10#$TIMEOUT))

if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
fi
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="${IMPLEMENT_TMPDIR}/claude-source.env"
fi

: "${TIMING_TASK_KIND:=gemini-review}"
TIMING_START_S=$(date +%s)

# Assign DIRTY_TREE_SIDECAR / UNTRACKED_BASELINE BEFORE installing the EXIT
# trap so an asynchronous exit (SIGINT / SIGTERM) between trap registration and
# the stale-cleanup block below can still publish a sidecar. The helpers no-op
# when these vars are empty, so without this ordering the narrow window between
# trap install and assignment would silently produce no sidecar on early
# signal-driven exits. The actual stale cleanup of these paths and the
# baseline-capture call still happen below, after the MISSING_JQ check, so the
# baseline reflects the post-stale-cleanup state of the working tree.
DIRTY_TREE_SIDECAR="${OUTPUT}.dirty-tree"
UNTRACKED_BASELINE="${OUTPUT}.untracked-baseline"

trap '_emit_timing_record $?; _publish_dirty_tree_on_exit' EXIT

EFFECTIVE_TIMEOUT="$TIMEOUT"
if (( EFFECTIVE_TIMEOUT > 600 )); then
    EFFECTIVE_TIMEOUT=600
fi

RAW_OUTPUT="${OUTPUT}.raw"
rm -f "$OUTPUT" "${OUTPUT}.done" "${OUTPUT}.meta" "${OUTPUT}.diag" \
      "$RAW_OUTPUT" "${RAW_OUTPUT}.done" "${RAW_OUTPUT}.meta" "${RAW_OUTPUT}.diag"

# Stale-cleanup of the dirty-tree sidecar paths (the variables themselves
# were assigned earlier, before the EXIT trap was installed, so an early
# signal-driven exit can already publish a sidecar). Capture the untracked
# baseline AFTER stale cleanup so the baseline reflects the post-cleanup
# state of the working tree. The capture itself happens BEFORE the
# early-short-circuit fail_closed branches below (MISSING_JQ, model-resolve
# failure, snapshot-guard setup failure — all reached AFTER this block) so
# each of those paths can emit STATUS=unknown via
# _write_unknown_dirty_tree_sidecar.
# Gemini reviewer call sites are dormant per SECURITY.md; this machinery is
# preparatory so /review Step 5 sidecar consultation picks up Gemini coverage
# automatically when the call sites are reintroduced (issue #1487; matches
# the contract introduced for Cursor/Codex by #1437).
rm -f "$DIRTY_TREE_SIDECAR" "$UNTRACKED_BASELINE" \
      "${DIRTY_TREE_SIDECAR}.tracked-paths" \
      "${DIRTY_TREE_SIDECAR}.new-untracked-paths"
"$SCRIPT_DIR/snapshot-untracked.sh" --output "$UNTRACKED_BASELINE" --nul

if [[ "${LARCH_TEST_FORCE_MISSING_JQ:-}" == "true" ]] || ! command -v jq >/dev/null 2>&1; then
    RAW_OUTPUT="${OUTPUT}.raw"
    fail_closed 127 "MISSING_JQ: jq is required to parse Gemini JSON output"
fi

GEMINI_REVIEW_HARDENING_PREAMBLE=$(cat <<'EOF'
HARD CONSTRAINTS — your role is read-only review. You MUST NOT modify the working tree by any means:
- Do not redirect, tee, append, or pipe into any file (no `>`, `>>`, `tee`, `tee -a`).
- Do not run `rm`, `mv`, `cp` (when target is in the repo), `mkdir`, `touch`, `sed -i`, `awk -i inplace`, `perl -i`, or any command with an in-place / write effect.
- Do not run `git add`, `git commit`, `git checkout <path>`, `git reset <path>`, `git restore`, `git stash`, `git rebase`, `git merge`, `git push`, or any command that mutates branch state, the index, or refs.
- Do not invoke any tool that writes files (write_file, replace, edit, edit_file, delete_file, or any future-renamed equivalent).
The launcher enforces this with a working-tree snapshot guard: any mutation triggers a loud failure and a revert, regardless of how the mutation was performed.
EOF
)
PROMPT="${GEMINI_REVIEW_HARDENING_PREAMBLE}"$'\n\n'"${PROMPT}"

GEMINI_MODEL_ERR=$(mktemp "${OUTPUT}.gemini-model.tmp.XXXXXX")
if GEMINI_MODEL=$(resolve_gemini_model 2> "$GEMINI_MODEL_ERR"); then
    rm -f "$GEMINI_MODEL_ERR"
else
    MODEL_REASON=$(cat "$GEMINI_MODEL_ERR")
    rm -f "$GEMINI_MODEL_ERR"
    fail_closed 2 "$MODEL_REASON"
fi

if ! setup_snapshot_guard; then
    fail_closed 99 "$SNAPSHOT_GUARD_MESSAGE"
fi

RUN_EXIT=0
AGENT_RAN=true
"$SCRIPT_DIR/run-external-agent.sh" \
    --tool gemini \
    --output "$RAW_OUTPUT" \
    --timeout "$EFFECTIVE_TIMEOUT" \
    --capture-stdout-only \
    -- gemini -m "$GEMINI_MODEL" -p "$PROMPT" -o json --skip-trust --approval-mode yolo --admin-policy "$SCRIPT_DIR/gemini-reviewer-policy.toml" || RUN_EXIT=$?

if [[ "$RUN_EXIT" -ne 0 ]]; then
    fail_closed "$RUN_EXIT" "Gemini exited with code $RUN_EXIT"
fi

if jq -e '.error? // empty' "$RAW_OUTPUT" >/dev/null 2>&1; then
    GEMINI_ERROR=$(jq -r '.error' "$RAW_OUTPUT" 2>/dev/null | head -c 500 | tr '\n\r' '  ')
    fail_closed 1 "Gemini returned error: $GEMINI_ERROR"
fi

RESPONSE_TMP=$(mktemp "${OUTPUT}.tmp.XXXXXX")
if ! jq -er '.response // empty' "$RAW_OUTPUT" > "$RESPONSE_TMP"; then
    rm -f "$RESPONSE_TMP"
    fail_closed 1 "Gemini JSON missing non-empty .response"
fi

if [[ ! -s "$RESPONSE_TMP" ]] || [[ -z "$(tr -d '[:space:]' < "$RESPONSE_TMP")" ]]; then
    rm -f "$RESPONSE_TMP"
    fail_closed 1 "Gemini JSON .response was empty (or whitespace-only)"
fi

mv "$RESPONSE_TMP" "$OUTPUT"
GUARD_EXIT=0
run_snapshot_guard || GUARD_EXIT=$?
if [[ "$GUARD_EXIT" -ne 0 ]]; then
    # Clear $OUTPUT to match fail_closed's contract — non-zero $OUTPUT.done
    # MUST imply empty $OUTPUT, so consumers that read $OUTPUT without
    # checking .done first do not see a "successful-looking" review body
    # for a run that actually failed and triggered a revert.
    write_empty_output
    {
        [[ -n "$SNAPSHOT_GUARD_MESSAGE" ]] && printf '%s\n' "$SNAPSHOT_GUARD_MESSAGE"
        [[ -n "$SNAPSHOT_GUARD_NOTICE" ]] && printf '%s\n' "$SNAPSHOT_GUARD_NOTICE"
        [[ -f "$RAW_OUTPUT.diag" ]] && cat "$RAW_OUTPUT.diag"
    } >> "${OUTPUT}.diag"
    _write_dirty_tree_sidecar
    write_meta
    if [[ "$GUARD_EXIT" -eq 99 ]]; then
        write_done 99
        exit 99
    fi
    write_done 1
    exit 1
fi
if [[ -n "$SNAPSHOT_GUARD_NOTICE" ]]; then
    printf '%s\n' "$SNAPSHOT_GUARD_NOTICE" >> "${OUTPUT}.diag"
fi
_write_dirty_tree_sidecar
write_meta
write_done 0
exit 0
