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
            echo "https://github.com/owner/repo/pull/101"
            exit 0
            ;;
        merge)
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
            echo '[{"number":101}]'
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

echo "=== dry-run emits ok without gh ==="
TMPDR=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-dry.XXXXXX")
trap 'rm -rf "$TMPDR"' EXIT
mkdir -p "$TMPDR/design"
printf 'x\n' >"$TMPDR/design/a.txt"
out=$(
    cd "$TMPDR" && bash "$PUBLISH" --design-tmpdir "$TMPDR/design" --run-id "RUN1AB" --issue 9 --dry-run
)
[[ "$out" == *"PUBLISH_OK=true"* ]] || fail "dry-run missing PUBLISH_OK=true: $out"

echo "=== invalid run-id ==="
out=$(
    (cd "$TMPDR" && bash "$PUBLISH" --design-tmpdir "$TMPDR/design" --run-id '../bad' --issue 9) 2>/dev/null || true
)
[[ "$out" == *"PUBLISH_OK=false"* ]] || fail "bad slug should fail: $out"

echo "=== happy path + sidecar trim + render-cache ==="
TMP=$(mktemp -d "${TMPDIR:-/tmp}/tdlp.XXXXXX")
trap 'rm -rf "$TMP" "$TMPDR"' EXIT
clone=$(setup_clone_with_origin_head "$TMP")
stub="$TMP/stub"
GH_STUB_LOG="$TMP/gh.log"
: >"$GH_STUB_LOG"
export GH_STUB_LOG
make_gh_stub "$stub"
export PATH="$stub:$PATH"
export TEST_CLONE_ROOT="$clone"
export TEST_MERGE_BRANCH="larch-log-design-RUNPUB1"

mkdir -p "$TMP/design/render-cache/nested"
printf 'body\n' >"$TMP/design/plan.txt"
printf 'CMD_JSON=["secret"]\nkeep\n' >"$TMP/design/out.txt.meta"
printf '{"ok":1,"result":{"token":"x"}}\n' >"$TMP/design/voter-output-1.json"
printf 'deep\n' >"$TMP/design/render-cache/nested/c.txt"

(
    cd "$clone" || exit 1
    out=$(bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNPUB1" --issue 42 --repo owner/repo)
    [[ "$out" == *"PUBLISH_OK=true"* ]] || fail "happy PUBLISH_OK: $out"
    [[ "$out" == *"PR_NUMBER=101"* ]] || fail "happy PR_NUMBER: $out"
)

git -C "$clone" pull -q origin main
[[ -f "$clone/larch-logs/design/RUNPUB1/plan.txt" ]] || fail "plan.txt missing on main"
[[ -f "$clone/larch-logs/design/RUNPUB1/render-cache/nested/c.txt" ]] || fail "render-cache nested missing"
grep -q '^keep$' "$clone/larch-logs/design/RUNPUB1/out.txt.meta" || fail "meta trim failed"
! grep -q CMD_JSON "$clone/larch-logs/design/RUNPUB1/out.txt.meta" || fail "CMD_JSON should be stripped"
! grep -q '"result"' "$clone/larch-logs/design/RUNPUB1/voter-output-1.json" || fail ".result should be stripped"
grep -qE '"ok"[[:space:]]*:[[:space:]]*1' "$clone/larch-logs/design/RUNPUB1/voter-output-1.json" || fail "json body missing"
grep -q 'pr create' "$GH_STUB_LOG" || fail "expected gh pr create in log"
grep -q 'pr merge' "$GH_STUB_LOG" || fail "expected gh pr merge in log"

echo "=== trim fail-closed on bad json sidecar ==="
TMP2=$(mktemp -d "${TMPDIR:-/tmp}/tdlp2.XXXXXX")
clone2=$(setup_clone_with_origin_head "$TMP2")
stub2="$TMP2/stub"
make_gh_stub "$stub2"
export PATH="$stub2:$PATH"
unset TEST_CLONE_ROOT TEST_MERGE_BRANCH
mkdir -p "$TMP2/design"
printf 'not-json' >"$TMP2/design/bad-output-x.json"
out2=$(
    (cd "$clone2" && bash "$PUBLISH" --design-tmpdir "$TMP2/design" --run-id "RUNBAD1" --issue 1 --repo owner/repo) 2>/dev/null || true
)
[[ "$out2" == *"PUBLISH_OK=false"* ]] || fail "bad json should fail publish: $out2"

echo "All design-log-publish harness assertions passed."
