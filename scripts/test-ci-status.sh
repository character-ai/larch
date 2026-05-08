#!/usr/bin/env bash
# Regression harness for scripts/ci-status.sh base-ref and empty-check behavior.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/ci-status.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-ci-status.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

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
    "pr view") echo "OPEN"; exit 0 ;;
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

out=$(GH_LOG="$TMPROOT/gh2.log" GIT_LOG="$TMPROOT/git2.log" PATH="$stub_dir:$PATH" "$SCRIPT" --pr 7 --repo fork/repo --base-remote upstream --base-ref main --empty-checks-grace 30)
grep -Fxq 'CI_STATUS=NO_CHECKS' <<<"$out" || fail "empty checks after grace should be NO_CHECKS"
grep -Fq 'fetch upstream main --quiet' "$TMPROOT/git2.log" || fail "base remote/ref not used for fetch"
grep -Fq 'rev-list HEAD..upstream/main --count' "$TMPROOT/git2.log" || fail "base remote/ref not used for behind count"

echo "PASS: test-ci-status.sh"
