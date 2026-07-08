# Review Round 1

- Mode: `diff`
- 6 accepted, 0 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 5 stall envelopes bypass the stall branch
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: Step 5 currently treats any non-zero `BGJOB_RC` as a generic failure before it inspects `STEP5_REVIEW_STATUS`, so valid stall envelopes can skip the stall branch and lose record-only timing, `STALL_REASON` capture, and durable state seeding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Parse STEP5_REVIEW_STATUS from result env even when BGJOB_RC is non-zero for stall routing, or return exit 0 on stall while preserving KVs; mirror for resume stall exits.
  - From codex-specialist-correctness: Parse STEP5_REVIEW_STATUS before the generic non-zero BGJOB_RC failure path. When the status is stall, route to the existing Step 5 stall branch even if BGJOB_RC is non-zero; reserve the generic path for missing or malformed Step 5 envelopes.
  - From cursor-specialist-edge-cases: Parse STEP5_REVIEW_STATUS before the hard rc gate; allow stall/cap-hit/mav statuses with non-zero BGJOB_RC
  - From codex-specialist-edge-cases: After `BGJOB_RC=0` is confirmed, branch on `STEP5_REVIEW_STATUS` first; only treat non-zero `BGJOB_RC` without a parseable stall envelope as generic preflight failure.
  - From cursor-specialist-testing: Parse STEP5_REVIEW_STATUS from result env first; route stall through step5-review-branches.md even when BGJOB_RC is non-zero
  - From dyn-dyn-bgjob-flow: After `BGJOB_RC=0` is confirmed, branch on `STEP5_REVIEW_STATUS` first; only treat non-zero `BGJOB_RC` without a parseable stall envelope as generic preflight failure.


### FINDING_2: Step 5 re-entry must rejoin valid canonical results and clear stale result envs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: Same-step re-entry only checks the live registry, so a completed canonical result env can be relaunched instead of rejoined, and fresh starts can trust stale `DONE` data unless the canonical env is consumed or cleared first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Before bgjob start, treat BGJOB_RC=0 plus required KVs in implement-step5-review.result.env as completion when no live registry row exists.
  - From codex-specialist-correctness: Before fresh `bgjob start`, check the canonical result env for the current step. If it exists and has `BGJOB_RC` plus required Step 5 KVs, emit or direct the caller to consume that result instead of launching.
  - From cursor-specialist-edge-cases: Delete bgjob/implement-step5-review.result.env on fresh start and before trusting DONE
  - From cursor-specialist-testing: Check canonical result env before bgjob start; rejoin completed work without relaunching
  - From dyn-dyn-bgjob-flow: Before fresh `bgjob start`, if the canonical result env exists with identity-valid completion (`BGJOB_RC=0` plus required Step 5 KVs) and no live registry row, emit/consume that env and skip relaunch; only clear and restart when the row is stale or incomplete.


### FINDING_3: Registry probe failures must fail closed
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: `step5_live_registry_exists` failures are being treated as “no live row,” so any transient registry I/O or import error can fresh-start a second `implement-step5-review` daemon instead of failing closed or rejoining.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Registry probe errors are treated as no live row and fall through to bgjob start. Transient registry read failure while a live daemon exists starts a duplicate implement-step5-review job. Fail closed on unexpected registry exceptions; only proceed to start when probe definitively finds no live row.
  - From codex-specialist-correctness: Registry inspection errors are treated as “no live row,” which can start a duplicate daemon. Scenario: `registry.read_for()` raises `OSError` or `ValueError` while a live `implement-step5-review` row exists; the helper exits `1`, line 125 falls through, and line 142 starts another review loop against the same tmpdir and merge env. **Suggested fix:** Return a distinct error code for registry read or liveness failures, print a `BGJOB_ERROR=...` envelope, and abort instead of fresh-starting. Only fresh-start after a verified missing, stale, or dead row.
  - From cursor-specialist-edge-cases: Fail closed or retry on probe exceptions; start only on conclusive no-live-row
  - From cursor-specialist-testing: Fail closed or retry on registry probe errors; only absent/dead rows permit fresh start
  - From codex-specialist-testing: Fail closed on probe errors, and check the canonical bgjob result env before any fresh start.
  - From dyn-dyn-bgjob-flow: `step5_live_registry_exists` maps registry read/import failures to exit `1`, and the launcher treats that as “no live row” and falls through to `bgjob start`. A transient I/O or import error can therefore launch a second `implement-step5-review` daemon instead of failing closed or rejoining. **Suggested fix:** Distinguish “no live row” from probe failure: on registry exceptions exit non-zero from the wrapper without calling `bgjob start`, and route the orchestrator to the existing Step 5 failure/stall path.


### FINDING_4: Self-review launch needs the legacy sentinel and 14700s budget
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: The migrated step-5-self-review path still uses the default 10800s budget and can miss the legacy `.completed/step-5-self-review-terminal` contract, so hook release and long self-review timing diverge from the old path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add step5-self-review branch with BUDGET_S=14700 and --sentinel .completed/step-5-self-review-terminal; pin in structure tests.
  - From cursor-specialist-edge-cases: Add a step5-self-review branch with BUDGET_S=14700 and --sentinel .completed/step-5-self-review-terminal
  - From cursor-specialist-testing: Add step5-self-review branch with BUDGET_S=14700 and --sentinel .completed/step-5-self-review-terminal
  - From dyn-dyn-bgjob-flow: Add a `step5-self-review` branch setting `BUDGET_S=14700` and `--sentinel "$IMPLEMENT_TMPDIR/.completed/step-5-self-review-terminal"`, and pin it in `scripts/test-implement-structure.sh`.
  - From dyn-dyn-bgjob-flow: Preserve the legacy step slug and .completed/step-5-self-review-terminal sentinel or update all hook test and doc consumers atomically.


### FINDING_5: Step 5 wrapper tests need DEAD/orphan/timeout and stale-result coverage
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: The wrapper harness still misses the bgjob replacement cases that plan acceptance depends on, so regressions in `DEAD`, orphaned, timeout, or stale canonical result handling can ship without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add harness simulations for BGJOB_STATUS=DEAD and BGJOB_RC=orphaned/timeout with assertions against false-success routing.
  - From codex-specialist-correctness: Add harness cases that simulate bgjob `DONE` with `BGJOB_RC=orphaned` or `BGJOB_RC=timeout`, plus `BGJOB_STATUS=DEAD`, and assert the Step 5 contract routes them to stall/failure instead of success or relaunch.
  - From cursor-specialist-testing: Add fake bgjob wait tests for DEAD, timeout/orphan rc, and stale result.env re-entry
  - From dyn-dyn-bgjob-flow: Extend the harness with fake `bgjob wait` modes for `DEAD`/orphan/timeout and an assertion that a pre-seeded canonical result env is removed or ignored on fresh start before `DONE` can authorize continuation.


### FINDING_6: Structure tests should pin the Step 5 BGJOB_RC gate and rejoin prose
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The structure harness does not pin the Step 5 BGJOB_RC=0 gate or the review/resume rejoin text, so prose can drift without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: require() pins on SKILL Step 5 review/resume BGJOB_RC=0 sentences and step5-review-branches bgjob rejoin contract.
  - From cursor-specialist-testing: require BGJOB_RC=0 in SKILL Step 5 blockquotes and step5-review-branches.md; pin resume launcher STARTED stdout


