#!/usr/bin/env bash
# test-step2-dispatch.sh — Offline harness for skills/implement/scripts/step2-implement.sh.
#
# Covers the dispatcher branches that do NOT require spawning an external implementer
# (for the full per-test inventory see test-step2-dispatch.md):
#   - --coder claude → STATUS=claude_fallback (no launcher run; no baseline-file leak).
#   - missing --coder exits 2 (Step 0 is the sole omitted-coder authority).
#   - Legacy --codex-available false → STATUS=claude_fallback + deprecation warning on stderr.
#   - Bad --coder enum value → exit 2 and names {claude,codex,cursor}.
#   - --coder cursor with false/missing/empty health → STATUS=claude_fallback (no baseline-file leak; Step 2 backstop when Step 1 did not bail for explicit unhealthy Cursor).
#   - Test 3e: explicit --coder cursor --cursor-present true reaches external Cursor launcher (stub-bailed).
#   - Bad --cursor-present enum value → exit 2.
#   - --coder claude --cursor-present "" → STATUS=claude_fallback.
#   - --coder cursor outside a git work-tree with false health → claude_fallback before REPO_ROOT lookup.
#   - --coder + --codex-available together → exit 2 (mutex).
#   - Bad --codex-available enum value → exit 2.
#   - Bad --tmpdir → exit 2.
#   - Pre-seeded resume counter at 5; 6th --answers invocation → STATUS=bailed REASON=qa-loop-exceeded.
#   - --answers but file does not exist → exit 2.
#   - Corrupt resume counter → STATUS=bailed REASON=manifest-schema-invalid.
#   - --coder codex outside a git working tree → exit 2 (no baseline-file leak).
#   - First codex invocation writes step2-spawn-coder.txt with the resolved coder.
#   - Second invocation against same tmpdir with mismatched --coder → STATUS=bailed
#     REASON=coder-mismatch-tmpdir-reuse TOOL=<current-tool>.
#   - In a scratch git repo without .claude-plugin/plugin.json, a stub-Codex
#     run that touches only non-protected files reaches STATUS=complete
#     (no false-positive REASON=protected-path-modified — issue #1475).
#   - --workflow SIMPLE is accepted (STATUS=claude_fallback as normal).
#   - --workflow HARD is accepted (STATUS=claude_fallback as normal).
#   - --workflow bogus exits 2 with the exact error message.
#   - needs_qa repair path: stub-Codex writes a needs_qa manifest without
#     needs_qa.questions and a qa-pending.json with items[] format; dispatcher
#     normalizes to questions[] and emits STATUS=needs_qa (not bailed — issue #1883).
#   - --workflow SIMPLE passed to a stub-Codex run results in --timeout 3600 passed
#     to the launcher (verified via the .meta file written by run-external-agent.sh).
#   - --workflow HARD passed to a stub-Codex run results in --timeout 7200.
#   - --workflow omitted (default) passed to a stub-Codex run results in --timeout 3600
#     (default workflow resolves to SIMPLE).
#   - Test 19 / 19a / 19b: protected spawn branch (`main` or `master`) +
#     issue-anchored tmpdir → `main-branch-prohibited` before stub Cursor runs
#     (19b: `ISSUE_NUMBER` from `parent-issue.md` when absent from session-env).
#   - Test 19d: `main` spawn with neither session-env nor parent-issue (unanchored
#     harness tmpdir) → must not emit `main-branch-prohibited`; stub launcher runs.
#   - Test 19e: detached HEAD + issue-anchored session-env → `detached-head-prohibited`.
#   - Test 20: scratch repo after create-branch.sh --branch (simulates SKILL.md creation path);
#     dispatcher must NOT emit `main-branch-prohibited` (may bail cursor-runtime-failure from stub).
#   - Test 21: scratch repo already on user-prefix branch without create-branch; same dispatcher assertion.
#
# External-implementer spawning paths (manifest validation, dispatcher-side commit,
# sanitization, launcher-retry) are covered by separate launcher / end-to-end tests;
# this offline harness intentionally stays narrow so it runs in <1s with no
# external dependencies.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DISPATCHER="$REPO_ROOT/skills/implement/scripts/step2-implement.sh"

[[ -x "$DISPATCHER" ]] || { echo "FAIL: dispatcher not executable: $DISPATCHER" >&2; exit 1; }

PASS_COUNT=0
FAIL_COUNT=0
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }

# Temp scratch.
SCRATCH=$(mktemp -d -t step2-dispatch-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

PLAN="$SCRATCH/plan.md"
FEATURE="$SCRATCH/feature.txt"
echo "fake plan" > "$PLAN"
echo "fake feature" > "$FEATURE"

# ---------------------------------------------------------------------------
# Test 1: --coder claude → STATUS=claude_fallback, no other keys.
# ---------------------------------------------------------------------------
TMP1="$SCRATCH/test1"; mkdir -p "$TMP1"
OUT=$("$DISPATCHER" --tmpdir "$TMP1" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]] \
   && [[ "$OUT" != *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT" != *"MANIFEST="* ]] \
   && [[ "$OUT" != *"TRANSCRIPT="* ]]; then
    pass
else
    fail 1 "claude_fallback branch wrong output: $OUT"
fi
# Baseline files MUST NOT have been written on the claude_fallback branch.
if [[ -f "$TMP1/step2-baseline.txt" ]]; then
    fail 1 "claude_fallback branch leaked baseline file"
else
    pass
fi

# ---------------------------------------------------------------------------
# Test 1b: missing --coder exits 2. Step 0 is the sole omitted-coder authority.
# ---------------------------------------------------------------------------
TMP1B="$SCRATCH/test1b"; mkdir -p "$TMP1B"
NON_GIT_DIR_1B="$SCRATCH/test1b-nongit"; mkdir -p "$NON_GIT_DIR_1B"
EXIT=0
ERR=$(cd "$NON_GIT_DIR_1B" && "$DISPATCHER" --tmpdir "$TMP1B" --plan-file "$PLAN" --feature-file "$FEATURE" \
    2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"--coder is required"* ]]; then
    pass
else
    fail 1b "missing --coder should exit 2 before git resolution, got exit=$EXIT err=$ERR"
fi
if [[ -f "$TMP1B/step2-baseline.txt" ]]; then
    fail 1b "missing --coder should not leak baseline file"
else
    pass
fi

# ---------------------------------------------------------------------------
# Test 1c: --codex-available false → claude_fallback + deprecation warning.
# ---------------------------------------------------------------------------
TMP1C="$SCRATCH/test1c"; mkdir -p "$TMP1C"
ERR=$("$DISPATCHER" --tmpdir "$TMP1C" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --codex-available false 2>&1 >/dev/null)
OUT=$("$DISPATCHER" --tmpdir "$TMP1C" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --codex-available false 2>/dev/null)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]] \
   && [[ "$ERR" == *"deprecated"* ]]; then
    pass
else
    fail 1c "--codex-available false should claude_fallback + deprecate, out=$OUT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 3: bad --coder enum value → exit 2.
# ---------------------------------------------------------------------------
TMP3="$SCRATCH/test3"; mkdir -p "$TMP3"
EXIT=0
ERR=$("$DISPATCHER" --tmpdir "$TMP3" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder bogus 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"{claude,codex,cursor}"* ]]; then
    pass
else
    fail 3 "bad --coder value should exit 2 and name {claude,codex,cursor}, got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 3b: --coder cursor --cursor-present false → claude_fallback.
# ---------------------------------------------------------------------------
TMP3B="$SCRATCH/test3b"; mkdir -p "$TMP3B"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder cursor --cursor-present false 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b "--coder cursor with unhealthy gate should fall back to claude, got: $OUT"
fi
if [[ -f "$TMP3B/step2-baseline.txt" ]]; then
    fail 3b "cursor unhealthy fallback branch leaked baseline file"
else
    pass
fi

# ---------------------------------------------------------------------------
# Test 3e: explicit --coder cursor --cursor-present true reaches external Cursor
# launcher (distinct from default-coder Test 1b and unhealthy Test 3b).
# ---------------------------------------------------------------------------
TMP3E="$SCRATCH/test3e"; mkdir -p "$TMP3E"
STUB_BIN_3E="$SCRATCH/test3e-bin"; mkdir -p "$STUB_BIN_3E"
STUB_CURSOR_3E="$STUB_BIN_3E/cursor"
cat > "$STUB_CURSOR_3E" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
cat > "$STUB_MANIFEST_PATH.tmp" <<'JSON'
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'stub cursor stdout\n'
EOF
chmod +x "$STUB_CURSOR_3E"
STDOUT_3E="$TMP3E/stdout.txt"
STDERR_3E="$TMP3E/stderr.txt"
set +e
(
    cd "$REPO_ROOT" && \
    PATH="$STUB_BIN_3E:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STUB_MANIFEST_PATH="$TMP3E/manifest.json" \
    LARCH_TIMING_LEDGER="$TMP3E/timing-ledger.tsv" \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP3E" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true >"$STDOUT_3E" 2>"$STDERR_3E"
)
_3e_rc=$?
set -e
OUT=$(cat "$STDOUT_3E")
ERR=$(cat "$STDERR_3E")
if [[ "$_3e_rc" -ne 0 ]]; then
    fail 3e "explicit healthy cursor dispatcher exited non-zero (rc=$_3e_rc) out=$(cat "$STDOUT_3E" 2>/dev/null || true) err=$(cat "$STDERR_3E" 2>/dev/null || true)"
fi
if [[ "$OUT" == *"STATUS=bailed"* ]] \
   && [[ "$OUT" == *"REASON=stub-bailed"* ]] \
   && [[ "$OUT" == *"TOOL=cursor"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT" != *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]] \
   && [[ -f "$TMP3E/step2-spawn-coder.txt" ]] \
   && [[ "$(cat "$TMP3E/step2-spawn-coder.txt")" == "cursor" ]]; then
    pass
else
    fail 3e "explicit healthy cursor should reach stub launcher, got out=$OUT err=$ERR sentinel=$(cat "$TMP3E/step2-spawn-coder.txt" 2>/dev/null || echo MISSING)"
fi

# ---------------------------------------------------------------------------
# Test 3b2: --coder cursor with no --cursor-present defaults to false.
# ---------------------------------------------------------------------------
TMP3B2="$SCRATCH/test3b2"; mkdir -p "$TMP3B2"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B2" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder cursor 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b2 "--coder cursor without health should fall back to claude, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 3b3: --coder cursor --cursor-present "" treats empty as false.
# ---------------------------------------------------------------------------
TMP3B3="$SCRATCH/test3b3"; mkdir -p "$TMP3B3"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B3" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder cursor --cursor-present "" 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b3 "--coder cursor with empty health should fall back to claude, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 3b4: bogus --cursor-present value exits 2.
# ---------------------------------------------------------------------------
TMP3B4="$SCRATCH/test3b4"; mkdir -p "$TMP3B4"
EXIT=0
ERR=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B4" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder cursor --cursor-present bogus 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"--cursor-present must be 'true', 'false', or empty"* ]]; then
    pass
else
    fail 3b4 "bad --cursor-present should exit 2, got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 3b5: --coder claude --cursor-present "" remains claude_fallback.
# ---------------------------------------------------------------------------
TMP3B5="$SCRATCH/test3b5"; mkdir -p "$TMP3B5"
OUT=$("$DISPATCHER" --tmpdir "$TMP3B5" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude --cursor-present "" 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b5 "claude path should ignore empty cursor health, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 3b6: outside git tree, unhealthy Cursor falls back before REPO_ROOT lookup.
# ---------------------------------------------------------------------------
TMP3B6="$SCRATCH/test3b6"; mkdir -p "$TMP3B6"
NON_GIT_CURSOR_DIR="$SCRATCH/not-a-repo-cursor"; mkdir -p "$NON_GIT_CURSOR_DIR"
OUT=$(cd "$NON_GIT_CURSOR_DIR" && "$DISPATCHER" --tmpdir "$TMP3B6" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder cursor --cursor-present false 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b6 "cursor unhealthy fallback should win before git-tree lookup, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 3c: --coder + --codex-available together → exit 2 (mutex).
# ---------------------------------------------------------------------------
EXIT=0
ERR=$("$DISPATCHER" --tmpdir "$SCRATCH/test3c" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude --codex-available false 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"mutually exclusive"* ]]; then
    pass
else
    fail 3c "--coder + --codex-available should be mutually exclusive, got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 3d: bad --codex-available enum value → exit 2.
# ---------------------------------------------------------------------------
EXIT=0
"$DISPATCHER" --tmpdir "$SCRATCH/test3d" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --codex-available maybe >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 3d "bad --codex-available value should exit 2, got $EXIT"; fi

# ---------------------------------------------------------------------------
# Test 4: bad --tmpdir (not a directory) → exit 2.
# ---------------------------------------------------------------------------
EXIT=0
"$DISPATCHER" --tmpdir "$SCRATCH/nonexistent" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 4 "missing tmpdir should exit 2, got $EXIT"; fi

# ---------------------------------------------------------------------------
# Test 5: resume cap. Pre-seed step2-baseline / spawn-branch / plugin-json /
# resume-counter to simulate the 6th --answers invocation. Dispatcher should
# bail with REASON=qa-loop-exceeded BEFORE attempting to spawn Codex.
# ---------------------------------------------------------------------------
TMP5="$SCRATCH/test5"; mkdir -p "$TMP5"
git -C "$REPO_ROOT" rev-parse HEAD > "$TMP5/step2-baseline.txt"
git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD > "$TMP5/step2-spawn-branch.txt"
if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
    git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$TMP5/step2-plugin-json-baseline.txt"
else
    : > "$TMP5/step2-plugin-json-baseline.txt"
fi
echo "5" > "$TMP5/codex-resume-count.txt"
ANSWERS="$SCRATCH/answers.json"
echo '{"answers":[{"id":"q1","text":"x"}]}' > "$ANSWERS"

OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP5" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex --answers "$ANSWERS" 2>&1)
if [[ "$OUT" == *"STATUS=bailed"* ]] \
   && [[ "$OUT" == *"REASON=qa-loop-exceeded"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT" != *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 5 "resume cap should emit qa-loop-exceeded with AUTH=forbidden, got: $OUT"
fi
if [[ -f "$TMP5/codex-resume-count.txt" ]]; then
    pass
else
    fail 5 "Codex path should retain codex-resume-count.txt filename"
fi

# ---------------------------------------------------------------------------
# Test 6: --answers but file does not exist → exit 2.
# ---------------------------------------------------------------------------
EXIT=0
( cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP5" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex --answers "$SCRATCH/missing-answers.json" \
    >/dev/null 2>&1 ) || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 6 "missing --answers file should exit 2, got $EXIT"; fi

# ---------------------------------------------------------------------------
# Test 7: corrupt resume counter (non-numeric) → STATUS=bailed
# REASON=manifest-schema-invalid (defense-in-depth against tmpdir tampering).
# ---------------------------------------------------------------------------
TMP7="$SCRATCH/test7"; mkdir -p "$TMP7"
git -C "$REPO_ROOT" rev-parse HEAD > "$TMP7/step2-baseline.txt"
git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD > "$TMP7/step2-spawn-branch.txt"
if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
    git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$TMP7/step2-plugin-json-baseline.txt"
else
    : > "$TMP7/step2-plugin-json-baseline.txt"
fi
echo "garbage" > "$TMP7/codex-resume-count.txt"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP7" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex --answers "$ANSWERS" 2>&1)
if [[ "$OUT" == *"STATUS=bailed"* ]] \
   && [[ "$OUT" == *"REASON=manifest-schema-invalid"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]]; then
    pass
else
    fail 7 "corrupt resume counter should bail with manifest-schema-invalid + AUTH=forbidden, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 8: --coder codex outside a git working tree → exit 2
# (the new git-tree precondition added when REPO_ROOT was switched from
# SCRIPT_DIR-relative to git rev-parse --show-toplevel; closes the
# plugin-cache fallback regression).
# ---------------------------------------------------------------------------
TMP8="$SCRATCH/test8"; mkdir -p "$TMP8"
NON_GIT_DIR="$SCRATCH/not-a-repo"; mkdir -p "$NON_GIT_DIR"
EXIT=0
ERR=$(cd "$NON_GIT_DIR" && "$DISPATCHER" --tmpdir "$TMP8" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"must be invoked from within a git working tree"* ]]; then
    pass
else
    fail 8 "non-git cwd on Codex path should exit 2 with git-tree message, got exit=$EXIT err=$ERR"
fi
# A failed pre-spawn validation MUST NOT have written baseline files.
if [[ -f "$TMP8/step2-baseline.txt" ]]; then
    fail 8 "non-git cwd exit-2 leaked baseline file"
else
    pass
fi

# ---------------------------------------------------------------------------
# Test 9: first codex invocation writes step2-spawn-coder.txt. Reuse the
# Test 5 setup (pre-seeded baselines + resume counter at 5) so the dispatcher
# bails on qa-loop-exceeded AFTER the cross-coder guard records the coder.
# Asserts the sentinel file exists with content "codex".
# ---------------------------------------------------------------------------
TMP9="$SCRATCH/test9"; mkdir -p "$TMP9"
git -C "$REPO_ROOT" rev-parse HEAD > "$TMP9/step2-baseline.txt"
git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD > "$TMP9/step2-spawn-branch.txt"
if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
    git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$TMP9/step2-plugin-json-baseline.txt"
else
    : > "$TMP9/step2-plugin-json-baseline.txt"
fi
echo "5" > "$TMP9/codex-resume-count.txt"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP9" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex --answers "$ANSWERS" 2>&1)
if [[ -f "$TMP9/step2-spawn-coder.txt" ]] && [[ "$(cat "$TMP9/step2-spawn-coder.txt")" == "codex" ]]; then
    pass
else
    fail 9 "first codex invocation should write step2-spawn-coder.txt=codex, got: $(cat "$TMP9/step2-spawn-coder.txt" 2>/dev/null || echo MISSING)"
fi

# ---------------------------------------------------------------------------
# Test 10: second invocation against a tmpdir that recorded a different coder
# bails with coder-mismatch-tmpdir-reuse before touching shared baselines or
# resume counters. Pre-seed sentinel=codex + baselines, then invoke with
# --coder=cursor --cursor-present true so the cursor health gate passes and
# the cross-coder guard is the first state mutation reached.
# ---------------------------------------------------------------------------
TMP10="$SCRATCH/test10"; mkdir -p "$TMP10"
git -C "$REPO_ROOT" rev-parse HEAD > "$TMP10/step2-baseline.txt"
git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD > "$TMP10/step2-spawn-branch.txt"
if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
    git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$TMP10/step2-plugin-json-baseline.txt"
else
    : > "$TMP10/step2-plugin-json-baseline.txt"
fi
echo "codex" > "$TMP10/step2-spawn-coder.txt"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP10" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder cursor --cursor-present true 2>&1)
if [[ "$OUT" == *"STATUS=bailed"* ]] \
   && [[ "$OUT" == *"REASON=coder-mismatch-tmpdir-reuse"* ]] \
   && [[ "$OUT" == *"TOOL=cursor"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT" != *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 10 "cross-coder reuse should bail with coder-mismatch-tmpdir-reuse TOOL=cursor + AUTH=forbidden, got: $OUT"
fi
# Sentinel content must be unchanged (still codex) — guard must not overwrite.
if [[ "$(cat "$TMP10/step2-spawn-coder.txt")" == "codex" ]]; then
    pass
else
    fail 10 "sentinel file overwritten on mismatch path: $(cat "$TMP10/step2-spawn-coder.txt")"
fi
# The cursor-resume-count.txt must NOT have been written — the guard runs
# before the resume-counter logic.
if [[ -f "$TMP10/cursor-resume-count.txt" ]]; then
    fail 10 "coder-mismatch path leaked cursor-resume-count.txt"
else
    pass
fi

# ---------------------------------------------------------------------------
# Test 11: ORCHESTRATOR_EDIT_AUTHORITY pair invariant — every reachable exit-0
# outcome from this offline harness emits exactly one
# ORCHESTRATOR_EDIT_AUTHORITY line, with `allowed` iff STATUS=claude_fallback.
# Re-runs minimal claude_fallback + bailed scenarios and asserts the iff.
# ---------------------------------------------------------------------------
TMP11A="$SCRATCH/test11a"; mkdir -p "$TMP11A"
OUT_A=$("$DISPATCHER" --tmpdir "$TMP11A" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude 2>&1)
AUTH_A_LINES=$(printf '%s\n' "$OUT_A" | grep -c '^ORCHESTRATOR_EDIT_AUTHORITY=' || true)
if [[ "$AUTH_A_LINES" == "1" ]] \
   && [[ "$OUT_A" == *"STATUS=claude_fallback"* ]] \
   && [[ "$OUT_A" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 11a "pair invariant: claude_fallback must emit exactly one AUTH=allowed line, got auth_lines=$AUTH_A_LINES out=$OUT_A"
fi

TMP11B="$SCRATCH/test11b"; mkdir -p "$TMP11B"
git -C "$REPO_ROOT" rev-parse HEAD > "$TMP11B/step2-baseline.txt"
git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD > "$TMP11B/step2-spawn-branch.txt"
if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
    git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$TMP11B/step2-plugin-json-baseline.txt"
else
    : > "$TMP11B/step2-plugin-json-baseline.txt"
fi
echo "5" > "$TMP11B/codex-resume-count.txt"
OUT_B=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP11B" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder codex --answers "$ANSWERS" 2>&1)
AUTH_B_LINES=$(printf '%s\n' "$OUT_B" | grep -c '^ORCHESTRATOR_EDIT_AUTHORITY=' || true)
if [[ "$AUTH_B_LINES" == "1" ]] \
   && [[ "$OUT_B" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_B" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT_B" != *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 11b "pair invariant: external bailed must emit exactly one AUTH=forbidden line, got auth_lines=$AUTH_B_LINES out=$OUT_B"
fi

# ---------------------------------------------------------------------------
# Test 12: canonical --tmpdir/session-id overwrites stale token session env
# before the launcher subprocess runs.
# ---------------------------------------------------------------------------
STUB_BIN="$SCRATCH/stub-bin"; mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_TOKEN_SESSION_FILE:?}"
: "${STEP2_MANIFEST_PATH:?}"
printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$STEP2_TOKEN_SESSION_FILE"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub transcript\n' > "$output_path"
cat > "$STEP2_MANIFEST_PATH.tmp" <<JSON
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUB_CODEX
chmod +x "$STUB_BIN/codex"

TMP12A="$SCRATCH/test12a"; mkdir -p "$TMP12A"
printf 'fresh-step2-A\n' > "$TMP12A/session-id"
TOKEN12A="$SCRATCH/token12a.txt"
OUT_12A=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_TOKEN_SESSION_FILE="$TOKEN12A" \
    STEP2_MANIFEST_PATH="$TMP12A/codex-step2-out/manifest.json" \
    LARCH_TOKEN_SESSION_ID=stale-step2 \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP12A" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
if [[ "$OUT_12A" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_12A" == *"REASON=stub-bailed"* ]] \
   && [[ "$(cat "$TOKEN12A")" == "fresh-step2-A" ]]; then
    pass
else
    fail 12a "step2 should export fresh tmpdir session id to launcher, out=$OUT_12A token=$(cat "$TOKEN12A" 2>/dev/null)"
fi

TMP12B="$SCRATCH/test12b"; mkdir -p "$TMP12B"
printf 'fresh-step2-B\n' > "$TMP12B/session-id"
TOKEN12B="$SCRATCH/token12b.txt"
OUT_12B=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_TOKEN_SESSION_FILE="$TOKEN12B" \
    STEP2_MANIFEST_PATH="$TMP12B/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP12B" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
if [[ "$OUT_12B" == *"STATUS=bailed"* ]] && [[ "$(cat "$TOKEN12B")" == "fresh-step2-B" ]]; then
    pass
else
    fail 12b "second tmpdir should export its own session id, out=$OUT_12B token=$(cat "$TOKEN12B" 2>/dev/null)"
fi

# ---------------------------------------------------------------------------
# Test 13: in a git repo WITHOUT .claude-plugin/plugin.json, a successful
# implementer run that does NOT touch plugin.json must reach STATUS=complete
# (not bail with REASON=protected-path-modified). Regression coverage for
# issue #1475 — absent-then-still-absent must compare equal in Step 6b.
# ---------------------------------------------------------------------------
TMP13="$SCRATCH/test13"; mkdir -p "$TMP13"
printf 'fresh-step2-13\n' > "$TMP13/session-id"

# Scratch git repo with no .claude-plugin/plugin.json.
SCRATCH_REPO="$SCRATCH/scratch-repo-13"
mkdir -p "$SCRATCH_REPO"
git -C "$SCRATCH_REPO" init -q -b main
git -C "$SCRATCH_REPO" config user.email "test@example.com"
git -C "$SCRATCH_REPO" config user.name "Test"
echo "initial" > "$SCRATCH_REPO/README.md"
git -C "$SCRATCH_REPO" add README.md
git -C "$SCRATCH_REPO" commit -q -m "init"
[[ ! -e "$SCRATCH_REPO/.claude-plugin/plugin.json" ]] || \
    fail 13 "scratch repo precondition: plugin.json should not exist"

# Stub codex: modify a benign file in the working tree and write a
# status=complete manifest. Does NOT touch .claude-plugin/plugin.json.
STUB13="$SCRATCH/stub-bin-13"; mkdir -p "$STUB13"
cat > "$STUB13/codex" <<'STUB13_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub transcript\n' > "$output_path"
# Modify a benign tracked file. Working tree is the dispatcher's cwd.
echo "edited by stub" >> "$PWD/README.md"
cat > "$STEP2_MANIFEST_PATH.tmp" <<JSON
{
  "schema_version": "1",
  "status": "complete",
  "files_touched": [{"path": "README.md"}],
  "commit_message": "stub: edit README",
  "summary_bullets": ["edited README"],
  "tests_added_or_modified": [],
  "todos_left": [],
  "oos_observations": []
}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUB13_CODEX
chmod +x "$STUB13/codex"

OUT_13=$(cd "$SCRATCH_REPO" && \
    PATH="$STUB13:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP13/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP13" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)

if [[ "$OUT_13" == *"STATUS=complete"* ]] \
   && [[ "$OUT_13" != *"REASON=protected-path-modified"* ]] \
   && [[ "$OUT_13" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT_13" != *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]] \
   && [[ "$OUT_13" == *"MANIFEST="* ]]; then
    pass
else
    fail 13 "absent plugin.json + benign edit should reach STATUS=complete with AUTH=forbidden + MANIFEST= (no protected-path-modified false positive); got: $OUT_13"
fi

# ---------------------------------------------------------------------------
# Test 14: cap-hit path. When LARCH_TOKEN_BUDGET_CAP_IMPLEMENT=1 and the
# token ledger shows vendor spend >= 1, the launcher short-circuits with
# STATUS=cap_hit on stdout. The dispatcher must surface STATUS=bailed
# REASON=cap_hit ORCHESTRATOR_EDIT_AUTHORITY=forbidden without retrying.
# No stub coder binary is needed — the launcher exits before spawning one.
# ---------------------------------------------------------------------------
TMP14="$SCRATCH/test14"; mkdir -p "$TMP14"
CH14_SESSION="cap-hit-step2-$$-$RANDOM"
# Ledger must live under TMPDIR: token-ledger.sh validate_under_tmp rejects paths outside it.
CH14_LEDGER="${TMPDIR:-/tmp}/cap-hit-step2-ledger-$$-$RANDOM.jsonl"
printf '{"type":"vendor","vendor":"codex","total":9999}\n' > "$CH14_LEDGER"

OUT_14=$(cd "$REPO_ROOT" && \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_TOKEN_SESSION_ID="$CH14_SESSION" \
    LARCH_TOKEN_LEDGER="$CH14_LEDGER" \
    LARCH_TOKEN_BUDGET_CAP_IMPLEMENT=1 \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP14" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
rm -f "$CH14_LEDGER"

if [[ "$OUT_14" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_14" == *"REASON=cap_hit"* ]] \
   && [[ "$OUT_14" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$OUT_14" != *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 14 "cap_hit path should emit STATUS=bailed REASON=cap_hit AUTH=forbidden; got: $OUT_14"
fi

# ---------------------------------------------------------------------------
# Test 15a: --workflow SIMPLE is accepted (STATUS=claude_fallback as normal).
# ---------------------------------------------------------------------------
TMP15A="$SCRATCH/test15a"; mkdir -p "$TMP15A"
OUT=$(  "$DISPATCHER" --tmpdir "$TMP15A" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude --workflow SIMPLE 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 15a "--workflow SIMPLE should be accepted, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 15b: --workflow HARD is accepted (STATUS=claude_fallback as normal).
# ---------------------------------------------------------------------------
TMP15B="$SCRATCH/test15b"; mkdir -p "$TMP15B"
OUT=$(  "$DISPATCHER" --tmpdir "$TMP15B" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude --workflow HARD 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 15b "--workflow HARD should be accepted, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 15c: --workflow bogus → exit 2.
# ---------------------------------------------------------------------------
TMP15C="$SCRATCH/test15c"; mkdir -p "$TMP15C"
EXIT=0
ERR=$("$DISPATCHER" --tmpdir "$TMP15C" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude --workflow bogus 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"--workflow must be 'SIMPLE' or 'HARD'"* ]]; then
    pass
else
    fail 15c "--workflow bogus should exit 2 with message, got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 16: needs_qa repair path. When the implementer writes a manifest with
# status=needs_qa but no needs_qa.questions, and qa-pending.json uses a
# non-standard items[] shape, the dispatcher must normalize items[] to
# questions[] and emit STATUS=needs_qa (not STATUS=bailed REASON=manifest-
# schema-invalid). Regression coverage for issue #1883.
# ---------------------------------------------------------------------------
TMP16="$SCRATCH/test16"; mkdir -p "$TMP16"
printf 'fresh-step2-16\n' > "$TMP16/session-id"

SCRATCH_REPO16="$SCRATCH/scratch-repo-16"
mkdir -p "$SCRATCH_REPO16"
git -C "$SCRATCH_REPO16" init -q -b main
git -C "$SCRATCH_REPO16" config user.email "test@example.com"
git -C "$SCRATCH_REPO16" config user.name "Test"
echo "initial" > "$SCRATCH_REPO16/README.md"
git -C "$SCRATCH_REPO16" add README.md
git -C "$SCRATCH_REPO16" commit -q -m "init"

STUB16="$SCRATCH/stub-bin-16"; mkdir -p "$STUB16"
cat > "$STUB16/codex" <<'STUB16_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
: "${IMPLEMENT_TMPDIR:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub transcript\n' > "$output_path"
# Write manifest with status=needs_qa but non-standard shape (no needs_qa.questions).
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"schema_version":"1","status":"needs_qa"}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
# Write qa-pending.json with non-standard items[] format.
STEP2_QA_PENDING="$(dirname "$STEP2_MANIFEST_PATH")/qa-pending.json"
cat > "${STEP2_QA_PENDING}.tmp" <<'JSON'
{"status":"needs_qa","items":[{"area":"area1","risk":"risk1","suggested_check":"check1"}]}
JSON
mv "${STEP2_QA_PENDING}.tmp" "$STEP2_QA_PENDING"
printf 'stub codex stdout\n'
STUB16_CODEX
chmod +x "$STUB16/codex"

OUT_16=$(cd "$SCRATCH_REPO16" && \
    PATH="$STUB16:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP16/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP16" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)

if [[ "$OUT_16" == *"STATUS=needs_qa"* ]] \
   && [[ "$OUT_16" != *"STATUS=bailed"* ]] \
   && [[ "$OUT_16" == *"QA_PENDING="* ]] \
   && [[ "$OUT_16" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]]; then
    pass
else
    fail 16 "items[] qa-pending.json should be repaired to STATUS=needs_qa (not bailed); got: $OUT_16"
fi

# Verify the repaired qa-pending.json contains questions[] not items[].
QA_PENDING_16="$TMP16/codex-step2-out/qa-pending.json"
if [[ -s "$QA_PENDING_16" ]] \
   && jq -e '(.questions | type == "array" and length > 0)' "$QA_PENDING_16" >/dev/null 2>&1 \
   && ! jq -e '.items' "$QA_PENDING_16" >/dev/null 2>&1; then
    pass
else
    fail 16 "repaired qa-pending.json should have questions[] and no items[]; contents: $(cat "$QA_PENDING_16" 2>/dev/null)"
fi

# ---------------------------------------------------------------------------
# Tests 17a/17b: --workflow SIMPLE/HARD selects the correct --timeout for the
# launcher. The wiring LAUNCHER_TIMEOUT=3600 (SIMPLE) / 7200 (HARD) in
# step2-implement.sh is verified via the TIMEOUT= key written by
# run-external-agent.sh to the .meta sidecar before spawning the subprocess.
# ---------------------------------------------------------------------------
STUB17="$SCRATCH/stub-bin-17"; mkdir -p "$STUB17"
cat > "$STUB17/codex" <<'STUB17_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub transcript\n' > "$output_path"
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUB17_CODEX
chmod +x "$STUB17/codex"

# Test 17a: --workflow SIMPLE → launcher must receive --timeout 3600.
TMP17A="$SCRATCH/test17a"; mkdir -p "$TMP17A"
printf 'fresh-step2-17a\n' > "$TMP17A/session-id"
OUT_17A=$(cd "$REPO_ROOT" && \
    PATH="$STUB17:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP17A/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP17A" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex --workflow SIMPLE 2>&1)
META17A="$TMP17A/codex-step2-out/codex-impl-transcript.txt.meta"
TIMEOUT17A=$(awk -F= '/^TIMEOUT=/{print $2; exit}' "$META17A" 2>/dev/null || true)
if [[ "$TIMEOUT17A" == "3600" ]]; then
    pass
else
    fail 17a "--workflow SIMPLE should set launcher --timeout 3600, got TIMEOUT=$TIMEOUT17A (out=$OUT_17A meta=$(cat "$META17A" 2>/dev/null))"
fi

# Test 17b: --workflow HARD → launcher must receive --timeout 7200.
TMP17B="$SCRATCH/test17b"; mkdir -p "$TMP17B"
printf 'fresh-step2-17b\n' > "$TMP17B/session-id"
OUT_17B=$(cd "$REPO_ROOT" && \
    PATH="$STUB17:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP17B/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP17B" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex --workflow HARD 2>&1)
META17B="$TMP17B/codex-step2-out/codex-impl-transcript.txt.meta"
TIMEOUT17B=$(awk -F= '/^TIMEOUT=/{print $2; exit}' "$META17B" 2>/dev/null || true)
if [[ "$TIMEOUT17B" == "7200" ]]; then
    pass
else
    fail 17b "--workflow HARD should set launcher --timeout 7200, got TIMEOUT=$TIMEOUT17B (out=$OUT_17B meta=$(cat "$META17B" 2>/dev/null))"
fi

# Test 17c: --workflow omitted (default) → default workflow is SIMPLE → --timeout 3600.
TMP17C="$SCRATCH/test17c"; mkdir -p "$TMP17C"
printf 'fresh-step2-17c\n' > "$TMP17C/session-id"
OUT_17C=$(cd "$REPO_ROOT" && \
    PATH="$STUB17:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP17C/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP17C" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
META17C="$TMP17C/codex-step2-out/codex-impl-transcript.txt.meta"
TIMEOUT17C=$(awk -F= '/^TIMEOUT=/{print $2; exit}' "$META17C" 2>/dev/null || true)
if [[ "$TIMEOUT17C" == "3600" ]]; then
    pass
else
    fail 17c "default --workflow (SIMPLE) should set launcher --timeout 3600, got TIMEOUT=$TIMEOUT17C (out=$OUT_17C meta=$(cat "$META17C" 2>/dev/null))"
fi

# ---------------------------------------------------------------------------
# Test 18: complete manifest that omits a working-tree change logs an OOS
# warning to execution-issues.md before dispatcher-side git add/commit.
# ---------------------------------------------------------------------------
TMP18="$SCRATCH/test18"; mkdir -p "$TMP18"
printf 'fresh-step2-18\n' > "$TMP18/session-id"

SCRATCH_REPO18="$SCRATCH/scratch-repo-18"
mkdir -p "$SCRATCH_REPO18"
git -C "$SCRATCH_REPO18" init -q -b main
git -C "$SCRATCH_REPO18" config user.email "test@example.com"
git -C "$SCRATCH_REPO18" config user.name "Test"
echo "initial" > "$SCRATCH_REPO18/README.md"
git -C "$SCRATCH_REPO18" add README.md
git -C "$SCRATCH_REPO18" commit -q -m "init"

STUB18="$SCRATCH/stub-bin-18"; mkdir -p "$STUB18"
cat > "$STUB18/codex" <<'STUB18_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub transcript\n' > "$output_path"
echo "declared edit" >> "$PWD/README.md"
echo "undeclared edit" > "$PWD/undeclared.txt"
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "files_touched": [{"path": "README.md"}],
  "commit_message": "stub: edit README with undeclared side file",
  "summary_bullets": ["edited README"],
  "tests_added_or_modified": [],
  "todos_left": [],
  "oos_observations": []
}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUB18_CODEX
chmod +x "$STUB18/codex"

OUT_18=$(cd "$SCRATCH_REPO18" && \
    PATH="$STUB18:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP18/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP18" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)

if [[ "$OUT_18" == *"STATUS=complete"* ]] \
   && [[ -s "$TMP18/execution-issues.md" ]] \
   && grep -Fq "not declared in manifest files_touched/tests_added_or_modified" "$TMP18/execution-issues.md" \
   && grep -Fq -- "- undeclared.txt" "$TMP18/execution-issues.md" \
   && ! grep -Fq -- "- README.md" "$TMP18/execution-issues.md"; then
    pass
else
    fail 18 "undeclared working-tree path should log OOS warning (undeclared.txt present, README.md absent); out=$OUT_18 issues=$(cat "$TMP18/execution-issues.md" 2>/dev/null)"
fi

# ---------------------------------------------------------------------------
# Test 19 / 19a / 19b: cursor path on protected spawn branch → main-branch-prohibited
# before any external launcher runs (issue: commits on main when branch
# creation fails).
# ---------------------------------------------------------------------------
TMP19="$SCRATCH/test19"; mkdir -p "$TMP19"
printf 'fresh-step2-19\n' > "$TMP19/session-id"

SCRATCH_REPO19="$SCRATCH/scratch-repo-19"
mkdir -p "$SCRATCH_REPO19"
git -C "$SCRATCH_REPO19" init -q -b main
git -C "$SCRATCH_REPO19" config user.email "test@example.com"
git -C "$SCRATCH_REPO19" config user.name "Test"
echo "initial" > "$SCRATCH_REPO19/README.md"
git -C "$SCRATCH_REPO19" add README.md
git -C "$SCRATCH_REPO19" commit -q -m "init"
cat > "$TMP19/session-env.sh" <<'ENV'
ISSUE_NUMBER=2486
FORKED_TARGET=false
ENV

STUB_BIN_19="$SCRATCH/test19-bin"
mkdir -p "$STUB_BIN_19"
STUB_CURSOR_19="$STUB_BIN_19/cursor"
cat > "$STUB_CURSOR_19" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'stub cursor should not run\n' >&2
exit 99
EOF
chmod +x "$STUB_CURSOR_19"

assert_main_branch_prohibited_cursor() {
    local out=$1
    [[ "$out" == *"STATUS=bailed"* ]] \
        && [[ "$out" == *"REASON=main-branch-prohibited"* ]] \
        && [[ "$out" == *"TOOL=cursor"* ]] \
        && [[ "$out" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]]
}

OUT_19=$(cd "$SCRATCH_REPO19" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP19" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if assert_main_branch_prohibited_cursor "$OUT_19"; then
    pass
else
    fail 19 "expected main-branch-prohibited bail before PATH-stubbed cursor runs; stub must not execute; got: $OUT_19"
fi

TMP19A="$SCRATCH/test19a"; mkdir -p "$TMP19A"
printf 'fresh-step2-19a\n' > "$TMP19A/session-id"
SCRATCH_REPO19A="$SCRATCH/scratch-repo-19a"
mkdir -p "$SCRATCH_REPO19A"
git -C "$SCRATCH_REPO19A" init -q -b master
git -C "$SCRATCH_REPO19A" config user.email "test@example.com"
git -C "$SCRATCH_REPO19A" config user.name "Test"
echo "initial" > "$SCRATCH_REPO19A/README.md"
git -C "$SCRATCH_REPO19A" add README.md
git -C "$SCRATCH_REPO19A" commit -q -m "init"
cat > "$TMP19A/session-env.sh" <<'ENV'
ISSUE_NUMBER=2486
FORKED_TARGET=false
ENV

OUT_19A=$(cd "$SCRATCH_REPO19A" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP19A" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if assert_main_branch_prohibited_cursor "$OUT_19A"; then
    pass
else
    fail "19-master" "expected main-branch-prohibited on master spawn branch before stub cursor; got: $OUT_19A"
fi

TMP19B="$SCRATCH/test19b"; mkdir -p "$TMP19B"
printf 'fresh-step2-19b\n' > "$TMP19B/session-id"
SCRATCH_REPO19B="$SCRATCH/scratch-repo-19b"
mkdir -p "$SCRATCH_REPO19B"
git -C "$SCRATCH_REPO19B" init -q -b main
git -C "$SCRATCH_REPO19B" config user.email "test@example.com"
git -C "$SCRATCH_REPO19B" config user.name "Test"
echo "initial" > "$SCRATCH_REPO19B/README.md"
git -C "$SCRATCH_REPO19B" add README.md
git -C "$SCRATCH_REPO19B" commit -q -m "init"
cat > "$TMP19B/session-env.sh" <<'ENV'
FORKED_TARGET=false
ENV
printf 'ISSUE_NUMBER=2486\nRUN_ID=r-test\nADOPTED=true\n' > "$TMP19B/parent-issue.md"

OUT_19B=$(cd "$SCRATCH_REPO19B" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP19B" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if assert_main_branch_prohibited_cursor "$OUT_19B"; then
    pass
else
    fail "19-parent-issue" "expected main-branch-prohibited from parent-issue ISSUE_NUMBER without session ISSUE_NUMBER; got: $OUT_19B"
fi

# Test 19c: FORKED_TARGET=true on main — fork carve-out; must not bail
# main-branch-prohibited before the stubbed launcher runs.
TMP19C="$SCRATCH/test19c"; mkdir -p "$TMP19C"
printf 'fresh-step2-19c\n' > "$TMP19C/session-id"
SCRATCH_REPO19C="$SCRATCH/scratch-repo-19c"
mkdir -p "$SCRATCH_REPO19C"
git -C "$SCRATCH_REPO19C" init -q -b main
git -C "$SCRATCH_REPO19C" config user.email "test@example.com"
git -C "$SCRATCH_REPO19C" config user.name "Test"
echo "initial" > "$SCRATCH_REPO19C/README.md"
git -C "$SCRATCH_REPO19C" add README.md
git -C "$SCRATCH_REPO19C" commit -q -m "init"
cat > "$TMP19C/session-env.sh" <<'ENV'
ISSUE_NUMBER=2486
FORKED_TARGET=true
ENV

OUT_19C=$(cd "$SCRATCH_REPO19C" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP19C" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if [[ "$OUT_19C" == *"REASON=main-branch-prohibited"* ]]; then
    fail 19c "fork carve-out must not emit main-branch-prohibited when FORKED_TARGET=true; got: $OUT_19C"
elif [[ "$OUT_19C" != *"REASON=cursor-runtime-failure"* ]] || [[ "$OUT_19C" != *"TOOL=cursor"* ]]; then
    fail 19c "fork carve-out: expected launcher attempt (cursor-runtime-failure + TOOL=cursor); got: $OUT_19C"
else
    pass
fi

# Test 19d: main spawn without issue-anchor signals — must not main-branch-prohibited.
TMP19D="$SCRATCH/test19d"; mkdir -p "$TMP19D"
printf 'fresh-step2-19d\n' > "$TMP19D/session-id"
SCRATCH_REPO19D="$SCRATCH/scratch-repo-19d"
mkdir -p "$SCRATCH_REPO19D"
git -C "$SCRATCH_REPO19D" init -q -b main
git -C "$SCRATCH_REPO19D" config user.email "test@example.com"
git -C "$SCRATCH_REPO19D" config user.name "Test"
echo "initial" > "$SCRATCH_REPO19D/README.md"
git -C "$SCRATCH_REPO19D" add README.md
git -C "$SCRATCH_REPO19D" commit -q -m "init"

OUT_19D=$(cd "$SCRATCH_REPO19D" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP19D" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if [[ "$OUT_19D" == *"REASON=main-branch-prohibited"* ]]; then
    fail 19d "unanchored tmpdir must not emit main-branch-prohibited on main; got: $OUT_19D"
elif [[ "$OUT_19D" != *"REASON=cursor-runtime-failure"* ]] || [[ "$OUT_19D" != *"TOOL=cursor"* ]]; then
    fail 19d "unanchored main: expected launcher attempt (cursor-runtime-failure + TOOL=cursor); got: $OUT_19D"
else
    pass
fi

# Test 19e: detached HEAD + issue-anchored session-env → detached-head-prohibited.
TMP19E="$SCRATCH/test19e"; mkdir -p "$TMP19E"
printf 'fresh-step2-19e\n' > "$TMP19E/session-id"
SCRATCH_REPO19E="$SCRATCH/scratch-repo-19e"
mkdir -p "$SCRATCH_REPO19E"
git -C "$SCRATCH_REPO19E" init -q -b main
git -C "$SCRATCH_REPO19E" config user.email "test@example.com"
git -C "$SCRATCH_REPO19E" config user.name "Test"
echo "initial" > "$SCRATCH_REPO19E/README.md"
git -C "$SCRATCH_REPO19E" add README.md
git -C "$SCRATCH_REPO19E" commit -q -m "init"
git -C "$SCRATCH_REPO19E" checkout -q --detach
cat > "$TMP19E/session-env.sh" <<'ENV'
ISSUE_NUMBER=2486
FORKED_TARGET=false
ENV

OUT_19E=$(cd "$SCRATCH_REPO19E" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP19E" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if [[ "$OUT_19E" == *"STATUS=bailed"* ]] \
    && [[ "$OUT_19E" == *"REASON=detached-head-prohibited"* ]] \
    && [[ "$OUT_19E" == *"TOOL=cursor"* ]] \
    && [[ "$OUT_19E" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]]; then
    pass
else
    fail 19e "expected detached-head-prohibited before stub cursor on detached HEAD; got: $OUT_19E"
fi

# ---------------------------------------------------------------------------
# Test 20: main → create-branch.sh --branch, then dispatch — must not
# main-branch-prohibited (simulates new Step 0 branch creation before Step 2).
# ---------------------------------------------------------------------------
TMP20="$SCRATCH/test20"
mkdir -p "$TMP20"
printf 'fresh-step2-20\n' > "$TMP20/session-id"
SCRATCH_REPO20="$SCRATCH/scratch-repo-20"
BARE20="$SCRATCH/scratch-origin-20.git"
rm -rf "$SCRATCH_REPO20" "$BARE20"
mkdir -p "$SCRATCH_REPO20"
git init --bare -q "$BARE20"
git -C "$SCRATCH_REPO20" init -q -b main
git -C "$SCRATCH_REPO20" config user.email "test@example.com"
git -C "$SCRATCH_REPO20" config user.name "Test"
echo "initial" > "$SCRATCH_REPO20/README.md"
git -C "$SCRATCH_REPO20" add README.md
git -C "$SCRATCH_REPO20" commit -q -m "init"
git -C "$SCRATCH_REPO20" remote add origin "$BARE20"
git -C "$SCRATCH_REPO20" push -u -q origin main
cat > "$TMP20/session-env.sh" <<'ENV'
ISSUE_NUMBER=42
FORKED_TARGET=false
ENV
printf 'ISSUE_NUMBER=42\nRUN_ID=r-test\nADOPTED=true\n' > "$TMP20/parent-issue.md"

if ! (cd "$SCRATCH_REPO20" && "$REPO_ROOT/scripts/create-branch.sh" --branch "test/test-feature-42") >/dev/null 2>&1; then
    fail 20 "create-branch.sh --branch failed in scratch repo (origin/main setup required for harness)"
fi
if [[ "$(git -C "$SCRATCH_REPO20" symbolic-ref --short HEAD 2>/dev/null || true)" != "test/test-feature-42" ]]; then
    fail 20 "expected checkout onto test/test-feature-42 after create-branch; got: $(git -C "$SCRATCH_REPO20" symbolic-ref --short HEAD 2>/dev/null || echo '?')"
fi
printf '%s\n' "test/test-feature-42" > "$TMP20/step2-spawn-branch.txt"

OUT_20=$(cd "$SCRATCH_REPO20" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP20" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if [[ "$OUT_20" == *"REASON=main-branch-prohibited"* ]]; then
    fail 20 "post-create-branch dispatch must not emit main-branch-prohibited; got: $OUT_20"
elif [[ "$OUT_20" != *"REASON=cursor-runtime-failure"* ]] || [[ "$OUT_20" != *"TOOL=cursor"* ]]; then
    fail 20 "expected stub cursor attempt (cursor-runtime-failure + TOOL=cursor); got: $OUT_20"
else
    pass
fi

# ---------------------------------------------------------------------------
# Test 21: existing user-prefix branch without create-branch — must not
# main-branch-prohibited (simulates IS_USER_BRANCH skip path).
# ---------------------------------------------------------------------------
TMP21="$SCRATCH/test21"
mkdir -p "$TMP21"
printf 'fresh-step2-21\n' > "$TMP21/session-id"
SCRATCH_REPO21="$SCRATCH/scratch-repo-21"
rm -rf "$SCRATCH_REPO21"
mkdir -p "$SCRATCH_REPO21"
git -C "$SCRATCH_REPO21" init -q -b main
git -C "$SCRATCH_REPO21" config user.email "test@example.com"
git -C "$SCRATCH_REPO21" config user.name "Test"
echo "initial" > "$SCRATCH_REPO21/README.md"
git -C "$SCRATCH_REPO21" add README.md
git -C "$SCRATCH_REPO21" commit -q -m "init"
git -C "$SCRATCH_REPO21" checkout -q -b "test/existing-feature-42"
cat > "$TMP21/session-env.sh" <<'ENV'
ISSUE_NUMBER=42
FORKED_TARGET=false
ENV
printf 'ISSUE_NUMBER=42\nRUN_ID=r-test\nADOPTED=true\n' > "$TMP21/parent-issue.md"
printf '%s\n' "test/existing-feature-42" > "$TMP21/step2-spawn-branch.txt"

if [[ "$(git -C "$SCRATCH_REPO21" symbolic-ref --short HEAD 2>/dev/null || true)" != "test/existing-feature-42" ]]; then
    fail 21 "scratch repo must be on test/existing-feature-42"
fi

OUT_21=$(cd "$SCRATCH_REPO21" && \
    PATH="$STUB_BIN_19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP21" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)

if [[ "$OUT_21" == *"REASON=main-branch-prohibited"* ]]; then
    fail 21 "user-prefix branch dispatch must not emit main-branch-prohibited; got: $OUT_21"
elif [[ "$OUT_21" != *"REASON=cursor-runtime-failure"* ]] || [[ "$OUT_21" != *"TOOL=cursor"* ]]; then
    fail 21 "expected stub cursor attempt (cursor-runtime-failure + TOOL=cursor); got: $OUT_21"
else
    pass
fi

assert_recovery_envelope() {
    local out="$1" tool="$2"
    local auth_lines
    auth_lines=$(printf '%s\n' "$out" | grep -c '^ORCHESTRATOR_EDIT_AUTHORITY=' || true)
    [[ "$out" == *"STATUS=claude_fallback"* ]] \
        && [[ "$out" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]] \
        && [[ "$out" == *"RECOVERY_FROM=manifest-schema-invalid"* ]] \
        && [[ "$out" == *"RECOVERY_PRIOR_TOOL=$tool"* ]] \
        && [[ "$out" == *"RECOVERY_PATHS_FILE="* ]] \
        && [[ "$auth_lines" == "1" ]]
}

# ---------------------------------------------------------------------------
# Test M1: legacy complete-shaped manifest plus post-launch edits recovers to
# claude_fallback with recovery metadata and exactly one AUTH line.
# ---------------------------------------------------------------------------
TMPM1="$SCRATCH/testM1"; mkdir -p "$TMPM1"
SCRATCH_REPOM1="$SCRATCH/scratch-repo-M1"
mkdir -p "$SCRATCH_REPOM1"
git -C "$SCRATCH_REPOM1" init -q -b main
git -C "$SCRATCH_REPOM1" config user.email "test@example.com"
git -C "$SCRATCH_REPOM1" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM1/README.md"
git -C "$SCRATCH_REPOM1" add README.md
git -C "$SCRATCH_REPOM1" commit -q -m "init"

STUBM1="$SCRATCH/stub-bin-M1"; mkdir -p "$STUBM1"
cat > "$STUBM1/codex" <<'STUBM1_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub transcript\n' > "$output_path"
printf 'recovered edit\n' >> "$PWD/README.md"
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"status":"complete","summary":"done","checks":"ok"}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUBM1_CODEX
chmod +x "$STUBM1/codex"

OUT_M1=$(cd "$SCRATCH_REPOM1" && \
    PATH="$STUBM1:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM1/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM1" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
RECOVERY_FILE_M1=$(printf '%s\n' "$OUT_M1" | awk -F= '$1=="RECOVERY_PATHS_FILE"{print $2; exit}')
if assert_recovery_envelope "$OUT_M1" codex \
   && [[ -s "$RECOVERY_FILE_M1" ]] \
   && python3 - "$RECOVERY_FILE_M1" <<'PY'
import sys
paths = [p.decode() for p in open(sys.argv[1], "rb").read().split(b"\0") if p]
sys.exit(0 if paths == ["README.md"] else 1)
PY
then
    pass
else
    fail M1 "legacy malformed manifest with edit should recover; out=$OUT_M1 recovery_file=$RECOVERY_FILE_M1"
fi
if [[ -s "$TMPM1/manifest-raw.invalid.json" ]] && [[ -s "$TMPM1/recovery-metadata.json" ]]; then
    pass
else
    fail M1 "recovery should quarantine raw manifest and write recovery metadata"
fi

# ---------------------------------------------------------------------------
# Test M1b: same malformed-manifest recovery path on cursor preserves
# RECOVERY_PRIOR_TOOL=cursor.
# ---------------------------------------------------------------------------
TMPM1B="$SCRATCH/testM1b"; mkdir -p "$TMPM1B"
SCRATCH_REPOM1B="$SCRATCH/scratch-repo-M1b"
mkdir -p "$SCRATCH_REPOM1B"
git -C "$SCRATCH_REPOM1B" init -q -b main
git -C "$SCRATCH_REPOM1B" config user.email "test@example.com"
git -C "$SCRATCH_REPOM1B" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM1B/README.md"
git -C "$SCRATCH_REPOM1B" add README.md
git -C "$SCRATCH_REPOM1B" commit -q -m "init"

STUBM1B="$SCRATCH/stub-bin-M1b"; mkdir -p "$STUBM1B"
cat > "$STUBM1B/cursor" <<'STUBM1B_CURSOR'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
printf 'recovered edit\n' >> "$PWD/README.md"
cat > "$STUB_MANIFEST_PATH.tmp" <<'JSON'
{"status":"complete","summary":"done","checks":"ok"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'stub cursor stdout\n'
STUBM1B_CURSOR
chmod +x "$STUBM1B/cursor"

OUT_M1B=$(cd "$SCRATCH_REPOM1B" && \
    PATH="$STUBM1B:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STUB_MANIFEST_PATH="$TMPM1B/manifest.json" \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMPM1B" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)
RECOVERY_FILE_M1B=$(printf '%s\n' "$OUT_M1B" | awk -F= '$1=="RECOVERY_PATHS_FILE"{print $2; exit}')
if assert_recovery_envelope "$OUT_M1B" cursor \
   && [[ -s "$RECOVERY_FILE_M1B" ]] \
   && python3 - "$RECOVERY_FILE_M1B" <<'PY'
import sys
paths = [p.decode() for p in open(sys.argv[1], "rb").read().split(b"\0") if p]
sys.exit(0 if paths == ["README.md"] else 1)
PY
then
    pass
else
    fail M1b "cursor malformed manifest with edit should recover; out=$OUT_M1B recovery_file=$RECOVERY_FILE_M1B"
fi

# ---------------------------------------------------------------------------
# Test M2: same malformed manifest with no post-launch delta stays bailed.
# ---------------------------------------------------------------------------
TMPM2="$SCRATCH/testM2"; mkdir -p "$TMPM2"
SCRATCH_REPOM2="$SCRATCH/scratch-repo-M2"
mkdir -p "$SCRATCH_REPOM2"
git -C "$SCRATCH_REPOM2" init -q -b main
git -C "$SCRATCH_REPOM2" config user.email "test@example.com"
git -C "$SCRATCH_REPOM2" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM2/README.md"
git -C "$SCRATCH_REPOM2" add README.md
git -C "$SCRATCH_REPOM2" commit -q -m "init"

STUBM2="$SCRATCH/stub-bin-M2"; mkdir -p "$STUBM2"
cat > "$STUBM2/codex" <<'STUBM2_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"status":"complete","summary":"done","checks":"ok"}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUBM2_CODEX
chmod +x "$STUBM2/codex"

OUT_M2=$(cd "$SCRATCH_REPOM2" && \
    PATH="$STUBM2:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM2/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM2" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
if [[ "$OUT_M2" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_M2" == *"REASON=manifest-schema-invalid"* ]] \
   && [[ "$OUT_M2" != *"RECOVERY_FROM="* ]]; then
    pass
else
    fail M2 "empty post-launch delta should not recover; out=$OUT_M2"
fi

# ---------------------------------------------------------------------------
# Test M12: truncated/non-JSON manifest never recovers even with edits.
# ---------------------------------------------------------------------------
TMPM12="$SCRATCH/testM12"; mkdir -p "$TMPM12"
SCRATCH_REPOM12="$SCRATCH/scratch-repo-M12"
mkdir -p "$SCRATCH_REPOM12"
git -C "$SCRATCH_REPOM12" init -q -b main
git -C "$SCRATCH_REPOM12" config user.email "test@example.com"
git -C "$SCRATCH_REPOM12" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM12/README.md"
git -C "$SCRATCH_REPOM12" add README.md
git -C "$SCRATCH_REPOM12" commit -q -m "init"

STUBM12="$SCRATCH/stub-bin-M12"; mkdir -p "$STUBM12"
cat > "$STUBM12/codex" <<'STUBM12_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
printf 'edit\n' >> "$PWD/README.md"
printf '{"status":"complete"' > "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUBM12_CODEX
chmod +x "$STUBM12/codex"

OUT_M12=$(cd "$SCRATCH_REPOM12" && \
    PATH="$STUBM12:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM12/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM12" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
if [[ "$OUT_M12" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_M12" == *"REASON=manifest-schema-invalid"* ]] \
   && [[ "$OUT_M12" != *"RECOVERY_FROM="* ]]; then
    pass
else
    fail M12 "truncated manifest should not recover; out=$OUT_M12"
fi

# ---------------------------------------------------------------------------
# Test M16: prelaunch staged content blocks recovery.
# ---------------------------------------------------------------------------
TMPM16="$SCRATCH/testM16"; mkdir -p "$TMPM16"
SCRATCH_REPOM16="$SCRATCH/scratch-repo-M16"
mkdir -p "$SCRATCH_REPOM16"
git -C "$SCRATCH_REPOM16" init -q -b main
git -C "$SCRATCH_REPOM16" config user.email "test@example.com"
git -C "$SCRATCH_REPOM16" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM16/README.md"
printf 'initial\n' > "$SCRATCH_REPOM16/staged.txt"
git -C "$SCRATCH_REPOM16" add README.md staged.txt
git -C "$SCRATCH_REPOM16" commit -q -m "init"
printf 'prelaunch staged\n' > "$SCRATCH_REPOM16/staged.txt"
git -C "$SCRATCH_REPOM16" add staged.txt

OUT_M16=$(cd "$SCRATCH_REPOM16" && \
    PATH="$STUBM1:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM16/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM16" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
if [[ "$OUT_M16" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_M16" == *"REASON=manifest-schema-invalid"* ]] \
   && [[ "$OUT_M16" != *"RECOVERY_FROM="* ]] \
   && grep -Fq "PRELAUNCH_INDEX_NONEMPTY=true" "$TMPM16/step2-prelaunch-index.env"; then
    pass
else
    fail M16 "prelaunch staged content should block recovery; out=$OUT_M16 flag=$(cat "$TMPM16/step2-prelaunch-index.env" 2>/dev/null)"
fi

# ---------------------------------------------------------------------------
# Test M17: rename/copy porcelain rows recover the destination path, not the
# deleted source path.
# ---------------------------------------------------------------------------
TMPM17="$SCRATCH/testM17"; mkdir -p "$TMPM17"
SCRATCH_REPOM17="$SCRATCH/scratch-repo-M17"
mkdir -p "$SCRATCH_REPOM17"
git -C "$SCRATCH_REPOM17" init -q -b main
git -C "$SCRATCH_REPOM17" config user.email "test@example.com"
git -C "$SCRATCH_REPOM17" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM17/README.md"
git -C "$SCRATCH_REPOM17" add README.md
git -C "$SCRATCH_REPOM17" commit -q -m "init"

STUBM17="$SCRATCH/stub-bin-M17"; mkdir -p "$STUBM17"
cat > "$STUBM17/codex" <<'STUBM17_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
git mv README.md RENAMED.md
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"status":"complete","summary":"done","checks":"ok"}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUBM17_CODEX
chmod +x "$STUBM17/codex"

OUT_M17=$(cd "$SCRATCH_REPOM17" && \
    PATH="$STUBM17:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM17/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM17" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
RECOVERY_FILE_M17=$(printf '%s\n' "$OUT_M17" | awk -F= '$1=="RECOVERY_PATHS_FILE"{print $2; exit}')
if assert_recovery_envelope "$OUT_M17" codex \
   && [[ -s "$RECOVERY_FILE_M17" ]] \
   && python3 - "$RECOVERY_FILE_M17" <<'PY'
import sys
paths = [p.decode() for p in open(sys.argv[1], "rb").read().split(b"\0") if p]
sys.exit(0 if paths == ["RENAMED.md"] else 1)
PY
then
    pass
else
    fail M17 "rename recovery should preserve destination path; out=$OUT_M17 recovery_file=$RECOVERY_FILE_M17"
fi

# ---------------------------------------------------------------------------
# Test M18: prelaunch recovery baseline persists across --answers resumes so a
# later malformed-manifest recovery still includes earlier uncommitted edits.
# ---------------------------------------------------------------------------
TMPM18="$SCRATCH/testM18"; mkdir -p "$TMPM18"
SCRATCH_REPOM18="$SCRATCH/scratch-repo-M18"
mkdir -p "$SCRATCH_REPOM18"
git -C "$SCRATCH_REPOM18" init -q -b main
git -C "$SCRATCH_REPOM18" config user.email "test@example.com"
git -C "$SCRATCH_REPOM18" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM18/README.md"
git -C "$SCRATCH_REPOM18" add README.md
git -C "$SCRATCH_REPOM18" commit -q -m "init"

STUBM18="$SCRATCH/stub-bin-M18"; mkdir -p "$STUBM18"
cat > "$STUBM18/codex" <<'STUBM18_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
: "${STEP2_STATE_FILE:?}"
prompt="${!#}"
qa_path=$(printf '%s\n' "$prompt" | awk '/Write qa-pending.json \(atomically, only if status=needs_qa\) at: /{sub(/^.* at: /,""); print; exit}')
if [[ ! -f "$STEP2_STATE_FILE" ]]; then
    printf 'round1\n' > "$PWD/A.txt"
    cat > "$qa_path.tmp" <<'JSON'
{"questions":[{"id":"q1","text":"continue?"}]}
JSON
    mv "$qa_path.tmp" "$qa_path"
    cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"schema_version":1,"status":"needs_qa","needs_qa":{"questions":[{"id":"q1","text":"continue?"}]}}
JSON
    mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
    touch "$STEP2_STATE_FILE"
else
    printf 'round2\n' > "$PWD/B.txt"
    cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"status":"complete","summary":"done","checks":"ok"}
JSON
    mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
fi
printf 'stub codex stdout\n'
STUBM18_CODEX
chmod +x "$STUBM18/codex"

OUT_M18_QA=$(cd "$SCRATCH_REPOM18" && \
    PATH="$STUBM18:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM18/codex-step2-out/manifest.json" \
    STEP2_STATE_FILE="$TMPM18/state" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM18" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
printf '{"answers":[{"id":"q1","text":"yes"}]}\n' > "$TMPM18/answers.json"
OUT_M18_RECOVERY=$(cd "$SCRATCH_REPOM18" && \
    PATH="$STUBM18:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM18/codex-step2-out/manifest.json" \
    STEP2_STATE_FILE="$TMPM18/state" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM18" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex --answers "$TMPM18/answers.json" 2>&1)
RECOVERY_FILE_M18=$(printf '%s\n' "$OUT_M18_RECOVERY" | awk -F= '$1=="RECOVERY_PATHS_FILE"{print $2; exit}')
if [[ "$OUT_M18_QA" == *"STATUS=needs_qa"* ]] \
   && assert_recovery_envelope "$OUT_M18_RECOVERY" codex \
   && [[ -s "$RECOVERY_FILE_M18" ]] \
   && python3 - "$RECOVERY_FILE_M18" <<'PY'
import sys
paths = [p.decode() for p in open(sys.argv[1], "rb").read().split(b"\0") if p]
sys.exit(0 if paths == ["A.txt", "B.txt"] else 1)
PY
then
    pass
else
    fail M18 "answers resume should preserve round-1 recovery baseline; qa=$OUT_M18_QA recovery=$OUT_M18_RECOVERY recovery_file=$RECOVERY_FILE_M18"
fi

# ---------------------------------------------------------------------------
# Test M19: non-v1 schema_version must hard-bail instead of entering malformed
# manifest recovery, even when post-launch edits exist.
# ---------------------------------------------------------------------------
TMPM19="$SCRATCH/testM19"; mkdir -p "$TMPM19"
SCRATCH_REPOM19="$SCRATCH/scratch-repo-M19"
mkdir -p "$SCRATCH_REPOM19"
git -C "$SCRATCH_REPOM19" init -q -b main
git -C "$SCRATCH_REPOM19" config user.email "test@example.com"
git -C "$SCRATCH_REPOM19" config user.name "Test"
printf 'initial\n' > "$SCRATCH_REPOM19/README.md"
git -C "$SCRATCH_REPOM19" add README.md
git -C "$SCRATCH_REPOM19" commit -q -m "init"

STUBM19="$SCRATCH/stub-bin-M19"; mkdir -p "$STUBM19"
cat > "$STUBM19/codex" <<'STUBM19_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
printf 'edit\n' >> "$PWD/README.md"
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{"schema_version":2,"status":"complete","summary":"done","checks":"ok"}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'stub codex stdout\n'
STUBM19_CODEX
chmod +x "$STUBM19/codex"

OUT_M19=$(cd "$SCRATCH_REPOM19" && \
    PATH="$STUBM19:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMPM19/codex-step2-out/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMPM19" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
if [[ "$OUT_M19" == *"STATUS=bailed"* ]] \
   && [[ "$OUT_M19" == *"REASON=manifest-schema-invalid"* ]] \
   && [[ "$OUT_M19" != *"RECOVERY_FROM="* ]]; then
    pass
else
    fail M19 "schema_version 2 should not recover; out=$OUT_M19"
fi

# ---------------------------------------------------------------------------
# Test 22: emit_bailed surfaces stub agent stderr on dispatcher stderr (cursor).
# ---------------------------------------------------------------------------
TMP22="$SCRATCH/test22"; mkdir -p "$TMP22"
printf 'fresh-step2-22\n' > "$TMP22/session-id"
SCRATCH_REPO22="$SCRATCH/scratch-repo-22"
mkdir -p "$SCRATCH_REPO22"
git -C "$SCRATCH_REPO22" init -q -b feature/step2-stderr-tail
git -C "$SCRATCH_REPO22" config user.email "test@example.com"
git -C "$SCRATCH_REPO22" config user.name "Test"
echo "initial" > "$SCRATCH_REPO22/README.md"
git -C "$SCRATCH_REPO22" add README.md
git -C "$SCRATCH_REPO22" commit -q -m "init"
cat > "$TMP22/session-env.sh" <<'ENV'
ISSUE_NUMBER=3227
FORKED_TARGET=false
ENV
STUB_BIN_22="$SCRATCH/stub-bin-22"; mkdir -p "$STUB_BIN_22"
cat > "$STUB_BIN_22/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'LARCH_STEP2_EMIT_BAILED_STDERR_PROBE\n' >&2
exit 1
EOF
chmod +x "$STUB_BIN_22/cursor"
STDERR_22="$TMP22/dispatcher.stderr"
set +e
(
    cd "$SCRATCH_REPO22" && \
    PATH="$STUB_BIN_22:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP22" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>"$STDERR_22"
) >"$TMP22/stdout.txt"
_rc22=$?
set -e
OUT_22=$(cat "$TMP22/stdout.txt")
if [[ "$_rc22" -ne 0 ]]; then
    fail 22 "dispatcher exited non-zero rc=$_rc22 out=$OUT_22 err=$(cat "$STDERR_22" 2>/dev/null || true)"
elif [[ "$OUT_22" != *"STATUS=bailed"* ]] || [[ "$OUT_22" != *"REASON=cursor-runtime-failure"* ]]; then
    fail 22 "expected cursor-runtime-failure bail; got: $OUT_22"
elif grep -Fq 'LARCH_STEP2_EMIT_BAILED_STDERR_PROBE' "$STDERR_22"; then
    pass
else
    fail 22 "emit_bailed must surface transcript stderr-tail on dispatcher stderr"
fi

# ---------------------------------------------------------------------------
# Test 23: manifest status=bailed surfaces stderr-tail on dispatcher stderr (cursor).
# ---------------------------------------------------------------------------
TMP23="$SCRATCH/test23"; mkdir -p "$TMP23"
printf 'fresh-step2-23\n' > "$TMP23/session-id"
STUB_BIN_23="$SCRATCH/stub-bin-23"; mkdir -p "$STUB_BIN_23"
cat > "$STUB_BIN_23/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
cat > "$STUB_MANIFEST_PATH.tmp" <<'JSON'
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-manifest-bailed"
}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'LARCH_STEP2_MANIFEST_BAILED_STDERR_PROBE\n' >&2
printf 'stub cursor stdout\n'
EOF
chmod +x "$STUB_BIN_23/cursor"
STDERR_23="$TMP23/dispatcher.stderr"
set +e
(
    cd "$REPO_ROOT" && \
    PATH="$STUB_BIN_23:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STUB_MANIFEST_PATH="$TMP23/manifest.json" \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$DISPATCHER" --tmpdir "$TMP23" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>"$STDERR_23"
) >"$TMP23/stdout.txt"
_rc23=$?
set -e
OUT_23=$(cat "$TMP23/stdout.txt")
if [[ "$_rc23" -ne 0 ]]; then
    fail 23 "dispatcher exited non-zero rc=$_rc23 out=$OUT_23"
elif [[ "$OUT_23" != *"STATUS=bailed"* ]] || [[ "$OUT_23" != *"REASON=stub-manifest-bailed"* ]]; then
    fail 23 "expected manifest-driven bail; got: $OUT_23"
elif grep -Fq 'LARCH_STEP2_MANIFEST_BAILED_STDERR_PROBE' "$STDERR_23"; then
    pass
else
    fail 23 "manifest status=bailed must surface stderr-tail on dispatcher stderr"
fi

# ---------------------------------------------------------------------------
# Test 24: emit_bailed surfaces stub agent stderr on dispatcher stderr (codex).
# ---------------------------------------------------------------------------
TMP24="$SCRATCH/test24"; mkdir -p "$TMP24"
printf 'fresh-step2-24\n' > "$TMP24/session-id"
SCRATCH_REPO24="$SCRATCH/scratch-repo-24"
mkdir -p "$SCRATCH_REPO24"
git -C "$SCRATCH_REPO24" init -q -b feature/step2-codex-stderr-tail
git -C "$SCRATCH_REPO24" config user.email "test@example.com"
git -C "$SCRATCH_REPO24" config user.name "Test"
echo "initial" > "$SCRATCH_REPO24/README.md"
git -C "$SCRATCH_REPO24" add README.md
git -C "$SCRATCH_REPO24" commit -q -m "init"
STUB_BIN_24="$SCRATCH/stub-bin-24"; mkdir -p "$STUB_BIN_24"
cat > "$STUB_BIN_24/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'LARCH_STEP2_CODEX_EMIT_BAILED_STDERR_PROBE\n' >&2
exit 1
EOF
chmod +x "$STUB_BIN_24/codex"
STDERR_24="$TMP24/dispatcher.stderr"
set +e
(
    cd "$SCRATCH_REPO24" && \
    PATH="$STUB_BIN_24:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CODEX_MODEL="stub-codex-model" \
    "$DISPATCHER" --tmpdir "$TMP24" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>"$STDERR_24"
) >"$TMP24/stdout.txt"
_rc24=$?
set -e
OUT_24=$(cat "$TMP24/stdout.txt")
if [[ "$_rc24" -ne 0 ]]; then
    fail 24 "dispatcher exited non-zero rc=$_rc24 out=$OUT_24"
elif [[ "$OUT_24" != *"STATUS=bailed"* ]] || [[ "$OUT_24" != *"REASON=codex-runtime-failure"* ]]; then
    fail 24 "expected codex-runtime-failure bail; got: $OUT_24"
elif grep -Fq 'LARCH_STEP2_CODEX_EMIT_BAILED_STDERR_PROBE' "$STDERR_24"; then
    pass
else
    fail 24 "emit_bailed must surface codex transcript stderr-tail on dispatcher stderr"
fi

# ---------------------------------------------------------------------------
# Test 25: manifest status=bailed surfaces stderr-tail on dispatcher stderr (codex).
# ---------------------------------------------------------------------------
TMP25="$SCRATCH/test25"; mkdir -p "$TMP25"
printf 'fresh-step2-25\n' > "$TMP25/session-id"
STUB_BIN_25="$SCRATCH/stub-bin-25"; mkdir -p "$STUB_BIN_25"
cat > "$STUB_BIN_25/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STEP2_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] && printf 'stub codex stdout\n' > "$output_path"
cat > "$STEP2_MANIFEST_PATH.tmp" <<'JSON'
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-codex-manifest-bailed"
}
JSON
mv "$STEP2_MANIFEST_PATH.tmp" "$STEP2_MANIFEST_PATH"
printf 'LARCH_STEP2_CODEX_MANIFEST_BAILED_STDERR_PROBE\n' >&2
EOF
chmod +x "$STUB_BIN_25/codex"
STDERR_25="$TMP25/dispatcher.stderr"
set +e
(
    cd "$REPO_ROOT" && \
    PATH="$STUB_BIN_25:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP25/codex-step2-out/manifest.json" \
    LARCH_QUIET_DISABLE=1 \
    LARCH_CODEX_MODEL="stub-codex-model" \
    "$DISPATCHER" --tmpdir "$TMP25" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>"$STDERR_25"
) >"$TMP25/stdout.txt"
_rc25=$?
set -e
OUT_25=$(cat "$TMP25/stdout.txt")
if [[ "$_rc25" -ne 0 ]]; then
    fail 25 "dispatcher exited non-zero rc=$_rc25 out=$OUT_25"
elif [[ "$OUT_25" != *"STATUS=bailed"* ]] || [[ "$OUT_25" != *"REASON=stub-codex-manifest-bailed"* ]]; then
    fail 25 "expected codex manifest-driven bail; got: $OUT_25"
elif grep -Fq 'LARCH_STEP2_CODEX_MANIFEST_BAILED_STDERR_PROBE' "$STDERR_25"; then
    pass
else
    fail 25 "codex manifest status=bailed must surface stderr-tail on dispatcher stderr"
fi

# ---------------------------------------------------------------------------
# Summary.
# ---------------------------------------------------------------------------
TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-step2-dispatch.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-step2-dispatch.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
