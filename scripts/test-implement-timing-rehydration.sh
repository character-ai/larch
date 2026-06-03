#!/usr/bin/env bash
# Regression test for /implement timing-ledger rehydration.
#
# Asserts four invariants on skills/implement/SKILL.md:
#
#   A) The legacy two-key rehydration export has been retired everywhere
#      (no `export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE` lines remain).
#   B) Every fenced ```bash block (including indented ones) AFTER Step 0 that invokes
#      `timing-ledger.sh` or `timing-report.sh` is preceded — inside the SAME
#      bash fence — by an `LARCH_TIMING_LEDGER=$(... read-session-env-key.sh ...)`
#      rehydration line. This catches the workflow-path one-liner regression
#      where a standalone timing-ledger call lacks per-run ledger isolation.
#
# Step 0's preflight block is exempt from (B) because it canonically writes
# `export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"` rather than
# rehydrating via read-session-env-key.sh.
#   C) Every fenced ```bash block that uses `${CLAUDE_PLUGIN_ROOT}` contains
#      the plugin-root.env source guard (canonical) or, on pre-bootstrap sites
#      only, the session-env.sh awk fallback, so nested Bash calls can recover
#      the plugin root without depending on the root variable to find helpers.
#   D) Cardinality guards stay in sync: every timing-ledger rehydration template
#      has the token-session-id sibling/export, and IMPLEMENT_TMPDIR assignment
#      plus export counts equal token_read_count + step_telemetry_mark_count.
#   E) The Step 18 closing-marks block (token/timing `--since-last-mark` reports
#      and the closing `Step 18 — done` marks) appears BEFORE the
#      `implement-finalize.sh teardown` invocation. The per-run token/timing
#      ledgers live INSIDE $IMPLEMENT_TMPDIR and teardown deletes them, so a
#      post-teardown mark fails with "no per-run ledger root set" (issue #3425).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"

# Invariant A: no stale two-key export lines.
stale_count=$(grep -Fxc 'export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE' "$SKILL_MD" || true)
[[ "$stale_count" == "0" ]] \
  || fail "stale two-key rehydration export remains ($stale_count matches)"

# Invariant B: in every fenced bash block (after Step 0, including indented
# fences inside list items) that calls timing-ledger.sh or timing-report.sh,
# the same fence MUST contain an
# `LARCH_TIMING_LEDGER=$(... read-session-env-key.sh ...)` line.
awk '
  BEGIN { in_fence=0; has_timing=0; has_rehydration=0; fence_start=0; offending=0 }
  /^[[:space:]]*```bash[[:space:]]*$/ {
    in_fence=1; has_timing=0; has_rehydration=0; fence_start=NR; next
  }
  /^[[:space:]]*```[[:space:]]*$/ && in_fence {
    if (has_timing && !has_rehydration && !is_step0) {
      printf "skills/implement/SKILL.md fence starting at line %d: timing-ledger/timing-report call lacks LARCH_TIMING_LEDGER rehydration in the same fence\n", fence_start > "/dev/stderr"
      offending=1
    }
    in_fence=0; has_timing=0; has_rehydration=0; is_step0=0; next
  }
  in_fence {
    # Step 0 carve-out: a fence containing the canonical static export is the
    # only place LARCH_TIMING_LEDGER is set without read-session-env-key.sh.
    if (index($0, "export LARCH_TIMING_LEDGER=\"$IMPLEMENT_TMPDIR/timing-ledger.tsv\"") > 0) {
      is_step0=1
      has_rehydration=1
    }
    if (index($0, "LARCH_TIMING_LEDGER=$(") > 0 && index($0, "read-session-env-key.sh") > 0) {
      has_rehydration=1
    }
    if (index($0, "scripts/timing-ledger.sh") > 0 || index($0, "scripts/timing-report.sh") > 0) {
      has_timing=1
    }
  }
  END {
    if (in_fence && has_timing && !has_rehydration && !is_step0) {
      printf "skills/implement/SKILL.md fence starting at line %d: timing-ledger/timing-report call lacks LARCH_TIMING_LEDGER rehydration in the same fence\n", fence_start > "/dev/stderr"
      offending=1
    }
    exit offending
  }
' "$SKILL_MD" || fail "one or more timing-ledger / timing-report fences are missing LARCH_TIMING_LEDGER rehydration (see stderr above)"

# Invariant C: every fenced bash block that uses CLAUDE_PLUGIN_ROOT must carry
# the same-fence plugin-root rehydration guard (plugin-root.env source, or
# session-env.sh awk on pre-bootstrap sites only).
awk '
  BEGIN { in_fence=0; has_plugin_root=0; has_root_rehydration=0; fence_start=0; offending=0 }
  /^```bash$/ {
    in_fence=1; has_plugin_root=0; has_root_rehydration=0; fence_start=NR; next
  }
  /^```$/ && in_fence {
    if (has_plugin_root && !has_root_rehydration) {
      printf "skills/implement/SKILL.md fence starting at line %d: CLAUDE_PLUGIN_ROOT use lacks plugin-root rehydration in the same fence\n", fence_start > "/dev/stderr"
      offending=1
    }
    in_fence=0; has_plugin_root=0; has_root_rehydration=0; next
  }
  in_fence {
    if (index($0, "${CLAUDE_PLUGIN_ROOT}") > 0) {
      has_plugin_root=1
    }
    if (index($0, "plugin-root.env") > 0 && index($0, ". \"$IMPLEMENT_TMPDIR/plugin-root.env\"") > 0) {
      has_root_rehydration=1
    }
    if (index($0, "LARCH_CLAUDE_PLUGIN_ROOT=") > 0 && index($0, "awk") > 0) {
      has_root_rehydration=1
    }
  }
  END { exit offending }
' "$SKILL_MD" || fail "one or more CLAUDE_PLUGIN_ROOT fences are missing plugin-root rehydration (see stderr above)"

# Additional consistency check: every read-session-env-key.sh fetch of
# LARCH_TIMING_LEDGER MUST be matched by a fetch of LARCH_TOKEN_SESSION_ID in
# the same template (catches the inverse: a stray timing-only rehydration with
# no token-session-id sibling).
# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
timing_read_count=$(grep -Fxc 'LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")' "$SKILL_MD" || true)
# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
token_read_count=$(grep -Fxc 'LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")' "$SKILL_MD" || true)
[[ "$timing_read_count" == "$token_read_count" ]] \
  || fail "LARCH_TIMING_LEDGER read count ($timing_read_count) does not match LARCH_TOKEN_SESSION_ID read count ($token_read_count)"

new_export_count=$(grep -Fxc 'export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER' "$SKILL_MD" || true)
[[ "$new_export_count" == "$token_read_count" ]] \
  || fail "three-key export count ($new_export_count) does not match LARCH_TOKEN_SESSION_ID read count ($token_read_count)"

# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
step_telemetry_mark_count=$(grep -Fc '"${CLAUDE_PLUGIN_ROOT}/scripts/step-telemetry-mark.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --label ' "$SKILL_MD" || true)
# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
tmpdir_assign_count=$(grep -Fxc 'IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"' "$SKILL_MD" || true)
tmpdir_export_count=$(grep -Fxc 'export IMPLEMENT_TMPDIR' "$SKILL_MD" || true)
expected_tmpdir_coupling=$(( token_read_count + step_telemetry_mark_count ))
[[ "$tmpdir_assign_count" == "$expected_tmpdir_coupling" ]] \
  || fail "IMPLEMENT_TMPDIR assignment count ($tmpdir_assign_count) does not match token rehydration + step-telemetry-mark count ($expected_tmpdir_coupling = $token_read_count + $step_telemetry_mark_count)"
[[ "$tmpdir_export_count" == "$expected_tmpdir_coupling" ]] \
  || fail "IMPLEMENT_TMPDIR export count ($tmpdir_export_count) does not match token rehydration + step-telemetry-mark count ($expected_tmpdir_coupling = $token_read_count + $step_telemetry_mark_count)"

# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
plugin_root_source_count=$(grep -Fxc '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"' "$SKILL_MD" || true)
[[ "$plugin_root_source_count" == "41" ]] \
  || fail "plugin-root.env source guard count ($plugin_root_source_count) expected 41"

# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
plugin_root_awk_count=$(grep -Fxc '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk '\''BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}'\'' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)' "$SKILL_MD" || true)
[[ "$plugin_root_awk_count" == "3" ]] \
  || fail "session-env.sh awk fallback count ($plugin_root_awk_count) expected 3"

# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
legacy_fence_count=$(grep -Fxc 'if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then' "$SKILL_MD" || true)
[[ "$legacy_fence_count" == "0" ]] \
  || fail "legacy 4-line awk fence opener count ($legacy_fence_count) expected 0"

# Invariant E (issue #3425): the Step 18 closing-marks block MUST run BEFORE
# `implement-finalize.sh teardown` removes $IMPLEMENT_TMPDIR. The per-run
# token/timing ledgers live INSIDE the tmpdir and resolve_ledger_path() requires
# a live $IMPLEMENT_TMPDIR directory root; a post-teardown mark fails with
# "no per-run ledger root set". Guard the ordering so the block is never moved
# back after teardown.
# shellcheck disable=SC2016 # SKILL.md literal token — single-quoted on purpose.
done_mark_pattern='"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 18 — done"'
# shellcheck disable=SC2016 # SKILL.md literal token — single-quoted on purpose.
teardown_pattern='"${CLAUDE_PLUGIN_ROOT}/scripts/implement-finalize.sh" teardown'
done_mark_count=$(grep -Fc "$done_mark_pattern" "$SKILL_MD" || true)
teardown_count=$(grep -Fc "$teardown_pattern" "$SKILL_MD" || true)
[[ "$done_mark_count" == "1" ]] \
  || fail "expected exactly 1 closing 'Step 18 — done' token mark in SKILL.md, found $done_mark_count"
[[ "$teardown_count" == "1" ]] \
  || fail "expected exactly 1 'implement-finalize.sh teardown' invocation in SKILL.md, found $teardown_count"
done_mark_line=$(grep -Fn "$done_mark_pattern" "$SKILL_MD"); done_mark_line=${done_mark_line%%:*}
teardown_line=$(grep -Fn "$teardown_pattern" "$SKILL_MD"); teardown_line=${teardown_line%%:*}
[[ "$done_mark_line" -lt "$teardown_line" ]] \
  || fail "Step 18 closing 'Step 18 — done' mark (line $done_mark_line) must precede implement-finalize.sh teardown (line $teardown_line) — per-run ledgers live inside \$IMPLEMENT_TMPDIR and teardown deletes them (issue #3425)"

echo "PASS: test-implement-timing-rehydration.sh ($token_read_count token reads; $step_telemetry_mark_count step-telemetry-mark calls; $plugin_root_source_count plugin-root source guards; $plugin_root_awk_count awk fallbacks; closing marks before teardown: line $done_mark_line < $teardown_line)"
