### FINDING_1: Recovery gate can be bypassed by Step 18 routing
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: A standalone Step 17.5 placed before Step 18 is not guaranteed to run because existing stall and continuation paths still jump directly to Step 18, so early/mid-run stalls can skip classification, bug filing, and recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Place 17.5 at the start of the Step 18 section (before cleanup prose) and retarget all skip-to-Step-18 directives to Step 17.5, or add an explicit Step 18 entry guard that always runs 17.5 when STALL_TRACKING=true
  - From Cursor-Edge, Cursor-Pragmatic: Retarget every STALL_TRACKING bail to Step 17.5 (or run 17.5 as the first Step 18 sub-step before token refresh) and add a structure/anti-halt grep pin for the new step boundary
  - From Cursor-Innovation: Early Step 0 coder/bootstrap stalls and preflight bails jump straight to Step 18 cleanup with no recovery attempt; the gate never runs despite the single-intercept design Move the gate to Step 18 entry (before token refresh/teardown) or retarget every STALL_TRACKING skip-to-18 directive to skip-to-17.5; add test-implement-structure pins for the chosen routing
  - From Codex-Innovation: Make the recovery gate the first block inside Step 18 before teardown, or update every STALL_TRACKING cleanup jump to target Step 17.5; add a grep/harness check that all stall routes pass through the gate.
  - From Cursor-Pragmatic, Cursor-Requirements: Add a single Step 18 entry guard: before any Step 18 work, if Step 17.5 has not run and STALL_TRACKING=true, execute Step 17.5; or retarget all skip-to-Step-18 directives to skip-to-Step-17.5
  - From Codex-Requirements: Make the recovery gate the first mandatory sub-step of Step 18 or update every STALL_TRACKING skip/bail target to Step 17.5; add tests for representative Step 0, Step 3, Step 5, and ship-pr stalls
  - From Codex-dyn-cross-contract-sync: Update both continuation directives to say continue to Step 17.5, then Step 17.5 continues to Step 18


### FINDING_2: Issue input file format is incompatible with batch parsing
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: The planned issue-input-file contract describes title-plus-body or ambiguous assembly, but `/larch:issue --input-file` batch parsing expects generic `### <title>` item headings, so bug filing can silently produce zero items or malformed bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the helper contract to emit generic batch markdown as `### [Bug] /implement stall: ...` followed by the body, or use single-mode `/issue --body-file <bug-body> "[Bug] ..."` instead of `--input-file`
  - From Codex-Pragmatic: Emit the generic batch shape ### [Bug] /implement stall: <class> at <step> followed by the body, or invoke /larch:issue single mode with --body-file and an explicit title
  - From Codex-dyn-cross-contract-sync: Make references/stall-recovery.md call stall-recovery-report.sh issue-input-file explicitly and document that it writes a single generic batch item headed by ### [Bug] ...


### FINDING_3: Step 5 recovery bypasses the established review wrapper
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Step 5 recovery names or implies direct `review-and-fix` invocation instead of the shipped `run-step5-review.sh` wrapper, risking wrong paths, missing session/run context, and violation of the Family B background+monitor contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify reuse of `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh --mode loop --starting-round <next>` with the same background+monitor envelope as Step 5; only call `skills/review-and-fix/scripts/review-and-fix.sh` through existing wrapper modes where Step 5 already does so
  - From Codex-Pragmatic: Route recovery through scripts/run-step5-review.sh --mode loop with the same Family B background+monitor pattern, or fully specify a direct review-and-fix invocation with all wrapper-provided args and the monitor envelope
  - From Codex-Requirements: Use ${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round ... or fully specify ${CLAUDE_PLUGIN_ROOT}/skills/review-and-fix/scripts/review-and-fix.sh with required args


### FINDING_4: Step 6 checks recovery conflicts with the no-edit stall contract
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: The planned `step6-checks` recovery would run repair/main-agent edits for stalls that the existing Step 8 Exit 4 contract says are unrecoverable and must not trigger main-agent edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Split pre-ship Step 3/6 check failures from `ship-pr.sh` `PHASE=checks` stalls in the classifier; keep the latter `unrecoverable` unless the plan also updates the Step 8+ invariant and tests the new recovery path
  - From Codex-Edge: Revise the plan to either update the Step 8 exit-4/STall_STEP=6 prose and tests to allow this new recovery path, or classify Step 6 checks stalls as contract-failure/unrecoverable and remove the step6 main-agent edit dispatch
  - From Codex-Innovation: Either explicitly supersede/remove the STALL_STEP=6 prohibition and define the sanitized evidence/commit path, or classify STALL_STEP=6 as contract-failure/unrecoverable.
  - From Codex-Pragmatic: Either update the Exit 4 contract and its structural tests to delegate STALL_STEP=6 to Step 17.5, or remove step6-checks recovery and classify these stalls as unrecoverable
  - From Codex-dyn-cross-contract-sync: Either update the Exit 4 STALL_STEP=6 contract and its tests to permit the new Step 17.5 recovery, or classify those stalls as unrecoverable and remove the step6-checks repair case


### FINDING_5: Same-cause repeat lacks a durable prior-signature interface
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-state-rewrite-auditor
- **Severity**: important
- **Concern**: Same-cause-repeat classification depends on prior failure signatures, but the classifier contract does not define how prior signatures or attempts state are passed and persisted across retries or restarts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a `classify --attempts-file` or `--previous-signature` contract, have the helper read/update only validated KV state under `$IMPLEMENT_TMPDIR`, and pin the same-cause test to that interface
  - From Codex-Pragmatic: Add an explicit --attempts-file or --prior-signature input to classify, or move same-cause comparison into stall-recovery.md and keep classify limited to emitting the current signature
  - From Codex-dyn-state-rewrite-auditor: Define the classifier/retry loop contract to read PRIOR_FAILURE_SIGNATURE from the last complete record in stall-recovery-attempts.env, append the current classified signature atomically after each attempt, and add a harness case that restarts with only the persisted attempts file available


### FINDING_6: current-implement-env prelude lacks a writer and trust model
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned Step 17.5 prelude relies on `current-implement-env-$PPID.sh`, but `/implement` currently rehydrates from `$IMPLEMENT_TMPDIR/session-env.sh` and has no documented writer, tests, or security model for the new sourceable file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use the existing `/implement` rehydration pattern from `session-env.sh`; if a `current-implement-env` mechanism is desired, add the writer, AGENTS/SECURITY documentation, and harness coverage in the same plan
  - From Codex-Pragmatic: Use the adjacent Step 17/18 key-based rehydration pattern, or add a real sourceable current-implement-env writer plus security docs and tests before relying on that prelude


### FINDING_7: Test harness wiring targets a nonexistent make test aggregate
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan wires the new harness to `make test`, but this repository runs harnesses through `test-harnesses` shards and `make lint`, so the new target may be omitted from normal validation and shard coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the target to `.PHONY`, define it with `scripts/harness-timer.sh`, and place it on one `test-harnesses-N` shard line so `make lint` and shard-coverage checks exercise it
  - From Codex-Innovation: Add the target to .PHONY, give it a recipe, assign it to exactly one test-harnesses-N shard, and update docs/linting.md if the public target list changes.
  - From Codex-Requirements: Add test-stall-recovery-report to .PHONY and exactly one test-harnesses-N shard; state final validation as bash scripts/relevant-checks.sh or make lint


### FINDING_8: Gate can miss stalls when ship-pr-state is absent
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Early Step 0/3/6 stalls may set in-memory `STALL_TRACKING=true` without a `ship-pr-state.sh`; if Step 17.5 only consults the state file, it can treat real stalls as no-stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Either normalize every stall path into a canonical ship-pr-state.sh before cleanup, or have Step 17.5 treat the in-memory STALL_TRACKING variable as authoritative fallback; add Step 3 and Step 6 pre-Step-8 recovery tests.
  - From Codex-Requirements: Have Step 17.5 consult in-memory STALL_TRACKING and session-env fallback before deciding to skip, or require all stall paths to persist a minimal ship-pr-state.sh; test missing-state recovery


### FINDING_9: Recovery success routing can skip downstream validation
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan simultaneously says step-specific recovery returns to the failed step and that success clears stall state and continues to Step 18, which can bypass required review, checks, ship-pr, notes, CI, or final reporting after mutating recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define one control-flow model: tail-call the recovered step and let the normal state machine run through Step 16 and Step 17 again, or restrict post-Step-17 recovery to non-mutating ship-pr resumes that have completed the full downstream workflow.
  - From Codex-Requirements: Make the success continuation explicit per RESUME_HINT; only go to Step 18 after the resumed workflow reaches the normal terminal path


### FINDING_10: Dry-run handling cannot reliably prevent issue creation
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: The dry-run flag is attached to a helper that does not perform the `/larch:issue` call, and the planned tests do not prove dry-run prevents real issue creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Move dry-run branching into references/stall-recovery.md before the Skill call, or make the reference consume a helper-emitted DRY_RUN decision; test that no issue command runs in dry-run mode
  - From Codex-dyn-cross-contract-sync: Add a harness case proving dry-run prevents real issue creation and emits/prints the expected artifact; specify whether the reference passes /issue --dry-run or skips the Skill call under this env var


### FINDING_11: Sanitization allowlists and leak tests are incomplete
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-sanitization-tracer, Codex-dyn-sanitization-tracer
- **Severity**: important
- **Concern**: Public bug body/comment/input/chat surfaces are not backed by a complete explicit allowlist, SECURITY.md coverage, or parity tests, so raw classifier state, paths, logs, session keys, or consumer output can leak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add SECURITY.md updates for stall-report sanitization and residual risk; extend harness deny-list/redaction assertions to bug-comment, issue-input-file, and dry-run/chat output
  - From Cursor-dyn-sanitization-tracer: Enumerate a separate `bug-comment` allowlist in `stall-recovery-report.md`; map every classify evidence source to a sanitized output token; forbid dumping raw classify KV lines (`BAIL_REASON`, etc.); hash or tokenize test/lint identifiers instead of echoing paths
  - From Codex-dyn-sanitization-tracer: Define separate explicit output schemas for bug-body and bug-comment in stall-recovery-report.md, including per-source allowed keys and transforms. Forbid rendering raw classifier output; render only named sanitized fields, hashes, enums, and bounded labels.
  - From Codex-dyn-sanitization-tracer: Put the allowlist in a machine-readable source or mirrored shell array, document the same list verbatim, and have the harness diff doc vs script vs tests. Seed every non-allowlisted source key from ship-pr-state.sh, execution-issues.md, session-env.sh, and failure-detail-log with unique sentinel values, then assert absence across bug-body, bug-comment, issue-input-file, and consumer chat-print output.


### FINDING_12: Failure detail log is not safely wired or validated
- **Reviewer(s)**: Codex-dyn-sanitization-tracer
- **Severity**: important
- **Concern**: The Step 17.5 classify call does not clearly pass validated failure detail logs, and an implementation could either omit high-signal evidence or read arbitrary/symlinked sensitive files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sanitization-tracer: Make stall-recovery.md pass BAIL_FAILURE_DETAIL_LOG or the captured FAILURE_DETAIL_LOG to classify when present. In stall-recovery-report.sh, require an absolute canonical regular non-symlink path physically under IMPLEMENT_TMPDIR, cap reads, and extract only allowlisted patterns/hashes. Add outside-tmpdir, symlink, relative-path, and missing-file tests.


### FINDING_13: Missing-state and exit-code contracts conflict
- **Reviewer(s)**: Codex-dyn-sanitization-tracer, Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: The plan gives contradictory meanings for missing `ship-pr-state.sh` and classify exit codes, so early stalls may fail classification instead of producing a bounded unrecoverable report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sanitization-tracer: Make missing ship-pr-state.sh a non-fatal classified outcome when session-env or execution-issues exists, with FAILURE_CLASS=unrecoverable and a bounded reason token. Reserve exit 3 for malformed/unparseable present state, and update the tests to cover missing-state fallback separately from malformed-state failure.
  - From Codex-dyn-cross-contract-sync: Choose one meaning for missing state files, then add the same exit-code table to stall-recovery-report.md and references/stall-recovery.md and assert it in tests


### FINDING_14: Recovery state rewrite lacks durable atomic ordering
- **Reviewer(s)**: Cursor-dyn-state-rewrite-auditor, Codex-dyn-state-rewrite-auditor
- **Severity**: important
- **Concern**: The success path can clear in-memory stall state before durably and atomically updating `ship-pr-state.sh`, while Step 18 later restores from disk, risking stale, truncated, or malformed stall state after a crash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-state-rewrite-auditor: Orchestrator clears the variable then crashes/halt before disk write; Step 18 restore-finalize-state.sh reads stale STALL_TRACKING=true from ship-pr-state.sh (scripts/implement-finalize.sh:1230-1242 Branch A [STALLED]) despite successful recovery In §5 success path: (1) atomically persist STALL_TRACKING=false (and STALL_STEP= per scripts/ship-pr.sh:983-985) to ship-pr-state.sh; (2) then assign orchestrator STALL_TRACKING=false; (3) optionally re-run write-final-report.sh after persist when Step 17 already emitted stalled
  - From Codex-dyn-state-rewrite-auditor: Specify the exact pattern in stall-recovery.md: write the complete revised ship-pr-state.sh to a same-directory temp file, validate syntax/readback, then mv -f it over ship-pr-state.sh; on failure leave STALL_TRACKING=true and route terminal failure
  - From Codex-dyn-state-rewrite-auditor: Revise the success path to persist atomically first, verify ship-pr-state.sh now has STALL_TRACKING=false with key extraction, then update any in-memory variable and continue to Step 18


### FINDING_15: Attempts state is not initialized before first retry
- **Reviewer(s)**: Codex-dyn-state-rewrite-auditor
- **Severity**: important
- **Concern**: The attempts file is only loosely described, so an abrupt exit during the first recovery iteration can leave no durable attempt record for retry caps, comments, or diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-rewrite-auditor: Create stall-recovery-attempts.env immediately after the first classify and before issue filing or retry dispatch, using temp-then-mv, with attempt index 0, FAILURE_CLASS, FAILURE_SIGNATURE, RESUME_HINT, and cap metadata


### FINDING_16: Retry cap authority can diverge
- **Reviewer(s)**: Cursor-dyn-cross-contract-sync, Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: The plan references a `--caps` mechanism that is not in the helper subcommand list while also saying caps live in docs/reference prose, creating multiple possible authorities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-contract-sync: Pick one mechanism: add a documented `caps` subcommand to `.sh`/`.md` and reference it from `references/stall-recovery.md`, or delete `--caps` from Approach and require caps be read only from `stall-recovery-report.md` (no second copy in references)
  - From Codex-dyn-cross-contract-sync: Either add a real caps subcommand to every subcommand list/doc/test, or make stall-recovery-report.md the sole authority and have references/stall-recovery.md point to it without duplicating values


### FINDING_17: RESUME_HINT enum does not match dispatch arms
- **Reviewer(s)**: Codex-dyn-cross-contract-sync
- **Severity**: important
- **Concern**: The planned classifier emits an open-ended or inconsistent set of `RESUME_HINT` values, while the reference dispatch uses different arms and may conflate failure class with resume hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cross-contract-sync: Define an exact RESUME_HINT enum in the script/report doc/reference, remove etc, use FAILURE_CLASS for contract-failure/unrecoverable, and add a harness assertion comparing emitted tokens to reference cases

