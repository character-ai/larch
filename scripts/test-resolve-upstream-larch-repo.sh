#!/usr/bin/env bash
# test-resolve-upstream-larch-repo.sh — offline harness for resolve-upstream-larch-repo.sh

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT="$SCRIPT_DIR/resolve-upstream-larch-repo.sh"
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-resolve-upstream.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$*" | sed 's/^/    /'; }

make_plugin() {
    local dir=$1 value=${2-__missing__}
    mkdir -p "$dir/.claude-plugin"
    if [ "$value" = __missing__ ]; then
        printf '{}\n' >"$dir/.claude-plugin/plugin.json"
    else
        python3 - "$dir/.claude-plugin/plugin.json" "$value" <<'PY'
import json, sys
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump({"repository": sys.argv[2]}, fh)
    fh.write("\n")
PY
    fi
}

run_case() {
    local name=$1 value=$2 expected=$3 dir out err rc
    dir="$TMPROOT/$name"
    make_plugin "$dir" "$value"
    cp "$SCRIPT" "$dir/resolve-upstream-larch-repo.sh"
    mkdir -p "$dir/scripts"
    mv "$dir/resolve-upstream-larch-repo.sh" "$dir/scripts/resolve-upstream-larch-repo.sh"
    chmod +x "$dir/scripts/resolve-upstream-larch-repo.sh"
    set +e
    out=$(cd "$dir" && ./scripts/resolve-upstream-larch-repo.sh 2>"$dir/err")
    rc=$?
    set -e
    err=$(cat "$dir/err")
    if [ "$rc" -eq 0 ] && [ "$out" = "$expected" ] && [ -z "$err" ]; then
        pass "$name"
    else
        fail "$name" "rc=$rc out=$out err=$err"
    fi
}

run_reject() {
    local name=$1 value=${2-__missing__} dir out rc
    dir="$TMPROOT/$name"
    make_plugin "$dir" "$value"
    cp "$SCRIPT" "$dir/resolve-upstream-larch-repo.sh"
    mkdir -p "$dir/scripts"
    mv "$dir/resolve-upstream-larch-repo.sh" "$dir/scripts/resolve-upstream-larch-repo.sh"
    chmod +x "$dir/scripts/resolve-upstream-larch-repo.sh"
    set +e
    out=$(cd "$dir" && ./scripts/resolve-upstream-larch-repo.sh 2>"$dir/err")
    rc=$?
    set -e
    if [ "$rc" -ne 0 ] && [ -z "$out" ] && [ -s "$dir/err" ]; then
        pass "$name"
    else
        fail "$name" "rc=$rc out=$out err=$(cat "$dir/err")"
    fi
}

run_case https-url 'https://github.com/character-ai/larch' 'character-ai/larch'
run_case ssh-url 'git@github.com:character-ai/larch.git' 'character-ai/larch'
run_case ssh-scheme-url 'ssh://git@github.com/character-ai/larch.git' 'character-ai/larch'
run_case plain-owner-repo 'character-ai/larch' 'character-ai/larch'
run_case git-suffix 'https://github.com/character-ai/larch.git' 'character-ai/larch'
run_case git-plus-https 'git+https://github.com/character-ai/larch.git' 'character-ai/larch'
run_reject missing-repository
run_reject non-github 'https://example.com/character-ai/larch'
run_reject malformed-owner '../larch'
run_reject malformed-repo 'character-ai/../larch'
run_reject trailing-newline $'https://github.com/character-ai/larch\n'
run_reject newline-injection $'https://github.com/character-ai/larch\nother/repo'

if [ "$FAIL" -ne 0 ]; then
    echo "FAILURES: $FAIL"
    exit 1
fi
echo "PASS: $PASS"
