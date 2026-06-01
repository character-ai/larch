# Review Round 4

- Mode: `diff`
- 5 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_2: Orchestrator “already logged” grep matches validation site substring
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-exit-site-mapping-output.txt
- **Severity**: important
- **Concern**: The Step 8+ fallback guard uses `grep -Fq 'step-8-oos-checkpoint'`, which matches rows written with `step-8-oos-checkpoint-validation` because the shorter token is a substring of the longer site and `append-tool-failure.sh` emits `- **Step %s —` headers. After a prior validation failure is logged, a later checkpoint exit 1 (or 126/127 launch failure) whose helper append failed can skip the orchestrator fallback entirely, leaving no fresh Tool Failures row while Step 8+ still halts with `OOS_PENDING` set. The harness negates the validation token for exit-1 assertions; the orchestrator guard does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Grep for exact append headers (e.g. `Step step-8-oos-checkpoint —` and `Step step-8-oos-checkpoint-validation —`) or match tool plus exact site, as in test-oos-disposition-gate.sh disposition-gap assertions.
  - From cursor-specialist-edge-cases-output.txt: Key fallback on this invocation (timestamped stderr log, full Step header match, or distinct retry site); do not use bare substring grep across the whole log file.
  - From dyn-exit-site-mapping-output.txt: Make the guard rc-specific: for `_oos_chk_rc -eq 1`, treat as logged only when a disposition-only header is present (e.g. `grep -Fq 'step-8-oos-checkpoint'` **and** `! grep -Fq 'step-8-oos-checkpoint-validation'`, or match the exact `Step step-8-oos-checkpoint —` header); for `_oos_chk_rc -eq 2`, require `step-8-oos-checkpoint-validation` only.


### FINDING_3: Bare `grep` in orchestrator fence can abort fallback before `if` evaluates
- **Reviewer(s)**: dyn-orchestrator-bash-hazard-output.txt
- **Severity**: important
- **Concern**: The disposition-checkpoint fence uses bare `! grep -Fq …` on continuation lines inside an `if [ … ] && …` chain. Per `BASH_AUTHORING.md` §1 (issue #3104), top-level `grep` in orchestrator Bash fences is the Claude Code wrapper, not `/usr/bin/grep`; a non-zero exit can abort the entire Bash tool block before the `if` branch runs. On the common fallback path (checkpoint non-zero, no `step-8-oos-checkpoint*` row yet), both probes no-match → wrapped `grep` exits 1 → the harness may terminate before `append-tool-failure.sh`, `printf 'OOS_CHECKPOINT_RC=…'`, or `[ "$_oos_chk_rc" -ne 0 ] && exit "$_oos_chk_rc"`. `scripts/lint-bare-grep-probe.sh` only flags lines starting with `if … grep`, not `&& ! grep` continuations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-bash-hazard-output.txt: Switch both probes to `command grep -Fq …` (preferred in `BASH_AUTHORING.md`), e.g. `&& ! command grep -Fq 'step-8-oos-checkpoint' "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null` (and the validation-site line likewise). Optionally extend `lint-bare-grep-probe.sh` to flag any fence line matching `&& … grep` / `|| … grep` without a leading `command` or `(`.


### FINDING_4: Orchestrator fallback always logs validation site even for rc 1
- **Reviewer(s)**: dyn-exit-site-mapping-output.txt
- **Severity**: important
- **Concern**: The orchestrator fallback `append-tool-failure.sh` always uses `--site step-8-oos-checkpoint-validation` even when `_oos_chk_rc` is `1`. That path runs only when neither site token appears in `execution-issues.md` (helper `log_checkpoint_failure` did not persist a row). A real disposition gap (exit `1`) is then logged under the validation site, contradicting Step 8+ prose (exit `1` → disposition remediation; exit `2` → range/setup) and the helper contract. The removed inline block branched `_oos_fail_site` on gate rc before appending.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-site-mapping-output.txt: Set fallback `--site` from `_oos_chk_rc` (`step-8-oos-checkpoint` when `_oos_chk_rc -eq 1`; `step-8-oos-checkpoint-validation` for `2` and other non-zero codes, matching the helper’s `log_checkpoint_failure` mapping). Optionally pass `--output-file` from `_gate_log` vs `_oos_chk_err` based on whether the gate ran.


### FINDING_8: Harness checks checkpoint `+x` but not gate `+x`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-oos-disposition-gate.sh` verifies checkpoint executable bit but not `oos-disposition-gate.sh`. Checkpoint invokes the gate directly; gate mode 644 in a bad checkout: gate unit tests may pass via bash wrapper while Step 8+ checkpoint fails at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `[ -x "$GATE" ]` prelude beside existing CHECKPOINT check.


### FINDING_9: Unquoted `DESIGN_TMPDIR` expansion on checkpoint argv line
- **Reviewer(s)**: dyn-orchestrator-bash-hazard-output.txt
- **Severity**: important
- **Concern**: `${DESIGN_TMPDIR:+--design-tmpdir "$DESIGN_TMPDIR"}` is expanded as an unquoted word on the `bash … checkpoint.sh` line. Whitespace or glob characters in `DESIGN_TMPDIR` can word-split into multiple argv tokens, mis-binding CLI args and breaking design-OOS resolution on a load-bearing Step 8+ call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-bash-hazard-output.txt: Avoid bare parameter expansion on the argv line — e.g. build args with a small array (`_oos_args=(--implement-tmpdir "$IMPLEMENT_TMPDIR")`; `[ -n "${DESIGN_TMPDIR:-}" ] && _oos_args+=(--design-tmpdir "$DESIGN_TMPDIR")`; `bash … "${_oos_args[@]}"`) or use a conditional second line that passes `--design-tmpdir "$DESIGN_TMPDIR"` only when `[ -n "${DESIGN_TMPDIR:-}" ]`.


