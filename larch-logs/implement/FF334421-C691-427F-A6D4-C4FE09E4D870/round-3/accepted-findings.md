### FINDING_1: Branch bundles unrelated ship-default, design, and log changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The branch combines the Python ship-default flip with unrelated design scope/review work and large log artifacts, making review, bisect, rollback, and CI attribution harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


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


### FINDING_14: ship-pr-state.sh writes are vulnerable to symlink swap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Containment is checked only at entry, while later writes follow symlinks, allowing mid-run state-file replacement to redirect writes under the same UID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


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


### FINDING_9: Exit 0 continuation can re-enter bash on the Python default path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-parity-contract-output.txt, dyn-routing-prose-output.txt
- **Severity**: important
- **Concern**: The Exit 0 matrix still contains an unqualified `ship-pr.sh` re-invocation tail, so a default Python run with a non-terminal phase can resume through legacy bash instead of the Python selector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-parity-contract-output.txt: Qualify that “Otherwise” branch the same way as Exit 3 step 12 and OOS re-entry: re-invoke `python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py"` (including `--state-file`) unless `LARCH_SHIP_PR_IMPL=bash`.
  - From dyn-routing-prose-output.txt: Prefix that “Otherwise…” clause with an explicit bash-only gate and add a parallel default-path line: re-invoke the Python selector foreground argv (including `--state-file`), with no `--resume-phase`.
  - From dyn-routing-prose-output.txt: Extend the Python selector Exit 0 prose to mirror the Exit 0 bullet’s OOS and non-terminal re-invoke branches, or relabel/move those bullets into a driver-agnostic section.


