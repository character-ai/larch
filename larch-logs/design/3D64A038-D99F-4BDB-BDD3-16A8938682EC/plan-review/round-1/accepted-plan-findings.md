### FINDING_1: Scout tier raw intermediates can be published without deny arms
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: F15 tier-specific scout raw stems such as `.raw.cursor` / `.raw.claude` need matching publish exclusions, or raw/intermediate scout artifacts and sidecars can be committed despite the no-raw-transcript policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add explicit deny patterns for scout tier intermediates (e.g. scout-plan-manifest.json.raw.* and/or *.raw.cursor / *.raw.claude and their sidecars); publish only *.failure-diag carriers


### FINDING_2: Code-flow Claude subprocess failures are not routed to execution-issues or vendor diagnostics
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The direct Claude subprocess path for code-flow diagram generation can leave diagnostics in `code-flow-launch.err` or `code-flow-diagram.raw.md.failure-diag`, while `generate-code-flow-diagram.sh` / `step-7a.sh` record only generic failure state or stderr, so committed execution issues and vendor diagnostics can miss the actual carrier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update this call path to resolve diagnostics from code-flow-diagram.raw.md and append the resolved carrier to execution-issues plus vendor-failure-diagnostics before returning failure
  - From Codex-Innovation: Add generate-code-flow-diagram.sh/step-7a.sh to the plan: resolve the raw output carrier on generation failure, append it to execution-issues, append_vendor_failure_diagnostics, and cover it in test-generate-code-flow-diagram.sh or test-step-7a.sh
  - From Codex-Requirements: Add these direct sites to the audit and either append their resolved carrier to execution-issues plus the canonical batch, or route them through an updated site-aware launcher that does so


### FINDING_3: lint-fix-loop direct launcher failures can lose their diagnostic carrier
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Concern**: `lint-fix-loop.sh` launches Codex/Cursor through direct launcher paths but is omitted from the saved/logged/flushed handling, so dispatch-failed lint-fix runs can leave the failure carrier only in scratch state while `ship-pr` records a generic failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add lint-fix-loop.sh to the audit and, on Codex/Cursor dispatch failure, resolve the per-tool carrier and append it to execution-issues and the canonical vendor-failure-diagnostics batch before emitting main-agent-required or failed
  - From Codex-Requirements: Add these direct sites to the audit and either append their resolved carrier to execution-issues plus the canonical batch, or route them through an updated site-aware launcher that does so


### FINDING_7: Claude subprocess stale failure carriers can survive successful reruns
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: `launch-claude-subprocess.sh` writes `OUTPUT.failure-diag` only on failure and does not clear it at launch start or success, so a later successful run using the same output path can flush stale diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Clear OUTPUT_CANON.failure-diag after output path validation before launching Claude, and remove it on success; add a failure-then-success same-output regression test


### FINDING_9: Collector retry failure carriers are not reachable from failure logging
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: When `collect-agent-results.sh` retries an empty reviewer and that retry fails, the carrier is written on the retry output path while collector failure logging still looks at the original reviewer path, so retry diagnostics can be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Teach compose-collector-failure-log or the shared collector resolver to check retry and ns-retry failure-diag candidates, or pass the retry output path in the collector record and use it when composing the failure log.


### FINDING_10: Claude subprocess pre-output failures have no durable carrier
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: `launch-claude-subprocess.sh` can fail before `OUTPUT_CANON` exists, leaving the only diagnostic in temporary wrapper stderr that cleanup deletes, while the proposed resolver only handles an existing output carrier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Before resolving/appending on rc != 0, have launch-claude-review compose the carrier from SUBPROCESS_STDERR with write_failure_diag --sink or persist it as OUTPUT.launcher-stderr and include that path in the resolver, batch append, and tests.


### FINDING_12: Cursor JSON `.result` diagnostics are stripped from failure carriers
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan strips top-level Cursor `.result` JSON sections even for failures, so a Cursor failure whose useful diagnostic is only in `.result` can produce a committed carrier without the actual error text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Preserve a bounded redacted failure-only excerpt of Cursor .result when exit is nonzero or is_error is true, while continuing to strip success transcripts and non-error bulk content


### FINDING_13: implement-finalize teardown does not flush vendor-failure-diagnostics
- **Reviewer(s)**: Cursor-dyn-publish-flush-consistency
- **Severity**: important
- **Concern**: `implement-finalize.sh` flushes execution issues and commits larch logs, but the plan omits flushing `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.txt`, so early bails before `step-7a.sh` can lose composed vendor carriers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-publish-flush-consistency: Mirror flush_execution_issues_safety_net: call the vendor-failure-diagnostics flush helper from implement-finalize.sh teardown before larch-log.sh commit; document in implement-finalize.md


### FINDING_14: Basename-only write-round filtering cannot safely allow batch-unreachable failure-diag paths
- **Reviewer(s)**: Codex-dyn-publish-flush-consistency
- **Severity**: important
- **Concern**: The plan targets `round_artifact_included`, but `larch-log.sh write-round` passes only basenames, so it cannot distinguish batch-reachable from batch-unreachable `*.failure-diag` paths; a broad allow risks duplicate commits, while a narrow allow risks dropping fallback diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-flush-consistency: Revise the plan to make the batch-unreachable set exact: either keep `*.failure-diag` denied in `round_artifact_included` when all implement review producers append the batch, or change the write-round predicate to receive the relative path/source context and allow only named batch-unreachable patterns. Add the planned `test-larch-log.sh` case for both a batch-reachable non-stage and any explicit batch-unreachable allowed path.


### FINDING_15: Implement/CI launcher no-wrapper branches need give-up-ordering A
- **Reviewer(s)**: Cursor-dyn-ordering-invariant, Codex-dyn-ordering-invariant
- **Severity**: important
- **Concern**: Implement and CI launcher paths include auth-setup, model-args, binary-missing, and direct Claude branches that can exit before `run-external-agent` creates a carrier; resolve-only give-up ordering can still leave empty logs and no durable batch entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ordering-invariant: Add explicit give-up-A steps per path: write_failure_diag with branch sink/.diag resolve append_launch_failure and batch; mirror launch-review.sh F8 and launch-codex-exec.sh:58-59
  - From Codex-dyn-ordering-invariant: Revise each listed site to use give-up-ordering A on no-wrapper/direct failure branches: write_failure_diag from the branch sink/stderr/diag, resolve it, then append_launch_failure and append_vendor_failure_diagnostics before the existing exit or KV return; keep ordering B only for post-run-external-agent give-up


