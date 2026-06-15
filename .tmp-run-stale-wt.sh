#!/usr/bin/env bash
set -euo pipefail
export LARCH_QUIET_DISABLE=1
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/test-design-log-publish.sh
source <(sed -n '1,380p' "$REPO_ROOT/scripts/test-design-log-publish.sh" | grep -v '^echo ')
PUBLISH="$REPO_ROOT/scripts/design-log-publish.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }

echo "=== stale same-RUN_ID temp worktree cleanup allows second publish ==="
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
stale_wt=$(mktemp -d "${TMPDIR:-/tmp}/design-log-publish.stale.XXXXXX")
git -C "$clone_stalewt" worktree add -q "$stale_wt" "$branch_stalewt"
mkdir -p "$TMPSTALEWT/design"
printf 'plan body\n' >"$TMPSTALEWT/design/plan.txt"
out_stalewt=$(
    (cd "$clone_stalewt" && bash "$PUBLISH" --design-tmpdir "$TMPSTALEWT/design" --run-id "RUNSTALEWT1" --issue 4 --repo owner/repo) 2>"$TMPSTALEWT/publish.stderr" || true
)
echo "$out_stalewt"
[[ "$out_stalewt" == *"PUBLISH_OK=true"* ]] || fail "stale worktree cleanup publish should succeed: $out_stalewt stderr=$(cat "$TMPSTALEWT/publish.stderr")"
if git -C "$clone_stalewt" worktree list | grep -Fq 'design-log-publish.'; then
    fail "stale design-log-publish worktree should be removed: $(git -C "$clone_stalewt" worktree list)"
fi
echo PASS
