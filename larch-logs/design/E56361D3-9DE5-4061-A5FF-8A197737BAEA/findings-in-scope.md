### FINDING_1: finalize-step5.md reference header not updated for relocated auto-error-reporting prose
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Appending run-wide `/design auto error reporting` prose without updating the reference triplet leaves **Consumer** / **Contract** / **When-to-load** scoped to Step 5 finalization only, while the moved section documents Final-summary and teardown behavior from Step 0 onward (`failure-report`, sentinel precedence, `stage-terminal-state`, panel-degradation taxonomy). Progressive-disclosure readers and maintainers can treat the file as Step-5-only and miss run-wide failure-path semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the same edit, extend **Contract** (and **When to load** if needed) to include the appended auto-error-reporting section; keep the Step 5 mandatory-read hook unchanged.

### FINDING_2: Dangling "Completion sentinels" cross-reference after folded-contract removal
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan removes the always-loaded **Folded contract**, **Tradeoff**, and pause/resume coverage block (~lines 67–72) but Phase 7 exception prose (~line 61) still says absorbed sentinels are folded into adjacent hosts "(see **Completion sentinels** below)". After deletion, SKILL.md retains a broken anchor with no **Completion sentinels** section, misdirecting orchestrators tracing absorbed 1c/1d/1e sentinel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the removed block with a one-line stub such as "**Completion sentinels for pause/resume.** Maintainer contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sentinel-host-table.md`." and keep the existing maintainer-only load rule on the following line.
  - From Cursor-Innovation: In the SKILL.md edit list, drop the see **Completion sentinels** below clause from the Phase 7 exception sentence (line 61 already ends with the sentinel-host-table pointer for Step 1d.7).
  - From Cursor-Pragmatic: In the SKILL.md edit list, retarget line 61 to `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sentinel-host-table.md` (new `## Folded contract and tradeoff` section) and expand the existing maintainer pointer (~74) to mention that section, not only the host table.

### FINDING_3: Auto-error-reporting relocation omits operator-action, cancelled-*, and terminal-state writer contracts
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Relocating `### /design auto error reporting` out of always-loaded SKILL.md without carrying the full teardown contract drops the operator-action / cancelled-* branch (required `design-failure-operator-action.env`, `design-failure-operator-action-chat.md`, run-log audit), report-gate precedence, and the `stall-recovery validate-token` / `validate-terminal-state` hard-halt writer checks. Non-Step-5 failure and cancel paths would lose documented requirements even though verbs still own the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Carry the operator-action / cancelled-* branch, its required sidecars, and the report-gate precedence into the new `## /design auto error reporting` section before deleting the SKILL.md block.
  - From Codex-Pragmatic: Carry those missing bullets into `skills/design/references/finalize-step5.md` before removing the source text, or leave the full paragraph in `SKILL.md` until the reference is complete.
  - From Codex-Requirements: Add that paragraph to `skills/design/references/finalize-step5.md` or leave a short `SKILL.md` pointer that preserves the sidecar and audit requirement.

### FINDING_4: Relocated auto-error-reporting reference lacks pre-Step-5 load hook
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Replacing the always-loaded `/design auto error reporting` block with only a pointer to `finalize-step5.md` (mandatory-read at Step 5) drops operator-visible failure-report / operator-action guidance on Step 0 cancel, clarify, decompose, and other Final summary exits before Step 5, unless another site loads the reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either keep a one-sentence always-loaded note at the old site (outcomes + pointer), or add an explicit lazy-load line in `### Final summary block` to read `finalize-step5.md` § `/design auto error reporting` before terminal exits; do not rely on Step 5 entry alone.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:67-74
- **Concern**: [SCOPE-REDUCTION] The SKILL.md removal list names Folded contract, Tradeoff, and pause/resume helper lines but not the Completion sentinels lead-in.. Scenario: Line 67 opens with **Completion sentinels for pause/resume.** and Phase 7 folds absorbed prior-step sentinel writes..., which duplicates the Phase 7 exception on line 61 and keeps always-loaded prose the issue targets for relocation.
- **Proposed resolution**: Explicitly remove the entire Completion sentinels subsection (heading plus lead-in through pause/resume helper coverage), not only the labeled subparagraphs; leave the single maintainer-only sentinel-host-table.md pointer.
