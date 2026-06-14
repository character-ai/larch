#!/usr/bin/env bash
# Offline harness for design-clarify.sh.
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

make_fake_root() {
  local root="$1"
  mkdir -p "$root/scripts" "$root/python" "$root/skills/design/scripts" "$root/bin"
  cat >"$root/scripts/read-result-env.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
input=""
output=""
allow=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --input) input="$2"; shift 2 ;;
    --allow) allow="${allow}${allow:+ }$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    *) shift ;;
  esac
done
: >"$output"
while IFS= read -r line || [ -n "$line" ]; do
  key="${line%%=*}"
  value="${line#*=}"
  for allowed in $allow; do
    if [ "$key" = "$allowed" ]; then
      sq=$(printf '%s' "$value" | sed "s/'/'\"'\"'/g")
      printf "%s='%s'\n" "$key" "$sq" >>"$output"
    fi
  done
done <"$input"
SH
  chmod +x "$root/scripts/read-result-env.sh"
  cat >"$root/scripts/design-log-publish.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'design-log-publish %s\n' "$*" >>"${STUB_CALL_LOG:?}"
if [ "${STUB_PUBLISH_FAIL:-}" = 1 ]; then
  printf 'publish failed\n' >&2
  printf 'PUBLISH_OK=true\n'
  exit 9
fi
printf 'PUBLISH_OK=true\n'
SH
  chmod +x "$root/scripts/design-log-publish.sh"
  cat >"$root/skills/design/scripts/design-stage-terminal-state.sh" <<'SH'
#!/usr/bin/env bash
printf 'stage-terminal %s\n' "$*" >>"${STUB_CALL_LOG:?}"
printf 'STAGED=true\n'
SH
  chmod +x "$root/skills/design/scripts/design-stage-terminal-state.sh"
  : >"$root/python/cli.py"
  cat >"$root/bin/python3" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
script="${1:-}"
shift || true
if [ "${script##*/}" != "cli.py" ]; then
  exec /usr/bin/python3 "$script" "$@"
fi
cmd1="${1:-}"
cmd2="${2:-}"
case "$cmd1 $cmd2" in
  "clarify state")
    printf 'STATE=%s\n' "${STUB_CLARIFY_STATE:-awaiting-response}"
    printf 'LAST_REQUEST_ID=2\n'
    printf 'LAST_RESPONSE_ID=1\n'
    ;;
  "clarify comment-fetch")
    out=""
    while [ "$#" -gt 0 ]; do
      case "$1" in --out) out="$2"; shift 2 ;; *) shift ;; esac
    done
    printf 'What should change?\n' >"$out"
    printf 'FETCHED=true\nCOMMENT_ID=44\nBODY_FILE=%s\n' "$out"
    ;;
  "redact secrets")
    if [ "${STUB_REDACT_FAIL:-}" = 1 ]; then
      exit 8
    fi
    cat
    ;;
  "named-block write")
    printf 'named-block %s\n' "$*" >>"${STUB_CALL_LOG:?}"
    if [ "${STUB_PLAN_WRITE_FAIL:-}" = 1 ]; then
      exit 7
    fi
    ;;
  "clarify comment-post")
    printf 'comment-post %s\n' "$*" >>"${STUB_CALL_LOG:?}"
    printf 'POSTED=true\n'
    ;;
  "clarify label")
    printf 'label %s\n' "$*" >>"${STUB_CALL_LOG:?}"
    ;;
  "tracking-issue rename")
    printf 'rename %s\n' "$*" >>"${STUB_CALL_LOG:?}"
    printf 'RENAMED=true\n'
    ;;
  "run-log append-failure")
    printf 'append-failure %s\n' "$*" >>"${STUB_CALL_LOG:?}"
    ;;
  *)
    printf 'unexpected python cli: %s %s\n' "$cmd1" "$cmd2" >&2
    exit 99
    ;;
esac
SH
  chmod +x "$root/bin/python3"
}

new_design() {
  local name="$1" root="$2" design
  design="$TMP/$name"
  mkdir -p "$design"
  printf 'export DESIGN_TMPDIR=%q\nexport SESSION_ID=%q\n' "$design" "${SESSION_ID_UNDER_TEST-RUN1}" >"$design/source-env.sh"
  printf 'REPO=owner/repo\nISSUE_NUMBER=7\nROUTE=clarify\n' >"$design/.design-step0-route-state.env"
  printf '%s\n' "$design"
}

seed_publish_artifacts() {
  local design="$1"
  printf 'REQUEST_ID=2\nPLAN_FILE=%s/clarify-plan.md\nRESPONSE_FILE=%s/clarify-response.md\nISSUE_NUMBER=7\nREPO=owner/repo\n' "$design" "$design" >"$design/.design-clarify-request.env"
  printf '## Plan\n\nDo it.\n' >"$design/clarify-plan.md"
  printf 'Posted response.\n' >"$design/clarify-response.md"
}

ROOT="$TMP/fake-root"
make_fake_root "$ROOT"
export PATH="$ROOT/bin:$PATH"
export CLAUDE_PLUGIN_ROOT="$ROOT"
export STUB_CALL_LOG="$TMP/calls.log"
: >"$STUB_CALL_LOG"

DESIGN_HAPPY=$(new_design happy "$ROOT")
out=$(env STUB_CALL_LOG="$STUB_CALL_LOG" "$SCRIPT" --session-env-path "$DESIGN_HAPPY/source-env.sh" --claude-pid 123 --phase fetch --issue 7)
printf '%s\n' "$out" | grep -Fq 'CLARIFY_FETCH_STATUS=ok' || fail 'fetch did not succeed'
contains "$DESIGN_HAPPY/clarify-request.md" 'What should change?' 'fetch did not write request body'
printf '## Plan\n\nDo it.\n' >"$DESIGN_HAPPY/clarify-plan.md"
printf 'Posted response.\n' >"$DESIGN_HAPPY/clarify-response.md"
out=$(env STUB_CALL_LOG="$STUB_CALL_LOG" "$SCRIPT" --session-env-path "$DESIGN_HAPPY/source-env.sh" --claude-pid 123 --phase publish --issue 7)
printf '%s\n' "$out" | grep -Fq 'CLARIFY_PUBLISH_STATUS=ok' || fail 'publish did not succeed'
contains "$STUB_CALL_LOG" 'named-block' 'happy path missing plan write'
contains "$STUB_CALL_LOG" 'design-log-publish' 'happy path missing publish'
contains "$STUB_CALL_LOG" 'comment-post' 'happy path missing clarify response'
contains "$STUB_CALL_LOG" 'label clarify label' 'happy path missing label removal'
contains "$STUB_CALL_LOG" 'rename tracking-issue rename' 'happy path missing rename'
contains "$STUB_CALL_LOG" '--repo owner/repo' 'repo fallback not forwarded'

: >"$STUB_CALL_LOG"
DESIGN_PLAN_FAIL=$(new_design plan-fail "$ROOT")
seed_publish_artifacts "$DESIGN_PLAN_FAIL"
set +e
out=$(env STUB_CALL_LOG="$STUB_CALL_LOG" STUB_PLAN_WRITE_FAIL=1 "$SCRIPT" --session-env-path "$DESIGN_PLAN_FAIL/source-env.sh" --claude-pid 123 --phase publish --issue 7)
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail 'plan-write failure should exit non-zero'
printf '%s\n' "$out" | grep -Fq 'CLARIFY_PUBLISH_STATUS=plan-write-failed' || fail 'plan-write failure status missing'
contains "$STUB_CALL_LOG" 'named-block' 'plan-write failure did not attempt plan write'
not_contains "$STUB_CALL_LOG" 'design-log-publish' 'plan-write failure must not publish'
not_contains "$STUB_CALL_LOG" 'comment-post' 'plan-write failure must not post response'
not_contains "$STUB_CALL_LOG" 'label clarify label' 'plan-write failure must not remove label'

: >"$STUB_CALL_LOG"
DESIGN_PUBLISH_FAIL=$(new_design publish-fail "$ROOT")
seed_publish_artifacts "$DESIGN_PUBLISH_FAIL"
out=$(env STUB_CALL_LOG="$STUB_CALL_LOG" STUB_PUBLISH_FAIL=1 "$SCRIPT" --session-env-path "$DESIGN_PUBLISH_FAIL/source-env.sh" --claude-pid 123 --phase publish --issue 7)
printf '%s\n' "$out" | grep -Fq 'PUBLISH_OK=false' || fail 'non-zero publish must force PUBLISH_OK=false'
contains "$STUB_CALL_LOG" 'append-failure' 'publish failure should append warning'
contains "$STUB_CALL_LOG" 'comment-post' 'publish failure should still post response'
contains "$STUB_CALL_LOG" 'label clarify label' 'publish failure should still remove label'
not_contains "$STUB_CALL_LOG" 'rename tracking-issue rename' 'publish failure must not rename'

: >"$STUB_CALL_LOG"
SESSION_ID_UNDER_TEST=""
DESIGN_EMPTY_SESSION=$(new_design empty-session "$ROOT")
unset SESSION_ID_UNDER_TEST
seed_publish_artifacts "$DESIGN_EMPTY_SESSION"
out=$(env STUB_CALL_LOG="$STUB_CALL_LOG" "$SCRIPT" --session-env-path "$DESIGN_EMPTY_SESSION/source-env.sh" --claude-pid 123 --phase publish --issue 7)
printf '%s\n' "$out" | grep -Fq 'SESSION_ID missing' || fail 'empty SESSION_ID warning missing'
contains "$STUB_CALL_LOG" 'comment-post' 'empty SESSION_ID should still post response'
contains "$STUB_CALL_LOG" 'label clarify label' 'empty SESSION_ID should still remove label'
not_contains "$STUB_CALL_LOG" 'design-log-publish' 'empty SESSION_ID must not publish'
not_contains "$STUB_CALL_LOG" 'rename tracking-issue rename' 'empty SESSION_ID must not rename'

printf 'PASS test-design-clarify\n'
