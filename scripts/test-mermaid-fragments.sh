#!/usr/bin/env bash
# test-mermaid-fragments.sh — regression harness for Mermaid sanitizer/lint.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANITIZE="$SCRIPT_DIR/sanitize-mermaid-fragment.sh"
LINT="$SCRIPT_DIR/lint-mermaid-fences.sh"

[ -x "$SANITIZE" ] || { echo "FAIL: sanitizer not executable"; exit 1; }
[ -x "$LINT" ] || { echo "FAIL: lint helper not executable"; exit 1; }

tmpdir="$(mktemp -d -t mermaid-fragments-test-XXXXXX)"
trap 'rm -rf "$tmpdir"' EXIT

pass=0
fail() {
    echo "FAIL: $1" >&2
    exit 1
}
ok() {
    pass=$((pass + 1))
    echo "PASS: $1"
}

run_case() {
    local name=$1 expected_rc=$2 expected_status=$3 expected_token=${4:-}
    local file="$tmpdir/$name.mmd"
    cat > "$file"
    set +e
    out="$("$SANITIZE" --input "$file" 2>"$tmpdir/$name.stderr")"
    rc=$?
    set -e
    [ "$rc" -eq "$expected_rc" ] || fail "$name rc: expected $expected_rc got $rc output=$out"
    grep -qxF "STATUS=$expected_status" <<<"$out" || fail "$name missing STATUS=$expected_status output=$out"
    if [ -n "$expected_token" ]; then
        grep -q "REASON_TOKEN=$expected_token fence=1 line=" <<<"$out" || fail "$name missing token $expected_token output=$out"
    fi
    ok "$name"
}

run_case pipe-in-flowchart-square-bracket 1 rejected pipe-in-node-label <<'EOF'
flowchart TD
  A[foo|bar]
EOF
run_case pipe-in-flowchart-paren 1 rejected pipe-in-node-label <<'EOF'
flowchart TD
  A(foo|bar)
EOF
run_case pipe-in-flowchart-curly 1 rejected pipe-in-node-label <<'EOF'
flowchart TD
  A{foo|bar}
EOF
run_case pipe-in-flowchart-double-paren 1 rejected pipe-in-node-label <<'EOF'
flowchart TD
  A((foo|bar))
EOF
run_case br-in-participant-alias 1 rejected br-in-participant-alias <<'EOF'
sequenceDiagram
  participant X as one<br/>two
EOF
run_case br-self-closing-alias 1 rejected br-in-participant-alias <<'EOF'
sequenceDiagram
  participant X as one<br />two
EOF
run_case br-tag-alias 1 rejected br-in-participant-alias <<'EOF'
sequenceDiagram
  participant X as one<br>two
EOF
run_case dollar-in-participant-alias 1 rejected dollar-in-participant-alias <<'EOF'
sequenceDiagram
  participant X as $IMPLEMENT_TMPDIR
EOF
run_case dollar-in-actor-alias 1 rejected dollar-in-participant-alias <<'EOF'
sequenceDiagram
  actor X as $VAR
EOF

run_case pipe-in-flowchart-edge-label 0 ok <<'EOF'
flowchart TD
  A -->|edge text| B
EOF
run_case br-in-flowchart-node-label 0 ok <<'EOF'
flowchart TD
  A[line one<br/>line two]
EOF
run_case dollar-outside-alias 0 ok <<'EOF'
sequenceDiagram
  participant X as Final
  Note over X: $RUNTIME_VAR ok
EOF
run_case clean-flowchart 0 ok <<'EOF'
flowchart TD
  A[Clean] --> B[Done]
EOF
run_case clean-sequenceDiagram 0 ok <<'EOF'
sequenceDiagram
  participant X as Final
  X->>X: done
EOF
run_case pipe-inside-quoted-node-label 0 ok <<'EOF'
flowchart TD
  A["foo|bar"]
EOF
run_case pipe-inside-quoted-with-escaped-quote 0 ok <<'EOF'
flowchart TD
  A["foo \"x\" |bar"]
EOF
run_case nested-brackets 0 ok <<'EOF'
flowchart TD
  A[foo [inner] bar]
EOF

# REJECT cases that prove the FINDING_17 frontmatter-bypass fix:
# unsafe content following a YAML frontmatter block must still trip
# the flowchart / sequenceDiagram checks. Without skipping the leading
# `---` block in body_start_line, both fences would falsely return
# STATUS=ok (closes #1426 follow-up FINDING_17).
run_case frontmatter-pipe-in-node-label 1 rejected pipe-in-node-label <<'EOF'
---
title: example
---
flowchart TD
  A[foo|bar]
EOF
run_case frontmatter-br-in-participant-alias 1 rejected br-in-participant-alias <<'EOF'
---
config:
  theme: forest
---
sequenceDiagram
  participant X as one<br/>two
EOF

# ACCEPT case: clean diagram preceded by YAML frontmatter (positive
# control — frontmatter alone must not produce false rejects).
run_case frontmatter-clean-flowchart 0 ok <<'EOF'
---
title: clean example
---
flowchart TD
  A[Hello] --> B[World]
EOF

# REJECT cases for round-2 follow-up regressions:
# (A) Unclosed YAML frontmatter must fail-closed: prior round-1 fix
#     for FINDING_17 returned NR+1 from body_start_line() when the
#     closing `---` was missing, silently skipping the flowchart /
#     sequenceDiagram checks. The fix emits unclosed-frontmatter and
#     exits non-zero.
run_case frontmatter-unclosed-no-trailing-marker 1 rejected unclosed-frontmatter <<'EOF'
---
title: missing close
flowchart TD
  A[unsafe|content]
EOF

# (C) Multi-space participant declarations must still trigger alias
#     rejection. Pre-existing bypass: the regex required exactly one
#     whitespace between keyword/id/as, so `participant   X   as ...`
#     skipped the alias check.
run_case multi-space-participant-with-br 1 rejected br-in-participant-alias <<'EOF'
sequenceDiagram
  participant   X   as one<br/>two
EOF
run_case tab-separated-participant-with-dollar 1 rejected dollar-in-participant-alias <<'EOF'
sequenceDiagram
	participant	X	as	$VAR
EOF

mixed="$tmpdir/mixed.md"
cat > "$mixed" <<'EOF'
## Architecture Diagram

```mermaid
flowchart TD
  A[Clean] --> B[Done]
```

## Code Flow Diagram

```mermaid
sequenceDiagram
  participant X as one<br/>two
```
EOF
set +e
mixed_out="$("$SANITIZE" --input "$mixed" --from-md)"
mixed_rc=$?
set -e
[ "$mixed_rc" -eq 1 ] || fail "mixed rc expected 1 got $mixed_rc output=$mixed_out"
grep -qxF "FENCE_COUNT=2" <<<"$mixed_out" || fail "mixed missing FENCE_COUNT=2"
grep -qxF "FENCE_1_HEADING=architecture" <<<"$mixed_out" || fail "mixed missing architecture heading"
grep -qxF "FENCE_2_HEADING=code-flow" <<<"$mixed_out" || fail "mixed missing code-flow heading"
grep -q "REASON_TOKEN=br-in-participant-alias fence=2 line=" <<<"$mixed_out" || fail "mixed missing fence-2 token"
ok "mixed-fences from-md"

# (B) Indented mermaid fences (up to 3 leading spaces per
#     GFM/CommonMark) MUST be detected by the from-md scanner; prior
#     fence_re started at column 0 and would silently skip indented
#     fences, bypassing the sanitizer entirely (round-2 follow-up
#     SECURITY).
indented="$tmpdir/indented.md"
cat > "$indented" <<'EOF'
## Architecture Diagram

   ```mermaid
   flowchart TD
     A[unsafe|content]
   ```
EOF
set +e
indented_out="$("$SANITIZE" --input "$indented" --from-md)"
indented_rc=$?
set -e
[ "$indented_rc" -eq 1 ] || fail "indented-fence rc expected 1 got $indented_rc output=$indented_out"
grep -qxF "FENCE_COUNT=1" <<<"$indented_out" || fail "indented-fence missing FENCE_COUNT=1 (scanner did not see indented fence)"
grep -q "REASON_TOKEN=pipe-in-node-label fence=1 line=" <<<"$indented_out" || fail "indented-fence missing pipe-in-node-label token"
ok "indented-fence detected by from-md scanner"

log="$tmpdir/execution-issues.md"
cat > "$log" <<'EOF'
### Tool Failures

- existing tool failure
EOF
set +e
warn_out="$("$SANITIZE" --input "$mixed" --from-md --warnings-log "$log" --warnings-step "7a")"
warn_rc=$?
set -e
[ "$warn_rc" -eq 1 ] || fail "warnings rc expected 1 got $warn_rc output=$warn_out"
grep -qxF '### Tool Failures' "$log" || fail "warnings log lost Tool Failures"
grep -qxF '### Warnings' "$log" || fail "warnings log missing Warnings"
grep -qF -- '- **Step 7a — mermaid sanitizer rejected:** br-in-participant-alias' "$log" || fail "warnings log missing sanitizer entry"
ok "warnings-log append"

reasons_agg="$tmpdir/reasons-agg"
cat > "$reasons_agg" <<'EOF'
REASON_TOKEN=normal-token fence=mermaid line=9
REASON_TOKEN=future=token fence=mermaid line=9
EOF
aggregated_tokens="$(awk '/^REASON_TOKEN=/{sub(/^REASON_TOKEN=/, ""); sub(/[[:space:]].*$/, ""); print}' "$reasons_agg" | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
[ "$aggregated_tokens" = "future=token normal-token" ] || fail "warnings-token aggregation expected 'future=token normal-token' got '$aggregated_tokens'"
ok "warnings-token aggregation preserves embedded equals"

nested="$tmpdir/nested.md"
cat > "$nested" <<'EOF'
````markdown
```mermaid
flowchart TD
  A[bad|example]
```
````
EOF
set +e
lint_out="$("$LINT" "$nested" 2>&1)"
lint_rc=$?
set -e
if [ "$lint_rc" -eq 2 ]; then
    ok "lint nested-fence fixture skipped without mmdc"
elif [ "$lint_rc" -eq 0 ]; then
    ok "lint nested-fence fixture"
else
    fail "lint nested-fence fixture rc=$lint_rc output=$lint_out"
fi

echo "Results: $pass passed"
