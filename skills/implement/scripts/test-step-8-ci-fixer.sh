#!/usr/bin/env bash
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

bash -n "$WRAPPER"
contains "$WRAPPER" 'python/cli.py" bgjob start'
not_contains "$WRAPPER" 'bgjob wait'
contains "$WRAPPER" 'ci fixer-lane'
contains "$WRAPPER" '--merge-result-env "$MERGE_ENV"'
contains "$WRAPPER" '--bgjob-result-env "$MERGE_ENV"'
not_contains "$WRAPPER" 'distilled-failure.md'
not_contains "$WRAPPER" 'gh run'
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

printf '%s\n' 'step-8-ci-fixer harness: ok'
