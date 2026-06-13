## Goal
Implement issue #4071: [IMPLEMENTING] /design: script-own sentinel, phase, and marker writes.

## Implementation Plan
## Plan

Revise the /design state-write migration so launcher-owned scripts write sentinels, phases, completion markers, and findings env files without changing pause/resume semantics.

## Files to modify/create

### UPDATED: `skills/design/scripts/design-step3-entry.sh`

Add a `--reentry` flag.

Behavior:
- Parse `--reentry`.
- Source `SESSION_ENV_PATH` as today.
- Validate `DESIGN_TMPDIR` before writing.
- When `--reentry` is set:
  - create `$DESIGN_TMPDIR/.step3-reentry`;
  - do **not** clear `$DESIGN_TMPDIR/.step3-entry-plan-printed`.
- Keep existing order:
  - clear `.pause-save-complete`;
  - call `design-step3-entry-state.sh`;
  - exit early on `.pause-save-complete`;
  - call preview.
- Only legacy heuristic continuation may clear `.step3-entry-plan-printed`.

### UPDATED: `skills/design/scripts/design-step3-continuation-entry.sh`

Move the legacy heuristic `.step3-entry-plan-printed` cleanup into this wrapper.

Behavior:
- After sourcing env and validating `DESIGN_TMPDIR`, clear `$DESIGN_TMPDIR/.step3-entry-plan-printed` before pause-save.
- Keep the existing `design-step3-state.sh --auto-continuation-entry` call.
- Preserve pause semantics by clearing before the pause-save branch.

### UPDATED: `skills/design/scripts/design-step3-review.sh`

Add Step 3 resume state flags.

New flags:
- `--phase <value>`
- `--findings-file <absolute-path>`
- `--postplan-operator-continue`

Behavior:
- Require `--starting-round` when any new state flag is present.
- Validate `--starting-round` as a positive integer.
- Mirror `run-step3-review.sh` starting-round bounds validation before any new state write:
  - read the current review round count the same way the inner driver does;
  - reject `--starting-round` values greater than `review-round-count.txt + 1`;
  - allow values less than or equal to the last count so the wrapper can create phase evidence for existing-round resumes.
- Validate `--phase` against phases consumed by `review-design-step3-loop.sh`:
  - `awaiting-apply`
  - `awaiting-revise`
  - `awaiting-post-apply`
  - `awaiting-postplan-operator`
  - `awaiting-continuation`
- Do **not** accept `awaiting-vote`.
- Validate `--findings-file` before writing any state:
  - path is absolute;
  - path has no CR/LF;
  - canonical path is under canonical `DESIGN_TMPDIR`;
  - path is a readable regular file;
  - path is not a symlink.
- Treat resume-state validation as all-or-nothing:
  - validate all supplied state flags first;
  - if any validation fails, write no state files.
- Branch pause-save ordering explicitly:
  - when no `--phase`, `--findings-file`, or `--postplan-operator-continue` flag is present, preserve today's pre-launch pause behavior;
  - when any resume-state flag is present, write validated state first, then honor pause-save, then launch `run-step3-review.sh`.
- For flag-bearing calls, after validation and before pause-save:
  - write `$DESIGN_TMPDIR/.step3-round-N.phase` when `--phase` is provided;
  - write `$DESIGN_TMPDIR/.gate-b-per-round-approval-round-N.env` with `FINDINGS_FILE=<path>` when `--findings-file` is provided;
  - write `$DESIGN_TMPDIR/.postplan-operator-continue-N` when `--postplan-operator-continue` is provided.
- Use temp-file plus `mv` for the env file, phase file, and postplan continue marker.
- Treat the wrapper as the single resume-launch boundary:
  - it writes requested resume state;
  - it then launches `run-step3-review.sh`;
  - callers must not call it once to write state and again to resume.

This keeps postplan operator continue launcher-owned. Do not route this marker through direct prompt-side calls to `design-step3-state.sh`.

### UPDATED: `skills/design/scripts/design-step3-review.md`

Document the new resume-state invariant.

Add concise contract text:
- `design-step3-review.sh` validates resume flags and starting-round bounds before writing state.
- Calls without resume-state flags preserve the existing first-entry pause ordering before review launch.
- Calls with resume-state flags write state before pause-save so paused resumes snapshot the required phase, findings env, or postplan continue marker.
- `run-step3-review.sh` still owns Step 3 review execution.
- `design-step3-review.sh` is not a state-only helper. A call with resume flags also resumes the Step 3 loop after pause-save.
- Sites that previously wrote phase state and then launched review separately must collapse to one wrapper invocation at the resume boundary.
- `awaiting-vote` remains an internal loop state and is not accepted as a wrapper resume phase.

### UPDATED: `skills/design/scripts/design-step2b-postplan.sh`

Extend the postplan wrapper as the completion-marker owner.

Changes:
- Add `--write-completion-only` for `.completed/step-2b.5`.
- Add `--include-step2b` for sites where both `.completed/step-2b` and `.completed/step-2b.5` are complete.
- Add `--write-step2b-completion-only` for validator Override paths that have completed Step 2b but have not yet run retained Step 2b.5.

Behavior:
- Parse completion-only flags immediately after env source and `DESIGN_TMPDIR` validation.
- Dispatch completion-only modes before the normal `.pause-requested` gate that protects `design-postplan-emit.sh`.
- In `--write-step2b-completion-only` mode:
  - source env;
  - validate `DESIGN_TMPDIR`;
  - create `$DESIGN_TMPDIR/.completed`;
  - write `.completed/step-2b`;
  - do **not** write `.completed/step-2b.5`;
  - then honor `.pause-requested`;
  - exit 0 without running `design-postplan-emit.sh`.
- In `--write-completion-only` mode:
  - source env;
  - validate `DESIGN_TMPDIR`;
  - create `$DESIGN_TMPDIR/.completed`;
  - write `.completed/step-2b.5`;
  - also write `.completed/step-2b` only when `--include-step2b` is set;
  - then honor `.pause-requested`;
  - exit 0 without running `design-postplan-emit.sh`.
- Keep the normal postplan emit path behavior:
  - normal path still honors the existing pause gate before `design-postplan-emit.sh`;
  - completion-only marker writes do not move that normal-path pause gate.
- On clean `_postplan_rc=0`, write `.completed/step-2b.5` for all sites.
- Continue writing `.completed/step-2b` only for the initial Step 2b site.
- Preserve current rc 12/13 behavior for initial Step 2b, which writes only `.completed/step-2b` before Split-path handling.

### UPDATED: `skills/design/scripts/design-step3-state.md`

Clarify sentinel ownership.

Keep this concise:
- `design-step3-review.sh --postplan-operator-continue` writes the non-plan-changing postplan resume marker.
- Legacy continuation preview cleanup is owned by `design-step3-continuation-entry.sh`.
- Do not document a new `design-step3-state.sh` mode for postplan operator continue.

### UPDATED: `skills/design/scripts/review-design-step3-loop.md`

Update the Step 3 loop contract to match launcher-owned state writes.

Update:
- Replace raw `.postplan-operator-continue-N` write instructions with `design-step3-review.sh --starting-round N --postplan-operator-continue`.
- Replace raw phase writes with `design-step3-review.sh --starting-round N --phase <phase>`.
- Replace raw per-round findings env writes with `design-step3-review.sh --starting-round N --findings-file <path>`.
- State that `design-step3-review.sh` is the launcher-owned wrapper for these resume-state writes.
- State that flag-bearing wrapper calls write validated resume state before pause-save.
- State that no-flag wrapper calls preserve first-entry pause behavior.
- State that the wrapper also resumes the review loop after state write and pause-save.
- State that callers must not split a migrated phase write and the following review resume into two wrapper calls.
- Keep existing loop consumption semantics:
  - per-round findings env is consumed once;
  - postplan continue marker is consumed once;
  - existing phase dispatch behavior is unchanged.

### UPDATED: `skills/design/SKILL.md`

Replace raw sentinel, phase, env, and completion instructions with wrapper calls.

Update the affected prose:
- Gate A Ready-for-review:
  - route to the single Step 3 entry fence;
  - do **not** add a separate `design-step3-entry.sh --reentry` call at the Gate A boundary;
  - ensure the Step 3 entry fence passes `--reentry` for this routed re-entry.
- Gate C Re-run review panel:
  - route to the single Step 3 entry fence;
  - do **not** add a separate `design-step3-entry.sh --reentry` call at the Gate C boundary;
  - ensure the Step 3 entry fence passes `--reentry` for this routed re-entry.
- Step 3 entry:
  - state that re-entry is requested through the Step 3 entry fence with `design-step3-entry.sh --reentry`.
- Canonical Step 3 resume fence:
  - replace any bare mid-loop `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"` template with the collapsed wrapper form;
  - point generic prose to the post-loop resume matrix when the required flag depends on state;
  - state that mid-loop resumes must include exactly the needed state flag on the same wrapper call;
  - state that no migrated mid-loop resume uses `--starting-round` alone.
- MAV re-tally prose:
  - replace any prompt-side phase write or bare resume call with one wrapper call;
  - when refreshed accepted findings count is zero, use `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation`;
  - when refreshed accepted findings count is greater than zero, use `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-apply`.
- Step 1e optional-trailer discussion re-entry postplan boundary:
  - rely on `design-step2b-postplan.sh --site discussion-round2` clean rc path to write `.completed/step-2b.5`;
  - remove any inline raw `.completed/step-2b.5` write for rc 0;
  - use `design-step2b-postplan.sh --write-completion-only` for non-exiting Override or drift returns that bypass the clean postplan path.
- Step 2b validator Override:
  - replace raw `.completed/step-2b` write with `design-step2b-postplan.sh --write-step2b-completion-only`;
  - keep retained Step 2b.5 as the owner of `.completed/step-2b.5`.
- Standalone retained Step 2b.5 success boundary before Step 3:
  - replace raw `.completed/step-2b.5` write with `design-step2b-postplan.sh --write-completion-only`;
  - if the immediately preceding normal postplan wrapper path already wrote the marker, document that and remove the duplicate prompt-side write.
- Split non-exiting returns:
  - replace raw completion marker writes with `design-step2b-postplan.sh --write-completion-only`;
  - add `--include-step2b` only for initial-site returns where both markers are already complete.
- Retained Step 2b.5 Override and drift returns:
  - replace raw `.completed/step-2b.5` writes with `design-step2b-postplan.sh --write-completion-only`.
- MainAgent vote resume:
  - when refreshed accepted findings count is zero, use one resume call: `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation`;
  - when refreshed accepted findings count is greater than zero, preserve apply flow with one resume call: `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-apply`.
- Post-loop resume matrix:
  - replace every raw `.step3-round-N.phase` write plus later review resume with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase <phase>` call at the resume boundary;
  - include `main-agent-apply-required` and settled loop-mode rows;
  - use `--phase awaiting-continuation` for non-apply continuation rows;
  - do not retain a second bare `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"` call for the same boundary.
- Gate B zero-findings and settled loop-mode resumes:
  - replace raw continuation phase writes plus separate review resume with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` call.
- Plan-changing postplan Fix-and-retry/autofix:
  - replace raw phase writes plus separate review resume with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-post-apply` call at the resume boundary.
- Per-round approval:
  - replace raw `.gate-b-per-round-approval-round-N.env` writes plus later review resume with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --findings-file "<path>"` call.
- Postplan operator non-plan-changing resume:
  - replace raw `.postplan-operator-continue-N` writes plus later review resume with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --postplan-operator-continue` call.
- Legacy heuristic continuation:
  - remove the raw clear instruction and say `design-step3-continuation-entry.sh` owns the clear.

Do not add direct `design-step3-state.sh` calls to SKILL bash fences for these migrated state writes.

Do not alter unrelated cleanup commands such as scout manifest cleanup or diagram branch cleanup.

### UPDATED: `skills/design/references/approval-gates.md`

Replace raw marker, phase, completion, and env writes with script-owned calls.

Update:
- Gate A Ready-for-review and loop exit:
  - route to the single Step 3 entry fence;
  - pass `--reentry` at that Step 3 entry fence only;
  - do not add a separate Gate A wrapper invocation.
- Gate C Re-run review panel:
  - route to the single Step 3 entry fence;
  - pass `--reentry` at that Step 3 entry fence only;
  - do not add a separate Gate C wrapper invocation.
- Gate B zero-findings loop-mode resume:
  - use a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` call at the resume boundary.
- MainAgent vote resume:
  - zero accepted findings resumes with `--phase awaiting-continuation`;
  - accepted findings resumes with `--phase awaiting-apply`;
  - no MAV re-tally path may end in a bare `--starting-round` mid-loop resume.
- Per-round approval persistence:
  - use `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --findings-file "<path>"`.
- Shared post-apply pipeline:
  - rc 0 stays on the normal postplan wrapper path and relies on that clean path to write `.completed/step-2b.5`;
  - remove raw `.completed/step-2b.5` writes from step 8;
  - rc 12 Override uses the exact completion wrapper for the completed boundary;
  - Split non-exiting returns use the completion-only wrapper;
  - plan-changing Fix-and-retry/autofix resumes with `--phase awaiting-post-apply`;
  - collapse old step 9 phase-write and step 10 resume into one resume fence:
    - step 9 only determines or binds `STEP3_RESUME_ROUND`;
    - step 9 does not call `design-step3-review.sh`;
    - step 10 calls `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` once;
    - remove any second `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"` call for the same resume.
- Any other migrated phase-write site that was followed by a separate review launch must use the same single-call pattern.
- Postplan operator continue marker prose:
  - use `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --postplan-operator-continue`.
- Legacy continuation clear prose:
  - state that `design-step3-continuation-entry.sh` owns the clear.

Keep gate choices and ordering unchanged.

### UPDATED: `skills/design/references/discussion-rounds.md`

Replace Round 2 postplan completion writes without bypassing validation.

Update:
- rc 0 keeps the normal `design-step2b-postplan.sh --site discussion-round2` fence and relies on that wrapper's clean rc path to write `.completed/step-2b.5`.
- Override and drift non-exiting returns use `design-step2b-postplan.sh --write-completion-only`.
- Split non-exiting returns use completion-only wrapper, with `--include-step2b` only when both boundaries are complete.
- Keep discussion revision authority and scout cleanup prose unchanged.

### UPDATED: `skills/design/references/decompose-panel.md`

Replace non-exiting Split return writes.

Update:
- Use `design-step2b-postplan.sh --write-completion-only`.
- Use `--include-step2b` for initial-site merged Split returns where both Step 2b and Step 2b.5 are complete.
- Preserve routing text for Refine, no-split Continue, and retained decomposition paths.

### UPDATED: `skills/design/scripts/test-design-pause-resume.sh`

Extend pause/resume coverage for moved sentinel ownership.

Add or update cases:
- Gate A/Gate C Step 3 re-entry uses the Step 3 entry fence with `design-step3-entry.sh --reentry`.
- `--reentry` does not clear `.step3-entry-plan-printed`.
- Continuation entry clears `.step3-entry-plan-printed` before pause-save.
- `--write-step2b-completion-only` writes `.completed/step-2b` only.
- `--write-completion-only` writes `.completed/step-2b.5`.
- `--write-completion-only --include-step2b` writes both completion markers.
- Paused `--write-step2b-completion-only` snapshots `.completed/step-2b`.
- Paused `--write-completion-only` snapshots `.completed/step-2b.5`.
- Paused `--write-completion-only --include-step2b` snapshots both completion markers.
- Completion-only modes write markers before honoring `.pause-requested`.
- Normal `design-step2b-postplan.sh` still honors the existing pause gate before `design-postplan-emit.sh`.
- No-flag `design-step3-review.sh` preserves existing first-entry pause behavior.
- A paused Step 3 resume after `--findings-file`, `--phase awaiting-apply`, `--phase awaiting-post-apply`, `--phase awaiting-continuation`, or `--postplan-operator-continue` snapshots the written state before pause-save.
- `--postplan-operator-continue` is invoked through `design-step3-review.sh`, not by directly calling `design-step3-state.sh`.
- A migrated phase-plus-resume flow uses one `design-step3-review.sh --starting-round ... --phase ...` call, not a state-write call followed by a second resume call.

### UPDATED: `skills/design/scripts/test-review-design-step3-loop.sh`

Add lightweight regression coverage for the new resume-file contract if practical.

Cover:
- A `.gate-b-per-round-approval-round-N.env` written with `FINDINGS_FILE=` under `DESIGN_TMPDIR` is consumed once.
- An invalid findings file outside `DESIGN_TMPDIR`, unreadable, non-regular, or symlinked is rejected before env state is written.
- An impossible `--starting-round` greater than `review-round-count.txt + 1` is rejected before phase, findings env, or postplan continue state is written.
- A postplan continue marker written through `design-step3-review.sh --postplan-operator-continue` is consumed once.
- `awaiting-vote` is not accepted as a resume phase.
- Existing loop-consumption cases remain unchanged when they already cover the behavior.

### UPDATED: `skills/design/scripts/test-design-step3-state.sh`

Extend coverage for the state-helper side of the ownership split.

Add or update cases:
- Direct-review and auto-continuation state-helper modes do not clear `.step3-entry-plan-printed`.
- No `design-step3-state.sh` mode writes `.postplan-operator-continue-N`.
- Existing state-helper ownership for direct-review, gate-b-bypass, and auto-continuation entry remains unchanged.
- The wrapper-level clear for `.step3-entry-plan-printed` is covered in `test-design-pause-resume.sh`, not by changing state-helper behavior.

### UPDATED: `skills/design/scripts/test-step3-review-cap.sh`

Update the cap harness grep pin after the approval-gates migration.

Change:
- Replace the grep that expects raw `.step3-round-$STEP3_RESUME_ROUND.phase` prose with a stable assertion for the wrapper-owned continuation resume contract.
- Prefer matching `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation`.
- Keep the harness intent unchanged.

### UPDATED: `scripts/test-design-structure.sh`

Update structure pins that depend on wrapper internals and prompt cross-references.

Add or update checks for:
- `design-step3-entry.sh` accepts `--reentry`.
- `design-step3-entry.sh --reentry` writes `.step3-reentry` without clearing `.step3-entry-plan-printed`.
- `design-step3-continuation-entry.sh` owns the `.step3-entry-plan-printed` clear.
- `design-step2b-postplan.sh` accepts `--write-completion-only`, `--include-step2b`, and `--write-step2b-completion-only`.
- `design-step3-review.sh` accepts `--phase`, `--findings-file`, and `--postplan-operator-continue`.
- `design-step3-review.sh` validates flag-bearing resume state before writing.
- `design-step3-review.sh` writes flag-bearing resume state before pause-save.
- `design-step3-review.sh` preserves no-flag first-entry pause behavior.
- `skills/design/SKILL.md` and `skills/design/references/approval-gates.md` use collapsed single-call resume prose for migrated mid-loop resumes.
- `skills/design/SKILL.md` does not retain a canonical mid-loop resume fence that uses `--starting-round` alone.
- MAV prose routes accepted findings to `--phase awaiting-apply` and zero accepted findings to `--phase awaiting-continuation`.
- Gate A/Gate C prose routes to the single Step 3 entry fence with `--reentry`, not a separate boundary call.

## Approach

Use existing launcher wrappers as state owners.

Keep the change small:
- Do not add a new script.
- Do not add a new `design-step3-state.sh` mode for postplan operator continue.
- Do not call `design-step3-state.sh` directly from SKILL bash fences for migrated state writes.
- Do not change review loop behavior.
- Do not change sentinel names.
- Do not change sentinel ordering.

The ownership pattern is:
- **Entry markers** ride the single Step 3 entry fence with `design-step3-entry.sh --reentry`.
- **Legacy continuation preview cleanup** lives only in `design-step3-continuation-entry.sh`.
- **Resume phase and findings env** ride `design-step3-review.sh`.
- **Postplan operator continue marker** rides `design-step3-review.sh --postplan-operator-continue`.
- **Step 2b-only completion** rides `design-step2b-postplan.sh --write-step2b-completion-only`.
- **Step 2b.5 completion** rides `design-step2b-postplan.sh --write-completion-only`.
- **Both Step 2b and Step 2b.5 completion** rides `design-step2b-postplan.sh --write-completion-only --include-step2b`.

Ordering invariants:
- `design-step3-review.sh` preserves current pre-launch pause behavior when no resume-state flag is supplied.
- `design-step3-review.sh` validates all resume flags and starting-round bounds, writes requested resume state, then honors pause-save, then launches the review driver when resume-state flags are supplied.
- Because flag-bearing `design-step3-review.sh` launches the review driver, migrated prose must collapse write-plus-resume pairs into one wrapper call at the point where review should resume.
- `design-step2b-postplan.sh` completion-only modes validate, write requested completion markers, then honor pause-save, then exit.
- `design-step2b-postplan.sh` normal postplan emit path keeps its existing pause gate before `design-postplan-emit.sh`.
- If validation fails, the wrapper writes no migrated state.

After script changes, update prompt prose and script contracts to name those owners instead of shell redirections.

## Edge cases

- `--phase` without `--starting-round` must fail with usage error.
- `--findings-file` without `--starting-round` must fail with usage error.
- `--postplan-operator-continue` without `--starting-round` must fail with usage error.
- No-flag `design-step3-review.sh` launch must preserve current first-entry pause behavior.
- Flag-bearing `design-step3-review.sh` launch must write validated state before pause-save.
- `--starting-round` greater than `review-round-count.txt + 1` must fail before any resume-state write.
- `--phase awaiting-vote` must fail.
- `--findings-file` must reject relative paths, CR/LF, paths outside `DESIGN_TMPDIR`, unreadable files, non-regular files, and symlinks.
- Failed `--findings-file` validation must leave no env state behind.
- Failed phase, postplan continue, or starting-round validation must leave no state behind.
- Combined resume flags must write all requested state only after all validation succeeds.
- A migrated phase write followed by review resume must become one wrapper call, not two.
- Shared Gate B post-apply steps must not call `design-step3-review.sh` in both step 9 and step 10.
- Mid-loop resumes for migrated state must not use bare `--starting-round` alone.
- Gate A and Gate C must not double-invoke `design-step3-entry.sh --reentry`; they route to the single Step 3 entry fence.
- `--write-step2b-completion-only` must not write `.completed/step-2b.5`.
- `--write-completion-only` must not run postplan validation.
- Completion-only modes must write completion markers before pause-save.
- Normal postplan mode must keep its existing pause gate before postplan emit.
- Initial Step 2b validator Override needs only `step-2b`.
- Initial Step 2b Split returns need both `step-2b` and `step-2b.5`.
- Gate B and discussion postplan returns need `step-2b.5` only.
- Discussion Round 2 rc 0 must keep the normal postplan fence.
- Standalone retained Step 2b.5 success before Step 3 must not leave prompt-owned completion writes.
- Vote re-tally with accepted findings must resume apply, not continuation.
- Vote re-tally with zero accepted findings may resume continuation.
- `main-agent-apply-required`, Gate B zero-findings, and settled loop-mode continuation rows must use `design-step3-review.sh --phase awaiting-continuation`.
- Plan-changing postplan Fix-and-retry/autofix must resume `awaiting-post-apply`.
- Non-plan-changing postplan operator continue must write the marker through `design-step3-review.sh --postplan-operator-continue`.
- Continuation preview cleanup must happen before pause-save.

## Failure modes

1. **Re-entry clears preview sentinel.** Warning: Gate A or Gate C re-entry prints Step 3 plan preview again. Mitigation: keep `.step3-entry-plan-printed` cleanup solely in `design-step3-continuation-entry.sh`.
2. **Gate A or Gate C double-launches entry.** Warning: entry runs preview/state twice. Mitigation: route gates to the single Step 3 entry fence.
3. **Validator Override marks Step 2b.5 too early.** Warning: pause/resume after Override skips retained Step 2b.5. Mitigation: use `--write-step2b-completion-only` for validator Override.
4. **Completion-only pause snapshots without markers.** Warning: paused Override or Split return resumes without sentinels. Mitigation: dispatch completion-only modes before the normal pause gate.
5. **Step 3 first entry changes pause snapshot.** Warning: no-flag launch snapshots different state. Mitigation: preserve existing pre-launch pause behavior for no-flag calls.
6. **Step 3 resume pause snapshots without resume state.** Warning: paused resume lacks phase/findings/continue marker. Mitigation: write validated resume state before flag-bearing pause-save.
7. **Invalid starting round leaves stale resume state.** Warning: wrapper writes files then inner driver rejects `--starting-round`. Mitigation: mirror starting-round bounds check before writes.
8. **Postplan operator continue has no launcher path.** Warning: prose names `design-step3-state.sh` directly. Mitigation: route through `design-step3-review.sh --postplan-operator-continue`.
9. **Vote resume skips apply.** Warning: accepted findings exist but loop resumes continuation. Mitigation: use `--phase awaiting-apply` when refreshed accepted count > 0.
10. **Findings env is written but ignored by the loop.** Warning: loop falls back to `accepted-plan-findings.md`. Mitigation: `--findings-file` validation must match loop consumer contract.
11. **Discussion rc 0 bypasses postplan validation.** Warning: Round 2 plan rewrite skips validation. Mitigation: keep rc 0 on normal `design-step2b-postplan.sh --site discussion-round2` path.
12. **Docs still contain raw writes.** Warning: grep finds raw prompt-side writes. Mitigation: update SKILL.md, reference docs, and `review-design-step3-loop.md`.
13. **Canonical resume fence still teaches bare `--starting-round`.** Warning: mid-loop resume prose omits state flag. Mitigation: replace canonical fence with collapsed wrapper forms.
14. **Approval gate step 8 keeps dual completion ownership.** Warning: `approval-gates.md` still tells orchestrator to write `.completed/step-2b.5` after rc 0. Mitigation: rely on postplan wrapper clean rc path.
15. **Cap harness pins removed raw prose.** Warning: `test-step3-review-cap.sh` fails on raw phase-write grep. Mitigation: update the pin to wrapper-owned continuation resume contract.
16. **Design structure harness pins stale contracts.** Warning: `scripts/test-design-structure.sh` fails. Mitigation: update structure pins.
17. **Gate B post-apply double-launches Step 3 review.** Warning: step 9 and step 10 both call `design-step3-review.sh`. Mitigation: collapse step 9 and step 10 into one resume fence.
18. **Review resumes before post-apply work finishes.** Warning: wrapper invoked before later Gate B steps run. Mitigation: place single wrapper invocation only at the final resume boundary.

## Testing strategy

- `bash skills/design/scripts/test-design-pause-resume.sh`
- `bash skills/design/scripts/test-review-design-step3-loop.sh`
- `bash skills/design/scripts/test-design-step3-state.sh`
- `bash skills/design/scripts/test-step3-review-cap.sh`
- `bash scripts/test-design-structure.sh`
- `bash scripts/relevant-checks.sh`

Grep verification — no raw prompt-side writes remain in /design prose for:
- `.step3-reentry`, `.step3-round-N.phase`, `.postplan-operator-continue-N`, `.gate-b-per-round-approval-round-N.env`, `.completed/step-2b`, `.completed/step-2b.5`, `.step3-entry-plan-printed`

Verify: migrated phase-plus-review-resume prose does not call `design-step3-review.sh` twice for one resume boundary; no mid-loop resume uses bare `--starting-round` alone; MAV routes zero accepted findings to `awaiting-continuation` and accepted findings to `awaiting-apply`; Gate A/C routes to single Step 3 entry fence.

## Acceptance

- No raw marker, phase, or env-write instruction remains in /design prose; every write has a script owner.
- Pause/resume semantics for each sentinel unchanged; `test-design-step3-state.sh` and the pause-resume harnesses extended.

diff_lines: 1115

## Test plan
(no test plan section in plan-file)
