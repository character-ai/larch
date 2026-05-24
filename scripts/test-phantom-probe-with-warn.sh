#!/usr/bin/env bash
# Offline harness: scripts/phantom-probe-with-warn.sh (see .md sibling).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
export LARCH_QUIET_BREADCRUMBS=1

PROD="$REPO_ROOT/scripts/phantom-probe-with-warn.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }

[ -x "$PROD" ] || fail "case9: production phantom-probe-with-warn.sh must be executable"

TMPROOT="$(mktemp -d /tmp/larch-test-phantom-wrap-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

stage() {
    local d="$1"
    mkdir -p "$d"
    cp "$REPO_ROOT/scripts/phantom-probe-with-warn.sh" "$d/"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$d/"
    cp "$REPO_ROOT/scripts/lib-phantom-probe.sh" "$d/"
    chmod +x "$d/phantom-probe-with-warn.sh"
}

IMP="$TMPROOT/imp"
mkdir -p "$IMP"
touch "$IMP/untracked-baseline.z"
touch "$IMP/execution-issues.md"

# 1 clean
d="$TMPROOT/w1"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step s1 2>&1) || fail "w1"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "w1 status"

# 2 tracked-only
d="$TMPROOT/w2"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=tracked-only
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step s2 2>&1) || fail "w2"
echo "$out" | grep -Fq 'PHANTOM_STATUS=tracked-only' || fail "w2"

# 3 phantom + append ok
d="$TMPROOT/w3"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=phantom
echo PHANTOM_COUNT=3
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
echo APPENDED=true
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step s3 2>&1) || fail "w3"
echo "$out" | grep -Fq 'PHANTOM_STATUS=phantom' || fail "w3 st"
echo "$out" | grep -Fq 'PHANTOM_COUNT=3' || fail "w3 cnt"

# 4 unknown + append ok
d="$TMPROOT/w4"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=unknown
echo REASON=r1
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step s4 2>&1) || fail "w4"
echo "$out" | grep -Fq 'PHANTOM_STATUS=unknown' || fail "w4"

# 5 append failure ERROR= stdout
d="$TMPROOT/w5"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=phantom
echo PHANTOM_COUNT=1
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
echo FAILED=true
echo ERROR=stdout-err
exit 2
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step s5 2>&1) || fail "w5"
echo "$out" | grep -Fq 'PHANTOM_APPEND_WARN_ERROR=stdout-err' || fail "w5 err"

# 6 append failure stderr only
d="$TMPROOT/w6"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=unknown
echo REASON=u1
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'tail-err' >&2
exit 2
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step s6 2>&1) || fail "w6"
echo "$out" | grep -Fq 'PHANTOM_APPEND_WARN_ERROR=' || fail "w6 fold"

# 7 breadcrumb count
d="$TMPROOT/w7"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step bc-step 2>&1) || fail "w7"
n=$(printf '%s\n' "$out" | grep -c '→ phantom-probe:' || true)
[ "$n" = "1" ] || fail "w7 breadcrumb n=$n"

# 8 bad step — real check-phantom-dirty rejects token
d="$TMPROOT/w8"
stage "$d"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$d/"
cp "$REPO_ROOT/scripts/check-phantom-dirty.sh" "$d/"
chmod +x "$d/check-phantom-dirty.sh"
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP" "$d/phantom-probe-with-warn.sh" --step 'bad!step' 2>&1) || fail "w8"
echo "$out" | grep -Fq 'PHANTOM_STATUS=unknown' || fail "w8"
echo "$out" | grep -Fq 'bad-step' || fail "w8 reason"

# 10 double-source lib then run
d="$TMPROOT/w10"
stage "$d"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
bash -c "set -euo pipefail; source \"$d/lib-phantom-probe.sh\"; source \"$d/lib-phantom-probe.sh\"; IMPLEMENT_TMPDIR=\"$IMP\" \"$d/phantom-probe-with-warn.sh\" --step z99" >/dev/null || fail "w10"

echo "PASS: test-phantom-probe-with-warn.sh"
exit 0
