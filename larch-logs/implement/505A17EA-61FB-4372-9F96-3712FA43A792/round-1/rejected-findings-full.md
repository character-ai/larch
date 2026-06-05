### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: **code-quality** `scripts/test-compute-pr-line-counts.sh:35-52` and `skills/implement/scripts/test-write-final-report.sh:62-79` — The `gh` shim heredoc body is byte-for-byte identical between the two files, including fixture filenames and tab-separated row values. If the shim behavior needs updating (e.g., to cover a new API shape), it must be changed in two places. **Suggested fix:** factor the shim into a shared fixture file (e.g., `scripts/test-fixtures/gh-shim.sh`) and source it in both harnesses, or at minimum add a comment pointing to the sibling file.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **code-quality** `scripts/test-compute-pr-line-counts.sh:35-52` and `skills/implement/scripts/test-write-final-report.sh:62-79` — The `gh` shim heredoc body is byte-for-byte identical between the two files, including fixture filenames and tab-separated row values. If the shim behavior needs updating (e.g., to cover a new API shape), it must be changed in two places. **Suggested fix:** factor the shim into a shared fixture file (e.g., `scripts/test-fixtures/gh-shim.sh`) and source it in both harnesses, or at minimum add a comment pointing to the sibling file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_18: **correctness** `scripts/test-implement-structure.sh:assert_degraded_tools_gate_fence` — **Nit** — The early-fail paths `[[ -n "$region" ]] || fail "…"` (line ~50) and `[[ -s "$tmp" ]] || fail "…"` (line ~60) call `fail()` (which calls `exit 1`) without cleaning up `$tmp` and `$tmp.region` first. The cleanup `rm -f "$tmp" "$tmp.region"` only appears at function end and on the needle-loop failure branch. **Suggested fix:** add `rm -f "$tmp" "$tmp.region"` before each early `fail` call, or use a `trap` inside the function.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **correctness** `scripts/test-implement-structure.sh:assert_degraded_tools_gate_fence` — **Nit** — The early-fail paths `[[ -n "$region" ]] || fail "…"` (line ~50) and `[[ -s "$tmp" ]] || fail "…"` (line ~60) call `fail()` (which calls `exit 1`) without cleaning up `$tmp` and `$tmp.region` first. The cleanup `rm -f "$tmp" "$tmp.region"` only appears at function end and on the needle-loop failure branch. **Suggested fix:** add `rm -f "$tmp" "$tmp.region"` before each early `fail` call, or use a `trap` inside the function.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **`scripts/degraded-tools-gate.sh` — new empty-presence detection.** The two new `larch_err` calls emit fully hardcoded strings; no user-controlled data is interpolated. The `PRESENCE_INPUT_EMPTY` KV uses a literal `true`. No injection vector.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`scripts/degraded-tools-gate.sh` — new empty-presence detection.** The two new `larch_err` calls emit fully hardcoded strings; no user-controlled data is interpolated. The `PRESENCE_INPUT_EMPTY` KV uses a literal `true`. No injection vector.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **`scripts/compute-pr-line-counts.sh` — new script.** `PR_NUMBER` and `REPO` are double-quoted throughout (`"$endpoint"`), preventing word-splitting/glob injection. Even with a non-integer `PR_NUMBER`, the failure path is handled: `gh api` returns non-zero, `gh_rc != 0` triggers `LINES_STATUS=unavailable`, and the caller never aborts. The awk `END` block uses `printf "%d"` for all counters, so attacker-supplied additions/deletions fields from the API response can only produce integers in the output KV. Temp-file cleanup via `mktemp` + EXIT trap is correct; the `trap - EXIT` + explicit `rm` on the clean path avoids double-deletion.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`scripts/compute-pr-line-counts.sh` — new script.** `PR_NUMBER` and `REPO` are double-quoted throughout (`"$endpoint"`), preventing word-splitting/glob injection. Even with a non-integer `PR_NUMBER`, the failure path is handled: `gh api` returns non-zero, `gh_rc != 0` triggers `LINES_STATUS=unavailable`, and the caller never aborts. The awk `END` block uses `printf "%d"` for all counters, so attacker-supplied additions/deletions fields from the API response can only produce integers in the output KV. Temp-file cleanup via `mktemp` + EXIT trap is correct; the `trap - EXIT` + explicit `rm` on the clean path avoids double-deletion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **`scripts/write-design-current-env.sh` — binary-found key preservation.** The new for-loop uses `${!_recover_key}` indirect expansion, but `_recover_key` is sourced only from a hardcoded list of six safe identifiers. The `recover_prior_bool_value` grep pattern `^export ${key}=(true|false)$` enforces anchored matching; `${line#*=}` strips the prefix to yield only `true`/`false`; the follow-up `validate_bool` calls reject anything else. No injection path.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`scripts/write-design-current-env.sh` — binary-found key preservation.** The new for-loop uses `${!_recover_key}` indirect expansion, but `_recover_key` is sourced only from a hardcoded list of six safe identifiers. The `recover_prior_bool_value` grep pattern `^export ${key}=(true|false)$` enforces anchored matching; `${line#*=}` strips the prefix to yield only `true`/`false`; the follow-up `validate_bool` calls reject anything else. No injection path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **`skills/implement/SKILL.md` / `skills/design/SKILL.md` fence changes.** The rehydrated values are passed as quoted shell arguments to the gate script, not evaluated as code. The `${CODEX_PRESENT:-false}` expansions in the design fence only produce `false` on empty, not arbitrary shell.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`skills/implement/SKILL.md` / `skills/design/SKILL.md` fence changes.** The rehydrated values are passed as quoted shell arguments to the gate script, not evaluated as code. The `${CODEX_PRESENT:-false}` expansions in the design fence only produce `false` on empty, not arbitrary shell.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **`skills/implement/scripts/write-final-report.sh` — PR line counts.** Data flows: `gh api` → awk (`%d`-formatted integers) → KV blob → `read_lines_kv` (awk field parse, key is hardcoded) → four integer variables → nested POSIX `case` integer guards → display-only `printf`. No point in this chain executes user-supplied data as code or shell.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`skills/implement/scripts/write-final-report.sh` — PR line counts.** Data flows: `gh api` → awk (`%d`-formatted integers) → KV blob → `read_lines_kv` (awk field parse, key is hardcoded) → four integer variables → nested POSIX `case` integer guards → display-only `printf`. No point in this chain executes user-supplied data as code or shell.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: **Test harness gh shims.** Standard test pattern: a stub binary written to a mktemp directory, prepended to PATH with `export`, using `${GH_SHIM_LOG:?}` to require the env var to be set. No security concern in test-only code.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Test harness gh shims.** Standard test pattern: a stub binary written to a mktemp directory, prepended to PATH with `export`, using `${GH_SHIM_LOG:?}` to require the env var to be set. No security concern in test-only code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: **Secret scanning.** No hard-coded secrets, tokens, or credentials introduced. Error messages name only flag identifiers and bug class descriptions.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secret scanning.** No hard-coded secrets, tokens, or credentials introduced. Error messages name only flag identifiers and bug class descriptions. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: **Nit** `correctness` `scripts/test-degraded-tools-gate.sh:94-97` (Case 5b) — Case 5b uses `2>&1` (merged streams) and asserts `PRESENCE_INPUT_EMPTY=true` appears in the merged output; the plan asked that in merged-output cases the stderr diagnostic substrings be exercised. The assertion `assert_contains "$out" "PRESENCE_INPUT_EMPTY=true"` is satisfied whether the KV appears on stdout or stderr, so the stdout-only invariant for that KV is only proven by Case 5a (the split case). This is a weak test for the merged case but the split case covers the separation contract; not a blocking gap. **Suggested fix:** No change required; Case 5a provides the authoritative stream-separation proof.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Nit** `correctness` `scripts/test-degraded-tools-gate.sh:94-97` (Case 5b) — Case 5b uses `2>&1` (merged streams) and asserts `PRESENCE_INPUT_EMPTY=true` appears in the merged output; the plan asked that in merged-output cases the stderr diagnostic substrings be exercised. The assertion `assert_contains "$out" "PRESENCE_INPUT_EMPTY=true"` is satisfied whether the KV appears on stdout or stderr, so the stdout-only invariant for that KV is only proven by Case 5a (the split case). This is a weak test for the merged case but the split case covers the separation contract; not a blocking gap. **Suggested fix:** No change required; Case 5a provides the authoritative stream-separation proof. --- All plan-required deliverables are present and correctly implemented:
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_31: `degraded-tools-gate.sh`: empty-presence detection (`[[ -z "${CODEX_PRESENT:-}" ]]`) fires before normalization; `PRESENCE_INPUT_EMPTY=true` emitted after `BOTH_DOWN` only when true; valid-input stdout byte-identical ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `degraded-tools-gate.sh`: empty-presence detection (`[[ -z "${CODEX_PRESENT:-}" ]]`) fires before normalization; `PRESENCE_INPUT_EMPTY=true` emitted after `BOTH_DOWN` only when true; valid-input stdout byte-identical ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_32: `degraded-tools-gate.md`: Caller contract extended; `PRESENCE_INPUT_EMPTY=true` KV documented; shard reference corrected to `test-harnesses-4` ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `degraded-tools-gate.md`: Caller contract extended; `PRESENCE_INPUT_EMPTY=true` KV documented; shard reference corrected to `test-harnesses-4` ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_33: `test-degraded-tools-gate.sh`: All required cases (5a all-empty/split streams, 5b one-empty/merged, 5c explicit-false non-signal, 5d omitted-with-empty-env, Case 1 regression pin) ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `test-degraded-tools-gate.sh`: All required cases (5a all-empty/split streams, 5b one-empty/merged, 5c explicit-false non-signal, 5d omitted-with-empty-env, Case 1 regression pin) ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_34: `skills/implement/SKILL.md`: Self-contained fence with root/tmpdir prelude + four `read-session-env-key.sh` reads + gate invocation; "from the bootstrap parse above" removed ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/implement/SKILL.md`: Self-contained fence with root/tmpdir prelude + four `read-session-env-key.sh` reads + gate invocation; "from the bootstrap parse above" removed ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_35: `skills/design/SKILL.md`: Sources `$DESIGN_TMPDIR/source-env.sh` then passes four `${VAR:-false}` flags ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/design/SKILL.md`: Sources `$DESIGN_TMPDIR/source-env.sh` then passes four `${VAR:-false}` flags ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_36: `scripts/write-design-current-env.sh`: `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` added to recovery loop and validation ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `scripts/write-design-current-env.sh`: `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` added to recovery loop and validation ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_37: `test-write-design-current-env.sh` Case 13: asserts all six gate keys survive no-flag refresh ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `test-write-design-current-env.sh` Case 13: asserts all six gate keys survive no-flag refresh ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_38: `skills/shared/external-reviewers.md`: Separate-block rehydration rule added; `PRESENCE_INPUT_EMPTY=true` named as violation symptom ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `skills/shared/external-reviewers.md`: Separate-block rehydration rule added; `PRESENCE_INPUT_EMPTY=true` named as violation symptom ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_39: `test-implement-structure.sh`: `assert_degraded_tools_gate_fence` scoped to gate region; checks all four assignments, four operands, prelude tokens, and negative pin ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `test-implement-structure.sh`: `assert_degraded_tools_gate_fence` scoped to gate region; checks all four assignments, four operands, prelude tokens, and negative pin ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_40

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_40: `test-design-structure.sh`: `assert_degraded_tools_gate_fence` checks source + gate + four `:-false` operands ✓
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `test-design-structure.sh`: `assert_degraded_tools_gate_fence` checks source + gate + four `:-false` operands ✓ ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	architecture	scripts/compute-pr-line-counts.sh, scripts/render-run-summary.sh, skills/implement/scripts/write-final-report.sh, scripts/test-compute-pr-line-counts.sh, Makefile, agent-lint.toml (and 5 related files)	Entire PR-diff-line-counts feature added with no plan coverage	Feature ships ~400 lines across 10+ files not in the plan; bugs in compute-pr-line-counts.sh (e.g., set +e wrapper leaving lines_blob empty on tool error) land without plan-level acceptance criteria; plan estimated diff_added:190	Separate the line-counts feature into its own issue and PR; this PR should contain only the plan-scoped gate and rehydration changes 1	in_scope	nit	correctness	scripts/test-degraded-tools-gate.sh:94-97	Case 5b merged-stream assertion for PRESENCE_INPUT_EMPTY=true satisfies stdout-only invariant coincidentally rather than proving it	If the KV were accidentally emitted on stderr instead of stdout, Case 5b would still pass; only Case 5a (split capture) proves the stream invariant	No change required; Case 5a is authoritative; nit only ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: **architecture** `skills/implement/SKILL.md:343-356` — The new `/implement` fence always routes presence through `read-session-env-key.sh --default "false"` before calling the gate, and that helper treats a missing **or empty** durable value as the default (`scripts/read-session-env-key.sh:101-102`). The gate therefore receives `--codex-present false` (non-empty), so `PRESENCE_INPUT_EMPTY` never fires for corrupt `session-env.sh` rows—only for orchestrator flag assembly that still passes `""`. That narrows the new detector well below the acceptance text about “empty resolved values” and duplicates the plan-review concern that defaulting to `false` suppresses the bug-class signal. **Suggested fix:** Either omit `--default "false"` for the two presence keys (let empty values reach the gate), add a `read-session-env-key` mode that distinguishes absent vs empty vs explicit `false`, or document in `skills/implement/SKILL.md` / `scripts/degraded-tools-gate.md` that `PRESENCE_INPUT_EMPTY` is strictly an orchestrator-assembly guard, not durable-env validation.
- **Reviewer**: dyn-prompt-runtime-sync-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:343-356` — The new `/implement` fence always routes presence through `read-session-env-key.sh --default "false"` before calling the gate, and that helper treats a missing **or empty** durable value as the default (`scripts/read-session-env-key.sh:101-102`). The gate therefore receives `--codex-present false` (non-empty), so `PRESENCE_INPUT_EMPTY` never fires for corrupt `session-env.sh` rows—only for orchestrator flag assembly that still passes `""`. That narrows the new detector well below the acceptance text about “empty resolved values” and duplicates the plan-review concern that defaulting to `false` suppresses the bug-class signal. **Suggested fix:** Either omit `--default "false"` for the two presence keys (let empty values reach the gate), add a `read-session-env-key` mode that distinguishes absent vs empty vs explicit `false`, or document in `skills/implement/SKILL.md` / `scripts/degraded-tools-gate.md` that `PRESENCE_INPUT_EMPTY` is strictly an orchestrator-assembly guard, not durable-env validation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

