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

echo "All assertions passed."
