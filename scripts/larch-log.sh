#!/usr/bin/env bash
# larch-log.sh — router for committed larch-logs artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# Resolve repo root from caller's CWD so git operations target the consumer
# repo, not the plugin install cache. Remains empty outside a git worktree.
REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || true

# shellcheck source=scripts/lib-larch-log.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-larch-log.sh"
# shellcheck source=scripts/lib-redact.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-redact.sh"

usage() {
    cat <<'USAGE' >&2
Usage:
  larch-log.sh init --log-root D --skill S --run-id R [--parent-skill P] [--issue N]
  larch-log.sh write --log-root D --skill S --run-id R --batch B --input-file F
  larch-log.sh write-round --log-root D --skill S --run-id R --round N --source-dir DIR
  larch-log.sh append --log-root D --skill S --run-id R --batch B --record-file F
  larch-log.sh exists --log-root D --skill S --run-id R --batch B
  larch-log.sh commit --log-root D --skill S --run-id R
  larch-log.sh manifest --log-root D --skill S --run-id R --field K=V...
USAGE
}

json_escape() {
    if command -v jq >/dev/null 2>&1; then
        jq -Rn --arg v "$1" '$v'
    else
        printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    fi
}

now_utc() {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
}

plugin_version() {
    "$SCRIPT_DIR/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}'
}

require_common() {
    [ -n "${SKILL:-}" ] || { usage; larch_log_fail 1 "--skill is required"; }
    [ -n "${RUN_ID:-}" ] || { usage; larch_log_fail 1 "--run-id is required"; }
    larch_log_validate_slug skill "$SKILL"
    larch_log_validate_slug run-id "$RUN_ID"
}

require_log_root() {
    if [ -n "${LOG_ROOT:-}" ]; then
        [[ "$LOG_ROOT" == /* ]] || larch_log_fail 1 "--log-root must be an absolute path: $LOG_ROOT"
        export LARCH_LOG_ROOT="$LOG_ROOT"
        return 0
    fi
    if [ -n "${LARCH_LOG_ROOT:-}" ]; then
        [[ "$LARCH_LOG_ROOT" == /* ]] || larch_log_fail 1 "LARCH_LOG_ROOT must be an absolute path: $LARCH_LOG_ROOT"
        return 0
    fi
    larch_log_fail 1 "--log-root is required (or export LARCH_LOG_ROOT for test isolation)"
}

round_artifact_included() {
    local name="$1"
    case "$name" in
        *.dirty-tree|*.untracked-baseline|*.done|*.diag|*.sidecar|*-output.txt.prompt|*-output-*.txt.prompt|coder-output.log|coder-codex.log)
            return 1
            ;;
        # Excluded raw per-specialist reviewer outputs and their sidecars
        # (findings.md is the canonical aggregate). Phased outputs
        # (cursor-specialist-*-output-phase*.txt) and their sidecars remain
        # included via the broad *-output-*.txt patterns below.
        cursor-specialist-*-output.txt|cursor-specialist-*-output.txt.meta|cursor-specialist-*-output.txt.json|cursor-specialist-*-output.txt.cap-hit)
            return 1
            ;;
        # Excluded vote prompts (the ballot is byte-identical across voters
        # and is already captured by voting-tally.md plus the per-voter outputs).
        *-vote-prompt.txt)
            return 1
            ;;
        # Excluded zero-byte placeholders (observed empty in every committed run).
        skipped-findings.security.md|submodule-paths.txt|submodule-scrub.log|submodule-revert.log|coder-commit.log)
            return 1
            ;;
        findings.md|accepted-findings.md|rejected-findings.md|rejected-findings-full.md|oos.md|oos-accepted-review.md|review-round-summary.md|review-summary.json|voting-tally.md|review-tally.env|review-dirty-tree-summary.env|collector-results.env|collect-agent-results.log|panel-manifest.ndjson|code-voter-slots.ndjson|coder.env|coder-prompt.md|coder-tool.txt|coder-codex.wrapper.log|coder-cursor.log|coder-cursor.wrapper.log)
            return 0
            ;;
        dirty-checkpoint-*.env|voter*-diag.txt|*-parse-rate-diag.txt|skipped-findings*.md|*-vote-output-first-pass.txt|*-output.txt|*-output-*.txt|*-output.txt.meta|*-output-*.txt.meta|*-output.txt.json|*-output-*.txt.json|*-output.txt.cap-hit|*-output-*.txt.cap-hit|scout-round*-status.env|scout-round*-manifest.json|scout-round*-manifest.json.raw|reviewer-dyn-*.md|dyn-*-prompt.md)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

stage_round_artifact() {
    local input="$1"
    local output="$2"
    local name trim_tmp
    name="$(basename "$input")"
    trim_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-trim.XXXXXX")" || larch_log_fail 2 "cannot create round trim temp"
    (
        trap 'rm -f "$trim_tmp"' EXIT
        case "$name" in
            *.meta)
                larch_redact_strip_meta_cmd_json "$input" "$trim_tmp" || larch_log_fail 2 "cannot trim meta sidecar: $input"
                ;;
            *-output.txt.json|*-output-*.txt.json)
                larch_redact_strip_json_result "$input" "$trim_tmp" || larch_log_fail 2 "cannot trim json sidecar: $input"
                ;;
            *)
                cp "$input" "$trim_tmp" || larch_log_fail 2 "cannot stage round artifact: $input"
                ;;
        esac
        larch_log_redact_file "$trim_tmp" "$output"
    )
}

current_branch_is_default() {
    local current_branch default_branch
    current_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    [ -n "$current_branch" ] || return 1
    [ "$current_branch" != "HEAD" ] || return 1
    [ "$current_branch" != "main" ] || return 0
    [ "$current_branch" != "master" ] || return 0

    default_branch="$(
        git -C "$REPO_ROOT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
            | sed 's|^refs/remotes/origin/||'
    )" || default_branch=""
    [ -n "$default_branch" ] || return 1
    [ "$current_branch" = "$default_branch" ]
}

write_manifest_file() {
    local path="$1"
    local parent_skill="$2"
    local issue="$3"
    local status="$4"
    local ts version parent_json issue_json model_json effort_json operator_repo_root operator_cwd_json operator_repo_root_json tmp
    ts="$(now_utc)"
    version="$(plugin_version)"
    [ -n "$version" ] || version="unknown"
    operator_repo_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || true
    operator_cwd_json='"<OPERATOR_CWD>"'
    if [ -n "$operator_repo_root" ]; then
        operator_repo_root_json='"<REPO_ROOT>"'
    else
        operator_repo_root_json="null"
    fi
    if [ -n "$parent_skill" ]; then
        parent_json="$(json_escape "$parent_skill")"
    else
        parent_json="null"
    fi
    if [ -n "$issue" ]; then
        issue_json="$issue"
    else
        issue_json="null"
    fi
    model_json="$(json_escape "${CLAUDE_CODE_MODEL:-${CLAUDE_MODEL:-unknown}}")"
    effort_json="$(json_escape "${CLAUDE_CODE_EFFORT_LEVEL:-${CLAUDE_EFFORT:-unknown}}")"
    mkdir -p "$(dirname "$path")" || larch_log_fail 2 "cannot create manifest directory"
    tmp="$(mktemp "$(dirname "$path")/.tmp.manifest.XXXXXX")" || larch_log_fail 2 "cannot create manifest temp"
    cat > "$tmp" <<EOF
{
  "schema_version": 2,
  "skill": "$SKILL",
  "run_id": "$RUN_ID",
  "operator_cwd": $operator_cwd_json,
  "operator_repo_root": $operator_repo_root_json,
  "parent_skill": $parent_json,
  "issue_number": $issue_json,
  "pr_number": null,
  "status": "$status",
  "larch_version": "$version",
  "model_roster": {"main": $model_json},
  "effort": $effort_json,
  "started_at": "$ts",
  "updated_at": "$ts",
  "attempt": 1,
  "superseded_by": null,
  "stalled_at_step": null,
  "flags": {}
}
EOF
    mv -f "$tmp" "$path" || {
        rm -f "$tmp"
        larch_log_fail 2 "cannot publish manifest"
    }
}

cmd="${1:-}"
[ -n "$cmd" ] || { usage; exit 1; }
shift

case "$cmd" in
    init)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; PARENT_SKILL=""; ISSUE=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --parent-skill) PARENT_SKILL="${2:?--parent-skill requires a value}"; shift 2 ;;
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for init: $1" ;;
            esac
        done
        require_log_root
        require_common
        [ -z "$PARENT_SKILL" ] || larch_log_validate_slug parent-skill "$PARENT_SKILL"
        case "$ISSUE" in ""|*[!0-9]*) [ -z "$ISSUE" ] || larch_log_fail 1 "invalid issue: $ISSUE" ;; esac
        path="$(larch_log_run_dir "$SKILL" "$RUN_ID")/manifest.json"
        if [ -f "$path" ]; then
            larch_log_emit_success "$path" false true
            exit 0
        fi
        write_manifest_file "$path" "$PARENT_SKILL" "$ISSUE" "in-progress"
        larch_log_emit_success "$path" true false
        ;;

    write)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; BATCH=""; INPUT_FILE=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
                --input-file) INPUT_FILE="${2:?--input-file requires a value}"; shift 2 ;;
                --commit) shift ;;
                *) usage; larch_log_fail 1 "unknown option for write: $1" ;;
            esac
        done
        require_log_root
        require_common
        [ -n "$BATCH" ] || larch_log_fail 1 "--batch is required"
        [ -f "$INPUT_FILE" ] || larch_log_fail 1 "input file not found: $INPUT_FILE"
        mode="$(larch_log_batch_mode "$BATCH")" || larch_log_fail 1 "unknown batch: $BATCH"
        [ "$mode" = "replace" ] || larch_log_fail 1 "batch $BATCH is append-only; use append"
        path="$(larch_log_batch_path "$SKILL" "$RUN_ID" "$BATCH")"
        tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-write.XXXXXX")" || larch_log_fail 2 "cannot create temp payload"
        trap 'rm -f "${tmp:-}"' EXIT
        larch_log_redact_file "$INPUT_FILE" "$tmp"
        larch_log_validate_batch_payload "$BATCH" "$tmp"
        if [ -f "$path" ] && cmp -s "$tmp" "$path"; then
            larch_log_emit_success "$path" false true
            exit 0
        fi
        larch_log_atomic_replace "$tmp" "$path"
        larch_log_emit_success "$path" true false
        ;;

    write-round)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; ROUND_NUM=""; SOURCE_DIR=""
        round_dir=""; written=false; found=false; round_tmp=""; src=""; name=""; dest=""; dynamic_dir=""; seen_round_artifacts=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --round) ROUND_NUM="${2:?--round requires a value}"; shift 2 ;;
                --source-dir) SOURCE_DIR="${2:?--source-dir requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for write-round: $1" ;;
            esac
        done
        require_log_root
        require_common
        case "$ROUND_NUM" in ''|*[!0-9]*) larch_log_fail 1 "--round must be a positive integer" ;; esac
        [ "$ROUND_NUM" -gt 0 ] || larch_log_fail 1 "--round must be a positive integer"
        [ -d "$SOURCE_DIR" ] || larch_log_fail 1 "source directory not found: $SOURCE_DIR"
        [ ! -L "$SOURCE_DIR" ] || larch_log_fail 1 "source directory must not be a symlink: $SOURCE_DIR"
        dynamic_dir="$SOURCE_DIR/dynamic-archetypes"
        [ ! -L "$dynamic_dir" ] || larch_log_fail 2 "dynamic-archetypes must not be a symlink: $dynamic_dir"

        round_dir="$(larch_log_run_dir "$SKILL" "$RUN_ID")/round-$ROUND_NUM"
        mkdir -p "$round_dir" || larch_log_fail 2 "cannot create round log directory: $round_dir"
        written=false
        found=false
        round_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-round.XXXXXX")" || larch_log_fail 2 "cannot create round artifact temp"
        seen_round_artifacts="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-seen.XXXXXX")" || larch_log_fail 2 "cannot create round basename temp"
        trap 'rm -f "${round_tmp:-}" "${seen_round_artifacts:-}"' EXIT
        while IFS= read -r src || [ -n "$src" ]; do
            name="$(basename "$src")"
            round_artifact_included "$name" || continue
            [ -f "$src" ] || continue
            [ ! -L "$src" ] || continue
            prev_src="$(awk -F '\t' -v target="$name" '$1 == target { print $2; exit }' "$seen_round_artifacts")"
            if [ -n "$prev_src" ]; then
                larch_log_fail 2 "duplicate round artifact basename '$name' from $src and $prev_src"
            fi
            printf '%s\t%s\n' "$name" "$src" >> "$seen_round_artifacts"
            found=true
            : > "$round_tmp"
            stage_round_artifact "$src" "$round_tmp"
            dest="$round_dir/$name"
            if [ -f "$dest" ] && cmp -s "$round_tmp" "$dest"; then
                continue
            fi
            larch_log_atomic_replace "$round_tmp" "$dest"
            written=true
        done < <({
            find "$SOURCE_DIR" -maxdepth 1 -type f -print
            if [ -d "$dynamic_dir" ]; then
                find "$dynamic_dir" -maxdepth 1 -type f -print
            fi
        } | LC_ALL=C sort)
        if [ "$found" = false ]; then
            larch_log_emit_success "$round_dir" false true
        else
            if [ "$written" = true ]; then
                larch_log_emit_success "$round_dir" true false
            else
                larch_log_emit_success "$round_dir" false true
            fi
        fi
        ;;

    append)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; BATCH=""; RECORD_FILE=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
                --record-file) RECORD_FILE="${2:?--record-file requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for append: $1" ;;
            esac
        done
        require_log_root
        require_common
        [ -n "$BATCH" ] || larch_log_fail 1 "--batch is required"
        [ -f "$RECORD_FILE" ] || larch_log_fail 1 "record file not found: $RECORD_FILE"
        mode="$(larch_log_batch_mode "$BATCH")" || larch_log_fail 1 "unknown batch: $BATCH"
        [ "$mode" = "append" ] || larch_log_fail 1 "batch $BATCH is replace-only; use write"
        path="$(larch_log_batch_path "$SKILL" "$RUN_ID" "$BATCH")"
        dir="$(dirname "$path")"
        mkdir -p "$dir" || larch_log_fail 2 "cannot create log directory: $dir"
        redacted="$(mktemp "${TMPDIR:-/tmp}/larch-log-record.XXXXXX")" || larch_log_fail 2 "cannot create record temp"
        staged="$(mktemp "$dir/.tmp.$(basename "$path").XXXXXX")" || larch_log_fail 2 "cannot create append temp"
        trap 'rm -f "${redacted:-}" "${staged:-}"' EXIT
        larch_log_redact_file "$RECORD_FILE" "$redacted"
        larch_log_validate_batch_payload "$BATCH" "$redacted"
        [ -f "$path" ] && cat "$path" > "$staged"
        cat "$redacted" >> "$staged"
        tail_char="$(tail -c 1 "$staged" 2>/dev/null || true)"
        [ "$tail_char" = "" ] || printf '\n' >> "$staged"
        mv -f "$staged" "$path" || larch_log_fail 2 "cannot append log record"
        larch_log_emit_success "$path" true false
        ;;

    exists)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; BATCH=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for exists: $1" ;;
            esac
        done
        require_log_root
        require_common
        path="$(larch_log_batch_path "$SKILL" "$RUN_ID" "$BATCH")"
        if [ -f "$path" ]; then
            larch_log_emit_success "$path" false true
        else
            larch_log_emit_success "$path" false false
        fi
        ;;

    manifest)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; FIELDS=()
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --field) FIELDS+=("${2:?--field requires a value}"); shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for manifest: $1" ;;
            esac
        done
        require_log_root
        require_common
        path="$(larch_log_run_dir "$SKILL" "$RUN_ID")/manifest.json"
        [ -f "$path" ] || larch_log_fail 1 "manifest not found: $path"
        command -v jq >/dev/null 2>&1 || larch_log_fail 2 "jq is required for manifest updates"
        # shellcheck disable=SC2016 # jq variables are expanded by jq, not the shell.
        filter='.updated_at = $updated'
        args=(--arg updated "$(now_utc)")
        for field in "${FIELDS[@]}"; do
            case "$field" in
                *=*) key="${field%%=*}"; value="${field#*=}" ;;
                *) larch_log_fail 1 "invalid --field: $field" ;;
            esac
            case "$key" in
                schema_version|skill|run_id|started_at|operator_cwd|operator_repo_root) larch_log_fail 1 "manifest field is immutable: $key" ;;
                *[!A-Za-z0-9_]*|"") larch_log_fail 1 "invalid manifest field: $key" ;;
            esac
            var="v${#args[@]}"
            # Use --argjson for JSON-native scalar types so numeric fields
            # like pr_number are stored as numbers rather than strings.
            if printf '%s' "$value" | grep -Eq '^(null|true|false|-?[0-9]+)$'; then
                args+=(--argjson "$var" "$value")
            else
                args+=(--arg "$var" "$value")
            fi
            filter="$filter | .$key = \$$var"
        done
        tmp="$(mktemp "$(dirname "$path")/.tmp.manifest.XXXXXX")" || larch_log_fail 2 "cannot create manifest temp"
        jq "${args[@]}" "$filter" "$path" > "$tmp" || {
            rm -f "$tmp"
            larch_log_fail 2 "manifest update failed"
        }
        if cmp -s "$tmp" "$path"; then
            rm -f "$tmp"
            larch_log_emit_success "$path" false true
        else
            mv -f "$tmp" "$path" || larch_log_fail 2 "cannot publish manifest"
            larch_log_emit_success "$path" true false
        fi
        ;;

    commit)
        LOG_ROOT=""; SKILL=""; RUN_ID=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for commit: $1" ;;
            esac
        done
        if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -e "$IMPLEMENT_TMPDIR/post-merge-sentinel" ]; then
            printf 'larch-log.sh: refusing commit after post-merge sentinel exists: %s\n' "$IMPLEMENT_TMPDIR/post-merge-sentinel" >&2
            exit 1
        fi
        [ -n "$REPO_ROOT" ] || larch_log_fail 1 "commit requires a git worktree (PWD is not inside a git repo)"
        if current_branch_is_default; then
            printf 'larch-log.sh: refusing commit on default branch/main after post-merge cleanup guard\n' >&2
            exit 1
        fi
        require_log_root
        require_common
        src_path="$(larch_log_run_dir "$SKILL" "$RUN_ID")"
        repo_path="$(larch_log_repo_run_dir "$SKILL" "$RUN_ID")"
        [ -d "$src_path" ] || larch_log_fail 1 "log directory not found: $src_path"
        if [ "$src_path" != "$repo_path" ]; then
            mkdir -p "$repo_path" || larch_log_fail 3 "cannot create repo log directory"
            cp -rp "$src_path/." "$repo_path/" || larch_log_fail 3 "cannot copy logs from temp to repo"
        fi
        # Scope all git operations to exactly this run's directory, not the broader
        # skill parent. Building the pathspec explicitly hardens add/status/diff
        # against prefix math mistakes and untracked-file omissions.
        rel="larch-logs/$SKILL/$RUN_ID"
        # Check status first: git diff alone misses untracked files.
        if ! git -C "$REPO_ROOT" status --porcelain -- "$rel" | grep -q .; then
            larch_log_emit_success "$repo_path" false true
            exit 0
        fi
        git -C "$REPO_ROOT" add -- "$rel" || larch_log_fail 3 "git add failed"
        if git -C "$REPO_ROOT" diff --cached --quiet -- "$rel"; then
            larch_log_emit_success "$repo_path" false true
            exit 0
        fi
        git -C "$REPO_ROOT" commit -m "chore(larch-logs): flush $SKILL run $RUN_ID" -- "$rel" >/dev/null || {
            git -C "$REPO_ROOT" reset HEAD -- "$rel" 2>/dev/null || true
            larch_log_fail 3 "git commit failed"
        }
        commit_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
        larch_log_emit_success "$repo_path" true false "$commit_sha"
        ;;

    *)
        usage
        larch_log_fail 1 "unknown command: $cmd"
        ;;
esac
