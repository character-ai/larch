#!/usr/bin/env bash
# Regression coverage for git-push.sh retry exit propagation.
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

repo="$TMPROOT/repo"
stub_bin="$TMPROOT/bin"
mkdir -p "$repo" "$stub_bin"

"$REAL_GIT" -C "$repo" init -q
"$REAL_GIT" -C "$repo" config user.email "larch-test@example.invalid"
"$REAL_GIT" -C "$repo" config user.name "Larch Test"
"$REAL_GIT" -C "$repo" checkout -b feature >/dev/null 2>&1
printf 'probe\n' > "$repo/probe.txt"
"$REAL_GIT" -C "$repo" add probe.txt
"$REAL_GIT" -C "$repo" commit -m "probe" -q

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
    ATTEMPTS_FILE="$TMPROOT/push-attempts.txt" \
    REAL_GIT="$REAL_GIT" \
    PATH="$stub_bin:$PATH" \
        bash "$SCRIPT"
) >"$TMPROOT/stdout.log" 2>"$TMPROOT/stderr.log"
rc=$?
set -e

[[ "$rc" == "7" ]] || fail "expected git-push.sh to exit 7 after failed pushes, got $rc"
[[ "$(cat "$TMPROOT/push-attempts.txt")" == "3" ]] || fail "expected 3 push attempts"
grep -Fqx 'BRANCH=feature' "$TMPROOT/stdout.log" || fail "expected BRANCH=feature on stdout"

echo "PASS: test-git-push.sh"
