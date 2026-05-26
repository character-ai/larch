#!/usr/bin/env bash
# test-classify-bump.sh — Offline harness for classify-bump.sh idempotency edges.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/classify-bump.sh"

PASS=0
FAIL=0
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

ok() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $*" >&2; FAIL=$((FAIL + 1)); }

run_subject() {
    local repo=$1 tmpdir=$2
    (cd "$repo" && IMPLEMENT_TMPDIR="$tmpdir" bash "$SUBJECT" 2>/dev/null) || true
}

setup_repo() {
    local repo=$1
    mkdir -p "$repo/.claude-plugin" "$repo/skills/base"
    git -C "$repo" init -q -b main
    git -C "$repo" config user.email test@test.com
    git -C "$repo" config user.name Test
    cat > "$repo/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.2"}
JSON
    cat > "$repo/skills/base/SKILL.md" <<'SKILL'
---
name: base
description: base
---
SKILL
    cat > "$repo/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [1.2.2] - 2026-01-01

### Fixed

- Base entry.
CHANGELOG
    echo "base" > "$repo/README.md"
    git -C "$repo" add -A
    git -C "$repo" commit -q -m "Initial commit"
    git -C "$repo" checkout -q -b feature
}

# Test 1: HEAD bump commit is idempotent NONE.
repo="$TMPDIR_BASE/test1"
setup_repo "$repo"
printf '{"version":"1.2.3"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.2.3"
out=$(run_subject "$repo" "$TMPDIR_BASE/t1impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=NONE$'; then
    ok
else
    fail "HEAD bump commit should be NONE: $out"
fi

# Test 2: CHANGELOG-only commit above bump is transparent.
repo="$TMPDIR_BASE/test2"
setup_repo "$repo"
printf '{"version":"1.2.3"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.2.3"
printf '\n- New fix.\n' >> "$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m "Update CHANGELOG for 1.2.3"
out=$(run_subject "$repo" "$TMPDIR_BASE/t2impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=NONE$'; then
    ok
else
    fail "HEAD CHANGELOG over bump should be NONE: $out"
fi

# Test 3: larch-log flush above CHANGELOG above bump is also transparent.
repo="$TMPDIR_BASE/test3"
setup_repo "$repo"
printf '{"version":"1.2.3"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.2.3"
printf '\n- New fix.\n' >> "$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m "Update CHANGELOG for 1.2.3"
mkdir -p "$repo/larch-logs/implement/run-1"
printf '{}\n' > "$repo/larch-logs/implement/run-1/manifest.json"
git -C "$repo" add larch-logs/implement/run-1/manifest.json
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run run-1"
out=$(run_subject "$repo" "$TMPDIR_BASE/t3impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=NONE$'; then
    ok
else
    fail "HEAD larch-log flush over CHANGELOG over bump should be NONE: $out"
fi

# Test 4: CHANGELOG-at-HEAD over ordinary feature work still needs a bump.
repo="$TMPDIR_BASE/test4"
setup_repo "$repo"
echo "feature" >> "$repo/README.md"
git -C "$repo" add README.md
git -C "$repo" commit -q -m "Feature work"
printf '\n- Feature note.\n' >> "$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m "Update CHANGELOG for 1.2.3"
out=$(run_subject "$repo" "$TMPDIR_BASE/t4impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=PATCH$'; then
    ok
else
    fail "HEAD CHANGELOG over feature should be PATCH, got: $out"
fi

# Test 5: Subject-only spoofing cannot bypass a public-surface change.
repo="$TMPDIR_BASE/test5"
setup_repo "$repo"
mkdir -p "$repo/skills/new-skill"
cat > "$repo/skills/new-skill/SKILL.md" <<'SKILL'
---
name: new-skill
description: new skill
---
SKILL
git -C "$repo" add skills/new-skill/SKILL.md
git -C "$repo" commit -q -m "Update CHANGELOG for 1.2.3"
out=$(run_subject "$repo" "$TMPDIR_BASE/t5impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=MINOR$'; then
    ok
else
    fail "forged CHANGELOG subject touching skills should be MINOR: $out"
fi

total=$((PASS + FAIL))
echo "test-classify-bump: $PASS/$total passed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
