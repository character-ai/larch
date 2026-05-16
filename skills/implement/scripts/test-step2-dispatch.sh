#!/usr/bin/env bash
# test-step2-dispatch.sh — Offline harness for skills/implement/scripts/step2-implement.sh.
#
# Covers the dispatcher branches that do NOT require spawning an external implementer
# (for the full per-test inventory see test-step2-dispatch.md):
#   - --coder claude → STATUS=claude_fallback (no launcher run; no baseline-file leak).
#   - default coder (no --coder flag) is codex.
#   - Default codex path outside a git work-tree → exit 2.
#   - Legacy --codex-available false → STATUS=claude_fallback + deprecation warning on stderr.
#   - Missing required flag (--auto-mode) → exit 2.
#   - Bad --coder enum value → exit 2 and names {claude,codex,cursor}.
#   - --coder cursor with false/missing/empty health → STATUS=claude_fallback (no baseline-file leak).
#   - Bad --cursor-healthy enum value → exit 2.
#   - --coder claude --cursor-healthy "" → STATUS=claude_fallback.
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
#   - Stub-Codex complete run with an undeclared working-tree file appends an
#     OOS warning to execution-issues.md before the dispatcher commits.
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
    --auto-mode false --coder claude 2>&1)
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
# Test 1b: default coder (neither flag set) is codex. From a non-git cwd the
# codex path fails the git-tree precondition and exits 2 — if the default
# were still claude, the dispatcher would early-return STATUS=claude_fallback
# from the git-free claude branch with exit 0.
# ---------------------------------------------------------------------------
TMP1B="$SCRATCH/test1b"; mkdir -p "$TMP1B"
NON_GIT_1B="$SCRATCH/not-a-repo-default"; mkdir -p "$NON_GIT_1B"
EXIT=0
ERR=$(cd "$NON_GIT_1B" && "$DISPATCHER" --tmpdir "$TMP1B" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"must be invoked from within a git working tree"* ]]; then
    pass
else
    fail 1b "default coder should be codex (non-git cwd → git-tree exit 2), got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 1c: --codex-available false → claude_fallback + deprecation warning.
# ---------------------------------------------------------------------------
TMP1C="$SCRATCH/test1c"; mkdir -p "$TMP1C"
ERR=$("$DISPATCHER" --tmpdir "$TMP1C" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --codex-available false 2>&1 >/dev/null)
OUT=$("$DISPATCHER" --tmpdir "$TMP1C" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --codex-available false 2>/dev/null)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] \
   && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]] \
   && [[ "$ERR" == *"deprecated"* ]]; then
    pass
else
    fail 1c "--codex-available false should claude_fallback + deprecate, out=$OUT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 2: missing required flag (--auto-mode) → exit 2.
# ---------------------------------------------------------------------------
EXIT=0
"$DISPATCHER" --tmpdir "$SCRATCH/test2" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --coder claude >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 2 "missing --auto-mode should exit 2, got $EXIT"; fi

# ---------------------------------------------------------------------------
# Test 3: bad --coder enum value → exit 2.
# ---------------------------------------------------------------------------
TMP3="$SCRATCH/test3"; mkdir -p "$TMP3"
EXIT=0
ERR=$("$DISPATCHER" --tmpdir "$TMP3" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder bogus 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"{claude,codex,cursor}"* ]]; then
    pass
else
    fail 3 "bad --coder value should exit 2 and name {claude,codex,cursor}, got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 3b: --coder cursor --cursor-healthy false → claude_fallback.
# ---------------------------------------------------------------------------
TMP3B="$SCRATCH/test3b"; mkdir -p "$TMP3B"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder cursor --cursor-healthy false 2>&1)
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
# Test 3b2: --coder cursor with no --cursor-healthy defaults to false.
# ---------------------------------------------------------------------------
TMP3B2="$SCRATCH/test3b2"; mkdir -p "$TMP3B2"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B2" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder cursor 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b2 "--coder cursor without health should fall back to claude, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 3b3: --coder cursor --cursor-healthy "" treats empty as false.
# ---------------------------------------------------------------------------
TMP3B3="$SCRATCH/test3b3"; mkdir -p "$TMP3B3"
OUT=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B3" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder cursor --cursor-healthy "" 2>&1)
if [[ "$OUT" == *"STATUS=claude_fallback"* ]] && [[ "$OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=allowed"* ]]; then
    pass
else
    fail 3b3 "--coder cursor with empty health should fall back to claude, got: $OUT"
fi

# ---------------------------------------------------------------------------
# Test 3b4: bogus --cursor-healthy value exits 2.
# ---------------------------------------------------------------------------
TMP3B4="$SCRATCH/test3b4"; mkdir -p "$TMP3B4"
EXIT=0
ERR=$(cd "$REPO_ROOT" && "$DISPATCHER" --tmpdir "$TMP3B4" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder cursor --cursor-healthy bogus 2>&1 >/dev/null) || EXIT=$?
if [[ "$EXIT" == "2" ]] && [[ "$ERR" == *"--cursor-healthy must be 'true', 'false', or empty"* ]]; then
    pass
else
    fail 3b4 "bad --cursor-healthy should exit 2, got exit=$EXIT err=$ERR"
fi

# ---------------------------------------------------------------------------
# Test 3b5: --coder claude --cursor-healthy "" remains claude_fallback.
# ---------------------------------------------------------------------------
TMP3B5="$SCRATCH/test3b5"; mkdir -p "$TMP3B5"
OUT=$("$DISPATCHER" --tmpdir "$TMP3B5" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder claude --cursor-healthy "" 2>&1)
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
    --auto-mode false --coder cursor --cursor-healthy false 2>&1)
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
    --auto-mode false --coder claude --codex-available false 2>&1 >/dev/null) || EXIT=$?
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
    --auto-mode false --codex-available maybe >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 3d "bad --codex-available value should exit 2, got $EXIT"; fi

# ---------------------------------------------------------------------------
# Test 4: bad --tmpdir (not a directory) → exit 2.
# ---------------------------------------------------------------------------
EXIT=0
"$DISPATCHER" --tmpdir "$SCRATCH/nonexistent" --plan-file "$PLAN" --feature-file "$FEATURE" \
    --auto-mode false --coder codex >/dev/null 2>&1 || EXIT=$?
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
    --auto-mode false --coder codex --answers "$ANSWERS" 2>&1)
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
    --auto-mode false --coder codex --answers "$SCRATCH/missing-answers.json" \
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
    --auto-mode false --coder codex --answers "$ANSWERS" 2>&1)
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
    --auto-mode false --coder codex 2>&1 >/dev/null) || EXIT=$?
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
    --auto-mode false --coder codex --answers "$ANSWERS" 2>&1)
if [[ -f "$TMP9/step2-spawn-coder.txt" ]] && [[ "$(cat "$TMP9/step2-spawn-coder.txt")" == "codex" ]]; then
    pass
else
    fail 9 "first codex invocation should write step2-spawn-coder.txt=codex, got: $(cat "$TMP9/step2-spawn-coder.txt" 2>/dev/null || echo MISSING)"
fi

# ---------------------------------------------------------------------------
# Test 10: second invocation against a tmpdir that recorded a different coder
# bails with coder-mismatch-tmpdir-reuse before touching shared baselines or
# resume counters. Pre-seed sentinel=codex + baselines, then invoke with
# --coder=cursor --cursor-healthy true so the cursor health gate passes and
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
    --auto-mode false --coder cursor --cursor-healthy true 2>&1)
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
    --auto-mode false --coder claude 2>&1)
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
    --auto-mode false --coder codex --answers "$ANSWERS" 2>&1)
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
    STEP2_MANIFEST_PATH="$TMP12A/manifest.json" \
    LARCH_TOKEN_SESSION_ID=stale-step2 \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP12A" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)
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
    STEP2_MANIFEST_PATH="$TMP12B/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP12B" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)
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
    STEP2_MANIFEST_PATH="$TMP13/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP13" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)

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
CH14_LEDGER="$TMP14/cap-hit-step2-ledger.jsonl"
printf '{"type":"vendor","vendor":"codex","total":9999}\n' > "$CH14_LEDGER"

OUT_14=$(cd "$REPO_ROOT" && \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_TOKEN_SESSION_ID="$CH14_SESSION" \
    LARCH_TOKEN_LEDGER="$CH14_LEDGER" \
    LARCH_TOKEN_BUDGET_CAP_IMPLEMENT=1 \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP14" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)
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
    --auto-mode false --coder claude --workflow SIMPLE 2>&1)
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
    --auto-mode false --coder claude --workflow HARD 2>&1)
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
    --auto-mode false --coder claude --workflow bogus 2>&1 >/dev/null) || EXIT=$?
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
cat > "$IMPLEMENT_TMPDIR/qa-pending.json.tmp" <<'JSON'
{"status":"needs_qa","items":[{"area":"area1","risk":"risk1","suggested_check":"check1"}]}
JSON
mv "$IMPLEMENT_TMPDIR/qa-pending.json.tmp" "$IMPLEMENT_TMPDIR/qa-pending.json"
printf 'stub codex stdout\n'
STUB16_CODEX
chmod +x "$STUB16/codex"

OUT_16=$(cd "$SCRATCH_REPO16" && \
    PATH="$STUB16:$PATH" \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    STEP2_MANIFEST_PATH="$TMP16/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP16" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)

if [[ "$OUT_16" == *"STATUS=needs_qa"* ]] \
   && [[ "$OUT_16" != *"STATUS=bailed"* ]] \
   && [[ "$OUT_16" == *"QA_PENDING="* ]] \
   && [[ "$OUT_16" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]]; then
    pass
else
    fail 16 "items[] qa-pending.json should be repaired to STATUS=needs_qa (not bailed); got: $OUT_16"
fi

# Verify the repaired qa-pending.json contains questions[] not items[].
QA_PENDING_16="$TMP16/qa-pending.json"
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
    STEP2_MANIFEST_PATH="$TMP17A/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP17A" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex --workflow SIMPLE 2>&1)
META17A="$TMP17A/codex-impl-transcript.txt.meta"
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
    STEP2_MANIFEST_PATH="$TMP17B/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP17B" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex --workflow HARD 2>&1)
META17B="$TMP17B/codex-impl-transcript.txt.meta"
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
    STEP2_MANIFEST_PATH="$TMP17C/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP17C" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)
META17C="$TMP17C/codex-impl-transcript.txt.meta"
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
    STEP2_MANIFEST_PATH="$TMP18/manifest.json" \
    LARCH_CODEX_MODEL=stub-codex-model \
    "$DISPATCHER" --tmpdir "$TMP18" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --auto-mode false --coder codex 2>&1)

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
