### FINDING_1: No canonical dependency-removal operation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Dependency Migration Auditor, Codex-dyn-Dependency Migration Auditor
- **Severity**: major
- **Concern**: The migration flow requires adding and verifying replacement edges, then removing the original issue’s incoming and outgoing dependency relationships. The repository currently exposes add and read operations but no canonical removal helper, CLI verb, endpoint contract, post-removal verification, or failure/idempotency behavior. Without this surface, `migrate-deps` cannot satisfy its postcondition or safely permit `close-original`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a remove-blocked-by helper and CLI registration (extend issue_block.py or issue_create.py using the GitHub dependency DELETE/GraphQL remove API), and call it from decompose migrate-deps after live verification. Keep add paths on the same canonical surface.
  - From Codex-Arch: Add an explicit supported dependency-removal helper or CLI path, including its endpoint and authorization contract, and specify its verify-after-remove behavior. Add focused tests for successful removal, removal failure, and idempotent retry before `close-original`
  - From Cursor-Innovation: Extend the firm file set with `python/larch/git/gh.py` (and tests) for blocked-by removal plus re-read verification; have `decompose migrate-deps` call those helpers and fail closed when removal cannot be verified.
  - From Codex-Innovation: Specify and implement the canonical GitHub dependency-removal mutation and CLI path, including post-removal verification and idempotent retry behavior; add focused tests for successful removal and removal failure.
  - From Cursor-Pragmatic: Add a remove-blocked-by helper (GraphQL removeBlockedBy or REST DELETE) in issue_block.py or gh.py, register cli.py block-issue remove-blocked-by, call it from migrate-deps only after live verification, and extend test_decompose.py with removal-failure and idempotent-removal cases
  - From Cursor-Requirements: Add a removal primitive (e.g. `issue remove-blocked-by` via `gh api` DELETE) to `decompose migrate-deps`, document KV/exit semantics in the plan, and test add-verify-remove ordering plus fail-closed behavior when removal fails.
  - From Cursor-dyn-Dependency Migration Auditor: MExtend decompose.py plan with a remove-blocked-by helper (likely gh DELETE on dependencies/blocked_by/{id} after read), wire it through migrate-deps, and add failure tests before close-original runs.
  - From Codex-dyn-Dependency Migration Auditor: Define and implement the canonical removal path, including its CLI registration, live verification, idempotent retry behavior, and failure logging before allowing the migration sentinel


### FINDING_2: Retained paths still emit multiple partition prompts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Dependency Migration Auditor
- **Severity**: major
- **Concern**: Hard-trigger, Gate B, settle-dispatch, and sprawl routes still prescribe preliminary Split / Override / Cancel or Split / Cancel questions before entering the unified inline Split-path. These routes can therefore violate the binding exactly-one-question requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/references/step2b5-rc-handling.md (and align approval-gates-gate-b.md hard-size prose): for hard-trigger and gate-b split entry, route directly into Split-path with the inline proposal already prepared; do not emit a separate Split/Override/Cancel AskUserQuestion before decompose-panel.md.
  - From Cursor-Innovation: Add firm `### UPDATED:` rows for `step2b5-rc-handling.md`, `approval-gates-gate-b.md`, `settle-rc-dispatch.md`, `discussion-rounds.md`, `flags.md`, and `python/larch/design/design_step2b.py` so every size-trigger and sprawl entry routes straight to the unified inline Split-path with exactly one `AskUserQuestion` (partition proposal / override / other-chat).
  - From Cursor-Pragmatic: Update discussion-rounds.md so sprawl Split routes into inline partition prep and the single gate in decompose-panel.md; remove the standalone two-option sprawl prompt
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/references/step2b5-rc-handling.md: route hard-trigger and partition-split into inline partition prep then the single AskUserQuestion; drop the intermediate Split/Override/Cancel branch
  - From Cursor-Pragmatic: Extend the plan to update approval-gates-gate-b.md so Gate B size triggers use the same inline partition plus single-question contract as Step 2b.5
  - From Cursor-Requirements: Add `### UPDATED:` entries for those references (or a single shared pointer) so every size/sprawl entry routes directly into the unified inline Split-path single `AskUserQuestion`, with Override/Cancel handled there only.
  - From Cursor-dyn-Dependency Migration Auditor: Add skills/design/references/step2b5-rc-handling.md to firm UPDATED files. Route hard-trigger like partition-split: enter Split-path immediately; let the single decompose-panel question own partition, override, and cancel.


### FINDING_9: Publish-time oversize retains a separate decomposition prompt
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Step 5c/finalize still offers a standalone Decompose / Override / Cancel prompt for publish-time oversize refusal. This creates another partition gate after Gate C and bypasses the unified inline proposal flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Step 5c / finalize still offer Decompose / Override / Cancel on `PUBLISH_REFUSE_REASON=oversize-no-override|size-check-failed`. That is another partition gate after Gate C, so a run that reaches publish without earlier Split-path still gets a second decomposition UX and never reaches the inline proposal flow. Route Step 5c oversize refusal to the same unified Split-path (inline proposal + override + other-chat) and update `finalize-step5.md` accordingly; drop the standalone Decompose prompt there.


### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py:306-313
- **Concern**: [SCOPE-REDUCTION] The plan leaves `decompose prepare` free to add adjacent serial edges that the inline proposal did not declare. Scenario: Every accepted partition becomes a forced chain such as Piece 1 blocking Piece 2 blocking Piece 3, even when pieces are independent. This changes the proposed dependency scheme, prevents safe parallel work, and fails the requirement to express the optimal dependencies.
- **Proposed resolution**: Update the plan and `test_decompose.py` requirements so `prepare_partition_issues` emits only dependencies declared or derived by the inline proposal. Reject cyclic declared edges instead of silently dropping them, and remove test expectations that every partition receives an automatic serial chain.


### FINDING_6: Accepted Step 5c partitioning must terminate after final summary
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: If Step 5c accepts partitioning after a publish-time oversize result, the flow may continue ordinary publishing after filing, annotating, migrating dependencies, and closing the original issue. This conflicts with the approved-partition terminal behavior and risks targeting a closed or obsolete issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly that Step 5c Split-path acceptance exports SUMMARY_OUTCOME=approved-partition, runs the Final summary block, and exits 0 like Step 2b.5; only Override reruns design-step5c.sh.


### FINDING_7: Gate migrate-deps with session-backed live-mutation authorization
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The new `migrate-deps` path may mutate production dependency graphs directly without validating `LARCH_LIVE_MUTATION_OK`, unlike the session-gated issue-filing path. A replayed or harness temporary directory could therefore authorize unintended mutations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require migrate-deps_main to validate source-env.sh with check_live_mutation_auth before any dependency read or block-issue mutation, refuse with stable DECOMPOSE_DEPS_STATUS rows on denial, and add a test proving zero gh calls when unauthorized.


### FINDING_8: Ensure unrecoverable validation failure still presents exactly one question
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: If inline repair cannot produce a valid multi-piece acyclic proposal, the flow may terminate before presenting the required single partition question. That violates the requirement that every partition process offer partition, override, other, or chat choices through exactly one question.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define a terminal fallback that still emits exactly one AskUserQuestion when proposal validation cannot be repaired, or explicitly route the failure through one existing partition question before terminating; add a test for unrecoverable proposal validation failure


