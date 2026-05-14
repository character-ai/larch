#!/usr/bin/env bash
# Regression test for /implement timing-ledger rehydration.
#
# Asserts three invariants on skills/implement/SKILL.md:
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
#      the local `LARCH_CLAUDE_PLUGIN_ROOT` awk rehydration guard, so nested
#      Bash calls can recover the plugin root from session-env without
#      depending on the root variable to find the reader script.

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
# the same-fence plugin-root rehydration guard. The guard reads session-env via
# awk instead of read-session-env-key.sh because the latter itself lives under
# CLAUDE_PLUGIN_ROOT.
awk '
  BEGIN { in_fence=0; has_plugin_root=0; has_root_rehydration=0; fence_start=0; offending=0 }
  /^```bash$/ {
    in_fence=1; has_plugin_root=0; has_root_rehydration=0; fence_start=NR; next
  }
  /^```$/ && in_fence {
    if (has_plugin_root && !has_root_rehydration) {
      printf "skills/implement/SKILL.md fence starting at line %d: CLAUDE_PLUGIN_ROOT use lacks LARCH_CLAUDE_PLUGIN_ROOT rehydration in the same fence\n", fence_start > "/dev/stderr"
      offending=1
    }
    in_fence=0; has_plugin_root=0; has_root_rehydration=0; next
  }
  in_fence {
    if (index($0, "${CLAUDE_PLUGIN_ROOT}") > 0) {
      has_plugin_root=1
    }
    if (index($0, "LARCH_CLAUDE_PLUGIN_ROOT=") > 0) {
      has_root_rehydration=1
    }
  }
  END { exit offending }
' "$SKILL_MD" || fail "one or more CLAUDE_PLUGIN_ROOT fences are missing LARCH_CLAUDE_PLUGIN_ROOT rehydration (see stderr above)"

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
tmpdir_assign_count=$(grep -Fxc 'IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"' "$SKILL_MD" || true)
tmpdir_export_count=$(grep -Fxc 'export IMPLEMENT_TMPDIR' "$SKILL_MD" || true)
[[ "$tmpdir_assign_count" == "$token_read_count" ]] \
  || fail "IMPLEMENT_TMPDIR assignment count ($tmpdir_assign_count) does not match token rehydration count ($token_read_count)"
[[ "$tmpdir_export_count" == "$token_read_count" ]] \
  || fail "IMPLEMENT_TMPDIR export count ($tmpdir_export_count) does not match token rehydration count ($token_read_count)"

# shellcheck disable=SC2016 # SKILL.md literal template — single-quoted on purpose.
plugin_root_read_count=$(grep -Fxc '  CLAUDE_PLUGIN_ROOT=$(awk '\''BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}'\'' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)' "$SKILL_MD" || true)
plugin_root_export_count=$(grep -Fxc 'export CLAUDE_PLUGIN_ROOT' "$SKILL_MD" || true)
[[ "$plugin_root_read_count" == "$plugin_root_export_count" ]] \
  || fail "CLAUDE_PLUGIN_ROOT read count ($plugin_root_read_count) does not match export count ($plugin_root_export_count)"

echo "PASS: test-implement-timing-rehydration.sh ($token_read_count timing sites; $plugin_root_read_count plugin-root sites covered)"
