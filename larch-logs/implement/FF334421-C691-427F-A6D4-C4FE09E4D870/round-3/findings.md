### FINDING_1: Branch bundles unrelated ship-default, design, and log changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The branch combines the Python ship-default flip with unrelated design scope/review work and large log artifacts, making review, bisect, rollback, and CI attribution harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: ship-pr-state.sh parsing/writing is not canonicalized
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `ship-pr-state.sh` is parsed inline while other paths use canonical KV readers, so quoted or shell-escaped values can be interpreted differently and break state preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Terminal finalize/stall metadata is written through divergent paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multiple terminal/finalize writers populate overlapping stall and PR metadata from different contexts, so terminal state can become path-dependent or stale, and tests do not fully cover common stalled paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Python version floor is inconsistent across runtime, docs, and tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Runtime guards/tests still allow or simulate Python 3.11 in places while SKILL/operator docs require 3.12+, causing direct invocation and CI expectations to diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Remaining Step 8+ docs still describe bash as the active driver
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-prose-output.txt
- **Severity**: important
- **Concern**: Several operator-facing references still name `ship-pr.sh` as the active or sole Step 8+ driver, which can mislead default-path orchestrators/operators away from the Python selector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-routing-prose-output.txt: Lead with “re-invoke the active Step 8+ driver (Python selector argv unless `LARCH_SHIP_PR_IMPL=bash`)” and demote bash/`Invoke:` to the opt-in clause.
  - From dyn-routing-prose-output.txt: Align with line 993/1172 opener: “active Step 8+ driver (default `python/ship.py`; bash when `LARCH_SHIP_PR_IMPL=bash`)” and “when the driver reaches `PHASE=done`”.

### FINDING_6: Selector/routing structure-test coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dual-path Step 8+ routing is spread across prose and awk pins, with gaps for anti-halt, stall recovery, conflict-resolution, and stale contract docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Design/log artifacts inflate review surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Large design/log additions are unrelated to the ship-flip functional review surface and increase review and merge-conflict cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] NEVER #8 examples still cite only ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The examples drift from active-driver terminology by naming only `ship-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Exit 0 continuation can re-enter bash on the Python default path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-parity-contract-output.txt, dyn-routing-prose-output.txt
- **Severity**: important
- **Concern**: The Exit 0 matrix still contains an unqualified `ship-pr.sh` re-invocation tail, so a default Python run with a non-terminal phase can resume through legacy bash instead of the Python selector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-parity-contract-output.txt: Qualify that “Otherwise” branch the same way as Exit 3 step 12 and OOS re-entry: re-invoke `python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py"` (including `--state-file`) unless `LARCH_SHIP_PR_IMPL=bash`.
  - From dyn-routing-prose-output.txt: Prefix that “Otherwise…” clause with an explicit bash-only gate and add a parallel default-path line: re-invoke the Python selector foreground argv (including `--state-file`), with no `--resume-phase`.
  - From dyn-routing-prose-output.txt: Extend the Python selector Exit 0 prose to mirror the Exit 0 bullet’s OOS and non-terminal re-invoke branches, or relabel/move those bullets into a driver-agnostic section.

### FINDING_10: Stale STALL_TRACKING can survive healthy or successful writes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-coherence-output.txt
- **Severity**: important
- **Concern**: Routine and postmerge state writes can preserve stale `STALL_TRACKING`/`STALL_STEP`, creating split-brain state between `ship-pr-state.sh` and `finalize-state.sh` and confusing Step 18 restore/classify behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-state-coherence-output.txt: Write terminal OK finalize only after the line-1208 `_write_ship_state(..., phase="done", terminal_outcome=Outcome.OK)` succeeds, or atomically update both files in one helper; alternatively clear/normalize `STALL_TRACKING`/`STALL_STEP` in `ship-pr-state.sh` immediately before writing OK finalize at 1195.
  - From dyn-state-coherence-output.txt: Either add `STALL_TRACKING`/`STALL_STEP` to the non-terminal prune set whenever `terminal_outcome is None` and `ctx.stall_tracking` is false, or explicitly zero them in that branch before merge-overlay; keep the orchestrator-seed preservation behavior only when `ctx.stall_tracking` is still true or the key is missing.

### FINDING_11: Step 18 restore gate lacks executable branch coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The conditional restore behavior is only prose-pinned, so skip/run regressions on the Python path could pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Python default ships despite documented parity gaps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-parity-contract-output.txt
- **Severity**: important
- **Concern**: The default Python ship driver is enabled while SECURITY.md documents unresolved parity/soak issues, exposing unset-`LARCH_SHIP_PR_IMPL` users to known gaps unless bash rollback is explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-parity-contract-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Empty/unset LARCH_SHIP_PR_IMPL default is only manually verified
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The empty-env default-to-Python behavior lacks CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: ship-pr-state.sh writes are vulnerable to symlink swap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Containment is checked only at entry, while later writes follow symlinks, allowing mid-run state-file replacement to redirect writes under the same UID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Unvalidated state keys and overlays can poison terminal metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Merged state keys and overlayed repo/PR fields are not sufficiently allowlisted, quoted, or slug/URL-validated before being persisted into state/finalize files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Corrupt or unreadable ship-pr-state.sh now aborts instead of recovering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The new fail-closed read path can turn partially corrupt state into an `INTERNAL_ERROR` rather than recovering or retrying with a fresh overlay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Exit-matrix prose mixes bash-only and shared Python orchestration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-routing-prose-output.txt
- **Severity**: important
- **Concern**: The bash-only gate surrounds shared OOS, CI-fix, Exit 6, and state-reading guidance that Python still depends on, creating ambiguity about whether default-path orchestrators should skip or apply the matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-routing-prose-output.txt: Split into (a) a **shared** “exit-code orchestration” section (OOS checkpoint, autonomous CI-fix, Exit 6 counter/stall persistence) applying to both drivers, and (b) a bash-only subsection for `ship-pr-state.sh` continuation parsing, `--resume-phase`, and per-`$PHASE` retry files.
  - From dyn-routing-prose-output.txt: Lead with path split: default path parses JSON first and does not read `ship-pr-state.sh` for continuation; bash path parses exit code then reads `ship-pr-state.sh`; scoped reads (OOS, `ship_pr_pre_push`) stay in a separate bullet.
  - From dyn-routing-prose-output.txt: Split into two blockquotes (bash continuation vs Python JSON continuation) or move Python instructions up to the selector / shared section.

### FINDING_18: Exit 6 fourth-failure stall persistence is prompt-enforced only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If the orchestrator misses the prompt-side rewrite after repeated transient failures, disk state may lack `STALL_TRACKING` for teardown/classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Missing focused RESUME_PHASE/CALLER_KIND preservation regression
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-coherence-output.txt
- **Severity**: nit
- **Concern**: Existing tests only partially cover preservation of resume tokens; there is no focused routine-refresh regression for non-empty `RESUME_PHASE`/`CALLER_KIND`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-state-coherence-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] write-final-report.sh state merge is outside plan traceability
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` now merges line-count KVs into `ship-pr-state.sh`, but that path was not in the plan file list, so rationale and acceptance coverage are unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] stall-recovery report does not use finalize-state.sh for phase fallback
- **Reviewer(s)**: dyn-state-coherence-output.txt
- **Severity**: latent
- **Concern**: `stall-recovery-report.sh` falls back to finalize for `stall_step` but not `phase`; reviewer notes this predates the branch and is unlikely to bite when terminal files stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-coherence-output.txt: Address the concern above.

### FINDING_22: Python pre-push conflict handoff lacks documented CONFLICT_FILES source
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: important
- **Concern**: Exit 4 conflict docs still describe bash contract-stream `CONFLICT_FILES`, while the Python driver writes conflict files only to merged `ship-pr-state.sh`; the Python scoped-read list omits that key.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Document that on the default Python path, after exit 4 with `RESUME_PHASE=ship-pr-rrr-phase14` / `CALLER_KIND=ship_pr_pre_push`, read `CONFLICT_FILES` from `$IMPLEMENT_TMPDIR/ship-pr-state.sh` (post `--state-file` merge); add `CONFLICT_FILES` to the Python scoped-read key list; update `conflict-resolution.md` and `subskill-invocation.md` accordingly.
  - From dyn-parity-contract-output.txt: Split the sentence: bash opt-in emits `CONFLICT_FILES` on the contract stream; default Python writes it into `ship-pr-state.sh` only.

### FINDING_23: Exit 3 docs conflate bash BAIL_REASON with Python JSON needs_user_reason
- **Reviewer(s)**: dyn-parity-contract-output.txt, dyn-routing-prose-output.txt
- **Severity**: important
- **Concern**: Python exit-3 routing is JSON-first, but prose and telemetry still refer to `BAIL_REASON`/state-file behavior, risking skipped CI-fix routing or classify evidence gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Either document that Python exit-3 paths must not rely on state-file `BAIL_REASON` (JSON `needs_user_reason` is authoritative), or persist a non-finalize `BAIL_REASON`/`FAILED_RUN_ID` pair into `ship-pr-state.sh` on NEEDS_USER_INPUT writes for parity with bash telemetry and classify evidence.
  - From dyn-routing-prose-output.txt: Duplicate the trigger with explicit path guards, e.g. “on bash path when `BAIL_REASON=…`; on default Python path when JSON `needs_user_reason` is …”.

### FINDING_24: Some Python needs_user_reason tokens lack explicit selector rows
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: latent
- **Concern**: `unsupported-rebase-continuation` and `checkout-mismatch` can fall through to generic handling instead of a defined stall/resume/operator path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Add explicit selector rows for both tokens (likely: user bail with clear operator message, or a dedicated re-seed/restart path), matching how `python/README.md` describes `unsupported-rebase-continuation`.

### FINDING_25: ShipError outcome handling is split across envelopes
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: latent
- **Concern**: Similar `ShipError`/terminal failures can become different exit codes, JSON outcomes, and disk-finalize behavior depending on whether they surface inside `run_ship` or outer `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Route all terminal `ShipError`/`Stalled` outcomes through one envelope builder in `main()` so exit code, JSON `outcome`, and optional terminal disk writes stay aligned; keep `INTERNAL_ERROR` strictly for truly unexpected exceptions.

### FINDING_26: Unified Invoke fence is described as bash-only despite containing canonical Python argv
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: important
- **Concern**: Post-fence prose can make default-path orchestrators skip the canonical Python branch and reconstruct an incomplete invocation from selector prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: State explicitly that the default path runs the **Python branch of the unified `Invoke:` fence** (or rename/restructure so the canonical launcher is driver-neutral, not “fenced `ship-pr.sh` invocation”).

### FINDING_27: Python Exit 6 counter wording reintroduces per-phase semantics
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: latent
- **Concern**: The Python retry counter is phase-agnostic, but prose still says to increment “for this PHASE.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: For the Python path, say “increment `ship-pr-net-retries-python.count` on each Exit 6 (phase-agnostic)”; reserve “for this `PHASE`” language for the bash per-phase counter only.

### FINDING_28: [OUT_OF_SCOPE] stall-recovery classify coverage already exists
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes existing tests cover finalize-only stall classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Pre-push conflict handoff intentionally omits finalize-state.sh
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes the missing `finalize-state.sh` on `PrePushConflictHandoff` is intentional and bridged by Step 18 restore.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Recovery blockquote appears already fixed
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes the pre-fence recovery blockquote no longer contains the earlier bare inline `Invoke:` issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] NEVER #11/#13 and Step 18 restore read coherently
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes those rewrites appear coherent, with bash restoring when state exists and Python skipping when finalize is current.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Harness does not pin several routing-prose regressions
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: nit
- **Concern**: Structure tests pin some selector behavior but do not assert absence of unqualified Exit 0 `ship-pr.sh`/`Invoke:` tails or the Exit 3 `BAIL_REASON` vs `needs_user_reason` split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: Address the concern above.
