#!/usr/bin/env bash
# test-design-step5c.sh — offline harness for design-step5c bgjob launcher.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step5c.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step5c.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
mkdir -p "$FAKE_PLUGIN/python" "$FAKE_PLUGIN/skills/design/scripts"
ln -s "$ROOT/python/larch" "$FAKE_PLUGIN/python/larch"
cp "$SUBJECT" "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh"
chmod +x "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh"
cat >"$FAKE_PLUGIN/python/cli.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

args = sys.argv[1:]
if args[:3] == ["session", "validate-design-tmpdir", os.environ.get("DESIGN_TMPDIR", "")]:
    raise SystemExit(0)
if args[:2] == ["bgjob", "start"]:
    step = args[args.index("--step") + 1]
    tmpdir = Path(args[args.index("--tmpdir") + 1])
    merge_env = Path(args[args.index("--merge-result-env") + 1])
    sentinel = Path(args[args.index("--sentinel") + 1])
    command = args[args.index("--") + 1 :]
    result_dir = tmpdir / "bgjob"
    result_dir.mkdir(exist_ok=True)
    result_env = result_dir / f"{step}.result.env"
    try:
        result_env.unlink()
    except FileNotFoundError:
        pass
    rc = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = [("BGJOB_RC", str(rc)), ("BGJOB_ELAPSED_S", "0"), ("STEP", step)]
    if merge_env.is_file() and not merge_env.is_symlink():
        for raw in merge_env.read_text(encoding="utf-8").splitlines():
            if "=" in raw:
                key, value = raw.split("=", 1)
                if key not in {"BGJOB_RC", "BGJOB_ELAPSED_S", "STEP"}:
                    rows.append((key, value))
    result_env.write_text("".join(f"{key}={value}\n" for key, value in rows), encoding="utf-8")
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("", encoding="utf-8")
    print(f"BGJOB_STATUS=STARTED STEP={step} PGID=12345")
    raise SystemExit(0)
if args[:2] == ["bgjob", "wait"]:
    step = args[args.index("--step") + 1]
    tmpdir = Path(args[args.index("--tmpdir") + 1])
    result_env = tmpdir / "bgjob" / f"{step}.result.env"
    if result_env.is_file() and not result_env.is_symlink():
        print("BGJOB_STATUS=DONE")
        print(result_env.read_text(encoding="utf-8"), end="")
    else:
        print("BGJOB_STATUS=DEAD")
    raise SystemExit(0)
if args[:2] == ["design", "step5c"]:
    log = os.environ.get("DESIGN_STEP5C_STUB_LOG")
    if log:
        Path(log).write_text(json.dumps(args) + "\n", encoding="utf-8")
    design_tmpdir = Path(os.environ["DESIGN_TMPDIR"])
    (design_tmpdir / ".design-step5c-status.env").write_text(
        "PLAN_WRITE_OK=true\nPUBLISH_OK=true\nPUBLISH_RC=0\nCLEANUP_ELIGIBLE=true\n",
        encoding="utf-8",
    )
    raise SystemExit(int(os.environ.get("DESIGN_STEP5C_STUB_RC", "0")))
raise SystemExit(2)
PY
chmod +x "$FAKE_PLUGIN/python/cli.py"

D="$TMP/design"
mkdir -p "$D/.completed" "$TMP/registry"
: >"$D/.completed/step-5b"
cat >"$TMP/source-env.sh" <<ENV
export DESIGN_TMPDIR=$D
export CLAUDE_PLUGIN_ROOT=$FAKE_PLUGIN
ENV

LOG="$TMP/argv.json"
out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D" DESIGN_STEP5C_STUB_LOG="$LOG" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" \
  --session-env-path "$TMP/source-env.sh" --claude-pid $$ --skip-validate -- --public value)
case "$out" in
  BGJOB_STATUS=STARTED\ STEP=design-step5c\ PGID=*) ;;
  *) fail "wrapper stdout must be exactly bgjob STARTED line, got: $out" ;;
esac
python3 - "$LOG" "$TMP/source-env.sh" "$$" <<'PY'
import json
import sys
from pathlib import Path

args = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_prefix = [
    "design",
    "step5c",
    "--session-env-path",
    sys.argv[2],
    "--claude-pid",
    sys.argv[3],
]
if args[:6] != expected_prefix or "--skip-validate" not in args or args[-2:] != ["--public", "value"]:
    print(f"FAIL: wrapper argv mismatch: {args!r}", file=sys.stderr)
    raise SystemExit(1)
PY
pass 'wrapper launches bgjob and child delegates to python/cli.py design step5c'

grep -Fxq 'PLAN_WRITE_OK=true' "$D/bgjob/design-step5c.result.env" || fail 'bgjob result env must merge Step 5c status rows'
grep -Fxq 'BGJOB_RC=0' "$D/bgjob/design-step5c.result.env" || fail 'bgjob result env must include BGJOB_RC'
[ -f "$D/.completed/step-5c-terminal" ] || fail 'bgjob must preserve step-5c-terminal sentinel'
pass 'wrapper writes bgjob result env and terminal sentinel'

out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" DESIGN_TMPDIR="$D" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$FAKE_PLUGIN/skills/design/scripts/design-step5c.sh" --session-env-path "$TMP/source-env.sh" --claude-pid $$)
case "$out" in
  $'BGJOB_STATUS=DONE\n'*) ;;
  *) fail "existing result env must route to bgjob wait DONE, got: $out" ;;
esac
pass 'existing bgjob result env routes to wait instead of relaunch'

printf 'PASS: test-design-step5c.sh\n'
