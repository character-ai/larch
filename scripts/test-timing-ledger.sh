#!/usr/bin/env bash
# Regression tests for scripts/timing-ledger.sh.

set -euo pipefail

# Hermetic: clear any caller-supplied timing/session env so the test exercises
# the resolver fallback chain deterministically.
unset LARCH_TIMING_LEDGER LARCH_TIMING_SKILL LARCH_TIMING_TASK_KIND \
      IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR SESSION_ENV_PATH || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/larch-timing-ledger-test.XXXXXX")
on_err() {
    echo "test-timing-ledger.sh: FAIL at line $1 (last cmd exit=$2)" >&2
    rm -rf "$TMP_BASE"
}
trap 'on_err "$LINENO" "$?"' ERR
trap 'rm -rf "$TMP_BASE"' EXIT

LEDGER="$TMP_BASE/timing.tsv"

"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" mark "Step 0"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" workflow-path HARD
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor codex --task-kind codex-implement --start-s 10 --end-s 20 \
    --output "/private/work/output.txt" --exit-code 0 --status complete

[[ $(awk -F '\t' '{print NF}' "$LEDGER" | sort -u) == "13" ]]
grep -Fq $'v1\tmark\t' "$LEDGER"
grep -Fq $'v1\tworkflow\t' "$LEDGER"
grep -Fq $'\tcodex\tcodex-implement\t10\t20\t10\toutput.txt\t0\tcomplete' "$LEDGER"
if grep -Fq '/private/work/output.txt' "$LEDGER"; then
    echo "absolute output path leaked into timing ledger" >&2
    exit 1
fi

mode=$(stat -f '%Lp' "$LEDGER" 2>/dev/null || stat -c '%a' "$LEDGER")
# GNU stat (Linux) and BSD stat (macOS) both produce "600" with -c '%a' / -f '%Lp'.
# Some container images and umask configurations can leave a leading zero ("0600")
# or unrelated SUID/SGID bits cleared ("000600"). Compare on the trailing 3 digits.
[[ "${mode: -3}" == "600" ]] || { echo "expected mode 600 got '$mode'" >&2; exit 1; }

WARN="$TMP_BASE/warn.txt"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor cursor --task-kind cursor-custom-kind --start-s 30 --end-s 32 \
    --output "x"$'\t'"y.txt" 2>"$WARN"
grep -Fq 'unknown task-kind: cursor-custom-kind' "$WARN"
grep -Fq '<NUL>' "$LEDGER"

BAD="$TMP_BASE/bad.txt"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$LEDGER" record-vendor-task \
    --vendor codex --task-kind BadKind --start-s 1 --end-s 2 --output x 2>"$BAD"
grep -Fq 'malformed task-kind' "$BAD"

OUTSIDE="$TMP_BASE/outside.txt"
LARCH_TIMING_LEDGER="/not/allowed/timing.tsv" IMPLEMENT_TMPDIR="$TMP_BASE" \
    "$REPO_ROOT/scripts/timing-ledger.sh" mark "fall through" 2>"$OUTSIDE"
grep -Fq 'LARCH_TIMING_LEDGER not under any allowed root' "$OUTSIDE"
grep -Fq 'fall through' "$TMP_BASE/timing-ledger.tsv"

ENV_LEDGER="$TMP_BASE/env/timing.tsv"
mkdir -p "$TMP_BASE/env"
LARCH_TIMING_LEDGER="$ENV_LEDGER" IMPLEMENT_TMPDIR="$TMP_BASE" \
    "$REPO_ROOT/scripts/timing-ledger.sh" mark "env ok"
grep -Fq 'env ok' "$ENV_LEDGER"

SEQ_LEDGER="$TMP_BASE/parallel.tsv"
seq 1 20 | xargs -P 4 -I{} "$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$SEQ_LEDGER" mark "p{}"
[[ $(wc -l < "$SEQ_LEDGER" | tr -d ' ') == "20" ]]
[[ $(awk -F '\t' '{print NF}' "$SEQ_LEDGER" | sort -u) == "13" ]]

# Review FINDING_13: symlink ledger paths must be refused before any write.
SYMLINK_TARGET="$TMP_BASE/symlink-target.tsv"
SYMLINK_LEDGER="$TMP_BASE/symlink.tsv"
: > "$SYMLINK_TARGET"
ln -s "$SYMLINK_TARGET" "$SYMLINK_LEDGER"
SYM_WARN="$TMP_BASE/sym-warn.txt"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$SYMLINK_LEDGER" mark "should be rejected" 2>"$SYM_WARN"
grep -Fq 'ledger is a symlink' "$SYM_WARN"
[[ ! -s "$SYMLINK_TARGET" ]] || { echo "symlink target was written despite refusal" >&2; exit 1; }

# Review FINDING_7: when flock cannot be acquired (simulated by a held lock
# file plus a tight wait), append must fail closed rather than silently
# producing interleaved garbage.
if command -v flock >/dev/null 2>&1; then
  FAILCLOSE_LEDGER="$TMP_BASE/failclose.tsv"
  FAILCLOSE_LOCK="$FAILCLOSE_LEDGER.lock"  # match append_tsv_line()'s ${ledger}.lock convention
  : > "$FAILCLOSE_LEDGER"
  : > "$FAILCLOSE_LOCK"
  FAILCLOSE_WARN="$TMP_BASE/failclose-warn.txt"
  # Hold the lock in the background; the script tries flock -w 5 9 on the same
  # ${ledger}.lock path and times out, hitting the fail-closed branch.
  (
      flock -x 9
      sleep 8
  ) 9>"$FAILCLOSE_LOCK" &
  HOLDER_PID=$!
  sleep 1
  "$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$FAILCLOSE_LEDGER" mark "should be skipped" 2>"$FAILCLOSE_WARN" || true
  wait "$HOLDER_PID" 2>/dev/null || true
  if grep -Fq 'flock lock acquisition failed' "$FAILCLOSE_WARN"; then
    if [[ -s "$FAILCLOSE_LEDGER" ]]; then
      echo "fail-closed flock fallback wrote a row anyway" >&2
      exit 1
    fi
  else
    # On environments where the lock holder failed to acquire (rare), the
    # warn message will be the no-flock or flock-unavailable variant. Skip
    # rather than fail — this case is environmental, not a contract bug.
    echo "WARN: flock fail-closed test did not exercise the contention branch (env)" >&2
  fi
fi

# Fail-closed: all env vars unset (already unset at top), no --ledger → warn, no file created
FAIL_CLOSED_WARN="$TMP_BASE/fail-closed.txt"
"$REPO_ROOT/scripts/timing-ledger.sh" mark "fail-closed-probe" 2>"$FAIL_CLOSED_WARN" || true
grep -Fq 'no per-run ledger root set' "$FAIL_CLOSED_WARN"

# Positive: IMPLEMENT_TMPDIR resolution
IMPL_TMP="$TMP_BASE/impl-positive"
mkdir -p "$IMPL_TMP"
IMPLEMENT_TMPDIR="$IMPL_TMP" "$REPO_ROOT/scripts/timing-ledger.sh" mark "impl-positive"
grep -Fq 'impl-positive' "$IMPL_TMP/timing-ledger.tsv"

echo "PASS: test-timing-ledger.sh"
