### FINDING_11: Exit 6 fourth-failure stall persistence is prompt-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: The fourth transient retry must persist terminal stall keys, but enforcement lives only in prompt prose; an orchestrator miss can leave transient-shaped state and break teardown/classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add structure pin for stall-persistence prose or integration harness.
  - From cursor-specialist-edge-cases-output.txt: Enforce in python/ship.py or a Bash helper invoked from the selector fence.
  - From dyn-ship-state-output.txt: Either add a small helper (e.g. `scripts/persist-python-transient-stall.sh`) invoked from the Step 8+ fence on the 4th Exit 6, or teach `python/ship.py` to emit a distinct outcome/flag that triggers a deterministic stall-state write before JSON return.
  - From dyn-plan-voting-output.txt: Address the concern above.


### FINDING_13: `stall-recovery-report.sh` reads `finalize-state.sh` without symlink/regular-file guards
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A symlinked or non-regular `finalize-state.sh` under `IMPLEMENT_TMPDIR` can be read into evidence and influence classification/resume hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject symlinked/non-regular finalize-state.sh under tmpdir before kv_get and evidence cat; cap file size like failure-detail-log.


### FINDING_15: `_write_ship_state` overwrites existing state on read error
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A transient read failure causes `_write_ship_state` to start from empty fields and silently drop orchestrator-seeded keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail closed when an existing state file cannot be read; only start from empty fields when the file is absent.


### FINDING_16: Terminal disk-write failures are suppressed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The outer `Stalled` handler suppresses terminal state write failures, so JSON can report STALLED while required disk artifacts are missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Do not suppress terminal write failures; surface INTERNAL_ERROR or re-raise after logging.


### FINDING_18: Exit 4 / conflict-resolution prose still resumes bash on default Python path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` and `conflict-resolution.md` still contain executable Phase 4 / Exit 4 text that unconditionally resumes `ship-pr.sh --resume-phase`, despite the Python-default selector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Align bullet with conflict-resolution.md: Python selector re-invoke; bash-only --resume-phase
  - From dyn-ship-state-output.txt: Rewrite the Exit 4 `ship_pr_pre_push` parenthetical to match `conflict-resolution.md` §Contract: default Python selector re-invoke; bash-only `--resume-phase ship-pr-rrr-phase14` when `LARCH_SHIP_PR_IMPL=bash`.
  - From dyn-ship-state-output.txt: Replace line 107 with the same dual-path wording used in lines 5–7 (Python selector foreground argv including `--state-file`, no `--resume-phase`; bash opt-in keeps `--resume-phase ship-pr-rrr-phase14`).
  - From dyn-plan-voting-output.txt: Align line 107 with the Contract (Python selector unless `LARCH_SHIP_PR_IMPL=bash`) and add a structure-test pin on that paragraph.
  - From dyn-contract-drift-output.txt: Replace line 107 with the same dual-path wording as the contract header, or add an explicit “when `LARCH_SHIP_PR_IMPL=bash`” gate before the `ship-pr.sh --resume-phase` sentence.
  - From dyn-contract-drift-output.txt: Mirror the conflict-resolution contract: Phase 4 exit 0 → Python selector re-invoke (no `--resume-phase`); bash-only `--resume-phase ship-pr-rrr-phase14` when `LARCH_SHIP_PR_IMPL=bash`.


### FINDING_19: Python conflict-resolution resume is unsupported despite prose claiming re-invoke works
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: After Phase 4, Python re-entry sees `RESUME_PHASE=ship-pr-rrr-phase14` and returns unsupported rebase continuation, so the documented default-path conflict recovery is not end-to-end functional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Either implement Python parity (honor `ship-pr-rrr-after-phase14.flag` and continue `run_rebase_rebump` after Phase 4), or require the orchestrator to clear `RESUME_PHASE`/`CALLER_KIND` before Python re-invoke and document that Phase 4 success on the default path still requires `LARCH_SHIP_PR_IMPL=bash` until #3404 lands.


### FINDING_21: Finalize-only stall recovery tests do not assert `RESUME_HINT`
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: New finalize-only classify fixtures assert class and stall keys but not non-`none` resume hints, so hint mapping regressions can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Add `assert_eq step8-shippr "$(kv RESUME_HINT "$SANDBOX/case_finalize_fallback.out")"` (and the same for `case8finalize`) alongside the existing class/step assertions.


### FINDING_22: Step 18 restore gate uses narrower truthiness than classifier
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: Step 18 checks only literal `"true"` for stall/user-input flags, while Step 18a accepts broader truthy values; non-lowercase truthy state can skip needed restore.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Reuse the same truthy predicate as `stall-recovery-report.sh` (small shared helper or duplicated `case` arm) before setting `_restore_finalize=true`.


### FINDING_23: Scope-anchor/feature/findings files can inline arbitrary readable paths into external prompts
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: Several new prompt render paths accept readable file arguments without symlink rejection or `DESIGN_TMPDIR` containment, risking leakage of local file contents into Codex/Cursor/revise prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Reuse the containment contract from `render-main-agent-scope-anchor.sh` (require `DESIGN_TMPDIR`, `pwd -P` under-tmpdir check, `! -L`, CR/LF path rejection) before `emit_untrusted_file_block`, or delegate body emission to that helper; mirror the guard in `scripts/dispatch-plan-voters.sh:48-76`.
  - From dyn-prompt-safety-output.txt: Add the same canonical-path + under-`DESIGN_TMPDIR` + non-symlink checks used in `render-main-agent-scope-anchor.sh` before calling `emit_untrusted_file_block reviewer_feature_description`.
  - From dyn-prompt-safety-output.txt: Canonicalize and require both `FEATURE_FILE` and `FINDINGS_FILE` to resolve under `$CANONICAL_DESIGN_TMPDIR` (non-symlink regular files), matching the `plan.txt` invariant.


### FINDING_24: `write-final-report.sh` appends duplicate state keys
- **Reviewer(s)**: dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: Repeated final-report renders append `LINES_*` / `CODE_*` keys to `ship-pr-state.sh`, leaving stale first-match values for readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-voting-output.txt: Merge-replace those keys (same pattern as `_write_ship_state`) or write them only through the Python state merge path; add a test that two append passes yield the latest counts.


### FINDING_25: Plan-review dedup ignores `what:` lines in production path
- **Reviewer(s)**: dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: Production dedup and parity helper normalize different fields, so scope-reduction findings that only use `what:` can under-deduplicate in real voting/aggregation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-voting-output.txt: Teach `problem_text()` to include `what:` lines (and the same `[SCOPE-REDUCTION]` strip) or normalize all reviewer output to `Concern:` before dedup; add a harness case with marker-only-on-`what:`.


### FINDING_26: Python README still documents stale Phase 7/pre-push behavior
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `python/README.md` says pre-push conflict wiring and `ci_monitor.py` are deferred, but Python now partially implements/imports those paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Rewrite the pre-push section to describe current Python behavior (state write + `PrePushConflictHandoff`), document that resume after conflict-resolution Phase 4 is still unsupported on the Python path (`unsupported-rebase-continuation` at `python/ship.py:813-826`), and cross-link `skills/implement/references/conflict-resolution.md` plus issue #3404.
  - From dyn-contract-drift-output.txt: Update the `ci_monitor.py` bullet to state it is live on the default Python Step 8+ path (with a one-line pointer to the call site in `python/ship.py`).


### FINDING_28: Conflict-resolution structure pins do not enforce dual-path Phase 4 wording
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: Existing structure tests only pin caller-kind strings and would miss regression to bash-only Phase 4 resume prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Add a positive pin for the dual-path Phase 4 exit-0 wording (Python selector + bash `--resume-phase` gate) and a negative pin that line 107 must not be the sole resume instruction without a Python branch.


### FINDING_3: Missing structure pins for Step 18 restore gate and bash/Python routing qualifiers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` does not mechanically pin the Step 18 `_restore_finalize` gate, terminal override predicates, or full bash-only exit-matrix boundaries, so prompt regressions can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add grep/awk pins for _restore_finalize gate prose and bash-only continuation qualifiers.
  - From cursor-specialist-testing-output.txt: Add grep/awk assertions from plan acceptance to test-implement-structure.sh.
  - From dyn-bash32-output.txt: Add awk- or grep-scoped assertions in the Step 18 bash-fence region for `_restore_finalize`, `[ "${LARCH_SHIP_PR_IMPL:-python}" = "bash" ]`, and at least one terminal-override predicate (`STALL_TRACKING=true`, `BAIL_NEEDS_USER_INPUT=true`, or differing `STALL_STEP`).
  - From dyn-bash32-output.txt: Extend the awk end anchor to a stable token inside the first matrix bullet (for example the Exit 0 heading) or add a separate `grep -Fq` that the Exit 0 bullet retains an explicit bash-only qualifier for `ship-pr.sh --resume-phase pr-create`.


### FINDING_4: Postbump/checks terminal-finalize stall paths lack tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned tests for checks/postbump STALLED terminal-finalize paths are absent, so those paths could stop writing stall-shaped `finalize-state.sh` without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add parametrized or focused tests for those stall paths asserting finalize-state.sh shape.
  - From cursor-specialist-testing-output.txt: Add test_postbump_stall_writes_terminal_finalize with monkeypatched postbump STALLED.
  - From cursor-specialist-plan-fidelity-output.txt: Add test where postbump returns STALLED and finalize has stall keys.


### FINDING_6: PrePushConflictHandoff is terminalized instead of treated as re-entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The outer stalled handler writes terminal `finalize-state.sh` for `PrePushConflictHandoff`, causing a resumable conflict handoff to look like a terminal stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip _write_terminal_state for PrePushConflictHandoff (and similar handoff exceptions); assert no finalize in test_pre_push_conflict_handoff_persists_resume_tokens
  - From cursor-specialist-edge-cases-output.txt: Skip terminal finalize for PrePushConflictHandoff or add explicit handoff disposition in restore gate.


### FINDING_7: Outer stalled handler writes terminal state from stale entry context
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: The outer `except Stalled` handler uses the original `ctx`, not the latest working context, so terminal `finalize-state.sh` can miss PR metadata or disagree with handoff state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass latest hydrated RunContext (working) to _write_terminal_state or avoid double-write when inner path already persisted state
  - From dyn-ship-state-output.txt: In the `PrePushConflictHandoff` path (or the outer handler generally), pass the active context (`working`) and an explicit `stall_step` (e.g. `"rebase"` or `config.SHIP_PR_PRE_PUSH_*`) into `_write_terminal_state`, and add a test asserting `finalize-state.sh` `STALL_STEP` matches the handoff phase.
  - From dyn-plan-voting-output.txt: Pass `working` (or merge `ship-pr-state.sh` into the context) in the outer stall handler before `_write_terminal_state`; extend `test_pre_push_conflict_handoff_persists_resume_tokens` / outer-stall tests to assert `finalize-state.sh` carries matching `PR_NUMBER` / stall keys.


### FINDING_8: Pre-push handoff no-finalize contract lacks a direct test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `test_pre_push_conflict_handoff_persists_resume_tokens` does not assert that `finalize-state.sh` is absent after a re-entry handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add assert not finalize-state.sh.exists() after PrePushConflictHandoff run


