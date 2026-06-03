#!/usr/bin/env bash
# Regression harness for scripts/ci-status.sh base-ref and empty-check behavior.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-ci-status.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

test_scripts="$TMPROOT/scripts"
mkdir -p "$test_scripts"
cp "$REPO_ROOT/scripts/ci-status.sh" "$test_scripts/"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$test_scripts/"
cat > "$test_scripts/ci-behind-count.sh" <<'BEHIND'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${BEHIND_LOG:?}"
echo "BEHIND_COUNT=${BEHIND_STUB:-0}"
BEHIND
chmod +x "$test_scripts/ci-behind-count.sh"
SCRIPT="$test_scripts/ci-status.sh"

stub_dir="$TMPROOT/bin"
mkdir -p "$stub_dir"
cat > "$stub_dir/git" <<'GIT'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${GIT_LOG:?}"
case "$1" in
    fetch) exit 0 ;;
    rev-list) echo "${BEHIND_STUB:-0}"; exit 0 ;;
    log) exit 0 ;;
esac
echo "unexpected git command: $*" >&2
exit 2
GIT
chmod +x "$stub_dir/git"
cat > "$stub_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${GH_LOG:?}"
case "$1 $2" in
    "pr view")
        if [[ "${MERGE_STATE_STUB:-CLEAN}" == "__EMPTY__" ]]; then
            printf '{"state":"%s","mergeStateStatus":null}\n' "${PR_STATE_STUB:-OPEN}"
        else
            printf '{"state":"%s","mergeStateStatus":"%s"}\n' "${PR_STATE_STUB:-OPEN}" "${MERGE_STATE_STUB:-CLEAN}"
        fi
        exit 0
        ;;
    "pr checks") printf '%s\n' "${CHECKS_JSON:-[]}"; exit 0 ;;
esac
echo "unexpected gh command: $*" >&2
exit 2
GH
chmod +x "$stub_dir/gh"
cat > "$stub_dir/sleep" <<'SLEEP'
#!/usr/bin/env bash
exit 0
SLEEP
chmod +x "$stub_dir/sleep"

out=$(GH_LOG="$TMPROOT/gh1.log" GIT_LOG="$TMPROOT/git1.log" PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo)
grep -Fxq 'CI_STATUS=pending' <<<"$out" || fail "empty checks without grace should be pending"
grep -Fxq 'CONFLICTED=false' <<<"$out" || fail "CONFLICTED line must be emitted (default CLEAN)"

out=$(GH_LOG="$TMPROOT/gh2.log" GIT_LOG="$TMPROOT/git2.log" BEHIND_LOG="$TMPROOT/behind2.log" PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo --base-remote upstream --base-ref main --empty-checks-grace 30)
grep -Fxq 'CI_STATUS=NO_CHECKS' <<<"$out" || fail "empty checks after grace should be NO_CHECKS"
grep -Fxq 'CONFLICTED=false' <<<"$out" || fail "CONFLICTED line must be emitted after grace"
grep -Fq 'fetch upstream main --quiet' "$TMPROOT/git2.log" || fail "base remote/ref not used for fetch"
grep -Fq -- '--base-remote upstream --base-ref main --no-fetch' "$TMPROOT/behind2.log" || fail "ci-behind-count.sh not delegated for behind count"

out=$(GH_LOG="$TMPROOT/gh-dirty.log" GIT_LOG="$TMPROOT/git-dirty.log" MERGE_STATE_STUB=DIRTY PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo)
grep -Fxq 'CONFLICTED=true' <<<"$out" || fail "DIRTY mergeStateStatus should emit CONFLICTED=true"

out=$(GH_LOG="$TMPROOT/gh-behind.log" GIT_LOG="$TMPROOT/git-behind.log" MERGE_STATE_STUB=BEHIND PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo)
grep -Fxq 'CONFLICTED=false' <<<"$out" || fail "BEHIND mergeStateStatus should emit CONFLICTED=false"

out=$(GH_LOG="$TMPROOT/gh-unknown.log" GIT_LOG="$TMPROOT/git-unknown.log" MERGE_STATE_STUB=UNKNOWN PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo)
grep -Fxq 'CONFLICTED=true' <<<"$out" || fail "UNKNOWN mergeStateStatus should emit CONFLICTED=true"

out=$(GH_LOG="$TMPROOT/gh-empty.log" GIT_LOG="$TMPROOT/git-empty.log" MERGE_STATE_STUB=__EMPTY__ PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo)
grep -Fxq 'CONFLICTED=true' <<<"$out" || fail "empty mergeStateStatus should emit CONFLICTED=true"

echo "PASS: test-ci-status.sh"
