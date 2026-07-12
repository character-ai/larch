## Goal
Implement issue #7088: [IMPLEMENTING] [OOS] Salvage provenance is spoofable [OUT_OF_SCOPE].

## Implementation Plan
## Plan

## Approach

Bind each salvage commit to its deterministic lane step. Keep the existing subject, single-commit ancestry, and parent-equals-`starting_head` checks. Require exactly one `Larch-Salvage-Step` trailer whose value equals `identity.step` before either normal dispatch or crash recovery authorizes reship.

Extract one shared provenance validator used by crash finalize and normal dispatch. Every reship-capable HEAD change must pass it; unvalidated commits fail closed.

### UPDATED: python/larch/implement/ci_fixer_lane.py

- Add a shared `_salvage_provenance_valid(identity, *, runner, live_head) -> bool` helper (or refactor `_validated_salvage_head` into it) that checks:
  - `live_head != starting_head`
  - exactly one commit between `starting_head` and `live_head`
  - parent of `live_head` is `starting_head`
  - subject is `Apply CI fixer working-tree edits ({tier})`
  - full commit body from `git show -s --format=%B` contains exactly one `Larch-Salvage-Step` trailer whose value equals `identity.step`
  - reject missing, duplicate, or mismatched trailers
- In `_salvage_uncommitted_fixer_edits`, write `Larch-Salvage-Step: {identity.step}` into the salvage commit body when committing the fixer delta.
- After `_salvage_uncommitted_fixer_edits` returns `committed_head`, call the shared validator on that head. Raise `LaneClosedError` (not a reship result) when post-commit provenance verification fails; leave the commit on disk for operator inspection.
- In `_dispatch`, when `launcher_exit == 0` and `final_head != identity.starting_head` (the `fixer-produced-change` branch), call the shared validator on `final_head` before returning reship. Raise `LaneClosedError` on any provenance or ancestry failure instead of authorizing reship.
- In `_dispatch`, when `launcher_exit == 0`, `final_head == identity.starting_head`, and `_salvage_uncommitted_fixer_edits` returns `committed_head`, keep the existing reship path only after post-commit validation succeeds.
- Keep `finalize_crashed_lane` fail closed: route salvage heads through the shared validator; a subject-only or malformed-provenance commit returns `operator-bail` with `crashed-lane-head-unverified` and does not advance lineage or authorize reship.

### UPDATED: python/tests/implement/test_ci.py

- Update `test_fixer_lane_dispatch_salvages_uncommitted_fixer_edit` to assert the generated commit body contains `Larch-Salvage-Step: {identity.step}`.
- Update `test_crashed_lane_validated_salvage_commit_reships` to create a commit whose body includes the expected `Larch-Salvage-Step` trailer for `identity.step`.
- Add `test_crashed_lane_spoofed_subject_without_trailer_bails`: subject-only salvage commit must return `operator-bail` / `crashed-lane-head-unverified`, must not reship, and must not write lineage state.
- Add mandatory parametrized coverage for missing, wrong-step, and duplicate `Larch-Salvage-Step` trailers on crash finalize and normal dispatch direct-HEAD-change paths. Each case must fail closed with no reship and no lineage or rounds advance.
- Add explicit normal-dispatch uncommitted-salvage coverage for a subject-only commit without the trailer: make the salvage path produce and retain the expected-subject commit without `Larch-Salvage-Step`, assert `_dispatch` raises `LaneClosedError`, no reship or lineage/rounds advance occurs, and the offending commit remains available for inspection.
- Add normal-dispatch uncommitted-salvage coverage for wrong-step and duplicate trailers, with the same `LaneClosedError`, no-reship, no-advance, and preserved-commit assertions.
- Add `test_fixer_lane_dispatch_salvage_provenance_verification_failure_raises`: force salvage to commit, then make provenance verification fail. Assert `LaneClosedError`, no `reship`, commit preserved for inspection, and no lineage/rounds advance.

### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh

- In the `crashed-salvage` fixture, include `Larch-Salvage-Step: $FINALIZE_STEP` in the salvage commit message body.
- Add a sibling negative fixture that creates a subject-only salvage commit without the trailer and asserts `RESULT=operator-bail` / `REASON=crashed-lane-head-unverified`.

### UPDATED: SECURITY.md

- Document that CI-fixer salvage reship requires the expected subject, one-commit ancestry, parent equal to lane `starting_head`, and an exact `Larch-Salvage-Step` trailer matching the lane step.
- State that the trailer is deterministic provenance, not a cryptographic signature.

## Edge cases

- The commit has the expected subject but no `Larch-Salvage-Step` trailer.
- The trailer names another lane step.
- Multiple `Larch-Salvage-Step` trailers make identity ambiguous.
- Git cannot read the full commit body.
- Normal dispatch direct-HEAD and uncommitted-salvage paths produce subject-only commits.
- Normal dispatch: launcher exits cleanly and HEAD advanced, but provenance is missing or malformed.
- Normal dispatch: salvage commit succeeds, then post-commit provenance verification fails.
- Crash finalize: clean worktree with subject-only or malformed-provenance HEAD.

## Failure modes

All provenance read or validation failures must block reship. Preserve offending commits for operator inspection, but do not treat them as authorized fixer results. Normal-dispatch validation failures raise `LaneClosedError`; crash-finalize validation failures return `operator-bail` / `crashed-lane-head-unverified`.

## Testing strategy

Run the changed CI unit tests in `python/tests/implement/test_ci.py`, including missing, wrong-step, and duplicate-trailer cases for crash finalize, direct-HEAD dispatch, and uncommitted-salvage dispatch, plus the post-salvage-commit `LaneClosedError` regression. Run `skills/implement/scripts/test-step-8-ci-fixer.sh` to confirm the updated `crashed-salvage` fixture still reships and the new subject-only fixture bails closed.

Confidence: high. The producer, validator, dispatch, crash-finalize, and harness surfaces identify the complete change set.

## Acceptance

Run the changed CI unit tests in `python/tests/implement/test_ci.py`, including missing, wrong-step, and duplicate-trailer cases for crash finalize, direct-HEAD dispatch, and uncommitted-salvage dispatch, plus the post-salvage-commit `LaneClosedError` regression. Run `skills/implement/scripts/test-step-8-ci-fixer.sh` to confirm the updated `crashed-salvage` fixture still reships and the new subject-only fixture bails closed.

Confidence: high. The producer, validator, dispatch, crash-finalize, and harness surfaces identify the complete change set.

diff_added: 86
diff_deleted: 12
mechanical_churn: false
diff_lines: 98

## Test plan
(no test plan section in plan-file)
