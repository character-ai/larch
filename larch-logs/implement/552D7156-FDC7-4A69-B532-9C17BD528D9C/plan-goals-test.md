## Goal
Implement issue #4072: [IMPLEMENTING] /design Gate B: shared post-apply settle wrapper across three rewrite sites.

## Implementation Plan
## Plan

### Approach

Add one launcher-safe post-rewrite settle wrapper for the three rewrite sites:

- Gate B after accepted reviewer findings are applied.
- Gate A after a direct discussion rewrite.
- Discussion Round 2 after user-resolved discussion decisions are applied.

Keep `gate-b-dedup-plan.sh --snapshot-trailers` as the pre-rewrite guard at each site.

After the rewrite, call the new wrapper through the design launcher:

- `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b`
- `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-a`
- `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site discussion-round2`

For Gate B, avoid `STEP3_RESUME_ROUND` before it is bound. Either omit `--round-num` and let the wrapper derive the round from `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`, or pass `--round-num` only after binding and validating the same fallback expression.

The wrapper will:

- Accept `--site gate-b|gate-a|discussion-round2`.
- Accept optional `--round-num N`.
- Validate `DESIGN_TMPDIR` with `lib-design-tmpdir.sh`.
- Run `gate-b-dedup-plan.sh --dedup` exactly once per new rewrite.
- Relay dedup rc `1` as a revise-again result.
- For Gate B, write `.gate-b-postapply-ready-N` only after dedup succeeds.
- For Gate B resume with `.gate-b-postapply-ready-N` already present, skip dedup and enter postplan without reapplying findings.
- Write `.step3-round-N.phase` to `awaiting-post-apply` before invoking postplan once the Gate B apply-ready marker exists.
- Call `design-step2b-postplan.sh` internally with the mapped site.
  - `gate-b` maps to `gate-b`.
  - `gate-a` maps to `discussion-round2`.
  - `discussion-round2` maps to `discussion-round2`.
- Leave scout-manifest cleanup owned by `design-step2b-postplan.sh`.
- Print child output once.
- Require an anchored whole-line `POSTPLAN_RC=0` for clean settle.
- Treat delegated pause-save output as terminal rc `11`, not clean settle.
- Relay `10`, `12`, and `13` as wrapper exit codes.
- For Gate B rc `10` or `13`, write `.step3-round-N.phase` as `awaiting-postplan-operator` before returning.
- For clean Gate B rc `0`, write `.step3-round-N.phase` as `awaiting-continuation`.
- Do not create `plan-after-round-N.txt`.
- Keep pause-save behavior owned by `design-step2b-postplan.sh`.

Keep prompt-side handling minimal:

- Snapshot trailers before any direct plan replacement.
- After any direct rewrite, run the new wrapper once through the design launcher.
- Branch on wrapper rc `0`, `1`, `10`, `11`, `12`, and `13`.
- Treat rc `1` as the existing revise-again loop for optional trailer or duplicate cleanup.
- Treat rc `11` as a delegated pause boundary and stop without continuation.
- Treat any other non-zero as wrapper or child failure and stop for operator repair.
- Do not reintroduce HARD-only snapshot sub-steps removed by #4019.
- Do not add prompt-side scout-manifest clearing.

## Files to modify/create

### NEW: skills/design/scripts/design-step35-settle.sh

Create the shared settle wrapper.

Implementation notes:

- Follow the generated-wrapper style used by `design-step2b-postplan.sh` and `design-step35.sh`.
- Parse standard wrapper args:
  - `--session-env-path`
  - `--claude-pid`
  - `--plugin-root`
  - `--site`
  - `--round-num`
- Source the optional session env before validating plugin root.
- Default prompt-side variables before sourcing, matching nearby wrappers.
- Add test seams:
  - `DESIGN_STEP35_DEDUP_PLAN_SH`, defaulting to `skills/design/scripts/gate-b-dedup-plan.sh`.
  - `DESIGN_STEP35_POSTPLAN_SH`, defaulting to `skills/design/scripts/design-step2b-postplan.sh`.
- Use `mktemp` only under `$DESIGN_TMPDIR` if temporary output files are needed.
- Do not call `--snapshot-trailers`; callers still do that before the plan rewrite.
- Do not clear scout manifests; `design-step2b-postplan.sh` owns that for mapped non-initial sites.
- Validate `--site`.
- For `gate-b`, resolve the round from:
  1. `--round-num`
  2. `FINAL_ROUND_NUM`
  3. `STEP3_REVIEW_ROUND_NUM`
  4. `ROUND_NUM`
- For invalid or missing Gate B round, exit `2`.
- For non-Gate-B sites, do not write Gate B round markers.

Gate B idempotency:

- If `.gate-b-postapply-ready-N` already exists, treat dedup as complete and skip dedup.
- If the marker does not exist:
  - Run dedup under `set +e`.
  - Capture rc.
  - Print dedup stdout normally.
  - On rc `0`, continue.
  - On rc `1`, print concise context and exit `1` so the caller can revise and retry.
  - On any other non-zero, print concise context and relay that rc.
  - Write `.gate-b-postapply-ready-N` atomically after dedup succeeds.
- After the marker exists, atomically write `.step3-round-N.phase` as `awaiting-post-apply` before invoking postplan.

Postplan handling:

- Invoke `design-step2b-postplan.sh` directly with the current `--session-env-path`, `--claude-pid`, `--plugin-root`, and mapped `--site`.
- Clear stale pause completion breadcrumbs before the child call if the existing postplan pause contract uses `.pause-save-complete`.
- Capture child stdout and rc under `set +e`.
- Print child stdout once.
- Parse only anchored whole-line `POSTPLAN_RC=` values.
- If child output contains `PAUSE_OK=true`, `POSTPLAN_EMIT_STATUS=paused`, or a fresh pause completion breadcrumb exists, exit `11` before any clean-settle work.
- If stdout contains `POSTPLAN_RC=10`, `POSTPLAN_RC=12`, or `POSTPLAN_RC=13`, relay that rc.
- If site is `gate-b` and postplan rc is `10` or `13`, atomically write `.step3-round-N.phase` as `awaiting-postplan-operator` before returning the brake rc.
- If stdout contains `POSTPLAN_RC=0` and child rc is `0`, finish clean.
- If stdout lacks `POSTPLAN_RC=` and no pause signal is present, exit non-zero with a contextual contract error.
- If stdout contains an unexpected `POSTPLAN_RC`, exit non-zero with a contextual contract error.
- On clean `gate-b`, atomically write `.step3-round-N.phase` as `awaiting-continuation`.
- Do not copy `plan.txt` to `plan-after-round-N.txt`.

### NEW: skills/design/scripts/design-step35-settle.md

Document the wrapper contract.

Include:

- Purpose: shared post-rewrite settle wrapper for Gate B, Gate A after-discussion rewrites, and discussion Round 2.
- Prompt-side transport: call through `"$HOME/.cache/larch/sessions/design-run-$PPID.sh"`.
- Argv table.
- Gate B round derivation table.
- Site mapping table.
- Exit code contract:
  - `0`: settled.
  - `1`: dedup revise-again result; caller revises `plan.txt` and retries settle.
  - `2`: usage, invalid site, invalid tmpdir, or invalid Gate B round.
  - `3`: fail-closed wrapper or dedup contract failure.
  - `10`: validator operator brake.
  - `11`: delegated pause-save terminal result.
  - `12`: hard plan-size brake.
  - `13`: split path.
- Marker ownership:
  - `.gate-b-postapply-ready-N`
  - `.step3-round-N.phase`
  - `.completed/step-2b.5` remains owned by `design-step2b-postplan.sh`.
  - Scout-manifest clearing remains owned by `design-step2b-postplan.sh`.
  - `plan-after-round-N.txt` is not owned or written by this wrapper.
- Gate B resume idempotency:
  - Existing apply-ready marker means skip dedup and re-enter postplan.
  - Do not reapply reviewer findings during marker resume.
- Pause contract:
  - Pause output or pause breadcrumb exits `11`.
  - Pause never writes clean Gate B continuation phase.
- Test seams.

### UPDATED: skills/design/references/approval-gates.md

Rewrite `### Shared post-apply pipeline`.

Keep these parts:

- Pre-rewrite `gate-b-dedup-plan.sh --snapshot-trailers`.
- LLM duplicate-content cleanup and plan rewrite.
- Optional trailer preservation rules.
- Gate B continuation semantics.
- Operator-brake prose for rc `10`, `12`, and `13`.
- Retained recovery wording for non-exiting Override, Continue, or Split returns that bypass the clean path.

Replace the respelled mechanical sequence with:

- Run the pre-rewrite trailer snapshot.
- Apply the accepted reviewer-finding rewrite.
- Run the settle wrapper through the launcher:
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b`
- Do not pass `STEP3_RESUME_ROUND` before it is bound.
- If the surrounding prose already has a validated round variable, pass it with `--round-num`.
- Otherwise let the wrapper derive the Gate B round from `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`.

Branch on wrapper rc:

- `0`: continue to loop-mode or legacy continuation handling.
- `1`: repeat the LLM duplicate/trailer cleanup and retry the settle wrapper.
- `10`: execute the shared validator failure procedure with site context `design Step 3.5 / Gate B`.
- `11`: stop at the delegated pause boundary.
- `12`: run the existing Gate B hard plan-size prompt.
- `13`: run Split-path.
- Other non-zero: stop for operator repair.

Remove prose that tells the orchestrator to hand-code:

- `gate-b-dedup-plan.sh --dedup` after the rewrite.
- Post-dedup apply-ready marker writes.
- Scout-manifest clearing.
- Raw `set +e` capture of `design-step2b-postplan.sh`.
- Immediate `printf` of captured postplan output.
- Seven-arm `_postplan_rc` case composition.
- Direct `.step3-round-N.phase` writes.
- `plan-after-round-N.txt` writes.

Keep a literal internal-mapping reference that `design-step35-settle.sh` calls `design-step2b-postplan.sh --site gate-b` internally.

### UPDATED: skills/design/SKILL.md

Update Step 1e's optional-trailer guard.

Change the post-rewrite contract to:

- Snapshot trailers before any plan replacement.
- After the direct discussion rewrite, run the settle wrapper through the launcher:
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-a`
- Branch on wrapper rc:
  - `0`: continue.
  - `1`: revise duplicate/trailer cleanup and retry settle.
  - `10`: use the same `design discussion-round2` validator context.
  - `11`: stop at the delegated pause boundary.
  - `12`: use the same retained Step 2b.5 behavior.
  - `13`: use the same Split-path behavior.
  - Other non-zero: stop for operator repair.
- Do not change first-time Gate A routing.

Update Step 3.5 Gate B prose.

Change the Gate B apply and resume contract to:

- Snapshot trailers before any reviewer-finding plan replacement.
- After applying accepted findings, run the settle wrapper through the launcher:
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b`
- Do not use `STEP3_RESUME_ROUND` before the existing later binding.
- When an explicit round is needed, derive it from `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`.
- On apply-ready marker resume, route through the same settle wrapper without reapplying findings.
- State that the wrapper skips dedup when `.gate-b-postapply-ready-N` already exists.
- Preserve the existing continuation split between loop-mode and legacy handling after rc `0`.
- Preserve the existing operator procedures for rc `10`, `12`, and `13`.
- Add rc `1` as the revise-again loop.
- Add rc `11` as the delegated pause boundary.
- Remove stale directions to resume at a raw `design-postplan-emit` or direct Step 2b postplan fence after `.gate-b-postapply-ready-N`.

Add `design-step35-settle.sh` and `design-step35-settle.md` to the wrapper contract inventory.

### UPDATED: skills/design/references/discussion-rounds.md

Update the Round 2 plan revision authority paragraph.

Change it to point to the shared settle wrapper:

- Keep `gate-b-dedup-plan.sh --snapshot-trailers` before direct replacement.
- After the plan rewrite, run the settle wrapper through the launcher:
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site discussion-round2`
- State that `gate-a` and `discussion-round2` both map to `design-step2b-postplan.sh --site discussion-round2` internally.
- Keep reviewer-finding ownership unchanged:
  - Gate B applies reviewer findings.
  - Round 2 applies only user-resolved discussion decisions.
- Keep drift advisory unchanged.
- Keep retained Step 2b.5 and Split-path semantics unchanged.
- Add rc `1` as the revise-again loop.
- Add rc `11` as the delegated pause boundary.

Remove inline prose for:

- `gate-b-dedup-plan.sh --dedup` after the rewrite.
- Scout-manifest clearing.
- `set +e`.
- `printf` of captured postplan output.
- Full Step 2b thin-fence case-arm composition.

### UPDATED: scripts/test-design-structure.sh

Update structure pins for the new launcher-form settle wrapper.

Change `assert_reference_updates` or the equivalent pins to:

- Require launcher-form `design-step35-settle.sh --site gate-b` at the Gate B site.
- Require launcher-form `design-step35-settle.sh --site gate-a` in `SKILL.md` Step 1e.
- Require launcher-form `design-step35-settle.sh --site discussion-round2` at the discussion Round 2 site.
- Stop requiring prompt-side launcher-form `design-step2b-postplan.sh` at those three rewrite sites.
- Add separate assertions that internal postplan mapping is documented:
  - `gate-b` maps to `design-step2b-postplan.sh --site gate-b`.
  - `gate-a` maps to `design-step2b-postplan.sh --site discussion-round2`.
  - `discussion-round2` maps to `design-step2b-postplan.sh --site discussion-round2`.
- Keep or add anti-pattern coverage so the references do not instruct bare prompt-side `design-step35-settle.sh` calls without `design-run-$PPID.sh`.

### UPDATED: skills/design/scripts/test-gate-b-dedup-plan.sh

Extend the harness for the new wrapper.

Add cases for:

- `bash -n skills/design/scripts/design-step35-settle.sh`.
- Gate B clean path with:
  - Prior trailer snapshot.
  - Successful dedup.
  - Stub postplan output containing whole-line `POSTPLAN_RC=0`.
  - `.gate-b-postapply-ready-N` written.
  - `.step3-round-N.phase` equals `awaiting-continuation`.
  - No `plan-after-round-N.txt` assertion.
- Gate B resume path with existing `.gate-b-postapply-ready-N`:
  - Dedup is skipped.
  - Postplan still runs.
  - Clean rc writes `awaiting-continuation`.
- Gate B rejects missing or non-numeric round.
- Dedup failure exits before postplan and does not write apply-ready markers.
- Dedup rc `1` relays wrapper rc `1` for the revise-again loop.
- Gate A maps postplan site to `discussion-round2`.
- Discussion Round 2 maps postplan site to `discussion-round2`.
- Pause output without `POSTPLAN_RC=0` exits rc `11`.
- Pause output does not write `awaiting-continuation`.
- Postplan rc `10` or `13` on Gate B writes `awaiting-postplan-operator`.
- Missing `POSTPLAN_RC=` without a pause signal is not treated as clean.

Use wrapper test seams rather than invoking real operator prompts.

### UPDATED: skills/design/scripts/test-gate-b-apply-mode.sh

Extend the apply-mode harness to cover wrapper-mediated settle.

Add cases for:

- Auto-apply simulated rewrite now settles through `design-step35-settle.sh`.
- The dedup breadcrumb still appears once.
- Stubbed postplan rc `10` exits wrapper rc `10`.
- Stubbed postplan rc `10` writes Gate B phase `awaiting-postplan-operator`.
- Stubbed postplan rc `12` exits wrapper rc `12` and does not write `.completed/step-2b.5` through the clean path.
- Stubbed postplan rc `13` exits wrapper rc `13`.
- Stubbed postplan rc `13` writes Gate B phase `awaiting-postplan-operator`.
- Stubbed pause output exits wrapper rc `11` and does not write clean continuation phase.
- Clean rc `0` still leaves the postplan clean marker behavior intact.
- Clean rc `0` writes Gate B phase `awaiting-continuation`.

Keep existing auto-apply and `--per-round-approval` mode assertions.

## Edge cases

- Missing trailer snapshot still fails closed through `gate-b-dedup-plan.sh --dedup` rc `3`.
- Optional trailer key or value loss exits wrapper rc `1` and enters the revise-again loop.
- Dedup rc `1` must not be folded into generic operator repair.
- `gate-a` and `discussion-round2` must not write Gate B round markers.
- Gate B must not write apply-ready markers before dedup succeeds.
- Gate B marker resume must not reapply reviewer findings.
- Existing `.gate-b-postapply-ready-N` means dedup is skipped and postplan is retried.
- Pause-save output must not be classified as clean settle.
- A clean postplan requires whole-line `POSTPLAN_RC=0`.
- Missing `POSTPLAN_RC=` is a contract error unless pause output or a fresh pause breadcrumb is present.
- Operator brakes must not be converted to success.
- Gate B rc `10` and `13` must write `awaiting-postplan-operator`.
- Clean Gate B rc `0` must write `awaiting-continuation`.
- Pause-save remains delegated to `design-step2b-postplan.sh`; the new wrapper must not add a second pause path around it.
- Scout-manifest clearing remains delegated to `design-step2b-postplan.sh`.
- The wrapper must not create `plan-after-round-N.txt`.

## Failure modes

- If the wrapper cannot validate `$DESIGN_TMPDIR`, exit `2`.
- If site is unknown, exit `2`.
- If Gate B round is missing or invalid, exit `2`.
- If dedup exits `1`, relay rc `1` for revise-again handling.
- If dedup fails with another rc, relay the dedup rc and stop.
- If postplan wrapper returns an unexpected non-zero, relay that rc unless an anchored expected `POSTPLAN_RC` or pause result is present.
- If postplan output contains an unexpected `POSTPLAN_RC`, exit non-zero with a contextual error.
- If postplan exits `0` without `POSTPLAN_RC=0` and without a pause signal, exit non-zero with a contextual error.
- If Gate B cannot write the apply-ready marker or phase file, exit non-zero and do not claim rc `0`.
- If pause is detected, exit `11` and do not write clean continuation phase.

## Testing strategy

Run targeted tests first:

- `bash skills/design/scripts/test-gate-b-dedup-plan.sh`
- `bash skills/design/scripts/test-gate-b-apply-mode.sh`
- `bash scripts/test-design-structure.sh`

Then run the repository-relevant check:

- `bash scripts/relevant-checks.sh`

## Acceptance

- Each of the three sites calls the settle wrapper after a plan rewrite; rc 10/12/13 routing byte-compatible with the prior per-site postplan case arms.
- `test-gate-b-dedup-plan.sh` and `test-gate-b-apply-mode.sh` extended to cover the wrapper.
- Structure harness pins updated to require launcher-form settle references.

diff_lines: 700

## Test plan
(no test plan section in plan-file)
