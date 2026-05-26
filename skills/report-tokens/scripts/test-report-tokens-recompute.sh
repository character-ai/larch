#!/usr/bin/env bash
# test-report-tokens-recompute.sh — /report-tokens shows reported vs estimated columns (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd -P)"
FIX_SRC="$REPO/skills/report-tokens/scripts/fixtures/recompute-run"
RUN_DIR="$REPO/larch-logs/implement/AAAA-report-tokens-recompute-fixture"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

# Avoid inheriting a parent Claude quiet-session FD contract (this harness runs under CI / tools).
unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG \
    LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_DISABLE 2>/dev/null || true
export LARCH_QUIET_DISABLE=1
unset LARCH_BREADCRUMB_STREAM LARCH_BREADCRUMBS_SURFACED_FILE 2>/dev/null || true

export LARCH_REPORT_TOKENS_REPO="${LARCH_REPORT_TOKENS_REPO:-fixture/local}"

cleanup() { rm -rf "$RUN_DIR" "${GH_STUB_DIR:-}"; }
trap cleanup EXIT
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR"
cp "$FIX_SRC/manifest.json" "$FIX_SRC/token-report.json" "$RUN_DIR/"

export CLAUDE_PLUGIN_ROOT="$REPO"
export LARCH_REPORT_TOKENS_NO_ISSUE=1
export LARCH_REPORT_TOKENS_NO_PLOT=1
export LARCH_REPORT_TOKENS_LIMIT=500

out=$("$REPO/skills/report-tokens/scripts/run-analysis.sh")

case "$out" in
    *'### Reported vs estimated'*) ;;
    *) fail "analysis output missing reported vs estimated section";;
esac
case "$out" in
    *'#999001'*) ;;
    *) fail "fixture issue #999001 not listed";;
esac
case "$out" in
    *'token-cost.sh'*) ;;
    *) fail "summary line should mention token-cost.sh";;
esac
pass 'fixture run surfaced in reported vs estimated table'

GH_STUB_DIR=$(mktemp -d "${TMPDIR:-/tmp}/test-report-tokens-gh.XXXXXX")
GH_STUB_LOG="$GH_STUB_DIR/gh.log"
cat >"$GH_STUB_DIR/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${GH_STUB_LOG:?}"
if [[ "${1:-}" == "issue" && "${2:-}" == "create" ]]; then
    if [[ "$*" == *" --body "* ]]; then
        printf 'inline --body is forbidden: %s\n' "$*" >&2
        exit 1
    fi
    body_file=""
    for ((i = 1; i <= $#; i++)); do
        if [[ "${!i}" == "--body-file" ]]; then
            next=$((i + 1))
            body_file="${!next:-}"
            break
        fi
    done
    [[ -n "$body_file" ]] || { printf 'missing --body-file: %s\n' "$*" >&2; exit 1; }
    [[ -f "$body_file" ]] || { printf 'body file missing: %s\n' "$body_file" >&2; exit 1; }
    grep -Fq '<TMPDIR>' "$body_file" || { printf 'tmpdir redaction missing\n' >&2; exit 1; }
    ! grep -Fq 'larch-report-tokens.' "$body_file" || { printf 'unredacted report tmpdir leaked\n' >&2; exit 1; }
    printf 'https://github.com/fixture/local/issues/999999\n'
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$GH_STUB_DIR/gh"

unset LARCH_REPORT_TOKENS_NO_ISSUE
PATH="$GH_STUB_DIR:$PATH" GH_STUB_LOG="$GH_STUB_LOG" "$REPO/skills/report-tokens/scripts/run-analysis.sh" >/dev/null
grep -Fq -- '--body-file' "$GH_STUB_LOG" || fail "expected gh issue create --body-file in log"
! grep -Eq '(^| )--body( |$)' "$GH_STUB_LOG" || fail "gh issue create should not use inline --body"
pass 'issue creation uses body-file with redacted tmpdir content'

printf 'PASS: test-report-tokens-recompute.sh\n'
