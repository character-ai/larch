#!/usr/bin/env bash
# Regression coverage for rebase-push.sh lease-race recovery.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/rebase-push.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-rebase-push.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

stub_bin="$TMPROOT/bin"
mkdir -p "$stub_bin"
: > "$TMPROOT/git.log"

cat > "$stub_bin/git" <<'SH'
#!/usr/bin/env bash
set -u
LOG_FILE="${LOG_FILE:?}"
STATE_DIR="${STATE_DIR:?}"
printf '%s\n' "$*" >> "$LOG_FILE"

case "${1:-}" in
    symbolic-ref)
        if [[ "${2:-}" == "--quiet" && "${3:-}" == "HEAD" ]]; then
            exit 0
        fi
        ;;
    branch)
        if [[ "${2:-}" == "--show-current" ]]; then
            printf 'feature\n'
            exit 0
        fi
        ;;
    fetch)
        exit 0
        ;;
    merge-base)
        exit 1
        ;;
    rebase)
        exit 0
        ;;
    push)
        count=0
        if [[ -f "$STATE_DIR/push-count" ]]; then
            count=$(cat "$STATE_DIR/push-count")
        fi
        count=$((count + 1))
        printf '%s\n' "$count" > "$STATE_DIR/push-count"
        exit 1
        ;;
    rev-parse)
        case "${2:-}" in
            HEAD)
                printf 'abc123\n'
                exit 0
                ;;
            origin/feature)
                printf 'abc123\n'
                exit 0
                ;;
        esac
        ;;
esac

echo "unexpected git invocation: $*" >&2
exit 99
SH
chmod +x "$stub_bin/git"

cat > "$stub_bin/sleep" <<'SH'
#!/usr/bin/env bash
echo "sleep should not be called" >&2
exit 98
SH
chmod +x "$stub_bin/sleep"

set +e
LOG_FILE="$TMPROOT/git.log" \
STATE_DIR="$TMPROOT" \
PATH="$stub_bin:$PATH" \
    bash "$SCRIPT" >"$TMPROOT/stdout.log" 2>"$TMPROOT/stderr.log"
rc=$?
set -e

[[ "$rc" == "0" ]] || fail "expected lease-race recovery to exit 0, got $rc ($(cat "$TMPROOT/stderr.log"))"
[[ "$(cat "$TMPROOT/push-count")" == "1" ]] || fail "expected only one push attempt when remote already matches local"
grep -Fqx 'fetch origin feature --quiet' "$TMPROOT/git.log" || fail "expected branch refresh after failed push"
if grep -Fq 'sleep should not be called' "$TMPROOT/stderr.log"; then
    fail "sleep should not run when refresh shows the push already landed"
fi

echo "PASS: test-rebase-push-force-lease.sh"
