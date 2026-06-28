### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/finalize-step5.md:1-7
- **Concern**: Appending run-wide `/design auto error reporting` prose without updating the reference triplet. Scenario: The Consumer/Contract/When-to-load header still scopes the file to Step 5 finalization only. The moved section documents Final-summary and teardown behavior from Step 0 onward (`failure-report`, sentinel precedence, `stage-terminal-state`, panel-degradation taxonomy). Progressive-disclosure readers and maintainers can treat the file as Step-5-only and miss run-wide failure-path semantics.
- **Proposed resolution**: In the same edit, extend **Contract** (and **When to load** if needed) to include the appended auto-error-reporting section; keep the Step 5 mandatory-read hook unchanged.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:61-74
- **Concern**: Removal spec leaves a dangling Phase 7 cross-reference. Scenario: The plan removes the **Folded contract**, **Tradeoff**, and pause/resume coverage block but Step 61 still says absorbed sentinels are folded into adjacent hosts "(see **Completion sentinels** below)". If lines 67-72 are deleted without a replacement stub, SKILL.md retains a broken anchor with no **Completion sentinels** section.
- **Proposed resolution**: Replace the removed block with a one-line stub such as "**Completion sentinels for pause/resume.** Maintainer contract: `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sentinel-host-table.md`." and keep the existing maintainer-only load rule on the following line. [OUT_OF_SCOPE] skills/design/SKILL.md / docs/configuration-and-permissions.md:424-432 — `docs/configuration-and-permissions.md` still has a parallel `/design auto error reporting` section that the plan does not update; operator docs can drift from the relocated SKILL/reference surface after merge.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:295-299; skills/design/references/finalize-step5.md:1-120
- **Concern**: The proposed relocation drops the current operator-action / cancelled-* branch from the only always-loaded report-gate prose, and the new Step 5 reference as specified does not add it back.. Scenario: After `### /design auto error reporting` is removed, no file still says those outcomes must write `design-failure-operator-action.env`, `design-failure-operator-action-chat.md`, and the run-log audit, so non-Step-5 failure paths lose the teardown contract.
- **Proposed resolution**: Carry the operator-action / cancelled-* branch, its required sidecars, and the report-gate precedence into the new `## /design auto error reporting` section before deleting the SKILL.md block.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:61
- **Concern**: The plan removes the always-loaded Completion sentinels block but does not retarget the Phase 7 exception cross-reference.. Scenario: Line 61 still says absorbed sentinels are folded into adjacent hosts (see **Completion sentinels** below). After relocation only the maintainer pointer to sentinel-host-table.md remains, so the below anchor is dangling and misleads orchestrators editing Bash prelude prose.
- **Proposed resolution**: In the SKILL.md edit list, drop the see **Completion sentinels** below clause from the Phase 7 exception sentence (line 61 already ends with the sentinel-host-table pointer for Step 1d.7).



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:67-74
- **Concern**: [SCOPE-REDUCTION] The SKILL.md removal list names Folded contract, Tradeoff, and pause/resume helper lines but not the Completion sentinels lead-in.. Scenario: Line 67 opens with **Completion sentinels for pause/resume.** and Phase 7 folds absorbed prior-step sentinel writes..., which duplicates the Phase 7 exception on line 61 and keeps always-loaded prose the issue targets for relocation.
- **Proposed resolution**: Explicitly remove the entire Completion sentinels subsection (heading plus lead-in through pause/resume helper coverage), not only the labeled subparagraphs; leave the single maintainer-only sentinel-host-table.md pointer.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:61
- **Concern**: Phase 7 exception still points to removed Completion sentinels section. Scenario: The plan deletes the always-loaded Folded contract / Tradeoff block (~67-72) but leaves `(see **Completion sentinels** below)` at line 61. After the edit, that cross-reference is dangling and misdirects anyone tracing absorbed 1c/1d/1e sentinel behavior.
- **Proposed resolution**: In the SKILL.md edit list, retarget line 61 to `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sentinel-host-table.md` (new `## Folded contract and tradeoff` section) and expand the existing maintainer pointer (~74) to mention that section, not only the host table.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:293-301
- **Concern**: Auto-error-reporting pointer targets a Step-5-only reference without a Final-summary load hook. Scenario: The relocated `/design auto error reporting` block documents failure-report / operator-action semantics used on Step 0 cancel, clarify, decompose, and other Final summary exits before Step 5. Replacing the section with only a pointer to `finalize-step5.md` (loaded mandatorily at Step 5) drops always-loaded guidance on every pre-Step-5 terminal path unless another site loads it. Issue scope says verbs own the gate, but SKILL still documents operator-visible skip/audit expectations in that block today.
- **Proposed resolution**: Either keep a one-sentence always-loaded note at the old site (outcomes + pointer), or add an explicit lazy-load line in `### Final summary block` to read `finalize-step5.md` § `/design auto error reporting` before terminal exits; do not rely on Step 5 entry alone.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:293-299
- **Concern**: The proposed move out of `SKILL.md` omits the operator-action/cancelled-* sidecar and run-log audit contract, and it also drops the exact `stall-recovery validate-token` / `validate-terminal-state` hard-halt writer checks.. Scenario: After the relocation, failure and cancel paths would still be mentioned at a high level, but the docs would no longer preserve the required audit-file writes or the validated terminal-state writer contract, so the auto-error-reporting move is incomplete.
- **Proposed resolution**: Carry those missing bullets into `skills/design/references/finalize-step5.md` before removing the source text, or leave the full paragraph in `SKILL.md` until the reference is complete.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:295-299
- **Concern**: Planned auto-error-reporting relocation omits the operator-action/cancelled-* cleanup contract.. Scenario: A cancelled or operator-action `/design` run would lose the requirement to write `design-failure-operator-action.env`, `design-failure-operator-action-chat.md`, and the run-log audit before exit, so the relocated docs would no longer preserve the existing failure-path behavior.
- **Proposed resolution**: Add that paragraph to `skills/design/references/finalize-step5.md` or leave a short `SKILL.md` pointer that preserves the sidecar and audit requirement.



