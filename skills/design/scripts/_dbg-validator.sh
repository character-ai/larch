#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
TMP=$(mktemp -d)
D="$TMP/d"
mkdir -p "$D"
printf 'plan body\ndiff_lines: 3\n' >"$D/plan.txt"
printf 'validate defects\n' >"$D/validate-plan-commands.log"
DISPATCH_STUB="$TMP/dispatch.sh"
printf '#!/bin/bash\nexit 0\n' >"$DISPATCH_STUB"
chmod +x "$DISPATCH_STUB"
VALIDATE_STUB="$TMP/validate.sh"
printf '#!/bin/bash\nprintf VALIDATE_STATUS=defects-found\n' >"$VALIDATE_STUB"
chmod +x "$VALIDATE_STUB"
set +e
out=$(AUTOFIX_TEST_MODE=never-fix CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D" SITE='design Step 2b' \
  CODEX_BINARY_FOUND=true CURSOR_BINARY_FOUND=true \
  LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
  python3 "$ROOT/python/cli.py" plan validator-autofix \
  --validator-target-file "$D/plan.txt" --validate-log-file "$D/validate-plan-commands.log" \
  --validate-defect-count 1 --validate-unsafe-token-count 0 --validate-skipped-count 0 2>"$TMP/err")
rc=$?
set -e
echo "rc=$rc"
printf 'out=[%s]\n' "$out"
cat "$TMP/err"
ls -la "$D"
