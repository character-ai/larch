# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Executable normalization of legacy assessment handoffs
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-step8-route
- **Severity**: major
- **Concern**: Legacy `NEXT_ACTION=invariants-assessment` and `NEXT_ACTION=guidelines-assessment` handoffs can reach the adapter without being mechanically normalized to `NEXT_ACTION=assessments`. The current prompt-only normalization prose does not atomically persist the canonical handoff, so the adapter can hard-fail before assessment and resume/re-entry can repeat the stale alias. Normalization should preserve unrelated keys, canonicalize aliases, validate kind tokens and combined detail, and fail closed before the adapter launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-step8-route: Add a thin pre-adapter launcher (for example `python/cli.py ship normalize-assessment-handoff` or a one-line `implement-run` wrapper) that reads `.ship-route-exit-handoff.env`, applies the three alias rules, validates kind tokens fail-closed, writes the normalized env, and emits the canonical `DETAIL`/kind list for downstream validation; keep the SKILL prose but bind validation to that helper’s stdout instead of free-form Edit/Write.


### FINDING_2: Canonical expected-kind binding and order-independent validation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-step8-route
- **Severity**: major
- **Concern**: Post-adapter validation does not explicitly bind the expected kind list to Piece 2 `normalize_kinds` ordering. A combined request such as `DETAIL=guidelines,invariants` can validly produce `ASSESSMENT_REQUESTED_KINDS=invariants,guidelines`, but comparison with raw `DETAIL` order can falsely route a successful assessment to Tool Failure. Bind the expected kinds once using canonical normalization, compare terminal values only to that binding, and forbid raw `DETAIL` or `DETAIL_FILE` order equality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step8-route: State explicitly that canonical kind comparison uses Piece 2 order (`invariants` before `guidelines`, set equality not raw `DETAIL` order), or compare parsed kind sets; add a regression in `test-architectural-guidelines-step.sh` that `DETAIL=guidelines,invariants` must accept adapter stdout `ASSESSMENT_REQUESTED_KINDS=invariants,guidelines`.
