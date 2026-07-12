### FINDING_1: Adapt child-control argument incompatibility
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Bgjob Lifecycle Integrator, Codex-dyn-Bgjob Lifecycle Integrator
- **Severity**: major
- **Concern**: `bgjob adapt` appends `--bgjob-child --merge-result-env <path>`, but the three wrappers still use legacy child flags or reject/ignore the injected arguments. Children may relaunch the parent path, exit with usage errors, or fail to publish results.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Child entry must adopt adapt --bgjob-child and --merge-result-env contract bgjob adapt always appends --bgjob-child and --merge-result-env to the launched command (python/larch/bgjob/adapt.py:312-313). The three wrappers still gate child mode on --run-loop-child, --run-tail-child, and --run-step5c-child and treat unknown flags as fatal (e.g. design-step3-review.sh:101). A fresh adapt launch would re-enter the parent launcher path or exit 2 instead of running child work. Replace the --run-*-child gates with --bgjob-child plus required --merge-result-env parsing in all three scripts; build the adapt child argv without the legacy child flag and let adapt append the standard child suffix.
  - From Cursor-Innovation: Child entry still keys off --run-loop-child/--run-tail-child/--run-step5c-child but bgjob adapt appends --bgjob-child and --merge-result-env After conversion the launcher never enters child mode; plan-review loop Gate C tail and step5c never run and merge KVs never reach the daemon Replace retired --run-*-child gates with --bgjob-child plus required --merge-result-env parsing; keep resume/public argv forwarding on the pre-adapt argv tail only
  - From Codex-Innovation: Specify and test a shared child-mode argument path that recognizes the appended adapter flags even after public argv, preserves public arguments unchanged, and writes the required rows to the supplied merge path.
  - From Cursor-Pragmatic: skills/design/scripts/design-step5c.sh:17 `bgjob adapt` injects `--bgjob-child` and `--merge-result-env`, but all three design adapters still gate child work on `--run-loop-child`, `--run-tail-child`, and `--run-step5c-child` After conversion, `adapt` launches `bash … --bgjob-child --merge-result-env …`; the scripts ignore those flags, stay in launcher mode, and either recurse into another `bgjob adapt`/`start` or run the full foreground path without publishing merge KVs to the daemon contract In each firm script, accept `--bgjob-child` (drop the `--run-*-child` tokens), parse `--merge-result-env`, and branch child work only when `--bgjob-child` is set; pin this argv contract in the three `.md` files and in `test-design-structure.sh`
  - From Cursor-Requirements: Plan omits child-mode contract for bgjob adapt argv injection bgjob adapt always appends --bgjob-child and --merge-result-env to the launched command (python/larch/bgjob/adapt.py:312). These wrappers gate child work on --run-loop-child / --run-tail-child / --run-step5c-child and do not parse --merge-result-env. A thin outer exec into adapt would relaunch launcher mode or treat injected flags as unknown, breaking Step 3/4/5c. Add firm steps: accept --bgjob-child (alias or replace script-specific flags); parse --merge-result-env in child mode; pass bash $0 plus resume/public argv to adapt without self-reexec flags; document the contract in the three .md files.
  - From Cursor-dyn-Bgjob Lifecycle Integrator: Add explicit `--bgjob-child` / `--merge-result-env` parsing to all three wrappers, replace `--run-loop-child` / `--run-tail-child` / `--run-step5c-child` child gates, and launch child work only when `--bgjob-child` is set.
  - From Codex-dyn-Bgjob Lifecycle Integrator: Define child-mode parsing for all three wrappers. Strip only the appended controls, preserve resume and public arguments unchanged, atomically publish fresh child KVs to PATH, and return the original child rc.


### FINDING_3: Fresh Step 3 completion sentinel is not cleared
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Bgjob Lifecycle Integrator
- **Severity**: major
- **Concern**: `bgjob adapt` does not remove a stale `.completed/step-3` marker before a fresh Step 3 attempt, allowing later workflow stages to treat an incomplete rerun as already completed.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Preserve the existing rm -f $DESIGN_TMPDIR/.completed/step-3 (and resume-state file writes) in the thin launcher immediately before invoking bgjob adapt; do not rely on adapt for completion-boundary hygiene.
  - From Cursor-Innovation: Keep the existing non-resume rm of .completed/step-3 in the thin launcher immediately before bgjob adapt; do not move it into adapt or drop it
  - From Cursor-Requirements: On outer wrapper paths that start new work (not completed-result DONE reattach), delete .completed/step-3 before calling bgjob adapt; skip clearing when adapt returns DONE from a valid completed result env.
  - From Cursor-dyn-Bgjob Lifecycle Integrator: Keep a launcher-only pre-adapt hook: on non-`--read-result-env` fresh starts, `rm -f "$DESIGN_TMPDIR/.completed/step-3"` before `bgjob adapt`, matching today's fresh-start path.


### FINDING_4: Early exits do not publish terminal results
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Pause-save and missing-scope/panel-init-failed exits occurring inside the child path can produce a generic DONE result without the routing KVs needed by the orchestrator.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Arch: Keep these gates before adapt, or require every early exit to publish its terminal KVs to the adapter merge file. Add pause and missing-scope harness cases.


### FINDING_5: Step 4 and Step 5c lack explicit workspace and owner bindings
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-dyn-Bgjob Lifecycle Integrator
- **Severity**: major
- **Concern**: Omitting explicit `DESIGN_TMPDIR` and owner-PID arguments can make `bgjob adapt` use the wrong temporary workspace or lose owner/orphan validation.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Arch: Require both wrappers to pass --tmpdir "$DESIGN_TMPDIR" and --owner-pid "$CLAUDE_PID" when set. Assert these arguments in both updated harnesses.
  - From Cursor-Requirements: All design adapt calls must pass --tmpdir explicitly bgjob adapt resolves tmpdir from --tmpdir or IMPLEMENT_TMPDIR only, not DESIGN_TMPDIR. Step 3 mentions explicit tmpdir; Step 4/5c sections do not. Omitting --tmpdir "$DESIGN_TMPDIR" can yield BGJOB_ERROR=missing-tmpdir or probe the wrong session root. State in all three adapter sections that every bgjob adapt invocation must include --tmpdir "$DESIGN_TMPDIR", --step, --budget-s, and --owner-pid when available.
  - From Codex-dyn-Bgjob Lifecycle Integrator: Add `--owner-pid "$CLAUDE_PID"` to both adapt delegations, or explicitly export the validated owner identity before invoking adapt.


### FINDING_6: Parent-only launcher lifecycle is not preserved
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Bgjob Lifecycle Integrator
- **Severity**: major
- **Concern**: Moving pre-adapter handling into child mode can drop completed-result reads, resume validation/state writes, pause-save behavior, and other launcher-only lifecycle operations when `adapt` reattaches instead of spawning a child.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Pragmatic: Keep a short parent launcher block before `bgjob adapt` for `--read-result-env` early exit, resume validation plus `step3_review_write_resume_state`, pause-save, and fresh-start `.completed/step-3` clearing; limit `--bgjob-child` to scope-anchor check, loop execution, stderr capture, normalization, and merge-env publication
  - From Cursor-dyn-Bgjob Lifecycle Integrator: Preserve a launcher-only `--read-result-env` branch that bypasses `bgjob adapt` and delegates directly to `plan-review normalize-status --read-result-env`.


### FINDING_7: DESIGN_TMPDIR session rehydration is removed
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Removing wrapper session rehydration without another trusted source for `DESIGN_TMPDIR` can cause normal launches to fail before the child starts.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Pragmatic: Retain minimal session-env sourcing before delegation, or add a trusted common mechanism that resolves DESIGN_TMPDIR


### FINDING_8: Completed-result reattachment blocks Step 5c retries
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Validator, size, or assessment refusals can leave a valid completed result that `bgjob adapt` reattaches on retry, preventing the required fresh Step 5c publish attempt.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Pragmatic: Add safe result invalidation for intentional Step 5c retries, or retain the current relaunch behavior until the shared adapter supports retries
  - From Codex-Requirements: Define an adapter-compatible fresh-attempt boundary for explicit Step 5c retries and test refusal, repair, and successful relaunch


### FINDING_1: Step 5c retry references omit the fresh-attempt control
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Authoritative Step 5c retry documentation still invokes bare wrapper relaunches, so completed refusal results may be reattached instead of triggering fresh publishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED:` rows for the four reference files (or a single shared retry-authority file they import) and pin every Step 5c re-run path to the wrapper fresh-attempt flag; keep ordinary first entry on default reattachment.
  - From Cursor-Pragmatic: Update all retry owners, including `approval-gates.md`, `finalize-step5.md`, `decompose-panel.md`, and `validator-failure.md`, to pass the private retry control
  - From Cursor-Requirements: Add `### UPDATED:` rows for `skills/design/references/finalize-step5.md`, `skills/design/references/validator-failure.md` (autofix-ok and Fix-and-retry Step 5c paths), `skills/design/references/approval-gates.md`, and `skills/design/references/decompose-panel.md` (size Override) that pin the wrapper argv token and require it on every documented Step 5c re-run.


### FINDING_4: Session environment is not available during wrapper parent logic
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: When launchers provide only `--session-env-path`, wrapper parent logic may run before trusted session values are resolved, leaving `DESIGN_TMPDIR` and related routing variables unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Parse the trusted allowlisted session env once and export the validated child environment before daemon start, or pass equivalent explicit bindings to the child. Test launcher-style invocation with DESIGN_TMPDIR unset.
  - From Codex-Pragmatic: Add a shared trusted resolver before parent-only logic, or retain minimal parent rehydration for Steps 3 and 4
  - From Codex-Requirements: Add one trusted pre-wrapper rehydration point, such as the launcher, so parent-only logic receives validated session values before `bgjob adapt` runs.


### FINDING_5: Step 3 resume paths can reattach stale completed results
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Mid-loop Step 3 resumes can encounter an existing terminal result and have `bgjob adapt` reattach it instead of launching the requested fresh phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When `STEP3_REVIEW_HAS_RESUME_STATE=true`, delegate through `bgjob adapt` with `--replace-completed-result` (or an equivalent adapter flag). Keep default reattachment for ordinary duplicate invocations and reentry paths that already clear the result via `plan-review step3-state` / `_step3_clear_downstream_sentinels`. Extend `test-design-step3-review.sh` with a completed-result plus resume-argv case that must launch a new child.
  - From Cursor-Pragmatic: In design-step3-review.sh parent mode, when STEP3_REVIEW_HAS_RESUME_STATE=true pass --replace-completed-result to bgjob adapt (wrapper-private flag, not forwarded to plan-review run). Keep default reattach for duplicate ordinary invocations. Extend test-design-step3-review.sh and test-design-structure.sh to seed a terminal result env with NEXT_ACTION=gate-b, invoke with --starting-round and --phase awaiting-continuation, and assert adapt emits STARTED (fresh child) rather than DONE reattach.


### FINDING_6: Step 3 terminal child failures return the wrong status
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Step 3 child failure paths can publish routing rows but still exit nonzero, causing the orchestrator to ignore the valid `NEXT_ACTION` because it requires `BGJOB_RC=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin in `design-step3-review.sh` / `design-step3-review.md`: after atomically writing required terminal rows (including `NEXT_ACTION=final-summary:*` when applicable) to the adapter merge path, the child must exit 0. Reserve non-zero child rc for merge-publication failures only. Add harness coverage for missing-scope-anchor and panel-init-failed paths asserting `BGJOB_RC=0` plus the expected `NEXT_ACTION` in the bgjob result env.


### FINDING_8: New harness is not registered across test and lint surfaces
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The planned harness may be skipped, omitted from Bash linting, or rejected as an unreachable skill script without repository registration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the harness to `.PHONY`, `scripts/residual-bash-paths.txt`, and the existing Makefile-only harness exclusions in `agent-lint.toml` 1. **[risk-integration]** Register the planned Step 4 harness across the repository’s test and lint surfaces. Without these entries, `make lint` or the harness target can fail, or the new adapter test can be silently skipped.


