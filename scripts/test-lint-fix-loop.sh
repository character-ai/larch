#!/usr/bin/env bash
# Regression harness for lint-fix-loop.sh dispatch safety.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SOURCE_SCRIPTS="$REPO_ROOT/scripts"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

grep -F -- "--stderr-sink \"\$codex_wrapper_log\"" "$SOURCE_SCRIPTS/lint-fix-loop.sh" \
    || fail "lint-fix-loop.sh run_codex must forward --stderr-sink \"\$codex_wrapper_log\""

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-fix-loop.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    [[ "$haystack" == *"$needle"* ]] || fail "$label missing '$needle' in: $haystack"
}

kv_value() {
    local key="$1" text="$2"
    printf '%s\n' "$text" | awk -F= -v key="$key" '$1 == key { print substr($0, index($0,"=")+1); exit }'
}

make_repo() {
    local dir="$1"
    mkdir -p "$dir"
    (
        cd "$dir"
        git init -q -b main
        git config user.name "Test User"
        git config user.email "test@example.com"
        printf 'base\n' > tracked.txt
        git add tracked.txt
        git commit -q -m "baseline"
    )
}

add_forbidden_submodule_fixture() {
    local dir="$1"
    (
        cd "$dir"
        cat > .gitmodules <<'EOF'
[submodule "submod"]
	path = submod
	url = https://example.invalid/submod.git
EOF
        mkdir -p submod
        printf 'base\n' > submod/file
        git add .gitmodules submod/file
        git commit -q -m "add synthetic submodule path"
    )
}

make_fixture_scripts() {
    local dir="$1"
    mkdir -p "$dir"
    cp "$SOURCE_SCRIPTS/lint-fix-loop.sh" "$dir/lint-fix-loop.sh"
    cp "$SOURCE_SCRIPTS/lib-quiet.sh" "$dir/lib-quiet.sh"
    cp "$SOURCE_SCRIPTS/lib-cursor-launcher-common.sh" "$dir/lib-cursor-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/lib-codex-launcher-common.sh" "$dir/lib-codex-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/lib-external-launcher-common.sh" "$dir/lib-external-launcher-common.sh"
    cp "$SOURCE_SCRIPTS/lib-submodule-prohibition.sh" "$dir/lib-submodule-prohibition.sh"
    cp "$SOURCE_SCRIPTS/parse-codex-usage.sh" "$dir/parse-codex-usage.sh"
    cp "$SOURCE_SCRIPTS/token-ledger.sh" "$dir/token-ledger.sh"
    cp "$SOURCE_SCRIPTS/read-session-env-key.sh" "$dir/read-session-env-key.sh"
    cp "$SOURCE_SCRIPTS/git-commit.sh" "$dir/git-commit.sh"
    cp "$SOURCE_SCRIPTS/lib-failed-agent-stderr-tail.sh" "$dir/lib-failed-agent-stderr-tail.sh"
    cp "$SOURCE_SCRIPTS/redact-tmpdir-paths.sh" "$dir/redact-tmpdir-paths.sh"
    cp "$SOURCE_SCRIPTS/redact-secrets.sh" "$dir/redact-secrets.sh"
    cp "$SOURCE_SCRIPTS/agent-model-args.sh" "$dir/agent-model-args.sh"
    cp "$SOURCE_SCRIPTS/external-tool-registry.sh" "$dir/external-tool-registry.sh"
    cp "$SOURCE_SCRIPTS/lib-cursor-auth.sh" "$dir/lib-cursor-auth.sh"
    cp "$SOURCE_SCRIPTS/cursor-wrap-prompt.sh" "$dir/cursor-wrap-prompt.sh"
    chmod +x \
        "$dir/agent-model-args.sh" \
        "$dir/cursor-wrap-prompt.sh" \
        "$dir/lint-fix-loop.sh" \
        "$dir/lib-cursor-launcher-common.sh" \
        "$dir/parse-codex-usage.sh" \
        "$dir/token-ledger.sh" \
        "$dir/read-session-env-key.sh" \
        "$dir/git-commit.sh"
}

make_session() {
    local dir="$1"
    mkdir -p "$dir"
    cat > "$dir/session-env.sh" <<'EOF'
CODEX_PRESENT=true
CURSOR_PRESENT=false
EOF
}

write_wrapper_commit_head() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub commit head change\n' > "$output"
printf 'committed-by-stub\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub commit"
EOF
    chmod +x "$path"
}

write_wrapper_amend_history_rewrite() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub amend history rewrite\n' > "$output"
printf 'amended-change\n' > tracked.txt
git add tracked.txt
git commit --amend -q -m "stub amended commit"
EOF
    chmod +x "$path"
}

write_wrapper_modify_only() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub modify only\n' > "$output"
printf 'modified-without-commit\n' > tracked.txt
EOF
    chmod +x "$path"
}

write_wrapper_codex_telemetry() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
json=false
last_message=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --timeout) shift 2 ;;
        --tool) shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) json=true; shift ;;
        --output-last-message) last_message="$2"; shift 2 ;;
        *) shift ;;
    esac
done

[[ "$json" == "true" ]] || { printf 'missing --json\n' >&2; exit 64; }
[[ -n "$last_message" ]] || { printf 'missing --output-last-message\n' >&2; exit 65; }
printf 'CODEX FINAL MESSAGE\n' > "$last_message"
[[ -n "$output" ]] && printf 'CODEX FINAL MESSAGE\n' > "$output"
printf '{"type":"token_usage","input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}\n'
printf 'wrapper diagnostic\n' >&2
exit "${TEST_CODEX_RC:-0}"
EOF
    chmod +x "$path"
}

write_wrapper_codex_fail_stderr() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
json=false
last_message=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --timeout) shift 2 ;;
        --tool) shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) json=true; shift ;;
        --output-last-message) last_message="$2"; shift 2 ;;
        *) shift ;;
    esac
done

[[ "$json" == "true" ]] || { printf 'missing --json\n' >&2; exit 64; }
[[ -n "$last_message" ]] || { printf 'missing --output-last-message\n' >&2; exit 65; }
printf 'LARCH_LINT_FIX_CODEX_STDERR_PROBE\n' >&2
exit 1
EOF
    chmod +x "$path"
}

write_wrapper_cursor_fail_preserve_tail() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
tool=""
json=false
last_message=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --timeout) shift 2 ;;
        --tool) tool="$2"; shift 2 ;;
        --capture-stdout) shift ;;
        --stderr-sink) shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) json=true; shift ;;
        --output-last-message) last_message="$2"; shift 2 ;;
        *) shift ;;
    esac
done

[[ -n "$output" ]] || exit 9
if [[ "$tool" == "cursor" ]]; then
    printf 'agent stderr from cursor agent\n' > "${output}.stderr-tail"
    printf 'wrapper progress noise\n' >&2
    exit 1
fi
[[ "$json" == "true" ]] || { printf 'missing --json\n' >&2; exit 64; }
[[ -n "$last_message" ]] || { printf 'missing --output-last-message\n' >&2; exit 65; }
printf 'LARCH_LINT_FIX_CODEX_STDERR_PROBE\n' >&2
exit 1
EOF
    chmod +x "$path"
}

write_wrapper_codex_bad_usage() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
json=false
last_message=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --timeout) shift 2 ;;
        --tool) shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) json=true; shift ;;
        --output-last-message) last_message="$2"; shift 2 ;;
        *) shift ;;
    esac
done

[[ "$json" == "true" ]] || { printf 'missing --json\n' >&2; exit 64; }
[[ -n "$last_message" ]] || { printf 'missing --output-last-message\n' >&2; exit 65; }
printf 'CODEX FINAL MESSAGE\n' > "$last_message"
[[ -n "$output" ]] && printf 'CODEX FINAL MESSAGE\n' > "$output"
printf '{"type":"token_usage"\n'
printf 'wrapper diagnostic\n' >&2
EOF
    chmod +x "$path"
}

write_wrapper_commit_forbidden_path() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub forbidden commit\n' > "$output"
printf 'forbidden-change\n' > submod/file
git add submod/file
git commit -q -m "stub forbidden commit"
EOF
    chmod +x "$path"
}

write_wrapper_merge_commit() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub merge commit\n' > "$output"
git checkout -q -b sibling
printf 'sibling-change\n' > sibling.txt
git add sibling.txt
git commit -q -m "stub sibling commit"
git checkout -q main
printf 'main-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub main commit"
git merge --no-ff -q sibling -m "stub merge commit"
EOF
    chmod +x "$path"
}

write_wrapper_detached_commit() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub detached commit\n' > "$output"
git checkout -q --detach
printf 'detached-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub detached commit"
EOF
    chmod +x "$path"
}

write_wrapper_branch_switch_commit() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub branch switch commit\n' > "$output"
git checkout -q -b sibling
printf 'sibling-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub sibling commit"
EOF
    chmod +x "$path"
}

write_wrapper_commit_other_file() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub dirty baseline commit\n' > "$output"
printf 'new committed file\n' > committed.txt
git add committed.txt
git commit -q -m "stub dirty baseline commit"
EOF
    chmod +x "$path"
}

write_wrapper_two_commits_same_branch() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

printf 'stub two commits\n' > "$output"
printf 'first-change\n' > tracked.txt
git add tracked.txt
git commit -q -m "stub first commit"
printf 'second-change\n' > second.txt
git add second.txt
git commit -q -m "stub second commit"
EOF
    chmod +x "$path"
}

run_case() {
    local fixture_scripts="$1" repo="$2" session="$3" checks_log="$4" wrapper="$5" site="${6:-step3}" target_args_file="${7:-}"
    local rc=0 out
    local extra_args=()
    if [[ -n "$target_args_file" ]]; then
        extra_args=(--target-cmd-args-file "$target_args_file")
    fi
    out=$(
        cd "$repo" && \
        unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG || true
        # shellcheck disable=SC2030,SC2031
        export IMPLEMENT_TMPDIR="$session"
        LINT_FIX_LOOP_RUN_EXTERNAL_AGENT_SH="$wrapper" \
        LARCH_TOKEN_LEDGER="${LARCH_TOKEN_LEDGER:-}" \
        bash "$fixture_scripts/lint-fix-loop.sh" --tmpdir "$session" --site "$site" --checks-log "$checks_log" ${extra_args[@]+"${extra_args[@]}"} 2>&1
    ) || rc=$?
    printf '%s\n%s\n' "$rc" "$out"
}

# Case 0a: Codex JSONL is split from wrapper diagnostics and recorded to the token ledger.
CASE0A="$TMPROOT/case0a"
REPO0A="$CASE0A/repo"
SCRIPTS0A="$CASE0A/scripts"
SESSION0A="$CASE0A/session"
CHECKS0A="$CASE0A/checks.log"
WRAPPER0A="$CASE0A/wrapper.sh"
LEDGER0A="$CASE0A/token-ledger.jsonl"
make_repo "$REPO0A"
make_fixture_scripts "$SCRIPTS0A"
make_session "$SESSION0A"
printf 'synthetic checks failure\n' > "$CHECKS0A"
write_wrapper_codex_telemetry "$WRAPPER0A"

case0a_result=$(LARCH_TOKEN_LEDGER="$LEDGER0A" run_case "$SCRIPTS0A" "$REPO0A" "$SESSION0A" "$CHECKS0A" "$WRAPPER0A")
case0a_rc=$(printf '%s\n' "$case0a_result" | sed -n '1p')
case0a_out=$(printf '%s\n' "$case0a_result" | sed -n '2,$p')
[[ "$case0a_rc" == "0" ]] || fail "case0a expected rc 0, got $case0a_rc"
assert_contains "$case0a_out" 'LINT_FIX_STATUS=no-changes' "case0a no changes"
case0a_run_dir=$(kv_value LINT_FIX_RUN_DIR "$case0a_out")
[[ -s "$case0a_run_dir/codex.events.jsonl" ]] || fail "case0a expected codex.events.jsonl"
grep -Fq 'CODEX FINAL MESSAGE' "$case0a_run_dir/codex.log" || fail "case0a expected codex.log final message"
[[ -f "$case0a_run_dir/codex.wrapper.log" ]] || fail "case0a expected codex.wrapper.log"
if grep -Fq '"type":"token_usage"' "$case0a_run_dir/codex.wrapper.log"; then
    fail "case0a wrapper log must not contain JSONL events"
fi
jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_lint_fix" and .input==100 and .cache_read==900 and .output==50 and .total==1050)' "$LEDGER0A" >/dev/null \
    || fail "case0a expected codex_lint_fix token ledger row"

# Case 0a.1: unset CLAUDE_PLUGIN_ROOT still records Codex telemetry through the script-dir fallback.
CASE0A1="$TMPROOT/case0a1"
REPO0A1="$CASE0A1/repo"
SCRIPTS0A1="$CASE0A1/scripts"
SESSION0A1="$CASE0A1/session"
CHECKS0A1="$CASE0A1/checks.log"
WRAPPER0A1="$CASE0A1/wrapper.sh"
LEDGER0A1="$CASE0A1/token-ledger.jsonl"
make_repo "$REPO0A1"
make_fixture_scripts "$SCRIPTS0A1"
make_session "$SESSION0A1"
printf 'synthetic checks failure\n' > "$CHECKS0A1"
write_wrapper_codex_telemetry "$WRAPPER0A1"

case0a1_result=$(
    cd "$REPO0A1" && \
    unset CLAUDE_PLUGIN_ROOT && \
    IMPLEMENT_TMPDIR="$SESSION0A1" \
    LINT_FIX_LOOP_RUN_EXTERNAL_AGENT_SH="$WRAPPER0A1" \
    LARCH_TOKEN_LEDGER="$LEDGER0A1" \
    bash "$SCRIPTS0A1/lint-fix-loop.sh" --tmpdir "$SESSION0A1" --site step3 --checks-log "$CHECKS0A1" 2>&1
)
case0a1_rc=$?
[[ "$case0a1_rc" == "0" ]] || fail "case0a1 expected rc 0, got $case0a1_rc"
assert_contains "$case0a1_result" 'LINT_FIX_STATUS=no-changes' "case0a1 no changes"
case0a1_run_dir=$(kv_value LINT_FIX_RUN_DIR "$case0a1_result")
[[ -s "$case0a1_run_dir/codex.events.jsonl" ]] || fail "case0a1 expected codex.events.jsonl"
jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_lint_fix" and .total==1050)' "$LEDGER0A1" >/dev/null \
    || fail "case0a1 expected unset-root codex_lint_fix token ledger row"

# Case 0a.2: parse diagnostics go to a telemetry sidecar instead of the publishable wrapper log.
CASE0A2="$TMPROOT/case0a2"
REPO0A2="$CASE0A2/repo"
SCRIPTS0A2="$CASE0A2/scripts"
SESSION0A2="$CASE0A2/session"
CHECKS0A2="$CASE0A2/checks.log"
WRAPPER0A2="$CASE0A2/wrapper.sh"
make_repo "$REPO0A2"
make_fixture_scripts "$SCRIPTS0A2"
make_session "$SESSION0A2"
printf 'synthetic checks failure\n' > "$CHECKS0A2"
write_wrapper_codex_bad_usage "$WRAPPER0A2"

case0a2_result=$(run_case "$SCRIPTS0A2" "$REPO0A2" "$SESSION0A2" "$CHECKS0A2" "$WRAPPER0A2")
case0a2_rc=$(printf '%s\n' "$case0a2_result" | sed -n '1p')
case0a2_out=$(printf '%s\n' "$case0a2_result" | sed -n '2,$p')
[[ "$case0a2_rc" == "0" ]] || fail "case0a2 expected rc 0, got $case0a2_rc"
assert_contains "$case0a2_out" 'LINT_FIX_STATUS=no-changes' "case0a2 no changes"
case0a2_run_dir=$(kv_value LINT_FIX_RUN_DIR "$case0a2_out")
[[ -f "$case0a2_run_dir/codex.wrapper.log" ]] || fail "case0a2 expected codex.wrapper.log"
if grep -Fq 'parse-codex-usage.sh:' "$case0a2_run_dir/codex.wrapper.log"; then
    fail "case0a2 wrapper log must not contain parse diagnostics"
fi
grep -Fq 'parse-codex-usage.sh:' "$case0a2_run_dir/codex.sidecar" \
    || fail "case0a2 telemetry sidecar should capture parse diagnostics"

# Case 0b: Codex fails at runtime and Cursor is absent; #3207 waterfalls to the
# Claude/main-agent tier (main-agent-required, exit 0) instead of hard-failing.
# Codex events and telemetry are still written.
CASE0B="$TMPROOT/case0b"
REPO0B="$CASE0B/repo"
SCRIPTS0B="$CASE0B/scripts"
SESSION0B="$CASE0B/session"
CHECKS0B="$CASE0B/checks.log"
WRAPPER0B="$CASE0B/wrapper.sh"
LEDGER0B="$CASE0B/token-ledger.jsonl"
make_repo "$REPO0B"
make_fixture_scripts "$SCRIPTS0B"
make_session "$SESSION0B"
printf 'synthetic checks failure\n' > "$CHECKS0B"
write_wrapper_codex_telemetry "$WRAPPER0B"

case0b_result=$(TEST_CODEX_RC=23 LARCH_TOKEN_LEDGER="$LEDGER0B" run_case "$SCRIPTS0B" "$REPO0B" "$SESSION0B" "$CHECKS0B" "$WRAPPER0B")
case0b_rc=$(printf '%s\n' "$case0b_result" | sed -n '1p')
case0b_out=$(printf '%s\n' "$case0b_result" | sed -n '2,$p')
[[ "$case0b_rc" == "0" ]] || fail "case0b expected rc 0 (#3207 waterfall to main-agent), got $case0b_rc"
assert_contains "$case0b_out" 'LINT_FIX_STATUS=main-agent-required' "case0b waterfalls to main-agent (#3207)"
assert_contains "$case0b_out" 'FAILURE_REASON=dispatch-failed' "case0b retains dispatch-failed diagnostic"
case0b_run_dir=$(kv_value LINT_FIX_RUN_DIR "$case0b_out")
[[ -s "$case0b_run_dir/codex.events.jsonl" ]] || fail "case0b expected codex.events.jsonl despite failure"
jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_lint_fix" and .total==1050)' "$LEDGER0B" >/dev/null \
    || fail "case0b expected failed Codex token ledger row"

# Case 1: external coder commits on the same clean branch; lint-fix-loop accepts it.
CASE1="$TMPROOT/case1"
REPO1="$CASE1/repo"
SCRIPTS1="$CASE1/scripts"
SESSION1="$CASE1/session"
CHECKS1="$CASE1/checks.log"
WRAPPER1="$CASE1/wrapper.sh"
make_repo "$REPO1"
make_fixture_scripts "$SCRIPTS1"
make_session "$SESSION1"
printf 'synthetic checks failure\n' > "$CHECKS1"
write_wrapper_commit_head "$WRAPPER1"

case1_result=$(run_case "$SCRIPTS1" "$REPO1" "$SESSION1" "$CHECKS1" "$WRAPPER1")
case1_rc=$(printf '%s\n' "$case1_result" | sed -n '1p')
case1_out=$(printf '%s\n' "$case1_result" | sed -n '2,$p')
[[ "$case1_rc" == "0" ]] || fail "case1 expected rc 0, got $case1_rc"
assert_contains "$case1_out" 'LINT_FIX_STATUS=applied' "case1 status"
case1_commit_sha=$(kv_value LINT_FIX_COMMIT_SHA "$case1_out")
[[ -n "$case1_commit_sha" ]] || fail "case1 expected non-empty LINT_FIX_COMMIT_SHA"
case1_head=$(cd "$REPO1" && git rev-parse HEAD)
[[ "$case1_commit_sha" == "$case1_head" ]] || fail "case1 expected commit sha $case1_head, got $case1_commit_sha"
assert_contains "$case1_out" 'LINT_FIX_HEAD_CHANGED=true' "case1 head changed"
case1_delta_file=$(kv_value LINT_FIX_DELTA_PATHS_FILE "$case1_out")
[[ -n "$case1_delta_file" && -f "$case1_delta_file" ]] || fail "case1 expected readable delta paths file"
grep -Fxq 'tracked.txt' "$case1_delta_file" || fail "case1 expected tracked.txt in delta paths"

# Case 1b: coder commits a forbidden submodule path; lint-fix-loop resets to baseline.
CASE1B="$TMPROOT/case1b"
REPO1B="$CASE1B/repo"
SCRIPTS1B="$CASE1B/scripts"
SESSION1B="$CASE1B/session"
CHECKS1B="$CASE1B/checks.log"
WRAPPER1B="$CASE1B/wrapper.sh"
make_repo "$REPO1B"
add_forbidden_submodule_fixture "$REPO1B"
make_fixture_scripts "$SCRIPTS1B"
make_session "$SESSION1B"
printf 'synthetic checks failure\n' > "$CHECKS1B"
write_wrapper_commit_forbidden_path "$WRAPPER1B"
case1b_baseline=$(cd "$REPO1B" && git rev-parse HEAD)

case1b_result=$(run_case "$SCRIPTS1B" "$REPO1B" "$SESSION1B" "$CHECKS1B" "$WRAPPER1B")
case1b_rc=$(printf '%s\n' "$case1b_result" | sed -n '1p')
case1b_out=$(printf '%s\n' "$case1b_result" | sed -n '2,$p')
[[ "$case1b_rc" == "1" ]] || fail "case1b expected rc 1, got $case1b_rc"
assert_contains "$case1b_out" 'LINT_FIX_STATUS=failed' "case1b status"
assert_contains "$case1b_out" 'FAILURE_REASON=forbidden-path-violation' "case1b reason"
case1b_head=$(cd "$REPO1B" && git rev-parse HEAD)
[[ "$case1b_head" == "$case1b_baseline" ]] || fail "case1b expected reset to $case1b_baseline, got $case1b_head"

# Case 1c: detached HEAD after dispatch still fails closed.
CASE1C="$TMPROOT/case1c"
REPO1C="$CASE1C/repo"
SCRIPTS1C="$CASE1C/scripts"
SESSION1C="$CASE1C/session"
CHECKS1C="$CASE1C/checks.log"
WRAPPER1C="$CASE1C/wrapper.sh"
make_repo "$REPO1C"
make_fixture_scripts "$SCRIPTS1C"
make_session "$SESSION1C"
printf 'synthetic checks failure\n' > "$CHECKS1C"
write_wrapper_detached_commit "$WRAPPER1C"

case1c_result=$(run_case "$SCRIPTS1C" "$REPO1C" "$SESSION1C" "$CHECKS1C" "$WRAPPER1C")
case1c_rc=$(printf '%s\n' "$case1c_result" | sed -n '1p')
case1c_out=$(printf '%s\n' "$case1c_result" | sed -n '2,$p')
[[ "$case1c_rc" == "1" ]] || fail "case1c expected rc 1, got $case1c_rc"
assert_contains "$case1c_out" 'LINT_FIX_STATUS=failed' "case1c status"
assert_contains "$case1c_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1c reason"

# Case 1d: branch switch after dispatch still fails closed.
CASE1D="$TMPROOT/case1d"
REPO1D="$CASE1D/repo"
SCRIPTS1D="$CASE1D/scripts"
SESSION1D="$CASE1D/session"
CHECKS1D="$CASE1D/checks.log"
WRAPPER1D="$CASE1D/wrapper.sh"
make_repo "$REPO1D"
make_fixture_scripts "$SCRIPTS1D"
make_session "$SESSION1D"
printf 'synthetic checks failure\n' > "$CHECKS1D"
write_wrapper_branch_switch_commit "$WRAPPER1D"

case1d_result=$(run_case "$SCRIPTS1D" "$REPO1D" "$SESSION1D" "$CHECKS1D" "$WRAPPER1D")
case1d_rc=$(printf '%s\n' "$case1d_result" | sed -n '1p')
case1d_out=$(printf '%s\n' "$case1d_result" | sed -n '2,$p')
[[ "$case1d_rc" == "1" ]] || fail "case1d expected rc 1, got $case1d_rc"
assert_contains "$case1d_out" 'LINT_FIX_STATUS=failed' "case1d status"
assert_contains "$case1d_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1d reason"

# Case 1d.5: amended history rewrite after dispatch still fails closed.
CASE1D5="$TMPROOT/case1d5"
REPO1D5="$CASE1D5/repo"
SCRIPTS1D5="$CASE1D5/scripts"
SESSION1D5="$CASE1D5/session"
CHECKS1D5="$CASE1D5/checks.log"
WRAPPER1D5="$CASE1D5/wrapper.sh"
make_repo "$REPO1D5"
make_fixture_scripts "$SCRIPTS1D5"
make_session "$SESSION1D5"
printf 'synthetic checks failure\n' > "$CHECKS1D5"
write_wrapper_amend_history_rewrite "$WRAPPER1D5"

case1d5_result=$(run_case "$SCRIPTS1D5" "$REPO1D5" "$SESSION1D5" "$CHECKS1D5" "$WRAPPER1D5")
case1d5_rc=$(printf '%s\n' "$case1d5_result" | sed -n '1p')
case1d5_out=$(printf '%s\n' "$case1d5_result" | sed -n '2,$p')
[[ "$case1d5_rc" == "1" ]] || fail "case1d5 expected rc 1, got $case1d5_rc"
assert_contains "$case1d5_out" 'LINT_FIX_STATUS=failed' "case1d5 status"
assert_contains "$case1d5_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1d5 reason"

# Case 1d.6: merge commits after dispatch still fail closed.
CASE1D6="$TMPROOT/case1d6"
REPO1D6="$CASE1D6/repo"
SCRIPTS1D6="$CASE1D6/scripts"
SESSION1D6="$CASE1D6/session"
CHECKS1D6="$CASE1D6/checks.log"
WRAPPER1D6="$CASE1D6/wrapper.sh"
make_repo "$REPO1D6"
make_fixture_scripts "$SCRIPTS1D6"
make_session "$SESSION1D6"
printf 'synthetic checks failure\n' > "$CHECKS1D6"
write_wrapper_merge_commit "$WRAPPER1D6"

case1d6_result=$(run_case "$SCRIPTS1D6" "$REPO1D6" "$SESSION1D6" "$CHECKS1D6" "$WRAPPER1D6")
case1d6_rc=$(printf '%s\n' "$case1d6_result" | sed -n '1p')
case1d6_out=$(printf '%s\n' "$case1d6_result" | sed -n '2,$p')
[[ "$case1d6_rc" == "1" ]] || fail "case1d6 expected rc 1, got $case1d6_rc"
assert_contains "$case1d6_out" 'LINT_FIX_STATUS=failed' "case1d6 status"
assert_contains "$case1d6_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1d6 reason"

# Case 1e: dirty baseline plus HEAD movement still fails closed without reset.
CASE1E="$TMPROOT/case1e"
REPO1E="$CASE1E/repo"
SCRIPTS1E="$CASE1E/scripts"
SESSION1E="$CASE1E/session"
CHECKS1E="$CASE1E/checks.log"
WRAPPER1E="$CASE1E/wrapper.sh"
make_repo "$REPO1E"
make_fixture_scripts "$SCRIPTS1E"
make_session "$SESSION1E"
printf 'synthetic checks failure\n' > "$CHECKS1E"
printf 'preexisting dirty work\n' > "$REPO1E/tracked.txt"
write_wrapper_commit_other_file "$WRAPPER1E"

case1e_result=$(run_case "$SCRIPTS1E" "$REPO1E" "$SESSION1E" "$CHECKS1E" "$WRAPPER1E")
case1e_rc=$(printf '%s\n' "$case1e_result" | sed -n '1p')
case1e_out=$(printf '%s\n' "$case1e_result" | sed -n '2,$p')
[[ "$case1e_rc" == "1" ]] || fail "case1e expected rc 1, got $case1e_rc"
assert_contains "$case1e_out" 'LINT_FIX_STATUS=failed' "case1e status"
assert_contains "$case1e_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1e reason"
case1e_dirty=$(cd "$REPO1E" && git diff --name-only)
[[ "$case1e_dirty" == "tracked.txt" ]] || fail "case1e expected dirty tracked.txt to survive, got: $case1e_dirty"

# Case 1f: same-branch two-commit advancement still fails closed.
CASE1F="$TMPROOT/case1f"
REPO1F="$CASE1F/repo"
SCRIPTS1F="$CASE1F/scripts"
SESSION1F="$CASE1F/session"
CHECKS1F="$CASE1F/checks.log"
WRAPPER1F="$CASE1F/wrapper.sh"
make_repo "$REPO1F"
make_fixture_scripts "$SCRIPTS1F"
make_session "$SESSION1F"
printf 'synthetic checks failure\n' > "$CHECKS1F"
write_wrapper_two_commits_same_branch "$WRAPPER1F"

case1f_result=$(run_case "$SCRIPTS1F" "$REPO1F" "$SESSION1F" "$CHECKS1F" "$WRAPPER1F")
case1f_rc=$(printf '%s\n' "$case1f_result" | sed -n '1p')
case1f_out=$(printf '%s\n' "$case1f_result" | sed -n '2,$p')
[[ "$case1f_rc" == "1" ]] || fail "case1f expected rc 1, got $case1f_rc"
assert_contains "$case1f_out" 'LINT_FIX_STATUS=failed' "case1f status"
assert_contains "$case1f_out" 'FAILURE_REASON=head-changed-after-dispatch' "case1f reason"
if printf '%s\n' "$case1f_out" | grep -Fq 'LINT_FIX_DELTA_PATHS_FILE='; then
    fail "case1f should not export LINT_FIX_DELTA_PATHS_FILE"
fi

# Case 2: helper-owned commit fails; staged delta paths must be reset.
CASE2="$TMPROOT/case2"
REPO2="$CASE2/repo"
SCRIPTS2="$CASE2/scripts"
SESSION2="$CASE2/session"
CHECKS2="$CASE2/checks.log"
WRAPPER2="$CASE2/wrapper.sh"
make_repo "$REPO2"
make_fixture_scripts "$SCRIPTS2"
make_session "$SESSION2"
printf 'synthetic checks failure\n' > "$CHECKS2"
write_wrapper_modify_only "$WRAPPER2"
cat > "$SCRIPTS2/git-commit.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exit 1
EOF
chmod +x "$SCRIPTS2/git-commit.sh"

case2_result=$(run_case "$SCRIPTS2" "$REPO2" "$SESSION2" "$CHECKS2" "$WRAPPER2")
case2_rc=$(printf '%s\n' "$case2_result" | sed -n '1p')
case2_out=$(printf '%s\n' "$case2_result" | sed -n '2,$p')
[[ "$case2_rc" == "1" ]] || fail "case2 expected rc 1, got $case2_rc"
assert_contains "$case2_out" 'LINT_FIX_STATUS=failed' "case2 status"
assert_contains "$case2_out" 'FAILURE_REASON=git-commit-failed' "case2 reason"
cached_after_case2=$(cd "$REPO2" && git diff --cached --name-only)
[[ -z "$cached_after_case2" ]] || fail "case2 expected empty index, got: $cached_after_case2"
worktree_after_case2=$(cd "$REPO2" && git diff --name-only)
[[ "$worktree_after_case2" == "tracked.txt" ]] || fail "case2 expected unstaged tracked.txt delta, got: $worktree_after_case2"

# Case 3: ship-pr-ci-initial site — success path (coder modifies file).
CASE3="$TMPROOT/case3"
REPO3="$CASE3/repo"
SCRIPTS3="$CASE3/scripts"
SESSION3="$CASE3/session"
CHECKS3="$CASE3/checks.log"
WRAPPER3="$CASE3/wrapper.sh"
make_repo "$REPO3"
make_fixture_scripts "$SCRIPTS3"
make_session "$SESSION3"
printf 'synthetic checks failure\n' > "$CHECKS3"
write_wrapper_modify_only "$WRAPPER3"

case3_result=$(run_case "$SCRIPTS3" "$REPO3" "$SESSION3" "$CHECKS3" "$WRAPPER3" ship-pr-ci-initial)
assert_contains "$case3_result" 'LINT_FIX_STATUS=applied' "case3 status"
assert_contains "$case3_result" 'LINT_FIX_SITE=ship-pr-ci-initial' "case3 site"
assert_contains "$case3_result" 'LINT_FIX_DELTA_PATHS_FILE=' "case3 delta paths file"

# Case 4: ship-pr-ci-initial site — no-changes path (coder makes no changes).
CASE4="$TMPROOT/case4"
REPO4="$CASE4/repo"
SCRIPTS4="$CASE4/scripts"
SESSION4="$CASE4/session"
CHECKS4="$CASE4/checks.log"
WRAPPER4="$CASE4/wrapper.sh"
make_repo "$REPO4"
make_fixture_scripts "$SCRIPTS4"
make_session "$SESSION4"
printf 'synthetic checks failure\n' > "$CHECKS4"
# Wrapper that writes nothing to disk.
cat > "$WRAPPER4" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
printf 'stub no-op\n' > "$output"
EOF
chmod +x "$WRAPPER4"

case4_result=$(run_case "$SCRIPTS4" "$REPO4" "$SESSION4" "$CHECKS4" "$WRAPPER4" ship-pr-ci-initial)
assert_contains "$case4_result" 'LINT_FIX_STATUS=no-changes' "case4 status"
assert_contains "$case4_result" 'LINT_FIX_SITE=ship-pr-ci-initial' "case4 site"

# Case 5: ship-pr-ci-merge site — success path (coder modifies file).
CASE5="$TMPROOT/case5"
REPO5="$CASE5/repo"
SCRIPTS5="$CASE5/scripts"
SESSION5="$CASE5/session"
CHECKS5="$CASE5/checks.log"
WRAPPER5="$CASE5/wrapper.sh"
make_repo "$REPO5"
make_fixture_scripts "$SCRIPTS5"
make_session "$SESSION5"
printf 'synthetic checks failure\n' > "$CHECKS5"
write_wrapper_modify_only "$WRAPPER5"

case5_result=$(run_case "$SCRIPTS5" "$REPO5" "$SESSION5" "$CHECKS5" "$WRAPPER5" ship-pr-ci-merge)
assert_contains "$case5_result" 'LINT_FIX_STATUS=applied' "case5 status"
assert_contains "$case5_result" 'LINT_FIX_SITE=ship-pr-ci-merge' "case5 site"
assert_contains "$case5_result" 'LINT_FIX_DELTA_PATHS_FILE=' "case5 delta paths file"

# Case 6: per-job site includes the display-only local argv in the prompt.
CASE6="$TMPROOT/case6"
REPO6="$CASE6/repo"
SCRIPTS6="$CASE6/scripts"
SESSION6="$CASE6/session"
CHECKS6="$CASE6/checks.log"
WRAPPER6="$CASE6/wrapper.sh"
ARGS6="$CASE6/target-args.txt"
make_repo "$REPO6"
make_fixture_scripts "$SCRIPTS6"
make_session "$SESSION6"
printf 'synthetic per-job failure\n' > "$CHECKS6"
printf '%s\n' env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only > "$ARGS6"
write_wrapper_modify_only "$WRAPPER6"

case6_result=$(run_case "$SCRIPTS6" "$REPO6" "$SESSION6" "$CHECKS6" "$WRAPPER6" ship-pr-ci-per-job "$ARGS6")
assert_contains "$case6_result" 'LINT_FIX_STATUS=applied' "case6 status"
assert_contains "$case6_result" 'LINT_FIX_SITE=ship-pr-ci-per-job' "case6 site"
case6_prompt=$(find "$SESSION6/lint-fix-loop" -name prompt.md -print -quit)
[[ -n "$case6_prompt" ]] || fail "case6 prompt was not written"
assert_contains "$(cat "$case6_prompt")" "local command \`env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only\` passes" "case6 prompt local command"

# Case 7: existing sites reject --target-cmd-args-file.
CASE7="$TMPROOT/case7"
REPO7="$CASE7/repo"
SCRIPTS7="$CASE7/scripts"
SESSION7="$CASE7/session"
CHECKS7="$CASE7/checks.log"
WRAPPER7="$CASE7/wrapper.sh"
ARGS7="$CASE7/target-args.txt"
make_repo "$REPO7"
make_fixture_scripts "$SCRIPTS7"
make_session "$SESSION7"
printf 'synthetic checks failure\n' > "$CHECKS7"
printf '%s\n' make lint-only > "$ARGS7"
write_wrapper_modify_only "$WRAPPER7"
case7_result=$(run_case "$SCRIPTS7" "$REPO7" "$SESSION7" "$CHECKS7" "$WRAPPER7" ship-pr-ci-initial "$ARGS7")
case7_rc=$(printf '%s\n' "$case7_result" | sed -n '1p')
[[ "$case7_rc" == "2" ]] || fail "case7 expected rc 2, got $case7_rc"

# Case 8: per-job target argv files reject control characters.
CASE8="$TMPROOT/case8"
REPO8="$CASE8/repo"
SCRIPTS8="$CASE8/scripts"
SESSION8="$CASE8/session"
CHECKS8="$CASE8/checks.log"
WRAPPER8="$CASE8/wrapper.sh"
ARGS8="$CASE8/target-args.txt"
make_repo "$REPO8"
make_fixture_scripts "$SCRIPTS8"
make_session "$SESSION8"
printf 'synthetic checks failure\n' > "$CHECKS8"
printf 'make\ntest-harnesses-3\001\n' > "$ARGS8"
write_wrapper_modify_only "$WRAPPER8"
case8_result=$(run_case "$SCRIPTS8" "$REPO8" "$SESSION8" "$CHECKS8" "$WRAPPER8" ship-pr-ci-per-job "$ARGS8")
case8_rc=$(printf '%s\n' "$case8_result" | sed -n '1p')
[[ "$case8_rc" == "2" ]] || fail "case8 expected rc 2, got $case8_rc"
assert_contains "$case8_result" '--target-cmd-args-file must not contain control characters' "case8 rejection message"

# Case 9: codex failure writes stderr-tail and STDERR_TAIL_PATH on dispatch-failed.
CASE9="$TMPROOT/case9"
REPO9="$CASE9/repo"
SCRIPTS9="$CASE9/scripts"
SESSION9="$CASE9/session"
CHECKS9="$CASE9/checks.log"
WRAPPER9="$CASE9/wrapper.sh"
make_repo "$REPO9"
make_fixture_scripts "$SCRIPTS9"
make_session "$SESSION9"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=false\n' > "$SESSION9/session-env.sh"
printf 'synthetic checks failure\n' > "$CHECKS9"
write_wrapper_codex_fail_stderr "$WRAPPER9"

case9_result=$(run_case "$SCRIPTS9" "$REPO9" "$SESSION9" "$CHECKS9" "$WRAPPER9")
case9_rc=$(printf '%s\n' "$case9_result" | sed -n '1p')
case9_out=$(printf '%s\n' "$case9_result" | sed -n '2,$p')
[[ "$case9_rc" == "0" ]] || fail "case9 expected rc 0, got $case9_rc"
assert_contains "$case9_out" 'LINT_FIX_STATUS=main-agent-required' "case9 status"
assert_contains "$case9_out" 'STDERR_TAIL_PATH=' "case9 stderr tail path kv"
case9_run_dir=$(kv_value LINT_FIX_RUN_DIR "$case9_out")
[[ -s "$case9_run_dir/codex.log.stderr-tail" ]] \
    || fail "case9 expected codex.log.stderr-tail"
grep -Fq 'LARCH_LINT_FIX_CODEX_STDERR_PROBE' "$case9_run_dir/codex.log.stderr-tail" \
    || fail "case9 stderr-tail must contain codex stderr probe"

# Case 10: cursor failure preserves agent stderr-tail (no wrapper clobber).
CASE10="$TMPROOT/case10"
REPO10="$CASE10/repo"
SCRIPTS10="$CASE10/scripts"
SESSION10="$CASE10/session"
CHECKS10="$CASE10/checks.log"
WRAPPER10="$CASE10/wrapper.sh"
make_repo "$REPO10"
make_fixture_scripts "$SCRIPTS10"
make_session "$SESSION10"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$SESSION10/session-env.sh"
export LARCH_CURSOR_MODEL=stub-cursor-model
printf 'synthetic checks failure\n' > "$CHECKS10"
write_wrapper_cursor_fail_preserve_tail "$WRAPPER10"

case10_result=$(LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux CURSOR_API_KEY='' \
    run_case "$SCRIPTS10" "$REPO10" "$SESSION10" "$CHECKS10" "$WRAPPER10")
case10_rc=$(printf '%s\n' "$case10_result" | sed -n '1p')
case10_out=$(printf '%s\n' "$case10_result" | sed -n '2,$p')
[[ "$case10_rc" == "0" ]] || fail "case10 expected rc 0, got $case10_rc"
assert_contains "$case10_out" 'LINT_FIX_STATUS=main-agent-required' "case10 status"
case10_run_dir=$(kv_value LINT_FIX_RUN_DIR "$case10_out")
case10_tail_stem=$(kv_value STDERR_TAIL_PATH "$case10_out")
[[ "$case10_tail_stem" == "$case10_run_dir/cursor.log" ]] \
    || fail "case10 expected STDERR_TAIL_PATH cursor.log stem, got $case10_tail_stem"
grep -Fq 'agent stderr from cursor agent' "$case10_run_dir/cursor.log.stderr-tail" \
    || fail "case10 stderr-tail must retain agent stderr"
grep -Fq 'wrapper progress noise' "$case10_run_dir/cursor.log.stderr-tail" \
    && fail "case10 stderr-tail must not contain wrapper progress text"

echo "test-lint-fix-loop: ok"
