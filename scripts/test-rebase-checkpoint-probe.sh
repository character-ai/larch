#!/usr/bin/env bash
# Offline harness: scripts/rebase-checkpoint-probe.sh (see .md sibling).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID \
    LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_QUIET_BREADCRUMB_FD 2>/dev/null || true

SUT_PROD="$REPO_ROOT/scripts/rebase-checkpoint-probe.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }

[ -x "$SUT_PROD" ] || fail "case 18: production rebase-checkpoint-probe.sh must be executable"

TMPROOT="$(mktemp -d /tmp/larch-test-rebase-probe-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

stage_with_stubs() {
    local d="$1"
    mkdir -p "$d"
    cp "$REPO_ROOT/scripts/rebase-checkpoint-probe.sh" "$d/"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$d/"
    cp "$REPO_ROOT/scripts/lib-phantom-probe.sh" "$d/"
    chmod +x "$d/rebase-checkpoint-probe.sh"
}

write_phantom_clean_stubs() {
    local d="$1"
    cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
    mkdir -p "$TMPROOT/python"
    cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
    chmod +x "$d"/*.sh
}

make_conflict_repo() {
    local repo="$1" path dir base_blob ours_blob theirs_blob zero
    shift
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email t@e
    git -C "$repo" config user.name T
    printf 'base\n' >"$repo/README.md"
    git -C "$repo" add README.md
    git -C "$repo" commit -q -m init
    zero=0000000000000000000000000000000000000000
    while [ "$#" -gt 0 ]; do
        path="$1"
        shift
        dir=${path%/*}
        if [ "$dir" != "$path" ]; then
            mkdir -p "$repo/$dir"
        fi
        base_blob=$(printf 'base %s\n' "$path" | git -C "$repo" hash-object -w --stdin)
        ours_blob=$(printf 'ours %s\n' "$path" | git -C "$repo" hash-object -w --stdin)
        theirs_blob=$(printf 'theirs %s\n' "$path" | git -C "$repo" hash-object -w --stdin)
        printf 'worktree conflict %s\n' "$path" >"$repo/$path"
        {
            printf '0 %s\t%s\n' "$zero" "$path"
            printf '100644 %s 1\t%s\n' "$base_blob" "$path"
            printf '100644 %s 2\t%s\n' "$ours_blob" "$path"
            printf '100644 %s 3\t%s\n' "$theirs_blob" "$path"
        } | git -C "$repo" update-index --index-info
    done
}

IMP_BASE="$TMPROOT/imp"
mkdir -p "$IMP_BASE"
touch "$IMP_BASE/untracked-baseline.z"
touch "$IMP_BASE/execution-issues.md"

# --- Case 1: green ---
d="$TMPROOT/c1"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
print("APPENDED=true")
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" 1.r 'plan materialization' 2>&1) || fail "case1 rc"
echo "$out" | grep -Fq 'REBASE_OUTCOME=ok' || fail "case1 outcome"
echo "$out" | grep -Fq 'ROUTE=continue' || fail "case1 route"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "case1 phantom"
echo "$out" | grep -Fq '→ rebase-probe: 1.r plan materialization' || fail "case1 breadcrumb"

# --- Case 2: pushed before fresh precedence ---
d="$TMPROOT/c2"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'SKIPPED_ALREADY_FRESH=true' 'SKIPPED_ALREADY_PUSHED=true'
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
print("APPENDED=true")
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "case2 rc"
echo "$out" | grep -Fq 'SKIPPED_ALREADY_PUSHED=true' || fail "case2 pushed"
echo "$out" | grep -Fq 'REBASE_OUTCOME=skipped' || fail "case2 skipped"
echo "$out" | grep -Fq 'ROUTE=continue' || fail "case2 route"
if echo "$out" | grep -Fq 'SKIPPED_ALREADY_FRESH=true'; then
    fail "case2 fresh must not emit when pushed wins"
fi

# --- Case 3: fresh only ---
d="$TMPROOT/c3"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo SKIPPED_ALREADY_FRESH=true
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "case3 rc"
echo "$out" | grep -Fq 'SKIPPED_ALREADY_FRESH=true' || fail "case3 fresh"
echo "$out" | grep -Fq 'REBASE_OUTCOME=skipped' || fail "case3 skipped"
echo "$out" | grep -Fq 'ROUTE=continue' || fail "case3 route"

# --- Case 4: conflict + CONFLICT_FILES, no phantom ---
d="$TMPROOT/c4"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo CONFLICT_FILES=a.txt,b.txt
exit 1
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo SHOULD_NOT_RUN=1
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case4 rc=$rc"
echo "$out" | grep -Fq 'REBASE_OUTCOME=conflict' || fail "case4 outcome"
echo "$out" | grep -Fq 'ROUTE=conflict' || fail "case4 route"
echo "$out" | grep -Fq 'CONFLICT_FILES=a.txt,b.txt' || fail "case4 files"
if echo "$out" | grep -Fq 'PHANTOM_STATUS'; then
    fail "case4 phantom must not run"
fi

# --- Case 5: conflict missing CONFLICT_FILES (defensive git diff) ---
d="$TMPROOT/c5"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
set +e
out=$(cd "$REPO_ROOT" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case5 rc=$rc"
echo "$out" | grep -Fq 'REBASE_OUTCOME=conflict' || fail "case5 outcome"
echo "$out" | grep -Fq 'ROUTE=conflict' || fail "case5 route"

# --- Case 6: rc=3 stdout REBASE_ERROR ---
d="$TMPROOT/c6"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo REBASE_ERROR=fetch-failed
exit 3
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case6 rc=$rc"
echo "$out" | grep -Fq 'REBASE_ERROR=fetch-failed' || fail "case6 err"
echo "$out" | grep -Fq 'ROUTE=bail' || fail "case6 route"

# --- Case 7: rc=3 stderr REBASE_ERROR ---
d="$TMPROOT/c7"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'REBASE_ERROR=stderr-err' >&2
exit 3
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case7 rc=$rc"
echo "$out" | grep -Fq 'REBASE_ERROR=stderr-err' || fail "case7 err"
echo "$out" | grep -Fq 'ROUTE=bail' || fail "case7 route"

# --- Case 8: unexpected rc ---
d="$TMPROOT/c8"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 7
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "7" ] || fail "case8 rc=$rc"
echo "$out" | grep -Fq 'REBASE_ERROR=unexpected-rc-7' || fail "case8 unexpected"
echo "$out" | grep -Fq 'ROUTE=bail' || fail "case8 route"

# --- Case 9 (phantom clean) ---
d="$TMPROOT/c9x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c9x"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "c9x status"

# --- Case 10 ---
d="$TMPROOT/c10x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=tracked-only
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c10x"
echo "$out" | grep -Fq 'PHANTOM_STATUS=tracked-only' || fail "c10x"

# --- Case 11 phantom + append ---
d="$TMPROOT/c11x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=phantom
echo PHANTOM_COUNT=1
echo PHANTOM_PATHS_FILE=/tmp/x.z
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
print("FAILED=true")
print("ERROR=cap-test")
raise SystemExit(2)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c11x rc"
echo "$out" | grep -Fq 'PHANTOM_APPEND_WARN_ERROR=cap-test' || fail "c11x append err"

# --- Case 12 unknown append stderr fallback ---
d="$TMPROOT/c12x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=unknown
echo REASON=probe-ambiguous
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
print("some stderr", file=sys.stderr)
raise SystemExit(2)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c12x rc"
echo "$out" | grep -Fq 'PHANTOM_APPEND_WARN_ERROR=' || fail "c12x append fold"

# --- Case 13: base args pass-through ---
d="$TMPROOT/c13"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$(dirname "$0")/rebase.argv"
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" p s --base-remote upstream --base-ref main >/dev/null 2>&1 || fail "c13 rc"
grep -Fq -- '--base-remote' "$d/rebase.argv" || fail "c13 remote"
grep -Fq -- 'upstream' "$d/rebase.argv" || fail "c13 upstream val"
grep -Fq -- '--base-ref' "$d/rebase.argv" || fail "c13 ref flag"
grep -Fq -- 'main' "$d/rebase.argv" || fail "c13 main val"

# --- Case 13b: forked target defaults to upstream/main ---
d="$TMPROOT/c13b"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$(dirname "$0")/rebase.argv"
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" p s --forked-target true >/dev/null 2>&1 || fail "c13b rc"
grep -Fq -- '--base-remote' "$d/rebase.argv" || fail "c13b remote"
grep -Fq -- 'upstream' "$d/rebase.argv" || fail "c13b upstream val"
grep -Fq -- '--base-ref' "$d/rebase.argv" || fail "c13b ref flag"
grep -Fq -- 'main' "$d/rebase.argv" || fail "c13b main val"

# --- Case 14: regex rejection (real rebase-push) ---
gitrepo="$TMPROOT/gitregex"
mkdir -p "$gitrepo"
git -C "$gitrepo" init -q
git -C "$gitrepo" config user.email t@e
git -C "$gitrepo" config user.name T
printf 'x\n' >"$gitrepo/README.md"
git -C "$gitrepo" add README.md
git -C "$gitrepo" commit -q -m init
d="$TMPROOT/c14"
mkdir -p "$d"
cp "$REPO_ROOT/scripts/rebase-checkpoint-probe.sh" "$d/"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$d/"
cp "$REPO_ROOT/scripts/lib-phantom-probe.sh" "$d/"
cp "$REPO_ROOT/scripts/rebase-push.sh" "$d/"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
chmod +x "$d/rebase-push.sh"
set +e
out=$(cd "$gitrepo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y --base-remote 'bad name' 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case14 rc=$rc got $out"
echo "$out" | grep -Fq 'REBASE_OUTCOME=failed' || fail "case14 failed"
echo "$out" | grep -Fq 'ROUTE=bail' || fail "case14 route"
echo "$out" | grep -Fq 'REBASE_ERROR=' || fail "case14 err"

# --- Case 15: breadcrumb count ---
d="$TMPROOT/c15"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" a b 2>&1) || fail "c15"
bc=$(printf '%s\n' "$out" | grep -c '→ rebase-probe:' || true)
[ "$bc" = "1" ] || fail "case15 breadcrumb count=$bc"

# --- Case 16: double-source library ---
d="$TMPROOT/c16"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
mkdir -p "$TMPROOT/python"
cat >"$TMPROOT/python/cli.py" <<'EOF'
import sys
if sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
EOF
chmod +x "$d"/*.sh
bash -c "set -euo pipefail; source \"$d/lib-phantom-probe.sh\"; source \"$d/lib-phantom-probe.sh\"; IMPLEMENT_TMPDIR=\"$IMP_BASE\" \"$d/rebase-checkpoint-probe.sh\" z z" >/dev/null || fail "c16"

# --- Case 17: larch-log-only conflict resolves and exits 0 ---
repo="$TMPROOT/repo17"
make_conflict_repo "$repo" 'larch-logs/implement/run-1/manifest.json'
d="$TMPROOT/c17"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--continue" ]; then
    echo CONTINUE_CALLED=true >"$(dirname "$0")/continue.called"
    exit 0
fi
echo CONFLICT_FILES=larch-logs/implement/run-1/manifest.json
exit 1
EOF
write_phantom_clean_stubs "$d"
set +e
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "0" ] || fail "case17 rc=$rc out=$out"
echo "$out" | grep -Fq 'REBASE_OUTCOME=ok' || fail "case17 outcome"
echo "$out" | grep -Fq 'ROUTE=continue' || fail "case17 route"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "case17 phantom"
[ -f "$d/continue.called" ] || fail "case17 continue not called"
remaining=$(git -C "$repo" diff --name-only --diff-filter=U)
[ -z "$remaining" ] || fail "case17 unmerged=$remaining"

# --- Case 18: consecutive larch-log-only conflicts loop internally ---
repo="$TMPROOT/repo18"
make_conflict_repo "$repo" \
    'larch-logs/implement/run-1/manifest.json' \
    'larch-logs/review/run-2/manifest.json'
d="$TMPROOT/c18"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
state="$(dirname "$0")/continue-count"
if [ "${1:-}" = "--continue" ]; then
    n=0
    [ -f "$state" ] && n=$(cat "$state")
    n=$((n + 1))
    echo "$n" >"$state"
    if [ "$n" -eq 1 ]; then
        echo CONFLICT_FILES=larch-logs/review/run-2/manifest.json
        exit 1
    fi
    exit 0
fi
echo CONFLICT_FILES=larch-logs/implement/run-1/manifest.json
exit 1
EOF
write_phantom_clean_stubs "$d"
set +e
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "0" ] || fail "case18 rc=$rc out=$out"
[ "$(cat "$d/continue-count")" = "2" ] || fail "case18 continue count"
echo "$out" | grep -Fq 'REBASE_OUTCOME=ok' || fail "case18 outcome"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "case18 phantom"
remaining=$(git -C "$repo" diff --name-only --diff-filter=U)
[ -z "$remaining" ] || fail "case18 unmerged=$remaining"

# --- Case 19: mixed conflict resolves trivial subset only ---
repo="$TMPROOT/repo19"
make_conflict_repo "$repo" \
    'larch-logs/implement/run-1/manifest.json' \
    'python/stall_recovery.py'
d="$TMPROOT/c19"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--continue" ]; then
    echo SHOULD_NOT_CONTINUE=true >"$(dirname "$0")/continue.called"
    exit 0
fi
echo CONFLICT_FILES=larch-logs/implement/run-1/manifest.json,python/stall_recovery.py
exit 1
EOF
write_phantom_clean_stubs "$d"
set +e
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case19 rc=$rc out=$out"
echo "$out" | grep -Fq 'REBASE_OUTCOME=conflict' || fail "case19 outcome"
echo "$out" | grep -Fq 'CONFLICT_FILES=python/stall_recovery.py' || fail "case19 files"
if echo "$out" | grep -Fq 'PHANTOM_STATUS'; then
    fail "case19 phantom must not run"
fi
[ ! -f "$d/continue.called" ] || fail "case19 continue must not run"
remaining=$(git -C "$repo" diff --name-only --diff-filter=U)
[ "$remaining" = "python/stall_recovery.py" ] || fail "case19 unmerged=$remaining"

# --- Case 20: trivial conflict followed by non-trivial continue conflict ---
repo="$TMPROOT/repo20"
make_conflict_repo "$repo" \
    'larch-logs/implement/run-1/manifest.json' \
    'agent-lint.toml'
d="$TMPROOT/c20"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--continue" ]; then
    echo CONFLICT_FILES=agent-lint.toml
    exit 1
fi
echo CONFLICT_FILES=larch-logs/implement/run-1/manifest.json
exit 1
EOF
write_phantom_clean_stubs "$d"
set +e
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case20 rc=$rc out=$out"
echo "$out" | grep -Fq 'CONFLICT_FILES=agent-lint.toml' || fail "case20 files"
if echo "$out" | grep -Fq 'PHANTOM_STATUS'; then
    fail "case20 phantom must not run"
fi

# --- Case 21: trivial conflict with continue failure ---
repo="$TMPROOT/repo21"
make_conflict_repo "$repo" 'larch-logs/implement/run-1/manifest.json'
d="$TMPROOT/c21"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--continue" ]; then
    echo REBASE_ERROR=continue-failed
    exit 3
fi
echo CONFLICT_FILES=larch-logs/implement/run-1/manifest.json
exit 1
EOF
write_phantom_clean_stubs "$d"
set +e
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case21 rc=$rc out=$out"
echo "$out" | grep -Fq 'REBASE_OUTCOME=failed' || fail "case21 failed"
echo "$out" | grep -Fq 'REBASE_ERROR=continue-failed' || fail "case21 err"
echo "$out" | grep -Fq 'ROUTE=bail' || fail "case21 route"

# --- Case 22: resolve command failure re-derives CONFLICT_FILES ---
repo="$TMPROOT/repo22"
make_conflict_repo "$repo" \
    'larch-logs/implement/run-1/one.json' \
    'larch-logs/implement/run-1/two.json'
d="$TMPROOT/c22"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo CONFLICT_FILES=larch-logs/implement/run-1/one.json,larch-logs/implement/run-1/two.json
exit 1
EOF
write_phantom_clean_stubs "$d"
fakebin="$TMPROOT/fakegit22"
mkdir -p "$fakebin"
real_git=$(command -v git)
cat >"$fakebin/git" <<EOF
#!/usr/bin/env bash
if [ "\$1" = "checkout" ] && [ "\$2" = "--ours" ] && [ "\$3" = "--" ] && [ "\$4" = "larch-logs/implement/run-1/two.json" ]; then
    exit 42
fi
if [ "\$1" = "rm" ] && [ "\$2" = "-f" ] && [ "\$3" = "--" ] && [ "\$4" = "larch-logs/implement/run-1/two.json" ]; then
    exit 42
fi
exec "$real_git" "\$@"
EOF
chmod +x "$fakebin/git"
set +e
out=$(cd "$repo" && PATH="$fakebin:$PATH" IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case22 rc=$rc out=$out"
echo "$out" | grep -Fq 'CONFLICT_FILES=larch-logs/implement/run-1/two.json' || fail "case22 files"
if echo "$out" | grep -Fq 'CONFLICT_FILES=larch-logs/implement/run-1/one.json,larch-logs/implement/run-1/two.json'; then
    fail "case22 stale conflict list"
fi

# --- Case 23: empty CONFLICT_FILES on rc=1 skips loop ---
repo="$TMPROOT/repo23"
mkdir -p "$repo"
git -C "$repo" init -q
git -C "$repo" config user.email t@e
git -C "$repo" config user.name T
printf 'base\n' >"$repo/README.md"
git -C "$repo" add README.md
git -C "$repo" commit -q -m init
d="$TMPROOT/c23"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--continue" ]; then
    echo SHOULD_NOT_CONTINUE=true >"$(dirname "$0")/continue.called"
    exit 0
fi
exit 1
EOF
write_phantom_clean_stubs "$d"
set +e
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case23 rc=$rc out=$out"
echo "$out" | grep -Fq 'REBASE_OUTCOME=conflict' || fail "case23 outcome"
echo "$out" | grep -Fxq 'CONFLICT_FILES=' || fail "case23 empty files"
[ ! -f "$d/continue.called" ] || fail "case23 continue must not run"

echo "PASS: test-rebase-checkpoint-probe.sh"
exit 0
