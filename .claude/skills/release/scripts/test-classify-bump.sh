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

# Test 2: larch-log flush above bump is transparent.
repo="$TMPDIR_BASE/test2"
setup_repo "$repo"
printf '{"version":"1.2.3"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.2.3"
mkdir -p "$repo/larch-logs/implement/run-1"
printf '{}\n' > "$repo/larch-logs/implement/run-1/manifest.json"
git -C "$repo" add larch-logs/implement/run-1/manifest.json
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run run-1"
out=$(run_subject "$repo" "$TMPDIR_BASE/t2impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=NONE$'; then
    ok
else
    fail "HEAD larch-log flush over bump should be NONE: $out"
fi

# Test 3: CHANGELOG update above bump is transparent.
repo="$TMPDIR_BASE/test3"
setup_repo "$repo"
printf '{"version":"1.2.3"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.2.3"
printf '# Changelog\n\n- 1.2.3\n' > "$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m "Update CHANGELOG for 1.2.3"
out=$(run_subject "$repo" "$TMPDIR_BASE/t3impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=NONE$'; then
    ok
else
    fail "HEAD CHANGELOG update over bump should be NONE: $out"
fi

# Test 4: CHANGELOG-subject spoofing cannot hide a public-surface change.
repo="$TMPDIR_BASE/test4"
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
out=$(run_subject "$repo" "$TMPDIR_BASE/t4impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=MINOR$'; then
    ok
else
    fail "CHANGELOG-subject spoof touching skills should be MINOR: $out"
fi

# Test 5: larch-log subject spoofing cannot bypass a public-surface change.
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
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run run-1"
out=$(run_subject "$repo" "$TMPDIR_BASE/t5impl")
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=MINOR$'; then
    ok
else
    fail "larch-log subject spoof touching skills should be MINOR: $out"
fi

# Test 6: --base skips idempotency over a trailing bump commit.
repo="$TMPDIR_BASE/test6"
setup_repo "$repo"
git -C "$repo" checkout -q main 2>/dev/null || git -C "$repo" checkout -q -b main
git -C "$repo" tag -a v1.0.0 -m "baseline" "$(git -C "$repo" rev-parse HEAD)"
mkdir -p "$repo/skills/extra"
cat > "$repo/skills/extra/SKILL.md" <<'SKILL'
---
name: extra
description: extra skill
---
SKILL
git -C "$repo" add skills/extra/SKILL.md
git -C "$repo" commit -q -m "Add extra skill (#99)"
printf '{"version":"1.0.1"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.0.1"
echo tweak >> "$repo/skills/extra/SKILL.md"
git -C "$repo" add skills/extra/SKILL.md
git -C "$repo" commit -q -m "Tweak extra (#100)"
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$TMPDIR_BASE/t6impl" bash "$SUBJECT" --base v1.0.0 2>/dev/null)
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=MINOR$'; then
    ok
else
    fail "--base over trailing bump should be MINOR: $out"
fi

# Test 7: --head origin/main excludes commits not on origin/main.
repo="$TMPDIR_BASE/test7"
bare="$TMPDIR_BASE/test7-bare.git"
git init -q --bare "$bare"
setup_repo "$repo"
git -C "$repo" remote add origin "$bare"
git -C "$repo" push -q -u origin main
git -C "$repo" tag -a v1.0.0 -m "baseline" "$(git -C "$repo" rev-parse HEAD)"
git -C "$repo" push -q origin v1.0.0
mkdir -p "$repo/skills/local-only"
cat > "$repo/skills/local-only/SKILL.md" <<'SKILL'
---
name: local-only
description: local only
---
SKILL
git -C "$repo" add skills/local-only/SKILL.md
git -C "$repo" commit -q -m "Local-only skill (#42)"
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$TMPDIR_BASE/t7impl" bash "$SUBJECT" --base v1.0.0 --head origin/main 2>/dev/null)
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=PATCH$'; then
    ok
else
    fail "--head origin/main should ignore local-only commit (expect PATCH): $out"
fi

# Test 8: --head anchors idempotency walk on the supplied ref, not local HEAD.
repo="$TMPDIR_BASE/test8"
bare="$TMPDIR_BASE/test8-bare.git"
git init -q --bare "$bare"
setup_repo "$repo"
git -C "$repo" remote add origin "$bare"
git -C "$repo" push -q -u origin main
printf '{"version":"1.2.3"}\n' > "$repo/.claude-plugin/plugin.json"
git -C "$repo" add .claude-plugin/plugin.json
git -C "$repo" commit -q -m "Bump version to 1.2.3"
git -C "$repo" push -q origin feature:main
echo local >> "$repo/README.md"
git -C "$repo" add README.md
git -C "$repo" commit -q -m "Local-only docs (#43)"
out=$(cd "$repo" && IMPLEMENT_TMPDIR="$TMPDIR_BASE/t8impl" bash "$SUBJECT" --head origin/main 2>/dev/null)
if printf '%s\n' "$out" | grep -q '^BUMP_TYPE=NONE$'; then
    ok
else
    fail "--head origin/main should treat origin/main bump as idempotent: $out"
fi

# Test 9: default path emits required KV lines; unknown args fail closed.
repo="$TMPDIR_BASE/test9"
setup_repo "$repo"
out=$(run_subject "$repo" "$TMPDIR_BASE/t9impl")
if printf '%s\n' "$out" | grep -q '^CURRENT_VERSION=' \
  && printf '%s\n' "$out" | grep -q '^NEW_VERSION=' \
  && printf '%s\n' "$out" | grep -qE '^BUMP_TYPE=(MAJOR|MINOR|PATCH|NONE)$' \
  && printf '%s\n' "$out" | grep -q '^REASONING_FILE='; then
    ok
else
    fail "default path KV shape: $out"
fi
set +e
(cd "$repo" && IMPLEMENT_TMPDIR="$TMPDIR_BASE/t9bad" bash "$SUBJECT" --bogus >/dev/null 2>&1)
bad_rc=$?
set -e
if [[ $bad_rc -ne 0 ]]; then
    ok
else
    fail "unknown argument should exit non-zero"
fi

total=$((PASS + FAIL))
echo "test-classify-bump: $PASS/$total passed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
