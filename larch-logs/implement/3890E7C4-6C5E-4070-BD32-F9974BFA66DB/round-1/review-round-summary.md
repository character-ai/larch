# Review Round 1

- Mode: `diff`
- Accepted findings: 8
- Rejected findings: 0
- Exonerated findings: 0
- Neutral findings: 1

## Accepted Findings

### FINDING_1: Post-merge flush can commit logs after manifest or write-final-report failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-path-resolution-output.txt
- **Concern**: After `larch-log.sh manifest`, `run_postmerge_phase` can still run `write-final-report.sh` and (when not suppressed) `larch-log.sh commit` without treating a non-zero manifest exit as a hard stop; `larch-log.sh commit` can also run after `write-final-report.sh` fails because failures are folded into `record_failure` while the phase still advances. That can land a log commit whose tree does not reliably reflect `status=done` plus an updated merged `final-summary.md`, preserving stale `OUTCOME`/summary on failure paths (the original audit-class bug on partial failure). Doc text that reads like strict ordering after manifest reaches `status=done` mismatches this non-aborting control flow.
- **Suggested revision**: Persist manifest exit status and skip flush/commit unless it is zero; run `larch-log.sh commit` only when `write-final-report.sh` exits zero (or document and test an explicit alternative fail-closed policy); align `scripts/ship-pr.md` narrative with whichever policy is chosen.


### FINDING_2: Post-merge write-final-report lacks transient-error parity with pre-PR path
- **Reviewer(s)**: dyn-path-resolution-output.txt
- **Concern**: The pre-PR `write-final-report.sh` path classifies combined output with `is_transient_net_signature` and can `exit_transient_net`, but the post-merge invocation only records warnings, so the same class of transient GitHub/API failures can be treated as soft while the phase still reaches `done`.
- **Suggested revision**: Mirror the pr-create envelope handling (scan captured failure output and `exit_transient_net` when the signature matches) so retryable failures are not silently folded into completion.


### FINDING_3: Post-merge larch-log commit likely conflicts with sentinel and default-branch refusal
- **Reviewer(s)**: dyn-ordering-invariant-output.txt
- **Concern**: Ordering/invariants imply a post-merge sentinel exists before `postmerge`, and `implement-finalize.sh postmerge` leaves the worktree on the default branch; `larch-log.sh commit` is documented to refuse when the sentinel exists and on the default branch, so the new post-merge commit may be best-effort-only via `record_failure`, failing to update `final-summary.md` on `main` while adding recurring warnings—undermining the intended audit fix unless refusal rules and callers are reconciled.
- **Suggested revision**: Add a deliberately narrow, audited exception or alternate scoped commit path allowed only from `run_postmerge_phase` under explicit preconditions, and align `scripts/ship-pr.md` (and related policy text) with the real guardrails.


### FINDING_4: ship-pr.md contradicts itself on post-merge sentinel vs post-merge larch-log commit
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ordering-invariant-output.txt
- **Concern**: Interface/State/Invariants still read like the sentinel suppresses post-merge `larch-log` commits (and/or that postmerge cannot create/push larch-log-only commits on `main`) while the Postmerge section documents an intentional post-merge `larch-log.sh commit` on the current branch (typically `main`). Operators and auditors cannot tell which contract is authoritative.
- **Suggested revision**: Rewrite State/Invariants/Interface and Postmerge together so sentinel rationale, suppressions, and the intentional post-merge flush/commit path are explicitly reconciled (e.g., sentinel blocks prompt-side/teardown commits while a named exception covers only the `ship-pr.sh` post-merge call).


### FINDING_5: Intro lifecycle still pins final tracking-issue summary to Step 18 only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The intro still assigns the final tracking-issue summary to Step 18 only, which is misleading now that post-merge upserts the final summary via `write-final-report`.
- **Suggested revision**: Update the intro lifecycle paragraph to include the post-merge upsert/flush step in the authoritative story.


### FINDING_6: test harness stub does not model real larch-log commit refusal rules
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The default `larch-log.sh` stub exits success and does not enforce production refusal behavior (sentinel/main guards), so regressions in the real `ship-pr` vs `larch-log` contract can ship undetected.
- **Suggested revision**: Extend the stub and/or add integration coverage that exercises the real `larch-log.sh commit` refusal/bypass contract for sentinel+default-branch scenarios.


### FINDING_7: postmerge tests do not pin write-final-report invocation or outcome rendering
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-stub-coverage-output.txt
- **Concern**: Postmerge tests primarily grep `larch-log-calls.txt` for manifest/`status=done`/commit lines and do not assert `write-final-report.sh` ran in the expected order; because `record_failure` does not fail the phase, removing the new write-final-report block or letting it fail non-zero may not turn the harness red unless additional assertions exist.
- **Suggested revision**: Teach the `write-final-report.sh` stub (or a dedicated fixture) to record a sentinel line for post-merge invocations and assert ordering relative to manifest/commit; optionally assert merged `final-summary.md` content (e.g., `OUTCOME=merged`) once fixture state includes `MERGE_RESULT=merged`.


### FINDING_8: Stale comment in ship-pr.sh misstates manifest snapshot semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A comment around the post-merge manifest block is misleading about local-only manifest / in-progress snapshot semantics relative to the new behavior.
- **Suggested revision**: Update the comment to match the current manifest/update semantics.


