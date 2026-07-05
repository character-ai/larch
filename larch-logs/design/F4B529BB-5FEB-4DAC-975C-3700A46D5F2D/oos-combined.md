### OOS_1: Aggregated rollup of 13 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 13 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **oos-2 must branch on kept items, not just actuality**: [Files: forward/terminal oos-3/oos-4.]
    ### OOS_1: oos-2 must branch on kept items, not just actuality
    - **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-dyn-Prompt Flow Contract
    - **Severity**: blocking
    - **Concern**: The `oos-2` terminal logic still keys on actuality-pass items, so zero-kept runs can skip batch confirmation or close sources too early instead of flowing through the new merit gate.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Codex-Arch: After merit approval, re-check whether any kept items remain. If none do, close the fully discarded sources and stop before dedupe or dependency phases.
      - From Codex-Arch: Make the no-kept-items branch trigger on any pending low-merit item, even when there are no stale items, so oos-4 still presents the batch confirmation.
      - From Cursor-Innovation: In oos-2, redefine forward/terminal branches on kept (merit-passing) counts only; treat merit-pending separately; add an explicit zero-kept path that goes to consolidated merit confirmation and fully-discarded closure without entering combination planning
      - From Cursor-dyn-Prompt Flow Contract: In oos-2 add a guard: if any pending low-merit items exist, do not invoke close-stale or stop; continue to oos-3/oos-4. Preserve the existing lines 170-180 path only when P=0 (stale-only-only). Add the rescued-all branch: after merit confirmation at oos-4, if all pending were rescued, continue to oos-3 instead of stopping
      - From Cursor-dyn-Prompt Flow Contract: State explicitly: while P>0 anywhere in the run, do not call close-stale in oos-2; carry every fully-discarded candidate (stale-only or mixed) to oos-4 and close only after the single batch gate confirms merit rejections (and rescues are resolved)


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **oos-4 partial approval needs clear merit semantics**:
    ### OOS_2: oos-4 partial approval needs clear merit semantics
    - **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Prompt Flow Contract
    - **Severity**: important
    - **Concern**: Partial list approval is still under-specified for merit outcomes, so a selective apply can leave merit rejections ambiguous or accidentally applied without a batch decision.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Innovation: State that partial list approval does not apply merit rejections; require an explicit merit batch outcome (approve all rejections, free-prose rescue, or cancel) before any oos-5 apply or close-stale for merit-affected sources
      - From Cursor-Requirements: Keep the existing partial list apply option for groups and fully-discarded closures; state how merit rejections behave on that path (e.g. held until explicit batch confirm or resolved in the same response).
      - From Cursor-dyn-Prompt Flow Contract: Clarify in oos-4: partial lists apply only to combination groups and fully-discarded closures; merit rejections are all-or-nothing per batch (approve all listed minus rescued items, or cancel). Cancel leaves all merit items un-rejected


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **Rescue regroup must precede close/apply**: [Files: close/apply cancel/rescue/approve oos-3/oos-4 oos-3/4]
    ### OOS_3: Rescue regroup must precede close/apply
    - **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Prompt Flow Contract
    - **Severity**: blocking
    - **Concern**: After a rescue, the workflow still needs to recompute the discarded set, regroup, and re-present the changed scheme before any close or apply step; otherwise rescues can be lost or applied against a stale plan.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Innovation: In oos-4, pin order: parse approval and rescue prose; finalize merit rejections; rerun oos-3 dedup and rebuild groups when any item is rescued; close fully discarded sources; then run oos-5 apply
      - From Cursor-Pragmatic: Order oos-4 post-response work as: parse cancel/rescue/approve; apply confirmed merit rejections; recompute fully discarded sources; rerun oos-3/oos-4 grouping when any rescue; then close-stale fully discarded sources; then oos-5 apply
      - From Codex-Pragmatic: After any rescue, rebuild the fully discarded-source list from the updated actual-item set before prompting or closing anything.
      - From Cursor-Requirements: In oos-4 prose, after parsing rescue targets and finalizing merit rejections, rerun oos-3 dedup and regroup; if the kept-item set changed, re-present the combination scheme and require explicit operator confirmation before oos-5 apply (or define a single response that finalizes merit and approves the post-rescue scheme).
      - From Cursor-dyn-Prompt Flow Contract: Add: after parsing rescues, rerun oos-3/4 grouping; if the scheme differs from what was shown, re-present the updated groups (and closures) for approval before oos-5; do not apply the pre-rescue scheme


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **Rescue matching needs stable keys**:
    ### OOS_4: Rescue matching needs stable keys
    - **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
    - **Severity**: important
    - **Concern**: Free-prose rescue still lacks a concrete matching contract, so the operator’s “keep the caching one” style responses can be misread or rejected.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Pragmatic: Require each merit line to show stable display key plus issue number and item title; instruct rescue matching against those identifiers and titles before any rejection or close-stale.
      - From Cursor-Requirements: Mandate oos-4 display keys in the Rejected items (merit) list and document rescue parsing: match display keys first, then issue number plus item title; ambiguous matches default to keep.


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **Generated /combine-issues catalog blurb still mentions only actuality**: [Files: docs/skills.md:318]
    ### OOS_5: Generated `/combine-issues` catalog blurb still mentions only actuality
    - **Description**: Generated `/combine-issues` catalog blurb still mentions only actuality. Scenario: The skills catalog mirrors the pre-merit combine-issues description. Operators discovering the skill from docs alone will not see the merit chokepoint, though runtime behavior comes from SKILL.md.
    - **Reviewer**: Cursor-Arch
    - **Severity**: latent
    - **Focus area**: risk-integration
    - **Location**: docs/skills.md:318
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **Flags table and OOS intro still describe actuality-only filtering**: [Files: .claude/skills/combine-issues/SKILL.md:15-17]
    ### OOS_6: Flags table and OOS intro still describe actuality-only filtering
    - **Description**: Flags table and OOS intro still describe actuality-only filtering. Scenario: The --oos flag blurb and OOS Mode intro still say actuality-only checks; operators may not expect a merit gate or separate pending counts
    - **Reviewer**: Cursor-Innovation
    - **Severity**: latent
    - **Focus area**: code-quality
    - **Location**: .claude/skills/combine-issues/SKILL.md:15-17
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **--oos flag blurb still actuality-only**: [Files: .claude/skills/combine-issues/SKILL.md:17-17]
    ### OOS_7: --oos flag blurb still actuality-only
    - **Description**: --oos flag blurb still actuality-only. Scenario: The flags table and OOS intro still describe only actuality filtering; merit is discoverable only after reading oos-2.
    - **Reviewer**: Cursor-Requirements
    - **Severity**: nit
    - **Focus area**: code-quality
    - **Location**: .claude/skills/combine-issues/SKILL.md:17-17
    - **Phase**: design




    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **No anti-pattern guard for auto-applying merit rejections**: [Files: .claude/skills/combine-issues/SKILL.md:427-438]
    ### OOS_8: No anti-pattern guard for auto-applying merit rejections
    - **Description**: No anti-pattern guard for auto-applying merit rejections. Scenario: Failure modes mention the risk, but the Anti-patterns section has no NEVER auto-apply merit rejections rule parallel to stale and close guards.
    - **Reviewer**: Cursor-Requirements
    - **Severity**: nit
    - **Focus area**: risk-integration
    - **Location**: .claude/skills/combine-issues/SKILL.md:427-438
    - **Phase**: design




    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **Frontmatter description omits merit gate**: [Files: .claude/skills/combine-issues/SKILL.md:3-3]
    ### OOS_9: Frontmatter description omits merit gate
    - **Description**: Frontmatter description omits merit gate. Scenario: The skill description string still says verifies actuality only; plugin discovery may understate the new behavior.
    - **Reviewer**: Cursor-Requirements
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: .claude/skills/combine-issues/SKILL.md:3-3
    - **Phase**: design




    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **Catalog blurb still describes actuality-only OOS mode**: [Files: docs/skills.md docs/skills.md:318]
    ### OOS_10: Catalog blurb still describes actuality-only OOS mode
    - **Description**: Catalog blurb still describes actuality-only OOS mode. Scenario: Issue scope confines changes to SKILL.md; docs/skills.md will remain stale until separately updated
    - **Reviewer**: Cursor-dyn-Prompt Flow Contract
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: docs/skills.md:318
    - **Phase**: design

    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **[OUT_OF_SCOPE] Catalog blurb still describes actuality-only OOS mode**: [Files: docs/skills.md docs/skills.md:318]
    ### OOS_11: [OUT_OF_SCOPE] Catalog blurb still describes actuality-only OOS mode
    - **Description**: [OUT_OF_SCOPE] Catalog blurb still describes actuality-only OOS mode. Scenario: Operators reading docs/skills.md will not learn about the merit gate until they open the dev skill
    - **Reviewer**: Cursor-Arch
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: docs/skills.md:318
    - **Phase**: design




    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **[OUT_OF_SCOPE] Frontmatter description and --oos flag table omit merit**: [Files: .claude/skills/combine-issues/SKILL.md:3-17]
    ### OOS_12: [OUT_OF_SCOPE] Frontmatter description and --oos flag table omit merit
    - **Description**: [OUT_OF_SCOPE] Frontmatter description and --oos flag table omit merit. Scenario: The first skill discovery surfaces still say actuality-only filtering
    - **Reviewer**: Cursor-Arch
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: .claude/skills/combine-issues/SKILL.md:3-17
    - **Phase**: design




    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **[OUT_OF_SCOPE] OOS Mode intro paragraph still says actuality-only**: [Files: .claude/skills/combine-issues/SKILL.md:81-83]
    ### OOS_13: [OUT_OF_SCOPE] OOS Mode intro paragraph still says actuality-only
    - **Description**: [OUT_OF_SCOPE] OOS Mode intro paragraph still says actuality-only. Scenario: The section opener contradicts the new two-gate flow before operators reach oos-2
    - **Reviewer**: Cursor-Arch
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: .claude/skills/combine-issues/SKILL.md:81-83
    - **Phase**: design

    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 13 entries
- **Phase**: implement
