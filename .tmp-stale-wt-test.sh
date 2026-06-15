#!/usr/bin/env bash
set -euo pipefail
export LARCH_QUIET_DISABLE=1
REPO_ROOT="/Users/zhupanov/larch7"
PUBLISH="$REPO_ROOT/scripts/design-log-publish.sh"
source /dev/null
# shellcheck source=scripts/test-design-log-publish.sh
# Run only stale worktree section by extracting helpers from full harness
fail() { echo "FAIL: $1" >&2; exit 1; }

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
    git --git-dir="$bare" symbolic-ref HEAD refs/heads/main
    git -C "$clone" remote set-head origin main
    printf '%s\n' "$clone"
}

make_gh_stub() {
    local d="$1"
    mkdir -p "$d"
    cp "$REPO_ROOT/scripts/test-design-log-publish.sh" "$d/parent.sh"
    # reuse stub from parent file - inline minimal stub
    cat >"$d/gh" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "pr" && "$2" == "create" ]]; then
  echo "https://github.com/owner/repo/pull/101"
  exit 0
fi
if [[ "$1" == "pr" && "$2" == "view" ]]; then
  echo "abc123"
  exit 0
fi
if [[ "$1" == "pr" && "$2" == "checks" ]]; then
  echo "all required checks passing"
  exit 0
fi
if [[ "$1" == "pr" && "$2" == "merge" ]]; then exit 0; fi
if [[ "$1" == "repo" && "$2" == "view" ]]; then echo "owner/repo"; exit 0; fi
exit 0
STUB
    chmod +x "$d/gh"
}

TMPSTALEWT=$(mktemp -d "${TMPDIR:-/tmp}/tdlp-stale-wt.XXXXXX")
trap 'rm -rf "$TMPSTALEWT"' EXIT
clone_stalewt=$(setup_clone_with_origin_head "$TMPSTALEWT")
stub_stalewt="$TMPSTALEWT/stub"
make_gh_stub "$stub_stalewt"
export PATH="$stub_stalewt:$PATH"
export TEST_CLONE_ROOT="$clone_stalewt"
export TEST_MERGE_BRANCH="larch-log-design-RUNSTALEWT1"
branch_stalewt="larch-log-design-RUNSTALEWT1"
git -C "$clone_stalewt" branch -q "$branch_stalewt"
stale_wt="$TMPSTALEWT/design-log-publish.stale"
git -C "$clone_stalewt" worktree add -q "$stale_wt" "$branch_stalewt"
mkdir -p "$TMPSTALEWT/design"
printf 'plan body\n' >"$TMPSTALEWT/design/plan.txt"
out_stalewt=$(cd "$clone_stalewt" && bash "$PUBLISH" --design-tmpdir "$TMPSTALEWT/design" --run-id "RUNSTALEWT1" --issue 4 --repo owner/repo 2>"$TMPSTALEWT/err" || true)
echo "$out_stalewt"
[[ "$out_stalewt" == *"PUBLISH_OK=true"* ]] || fail "stale worktree cleanup publish should succeed: $out_stalewt err=$(cat "$TMPSTALEWT/err")"
echo PASS
