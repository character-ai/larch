#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
D=$(mktemp -d)
printf 'fail\n' >"$D/design-publish-tail.failure.log"
set +e
CLAUDE_PLUGIN_ROOT="$ROOT" "$ROOT/skills/design/scripts/design-stage-terminal-state.sh" \
  --design-tmpdir "$D" --outcome failed-publish-tail --step publish --phase publish \
  --site design-publish --trigger publish-tail-failed --bail-reason publish-tail-failed \
  --exit-code 2 --source-script design-step5c --summary-outcome failed-publish-tail \
  --failure-detail-log "$D/design-publish-tail.failure.log" >"$D/out" 2>"$D/err"
rc=$?
set -e
echo "rc=$rc"
ls -la "$D"
cat "$D/out"
cat "$D/err"
