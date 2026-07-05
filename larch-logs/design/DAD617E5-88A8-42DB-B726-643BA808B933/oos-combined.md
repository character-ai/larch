### OOS_1: Aggregated rollup of 7 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 7 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **Display keys can collide across sources**: [Files: .claude/skills/combine-issues/SKILL.md:207-212]
    ### OOS_1: Display keys can collide across sources
    - **Description**: Display keys can collide across sources. Scenario: The rejected list format allows duplicate letters such as A for different source issues. Bare-key rescue stays ambiguous even with better prose rules.
    - **Reviewer**: Cursor-Innovation
    - **Severity**: latent
    - **Focus area**: architecture
    - **Location**: .claude/skills/combine-issues/SKILL.md:207-212
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **oos-4 prompt still invites unstructured free-prose rescue**: [Files: .claude/skills/combine-issues/SKILL.md:222]
    ### OOS_2: oos-4 prompt still invites unstructured free-prose rescue
    - **Description**: oos-4 prompt still invites unstructured free-prose rescue. Scenario: The AskUserQuestion option remains rescue named merit items in free prose without pointing operators to the stable display keys shown in the Rejected items (merit) list. Behavior is safe with the new matching rules, but operators are nudged toward the highest-ambiguity input path.
    - **Reviewer**: Cursor-Pragmatic
    - **Severity**: latent
    - **Focus area**: code-quality
    - **Location**: .claude/skills/combine-issues/SKILL.md:222
    - **Phase**: design




    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **README combine-issues blurb still omits merit gate**: [Files: docs/skills.md]
    ### OOS_3: README combine-issues blurb still omits merit gate
    - **Description**: README combine-issues blurb still omits merit gate. Scenario: Issue scope covers docs/skills.md only; README row 220 still says --oos discards stale items without merit staging, so feature-matrix readers keep stale discovery text
    - **Reviewer**: Cursor-Requirements
    - **Severity**: latent
    - **Focus area**: risk-integration
    - **Location**: README.md:220
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **README --oos blurb still actuality-only**: [Files: docs/skills.md]
    ### OOS_4: README --oos blurb still actuality-only
    - **Description**: README --oos blurb still actuality-only. Scenario: Operators using the feature matrix miss the merit gate until they open docs/skills.md or the dev skill
    - **Reviewer**: Cursor-dyn-Prompt Contract Reviewer
    - **Severity**: latent
    - **Focus area**: risk-integration
    - **Location**: README.md:220
    - **Phase**: design

    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
  - **[OUT_OF_SCOPE] README catalog blurb still lags the merit gate**:
    ### OOS_5: [OUT_OF_SCOPE] README catalog blurb still lags the merit gate
    - **Reviewer(s)**: Cursor-Arch
    - **Severity**: latent
    - **Concern**: The README `--oos` blurb still mentions actuality-only discard behavior and omits the merit gate, so the catalog will keep drifting from the updated skill description until a separate sync lands.
    - **Suggested revisions (informational for voters; coder decides)**:


    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)
  - **[OUT_OF_SCOPE] Rejected-items display should show source keys on collisions**: [Files: source/key]
    ### OOS_6: [OUT_OF_SCOPE] Rejected-items display should show source keys on collisions
    - **Reviewer(s)**: Cursor-Requirements
    - **Severity**: latent
    - **Concern**: Showing bare keys in the `Rejected items (merit)` list can collide across sources; proactively showing `#source/key` would reduce ambiguity.
    - **Suggested revisions (informational for voters; coder decides)**:


    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)
  - **[OUT_OF_SCOPE] Frontmatter description still needs a char-budgeted draft**:
    ### OOS_7: [OUT_OF_SCOPE] Frontmatter description still needs a char-budgeted draft
    - **Reviewer(s)**: Cursor-Requirements
    - **Severity**: latent
    - **Concern**: The frontmatter `description:` follow-up can still use a candidate string with a char-budget note; the failure mode and lint commands are enough for implementation.
    - **Suggested revisions (informational for voters; coder decides)**:

    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 7 entries
- **Phase**: implement
