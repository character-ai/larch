#!/usr/bin/env bash
# test-design-step3b-tail.sh — offline adapter contract for the Step 4 tail.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step3b-tail.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

command grep -Fq 'bgjob adapt' "$SUBJECT" || fail 'wrapper must delegate through bgjob adapt'
command grep -Fq -- '--bgjob-child|--merge-result-env' "$SUBJECT" || fail 'wrapper must parse standard child controls'
if ( command grep -Fq 'bgjob start' "$SUBJECT" ) || ( command grep -Fq 'design_step4_tail_bgjob_registry_state' "$SUBJECT" ); then
  fail 'wrapper must not retain direct start or local registry policy'
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-step3b-tail.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
PLUGIN="$TMP/plugin"
mkdir -p "$PLUGIN/python" "$PLUGIN/skills/design/scripts"
ln -s "$ROOT/python/larch" "$PLUGIN/python/larch"
cp "$SUBJECT" "$PLUGIN/skills/design/scripts/design-step3b-tail.sh"
chmod +x "$PLUGIN/skills/design/scripts/design-step3b-tail.sh"
# The wrappers reach the Rust session verbs through the verified bootstrap.
mkdir -p "$PLUGIN/scripts"
cat >"$PLUGIN/scripts/larch.sh" <<'LARCH_STUB'
#!/usr/bin/env bash
set -uo pipefail
case "${1:-} ${2:-}" in
  "session require-plugin-root"|"session validate-design-tmpdir") exit 0 ;;
esac
printf '%s\n' "unexpected larch command: $*" >&2
exit 64
LARCH_STUB
chmod +x "$PLUGIN/scripts/larch.sh"
cat >"$PLUGIN/python/cli.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

args = sys.argv[1:]
if args[:2] == ["bgjob", "adapt"] and "--resolve-session-env" in args:
    source = Path(args[args.index("--session-env-path") + 1])
    print(source.read_text(encoding="utf-8"), end="")
    raise SystemExit(0)
if args[:2] == ["bgjob", "adapt"]:
    step = args[args.index("--step") + 1]
    tmpdir = Path(args[args.index("--tmpdir") + 1])
    command = args[args.index("--") + 1:]
    bgjob = tmpdir / "bgjob"
    bgjob.mkdir(exist_ok=True)
    result = bgjob / f"{step}.result.env"
    if result.is_file():
        print("BGJOB_STATUS=DONE")
        print(result.read_text(encoding="utf-8"), end="")
        raise SystemExit(0)
    merge = bgjob / f"{step}.merge.env"
    merge.write_text("", encoding="utf-8")
    if os.environ.get("TAIL_PAUSE_RACE") == "1":
        (tmpdir / ".pause-requested").touch()
    rc = subprocess.call(
        [*command, "--bgjob-child", "--merge-result-env", str(merge)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rows = [("BGJOB_RC", str(rc)), ("STEP", step)]
    if merge.is_file():
        for line in merge.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                rows.append(tuple(line.split("=", 1)))
    result.write_text("".join(f"{key}={value}\n" for key, value in rows), encoding="utf-8")
    print(f"BGJOB_STATUS=STARTED STEP={step} PGID=12345")
    raise SystemExit(0)
if args[:2] == ["session", "validate-design-tmpdir"]:
    raise SystemExit(0)
if args[:2] == ["timing", "mark"]:
    raise SystemExit(0)
if args[:2] == ["design", "pause-save"]:
    design = Path(args[args.index("--design-tmpdir") + 1])
    (design / ".pause-save-complete").touch()
    raise SystemExit(0)
if args[:2] == ["design", "dialectic-gatec"]:
    raise SystemExit(0)
if args[:2] == ["plan-review", "preview"]:
    print("preview")
    raise SystemExit(0)
if args[:2] == ["plan-review", "emit-rejected"]:
    raise SystemExit(0)
raise SystemExit(2)
PY
chmod +x "$PLUGIN/python/cli.py"

D="$TMP/design"
mkdir -p "$D/.completed" "$TMP/registry"
D="$(cd "$D" && pwd -P)"
: >"$D/.completed/finalize"
printf '{"skip_approve_requested":false}\n' >"$D/run-params.json"
cat >"$TMP/session-env.sh" <<ENV
export DESIGN_TMPDIR=$D
export CLAUDE_PLUGIN_ROOT=$PLUGIN
export ISSUE_NUMBER=42
ENV

out=$(env -u DESIGN_TMPDIR CLAUDE_PLUGIN_ROOT="$PLUGIN" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$PLUGIN/skills/design/scripts/design-step3b-tail.sh" \
  --session-env-path "$TMP/session-env.sh" --claude-pid $$)
case "$out" in
  BGJOB_STATUS=STARTED\ STEP=design-step4-tail\ PGID=*) ;;
  *) fail "fresh invocation must start through the adapter: $out" ;;
esac
result="$D/bgjob/design-step4-tail.result.env"
command grep -Fxq 'BGJOB_RC=0' "$result" || fail 'successful child result must have BGJOB_RC=0'
command grep -Fxq 'STEP4_STATUS=complete' "$result" || fail 'successful child must publish terminal status'
command grep -Fxq 'SKIP_APPROVE_REQUESTED_GATEC=false' "$result" || fail 'Gate C skip row missing'
command grep -Fxq "GATEC_PREVIEW_PATH=$D/gatec-preview.md" "$result" || fail 'Gate C preview row missing'
pass 'fresh launcher-only session resolution and Gate C publication work'

out=$(env -u DESIGN_TMPDIR CLAUDE_PLUGIN_ROOT="$PLUGIN" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$PLUGIN/skills/design/scripts/design-step3b-tail.sh" \
  --session-env-path "$TMP/session-env.sh" --claude-pid $$)
case "$out" in BGJOB_STATUS=DONE*) ;; *) fail "completed result must reattach: $out" ;; esac
pass 'completed result reattaches without relaunch'

rm -f "$result" "$D/.pause-requested" "$D/.pause-save-complete"
out=$(env -u DESIGN_TMPDIR TAIL_PAUSE_RACE=1 CLAUDE_PLUGIN_ROOT="$PLUGIN" LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry" \
  "$PLUGIN/skills/design/scripts/design-step3b-tail.sh" \
  --session-env-path "$TMP/session-env.sh" --claude-pid $$)
case "$out" in BGJOB_STATUS=STARTED*) ;; *) fail "pause-race invocation must start adapter: $out" ;; esac
command grep -Fxq 'BGJOB_RC=0' "$result" || fail 'handled pause race must exit zero'
command grep -Fxq 'STEP4_STATUS=pause-save' "$result" || fail 'handled pause race must publish its terminal route'
pass 'in-flight pause publishes a terminal adapter envelope'

printf 'PASS: test-design-step3b-tail.sh\n'
