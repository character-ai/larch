### [Plan Review] FINDING_1

### FINDING_1: Visible-output anti-halt trigger omitted from preserved deltas
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan binds implementers to keep only `/design`-specific anti-halt deltas listed in Approach while pointing generic continuation at `skills/shared/subskill-invocation.md#anti-halt`. That list omits the always-loaded preamble trigger `after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue` (live at `skills/design/SKILL.md:29`). Shared `#anti-halt` names visible outputs as intermediate artifacts in narrative prose and its canonical banner covers child-Skill returns plus numbered-step Bash helpers, but not the explicit immediate-continuation mandate after inline plan prints, voting tallies, or skip breadcrumbs. `/design` is outside `test-anti-halt-banners.sh`; planned `test-design-structure.sh` pins grep the `#anti-halt` anchor and recap rules but not visible-output continuation. Following the plan literally can restore halts after Step 2b plan output, Step 3 tallies, and skip breadcrumbs while still passing binding-dedup harness checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the visible-output continuation trigger to Approach preserved deltas and the SKILL.md preamble revise bullets (keep it inline next to the `#anti-halt` cite, matching `/implement`'s pattern of local deltas plus shared anchor); add a `contains` regression in `scripts/test-design-structure.sh` for the contract token (for example `after every visible output`).
  - From Cursor-Innovation: Add `after every visible output (plans, voting tallies, skip breadcrumbs)` to the Approach preserved-delta list and the SKILL.md preamble edit bullets. Pin the literal in `scripts/test-design-structure.sh`.
  - From Cursor-Pragmatic: Add after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue to the preserved-delta list, the SKILL.md preamble revision bullets, and a test-design-structure.sh grep pin for that phrase (or an equivalent literal token).
  - From Cursor-Requirements: Add visible-output continuation to Approach preserved deltas and the always-loaded preamble stub; add a matching `test-design-structure.sh` grep pin


### [Plan Review] FINDING_2

### FINDING_2: Recap-ban operative gates weakened in preamble stub
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The live preamble ties recap prohibition to precise driver outcomes: after Step 5c `python/cli.py design step5c` returns with `_publish_rc` in {0, 1, 3}, or after any cancellation outcome's Final summary block writes a non-empty summary file (`skills/design/SKILL.md:29`). The plan replaces that with vaguer timing (`no free-form recap after Step 5c or cancellation final-summary render`) and collapses Step 5d to back-reference the preamble, removing the explicit Step 5d backup that ties the ban to driver refresh plus mandatory Step 5c item 5 emit. Planned harness work pins render-exit carve-out and generic no-recap/no-cost tokens but not the `_publish_rc` / non-empty-cancellation-file trigger. Agents may recap too early, miss the `_publish_rc`=1 plan-block-write path, treat empty cancellation renders as recap-ban boundaries, or emit recap between driver return and mandatory marker-first emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Preserve the operative trigger verbatim in the always-loaded stub (Step 5c `_publish_rc` 0/1/3 plus cancellation non-empty summary file). Add a `test-design-structure.sh` grep for that trigger alongside the render-exit carve-out pin.
  - From Cursor-Pragmatic: Keep the operative driver-return trigger in the always-loaded preamble stub (_publish_rc 0, 1, or 3 plus cancellation non-empty summary file) or an equivalent shortened token, and pin it in test-design-structure.sh alongside the existing no-recap grep.


### [Plan Review] FINDING_3

### FINDING_3: Step 5d emit-to-footer ordering token dropped
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Current Step 5d forbids free-form recap between mandatory marker-first emit and warning replay/footer: `No free-form recap may appear between or after those pieces` (`skills/design/SKILL.md:819`). The plan instructs Step 5d to replace its duplicated binding block with a back-reference to Step 5c item 5 and a vaguer preamble no-recap rule (`after Step 5c or cancellation final-summary render`). That wording does not encode the intra-Step-5 ordering gap between Step 5c item 5 emit, Step 5d warning replay, and the machine footer. After item 5 emits the structured summary, an orchestrator can insert free-form recap before warning replay or the footer, halting mid-Step-5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Preserve an explicit Step 5d token forbidding recap between mandatory marker-first emit and warning replay/footer, or strengthen the preamble no-recap rule to name that sub-step boundary

**Not re-raised (already addressed in current plan per reviewers):** round-1 accepted `test-render-cost-line-callsites.sh` retargeting; round-2 accepted render-exit carve-out at preamble and Step 5c item 5.

