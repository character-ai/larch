#!/usr/bin/env bash
set -euo pipefail
export LARCH_QUIET_DISABLE=1
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMP=/tmp/step5c-debug-once
rm -rf "$TMP"
FAKE="$TMP/plugin"
STUB="$FAKE/skills/design/scripts"
mkdir -p "$STUB" "$FAKE/scripts" "$FAKE/skills/implement/scripts" "$FAKE/bin" "$FAKE/python"
ln -sf "$ROOT/python"/* "$FAKE/python/"
ln -sf "$ROOT/skills/design/scripts/design-stage-terminal-state.sh" "$STUB/design-stage-terminal-state.sh"
ln -sf "$ROOT/scripts/lib-design-tmpdir.sh" "$FAKE/scripts/lib-design-tmpdir.sh"
ln -sf "$ROOT/scripts/lib-quiet.sh" "$FAKE/scripts/lib-quiet.sh"
# shellcheck disable=SC2016
cat >"$FAKE/bin/python3" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
script="${1:-}"
shift || true
if [ "${script##*/}" != "cli.py" ]; then
  exec python3 "$script" "$@"
fi
cmd1="${1:-}"
cmd2="${2:-}"
shift 2 || true
case "$cmd1 $cmd2" in
  "design publish")
    exit "${DESIGN_PUBLISH_STUB_RC:-0}"
    ;;
  "design render-final-summary")
    tmp="${DESIGN_TMPDIR:-}"
    [ -n "$tmp" ] || tmp="$(pwd)"
    printf 'stub summary\n' >"$tmp/final-summary.md"
    sidecar="$tmp/design-failure-operator-action-chat.md"
    if [ -s "$sidecar" ]; then
      printf 'REPORT_GATE_SIDECARS_FILE=%s\n' "$sidecar"
    fi
    exit 0
    ;;
  *)
    exec python3 "/Users/zhupanov/larch8/python/cli.py" "$cmd1" "$cmd2" "$@"
    ;;
esac
EOF
chmod +x "$FAKE/bin/python3"
D="$TMP/design"
mkdir -p "$D/.completed"
: >"$D/.completed/step-5b"
: >"$D/execution-issues.md"
printf 'operator action sidecar\n' >"$D/design-failure-operator-action-chat.md"
set +e
CLAUDE_PLUGIN_ROOT="$FAKE" PATH="$FAKE/bin:$PATH" DESIGN_TMPDIR="$D" DESIGN_PUBLISH_STUB_RC=2 \
  "$ROOT/skills/design/scripts/design-step5c.sh" >"$D/stdout" 2>"$D/stderr"
rc=$?
set -e
printf 'step5c_exit=%s\n' "$rc"
printf 'terminal_state=%s\n' "$([ -f "$D/design-failure-terminal-state.env" ] && echo yes || echo no)"
printf 'stage_stdout:\n'
cat "$D/design-stage-terminal-state.stdout.log" 2>/dev/null || true
printf 'stage_stderr:\n'
cat "$D/design-stage-terminal-state.stderr.log" 2>/dev/null || true
printf 'stderr:\n'
cat "$D/stderr"
