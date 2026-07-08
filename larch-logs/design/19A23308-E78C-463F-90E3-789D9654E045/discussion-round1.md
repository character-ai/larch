# Discussion Round 1 — issue #6612

## Decision 1: #6591 disposition mechanic
- **Question**: How should the #6591 disposition be corrected: correcting comment only, reopen-and-re-close as completed, or no tracker mutation?
- **Resolution**: Correcting comment only. Post one comment on closed #6591 recording the real root cause (bgjob owner-validation on harness kill, fixed via #6580/#6595). Leave close state and reason untouched. Explicit refusal: do NOT reopen #6591 or change its close reason.
- **Source**: user

## Decision 2: Executor for the #6591 correction
- **Question**: Who posts the correcting comment: the /implement run, the design run, or the operator manually?
- **Resolution**: The /implement run posts it as a plan step, using a file-backed body (`gh issue comment 6591 --body-file ...`), so the correction can cite the regression test that pins the behavior. Explicit refusal: do NOT post the comment during this design run.
- **Source**: user

## Scope boundaries and hard constraints (from issue + repo conventions)
- In-scope: static confirmation that the Step 3 (`implement-step3-checks`) path inherits the #6580/#6595 fixes; a false-orphan regression test parameterized across the shared-launcher steps (step3, step5, step6, step7a, step8); the #6591 correcting comment posted by the implement run.
- Conditional scope: a Step-3-specific code fix only if drafting-time analysis finds a trigger the #6580/#6595 fixes do not cover.
- Hard constraint: tests must use fake/injected time, no real sleeps (repo testing convention).
- Hard constraint: GitHub body payloads are file-backed (`--body-file`), never inline `--body`.
