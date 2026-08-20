#!/usr/bin/env bash
# Offline harness for design-clarify.sh wrapper delegation.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SCRIPT="$REPO_ROOT/skills/design/scripts/design-clarify.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-clarify.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

contains() {
  local file="$1" needle="$2" label="$3"
  grep -Fq -- "$needle" "$file" || fail "$label"
}

not_contains() {
  local file="$1" needle="$2" label="$3"
  ! grep -Fq -- "$needle" "$file" || fail "$label"
}

ROOT="$TMP/fake-root"
mkdir -p "$ROOT/scripts"
CALL_LOG="$TMP/calls.log"
cat >"$ROOT/scripts/larch.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${STUB_CALL_LOG:?}"
if [ "$*" != "${EXPECTED_DELEGATE_ARGS:?}" ]; then
  printf 'unexpected delegate argv: %s\n' "$*" >&2
  exit 99
fi
printf 'CLARIFY_WRAPPER_DELEGATED=true\n'
SH
chmod +x "$ROOT/scripts/larch.sh"
export CLAUDE_PLUGIN_ROOT="$ROOT"
export STUB_CALL_LOG="$CALL_LOG"
: >"$CALL_LOG"

SESSION_ENV="$TMP/source-env.sh"
printf 'export DESIGN_TMPDIR=%q\nexport SESSION_ID=%q\n' "$TMP/design" "RUN1" >"$SESSION_ENV"
mkdir -p "$TMP/design"

EXPECTED_DELEGATE_ARGS="design clarify --session-env-path $SESSION_ENV --claude-pid 123 --phase fetch --issue 7"
out=$(env EXPECTED_DELEGATE_ARGS="$EXPECTED_DELEGATE_ARGS" "$SCRIPT" \
  --session-env-path "$SESSION_ENV" \
  --claude-pid 123 \
  --phase fetch \
  --issue 7)
printf '%s\n' "$out" | grep -Fq 'CLARIFY_WRAPPER_DELEGATED=true' || fail 'wrapper did not delegate'
contains "$CALL_LOG" "$EXPECTED_DELEGATE_ARGS" 'delegation argv mismatch'

: >"$CALL_LOG"
set +e
err=$(env EXPECTED_DELEGATE_ARGS=unused "$SCRIPT" --phase invalid --issue 7 2>&1 >/dev/null)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail 'invalid phase should exit 2'
printf '%s\n' "$err" | grep -Fq -- '--phase must be fetch or publish' || fail 'invalid phase message missing'
not_contains "$CALL_LOG" 'design clarify' 'invalid phase should not delegate'

set +e
err=$(env EXPECTED_DELEGATE_ARGS=unused "$SCRIPT" --phase fetch --issue 0 2>&1 >/dev/null)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail 'invalid issue should exit 2'
printf '%s\n' "$err" | grep -Fq -- '--issue must be a positive integer' || fail 'invalid issue message missing'

set +e
err=$(env EXPECTED_DELEGATE_ARGS=unused "$SCRIPT" --phase fetch --issue 7 --claude-pid nope 2>&1 >/dev/null)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail 'invalid claude pid should exit 2'
printf '%s\n' "$err" | grep -Fq -- '--claude-pid must be a positive integer' || fail 'invalid claude pid message missing'

printf 'PASS test-design-clarify\n'
