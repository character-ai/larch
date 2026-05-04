#!/usr/bin/env bash
# test-validate-citations-budget.sh — Budget-exhaustion regression harness for validate-citations.sh.
#
# Split from test-validate-citations.sh to keep CI harness shards under the
# target wall-clock. Tests 20 and 21 are real-time-bound because they assert
# timeout and process-cleanup behavior around deliberate sleeps; Tests 1-19
# are CPU-bound and stay in the parent harness.
#
# Test seams (env vars exported per case):
#   __VC_FAKE_CURL    : absolute path to a fake-curl shim that returns scripted
#                       HTTP codes per --output-flag URL pattern.
#   __VC_SKIP_DNS     : skip real DNS resolution.
#   __VC_STUB_RESOLVE : 'host=ip;host=ip;...' for stub resolution.
#   __VC_DRY_RUN      : exit after extraction, print to stderr.
#
# Exit 0 on pass, 1 on any failure.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../../.." && pwd -P)
VALIDATOR="$REPO_ROOT/skills/research/scripts/validate-citations.sh"
WORK=$(mktemp -d -t validate-citations-test.XXXXXX)
trap 'rm -rf "$WORK"' EXIT

[[ -x "$VALIDATOR" ]] || { echo "FAIL: $VALIDATOR is not executable"; exit 1; }

PASS=0
FAIL=0

note() { printf '  %s\n' "$1"; }

assert() {
    local name="$1" cond_cmd="$2"
    if eval "$cond_cmd"; then
        PASS=$((PASS + 1))
        note "ok: $name"
    else
        FAIL=$((FAIL + 1))
        note "FAIL: $name"
    fi
}

ARGV_LOG="$WORK/last-argv"

# ---------- Test 20: Darwin budget-exhaustion kills background curl (#662) ----------
echo "=== Test 20: Darwin budget-exhaustion no-orphan-curl ==="
case "$(uname -s 2>/dev/null)" in
    Darwin*)
        mkdir -p "$WORK/c20"
        cat > "$WORK/c20/report.txt" <<'REPORT'
See https://example-hang.invalid/page1 and https://example-hang.invalid/page2.
REPORT
        # PID-recording fake curl: records its own PID to a per-invocation file
        # at start, removes it on clean exit. After the validator returns, any
        # surviving .pid file whose process is still alive is an orphan.
        PIDS_DIR="$WORK/c20/pids"
        mkdir -p "$PIDS_DIR"
        FAKE_CURL_PIDREC="$WORK/c20/fake-curl-pidrec"
        cat > "$FAKE_CURL_PIDREC" <<FAKEEOF
#!/usr/bin/env bash
PIDS_DIR="$PIDS_DIR"
echo "\$\$" > "\$PIDS_DIR/\$\$.pid"
trap 'rm -f "\$PIDS_DIR/\$\$.pid"' EXIT
url=""
for a in "\$@"; do
    case "\$a" in http://*|https://*) url="\$a" ;; esac
done
case "\$url" in
    *example-hang.invalid*) sleep 15; printf '200'; exit 0 ;;
    *) printf '200'; exit 0 ;;
esac
FAKEEOF
        chmod +x "$FAKE_CURL_PIDREC"
        START=$(date +%s)
        set +e
        __VC_FAKE_CURL="$FAKE_CURL_PIDREC" __VC_LAST_ARGV="$ARGV_LOG" \
        __VC_SKIP_DNS=1 __VC_STUB_RESOLVE='example-hang.invalid=8.8.8.8' \
            "$VALIDATOR" --report "$WORK/c20/report.txt" --output "$WORK/c20/cv.md" \
                         --tmpdir "$WORK/c20" --budget-seconds 1 >/dev/null 2>&1
        VALIDATOR_RC=$?
        set -e
        END=$(date +%s)
        ELAPSED=$((END - START))
        # Wait briefly for any in-flight kill signals to land before scanning
        # for survivors. Bug behavior leaves ~15s sleeps running.
        sleep 2
        ORPHAN_COUNT=0
        for pf in "$PIDS_DIR"/*.pid; do
            [[ -e "$pf" ]] || continue
            opid=$(cat "$pf" 2>/dev/null || echo "")
            [[ -z "$opid" ]] && continue
            if kill -0 "$opid" 2>/dev/null; then
                ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
            fi
        done
        # Bug-#662 leak behavior is ~15s (the fake-curl sleep); ceiling 15s
        # filters that out while leaving slack for slow / shared CI.
        assert "Test 20: validator returned within budget + slack (got ${ELAPSED}s)" "[[ \"$ELAPSED\" -le 15 ]]"
        # Fail-soft contract: validator MUST exit 0 even on budget timeout.
        # Catches the regression class where the kill path signals $$'s
        # process group and SIGTERMs the validator itself (exit 143, no
        # sidecar).
        assert "Test 20: validator exited 0 (fail-soft contract on timeout)" "[[ \"$VALIDATOR_RC\" -eq 0 ]]"
        assert "Test 20: sidecar produced" "[[ -s \"$WORK/c20/cv.md\" ]]"
        assert "Test 20: sidecar has UNKNOWN | timeout for hung URL #1" "grep -F 'https://example-hang.invalid/page1' \"$WORK/c20/cv.md\" | grep -F 'UNKNOWN' | grep -Fq 'timeout'"
        assert "Test 20: sidecar has UNKNOWN | timeout for hung URL #2" "grep -F 'https://example-hang.invalid/page2' \"$WORK/c20/cv.md\" | grep -F 'UNKNOWN' | grep -Fq 'timeout'"
        assert "Test 20: no orphan fake-curl processes after budget-kill (got $ORPHAN_COUNT)" "[[ \"$ORPHAN_COUNT\" == 0 ]]"
        ;;
    *)
        note "skip: Darwin-only (Linux no-setsid path covered by Test 21)"
        ;;
esac

# ---------- Test 21: Linux no-setsid budget-exhaustion fail-soft (#849) ----------
echo "=== Test 21: Linux no-setsid budget-exhaustion fail-soft ==="
case "$(uname -s 2>/dev/null)" in
    Linux*)
        # Test 21 verifies the no-setsid Linux branch of validate-citations.sh
        # (the per-PID `kill <subshell>` fallback at :765, gated by the
        # __VC_SETSID_DONE marker). The runner needs `setsid` available on
        # its PATH so the harness can put the validator in its OWN session;
        # without that isolation, a hypothetical regression of the marker
        # gate (`kill -- -$$` running unconditionally) would also kill the
        # test runner, leaving the failure mode ambiguous.
        if ! command -v setsid >/dev/null 2>&1; then
            note "skip: setsid not available on this Linux runner — cannot isolate validator session for regression test"
        else
            mkdir -p "$WORK/c21"
            cat > "$WORK/c21/report.txt" <<'REPORT'
See https://example-hang.invalid/page1 and https://example-hang.invalid/page2.
REPORT
            # Hermetic clean-bin: symlink common tools into a directory that
            # explicitly omits `setsid`. PATH=$CLEAN_BIN forces the
            # validator's `command -v setsid` check (validate-citations.sh:669)
            # to fail so it takes the no-setsid Linux branch (the production
            # scenario under test). Directory-stripping `/usr/bin` is unsafe
            # on merged-/usr distros (would also remove grep/awk/etc.).
            # Profile: URL-only fixture with __VC_SKIP_DNS / __VC_STUB_RESOLVE
            # set; if the scenario ever grows beyond URL-only fetches, the
            # tool list here must be extended in sync.
            CLEAN_BIN="$WORK/c21/clean-bin"
            mkdir -p "$CLEAN_BIN"
            for t in bash sh mktemp mkdir rm mv cp grep sed awk wc sort head tail tr cut sleep kill ps echo date dirname basename env cat tee touch chmod ln readlink stat find xargs which test '[' printf shasum md5sum md5 expr seq uname; do
                src=$(command -v "$t" 2>/dev/null || true)
                [[ -n "$src" && -x "$src" ]] && ln -sf "$src" "$CLEAN_BIN/$t"
            done
            # Defense in depth: explicit removal in case any tool above is
            # named/aliased to setsid on some distro.
            rm -f "$CLEAN_BIN/setsid"

            # PID-recording fake curl that honors --max-time so orphans
            # naturally die after $PER_FETCH_TIMEOUT per the documented
            # contract on the no-setsid Linux branch (orphan curls bounded
            # by --per-fetch-timeout). Handles both two-element form
            # (`--max-time N`) and bundled form (`--max-time=N`).
            PIDS_DIR="$WORK/c21/pids"
            mkdir -p "$PIDS_DIR"
            FAKE_CURL_PIDREC="$WORK/c21/fake-curl-pidrec"
            cat > "$FAKE_CURL_PIDREC" <<FAKEEOF
#!/usr/bin/env bash
PIDS_DIR="$PIDS_DIR"
echo "\$\$" > "\$PIDS_DIR/\$\$.pid"
trap 'rm -f "\$PIDS_DIR/\$\$.pid"' EXIT
url=""
max_time=10
prev=""
for a in "\$@"; do
    case "\$prev" in --max-time) max_time="\$a" ;; esac
    case "\$a" in --max-time=*) max_time="\${a#--max-time=}" ;; esac
    case "\$a" in http://*|https://*) url="\$a" ;; esac
    prev="\$a"
done
case "\$url" in
    *example-hang.invalid*) sleep \$((max_time + 1)); exit 28 ;;
    *) printf '200'; exit 0 ;;
esac
FAKEEOF
            chmod +x "$FAKE_CURL_PIDREC"

            # Pre-flight: hermetic PATH must hide setsid AND must still
            # expose uname (the validator branches on `case "$(uname -s)"`
            # at :662 and :755 — without uname both OS branches fall
            # through and the test would pass for the wrong reason).
            assert "Test 21: clean-bin hides setsid (command -v setsid fails under clean PATH)" "! PATH=\"$CLEAN_BIN\" command -v setsid >/dev/null 2>&1"
            UNAME_OUT=$(PATH="$CLEAN_BIN" uname -s 2>/dev/null || echo "")
            assert "Test 21: clean-bin exposes uname returning Linux* (got '${UNAME_OUT}')" "[[ \"$UNAME_OUT\" == Linux* ]]"

            PER_FETCH_TIMEOUT_T21=2
            START=$(date +%s)
            set +e
            # Outer `setsid -w` puts the validator in its own POSIX session
            # so a hypothetical regression of the :765 marker gate
            # (`kill -- -$$` unconditional) only kills the validator's
            # session, not this test runner. `env -u __VC_SETSID_DONE` clears
            # any leaked marker from the parent environment that would
            # otherwise route the validator into the unsafe kill branch.
            # PATH=$CLEAN_BIN strips setsid from the validator's own PATH so
            # `command -v setsid` at :669 fails (the production no-setsid
            # scenario under test). The setsid binary used by the outer
            # wrapper is resolved from the runner's PATH (not the clean-bin).
            __VC_FAKE_CURL="$FAKE_CURL_PIDREC" __VC_LAST_ARGV="$ARGV_LOG" \
            __VC_SKIP_DNS=1 __VC_STUB_RESOLVE='example-hang.invalid=8.8.8.8' \
                setsid -w env -u __VC_SETSID_DONE PATH="$CLEAN_BIN" \
                    "$VALIDATOR" --report "$WORK/c21/report.txt" --output "$WORK/c21/cv.md" \
                                 --tmpdir "$WORK/c21" --budget-seconds 1 \
                                 --per-fetch-timeout "$PER_FETCH_TIMEOUT_T21" >/dev/null 2>&1
            VALIDATOR_RC=$?
            set -e
            END=$(date +%s)
            ELAPSED=$((END - START))
            # The no-setsid Linux branch runs `kill <subshell-pid>` (NOT
            # `kill -- -<pgid>`), so subshells die but their fake-curl
            # children persist as orphans until self-termination via
            # --max-time. Wait per-fetch-timeout + 3 lets all orphans
            # clear before the assertion.
            sleep $((PER_FETCH_TIMEOUT_T21 + 3))
            ORPHAN_COUNT=0
            for pf in "$PIDS_DIR"/*.pid; do
                [[ -e "$pf" ]] || continue
                opid=$(cat "$pf" 2>/dev/null || echo "")
                [[ -z "$opid" ]] && continue
                if kill -0 "$opid" 2>/dev/null; then
                    ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
                fi
            done
            assert "Test 21: validator returned within budget + slack (got ${ELAPSED}s)" "[[ \"$ELAPSED\" -le 15 ]]"
            # Regression-detection assertion: if validate-citations.sh:765
            # is reverted to unconditional `kill -- -$$`, the validator
            # gets SIGTERM under outer setsid, exits 143, and this fails.
            assert "Test 21: validator exited 0 (fail-soft contract on timeout, no-setsid branch)" "[[ \"$VALIDATOR_RC\" -eq 0 ]]"
            assert "Test 21: sidecar produced" "[[ -s \"$WORK/c21/cv.md\" ]]"
            assert "Test 21: sidecar has UNKNOWN | timeout for hung URL #1" "grep -F 'https://example-hang.invalid/page1' \"$WORK/c21/cv.md\" | grep -F 'UNKNOWN' | grep -Fq 'timeout'"
            assert "Test 21: sidecar has UNKNOWN | timeout for hung URL #2" "grep -F 'https://example-hang.invalid/page2' \"$WORK/c21/cv.md\" | grep -F 'UNKNOWN' | grep -Fq 'timeout'"
            assert "Test 21: no orphan fake-curl processes after per-fetch-timeout window (got $ORPHAN_COUNT)" "[[ \"$ORPHAN_COUNT\" == 0 ]]"
        fi
        ;;
    *)
        note "skip: Linux-only (Darwin coverage in Test 20)"
        ;;
esac

# ---------- Summary ----------
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
echo "All assertions passed."
exit 0
