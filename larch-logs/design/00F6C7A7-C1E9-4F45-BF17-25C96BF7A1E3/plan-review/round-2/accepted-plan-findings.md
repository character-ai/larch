### FINDING_1: Step-2 bail reason handoff is underspecified and can drop real bail reasons
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-scope-gap, Codex-dyn-scope-gap
- **Severity**: important
- **Concern**: The plan does not concretely wire Step-2 hard-bail reasons from `FINAL_BAIL_REASON` / dispatcher `REASON` into the Step-18a `classify --bail-reason` path, and several reviewers note that the actual orchestration files are missing or unnamed. As a result, real `orchestrator-envelope-invalid` / `wrapper-validation-failure` bails can still classify/render with an empty bail reason even if renderer/allowlist fixtures pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit ### UPDATED: skills/implement/references/stall-recovery.md (classify --bail-reason "${FINAL_BAIL_REASON:-${IMPLEMENT_BAIL_REASON:-}}") and matching skills/implement/SKILL.md §2.1.5/§2.2 bail bullets to set IMPLEMENT_BAIL_REASON from FINAL_BAIL_REASON or dispatcher REASON; do not persist via session-env (NEVER #12)
  - From Cursor-Edge: Add ### UPDATED: skills/implement/SKILL.md (and only if needed a minimal STATUS=bailed REASON→IMPLEMENT_BAIL_REASON mirror at §2.2): at every Step-2 hard-bail that sets FINAL_BAIL_REASON and STALL_TRACKING=true, set IMPLEMENT_BAIL_REASON to the same allowlisted token; keep the harness Step-2 case asserting classify input via that variable path, not only a direct --bail-reason fixture seed
  - From Cursor-Innovation: Name concrete edits: skills/implement/SKILL.md mirror FINAL_BAIL_REASON into IMPLEMENT_BAIL_REASON on every Step-2 bail site (§2.1.5 plus a new STATUS=bailed bullet that sets both from REASON before Step 12d); skills/implement/references/stall-recovery.md classify argv use --bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"; keep renderer/harness --bail-reason fixtures as secondary coverage only
  - From Cursor-Pragmatic: Name the minimum targets: e.g. `### UPDATED: skills/implement/references/stall-recovery.md` — coalesce in-memory bail into classify (`IMPLEMENT_BAIL_REASON`, `FINAL_BAIL_REASON`, and dispatcher `REASON` when `STATUS=bailed`); optionally `### UPDATED: skills/implement/SKILL.md` — on Step-2 hard-bail set the same token into the variable stall-recovery reads (or alias `IMPLEMENT_BAIL_REASON` from `FINAL_BAIL_REASON` / sanitized `REASON`).
  - From Cursor-Pragmatic: In the handoff step, specify updating stall-recovery.md classify to pass a coalesced bail token (e.g. `IMPLEMENT_BAIL_REASON` then `FINAL_BAIL_REASON` then sanitized Step-2 `REASON`) and, if needed, a matching SKILL.md assignment when `STATUS=bailed` / §2.1.5 envelope-invalid fires so Step 18a receives an allowlisted token without widening the public enum.
  - From Cursor-Requirements: Name the minimal touch points: e.g. `skills/implement/SKILL.md` §2.1.5/§2.2 set `IMPLEMENT_BAIL_REASON` alongside `FINAL_BAIL_REASON` for envelope and dispatcher `STATUS=bailed` reasons; Step 18a preamble rehydrates `IMPLEMENT_BAIL_REASON` from `session-env.sh`; add one sanctioned persist step (smallest: key-rewrite `IMPLEMENT_BAIL_REASON`+`STALL_TRACKING` into `session-env.sh` via an existing allowed writer, or pre-18a `ship-pr-state.sh` `BAIL_REASON`) before `classify`; point the promised Step-2 harness case at that contract.
  - From Codex-Requirements: Add an explicit SKILL.md/stall-recovery.md handoff change and pin it in scripts/test-implement-structure.sh or an equivalent prompt-contract test; keep test-stall-recovery-report.sh for helper rendering/classify coverage.
  - From Cursor-dyn-scope-gap: Add `### UPDATED: skills/implement/SKILL.md` (minimum): at Step-2 hard-bail and `STATUS=bailed` Step-12d routing, set `IMPLEMENT_BAIL_REASON` from dispatcher `REASON` or `FINAL_BAIL_REASON` before Step 18a; include `skills/implement/SKILL.md` in scope-files. Only touch `skills/implement/references/stall-recovery.md` if the Step 18a classify invocation prose must change.
  - From Codex-dyn-scope-gap: Add the real handoff files to Files-to-modify/scope-files, minimally skills/implement/SKILL.md and skills/implement/references/stall-recovery.md, and specify how Step 2’s existing REASON/FINAL_BAIL_REASON becomes the --bail-reason value before Step 18a classify. Only include step2-implement.sh if the dispatcher-emitted wrapper-validation REASON itself must change.


### FINDING_2: Bail reason input may change classification behavior despite reporting-only framing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan routes Step-2 bail reason through classifier evidence while describing the change as reporting-only. Because `bail_reason` can influence `FAILURE_CLASS`, the change may affect issue filing, retry policy, or dispatch flow rather than only adding a rendered report row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep classification inputs behavior-stable; add the sanitized bail reason to the rendered classification/env after the existing class decision, or explicitly revise the plan to accept and test the behavior change rather than calling it reporting-only


### FINDING_3: Proposed harness may duplicate fixture coverage instead of testing the real handoff
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Concern**: A new “actual Step-2 bailed flow” test that directly calls `classify --bail-reason ...` would only duplicate existing helper/renderer fixture coverage and would not catch missing `SKILL.md` / `stall-recovery.md` handoff wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Scope the new harness to the handoff contract (e.g. simulate post-bail orchestrator state with `FINAL_BAIL_REASON` / `REASON` set and `IMPLEMENT_BAIL_REASON` empty, then assert classify input receives the token via the updated stall-recovery invocation), or drop the duplicate case if handoff is covered elsewhere.

