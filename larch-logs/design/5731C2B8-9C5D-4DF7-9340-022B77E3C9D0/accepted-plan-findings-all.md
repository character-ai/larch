### FINDING_1: Legacy assessment aliases are not normalized before the frozen adapter call
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Step8 Trust Boundary
- **Severity**: major
- **Concern**: The legacy `invariants-assessment` and `guidelines-assessment` route-exit handoffs do not satisfy the adapter’s required `NEXT_ACTION=assessments` plus non-empty kind-list contract. Invoking the unchanged adapter on those handoffs can fail before the bgjob starts, breaking the required compatibility routes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit `skills/implement/SKILL.md` step: for legacy alias branches, rewrite `.ship-route-exit-handoff.env` to `NEXT_ACTION=assessments` and `DETAIL=invariants` or `DETAIL=guidelines` (infer from alias when `DETAIL` is absent) immediately before the single `step-8-assessment.sh` fence; pin this mapping in `test-architectural-guidelines-step.sh`.
  - From Cursor-Innovation: In skills/implement/SKILL.md pin a pre-adapter normalization step for all three branches: rewrite handoff to NEXT_ACTION=assessments and set DETAIL to the single kind (invariants or guidelines) when absent; preserve other handoff keys; then invoke the adapter once.
  - From Codex-Innovation: Specify and implement one concrete normalization mechanism. Either allow `step-8-assessment.sh` to accept and canonicalize the two legacy handoffs, or add a documented non-inline normalization helper that produces the combined `assessments` handoff before invoking the adapter. Add an execution test proving both aliases reach the adapter with the correct requested kinds.
  - From Cursor-Pragmatic: In SKILL.md pin a pre-adapter normalization step for all three branches: rewrite .ship-route-exit-handoff.env to NEXT_ACTION=assessments, set DETAIL to the canonical kind list (invariants for invariants-assessment, guidelines for guidelines-assessment, existing DETAIL/DETAIL_FILE for assessments), preserve other handoff keys, then invoke step-8-assessment.sh once. Assert this in test-architectural-guidelines-step.sh.
  - From Codex-Pragmatic: Add the minimal adapter change and focused tests needed to map each legacy action to NEXT_ACTION=assessments with its single requested kind before normal validation. Remove the conflicting scope control that forbids changing step-8-assessment.sh.
  - From Cursor-Requirements: In each legacy alias branch, rewrite .ship-route-exit-handoff.env to NEXT_ACTION=assessments and set DETAIL to the single kind (invariants or guidelines) before the one step-8-assessment.sh fence; pin this in SKILL.md, both present references, ship-pr-exit-matrix.md, and test-architectural-guidelines-step.sh.
  - From Cursor-dyn-Step8 Trust Boundary: In `skills/implement/SKILL.md`, require all three branches to rewrite `.ship-route-exit-handoff.env` to `NEXT_ACTION=assessments` plus `DETAIL=invariants`, `DETAIL=guidelines`, or the combined list (synthesizing `DETAIL` when legacy payloads omit it) immediately before the single `step-8-assessment.sh` fence; pin the same rule in `ship-pr-exit-matrix.md` and the rewritten present references.


### FINDING_3: Failed or incomplete adapter results need an explicit terminal tool-failure route
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Step8 Trust Boundary
- **Severity**: major
- **Concern**: The plan does not define the terminal orchestrator branch for adapter exit errors, `fail-closed` status, stale identity, non-zero `BGJOB_RC`, incomplete results, or other validation failures. Without an explicit route, the orchestrator could relaunch ship, retry incorrectly, or improvise inline recovery. Identical-fence repetition must remain limited to Bash-tool timeout re-entry while the adapter job is still live.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After the adapter fence, fail closed on any missing/mismatched KV, non-zero adapter exit (except Bash-tool timeout rejoin), or `ASSESSMENT_STATUS` other than `complete`; route to the existing `tool-failure` branch with no ship relaunch and no inline fallback; document `ASSESSMENT_STATUS=fail-closed` and `ASSESSMENT_ERROR=active-stale-identity-mismatch` explicitly.
  - From Cursor-Innovation: Omit ship relaunch on any failed validation including fail-closed; route to the existing post-driver tool-failure branch (append Tool Failures, hard stop, no Step 18 stall rename) and pin that in SKILL.md and ship-pr-exit-matrix.md.
  - From Cursor-Pragmatic: After failed validation (non-zero adapter rc, ASSESSMENT_STATUS!=complete, BGJOB_RC!=0, kind mismatch, or incomplete ASSESSMENT_RESULTS), route to existing Step 8 tool-failure handling with no step-8-ship.sh relaunch and no inline fallback.
  - From Cursor-Requirements: After adapter return, when ASSESSMENT_STATUS is not complete, identity or coverage checks fail, or BGJOB_RC is non-zero without a validated complete envelope, route to the existing tool-failure branch (append Tool Failures, stop hard, no ship relaunch); pin this beside the validation KV list in SKILL.md and ship-pr-exit-matrix.md.
  - From Cursor-dyn-Step8 Trust Boundary: The plan mandates repeating the identical adapter fence only on Bash-tool timeout (live rejoin). The adapter also exits 0 with `ASSESSMENT_STATUS=fail-closed` or exits 2 with `ASSESSMENT_ERROR=active-stale-identity-mismatch` without starting replacement work. Without an explicit non-relaunch terminal route, the orchestrator may loop retries, relaunch ship, or treat non-zero wrapper exit like a timeout rejoin. In `skills/implement/SKILL.md`, after validation: on `ASSESSMENT_STATUS=fail-closed`, adapter exit 2, or any failed validation, route `tool-failure` (append Tool Failures, no `step-8-ship.sh` relaunch); reserve identical-fence repetition solely for Bash-tool timeout while the adapter bgjob remains live; pin negative routing in `test-architectural-guidelines-step.sh`.


### FINDING_4: Reassessment documentation still describes unconditional HEAD-based refresh
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: minor
- **Concern**: Existing Step 7a/Step 8 prose and matching tests still claim assessments refresh after every `HEAD` change, contradicting the scoped once-per-run reassessment semantics and docs-only reuse path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace that sentence with scoped reassessment semantics (fingerprinted once-per-run coverage, pre-filter reuse, reassess only on new scope intersection) in `SKILL.md` and update the matching assertion in `test-architectural-guidelines-step.sh`.
  - From Cursor-Requirements: Replace that breadcrumb with scoped reassessment wording (deterministic pre-filter reuse; bgjob re-authorship only on new scope intersection) and update the harness assertion accordingly.


### FINDING_5: Durable references and security guidance must remove contradictory inline-authorship descriptions
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Step8 Trust Boundary
- **Severity**: major
- **Concern**: Durable handoff, present-reference, and SECURITY.md prose can continue to describe main-agent diff reading, prompt-side staging, materialized-diff consumption, or per-kind authorship after the delegated adapter route is activated. This creates contradictory guidance and preserves an inline-authorship escape hatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite the `assessments`/alias handoff paragraph to state all three tokens delegate through `step-8-assessment.sh`, validate adapter KVs, then relaunch ship once; remove materialized-diff reading and per-kind writer/relaunch wording.
  - From Cursor-Pragmatic: Revise the line 34 paragraph (or add an explicit supersession pointer) so it matches delegated bgjob authoring, untrusted evidence, and strict pre-ship validation in the new section.
  - From Cursor-Pragmatic: Explicitly prohibit loading architectural-invariants-present.md and architectural-guidelines-present.md on assessment branches; route only through step-8-assessment.sh. Add negative assertions in test-architectural-guidelines-step.sh.
  - From Cursor-dyn-Step8 Trust Boundary: In the `SECURITY.md` update, revise the existing `ARCHITECTURAL_INVARIANTS.md` / `ARCHITECTURAL_GUIDELINES.md` paragraph to describe adapter-delegated Step 8 assessment, untrusted evidence, strict KV validation before consumption, and redacted diagnostics; cross-link the new Step 8 trust-boundary section.


### FINDING_1: Update fence-shape tests for the adapter-only Step 8 flow
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan updates plan/fence counts but does not remove legacy compose-write ordering assertions. The harness may still require per-kind compose writers and a guidelines-only relaunch, causing the approved adapter-only Step 8 flow to fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `scripts/test-implement-fence-shape.sh` plan item to replace those slices with adapter-first checks: one `step-8-assessment.sh` launcher through `implement-run-$PPID.sh`, no prompt-side assessment start/wait pair, and exactly one post-validation `step-8-ship.sh` relaunch


