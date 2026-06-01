Structured aggregator output from the supplied reviewer findings:

### FINDING_1: Stale RUN_ID no longer triggers ndjson find fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: When `session-id` / `RUN_ID` is non-empty but the keyed `oos-issues.ndjson` is missing, the extracted helper only runs `find` when `RUN_ID` is empty. The removed inline SKILL block also find-bound when the keyed path was missing. A resume with a stale session-id and exactly one foreign ndjson under `larch-logs/implement/` could previously bind via find and pass (including non-security OOS clear); the helper now exits 2 and blocks `OOS_PENDING` clear. Security treats this as intentional hardening (closes foreign-batch bind while OOS is pending); other reviewers flag plan/acceptance drift vs inline 1:1 port and operator impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align plan/acceptance with documented policy or restore find when keyed path is missing but RUN_ID is set.
  - From cursor-specialist-correctness-output.txt: Document in SKILL.md Step 8+ (or revert to inline find-when-missing if 1:1 port is required); keep harness stale-RUN_ID case if hardening stands.
  - From cursor-specialist-testing-output.txt: Document as intentional contract change and keep stale-RUN_ID test; revert only if product requires old fallback.
  - From cursor-specialist-edge-cases-output.txt: Keep hardening; add operator-facing remediation in SKILL Step 8+ and log the keyed path in fail_validation output.
  - From cursor-specialist-plan-fidelity-output.txt: Restore inline find when keyed path missing (keep ambiguity exit 2 only for empty RUN_ID + multiple matches), or update plan/acceptance to authorize stale-RUN_ID hardening.

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

### FINDING_5: SKILL invokes checkpoint via `bash` instead of direct executable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan, harness, and `oos-disposition-checkpoint.md` expect direct `+x` invocation; SKILL.md invokes via `bash …/oos-disposition-checkpoint.sh`. The harness `[ -x ]` check does not cover the orchestrator path, so a 100755 regression or wrong shebang may surface only as shell exit 127 at runtime, with orchestrator fallback/mis-branch risk vs the 0/1/2 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align SKILL with direct invocation or document bash as canonical and adjust acceptance/harness accordingly.
  - From cursor-specialist-edge-cases-output.txt: Align checkpoint.md with bash wrapper or change SKILL to direct invocation consistent with harness.
  - From cursor-specialist-plan-fidelity-output.txt: Use direct `"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-disposition-checkpoint.sh"` invocation per plan refinement #2.
  - From cursor-specialist-plan-fidelity-output.txt: Align SKILL with doc or document bash in the contract sibling.

### FINDING_6: `log_checkpoint_failure` swallows append failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `log_checkpoint_failure` uses `append-tool-failure.sh … || true` and does not pre-touch `execution-issues.md`. If append fails (permissions/redaction), the checkpoint exits non-zero with no Tool Failures row; the orchestrator fallback may also be skipped (FINDING_2), leaving no audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Touch execution-issues.md before append; consider logging append failure to stderr without overriding checkpoint rc.

### FINDING_7: Orchestrator fallback append path lacks regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: When the checkpoint fails without writing to `execution-issues.md` (missing/swallowed `append-tool-failure.sh`), the orchestrator fallback is the only audit trail; no harness forces non-zero checkpoint rc with empty `execution-issues.md` and asserts fallback append, so grep/append drift can ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness or integration case forcing non-zero checkpoint rc with empty execution-issues.md and assert fallback append.

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

### FINDING_10: No test for `DESIGN_TMPDIR` env without `--design-tmpdir` flag
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness covers `--design-tmpdir` CLI but not exported `DESIGN_TMPDIR` alone. Standalone or future callers relying on env-only binding could regress design-path resolution undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one exported-DESIGN_TMPDIR checkpoint case parallel to --design-tmpdir tests.

### FINDING_11: `--help` exits 0 without validation logging
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `oos-disposition-checkpoint.sh --help` exits 0 without going through `fail_validation`. A thin wrapper could misread `-h` as checkpoint pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Exit 2 through fail_validation or drop help from production CLI.

### OOS_1: [OUT_OF_SCOPE] CI harness shards vs local relevant-checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness shards are the CI gate; local `relevant-checks` may skip them on script-only edits. Developer merges without running shard 5/16 locally; CI still catches failures on PR. Pre-existing; run `make test-oos-disposition-gate` when touching checkpoint/gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — reviewer provided concern only; generic “Address the concern above” omitted)

### OOS_2: [OUT_OF_SCOPE] Python OOS parity with bash gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Python OOS parity with bash gate not in this diff scope. Python cutover could pass disposition while bash checkpoint fails. Track separately from bash Phase 3 extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — reviewer provided concern only)

### OOS_3: [OUT_OF_SCOPE] `RUN_ID` slug validation before ndjson path build
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_ID` from `session-id` is interpolated into `_oos_ndjson` without the slug rules `larch_log_slug_is_valid` / `larch_log_validate_slug` use in `scripts/larch-log.sh`. A corrupted or hand-edited `session-id` containing `..` segments could resolve paths outside `larch-logs/implement/<RUN_ID>/`. Same pattern existed in the removed inline SKILL block; not introduced by this refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse `larch_log_slug_is_valid` (or `^[A-Za-z0-9._-]+$` with rejection of `..` and `/`) before building the ndjson path; fail validation exit 2 on mismatch.

### OOS_4: [OUT_OF_SCOPE] Arbitrary `--implement-tmpdir` / `--design-tmpdir` without session guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--implement-tmpdir` and `--design-tmpdir` are accepted as arbitrary directory strings with no check that they lie under the active session cache or match `expected-tmpdir-basename-prefix` semantics used elsewhere (e.g. `ship-pr.sh`). Mis-invoked CLI could read/write marker files and append redacted stderr from paths outside the intended session tmpdir. Pre-existing orchestrator trust model; not new to the checkpoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional prefix/canonicalization guard (compare realpath to `IMPLEMENT_TMPDIR` from env or session sentinel), aligned with other implement helpers if adopted repo-wide.

### OOS_5: [OUT_OF_SCOPE] `FORKED_TARGET` / `REPO_UNAVAILABLE` from unauthenticated `ship-pr-state.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `FORKED_TARGET` / `REPO_UNAVAILABLE` are read from `ship-pr-state.sh` without authentication; any writer of that file in the tmpdir can force gate skip (exit 0). Unchanged from inline behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Treat as intentional carve-out under session-tmpdir trust; document that tmpdir integrity is part of the single-runner invariant.

### OOS_6: [OUT_OF_SCOPE] Non-canonical boolean strings in `ship-pr-state.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `FORKED_TARGET` / `REPO_UNAVAILABLE` require exact `true` string (pre-existing). Non-canonical state values run full gate/precondition paths unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Normalize booleans when reading ship-pr-state.sh (separate change).

### OOS_7: [OUT_OF_SCOPE] No harness for SKILL.md orchestrator checkpoint wrapper / fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-exit-site-mapping-output.txt
- **Severity**: nit
- **Concern**: Checkpoint unit tests can pass while the SKILL.md fence (bash wrapper, grep guards, fallback `--site`, rc propagation) regresses. No structure or harness test exercises the orchestrator block; mis-site fallback (FINDING_4) would not be caught by `make test-oos-disposition-gate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a small structure or harness test for the SKILL fence block.

---

**Subsumed / omitted (not emitted as findings):** FINDING_11–14 and FINDING_35 are positive security/consistency attestations with no actionable defect. FINDING_30, FINDING_31, FINDING_32, and FINDING_36 are informational context (acceptable child-script grep, documented ndjson contract change, commit list) without distinct fix direction beyond FINDING_1 documentation.
