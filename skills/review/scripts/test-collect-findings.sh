#!/usr/bin/env bash
# Regression harness for collect-findings.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/collect-findings.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-collect-findings.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues.md"

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

outf="$TMP/claude-vote-output.txt"
cat > "$outf" <<'EOF'
### In-Scope Findings
- Missing validation in parser.

### Out-of-Scope Observations
- Cleanup old tests.
EOF
printf '0\n' > "$outf.done"
printf 'STATUS=clean\n' > "$outf.dirty-tree"

out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$outf" --mode description --timeout 1 --findings-file "$TMP/findings.md" --oos-file "$TMP/oos.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=2' <<< "$out"
grep -Fq 'OOS_COUNT=1' <<< "$out"
grep -Fq 'DIRTY_DETECTED=false' <<< "$out"
grep -Fq 'COLLECTOR_OUTPUT_FILE=' <<< "$out"
grep -Fq '### FINDING_1:' "$TMP/findings.md"
grep -Fq -- '- **Concern**: - Missing validation in parser.' "$TMP/findings.md"

multiline="$TMP/cursor-specialist-multiline-output.txt"
cat > "$multiline" <<'EOF'
### In-Scope Findings
1. Parser misses a guard.
Continuation line keeps the same finding together.
EOF
printf '0\n' > "$multiline.done"
printf 'STATUS=clean\n' > "$multiline.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$multiline" --mode description --timeout 1 --findings-file "$TMP/findings-multiline.md" --oos-file "$TMP/oos-multiline.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1: Parser misses a guard.' "$TMP/findings-multiline.md"
grep -Fq -- '- **Concern**: 1. Parser misses a guard. Continuation line keeps the same finding together.' "$TMP/findings-multiline.md"
if grep -Fq '### FINDING_2:' "$TMP/findings-multiline.md"; then
    echo "FAIL: multiline finding was split" >&2
    exit 1
fi

printf 'NO_ISSUES_FOUND\n' > "$TMP/no.txt"
printf '0\n' > "$TMP/no.txt.done"
printf 'STATUS=clean\n' > "$TMP/no.txt.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$TMP/no.txt" --mode diff --timeout 1 --findings-file "$TMP/findings2.md" --oos-file "$TMP/oos2.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=0' <<< "$out"

# JSON no-findings sentinel (canonical form per #2156) — when jq is present.
if command -v jq >/dev/null 2>&1; then
    printf '{"no_issues_found": true}\n' > "$TMP/json-sentinel.txt"
    printf '0\n' > "$TMP/json-sentinel.txt.done"
    printf 'STATUS=clean\n' > "$TMP/json-sentinel.txt.dirty-tree"
    out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$TMP/json-sentinel.txt" --mode diff --timeout 1 --findings-file "$TMP/findings-json.md" --oos-file "$TMP/oos-json.md")
    assert_stdout_cap "$out"
    grep -Fq 'FINDINGS_COUNT=0' <<< "$out"
fi

external="$TMP/codex-generalist-output.txt"
cat > "$external" <<'EOF'
Read-only: we can't write the TSV sidecar here, so the findings follow inline.

```
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/foo.sh:42	Null pointer not checked	Returns nil on error path	Add nil guard before use
1	out_of_scope	nit	code-quality	scripts/bar.sh:10	Unused variable x	Dead code	Remove the variable
```
EOF
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --external-output-files "$external" --mode diff --timeout 1 --findings-file "$TMP/findings-inline-tsv.md" --oos-file "$TMP/oos-inline-tsv.md" 2>"$TMP/inline-tsv.stderr")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=2' <<< "$out"
grep -Fq 'OOS_COUNT=1' <<< "$out"
grep -Fq 'correctness: scripts/foo.sh:42' "$TMP/findings-inline-tsv.md"
grep -Fq 'code-quality: scripts/bar.sh:10' "$TMP/findings-inline-tsv.md"
grep -Fq '[OUT_OF_SCOPE] code-quality: scripts/bar.sh:10' "$TMP/oos-inline-tsv.md"
# Normal inline TSV is collected silently — no stderr noise and no execution-issues tsv-fallback rows.
if [[ -s "$TMP/inline-tsv.stderr" ]]; then
    echo "FAIL: expected empty stderr for silent inline-TSV collection" >&2
    cat "$TMP/inline-tsv.stderr" >&2
    exit 1
fi
if [[ -f "$TMP/execution-issues.md" ]] && grep -Eiq 'tsv-fallback|inline-TSV recovery' "$TMP/execution-issues.md"; then
    echo "FAIL: execution-issues must not log tsv-fallback for normal inline TSV" >&2
    cat "$TMP/execution-issues.md" >&2
    exit 1
fi

# Narrative-only output (no structured findings) must produce FINDINGS_COUNT=0,
# not a spurious "Reviewer finding" catchall row (#2254).
narrative="$TMP/cursor-specialist-correctness-output.txt"
cat > "$narrative" <<'EOF'
Gathering the diff and reviewing changes... everything looks fine to me.
No specific concerns to raise at this time.
EOF
printf '0\n' > "$narrative.done"
printf 'STATUS=clean\n' > "$narrative.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$narrative" --mode description --timeout 1 --findings-file "$TMP/findings-narrative.md" --oos-file "$TMP/oos-narrative.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=0' <<< "$out"
if grep -Fq 'Reviewer finding' "$TMP/findings-narrative.md" 2>/dev/null; then
    echo "FAIL: narrative-only output produced a Reviewer finding row" >&2
    exit 1
fi
grep -Fq 'STATUS=NOT_SUBSTANTIVE' "$TMP/collector-results.env"
grep -Fq "REVIEWER_FILE=$narrative" "$TMP/collector-results.env"
grep -Fq 'collect-findings.sh claude NOT_SUBSTANTIVE warning (exit 0)' "$TMP/execution-issues.md"

# Corrupted reviewer column: tab in finding title shifts TSV columns (#2265).
# Without the tab-strip fix in flush(), the TSV columns would shift, making
# label="in the title" (not *-output.txt) and the row would be skipped by the
# validation. With the fix, title="Finding with tab in the title", the label
# is the filename (which ends in -output.txt), and the finding IS collected.
# This test verifies the combined fix: tab-stripping prevents corruption so
# the finding is collected normally.
: > "$TMP/execution-issues-tab.md"
tab_file="$TMP/cursor-specialist-edge-cases-output.txt"
printf '### In-Scope Findings\n' > "$tab_file"
printf -- '- Finding with tab\tin the title\n' >> "$tab_file"
printf '0\n' > "$tab_file.done"
printf 'STATUS=clean\n' > "$tab_file.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues-tab.md" \
    "$SCRIPT" --claude-output-files "$tab_file" --mode description --timeout 1 \
    --findings-file "$TMP/findings-tab.md" --oos-file "$TMP/oos-tab.md")
assert_stdout_cap "$out"
# With the tab-strip fix: the tab in the title is replaced with a space, so
# "Finding with tab in the title" becomes one finding with the correct reviewer.
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1: Finding with tab in the title' "$TMP/findings-tab.md"
grep -Fq "cursor-specialist-edge-cases-output.txt" "$TMP/findings-tab.md"
# No invalid-reviewer-column warning should appear (the fix prevents corruption).
if [[ -f "$TMP/execution-issues-tab.md" ]] && grep -Fq 'invalid reviewer column' "$TMP/execution-issues-tab.md"; then
    echo "FAIL: tab-strip fix should prevent reviewer column corruption, not trigger warning" >&2
    cat "$TMP/execution-issues-tab.md" >&2
    exit 1
fi

phase2="$TMP/dyn-api-contract-output-phase2.txt"
cat > "$phase2" <<'EOF'
### In-Scope Findings
- Dynamic fallback finding.
EOF
printf '0\n' > "$phase2.done"
printf 'STATUS=clean\n' > "$phase2.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$phase2" --mode description --timeout 1 --findings-file "$TMP/findings-phase2.md" --oos-file "$TMP/oos-phase2.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq -- '- **Reviewer**: dyn-api-contract-output.txt' "$TMP/findings-phase2.md"

phase2_retry="$TMP/dyn-api-contract-output-phase2-retry.txt"
cat > "$phase2_retry" <<'EOF'
### In-Scope Findings
- Dynamic retry fallback finding.
EOF
printf '0\n' > "$phase2_retry.done"
printf 'STATUS=clean\n' > "$phase2_retry.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$phase2_retry" --mode description --timeout 1 --findings-file "$TMP/findings-phase2-retry.md" --oos-file "$TMP/oos-phase2-retry.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq -- '- **Reviewer**: dyn-api-contract-output.txt' "$TMP/findings-phase2-retry.md"


# bullet-not-a-finding: commit-hash bullets in ## preamble must not become FINDING_N entries
preamble="$TMP/dyn-preamble-output.txt"
cat > "$preamble" <<'EOF'
## Commits since merge-base with main

Merge-base: `7ee70f6130baaf39ec9b58c5be30a0db294ba457`

- `abc1234` Drop post-PR-create push to eliminate duplicate CI runs per PR
- `def5678` Address code review feedback (round 1)

---

### In-Scope Findings
- Missing nil guard in foo.sh:42.
EOF
printf '0\n' > "$preamble.done"
printf 'STATUS=clean\n' > "$preamble.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$preamble" --mode diff --timeout 1 --findings-file "$TMP/findings-preamble.md" --oos-file "$TMP/oos-preamble.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1:' "$TMP/findings-preamble.md"
if grep -Fq 'abc1234' "$TMP/findings-preamble.md"; then
    echo "FAIL: commit hash bullet was promoted to a FINDING entry" >&2
    exit 1
fi
if grep -Fq 'def5678' "$TMP/findings-preamble.md"; then
    echo "FAIL: commit hash bullet was promoted to a FINDING entry" >&2
    exit 1
fi
if grep -Fq '### FINDING_2:' "$TMP/findings-preamble.md"; then
    echo "FAIL: expected exactly 1 finding but found FINDING_2" >&2
    exit 1
fi

# noncanonical-heading-fail-open: generic ## headings must not suppress findings
noncanonical="$TMP/noncanonical-heading-output.txt"
cat > "$noncanonical" <<'EOF'
## Findings
- Real parser issue survives noncanonical heading.
EOF
printf '0\n' > "$noncanonical.done"
printf 'STATUS=clean\n' > "$noncanonical.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$noncanonical" --mode diff --timeout 1 --findings-file "$TMP/findings-noncanonical.md" --oos-file "$TMP/oos-noncanonical.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1: Real parser issue survives noncanonical heading.' "$TMP/findings-noncanonical.md"

# preamble-noncanonical-heading-fail-open: skip state clears on next heading
preamble_noncanonical="$TMP/preamble-noncanonical-heading-output.txt"
cat > "$preamble_noncanonical" <<'EOF'
## Commits since merge-base with main

- `abc1234` Preable commit bullet should not become a finding.

## Findings
- Real bug after merge-base preamble still parses.
EOF
printf '0\n' > "$preamble_noncanonical.done"
printf 'STATUS=clean\n' > "$preamble_noncanonical.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$preamble_noncanonical" --mode diff --timeout 1 --findings-file "$TMP/findings-preamble-noncanonical.md" --oos-file "$TMP/oos-preamble-noncanonical.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1: Real bug after merge-base preamble still parses.' "$TMP/findings-preamble-noncanonical.md"
if grep -Fq 'abc1234' "$TMP/findings-preamble-noncanonical.md"; then
    echo "FAIL: preamble commit bullet leaked through noncanonical heading recovery" >&2
    exit 1
fi

# unknown-third-level-heading-fail-open: unknown ### headings must not trigger skip
unknown_h3="$TMP/unknown-h3-output.txt"
cat > "$unknown_h3" <<'EOF'
### In-Scope Findings
- First finding remains in scope.
### Notes
- Second finding after unknown heading still parses.
EOF
printf '0\n' > "$unknown_h3.done"
printf 'STATUS=clean\n' > "$unknown_h3.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$unknown_h3" --mode description --timeout 1 --findings-file "$TMP/findings-unknown-h3.md" --oos-file "$TMP/oos-unknown-h3.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=2' <<< "$out"
grep -Fq '### FINDING_1: First finding remains in scope.' "$TMP/findings-unknown-h3.md"
grep -Fq '### FINDING_2: Second finding after unknown heading still parses.' "$TMP/findings-unknown-h3.md"

# canonical-3-finding-guard: 3 in-scope + 1 OOS from canonical grammar
canonical3="$TMP/canonical-3-finding-output.txt"
cat > "$canonical3" <<'EOF'
### In-Scope Findings
- First real finding in scripts/foo.sh:10.
- Second real finding in scripts/bar.sh:20.
- Third real finding in scripts/baz.sh:30.

### Out-of-Scope Observations
- Pre-existing issue in scripts/old.sh:5.
EOF
printf '0\n' > "$canonical3.done"
printf 'STATUS=clean\n' > "$canonical3.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$canonical3" --mode description --timeout 1 --findings-file "$TMP/findings-3.md" --oos-file "$TMP/oos-3.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=4' <<< "$out"
grep -Fq 'OOS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1:' "$TMP/findings-3.md"
grep -Fq '### FINDING_2:' "$TMP/findings-3.md"
grep -Fq '### FINDING_3:' "$TMP/findings-3.md"
grep -Fq '[OUT_OF_SCOPE]' "$TMP/oos-3.md"

echo "All assertions passed."
