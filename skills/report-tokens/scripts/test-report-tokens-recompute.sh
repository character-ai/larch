#!/usr/bin/env bash
# test-report-tokens-recompute.sh — /report-tokens shows reported vs estimated columns (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd -P)"
FIX_SRC="$REPO/skills/report-tokens/scripts/fixtures/recompute-run"
RUN_DIR="$REPO/larch-logs/implement/AAAA-report-tokens-recompute-fixture"
DESIGN_RUN="$REPO/larch-logs/design/BBBB-report-tokens-design-fixture"
DESIGN_MISSING_RUN="$REPO/larch-logs/design/CCCC-report-tokens-design-missing-fixture"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

# Avoid inheriting a parent Claude quiet-session FD contract (this harness runs under CI / tools).
unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG \
    LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_DISABLE 2>/dev/null || true
export LARCH_QUIET_DISABLE=1
unset LARCH_BREADCRUMB_STREAM LARCH_BREADCRUMBS_SURFACED_FILE 2>/dev/null || true

export LARCH_REPORT_TOKENS_REPO="${LARCH_REPORT_TOKENS_REPO:-fixture/local}"

PLOT_FROM_ERR=""
MISSING_SKILL_ERR=""
BAD_SKILL_ERR=""
cleanup() {
    rm -rf "$RUN_DIR" "$DESIGN_RUN" "$DESIGN_MISSING_RUN" "${GH_STUB_DIR:-}" "${GH_DESIGN_STUB:-}"
    rm -f "${PLOT_FROM_ERR:-}" "${MISSING_SKILL_ERR:-}" "${BAD_SKILL_ERR:-}"
}
trap cleanup EXIT
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR"
cp "$FIX_SRC/manifest.json" "$FIX_SRC/token-report.json" "$RUN_DIR/"

export CLAUDE_PLUGIN_ROOT="$REPO"
export LARCH_REPORT_TOKENS_NO_ISSUE=1
export LARCH_REPORT_TOKENS_NO_PLOT=1
export LARCH_REPORT_TOKENS_LIMIT=500

out=$("$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill implement)

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
    title=""
    if [[ "$*" == *" --body "* ]]; then
        printf 'inline --body is forbidden: %s\n' "$*" >&2
        exit 1
    fi
    for ((i = 1; i <= $#; i++)); do
        if [[ "${!i}" == "--title" ]]; then
            next=$((i + 1))
            title="${!next:-}"
        fi
    done
    [[ "$title" == "[Implement Analysis Report]"* ]] || {
        printf 'unexpected title: %s\n' "$title" >&2
        exit 1
    }
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
PATH="$GH_STUB_DIR:$PATH" GH_STUB_LOG="$GH_STUB_LOG" "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill implement >/dev/null
grep -Fq -- '--body-file' "$GH_STUB_LOG" || fail "expected gh issue create --body-file in log"
! grep -Eq '(^| )--body( |$)' "$GH_STUB_LOG" || fail "gh issue create should not use inline --body" # lint-gh-body-inline: ok gh-stub assertion fixture
pass 'issue creation uses body-file with redacted tmpdir content'

rm -rf "$DESIGN_RUN"
mkdir -p "$DESIGN_RUN"
cp "$FIX_SRC/manifest.json" "$DESIGN_RUN/"
cp "$FIX_SRC/token-report.json" "$DESIGN_RUN/token-report-final.json"
printf '%s\n' '{"workflow_path":"HARD"}' > "$DESIGN_RUN/timing-report-final.json"
design_out=$(LARCH_REPORT_TOKENS_NO_ISSUE=1 LARCH_REPORT_TOKENS_NO_PLOT=1 \
    "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill design)
case "$design_out" in
    *'#999001'*) pass 'design --skill reads -final suffixed token report' ;;
    *) fail "design scan missing fixture issue #999001";;
esac

rm -rf "$DESIGN_MISSING_RUN"
mkdir -p "$DESIGN_MISSING_RUN"
cp "$FIX_SRC/manifest.json" "$DESIGN_MISSING_RUN/"
design_skip_out=$(LARCH_REPORT_TOKENS_NO_ISSUE=1 LARCH_REPORT_TOKENS_NO_PLOT=1 \
    "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill design)
case "$design_skip_out" in
    *'#999001'*) pass 'design run with manifest but no token-report-final.json skips cleanly' ;;
    *) fail "design scan should still succeed when another design run is missing token-report-final.json";;
esac

GH_DESIGN_STUB=$(mktemp -d "${TMPDIR:-/tmp}/test-report-tokens-design-gh.XXXXXX")
GH_DESIGN_LOG="$GH_DESIGN_STUB/gh.log"
cat >"$GH_DESIGN_STUB/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${GH_DESIGN_LOG:?}"
if [[ "${1:-}" == "issue" && "${2:-}" == "create" ]]; then
    title=""
    body_file=""
    for ((i = 1; i <= $#; i++)); do
        if [[ "${!i}" == "--title" ]]; then
            next=$((i + 1))
            title="${!next:-}"
        fi
        if [[ "${!i}" == "--body-file" ]]; then
            next=$((i + 1))
            body_file="${!next:-}"
        fi
    done
    [[ "$title" == "[Design Analysis Report]"* ]] || { printf 'unexpected title: %s\n' "$title" >&2; exit 1; }
    [[ -f "$body_file" ]] || { printf 'body file missing: %s\n' "$body_file" >&2; exit 1; }
    printf 'https://github.com/fixture/local/issues/999998\n'
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$GH_DESIGN_STUB/gh"
PATH="$GH_DESIGN_STUB:$PATH" GH_DESIGN_LOG="$GH_DESIGN_LOG" \
    LARCH_REPORT_TOKENS_NO_PLOT=1 "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill design >/dev/null
grep -Fq -- '--title [Design Analysis Report]' "$GH_DESIGN_LOG" || fail "expected design issue title prefix in gh log"
pass 'issue creation uses design-prefixed analysis report title'
rm -rf "$DESIGN_RUN"
rm -rf "$GH_DESIGN_STUB"

GH_PLOT_STUB=$(mktemp -d "${TMPDIR:-/tmp}/test-report-tokens-plot.XXXXXX")
cat >"$GH_PLOT_STUB/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "issue" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"title":"[Analysis Report] legacy","body":"## Raw per-issue data\n\n```json\n[]\n```\n"}'
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$GH_PLOT_STUB/gh"
set +e
PATH="$GH_PLOT_STUB:$PATH" LARCH_REPORT_TOKENS_NO_PLOT=1 \
    "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill design --plot-from 42 >/dev/null 2>"$GH_PLOT_STUB/err.txt"
plot_rc=$?
set -e
if [ "$plot_rc" -ne 0 ] && grep -q 'does not match --skill=design' "$GH_PLOT_STUB/err.txt" 2>/dev/null; then
    pass '--plot-from cross-skill title mismatch rejected for design'
else
    fail "expected design --plot-from legacy implement title rejection (rc=$plot_rc)"
fi
rm -rf "$GH_PLOT_STUB"

GH_PLOT_IMPL_STUB=$(mktemp -d "${TMPDIR:-/tmp}/test-report-tokens-plot-impl.XXXXXX")
cat >"$GH_PLOT_IMPL_STUB/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "issue" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"title":"[Analysis Report] legacy","body":"## Raw per-issue data\n\n```json\n[]\n```\n"}'
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$GH_PLOT_IMPL_STUB/gh"
plot_impl_out=$(PATH="$GH_PLOT_IMPL_STUB:$PATH" LARCH_REPORT_TOKENS_NO_PLOT=1 \
    "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill implement --plot-from 42)
case "$plot_impl_out" in
    *'No plots generated.'*) pass '--plot-from implement accepts legacy analysis-report title' ;;
    *) fail "expected implement --plot-from legacy title compatibility";;
esac
rm -rf "$GH_PLOT_IMPL_STUB"

GH_PLOT_IMPL_MISMATCH=$(mktemp -d "${TMPDIR:-/tmp}/test-report-tokens-plot-impl-mismatch.XXXXXX")
cat >"$GH_PLOT_IMPL_MISMATCH/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "issue" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"title":"[Design Analysis Report] design-only","body":"## Raw per-issue data\n\n```json\n[]\n```\n"}'
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$GH_PLOT_IMPL_MISMATCH/gh"
set +e
PATH="$GH_PLOT_IMPL_MISMATCH:$PATH" LARCH_REPORT_TOKENS_NO_PLOT=1 \
    "$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill implement --plot-from 42 >/dev/null 2>"$GH_PLOT_IMPL_MISMATCH/err.txt"
plot_impl_mismatch_rc=$?
set -e
if [ "$plot_impl_mismatch_rc" -ne 0 ] && grep -q 'does not match --skill=implement' "$GH_PLOT_IMPL_MISMATCH/err.txt" 2>/dev/null; then
    pass '--plot-from implement rejects design-prefixed analysis-report title'
else
    fail "expected implement --plot-from design title rejection (rc=$plot_impl_mismatch_rc)"
fi
rm -rf "$GH_PLOT_IMPL_MISMATCH"

PLOT_FROM_ERR=$(mktemp "${TMPDIR:-/tmp}/report-tokens-bad-plot-from.XXXXXX")
MISSING_SKILL_ERR=$(mktemp "${TMPDIR:-/tmp}/report-tokens-missing-skill.XXXXXX")
BAD_SKILL_ERR=$(mktemp "${TMPDIR:-/tmp}/report-tokens-bad-skill.XXXXXX")

set +e
"$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill implement --plot-from nope >/dev/null 2>"$PLOT_FROM_ERR"
bad_plot_from_rc=$?
set -e
if [ "$bad_plot_from_rc" -ne 0 ] && grep -q -- '--plot-from must be a decimal issue number' "$PLOT_FROM_ERR"; then
    pass 'non-numeric --plot-from rejected'
else
    fail "expected non-numeric --plot-from rejection (rc=$bad_plot_from_rc)"
fi

set +e
"$REPO/skills/report-tokens/scripts/run-analysis.sh" >/dev/null 2>"$MISSING_SKILL_ERR"
missing_skill_rc=$?
set -e
if [ "$missing_skill_rc" -ne 0 ] && grep -q -- '--skill is required' "$MISSING_SKILL_ERR"; then
    pass 'missing --skill rejected'
else
    fail "expected missing --skill rejection (rc=$missing_skill_rc)"
fi

set +e
"$REPO/skills/report-tokens/scripts/run-analysis.sh" --skill bogus >/dev/null 2>"$BAD_SKILL_ERR"
bad_skill_rc=$?
set -e
if [ "$bad_skill_rc" -ne 0 ] && grep -q -- '--skill must be design or implement' "$BAD_SKILL_ERR"; then
    pass 'invalid --skill rejected'
else
    fail "expected invalid --skill rejection (rc=$bad_skill_rc)"
fi

printf 'PASS: test-report-tokens-recompute.sh\n'
