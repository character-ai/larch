#!/usr/bin/env bash
set -euo pipefail
REPO=/Users/zhupanov/larch6
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# copy stubs from test harness pattern
cp "$REPO/skills/review-and-fix/scripts/test-review-and-fix.sh" "$TMP/th.sh"
# extract is hard; inline minimal stubs matching test
cat > "$TMP/run-external-agent-stub.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool=""
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) tool="$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    --timeout) shift 2 ;;
    --capture-stdout) shift ;;
    --) shift; break ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$output")"
if [[ "$tool" == "codex" ]]; then
  printf 'modified by codex stub\n' >> src/main.py
  printf 'APPLIED: FINDING_1\n' > "$output"
  exit 0
fi
exit 1
EOF
chmod +x "$TMP/run-external-agent-stub.sh"
cat > "$TMP/review-core-stub.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
cat > "$out/accepted-findings.md" <<'INNER'
### FINDING_1: First
- **Location**: src/main.py
- **Concern**: First concern.
- **Suggested revision**: First fix.
INNER
cat > "$out/oos-accepted-review.md" <<'INNER'
### OOS_1: Stub follow-up
Description: deferred work
INNER
: > "$out/findings.md"
: > "$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=fix-required\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF
chmod +x "$TMP/review-core-stub.sh"
WORK=$TMP/work
mkdir -p "$WORK/src" "$WORK/implement"
git -C "$WORK" init -q
git -C "$WORK" config user.email test@example.com
git -C "$WORK" config user.name Test
git -C "$WORK" config commit.gpgsign false
printf 'original\n' >"$WORK/src/main.py"
printf 'implement*/\nreview*/\n' >"$WORK/.gitignore"
git -C "$WORK" add -A
git -C "$WORK" commit -qm init
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' >"$WORK/implement/session-env.sh"
(
  cd "$WORK"
  CLAUDE_PLUGIN_ROOT="$REPO" \
  CURSOR_API_KEY=test-cursor-key \
  REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh" \
  REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
  LARCH_QUIET_DISABLE=1 \
  "$REPO/skills/review-and-fix/scripts/review-and-fix.sh" \
    --implement-tmpdir "$WORK/implement" \
    --mode diff --panel simple --round-num 1 \
    --session-env-path "$WORK/implement/session-env.sh" \
    --run-id debug-run
) >"$TMP/out.txt" 2>"$TMP/err.txt" || echo rc=$?
echo '--- stdout ---'
cat "$TMP/out.txt"
echo '--- stderr ---'
cat "$TMP/err.txt"
