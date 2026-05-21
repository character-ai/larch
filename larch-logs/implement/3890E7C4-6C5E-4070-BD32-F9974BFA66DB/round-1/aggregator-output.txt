```text
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

### FINDING_9: Misleading test comment about LARCH_NO_LOGS_COMMIT vs CLI flag
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: A comment references `LARCH_NO_LOGS_COMMIT` while the test sets suppression via `--no-logs-commit true`, which slows tracing of how the env is established.
- **Suggested revision**: Align the comment with the CLI flag or note the export path from `ship-pr.sh`.

### FINDING_10: [OUT_OF_SCOPE] SECURITY.md durable-store narrative vs new post-merge commit intent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `SECURITY.md` still describes commit refusal patterns (e.g., post-merge on `main`) that may become inaccurate once the ship-pr-owned flush/bypass behavior is finalized; the file is called out as not part of the functional diff surface.
- **Suggested revision**: Update `SECURITY.md` after the sentinel/commit contract and any bypass are finalized and landed.

### FINDING_11: [OUT_OF_SCOPE] Unrelated committed implement run artifacts under larch-logs/implement/
- **Reviewer(s)**: dyn-path-resolution-output.txt, dyn-ordering-invariant-output.txt, dyn-test-stub-coverage-output.txt
- **Concern**: The branch diff appears to add committed implement run metadata under `larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/`, orthogonal to `run_postmerge_phase` logic and potentially unintended PR churn for review/bisect/policy.
- **Suggested revision**: Drop or relocate per repo run-log policy before merge if not intentionally part of the functional change.

### FINDING_12: [OUT_OF_SCOPE] postmerge_missing_manifest test likewise does not assert write-final-report
- **Reviewer(s)**: dyn-test-stub-coverage-output.txt
- **Concern**: `postmerge_missing_manifest` uses the same larch-log-only sentinel pattern and does not pin the new `write-final-report.sh` step.
- **Suggested revision**: Extend that scenario with the same write-final-report call/order assertions if/when in scope for the change set.

### FINDING_13: [OUT_OF_SCOPE] write_state fixtures omit MERGE_RESULT for future final-summary assertions
- **Reviewer(s)**: dyn-test-stub-coverage-output.txt
- **Concern**: `write_state` omits `MERGE_RESULT`, so future assertions against real `final-summary.md` rendering would need explicit merged state because `write-final-report.sh` defaults `OUTCOME` to `bailed` when `MERGE_RESULT` is empty; this predates the branch but affects how hardening tests should model production.
- **Suggested revision**: When adding content-level assertions, extend fixtures with `MERGE_RESULT=merged` (or equivalent) rather than assuming existing `write_state` is sufficient.
```
