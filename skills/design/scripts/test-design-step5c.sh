#!/usr/bin/env bash
# test-design-step5c.sh — offline harness for design-step5c thin delegation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step5c.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step5c.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
mkdir -p "$FAKE_PLUGIN/python" "$FAKE_PLUGIN/skills/design/scripts"
cp "$SUBJECT" "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh"
chmod +x "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh"
cat >"$FAKE_PLUGIN/python/cli.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

log = os.environ.get("DESIGN_STEP5C_STUB_LOG")
if log:
    Path(log).write_text(json.dumps(sys.argv[1:]) + "\n", encoding="utf-8")
raise SystemExit(int(os.environ.get("DESIGN_STEP5C_STUB_RC", "0")))
PY
chmod +x "$FAKE_PLUGIN/python/cli.py"

LOG="$TMP/argv.json"
CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_STEP5C_STUB_LOG="$LOG" \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" \
  --session-env-path "$TMP/source-env.sh" --claude-pid 123 --skip-validate -- --public value
python3 - "$LOG" "$TMP/source-env.sh" <<'PY'
import json
import sys
from pathlib import Path

args = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = [
    "design",
    "step5c",
    "--session-env-path",
    sys.argv[2],
    "--claude-pid",
    "123",
    "--skip-validate",
    "--",
    "--public",
    "value",
]
if args != expected:
    print(f"FAIL: wrapper argv mismatch: {args!r} != {expected!r}", file=sys.stderr)
    raise SystemExit(1)
PY
pass 'wrapper delegates to python/cli.py design step5c with argv passthrough'

set +e
CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_STEP5C_STUB_LOG="$TMP/argv-fail.json" DESIGN_STEP5C_STUB_RC=7 \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" --session-env-path "$TMP/missing-env.sh" >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" -eq 7 ]] || fail "wrapper must propagate python entrypoint rc 7 (got $rc)"
pass 'wrapper propagates python entrypoint failures'

printf 'PASS: test-design-step5c.sh\n'
