#!/usr/bin/env bash
# test-lint-literal-counts.sh - Regression harness for scripts/lint-literal-counts.py.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LINT="$REPO_ROOT/scripts/lint-literal-counts.py"

if [[ ! -f "$LINT" ]]; then
    echo "ERROR: lint script not found: $LINT" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: python3 not on PATH" >&2
    exit 1
fi

TMPROOT=$(mktemp -d -t lint-literal-counts-test-XXXXXX)
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

assert_case() {
    local label="$1" expected_exit="$2" stderr_file="$3" exit_code="$4"
    shift 4
    if [[ "$exit_code" -ne "$expected_exit" ]]; then
        echo "FAIL [$label]: expected exit $expected_exit, got $exit_code" >&2
        echo "--- stderr ---" >&2
        cat "$stderr_file" >&2
        echo "--------------" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if ! grep -Fq "$needle" "$stderr_file"; then
            echo "FAIL [$label]: stderr missing expected needle: $needle" >&2
            echo "--- stderr ---" >&2
            cat "$stderr_file" >&2
            echo "--------------" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    PASS=$((PASS + 1))
    echo "PASS [$label]"
}

write_md() {
    local path="$1"
    mkdir -p "$(dirname "$path")"
    cat > "$path"
}

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

run_lint() {
    local stderr_file="$1"
    set +e
    python3 "$LINT" --root "$TMPROOT" 2>"$stderr_file"
    local rc=$?
    set -e
    echo "$rc"
}

# --- Case a: clean file ----------------------------------------------------
reset_tree
write_md "$TMPROOT/docs/case-a.md" <<'EOF'
The reviewer set is rendered from current configuration.
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "a (clean file)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case b: single violation --------------------------------------------
reset_tree
write_md "$TMPROOT/docs/case-b.md" <<'EOF'
5 reviewers handle this lane.
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "b (single violation)" 1 "$stderr_file" "$rc" \
    "docs/case-b.md:1:" "literal item count" "the panel"
rm -f "$stderr_file"

# --- Case c: fenced violation exempt --------------------------------------
reset_tree
write_md "$TMPROOT/docs/case-c.md" <<'EOF'
```markdown
5 reviewers
```
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "c (fence exempt)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case d: inline allow-list with reason --------------------------------
reset_tree
write_md "$TMPROOT/docs/case-d.md" <<'EOF'
5 reviewers fixed by statute. <!-- lint-literal-counts: allow historical -->
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "d (allow with reason)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case e: empty allow reason does not apply ----------------------------
reset_tree
write_md "$TMPROOT/docs/case-e.md" <<'EOF'
5 reviewers fixed by statute. <!-- lint-literal-counts: allow -->
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "e (empty allow reason)" 1 "$stderr_file" "$rc" "docs/case-e.md:1:"
rm -f "$stderr_file"

# --- Case f: all plural nouns ---------------------------------------------
reset_tree
write_md "$TMPROOT/docs/case-f.md" <<'EOF'
1 assertions
2 rules
3 bullets
4 rows
5 reviewers
6 agents
7 specialists
8 cases
9 fields
10 sections
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "f (all nouns)" 1 "$stderr_file" "$rc" \
    "docs/case-f.md:1:" "docs/case-f.md:2:" "docs/case-f.md:3:" \
    "docs/case-f.md:4:" "docs/case-f.md:5:" "docs/case-f.md:6:" \
    "docs/case-f.md:7:" "docs/case-f.md:8:" "docs/case-f.md:9:" \
    "docs/case-f.md:10:"
rm -f "$stderr_file"

# --- Case g: mid-line count exempt ----------------------------------------
reset_tree
write_md "$TMPROOT/docs/case-g.md" <<'EOF'
The panel of 5 reviewers handles this lane.
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "g (mid-line exempt)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case h: multiple files -----------------------------------------------
reset_tree
write_md "$TMPROOT/docs/case-h1.md" <<'EOF'
5 reviewers
EOF
write_md "$TMPROOT/notes/case-h2.md" <<'EOF'
7 agents
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "h (multiple files)" 1 "$stderr_file" "$rc" \
    "docs/case-h1.md:1:" "notes/case-h2.md:1:"
rm -f "$stderr_file"

# --- Case i: CRLF + BOM ----------------------------------------------------
reset_tree
mkdir -p "$TMPROOT/docs"
printf '\xef\xbb\xbf5 reviewers\r\n' >"$TMPROOT/docs/case-i.md"
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "i (BOM + CRLF)" 1 "$stderr_file" "$rc" "docs/case-i.md:1:"
rm -f "$stderr_file"

# --- Case j: non-UTF-8 bytes ----------------------------------------------
reset_tree
mkdir -p "$TMPROOT/docs"
printf '\xff\xfe' >"$TMPROOT/docs/case-j.md"
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "j (non-UTF-8)" 2 "$stderr_file" "$rc" "cannot read file"
rm -f "$stderr_file"

# --- Case k: internal error wins over violations --------------------------
reset_tree
mkdir -p "$TMPROOT/docs"
printf '\xff\xfe' >"$TMPROOT/docs/case-k-bad.md"
write_md "$TMPROOT/docs/case-k-violation.md" <<'EOF'
5 reviewers
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "k (exit 2 priority)" 2 "$stderr_file" "$rc" \
    "cannot read file" "docs/case-k-violation.md:1:"
rm -f "$stderr_file"

# --- Case l: violation after fence close ----------------------------------
reset_tree
write_md "$TMPROOT/docs/case-l.md" <<'EOF'
```
5 reviewers
```
5 reviewers
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "l (after fence close)" 1 "$stderr_file" "$rc" "docs/case-l.md:4:"
rm -f "$stderr_file"

# --- Case m: empty root ----------------------------------------------------
reset_tree
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "m (empty root)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case n: uppercase ALLOW does not apply -------------------------------
reset_tree
write_md "$TMPROOT/docs/case-n.md" <<'EOF'
5 reviewers <!-- lint-literal-counts: ALLOW historical -->
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "n (uppercase allow rejected)" 1 "$stderr_file" "$rc" "docs/case-n.md:1:"
rm -f "$stderr_file"

# --- Case o: nested fence length awareness --------------------------------
reset_tree
write_md "$TMPROOT/docs/case-o.md" <<'EOF'
````
```markdown
5 rows
```
5 rows
````
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "o (nested fence)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case p: gitignored-dir scan exclusion --------------------------------
reset_tree
git -C "$TMPROOT" init >/dev/null 2>&1
printf '.agents/\n' >"$TMPROOT/.gitignore"
write_md "$TMPROOT/.agents/notes.md" <<'EOF'
5 reviewers
EOF
write_md "$TMPROOT/docs/control.md" <<'EOF'
5 reviewers
EOF
git -C "$TMPROOT" add .gitignore docs/control.md >/dev/null 2>&1
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "p1 (git worktree ignores .agents, scans control)" 1 "$stderr_file" "$rc" \
    "docs/control.md:1:"
if grep -Fq ".agents/notes.md" "$stderr_file"; then
    echo "FAIL [p1 (git worktree ignores .agents, scans control)]: scanned ignored .agents file" >&2
    FAIL=$((FAIL + 1))
else
    PASS=$((PASS + 1))
    echo "PASS [p1 (ignored .agents omitted)]"
fi
rm -f "$stderr_file"

rm -rf "$TMPROOT/.git"
rm -f "$TMPROOT/.gitignore"
rm -rf "$TMPROOT/docs"
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "p2 (non-git ignores .agents only)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"
write_md "$TMPROOT/docs/control.md" <<'EOF'
5 reviewers
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "p3 (non-git scans control)" 1 "$stderr_file" "$rc" "docs/control.md:1:"
rm -f "$stderr_file"

# --- Case q: symlink not followed -----------------------------------------
reset_tree
external_dir=$(mktemp -d -t lint-literal-counts-external-XXXXXX)
printf '5 reviewers\n' >"$external_dir/outside.md"
ln -s "$external_dir/outside.md" "$TMPROOT/linked.md"
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "q (symlink not followed)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"
rm -rf "$external_dir"

# --- Case r: positional arguments rejected --------------------------------
reset_tree
stderr_file=$(mktemp)
set +e
python3 "$LINT" --root "$TMPROOT" extra-positional.md 2>"$stderr_file"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    echo "FAIL [r (positional rejected)]: expected non-zero exit" >&2
    FAIL=$((FAIL + 1))
elif ! grep -Fq "unrecognized arguments: extra-positional.md" "$stderr_file"; then
    echo "FAIL [r (positional rejected)]: stderr missing argparse error" >&2
    cat "$stderr_file" >&2
    FAIL=$((FAIL + 1))
else
    PASS=$((PASS + 1))
    echo "PASS [r (positional rejected)]"
fi
rm -f "$stderr_file"

if [[ "$FAIL" -ne 0 ]]; then
    echo "Summary: $PASS passed, $FAIL failed" >&2
    exit 1
fi

echo "Summary: $PASS passed, $FAIL failed"
