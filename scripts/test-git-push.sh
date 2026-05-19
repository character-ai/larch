#!/usr/bin/env bash
# Regression coverage for git-push.sh retry exit propagation and stderr dedup.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/git-push.sh"
REAL_GIT="$(command -v git)"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-git-push.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

setup_repo() {
    local r="$1"
    mkdir -p "$r"
    "$REAL_GIT" -C "$r" init -q
    "$REAL_GIT" -C "$r" config user.email "larch-test@example.invalid"
    "$REAL_GIT" -C "$r" config user.name "Larch Test"
    "$REAL_GIT" -C "$r" checkout -b feature >/dev/null 2>&1
    printf 'probe\n' > "$r/probe.txt"
    "$REAL_GIT" -C "$r" add probe.txt
    "$REAL_GIT" -C "$r" commit -m "probe" -q
}

# --- Test 1: exit code propagation (original coverage) ---

repo="$TMPROOT/repo1"
stub_bin="$TMPROOT/bin1"
mkdir -p "$stub_bin"
setup_repo "$repo"

cat > "$stub_bin/git" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
REAL_GIT="${REAL_GIT:?}"
ATTEMPTS_FILE="${ATTEMPTS_FILE:?}"
if [[ "${1:-}" == "push" ]]; then
    count=0
    if [[ -f "$ATTEMPTS_FILE" ]]; then
        count=$(cat "$ATTEMPTS_FILE")
    fi
    count=$((count + 1))
    printf '%s\n' "$count" > "$ATTEMPTS_FILE"
    exit 7
fi
exec "$REAL_GIT" "$@"
SH
chmod +x "$stub_bin/git"

cat > "$stub_bin/sleep" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$stub_bin/sleep"

set +e
(
    cd "$repo"
    ATTEMPTS_FILE="$TMPROOT/push1-attempts.txt" \
    REAL_GIT="$REAL_GIT" \
    PATH="$stub_bin:$PATH" \
        bash "$SCRIPT"
) >"$TMPROOT/stdout1.log" 2>"$TMPROOT/stderr1.log"
rc=$?
set -e

[[ "$rc" == "7" ]] || fail "Test 1: expected git-push.sh to exit 7 after failed pushes, got $rc"
[[ "$(cat "$TMPROOT/push1-attempts.txt")" == "3" ]] || fail "Test 1: expected 3 push attempts"
grep -Fqx 'BRANCH=feature' "$TMPROOT/stdout1.log" || fail "Test 1: expected BRANCH=feature on stdout"

# --- Test 2: stderr deduplication — 3 identical blocks → emitted once with "(repeated 3 times)" ---

repo2="$TMPROOT/repo2"
stub_bin2="$TMPROOT/bin2"
mkdir -p "$stub_bin2"
setup_repo "$repo2"

# Stub git push: emits a fixed two-line stderr block on each attempt
cat > "$stub_bin2/git" <<'SH'
#!/usr/bin/env bash
REAL_GIT="${REAL_GIT:?}"
if [[ "${1:-}" == "push" ]]; then
    printf '! [rejected] main -> main (non-fast-forward)\nerror: failed to push some refs\n' >&2
    exit 1
fi
exec "$REAL_GIT" "$@"
SH
chmod +x "$stub_bin2/git"

cat > "$stub_bin2/sleep" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$stub_bin2/sleep"

set +e
(
    cd "$repo2"
    REAL_GIT="$REAL_GIT" \
    PATH="$stub_bin2:$PATH" \
        bash "$SCRIPT"
) >"$TMPROOT/stdout2.log" 2>"$TMPROOT/stderr2.log"
rc=$?
set -e

# Verify the rejection text appears exactly once in stderr
rejection_count=$(grep -c 'non-fast-forward' "$TMPROOT/stderr2.log" || true)
[[ "$rejection_count" -eq 1 ]] || fail "Test 2: expected rejection text exactly once, got $rejection_count times"

# Verify the repeated annotation is present
grep -Fq '(repeated 3 times)' "$TMPROOT/stderr2.log" || fail "Test 2: expected '(repeated 3 times)' annotation in stderr"

echo "PASS: test-git-push.sh"
