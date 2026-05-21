```text
### FINDING_1: Phase4 umbrella intro contradicts step12 push story
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Umbrella Phase 4 framing says the rebase completed locally in a way that can imply Step 12 Phase 4 has not pushed yet, conflicting with the step12_phase4 subsection that describes a full continue path that is already pushed.
- **Suggested revision**: Reword the umbrella Phase 4 intro to explicitly separate step12 pushed outcomes from step8b local-only continuation, or drop ambiguous “local” wording from the umbrella layer.

### FINDING_2: Overlong single-line bullets hurt maintainability
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Very long single-line bullets in the referenced docs are harder to edit safely and more error-prone during conflict edits.
- **Suggested revision**: Split dense bullets into sub-bullets (similar to the early_rebase style) without changing semantics.

### FINDING_3: [OUT_OF_SCOPE] Step 6e “already pushed” wording overstates skip-push paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 6e bump/push-state wording can read as “already pushed” even when a step8 skip-push path applies, overstating remote push guarantees.
- **Suggested revision**: Refactor step 6e wording in a later change; treat as pre-existing scope drift rather than blocking this thread.

### FINDING_4: rebase_already_done=true is documented as universally post-push
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cross-doc-consistency-output.txt, dyn-caller-kind-contract-output.txt
- **Concern**: Inputs still describe rebase_already_done=true as skipping steps 1–2 because the rebase was completed and pushed by the caller (often anchored to step12_phase4), but caller_kind=step8b_rebase can re-enter after conflict-resolution Phase 4 local --continue --no-push --keep-on-conflict with no Phase 4 push, misleading orchestrators about push ownership before later steps (postbump/force-push/freshness gates).
- **Suggested revision**: Qualify semantics by caller_kind: pushed for step12_phase4-style handoffs vs local-only complete for step8b_rebase Phase 4 re-entry; prefer neutral “finished locally” language plus explicit push vs no-push ownership.

### FINDING_5: CONFLICT_FILES can go stale across Phase 4 exit-1 loopbacks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Phase 1 guidance that pins CONFLICT_FILES to an earlier sub-procedure step 2 stdout can mis-target later conflicts after a multi-hop rebase (--continue then conflict again), because a second conflict needs a fresh path set.
- **Suggested revision**: Document re-capture from the latest rebase-push.sh --continue --no-push --keep-on-conflict stdout on each Phase 4 exit-1 iteration (and/or an explicit unmerged-path enumeration fallback); align any early_rebase wording similarly.

### FINDING_6: Step 7 provenance omits step8b_rebase Phase 4 exit-0 re-entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cross-doc-consistency-output.txt, dyn-caller-kind-contract-output.txt
- **Concern**: The step 7 return-row narrative for step8b_rebase still reads like it applies only to Step 8b’s initial rebase-push.sh --no-push exit-1 dispatch, omitting the second legitimate lifetime: re-dispatch after conflict-resolution.md Phase 4 exit 0 with rebase_already_done=true.
- **Suggested revision**: Extend the step8b_rebase step 7 bullet to explicitly include the Phase 4 exit-0 re-entry handoff so provenance matches the Phase 4 caller subsection and conflict-resolution.md.

### FINDING_7: [OUT_OF_SCOPE] DROPPED=false warning references Phase 1–3 routing drift
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-existing DROPPED=false warning text still describes Phase 1–3 routing even when the step8b path skips Phase 3, creating minor terminology drift.
- **Suggested revision**: Optional follow-up doc hygiene; no PR-blocking requirement unless that line is being edited for other reasons.

### FINDING_8: New step8b_rebase / Phase 1–4 behavior is not CI-pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Documentation introduces step8b_rebase --keep-on-conflict and Phase 1–4 dispatch without an automated guard, so future edits could drop flags while scripts/test-implement-rebase-macro.sh (H) still passes and step8b can stall again; separately, expanded conflict-resolution contracts can drift from the sub-procedure without CI failure.
- **Suggested revision**: Add grep-based structural tests and/or agent-lint pins for the normative step8b_rebase invocation shape and for shared invariant strings across conflict-resolution.md and rebase-rebump-subprocedure.md.

### FINDING_9: [OUT_OF_SCOPE] Macro test (H) header comment is outdated about flags
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The test header comment still implies the sub-procedure story is --no-push alone, which can mislead maintainers updating rebase flags.
- **Suggested revision**: Update the comment on a future edit to the test file; treat as non-blocking hygiene outside the core doc contract edits.

### FINDING_10: Top-of-file Consumer/When-to-load diverges from inner step2 flag story
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cross-doc-consistency-output.txt
- **Concern**: Consumer/When-to-load anchors Step 8b on plain --no-push while Phase 1–4 conflict work is tied to sub-procedure step 2’s --no-push --keep-on-conflict; Inputs phrasing can be read as applying to the outer Step 8b invocation, inviting mis-ordered gates relative to conflict-resolution.md.
- **Suggested revision**: Add an explicit cross-reference under Consumer/When-to-load clarifying which invocation owns --keep-on-conflict, that conflict-resolution.md loads for that exit-1 shape, and how it differs from the outer Step 8b entry semantics.

### FINDING_11: Redundant explicit git rebase --abort in Phase 1–4 bail text
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Phase 1–4 bail prose duplicates conflict-resolution.md’s global bail invariant, which can confuse ownership/ordering (“double abort” mental model).
- **Suggested revision**: Prefer pointing to conflict-resolution.md bail paths and remove redundant abort ordering from the sub-procedure unless it adds non-duplicative constraints.

### FINDING_12: [OUT_OF_SCOPE] conflict-resolution intro overgeneralizes reviewer panel gating
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Intro prose can read like the reviewer panel always applies on exit 1 even when caller families skip Phase 3.
- **Suggested revision**: Tighten intro to reference caller families / Phase 3 gating; treat as minor pre-existing imprecision unless editing that section anyway.

### FINDING_13: [OUT_OF_SCOPE] SKILL.md token naming diverges from sub-procedure vocabulary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: skills/implement/SKILL.md uses step8b_same_version style naming that diverges from sub-procedure tokens, risking cross-file orchestrator confusion.
- **Suggested revision**: SKILL-only follow-up alignment; explicitly out of scope for the referenced two-doc threading change.

### FINDING_14: [OUT_OF_SCOPE] Historical CHANGELOG text may contradict current references
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Older changelog entries can make readers briefly think step8b behavior is unchanged versus the updated reference docs.
- **Suggested revision**: Accept as historical or add a separate changelog note in a later change if cross-time clarity matters.

### FINDING_15: [OUT_OF_SCOPE] Run artifacts widen scope vs stated “two markdown files only” framing
- **Reviewer(s)**: dyn-caller-kind-contract-output.txt
- **Concern**: Branch history includes added larch-logs/implement/... material beyond a narrow “two files only” scope narrative in planning text.
- **Suggested revision**: Reconcile scope documentation/process expectations separately; not a caller_kind threading defect.

### FINDING_16: [OUT_OF_SCOPE] Doc-only lifecycle vs executable enforcement gap
- **Reviewer(s)**: dyn-caller-kind-contract-output.txt
- **Concern**: The documented lifecycle assumes orchestrators adopt sub-procedure step 2’s --no-push --keep-on-conflict for step8b_rebase, but this diff’s verification surface is documentation-first relative to SKILL.md/shell helpers.
- **Suggested revision**: Track as follow-up automation/testing alignment (overlaps FINDING_8’s direction) rather than a contradiction inside the markdown handoff alone.
```
