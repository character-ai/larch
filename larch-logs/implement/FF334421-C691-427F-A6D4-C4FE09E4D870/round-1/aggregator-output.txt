### FINDING_1: [OUT_OF_SCOPE] Branch bundles unrelated design/run-log work with ship-driver flip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: The branch combines the Python ship-driver default flip with substantial unrelated `/design` scope-anchor/run-log work, increasing review noise, regression attribution risk, and revert/bisect complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or rebase so the ship-driver flip lands alone (or with minimal deps).
  - From cursor-specialist-testing-output.txt: Split PRs or run full make lint/harness shards and document coupling.
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_2: Terminal finalize writers can diverge or double-write state
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_write_terminal_finalize_if_terminal` and `_persist_stall_metadata_if_needed` both write terminal state; future key drift or duplicate writes could leave Step 18/stall recovery with inconsistent metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate to one terminal writer or narrow the main() backstop to paths that skip the primary writer with a shared field map.

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

### FINDING_5: Step 8+ prose is overly long and internally fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: Step 8+ mixes Python selector routing, bash matrix prose, and state-file reads in a way that is hard to maintain and can create contradictory routing authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider extracting normative selector contract to a reference file.
  - From dyn-ship-state-output.txt: Restructure Step 8+ into two clearly separated subsections (“Python selector routing” vs “Bash exit matrix”), move all shared Exit 0/3/4/6 handling under the Python selector with bash-only cross-refs, and keep the legacy matrix byte-stable behind an explicit `LARCH_SHIP_PR_IMPL=bash` fence only.

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

### FINDING_9: [OUT_OF_SCOPE] Python prerequisite version is inconsistent with plan/runtime expectations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: Reviewers disagree whether the accepted plan required Python 3.12+ while shipped docs/guards use 3.11+, creating acceptance/runtime drift or at least an operator-facing mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align docs to 3.12 or update plan acceptance to 3.11 explicitly
  - From cursor-specialist-testing-output.txt: Align plan acceptance with 3.11 or bump guard/docs to 3.12.
  - From cursor-specialist-plan-fidelity-output.txt: Raise to 3.12+ in docs/guards or amend plan to 3.11
  - From dyn-bash32-output.txt, dyn-contract-drift-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Default Python flip ships before soak/security blockers are resolved
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: The default path now routes unset `LARCH_SHIP_PR_IMPL` runs through less-soaked Python paths with known blockers, while `SECURITY.md` removes/softens prior pending-review language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track blockers; document opt-out LARCH_SHIP_PR_IMPL=bash prominently.
  - From cursor-specialist-security-output.txt: Gate default flip on listed blockers or complete python/ship.py and python/finalize.py review and document residual risks instead of claiming unchanged properties.
  - From cursor-specialist-edge-cases-output.txt: Document escape hatch; close blockers or add env-based soak gate.
  - From dyn-ship-state-output.txt, dyn-plan-voting-output.txt, dyn-contract-drift-output.txt: Address the concern above.

### FINDING_11: Exit 6 fourth-failure stall persistence is prompt-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: The fourth transient retry must persist terminal stall keys, but enforcement lives only in prompt prose; an orchestrator miss can leave transient-shaped state and break teardown/classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add structure pin for stall-persistence prose or integration harness.
  - From cursor-specialist-edge-cases-output.txt: Enforce in python/ship.py or a Bash helper invoked from the selector fence.
  - From dyn-ship-state-output.txt: Either add a small helper (e.g. `scripts/persist-python-transient-stall.sh`) invoked from the Step 8+ fence on the 4th Exit 6, or teach `python/ship.py` to emit a distinct outcome/flag that triggers a deterministic stall-state write before JSON return.
  - From dyn-plan-voting-output.txt: Address the concern above.

### FINDING_12: `_write_ship_state` preserves unknown state keys
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: Python state refreshes preserve arbitrary existing `ship-pr-state.sh` keys, widening the durable trust surface for same-UID or prompt-side key injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict merged keys to a documented allowlist matching finalize _FINALIZE_KEY_RE plus orchestrator-seeded fields; drop unknown keys on write.
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_13: `stall-recovery-report.sh` reads `finalize-state.sh` without symlink/regular-file guards
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A symlinked or non-regular `finalize-state.sh` under `IMPLEMENT_TMPDIR` can be read into evidence and influence classification/resume hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject symlinked/non-regular finalize-state.sh under tmpdir before kv_get and evidence cat; cap file size like failure-detail-log.

### FINDING_14: Stale handoff keys can survive Python state refreshes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Preserved `RESUME_PHASE`, `CALLER_KIND`, and related keys can linger across terminal success or user-input boundaries and mis-route later Exit 4/Step 18a handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Clear handoff keys on terminal success and NEEDS_USER_INPUT boundaries,or overwrite them whenever terminal_outcome is written.

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

### FINDING_17: Exit 0 fallback can route default Python runs back to `ship-pr.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt
- **Severity**: important
- **Concern**: The Exit 0 fallback still says to re-invoke `ship-pr.sh` without an explicit bash-only qualifier, contradicting the Python-default selector contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add bash-only qualifier or Python selector wording.
  - From cursor-specialist-plan-fidelity-output.txt: Qualify bash-only; add Python selector re-invoke for default path
  - From dyn-ship-state-output.txt: Split Exit 0 into explicit bash vs Python branches (mirror the OOS re-entry wording on the same line), or qualify the “Otherwise” clause with “when `LARCH_SHIP_PR_IMPL=bash`” and add a parallel “on the default Python path, re-invoke the Python selector argv (including `--state-file`); never the fenced `ship-pr.sh` block.”
  - From dyn-plan-voting-output.txt: Qualify the else branch explicitly (“when `LARCH_SHIP_PR_IMPL=bash` …; on the default Python path re-invoke `python3 …/python/ship.py` per the selector”) or move the entire exit-matrix bullet list under a single bash-only wrapper.

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

### FINDING_20: Unconditional post-matrix state-file reads are easy to misinterpret as Python continuation parsing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-plan-voting-output.txt
- **Severity**: latent
- **Concern**: Step 8+ tells the default path not to parse `ship-pr-state.sh` for continuation, but nearby text still instructs state-file reads; reviewers flagged this as either ambiguous or intentional-but-easy-to-misread.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Gate read behind bash or clarify scoped-read-only default path
  - From dyn-plan-voting-output.txt: Address the concern above.

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

### FINDING_27: Restore/finalize and implement prose retain stale bash-only writer breadcrumbs
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `restore-finalize-state.md` and several `SKILL.md` passages still name only `ship-pr.sh` for driver/finalize behavior, conflicting with Python-default execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Rewrite the Purpose paragraph to name both writers (`python/ship.py` on terminal outcomes by default; `ship-pr.sh` when `LARCH_SHIP_PR_IMPL=bash`) and reference the Step 18 conditional-restore gate in `skills/implement/SKILL.md`.
  - From dyn-contract-drift-output.txt: Align all three passages with the Step 8+ “active Step 8+ driver (default Python; bash opt-in)” wording used elsewhere in the same file.

### FINDING_28: Conflict-resolution structure pins do not enforce dual-path Phase 4 wording
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: Existing structure tests only pin caller-kind strings and would miss regression to bash-only Phase 4 resume prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Add a positive pin for the dual-path Phase 4 exit-0 wording (Python selector + bash `--resume-phase` gate) and a negative pin that line 107 must not be the sole resume instruction without a Python branch.

### FINDING_29: [OUT_OF_SCOPE] `stall-recovery-report.sh` finalize consult was pre-existing
- **Reviewer(s)**: dyn-ship-state-output.txt, dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: Reviewers noted that `stall-recovery-report.sh` already consulted `finalize-state.sh`; this branch mostly extended docs/tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-state-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Bash 3.2 portability appears preserved
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: New shell test windows use Bash 3.2-safe constructs and no Bash 4-only features were identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Prompt-safety hardening positives
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Reviewer called out positive hardening in scout/subprocess prompt rendering, delimiter-breakout harnesses, and plan-mode aggregation filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Pre-existing raw path printing in prompt renderers
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Raw `PLAN_FILE` / `BALLOT_FILE` path printing into prompts is pre-existing and unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Commit-list observations
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Reviewer listed branch commits for context rather than raising a behavioral defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Cached plugin anti-halt prose drift
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: nit
- **Concern**: Cached-plugin copy still says “after `ship-pr.sh` exits” unconditionally, but workspace copy has been updated; reviewer marked this as not introduced by the branch diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Address the concern above.
