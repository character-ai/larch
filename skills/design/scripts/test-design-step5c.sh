#!/usr/bin/env bash
# test-design-step5c.sh — offline harness for design-step5c publish-tail abort paths.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step5c.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step5c.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
STUB="$FAKE_PLUGIN/skills/design/scripts"
mkdir -p "$STUB" "$FAKE_PLUGIN/scripts" "$FAKE_PLUGIN/skills/implement/scripts"
ln -sf "$ROOT/python" "$FAKE_PLUGIN/python"
ln -sf "$ROOT/skills/design/scripts/design-stage-terminal-state.sh" "$STUB/design-stage-terminal-state.sh"
ln -sf "$ROOT/skills/implement/scripts/stall-recovery-report.sh" "$FAKE_PLUGIN/skills/implement/scripts/stall-recovery-report.sh"
ln -sf "$ROOT/scripts/lib-design-tmpdir.sh" "$FAKE_PLUGIN/scripts/lib-design-tmpdir.sh"
ln -sf "$ROOT/scripts/lib-quiet.sh" "$FAKE_PLUGIN/scripts/lib-quiet.sh"
ln -sf "$ROOT/scripts/lib-larch-dev-clone.sh" "$FAKE_PLUGIN/scripts/lib-larch-dev-clone.sh"
ln -sf "$ROOT/scripts/read-result-env.sh" "$FAKE_PLUGIN/scripts/read-result-env.sh"

cat >"$STUB/design-publish.sh" <<'STUB'
#!/usr/bin/env bash
printf 'design-publish stub rc=%s\n' "${DESIGN_PUBLISH_STUB_RC:-0}" >&2
exit "${DESIGN_PUBLISH_STUB_RC:-0}"
STUB
chmod +x "$STUB/design-publish.sh"

cat >"$STUB/render-final-summary.sh" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do case "$1" in --outcome) shift 2 ;; *) shift ;; esac; done
tmp="${DESIGN_TMPDIR:-}"
[ -n "$tmp" ] || tmp="$(pwd)"
: >"$tmp/final-summary.md"
exit 0
STUB
chmod +x "$STUB/render-final-summary.sh"

setup_design_tmp() {
  local d=$1
  mkdir -p "$d/.completed"
  : >"$d/.completed/step-5b"
  : >"$d/execution-issues.md"
}

run_step5c() {
  local d=$1 rc=$2
  d=$(cd "$d" && pwd -P)
  setup_design_tmp "$d"
  set +e
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$d" DESIGN_PUBLISH_STUB_RC="$rc" \
    "$SUBJECT" >"$d/stdout" 2>"$d/stderr"
  local got=$?
  set -e
  printf '%s\n' "$got"
}

D=$(mktemp -d "$TMP/rc2.XXXXXX")
D=$(cd "$D" && pwd -P)
got=$(run_step5c "$D" 2)
[[ "$got" -eq 1 ]] || fail "publish rc=2 must abort step5c with exit 1 (got $got)"
[ -f "$D/design-failure-terminal-state.env" ] || fail 'rc=2 must stage failed-publish-tail terminal state'
grep -Fxq 'FAILURE_OUTCOME=failed-publish-tail' "$D/design-failure-terminal-state.env" \
  || fail 'rc=2 terminal outcome must be failed-publish-tail'
if [ ! -f "$D/final-summary.md" ]; then
  ls -la "$D" >&2
  fail 'rc=2 must write final-summary via render'
fi
pass 'publish-tail rc=2 stages terminal state and renders summary'

D2=$(mktemp -d "$TMP/rc9.XXXXXX")
D2=$(cd "$D2" && pwd -P)
got=$(run_step5c "$D2" 9)
[[ "$got" -eq 1 ]] || fail "unexpected publish rc must abort step5c with exit 1 (got $got)"
[ -f "$D2/design-failure-terminal-state.env" ] || fail 'unexpected rc must stage failed-publish-tail terminal state'
grep -Fxq 'FAILURE_OUTCOME=failed-publish-tail' "$D2/design-failure-terminal-state.env" \
  || fail 'unexpected rc terminal outcome must be failed-publish-tail'
pass 'publish-tail unexpected rc stages terminal state'

printf 'PASS: test-design-step5c.sh\n'
