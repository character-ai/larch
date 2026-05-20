#!/usr/bin/env bash
# test-auto-resolve-changelog.sh — Regression harness for auto-resolve-changelog.sh.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/auto-resolve-changelog.sh"
TMP_BASE="$(mktemp -d "${TMPDIR:-/tmp}/larch-arv-test.XXXXXX")"
trap 'rm -rf "$TMP_BASE"' EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "PASS: $1"; }

run_arv() {
    local repo=$1 path=${2:-CHANGELOG.md}
    (cd "$repo" && "$SCRIPT" "$path")
}

# --- Two distinct Unreleased entries merge; tail from upstream preserved ---
repo="$TMP_BASE/two-entries"
mkdir -p "$repo"
git -C "$repo" init -q
git -C "$repo" config user.email t@e.invalid
git -C "$repo" config user.name T
git -C "$repo" checkout -b main -q
cat >"$repo/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet

## [1.0.0]

### Fixed

- Old
EOF
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m base
mkdir -p "$repo/origin.git"
git init --bare "$repo/origin.git" -q
git -C "$repo" remote add origin "$repo/origin.git"
git -C "$repo" push -q -u origin main
git -C "$repo" checkout -b feature -q
cat >"$repo/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet
- Branch bullet

## [1.0.0]

### Fixed

- Old
EOF
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m feature
git -C "$repo" checkout main -q
cat >"$repo/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet
- Mainline bullet

## [1.0.0]

### Fixed

- Old
EOF
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m advance-main
git -C "$repo" push -q origin main
git -C "$repo" checkout feature -q
set +e
git -C "$repo" rebase origin/main >/dev/null 2>&1
rb=$?
set -e
[[ "$rb" != 0 ]] || fail "expected rebase conflict"
run_arv "$repo" CHANGELOG.md
grep -q -- '- Mainline bullet' "$repo/CHANGELOG.md" || fail "missing upstream-only bullet"
grep -q -- '- Branch bullet' "$repo/CHANGELOG.md" || fail "missing branch-only bullet"
grep -q -- '## \[1.0.0\]' "$repo/CHANGELOG.md" || fail "missing version tail"
pass "merges distinct Unreleased bullets and keeps upstream tail"

# --- Same line in both sides deduped ---
repo="$TMP_BASE/dedupe"
mkdir -p "$repo"
git -C "$repo" init -q
git -C "$repo" config user.email t@e.invalid
git -C "$repo" config user.name T
git -C "$repo" checkout -b main -q
printf '%s\n' '# C' '' '## Unreleased' '- Same' '## [1.0.0]' 'x' >"$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md && git -C "$repo" commit -q -m a
mkdir -p "$repo/o.git" && git init --bare "$repo/o.git" -q
git -C "$repo" remote add origin "$repo/o.git" && git -C "$repo" push -q -u origin main
git -C "$repo" checkout -b feature -q
printf '%s\n' '# C' '' '## Unreleased' '- Same' '- OnlyBranch' '## [1.0.0]' 'x' >"$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md && git -C "$repo" commit -q -m b
git -C "$repo" checkout main -q
printf '%s\n' '# C' '' '## Unreleased' '- Same' '- OnlyMain' '## [1.0.0]' 'x' >"$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md && git -C "$repo" commit -q -m c
git -C "$repo" push -q origin main && git -C "$repo" checkout feature -q
set +e
git -C "$repo" rebase origin/main >/dev/null 2>&1
set -e
run_arv "$repo"
c=$(grep -c -- '- Same' "$repo/CHANGELOG.md" || true)
[[ "$c" == 1 ]] || fail "expected exactly one - Same line, got $c"
pass "dedupes identical entry line"

# --- No heading → exit 1 ---
repo="$TMP_BASE/no-head"
mkdir -p "$repo"
git -C "$repo" init -q
git -C "$repo" config user.email t@e.invalid
git -C "$repo" config user.name T
printf 'plain\n' >"$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md && git -C "$repo" commit -q -m only
git -C "$repo" checkout -b alt -q
printf 'other\n' >"$repo/CHANGELOG.md"
git -C "$repo" add CHANGELOG.md && git -C "$repo" commit -q -m alt
set +e
git -C "$repo" rebase main >/dev/null 2>&1
set -e
set +e
run_arv "$repo"
rc=$?
set -e
[[ "$rc" == 1 ]] || fail "no heading expected exit 1, got $rc"
pass "exits 1 when no ## heading"

echo "test-auto-resolve-changelog: all checks passed"
