#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional source literals.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
WRAPPER="$SCRIPT_DIR/step-8-ci-fixer.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/larch-ci-fixer-test.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

contains() {
  command grep -Fq -- "$2" "$1" || { printf 'missing %s in %s\n' "$2" "$1" >&2; exit 1; }
}
not_contains() {
  if ( command grep -Fq -- "$2" "$1" ); then printf 'unexpected %s in %s\n' "$2" "$1" >&2; exit 1; fi
}

# Shared Git-backed fixture for --start route-handoff parsing.
# --start runs git -C "$REPO_ROOT" rev-parse HEAD before reading the handoff.
setup_route_fixture() {
  local name=$1
  local fixture="$TMP/$name"
  local checkout="$fixture/checkout"
  local impl="$fixture/impl"
  mkdir -p "$checkout" "$impl" "$TMP/plugin/python"
  (
    cd "$checkout"
    git init >/dev/null
    git config user.email 'ci-fixer-test@example.com'
    git config user.name 'ci-fixer-test'
    printf 'seed\n' >README
    git add README
    git commit -m 'seed' >/dev/null
  )
  printf 'REPO_ROOT=%s\n' "$checkout" >"$impl/session-env.sh"
  printf 'REPO=owner/repo\nPR_NUMBER=42\n' >"$impl/ship-pr-state.sh"
  FIXTURE_IMPL=$impl
}

run_start() {
  local out_file=$1
  set +e
  IMPLEMENT_TMPDIR="$FIXTURE_IMPL" CLAUDE_PLUGIN_ROOT="$TMP/plugin" \
    bash "$WRAPPER" --start >"$out_file" 2>&1
  local rc=$?
  set -e
  [ "$rc" -eq 0 ]
}

setup_finalize_fixture() {
  local name=$1
  local tier=${2:-codex}
  local attempt=${3:-1}
  local run_id=${4:-42}
  local fixture="$TMP/$name"
  local checkout="$fixture/checkout"
  local impl="$fixture/impl"
  mkdir -p "$checkout" "$impl/ci-fixer" "$impl/bgjob"
  (
    cd "$checkout"
    git init >/dev/null
    git config user.email 'ci-fixer-test@example.com'
    git config user.name 'ci-fixer-test'
    printf 'seed\n' >README
    git add README
    git commit -m 'seed' >/dev/null
  )
  local head fingerprint suffix lineage_key step lineage
  head=$(git -C "$checkout" rev-parse HEAD)
  fingerprint=$(printf '%064d' 0 | tr '0' 'b')
  suffix=$(printf '%s\0%s\0%s\0%s\0%s\0%s' ci "$run_id" "$attempt" "$tier" "$head" "$fingerprint" | shasum -a 256 | awk '{print substr($1,1,16)}')
  step="implement-step8-ci-fixer-${attempt}-${tier}-${suffix}"
  lineage_key=$(printf '%s\0%s' ci "$run_id" | shasum -a 256 | awk '{print substr($1,1,20)}')
  lineage="$impl/ci-fixer/lineage-$lineage_key.tsv"
  printf 'REPO_ROOT=%s\n' "$checkout" >"$impl/session-env.sh"
  printf 'REPO=owner/repo\nPR_NUMBER=42\n' >"$impl/ship-pr-state.sh"
  printf 'MODE=ci\nRUN_ID=%s\nSTARTING_HEAD=%s\nINPUT_FINGERPRINT=%s\nTIER=%s\nATTEMPT=%s\nSTEP=%s\nLINEAGE=%s\n' \
    "$run_id" "$head" "$fingerprint" "$tier" "$attempt" "$step" "$lineage" \
    >"$impl/ci-fixer/launch-$step.env"
  printf 'BGJOB_RC=1\nBGJOB_ELAPSED_S=9\nSTEP=%s\n' "$step" >"$impl/bgjob/$step.result.env"
  printf 'daemon stdout\n' >"$impl/bgjob/$step.stdout.log"
  printf 'daemon stderr\n' >"$impl/bgjob/$step.stderr.log"
  FINALIZE_IMPL=$impl
  FINALIZE_REPO=$checkout
  FINALIZE_STEP=$step
  FINALIZE_LINEAGE=$lineage
  FINALIZE_HEAD=$head
  FINALIZE_FINGERPRINT=$fingerprint
}

run_finalize() {
  local out_file=$1
  set +e
  PATH="$TMP/bin:$PATH" IMPLEMENT_TMPDIR="$FINALIZE_IMPL" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$WRAPPER" --finalize --step "$FINALIZE_STEP" >"$out_file" 2>&1
  local rc=$?
  set -e
  [ "$rc" -eq 0 ]
}

bash -n "$WRAPPER"
contains "$WRAPPER" 'python/cli.py" bgjob start'
not_contains "$WRAPPER" 'bgjob wait'
contains "$WRAPPER" 'ci fixer-lane'
contains "$WRAPPER" '--merge-result-env "$MERGE_ENV"'
contains "$WRAPPER" '--bgjob-result-env "$MERGE_ENV"'
not_contains "$WRAPPER" 'distilled-failure.md'
not_contains "$WRAPPER" 'gh run'
not_contains "$WRAPPER" '.stdout.log'
not_contains "$WRAPPER" '.stderr.log'
not_contains "$WRAPPER" 'execution-issues.md'
contains "$REPO_ROOT/skills/implement/SKILL.md" 'step-8-ci-fixer.sh'
not_contains "$REPO_ROOT/skills/implement/scripts/step-8-ship.sh" 'step-8-ci-fixer.sh'
not_contains "$REPO_ROOT/python/larch/implement/ship.py" 'step-8-ci-fixer.sh'

mkdir -p "$TMP/impl" "$TMP/plugin/python"
set +e
OUT=$(IMPLEMENT_TMPDIR="$TMP/impl" CLAUDE_PLUGIN_ROOT="$TMP/plugin" bash "$WRAPPER" --start 2>&1)
RC=$?
set -e
[ "$RC" -eq 0 ]
printf '%s\n' "$OUT" | command grep -Fq 'RESULT=operator-bail'
printf '%s\n' "$OUT" | command grep -Fq 'REASON=missing-repo-root'

mkdir -p "$TMP/unsafe-impl"
ln -s "$TMP" "$TMP/unsafe-impl/ci-fixer"
set +e
OUT=$(IMPLEMENT_TMPDIR="$TMP/unsafe-impl" CLAUDE_PLUGIN_ROOT="$TMP/plugin" bash "$WRAPPER" --start 2>&1)
RC=$?
set -e
[ "$RC" -eq 0 ]
printf '%s\n' "$OUT" | command grep -Fq 'REASON=unsafe-handoff-dir'

# Lowercase ledger_* keys must be ignored so uppercase routing fields still parse.
# Invalid CI_FAILURE_SCOPE stops after route parsing (before tier/bgjob).
setup_route_fixture lowercase-ledger
cat >"$FIXTURE_IMPL/.ship-route-exit-handoff.env" <<'EOF'
NEEDS_USER_REASON=first-fixer-non-health
CI_FAILURE_SCOPE=bogus
FAILED_RUN_ID=29145966394
ledger_ready=true
ledger_site=ship-pr
ledger_trigger=ci-failure
ledger_step=8
ledger_phase=ship
ledger_dispatcher=ship
ledger_exit_code=0
ledger_failure_detail_log=
EOF
run_start "$TMP/lowercase-ledger.out"
contains "$TMP/lowercase-ledger.out" 'REASON=unknown-ci-failure-scope'
not_contains "$TMP/lowercase-ledger.out" 'REASON=invalid-route-handoff'

# Duplicate uppercase keys still fail closed.
setup_route_fixture duplicate-uppercase
cat >"$FIXTURE_IMPL/.ship-route-exit-handoff.env" <<'EOF'
NEEDS_USER_REASON=first-fixer-non-health
CI_FAILURE_SCOPE=bogus
FAILED_RUN_ID=29145966394
NEEDS_USER_REASON=duplicate
EOF
run_start "$TMP/duplicate-uppercase.out"
contains "$TMP/duplicate-uppercase.out" 'REASON=invalid-route-handoff'

# Control characters in an uppercase-key value still fail closed.
setup_route_fixture control-char-value
printf 'NEEDS_USER_REASON=first-fixer-non-health\nCI_FAILURE_SCOPE=bogus\nFAILED_RUN_ID=29145966394\nDETAIL=bad\x01value\n' \
  >"$FIXTURE_IMPL/.ship-route-exit-handoff.env"
run_start "$TMP/control-char-value.out"
contains "$TMP/control-char-value.out" 'REASON=invalid-route-handoff'

# Non-zero daemon completion needs no lane-owned merge or status artifact.
mkdir -p "$TMP/bin"
for tool in codex cursor claude; do
  printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/$tool"
  chmod +x "$TMP/bin/$tool"
done
setup_finalize_fixture crashed-first codex 1 42
printf 'RESULT=reship\nRUN_ID=stale\n' >"$FINALIZE_IMPL/ci-fixer/fixer-status.env"
run_finalize "$TMP/crashed-first.out"
contains "$TMP/crashed-first.out" 'RESULT=retry-next-tool'
contains "$TMP/crashed-first.out" 'REASON=crashed-lane-recorded'
[ "$(awk 'END{print NR+0}' "$FINALIZE_LINEAGE")" -eq 1 ]
run_finalize "$TMP/crashed-first-repeat.out"
contains "$TMP/crashed-first-repeat.out" 'RESULT=retry-next-tool'
[ "$(awk 'END{print NR+0}' "$FINALIZE_LINEAGE")" -eq 1 ]
[ "$(command grep -c 'larch:ci-fixer-crash:' "$FINALIZE_IMPL/execution-issues.md")" -eq 1 ]

# A crashed final tier records the diagnostic but does not advance lineage.
setup_finalize_fixture crashed-final claude 3 43
printf '1\tcodex\t%s\t%s\tretry-next-tool\t%s\n2\tcursor\t%s\t%s\tretry-next-tool\t%s\n' \
  "$FINALIZE_HEAD" "$FINALIZE_FINGERPRINT" "$FINALIZE_HEAD" \
  "$FINALIZE_HEAD" "$FINALIZE_FINGERPRINT" "$FINALIZE_HEAD" >"$FINALIZE_LINEAGE"
run_finalize "$TMP/crashed-final.out"
contains "$TMP/crashed-final.out" 'RESULT=operator-bail'
contains "$TMP/crashed-final.out" 'REASON=crashed-lane-tiers-exhausted'
[ "$(awk 'END{print NR+0}' "$FINALIZE_LINEAGE")" -eq 2 ]

# A narrowly attributed clean salvage commit reships without consuming a tier.
setup_finalize_fixture crashed-salvage codex 1 44
printf 'salvaged\n' >"$FINALIZE_REPO/README"
git -C "$FINALIZE_REPO" add README
git -C "$FINALIZE_REPO" commit -m 'Apply CI fixer working-tree edits (codex)' >/dev/null
run_finalize "$TMP/crashed-salvage.out"
contains "$TMP/crashed-salvage.out" 'RESULT=reship'
contains "$TMP/crashed-salvage.out" 'REASON=crashed-lane-salvage-commit'
[ ! -f "$FINALIZE_LINEAGE" ]

# Dirty repository state fails closed.
setup_finalize_fixture crashed-dirty codex 1 45
printf 'dirty\n' >>"$FINALIZE_REPO/README"
run_finalize "$TMP/crashed-dirty.out"
contains "$TMP/crashed-dirty.out" 'RESULT=operator-bail'
contains "$TMP/crashed-dirty.out" 'REASON=crashed-lane-worktree-drift'
[ ! -f "$FINALIZE_LINEAGE" ]

# A successful daemon exit still requires the normal lane-owned artifacts.
setup_finalize_fixture successful-missing codex 1 46
printf 'BGJOB_RC=0\nBGJOB_ELAPSED_S=9\nSTEP=%s\n' "$FINALIZE_STEP" \
  >"$FINALIZE_IMPL/bgjob/$FINALIZE_STEP.result.env"
run_finalize "$TMP/successful-missing.out"
contains "$TMP/successful-missing.out" 'REASON=missing-result'

printf '%s\n' 'step-8-ci-fixer harness: ok'
