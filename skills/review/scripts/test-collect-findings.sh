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
# collect-findings pins LARCH_QUIET_DISABLE=1 on the collector so §3.8 larch_err lines reach the tee.
# shellcheck disable=SC2016 # single-quoted grep literal matches unexpanded "$PLUGIN_ROOT" in source
if ! grep -Fq 'LARCH_QUIET_DISABLE=1 "$PLUGIN_ROOT/scripts/collect-agent-results.sh"' "$SCRIPT"; then
    echo "FAIL: collect-findings.sh must run collector with LARCH_QUIET_DISABLE=1 for stderr-tail tee" >&2
    exit 1
fi
# shellcheck disable=SC2016 # single-quoted grep literal matches unexpanded "$collector_stderr" in source
if ! grep -Fq 'collect-agent-results.stderr' "$SCRIPT"; then
    echo "FAIL: collect-findings.sh must capture collector stderr for §3.8 replay to FD 2/4" >&2
    exit 1
fi
# Failed external slots: collector stderr tails on FD 2 when collector_rc=0 (mirrors collect-findings tee path).
COLLECTOR="$REPO_ROOT/scripts/collect-agent-results.sh"
ext_fail_a="$TMP/codex-generalist-fail-a.txt"
ext_fail_b="$TMP/cursor-specialist-fail-b.txt"
: > "$ext_fail_a"
: > "$ext_fail_b"
printf '1\n' > "${ext_fail_a}.done"
printf '1\n' > "${ext_fail_b}.done"
printf 'non-transient failure\n' > "${ext_fail_a}.diag"
printf 'non-transient failure\n' > "${ext_fail_b}.diag"
printf 'external stderr tail alpha\n' > "${ext_fail_a}.stderr-tail"
printf 'external stderr tail beta\n' > "${ext_fail_b}.stderr-tail"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
    LARCH_QUIET_DISABLE=1 "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode \
    "$ext_fail_a" "$ext_fail_b" >"$TMP/ext-fail.stdout" 2>"$TMP/ext-fail-collector.stderr"
if grep -Fq 'failed agent stderr tail' "$TMP/ext-fail-collector.stderr" \
    && grep -Fq 'external stderr tail alpha' "$TMP/ext-fail-collector.stderr"; then
    :
else
    echo "FAIL: collector should emit stderr tails to FD 2 under LARCH_QUIET_DISABLE=1" >&2
    cat "$TMP/ext-fail-collector.stderr" >&2
    exit 1
fi
# E2E: collect-findings wrapper surfaces §3.8 tails on captured stderr when collector_rc=0.
set +e
cf_out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 LARCH_QUIET_DISABLE=1 "$SCRIPT" \
    --external-output-files "$ext_fail_a" --mode diff --timeout 5 \
    --findings-file "$TMP/findings-cf-fail.md" --oos-file "$TMP/oos-cf-fail.md" 2>"$TMP/cf-fail-wrapper.stderr")
cf_wrapper_rc=$?
set -e
assert_stdout_cap "$cf_out"
[[ "$cf_wrapper_rc" -eq 0 ]] || { echo "FAIL: collect-findings E2E exit $cf_wrapper_rc" >&2; exit 1; }
if grep -Fq 'failed agent stderr tail' "$TMP/cf-fail-wrapper.stderr" \
    && grep -Fq 'external stderr tail alpha' "$TMP/cf-fail-wrapper.stderr"; then
    :
else
    echo "FAIL: collect-findings.sh must tee §3.8 stderr tails to wrapper stderr when collector_rc=0" >&2
    echo "wrapper stderr:" >&2
    cat "$TMP/cf-fail-wrapper.stderr" >&2
    echo "captured collector stderr:" >&2
    cat "$TMP/collect-agent-results.stderr" 2>/dev/null >&2
    exit 1
fi
# Replay fallback: empty collector stderr capture + pre-planted sidecars still reach wrapper FD 2.
replay_a="$TMP/replay-fail-a.txt"
replay_b="$TMP/replay-fail-b.txt"
: > "$replay_a"
: > "$replay_b"
printf '1\n' > "${replay_a}.done"
printf '1\n' > "${replay_b}.done"
printf 'non-transient failure\n' > "${replay_a}.diag"
printf 'non-transient failure\n' > "${replay_b}.diag"
printf 'replay stderr tail alpha\n' > "${replay_a}.stderr-tail"
printf 'replay stderr tail beta\n' > "${replay_b}.stderr-tail"
: > "$TMP/replay-collector.stderr"
LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0 RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
    LARCH_QUIET_DISABLE=1 "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode \
    "$replay_a" "$replay_b" >"$TMP/replay-collector.stdout" 2>"$TMP/replay-collector.stderr"
if grep -Fq 'failed agent stderr tail' "$TMP/replay-collector.stderr"; then
    echo "FAIL: collector should not emit tails when LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0" >&2
    cat "$TMP/replay-collector.stderr" >&2
    exit 1
fi
set +e
cf_replay_out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 LARCH_QUIET_DISABLE=1 "$SCRIPT" \
    --external-output-files "$replay_a" --mode diff --timeout 5 \
    --findings-file "$TMP/findings-cf-replay.md" --oos-file "$TMP/oos-cf-replay.md" 2>"$TMP/cf-replay-wrapper.stderr")
cf_replay_rc=$?
set -e
assert_stdout_cap "$cf_replay_out"
[[ "$cf_replay_rc" -eq 0 ]] || { echo "FAIL: collect-findings replay E2E exit $cf_replay_rc" >&2; exit 1; }
if grep -Fq 'failed agent stderr tail' "$TMP/cf-replay-wrapper.stderr" \
    && grep -Fq 'replay stderr tail alpha' "$TMP/cf-replay-wrapper.stderr"; then
    :
else
    echo "FAIL: collect-findings replay must surface planted stderr tails when collector stderr is empty" >&2
    cat "$TMP/cf-replay-wrapper.stderr" >&2
    exit 1
fi
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

# Bold-markdown OOS bullets normalize to short titles (#2417).
bold_oos="$TMP/cursor-dynamic-oos-output.txt"
cat > "$bold_oos" <<'EOF'
### In-Scope Findings
- In-scope only.

### Out-of-Scope Observations
- **risk-integration** — [`scripts/foo.sh`](https://example.com/doc) docs drift note.
- **code-quality** — prose-only note without a file link.
EOF
printf '0\n' > "$bold_oos.done"
printf 'STATUS=clean\n' > "$bold_oos.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$bold_oos" --mode description --timeout 1 --findings-file "$TMP/findings-bold-oos.md" --oos-file "$TMP/oos-bold-oos.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=3' <<< "$out"
grep -Fq 'OOS_COUNT=2' <<< "$out"
grep -Eq '^### FINDING_[0-9]+: \[OUT_OF_SCOPE\] risk-integration: scripts/foo\.sh$' "$TMP/findings-bold-oos.md" \
    || { echo "FAIL: expected normalized OOS title in findings" >&2; cat "$TMP/findings-bold-oos.md" >&2; exit 1; }
grep -Eq '^### FINDING_[0-9]+: \[OUT_OF_SCOPE\] code-quality$' "$TMP/findings-bold-oos.md" \
    || { echo "FAIL: expected category-only normalized OOS title in findings" >&2; cat "$TMP/findings-bold-oos.md" >&2; exit 1; }
if grep -Eq '^### FINDING_[0-9]+: \[OUT_OF_SCOPE\] \*\*' "$TMP/findings-bold-oos.md"; then
    echo "FAIL: OOS titles should not keep bold-markdown prefix" >&2
    exit 1
fi

# Severity-first OOS bullets (e.g. **Latent** `category` `file`) must NOT be normalized (#2417).
sev_oos="$TMP/cursor-sev-oos-output.txt"
cat > "$sev_oos" <<'EOF'
### In-Scope Findings
- In-scope only.

### Out-of-Scope Observations
- **Latent** `code-quality` `scripts/old.sh:5` Pre-existing issue not introduced by this diff.
EOF
printf '0\n' > "$sev_oos.done"
printf 'STATUS=clean\n' > "$sev_oos.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$sev_oos" --mode description --timeout 1 --findings-file "$TMP/findings-sev-oos.md" --oos-file "$TMP/oos-sev-oos.md")
assert_stdout_cap "$out"
grep -Fq 'OOS_COUNT=1' <<< "$out"
# Severity token "Latent" must NOT become a category label — title must keep the full text or be left as-is.
grep -Fq '[OUT_OF_SCOPE] Latent' "$TMP/findings-sev-oos.md" && {
    echo "FAIL: severity-first OOS bullet was incorrectly normalized to '[OUT_OF_SCOPE] Latent'" >&2
    cat "$TMP/findings-sev-oos.md" >&2
    exit 1
}
grep -Fq '[OUT_OF_SCOPE] **Latent**' "$TMP/findings-sev-oos.md" \
    || { echo "FAIL: severity-first OOS bullet title should be left intact" >&2; cat "$TMP/findings-sev-oos.md" >&2; exit 1; }

# Collector failure relay strips control bytes (minimal CLAUDE_PLUGIN_ROOT harness).
collector_harness=$(mktemp -d "${TMPDIR:-/tmp}/tcf-collector-harness.XXXXXX")
mkdir -p "$collector_harness/scripts" "$collector_harness/skills/review/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$collector_harness/scripts/"
cp "$REPO_ROOT/scripts/redact-secrets.sh" "$collector_harness/scripts/"
chmod +x "$collector_harness/scripts/"*.sh
cp "$REPO_ROOT/skills/review/scripts/collect-findings.sh" "$collector_harness/skills/review/scripts/"
cat > "$collector_harness/scripts/collect-agent-results.sh" <<'COLLECTOR_RELAY_STUB'
#!/usr/bin/env bash
printf '%b\n' 'HTTP 500\x07Bad Gateway\x1b[31mred\x1b[0m' >&2
exit 1
COLLECTOR_RELAY_STUB
chmod +x "$collector_harness/scripts/collect-agent-results.sh"
external_relay="$TMP/external-relay.txt"
printf 'x\n' > "$external_relay"
collector_review="$TMP/collector-relay-review"
mkdir -p "$collector_review"
set +e
out_collector=$(CLAUDE_PLUGIN_ROOT="$collector_harness" REVIEW_TMPDIR="$collector_review" \
    WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
    bash "$collector_harness/skills/review/scripts/collect-findings.sh" \
    --mode description --timeout 1 \
    --external-output-files "$external_relay" \
    --findings-file "$collector_review/findings.md" \
    --oos-file "$collector_review/oos.md" 2>&1)
collector_rc=$?
set -e
[[ "$collector_rc" -ne 0 ]] || { echo "FAIL: collector relay expected non-zero exit" >&2; exit 1; }
grep -Fq 'HTTP 500' <<< "$out_collector" || { echo "FAIL: collector relay missing HTTP 500" >&2; printf '%s\n' "$out_collector" >&2; exit 1; }
grep -Fq 'Bad Gateway' <<< "$out_collector" || { echo "FAIL: collector relay missing Bad Gateway" >&2; exit 1; }
if grep -aF $'\x07' <<< "$out_collector" >/dev/null; then
    echo "FAIL: collector relay still contains BEL" >&2
    exit 1
fi
if grep -aF $'\x1b' <<< "$out_collector" >/dev/null; then
    echo "FAIL: collector relay still contains ESC" >&2
    exit 1
fi

# Wait failure relay strips control bytes (wait-for-claude-reviewers.log path).
wait_harness=$(mktemp -d "${TMPDIR:-/tmp}/tcf-wait-harness.XXXXXX")
mkdir -p "$wait_harness/scripts" "$wait_harness/skills/review/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$wait_harness/scripts/"
cp "$REPO_ROOT/scripts/redact-secrets.sh" "$wait_harness/scripts/"
chmod +x "$wait_harness/scripts/"*.sh
cp "$REPO_ROOT/skills/review/scripts/collect-findings.sh" "$wait_harness/skills/review/scripts/"
cat > "$wait_harness/scripts/wait-for-reviewers.sh" <<'WAIT_RELAY_STUB'
#!/usr/bin/env bash
printf '%b\n' 'HTTP 500\x07Bad Gateway\x1b[31mred\x1b[0m' >&2
exit 1
WAIT_RELAY_STUB
chmod +x "$wait_harness/scripts/wait-for-reviewers.sh"
claude_wait="$TMP/claude-wait-relay.txt"
cat > "$claude_wait" <<'EOF'
### In-Scope Findings
- relay case finding.
EOF
printf '0\n' > "${claude_wait}.done"
printf 'STATUS=clean\n' > "${claude_wait}.dirty-tree"
wait_review="$TMP/wait-relay-review"
mkdir -p "$wait_review"
set +e
out_wait=$(CLAUDE_PLUGIN_ROOT="$wait_harness" REVIEW_TMPDIR="$wait_review" \
    WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
    bash "$wait_harness/skills/review/scripts/collect-findings.sh" \
    --mode description --timeout 1 \
    --claude-output-files "$claude_wait" \
    --findings-file "$wait_review/findings.md" \
    --oos-file "$wait_review/oos.md" 2>&1)
wait_rc=$?
set -e
[[ "$wait_rc" -ne 0 ]] || { echo "FAIL: wait relay expected non-zero exit" >&2; exit 1; }
grep -Fq 'HTTP 500' <<< "$out_wait" || { echo "FAIL: wait relay missing HTTP 500" >&2; printf '%s\n' "$out_wait" >&2; exit 1; }
grep -Fq 'Bad Gateway' <<< "$out_wait" || { echo "FAIL: wait relay missing Bad Gateway" >&2; exit 1; }
if grep -aF $'\x07' <<< "$out_wait" >/dev/null; then
    echo "FAIL: wait relay still contains BEL" >&2
    exit 1
fi
if grep -aF $'\x1b' <<< "$out_wait" >/dev/null; then
    echo "FAIL: wait relay still contains ESC" >&2
    exit 1
fi

echo "All assertions passed."
