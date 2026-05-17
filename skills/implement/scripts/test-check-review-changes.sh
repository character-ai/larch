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
#   (m) parse error (clean repo + --bogus) → FILES_CHANGED=false
#       UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=false (parse error
#       short-circuits before any git probe runs)
#   (n) parse error + --strict footgun (non-git + "--strict --bogus") →
#       FILES_CHANGED=false UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=false
#       (issue #1485 round-1 review fix: parse error must short-circuit
#       BEFORE probes run, so --strict cannot promote a typo to
#       FILES_CHANGED=true via probe failure)
#   (o) HEAD-baseline equals current HEAD → FILES_CHANGED=false
#       (no movement; the head-baseline dimension is a no-op)
#   (p) HEAD-baseline points at a prior commit, current HEAD has advanced →
#       FILES_CHANGED=true (issue #2236: review-and-fix.sh per-round commits
#       leave a clean working tree, so the head-baseline dimension is the
#       only signal that Step 5 modified the repo)
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

# Cases (m)-(n): parse-error contract pinning. The script must short-
# circuit on bad CLI input BEFORE running any git probe — emit ERROR= on
# stderr and the three stdout keys with their conservative degraded
# values. In particular, "--strict --bogus" outside a git repo must
# NOT flip FILES_CHANGED=true via a probe failure (the parse-error +
# --strict footgun the round-1 review surfaced). These cases are
# inline (rather than via run_case) because they need to pass multiple
# args to the SUT, while run_case's $extra_args is a single token.

# Case (m): clean repo + bogus flag → parse error, three keys, no probe.
# Capture stderr separately to assert the documented ERROR= line is
# emitted (a regression that dropped the stderr line would otherwise
# pass silently if only stdout were checked — round-2 review nit).
SBX_M=$(mkrepo)
STDERR_M=$(mktemp)
out_m=$(cd "$SBX_M" && "$SUT" --bogus 2>"$STDERR_M")
fc_m=$(echo "$out_m" | awk -F= '$1=="FILES_CHANGED"{print $2}')
ub_m=$(echo "$out_m" | awk -F= '$1=="UNTRACKED_BASELINE"{print $2}')
gpf_m=$(echo "$out_m" | awk -F= '$1=="GIT_PROBE_FAILED"{print $2}')
err_m_ok="false"
grep -q '^ERROR=' "$STDERR_M" && err_m_ok="true"
if [[ "$fc_m" == "false" && "$ub_m" == "missing" && "$gpf_m" == "false" && "$err_m_ok" == "true" ]]; then
    echo "PASS: (m) parse error (clean repo + --bogus) emits 3 keys + ERROR= on stderr, no probe (FILES_CHANGED=$fc_m UNTRACKED_BASELINE=$ub_m GIT_PROBE_FAILED=$gpf_m ERROR_ON_STDERR=$err_m_ok)"
    PASS=$((PASS + 1))
else
    echo "FAIL: (m) parse error (clean repo + --bogus)" >&2
    echo "  expected: FILES_CHANGED=false UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=false ERROR_ON_STDERR=true" >&2
    echo "  actual:   FILES_CHANGED=$fc_m UNTRACKED_BASELINE=$ub_m GIT_PROBE_FAILED=$gpf_m ERROR_ON_STDERR=$err_m_ok" >&2
    FAIL=$((FAIL + 1))
fi
rm -f "$STDERR_M"

# Case (n): non-git sandbox + "--strict --bogus" → parse error must
# short-circuit BEFORE probes run, so GIT_PROBE_FAILED stays false and
# --strict cannot promote FILES_CHANGED=true on a CLI typo. Pre-fix
# this case would yield FILES_CHANGED=true GIT_PROBE_FAILED=true (the
# parse-error + strict footgun); the fix exits 0 with the conservative
# degraded values before any git probe is invoked. Stderr ERROR= is
# also asserted (round-2 review nit) so a regression dropping the
# stderr line is caught.
SBX_N=$(mktemp -d)
STDERR_N=$(mktemp)
out_n=$(cd "$SBX_N" && "$SUT" --strict --bogus 2>"$STDERR_N")
fc_n=$(echo "$out_n" | awk -F= '$1=="FILES_CHANGED"{print $2}')
ub_n=$(echo "$out_n" | awk -F= '$1=="UNTRACKED_BASELINE"{print $2}')
gpf_n=$(echo "$out_n" | awk -F= '$1=="GIT_PROBE_FAILED"{print $2}')
err_n_ok="false"
grep -q '^ERROR=' "$STDERR_N" && err_n_ok="true"
if [[ "$fc_n" == "false" && "$ub_n" == "missing" && "$gpf_n" == "false" && "$err_n_ok" == "true" ]]; then
    echo "PASS: (n) parse error short-circuits before --strict can flip FILES_CHANGED, ERROR= on stderr (FILES_CHANGED=$fc_n UNTRACKED_BASELINE=$ub_n GIT_PROBE_FAILED=$gpf_n ERROR_ON_STDERR=$err_n_ok)"
    PASS=$((PASS + 1))
else
    echo "FAIL: (n) parse error + --strict footgun: parse error did not short-circuit before probe ran" >&2
    echo "  expected: FILES_CHANGED=false UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=false ERROR_ON_STDERR=true" >&2
    echo "  actual:   FILES_CHANGED=$fc_n UNTRACKED_BASELINE=$ub_n GIT_PROBE_FAILED=$gpf_n ERROR_ON_STDERR=$err_n_ok" >&2
    FAIL=$((FAIL + 1))
fi
rm -f "$STDERR_N"

# Cases (o)-(p): HEAD-baseline dimension. Covers the issue #2236 per-round
# commit flow — review-and-fix.sh commits each round's accepted-fixes, so by
# Step 6 entry the working tree is clean but HEAD has advanced. Without the
# HEAD-baseline source, FILES_CHANGED would be false and the second lint
# pass would silently skip. With --head-baseline, the SUT detects HEAD
# movement and reports FILES_CHANGED=true.

# Case (o): HEAD-baseline matches current HEAD (no movement) → no signal.
SBX_O=$(mkrepo)
HEAD_BL_O="$SBX_O/pre-review-head.txt"
( cd "$SBX_O" && git rev-parse HEAD > "$HEAD_BL_O" )
out_o=$(cd "$SBX_O" && "$SUT" --head-baseline "$HEAD_BL_O")
fc_o=$(echo "$out_o" | awk -F= '$1=="FILES_CHANGED"{print $2}')
if [[ "$fc_o" == "false" ]]; then
    echo "PASS: (o) head-baseline matches current HEAD → FILES_CHANGED=$fc_o"
    PASS=$((PASS + 1))
else
    echo "FAIL: (o) head-baseline matches current HEAD" >&2
    echo "  expected: FILES_CHANGED=false" >&2
    echo "  actual:   FILES_CHANGED=$fc_o" >&2
    FAIL=$((FAIL + 1))
fi

# Case (p): HEAD-baseline points at a prior commit; current HEAD has
# advanced → FILES_CHANGED=true even though the working tree is clean.
# This is the load-bearing case for issue #2236.
SBX_P=$(mkrepo)
HEAD_BL_P="$SBX_P/pre-review-head.txt"
( cd "$SBX_P" && git rev-parse HEAD > "$HEAD_BL_P" )
( cd "$SBX_P" && echo "review-fix" >> tracked.txt && git add tracked.txt && git commit --quiet -m "Address code review feedback (round 1)" )
out_p=$(cd "$SBX_P" && "$SUT" --head-baseline "$HEAD_BL_P")
fc_p=$(echo "$out_p" | awk -F= '$1=="FILES_CHANGED"{print $2}')
if [[ "$fc_p" == "true" ]]; then
    echo "PASS: (p) head-baseline differs from current HEAD (per-round commit) → FILES_CHANGED=$fc_p"
    PASS=$((PASS + 1))
else
    echo "FAIL: (p) head-baseline differs from current HEAD (per-round commit)" >&2
    echo "  expected: FILES_CHANGED=true" >&2
    echo "  actual:   FILES_CHANGED=$fc_p" >&2
    FAIL=$((FAIL + 1))
fi

# Cleanup sandboxes.
rm -rf "$SBX_A" "$SBX_B" "$SBX_C" "$SBX_D" "$SBX_E" "$SBX_F" "$SBX_G" "$SBX_H" "$SBX_I" "$SBX_J" "$SBX_K" "$SBX_L" "$SBX_M" "$SBX_N" "$SBX_O" "$SBX_P"

echo ""
echo "RESULTS: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
