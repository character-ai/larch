#!/usr/bin/env bash
# test-write-final-report.sh — /fix-issue write-final-report harness.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-fix-wfr.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

plugin="$TMP_ROOT/plugin"
mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/"
cp "$REPO_ROOT/scripts/render-run-summary.sh" "$plugin/scripts/"
cp "$REPO_ROOT/scripts/token-cost.sh" "$plugin/scripts/"
chmod +x "$plugin/scripts/render-run-summary.sh" "$plugin/scripts/token-cost.sh"
cat > "$plugin/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
printf 'COMMENT_URL=https://ex.example/c\n'
STUB
chmod +x "$plugin/scripts/tracking-issue-summary.sh"

fixd="$TMP_ROOT/fix"
mkdir -p "$fixd"
printf 'ISSUE_NUMBER=3\nCLASSIFICATION=PR\nOUTCOME=closed-non-pr\n' > "$fixd/final-report-state.sh"
printf 'REPO=own/r\nREPO_UNAVAILABLE=false\n' > "$fixd/session-env.sh"
printf 'sid\n' > "$fixd/session-id"

out=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --fix-issue-tmpdir "$fixd" --print-stdout 2>/dev/null)
case "$out" in *'## /fix-issue'*) ;; *) printf 'FAIL: missing header\n' >&2; exit 1 ;; esac
case "$out" in *'closed-non-pr'*) ;; *) printf 'FAIL: missing outcome\n' >&2; exit 1 ;; esac

out2=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --outcome no-candidate --issue-number 0 --print-stdout 2>/dev/null)
case "$out2" in *'no-candidate'*) ;; *) printf 'FAIL: no-candidate\n' >&2; exit 1 ;; esac

printf 'PASS=2\n'
