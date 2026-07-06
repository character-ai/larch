#!/usr/bin/env bash
# hook-anti-read-poll.sh — PostToolUse hook: warn on repeated identical Read calls
# and on per-turn polling of background task .output files (Read or Bash).
#
# Generic Read: third consecutive read of the same path+offset within 30s.
# Task output: second read of the same tasks/<id>.output token within 600s
# (Read or Bash; offset ignored for task-output paths).
# set -e intentionally omitted: hooks must never block tool use.

set -uo pipefail

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null) || exit 0
case "$tool_name" in
    Read|Bash) ;;
    *) exit 0 ;;
esac

_bash_sanitized_command=""
if [ "$tool_name" = "Bash" ]; then
    _bash_command_body=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
    [ -n "$_bash_command_body" ] || exit 0
    _bash_sanitized_command=${_bash_command_body//$'\t'/ }
    case "$(printf '%s' "$_bash_sanitized_command" | tr '[:upper:]' '[:lower:]')" in
        *tasks/*) ;;
        *) exit 0 ;;
    esac
    case "$(printf '%s' "$_bash_sanitized_command" | tr '[:upper:]' '[:lower:]')" in
        *.output*) ;;
        *) exit 0 ;;
    esac
fi

cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || cwd=""
cwd_hash=$(printf '%s' "${cwd:-/}" | cksum 2>/dev/null | awk '{print $1}') || cwd_hash="0"

session_id=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || session_id=""
if [ -z "$session_id" ]; then
    session_id=$(printf '%s' "$INPUT" | jq -r '.conversation_id // ""' 2>/dev/null) || session_id=""
fi
if [ -n "$session_id" ]; then
    session_key="$session_id"
elif [ -n "${HOOK_ANTI_READ_POLL_DISCRIMINATOR:-}" ]; then
    session_key="nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}"
else
    session_key="nosession"
fi
session_hash=$(printf '%s' "$session_key" | cksum 2>/dev/null | awk '{print $1}') || session_hash="0"

if [ -n "${HOOK_ANTI_READ_POLL_NOW:-}" ]; then
    now=$HOOK_ANTI_READ_POLL_NOW
    case "$now" in ''|*[!0-9]*) exit 0 ;; esac
else
    now=$(date +%s 2>/dev/null) || exit 0
fi

state_dir="${TMPDIR:-/tmp}/larch-read-poll"
mkdir -p "$state_dir" 2>/dev/null || exit 0
chmod 700 "$state_dir" 2>/dev/null || true

emit_reminder() {
    local msg="$1"
    jq -cn --arg ctx "$msg" \
        '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}' \
        2>/dev/null || true
}

canonical_dir() {
    [ -n "$1" ] || return 1
    [ -d "$1" ] || return 1
    (cd "$1" 2>/dev/null && pwd -P)
}

marker_candidates() {
    if [ -n "${LARCH_BG_POLL_GUARD_MARKER:-}" ]; then
        printf '%s\n' "$LARCH_BG_POLL_GUARD_MARKER"
        return 0
    fi
    if [ -n "${HOME:-}" ] && [ -d "$HOME/.cache/larch/sessions" ]; then
        find "$HOME/.cache/larch/sessions" -maxdepth 2 -name .bg-wait-active -type f 2>/dev/null || true
    fi
    if [ -d "${TMPDIR:-/tmp}" ]; then
        _lmc_dirs=()
        for _lmc_d in "${TMPDIR:-/tmp}"/larch-* "${TMPDIR:-/tmp}"/claude-design-* "${TMPDIR:-/tmp}"/claude-implement-*; do
            [ -d "$_lmc_d" ] || continue
            _lmc_dirs+=("$_lmc_d")
        done
        if [ "${#_lmc_dirs[@]}" -gt 0 ]; then
            find "${_lmc_dirs[@]}" -maxdepth 2 -name .bg-wait-active -type f 2>/dev/null || true
        fi
    fi
}

marker_value() {
    local marker="$1" key="$2"
    awk -F= -v k="$key" '$1 == k { sub(/^[^=]*=/, ""); print; found=1; exit } END { exit found ? 0 : 1 }' "$marker" 2>/dev/null
}

clone_paths_same() {
    local marker_canon="$1" current_canon="$2"
    [ "$marker_canon" = "$current_canon" ] && return 0
    case "$current_canon" in
        "$marker_canon"/*) return 0 ;;
    esac
    case "$marker_canon" in
        "$current_canon"/*) return 0 ;;
    esac
    return 1
}

marker_foreign_clone() {
    local dir="$1" current_canon="$2" marker keepalive marker_clone marker_canon
    [ -n "$current_canon" ] || return 1
    marker="$dir/.bg-wait-active"
    if [ -f "$marker" ] && [ ! -L "$marker" ]; then
        marker_clone=$(marker_value "$marker" CLONE_PATH 2>/dev/null || true)
        if [ -n "$marker_clone" ]; then
            marker_canon=$(canonical_dir "$marker_clone" 2>/dev/null || true)
            if [ -n "$marker_canon" ]; then
                clone_paths_same "$marker_canon" "$current_canon" && return 1
                return 0
            fi
        fi
    fi
    keepalive="$dir/.larch-keepalive"
    [ -f "$keepalive" ] && [ ! -L "$keepalive" ] || return 1
    marker_clone=$(marker_value "$keepalive" CLONE_PATH) || return 1
    [ -n "$marker_clone" ] || return 1
    marker_canon=$(canonical_dir "$marker_clone" 2>/dev/null) || return 1
    clone_paths_same "$marker_canon" "$current_canon" && return 1
    return 0
}

design_step_completed() {
    local dir="$1" step="$2" sentinel sidecar
    case "$step" in
        design-step3-review)
            sentinel="$dir/.completed/step-3-terminal"
            sidecar="$dir/.step3-terminal-persisted-this-run"
            [ -f "$sentinel" ] && [ ! -L "$sentinel" ] && [ -f "$sidecar" ] && [ ! -L "$sidecar" ] && [ -r "$sidecar" ]
            ;;
        design-step4-tail)
            sentinel="$dir/.completed/step-4"
            [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
            ;;
        design-step5c)
            sentinel="$dir/.completed/step-5c-terminal"
            [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
            ;;
        design-step-final-summary)
            sentinel="$dir/.completed/step-final-summary"
            [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
            ;;
        *) return 1 ;;
    esac
}

live_same_clone_design_marker_active() {
    local cwd_canon="" marker dir step pid start timeout grace limit age
    [ -n "$cwd" ] && cwd_canon=$(canonical_dir "$cwd" 2>/dev/null || true)
    while IFS= read -r marker || [ -n "$marker" ]; do
        [ -n "$marker" ] || continue
        [ -f "$marker" ] && [ ! -L "$marker" ] || continue
        dir=$(dirname "$marker") || continue
        dir=$(canonical_dir "$dir" 2>/dev/null) || continue
        step=$(marker_value "$marker" STEP 2>/dev/null) || step=""
        case "$step" in
            design-step*) ;;
            *) continue ;;
        esac
        design_step_completed "$dir" "$step" && continue
        marker_foreign_clone "$dir" "$cwd_canon" && continue
        pid=$(marker_value "$marker" PID 2>/dev/null) || continue
        start=$(marker_value "$marker" START_EPOCH 2>/dev/null) || continue
        timeout=$(marker_value "$marker" TIMEOUT_S 2>/dev/null) || continue
        case "$pid" in ''|*[!0-9]*) continue ;; esac
        case "$start" in ''|*[!0-9]*) continue ;; esac
        case "$timeout" in ''|*[!0-9]*) continue ;; esac
        kill -0 "$pid" 2>/dev/null || continue
        grace=60
        limit=$((timeout + grace))
        age=$((now - start))
        [ "$age" -ge 0 ] || continue
        [ "$age" -le "$limit" ] || continue
        return 0
    done <<EOF_MARKERS
$(marker_candidates)
EOF_MARKERS
    return 1
}

# Read file_path: end-anchored tasks/<id>.output
is_read_task_output_path() {
    printf '%s' "$1" | grep -Eq '(^|/)tasks/[A-Za-z0-9._-]+\.output$'
}

bash_strip_quoted_for_read_verb() {
    local cmd="$1" normalized
    normalized=$(printf '%s' "$cmd" | sed "s/'\\\\''//g")
    printf '%s' "$normalized" | sed -E "s/'[^']*'//g; s/\"([^\"]|\\\\.)*\"//g"
}

bash_has_read_verb() {
    local cmd="$1"
    cmd=$(bash_strip_quoted_for_read_verb "$cmd")
    if printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_])(cat|tail|head|less|more)([^[:alnum:]_]|$)'; then
        return 0
    fi
    if printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_])sed([^[:alnum:]_]|$)[^|;&]*(-[[:space:]]*n([^[:alnum:]_]|$)|--quiet)'; then
        return 0
    fi
    return 1
}

bash_line_is_read_verb_only() {
    local line="$1"
    line=$(printf '%s' "$line" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    [ -n "$line" ] || return 1
    bash_segment_is_echo_only "$line" && return 1
    bash_has_read_verb "$line" || return 1
    extract_task_output_token "$line" >/dev/null && return 1
    return 0
}

bash_expand_simple_var_refs() {
    local line="$1" scan="$1" var val ref
    while [[ "$scan" =~ (^|[[:space:];&|]+)([A-Za-z_][A-Za-z0-9_]*)=(tasks/[A-Za-z0-9._-]+\.output) ]]; do
        var="${BASH_REMATCH[2]}"
        val="${BASH_REMATCH[3]}"
        ref="\$$var"
        line=${line//"$ref"/$val} # lint-renderer-safe: ok ref/val from BASH_REMATCH capture
        line=${line//$ref/$val} # lint-renderer-safe: ok ref/val from BASH_REMATCH capture
        scan="${scan/${BASH_REMATCH[0]}/ }"
    done
    printf '%s' "$line"
}

bash_normalize_cmd() {
    printf '%s' "$1" | sed -e ':a' -e '/\\[[:space:]]*$/N' -e 's/\\[[:space:]]*\n[[:space:]]*/ /' -e 'ta'
}

bash_segment_is_echo_only() {
    local seg="$1"
    seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    case "$seg" in
        echo|echo\ *|printf|printf\ *) return 0 ;;
    esac
    return 1
}

bash_segment_task_output_poll_token() {
    local seg="$1" token
    seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    [ -n "$seg" ] || return 1
    bash_segment_is_echo_only "$seg" && return 1
    bash_has_read_verb "$seg" || return 1
    extract_task_output_token "$seg"
}

# Segment split is a deliberate heuristic: metacharacters inside quoted strings may
# produce extra segments (false negatives) or combine read verbs with paths (false
# positives). Read-verb detection strips quoted spans; task-output tokens are
# extracted only from unquoted command text.
bash_line_is_echo_with_embedded_semicolon() {
    local line="$1"
    case "$line" in
        echo\ \'*\;*\') return 0 ;;
        echo\ \"*\"\;*\") return 0 ;;
    esac
    return 1
}

bash_line_task_output_poll_tokens() {
    local line="$1" seg rest token ch in_s in_d in_b stripped_line
    bash_line_is_echo_with_embedded_semicolon "$line" && return 0
    stripped_line=$(bash_strip_quoted_for_read_verb "$line")
    rest="$line"
    seg=""
    in_s=0
    in_d=0
    in_b=0
    while [ -n "$rest" ]; do
        ch=${rest:0:1}
        if [ "$in_s" -eq 0 ] && [ "$in_d" -eq 0 ] && [ "$in_b" -eq 0 ]; then
            case "$rest" in
                ';'*)
                    token=$(bash_segment_task_output_poll_token "$seg") || true
                    if [ -n "${token:-}" ]; then
                        case "$line" in
                            *"$token"*) printf '%s\n' "$token" ;;
                            *)
                                case "$stripped_line" in
                                    *"$token"*) printf '%s\n' "$token" ;;
                                esac
                                ;;
                        esac
                    fi
                    rest=${rest#;}
                    seg=""
                    continue
                    ;;
                '&&'*)
                    token=$(bash_segment_task_output_poll_token "$seg") || true
                    if [ -n "${token:-}" ]; then
                        case "$line" in
                            *"$token"*) printf '%s\n' "$token" ;;
                            *)
                                case "$stripped_line" in
                                    *"$token"*) printf '%s\n' "$token" ;;
                                esac
                                ;;
                        esac
                    fi
                    rest=${rest#&&}
                    seg=""
                    continue
                    ;;
                '||'*)
                    token=$(bash_segment_task_output_poll_token "$seg") || true
                    if [ -n "${token:-}" ]; then
                        case "$line" in
                            *"$token"*) printf '%s\n' "$token" ;;
                            *)
                                case "$stripped_line" in
                                    *"$token"*) printf '%s\n' "$token" ;;
                                esac
                                ;;
                        esac
                    fi
                    rest=${rest#||}
                    seg=""
                    continue
                    ;;
            esac
        fi
        case "$ch" in
            "'")
                if [ "$in_d" -eq 0 ] && [ "$in_b" -eq 0 ]; then
                    in_s=$((1 - in_s))
                fi
                ;;
            '"')
                if [ "$in_s" -eq 0 ] && [ "$in_b" -eq 0 ]; then
                    in_d=$((1 - in_d))
                fi
                ;;
            '`')
                if [ "$in_s" -eq 0 ] && [ "$in_d" -eq 0 ]; then
                    in_b=$((1 - in_b))
                fi
                ;;
        esac
        seg="${seg}${ch}"
        rest=${rest#?}
    done
    token=$(bash_segment_task_output_poll_token "$seg") || return 0
    case "$line" in
        *"$token"*) printf '%s\n' "$token" ;;
        *)
            case "$stripped_line" in
                *"$token"*) printf '%s\n' "$token" ;;
            esac
            ;;
    esac
}

extract_bash_task_output_poll_tokens() {
    local cmd="$1" normalized line token
    local i merged
    lines=()
    normalized=$(bash_normalize_cmd "$cmd")
    normalized=$(bash_expand_simple_var_refs "$normalized")
    while IFS= read -r line || [ -n "$line" ]; do
        lines+=("$line")
    done < <(printf '%s\n' "$normalized")
    i=0
    while [ "$i" -lt "${#lines[@]}" ]; do
        line="${lines[$i]}"
        if bash_line_is_read_verb_only "$line" && [ $((i + 1)) -lt "${#lines[@]}" ]; then
            merged="$line ${lines[$((i + 1))]}"
            while IFS= read -r token || [ -n "$token" ]; do
                [ -n "$token" ] || continue
                printf '%s\n' "$token"
            done < <(bash_line_task_output_poll_tokens "$merged")
            i=$((i + 2))
            continue
        fi
        while IFS= read -r token || [ -n "$token" ]; do
            [ -n "$token" ] || continue
            printf '%s\n' "$token"
        done < <(bash_line_task_output_poll_tokens "$line")
        i=$((i + 1))
    done
}

# shellcheck disable=SC2329,SC2317  # wrapper invoked indirectly; body reachability follows from SC2329
extract_bash_task_output_poll_token() {
    extract_bash_task_output_poll_tokens "$1" | head -1
}

# Canonical state key: rightmost tasks/<id>.output tail (absolute vs relative ignored).
extract_task_output_token() {
    local text="$1" stripped token
    token=$(printf '%s' "$text" | grep -oE 'tasks/[A-Za-z0-9._-]+\.output' | tail -1)
    if [ -n "$token" ]; then
        printf '%s' "$token"
        return 0
    fi
    stripped=$(bash_strip_quoted_for_read_verb "$text")
    token=$(printf '%s' "$stripped" | grep -oE 'tasks/[A-Za-z0-9._-]+\.output' | tail -1)
    if [ -n "$token" ]; then
        printf '%s' "$token"
        return 0
    fi
    return 1
}

task_id_from_token() {
    local token="$1" id
    id=$(printf '%s' "$token" | sed -n 's|^tasks/\([A-Za-z0-9._-]*\)\.output$|\1|p')
    [ -n "$id" ] || return 1
    printf '%s' "$id"
}

handle_task_output_poll() {
    local token="$1"
    local task_id
    task_id=$(task_id_from_token "$token") || return 0
    local TASK_OUTPUT_THRESHOLD=2
    local TASK_OUTPUT_WINDOW_SECS=600
    local taskout_file="$state_dir/state-taskout-${session_hash}-${cwd_hash}-${task_id}.tsv"

    local count=0 first_ts=0
    if [ -f "$taskout_file" ]; then
        IFS=$'\t' read -r count first_ts < "$taskout_file" 2>/dev/null || true
        case "$count" in ''|*[!0-9]*) count=0 ;; esac
        case "$first_ts" in ''|*[!0-9]*) first_ts=0 ;; esac
    fi

    local age=0
    if [ "$count" -gt 0 ]; then
        age=$(( now - first_ts ))
        if [ "$age" -lt 0 ] || [ "$age" -gt "$TASK_OUTPUT_WINDOW_SECS" ]; then
            count=1
            first_ts=$now
            age=0
        else
            count=$((count + 1))
        fi
    else
        count=1
        first_ts=$now
        age=0
    fi

    _state_tmp=$(mktemp "${state_dir}/taskout-state.XXXXXX" 2>/dev/null) || _state_tmp=""
    if [ -n "$_state_tmp" ]; then
        printf '%s\t%s\n' "$count" "$first_ts" > "$_state_tmp" 2>/dev/null || true
        mv -f "$_state_tmp" "$taskout_file" 2>/dev/null || printf '%s\t%s\n' "$count" "$first_ts" > "$taskout_file" 2>/dev/null || true
    else
        printf '%s\t%s\n' "$count" "$first_ts" > "$taskout_file" 2>/dev/null || true
    fi
    chmod 600 "$taskout_file" 2>/dev/null || true

    if [ "$age" -eq 0 ] && [ "$count" -gt 1 ]; then
        age=$(( now - first_ts ))
    fi
    if [ "$count" -eq "$TASK_OUTPUT_THRESHOLD" ] && [ "$age" -le "$TASK_OUTPUT_WINDOW_SECS" ]; then
        emit_reminder "[system-reminder] Task-output poll detected: the same background task output has been read $count times within ${age}s. If waiting for a background job, use the Bash <task-notification> for one-shot completion instead of re-reading the task output file each turn."
    fi
}

handle_generic_read_poll() {
    local sanitized_path="$1"
    local offset="$2"
    local POLL_THRESHOLD=3
    local WINDOW_SECS=30
    local state_file="$state_dir/state-${session_hash}-${cwd_hash}.tsv"

    local last_path="" last_offset="0" count=0 first_ts=0
    if [ -f "$state_file" ]; then
        IFS=$'\t' read -r last_path last_offset count first_ts < "$state_file" 2>/dev/null || true
        case "$count" in ''|*[!0-9]*) count=0 ;; esac
        case "$first_ts" in ''|*[!0-9]*) first_ts=0 ;; esac
    fi

    local age=0
    if [ "$sanitized_path" = "$last_path" ] && [ "$offset" = "$last_offset" ]; then
        age=$(( now - first_ts ))
        if [ "$age" -lt 0 ] || [ "$age" -gt "$WINDOW_SECS" ]; then
            count=1
            first_ts=$now
        else
            count=$((count + 1))
        fi
    else
        count=1
        first_ts=$now
    fi

    _state_tmp=$(mktemp "${state_dir}/read-poll-state.XXXXXX" 2>/dev/null) || _state_tmp=""
    if [ -n "$_state_tmp" ]; then
        printf '%s\t%s\t%s\t%s\n' "$sanitized_path" "$offset" "$count" "$first_ts" > "$_state_tmp" 2>/dev/null || true
        mv -f "$_state_tmp" "$state_file" 2>/dev/null || printf '%s\t%s\t%s\t%s\n' "$sanitized_path" "$offset" "$count" "$first_ts" > "$state_file" 2>/dev/null || true
    else
        printf '%s\t%s\t%s\t%s\n' "$sanitized_path" "$offset" "$count" "$first_ts" > "$state_file" 2>/dev/null || true
    fi
    chmod 600 "$state_file" 2>/dev/null || true

    age=$(( now - first_ts ))
    if [ "$count" -eq "$POLL_THRESHOLD" ] && [ "$age" -le "$WINDOW_SECS" ]; then
        emit_reminder "[system-reminder] Read-poll detected: the same path+offset has been read $count times consecutively within ${age}s. If waiting for a file to appear, use the Bash background-job completion notification instead of polling with repeated Read calls."
    fi
}

case "$tool_name" in
    Read)
        file_path=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
        [ -n "$file_path" ] || exit 0
        sanitized_path=${file_path//$'\t'/ }
        sanitized_path=${sanitized_path//$'\n'/ }

        if is_read_task_output_path "$sanitized_path"; then
            token=$(extract_task_output_token "$sanitized_path") || exit 0
            live_same_clone_design_marker_active && exit 0
            handle_task_output_poll "$token"
            exit 0
        fi

        offset=$(printf '%s' "$INPUT" | jq -r '.tool_input.offset // 0' 2>/dev/null) || offset=0
        case "$offset" in ''|*[!0-9]*) offset=0 ;; esac
        handle_generic_read_poll "$sanitized_path" "$offset"
        ;;
    Bash)
        live_same_clone_design_marker_active && exit 0
        found=false
        while IFS= read -r token || [ -n "$token" ]; do
            [ -n "$token" ] || continue
            found=true
            handle_task_output_poll "$token"
        done < <(extract_bash_task_output_poll_tokens "$_bash_sanitized_command")
        [ "$found" = true ] || exit 0
        ;;
esac

exit 0
