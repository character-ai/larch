# Review Round 1

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Phase4 umbrella intro contradicts step12 push story
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Umbrella Phase 4 framing says the rebase completed locally in a way that can imply Step 12 Phase 4 has not pushed yet, conflicting with the step12_phase4 subsection that describes a full continue path that is already pushed.
- **Suggested revision**: Reword the umbrella Phase 4 intro to explicitly separate step12 pushed outcomes from step8b local-only continuation, or drop ambiguous “local” wording from the umbrella layer.


### FINDING_10: Top-of-file Consumer/When-to-load diverges from inner step2 flag story
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cross-doc-consistency-output.txt
- **Concern**: Consumer/When-to-load anchors Step 8b on plain --no-push while Phase 1–4 conflict work is tied to sub-procedure step 2’s --no-push --keep-on-conflict; Inputs phrasing can be read as applying to the outer Step 8b invocation, inviting mis-ordered gates relative to conflict-resolution.md.
- **Suggested revision**: Add an explicit cross-reference under Consumer/When-to-load clarifying which invocation owns --keep-on-conflict, that conflict-resolution.md loads for that exit-1 shape, and how it differs from the outer Step 8b entry semantics.


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


### FINDING_8: New step8b_rebase / Phase 1–4 behavior is not CI-pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Documentation introduces step8b_rebase --keep-on-conflict and Phase 1–4 dispatch without an automated guard, so future edits could drop flags while scripts/test-implement-rebase-macro.sh (H) still passes and step8b can stall again; separately, expanded conflict-resolution contracts can drift from the sub-procedure without CI failure.
- **Suggested revision**: Add grep-based structural tests and/or agent-lint pins for the normative step8b_rebase invocation shape and for shared invariant strings across conflict-resolution.md and rebase-rebump-subprocedure.md.


