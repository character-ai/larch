#!/usr/bin/env bash
# test-drop-changelog-commit.sh — Offline regression harness for
# drop-changelog-commit.sh. Mirrors test-drop-bump-commit.sh's structure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DROP_SCRIPT="$SCRIPT_DIR/drop-changelog-commit.sh"

PASS=0
FAIL=0
TMPDIR_BASE=""

cleanup() {
    [[ -n "$TMPDIR_BASE" && -d "$TMPDIR_BASE" ]] && rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

TMPDIR_BASE=$(mktemp -d)

# Helper: fresh repo + initial commit + an "Update CHANGELOG for VERSION" commit
# touching exactly the supplied files.
# Usage: setup_repo <repo> <version> [file ...] (defaults to CHANGELOG.md)
setup_repo() {
    local repo_dir="$1" version="$2"; shift 2
    local files=("$@")
    [[ ${#files[@]} -eq 0 ]] && files=("CHANGELOG.md")

    mkdir -p "$repo_dir"
    cd "$repo_dir"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"

    mkdir -p .claude-plugin
    echo '{}' > .claude-plugin/plugin.json
    printf '## [Unreleased]\n\n## [0.0.0] - 2020-01-01\n' > CHANGELOG.md
    git add -A
    git commit -q -m "Initial commit"

    local f
    for f in "${files[@]}"; do
        local dir
        dir=$(dirname "$f")
        [[ "$dir" != "." ]] && mkdir -p "$dir"
        printf '## [Unreleased]\n\n## [%s] - 2026-05-26\n\n### Changed\n\n- bullet\n' "$version" > "$f"
    done
    git add -A
    git commit -q -m "Update CHANGELOG for $version"
}

run_test() {
    local test_name="$1" expected="$2" version="$3"
    shift 3
    local extra_args=("$@")
    local output actual

    output=$(bash "$DROP_SCRIPT" --version "$version" "${extra_args[@]+"${extra_args[@]}"}" 2>/dev/null) || true
    actual=$(echo "$output" | grep "^DROPPED=" | head -1 | cut -d= -f2)
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name — expected DROPPED=$expected, got DROPPED=$actual" >&2
        FAIL=$((FAIL + 1))
    fi
}

# --- Basic happy path ---
REPO="$TMPDIR_BASE/test-happy"
setup_repo "$REPO" "1.2.3"
run_test "CHANGELOG-only commit at HEAD → DROPPED=true" "true" "1.2.3"

# --- Wrong version: no matching commit ---
REPO="$TMPDIR_BASE/test-wrong-version"
setup_repo "$REPO" "1.2.3"
run_test "Wrong version → DROPPED=false" "false" "9.9.9"

# --- Guard 4: extra file touched ---
REPO="$TMPDIR_BASE/test-extra-file"
setup_repo "$REPO" "1.2.4" CHANGELOG.md README.md
run_test "Extra file in diff → DROPPED=false" "false" "1.2.4"

# --- Guard 4: wrong file touched ---
REPO="$TMPDIR_BASE/test-wrong-file"
setup_repo "$REPO" "1.2.5" README.md
run_test "CHANGELOG.md absent → DROPPED=false" "false" "1.2.5"

# --- Walk-back: commit not at HEAD ---
REPO="$TMPDIR_BASE/test-walkback"
setup_repo "$REPO" "1.2.6"
cd "$REPO"
mkdir -p larch-logs
echo "noop" > larch-logs/noop.txt
git add -A
git commit -q -m "chore: noop above changelog"
run_test "Walk-back finds commit at HEAD~1 → DROPPED=true" "true" "1.2.6"

# --- Walk-back depth: exceed max-depth ---
REPO="$TMPDIR_BASE/test-depth"
setup_repo "$REPO" "1.2.7"
cd "$REPO"
for i in 1 2 3; do
    echo "noop$i" > "noop$i.txt"
    git add -A
    git commit -q -m "chore: noop $i"
done
run_test "max-depth too low → DROPPED=false" "false" "1.2.7" --max-depth 2
run_test "max-depth sufficient → DROPPED=true" "true" "1.2.7" --max-depth 10

# --- Untracked file is OK (Guard 1 only checks tracked) ---
REPO="$TMPDIR_BASE/test-untracked"
setup_repo "$REPO" "1.2.8"
cd "$REPO"
echo "pending" > "untracked.txt"
run_test "Untracked file present → DROPPED=true" "true" "1.2.8"

# --- Dirty tracked file refuses (Guard 1) ---
REPO="$TMPDIR_BASE/test-dirty"
setup_repo "$REPO" "1.2.9"
cd "$REPO"
echo "modified" >> CHANGELOG.md
run_test "Dirty tracked file → DROPPED=false" "false" "1.2.9"

# --- Bad version flag ---
REPO="$TMPDIR_BASE/test-bad-version"
setup_repo "$REPO" "1.2.10"
run_test "Bad version → DROPPED=false" "false" "not-a-version"

# --- After drop, subsequent commits are preserved (walk-back integrity) ---
REPO="$TMPDIR_BASE/test-preserve"
setup_repo "$REPO" "1.2.11"
cd "$REPO"
echo "preserve me" > "preserve.txt"
git add -A
git commit -q -m "chore: preserve me"
output=$(bash "$DROP_SCRIPT" --version "1.2.11" 2>/dev/null) || true
if [[ "$(echo "$output" | grep "^DROPPED=" | cut -d= -f2)" == "true" ]]; then
    if git log -1 --format=%s HEAD | grep -q "^chore: preserve me$"; then
        if ! git log --format=%s HEAD | grep -q "^Update CHANGELOG for 1.2.11$"; then
            PASS=$((PASS + 1))
        else
            echo "FAIL: walk-back integrity — Update CHANGELOG commit still present" >&2
            FAIL=$((FAIL + 1))
        fi
    else
        echo "FAIL: walk-back integrity — preserve commit was lost" >&2
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: walk-back integrity — DROPPED was not true" >&2
    FAIL=$((FAIL + 1))
fi

# --- Bullets-extract sibling lib helper: changelog_extract_version_body ---
# Standalone smoke for the lib function used by ship-pr.sh.
REPO="$TMPDIR_BASE/test-extract"
mkdir -p "$REPO"
cd "$REPO"
cat > CHANGELOG.md <<'EOF'
## [Unreleased]

## [1.2.12] - 2026-05-26

### Changed

- Add foo
- Update bar

## [1.2.11] - 2026-05-25

### Fixed

- Earlier
EOF
# shellcheck source=scripts/lib-changelog.sh
source "$SCRIPT_DIR/lib-changelog.sh"
extract_out="$REPO/extract.out"
if changelog_extract_version_body "1.2.12" "$extract_out" CHANGELOG.md; then
    expected="### Changed

- Add foo
- Update bar"
    actual=$(cat "$extract_out")
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: changelog_extract_version_body content mismatch" >&2
        echo "EXPECTED:" >&2
        printf '%s\n' "$expected" >&2
        echo "ACTUAL:" >&2
        printf '%s\n' "$actual" >&2
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: changelog_extract_version_body returned non-zero for present version" >&2
    FAIL=$((FAIL + 1))
fi

# Missing version → returns 1
if changelog_extract_version_body "9.9.9" "$extract_out" CHANGELOG.md; then
    echo "FAIL: changelog_extract_version_body did not refuse missing version" >&2
    FAIL=$((FAIL + 1))
else
    PASS=$((PASS + 1))
fi

if [[ "$FAIL" -gt 0 ]]; then
    echo "drop-changelog-commit harness FAIL: pass=$PASS fail=$FAIL" >&2
    exit 1
fi
echo "drop-changelog-commit harness OK: pass=$PASS"
