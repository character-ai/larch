#!/usr/bin/env bash
# Regression harness for scrub-submodule-paths.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/scrub-submodule-paths.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-scrub-submodule-paths.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

run_case() {
    local work="$1" input="$2" output="$3" log="$4"
    (cd "$work" && "$SCRIPT" --input "$input" --output "$output" --log "$log")
}

make_repo() {
    local dir="$1"
    mkdir -p "$dir"
    git -C "$dir" init -q
}

repo_no_sub="$TMP/no-submodules"
make_repo "$repo_no_sub"
cat > "$repo_no_sub/findings.md" <<'EOF'
### FINDING_1: Keep
- **Location**: src/main.py
- **Concern**: Concern.
- **Suggested revision**: Fix.
EOF
out=$(run_case "$repo_no_sub" "$repo_no_sub/findings.md" "$repo_no_sub/out.md" "$repo_no_sub/scrub.log")
grep -Fq 'SCRUB_COUNT=0' <<< "$out" || fail "no-submodules scrub count"
grep -Fq 'SCRUB_OK=true' <<< "$out" || fail "no-submodules ok"
cmp "$repo_no_sub/findings.md" "$repo_no_sub/out.md" || fail "no-submodules should pass through"
[[ ! -s "$repo_no_sub/scrub.log" ]] || fail "no-submodules log should be empty"

repo_single="$TMP/single-submodule"
make_repo "$repo_single"
cat > "$repo_single/.gitmodules" <<'EOF'
[submodule "vendor/lib"]
	path = vendor/lib
EOF
cat > "$repo_single/findings.md" <<'EOF'
### FINDING_1: Drop
- **Location**: vendor/lib/file.py
- **Concern**: Concern.
- **Suggested revision**: Fix.

### FINDING_2: Keep
- **Location**: src/main.py
- **Concern**: Concern.
- **Suggested revision**: Fix.
EOF
out=$(run_case "$repo_single" "$repo_single/findings.md" "$repo_single/out.md" "$repo_single/scrub.log")
grep -Fq 'SCRUB_COUNT=1' <<< "$out" || fail "single-submodule scrub count"
grep -Fq 'FINDING_1 | vendor/lib/file.py | reason=under-submodule' "$repo_single/scrub.log" || fail "single-submodule log"
! grep -Fq 'FINDING_1' "$repo_single/out.md" || fail "submodule finding should be dropped"
grep -Fq 'FINDING_2' "$repo_single/out.md" || fail "non-submodule finding should remain"

repo_nested="$TMP/nested-submodule"
make_repo "$repo_nested"
cat > "$repo_nested/.gitmodules" <<'EOF'
[submodule "a/b/c"]
	path = a/b/c
EOF
cat > "$repo_nested/findings.md" <<'EOF'
### FINDING_1: Drop nested
- **Location**: a/b/c/x.py
- **Concern**: Concern.
- **Suggested revision**: Fix.

### FINDING_2: Keep sibling
- **Location**: a/b/other.py
- **Concern**: Concern.
- **Suggested revision**: Fix.
EOF
out=$(run_case "$repo_nested" "$repo_nested/findings.md" "$repo_nested/out.md" "$repo_nested/scrub.log")
grep -Fq 'SCRUB_COUNT=1' <<< "$out" || fail "nested scrub count"
! grep -Fq 'FINDING_1' "$repo_nested/out.md" || fail "nested submodule finding should be dropped"
grep -Fq 'FINDING_2' "$repo_nested/out.md" || fail "nested sibling finding should remain"

repo_fenced="$TMP/fenced-path"
make_repo "$repo_fenced"
cat > "$repo_fenced/.gitmodules" <<'EOF'
[submodule "vendor/lib"]
	path = vendor/lib
EOF
cat > "$repo_fenced/findings.md" <<'EOF'
### FINDING_1: Drop from code span
- **Concern**: The issue appears in `vendor/lib/file.py`.
- **Suggested revision**: Update the call.

### FINDING_2: Keep fenced non-submodule
- **Concern**: The issue appears in:
```text
src/main.py
```
- **Suggested revision**: Update the call.
EOF
out=$(run_case "$repo_fenced" "$repo_fenced/findings.md" "$repo_fenced/out.md" "$repo_fenced/scrub.log")
grep -Fq 'SCRUB_COUNT=1' <<< "$out" || fail "fenced scrub count"
! grep -Fq 'FINDING_1' "$repo_fenced/out.md" || fail "code-span submodule finding should be dropped"
grep -Fq 'FINDING_2' "$repo_fenced/out.md" || fail "fenced non-submodule finding should remain"

repo_empty="$TMP/empty"
make_repo "$repo_empty"
: > "$repo_empty/findings.md"
out=$(run_case "$repo_empty" "$repo_empty/findings.md" "$repo_empty/out.md" "$repo_empty/scrub.log")
grep -Fq 'SCRUB_COUNT=0' <<< "$out" || fail "empty scrub count"
grep -Fq 'SCRUB_OK=true' <<< "$out" || fail "empty ok"
[[ ! -s "$repo_empty/out.md" ]] || fail "empty output should be empty"

echo "test-scrub-submodule-paths: ok"
