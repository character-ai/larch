### FINDING_2: Step 3 preview contract still lives in the wrong slice
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Prompt Slice Contract, Codex-dyn-Prompt Slice Contract
- **Severity**: major
- **Concern**: The Step 3 preview and post-driver references still depend on `plan-review.md` / Gate C content, while `plan-review-runtime.md` does not fully own the runtime preview contract or the residual cross-refs. That can keep the hot path eager or leave preview rules undefined after the split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: "Add an explicit plan-review-runtime section for Step 3 entry preview: default --variant step3, ## Plan Candidate for Review header, threshold note behavior, and operator show full plan before voting. Split Gate C-only See full plan / render-gate re-fire text into approval-gates-gate-c.md only."
  - From Cursor-Pragmatic: "Copy the Step 3-only When to load contract and do-not-load step list into plan-review-runtime.md; demote plan-review.md to editing-only with a pointer to the runtime file."
  - From Cursor-Pragmatic: "Update the State invariants bullet to cite plan-review-runtime.md (or the shared core load matrix) when rewriting approval-gates.md."
  - From Cursor-Requirements: "Move the plan-review-runtime MANDATORY READ to immediately after design-step3-entry.sh and before the pre-voting preview block; relocate the Step 3 large-plan summary / plan-review preview contract into plan-review-runtime.md; retarget line 376 to that runtime file (or inline preview-only rules that do not require any approval-gates slice)."
  - From Cursor-Requirements: "Retarget those references to plan-review-runtime.md (or split runtime vs maintainer cross-refs explicitly) and pin the strings in test-design-structure.sh."
  - From Codex-Requirements: "Move the Step 3 pre-voting preview and large-plan-summary contract into plan-review-runtime.md, and update SKILL.md so that slice is read before the preview or the preview line points to an already-loaded runtime authority."
  - From Cursor-dyn-Prompt Slice Contract: "Extend the SKILL.md sweep: post-loop interpretation and any Step 3 MAV/self-review branches must read or follow `plan-review-runtime.md`, not `plan-review.md`"
  - From Cursor-dyn-Prompt Slice Contract: "Move Step 3 large-plan/preview summary-mode contract into plan-review-runtime.md (or shared core with an explicit Step 3 load pointer) and update line 376 to cite that file instead of Gate C"
  - From Cursor-dyn-Prompt Slice Contract: "Gate A/B/C shared core should reference `plan-review-runtime.md` for runtime cumulation semantics (or duplicate the minimal invariant text in core); include this file in the cross-reference sweep"
  - From Codex-dyn-Prompt Slice Contract: "Move the large-plan summary contract out of approval-gates.md into a Step 3-only slice or plan-review-runtime.md, then retarget the Step 3 preview note and tests to that new owner."


### FINDING_4: Gate slice split still leaves stale anchors and skip-if-loaded holes
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Prompt Slice Contract
- **Severity**: major
- **Concern**: The approval-gates split is only partially wired through SKILL and the harness: monolith anchors and grep pins remain, and the Step 3.5 / 4b skip-if-loaded wording can suppress the new gate slices.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Retarget SKILL citations to approval-gates.md core plus approval-gates-gate-b.md for Gate B-only sections. Mirror the new paths in scripts/test-design-structure.sh settle and Gate B pins currently aimed at APPROVAL_GATES_MD"
  - From Cursor-Arch: "Extend the harness migration checklist: retarget line 473 and 644 to plan-review-runtime.md, split Gate A/B/C contains to the new slice variables, and keep negative monolith-eager-load checks for Step 3, Gate B/C, and Step 5 entry"
  - From Cursor-Pragmatic: "Extend test-design-structure.sh with APPROVAL_GATES_GATE_A/B/C_MD variables; migrate each gate-specific contains/assert to the owning slice; keep shared-core checks on approval-gates.md; update the settle-rc-dispatch caller loop to include the Gate B slice file."
  - From Cursor-Requirements: "Gate-specific structure pins still target the approval-gates.md monolith variable... Split variables per slice and move each gate-specific assertion to the correct file."
  - From Cursor-dyn-Prompt Slice Contract: "Always MANDATORY READ `approval-gates-gate-b.md` at Step 3.5; apply skip-if-loaded only to shared core (or drop it), and retarget §Gate B / Shared post-apply prose to core plus gate-b paths"
  - From Cursor-dyn-Prompt Slice Contract: "Require an unconditional MANDATORY READ of `approval-gates-gate-c.md` at Step 4b; limit any skip-if-loaded qualifier to shared core only, and point Gate C body execution at the gate-c slice"


### FINDING_5: Validation updates are still optional
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-Prompt Slice Contract
- **Severity**: major
- **Concern**: The testing plan leaves split-sensitive pytest regressions and heatmap evidence optional, so CI can pass without checking the files most likely to break or without proving the token-reduction result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: "Promote the affected pytest files from MAY_UPDATE to UPDATED and add a focused pytest command for the changed tests to the testing strategy."
  - From Cursor-dyn-Prompt Slice Contract: "Promote to a firm `### UPDATED:` deliverable: expect `plan-review-runtime.md` in eager closure, `plan-review.md` absent or conditional, and regenerate `python/skill-closure-baseline.json` accordingly"
  - From Codex-Requirements: "Make measure-references-heatmap a required validation when transcript-bearing samples are available, and require recording the fallback reason if no fresh sample exists."


### FINDING_1: Finalize failure-slice wiring is incomplete
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The split moves auto error reporting into a failure-only slice, but the SKILL update still leaves early terminal exits and the Final summary path able to run without loading that normative teardown contract. That can mis-stage failure handling or keep treating the green finalize file as the authority on pre-Step-5 exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: `Extend the SKILL.md update list beyond Step 5 entry: retarget line 189 to \`finalize-step5-failures.md\`; add a conditional MANDATORY READ of \`finalize-step5-failures.md\` immediately before any \`failed-*\` staging and before the Final summary block (clarify, Split-path, Step 3 \`final-summary:*\`, Step 5c non-zero abort routing); keep green \`finalize-step5.md\` limited to Step 5 happy-path 5b/5b.5/5c/5d. Pin those load triggers and moved auto-error-reporting needles in \`scripts/test-design-structure.sh\`.`
  - From Cursor-Requirements: `Add explicit SKILL bullets: retarget line 189 to finalize-step5-failures.md; MANDATORY READ the failures slice immediately before any failed-* SUMMARY_OUTCOME Final summary launch and before Step 5c _publish_rc abort/staging; extend finalize-step5-failures.md When to load with that exit list; pin anchor retarget and at least one pre-Step-5 failure-path read in scripts/test-design-structure.sh.`


### FINDING_2: Gate A default-path guard is untested in the structure harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The plan intends Gate A to stay off the common path, but the structure harness does not add a negative assertion that the Gate A slice is absent outside the re-entry path. A regression could reintroduce Gate A on default runs while the baseline still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `Add not_contains checks that SKILL.md lacks approval-gates-gate-a.md outside Step 1e Gate A re-entry; keep Gate A render-gate contains probes on APPROVAL_GATES_GATE_A_MD only.`


### FINDING_3: Step 3 preview runs before the new runtime slice can load
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The Step 3 runtime read is ordered too late relative to a wrapper that already emits the preview. If the preview wrapper fires before the runtime slice is loaded, the accepted Step 3 preview-ownership fix remains incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: `Either read \`plan-review-runtime.md\` before launching \`design-step3-entry.sh\`, or add firm updates to split/move \`design-step3-entry-preview.sh\` so \`SKILL.md\` reads the runtime slice before invoking the preview wrapper, with matching script-doc and structure-test pins.`


