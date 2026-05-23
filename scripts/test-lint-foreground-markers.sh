#!/usr/bin/env bash
# test-lint-foreground-markers.sh — regression harness for lint-foreground-markers.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-foreground-markers.sh"

if [[ ! -f "$LINT" ]]; then
    printf 'ERROR: lint script not found: %s\n' "$LINT" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-foreground-markers.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

write_md() {
    local rel="$1"
    mkdir -p "$(dirname "$TMPROOT/$rel")"
    cat >"$TMPROOT/$rel"
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

assert_case_clean() {
    local label="$1"
    local stderr_file="$2"
    local rc="$3"
    if [[ "$rc" -ne 0 ]]; then
        printf 'FAIL [%s]: expected exit 0, got %s\n' "$label" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    if [[ -s "$stderr_file" ]]; then
        printf 'FAIL [%s]: expected empty stderr\n' "$label" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

stderr_file="$(mktemp)"

# 1 — clean collect-agent-results.sh
reset_tree
write_md skills/clean/SKILL.md <<'EOF'
# Case 1

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "clean collect-agent-results fence" "$stderr_file" "$rc"

# 2 — missing banner
reset_tree
write_md skills/miss-banner/SKILL.md <<'EOF'
# Case 2

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "missing banner" 1 "$stderr_file" "$rc" 'missing banner for collect-agent-results.sh'

# 3 — missing comment
reset_tree
write_md skills/miss-comment/SKILL.md <<'EOF'
# Case 3

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "missing comment" 1 "$stderr_file" "$rc" 'missing comment for collect-agent-results.sh'

# 4 — blockquoted banner
reset_tree
write_md skills/bq-banner/SKILL.md <<'EOF'
# Case 4

> **⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "blockquoted banner" "$stderr_file" "$rc"

# 5 — banner falls outside the 20-line pre-fence window
reset_tree
write_md skills/banner-window/SKILL.md <<'EOF'
# Case 5

**⚠ Foreground required — do NOT set `run_in_background: true`.**

x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "banner outside pre-fence window" 1 "$stderr_file" "$rc" 'missing banner for collect-agent-results.sh'

# 6 — comment more than five in-fence lines above the anchor
reset_tree
write_md skills/comment-window/SKILL.md <<'EOF'
# Case 6

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4





${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "comment too far above anchor" 1 "$stderr_file" "$rc" 'missing comment for collect-agent-results.sh'

# 7 — non-denylist script
reset_tree
write_md skills/non-deny/SKILL.md <<'EOF'
# Case 7

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-reviewers.sh --timeout 1 a.done b.done
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "wait-for-reviewers not denylisted" "$stderr_file" "$rc"

# 8 — yaml fence ignored
reset_tree
write_md skills/yaml-fence/SKILL.md <<'EOF'
# Case 8

```yaml
path: ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "yaml fence ignores shell anchors" "$stderr_file" "$rc"

# 9 — ship-pr.sh
reset_tree
write_md skills/ship-pr/SKILL.md <<'EOF'
# Case 9

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "ship-pr with markers" "$stderr_file" "$rc"

# 10 — indented ```bash opening fence
reset_tree
write_md skills/indented-fence/SKILL.md <<'EOF'
# Case 10

**⚠ Foreground required — do NOT set `run_in_background: true`.**

   ```bash
   # Foreground required: see BASH_AUTHORING.md §4
   ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
   ```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "indented bash fence" "$stderr_file" "$rc"

# 11 — skills/shared/*.md
reset_tree
write_md skills/shared/case11.md <<'EOF'
# Case 11

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "skills/shared markdown path" "$stderr_file" "$rc"

# 12 — if-shaped run-step5-review.sh
reset_tree
write_md skills/if-shape/SKILL.md <<'EOF'
# Case 12

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
if ! "${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh" --flag; then
  exit 1
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "if-shaped denylisted invoke" "$stderr_file" "$rc"

# 13 — assignment-shaped review-and-fix.sh
reset_tree
write_md skills/assign-shape/SKILL.md <<'EOF'
# Case 13

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
CMD=${CLAUDE_PLUGIN_ROOT}/scripts/review-and-fix.sh
printf '%s\n' "$CMD"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "assignment-shaped denylisted invoke" "$stderr_file" "$rc"

# 13b — command-substitution assignment with denylisted path (dispatch-with-waterfall)
reset_tree
write_md skills/cmdsubst-assign/SKILL.md <<'EOF'
# Case 13b

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
VAR=$(${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-with-waterfall.sh --timeout 1)
printf '%s\n' "$VAR"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "cmdsubst assignment-shaped denylisted invoke" "$stderr_file" "$rc"

# 13c — unbraced CLAUDE_PLUGIN_ROOT path to denylisted script
reset_tree
write_md skills/unbraced-root/SKILL.md <<'EOF'
# Case 13c

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
$CLAUDE_PLUGIN_ROOT/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "unbraced CLAUDE_PLUGIN_ROOT denylisted invoke" "$stderr_file" "$rc"

# 14 — substring file name must not anchor collect-agent-results.sh
reset_tree
write_md skills/substring-guard/SKILL.md <<'EOF'
# Case 14

```bash
echo "fixture path test-collect-agent-results.sh"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "substring test-collect-agent-results false negative" "$stderr_file" "$rc"

# 14b — plugin-root path ending in test-review-and-fix.sh must not match review-and-fix.sh
reset_tree
write_md skills/plugin-root-suffix-guard/SKILL.md <<'EOF'
# Case 14b

```bash
echo "${CLAUDE_PLUGIN_ROOT}/scripts/test-review-and-fix.sh"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "plugin-root path suffix must not false-anchor review-and-fix" "$stderr_file" "$rc"

# 15 — dispatch-plan-voters.sh
reset_tree
write_md skills/plan-voters/SKILL.md <<'EOF'
# Case 15

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-plan-voters.sh --tmpdir "$TMP"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "dispatch-plan-voters with markers" "$stderr_file" "$rc"

# 17 — parse-only safety: fence body would exit 99 if executed as a script; linter must not
reset_tree
write_md skills/parse-only-exec/SKILL.md <<'EOF'
# Case 17

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
exit 99
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "parse-only fence body not executed" "$stderr_file" "$rc"

# 18 — EOF: unterminated fence still scanned (missing banner)
reset_tree
write_md skills/eof-open-fence/SKILL.md <<'EOF'
# Case 18

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
EOF
rc="$(run_lint "$stderr_file")"
assert_case "EOF unterminated fence still linted" 1 "$stderr_file" "$rc" 'missing banner for collect-agent-results.sh'

# 19 — second Family-B anchor after >5 in-fence lines needs its own comment
reset_tree
write_md skills/multi-anchor-gap/SKILL.md <<'EOF'
# Case 19

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt






${CLAUDE_PLUGIN_ROOT}/scripts/ci-wait.sh --dry-run
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "second anchor after long gap needs comment" 1 "$stderr_file" "$rc" 'missing comment for ci-wait.sh'

# 20 — if ! with repo-relative path (no CLAUDE_PLUGIN_ROOT prefix)
reset_tree
write_md skills/if-not-claude-path/SKILL.md <<'EOF'
# Case 20

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
if ! scripts/run-step5-review.sh --mode loop; then
  exit 1
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "if ! relative denylisted path" "$stderr_file" "$rc"

# 21 — env-prefixed bash invocation
reset_tree
write_md skills/env-bash-prefix/SKILL.md <<'EOF'
# Case 21

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
FOO=1 bash "${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh" --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "env-prefixed bash denylisted invoke" "$stderr_file" "$rc"

# 21b — step2-implement.sh (denylist coverage)
reset_tree
write_md skills/step2-impl/SKILL.md <<'EOF'
# Case 21b

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
bash "${CLAUDE_PLUGIN_ROOT}/scripts/step2-implement.sh" --help
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "step2-implement denylisted invoke" "$stderr_file" "$rc"

# 22 — commented-out denylisted path is not an anchor
reset_tree
write_md skills/commented-denylist/SKILL.md <<'EOF'
# Case 22

```bash
# ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
echo ok
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "commented denylisted line ignored" "$stderr_file" "$rc"

# 23 — denylist-shaped path inside a quoted heredoc body must not anchor (false-positive guard)
reset_tree
write_md skills/heredoc-doc/SKILL.md <<'EOF'
# Case 23

```bash
cat <<'MD'
Example: ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1
MD
echo done
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "heredoc body ignores denylist-shaped text" "$stderr_file" "$rc"

# 24 — backslash-continued denylisted path with markers (single logical invocation)
reset_tree
write_md skills/bs-cont/SKILL.md <<'EOF'
# Case 24

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.\
sh --timeout 1 x.txt
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "backslash-continued denylisted path with markers" "$stderr_file" "$rc"

# 16 — Family A: minimum run_in_background: true counts on reference paths (sketch / dialectic / voting)
assert_family_count() {
    local path="$1" expected="$2" label="$3"
    local got
    got=$(grep -cF 'run_in_background: true' "$path" || true)
    if [[ "$got" -lt "$expected" ]]; then
        printf 'FAIL [family-a %s]: count decreased below floor %s, got %s (%s)\n' "$label" "$expected" "$got" "$path" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    printf 'PASS [family-a %s]\n' "$label"
    PASS=$((PASS + 1))
}

assert_family_count "$REPO_ROOT/skills/design/references/sketch-launch.md" 9 'sketch-launch.md'
assert_family_count "$REPO_ROOT/skills/design/references/dialectic-execution.md" 5 'dialectic-execution.md'
assert_family_count "$REPO_ROOT/skills/shared/voting-protocol.md" 3 'voting-protocol.md'
assert_family_count "$REPO_ROOT/skills/shared/dialectic-protocol.md" 3 'dialectic-protocol.md'

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
