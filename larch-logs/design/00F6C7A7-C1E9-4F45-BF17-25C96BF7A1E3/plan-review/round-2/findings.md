### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:17
- **Concern**: Step-2 hard-bail handoff has no concrete edit target; classify still reads only IMPLEMENT_BAIL_REASON while Step 2 §2.1.5 sets FINAL_BAIL_REASON. Scenario: After orchestrator-envelope-invalid or wrapper-validation-failure, Step 18a passes empty --bail-reason; the new Bail reason row renders none even though FAILURE_CLASS may be dispatch-failure
- **Proposed resolution**: Add an explicit ### UPDATED: skills/implement/references/stall-recovery.md (classify --bail-reason "${FINAL_BAIL_REASON:-${IMPLEMENT_BAIL_REASON:-}}") and matching skills/implement/SKILL.md §2.1.5/§2.2 bail bullets to set IMPLEMENT_BAIL_REASON from FINAL_BAIL_REASON or dispatcher REASON; do not persist via session-env (NEVER #12)

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-27; skills/implement/SKILL.md:616; skills/implement/references/stall-recovery.md:17
- **Concern**: Step-2 bail handoff has no named target file and does not mirror FINAL_BAIL_REASON into IMPLEMENT_BAIL_REASON. Scenario: Step 2 hard-bail sites set FINAL_BAIL_REASON (e.g. orchestrator-envelope-invalid at SKILL.md:616) but Step 18a classify passes --bail-reason "${IMPLEMENT_BAIL_REASON:-}"; without also setting IMPLEMENT_BAIL_REASON (and the same for dispatcher STATUS=bailed REASON=wrapper-validation-failure), the new Bail reason row stays none despite item 3
- **Proposed resolution**: Add ### UPDATED: skills/implement/SKILL.md (and only if needed a minimal STATUS=bailed REASON→IMPLEMENT_BAIL_REASON mirror at §2.2): at every Step-2 hard-bail that sets FINAL_BAIL_REASON and STALL_TRACKING=true, set IMPLEMENT_BAIL_REASON to the same allowlisted token; keep the harness Step-2 case asserting classify input via that variable path, not only a direct --bail-reason fixture seed

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:17 skills/implement/SKILL.md:616-633
- **Concern**: Step-2-to-18a handoff is vague and misaligned with live contracts: classify only gets --bail-reason "${IMPLEMENT_BAIL_REASON:-}" but §2.1.5 sets FINAL_BAIL_REASON without mirroring IMPLEMENT_BAIL_REASON; §2.2 has no STATUS=bailed bullet wiring dispatcher REASON (e.g. wrapper-validation-failure) into that channel. Scenario: Pre-Step-8 dispatch stalls can classify as dispatch-failure yet render Bail reason as none and classify with empty BAIL_REASON even when orchestrator-envelope-invalid or wrapper-validation-failure caused the bail
- **Proposed resolution**: Name concrete edits: skills/implement/SKILL.md mirror FINAL_BAIL_REASON into IMPLEMENT_BAIL_REASON on every Step-2 bail site (§2.1.5 plus a new STATUS=bailed bullet that sets both from REASON before Step 12d); skills/implement/references/stall-recovery.md classify argv use --bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"; keep renderer/harness --bail-reason fixtures as secondary coverage only

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/stall-recovery-report.sh:486-502; skills/implement/references/stall-recovery.md:17-21
- **Concern**: Plan routes Step-2 bail reason through classify while claiming reporting-only behavior. Scenario: The classifier includes bail_reason in evidence; passing orchestrator-envelope-invalid or wrapper-validation-failure can change FAILURE_CLASS from unrecoverable to dispatch-failure, which changes issue filing, retry policy, and possible dispatch flow
- **Proposed resolution**: Keep classification inputs behavior-stable; add the sanitized bail reason to the rendered classification/env after the existing class decision, or explicitly revise the plan to accept and test the behavior change rather than calling it reporting-only

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-27
- **Concern**: Step-2 hard-bail handoff names no concrete files. Scenario: The subsection only says "locate the real Step-2 hard-bail path" and "pass through --bail-reason / BAIL_REASON" but never names `skills/implement/references/stall-recovery.md` (classify uses `--bail-reason "${IMPLEMENT_BAIL_REASON:-}"` at line 17) or `skills/implement/SKILL.md` (§2.1.5 sets `FINAL_BAIL_REASON=orchestrator-envelope-invalid` at line 616, not `IMPLEMENT_BAIL_REASON`). Item 3 stays unimplementable without guessing which surface to edit.
- **Proposed resolution**: Name the minimum targets: e.g. `### UPDATED: skills/implement/references/stall-recovery.md` — coalesce in-memory bail into classify (`IMPLEMENT_BAIL_REASON`, `FINAL_BAIL_REASON`, and dispatcher `REASON` when `STATUS=bailed`); optionally `### UPDATED: skills/implement/SKILL.md` — on Step-2 hard-bail set the same token into the variable stall-recovery reads (or alias `IMPLEMENT_BAIL_REASON` from `FINAL_BAIL_REASON` / sanitized `REASON`).

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:17
- **Concern**: Plan handoff does not bridge `FINAL_BAIL_REASON` / dispatcher `REASON` to classify input. Scenario: Step 18a classify is invoked with `--bail-reason "${IMPLEMENT_BAIL_REASON:-}"` only. Envelope-invalid bails set `FINAL_BAIL_REASON` (SKILL.md:616); dispatcher `STATUS=bailed` exposes `REASON=wrapper-validation-failure` but neither is passed today — run logs show `--bail-reason ""` at classify. Renderer changes alone leave `Bail reason` as `none` for the dispatch-failure path this issue targets.
- **Proposed resolution**: In the handoff step, specify updating stall-recovery.md classify to pass a coalesced bail token (e.g. `IMPLEMENT_BAIL_REASON` then `FINAL_BAIL_REASON` then sanitized Step-2 `REASON`) and, if needed, a matching SKILL.md assignment when `STATUS=bailed` / §2.1.5 envelope-invalid fires so Step 18a receives an allowlisted token without widening the public enum.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:73-82
- **Concern**: Proposed "actual Step-2 bailed flow" harness may only re-test `--bail-reason` fixtures. Scenario: Existing harness already classifies via `--bail-reason` (e.g. case7b:157). A new case that only calls `classify --bail-reason orchestrator-envelope-invalid` duplicates renderer coverage and would not catch a missing stall-recovery.md / SKILL.md wiring fix.
- **Proposed resolution**: Scope the new harness to the handoff contract (e.g. simulate post-bail orchestrator state with `FINAL_BAIL_REASON` / `REASON` set and `IMPLEMENT_BAIL_REASON` empty, then assert classify input receives the token via the updated stall-recovery invocation), or drop the duplicate case if handoff is covered elsewhere.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-27
- **Concern**: Step-2 bail-reason handoff names no concrete files or durable persistence path. Scenario: Summary goal 3 and failure mode 4 require `orchestrator-envelope-invalid` / `wrapper-validation-failure` to reach `classify` before Step 18a, but today Step 2 sets `FINAL_BAIL_REASON` only (`skills/implement/SKILL.md:616`), Step 18a passes `--bail-reason "${IMPLEMENT_BAIL_REASON:-}"` (`skills/implement/references/stall-recovery.md:17`), `classify` falls back to `session-env.sh` `IMPLEMENT_BAIL_REASON` (`skills/implement/scripts/stall-recovery-report.sh:618-624`), and mid-run there is no sanctioned writer that persists Step-2 bail reasons (NEVER #12; `scripts/write-session-env.sh` has no `IMPLEMENT_BAIL_REASON` key). Renderer-only edits still emit `Bail reason | none` on the real dispatch-failure path.
- **Proposed resolution**: Name the minimal touch points: e.g. `skills/implement/SKILL.md` §2.1.5/§2.2 set `IMPLEMENT_BAIL_REASON` alongside `FINAL_BAIL_REASON` for envelope and dispatcher `STATUS=bailed` reasons; Step 18a preamble rehydrates `IMPLEMENT_BAIL_REASON` from `session-env.sh`; add one sanctioned persist step (smallest: key-rewrite `IMPLEMENT_BAIL_REASON`+`STALL_TRACKING` into `session-env.sh` via an existing allowed writer, or pre-18a `ship-pr-state.sh` `BAIL_REASON`) before `classify`; point the promised Step-2 harness case at that contract.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:616; skills/implement/references/stall-recovery.md:17; skills/implement/scripts/test-stall-recovery-report.sh:427-462
- **Concern**: The plan’s real Step-2 propagation test is aimed at the helper harness, but the Step-2 to Step-18a handoff lives in prompt/reference text.. Scenario: The renderer and classify fixtures can pass while the real Step 18a classify invocation still passes only ${IMPLEMENT_BAIL_REASON:-}, dropping Step 2’s FINAL_BAIL_REASON for orchestrator-envelope-invalid or wrapper-validation-failure.
- **Proposed resolution**: Add an explicit SKILL.md/stall-recovery.md handoff change and pin it in scripts/test-implement-structure.sh or an equivalent prompt-contract test; keep test-stall-recovery-report.sh for helper rendering/classify coverage.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-scope-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-27
- **Concern**: The Step-2→Step-18a handoff block has no `### UPDATED:` path and is missing from `scout-plan-scope-files.txt`; orchestration lives in `skills/implement/SKILL.md` and `skills/implement/references/stall-recovery.md`, not in the five scoped helper/doc files.. Scenario: Step 2 §2.1.5 sets `FINAL_BAIL_REASON` and routes to Step 12d (`skills/implement/SKILL.md:616`), but Step 18a classify consumes `--bail-reason "${IMPLEMENT_BAIL_REASON:-}"` (`skills/implement/references/stall-recovery.md:17`; `stall-recovery-report.sh:578-624`). With only renderer/allowlist edits, envelope/wrapper-validation hard-bails can still reach Step 18a with an empty bail channel and render `Bail reason` as `none`.
- **Proposed resolution**: Add `### UPDATED: skills/implement/SKILL.md` (minimum): at Step-2 hard-bail and `STATUS=bailed` Step-12d routing, set `IMPLEMENT_BAIL_REASON` from dispatcher `REASON` or `FINAL_BAIL_REASON` before Step 18a; include `skills/implement/SKILL.md` in scope-files. Only touch `skills/implement/references/stall-recovery.md` if the Step 18a classify invocation prose must change.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-scope-gap
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:603-616,1253-1285; skills/implement/references/stall-recovery.md:17; skills/implement/scripts/step2-implement.sh:682-690,719-727
- **Concern**: The plan names a Step-2 hard-bail handoff but omits the actual orchestration files from the scope list. Step 2 synthesizes or receives REASON/FINAL_BAIL_REASON in SKILL.md, wrapper-validation-failure originates in step2-implement.sh, and Step 18a classify currently passes only IMPLEMENT_BAIL_REASON via stall-recovery.md. The scope-files list contains only stall-recovery-report.sh, its allowlist/doc, SECURITY.md, and test-stall-recovery-report.sh.. Scenario: A wrapper-validation or envelope-invalid Step 2 bail can still reach Step 18a with IMPLEMENT_BAIL_REASON empty, so classify emits empty BAIL_REASON and the new report row renders none for the real failure path.
- **Proposed resolution**: Add the real handoff files to Files-to-modify/scope-files, minimally skills/implement/SKILL.md and skills/implement/references/stall-recovery.md, and specify how Step 2’s existing REASON/FINAL_BAIL_REASON becomes the --bail-reason value before Step 18a classify. Only include step2-implement.sh if the dispatcher-emitted wrapper-validation REASON itself must change.
