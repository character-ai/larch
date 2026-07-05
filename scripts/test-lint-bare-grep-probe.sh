#!/usr/bin/env bash
# test-lint-bare-grep-probe.sh - Regression harness for lint-bare-grep-probe.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-bare-grep-probe.sh"

if [[ ! -f "$LINT" ]]; then
    printf 'ERROR: lint script not found: %s\n' "$LINT" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-bare-grep-probe.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    mkdir -p "$TMPROOT/skills/foo" "$TMPROOT/.claude/skills/bar" "$TMPROOT/.claude/rules"
}

write_file() {
    local path="$1"
    shift
    mkdir -p "$(dirname "$path")"
    printf '%s\n' "$@" >"$path"
}

run_lint() {
    local stderr_file="$1"
    set +e
    bash "$LINT" --root "$TMPROOT" 2>"$stderr_file"
    local rc=$?
    set -e
    printf '%s\n' "$rc"
}

assert_case() {
    local label="$1"
    local expected_exit="$2"
    local stderr_file="$3"
    local rc="$4"
    shift 4

    if [[ "$rc" -ne "$expected_exit" ]]; then
        printf 'FAIL [%s]: expected exit %s, got %s\n' "$label" "$expected_exit" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if ! grep -Fq "$needle" "$stderr_file"; then
            printf 'FAIL [%s]: stderr missing expected needle: %s\n' "$label" "$needle" >&2
            cat "$stderr_file" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

assert_negative() {
    local label="$1"
    local stderr_file="$2"
    local rc="$3"
    shift 3

    if [[ "$rc" -ne 0 ]]; then
        printf 'FAIL [%s]: expected clean exit 0, got %s\n' "$label" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if grep -Fq "$needle" "$stderr_file"; then
            printf 'FAIL [%s]: stderr unexpectedly contains: %s\n' "$label" "$needle" >&2
            cat "$stderr_file" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

stderr_file="$(mktemp)"

# 1. Clean tree (no markdown files at all).
reset_tree
rc="$(run_lint "$stderr_file")"
assert_case "empty tree" 0 "$stderr_file" "$rc"

# 2. Bare grep || X violation in a SKILL.md bash fence.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '# Foo' \
    '' \
    '```bash' \
    'grep -q PATTERN file.txt || echo NO_MATCH' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "bare grep || X" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:4:" \
    "bare top-level grep in bash fence"

# 3. Bare grep with redirect (no || continuation).
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '# Foo' \
    '' \
    '```bash' \
    'grep -v PATTERN file.txt > out.txt' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "bare grep with redirect" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:4:" \
    "bare grep statement"

# 4. if grep ... ; then violation.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'if grep -q PATTERN file.txt; then echo found; fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "if grep then" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:2:" \
    "if grep ... ; then"

# 5. if ! grep ... ; then violation.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'if ! grep -q PATTERN file.txt; then echo missing; fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "if ! grep then" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:2:" \
    "if grep ... ; then"

# 6. command grep ... || X is allowed (safe form).
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'command grep -q PATTERN file.txt || echo NO_MATCH' \
    'if command grep -q PATTERN file.txt; then echo found; fi' \
    'command grep -v PATTERN file.txt > out.txt' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "command grep allowed" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

# 7. Explicit subshell wrap is allowed.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    '( grep -q PATTERN file.txt ) || echo NO_MATCH' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "subshell-wrap allowed" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

# 8. Piped grep is allowed (pipe creates a subshell).
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'cat file.txt | grep -q PATTERN || echo NO_MATCH' \
    'printf "%s\n" foo | grep -F bar > out.txt' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "piped grep allowed" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

assert_fence_line_violation() {
    local label="$1"
    local line="$2"
    shift 2

    reset_tree
    write_file "$TMPROOT/skills/foo/SKILL.md" \
        '```bash' \
        "$line" \
        '```'
    rc="$(run_lint "$stderr_file")"
    assert_case "$label" 1 "$stderr_file" "$rc" \
        "skills/foo/SKILL.md:2:" \
        "$@"
}

assert_fence_line_allowed() {
    local label="$1"
    local line="$2"

    reset_tree
    write_file "$TMPROOT/skills/foo/SKILL.md" \
        '```bash' \
        "$line" \
        '```'
    rc="$(run_lint "$stderr_file")"
    assert_negative "$label" "$stderr_file" "$rc" \
        "skills/foo/SKILL.md"
}

assert_fence_line_violation "no-path rg with type" 'rg -n PATTERN --type py' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path ripgrep with type" 'ripgrep -n PATTERN --type py' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path command grep" 'command grep -n PATTERN' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path command rg" 'command rg -n PATTERN --type py' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path command ripgrep" 'command ripgrep -n PATTERN --type py' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if rg" 'if rg -q PATTERN --type py; then echo found; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if ripgrep" 'if ripgrep -q PATTERN; then echo found; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if ! rg" 'if ! rg -q PATTERN --type py; then echo missing; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if ! ripgrep" 'if ! ripgrep -q PATTERN; then echo missing; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if command grep" 'if command grep -q PATTERN; then echo found; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if ! command ripgrep" 'if ! command ripgrep -q PATTERN; then echo missing; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path if ! command rg" 'if ! command rg -q PATTERN; then echo missing; fi' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path subshell rg" '( rg -n PATTERN ) || true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path subshell ripgrep" '( ripgrep -q PATTERN ) || true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path subshell grep" '( grep -n PATTERN ) || true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path subshell command rg" '( command rg -n PATTERN ) || true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path subshell command grep" '( command grep -q PATTERN ) || true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path env rg" 'LC_ALL=C rg -n PATTERN --type py' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path rg before or-suffix" 'rg -n PATTERN || true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path rg before pipe" 'rg -n PATTERN | head' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path rg before background" 'rg -n PATTERN &' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path rg before and-suffix" 'rg -n PATTERN && true' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path rg before semicolon" 'rg -n PATTERN; echo done' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path rg before pipe-stderr" 'rg -n PATTERN |& cat' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path brace rg" '{ rg -n PATTERN; }' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path brace command rg" '{ command rg -n PATTERN; }' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path brace ripgrep" '{ ripgrep -n PATTERN; }' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path brace command ripgrep" '{ command ripgrep -n PATTERN; }' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "no-path brace grep" '{ grep -n PATTERN; }' \
    "bare top-level grep in bash fence"
assert_fence_line_violation "no-path brace command grep" '{ command grep -q PATTERN; }' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "quoted stdin marker is not stdin-safe" "rg -n PATTERN; echo '< /dev/null'" \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "quoted redirect tokens are not stdin-safe" 'rg -n PATTERN "<" /dev/null' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "commented stdin marker is not stdin-safe" 'rg -n PATTERN # < /dev/null' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "rg -e without path rejected" 'rg -e PATTERN' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "rg equals type without path rejected" 'rg --type=py PATTERN' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "rg regexp equals without path rejected" 'rg --regexp=PATTERN' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "grep attached context without path rejected" 'grep -A3 PATTERN' \
    "bare top-level grep in bash fence"
assert_fence_line_violation "command grep -e without path rejected" 'command grep -e PATTERN' \
    "no-path rg/grep probe may block on stdin"

reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'if true; then' \
    '    rg -n PATTERN --type py' \
    'fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "indented no-path rg flagged" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:3:" \
    "no-path rg/grep probe may block on stdin"

reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'if true; then' \
    '    ripgrep -q PATTERN' \
    'fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "indented no-path ripgrep flagged" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:3:" \
    "no-path rg/grep probe may block on stdin"

assert_fence_line_allowed "path rg with type" 'rg -n PATTERN --type py python/'
assert_fence_line_allowed "path ripgrep with type" 'ripgrep -n PATTERN --type py skills/'
assert_fence_line_allowed "path command grep" 'command grep -n PATTERN file.txt'
assert_fence_line_allowed "path command rg" 'command rg -n PATTERN python/'
assert_fence_line_allowed "path command ripgrep" 'command ripgrep -n PATTERN skills/'
assert_fence_line_allowed "path if rg" 'if rg -q PATTERN python/; then echo found; fi'
assert_fence_line_allowed "path if ! ripgrep" 'if ! ripgrep -q PATTERN skills/; then echo missing; fi'
assert_fence_line_allowed "path if command rg" 'if command rg -q PATTERN python/; then echo found; fi'
assert_fence_line_allowed "path if command ripgrep" 'if command ripgrep -q PATTERN skills/; then echo missing; fi'
assert_fence_line_allowed "path subshell grep" '( grep -n PATTERN file.txt ) || true'
assert_fence_line_allowed "path subshell ripgrep" '( ripgrep -q PATTERN skills/ )'
assert_fence_line_allowed "path subshell command grep" '( command grep -q PATTERN file.txt )'
assert_fence_line_allowed "path subshell command rg" '( command rg -n PATTERN python/ )'
assert_fence_line_allowed "path brace command rg" '{ command rg -n PATTERN python/; }'
assert_fence_line_allowed "path brace command ripgrep" '{ command ripgrep -n PATTERN skills/; }'
assert_fence_line_violation "brace bare grep wrapper trap" '{ grep -n PATTERN file.txt; }' \
    "bare top-level grep in bash fence"
assert_fence_line_allowed "path brace command grep" '{ command grep -q PATTERN file.txt; }'
assert_fence_line_allowed "path env rg" 'LC_ALL=C rg -n PATTERN python/'
assert_fence_line_allowed "stdin-safe rg" 'rg -n PATTERN --type py < /dev/null'
assert_fence_line_allowed "redirected command grep with path" "command grep -v '^VALIDATION_' \"\$LANE_STATUS_FILE\" > \"\$LANE_STATUS_TMP\" || true"
assert_fence_line_allowed "redirected rg with later safe path" 'rg -n PATTERN < /dev/null python/'
assert_fence_line_allowed "piped rg allowed" 'cat file.txt | rg PATTERN'
assert_fence_line_allowed "piped stderr rg allowed" 'cat file.txt |& rg PATTERN'
assert_fence_line_violation "right-hand fallback rg parent ascent" 'false || rg PATTERN ../root' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "right-hand fallback command grep parent ascent" 'false || command grep PATTERN ../root' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "right-hand fallback bare grep" 'false || grep PATTERN file.txt' \
    "bare top-level grep in bash fence"
assert_fence_line_violation "semicolon rg parent ascent after non-grep" 'echo done; rg PATTERN ../root' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "logical-and rg parent ascent" 'true && rg PATTERN ../root' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "later pipeline rg parent ascent" 'cat file.txt | rg PATTERN ../root' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "safe first candidate unsafe later candidate" 'rg PATTERN python/; rg PATTERN ../root' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "rg split file parent ascent" 'rg -f ../patterns target/' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "rg long file parent ascent" 'rg --file ../patterns target/' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "rg long file equals parent ascent" 'rg --file=../patterns target/' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "rg attached file parent ascent" 'rg -f../patterns target/' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "rg split file parent ascent without path" 'rg -f ../patterns' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "grep split include no path rejected" "command grep --include '*.py' PATTERN" \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "grep split exclude no path rejected" "command grep --exclude '*.py' PATTERN" \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "grep split include parent ascent" "command grep --include '*.py' PATTERN ../root" \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "grep split exclude parent ascent" "command grep --exclude '*.py' PATTERN ../root" \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_allowed "rg -e with path allowed" 'rg -e PATTERN python/'
assert_fence_line_allowed "command grep -e with path allowed" 'command grep -e PATTERN file.txt'
assert_fence_line_allowed "command grep -l with path allowed" 'command grep -l PATTERN file.txt'
assert_fence_line_violation "command grep -l without path rejected" 'command grep -l PATTERN' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "stdin alias dash rejected" 'command grep -q PATTERN -' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_violation "stdin alias devstdin rejected" 'rg -n PATTERN /dev/stdin' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_allowed "quoted semicolon pattern with path" "rg ';' python/"
assert_fence_line_allowed "quoted less-than pattern with path" "rg '<' python/"
assert_fence_line_allowed "quoted pipe pattern with path" "rg '|' python/"
assert_fence_line_violation "rg -j without path rejected" 'rg -j 4 PATTERN' \
    "no-path rg/grep probe may block on stdin"
assert_fence_line_allowed "rg -j with path allowed" 'rg -j 4 PATTERN python/'
assert_fence_line_violation "parent ascent command grep" "command grep -r PATTERN \"\$IMPLEMENT_TMPDIR/../../../..\"" \
    "parent-directory ascent in grep-family path operand" \
    "use an absolute path or known bounded root"
assert_fence_line_violation "parent ascent subshell command grep" "( command grep -rn PATTERN \"\$IMPLEMENT_TMPDIR/../../../..\" ) || true" \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent rg relative" 'rg -n PATTERN ../python' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent ripgrep middle segment" 'ripgrep -n PATTERN skills/../python' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent rg trailing segment" 'rg -n PATTERN python/..' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent rg after terminator" 'rg -n PATTERN -- ../python' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent after redirect" 'rg -n PATTERN > out.txt ../python' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent before devnull" 'rg -n PATTERN ../python < /dev/null' \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_violation "parent ascent later path" "rg -n PATTERN \"\$CLAUDE_PLUGIN_ROOT/python\" ../python" \
    "parent-directory ascent in grep-family path operand"
assert_fence_line_allowed "bounded command grep root" "command grep -r PATTERN \"\$CLAUDE_PLUGIN_ROOT/python\""
assert_fence_line_allowed "bounded rg root" "rg -n PATTERN \"\$CLAUDE_PLUGIN_ROOT/python\""
assert_fence_line_allowed "rg pattern parent ascent allowed" 'rg -e "../pattern" python/'
assert_fence_line_allowed "command grep pattern parent ascent allowed" 'command grep -e "../pattern" python/file.py'
assert_fence_line_allowed "rg dot path allowed" 'rg -n PATTERN .'
assert_fence_line_allowed "rg include parent ascent option allowed" 'rg --include="../*.py" PATTERN python/'
assert_fence_line_allowed "rg parent-like hidden path allowed" 'rg -n PATTERN ..hidden'
assert_fence_line_allowed "rg parent-like version path allowed" 'rg -n PATTERN v1..2'
assert_fence_line_allowed "parent ascent pragma suppression" 'rg -n PATTERN ../fixture # lint-bare-grep-probe: ok reviewed parent-ascent fixture'

# 9. Same-line pragma suppression.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'grep -q PATTERN file.txt || echo NO_MATCH # lint-bare-grep-probe: ok harness fixture' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "pragma suppression" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

# 10. Full-line comments are skipped.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    '# grep -q PATTERN file.txt || echo NO_MATCH' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "full-line comment skipped" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

# 11. Non-bash fences are ignored.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```python' \
    'grep -q PATTERN file.txt || echo NO_MATCH' \
    '```' \
    '' \
    '```' \
    'grep -q PATTERN file.txt || echo NO_MATCH' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "non-bash fence skipped" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

# 12. Outside-of-fence grep prose is ignored.
reset_tree
# shellcheck disable=SC2016  # backticks are intentional markdown inline-code, not command substitution
write_file "$TMPROOT/skills/foo/SKILL.md" \
    'When you want to find a pattern, you can run `grep -q PATTERN file.txt || echo NO`.' \
    '' \
    'That same shape works at the top level of a script.'
rc="$(run_lint "$stderr_file")"
assert_negative "prose grep ignored" "$stderr_file" "$rc" \
    "skills/foo/SKILL.md"

# 13. .claude/skills/ and .claude/rules/ surfaces are scanned.
reset_tree
write_file "$TMPROOT/.claude/skills/bar/SKILL.md" \
    '```bash' \
    'grep -q PATTERN file.txt || echo NO' \
    '```'
write_file "$TMPROOT/.claude/rules/quux.md" \
    '```bash' \
    'if grep -q X y; then echo hi; fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case ".claude/skills + rules scanned" 1 "$stderr_file" "$rc" \
    ".claude/skills/bar/SKILL.md:2:" \
    ".claude/rules/quux.md:2:"

# 14. sh and shell info-strings count as bash fences.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```sh' \
    'grep -q X y || echo no' \
    '```' \
    '' \
    '```shell' \
    'grep -q X y || echo no' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "sh and shell info-strings" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:2:" \
    "skills/foo/SKILL.md:6:"

# 15. Out-of-scope: top-level README, docs/, larch-logs are not scanned.
reset_tree
write_file "$TMPROOT/README.md" \
    '```bash' \
    'grep -q X y || echo no' \
    '```'
mkdir -p "$TMPROOT/docs"
write_file "$TMPROOT/docs/something.md" \
    '```bash' \
    'grep -q X y || echo no' \
    '```'
mkdir -p "$TMPROOT/larch-logs/implement/RUN"
write_file "$TMPROOT/larch-logs/implement/RUN/notes.md" \
    '```bash' \
    'grep -q X y || echo no' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_negative "out-of-scope files unscanned" "$stderr_file" "$rc" \
    "README.md" \
    "docs/" \
    "larch-logs/"

# 16. Multiple files multiple violations.
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'grep -q X y || echo no' \
    'if grep Z w; then echo z; fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "multiple violations one file" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:2:" \
    "skills/foo/SKILL.md:3:"

# 17. Bash fence with leading whitespace before grep (indented inside fence body).
reset_tree
write_file "$TMPROOT/skills/foo/SKILL.md" \
    '```bash' \
    'if true; then' \
    '    grep -q X y || echo no' \
    'fi' \
    '```'
rc="$(run_lint "$stderr_file")"
assert_case "indented bare grep flagged" 1 "$stderr_file" "$rc" \
    "skills/foo/SKILL.md:3:"

# 18. Git-fallback parity: if git is available, scan results match the
#     non-git find-walk in the same tree.
if command -v git >/dev/null 2>&1; then
    reset_tree
    write_file "$TMPROOT/skills/foo/SKILL.md" \
        '```bash' \
        'grep -q X y || echo no' \
        '```'
    rc="$(run_lint "$stderr_file")"
    assert_case "non-git fallback finds violation" 1 "$stderr_file" "$rc" \
        "skills/foo/SKILL.md:2:"

    (cd "$TMPROOT" && git init -q)
    rc="$(run_lint "$stderr_file")"
    assert_case "git ls-files finds same violation" 1 "$stderr_file" "$rc" \
        "skills/foo/SKILL.md:2:"
else
    printf 'SKIP [git fallback parity]: git not on PATH\n'
fi

# 19. Invalid --root exits 2.
set +e
bash "$LINT" --root "$TMPROOT/nonexistent-$$-path" 2>"$stderr_file"
rc=$?
set -e
assert_case "invalid --root exits 2" 2 "$stderr_file" "$rc" \
    "is not a directory"

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
