#!/usr/bin/env bash
# test-step2-dispatch.sh — Offline harness for skills/implement/scripts/step2-implement.sh.
#
# Covers the dispatcher branches that do NOT require spawning an external implementer
# (26 assertions; for the full per-test inventory see test-step2-dispatch.md):
#   - --coder claude → STATUS=claude_fallback (no launcher run; no baseline-file leak).
#   - default coder (no --coder flag) is codex.
#   - Default coder (neither flag) → STATUS=claude_fallback.
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
    printf '\n' > "$TMP5/step2-plugin-json-baseline.txt"
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
    printf '\n' > "$TMP7/step2-plugin-json-baseline.txt"
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
    printf '\n' > "$TMP9/step2-plugin-json-baseline.txt"
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
    printf '\n' > "$TMP10/step2-plugin-json-baseline.txt"
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
    printf '\n' > "$TMP11B/step2-plugin-json-baseline.txt"
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
