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
if [[ "$1" == "repo" ]] && [[ "$2" == "view" ]]; then
    printf '{"nameWithOwner":"owner/repo"}\n'
    exit 0
fi
if [[ "$1" == "pr" ]]; then
    case "$2" in
        create)
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
            echo '{"url":"https://github.com/owner/repo/pull/101"}'
            exit 0
            ;;
        list)
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

echo "=== dry-run preflight inside git worktree ==="
DRYROOT=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-dry.XXXXXX")
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
out=$(
    (cd "$DRYCLONE" && PATH="$STUBDR:$PATH" bash "$PUBLISH" --design-tmpdir "$DRYROOT/design" --run-id "RUN1AB" --issue 0 --dry-run) 2>/dev/null || true
)
[[ "$out" == *"PUBLISH_OK=false"* ]] || fail "issue 0 should fail: $out"

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
printf 'Automated design log directory for run RUNPUB1. Commit uses [skip ci].' >"$GH_STUB_EXPECT_PR_BODY_FILE"
export GH_STUB_EXPECT_PR_BODY_FILE

mkdir -p "$TMP/design/render-cache/nested" "$TMP/design/plan-review/round-1"
printf 'body\n' >"$TMP/design/plan.txt"
printf 'CMD_JSON=["secret"]\nkeep\n' >"$TMP/design/out.txt.meta"
printf '{"ok":1,"result":{"token":"x"}}\n' >"$TMP/design/voter-output-1.json"
printf '{"x":1,"result":{"y":2}}\n' >"$TMP/design/plain.json"
printf 'deep\n' >"$TMP/design/render-cache/nested/c.txt"
printf 'finding_id\tfinding_reviewers\tvoting_result\n' >"$TMP/design/plan-review/round-1/findings-classification.tsv"
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
grep -q '^keep$' "$clone/larch-logs/design/RUNPUB1/out.txt.meta" || fail "meta trim failed"
! grep -q CMD_JSON "$clone/larch-logs/design/RUNPUB1/out.txt.meta" || fail "CMD_JSON should be stripped"
! grep -q '"result"' "$clone/larch-logs/design/RUNPUB1/voter-output-1.json" || fail ".result should be stripped from *-output*.json"
grep -q '"result"' "$clone/larch-logs/design/RUNPUB1/plain.json" || fail "plain.json should retain .result (not *-output*.json)"
grep -qE '"ok"[[:space:]]*:[[:space:]]*1' "$clone/larch-logs/design/RUNPUB1/voter-output-1.json" || fail "json body missing"
grep -q 'pr create' "$GH_STUB_LOG" || fail "expected gh pr create in log"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "expected gh pr merge in log"
grep -Fq -- '--body-file' "$GH_STUB_LOG" || fail "expected gh pr create --body-file in log"
! grep -Eq '(^| )--body( |$)' "$GH_STUB_LOG" || fail "gh pr create should not use inline --body"
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
# shellcheck disable=SC2016 # fixed literal in design-log-publish.sh source.
grep -Fq 'pause design run ${RUN_ID}' "$PUBLISH" || fail "pause commit subject branch missing in script"

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
out_cr=$(
    (cd "$clone_cr" && bash "$PUBLISH" --design-tmpdir "$TMPCR/design" --run-id "RUNCREATE1" --issue 11 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_cr" == *"PUBLISH_OK=true"* ]] || fail "create-fail recovery PUBLISH_OK: $out_cr"
[[ "$out_cr" == *"PR_NUMBER=101"* ]] || fail "create-fail recovery PR_NUMBER: $out_cr"
grep -q 'pr create' "$GH_STUB_LOG_CR" || fail "expected pr create attempt in log"
grep -q 'pr merge' "$GH_STUB_LOG_CR" || fail "expected pr merge after list recovery"
unset GH_STUB_CREATE_RC

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
export GH_STUB_MERGE_RC=1
unset GH_STUB_CREATE_NO_URL GH_STUB_CREATE_RC
mkdir -p "$TMPM/design"
printf 'm\n' >"$TMPM/design/m.txt"
out_m=$(
    (cd "$clone_m" && bash "$PUBLISH" --design-tmpdir "$TMPM/design" --run-id "RUNMERGE1" --issue 3 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_m" == *"PUBLISH_OK=false"* ]] || fail "merge fail PUBLISH_OK: $out_m"
[[ "$out_m" == *"PR_NUMBER=101"* ]] || fail "merge fail PR_NUMBER: $out_m"
[[ "$out_m" == *"RECOVERY_BRANCH=larch-log-design-RUNMERGE1"* ]] || fail "merge fail RECOVERY_BRANCH: $out_m"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "expected pr merge in stub log"
unset GH_STUB_MERGE_RC

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
out_pf=$(
    (cd "$clone_pf" && bash "$PUBLISH" --design-tmpdir "$TMP_PUSH/design" --run-id "RUNPUSHFAIL1" --issue 5 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pf" == *"PUBLISH_OK=false"* ]] || fail "push fail PUBLISH_OK: $out_pf"
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

echo "=== breadcrumb publish redacts PEM/tmpdir and copies non-ndjson files ==="
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
secret_path="$TMPBC/design/private.txt"
pem_begin_part1='-----BEGIN RSA PRIVATE '
pem_begin_part2='KEY-----'
pem_body_part1='MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1'
pem_body_part2='Pt8Qu'
pem_end_part1='-----END RSA PRIVATE '
pem_end_part2='KEY-----'
pem_body="${pem_body_part1}${pem_body_part2}"
{
    printf 'larch:bc t=now d=0 p=1 s=test c=progress text=tmpdir %s\n' "$secret_path"
    printf '%s%s\n' "$pem_begin_part1" "$pem_begin_part2"
    printf '%s%s\n' "$pem_body_part1" "$pem_body_part2"
    printf '%s%s\n' "$pem_end_part1" "$pem_end_part2"
} >"$TMPBC/design/breadcrumbs/stream.ndjson"
printf 'quiet tmpdir %s\n' "$secret_path" >"$TMPBC/design/breadcrumbs/stream.quiet"
(
    cd "$clone_bc" || exit 1
    out_bc=$(bash "$PUBLISH" --design-tmpdir "$TMPBC/design" --run-id "RUNBREAD1" --issue 13 --repo owner/repo)
    [[ "$out_bc" == *"PUBLISH_OK=true"* ]] || fail "breadcrumb publish PUBLISH_OK: $out_bc"
)
git -C "$clone_bc" pull -q origin main
bc_stream="$clone_bc/larch-logs/design/RUNBREAD1/breadcrumbs/stream.ndjson"
# Only .ndjson files are published; non-ndjson sidecars (e.g. .quiet) are filtered by larch_log_publish_breadcrumbs_shared
[[ -f "$bc_stream" ]] || fail "breadcrumb ndjson missing"
[[ ! -f "$clone_bc/larch-logs/design/RUNBREAD1/breadcrumbs/stream.quiet" ]] || fail "non-ndjson sidecar must not be published"
grep -Eq '<TMPDIR>|<OPERATOR_REPO_PATH>' "$bc_stream" || fail "breadcrumb ndjson tmpdir redaction missing"
! grep -Fq "$secret_path" "$bc_stream" || fail "breadcrumb ndjson leaked tmpdir path"
grep -q '<REDACTED-PRIVATE-KEY>' "$bc_stream" || fail "breadcrumb ndjson PEM redaction missing"
! grep -Fq "$pem_body" "$bc_stream" || fail "breadcrumb ndjson leaked PEM body"

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
ln -s "$TMPBCSYM/real-breadcrumb.txt" "$TMPBCSYM/design/breadcrumbs/bad.ndjson"
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
printf 'will fail redaction\n' >"$TMPBCFAIL/design/breadcrumbs/fail.ndjson"
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

echo "All design-log-publish harness assertions passed."
