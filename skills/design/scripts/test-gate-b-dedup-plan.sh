#!/usr/bin/env bash
# Offline harness for gate-b-dedup-plan.sh (issue #3175).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
SUBJECT="$SCRIPT_DIR/gate-b-dedup-plan.sh"
SETTLE="$SCRIPT_DIR/design-step35-settle.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-gate-b-dedup-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

write_plan() {
    local dir="$1"
    mkdir -p "$dir"
    cat >"$dir/plan.txt"
}

# --- snapshot writes keys and values ---
d="$TMPROOT/snapshot"
write_plan "$d" <<'EOF'
body
diff_added: 100
diff_deleted: 50
mechanical_churn: true
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
[[ -f "$d/.gate-b-optional-trailer-keys" ]] || fail "snapshot missing keys file"
grep -qx diff_added "$d/.gate-b-optional-trailer-keys" || fail "snapshot missing diff_added key"
[[ -f "$d/.gate-b-optional-trailer-keys.values" ]] || fail "snapshot missing values file"
grep -q '^diff_added=100$' "$d/.gate-b-optional-trailer-keys.values" || fail "snapshot missing diff_added value"

# --- dedup without prior snapshot fails closed ---
d="$TMPROOT/dedup-no-snapshot"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
set +e
"$SUBJECT" --design-tmpdir "$d" --dedup 2>/dev/null
rc=$?
set -e
[[ "$rc" == 3 ]] || fail "--dedup without snapshot should exit 3, got $rc"

# --- dedup preserves trailers ---
d="$TMPROOT/dedup-preserve"
write_plan "$d" <<'EOF'
body
body
diff_added: 100
diff_deleted: 50
mechanical_churn: true
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
out=$("$SUBJECT" --design-tmpdir "$d" --dedup)
printf '%s\n' "$out" | grep -q 'dedup-sweep: removed 1 duplicate' || fail "dedup should remove one duplicate body line"
grep -q '^diff_added: 100$' "$d/plan.txt" || fail "dedup must preserve diff_added trailer"
grep -q '^mechanical_churn: true$' "$d/plan.txt" || fail "dedup must preserve mechanical_churn trailer"

# --- dedup rejects newly introduced optional trailers when snapshot empty ---
d="$TMPROOT/no-new-trailers"
write_plan "$d" <<'EOF'
line
line
diff_lines: 10
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
printf 'line\nline\nmechanical_churn: true\ndiff_lines: 10\n' >"$d/plan.txt"
set +e
"$SUBJECT" --design-tmpdir "$d" --dedup 2>/dev/null
rc=$?
set -e
[[ "$rc" == 1 ]] || fail "dedup should reject newly introduced optional trailers, got rc=$rc"

# --- dedup allows pre-dedup trailer value recompute when keys preserved ---
d="$TMPROOT/value-recompute"
write_plan "$d" <<'EOF'
body
diff_added: 100
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
printf 'body\ndiff_added: 999\ndiff_lines: 200\n' >"$d/plan.txt"
"$SUBJECT" --design-tmpdir "$d" --dedup >/dev/null
grep -q '^diff_added: 999$' "$d/plan.txt" || fail "pre-dedup value recompute should preserve revised diff_added"

# --- dedup rejects trailer key loss before mechanical dedup ---
d="$TMPROOT/key-loss"
write_plan "$d" <<'EOF'
body
diff_added: 100
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
printf 'body\ndiff_lines: 200\n' >"$d/plan.txt"
set +e
"$SUBJECT" --design-tmpdir "$d" --dedup 2>/dev/null
rc=$?
set -e
[[ "$rc" == 1 ]] || fail "dedup should reject trailer key loss before dedup, got rc=$rc"


# --- settle wrapper syntax ---
bash -n "$SETTLE" || fail "design-step35-settle bash -n failed"

write_postplan_stub() {
    local path="$1"
    cat >"$path" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"$DESIGN_TMPDIR/postplan-argv.txt"
if [[ -f "$DESIGN_TMPDIR/postplan-output.txt" ]]; then
    cat "$DESIGN_TMPDIR/postplan-output.txt"
else
    printf 'POSTPLAN_RC=0\n'
fi
if [[ -f "$DESIGN_TMPDIR/postplan-rc.txt" ]]; then
    exit "$(cat "$DESIGN_TMPDIR/postplan-rc.txt")"
fi
exit 0
STUB
    chmod +x "$path"
}

write_dedup_stub() {
    local path="$1"
    cat >"$path" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'dedup\n' >>"$DESIGN_TMPDIR/dedup.log"
printf 'dedup stub\n'
if [[ -f "$DESIGN_TMPDIR/dedup-rc.txt" ]]; then
    exit "$(cat "$DESIGN_TMPDIR/dedup-rc.txt")"
fi
exit 0
STUB
    chmod +x "$path"
}

run_settle() {
    local d="$1" site="$2" round="${3:-}"
    local args
    shift 3 || true
    args=(--plugin-root "$REPO_ROOT" --site "$site")
    if [[ -n "$round" ]]; then
        args+=(--round-num "$round")
    fi
    DESIGN_TMPDIR="$d" "$SETTLE" "${args[@]}" "$@"
}

POSTPLAN_STUB="$TMPROOT/postplan-stub.sh"
DEDUP_STUB="$TMPROOT/dedup-stub.sh"
write_postplan_stub "$POSTPLAN_STUB"
write_dedup_stub "$DEDUP_STUB"

# --- Gate B clean path settles markers and skips plan-after snapshot ---
d="$TMPROOT/settle-gate-b-clean"
write_plan "$d" <<'EOF'
body
body
diff_lines: 2
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
out=$(DESIGN_TMPDIR="$d" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" "$SETTLE" --plugin-root "$REPO_ROOT" --site gate-b --round-num 7)
printf '%s\n' "$out" | grep -Fq 'dedup-sweep: removed 1 duplicate line(s) from plan.txt' || fail "settle should print dedup breadcrumb"
[[ -f "$d/.gate-b-postapply-ready-7" ]] || fail "settle should write Gate B apply-ready marker"
[[ "$(cat "$d/.step3-round-7.phase")" == awaiting-continuation ]] || fail "settle should write awaiting-continuation"
[[ ! -e "$d/plan-after-round-7.txt" ]] || fail "settle must not write plan-after-round snapshot"

# --- Gate B marker resume skips dedup and still runs postplan ---
d="$TMPROOT/settle-gate-b-resume"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
: >"$d/.gate-b-postapply-ready-8"
printf '3\n' >"$d/dedup-rc.txt"
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b 8 >/dev/null
[[ ! -e "$d/dedup.log" ]] || fail "Gate B marker resume must skip dedup"
[[ -f "$d/postplan-argv.txt" ]] || fail "Gate B marker resume should run postplan"
[[ "$(cat "$d/.step3-round-8.phase")" == awaiting-continuation ]] || fail "Gate B resume should settle continuation"

# --- Gate B rejects missing and non-numeric rounds ---
d="$TMPROOT/settle-missing-round"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b "" >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" == 2 ]] || fail "missing Gate B round should exit 2, got $rc"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b x >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" == 2 ]] || fail "non-numeric Gate B round should exit 2, got $rc"

# --- Dedup failure exits before postplan and before apply-ready ---
d="$TMPROOT/settle-dedup-fails"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
printf '3\n' >"$d/dedup-rc.txt"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b 9 >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" == 3 ]] || fail "dedup rc 3 should relay, got $rc"
[[ ! -e "$d/postplan-argv.txt" ]] || fail "dedup failure must not run postplan"
[[ ! -e "$d/.gate-b-postapply-ready-9" ]] || fail "dedup failure must not write apply-ready marker"

# --- Dedup rc 1 relays revise-again rc 1 ---
d="$TMPROOT/settle-dedup-rc1"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
printf '1\n' >"$d/dedup-rc.txt"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" discussion-round2 "" >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" == 1 ]] || fail "dedup rc 1 should relay revise-again rc 1, got $rc"
[[ ! -e "$d/postplan-argv.txt" ]] || fail "dedup rc 1 must not run postplan"

# --- Gate A and discussion Round 2 map to discussion-round2 postplan site ---
for site in gate-a discussion-round2; do
    d="$TMPROOT/settle-map-$site"
    write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
    DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" "$site" "" >/dev/null
    grep -Fq -- '--site discussion-round2' "$d/postplan-argv.txt" || fail "$site should map to discussion-round2 postplan site"
    [[ ! -e "$d/.step3-round-1.phase" ]] || fail "$site must not write Gate B phase markers"
done

# --- Pause output exits 11 and does not write clean continuation ---
d="$TMPROOT/settle-pause"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
printf 'PAUSE_OK=true\n' >"$d/postplan-output.txt"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b 10 >/dev/null
rc=$?
set -e
[[ "$rc" == 11 ]] || fail "pause output should exit 11, got $rc"
[[ "$(cat "$d/.step3-round-10.phase")" == awaiting-post-apply ]] || fail "pause must not write awaiting-continuation"

# --- Gate B operator brakes write awaiting-postplan-operator ---
for brake in 10 13; do
    d="$TMPROOT/settle-brake-$brake"
    write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
    printf 'POSTPLAN_RC=%s\n' "$brake" >"$d/postplan-output.txt"
    set +e
    DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b "$brake" >/dev/null
    rc=$?
    set -e
    [[ "$rc" == "$brake" ]] || fail "POSTPLAN_RC=$brake should relay, got $rc"
    [[ "$(cat "$d/.step3-round-$brake.phase")" == awaiting-postplan-operator ]] || fail "POSTPLAN_RC=$brake should write operator phase"
done

# --- Missing POSTPLAN_RC without pause is not clean ---
d="$TMPROOT/settle-missing-postplan-rc"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
printf 'POSTPLAN_STATUS=ok\n' >"$d/postplan-output.txt"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-a "" >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" == 3 ]] || fail "missing POSTPLAN_RC should exit 3, got $rc"

# --- POSTPLAN_RC=11 exits 11 without writing awaiting-continuation ---
d="$TMPROOT/settle-postplan-rc11"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
printf 'POSTPLAN_RC=11\n' >"$d/postplan-output.txt"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-b 11 >/dev/null
rc=$?
set -e
[[ "$rc" == 11 ]] || fail "POSTPLAN_RC=11 should exit 11, got $rc"
[[ "$(cat "$d/.step3-round-11.phase")" == awaiting-post-apply ]] || fail "POSTPLAN_RC=11 must not write awaiting-continuation"

# --- Missing POSTPLAN_RC with child rc 1 must not relay dedup revise-again rc 1 ---
d="$TMPROOT/settle-missing-postplan-rc-child1"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
printf 'POSTPLAN_STATUS=ok\n' >"$d/postplan-output.txt"
printf '1\n' >"$d/postplan-rc.txt"
set +e
DESIGN_STEP35_DEDUP_PLAN_SH="$DEDUP_STUB" DESIGN_STEP35_POSTPLAN_SH="$POSTPLAN_STUB" run_settle "$d" gate-a "" >/dev/null 2>/dev/null
rc=$?
set -e
[[ "$rc" == 3 ]] || fail "missing POSTPLAN_RC with child rc 1 should exit 3, got $rc"

echo "PASS: test-gate-b-dedup-plan.sh"
