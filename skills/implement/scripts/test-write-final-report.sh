#!/usr/bin/env bash
# test-write-final-report.sh — offline harness for write-final-report.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-final-report.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
assert_not_contains(){ case "$2" in *"$1"*) fail "$3 (unexpected $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; *) pass "$3" ;; esac; }
assert_eq(){ if [ "$1" = "$2" ]; then pass "$3"; else fail "$3 (expected=$1 actual=$2)"; fi; }
stdout_summary_block() {
    printf '%s\n' "$1" | awk '
        /^COMMENT_URL=|^STATUS=|^REASON=|^ERROR=/ { exit }
        { print }
    '
}
assert_schema_ordered() {
    local body=$1 label=$2 prev=0 current
    shift 2
    for needle in "$@"; do
        current=$(printf '%s\n' "$body" | awk -v needle="$needle" 'index($0, needle) { print NR; exit }')
        if [ -z "$current" ]; then
            fail "$label (missing $needle)"
            printf 'ACTUAL: %s\n' "$body" >&2
            return
        fi
        if [ "$current" -le "$prev" ]; then
            fail "$label (out of order at $needle)"
            printf 'ACTUAL: %s\n' "$body" >&2
            return
        fi
        prev=$current
    done
    pass "$label"
}
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts" "$plugin/python"
cp "$REPO_ROOT/python/"*.py "$plugin/python/"
cp -R "$REPO_ROOT/python/larch" "$plugin/python/larch"
mv "$plugin/python/cli.py" "$plugin/python/real-cli.py"
cat > "$plugin/python/cli.py" <<'DISPATCHER'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parent
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["tracking-issue", "upsert-summary"]:
        if os.environ.get("TRACKING_FAIL", "false") == "true":
            print(os.environ.get("TRACKING_ERR", "summary failed"), end="", file=sys.stderr)
            raise SystemExit(int(os.environ.get("TRACKING_RC", "1")))
        args = sys.argv[3:]
        if "--content-file" in args:
            src = Path(args[args.index("--content-file") + 1])
            dst = os.environ.get("TRACKING_CONTENT_LOG", "")
            if dst:
                Path(dst).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print("COMMENT_URL=https://example.test/comment/final")
        raise SystemExit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "run-log" and sys.argv[2] == "manifest":
        if os.environ.get("LARCH_LOG_MANIFEST_FAIL", "") == "true":
            print("manifest stub failure", file=sys.stderr)
            raise SystemExit(1)
        log = os.environ.get("LARCH_LOG_MANIFEST_LOG", "")
        if log:
            with open(log, "a", encoding="utf-8") as handle:
                handle.write(" ".join(sys.argv[3:]) + "\n")
        raise SystemExit(0)
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["agent", "launch-claude-subprocess"]:
        args = sys.argv[3:]
        if "--output-file" in args:
            Path(args[args.index("--output-file") + 1]).write_text('{"assessments":[]}\n', encoding="utf-8")
        raise SystemExit(0)
    os.execv(sys.executable, [sys.executable, str(root / "real-cli.py"), *sys.argv[1:]])

if __name__ == "__main__":
    main()
DISPATCHER
chmod +x "$plugin/python/cli.py"
mkdir -p "$TMP_ROOT/bin"
GH_SHIM_LOG="$TMP_ROOT/gh-shim.log"
: >"$GH_SHIM_LOG"
export GH_SHIM_LOG
cat > "$TMP_ROOT/bin/gh" <<'SHIM'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${GH_SHIM_LOG:?}"
if [ "${GH_SHIM_FAIL:-false}" = true ]; then
    exit 1
fi
case "$*" in
    *pulls/*/files*)
        printf '%s\t%s\t%s\n' 'scripts/foo.sh' 10 2
        printf '%s\t%s\t%s\n' 'larch-logs/implement/run-x/summary.md' 5 1
        printf '%s\t%s\t%s\n' 'assets/binary.png' 0 0
        printf '%s\t%s\t%s\n' 'scripts/renamed.sh' 4 0
        printf '%s\t%s\t%s\n' 'docs/user guide.md' 3 1
        ;;
esac
exit 0
SHIM
chmod +x "$TMP_ROOT/bin/gh"
export PATH="$TMP_ROOT/bin:$PATH"

# Happy path: IMPLEMENT_TMPDIR with parent-issue.md, session-env.sh, ship-pr-state.sh
impl_dir="$TMP_ROOT/impl"; mkdir -p "$impl_dir"
printf 'ISSUE_NUMBER=7\nRUN_ID=run-5\nADOPTED=true\n' > "$impl_dir/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_dir/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/5\n'
    printf 'PR_NUMBER=5\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_dir/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\n' > "$impl_dir/finalize-state.sh"
mkdir -p "$impl_dir/larch-logs/implement/run-5"
cat > "$impl_dir/larch-logs/implement/run-5/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'STATUS=ok' "$out" 'happy path status ok'
assert_contains 'COMMENT_URL=https://example.test/comment/final' "$out" 'comment URL emitted'
assert_contains 'https://example.test/pr/5' "$(cat "$TMP_ROOT/content.md")" 'summary includes PR URL'
assert_contains '<!-- larch:run-summary v=1 -->' "$(cat "$TMP_ROOT/content.md")" 'summary includes run-summary sentinel'
assert_contains '## /implement run run-5: merged' "$(cat "$TMP_ROOT/content.md")" 'summary title shows merged outcome'
assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1' "$(cat "$TMP_ROOT/content.md")" 'happy path includes bucketed line counts'
assert_not_contains '**Outcome**:' "$(cat "$TMP_ROOT/content.md")" 'success path omits Outcome bullet'
if [ -s "$impl_dir/larch-logs/implement/run-5/final-summary.md" ]; then pass 'final summary file written'; else fail 'final summary file written'; fi
assert_contains '## /implement run run-5: merged' "$(cat "$impl_dir/larch-logs/implement/run-5/final-summary.md")" 'final summary title merged'
assert_not_contains '**Outcome**:' "$(cat "$impl_dir/larch-logs/implement/run-5/final-summary.md")" 'final summary omits Outcome bullet on success'

# Comment-only path leaves the tracked run-log file untouched while still
# emitting the live tracking-comment projection.
printf 'legacy-stale-marker-do-not-touch\n' > "$impl_dir/larch-logs/implement/run-5/final-summary.md"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-comment-only.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --comment-only)
assert_contains 'STATUS=ok' "$out" 'comment-only status ok'
assert_contains 'https://example.test/pr/5' "$(cat "$TMP_ROOT/content-comment-only.md")" 'comment-only summary includes live PR'
assert_contains 'legacy-stale-marker-do-not-touch' "$(cat "$impl_dir/larch-logs/implement/run-5/final-summary.md")" 'comment-only does not rewrite tracked final summary'

# Upsert failure → STATUS=failed + non-zero exit
set +e
failed=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_FAIL=true TRACKING_ERR='gh auth failed' \
         "$HELPER" --implement-tmpdir "$impl_dir" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 1 ]; then pass 'upsert failure exits non-zero'; else fail 'upsert failure exits non-zero'; fi
assert_contains 'STATUS=failed' "$failed" 'upsert failure status failed'
assert_contains 'ERROR=' "$failed" 'upsert failure emits error'

# Missing --implement-tmpdir
set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing arg exits non-zero'; else fail 'missing arg exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing arg emits envelope'

# Stalled outcome (terminal STALL_TRACKING=true)
impl_st="$TMP_ROOT/impl-stall"; mkdir -p "$impl_st"
printf 'ISSUE_NUMBER=2\nRUN_ID=run-st\nADOPTED=true\n' > "$impl_st/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_st/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/2\n'
    printf 'PR_NUMBER=2\n'
    printf 'STALL_TRACKING=true\n'
    printf 'PHASE=stalled\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_st/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_TRACKING=true\n' > "$impl_st/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-stall.md" \
      "$HELPER" --implement-tmpdir "$impl_st")
assert_contains 'STATUS=ok' "$out" 'stalled path status ok'
assert_contains '**Outcome**: stalled' "$(cat "$TMP_ROOT/content-stall.md")" 'stalled outcome in summary'

# Design-only outcome
impl_do="$TMP_ROOT/impl-do"; mkdir -p "$impl_do"
printf 'ISSUE_NUMBER=3\nRUN_ID=run-do\nADOPTED=true\n' > "$impl_do/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_do/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_do/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=true\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_do/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-do.md" \
      "$HELPER" --implement-tmpdir "$impl_do")
assert_contains 'STATUS=ok' "$out" 'design-only status ok'
assert_contains '## /implement run run-do: design-only' "$(cat "$TMP_ROOT/content-do.md")" 'design-only title'
assert_not_contains '**Outcome**:' "$(cat "$TMP_ROOT/content-do.md")" 'design-only success omits Outcome bullet'

# BAIL_NEEDS_USER_INPUT → distinct outcome when still bailed
impl_bu="$TMP_ROOT/impl-bu"; mkdir -p "$impl_bu"
printf 'ISSUE_NUMBER=4\nRUN_ID=run-bu\nADOPTED=true\n' > "$impl_bu/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_bu/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'BAIL_REASON=early-failure\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_bu/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=true\n' > "$impl_bu/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-bu.md" \
      "$HELPER" --implement-tmpdir "$impl_bu")
assert_contains 'STATUS=ok' "$out" 'bail-user path status ok'
assert_contains '**Outcome**: bailed-needs-user-input' "$(cat "$TMP_ROOT/content-bu.md")" 'bail-user outcome'

# Plain bailed outcome (early exit without user-input flag)
impl_bl="$TMP_ROOT/impl-bl"; mkdir -p "$impl_bl"
printf 'ISSUE_NUMBER=9\nRUN_ID=run-bl\nADOPTED=true\n' > "$impl_bl/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_bl/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'BAIL_REASON=early-failure\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_bl/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_bl/finalize-state.sh"
printf 'NO_ISSUES=false\n' > "$impl_bl/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-bl.md" \
      "$HELPER" --implement-tmpdir "$impl_bl")
assert_contains 'STATUS=ok' "$out" 'bailed path status ok'
assert_contains '**Outcome**: bailed' "$(cat "$TMP_ROOT/content-bl.md")" 'plain bailed outcome in summary'
assert_contains '- **Cost**: N/A' "$(cat "$TMP_ROOT/content-bl.md")" 'missing token data renders cost N/A'
assert_contains '- **Lines (PR diff)**: N/A' "$(cat "$TMP_ROOT/content-bl.md")" 'no PR renders line counts N/A'
assert_not_contains '- **PR**:' "$(cat "$TMP_ROOT/content-bl.md")" 'bailed path omits PR bullet when PR is N/A'

impl_em="$TMP_ROOT/impl-em"; mkdir -p "$impl_em"
printf 'ISSUE_NUMBER=13\nRUN_ID=run-em\nADOPTED=true\n' > "$impl_em/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_em/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_em/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_em/finalize-state.sh"
printf 'NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=true\n' > "$impl_em/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-em.md" \
      "$HELPER" --implement-tmpdir "$impl_em")
assert_contains 'STATUS=ok' "$out" 'force path status ok'
assert_contains '- Force: true' "$(cat "$TMP_ROOT/content-em.md")" 'force path summary includes force line'

impl_emf="$TMP_ROOT/impl-emf"; mkdir -p "$impl_emf"
printf 'ISSUE_NUMBER=14\nRUN_ID=run-emf\nADOPTED=true\n' > "$impl_emf/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_emf/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_emf/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_emf/finalize-state.sh"
printf 'NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=false\n' > "$impl_emf/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-emf.md" \
      "$HELPER" --implement-tmpdir "$impl_emf")
assert_contains 'STATUS=ok' "$out" 'non-force explicit false status ok'
assert_not_contains 'Force: true' "$(cat "$TMP_ROOT/content-emf.md")" 'non-force summary omits force line'

impl_emo="$TMP_ROOT/impl-emo"; mkdir -p "$impl_emo"
printf 'ISSUE_NUMBER=15\nRUN_ID=run-emo\nADOPTED=true\n' > "$impl_emo/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_emo/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_emo/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_emo/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-emo.md" \
      "$HELPER" --implement-tmpdir "$impl_emo")
assert_contains 'STATUS=ok' "$out" 'omitted-force status ok'
assert_not_contains 'Force: true' "$(cat "$TMP_ROOT/content-emo.md")" 'omitted-force summary omits force line'

impl_emi="$TMP_ROOT/impl-emi"; mkdir -p "$impl_emi"
printf 'ISSUE_NUMBER=16\nRUN_ID=run-emi\nADOPTED=true\n' > "$impl_emi/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_emi/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_emi/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_emi/finalize-state.sh"
printf 'NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=maybe\n' > "$impl_emi/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-emi.md" \
      "$HELPER" --implement-tmpdir "$impl_emi")
assert_contains 'STATUS=ok' "$out" 'invalid-force status ok'
assert_not_contains 'Force: true' "$(cat "$TMP_ROOT/content-emi.md")" 'invalid-force summary omits force line'
assert_not_contains "Invalid \`FORCE_REQUESTED\` value" "$(cat "$TMP_ROOT/content-emi.md")" 'invalid-force summary omits warning note'
if [ ! -e "$impl_emi/execution-issues.md" ]; then
    pass 'invalid-force does not append warning section'
else
    assert_not_contains 'Invalid FORCE_REQUESTED value in run-flags.sh: maybe' "$(cat "$impl_emi/execution-issues.md")" 'invalid-force warning content absent'
fi

impl_legacy="$TMP_ROOT/impl-legacy"; mkdir -p "$impl_legacy"
printf 'ISSUE_NUMBER=17\nRUN_ID=run-legacy\nADOPTED=true\n' > "$impl_legacy/parent-issue.md"
printf 'REPO=owner/repo\nPOST_PLAN_WORKFLOW_PATH=\n' > "$impl_legacy/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_legacy/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_legacy/finalize-state.sh"
printf 'NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=false\n' > "$impl_legacy/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-legacy.md" \
      "$HELPER" --implement-tmpdir "$impl_legacy")
legacy_body="$(cat "$TMP_ROOT/content-legacy.md")"
assert_contains 'STATUS=ok' "$out" 'legacy workflow flags status ok'
assert_not_contains '- **Path**:' "$legacy_body" 'legacy workflow flags do not render Path bullet'
# removed "$legacy_body" 'legacy WORKFLOW_PATH does not leak into summary'
# removed "$legacy_body" 'legacy POST_PLAN_WORKFLOW_PATH does not leak into summary'

impl_exec="$TMP_ROOT/impl-exec"; mkdir -p "$impl_exec/larch-logs/implement/run-exec"
printf 'ISSUE_NUMBER=11\nRUN_ID=run-exec\nADOPTED=true\n' > "$impl_exec/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_exec/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_exec/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_exec/finalize-state.sh"
cat > "$impl_exec/execution-issues.md" <<'EOF'
### External Reviewer Issues
- **findings aggregator**: ballot merge failed
### Warnings
- post-flush warning
EOF
cat > "$impl_exec/larch-logs/implement/run-exec/execution-issues.ndjson" <<'JSON'
{"category":"Warnings","body":"- **Step design Step 5 — tracking failed (exit 1)**:\n  ```\nwarn\n  ```"}
JSON
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-exec.md" \
      "$HELPER" --implement-tmpdir "$impl_exec")
assert_contains '- **Exec issues**: 1' "$(cat "$TMP_ROOT/content-exec.md")" 'merged execution issues count live exec issue'
assert_contains '- **Warnings**: 2' "$(cat "$TMP_ROOT/content-exec.md")" 'merged execution issues count run-dir and live warnings'
assert_contains 'findings aggregator: ballot merge failed' "$(cat "$TMP_ROOT/content-exec.md")" 'merged execution issues include live exec detail'
assert_contains 'post-flush warning' "$(cat "$TMP_ROOT/content-exec.md")" 'merged execution issues include post-flush live warning'

rm -f "$impl_exec/execution-issues.md"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-exec-ndjson.md" \
      "$HELPER" --implement-tmpdir "$impl_exec")
assert_contains '- **Exec issues**: 0' "$(cat "$TMP_ROOT/content-exec-ndjson.md")" 'ndjson fallback keeps exec issue count at zero without exec categories'
assert_contains '- **Warnings**: 1' "$(cat "$TMP_ROOT/content-exec-ndjson.md")" 'ndjson fallback counts warning bodies without markdown headers'

impl_cost="$TMP_ROOT/impl-cost"; mkdir -p "$impl_cost/larch-logs/implement/run-cost"
printf 'ISSUE_NUMBER=12\nRUN_ID=run-cost\nADOPTED=true\n' > "$impl_cost/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_cost/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/12\n'
    printf 'PR_NUMBER=12\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_cost/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_cost/finalize-state.sh"
cat > "$impl_cost/larch-logs/implement/run-cost/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
cost_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-cost.md" \
      "$HELPER" --implement-tmpdir "$impl_cost" --print-stdout)
cost_line=$(printf '%s\n' "$cost_stdout" | grep -F -- '- **Cost**:' || true)
assert_contains '💰 TOTAL' "$cost_line" 'per-agent stdout cost has total'
assert_contains 'Claude $' "$cost_line" 'per-agent stdout cost has Claude'
assert_contains 'Codex-5.5 $' "$cost_line" 'per-agent stdout cost has Codex-5.5'
assert_contains 'Codex-mini $' "$cost_line" 'per-agent stdout cost has Codex-mini'
assert_contains 'Cursor $' "$cost_line" 'per-agent stdout cost has Cursor'
assert_contains 'Tokens: ' "$cost_line" 'per-agent stdout cost has token count'

# Retired renderer failure fallback coverage is omitted here; the final report
# wrapper now delegates to the in-process Python writer.

# Step 18 shell-wrapper body-emission coverage moved to test-step-18.sh.

# Bail + manifest.json: reconcile keys step8 off on-disk final-summary.md and hard-fails on manifest error
impl_mfb="$TMP_ROOT/impl-mfb"; mkdir -p "$impl_mfb/larch-logs/implement/run-mfb"
printf 'ISSUE_NUMBER=11\nRUN_ID=run-mfb\nADOPTED=true\n' > "$impl_mfb/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_mfb/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_mfb/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_mfb/finalize-state.sh"
printf 'NO_ISSUES=false\n' > "$impl_mfb/run-flags.sh"
printf '{"schema_version":2,"steps_ran":{}}\n' > "$impl_mfb/larch-logs/implement/run-mfb/manifest.json"
mf_log="$TMP_ROOT/mf-invoke.log"
: >"$mf_log"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" LARCH_LOG_MANIFEST_LOG="$mf_log" TRACKING_CONTENT_LOG="$TMP_ROOT/content-mfb.md" \
      "$HELPER" --implement-tmpdir "$impl_mfb")
assert_contains 'STATUS=ok' "$out" 'bail manifest stamp path status ok'
assert_contains 'steps_ran.step9a1=false' "$(cat "$mf_log")" 'manifest stamp includes step9a1 false'
assert_contains 'steps_ran.step8=true' "$(cat "$mf_log")" 'manifest stamp includes step8 true'
assert_contains 'steps_ran.step7a=false' "$(cat "$mf_log")" 'manifest stamp includes step7a false'
assert_contains '--log-root' "$(cat "$mf_log")" 'manifest forwards --log-root'
assert_contains '--skill implement' "$(cat "$mf_log")" 'manifest forwards --skill'
assert_contains '--run-id run-mfb' "$(cat "$mf_log")" 'manifest forwards --run-id'

set +e
out_mf_fail=$(CLAUDE_PLUGIN_ROOT="$plugin" LARCH_LOG_MANIFEST_FAIL=true LARCH_LOG_MANIFEST_LOG="$TMP_ROOT/mf-fail.log" \
    TRACKING_CONTENT_LOG="$TMP_ROOT/content-mf-fail.md" \
    "$HELPER" --implement-tmpdir "$impl_mfb" 2>/dev/null)
rc_mf=$?
set -e
if [ "$rc_mf" -eq 1 ]; then pass 'manifest update failure exits non-zero'; else fail 'manifest update failure exits non-zero'; fi
assert_contains 'STATUS=failed' "$out_mf_fail" 'manifest failure status failed'
assert_contains 'run-log manifest reconcile failed' "$out_mf_fail" 'manifest failure error text'

impl_badjson="$TMP_ROOT/impl-badjson"; mkdir -p "$impl_badjson/larch-logs/implement/run-badjson"
printf 'ISSUE_NUMBER=21\nRUN_ID=run-badjson\nADOPTED=true\n' > "$impl_badjson/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_badjson/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_badjson/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_badjson/finalize-state.sh"
printf '{not-json\n' > "$impl_badjson/larch-logs/implement/run-badjson/token-report.json"
badjson_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-badjson.md" \
      "$HELPER" --implement-tmpdir "$impl_badjson" --print-stdout)
assert_contains '- **Cost**: N/A' "$badjson_stdout" 'malformed token-report renders cost N/A'
assert_not_contains "Claude \$0.00, Codex-5.5 \$0.00, Codex-mini \$0.00, Cursor \$0.00" "$badjson_stdout" 'malformed token-report omits misleading zero-dollar breakdown'

impl_zero="$TMP_ROOT/impl-zero"; mkdir -p "$impl_zero/larch-logs/implement/run-zero"
printf 'ISSUE_NUMBER=22\nRUN_ID=run-zero\nADOPTED=true\n' > "$impl_zero/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_zero/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_zero/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_zero/finalize-state.sh"
cat > "$impl_zero/larch-logs/implement/run-zero/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 0}},
  "codex": {"totals": {"total": 0}},
  "cursor": {"totals": {"total": 0}},
  "claude_sub": {"totals": {"total": 0}},
  "BUCKETS_claude": {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0},
  "BUCKETS_codex": {"input": 0, "cached_input": 0, "output": 0},
  "BUCKETS_cursor": {"input": 0, "cache_read": 0, "output": 0},
  "BUCKETS_claude_sub": {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0}
}
JSON
zero_stderr="$TMP_ROOT/corrupt-zero.stderr"
zero_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-zero.md" \
      "$HELPER" --implement-tmpdir "$impl_zero" --print-stdout 2>"$zero_stderr")
assert_contains '- **Cost**: N/A' "$zero_stdout" 'corrupt-zero token-report renders cost N/A'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$zero_stdout" 'corrupt-zero warning omitted from stdout summary'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$(cat "$TMP_ROOT/content-zero.md")" 'corrupt-zero warning omitted from tracking summary body'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$(cat "$zero_stderr")" 'corrupt-zero warning omitted on stderr'
assert_not_contains "Claude \$0.00, Codex-5.5 \$0.00, Codex-mini \$0.00, Cursor \$0.00" "$zero_stdout" 'corrupt-zero token-report omits misleading zero-dollar breakdown'

impl_sub_nonzero="$TMP_ROOT/impl-sub-nonzero"; mkdir -p "$impl_sub_nonzero/larch-logs/implement/run-sub-nonzero"
printf 'ISSUE_NUMBER=23\nRUN_ID=run-sub-nonzero\nADOPTED=true\n' > "$impl_sub_nonzero/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_sub_nonzero/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_sub_nonzero/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_sub_nonzero/finalize-state.sh"
cat > "$impl_sub_nonzero/larch-logs/implement/run-sub-nonzero/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 0}},
  "codex": {"totals": {"total": 0}},
  "cursor": {"totals": {"total": 0}},
  "claude_sub": {"totals": {"total": 100}},
  "BUCKETS_claude": {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0},
  "BUCKETS_codex": {"input": 0, "cached_input": 0, "output": 0},
  "BUCKETS_cursor": {"input": 0, "cache_read": 0, "output": 0},
  "BUCKETS_claude_sub": {"input": 50, "cache_read": 10, "cache_create_5m": 20, "cache_create_1h": 0, "output": 20}
}
JSON
sub_nonzero_stderr="$TMP_ROOT/sub-nonzero.stderr"
sub_nonzero_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-sub-nonzero.md" \
      "$HELPER" --implement-tmpdir "$impl_sub_nonzero" --print-stdout 2>"$sub_nonzero_stderr")
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$sub_nonzero_stdout" 'claude_sub nonzero token-report omits corrupt warning from stdout summary'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$(cat "$TMP_ROOT/content-sub-nonzero.md")" 'claude_sub nonzero token-report omits corrupt warning from tracking summary body'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$(cat "$sub_nonzero_stderr")" 'claude_sub nonzero token-report omits corrupt warning on stderr'
sub_nonzero_cost_line=$(printf '%s\n' "$sub_nonzero_stdout" | grep -F -- '- **Cost**:' || true)
assert_contains 'Claude (subprocess)' "$sub_nonzero_cost_line" 'claude_sub nonzero cost line shows Claude (subprocess)'
assert_contains '💰 TOTAL' "$sub_nonzero_cost_line" 'claude_sub nonzero cost line has total'

impl_claude_zero="$TMP_ROOT/impl-claude-zero"; mkdir -p "$impl_claude_zero/larch-logs/implement/run-claude-zero"
printf 'ISSUE_NUMBER=23\nRUN_ID=run-claude-zero\nADOPTED=true\n' > "$impl_claude_zero/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_claude_zero/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_claude_zero/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_claude_zero/finalize-state.sh"
cat > "$impl_claude_zero/larch-logs/implement/run-claude-zero/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 0}},
  "BUCKETS_claude": {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0}
}
JSON
claude_zero_stderr="$TMP_ROOT/claude-zero.stderr"
claude_zero_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-claude-zero.md" \
      "$HELPER" --implement-tmpdir "$impl_claude_zero" --print-stdout 2>"$claude_zero_stderr")
assert_contains '- **Cost**: N/A' "$claude_zero_stdout" 'Claude-only zero token-report keeps cost unavailable rendering'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$claude_zero_stdout" 'Claude-only zero token-report omits corrupt warning from stdout summary'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$(cat "$TMP_ROOT/content-claude-zero.md")" 'Claude-only zero token-report omits corrupt warning from tracking summary body'
assert_not_contains '**⚠ token-report.json appears corrupt; reporting Cost: N/A**' "$(cat "$claude_zero_stderr")" 'Claude-only zero token-report omits corrupt warning on stderr'

make_impl_fixture() {
    local dir=$1 issue=$2 run=$3 pr_url=$4 pr_number=$5 stall=$6 merge_result=$7 merge=$8 draft=$9 forked=${10} design_only=${11} bail_user=${12}
    mkdir -p "$dir/larch-logs/implement/$run"
    printf 'ISSUE_NUMBER=%s\nRUN_ID=%s\nADOPTED=true\n' "$issue" "$run" > "$dir/parent-issue.md"
    printf 'REPO=owner/repo\n' > "$dir/session-env.sh"
    {
        printf 'PR_URL=%s\n' "$pr_url"
        printf 'PR_NUMBER=%s\n' "$pr_number"
        printf 'STALL_TRACKING=%s\n' "$stall"
        printf 'MERGE_RESULT=%s\n' "$merge_result"
        printf 'MERGE=%s\n' "$merge"
        printf 'DRAFT=%s\n' "$draft"
        printf 'FORKED_TARGET=%s\n' "$forked"
    } > "$dir/ship-pr-state.sh"
    printf 'DESIGN_ONLY_DONE=%s\nBAIL_NEEDS_USER_INPUT=%s\n' "$design_only" "$bail_user" > "$dir/finalize-state.sh"
    cat > "$dir/larch-logs/implement/$run/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
}

make_impl_fixture "$TMP_ROOT/impl-pr-created" 30 run-pr-created https://example.test/pr/30 30 false "" false false false false false
make_impl_fixture "$TMP_ROOT/impl-pr-created-draft" 31 run-pr-created-draft https://example.test/pr/31 31 false "" false true false false false
make_impl_fixture "$TMP_ROOT/impl-forked" 32 run-forked https://example.test/pr/32 32 false "" false false true false false
make_impl_fixture "$TMP_ROOT/impl-force-merged" 33 run-force-merged https://example.test/pr/33 33 false already_merged true false false false false

impl_lines="$TMP_ROOT/impl-lines"
mkdir -p "$impl_lines/larch-logs/implement/run-lines"
printf 'ISSUE_NUMBER=40\nRUN_ID=run-lines\nADOPTED=true\n' > "$impl_lines/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_lines/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/40\n'
    printf 'PR_NUMBER=40\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_lines/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_lines/finalize-state.sh"
cat > "$impl_lines/larch-logs/implement/run-lines/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
lines_out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-lines.md" \
      "$HELPER" --implement-tmpdir "$impl_lines")
assert_contains 'STATUS=ok' "$lines_out" 'line-count fixture status ok'
assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1' "$(cat "$TMP_ROOT/content-lines.md")" 'line-count fixture bucketed values'
assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1' "$(cat "$impl_lines/summary-final.md")" 'line-count fixture summary-final bucketed values'

impl_runav="$TMP_ROOT/impl-runav"
mkdir -p "$impl_runav/larch-logs/implement/run-runav"
printf 'ISSUE_NUMBER=41\nRUN_ID=run-runav\nADOPTED=true\n' > "$impl_runav/parent-issue.md"
printf 'REPO=owner/repo\nREPO_UNAVAILABLE=true\n' > "$impl_runav/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/41\n'
    printf 'PR_NUMBER=41\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_runav/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_runav/finalize-state.sh"
cat > "$impl_runav/larch-logs/implement/run-runav/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
: >"$GH_SHIM_LOG"
runav_out=$(GH_SHIM_FAIL=true CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-runav.md" \
      "$HELPER" --implement-tmpdir "$impl_runav")
assert_contains 'STATUS=ok' "$runav_out" 'repo-unavailable skips tracking upsert'
assert_contains '- **Lines (PR diff)**: N/A' "$(cat "$impl_runav/summary-final.md")" 'repo-unavailable line counts N/A'
if [ -s "$GH_SHIM_LOG" ]; then
    fail 'repo-unavailable must not invoke gh'
else
    pass 'repo-unavailable bypasses gh shim'
fi

impl_ghfail="$TMP_ROOT/impl-ghfail"
mkdir -p "$impl_ghfail/larch-logs/implement/run-ghfail"
printf 'ISSUE_NUMBER=42\nRUN_ID=run-ghfail\nADOPTED=true\n' > "$impl_ghfail/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_ghfail/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/42\n'
    printf 'PR_NUMBER=42\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_ghfail/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_ghfail/finalize-state.sh"
cat > "$impl_ghfail/larch-logs/implement/run-ghfail/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
ghfail_out=$(GH_SHIM_FAIL=true CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-ghfail.md" \
      "$HELPER" --implement-tmpdir "$impl_ghfail")
assert_contains 'STATUS=ok' "$ghfail_out" 'gh-failed line-count status ok'
assert_contains '- **Lines (PR diff)**: N/A' "$(cat "$impl_ghfail/summary-final.md")" 'gh-failed line counts N/A'

impl_line_cache="$TMP_ROOT/impl-line-cache"
mkdir -p "$impl_line_cache/larch-logs/implement/run-line-cache"
printf 'ISSUE_NUMBER=43\nRUN_ID=run-line-cache\nADOPTED=true\n' > "$impl_line_cache/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_line_cache/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/43\n'
    printf 'PR_NUMBER=43\n'
    printf 'LINES_PR_NUMBER=43\n'
    printf 'LINES_STATUS=unavailable\n'
    printf 'CODE_ADDED=999\n'
    printf 'CODE_DELETED=999\n'
    printf 'LOGS_ADDED=999\n'
    printf 'LOGS_DELETED=999\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_line_cache/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_line_cache/finalize-state.sh"
cp "$impl_lines/larch-logs/implement/run-lines/token-report.json" "$impl_line_cache/larch-logs/implement/run-line-cache/token-report.json"
line_cache_out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-line-cache.md" \
      "$HELPER" --implement-tmpdir "$impl_line_cache")
assert_contains 'STATUS=ok' "$line_cache_out" 'line-count unavailable cache status ok'
assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1' "$(cat "$impl_line_cache/summary-final.md")" 'line-count unavailable cache is recomputed'

impl_line_stale="$TMP_ROOT/impl-line-stale"
mkdir -p "$impl_line_stale/larch-logs/implement/run-line-stale"
printf 'ISSUE_NUMBER=44\nRUN_ID=run-line-stale\nADOPTED=true\n' > "$impl_line_stale/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_line_stale/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/44\n'
    printf 'PR_NUMBER=44\n'
    printf 'LINES_PR_NUMBER=43\n'
    printf 'LINES_STATUS=ok\n'
    printf 'CODE_ADDED=999\n'
    printf 'CODE_DELETED=999\n'
    printf 'LOGS_ADDED=999\n'
    printf 'LOGS_DELETED=999\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_line_stale/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_line_stale/finalize-state.sh"
cp "$impl_lines/larch-logs/implement/run-lines/token-report.json" "$impl_line_stale/larch-logs/implement/run-line-stale/token-report.json"
line_stale_out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-line-stale.md" \
      "$HELPER" --implement-tmpdir "$impl_line_stale")
assert_contains 'STATUS=ok' "$line_stale_out" 'line-count stale cache status ok'
assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1' "$(cat "$impl_line_stale/summary-final.md")" 'line-count stale PR cache is not reused'
assert_not_contains '+999/-999' "$(cat "$impl_line_stale/summary-final.md")" 'line-count stale PR cache values absent'
assert_eq "1" "$(grep -c '^LINES_STATUS=' "$impl_line_stale/ship-pr-state.sh")" 'line-count state merge replaces LINES_STATUS'
assert_eq "17" "$(awk -F= '$1=="CODE_ADDED"{print $2; exit}' "$impl_line_stale/ship-pr-state.sh")" 'line-count state merge stores latest CODE_ADDED'

for outcome_case in \
    "merged:$impl_dir:absent:present" \
    "stalled:$impl_st:present:present" \
    "design-only:$impl_do:absent:absent" \
    "bailed-needs-user-input:$impl_bu:present:absent" \
    "bailed:$impl_bl:present:absent" \
    "forked-dry-run:$TMP_ROOT/impl-forked:absent:present" \
    "pr-created:$TMP_ROOT/impl-pr-created:absent:present" \
    "pr-created-draft:$TMP_ROOT/impl-pr-created-draft:absent:present" \
    "force-merged-externally:$TMP_ROOT/impl-force-merged:absent:present"
do
    IFS=: read -r expected fixture expect_outcome expect_pr <<EOF
$outcome_case
EOF
    matrix_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/matrix-${expected}.md" \
        "$HELPER" --implement-tmpdir "$fixture" --print-stdout)
    matrix_summary="$(stdout_summary_block "$matrix_stdout")"
    cost_line=$(printf '%s\n' "$matrix_summary" | grep -F -- '- **Cost**:' || true)
    assert_contains "## /implement run " "$matrix_summary" "matrix $expected prints summary title"
    assert_contains ": $expected" "$matrix_summary" "matrix $expected title outcome"
    assert_contains '- **Cost**:' "$matrix_summary" "matrix $expected prints cost line"
    assert_contains '<!-- larch:run-summary v=1 -->' "$matrix_summary" "matrix $expected keeps sentinel"
    cmp -s <(printf '%s\n' "$matrix_summary") "$fixture/summary-final.md" || fail "matrix $expected stdout summary/file mismatch"
    assert_contains "## /implement run " "$(cat "$fixture/summary-final.md")" "matrix $expected file prints summary title"
    assert_contains ": $expected" "$(cat "$fixture/summary-final.md")" "matrix $expected file title outcome"
    assert_contains '- **Cost**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file prints cost line"
    assert_contains '<!-- larch:run-summary v=1 -->' "$(cat "$fixture/summary-final.md")" "matrix $expected file keeps sentinel"
    if [ "$expected" = "merged" ] || [ "$expected" = "forked-dry-run" ] || [ "$expected" = "pr-created" ] || [ "$expected" = "pr-created-draft" ] || [ "$expected" = "force-merged-externally" ]; then
        assert_contains '💰 TOTAL' "$cost_line" "matrix $expected cost line has total"
        assert_contains 'Claude $' "$cost_line" "matrix $expected cost line has Claude"
        assert_contains 'Codex-5.5 $' "$cost_line" "matrix $expected cost line has Codex-5.5"
        assert_contains 'Codex-mini $' "$cost_line" "matrix $expected cost line has Codex-mini"
        assert_contains 'Cursor $' "$cost_line" "matrix $expected cost line has Cursor"
        assert_contains 'Tokens: ' "$cost_line" "matrix $expected cost line has token count"
    fi
    if [ "$expect_outcome" = present ]; then
        assert_contains "- **Outcome**: $expected" "$matrix_summary" "matrix $expected emits Outcome bullet"
        assert_contains "- **Outcome**: $expected" "$(cat "$fixture/summary-final.md")" "matrix $expected file emits Outcome bullet"
    else
        assert_not_contains '- **Outcome**:' "$matrix_summary" "matrix $expected omits Outcome bullet"
        assert_not_contains '- **Outcome**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file omits Outcome bullet"
    fi
    if [ "$expect_pr" = present ]; then
        assert_contains '- **PR**:' "$matrix_summary" "matrix $expected emits PR bullet"
        assert_contains '- **PR**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file emits PR bullet"
    else
        assert_not_contains '- **PR**:' "$matrix_summary" "matrix $expected omits PR bullet"
        assert_not_contains '- **PR**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file omits PR bullet"
    fi
done

# --- Review Phase Detail injection (issue #3774) ---
# round-meta.json must be under run_dir (larch-logs/implement/$RUN_ID/round-N/), not
# directly under IMPLEMENT_TMPDIR/round-N/. See issue #3794 for the path-mismatch bug.
rpd_dir="$TMP_ROOT/impl-rpd"; mkdir -p "$rpd_dir/larch-logs/implement/run-rpd/round-1" "$rpd_dir/round-1"
printf 'ISSUE_NUMBER=11\nRUN_ID=run-rpd\nADOPTED=true\n' > "$rpd_dir/parent-issue.md"
printf 'REPO=owner/repo\n' > "$rpd_dir/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/11\n'
    printf 'PR_NUMBER=11\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$rpd_dir/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\n' > "$rpd_dir/finalize-state.sh"
# round-meta.json lives under run_dir (the committed run-log dir), not the live working dir.
cat > "$rpd_dir/larch-logs/implement/run-rpd/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"1","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"1","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":4}}}
JSON
# panel-manifest.ndjson stays in the live working dir (not committed to run-log).
cat > "$rpd_dir/round-1/panel-manifest.ndjson" <<'JSON'
{"slot":"correctness","tool":"cursor","output":"/t/round-1/cursor-specialist-correctness-output.txt"}
JSON
cat > "$rpd_dir/larch-logs/implement/run-rpd/review-findings-full.jsonl" <<'JSON'
{"id":"FINDING_1","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1"}
{"id":"FINDING_2","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1"}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000065\t65\t2\t1\t1\t-\n'
    printf 'v1\tvendor\t1700000010\timplement\t-\tcursor\treview\t1700000010\t1700000060\t50\tcursor-specialist-correctness-output.txt\t0\tcomplete\n'
} > "$rpd_dir/timing-ledger.tsv"
CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-rpd.md" \
      "$HELPER" --implement-tmpdir "$rpd_dir" >/dev/null
rpd_body="$(cat "$TMP_ROOT/content-rpd.md")"
assert_contains '## Review Phase Detail' "$rpd_body" 'review phase detail section injected'
assert_contains '| 1 | 3 | 2 | 1 | 0 |' "$rpd_body" 'review phase detail round-1 counts'
assert_contains 'cursor/correctness: 2' "$rpd_body" 'review phase detail top reviewer'
# Completed-review output can include reviewer timing ASCII Gantt charts.
assert_contains '### Round 1 reviewer timing' "$rpd_body" 'review phase detail includes reviewer timing heading'
assert_contains '```' "$rpd_body" 'review phase detail includes plain ASCII fence'
assert_not_contains '```mermaid' "$rpd_body" 'review phase detail omits Mermaid fence'
assert_not_contains 'dateFormat X' "$rpd_body" 'review phase detail omits Mermaid dateFormat'
assert_not_contains 'axisFormat %H:%M:%S' "$rpd_body" 'review phase detail omits hour axisFormat'
assert_contains 'cursor/correctness' "$rpd_body" 'review phase detail includes ASCII chart label'
assert_contains '50s' "$rpd_body" 'review phase detail includes bare ASCII duration'
assert_contains 'window 0:00-1:05 (65s)' "$rpd_body" 'review phase detail uses ledger round-window title span'
# Regression (issue #3794): round-meta.json only under live working dir -> no completed rounds for selected root.
# This reproduces the path-mismatch bug: renderer must NOT find the table when
# round-meta.json exists only under IMPLEMENT_TMPDIR/round-N/ (old wrong root).
rpd_dir_regression="$TMP_ROOT/impl-rpd-regression"
mkdir -p "$rpd_dir_regression/larch-logs/implement/run-rpd-r" "$rpd_dir_regression/round-1"
printf 'ISSUE_NUMBER=50\nRUN_ID=run-rpd-r\nADOPTED=true\n' > "$rpd_dir_regression/parent-issue.md"
printf 'REPO=owner/repo\n' > "$rpd_dir_regression/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/50\n'
    printf 'PR_NUMBER=50\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$rpd_dir_regression/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\n' > "$rpd_dir_regression/finalize-state.sh"
# round-meta.json only in live working dir — NOT in run_dir; renderer must skip it.
cat > "$rpd_dir_regression/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}
JSON
cat > "$rpd_dir_regression/larch-logs/implement/run-rpd-r/review-findings-full.jsonl" <<'JSON'
{"id":"FINDING_1","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1"}
JSON
CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-rpd-regression.md" \
      "$HELPER" --implement-tmpdir "$rpd_dir_regression" >/dev/null
rpd_regression_body="$(cat "$TMP_ROOT/content-rpd-regression.md")"
assert_not_contains '| 1 | 2 | 2 | 0 | 0 |' "$rpd_regression_body" 'regression #3794: round-meta only in live dir -> completed row absent'
assert_contains '## Review Phase Detail' "$rpd_regression_body" 'regression #3794: selected valid root still renders section'
assert_contains 'No review rounds completed.' "$rpd_regression_body" 'regression #3794: selected valid root renders no-round message'
# Happy path (run-5) has no review rounds -> section now reports no completed rounds.
assert_contains '## Review Phase Detail' "$(cat "$TMP_ROOT/content.md")" 'no review rounds -> section included'
assert_contains 'No review rounds completed.' "$(cat "$TMP_ROOT/content.md")" 'no review rounds -> no-round message included'

finish
