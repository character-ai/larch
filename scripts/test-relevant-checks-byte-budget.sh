#!/usr/bin/env bash
# Regression harness for run-relevant-checks-captured.sh green-path stdout.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HELPER="$REPO_ROOT/scripts/run-relevant-checks-captured.sh"

if [[ ! -x "$HELPER" ]]; then
    echo "FAIL: helper not executable: $HELPER" >&2
    exit 1
fi

tmp=$(mktemp -d "${TMPDIR:-/tmp}/test relevant checks byte budget.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

mode_of() {
    # Linux GNU stat: -c %a (octal). BSD/macOS stat: -f %Lp (low 12 bits octal).
    # Prefer GNU first because Linux is the CI host and BSD's %Lp is ambiguous
    # under GNU (--file-system mode dumps fs metadata regardless of format).
    stat -c %a "$1" 2>/dev/null || stat -f %Lp "$1"
}

fixture_repo="$tmp/repo"
mkdir -p "$fixture_repo/scripts"
cat > "$fixture_repo/scripts/relevant-checks.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
echo "=== Running pre-commit on 1 changed file(s) ==="
for n in $(seq 1 300); do
    echo "verbose validation output $n"
done
echo "=== Running agent-lint ==="
echo "agent lint ok"
SCRIPT
chmod +x "$fixture_repo/scripts/relevant-checks.sh"

xdg="$tmp/a a a/cache root with spaces and an intentionally long path segment"
session="$xdg/larch/sessions/claude-implement-repo-ABC123"
mkdir -p "$session"

old_umask=$(umask)
umask 000
out=$(XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$session")
umask "$old_umask"

[[ "$out" == RELEVANT_CHECKS_OK=true* ]] || fail "success line missing: $out"
[[ "$out" == *"COVERAGE=full"* ]] || fail "coverage not full: $out"
[[ "$out" != *"LOG="* && "$out" != *"LOG_FILE="* ]] || fail "success leaked log token: $out"

bytes=$(printf '%s\n' "$out" | wc -c | tr -d '[:space:]')
(( bytes <= 120 )) || fail "success stdout too large: $bytes bytes: $out"

log_dir="$session/relevant-checks"
log_file="$log_dir/step3-1.log"
[[ -d "$log_dir" ]] || fail "log dir missing"
[[ -f "$log_file" ]] || fail "captured log missing"
[[ "$(mode_of "$log_dir")" == "700" ]] || fail "log dir mode not 700: $(mode_of "$log_dir")"
[[ "$(mode_of "$log_file")" == "600" ]] || fail "log file mode not 600: $(mode_of "$log_file")"

repo_skip="$tmp/repo-skip"
mkdir -p "$repo_skip"
out=$(XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$repo_skip" "$HELPER" --site step5-review-fixes --tmpdir "$session")
[[ "$out" == RELEVANT_CHECKS_SKIPPED=true* ]] || fail "skip line missing: $out"
bytes=$(printf '%s\n' "$out" | wc -c | tr -d '[:space:]')
(( bytes <= 120 )) || fail "skip stdout too large: $bytes bytes: $out"

echo "test-relevant-checks-byte-budget: ok"
