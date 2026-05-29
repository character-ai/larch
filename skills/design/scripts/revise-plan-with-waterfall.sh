#!/usr/bin/env bash
# Revise a /design plan through a Codex -> Cursor -> Claude waterfall.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$REPO_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$REPO_ROOT/scripts/lib-design-tmpdir.sh"
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: revise-plan-with-waterfall.sh --design-tmpdir DIR --plan-file FILE --findings-file FILE --feature-file FILE --round-num N --codex-present true|false --cursor-present true|false [--timeout SECS] [--patch-format unified-diff|file-replacement]
USAGE
}

DESIGN_TMPDIR=""
PLAN_FILE=""
FINDINGS_FILE=""
FEATURE_FILE=""
ROUND_NUM=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
TIMEOUT="1800"
PATCH_FORMAT="unified-diff"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?--codex-present requires a value}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?--cursor-present requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --patch-format) PATCH_FORMAT="${2:?--patch-format requires a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "revise-plan-with-waterfall.sh: unknown argument: $1"; usage; exit 2 ;;
    esac
done

die_usage() {
    larch_err "revise-plan-with-waterfall.sh: $1"
    usage
    exit 2
}

[[ -n "$DESIGN_TMPDIR" ]] || die_usage "--design-tmpdir is required"
[[ -n "$PLAN_FILE" ]] || die_usage "--plan-file is required"
[[ -n "$FINDINGS_FILE" ]] || die_usage "--findings-file is required"
[[ -n "$FEATURE_FILE" ]] || die_usage "--feature-file is required"
[[ -n "$ROUND_NUM" ]] || die_usage "--round-num is required"
[[ -n "$CODEX_PRESENT" ]] || die_usage "--codex-present is required"
[[ -n "$CURSOR_PRESENT" ]] || die_usage "--cursor-present is required"
[[ -d "$DESIGN_TMPDIR" ]] || { larch_err "revise-plan-with-waterfall.sh: --design-tmpdir must name a directory"; exit 2; }
[[ -r "$PLAN_FILE" ]] || { larch_err "revise-plan-with-waterfall.sh: --plan-file is missing or unreadable: $PLAN_FILE"; exit 2; }
[[ -r "$FINDINGS_FILE" ]] || { larch_err "revise-plan-with-waterfall.sh: --findings-file is missing or unreadable: $FINDINGS_FILE"; exit 2; }
[[ -r "$FEATURE_FILE" ]] || { larch_err "revise-plan-with-waterfall.sh: --feature-file is missing or unreadable: $FEATURE_FILE"; exit 2; }
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "revise-plan-with-waterfall.sh: --round-num must be a non-negative integer"; exit 2 ;; esac
case "$TIMEOUT" in ''|*[!0-9]*|0) larch_err "revise-plan-with-waterfall.sh: --timeout must be a positive integer"; exit 2 ;; esac
[[ "$CODEX_PRESENT" == "true" || "$CODEX_PRESENT" == "false" ]] || { larch_err "revise-plan-with-waterfall.sh: --codex-present must be true or false"; exit 2; }
[[ "$CURSOR_PRESENT" == "true" || "$CURSOR_PRESENT" == "false" ]] || { larch_err "revise-plan-with-waterfall.sh: --cursor-present must be true or false"; exit 2; }
[[ "$PATCH_FORMAT" == "unified-diff" || "$PATCH_FORMAT" == "file-replacement" ]] || { larch_err "revise-plan-with-waterfall.sh: --patch-format must be unified-diff or file-replacement"; exit 2; }

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?

canonical_path() {
    local path="$1" dir base target
    dir=$(dirname "$path")
    base=$(basename "$path")
    dir=$(cd "$dir" && pwd -P)
    while [[ -L "$dir/$base" ]]; do
        target=$(readlink "$dir/$base")
        if [[ "$target" = /* ]]; then
            path="$target"
        else
            path="$dir/$target"
        fi
        dir=$(dirname "$path")
        base=$(basename "$path")
        dir=$(cd "$dir" && pwd -P)
    done
    printf '%s/%s\n' "$dir" "$base"
}

CANONICAL_DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
CANONICAL_PLAN_FILE=$(canonical_path "$PLAN_FILE")
EXPECTED_PLAN_FILE="$CANONICAL_DESIGN_TMPDIR/plan.txt"
if [[ "$CANONICAL_PLAN_FILE" != "$EXPECTED_PLAN_FILE" ]]; then
    larch_err "revise-plan-with-waterfall.sh: --plan-file must resolve to DESIGN_TMPDIR/plan.txt"
    larch_err "revise-plan-with-waterfall.sh: got: $CANONICAL_PLAN_FILE"
    larch_err "revise-plan-with-waterfall.sh: expected: $EXPECTED_PLAN_FILE"
    exit 2
fi
PLAN_FILE="$CANONICAL_PLAN_FILE"
DESIGN_TMPDIR="$CANONICAL_DESIGN_TMPDIR"

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
LAUNCH_CODEX_REVIEW="${LARCH_TEST_LAUNCH_CODEX_REVIEW:-$PLUGIN_ROOT/scripts/launch-review.sh}"
LAUNCH_CURSOR_REVIEW="${LARCH_TEST_LAUNCH_CURSOR_REVIEW:-$PLUGIN_ROOT/scripts/launch-review.sh}"
LAUNCH_CLAUDE_REVIEW="${LARCH_TEST_LAUNCH_CLAUDE_REVIEW:-$PLUGIN_ROOT/scripts/launch-claude-review.sh}"
DESIGN_DRIVER="${LARCH_TEST_DESIGN_DRIVER:-$PLUGIN_ROOT/skills/design/scripts/design-driver.sh}"

ROUND_DIR="$DESIGN_TMPDIR/plan-review/round-$ROUND_NUM"
REVISE_DIR="$ROUND_DIR/revise"
PROMPT_PATH="$REVISE_DIR/prompt.txt"
SNAPSHOT="$PLAN_FILE.before-revise"
mkdir -p "$REVISE_DIR"

sha256_file() {
    LC_ALL=C shasum -a 256 "$1" | awk '{print $1}'
}

heading_count() {
    grep -Ec '^###[[:space:]]+(NEW|UPDATED|REWRITTEN)[[:space:]]*:' "$1" || true
}

HASH_BEFORE=$(sha256_file "$PLAN_FILE")
ORIG_FILE_HEADING_COUNT=$(heading_count "$PLAN_FILE")
cp "$PLAN_FILE" "$SNAPSHOT"
OPTIONAL_TRAILER_KEYS_FILE="$SNAPSHOT.optional-trailer-keys"

snapshot_optional_trailer_keys "$PLAN_FILE" "$OPTIONAL_TRAILER_KEYS_FILE"

compose_prompt() {
    {
        printf 'You are revising an /design implementation plan based on accepted reviewer findings.\n\n'
        if [[ "$PATCH_FORMAT" == "unified-diff" ]]; then
            printf "%s\n\n" "Emit ONLY a single unified diff in your final response, with no prose, no fences, no narration. Use the canonical form \`--- a/plan.txt\` / \`+++ b/plan.txt\` (relative paths, no directory prefix beyond \`a/\` / \`b/\`)."
        else
            printf "%s\n\n" "Emit ONLY the complete replacement plan in your final response, beginning with \`## Plan\` and ending with \`diff_lines: <N>\`."
        fi
        printf "%s\n\n" "Hard rules: the revised plan must end with \`diff_lines: <N>\`. When the original plan has \`### NEW:\`, \`### UPDATED:\`, or \`### REWRITTEN:\` headings, preserve at least one such heading."
        if [[ -s "$OPTIONAL_TRAILER_KEYS_FILE" ]]; then
            printf "%s\n\n" "When the original plan has optional size trailers (\`diff_added:\`, \`diff_deleted:\`, \`mechanical_churn:\`) in the final metadata block immediately above \`diff_lines:\`, preserve each with strict trailer grammar or explicitly recompute the estimates — do not collapse to total-churn-only legacy behavior."
        fi
        printf '<plan>\n'
        sed -n '1,$p' "$PLAN_FILE"
        printf '\n</plan>\n\n<findings>\n'
        sed -n '1,$p' "$FINDINGS_FILE"
        printf '\n</findings>\n\n<feature>\n'
        sed -n '1,$p' "$FEATURE_FILE"
        printf '\n</feature>\n'
    } >"$PROMPT_PATH"
}

tier1_status=""
tier2_status=""
tier3_status=""
tier4_status=""
winner=""
winner_is_fallback=false
winner_output=""

tier4_rank() {
    case "$1" in
        not-attempted) printf '0\n' ;;
        skipped-not-present) printf '1\n' ;;
        no-patch) printf '2\n' ;;
        emit-plan-failed) printf '3\n' ;;
        apply-failed) printf '4\n' ;;
        invalid-patch) printf '5\n' ;;
        ok) printf '6\n' ;;
        *) printf '%s\n' '-1' ;;
    esac
}

merge_tier4_status() {
    local new="$1"
    local current_rank new_rank
    if [[ -z "$tier4_status" ]]; then
        tier4_status="$new"
        return
    fi
    if [[ "$tier4_status" == "ok" || "$new" == "ok" ]]; then
        tier4_status="ok"
        return
    fi
    current_rank=$(tier4_rank "$tier4_status")
    new_rank=$(tier4_rank "$new")
    if (( new_rank > current_rank )); then
        tier4_status="$new"
    fi
}

set_tier_status() {
    case "$1" in
        1) tier1_status="$2" ;;
        2) tier2_status="$2" ;;
        3) tier3_status="$2" ;;
        4) merge_tier4_status "$2" ;;
        *) return 1 ;;
    esac
}

get_tier_status() {
    case "$1" in
        1) printf '%s\n' "$tier1_status" ;;
        2) printf '%s\n' "$tier2_status" ;;
        3) printf '%s\n' "$tier3_status" ;;
        4) printf '%s\n' "$tier4_status" ;;
        *) return 1 ;;
    esac
}

restore_plan() {
    cp "$SNAPSHOT" "$PLAN_FILE"
}

restore_plan_or_die() {
    restore_plan || {
        larch_err "revise-plan-with-waterfall.sh: failed to restore $PLAN_FILE from $SNAPSHOT"
        exit 1
    }
}

last_nonblank_line() {
    awk 'NF { line=$0 } END { print line }' "$1"
}

extract_patch() {
    local output="$1" patch="$2"
    if [[ "$PATCH_FORMAT" == "unified-diff" ]]; then
        extract_unified_diff_candidates "$output" "$patch"
    else
        extract_file_replacement_candidate "$output" "$patch"
    fi
}

extract_unified_diff_candidates_from_source() {
    local src="$1" dest_dir="$2" found_file="$3"
    awk -v outdir="$dest_dir" -v found_file="$found_file" '
        function is_old_header(line) {
            return line ~ /^--- a\/[^ \t]+([ \t].*)?$/
        }
        function is_new_header(line) {
            return line ~ /^\+\+\+ b\/[^ \t]+([ \t].*)?$/
        }
        function is_candidate_start(idx) {
            if (lines[idx] ~ /^diff --git /) {
                return 1
            }
            if (idx < line_count && is_old_header(lines[idx]) && is_new_header(lines[idx + 1])) {
                return 1
            }
            return 0
        }
        function is_metadata_line(line) {
            return line ~ /^(diff --git |index |old mode |new mode |deleted file mode |new file mode |similarity index |rename from |rename to |copy from |copy to )/
        }
        function is_hunk_header(line) {
            return line ~ /^@@ /
        }
        function is_hunk_body(line) {
            return line ~ /^( |[-+]|\\ No newline at end of file)/
        }
        function emit_candidate(start,    end, idx, line, file, saw_old, saw_new, saw_content, in_hunk) {
            saw_old = 0
            saw_new = 0
            saw_content = 0
            in_hunk = 0
            end = start
            while (end <= line_count) {
                line = lines[end]
                if (end > start && is_candidate_start(end) && saw_old && saw_new && saw_content) {
                    break
                }
                if (line == "") {
                    if (saw_old && saw_new && end < line_count && is_hunk_header(lines[end + 1])) {
                        end++
                        continue
                    }
                    break
                }
                if (!saw_old && is_metadata_line(line)) {
                    end++
                    continue
                }
                if (!saw_old && is_old_header(line)) {
                    saw_old = 1
                    end++
                    continue
                }
                if (saw_old && !saw_new && is_new_header(line)) {
                    saw_new = 1
                    end++
                    continue
                }
                if (saw_new && is_hunk_header(line)) {
                    saw_content = 1
                    in_hunk = 1
                    end++
                    continue
                }
                if (saw_new && line ~ /^(Binary files |GIT binary patch|literal |delta )/) {
                    saw_content = 1
                    end++
                    continue
                }
                if (in_hunk && is_hunk_body(line)) {
                    end++
                    continue
                }
                break
            }
            if (!(saw_old && saw_new && saw_content)) {
                return start + 1
            }
            file = sprintf("%s/candidate-%03d.patch", outdir, ++count)
            for (idx = start; idx < end; idx++) {
                if (lines[idx] != "") {
                    print lines[idx] > file
                }
            }
            close(file)
            return end
        }
        {
            lines[++line_count] = $0
        }
        END {
            idx = 1
            while (idx <= line_count) {
                if (is_candidate_start(idx)) {
                    idx = emit_candidate(idx)
                } else {
                    idx++
                }
            }
            if (count > 0) {
                print "1" > found_file
                close(found_file)
            }
        }
    ' "$src"
}

extract_unified_diff_candidates() {
    local output="$1" patch="$2" tmpdir found_file block_dir block count first candidate_dir candidate_file list_file
    tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/revise-unified.XXXXXX")
    found_file="$tmpdir/found"
    block_dir="$tmpdir/blocks"
    list_file="${patch}.list"
    mkdir -p "$block_dir"
    : >"$list_file"

    awk -v outdir="$block_dir" '
        BEGIN { in_block = 0; count = 0 }
        /^```diff[[:space:]]*$/ {
            in_block = 1
            file = sprintf("%s/block-%03d.txt", outdir, ++count)
            next
        }
        in_block && /^```$/ {
            in_block = 0
            close(file)
            next
        }
        in_block {
            print > file
        }
    ' "$output"

    count=0
    first=""
    for block in "$block_dir"/block-*.txt; do
        [[ -e "$block" ]] || break
        count=$((count + 1))
        candidate_dir=$(printf '%s/extract-%03d' "$tmpdir" "$count")
        mkdir -p "$candidate_dir"
        extract_unified_diff_candidates_from_source "$block" "$candidate_dir" "$found_file"
    done
    candidate_dir=$(printf '%s/extract-%03d' "$tmpdir" $((count + 1)))
    mkdir -p "$candidate_dir"
    extract_unified_diff_candidates_from_source "$output" "$candidate_dir" "$found_file"
    count=0
    for candidate_dir in "$tmpdir"/extract-*; do
        [[ -d "$candidate_dir" ]] || break
        for candidate_file in "$candidate_dir"/candidate-*.patch; do
            [[ -e "$candidate_file" ]] || break
            count=$((count + 1))
            if [[ -z "$first" ]]; then
                first="$candidate_file"
                cp "$candidate_file" "$patch"
                printf '%s\n' "$patch" >>"$list_file"
            else
                printf -v candidate_file_suffix '%03d' "$count"
                cp "$candidate_file" "${patch%.patch}-${candidate_file_suffix}.patch"
                printf '%s\n' "${patch%.patch}-${candidate_file_suffix}.patch" >>"$list_file"
            fi
        done
    done
    if [[ -z "$first" ]]; then
        : >"$patch"
        rm -f "$list_file"
    fi
    rm -rf "$tmpdir"
}

extract_file_replacement_candidate() {
    local output="$1" patch="$2"
    awk '
        function reset_block() {
            block_len = 0
            trailer_idx = 0
        }
        function is_fence_open(line) {
            return line ~ /^```([[:alnum:]_-]+)?[[:space:]]*$/
        }
        function capture_candidate(    idx, start_idx, end_idx) {
            if (trailer_idx == 0) {
                return
            }
            candidate_len = 0
            start_idx = 1
            end_idx = trailer_idx
            if (start_idx <= end_idx && is_fence_open(block[start_idx])) {
                start_idx++
                if (start_idx <= end_idx && block[end_idx] == "```") {
                    end_idx--
                }
            }
            for (idx = start_idx; idx <= end_idx; idx++) {
                candidate[++candidate_len] = block[idx]
            }
        }
        BEGIN {
            in_block = 0
            reset_block()
            candidate_len = 0
        }
        /^## Plan$/ {
            if (in_block) {
                capture_candidate()
            }
            in_block = 1
            reset_block()
        }
        in_block {
            block[++block_len] = $0
            if ($0 ~ /^diff_lines:[[:space:]]*[0-9]+[[:space:]]*$/) {
                trailer_idx = block_len
            }
        }
        END {
            if (in_block) {
                capture_candidate()
            }
            for (idx = 1; idx <= candidate_len; idx++) {
                print candidate[idx]
            }
        }
    ' "$output" >"$patch"
}

validate_unified_headers() {
    awk '
        /^diff --git / {
            in_hunk=0
            seen=1
            if ($3 != "a/plan.txt" || $4 != "b/plan.txt") bad=1
            next
        }
        /^@@ / { in_hunk=1; next }
        !in_hunk && /^--- / {
            seen=1
            old=1
            if ($2 != "a/plan.txt") bad=1
            next
        }
        !in_hunk && /^\+\+\+ / {
            seen=1
            new=1
            if ($2 != "b/plan.txt") bad=1
            next
        }
        END {
            if (bad || !seen || !old || !new) exit 1
        }
    ' "$1"
}

validate_file_replacement() {
    local last_line
    [[ -s "$1" ]] || return 1
    last_line=$(last_nonblank_line "$1")
    case "$last_line" in
        diff_lines:\ *)
            case "${last_line#diff_lines: }" in
                ''|*[!0-9]*) return 1 ;;
                *) return 0 ;;
            esac
            ;;
        *) return 1 ;;
    esac
}

check_git_apply() {
    local patch="$1" plan_dir
    plan_dir=$(dirname "$PLAN_FILE")
    (cd "$plan_dir" && git apply --check --recount --whitespace=nowarn "$patch") >/dev/null 2>&1
}

apply_patch_file() {
    local patch="$1" plan_dir tmp
    if [[ "$PATCH_FORMAT" == "unified-diff" ]]; then
        plan_dir=$(dirname "$PLAN_FILE")
        (cd "$plan_dir" && git apply --recount --whitespace=nowarn "$patch") >/dev/null 2>&1
    else
        tmp=$(mktemp "$PLAN_FILE.replacement.XXXXXX")
        cp "$patch" "$tmp"
        mv -f "$tmp" "$PLAN_FILE"
    fi
}

_try_one_unified_diff_candidate() {
    local candidate="$1" patch_file="$2" post_heading_count
    if ! validate_unified_headers "$candidate"; then
        return 1
    fi
    if ! check_git_apply "$candidate"; then
        return 1
    fi
    cp "$candidate" "$patch_file"
    if ! apply_patch_file "$patch_file"; then
        restore_plan
        return 1
    fi
    if [[ "$ORIG_FILE_HEADING_COUNT" -gt 0 ]]; then
        post_heading_count=$(heading_count "$PLAN_FILE")
        if [[ "$post_heading_count" -eq 0 ]]; then
            restore_plan
            return 1
        fi
    fi
    if ! validate_optional_trailers_preserved "$PLAN_FILE" "$OPTIONAL_TRAILER_KEYS_FILE"; then
        restore_plan
        return 1
    fi
    return 0
}

run_emit_plan_gate() {
    local out status
    set +e
    out=$(printf 'ACTION=EMIT_PLAN\n' | "$DESIGN_DRIVER" --design-tmpdir "$DESIGN_TMPDIR")
    set -e
    status=$(printf '%s\n' "$out" | awk -F= '$1 == "EMIT_PLAN_STATUS" { print $2; found=1 } END { if (!found) print "" }')
    [[ "$status" == "ok" ]]
}

launch_tier() {
    local tier="$1" output="$2" rc
    set +e
    case "$tier" in
        codex)
            "$LAUNCH_CODEX_REVIEW" --tool codex --output "$output" --prompt-file "$PROMPT_PATH" --mode description --timeout "$TIMEOUT" --plan-file "$PLAN_FILE" --feature-file "$FEATURE_FILE" --scope-files "$FINDINGS_FILE"
            ;;
        cursor)
            "$LAUNCH_CURSOR_REVIEW" --tool cursor --output "$output" --prompt-file "$PROMPT_PATH" --mode description --timeout "$TIMEOUT" --plan-file "$PLAN_FILE" --feature-file "$FEATURE_FILE" --scope-files "$FINDINGS_FILE"
            ;;
        claude)
            "$LAUNCH_CLAUDE_REVIEW" --output "$output" --prompt-file "$PROMPT_PATH" --mode description --timeout "$TIMEOUT" --plan-file "$PLAN_FILE" --feature-file "$FEATURE_FILE" --scope-files "$FINDINGS_FILE"
            ;;
        *) return 2 ;;
    esac
    rc=$?
    set -e
    return "$rc"
}

attempt_tier() {
    local ordinal="$1" tier="$2" output="$3" patch_file output_name post_heading_count candidate candidate_ok candidate_list unified_diff_applied
    unified_diff_applied=false

    if [[ "$tier" == "codex" && "$CODEX_PRESENT" == "false" ]]; then
        set_tier_status "$ordinal" skipped-not-present
        return 1
    fi
    if [[ "$tier" == "cursor" && "$CURSOR_PRESENT" == "false" ]]; then
        set_tier_status "$ordinal" skipped-not-present
        return 1
    fi

    : >"$output"
    if ! launch_tier "$tier" "$output"; then
        set_tier_status "$ordinal" no-patch
        return 1
    fi
    if [[ ! -s "$output" ]]; then
        set_tier_status "$ordinal" no-patch
        return 1
    fi

    output_name=$(basename "$output")
    patch_file="$REVISE_DIR/${output_name%.txt}-candidate.patch"
    candidate_list="${patch_file}.list"
    rm -f "$patch_file" "$candidate_list" "$REVISE_DIR/${output_name%.txt}-candidate"-*.patch
    extract_patch "$output" "$patch_file"
    if [[ ! -s "$patch_file" ]]; then
        set_tier_status "$ordinal" no-patch
        return 1
    fi

    if [[ "$PATCH_FORMAT" == "unified-diff" ]]; then
        candidate_ok=false
        if [[ -f "$candidate_list" ]]; then
            while IFS= read -r candidate || [[ -n "$candidate" ]]; do
                [[ -n "$candidate" ]] || continue
                [[ -e "$candidate" ]] || continue
                if _try_one_unified_diff_candidate "$candidate" "$patch_file"; then
                    candidate_ok=true
                    unified_diff_applied=true
                    break
                fi
            done <"$candidate_list"
        else
            for candidate in "$REVISE_DIR/${output_name%.txt}-candidate"*.patch; do
                [[ -e "$candidate" ]] || break
                if _try_one_unified_diff_candidate "$candidate" "$patch_file"; then
                    candidate_ok=true
                    unified_diff_applied=true
                    break
                fi
            done
        fi
        if [[ "$candidate_ok" != "true" ]]; then
            set_tier_status "$ordinal" invalid-patch
            restore_plan_or_die
            return 1
        fi
    elif ! validate_file_replacement "$patch_file"; then
        set_tier_status "$ordinal" invalid-patch
        return 1
    elif ! validate_optional_trailers_preserved "$patch_file" "$OPTIONAL_TRAILER_KEYS_FILE"; then
        set_tier_status "$ordinal" invalid-patch
        return 1
    fi

    if [[ "$unified_diff_applied" != "true" ]]; then
        if ! apply_patch_file "$patch_file"; then
            set_tier_status "$ordinal" apply-failed
            restore_plan_or_die
            return 1
        fi

        if [[ "$ORIG_FILE_HEADING_COUNT" -gt 0 ]]; then
            post_heading_count=$(heading_count "$PLAN_FILE")
            if [[ "$post_heading_count" -eq 0 ]]; then
                set_tier_status "$ordinal" invalid-patch
                restore_plan_or_die
                return 1
            fi
        fi

        if ! validate_optional_trailers_preserved "$PLAN_FILE" "$OPTIONAL_TRAILER_KEYS_FILE"; then
            set_tier_status "$ordinal" invalid-patch
            restore_plan_or_die
            return 1
        fi
    fi

    if ! run_emit_plan_gate; then
        set_tier_status "$ordinal" emit-plan-failed
        restore_plan_or_die
        return 1
    fi

    set_tier_status "$ordinal" ok
    winner="$tier"
    winner_output="$output"
    return 0
}

finalize() {
    local status1 status2 status3 status4 final_status hash_after patch_path all_statuses revise_status
    local revise_tier
    status1=$(get_tier_status 1)
    status2=$(get_tier_status 2)
    status3=$(get_tier_status 3)
    status4=$(get_tier_status 4)
    [[ -n "$status1" ]] || status1=not-attempted
    [[ -n "$status2" ]] || status2=not-attempted
    [[ -n "$status3" ]] || status3=not-attempted
    [[ -n "$status4" ]] || status4=not-attempted

    if [[ -n "$winner" ]]; then
        hash_after=$(sha256_file "$PLAN_FILE")
        patch_path="$winner_output"
        rm -f "$SNAPSHOT"
        if [[ "$winner_is_fallback" == "true" ]]; then
            revise_status=ok-fallback
        else
            revise_status=ok
        fi
        revise_tier="$winner"
    else
        all_statuses="$status1 $status2 $status3 $status4"
        if [[ "$all_statuses" != *"invalid-patch"* && "$all_statuses" != *"apply-failed"* && "$all_statuses" != *"emit-plan-failed"* ]]; then
            final_status=failed-no-patch
        elif [[ "$all_statuses" == *"invalid-patch"* ]]; then
            final_status=failed-validation
        else
            final_status=failed-apply
        fi

        revise_status="$final_status"
        revise_tier=""
        patch_path=""
        hash_after="$HASH_BEFORE"
    fi

    {
        printf 'REVISE_TIER_1_STATUS=%s\n' "$status1"
        printf 'REVISE_TIER_2_STATUS=%s\n' "$status2"
        printf 'REVISE_TIER_3_STATUS=%s\n' "$status3"
        printf 'REVISE_TIER_4_STATUS=%s\n' "$status4"
        printf 'REVISE_STATUS=%s\n' "$revise_status"
        printf 'REVISE_TIER=%s\n' "$revise_tier"
        printf 'REVISE_WINNING_TIER=%s\n' "$revise_tier"
        printf 'REVISE_PATCH_PATH=%s\n' "$patch_path"
        printf 'REVISE_PLAN_HASH_BEFORE=%s\n' "$HASH_BEFORE"
        printf 'REVISE_PLAN_HASH_AFTER=%s\n' "$hash_after"
    } >"$REVISE_DIR/revise.env"
    emit_kv REVISE_TIER_1_STATUS "$status1"
    emit_kv REVISE_TIER_2_STATUS "$status2"
    emit_kv REVISE_TIER_3_STATUS "$status3"
    emit_kv REVISE_TIER_4_STATUS "$status4"
    emit_kv REVISE_STATUS "$revise_status"
    emit_kv REVISE_TIER "$revise_tier"
    emit_kv REVISE_WINNING_TIER "$revise_tier"
    emit_kv REVISE_PATCH_PATH "$patch_path"
    emit_kv REVISE_PLAN_HASH_BEFORE "$HASH_BEFORE"
    emit_kv REVISE_PLAN_HASH_AFTER "$hash_after"
    exit 0
}

compose_prompt

if attempt_tier 1 codex "$REVISE_DIR/codex-output.txt"; then
    :
elif attempt_tier 2 cursor "$REVISE_DIR/cursor-output.txt"; then
    :
else
    attempt_tier 3 claude "$REVISE_DIR/claude-output.txt" || true
fi

if [[ "$PATCH_FORMAT" == "unified-diff" && -z "$winner" ]]; then
    PATCH_FORMAT="file-replacement"
    winner_is_fallback=true
    compose_prompt
    if attempt_tier 4 codex "$REVISE_DIR/codex-output.txt"; then
        :
    elif attempt_tier 4 cursor "$REVISE_DIR/cursor-output.txt"; then
        :
    else
        attempt_tier 4 claude "$REVISE_DIR/claude-output.txt" || true
    fi
fi

finalize
