### FINDING_1: Architectural-invariant ci-fix cannot route without a failed CI run
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-Step8 Bgjob Contract
- **Severity**: major
- **Concern**: The planned architectural-invariant path does not define a runnable invariant-only branch before failed-run resolution. Compose-time invariant violations may have no `FAILED_RUN_ID` and green PR checks, yet the wrapper and lane currently require a numeric run ID and CI failure evidence. Without explicit branch ordering, canonical evidence materialization, and a lane carve-out, these violations can bail out instead of reaching delegated repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document the blocked-by Piece 3 contract explicitly, or add a firm ### MAY_UPDATE for python/larch/implement/ci_fixer_lane.py (and wrapper if needed) so invariant-primary invocations skip failed-run resolution and use invariant evidence as the sole failure-log input when NEEDS_USER_REASON=architectural-invariants-violation
  - From Cursor-Requirements: Extend the REWRITTEN ship-pr-ci-fix.md architectural-invariants branch with exact canonical paths, identity sidecar fields, and a single sanctioned materialization step (helper fence or explicit tmpdir writes) before invoking step-8-ci-fixer.sh.
  - From Cursor-dyn-Step8 Bgjob Contract: `ship-pr-exit-matrix.md` routes `architectural-invariants-violation` to `ci-fix` without requiring `FAILED_RUN_ID`, but `step-8-ci-fixer.sh` hard-fails when it cannot resolve a numeric run id and `ci_fixer_lane.main` always calls `_collect_evidence` before dispatch. A compose-time violation on a green PR never reaches delegated repair and regresses today’s first-branch inline repair in `ship-pr-ci-fix.md:11-13`. Specify an invariant-only branch before run-id resolution: materialize `architectural-invariants.md` plus matching `.identity.env`, skip CI run-id/evidence requirements when `NEEDS_USER_REASON=architectural-invariants-violation`, and add the minimal `ci_fixer_lane.py` carve-out (or equivalent wrapper flag) in firm plan files.
  - From Cursor-Arch: In the REWRITTEN ship-pr-ci-fix.md, make NEEDS_USER_REASON=architectural-invariants-violation the first branch: materialize canonical evidence, invoke the wrapper, and only then apply the empty FAILED_RUN_ID gate to ordinary CI-failure paths; pin ordering in test-architectural-guidelines-step.sh
  - From Cursor-dyn-Step8 Bgjob Contract: The current reference handles `NEEDS_USER_REASON=architectural-invariants-violation` before the empty `FAILED_RUN_ID` operator-bail at lines 15-17. The rewrite lists invariant evidence routing but does not explicitly retain first-branch ordering. A reorder can send no-run-id invariant handoffs to the empty-run-id bail and skip the delegated lane entirely. Keep `architectural-invariants-violation` as the first executable branch in the rewritten `ship-pr-ci-fix.md`, before empty `FAILED_RUN_ID` handling and before default wrapper dispatch; pin ordering in `test-architectural-guidelines-step.sh` and `scripts/test-implement-step8-exit3-first-fixer.sh`


### FINDING_2: Invariant evidence identity does not reject stale run IDs
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Codex-dyn-Step8 Bgjob Contract
- **Severity**: major
- **Concern**: The lane validator is planned to consume invariant evidence identified by `STARTING_HEAD` and `INPUT_FINGERPRINT`, but it does not validate the live `RUN_ID` or the complete tier/attempt identity. Evidence from another CI run with the same checkout state can therefore be accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add `RUN_ID` to the canonical evidence sidecar contract and reject missing or mismatched run IDs in the lane validator. Update the corresponding identity-materialization and tests.
  - From Cursor-Pragmatic: Add `python/larch/implement/ci_fixer_lane.py` and its focused tests to the plan. Persist and validate `RUN_ID` in the invariant identity sidecar.
  - From Codex-Pragmatic: Add an `### UPDATED:` heading for `python/larch/implement/ci_fixer_lane.py`. Require `RUN_ID` in the invariant identity sidecar and compare it with the validated lane run ID before consuming evidence
  - From Codex-Requirements: Add python/larch/implement/ci_fixer_lane.py as UPDATED. Require RUN_ID in architectural-invariants.md.identity.env and compare it with args.run_id before exposing the evidence to the fixer. Include matching and stale-run cases in the planned invariant evidence tests.
  - From Codex-dyn-Step8 Bgjob Contract: Make the invariant identity sidecar and lane validation include the live RUN_ID plus the complete tier attempt identity, or explicitly add the lane module to the firm changes. Add the planned stale run-ID and tier/attempt cases against that validator


### FINDING_3: Invariant evidence sidecar contract is underspecified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan does not specify the canonical invariant evidence paths, required identity keys, or fingerprint algorithm needed by the existing lane contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ship-pr-ci-fix.md, specify the exact writer steps and KV fields for architectural-invariants.md and .identity.env (including HEAD and shasum -a 256 of git diff --binary HEAD), and assert them in test-architectural-guidelines-step.sh


### FINDING_4: Wrapper handoff does not reliably preserve the failed run ID
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The thin Step 8 invocation does not reliably pass the authoritative failed run identity. The wrapper currently relies on `CI_RUN_ID` or PR re-resolution, while ship route handoffs write `FAILED_RUN_ID` or `MAIN_FAILED_RUN_ID`; this can select the wrong run or bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `skills/implement/scripts/step-8-ci-fixer.sh` to the plan. Read and validate `FAILED_RUN_ID` from the current route handoff or accept an explicit wrapper argument.
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/scripts/step-8-ci-fixer.sh: read FAILED_RUN_ID (and MAIN_FAILED_RUN_ID when present) from .ship-route-exit-handoff.env before PR re-resolution, and treat that value as authoritative when valid.


### FINDING_5: Wrapper harness still asserts dormant Step 8 wiring
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Step8 Bgjob Contract
- **Severity**: major
- **Concern**: The testing strategy invokes `test-step-8-ci-fixer.sh`, but the plan does not update its existing assertions that the wrapper is absent from the Step 8 prompt and ship path. The mandated harness will fail after the planned cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh to flip dormant assertions to active wiring checks (wrapper present, bgjob wait shape, forbid Agent/distill-log on default path)
  - From Codex-Arch: Rewrite these assertions for the active cutover. Require the wrapper in the intended prompt surface, preserve the production-Python non-wiring assertion if still applicable, and add the compact-result and retry-routing checks required by the new contract.
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh and replace dormant assertions with active wiring and protocol assertions.
  - From Codex-Pragmatic: Add `### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh` and replace the dormant assertion with the minimum active-cutover and wrapper-interface assertions required by the new contract
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh to assert production wiring (SKILL.md and ship-pr-ci-fix.md invoke the wrapper) and drop the not-wired checks; align test_implement_dispatch.py dormant test conversion with the new expectations.
  - From Cursor-dyn-Step8 Bgjob Contract: Add `### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh` to flip dormant assertions to require SKILL.md wiring while keeping production `ship.py` independent.


### FINDING_7: Wrapper performs an undocumented extra bgjob wait
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The wrapper performs `bgjob wait --max-wait-s 0` internally before deciding whether to start or rejoin a lane, while the planned orchestrator protocol separately requires identical documented waits. This creates two competing wait protocols and can cause premature routing or repeated start/rejoin behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the wrapper a start-or-identity-resolution operation that does not perform an undocumented wait, or explicitly make its internal wait the sole documented wait command and update the Step 8 fence and tests to use that exact command. Ensure one invocation cannot both perform an alternate wait and then require another wait protocol.


### FINDING_8: Post-wait choreography does not require wrapper finalization
- **Reviewer(s)**: Cursor-dyn-Step8 Bgjob Contract
- **Severity**: major
- **Concern**: The plan does not require a second wrapper invocation after the orchestrator’s documented waits. Directly consuming the bgjob result environment can bypass the wrapper’s `fixer-status.env` agreement checks and emit routing decisions without the required validation gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Step8 Bgjob Contract: The wrapper starts a tier and exits on fresh launch, while merge/status agreement checks run only on a later invocation after `BGJOB_STATUS=DONE`. The rewrite says the main agent performs documented `bgjob wait` calls and then consumes the compact envelope, but it never requires a second `step-8-ci-fixer.sh` finalize call. An implementer can parse `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env` directly and bypass the `fixer-status.env` disagreement gate at `step-8-ci-fixer.sh:180-200`. Document a fixed per-tier sequence in `ship-pr-ci-fix.md` and `skills/implement/SKILL.md`: wrapper start → parse dynamic `STEP` from `BGJOB_STATUS=STARTED` → repeated `bgjob wait --max-wait-s 270` → second wrapper call that alone may emit routable `RESULT=*` KVs; forbid direct consumption of bgjob result env on the default path.


### FINDING_9: Retry waits may use the wrong dynamic bgjob step slug
- **Reviewer(s)**: Cursor-dyn-Step8 Bgjob Contract
- **Severity**: major
- **Concern**: Retry tiers receive distinct dynamic bgjob step names, but the plan does not require capturing the emitted `STEP=` value and reusing it in every identical wait fence. A hardcoded step can wait on stale or unrelated registry state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Step8 Bgjob Contract: Each tier uses a distinct `implement-step8-ci-fixer-${ATTEMPT}-${TIER}-${SUFFIX}` step name. The plan adds SKILL.md wrapper/wait fences but does not require binding `--step` from the `BGJOB_STATUS=STARTED` line. A hardcoded wait fence would wait on the wrong registry row after `retry-next-tool`, letting stale evidence appear consumable or causing closed failure. Require the SKILL.md and fence-shape harness to parse/store the emitted `STEP=` value and reuse it verbatim in every identical wait fence for that tier; assert retries use different step slugs.


### FINDING_10: Post-success wrapper invocation loses the original step identity
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: After a fixer changes `HEAD`, a later wrapper invocation recomputes `STARTING_HEAD` from the repaired checkout. It can therefore derive a different step identity and reject the prior rounds file instead of emitting the successful reship result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add skills/implement/scripts/step-8-ci-fixer.sh as UPDATED. Persist or accept the launched step identity so post-DONE validation uses the original run ID, starting HEAD, fingerprint, tier, and attempt while still validating FINAL_HEAD separately. Add this case to the one-tier-success integration test.


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:140-180
- **Concern**: [SCOPE-REDUCTION] The plan cuts over to the existing wrapper without updating its incompatible wait interface. Scenario: The wrapper performs its own `bgjob wait --max-wait-s 0` before starting or finalizing a tier. After the prompt performs the documented repeated wait, it must invoke the wrapper again to validate results, which adds a non-identical wait and violates the acceptance contract that only identical documented waits occur
- **Proposed resolution**: Add an `### UPDATED:` heading for this wrapper. Give it explicit start and result-validation modes, or an equivalent minimal interface, so the prompt owns the sole documented wait loop and result validation does not issue another wait


### FINDING_1: Invariant-evidence materialization helper is unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan requires a sanctioned helper to materialize `$IMPLEMENT_TMPDIR/architectural-invariants.md` and its `.identity.env` sidecar, but names no implementation surface, invocation contract, input mapping, output bounds, or identity fields. The referenced files are not currently written by any identified runtime component, so invariant-primary recovery is not implementable from the plan alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a firm `### NEW:` or `### UPDATED:` deliverable for the materialization helper (CLI verb or wrapper start hook), document its inputs (`DETAIL`/`DETAIL_FILE` and/or `architectural-invariant-note.md`), outputs, and the exact identity fields written before lane dispatch.
  - From Cursor-Pragmatic: Add a firm `### NEW:` or `### UPDATED:` helper (Python CLI verb or thin wrapper), specify inputs from handoff `DETAIL`/`DETAIL_FILE` and existing invariant note artifacts, and require bounded redacted body bytes plus the `.identity.env` sidecar before wrapper start.
  - From Cursor-Requirements: Add one firm helper surface (for example a `python/cli.py` verb or thin wrapper script), list it under Files to modify/create, and wire ship-pr-ci-fix.md to invoke it with explicit inputs from `NEEDS_USER_REASON` / `DETAIL` / `DETAIL_FILE` and the launch identity fields.


### FINDING_2: Invariant sidecar identity ordering and non-CI run identity are circular
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The plan requires invariant evidence to contain `TIER`, `ATTEMPT`, and dynamic `STEP` before wrapper start, while wrapper start is also responsible for selecting or emitting those values. It likewise leaves the canonical non-CI `RUN_ID` undefined. This creates a circular launch contract in which evidence cannot be validated before launch and launch cannot proceed without the evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define a two-phase allocation contract that allocates and persists the immutable launch identity before evidence materialization, then launches only after the helper writes and validates the sidecar, or change the sidecar contract so its pre-launch fields are distinct from the post-allocation `STEP`
  - From Codex-Pragmatic: Move evidence materialization into wrapper start after identity selection, define the canonical invariant-only RUN_ID, and atomically write and validate the evidence plus sidecar before launching the lane
  - From Codex-Requirements: Make wrapper start own invariant preparation after it selects the tier, attempt, step, and explicit invariant-mode run identity. Define the stable `RUN_ID` source and require the wrapper or a prepare subcommand to materialize the evidence atomically from the validated handoff `DETAIL` or `DETAIL_FILE` and durable invariant note before launching the lane.


### FINDING_4: Failed-run handoff source and conflicting-ID precedence are undefined
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan directs the wrapper to read `MAIN_FAILED_RUN_ID` from a route-exit handoff that does not currently contain it, while the authoritative main-health value is persisted in `main-health.env`. It also does not define precedence or fail-closed behavior when valid `FAILED_RUN_ID` and `MAIN_FAILED_RUN_ID` values coexist but disagree. The wrapper could therefore select the wrong PR or default-branch run and collect unrelated evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Read `FAILED_RUN_ID` from `.ship-route-exit-handoff.env` when present; fall back to `MAIN_FAILED_RUN_ID` from `$IMPLEMENT_TMPDIR/main-health.env` (not the route-exit file). Document precedence when both exist and fail closed on malformed values.
  - From Codex-Arch: Specify the accepted relationship between the two fields, including which field applies to PR versus main-branch failures, and fail closed on an unexplained disagreement before tier selection or evidence collection
  - From Codex-Pragmatic: Define route-aware precedence, or fail closed on disagreement, and cover the valid-but-different case in the planned authoritative-handoff fixture
  - From Cursor-Requirements: Specify and implement the real source of truth: read `MAIN_FAILED_RUN_ID` from `main-health.env` (or teach ship route-exit to copy it into the handoff), document precedence when both PR and main run IDs exist, and add a fixture for distinct PR vs main run IDs.
  - From Codex-Requirements: Define route-specific run-ID selection using the handoff reason or an authoritative field. Fail closed on an unexplained disagreement, and add the disagreement case to the mandated handoff integration coverage.


### FINDING_5: Invariant-primary kill-switch behavior is undefined without a failed CI run
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan preserves the existing `LARCH_CI_FIXER=0` inline contract around `FAILED_RUN_ID` and `gh run-logs`, but invariant-primary explicitly permits no failed CI run. The kill-switch path therefore has no defined evidence source or attempt accounting for invariant-only violations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an invariant-specific kill-switch carve-out: use validated invariant evidence (not `gh run-logs`), define per-violation sentinel/counter paths that do not require `FAILED_RUN_ID`, and forbid the CI-log inline repair shape when only invariant evidence exists.


### FINDING_7: Retry-next-tool does not preserve waterfall lineage after HEAD changes
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The plan does not define how a retry after a fixer changes `HEAD` preserves waterfall progress. Because rounds identity is bound to `STARTING_HEAD` and `INPUT_FINGERPRINT`, a fresh start may reject prior rounds as foreign or restart at the first tier rather than selecting the next tool.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Persist a waterfall lineage and attempted-tier set separately from each tier's immutable launch identity, then make the planned multi-tier fixture return retry-next-tool after changing HEAD and verify that the next tier starts exactly once


