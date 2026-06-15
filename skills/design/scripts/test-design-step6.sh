#!/usr/bin/env bash
# test-design-step6.sh — offline harness for Step 6 in-flight publish guards.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PRELUDE="$ROOT/skills/design/scripts/design-step6-prelude.sh"
CLEANUP="$ROOT/skills/design/scripts/design-step6-cleanup.sh"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

contains() {
  local file="$1" needle="$2" label="$3"
  grep -Fq -- "$needle" "$file" || fail "$label"
}

not_contains() {
  local file="$1" needle="$2" label="$3"
  if grep -Fq -- "$needle" "$file"; then
    fail "$label"
  fi
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step6.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

STUB="$TMP/stub-plugin"
mkdir -p "$STUB/python"
cat >"$STUB/python/cli.py" <<'STUB'
#!/usr/bin/env python3
import os
from pathlib import Path
Path(os.environ["LARCH_TEST_PAUSE_LOG"]).open("a").write("pause-save-called\n")
raise SystemExit(0)
STUB
chmod +x "$STUB/python/cli.py"

run_subject() {
  local subject="$1" design_tmp="$2" stdout_file="$3" stderr_file="$4" plugin_root="${5:-$ROOT}"
  set +e
  CLAUDE_PLUGIN_ROOT="$plugin_root" DESIGN_TMPDIR="$design_tmp" ISSUE_NUMBER="${ISSUE_NUMBER:-99}" \
    env LARCH_TEST_PAUSE_LOG="${LARCH_TEST_PAUSE_LOG:-}" \
    "$subject" >"$stdout_file" 2>"$stderr_file"
  local got=$?
  set -e
  printf '%s\n' "$got"
}

D1=$(mktemp -d "$TMP/prelude-inflight.XXXXXX")
: >"$D1/.bg-wait-active"
got=$(run_subject "$PRELUDE" "$D1" "$D1/stdout" "$D1/stderr")
[[ "$got" -eq 1 ]] || fail "prelude in-flight guard must exit 1 (got $got)"
contains "$D1/stderr" 'appears still in-flight' 'prelude in-flight guard must write diagnostic to stderr'
not_contains "$D1/stdout" 'STEP6_PRELUDE_STATUS=skipped' 'prelude in-flight guard must not emit skipped status'
pass 'prelude in-flight guard fails hard'

D2=$(mktemp -d "$TMP/cleanup-inflight.XXXXXX")
: >"$D2/.bg-wait-active"
got=$(run_subject "$CLEANUP" "$D2" "$D2/stdout" "$D2/stderr")
[[ "$got" -eq 1 ]] || fail "cleanup in-flight guard must exit 1 (got $got)"
contains "$D2/stderr" 'appears still in-flight' 'cleanup in-flight guard must write diagnostic to stderr'
not_contains "$D2/stdout" 'CLEANUP_STATUS=preserved' 'cleanup in-flight guard must not emit preserved status'
pass 'cleanup in-flight guard fails hard'

D3=$(mktemp -d "$TMP/missing-sidecar.XXXXXX")
got=$(run_subject "$PRELUDE" "$D3" "$D3/prelude.stdout" "$D3/prelude.stderr")
[[ "$got" -eq 0 ]] || fail "prelude missing-sidecar path must exit 0 (got $got)"
contains "$D3/prelude.stdout" 'STEP6_PRELUDE_STATUS=skipped' 'prelude missing-sidecar path must emit skipped status'
not_contains "$D3/prelude.stderr" 'appears still in-flight' 'prelude missing-sidecar path must not write in-flight diagnostic'
got=$(run_subject "$CLEANUP" "$D3" "$D3/cleanup.stdout" "$D3/cleanup.stderr")
[[ "$got" -eq 0 ]] || fail "cleanup missing-sidecar path must exit 0 (got $got)"
contains "$D3/cleanup.stdout" 'CLEANUP_STATUS=preserved' 'cleanup missing-sidecar path must emit preserved status'
not_contains "$D3/cleanup.stderr" 'appears still in-flight' 'cleanup missing-sidecar path must not write in-flight diagnostic'
pass 'missing-sidecar behavior remains unchanged'

D4=$(mktemp -d "$TMP/status-sidecar.XXXXXX")
: >"$D4/.bg-wait-active"
printf 'PLAN_WRITE_OK=false\n' >"$D4/.design-step5c-status.env"
got=$(run_subject "$PRELUDE" "$D4" "$D4/prelude.stdout" "$D4/prelude.stderr")
[[ "$got" -eq 0 ]] || fail "prelude sidecar-plus-marker path must exit 0 (got $got)"
contains "$D4/prelude.stdout" 'STEP6_PRELUDE_STATUS=skipped' 'prelude sidecar-plus-marker path must emit skipped status'
not_contains "$D4/prelude.stderr" 'appears still in-flight' 'prelude sidecar-plus-marker path must not write in-flight diagnostic'
got=$(run_subject "$CLEANUP" "$D4" "$D4/cleanup.stdout" "$D4/cleanup.stderr")
[[ "$got" -eq 0 ]] || fail "cleanup sidecar-plus-marker path must exit 0 (got $got)"
contains "$D4/cleanup.stdout" 'CLEANUP_STATUS=preserved' 'cleanup sidecar-plus-marker path must emit preserved status'
not_contains "$D4/cleanup.stderr" 'appears still in-flight' 'cleanup sidecar-plus-marker path must not write in-flight diagnostic'
pass 'status sidecar overrides stale marker'

D5=$(mktemp -d "$TMP/pause-inflight.XXXXXX")
: >"$D5/.pause-requested"
: >"$D5/.bg-wait-active"
export LARCH_TEST_PAUSE_LOG="$D5/pause.log"
got=$(run_subject "$PRELUDE" "$D5" "$D5/prelude.stdout" "$D5/prelude.stderr" "$STUB")
[[ "$got" -eq 0 ]] || fail "prelude pause must win over in-flight guard (got $got)"
contains "$D5/pause.log" 'pause-save-called' 'prelude pause-inflight path must exec pause-save'
not_contains "$D5/prelude.stderr" 'appears still in-flight' 'prelude pause-inflight path must not write in-flight diagnostic'
got=$(run_subject "$CLEANUP" "$D5" "$D5/cleanup.stdout" "$D5/cleanup.stderr" "$STUB")
[[ "$got" -eq 0 ]] || fail "cleanup pause must win over in-flight guard (got $got)"
contains "$D5/pause.log" 'pause-save-called' 'cleanup pause-inflight path must exec pause-save'
not_contains "$D5/cleanup.stderr" 'appears still in-flight' 'cleanup pause-inflight path must not write in-flight diagnostic'
pass 'pause wins over in-flight guard'

printf 'PASS: test-design-step6.sh\n'
