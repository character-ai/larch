#!/usr/bin/env bash
# test-render-final-summary-bash32.sh - Regression test for the Bash 3.2
# `note_args[@]: unbound variable` portability hazard in
# skills/design/scripts/render-final-summary.sh (issue #3039).
#
# render-final-summary.sh runs under `set -euo pipefail`. Before #3039,
# invoke_render expanded empty `render_cost_args` / `note_args` arrays directly
# at the render-run-summary.sh call site. On Bash 3.2 (macOS /bin/bash), an
# empty array expansion under nounset raises `arr[@]: unbound variable`. The
# fix uses the safe-empty `${ARR[@]+"${ARR[@]}"}` idiom from BASH_AUTHORING.md
# §3.
#
# This harness layers two checks:
#
#   Case 1 - Static idiom check (always runs): grep the guarded COST_ARGS copy
#     and the render-run-summary.sh invocation line. This is the Linux-CI
#     backstop because Bash 4.4+ no longer exhibits the bug at runtime.
#
#   Case 2 - Dynamic empty-array path (only under /bin/bash < 4.4): build a
#     minimal DESIGN_TMPDIR fixture, invoke the subject with post-publish output
#     disabled from issue mutation, and assert the redirected renderer stderr
#     does not contain `unbound variable` and no fallback warning was appended.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBJECT="$REPO_ROOT/skills/design/scripts/render-final-summary.sh"

PASS=0
FAIL=0
SKIP=0
FAILED=()
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-render-final-summary-bash32-XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

ok()    { PASS=$((PASS + 1)); echo "  ok: $1"; }
fail()  { FAIL=$((FAIL + 1)); FAILED+=("$1"); echo "  FAIL: $1" >&2; }
skipm() { SKIP=$((SKIP + 1)); echo "  SKIPPED: $1"; }

# --- Case 1: static idiom check (always runs) -------------------------------
# shellcheck disable=SC2016 # Literal regex; outer-shell expansion is intentionally suppressed.
if grep -q 'render_cost_args=(\${COST_ARGS\[@\]+"\${COST_ARGS\[@\]}"})' "$SUBJECT" \
   && grep -q '"\${_rr_args\[@\]}" \${render_cost_args\[@\]+"\${render_cost_args\[@\]}"} \${note_args\[@\]+"\${note_args\[@\]}"}' "$SUBJECT"; then
    ok "case 1: safe-empty array idiom present in invoke_render"
else
    fail "case 1: safe-empty array idiom missing in $SUBJECT - issue #3039 may have regressed"
fi

# --- Case 2: dynamic empty-array path under vulnerable bash (< 4.4) ---------
SYSTEM_BASH="/bin/bash"
BASH_MAJOR=""
BASH_MINOR=""
if [[ -x "$SYSTEM_BASH" ]]; then
    # shellcheck disable=SC2016 # Expanded by the inner /bin/bash, not by this harness.
    BASH_MAJOR="$("$SYSTEM_BASH" -c 'echo "${BASH_VERSINFO[0]}"' 2>/dev/null || echo "")"
    # shellcheck disable=SC2016
    BASH_MINOR="$("$SYSTEM_BASH" -c 'echo "${BASH_VERSINFO[1]}"' 2>/dev/null || echo "")"
fi

DYNAMIC_VULNERABLE="false"
if [[ "$BASH_MAJOR" == "3" ]]; then
    DYNAMIC_VULNERABLE="true"
elif [[ "$BASH_MAJOR" == "4" ]] && [[ -n "$BASH_MINOR" ]] && (( BASH_MINOR < 4 )); then
    DYNAMIC_VULNERABLE="true"
fi

if [[ "$DYNAMIC_VULNERABLE" != "true" ]]; then
    BASH_VER_DISPLAY="${BASH_MAJOR:-unknown}.${BASH_MINOR:-?}"
    skipm "case 2: bash $BASH_VER_DISPLAY at $SYSTEM_BASH (need < 4.4 for dynamic empty-array check; bash 4.4+ fixed the hazard)"
else
    D="$TMPROOT/design"
    mkdir -p "$D"
    cat >"$D/run-params.json" <<'JSON'
{"classification":"SIMPLE","workflow_path":"SIMPLE"}
JSON
    cat >"$D/voting-tally.md" <<'EOF'
# Tally
EOF
    cat >"$D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Example
- **Reviewer**: Codex-Pragmatic
- focus-area = correctness
- Concern: example
EOF
    : >"$D/oos-accepted-design.md"
    : >"$D/execution-issues.md"
    : >"$D/oos-issues-created.md"

    rc=0
    ISSUE_NUMBER="" SESSION_ID="TEST-BASH32-FIXTURE" DESIGN_TMPDIR="$D" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$SYSTEM_BASH" "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only \
        >"$TMPROOT/case2.stdout" 2>"$TMPROOT/case2.stderr" || rc=$?

    case2_ok="true"
    if [[ "$rc" -ne 0 ]]; then
        fail "case 2: subject exited rc=$rc under vulnerable /bin/bash"
        case2_ok="false"
    fi
    if [[ ! -s "$D/final-summary.md" ]]; then
        fail "case 2: final-summary.md missing or empty"
        case2_ok="false"
    fi
    if [[ -f "$D/render-final-summary.stderr.log" ]] && grep -q 'unbound variable' "$D/render-final-summary.stderr.log"; then
        fail "case 2: renderer stderr contains 'unbound variable' - Bash 3.2 hazard regressed"
        case2_ok="false"
    fi
    if grep -q 'render-run-summary' "$D/execution-issues.md"; then
        fail "case 2: render-run-summary warning appended - fallback path fired"
        case2_ok="false"
    fi
    if [[ "$case2_ok" == "true" ]]; then
        ok "case 2: empty arrays render under vulnerable /bin/bash without fallback"
    fi
fi

echo ""
echo "Summary: $PASS passed, $FAIL failed, $SKIP skipped"
if (( FAIL > 0 )); then
    echo "Failed cases:" >&2
    for t in "${FAILED[@]+"${FAILED[@]}"}"; do
        echo "  - $t" >&2
    done
    exit 1
fi
exit 0
