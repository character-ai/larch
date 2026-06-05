### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: **`SKILL.md` gate fences**: The awk-based `LARCH_CLAUDE_PLUGIN_ROOT` extraction reads from the trusted, larch-written `session-env.sh`. The result is used as a script path — trust boundary is the same as any other larch session file.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`SKILL.md` gate fences**: The awk-based `LARCH_CLAUDE_PLUGIN_ROOT` extraction reads from the trusted, larch-written `session-env.sh`. The result is used as a script path — trust boundary is the same as any other larch session file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: No hard-coded secrets, no new deserialization surfaces, no SSRF-capable URL construction from user input, no path traversal in filesystem operations.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - No hard-coded secrets, no new deserialization surfaces, no SSRF-capable URL construction from user input, no path traversal in filesystem operations.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: **architecture** `skills/design/SKILL.md:315-323` — The design gate fence recovers `CLAUDE_PLUGIN_ROOT` only via `. "$DESIGN_TMPDIR/source-env.sh"`. `write-design-current-env.sh` emits `export CLAUDE_PLUGIN_ROOT=…` only when `$CLAUDE_PLUGIN_ROOT` was set at Step 0a time; if it was absent, `source-env.sh` won't have the key. After sourcing, `"$CLAUDE_PLUGIN_ROOT/scripts/degraded-tools-gate.sh"` expands to `/scripts/degraded-tools-gate.sh` (non-existent) and fails. By contrast, the implement fence has an explicit `plugin-root.env`+awk fallback recovery for exactly this case. The `assert_degraded_tools_gate_fence` in `test-design-structure.sh` pins for `. "$DESIGN_TMPDIR/source-env.sh"` but does not assert that `CLAUDE_PLUGIN_ROOT` becomes non-empty after the source, leaving the gap unpinned. **Suggested fix:** add a recovery line after the source (e.g., `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$DESIGN_TMPDIR/source-env.sh") && export CLAUDE_PLUGIN_ROOT`) and add a corresponding pin in `test-design-structure.sh`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:315-323` — The design gate fence recovers `CLAUDE_PLUGIN_ROOT` only via `. "$DESIGN_TMPDIR/source-env.sh"`. `write-design-current-env.sh` emits `export CLAUDE_PLUGIN_ROOT=…` only when `$CLAUDE_PLUGIN_ROOT` was set at Step 0a time; if it was absent, `source-env.sh` won't have the key. After sourcing, `"$CLAUDE_PLUGIN_ROOT/scripts/degraded-tools-gate.sh"` expands to `/scripts/degraded-tools-gate.sh` (non-existent) and fails. By contrast, the implement fence has an explicit `plugin-root.env`+awk fallback recovery for exactly this case. The `assert_degraded_tools_gate_fence` in `test-design-structure.sh` pins for `. "$DESIGN_TMPDIR/source-env.sh"` but does not assert that `CLAUDE_PLUGIN_ROOT` becomes non-empty after the source, leaving the gap unpinned. **Suggested fix:** add a recovery line after the source (e.g., `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$DESIGN_TMPDIR/source-env.sh") && export CLAUDE_PLUGIN_ROOT`) and add a corresponding pin in `test-design-structure.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: **risk-integration** `scripts/compute-pr-line-counts.sh:50` — `gh api --paginate … 2>/dev/null` has no explicit timeout. For PRs with many files (each page is a round-trip) or GitHub API slowness, this call blocks Step 17 of `write-final-report.sh` for an indeterminate duration with no user-visible indicator. `set +e` makes it non-fatal but latency is uncapped and all error output is swallowed. **Suggested fix:** wrap the `gh api` call in `timeout 30 gh api …` (or equivalent) inside `compute-pr-line-counts.sh` so the unavailable path is reached promptly on slowness.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **risk-integration** `scripts/compute-pr-line-counts.sh:50` — `gh api --paginate … 2>/dev/null` has no explicit timeout. For PRs with many files (each page is a round-trip) or GitHub API slowness, this call blocks Step 17 of `write-final-report.sh` for an indeterminate duration with no user-visible indicator. `set +e` makes it non-fatal but latency is uncapped and all error output is swallowed. **Suggested fix:** wrap the `gh api` call in `timeout 30 gh api …` (or equivalent) inside `compute-pr-line-counts.sh` so the unavailable path is reached promptly on slowness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: **correctness** `scripts/compute-pr-line-counts.sh:33` — `--pr-number` is accepted without numeric validation. Any non-empty, non-`"0"` value (e.g., `"abc"`) passes the early-skip guard (`[ -z ... ] || [ ... = "0" ]`), constructs `repos/.../pulls/abc/files`, and reaches `gh api` which fails silently (`2>/dev/null`), returning `LINES_STATUS=unavailable`. The caller (`write-final-report.sh:119`) uses `${PR_NUMBER:-0}`, which only substitutes `"0"` for an *empty* `PR_NUMBER`, not for a malformed one. The skip logic is therefore incomplete. **Suggested fix:** extend the skip guard: `case "$PR_NUMBER" in '' | 0 | *[!0-9]*) printf 'LINES_STATUS=skipped\nREASON=no-pr\n'; exit 0 ;; esac`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **correctness** `scripts/compute-pr-line-counts.sh:33` — `--pr-number` is accepted without numeric validation. Any non-empty, non-`"0"` value (e.g., `"abc"`) passes the early-skip guard (`[ -z ... ] || [ ... = "0" ]`), constructs `repos/.../pulls/abc/files`, and reaches `gh api` which fails silently (`2>/dev/null`), returning `LINES_STATUS=unavailable`. The caller (`write-final-report.sh:119`) uses `${PR_NUMBER:-0}`, which only substitutes `"0"` for an *empty* `PR_NUMBER`, not for a malformed one. The skip logic is therefore incomplete. **Suggested fix:** extend the skip guard: `case "$PR_NUMBER" in '' | 0 | *[!0-9]*) printf 'LINES_STATUS=skipped\nREASON=no-pr\n'; exit 0 ;; esac`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: - **architecture** `scripts/write-design-current-env.sh` — Plan requires preserving all four gate keys during refresh, but the implementation also adds `validate_bool codex-binary-found "$CODEX_BINARY_FOUND"` / `validate_bool cursor-binary-found "$CURSOR_BINARY_FOUND"`. If `validate_bool` rejects empty strings, a no-flag refresh on a session env that lacks those keys (e.g., a pre-#3514 `/design` session) would fail: the recovery loop returns empty when the prior file has no such key, and `validate_bool` would then exit 1 before any write occurs. The test Case 13 only seeds/verifies the happy path where both keys are present. **Suggested fix:** confirm `validate_bool` allows empty (if so, add a self-test that seeds a prior env file without `CODEX_BINARY_FOUND`, performs a no-flag refresh, and verifies the script exits 0 and writes the other keys correctly).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. - **architecture** `scripts/write-design-current-env.sh` — Plan requires preserving all four gate keys during refresh, but the implementation also adds `validate_bool codex-binary-found "$CODEX_BINARY_FOUND"` / `validate_bool cursor-binary-found "$CURSOR_BINARY_FOUND"`. If `validate_bool` rejects empty strings, a no-flag refresh on a session env that lacks those keys (e.g., a pre-#3514 `/design` session) would fail: the recovery loop returns empty when the prior file has no such key, and `validate_bool` would then exit 1 before any write occurs. The test Case 13 only seeds/verifies the happy path where both keys are present. **Suggested fix:** confirm `validate_bool` allows empty (if so, add a self-test that seeds a prior env file without `CODEX_BINARY_FOUND`, performs a no-flag refresh, and verifies the script exits 0 and writes the other keys correctly).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: `scripts/degraded-tools-gate.sh`: `PRESENCE_INPUT_EMPTY=true` emitted after `BOTH_DOWN` on stdout; `larch_err` diagnostics on stderr only when presence is empty (not for explicit `false`). ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/degraded-tools-gate.sh`: `PRESENCE_INPUT_EMPTY=true` emitted after `BOTH_DOWN` on stdout; `larch_err` diagnostics on stderr only when presence is empty (not for explicit `false`). ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: `scripts/test-degraded-tools-gate.sh`: all required cases present — all-empty (5a, stdout/stderr separated), one-empty (5b), explicit-false non-signal (5c), omitted-with-empty-env (5d), omitted-with-nonempty-env WARNING (5e), whitespace non-signal (5f), healthy regression pin (Case 1). ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/test-degraded-tools-gate.sh`: all required cases present — all-empty (5a, stdout/stderr separated), one-empty (5b), explicit-false non-signal (5c), omitted-with-empty-env (5d), omitted-with-nonempty-env WARNING (5e), whitespace non-signal (5f), healthy regression pin (Case 1). ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: - **code-quality** `scripts/test-design-structure.sh:112` — **Nit**: The negative pin `grep -Fq 'After the presence parse above' "$SKILL_MD"` searches the entire SKILL.md file rather than the extracted `$tmp` fence region. A future contributor who adds that phrase in an unrelated step or comment would get a confusing spurious failure with no connection to the gate fence. **Suggested fix:** Change to `grep -Fq 'After the presence parse above' "$tmp"` to scope the check to the already-extracted bash fence (or use the `region` variable); the old wording only needs to be absent from the gate paragraph, not the entire document.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. - **code-quality** `scripts/test-design-structure.sh:112` — **Nit**: The negative pin `grep -Fq 'After the presence parse above' "$SKILL_MD"` searches the entire SKILL.md file rather than the extracted `$tmp` fence region. A future contributor who adds that phrase in an unrelated step or comment would get a confusing spurious failure with no connection to the gate fence. **Suggested fix:** Change to `grep -Fq 'After the presence parse above' "$tmp"` to scope the check to the already-extracted bash fence (or use the `region` variable); the old wording only needs to be absent from the gate paragraph, not the entire document. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: `skills/implement/SKILL.md` gate fence: root/tmpdir prelude, four `read-session-env-key.sh --file "$IMPLEMENT_TMPDIR/session-env.sh" --key X --default "false"` reads, gate invocation with all four operands; "from the bootstrap parse above" is gone. ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/implement/SKILL.md` gate fence: root/tmpdir prelude, four `read-session-env-key.sh --file "$IMPLEMENT_TMPDIR/session-env.sh" --key X --default "false"` reads, gate invocation with all four operands; "from the bootstrap parse above" is gone. ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: `scripts/test-implement-structure.sh`: `assert_degraded_tools_gate_fence()` pins all 13 required tokens in the extracted fence, includes negative pin for "from the bootstrap parse above". ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/test-implement-structure.sh`: `assert_degraded_tools_gate_fence()` pins all 13 required tokens in the extracted fence, includes negative pin for "from the bootstrap parse above". ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: `skills/design/SKILL.md` gate fence: `export DESIGN_TMPDIR="${DESIGN_TMPDIR:?…}"`, `. "$DESIGN_TMPDIR/source-env.sh"`, gate invocation with `${CODEX_PRESENT:-false}` / `${CURSOR_PRESENT:-false}` / `${CODEX_BINARY_FOUND:-false}` / `${CURSOR_BINARY_FOUND:-false}`. ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/design/SKILL.md` gate fence: `export DESIGN_TMPDIR="${DESIGN_TMPDIR:?…}"`, `. "$DESIGN_TMPDIR/source-env.sh"`, gate invocation with `${CODEX_PRESENT:-false}` / `${CURSOR_PRESENT:-false}` / `${CODEX_BINARY_FOUND:-false}` / `${CURSOR_BINARY_FOUND:-false}`. ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `scripts/test-design-structure.sh`: `assert_degraded_tools_gate_fence()` verifies source line, DESIGN_TMPDIR prelude, all four flag operands, and negative pin for old prose. ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/test-design-structure.sh`: `assert_degraded_tools_gate_fence()` verifies source line, DESIGN_TMPDIR prelude, all four flag operands, and negative pin for old prose. ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: `scripts/write-design-current-env.sh`: `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` added to the recovery loop (now six keys). ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/write-design-current-env.sh`: `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` added to the recovery loop (now six keys). ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: `skills/design/scripts/test-write-design-current-env.sh` Case 13: seeds and asserts all four gate keys including binary-found. ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/design/scripts/test-write-design-current-env.sh` Case 13: seeds and asserts all four gate keys including binary-found. ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_26: `skills/shared/external-reviewers.md`: separate-block rehydration rule and `PRESENCE_INPUT_EMPTY=true` violation symptom documented. ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/shared/external-reviewers.md`: separate-block rehydration rule and `PRESENCE_INPUT_EMPTY=true` violation symptom documented. ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_27: `scripts/degraded-tools-gate.md`: empty-input signal documented, shard reference corrected from `test-harnesses-1` to `test-harnesses-4`. ✅  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/degraded-tools-gate.md`: empty-input signal documented, shard reference corrected from `test-harnesses-1` to `test-harnesses-4`. ✅
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_28: `/research` and `/review` gate call sites: not modified. ✅
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `/research` and `/review` gate call sites: not modified. ✅ ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	latent	correctness	scripts/write-design-current-env.sh	validate_bool called with potentially-empty CODEX_BINARY_FOUND / CURSOR_BINARY_FOUND after no-flag refresh on a legacy session env lacking those keys	If validate_bool rejects empty, a design refresh on any session created before CODEX_BINARY_FOUND was written will fail before writing; test Case 13 only covers the populated case	Confirm validate_bool allows empty; add a Case 13-variant that omits binary-found keys from the prior env and verifies exit 0 and correct output 1	in_scope	nit	architecture	scripts/compute-pr-line-counts.sh scripts/render-run-summary.sh skills/implement/scripts/write-final-report.sh (and siblings)	PR-line-count feature (#3506) bundled onto the #3514 branch adds hundreds of lines not in the #3514 plan	Plan states diff_added:190 but actual diff is substantially larger due to these additions; makes PR diff harder to scope-check against #3514 acceptance criteria	If intentional carry-along, note in PR description; otherwise move to a separate branch ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: **architecture** `skills/implement/SKILL.md` (gate fence, approx. lines 330–355 of the added block) — The `if/elif/fi` block that resolves `CLAUDE_PLUGIN_ROOT` from disk has no fail-fast guard after the block. If both `$IMPLEMENT_TMPDIR/plugin-root.env` is absent AND `session-env.sh` either is absent or lacks `LARCH_CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT` remains empty or unset. The four subsequent `read-session-env-key.sh` command-substitutions then expand as `$(""/scripts/read-session-env-key.sh ...)`, silently return empty strings on command-not-found (no `set -e` in a `$(...)` subshell), and all four presence flags stay empty — triggering `PRESENCE_INPUT_EMPTY=true BOTH_DOWN=true` and the interactive `AskUserQuestion` prompt, reproducing the original false-positive through a different root cause. The `"${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"` guard at the top of the same fence demonstrates the correct fail-fast discipline for required variables; `CLAUDE_PLUGIN_ROOT` receives no equivalent guard, and `test-implement-structure.sh` only pins that `'export CLAUDE_PLUGIN_ROOT'` is present in the fence text — not that a non-empty guard exists. **Suggested fix:** After the `if/elif/fi` block, add `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || { printf 'ERROR: CLAUDE_PLUGIN_ROOT unresolvable — plugin-root.env and session-env.sh both absent or missing key\n' >&2; exit 1; }` and add a corresponding structural pin in `assert_degraded_tools_gate_fence` (e.g. `grep -Fq 'CLAUDE_PLUGIN_ROOT:-}' "$tmp"`).
- **Reviewer**: dyn-skill-fences-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md` (gate fence, approx. lines 330–355 of the added block) — The `if/elif/fi` block that resolves `CLAUDE_PLUGIN_ROOT` from disk has no fail-fast guard after the block. If both `$IMPLEMENT_TMPDIR/plugin-root.env` is absent AND `session-env.sh` either is absent or lacks `LARCH_CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT` remains empty or unset. The four subsequent `read-session-env-key.sh` command-substitutions then expand as `$(""/scripts/read-session-env-key.sh ...)`, silently return empty strings on command-not-found (no `set -e` in a `$(...)` subshell), and all four presence flags stay empty — triggering `PRESENCE_INPUT_EMPTY=true BOTH_DOWN=true` and the interactive `AskUserQuestion` prompt, reproducing the original false-positive through a different root cause. The `"${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"` guard at the top of the same fence demonstrates the correct fail-fast discipline for required variables; `CLAUDE_PLUGIN_ROOT` receives no equivalent guard, and `test-implement-structure.sh` only pins that `'export CLAUDE_PLUGIN_ROOT'` is present in the fence text — not that a non-empty guard exists. **Suggested fix:** After the `if/elif/fi` block, add `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || { printf 'ERROR: CLAUDE_PLUGIN_ROOT unresolvable — plugin-root.env and session-env.sh both absent or missing key\n' >&2; exit 1; }` and add a corresponding structural pin in `assert_degraded_tools_gate_fence` (e.g. `grep -Fq 'CLAUDE_PLUGIN_ROOT:-}' "$tmp"`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: - **code-quality** `scripts/test-degraded-tools-gate.sh:87-96` — Case 5a creates `_empty_all_err` via `mktemp` and removes it with a bare `rm -f`, but does not add it to the harness `trap` cleanup. Because `assert_*` functions accumulate `FAIL` without early-exit, the `rm -f` is always reached in practice, but the pattern is inconsistent with the standard for temporary file lifetime in this script. **Suggested fix:** Add `"$_empty_all_err"` to the existing trap cleanup or declare it before the trap and include it there, matching the pattern used by other per-case temps.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. - **code-quality** `scripts/test-degraded-tools-gate.sh:87-96` — Case 5a creates `_empty_all_err` via `mktemp` and removes it with a bare `rm -f`, but does not add it to the harness `trap` cleanup. Because `assert_*` functions accumulate `FAIL` without early-exit, the `rm -f` is always reached in practice, but the pattern is inconsistent with the standard for temporary file lifetime in this script. **Suggested fix:** Add `"$_empty_all_err"` to the existing trap cleanup or declare it before the trap and include it there, matching the pattern used by other per-case temps.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: **`compute-pr-line-counts.sh`**: `REPO` and `PR_NUMBER` are composed into `endpoint="repos/${REPO}/pulls/${PR_NUMBER}/files"` and passed double-quoted to `gh api`. No shell word-splitting or injection because the endpoint is a single double-quoted argument. `REPO` originates from larch session-env (validated `OWNER/REPO` format by `resolve-repo.sh` upstream). The awk consumer uses `+ 0` coercion and integer `%d` formatting, so any corrupt numeric field yields 0 — no display injection. The downstream integer validation in `render-run-summary.sh` (`*[!0-9]*` case pattern) provides a second guard before interpolation into the display string.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`compute-pr-line-counts.sh`**: `REPO` and `PR_NUMBER` are composed into `endpoint="repos/${REPO}/pulls/${PR_NUMBER}/files"` and passed double-quoted to `gh api`. No shell word-splitting or injection because the endpoint is a single double-quoted argument. `REPO` originates from larch session-env (validated `OWNER/REPO` format by `resolve-repo.sh` upstream). The awk consumer uses `+ 0` coercion and integer `%d` formatting, so any corrupt numeric field yields 0 — no display injection. The downstream integer validation in `render-run-summary.sh` (`*[!0-9]*` case pattern) provides a second guard before interpolation into the display string.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: **`degraded-tools-gate.sh` error messages**: The new `larch_err` calls emit fully static string literals. No user-controlled content is interpolated into the diagnostic text.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`degraded-tools-gate.sh` error messages**: The new `larch_err` calls emit fully static string literals. No user-controlled content is interpolated into the diagnostic text.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: **`write-design-current-env.sh`**: The `validate_bool` calls added for `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND` correctly enforce `true`/`false` values before writing to the env file.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`write-design-current-env.sh`**: The `validate_bool` calls added for `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND` correctly enforce `true`/`false` values before writing to the env file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

