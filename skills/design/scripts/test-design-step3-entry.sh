#!/usr/bin/env bash
# test-design-step3-entry.sh — scope-anchor materialization harness for design-step3-entry.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
ENTRY="$ROOT/skills/design/scripts/design-step3-entry.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

prepare_entry_tmpdir() {
  local d="$1"
  printf 'plan body\n' >"$d/plan.txt"
  : >"$d/.step3-entry-plan-printed"
}

D_OK=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-ok.XXXXXX")
prepare_entry_tmpdir "$D_OK"
cat >"$D_OK/issue-body.txt" <<'EOF'
Feature request text
<!-- larch:plan:start -->
old plan
<!-- larch:plan:end -->
EOF
set +e
env CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_OK" ISSUE_NUMBER=9 ISSUE_TITLE='Feature' \
  "$ENTRY" 2>"$D_OK/stderr.log"
ok_rc=$?
set -e
[[ "$ok_rc" -eq 0 ]] || fail "entry ok rc=$ok_rc stderr=$(cat "$D_OK/stderr.log")"
grep -Fq 'Feature request text' "$D_OK/plan-review-scope-anchor.txt" || fail 'successful entry must write stripped scope anchor'
rm -rf "$D_OK"
pass 'Step 3 entry writes scope anchor from stripped issue body'

D_REENTRY=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-reentry.XXXXXX")
prepare_entry_tmpdir "$D_REENTRY"
printf 'stale aggregate pool\n' >"$D_REENTRY/oos-aggregate-pool.md"
cat >"$D_REENTRY/issue-body.txt" <<'EOF'
Feature request text
EOF
set +e
env CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_REENTRY" ISSUE_NUMBER=9 ISSUE_TITLE='Feature' \
  "$ENTRY" --reentry 2>"$D_REENTRY/stderr.log"
reentry_rc=$?
set -e
[[ "$reentry_rc" -eq 0 ]] || fail "entry reentry rc=$reentry_rc stderr=$(cat "$D_REENTRY/stderr.log")"
if [[ -s "$D_REENTRY/oos-aggregate-pool.md" ]]; then
  fail 'reentry must remove or empty stale oos-aggregate-pool.md'
fi
rm -rf "$D_REENTRY"
pass 'Step 3 reentry resets stale OOS aggregate pool'

D_EMPTY=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-empty.XXXXXX")
prepare_entry_tmpdir "$D_EMPTY"
cat >"$D_EMPTY/issue-body.txt" <<'EOF'
<!-- larch:plan:start -->
old plan only
<!-- larch:plan:end -->
EOF
printf 'raw feature-description with plan\n' >"$D_EMPTY/feature-description.txt"
set +e
empty_out=$(env CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_EMPTY" ISSUE_NUMBER=9 \
  "$ENTRY" 2>"$D_EMPTY/stderr.log")
empty_rc=$?
set -e
[[ "$empty_rc" -eq 1 ]] || fail "entry empty rc=$empty_rc stdout=$empty_out stderr=$(cat "$D_EMPTY/stderr.log")"
grep -Fxq 'SUMMARY_OUTCOME=failed-judge-panel' <<<"$empty_out" || fail 'empty anchor should emit failed-judge-panel summary'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$empty_out" || fail 'empty anchor should emit panel-init-failed envelope'
if [[ -f "$D_EMPTY/plan-review-scope-anchor.txt" ]] && grep -Fq 'raw feature-description' "$D_EMPTY/plan-review-scope-anchor.txt"; then
  fail 'plan-only issue must not fall back to raw feature-description.txt'
fi
rm -rf "$D_EMPTY"
pass 'Step 3 entry aborts empty stripped body without feature-description fallback'

pass 'design-step3-entry.sh checks passed'
