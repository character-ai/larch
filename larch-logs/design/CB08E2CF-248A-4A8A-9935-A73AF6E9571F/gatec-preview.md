## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

# Step 8 bgjob cutover and inline-fallback removal

## Difficulty assessment

Confidence: medium. The wrapper and lane exist, but this cutover must activate them with a complete launch contract: explicit identity allocation, invariant-evidence materialization, route-aware failed-run selection, lineage across changed `HEAD`s, one wait owner, and a defined invariant kill-switch path.

This is HARD because it changes the Step 8 prompt contract, bgjob lifecycle, wrapper interface, persisted-result validation, retry routing, invariant evidence, route handoffs, and the only sanctioned inline recovery exception.

## Approach

1. Replace the default Step 8 Agent-tool procedure with a three-phase wrapper protocol per waterfall tier:
   1. **start**: invoke `step-8-ci-fixer.sh --start` to select the tier, allocate and persist its immutable launch identity, prepare invariant evidence when required, launch one bgjob, and emit `BGJOB_STATUS=STARTED` with the dynamic `STEP`;
   2. **wait**: capture that emitted `STEP` and run only `python3 python/cli.py bgjob wait --step "$STEP" --max-wait-s 270`, repeating the byte-identical command after `BGJOB_STATUS=WAIT`;
   3. **finalize**: after `BGJOB_STATUS=DONE` and `BGJOB_RC=0`, invoke `step-8-ci-fixer.sh --finalize --step "$STEP"` to validate the completed bgjob result against its persisted launch envelope and `fixer-status.env`, then emit the sole compact routable `RESULT=*` envelope.
2. Make the Step 8 prompt the only wait owner. Remove the wrapper’s internal `bgjob wait --max-wait-s 0` behavior. Neither start nor finalize may poll or wait.
3. Persist two related but distinct state surfaces:
   - an immutable, step-keyed launch envelope containing `MODE`, `RUN_ID`, `STARTING_HEAD`, `INPUT_FINGERPRINT`, `TIER`, `ATTEMPT`, and `STEP`;
   - a waterfall-lineage record keyed by stable recovery identity and mode, containing the attempted-tier set and completed retry progression.
   
   A retry after a fixer changes `HEAD` retains the same lineage and starts exactly the next untried tier, while its new launch envelope binds that tier to the current `HEAD` and current `git diff --binary HEAD` fingerprint.
4. Define the canonical invariant-primary `RUN_ID` as the validated `LARCH_RUN_ID` from `$IMPLEMENT_TMPDIR/session-env.sh`. Ordinary CI-failure recovery continues to use the selected numeric GitHub Actions run ID. The lane must accept the invariant run identity only in explicit invariant-primary mode.
5. Make wrapper start own invariant preparation after it allocates `TIER`, `ATTEMPT`, `STEP`, `STARTING_HEAD`, and `INPUT_FINGERPRINT`. It invokes one sanctioned Python helper that atomically writes:
   - `$IMPLEMENT_TMPDIR/architectural-invariants.md`
   - `$IMPLEMENT_TMPDIR/architectural-invariants.md.identity.env`
   The helper reads the route handoff’s validated `DETAIL` or `DETAIL_FILE` plus the existing durable `$IMPLEMENT_TMPDIR/architectural-invariant-note.md` and its metadata. It emits bounded redacted evidence and an identity sidecar with `MODE`, `RUN_ID`, `STARTING_HEAD`, `INPUT_FINGERPRINT`, `TIER`, `ATTEMPT`, and `STEP`.
6. The materialization helper must reject unsafe paths, symlinks, duplicate or malformed KVs, unreadable or oversized inputs, missing durable invariant notes, stale note metadata, and identity disagreement. It must use no shell-evaluated input and must write evidence plus sidecar atomically before the lane starts.
7. Add the lane carve-out required by invariant-primary recovery: skip failed-run resolution and CI-log collection, consume only the validated canonical invariant evidence, and require an exact match between its sidecar and the immutable launch envelope.
8. Resolve ordinary CI failure IDs through a route-aware contract:
   - `dispatch_ship.py` writes `CI_FAILURE_SCOPE=pr` or `CI_FAILURE_SCOPE=main` into `.ship-route-exit-handoff.env`;
   - for `pr`, select numeric `FAILED_RUN_ID` from the route handoff;
   - for `main`, select numeric `MAIN_FAILED_RUN_ID` from `$IMPLEMENT_TMPDIR/main-health.env`;
   - require any present non-selected ID to be either absent or equal to the selected ID. A malformed ID, missing selected ID, unknown scope, or valid disagreement fails closed before tier selection or evidence collection.
9. Treat `NEEDS_USER_REASON=architectural-invariants-violation` as the first executable Step 8 branch, before ordinary failed-run validation. It starts invariant-primary recovery without a GitHub Actions run ID.
10. Route `RESULT=reship` back through the existing Step 8 ship bgjob. Route `RESULT=retry-next-tool` through a fresh start/wait/finalize sequence that receives a distinct dynamic `STEP`, preserves lineage, and selects the next configured tier. Route exhausted lineage to `ci-fix-exhausted`.
11. Delete the Agent-tool spawn flow, default-path `ci distill-log` flow, fixer-spawn sentinel, post-bail 10-attempt inline loop, and `fallback-attempts.count` routing.
12. Preserve `LARCH_CI_FIXER=0` as the sole inline path and its 30-attempt budget:
   - ordinary CI recovery retains its existing redacted CI-log inline flow;
   - invariant-primary recovery uses the same sanctioned materialization helper with an inline-allocated identity (`MODE=inline`, `TIER=inline`, per-attempt `STEP`) and a separate invariant-inline attempt counter. It consumes validated invariant evidence only and never calls `gh run-logs` or requires `FAILED_RUN_ID`.

## Files to modify/create

### REWRITTEN: skills/implement/references/ship-pr-ci-fix.md

Rewrite the Step 8 CI-fix procedure around the active wrapper protocol.

- Preserve the pre-fix rebase, fork, repository-unavailable, ledger, and operator-bail gates.
- Make `NEEDS_USER_REASON=architectural-invariants-violation` the first executable CI-fix branch, before empty `FAILED_RUN_ID` handling and ordinary CI-failure dispatch.
- For the default path, invoke `step-8-ci-fixer.sh --start`, retain its emitted dynamic `STEP`, and never derive, hardcode, or reuse a prior tier’s slug.
- Run only `python3 python/cli.py bgjob wait --step "$STEP" --max-wait-s 270` while the tier is active. On `BGJOB_STATUS=WAIT`, repeat that exact command with no prose, file reads, sleeps, task-output probes, wrapper calls, or alternate polling.
- On `BGJOB_STATUS=DONE`, require `BGJOB_RC=0`, then call `step-8-ci-fixer.sh --finalize --step "$STEP"`. Only finalize may validate `fixer-status.env`, the merge envelope, identity, lineage result, and emit routable compact KVs.
- Forbid direct consumption of `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`, merge envelopes, `fixer-status.env`, lane transcripts, invariant evidence, failure digests, CI logs, `main-health.env`, or repository state by the default main-agent path.
- State that invariant-primary start allocates its identity before materializing evidence. The prompt passes no evidence body, sidecar identity, tier, attempt, or step to the helper itself.
- For ordinary recovery, require the wrapper’s `CI_FAILURE_SCOPE` contract. It uses `FAILED_RUN_ID` from `.ship-route-exit-handoff.env` for PR failures and `MAIN_FAILED_RUN_ID` from `main-health.env` for main failures. Unknown, malformed, missing, or conflicting IDs route to closed failure.
- Route `reship` through the existing Step 8 ship start/wait pair. Route `retry-next-tool` to a fresh start/wait/finalize cycle that captures a new dynamic step. Route waterfall exhaustion to `ci-fix-exhausted`.
- Keep `LARCH_CI_FIXER=0` as the sole inline path. Preserve the ordinary `main-agent-ci-fix.count` attempts 1 through 30, redacted-log handling, relevant checks, explicit staging, existing commit message, refresh, push, and Step 8 relaunch behavior.
- Add the invariant-primary kill-switch branch. It allocates an inline identity, invokes the sanctioned invariant-evidence materializer, tracks attempts in a separate invariant-inline counter, consumes only the validated canonical evidence, and preserves the same 30-attempt budget. It must not call `gh run-logs`, `ci distill-log`, or require a failed run ID.
- Remove the default-path Agent prompt, Agent rounds, token marks for the in-session fixer, `ci distill-log`, `BAIL_CLASS` routing, `fixer-spawned.sentinel`, direct `fixer-bail.md` interpretation, and post-bail main-agent repair.
- State that the main agent must not read default-path CI evidence, author default-path repair commits, edit repository files, or inspect fixer transcripts.

### UPDATED: skills/implement/SKILL.md

Update the Step 8 routing contract.

- Describe `step-8-ci-fixer.sh` as the default `ci-fix` path and document its start/wait/finalize choreography.
- Require capture and verbatim reuse of the dynamic `STEP` emitted by every start invocation.
- Make the anti-halt rule explicit: `WAIT` repeats the identical wait command; `retry-next-tool` starts a fresh tier with a new step while retaining waterfall lineage; `reship` returns to the ship bgjob.
- State that start and finalize do not perform `bgjob wait`; the Step 8 prompt owns the sole wait protocol.
- Preserve pre-fix rebase ordering before loading the child reference.
- Make architectural-invariant routing first-class and first-ordered. Wrapper start allocates the launch identity, materializes validated canonical evidence, then launches invariant-only lane mode without a failed CI run.
- Define `LARCH_RUN_ID` from `session-env.sh` as the invariant-primary recovery identity.
- Describe route-aware ordinary run selection: `CI_FAILURE_SCOPE=pr` uses handoff `FAILED_RUN_ID`; `CI_FAILURE_SCOPE=main` uses `main-health.env` `MAIN_FAILED_RUN_ID`; disagreement fails closed.
- Preserve `LARCH_CI_FIXER=0` as the sole inline exception with 30 attempts, including a no-CI-log invariant-only inline branch.
- Keep the Step 3, Step 5, and Step 6 checks repair loops unchanged.

### UPDATED: skills/implement/scripts/step-8-ci-fixer.sh

Make the wrapper compatible with the documented Step 8 protocol.

- Add explicit `--start` and `--finalize --step "$STEP"` modes.
- Remove every internal `bgjob wait` call, including `--max-wait-s 0`.
- In start mode, validate paths and route handoff fields, select or resume waterfall lineage, allocate a fresh immutable per-tier launch envelope, and only then launch one bgjob.
- Store lineage separately from launch identity. Preserve stable mode and recovery run identity across retries, record each attempted tier exactly once, and permit later attempts to bind a new `STARTING_HEAD` and `INPUT_FINGERPRINT` after an earlier tier changed `HEAD`.
- For invariant-primary start, derive `RUN_ID` from validated `LARCH_RUN_ID`, allocate `TIER`, `ATTEMPT`, `STEP`, `STARTING_HEAD`, and fingerprint first, then invoke `python3 python/cli.py ci materialize-invariant-evidence` with the handoff path, durable-note source, and allocated identity.
- For ordinary start, consume `CI_FAILURE_SCOPE`. Read `FAILED_RUN_ID` only from `.ship-route-exit-handoff.env` for `pr`; read `MAIN_FAILED_RUN_ID` only from `$IMPLEMENT_TMPDIR/main-health.env` for `main`; parse all present IDs strictly; fail closed on missing, malformed, unknown-scope, or unequal co-present IDs.
- Pass invariant mode and canonical evidence only after successful helper materialization. Do not resolve a CI run or collect CI logs for invariant-primary invocations.
- In finalize mode, require `--step`, load the exact persisted launch envelope, verify the completed bgjob merge envelope and `fixer-status.env`, validate `FINAL_HEAD` separately, and update lineage only after successful identity validation.
- Do not recompute the launch `STARTING_HEAD`, input fingerprint, tier, attempt, step, or run identity from the repaired checkout.
- Emit no routable `RESULT` from start. Emit compact routing KVs only from successful finalize validation.

### NEW: python/larch/implement/invariant_evidence.py

Add the sanctioned invariant-evidence materialization helper.

- Implement `ci materialize-invariant-evidence` as a stdlib-only CLI entry point.
- Accept only explicit paths and allocated identity values: implement tmpdir, route-handoff path, durable invariant-note path, durable-note metadata path, `MODE`, `RUN_ID`, `STARTING_HEAD`, `INPUT_FINGERPRINT`, `TIER`, `ATTEMPT`, and `STEP`.
- Read `DETAIL` or `DETAIL_FILE` from the handoff. Reject duplicate keys, control characters, invalid `DETAIL_FILE` placement, symlinks, unsafe paths, unreadable files, and bodies exceeding the configured bounded evidence limit.
- Require a readable, non-symlinked durable `architectural-invariant-note.md` and valid durable metadata pinned to the allocated `STARTING_HEAD`.
- Construct only bounded, redacted, untrusted evidence from the durable note plus available handoff detail. Do not copy arbitrary environment variables, CI logs, or transcript content.
- Atomically write `$IMPLEMENT_TMPDIR/architectural-invariants.md` and `$IMPLEMENT_TMPDIR/architectural-invariants.md.identity.env` with restrictive permissions. The sidecar must contain exactly the mode and immutable identity fields required by the lane.
- Fail with bounded machine-readable status and no partial consumable artifacts.

### UPDATED: python/larch/cli.py

Register the invariant-evidence materializer.

- Add `("ci", "materialize-invariant-evidence")` to the lazy CLI command map.
- Keep the command available only through the existing `python3 python/cli.py` runtime surface.

### UPDATED: python/larch/implement/ci_fixer_lane.py

Add invariant-primary lane behavior and retry-safe identity validation.

- Add explicit lane mode to `LaneIdentity` and argument validation.
- Permit the validated nonnumeric invariant `RUN_ID` only when `MODE=invariant-primary`; retain numeric GitHub Actions run-ID validation for ordinary CI mode.
- For invariant-primary mode, skip `_resolve_run_id` and `_collect_evidence` CI-log collection. Consume only `$IMPLEMENT_TMPDIR/architectural-invariants.md`.
- Validate the canonical evidence and sidecar against every launch-envelope field: `MODE`, `RUN_ID`, `STARTING_HEAD`, `INPUT_FINGERPRINT`, `TIER`, `ATTEMPT`, and `STEP`.
- Reject missing, stale, oversized, unsafe, symlinked, malformed, duplicate, or identity-mismatched evidence before exposing it to a fixer.
- Change rounds validation so it records lineage membership and each launch’s own identity rather than requiring every historical tier to share a `STARTING_HEAD` and fingerprint.
- Require a retry result to be associated with the launch identity that produced it. Preserve ordinary CI-failure collection and validation behavior otherwise.
- Fail closed on stale run ID, stale head, stale fingerprint, wrong tier, wrong attempt, wrong step, unsafe evidence paths, symlinks, malformed sidecars, and merge/status disagreement.

### UPDATED: python/larch/implement/dispatch_ship.py

Add the route scope required for authoritative failed-run selection.

- Write `CI_FAILURE_SCOPE=pr` for ordinary PR CI recovery handoffs that carry `FAILED_RUN_ID`.
- Write `CI_FAILURE_SCOPE=main` for post-merge or default-branch health recovery handoffs that must use `main-health.env` `MAIN_FAILED_RUN_ID`.
- Do not infer scope from a numeric ID alone.
- Preserve existing handoff fields and detail-file behavior.

### UPDATED: scripts/test-implement-fence-shape.sh

Adjust pinned `SKILL.md` fence shape.

- Update expected fence totals as needed.
- Require wrapper start, dynamic `STEP` capture, the documented identical wait command, and wrapper finalize ordering.
- Assert pre-fix rebase precedes child-reference loading.
- Reject embedded repair logic, direct result-env reads, ad hoc polling, CI-log commands, and Agent dispatch inside default-path fences.
- Assert retry tiers use a newly captured step slug and retained lineage rather than a hardcoded or prior slug.
- Require the invariant kill-switch branch to materialize validated evidence without `gh run-logs`.

### REWRITTEN: scripts/test-implement-step8-exit3-first-fixer.sh

Replace Agent-first assertions with cutover assertions.

- Require invariant-primary handling before empty-run-ID bail.
- Require start allocation before invariant-evidence materialization, then one start/wait/finalize sequence.
- Require the canonical evidence and sidecar paths, `LARCH_RUN_ID` invariant identity, bounded helper inputs from `DETAIL` or `DETAIL_FILE` plus durable invariant note, and all required identity fields.
- Require compact result consumption, `retry-next-tool`, `reship`, `operator-bail`, and `ci-fix-exhausted`.
- Require the pre-fix rebase and nonzero ship-driver handoff ordering.
- Require the route-aware `CI_FAILURE_SCOPE` selection and reject conflicting PR/main IDs.
- Require the unchanged `LARCH_CI_FIXER=0` 30-attempt ordinary inline contract plus invariant-only inline recovery without CI logs or failed run IDs.
- Forbid default-path `ci distill-log`, Agent-tool dispatch, `fixer-spawned.sentinel`, `fallback-attempts.count`, the 20-round Agent loop, the 10-attempt fallback, direct bgjob result reads, default-path `gh run-logs`, and main-agent CI-fix commits.

### UPDATED: scripts/test-implement-structure.sh

Update broad Step 8 structural checks.

- Require active wrapper wiring in the skill and child reference.
- Assert per-tier start/wait/finalize protocol, dynamic-step reuse, launch identity, retry isolation, lineage preservation after changed `HEAD`, success routing, exhaustion, and closed failure.
- Assert no Agent dispatch, direct CI-evidence reads, main-agent edits, main-agent commits, fallback counter, wrapper-internal wait contract, or ad hoc polling on the default path.
- Assert the kill-switch path remains isolated, retains its 30-attempt budget, and uses invariant evidence instead of CI logs for invariant-primary recovery.
- Assert invariant-primary routing precedes ordinary failed-run validation and uses the validated lane rather than inline repair on the default path.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

Extend architectural-invariant routing coverage.

- Require `architectural-invariants-violation` to be the first executable Step 8 branch.
- Require the exact canonical evidence and sidecar paths, SHA-256 fingerprint source, `LARCH_RUN_ID` invariant identity, and required `MODE`, `RUN_ID`, `STARTING_HEAD`, `INPUT_FINGERPRINT`, `TIER`, `ATTEMPT`, and `STEP` fields.
- Require wrapper start to allocate launch identity before calling the materialization helper.
- Assert helper input is limited to route `DETAIL` or `DETAIL_FILE` and the durable invariant note plus metadata.
- Assert invariant-primary dispatch can proceed without `FAILED_RUN_ID`, skips CI-log collection, and fails closed on stale run ID, head, fingerprint, tier, attempt, step, missing sidecar, unsafe paths, symlinks, malformed KVs, oversized input, or stale durable note metadata.
- Forbid direct invariant repair, direct commit, and direct push in the default main-agent branch.
- Preserve existing compose-assessment and durable-note tests.

### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh

Convert dormant-wrapper checks into active-cutover coverage.

- Require wrapper invocation from `SKILL.md` and `ship-pr-ci-fix.md`.
- Preserve the assertion that production ship Python remains independent of prompt-side wrapper wiring.
- Require start mode, no internal wait, captured dynamic `STEP`, finalize mode, compact-result-only routing, and step-keyed immutable launch envelopes.
- Require invariant-primary no-run-ID support through validated `LARCH_RUN_ID` and materialized evidence.
- Require ordinary route-aware handoff selection: PR `FAILED_RUN_ID`, main-health `MAIN_FAILED_RUN_ID`, explicit scope, and closed failure on malformed or unequal co-present IDs.
- Require lineage to retain attempted tiers while permitting the next launch to bind changed `HEAD` and fingerprint after `retry-next-tool`.
- Require finalize to use original per-launch identity after a fixer changes `HEAD`.
- Forbid Agent dispatch and default-path `ci distill-log`.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Convert dormant-wrapper coverage into active integration coverage.

- Assert the skill and child reference wire the wrapper while production ship Python remains independent.
- Add offline fixtures for one-tier success, multi-tier retry followed by success after the first tier changes `HEAD`, all-tier exhaustion, unavailable tiers, hard lane failure, and stale or missing bgjob registry.
- Verify every retry starts a distinct identity-bound step, retains waterfall lineage, and invokes the next configured tier exactly once.
- Verify finalize uses the original per-launch identity after a fixer changes `HEAD`.
- Cover ordinary `CI_FAILURE_SCOPE=pr` and `CI_FAILURE_SCOPE=main` routing, malformed IDs, missing selected IDs, and valid-but-different PR/main IDs. Verify the scope-specific selected ID is used only when the other ID is absent or equal; otherwise fail closed.
- Cover stale run ID, head, tier, attempt, step, fingerprint, merge envelope, and status-envelope disagreement. Every case must fail closed.
- Cover invariant evidence with valid identity and no failed run, stale `LARCH_RUN_ID`, stale head, stale fingerprint, wrong tier or attempt, wrong step, missing identity, unsafe paths, symlinks, malformed duplicate KVs, oversized detail, and stale durable-note metadata.
- Add transcript assertions that main-agent output contains only bounded bgjob and routing KVs, not CI logs, invariant evidence bodies, failure digests, fixer prompts, vendor transcripts, or direct result-env content.
- Assert no Agent-tool call or main-agent CI-fixer token span occurs on the default path. Fixer usage remains attributed to the bgjob child or vendor lane.
- Retain explicit `LARCH_CI_FIXER=0` tests: ordinary recovery selects the isolated inline path without starting the wrapper; invariant-primary recovery materializes evidence, performs no CI-log call, and uses its independent 30-attempt counter.

### NEW: python/tests/implement/test_invariant_evidence.py

Add focused tests for the sanctioned invariant-evidence materializer.

- Test valid `DETAIL`, valid `DETAIL_FILE`, and durable-note-only materialization.
- Assert redaction and byte bounds.
- Assert the helper writes both canonical files atomically with complete identity fields.
- Reject unsafe tmpdirs, external or symlinked detail files, symlinked note or metadata files, missing note metadata, malformed or duplicate handoff KVs, control characters, oversized input, stale note identity, and output identity disagreement.
- Assert failure leaves no partial consumable evidence or sidecar.

### UPDATED: docs/configuration-and-permissions.md

Correct the fixer policy and document the kill switch.

- Describe default ship-pr CI recovery as the `implement.ci_recovery_fixer` waterfall: Codex, Cursor, then Claude.
- State that each tier uses a separate bgjob, the main agent performs the documented wait loop, and retryable results start a fresh next-tier bgjob while retaining waterfall lineage.
- State that CI evidence and repair reasoning remain in child or vendor lanes.
- Document invariant-primary recovery as validated file-backed evidence derived from route detail and the durable invariant note. It may proceed without a failed CI run and uses `LARCH_RUN_ID` as its stable recovery identity.
- Document route-aware ordinary run selection and the fail-closed behavior for conflicting PR and main run IDs.
- Document `LARCH_CI_FIXER=0` as the sole sanctioned inline Step 8 path with its existing 30-attempt budget. State that invariant-primary inline recovery consumes validated invariant evidence and never fetches CI logs.
- State that delegated-waterfall exhaustion routes to `ci-fix-exhausted`.
- Remove the stale delegated Claude/Opus Agent-tool loop description.

### UPDATED: python/larch/core/config.py

Remove configuration used only by retired paths after confirming no consumers remain.

- Remove `CI_FIXER_AGENT_MAX_ROUNDS`.
- Remove `CI_FIXER_MAIN_FALLBACK_MAX_ATTEMPTS`.
- Remove `CI_FIXER_SPAWNED_SENTINEL`.
- Remove `CI_FIXER_FALLBACK_ATTEMPTS_FILE`.
- Add bounded invariant-evidence input and output constants only if the helper cannot reuse an existing bounded evidence constant without changing its meaning.
- Keep `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS`, `ENV_LARCH_CI_FIXER`, lane timeouts, tier order, status files, rounds file, bail file, digest constants still used inside the lane, and `CLAUDE_CI_FIX_MODEL`.

### UPDATED: python/tests/core/test_config.py

Update constant coverage.

- Remove assertions for retired Agent-round, post-bail fallback, sentinel, and fallback-counter constants.
- Preserve assertions for the 30-attempt kill-switch budget, tier order, lane timeout, action tokens, failure reasons, and `LARCH_CI_FIXER`.
- Add assertions for any new invariant-evidence bounds constant.

## Edge cases

- An architectural-invariant violation occurs on a green PR with no failed run ID.
- The invariant route handoff has inline `DETAIL`, file-backed `DETAIL_FILE`, or only the durable invariant note.
- The durable invariant note or metadata is stale for the allocated launch `HEAD`.
- The ship handoff has no failed run ID for an ordinary CI failure.
- A default-branch failure has a run ID distinct from the PR run.
- `FAILED_RUN_ID` and `MAIN_FAILED_RUN_ID` are malformed, missing, equal, or valid-but-different.
- The selected vendor is unavailable before launch.
- A tier returns `retry-next-tool` after changing `HEAD`.
- Finalization occurs after a successful fixer changes `HEAD`.
- A prior lineage record, launch envelope, rounds file, result envelope, or invariant evidence sidecar belongs to another run ID, head, fingerprint, tier, attempt, or step.
- The bgjob registry is missing, dead, or stale.
- The merge result exists but disagrees with `fixer-status.env`.
- All configured tiers are exhausted.
- The kill switch is enabled after delegated sidecars already exist.
- Fork and repository-unavailable handoffs must never enter either repair path.

## Failure modes

- Treat malformed, stale, unsafe, oversized, or identity-mismatched invariant evidence as operator-bail or closed lane failure. Never reuse it.
- Treat missing, malformed, unknown-scope, or conflicting ordinary run IDs as closed failure before tier selection or evidence collection.
- Treat nonzero bgjob completion as closed failure. Do not reinterpret it as a retryable typed result.
- Treat a missing finalize envelope as failure, even if repository changes or green CI suggest success.
- Do not permit wrapper start or finalize to wait internally.
- Do not fall back to main-agent edits when tier selection, evidence materialization, launcher execution, finalize validation, or result validation fails.
- Do not route full waterfall exhaustion into stall recovery or the removed fallback counter.
- Keep delegated tier attempts, lineage state, ordinary inline attempts, and invariant-inline attempts independent.
- Do not allow invariant-primary recovery to call CI-log collection, resolve a failed run, or consume CI evidence.

## Testing strategy

Run only tests and linters that cover changed files.

- `bash scripts/test-implement-fence-shape.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`
- `bash scripts/test-implement-structure.sh`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `bash skills/implement/scripts/test-step-8-ci-fixer.sh`
- `python3 -m pytest -q python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest -q python/tests/implement/test_invariant_evidence.py`
- `python3 -m pytest -q python/tests/core/test_config.py`
- Run focused tests for `python/larch/implement/ci_fixer_lane.py`, `python/larch/implement/dispatch_ship.py`, and their existing or added invariant-evidence and route-handoff coverage.
- Run Bash syntax and Bash 3.2 checks for changed shell harnesses.
- Run configured Markdown and skill-structure checks for changed skill and reference files.
- Run configured Python formatter, linter, type checker, and targeted tests for changed Python files.
- Search changed runtime and documentation surfaces for `fallback-attempts.count`, `CI_FIXER_MAIN_FALLBACK_MAX_ATTEMPTS`, `CI_FIXER_AGENT_MAX_ROUNDS`, `fixer-spawned.sentinel`, internal wrapper waits, retired Agent-path wording, direct default-path CI-log reads, and undocumented run-ID inference. Allow only historical fixtures outside the runtime surface.
- Confirm the checks repair-loop and `python/larch/implement/checks_lint_fix.py` remain unchanged.

difficulty: HARD
diff_added: 560
diff_deleted: 270
mechanical_churn: false
oversize_override: operator
diff_lines: 830
