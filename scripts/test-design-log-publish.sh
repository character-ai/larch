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

mkdir -p "$TMP/design/render-cache/nested" "$TMP/design/plan-review/round-1"
printf 'body\n' >"$TMP/design/plan.txt"
printf 'CMD_JSON=["secret"]\nkeep\n' >"$TMP/design/out.txt.meta"
printf '{"ok":1,"result":{"token":"x"}}\n' >"$TMP/design/voter-output-1.json"
printf '{"x":1,"result":{"y":2}}\n' >"$TMP/design/plain.json"
printf 'deep\n' >"$TMP/design/render-cache/nested/c.txt"
printf 'finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\n' >"$TMP/design/plan-review/round-1/findings-classification.tsv"
# Files that MUST be denied by the suffix deny-list (mirrors /implement's
# round_artifact_included deny patterns):
printf 'noisy raw transcript\n' >"$TMP/design/codex-plan-arch-output.txt.sidecar"
printf 'STATUS=clean\n' >"$TMP/design/codex-plan-arch-output.txt.dirty-tree"
: >"$TMP/design/codex-plan-arch-output.txt.untracked-baseline"
printf 'OK\n' >"$TMP/design/codex-plan-arch-output.txt.done"
: >"$TMP/design/cursor-plan-arch-output.txt.diag"
printf 'launcher prompt body\n' >"$TMP/design/codex-plan-arch-output.txt.prompt"
printf 'phased launcher prompt\n' >"$TMP/design/codex-plan-arch-output-phase2.txt.prompt"
# Same suffix family in render-cache must also be denied:
printf 'rc noisy\n' >"$TMP/design/render-cache/cached-output.txt.sidecar"

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
# Verify suffix deny-list dropped each denied basename at both top-level and render-cache:
for denied in \
    "codex-plan-arch-output.txt.sidecar" \
    "codex-plan-arch-output.txt.dirty-tree" \
    "codex-plan-arch-output.txt.untracked-baseline" \
    "codex-plan-arch-output.txt.done" \
    "cursor-plan-arch-output.txt.diag" \
    "codex-plan-arch-output.txt.prompt" \
    "codex-plan-arch-output-phase2.txt.prompt"; do
    [[ ! -f "$clone/larch-logs/design/RUNPUB1/$denied" ]] || fail "denied basename leaked into top-level: $denied"
done
[[ ! -f "$clone/larch-logs/design/RUNPUB1/render-cache/cached-output.txt.sidecar" ]] || fail "denied basename leaked into render-cache"

echo "=== symlinked findings-classification.tsv is rejected ==="
TMPSYM=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-symlink.XXXXXX")
clone_sym=$(setup_clone_with_origin_head "$TMPSYM")
stub_sym="$TMPSYM/stub"
make_gh_stub "$stub_sym"
export PATH="$stub_sym:$PATH"
mkdir -p "$TMPSYM/design/plan-review/round-1"
printf 'safe\n' >"$TMPSYM/design/real.tsv"
ln -sf "$TMPSYM/design/real.tsv" "$TMPSYM/design/plan-review/round-1/findings-classification.tsv"
out_sym=$(
    (cd "$clone_sym" && bash "$PUBLISH" --design-tmpdir "$TMPSYM/design" --run-id "RUNSYML1" --issue 8 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_sym" == *"PUBLISH_OK=false"* ]] || fail "symlinked findings-classification.tsv should fail publish"

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

echo "=== plan-review unexpected file fails publish ==="
TMPPR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-planreview.XXXXXX")
clone_pr=$(setup_clone_with_origin_head "$TMPPR")
stub_pr="$TMPPR/stub"
make_gh_stub "$stub_pr"
export PATH="$stub_pr:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPR/design/plan-review/round-1"
printf 'body\n' >"$TMPPR/design/plan.txt"
printf 'bad\n' >"$TMPPR/design/plan-review/round-1/unexpected.txt"
out_pr=$(
    (cd "$clone_pr" && bash "$PUBLISH" --design-tmpdir "$TMPPR/design" --run-id "RUNPRBAD1" --issue 6 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pr" == *"PUBLISH_OK=false"* ]] || fail "unexpected plan-review file should fail publish: $out_pr"

echo "=== absent or empty plan-review succeeds ==="
TMPPRE=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-planreview-empty.XXXXXX")
clone_pre=$(setup_clone_with_origin_head "$TMPPRE")
stub_pre="$TMPPRE/stub"
make_gh_stub "$stub_pre"
export PATH="$stub_pre:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPRE/design-no-plan-review" "$TMPPRE/design-empty-plan-review/plan-review"
printf 'body\n' >"$TMPPRE/design-no-plan-review/plan.txt"
printf 'body\n' >"$TMPPRE/design-empty-plan-review/plan.txt"
out_pre_absent=$(
    (cd "$clone_pre" && bash "$PUBLISH" --design-tmpdir "$TMPPRE/design-no-plan-review" --run-id "RUNPRNONE1" --issue 12 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pre_absent" == *"PUBLISH_OK=true"* ]] || fail "absent plan-review should publish successfully: $out_pre_absent"
out_pre_empty=$(
    (cd "$clone_pre" && bash "$PUBLISH" --design-tmpdir "$TMPPRE/design-empty-plan-review" --run-id "RUNPREMPTY1" --issue 13 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_pre_empty" == *"PUBLISH_OK=true"* ]] || fail "empty plan-review should publish successfully: $out_pre_empty"

echo "=== plan-review symlink root fails publish ==="
TMPPRL=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-planreview-link.XXXXXX")
clone_prl=$(setup_clone_with_origin_head "$TMPPRL")
stub_prl="$TMPPRL/stub"
make_gh_stub "$stub_prl"
export PATH="$stub_prl:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH GH_STUB_LOG GH_STUB_CREATE_RC GH_STUB_CREATE_NO_URL GH_STUB_MERGE_RC
mkdir -p "$TMPPRL/design" "$TMPPRL/real-plan-review"
printf 'body\n' >"$TMPPRL/design/plan.txt"
ln -s "$TMPPRL/real-plan-review" "$TMPPRL/design/plan-review"
out_prl=$(
    (cd "$clone_prl" && bash "$PUBLISH" --design-tmpdir "$TMPPRL/design" --run-id "RUNPRLINK1" --issue 8 --repo owner/repo) 2>/dev/null || true
)
[[ "$out_prl" == *"PUBLISH_OK=false"* ]] || fail "symlink plan-review root should fail publish: $out_prl"

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

echo "All design-log-publish harness assertions passed."
