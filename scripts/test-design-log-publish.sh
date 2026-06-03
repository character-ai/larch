#!/usr/bin/env bash
# test-design-log-publish.sh — offline harness for design-log-publish.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PUBLISH="$REPO_ROOT/scripts/design-log-publish.sh"

[[ -x "$PUBLISH" ]] || {
    echo "FAIL: $PUBLISH not executable" >&2
    exit 1
}

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

make_gh_stub() {
    local d="$1"
    mkdir -p "$d"
    cat >"$d/gh" <<'STUB'
#!/usr/bin/env bash
if [[ -n "${GH_STUB_LOG:-}" ]]; then
    printf '%s\n' "$*" >>"$GH_STUB_LOG"
fi

has_arg() {
    needle="$1"
    shift
    for arg in "$@"; do
        [[ "$arg" == "$needle" ]] && return 0
    done
    return 1
}

arg_after() {
    needle="$1"
    shift
    prev=""
    for arg in "$@"; do
        if [[ "$prev" == "$needle" ]]; then
            printf '%s\n' "$arg"
            return 0
        fi
        prev="$arg"
    done
    return 1
}

resolve_pr_head_oid() {
    if [[ -n "${GH_STUB_PR_HEAD_OID:-}" ]]; then
        printf '%s\n' "$GH_STUB_PR_HEAD_OID"
        return 0
    fi
    branch="${TEST_MERGE_BRANCH:-}"
    if [[ -z "$branch" && -n "${GH_STUB_LOG:-}" && -f "$GH_STUB_LOG" ]]; then
        branch=$(awk '/pr create/ { for (i = 1; i <= NF; i++) if ($i == "--head") h = $(i + 1) } END { print h }' "$GH_STUB_LOG")
    fi
    if [[ -z "${TEST_CLONE_ROOT:-}" || -z "$branch" ]]; then
        echo "stub pr view headRefOid missing TEST_CLONE_ROOT or branch" >&2
        exit 98
    fi
    oid=$(git -C "$TEST_CLONE_ROOT" ls-remote origin "$branch" | awk '{ print $1; exit }')
    if [[ -z "$oid" ]]; then
        echo "stub pr view headRefOid could not resolve $branch" >&2
        exit 98
    fi
    printf '%s\n' "$oid"
}

if [[ "$1" == "repo" ]] && [[ "$2" == "view" ]]; then
    printf '{"nameWithOwner":"owner/repo"}\n'
    exit 0
fi
if [[ "$1" == "pr" ]]; then
    case "$2" in
        create)
            if [[ -n "${GH_STUB_CREATE_FAIL_COUNT:-}" && -n "${GH_STUB_CREATE_COUNT_FILE:-}" ]]; then
                create_count=$(( $(cat "${GH_STUB_CREATE_COUNT_FILE}" 2>/dev/null || echo 0) + 1 ))
                printf '%s\n' "$create_count" > "${GH_STUB_CREATE_COUNT_FILE}"
                if [[ "$create_count" -le "${GH_STUB_CREATE_FAIL_COUNT}" ]]; then
                    echo "Could not resolve host: api.github.com" >&2
                    exit 1
                fi
            fi
            body_file=""
            prev=""
            for arg in "$@"; do
                if [[ "$arg" == "--body" ]]; then
                    echo "stub pr create received forbidden --body" >&2
                    exit 98
                fi
                if [[ "$prev" == "--body-file" ]]; then
                    body_file="$arg"
                    prev=""
                    continue
                fi
                if [[ "$arg" == "--body-file" ]]; then
                    prev="--body-file"
                fi
            done
            if [[ -z "$body_file" ]]; then
                echo "stub pr create missing --body-file" >&2
                exit 98
            fi
            if [[ -n "${GH_STUB_EXPECT_PR_BODY_FILE:-}" ]]; then
                if ! cmp -s "$GH_STUB_EXPECT_PR_BODY_FILE" "$body_file"; then
                    echo "stub pr create body-file payload mismatch" >&2
                    exit 98
                fi
            fi
            if [[ -n "${GH_STUB_CREATE_RC:-}" && "${GH_STUB_CREATE_RC}" != "0" ]]; then
                echo "stub pr create failed" >&2
                exit "${GH_STUB_CREATE_RC}"
            fi
            if [[ "${GH_STUB_CREATE_NO_URL:-}" == "1" ]]; then
                echo "PR created (no URL line in stub output)"
                exit 0
            fi
            echo "https://github.com/owner/repo/pull/101"
            exit 0
            ;;
        checks)
            if has_arg --json "$@"; then
                count_file="${GH_STUB_CHECKS_JSON_COUNT_FILE:-}"
                if [[ -z "$count_file" && -n "${GH_STUB_LOG:-}" ]]; then
                    count_file="${GH_STUB_LOG}.checks-json-count"
                fi
                checks_probe=1
                if [[ -n "$count_file" ]]; then
                    checks_probe=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
                    printf '%s\n' "$checks_probe" >"$count_file"
                fi
                checks_knob_probe=1
                if [[ -n "${GH_STUB_CHECKS_JSON_EMPTY_FIRST:-}" ]]; then
                    knob_count_file="${GH_STUB_CHECKS_JSON_COUNT_FILE:-${GH_STUB_LOG:-}.checks-json-knob-count}"
                    if [[ -n "$knob_count_file" ]]; then
                        checks_knob_probe=$(( $(cat "$knob_count_file" 2>/dev/null || echo 0) + 1 ))
                        printf '%s\n' "$checks_knob_probe" >"$knob_count_file"
                    fi
                fi
                if [[ "${GH_STUB_CHECKS_JSON_ALWAYS_EMPTY:-0}" == "1" ]]; then
                    printf '[]\n'
                    exit "${GH_STUB_CHECKS_JSON_RC:-0}"
                fi
                if [[ -n "${GH_STUB_CHECKS_JSON_EMPTY_FIRST:-}" && "$checks_knob_probe" -le "$GH_STUB_CHECKS_JSON_EMPTY_FIRST" ]]; then
                    printf '[]\n'
                    exit "${GH_STUB_CHECKS_JSON_RC:-0}"
                fi
                if [[ -n "${GH_STUB_CHECKS_JSON_OUT:-}" ]]; then
                    printf '%s\n' "$GH_STUB_CHECKS_JSON_OUT"
                else
                    printf '[{"name":"ci","bucket":"pass"}]\n'
                fi
                exit "${GH_STUB_CHECKS_JSON_RC:-0}"
            fi
            if has_arg --watch "$@" && has_arg --fail-fast "$@"; then
                if [[ -n "${GH_STUB_CHECKS_RC:-}" && "${GH_STUB_CHECKS_RC}" != "0" ]]; then
                    echo "${GH_STUB_CHECKS_OUT:-some required checks failed}"
                    exit "${GH_STUB_CHECKS_RC}"
                fi
                echo "${GH_STUB_CHECKS_OUT:-all checks passing}"
                exit 0
            fi
            echo "STUB ERROR: unhandled pr checks $*" >&2
            exit 99
            ;;
        merge)
            if [[ -n "${GH_STUB_MERGE_RC:-}" && "${GH_STUB_MERGE_RC}" != "0" ]]; then
                exit "${GH_STUB_MERGE_RC}"
            fi
            if [[ -n "${TEST_CLONE_ROOT:-}" && -n "${TEST_MERGE_BRANCH:-}" ]]; then
                git -C "$TEST_CLONE_ROOT" fetch origin "$TEST_MERGE_BRANCH" >/dev/null 2>&1 || true
                git -C "$TEST_CLONE_ROOT" merge FETCH_HEAD -m "test merge design log" >/dev/null 2>&1 || true
                git -C "$TEST_CLONE_ROOT" push origin main >/dev/null 2>&1 || true
            fi
            exit 0
            ;;
        view)
            if [[ -n "${GH_STUB_PR_VIEW_RC:-}" && "${GH_STUB_PR_VIEW_RC}" != "0" ]]; then
                echo "Could not resolve host: api.github.com" >&2
                exit "${GH_STUB_PR_VIEW_RC}"
            fi
            json_fields=$(arg_after --json "$@" || true)
            case "$json_fields" in
                *headRefOid*)
                    head_count_file="${GH_STUB_PR_HEAD_OID_COUNT_FILE:-}"
                    if [[ -z "$head_count_file" && -n "${GH_STUB_LOG:-}" ]]; then
                        head_count_file="${GH_STUB_LOG}.head-count"
                    fi
                    head_probe=1
                    if [[ -n "$head_count_file" ]]; then
                        head_probe=$(( $(cat "$head_count_file" 2>/dev/null || echo 0) + 1 ))
                        printf '%s\n' "$head_probe" >"$head_count_file"
                    fi
                    head_knob_probe=1
                    if [[ -n "${GH_STUB_PR_HEAD_OID_MISMATCH_FIRST:-}" ]]; then
                        head_knob_count_file="${GH_STUB_PR_HEAD_OID_COUNT_FILE:-${GH_STUB_LOG:-}.head-knob-count}"
                        if [[ -n "$head_knob_count_file" ]]; then
                            head_knob_probe=$(( $(cat "$head_knob_count_file" 2>/dev/null || echo 0) + 1 ))
                            printf '%s\n' "$head_knob_probe" >"$head_knob_count_file"
                        fi
                    fi
                    if [[ "${GH_STUB_PR_HEAD_OID_MISMATCH:-0}" == "1" ]]; then
                        oid="0000000000000000000000000000000000000000"
                    elif [[ -n "${GH_STUB_PR_HEAD_OID_MISMATCH_FIRST:-}" && "$head_knob_probe" -le "$GH_STUB_PR_HEAD_OID_MISMATCH_FIRST" ]]; then
                        oid="0000000000000000000000000000000000000000"
                    else
                        oid=$(resolve_pr_head_oid)
                    fi
                    printf '{"headRefOid":"%s"}\n' "$oid"
                    exit 0
                    ;;
            esac
            echo '{"url":"https://github.com/owner/repo/pull/101"}'
            exit 0
            ;;
        list)
            if [[ -n "${GH_STUB_PR_LIST_RC:-}" && "${GH_STUB_PR_LIST_RC}" != "0" ]]; then
                echo "Could not resolve host: api.github.com" >&2
                exit "${GH_STUB_PR_LIST_RC}"
            fi
            if [[ "${GH_STUB_PR_LIST_EMPTY:-}" == "1" ]]; then
                if printf '%s\n' "$*" | grep -q -- '--jq'; then
                    echo 'null'
                else
                    echo '[]'
                fi
                exit 0
            fi
            if printf '%s\n' "$*" | grep -q -- '--jq'; then
                echo '101'
            else
                echo '[{"number":101}]'
            fi
            exit 0
            ;;
    esac
fi
echo "STUB ERROR: unhandled gh $*" >&2
exit 99
STUB
    chmod +x "$d/gh"
}

make_sleep_stub() {
    local d="$1"
    mkdir -p "$d"
    cat >"$d/sleep-seconds.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
    chmod +x "$d/sleep-seconds.sh"
}

make_find_escape_stub() {
    local d="$1" real_find="$2"
    mkdir -p "$d"
    cat >"$d/find" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == "\${ESCAPE_FIND_ROOT:-}" && "\${2:-}" == "-type" && "\${3:-}" == "f" ]]; then
    printf '%s\n' "\${ESCAPE_FIND_PATH:?}"
    exit 0
fi
exec "$real_find" "\$@"
EOF
    chmod +x "$d/find"
}

make_find_symlink_race_stub() {
    local d="$1" real_find="$2"
    mkdir -p "$d"
    cat >"$d/find" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == "\${RACE_FIND_ROOT:-}" && "\${2:-}" == "-type" && "\${3:-}" == "f" ]]; then
    printf '%s\n' "\${RACE_FIND_PATH:?}"
    rm -f "\${RACE_FIND_PATH:?}"
    ln -s "\${RACE_FIND_TARGET:?}" "\${RACE_FIND_PATH:?}"
    exit 0
fi
exec "$real_find" "\$@"
EOF
    chmod +x "$d/find"
}

make_find_ancestor_race_stub() {
    local d="$1" real_find="$2"
    mkdir -p "$d"
    cat >"$d/find" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == "\${ANCESTOR_RACE_FIND_ROOT:-}" && "\${2:-}" == "-type" && "\${3:-}" == "f" ]]; then
    rm -rf "\${ANCESTOR_RACE_PARENT:?}"
    ln -s "\${ANCESTOR_RACE_TARGET:?}" "\${ANCESTOR_RACE_PARENT:?}"
    printf '%s\n' "\${ANCESTOR_RACE_PATH:?}"
    exit 0
fi
exec "$real_find" "\$@"
EOF
    chmod +x "$d/find"
}

setup_clone_with_origin_head() {
    local root="$1"
    local bare="$root/upstream.git"
    local clone="$root/consumer"
    rm -rf "$bare" "$clone"
    mkdir -p "$bare"
    git init -q --bare "$bare"
    git clone -q "$bare" "$clone"
    git -C "$clone" config user.email "t@t"
    git -C "$clone" config user.name "t"
    printf 'init\n' >"$clone/README.md"
    git -C "$clone" add README.md
    git -C "$clone" commit -q -m "init"
    git -C "$clone" branch -M main
    git -C "$clone" push -q -u origin main
    git -C "$clone" remote set-head origin main
    printf '%s\n' "$clone"
}

expected_registration_probes() {
    local timeout interval
    timeout=$(awk -F= '$1=="REG_TIMEOUT"{gsub(/[^0-9]/, "", $2); print $2; exit}' "$PUBLISH")
    interval=$(awk -F= '$1=="REG_INTERVAL"{gsub(/[^0-9]/, "", $2); print $2; exit}' "$PUBLISH")
    [[ -n "$timeout" && -n "$interval" && "$interval" -gt 0 ]] || fail "could not derive registration probe count"
    printf '%s\n' $(( (timeout + interval - 1) / interval + 1 ))
}

echo "=== dry-run preflight inside git worktree ==="
DRYROOT=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-dry.XXXXXX")
GLOBAL_SLEEP_STUB="$DRYROOT/sleep-stub"
make_sleep_stub "$GLOBAL_SLEEP_STUB"
export SLEEP_SCRIPT_DIR="$GLOBAL_SLEEP_STUB"
trap 'rm -rf "$DRYROOT"' EXIT
DRYCLONE=$(setup_clone_with_origin_head "$DRYROOT")
STUBDR="$DRYROOT/minigh"
mkdir -p "$STUBDR"
cat >"$STUBDR/gh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$STUBDR/gh"
mkdir -p "$DRYROOT/design"
printf 'x\n' >"$DRYROOT/design/a.txt"
out=$(
    cd "$DRYCLONE" && PATH="$STUBDR:$PATH" bash "$PUBLISH" --design-tmpdir "$DRYROOT/design" --run-id "RUN1AB" --issue 9 --dry-run
)
[[ "$out" == *"PUBLISH_OK=true"* ]] || fail "dry-run missing PUBLISH_OK=true: $out"

echo "=== invalid issue 0 ==="
set +e
out=$(
    (cd "$DRYCLONE" && PATH="$STUBDR:$PATH" bash "$PUBLISH" --design-tmpdir "$DRYROOT/design" --run-id "RUN1AB" --issue 0 --dry-run) 2>/dev/null
)
rc_issue0=$?
set -e
[[ "$out" == *"PUBLISH_OK=false"* ]] || fail "issue 0 should fail: $out"
[[ "$rc_issue0" -eq 0 ]] || fail "pre-validation issue 0 should exit 0 (got $rc_issue0)"

echo "=== invalid run-id ==="
out=$(
    (cd "$DRYCLONE" && PATH="$STUBDR:$PATH" bash "$PUBLISH" --design-tmpdir "$DRYROOT/design" --run-id '../bad' --issue 9) 2>/dev/null || true
)
[[ "$out" == *"PUBLISH_OK=false"* ]] || fail "bad slug should fail: $out"

echo "=== jq required for non-dry-run ==="
JQTEST=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-jq.XXXXXX")
trap 'rm -rf "$DRYROOT" "$JQTEST"' EXIT
clone_j=$(setup_clone_with_origin_head "$JQTEST")
stub_j="$JQTEST/stub"
mkdir -p "$stub_j"
cat >"$stub_j/gh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_j/gh"
cat >"$stub_j/jq" <<'EOF'
#!/usr/bin/env bash
exit 127
EOF
chmod +x "$stub_j/jq"
GH_STUB_LOG="$JQTEST/gh.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
mkdir -p "$JQTEST/design"
printf 'a\n' >"$JQTEST/design/f.txt"
out_j=$(
    (cd "$clone_j" && PATH="$stub_j:$PATH" GH_STUB_LOG="$GH_STUB_LOG" bash "$PUBLISH" --design-tmpdir "$JQTEST/design" --run-id "RUNJQ1" --issue 1 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_j" == *"PUBLISH_OK=false"* ]] || fail "broken jq stub should fail publish: $out_j"

echo "=== happy path + sidecar trim + render-cache + suffix deny-list ==="
TMP=$(mktemp -d "${TMPDIR:-/tmp}/tdlp.XXXXXX")
trap 'rm -rf "$DRYROOT" "$JQTEST" "$TMP"' EXIT
clone=$(setup_clone_with_origin_head "$TMP")
stub="$TMP/stub"
GH_STUB_LOG="$TMP/gh.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub"
export PATH="$stub:$PATH"
export TEST_CLONE_ROOT="$clone"
export TEST_MERGE_BRANCH="larch-log-design-RUNPUB1"
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
GH_STUB_EXPECT_PR_BODY_FILE="$TMP/expected-pr-body.txt"
printf 'Automated design log directory for run RUNPUB1. Merged once required CI checks pass.' >"$GH_STUB_EXPECT_PR_BODY_FILE"
export GH_STUB_EXPECT_PR_BODY_FILE

mkdir -p "$TMP/design/render-cache/nested" "$TMP/design/plan-review/round-1"
printf 'body\n' >"$TMP/design/plan.txt"
printf 'CMD_JSON=["secret"]\nkeep\n' >"$TMP/design/out.txt.meta"
printf '{"ok":1,"result":{"token":"x"}}\n' >"$TMP/design/voter-output-1.json"
printf '{"x":1,"result":{"y":2}}\n' >"$TMP/design/plain.json"
printf 'deep\n' >"$TMP/design/render-cache/nested/c.txt"
printf 'finding_id\tfinding_reviewers\tvoting_result\n' >"$TMP/design/plan-review/round-1/findings-classification.tsv"
printf '### FINDING_1:\n' >"$TMP/design/plan-review/round-1/findings.md"
mkdir -p "$TMP/design/plan-review/round-1/revise"
printf 'prompt\n' >"$TMP/design/plan-review/round-1/revise/prompt.txt"
printf 'patch\n' >"$TMP/design/plan-review/round-1/revise/codex-output-candidate.patch"
# Files that MUST be denied by the suffix deny-list (mirrors /implement's
# round_artifact_included deny patterns):
printf 'noisy raw transcript\n' >"$TMP/design/codex-plan-arch-output.txt.sidecar"
printf 'STATUS=clean\n' >"$TMP/design/codex-plan-arch-output.txt.dirty-tree"
: >"$TMP/design/codex-plan-arch-output.txt.untracked-baseline"
printf 'OK\n' >"$TMP/design/codex-plan-arch-output.txt.done"
: >"$TMP/design/cursor-plan-arch-output.txt.diag"
printf 'launcher prompt body\n' >"$TMP/design/codex-plan-arch-output.txt.prompt"
printf 'phased launcher prompt\n' >"$TMP/design/codex-plan-arch-output-phase2.txt.prompt"
printf '{"type":"token_usage","input_tokens":1,"cached_input_tokens":0,"output_tokens":1}\n' >"$TMP/design/codex-plan-arch-output.txt.events.jsonl"
# Same suffix family in render-cache must also be denied:
printf 'rc noisy\n' >"$TMP/design/render-cache/cached-output.txt.sidecar"
printf '{"type":"token_usage","input_tokens":2,"cached_input_tokens":0,"output_tokens":1}\n' >"$TMP/design/render-cache/cached-output.txt.events.jsonl"

(
    cd "$clone" || exit 1
    out=$(bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNPUB1" --issue 42 --repo owner/repo)
    [[ "$out" == *"PUBLISH_OK=true"* ]] || fail "happy PUBLISH_OK: $out"
    [[ "$out" == *"PR_NUMBER=101"* ]] || fail "happy PR_NUMBER: $out"
)

git -C "$clone" pull -q origin main
[[ -f "$clone/larch-logs/design/RUNPUB1/plan.txt" ]] || fail "plan.txt missing on main"
[[ -f "$clone/larch-logs/design/RUNPUB1/render-cache/nested/c.txt" ]] || fail "render-cache nested missing"
[[ -f "$clone/larch-logs/design/RUNPUB1/plan-review/round-1/findings-classification.tsv" ]] || fail "plan-review classification TSV missing"
[[ -f "$clone/larch-logs/design/RUNPUB1/plan-review/round-1/findings.md" ]] || fail "plan-review findings.md missing"
[[ -f "$clone/larch-logs/design/RUNPUB1/plan-review/round-1/revise/prompt.txt" ]] || fail "plan-review revise prompt.txt missing"
[[ -f "$clone/larch-logs/design/RUNPUB1/plan-review/round-1/revise/codex-output-candidate.patch" ]] || fail "plan-review revise candidate patch missing"
grep -q '^keep$' "$clone/larch-logs/design/RUNPUB1/out.txt.meta" || fail "meta trim failed"
! grep -q CMD_JSON "$clone/larch-logs/design/RUNPUB1/out.txt.meta" || fail "CMD_JSON should be stripped"
! grep -q '"result"' "$clone/larch-logs/design/RUNPUB1/voter-output-1.json" || fail ".result should be stripped from *-output*.json"
grep -q '"result"' "$clone/larch-logs/design/RUNPUB1/plain.json" || fail "plain.json should retain .result (not *-output*.json)"
grep -qE '"ok"[[:space:]]*:[[:space:]]*1' "$clone/larch-logs/design/RUNPUB1/voter-output-1.json" || fail "json body missing"
grep -q 'pr create' "$GH_STUB_LOG" || fail "expected gh pr create in log"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "expected gh pr merge in log"
grep -q 'pr checks' "$GH_STUB_LOG" || fail "expected gh pr checks (required CI wait) before merge"
grep -Fq -- '--admin' "$GH_STUB_LOG" || fail "expected gh pr merge --admin in log"
! grep -Fq -- '--auto' "$GH_STUB_LOG" || fail "gh pr merge must not use --auto (review gate would never complete it)"
grep -Fq -- '--body-file' "$GH_STUB_LOG" || fail "expected gh pr create --body-file in log"
! grep -Eq '(^| )--body( |$)' "$GH_STUB_LOG" || fail "gh pr create should not use inline --body" # lint-gh-body-inline: ok gh-stub assertion fixture
unset GH_STUB_EXPECT_PR_BODY_FILE
# Verify suffix deny-list dropped each denied basename at both top-level and render-cache:
for denied in \
    "codex-plan-arch-output.txt.sidecar" \
    "codex-plan-arch-output.txt.dirty-tree" \
    "codex-plan-arch-output.txt.untracked-baseline" \
    "codex-plan-arch-output.txt.done" \
    "cursor-plan-arch-output.txt.diag" \
    "codex-plan-arch-output.txt.events.jsonl" \
    "codex-plan-arch-output.txt.prompt" \
    "codex-plan-arch-output-phase2.txt.prompt"; do
    [[ ! -f "$clone/larch-logs/design/RUNPUB1/$denied" ]] || fail "denied basename leaked into top-level: $denied"
done
[[ ! -f "$clone/larch-logs/design/RUNPUB1/render-cache/cached-output.txt.sidecar" ]] || fail "denied basename leaked into render-cache"
[[ ! -f "$clone/larch-logs/design/RUNPUB1/render-cache/cached-output.txt.events.jsonl" ]] || fail "denied events basename leaked into render-cache"

echo "=== revise allowlist rejects unexpected file under round-N/revise ==="
printf 'nope\n' >"$TMP/design/plan-review/round-1/revise/extra.log"
out_revise_bad=$(
    (cd "$clone" && bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNPUBREV1" --issue 42 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_revise_bad" == *"PUBLISH_OK=false"* ]] || fail "unexpected revise file should fail publish"
git -C "$clone" branch -D larch-log-design-RUNPUBREV1 >/dev/null 2>&1 || true
rm -f "$TMP/design/plan-review/round-1/revise/extra.log"

echo "=== pause reason stages .completed and manifest paused ==="
TMPPAUSE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pause.XXXXXX")
clone_pause=$(setup_clone_with_origin_head "$TMPPAUSE")
stub_pause="$TMPPAUSE/stub"
make_gh_stub "$stub_pause"
export PATH="$stub_pause:$PATH"
export TEST_CLONE_ROOT="$clone_pause"
export TEST_MERGE_BRANCH="larch-log-design-RUNPAUSE1"
unset GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPAUSE/design/.completed"
printf 'p\n' >"$TMPPAUSE/design/plan.txt"
printf 'done\n' >"$TMPPAUSE/design/.completed/step-1c"
(
    cd "$clone_pause" || exit 1
    out_pause=$(bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE/design" --run-id "RUNPAUSE1" --issue 42 --repo owner/repo)
    [[ "$out_pause" == *"PUBLISH_OK=true"* ]] || fail "pause PUBLISH_OK: $out_pause"
)
git -C "$clone_pause" pull -q origin main
[[ -f "$clone_pause/larch-logs/design/RUNPAUSE1/.completed/step-1c" ]] || fail "pause .completed sentinel missing"
jq -e '.paused == true' "$clone_pause/larch-logs/design/RUNPAUSE1/manifest.json" >/dev/null || fail "pause manifest missing paused=true"
git -C "$clone_pause" fetch -q origin larch-log-design-RUNPAUSE1:larch-log-design-RUNPAUSE1
pause_subject=$(git -C "$clone_pause" log -1 --format=%s larch-log-design-RUNPAUSE1)
[[ "$pause_subject" == "chore(larch-logs): pause design run RUNPAUSE1" ]] || fail "pause commit subject mismatch: $pause_subject"

echo "=== pause publish accepts no-op when default branch already has snapshot ==="
TMPPAUSE_NOOP=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pause-noop.XXXXXX")
clone_pause_noop=$(setup_clone_with_origin_head "$TMPPAUSE_NOOP")
stub_pause_noop="$TMPPAUSE_NOOP/stub"
make_gh_stub "$stub_pause_noop"
date_stub="$TMPPAUSE_NOOP/date-stub"
mkdir -p "$date_stub"
cat >"$date_stub/date" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-u" && "${2:-}" == "+%Y-%m-%dT%H:%M:%SZ" ]]; then
    printf '%s\n' '2026-01-01T00:00:00Z'
    exit 0
fi
exec /bin/date "$@"
EOF
chmod +x "$date_stub/date"
export PATH="$date_stub:$stub_pause_noop:$PATH"
export TEST_CLONE_ROOT="$clone_pause_noop"
export TEST_MERGE_BRANCH="larch-log-design-RUNPAUSENOOP1"
unset GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPAUSE_NOOP/design/.completed"
printf 'p\n' >"$TMPPAUSE_NOOP/design/plan.txt"
printf 'done\n' >"$TMPPAUSE_NOOP/design/.completed/step-1c"
(
    cd "$clone_pause_noop" || exit 1
    out_pause_seed=$(bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_NOOP/design" --run-id "RUNPAUSENOOP1" --issue 42 --repo owner/repo)
    [[ "$out_pause_seed" == *"PUBLISH_OK=true"* ]] || fail "pause seed publish failed: $out_pause_seed"
)
git -C "$clone_pause_noop" pull -q origin main
out_pause_noop=$(
    cd "$clone_pause_noop" && bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_NOOP/design" --run-id "RUNPAUSENOOP1" --issue 42 --repo owner/repo
)
[[ "$out_pause_noop" == *"PUBLISH_OK=false"* && "$out_pause_noop" == *"RECOVERY_BRANCH=larch-log-design-RUNPAUSENOOP1"* ]] \
  || fail "pause no-op snapshot should fail closed with recovery branch when no fresh snapshot exists: $out_pause_noop"

echo "=== pause no-op fails when recovery branch is newer than default ==="
(
    cd "$clone_pause_noop" || exit 1
    printf 'updated\n' >"$TMPPAUSE_NOOP/design/plan.txt"
    set +e
    out_pause_recovery_seed=$(GH_STUB_MERGE_RC=1 bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_NOOP/design" --run-id "RUNPAUSENOOP1" --issue 42 --repo owner/repo)
    rc_pause_recovery_seed=$?
    set -e
    [[ "$rc_pause_recovery_seed" -eq 1 ]] || fail "pause recovery seed should exit 1 on merge fail (got $rc_pause_recovery_seed)"
    [[ "$out_pause_recovery_seed" == *"PUBLISH_OK=false"* && "$out_pause_recovery_seed" == *"RECOVERY_BRANCH=larch-log-design-RUNPAUSENOOP1"* ]] || fail "pause recovery seed should preserve recovery branch: $out_pause_recovery_seed"
    git branch -D larch-log-design-RUNPAUSENOOP1 >/dev/null 2>&1 || true
    out_pause_stale_default=$(bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_NOOP/design" --run-id "RUNPAUSENOOP1" --issue 42 --repo owner/repo)
    [[ "$out_pause_stale_default" == *"PUBLISH_OK=false"* && "$out_pause_stale_default" == *"RECOVERY_BRANCH=larch-log-design-RUNPAUSENOOP1"* ]] || fail "pause no-op should not ignore ahead recovery branch: $out_pause_stale_default"
)

echo "=== pause publish reuses existing remote recovery branch on no-op ==="
TMPPAUSE_REC=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pause-recovery.XXXXXX")
clone_pause_rec=$(setup_clone_with_origin_head "$TMPPAUSE_REC")
stub_pause_rec="$TMPPAUSE_REC/stub"
make_gh_stub "$stub_pause_rec"
date_stub_rec="$TMPPAUSE_REC/date-stub"
mkdir -p "$date_stub_rec"
cat >"$date_stub_rec/date" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-u" && "${2:-}" == "+%Y-%m-%dT%H:%M:%SZ" ]]; then
    printf '%s\n' '2026-01-01T00:00:00Z'
    exit 0
fi
exec /bin/date "$@"
EOF
chmod +x "$date_stub_rec/date"
export PATH="$date_stub_rec:$stub_pause_rec:$PATH"
export TEST_CLONE_ROOT="$clone_pause_rec"
export TEST_MERGE_BRANCH="larch-log-design-RUNPAUSEREC1"
unset GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPAUSE_REC/design/.completed"
printf 'p\n' >"$TMPPAUSE_REC/design/plan.txt"
printf 'done\n' >"$TMPPAUSE_REC/design/.completed/step-1c"
(
    cd "$clone_pause_rec" || exit 1
    set +e
    seed_out=$(GH_STUB_MERGE_RC=1 bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_REC/design" --run-id "RUNPAUSEREC1" --issue 42 --repo owner/repo)
    rc_seed_out=$?
    set -e
    [[ "$rc_seed_out" -eq 1 ]] || fail "pause recovery seed should exit 1 on merge fail (got $rc_seed_out)"
    [[ "$seed_out" == *"PUBLISH_OK=false"* && "$seed_out" == *"RECOVERY_BRANCH=larch-log-design-RUNPAUSEREC1"* ]] || fail "pause recovery seed should leave remote branch: $seed_out"
    git branch -D larch-log-design-RUNPAUSEREC1 >/dev/null 2>&1 || true
    out_pause_rec=$(bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_REC/design" --run-id "RUNPAUSEREC1" --issue 42 --repo owner/repo)
    [[ "$out_pause_rec" == *"PUBLISH_OK=false"* ]] || fail "pause recovery no-op should fail soft: $out_pause_rec"
    [[ "$out_pause_rec" == *"RECOVERY_BRANCH=larch-log-design-RUNPAUSEREC1"* ]] || fail "pause recovery no-op missing recovery branch: $out_pause_rec"
)

echo "=== pause publish reuses existing remote branch with force-with-lease ==="
TMPPAUSE_REUSE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pause-reuse.XXXXXX")
clone_pause_reuse=$(setup_clone_with_origin_head "$TMPPAUSE_REUSE")
stub_pause_reuse="$TMPPAUSE_REUSE/stub"
make_gh_stub "$stub_pause_reuse"
GH_STUB_LOG="$TMPPAUSE_REUSE/gh-pause-reuse.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
export PATH="$stub_pause_reuse:$PATH"
export TEST_CLONE_ROOT="$clone_pause_reuse"
export TEST_MERGE_BRANCH="larch-log-design-RUNPAUSEREUSE1"
unset GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPAUSE_REUSE/design/.completed"
printf 'first\n' >"$TMPPAUSE_REUSE/design/plan.txt"
printf 'done\n' >"$TMPPAUSE_REUSE/design/.completed/step-1c"
(
    cd "$clone_pause_reuse" || exit 1
    set +e
    seed_reuse=$(GH_STUB_MERGE_RC=1 bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_REUSE/design" --run-id "RUNPAUSEREUSE1" --issue 42 --repo owner/repo)
    rc_seed_reuse=$?
    set -e
    [[ "$rc_seed_reuse" -eq 1 ]] || fail "pause branch reuse seed should exit 1 on merge fail (got $rc_seed_reuse)"
    [[ "$seed_reuse" == *"PUBLISH_OK=false"* && "$seed_reuse" == *"RECOVERY_BRANCH=larch-log-design-RUNPAUSEREUSE1"* ]] || fail "pause branch reuse seed should leave remote branch: $seed_reuse"
    printf 'second\n' >"$TMPPAUSE_REUSE/design/plan.txt"
    reuse_out=$(GH_STUB_PR_HEAD_OID_MISMATCH_FIRST=1 bash "$PUBLISH" --reason pause --design-tmpdir "$TMPPAUSE_REUSE/design" --run-id "RUNPAUSEREUSE1" --issue 42 --repo owner/repo)
    [[ "$reuse_out" == *"PUBLISH_OK=true"* ]] || fail "pause branch reuse publish should succeed: $reuse_out"
    [[ "$(cat "$GH_STUB_LOG.head-knob-count")" == "2" ]] || fail "pause branch reuse should cover stale-head retry probes, got $(cat "$GH_STUB_LOG.head-knob-count" 2>/dev/null || echo missing)"
)
git -C "$clone_pause_reuse" pull -q origin main
grep -Fxq 'second' "$clone_pause_reuse/larch-logs/design/RUNPAUSEREUSE1/plan.txt" || fail "pause branch reuse should publish updated snapshot"

echo "=== pr create non-zero with pr list/view recovery (plan publish path) ==="
TMPCR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-createfail.XXXXXX")
clone_cr=$(setup_clone_with_origin_head "$TMPCR")
stub_cr="$TMPCR/stub"
GH_STUB_LOG_CR="$TMPCR/gh-createfail.log"
: >"$GH_STUB_LOG_CR"
export GH_STUB_LOG="$GH_STUB_LOG_CR"
make_gh_stub "$stub_cr"
export PATH="$stub_cr:$PATH"
export TEST_CLONE_ROOT="$clone_cr"
export TEST_MERGE_BRANCH="larch-log-design-RUNCREATE1"
export GH_STUB_CREATE_RC=1
unset GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPCR/design"
printf 'c\n' >"$TMPCR/design/c.txt"
set +e
out_cr=$(
    (cd "$clone_cr" && bash "$PUBLISH" --design-tmpdir "$TMPCR/design" --run-id "RUNCREATE1" --issue 11 --repo owner/repo) 2>/dev/null
)
rc_cr=$?
set -e
[[ "$rc_cr" -eq 0 ]] || fail "create-fail recovery must exit 0: rc=$rc_cr"
[[ "$out_cr" == *"PUBLISH_OK=true"* ]] || fail "create-fail recovery PUBLISH_OK: $out_cr"
[[ "$out_cr" == *"PR_NUMBER=101"* ]] || fail "create-fail recovery PR_NUMBER: $out_cr"
grep -q 'pr create' "$GH_STUB_LOG_CR" || fail "expected pr create attempt in log"
grep -q 'pr merge' "$GH_STUB_LOG_CR" || fail "expected pr merge after list recovery"
unset GH_STUB_CREATE_RC

echo "=== pr create succeeds after transient retries ==="
TMPCRT=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-create-transient.XXXXXX")
clone_crt=$(setup_clone_with_origin_head "$TMPCRT")
stub_crt="$TMPCRT/stub"
GH_STUB_LOG_CRT="$TMPCRT/gh-create-transient.log"
: >"$GH_STUB_LOG_CRT"
export GH_STUB_LOG="$GH_STUB_LOG_CRT"
make_gh_stub "$stub_crt"
export PATH="$stub_crt:$PATH"
export TEST_CLONE_ROOT="$clone_crt"
export TEST_MERGE_BRANCH="larch-log-design-RUNCREATETR1"
export GH_STUB_CREATE_FAIL_COUNT=2
export GH_STUB_CREATE_COUNT_FILE="$TMPCRT/create-count"
mkdir -p "$TMPCRT/design"
printf 'crt\n' >"$TMPCRT/design/c.txt"
out_crt=$(
    cd "$clone_crt" && bash "$PUBLISH" --design-tmpdir "$TMPCRT/design" --run-id "RUNCREATETR1" --issue 15 --repo owner/repo
)
[[ "$out_crt" == *"PUBLISH_OK=true"* ]] || fail "create transient recovery PUBLISH_OK: $out_crt"
[[ "$(cat "$GH_STUB_CREATE_COUNT_FILE")" == "3" ]] || fail "create transient retry count mismatch: $(cat "$GH_STUB_CREATE_COUNT_FILE" 2>/dev/null || echo missing)"
unset GH_STUB_CREATE_FAIL_COUNT GH_STUB_CREATE_COUNT_FILE

wt_lines=$(git -C "$clone" worktree list | wc -l | tr -d ' ')
[[ "$wt_lines" == "1" ]] || fail "expected single worktree, got: $(git -C "$clone" worktree list)"
[[ $(git -C "$clone" branch --list 'larch-log-design-*' | wc -l | tr -d ' ') -eq 0 ]] || fail "unexpected local larch-log-design-* branch after publish"
[[ -z $(git -C "$clone" status --porcelain) ]] || fail "clone should be clean: $(git -C "$clone" status --porcelain)"

echo "=== pr create without URL falls back to pr list/view ==="
TMPU=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-url.XXXXXX")
clone_u=$(setup_clone_with_origin_head "$TMPU")
stub_u="$TMPU/stub"
make_gh_stub "$stub_u"
export PATH="$stub_u:$PATH"
export TEST_CLONE_ROOT="$clone_u"
export TEST_MERGE_BRANCH="larch-log-design-RUNURL1"
export GH_STUB_CREATE_NO_URL=1
unset GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPU/design"
printf 'z\n' >"$TMPU/design/p.txt"
(
    cd "$clone_u" || exit 1
    outu=$(bash "$PUBLISH" --design-tmpdir "$TMPU/design" --run-id "RUNURL1" --issue 7 --repo owner/repo)
    [[ "$outu" == *"PUBLISH_OK=true"* ]] || fail "fallback URL path PUBLISH_OK: $outu"
    [[ "$outu" == *"PR_NUMBER=101"* ]] || fail "fallback URL path PR_NUMBER: $outu"
)
unset GH_STUB_CREATE_NO_URL

echo "=== plan-review regular file is rejected ==="
TMPPR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-planreview-file.XXXXXX")
clone_pr=$(setup_clone_with_origin_head "$TMPPR")
stub_pr="$TMPPR/stub"
make_gh_stub "$stub_pr"
export PATH="$stub_pr:$PATH"
export TEST_CLONE_ROOT="$clone_pr"
export TEST_MERGE_BRANCH="larch-log-design-RUNPRFILE1"
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPPR/design"
printf 'p\n' >"$TMPPR/design/plan.txt"
printf 'not a directory\n' >"$TMPPR/design/plan-review"
out_pr=$(
    (cd "$clone_pr" && bash "$PUBLISH" --design-tmpdir "$TMPPR/design" --run-id "RUNPRFILE1" --issue 8 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pr" == *"PUBLISH_OK=false"* ]] || fail "plan-review regular file should fail publish: $out_pr"

echo "=== render-cache regular file is rejected ==="
TMPRC=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rendercache-file.XXXXXX")
clone_rc=$(setup_clone_with_origin_head "$TMPRC")
stub_rc="$TMPRC/stub"
make_gh_stub "$stub_rc"
export PATH="$stub_rc:$PATH"
export TEST_CLONE_ROOT="$clone_rc"
export TEST_MERGE_BRANCH="larch-log-design-RUNRCFILE1"
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPRC/design"
printf 'r\n' >"$TMPRC/design/plan.txt"
printf 'not a directory\n' >"$TMPRC/design/render-cache"
out_rc=$(
    (cd "$clone_rc" && bash "$PUBLISH" --design-tmpdir "$TMPRC/design" --run-id "RUNRCFILE1" --issue 9 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_rc" == *"PUBLISH_OK=false"* ]] || fail "render-cache regular file should fail publish: $out_rc"

echo "=== pr create failure after push exits 1 when list recovery fails ==="
TMPCF=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-createfail-hard.XXXXXX")
clone_cf=$(setup_clone_with_origin_head "$TMPCF")
stub_cf="$TMPCF/stub"
GH_STUB_LOG_CF="$TMPCF/gh-createfail-hard.log"
: >"$GH_STUB_LOG_CF"
export GH_STUB_LOG="$GH_STUB_LOG_CF"
make_gh_stub "$stub_cf"
export PATH="$stub_cf:$PATH"
export TEST_CLONE_ROOT="$clone_cf"
export TEST_MERGE_BRANCH="larch-log-design-RUNCREATEFAIL1"
export GH_STUB_CREATE_RC=1
export GH_STUB_PR_LIST_EMPTY=1
unset GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPCF/design"
printf 'cf\n' >"$TMPCF/design/cf.txt"
set +e
out_cf=$(
    (cd "$clone_cf" && bash "$PUBLISH" --design-tmpdir "$TMPCF/design" --run-id "RUNCREATEFAIL1" --issue 12 --repo owner/repo) 2>/dev/null
)
rc_cf=$?
set -e
[[ "$out_cf" == *"PUBLISH_OK=false"* ]] || fail "create-fail hard PUBLISH_OK: $out_cf"
[[ "$rc_cf" -eq 1 ]] || fail "create-fail after push should exit 1 (got $rc_cf)"
[[ "$out_cf" == *"RECOVERY_BRANCH=larch-log-design-RUNCREATEFAIL1"* ]] || fail "create-fail hard RECOVERY_BRANCH: $out_cf"
if git -C "$clone_cf" ls-remote --exit-code --heads origin larch-log-design-RUNCREATEFAIL1 >/dev/null 2>&1; then
    fail "create-fail hard path should delete remote branch after no-PR confirmation"
fi
unset GH_STUB_CREATE_RC GH_STUB_PR_LIST_EMPTY
rm -rf "$TMPCF"

echo "=== pr create failure preserves remote branch when list recovery probe fails transiently ==="
TMPCLF=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-createfail-listfail.XXXXXX")
clone_clf=$(setup_clone_with_origin_head "$TMPCLF")
stub_clf="$TMPCLF/stub"
GH_STUB_LOG_CLF="$TMPCLF/gh-createfail-listfail.log"
: >"$GH_STUB_LOG_CLF"
export GH_STUB_LOG="$GH_STUB_LOG_CLF"
make_gh_stub "$stub_clf"
export PATH="$stub_clf:$PATH"
export TEST_CLONE_ROOT="$clone_clf"
export TEST_MERGE_BRANCH="larch-log-design-RUNCREATEFAIL2"
export GH_STUB_CREATE_RC=1
export GH_STUB_PR_LIST_RC=1
unset GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC GH_STUB_PR_LIST_EMPTY GH_STUB_PR_VIEW_RC
mkdir -p "$TMPCLF/design"
printf 'clf\n' >"$TMPCLF/design/cf.txt"
set +e
out_clf=$(
    (cd "$clone_clf" && bash "$PUBLISH" --design-tmpdir "$TMPCLF/design" --run-id "RUNCREATEFAIL2" --issue 14 --repo owner/repo) 2>/dev/null
)
rc_clf=$?
set -e
[[ "$out_clf" == *"PUBLISH_OK=false"* ]] || fail "create-fail list-probe failure PUBLISH_OK: $out_clf"
[[ "$rc_clf" -eq 1 ]] || fail "create-fail list-probe failure should exit 1 (got $rc_clf)"
[[ "$out_clf" == *"RECOVERY_BRANCH=larch-log-design-RUNCREATEFAIL2"* ]] || fail "create-fail list-probe failure RECOVERY_BRANCH: $out_clf"
if ! git -C "$clone_clf" ls-remote --exit-code --heads origin larch-log-design-RUNCREATEFAIL2 >/dev/null 2>&1; then
    fail "create-fail list-probe failure should preserve remote branch after inconclusive recovery"
fi
unset GH_STUB_CREATE_RC GH_STUB_PR_LIST_RC
rm -rf "$TMPCLF"

echo "=== quiet logs excluded from top-level design artifacts ==="
TMPQL=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-quiet-excl.XXXXXX")
clone_ql=$(setup_clone_with_origin_head "$TMPQL")
stub_ql="$TMPQL/stub"
make_gh_stub "$stub_ql"
export PATH="$stub_ql:$PATH"
export TEST_CLONE_ROOT="$clone_ql"
export TEST_MERGE_BRANCH="larch-log-design-RUNQUIETEXCL1"
unset GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_MERGE_RC GH_STUB_PR_LIST_EMPTY
mkdir -p "$TMPQL/design/breadcrumbs"
printf 'top-level quiet must not duplicate\n' >"$TMPQL/design/larch-quiet-design-log-publish.sh-4242.log"
set +e
out_ql=$(
    (cd "$clone_ql" && bash "$PUBLISH" --design-tmpdir "$TMPQL/design" --run-id "RUNQUIETEXCL1" --issue 13 --repo owner/repo) 2>/dev/null
)
rc_ql=$?
set -e
[[ "$rc_ql" -eq 0 ]] || fail "quiet exclusion publish should exit 0 (got $rc_ql)"
[[ "$out_ql" == *"PUBLISH_OK=true"* ]] || fail "quiet exclusion PUBLISH_OK: $out_ql"
if [ -f "$clone_ql/larch-logs/design/RUNQUIETEXCL1/larch-quiet-design-log-publish.sh-4242.log" ]; then
    fail "quiet log must not appear as top-level design artifact"
fi
[ -f "$clone_ql/larch-logs/design/RUNQUIETEXCL1/breadcrumbs/larch-quiet-design-log-publish.sh-4242.log" ] \
    || fail "quiet log missing from breadcrumbs"
rm -rf "$TMPQL"

echo "=== merge failure preserves PR lines and RECOVERY_BRANCH ==="
TMPM=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-merge.XXXXXX")
clone_m=$(setup_clone_with_origin_head "$TMPM")
stub_m="$TMPM/stub"
GH_STUB_LOG="$TMPM/gh-merge.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_m"
export PATH="$stub_m:$PATH"
export TEST_CLONE_ROOT="$clone_m"
export TEST_MERGE_BRANCH="larch-log-design-RUNMERGE1"
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPM/design"
printf 'm\n' >"$TMPM/design/m.txt"
set +e
out_m=$(
    (cd "$clone_m" && GH_STUB_MERGE_RC=1 bash "$PUBLISH" --design-tmpdir "$TMPM/design" --run-id "RUNMERGE1" --issue 3 --repo owner/repo) 2>/dev/null
)
rc_m=$?
set -e
[[ "$out_m" == *"PUBLISH_OK=false"* ]] || fail "merge fail PUBLISH_OK: $out_m"
[[ "$rc_m" -eq 1 ]] || fail "merge fail should exit 1 (got $rc_m)"
[[ "$out_m" == *"PR_NUMBER=101"* ]] || fail "merge fail PR_NUMBER: $out_m"
[[ "$out_m" == *"RECOVERY_BRANCH=larch-log-design-RUNMERGE1"* ]] || fail "merge fail RECOVERY_BRANCH: $out_m"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "expected pr merge in stub log"

echo "=== required CI check failure refuses merge; preserves RECOVERY_BRANCH; no gh pr merge ==="
TMPCI=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-cifail.XXXXXX")
clone_ci=$(setup_clone_with_origin_head "$TMPCI")
stub_ci="$TMPCI/stub"
GH_STUB_LOG="$TMPCI/gh-cifail.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_ci"
export PATH="$stub_ci:$PATH"
export TEST_CLONE_ROOT="$clone_ci"
export TEST_MERGE_BRANCH="larch-log-design-RUNCIFAIL1"
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_EMPTY_FIRST
mkdir -p "$TMPCI/design"
printf 'c\n' >"$TMPCI/design/cifail.txt"
ci_stderr="$TMPCI/cifail.stderr"
set +e
out_ci=$(
    (cd "$clone_ci" && GH_STUB_CHECKS_RC=8 GH_STUB_CHECKS_OUT='required check failed' bash "$PUBLISH" --design-tmpdir "$TMPCI/design" --run-id "RUNCIFAIL1" --issue 7 --repo owner/repo) 2>"$ci_stderr"
)
rc_ci=$?
set -e
[[ "$out_ci" == *"PUBLISH_OK=false"* ]] || fail "ci fail PUBLISH_OK: $out_ci"
[[ "$rc_ci" -eq 1 ]] || fail "ci fail should exit 1 (got $rc_ci)"
[[ "$out_ci" == *"RECOVERY_BRANCH=larch-log-design-RUNCIFAIL1"* ]] || fail "ci fail RECOVERY_BRANCH: $out_ci"
grep -q 'required CI checks did not pass' "$ci_stderr" || fail "ci fail stderr missing did-not-pass diagnostic"
! grep -q 'did not register within' "$ci_stderr" || fail "ci fail stderr must not use registration-timeout wording"
grep -q 'pr checks' "$GH_STUB_LOG" || fail "expected pr checks in stub log"
grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "ci fail should invoke --watch"
! grep -q 'pr merge' "$GH_STUB_LOG" || fail "gh pr merge must NOT run when required CI checks fail"
rm -rf "$TMPCI"

echo "=== registration race waits for checks before watch/merge ==="
TMPREG=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-reg-race.XXXXXX")
clone_reg=$(setup_clone_with_origin_head "$TMPREG")
stub_reg="$TMPREG/stub"
GH_STUB_LOG="$TMPREG/gh-reg-race.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_reg"
make_sleep_stub "$TMPREG/sleep"
export PATH="$stub_reg:$PATH"
export SLEEP_SCRIPT_DIR="$TMPREG/sleep"
export TEST_CLONE_ROOT="$clone_reg"
export TEST_MERGE_BRANCH="larch-log-design-RUNREGRACE1"
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_PR_HEAD_OID_MISMATCH_FIRST GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
export GH_STUB_CHECKS_JSON_EMPTY_FIRST=2
mkdir -p "$TMPREG/design"
printf 'race\n' >"$TMPREG/design/race.txt"
out_reg=$(cd "$clone_reg" && bash "$PUBLISH" --design-tmpdir "$TMPREG/design" --run-id "RUNREGRACE1" --issue 21 --repo owner/repo)
[[ "$out_reg" == *"PUBLISH_OK=true"* ]] || fail "registration race PUBLISH_OK: $out_reg"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "registration race should merge"
grep -Fq -- '--admin' "$GH_STUB_LOG" || fail "registration race merge should keep --admin"
grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "registration race should invoke --watch after registration"
[[ "$(cat "$GH_STUB_LOG.checks-json-count")" == "3" ]] || fail "registration race probe count mismatch: $(cat "$GH_STUB_LOG.checks-json-count" 2>/dev/null || echo missing)"
unset GH_STUB_CHECKS_JSON_EMPTY_FIRST
rm -rf "$TMPREG"

echo "=== required checks never register skips watch and merge ==="
TMPNOREG=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-no-reg.XXXXXX")
clone_noreg=$(setup_clone_with_origin_head "$TMPNOREG")
stub_noreg="$TMPNOREG/stub"
GH_STUB_LOG="$TMPNOREG/gh-no-reg.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_noreg"
make_sleep_stub "$TMPNOREG/sleep"
export PATH="$stub_noreg:$PATH"
export SLEEP_SCRIPT_DIR="$TMPNOREG/sleep"
export TEST_CLONE_ROOT="$clone_noreg"
export TEST_MERGE_BRANCH="larch-log-design-RUNNOREG1"
export GH_STUB_CHECKS_JSON_ALWAYS_EMPTY=1
unset GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_PR_HEAD_OID_MISMATCH_FIRST GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPNOREG/design"
printf 'never\n' >"$TMPNOREG/design/never.txt"
noreg_stderr="$TMPNOREG/no-reg.stderr"
set +e
out_noreg=$(
    (cd "$clone_noreg" && bash "$PUBLISH" --design-tmpdir "$TMPNOREG/design" --run-id "RUNNOREG1" --issue 22 --repo owner/repo) 2>"$noreg_stderr"
)
rc_noreg=$?
set -e
[[ "$out_noreg" == *"PUBLISH_OK=false"* ]] || fail "never-registered PUBLISH_OK: $out_noreg"
[[ "$rc_noreg" -eq 1 ]] || fail "never-registered should exit 1 (got $rc_noreg)"
grep -q 'did not register within' "$noreg_stderr" || fail "never-registered stderr missing registration-timeout"
expected_probes=$(expected_registration_probes)
[[ "$(cat "$GH_STUB_LOG.checks-json-count")" == "$expected_probes" ]] || fail "never-registered should exhaust $expected_probes probes, got $(cat "$GH_STUB_LOG.checks-json-count" 2>/dev/null || echo missing)"
grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--json' || fail "never-registered should run json probes"
! grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "never-registered must not invoke --watch"
! grep -q 'pr merge' "$GH_STUB_LOG" || fail "never-registered must not merge"
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY
rm -rf "$TMPNOREG"

echo "=== registration probe fails fast on non-array JSON ==="
TMPREGOBJ=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-reg-object.XXXXXX")
clone_regobj=$(setup_clone_with_origin_head "$TMPREGOBJ")
stub_regobj="$TMPREGOBJ/stub"
GH_STUB_LOG="$TMPREGOBJ/gh-reg-object.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_regobj"
make_sleep_stub "$TMPREGOBJ/sleep"
export PATH="$stub_regobj:$PATH"
export SLEEP_SCRIPT_DIR="$TMPREGOBJ/sleep"
export TEST_CLONE_ROOT="$clone_regobj"
export TEST_MERGE_BRANCH="larch-log-design-RUNREGOBJ1"
export GH_STUB_CHECKS_JSON_OUT='{"message":"rate limited"}'
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_EMPTY_FIRST GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_PR_HEAD_OID_MISMATCH_FIRST GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPREGOBJ/design"
printf 'object\n' >"$TMPREGOBJ/design/object.txt"
regobj_stderr="$TMPREGOBJ/reg-object.stderr"
set +e
out_regobj=$(
    (cd "$clone_regobj" && bash "$PUBLISH" --design-tmpdir "$TMPREGOBJ/design" --run-id "RUNREGOBJ1" --issue 26 --repo owner/repo) 2>"$regobj_stderr"
)
rc_regobj=$?
set -e
[[ "$out_regobj" == *"PUBLISH_OK=false"* ]] || fail "non-array registration PUBLISH_OK: $out_regobj"
[[ "$rc_regobj" -eq 1 ]] || fail "non-array registration should exit 1 (got $rc_regobj)"
grep -q 'non-array JSON' "$regobj_stderr" || fail "non-array registration stderr missing diagnostic"
[[ "$(cat "$GH_STUB_LOG.checks-json-count")" == "1" ]] || fail "non-array registration should fail after one probe"
! grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "non-array registration must not invoke --watch"
! grep -q 'pr merge' "$GH_STUB_LOG" || fail "non-array registration must not merge"
unset GH_STUB_CHECKS_JSON_OUT
rm -rf "$TMPREGOBJ"

echo "=== registration probe accepts non-zero rc with pending JSON ==="
TMPREGRC=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-reg-rc.XXXXXX")
clone_regrc=$(setup_clone_with_origin_head "$TMPREGRC")
stub_regrc="$TMPREGRC/stub"
GH_STUB_LOG="$TMPREGRC/gh-reg-rc.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_regrc"
export PATH="$stub_regrc:$PATH"
export TEST_CLONE_ROOT="$clone_regrc"
export TEST_MERGE_BRANCH="larch-log-design-RUNREGRC1"
export GH_STUB_CHECKS_JSON_RC=8
export GH_STUB_CHECKS_JSON_OUT='[{"name":"ci","bucket":"pending"}]'
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_EMPTY_FIRST GH_STUB_CHECKS_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_PR_HEAD_OID_MISMATCH_FIRST GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPREGRC/design"
printf 'pending\n' >"$TMPREGRC/design/pending.txt"
out_regrc=$(cd "$clone_regrc" && bash "$PUBLISH" --design-tmpdir "$TMPREGRC/design" --run-id "RUNREGRC1" --issue 23 --repo owner/repo)
[[ "$out_regrc" == *"PUBLISH_OK=true"* ]] || fail "nonzero registration rc PUBLISH_OK: $out_regrc"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "nonzero registration rc should merge"
grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "nonzero registration rc should still watch"
unset GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_JSON_OUT
rm -rf "$TMPREGRC"

echo "=== registration pr view failure refuses merge ==="
TMPREGVIEW=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-reg-view.XXXXXX")
clone_regview=$(setup_clone_with_origin_head "$TMPREGVIEW")
stub_regview="$TMPREGVIEW/stub"
GH_STUB_LOG="$TMPREGVIEW/gh-reg-view.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_regview"
make_sleep_stub "$TMPREGVIEW/sleep"
export PATH="$stub_regview:$PATH"
export SLEEP_SCRIPT_DIR="$TMPREGVIEW/sleep"
export TEST_CLONE_ROOT="$clone_regview"
export TEST_MERGE_BRANCH="larch-log-design-RUNREGVIEW1"
export GH_STUB_PR_VIEW_RC=7
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_EMPTY_FIRST GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_PR_HEAD_OID_MISMATCH_FIRST GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPREGVIEW/design"
printf 'view fail\n' >"$TMPREGVIEW/design/view.txt"
regview_stderr="$TMPREGVIEW/reg-view.stderr"
set +e
out_regview=$(
    (cd "$clone_regview" && bash "$PUBLISH" --design-tmpdir "$TMPREGVIEW/design" --run-id "RUNREGVIEW1" --issue 27 --repo owner/repo) 2>"$regview_stderr"
)
rc_regview=$?
set -e
[[ "$out_regview" == *"PUBLISH_OK=false"* ]] || fail "registration view failure PUBLISH_OK: $out_regview"
[[ "$rc_regview" -eq 1 ]] || fail "registration view failure should exit 1 (got $rc_regview)"
grep -q 'did not register within' "$regview_stderr" || fail "registration view failure stderr missing registration-timeout"
grep -q 'Could not resolve host' "$regview_stderr" || fail "registration view failure stderr missing pr view diagnostic"
! grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "registration view failure must not invoke --watch"
! grep -q 'pr merge' "$GH_STUB_LOG" || fail "registration view failure must not merge"
unset GH_STUB_PR_VIEW_RC
export SLEEP_SCRIPT_DIR="$GLOBAL_SLEEP_STUB"
rm -rf "$TMPREGVIEW"

echo "=== stale head checks wait until PR head matches pushed head ==="
TMPSTALE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-stale-head.XXXXXX")
clone_stale=$(setup_clone_with_origin_head "$TMPSTALE")
stub_stale="$TMPSTALE/stub"
GH_STUB_LOG="$TMPSTALE/gh-stale-head.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_stale"
make_sleep_stub "$TMPSTALE/sleep"
export PATH="$stub_stale:$PATH"
export SLEEP_SCRIPT_DIR="$TMPSTALE/sleep"
export TEST_CLONE_ROOT="$clone_stale"
export TEST_MERGE_BRANCH="larch-log-design-RUNSTALE1"
export GH_STUB_PR_HEAD_OID_MISMATCH_FIRST=2
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_EMPTY_FIRST GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPSTALE/design"
printf 'stale\n' >"$TMPSTALE/design/stale.txt"
out_stale=$(cd "$clone_stale" && bash "$PUBLISH" --design-tmpdir "$TMPSTALE/design" --run-id "RUNSTALE1" --issue 24 --repo owner/repo)
[[ "$out_stale" == *"PUBLISH_OK=true"* ]] || fail "stale-head eventual match PUBLISH_OK: $out_stale"
[[ "$(cat "$GH_STUB_LOG.head-count")" == "3" ]] || fail "stale-head should wait for third head probe, got $(cat "$GH_STUB_LOG.head-count" 2>/dev/null || echo missing)"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "stale-head eventual match should merge"
unset GH_STUB_PR_HEAD_OID_MISMATCH_FIRST
rm -rf "$TMPSTALE"

echo "=== stale head never aligns skips watch and merge ==="
TMPSTALEN=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-stale-never.XXXXXX")
clone_stalen=$(setup_clone_with_origin_head "$TMPSTALEN")
stub_stalen="$TMPSTALEN/stub"
GH_STUB_LOG="$TMPSTALEN/gh-stale-never.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub_stalen"
make_sleep_stub "$TMPSTALEN/sleep"
export PATH="$stub_stalen:$PATH"
export SLEEP_SCRIPT_DIR="$TMPSTALEN/sleep"
export TEST_CLONE_ROOT="$clone_stalen"
export TEST_MERGE_BRANCH="larch-log-design-RUNSTALEN1"
export GH_STUB_PR_HEAD_OID_MISMATCH=1
unset GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_EMPTY_FIRST GH_STUB_CHECKS_JSON_RC GH_STUB_CHECKS_RC GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC
mkdir -p "$TMPSTALEN/design"
printf 'stale never\n' >"$TMPSTALEN/design/stale.txt"
stalen_stderr="$TMPSTALEN/stale-never.stderr"
set +e
out_stalen=$(
    (cd "$clone_stalen" && bash "$PUBLISH" --design-tmpdir "$TMPSTALEN/design" --run-id "RUNSTALEN1" --issue 25 --repo owner/repo) 2>"$stalen_stderr"
)
rc_stalen=$?
set -e
[[ "$out_stalen" == *"PUBLISH_OK=false"* ]] || fail "stale-head never aligns PUBLISH_OK: $out_stalen"
[[ "$rc_stalen" -eq 1 ]] || fail "stale-head never aligns should exit 1 (got $rc_stalen)"
grep -q 'did not register within' "$stalen_stderr" || fail "stale-head never aligns stderr missing registration-timeout"
! grep 'pr checks' "$GH_STUB_LOG" | grep -q -- '--watch' || fail "stale-head never aligns must not invoke --watch"
! grep -q 'pr merge' "$GH_STUB_LOG" || fail "stale-head never aligns must not merge"
unset GH_STUB_PR_HEAD_OID_MISMATCH
export SLEEP_SCRIPT_DIR="$GLOBAL_SLEEP_STUB"
rm -rf "$TMPSTALEN"

echo "=== git push failure after commit preserves recovery ref; no gh pr merge ==="
_PRE_PUSH_PATH="$PATH"
TMP_PUSH=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pushfail.XXXXXX")
clone_pf=$(setup_clone_with_origin_head "$TMP_PUSH")
stub_pf="$TMP_PUSH/ghstub"
GH_STUB_LOG_PF="$TMP_PUSH/gh-pushfail.log"
: >"$GH_STUB_LOG_PF"
export GH_STUB_LOG="$GH_STUB_LOG_PF"
make_gh_stub "$stub_pf"
REAL_GIT=$(command -v git)
mkdir -p "$TMP_PUSH/gitstub"
cat >"$TMP_PUSH/gitstub/git" <<GITS
#!/usr/bin/env bash
for arg in "\$@"; do
  if [[ "\$arg" == "push" ]] && [[ "\${GIT_STUB_FAIL_PUSH:-}" == "1" ]]; then
    echo "stub: push refused" >&2
    exit 1
  fi
done
exec "$REAL_GIT" "\$@"
GITS
chmod +x "$TMP_PUSH/gitstub/git"
export PATH="$TMP_PUSH/gitstub:$stub_pf:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH
export GIT_STUB_FAIL_PUSH=1
mkdir -p "$TMP_PUSH/design"
printf 'p\n' >"$TMP_PUSH/design/pushfail.txt"
set +e
out_pf=$(
    (cd "$clone_pf" && bash "$PUBLISH" --design-tmpdir "$TMP_PUSH/design" --run-id "RUNPUSHFAIL1" --issue 5 --repo owner/repo) 2>/dev/null
)
rc_pf=$?
set -e
[[ "$out_pf" == *"PUBLISH_OK=false"* ]] || fail "push fail PUBLISH_OK: $out_pf"
[[ "$rc_pf" -eq 1 ]] || fail "push fail should exit 1 (got $rc_pf)"
[[ "$out_pf" == *"RECOVERY_BRANCH=larch-log-design-recovery-RUNPUSHFAIL1"* ]] || fail "push fail should surface local recovery branch: $out_pf"
git -C "$clone_pf" show-ref --verify --quiet "refs/heads/larch-log-design-recovery-RUNPUSHFAIL1" || fail "recovery branch missing"
! grep -q 'pr merge' "$GH_STUB_LOG_PF" || fail "gh pr merge should not run when push fails"
unset GIT_STUB_FAIL_PUSH
rm -rf "$TMP_PUSH"
export PATH="$_PRE_PUSH_PATH"

echo "=== trim fail-closed on bad json sidecar ==="
TMP2=$(mktemp -d "${TMPDIR:-/tmp}/tdlp2.XXXXXX")
clone2=$(setup_clone_with_origin_head "$TMP2")
stub2="$TMP2/stub"
make_gh_stub "$stub2"
export PATH="$stub2:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG
mkdir -p "$TMP2/design"
printf 'not-json' >"$TMP2/design/bad-output.json"
out2=$(
    (cd "$clone2" && bash "$PUBLISH" --design-tmpdir "$TMP2/design" --run-id "RUNBAD1" --issue 1 --repo owner/repo) 2>/dev/null || true
)
[[ "$out2" == *"PUBLISH_OK=false"* ]] || fail "bad json should fail publish: $out2"

echo "=== malformed *.meta CMD_JSON fails publish closed ==="
TMPMETA=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-meta.XXXXXX")
clone_meta=$(setup_clone_with_origin_head "$TMPMETA")
stub_meta="$TMPMETA/stub"
make_gh_stub "$stub_meta"
export PATH="$stub_meta:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPMETA/design"
printf 'body\n' >"$TMPMETA/design/plan.txt"
printf 'CMD_JSON=this is not valid json\n' >"$TMPMETA/design/wrong.meta"
out_meta=$(
    (cd "$clone_meta" && bash "$PUBLISH" --design-tmpdir "$TMPMETA/design" --run-id "RUNMETA1" --issue 2 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_meta" == *"PUBLISH_OK=false"* ]] || fail "malformed meta should fail publish: $out_meta"

echo "=== breadcrumb publish redacts PEM/tmpdir from quiet logs only ==="
TMPBC=$(mktemp -d "${TMPDIR:-/tmp}/larch-design-breadcrumbs.XXXXXX")
clone_bc=$(setup_clone_with_origin_head "$TMPBC")
stub_bc="$TMPBC/stub"
make_gh_stub "$stub_bc"
export PATH="$stub_bc:$PATH"
export TEST_CLONE_ROOT="$clone_bc"
export TEST_MERGE_BRANCH="larch-log-design-RUNBREAD1"
unset GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPBC/design/breadcrumbs"
printf 'body\n' >"$TMPBC/design/plan.txt"
secret_path="/tmp/larch-design-breadcrumbs123/private.txt"
pem_begin_part1='-----BEGIN RSA PRIVATE '
pem_begin_part2='KEY-----'
pem_body_part1='MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1'
pem_body_part2='Pt8Qu'
pem_end_part1='-----END RSA PRIVATE '
pem_end_part2='KEY-----'
pem_body="${pem_body_part1}${pem_body_part2}"
printf 'legacy ndjson must not publish\n' >"$TMPBC/design/breadcrumbs/stream.ndjson"
{
    printf 'quiet tmpdir %s\n' "$secret_path"
    printf '%s%s\n' "$pem_begin_part1" "$pem_begin_part2"
    printf '%s%s\n' "$pem_body_part1" "$pem_body_part2"
    printf '%s%s\n' "$pem_end_part1" "$pem_end_part2"
} >"$TMPBC/design/larch-quiet-design-log-publish.sh-99999.log"
(
    cd "$clone_bc" || exit 1
    out_bc=$(bash "$PUBLISH" --design-tmpdir "$TMPBC/design" --run-id "RUNBREAD1" --issue 13 --repo owner/repo)
    [[ "$out_bc" == *"PUBLISH_OK=true"* ]] || fail "breadcrumb publish PUBLISH_OK: $out_bc"
)
git -C "$clone_bc" pull -q origin main
bc_quiet="$clone_bc/larch-logs/design/RUNBREAD1/breadcrumbs/larch-quiet-design-log-publish.sh-99999.log"
[[ -f "$bc_quiet" ]] || fail "breadcrumb quiet log missing"
[[ ! -f "$clone_bc/larch-logs/design/RUNBREAD1/breadcrumbs/stream.ndjson" ]] || fail "legacy ndjson must not be published"
grep -Eq '<TMPDIR>|<OPERATOR_REPO_PATH>' "$bc_quiet" || fail "breadcrumb quiet log tmpdir redaction missing"
! grep -Fq "$secret_path" "$bc_quiet" || fail "breadcrumb quiet log leaked tmpdir path"
grep -q '<REDACTED-PRIVATE-KEY>' "$bc_quiet" || fail "breadcrumb quiet log PEM redaction missing"
! grep -Fq "$pem_body" "$bc_quiet" || fail "breadcrumb quiet log leaked PEM body"

echo "=== breadcrumb publish rejects symlink source closed ==="
TMPBCSYM=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-breadcrumb-symlink.XXXXXX")
clone_bcsym=$(setup_clone_with_origin_head "$TMPBCSYM")
stub_bcsym="$TMPBCSYM/stub"
make_gh_stub "$stub_bcsym"
export PATH="$stub_bcsym:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPBCSYM/design/breadcrumbs"
printf 'body\n' >"$TMPBCSYM/design/plan.txt"
printf 'real\n' >"$TMPBCSYM/real-breadcrumb.txt"
ln -s "$TMPBCSYM/real-breadcrumb.txt" "$TMPBCSYM/design/larch-quiet-bad.sh-1.log"
out_bcsym=$(
    (cd "$clone_bcsym" && bash "$PUBLISH" --design-tmpdir "$TMPBCSYM/design" --run-id "RUNBSYM1" --issue 14 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_bcsym" == *"PUBLISH_OK=false"* ]] || fail "breadcrumb symlink should fail publish: $out_bcsym"
[[ ! -e "$clone_bcsym/larch-logs/design/RUNBSYM1/breadcrumbs" ]] || fail "breadcrumb symlink failure should leave no published breadcrumbs"

echo "=== breadcrumb publish fails closed on redactor failure ==="
TMPBCFAIL=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-breadcrumb-fail.XXXXXX")
clone_bcfail=$(setup_clone_with_origin_head "$TMPBCFAIL")
stub_bcfail="$TMPBCFAIL/stub"
make_gh_stub "$stub_bcfail"
export PATH="$stub_bcfail:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPBCFAIL/design/breadcrumbs"
printf 'body\n' >"$TMPBCFAIL/design/plan.txt"
printf 'will fail redaction\n' >"$TMPBCFAIL/design/larch-quiet-fail.sh-1.log"
orig_redact="$REPO_ROOT/scripts/redact-secrets.sh"
saved_redact="$TMPBCFAIL/redact-secrets.original.sh"
cp "$orig_redact" "$saved_redact"
cat >"$TMPBCFAIL/redact-secrets.fail.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
exit 1
EOF
chmod +x "$TMPBCFAIL/redact-secrets.fail.sh"
cp "$TMPBCFAIL/redact-secrets.fail.sh" "$orig_redact"
out_bcfail=$(
    (cd "$clone_bcfail" && bash "$PUBLISH" --design-tmpdir "$TMPBCFAIL/design" --run-id "RUNBFAIL1" --issue 15 --repo owner/repo) 2>/dev/null || true
)
cp "$saved_redact" "$orig_redact"
[[ "$out_bcfail" == *"PUBLISH_OK=false"* ]] || fail "breadcrumb redactor failure should fail publish: $out_bcfail"
[[ ! -e "$clone_bcfail/larch-logs/design/RUNBFAIL1/breadcrumbs" ]] || fail "breadcrumb redactor failure should leave no published breadcrumbs"

echo "=== plan-review allowlist rejects unexpected paths and symlinks ==="
TMPPRE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-empty.XXXXXX")
clone_pre=$(setup_clone_with_origin_head "$TMPPRE")
stub_pre="$TMPPRE/stub"
make_gh_stub "$stub_pre"
export PATH="$stub_pre:$PATH"
export TEST_CLONE_ROOT="$clone_pre"
export TEST_MERGE_BRANCH="larch-log-design-RUNPREMPTY1"
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC GH_STUB_MERGE_RC GH_STUB_CHECKS_JSON_ALWAYS_EMPTY GH_STUB_CHECKS_JSON_RC GH_STUB_PR_HEAD_OID_MISMATCH GH_STUB_PR_HEAD_OID_MISMATCH_FIRST
mkdir -p "$TMPPRE/design/plan-review"
printf 'body\n' >"$TMPPRE/design/plan.txt"
out_pre=$(
    (cd "$clone_pre" && bash "$PUBLISH" --design-tmpdir "$TMPPRE/design" --run-id "RUNPREMPTY1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pre" == *"PUBLISH_OK=true"* ]] || fail "empty plan-review dir should publish: $out_pre"

TMPPRU=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-unexpected.XXXXXX")
clone_pru=$(setup_clone_with_origin_head "$TMPPRU")
stub_pru="$TMPPRU/stub"
make_gh_stub "$stub_pru"
export PATH="$stub_pru:$PATH"
mkdir -p "$TMPPRU/design/plan-review/round-1"
printf 'body\n' >"$TMPPRU/design/plan.txt"
printf 'finding_id\tfinding_reviewers\tvoting_result\n' >"$TMPPRU/design/plan-review/round-1/findings-classification.tsv"
printf 'unexpected\n' >"$TMPPRU/design/plan-review/round-1/unexpected.txt"
out_pru=$(
    (cd "$clone_pru" && bash "$PUBLISH" --design-tmpdir "$TMPPRU/design" --run-id "RUNPRUNEXPECTED1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pru" == *"PUBLISH_OK=false"* ]] || fail "unexpected plan-review file should fail publish: $out_pru"

TMPPR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr.XXXXXX")
clone_pr=$(setup_clone_with_origin_head "$TMPPR")
stub_pr="$TMPPR/stub"
make_gh_stub "$stub_pr"
export PATH="$stub_pr:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPR/design/plan-review/round-01"
printf 'body\n' >"$TMPPR/design/plan.txt"
printf 'bad\n' >"$TMPPR/design/plan-review/round-01/findings-classification.tsv"
out_pr=$(
    (cd "$clone_pr" && bash "$PUBLISH" --design-tmpdir "$TMPPR/design" --run-id "RUNPRBAD1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pr" == *"PUBLISH_OK=false"* ]] || fail "bad plan-review path should fail publish: $out_pr"

TMPPR0=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-zero.XXXXXX")
clone_pr0=$(setup_clone_with_origin_head "$TMPPR0")
stub_pr0="$TMPPR0/stub"
make_gh_stub "$stub_pr0"
export PATH="$stub_pr0:$PATH"
mkdir -p "$TMPPR0/design/plan-review/round-0"
printf 'body\n' >"$TMPPR0/design/plan.txt"
printf 'bad\n' >"$TMPPR0/design/plan-review/round-0/findings-classification.tsv"
out_pr0=$(
    (cd "$clone_pr0" && bash "$PUBLISH" --design-tmpdir "$TMPPR0/design" --run-id "RUNPRZERO1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pr0" == *"PUBLISH_OK=false"* ]] || fail "round-0 plan-review path should fail publish: $out_pr0"

TMPPRROOT=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-rootsym.XXXXXX")
clone_prroot=$(setup_clone_with_origin_head "$TMPPRROOT")
stub_prroot="$TMPPRROOT/stub"
make_gh_stub "$stub_prroot"
export PATH="$stub_prroot:$PATH"
mkdir -p "$TMPPRROOT/real-plan-review/round-1"
mkdir -p "$TMPPRROOT/design"
printf 'body\n' >"$TMPPRROOT/design/plan.txt"
printf 'ok\n' >"$TMPPRROOT/real-plan-review/round-1/findings-classification.tsv"
ln -s "$TMPPRROOT/real-plan-review" "$TMPPRROOT/design/plan-review"
out_prroot=$(
    (cd "$clone_prroot" && bash "$PUBLISH" --design-tmpdir "$TMPPRROOT/design" --run-id "RUNPRROOT1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_prroot" == *"PUBLISH_OK=false"* ]] || fail "plan-review root symlink should fail publish: $out_prroot"

TMPPRS=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-sym.XXXXXX")
clone_prs=$(setup_clone_with_origin_head "$TMPPRS")
stub_prs="$TMPPRS/stub"
make_gh_stub "$stub_prs"
export PATH="$stub_prs:$PATH"
mkdir -p "$TMPPRS/design/plan-review/round-1"
printf 'body\n' >"$TMPPRS/design/plan.txt"
printf 'ok\n' >"$TMPPRS/design/plan-review/round-1/findings-classification.tsv"
ln -s "$TMPPRS/design/plan.txt" "$TMPPRS/design/plan-review/round-1/linked-plan.txt"
out_prs=$(
    (cd "$clone_prs" && bash "$PUBLISH" --design-tmpdir "$TMPPRS/design" --run-id "RUNPRSYM1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_prs" == *"PUBLISH_OK=false"* ]] || fail "plan-review symlink should fail publish: $out_prs"

TMPPRMID=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-midsym.XXXXXX")
clone_prmid=$(setup_clone_with_origin_head "$TMPPRMID")
stub_prmid="$TMPPRMID/stub"
make_gh_stub "$stub_prmid"
export PATH="$stub_prmid:$PATH"
mkdir -p "$TMPPRMID/real-round-1"
mkdir -p "$TMPPRMID/design/plan-review"
printf 'body\n' >"$TMPPRMID/design/plan.txt"
printf 'ok\n' >"$TMPPRMID/real-round-1/findings-classification.tsv"
ln -s "$TMPPRMID/real-round-1" "$TMPPRMID/design/plan-review/round-1"
out_prmid=$(
    (cd "$clone_prmid" && bash "$PUBLISH" --design-tmpdir "$TMPPRMID/design" --run-id "RUNPRMID1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_prmid" == *"PUBLISH_OK=false"* ]] || fail "plan-review intermediate symlink should fail publish: $out_prmid"

TMPPRESC=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-escape.XXXXXX")
clone_presc=$(setup_clone_with_origin_head "$TMPPRESC")
stub_presc="$TMPPRESC/stub"
make_gh_stub "$stub_presc"
REAL_FIND=$(command -v find)
make_find_escape_stub "$TMPPRESC/findstub" "$REAL_FIND"
export PATH="$TMPPRESC/findstub:$stub_presc:$PATH"
mkdir -p "$TMPPRESC/design/plan-review/round-1"
printf 'body\n' >"$TMPPRESC/design/plan.txt"
printf 'ok\n' >"$TMPPRESC/design/plan-review/round-1/findings-classification.tsv"
ESCAPE_FIND_ROOT="$(cd "$TMPPRESC/design/plan-review" && pwd -P)"
export ESCAPE_FIND_ROOT
export ESCAPE_FIND_PATH="$TMPPRESC/design/plan.txt"
out_presc=$(
    (cd "$clone_presc" && bash "$PUBLISH" --design-tmpdir "$TMPPRESC/design" --run-id "RUNPRESC1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
unset ESCAPE_FIND_ROOT ESCAPE_FIND_PATH
[[ "$out_presc" == *"PUBLISH_OK=false"* ]] || fail "plan-review path escape should fail publish: $out_presc"

TMPPRRACE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-race.XXXXXX")
clone_prrace=$(setup_clone_with_origin_head "$TMPPRRACE")
stub_prrace="$TMPPRRACE/stub"
make_gh_stub "$stub_prrace"
REAL_FIND=$(command -v find)
make_find_symlink_race_stub "$TMPPRRACE/findstub" "$REAL_FIND"
export PATH="$TMPPRRACE/findstub:$stub_prrace:$PATH"
mkdir -p "$TMPPRRACE/design/plan-review/round-1"
printf 'body\n' >"$TMPPRRACE/design/plan.txt"
printf 'ok\n' >"$TMPPRRACE/design/plan-review/round-1/findings-classification.tsv"
RACE_FIND_ROOT="$(cd "$TMPPRRACE/design/plan-review" && pwd -P)"
export RACE_FIND_ROOT
export RACE_FIND_PATH="$TMPPRRACE/design/plan-review/round-1/findings-classification.tsv"
export RACE_FIND_TARGET="$TMPPRRACE/design/plan.txt"
out_prrace=$(
    (cd "$clone_prrace" && bash "$PUBLISH" --design-tmpdir "$TMPPRRACE/design" --run-id "RUNPRRACE1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
unset RACE_FIND_ROOT RACE_FIND_PATH RACE_FIND_TARGET
[[ "$out_prrace" == *"PUBLISH_OK=false"* ]] || fail "plan-review symlink race should fail publish: $out_prrace"

echo "=== render-cache root symlink rejection ==="
TMPRCROOT=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rc-rootsym.XXXXXX")
clone_rcroot=$(setup_clone_with_origin_head "$TMPRCROOT")
stub_rcroot="$TMPRCROOT/stub"
make_gh_stub "$stub_rcroot"
export PATH="$stub_rcroot:$PATH"
mkdir -p "$TMPRCROOT/real-render-cache/nested"
mkdir -p "$TMPRCROOT/design"
printf 'body\n' >"$TMPRCROOT/design/plan.txt"
printf 'ok\n' >"$TMPRCROOT/real-render-cache/nested/c.txt"
ln -s "$TMPRCROOT/real-render-cache" "$TMPRCROOT/design/render-cache"
out_rcroot=$(
    (cd "$clone_rcroot" && bash "$PUBLISH" --design-tmpdir "$TMPRCROOT/design" --run-id "RUNRCROOT1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_rcroot" == *"PUBLISH_OK=false"* ]] || fail "render-cache root symlink should fail publish: $out_rcroot"

echo "=== render-cache dangling root symlink rejection ==="
TMPRCDANGLE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rc-dangle.XXXXXX")
clone_rcdangle=$(setup_clone_with_origin_head "$TMPRCDANGLE")
stub_rcdangle="$TMPRCDANGLE/stub"
make_gh_stub "$stub_rcdangle"
export PATH="$stub_rcdangle:$PATH"
mkdir -p "$TMPRCDANGLE/design"
printf 'body\n' >"$TMPRCDANGLE/design/plan.txt"
ln -s "$TMPRCDANGLE/does-not-exist" "$TMPRCDANGLE/design/render-cache"
out_rcdangle=$(
    (cd "$clone_rcdangle" && bash "$PUBLISH" --design-tmpdir "$TMPRCDANGLE/design" --run-id "RUNRCDANGLE1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_rcdangle" == *"PUBLISH_OK=false"* ]] || fail "render-cache dangling root symlink should fail publish: $out_rcdangle"

echo "=== render-cache leaf file-symlink rejection ==="
TMPRCLEAF=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rc-leaf.XXXXXX")
clone_rcleaf=$(setup_clone_with_origin_head "$TMPRCLEAF")
stub_rcleaf="$TMPRCLEAF/stub"
make_gh_stub "$stub_rcleaf"
export PATH="$stub_rcleaf:$PATH"
mkdir -p "$TMPRCLEAF/design/render-cache"
printf 'body\n' >"$TMPRCLEAF/design/plan.txt"
ln -s "$TMPRCLEAF/design/plan.txt" "$TMPRCLEAF/design/render-cache/linked.txt"
out_rcleaf=$(
    (cd "$clone_rcleaf" && bash "$PUBLISH" --design-tmpdir "$TMPRCLEAF/design" --run-id "RUNRCLEAF1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_rcleaf" == *"PUBLISH_OK=false"* ]] || fail "render-cache leaf file-symlink should fail publish: $out_rcleaf"

echo "=== render-cache intermediate symlink rejection ==="
TMPRCMID=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rc-midsym.XXXXXX")
clone_rcmid=$(setup_clone_with_origin_head "$TMPRCMID")
stub_rcmid="$TMPRCMID/stub"
make_gh_stub "$stub_rcmid"
export PATH="$stub_rcmid:$PATH"
mkdir -p "$TMPRCMID/real-nested"
mkdir -p "$TMPRCMID/design/render-cache"
printf 'body\n' >"$TMPRCMID/design/plan.txt"
printf 'ok\n' >"$TMPRCMID/real-nested/c.txt"
ln -s "$TMPRCMID/real-nested" "$TMPRCMID/design/render-cache/nested"
out_rcmid=$(
    (cd "$clone_rcmid" && bash "$PUBLISH" --design-tmpdir "$TMPRCMID/design" --run-id "RUNRCMID1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_rcmid" == *"PUBLISH_OK=false"* ]] || fail "render-cache intermediate symlink should fail publish: $out_rcmid"

echo "=== render-cache symlink race rejection ==="
TMPRCRACE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rc-race.XXXXXX")
clone_rcrace=$(setup_clone_with_origin_head "$TMPRCRACE")
stub_rcrace="$TMPRCRACE/stub"
make_gh_stub "$stub_rcrace"
REAL_FIND=$(command -v find)
make_find_symlink_race_stub "$TMPRCRACE/findstub" "$REAL_FIND"
export PATH="$TMPRCRACE/findstub:$stub_rcrace:$PATH"
mkdir -p "$TMPRCRACE/design/render-cache"
printf 'body\n' >"$TMPRCRACE/design/plan.txt"
printf 'ok\n' >"$TMPRCRACE/design/render-cache/cached-output.txt"
RACE_FIND_ROOT="$(cd "$TMPRCRACE/design/render-cache" && pwd -P)"
export RACE_FIND_ROOT
export RACE_FIND_PATH="$TMPRCRACE/design/render-cache/cached-output.txt"
export RACE_FIND_TARGET="$TMPRCRACE/design/plan.txt"
out_rcrace=$(
    (cd "$clone_rcrace" && bash "$PUBLISH" --design-tmpdir "$TMPRCRACE/design" --run-id "RUNRCRACE1" --issue 4 --repo owner/repo) 2>/dev/null || true
)
unset RACE_FIND_ROOT RACE_FIND_PATH RACE_FIND_TARGET
[[ "$out_rcrace" == *"PUBLISH_OK=false"* ]] || fail "render-cache symlink race should fail publish: $out_rcrace"

echo "=== render-cache ancestor-directory race rejection ==="
TMPRCANCESTOR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-rc-ancestor.XXXXXX")
clone_rcancestor=$(setup_clone_with_origin_head "$TMPRCANCESTOR")
stub_rcancestor="$TMPRCANCESTOR/stub"
make_gh_stub "$stub_rcancestor"
REAL_FIND=$(command -v find)
make_find_ancestor_race_stub "$TMPRCANCESTOR/findstub" "$REAL_FIND"
export PATH="$TMPRCANCESTOR/findstub:$stub_rcancestor:$PATH"
mkdir -p "$TMPRCANCESTOR/design/render-cache/sub"
printf 'body\n' >"$TMPRCANCESTOR/design/plan.txt"
printf 'ok\n' >"$TMPRCANCESTOR/design/render-cache/sub/file.txt"
ANCESTOR_RACE_FIND_ROOT="$(cd "$TMPRCANCESTOR/design/render-cache" && pwd -P)"
export ANCESTOR_RACE_FIND_ROOT
export ANCESTOR_RACE_PATH="$ANCESTOR_RACE_FIND_ROOT/sub/file.txt"
export ANCESTOR_RACE_PARENT="$ANCESTOR_RACE_FIND_ROOT/sub"
export ANCESTOR_RACE_TARGET="$TMPRCANCESTOR/outside"
mkdir -p "$ANCESTOR_RACE_TARGET"
out_rcancestor=$(
    (cd "$clone_rcancestor" && bash "$PUBLISH" --design-tmpdir "$TMPRCANCESTOR/design" --run-id "RUNRCANCESTOR1" --issue 4 --repo owner/repo) 2>&1 || true
)
unset ANCESTOR_RACE_FIND_ROOT ANCESTOR_RACE_PATH ANCESTOR_RACE_PARENT ANCESTOR_RACE_TARGET
[[ "$out_rcancestor" == *"PUBLISH_OK=false"* ]] || fail "render-cache ancestor race should fail publish: $out_rcancestor"
[[ "$out_rcancestor" == *"design-log-publish: render-cache ancestor became a symlink before staging"* ]] || fail "render-cache ancestor race missing larch_err: $out_rcancestor"

echo "=== plan-review ancestor-directory race rejection ==="
TMPPRANCESTOR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-pr-ancestor.XXXXXX")
clone_prancestor=$(setup_clone_with_origin_head "$TMPPRANCESTOR")
stub_prancestor="$TMPPRANCESTOR/stub"
make_gh_stub "$stub_prancestor"
make_find_ancestor_race_stub "$TMPPRANCESTOR/findstub" "$REAL_FIND"
export PATH="$TMPPRANCESTOR/findstub:$stub_prancestor:$PATH"
mkdir -p "$TMPPRANCESTOR/design/plan-review/round-1"
printf 'body\n' >"$TMPPRANCESTOR/design/plan.txt"
printf 'ok\n' >"$TMPPRANCESTOR/design/plan-review/round-1/findings-classification.tsv"
ANCESTOR_RACE_FIND_ROOT="$(cd "$TMPPRANCESTOR/design/plan-review" && pwd -P)"
export ANCESTOR_RACE_FIND_ROOT
export ANCESTOR_RACE_PATH="$ANCESTOR_RACE_FIND_ROOT/round-1/findings-classification.tsv"
export ANCESTOR_RACE_PARENT="$ANCESTOR_RACE_FIND_ROOT/round-1"
export ANCESTOR_RACE_TARGET="$TMPPRANCESTOR/outside-pr"
mkdir -p "$ANCESTOR_RACE_TARGET"
out_prancestor=$(
    (cd "$clone_prancestor" && bash "$PUBLISH" --design-tmpdir "$TMPPRANCESTOR/design" --run-id "RUNPRANCESTOR1" --issue 4 --repo owner/repo) 2>&1 || true
)
unset ANCESTOR_RACE_FIND_ROOT ANCESTOR_RACE_PATH ANCESTOR_RACE_PARENT ANCESTOR_RACE_TARGET
[[ "$out_prancestor" == *"PUBLISH_OK=false"* ]] || fail "plan-review ancestor race should fail publish: $out_prancestor"
[[ "$out_prancestor" == *"design-log-publish: plan-review ancestor became a symlink before staging"* ]] || fail "plan-review ancestor race missing larch_err: $out_prancestor"

echo "All design-log-publish harness assertions passed."
