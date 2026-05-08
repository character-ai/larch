#!/usr/bin/env bash
# test-check-review-changes.sh — Offline regression harness for check-review-changes.sh.
#
# Pins cases that together cover the issue #651 regression
# (pre-existing untracked → false positive), the empty-vs-missing
# baseline-state distinction, the printf '%s\n' -> comm -> sed safety net
# inside the SUT, the issue #695 dash-prefixed-filename regression, and
# the issue #1485 GIT_PROBE_FAILED / --strict fail-closed mode:
#   (a) clean tree, no baseline → FILES_CHANGED=false UNTRACKED_BASELINE=missing
#   (b) pre-existing untracked + matching baseline →
#       FILES_CHANGED=false UNTRACKED_BASELINE=present (THE regression case)
#   (c) review-created new untracked + matching baseline →
#       FILES_CHANGED=true UNTRACKED_BASELINE=present
#   (d) staged-only modification → FILES_CHANGED=true
#   (e) unstaged-only modification → FILES_CHANGED=true
#   (f) pre-existing untracked WITHOUT --baseline →
#       FILES_CHANGED=false UNTRACKED_BASELINE=missing (DELIBERATE behavior
#       change vs pre-fix script; see test-check-review-changes.md)
#   (g) zero-byte readable baseline + non-empty current untracked →
#       FILES_CHANGED=true UNTRACKED_BASELINE=present (empty-vs-missing
#       distinction — readable empty file is present, not missing)
#   (h) non-empty baseline + empty current untracked →
#       FILES_CHANGED=false UNTRACKED_BASELINE=present (pins the
#       printf '%s\n' -> comm -> sed '/^$/d' safety net for empty CURRENT)
#   (i) untracked file named "-n" + empty external baseline →
#       FILES_CHANGED=true UNTRACKED_BASELINE=present (issue #695:
#       feeding CURRENT to comm via printf '%s\n' instead of echo, so
#       filenames matching echo flags like -n / -e / -nn / -E are not
#       silently swallowed)
#   (j) probe failure (run outside any git tree), default mode →
#       FILES_CHANGED=false UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=true
#       (issue #1485: graceful degradation preserved by default; new
#       GIT_PROBE_FAILED key exposes the unknown-state signal)
#   (k) probe failure + --strict → FILES_CHANGED=true
#       UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=true (issue #1485
#       fail-closed: --strict promotes probe failure to FILES_CHANGED=true)
#   (l) clean tree + --strict → FILES_CHANGED=false UNTRACKED_BASELINE=missing
#       GIT_PROBE_FAILED=false (--strict is a no-op when probes succeed)
#
# Usage:
#   bash skills/implement/scripts/test-check-review-changes.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — at least one case failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUT="$SCRIPT_DIR/check-review-changes.sh"

if [[ ! -x "$SUT" ]]; then
    echo "FAIL: SUT not executable: $SUT" >&2
    exit 1
fi

PASS=0
FAIL=0

run_case() {
    local name="$1"; shift
    local expected_files_changed="$1"; shift
    local expected_baseline="$1"; shift
    local sandbox="$1"; shift
    local baseline_arg="$1"; shift
    # Optional 6th: expected_git_probe_failed (default "false" — most
    # legacy cases run inside a real git repo where probes succeed).
    local expected_git_probe_failed="${1:-false}"
    if [[ $# -gt 0 ]]; then
        shift
    fi
    # Optional 7th: extra args passed verbatim to the SUT (e.g. --strict).
    local extra_args="${1:-}"

    local out
    if [[ -n "$baseline_arg" ]]; then
        if [[ -n "$extra_args" ]]; then
            out=$(cd "$sandbox" && "$SUT" --baseline "$baseline_arg" "$extra_args")
        else
            out=$(cd "$sandbox" && "$SUT" --baseline "$baseline_arg")
        fi
    else
        if [[ -n "$extra_args" ]]; then
            out=$(cd "$sandbox" && "$SUT" "$extra_args")
        else
            out=$(cd "$sandbox" && "$SUT")
        fi
    fi

    local actual_fc actual_ub actual_gpf
    actual_fc=$(echo "$out" | awk -F= '$1=="FILES_CHANGED"{print $2}')
    actual_ub=$(echo "$out" | awk -F= '$1=="UNTRACKED_BASELINE"{print $2}')
    actual_gpf=$(echo "$out" | awk -F= '$1=="GIT_PROBE_FAILED"{print $2}')

    if [[ "$actual_fc" == "$expected_files_changed" ]] \
        && [[ "$actual_ub" == "$expected_baseline" ]] \
        && [[ "$actual_gpf" == "$expected_git_probe_failed" ]]; then
        echo "PASS: $name (FILES_CHANGED=$actual_fc UNTRACKED_BASELINE=$actual_ub GIT_PROBE_FAILED=$actual_gpf)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name" >&2
        echo "  expected: FILES_CHANGED=$expected_files_changed UNTRACKED_BASELINE=$expected_baseline GIT_PROBE_FAILED=$expected_git_probe_failed" >&2
        echo "  actual:   FILES_CHANGED=$actual_fc UNTRACKED_BASELINE=$actual_ub GIT_PROBE_FAILED=$actual_gpf" >&2
        echo "  full output:" >&2
        printf '    %s\n' "${out//$'\n'/$'\n'    }" >&2
        FAIL=$((FAIL + 1))
    fi
}

mkrepo() {
    local dir
    dir=$(mktemp -d)
    cd "$dir"
    git init --quiet
    git config user.email "test@example.com"
    git config user.name "Test"
    # Seed an initial committed file so git diff has a baseline tree.
    echo "initial" > tracked.txt
    git add tracked.txt
    git commit --quiet -m "initial"
    cd - > /dev/null
    echo "$dir"
}

# Case (a): clean tree, no baseline arg.
SBX_A=$(mkrepo)
run_case "(a) clean tree, no baseline" \
    "false" "missing" "$SBX_A" ""

# Case (b): pre-existing untracked + matching baseline (the regression case).
SBX_B=$(mkrepo)
( cd "$SBX_B" && touch stray-notes.txt )
BL_B="$SBX_B/baseline.txt"
( cd "$SBX_B" && git ls-files --others --exclude-standard | LC_ALL=C sort > "$BL_B" )
run_case "(b) pre-existing untracked + matching baseline (regression)" \
    "false" "present" "$SBX_B" "$BL_B"

# Case (c): review-created new untracked + matching baseline.
SBX_C=$(mkrepo)
( cd "$SBX_C" && touch stray-notes.txt )
BL_C="$SBX_C/baseline.txt"
( cd "$SBX_C" && git ls-files --others --exclude-standard | LC_ALL=C sort > "$BL_C" )
( cd "$SBX_C" && touch new-from-review.txt )
run_case "(c) review-created new untracked" \
    "true" "present" "$SBX_C" "$BL_C"

# Case (d): staged-only modification (with present baseline).
SBX_D=$(mkrepo)
BL_D="$SBX_D/baseline.txt"
: > "$BL_D"  # empty baseline, no untracked at snapshot time
( cd "$SBX_D" && echo "staged change" >> tracked.txt && git add tracked.txt )
run_case "(d) staged-only modification" \
    "true" "present" "$SBX_D" "$BL_D"

# Case (e): unstaged-only modification (with present baseline).
SBX_E=$(mkrepo)
BL_E="$SBX_E/baseline.txt"
: > "$BL_E"
( cd "$SBX_E" && echo "unstaged change" >> tracked.txt )
run_case "(e) unstaged-only modification" \
    "true" "present" "$SBX_E" "$BL_E"

# Case (f): pre-existing untracked WITHOUT baseline file (graceful degradation).
# DELIBERATE behavior change from pre-fix script: untracked-only with no
# baseline now reports FILES_CHANGED=false (was true). See
# test-check-review-changes.md.
SBX_F=$(mkrepo)
( cd "$SBX_F" && touch stray-notes.txt )
run_case "(f) pre-existing untracked WITHOUT baseline (deliberate behavior change)" \
    "false" "missing" "$SBX_F" ""

# Case (g): zero-byte readable baseline + non-empty current untracked.
# Empty-vs-missing distinction: a readable zero-byte file IS present and
# means "no untracked at snapshot time," so all current untracked are new.
SBX_G=$(mkrepo)
BL_G="$SBX_G/baseline.txt"
: > "$BL_G"  # zero-byte readable
( cd "$SBX_G" && touch new-from-review.txt )
run_case "(g) zero-byte readable baseline + non-empty current untracked" \
    "true" "present" "$SBX_G" "$BL_G"

# Case (h): non-empty baseline + empty current untracked. Exercises the
# printf '%s\n' -> comm -> sed '/^$/d' safety net path inside the SUT
# (when CURRENT is empty, printf '%s\n' "" emits one blank line that
# sed must strip). A regression that removes the trailing sed filter
# would yield a phantom delta entry and flip FILES_CHANGED to true
# incorrectly.
SBX_H=$(mkrepo)
( cd "$SBX_H" && touch ephemeral.txt )
BL_H="$SBX_H/baseline.txt"
( cd "$SBX_H" && git ls-files --others --exclude-standard | LC_ALL=C sort > "$BL_H" )
( cd "$SBX_H" && rm ephemeral.txt )
run_case "(h) non-empty baseline + empty current untracked (sed safety net)" \
    "false" "present" "$SBX_H" "$BL_H"

# Case (i): untracked file named "-n" with an EXTERNAL (outside-repo)
# empty baseline file. Issue #695: bash builtin echo treats values like
# "-n" / "-e" / "-nn" / "-E" as flags, so feeding CURRENT through
# `echo "$CURRENT"` would emit nothing on these names and comm would
# report an empty delta — silently masking review-created untracked
# files matching such names. The fix replaces echo with printf '%s\n'
# inside check-review-changes.sh; this case fails pre-fix and passes
# post-fix. The baseline lives outside the repo so `git ls-files
# --others` doesn't pick it up as part of CURRENT.
SBX_I=$(mkrepo)
BL_I=$(mktemp)  # external (outside the repo), empty baseline
( cd "$SBX_I" && touch -- -n )
run_case '(i) untracked filename "-n" + external empty baseline (#695)' \
    "true" "present" "$SBX_I" "$BL_I"
rm -f "$BL_I"

# Case (j): probe failure — run the SUT outside any git tree (no .git
# anywhere up the chain). git diff and git ls-files both exit non-zero
# with "fatal: not a git repository". Default mode preserves graceful
# degradation (FILES_CHANGED=false), but GIT_PROBE_FAILED=true now
# exposes the unknown-state signal so callers can fail-closed.
SBX_J=$(mktemp -d)
run_case "(j) probe failure (no git repo), default mode" \
    "false" "missing" "$SBX_J" "" "true"

# Case (k): probe failure + --strict. --strict promotes a probe failure
# to FILES_CHANGED=true (fail-closed) so the caller does not silently
# skip the post-/review checks pass on a transient git outage.
SBX_K=$(mktemp -d)
run_case "(k) probe failure (no git repo) + --strict (fail-closed)" \
    "true" "missing" "$SBX_K" "" "true" "--strict"

# Case (l): clean tree + --strict. --strict is a no-op when probes
# succeed — FILES_CHANGED reflects the observed signal (no changes
# here) and GIT_PROBE_FAILED stays false.
SBX_L=$(mkrepo)
run_case "(l) clean tree + --strict (no-op when probes succeed)" \
    "false" "missing" "$SBX_L" "" "false" "--strict"

# Cleanup sandboxes.
rm -rf "$SBX_A" "$SBX_B" "$SBX_C" "$SBX_D" "$SBX_E" "$SBX_F" "$SBX_G" "$SBX_H" "$SBX_I" "$SBX_J" "$SBX_K" "$SBX_L"

echo ""
echo "RESULTS: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
