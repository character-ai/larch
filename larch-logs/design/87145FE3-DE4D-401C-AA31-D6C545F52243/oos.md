### FINDING_1: Reviewer templates still gate OOS by highest-materiality
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Canonical reviewer templates and generated reviewer prompts still cap Out-of-Scope proposals with highest-materiality wording, so proposal-time OOS selection keeps using the old materiality gate even if rendering.py and the rubric are updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/shared/reviewer-templates.md: replace highest-materiality / materiality-gate cap bullets with legitimacy selection; add reviewer-templates.md to the rewritten Update triggers list in oos-acceptance-rubric.md; regenerate auto-generated agents via existing generate targets and extend test_rendering.py or generate check as needed
  - From Cursor-Innovation: Add `### UPDATED: skills/shared/reviewer-templates.md` to swap highest-materiality / materiality-gate cap text for highest-legitimacy / legitimacy auto-reject wording (mirror `rendering.py`), extend the rubric Update triggers list, and add a testing step to regenerate affected agents and run `python3 python/cli.py generate check`.
  - From Cursor-Requirements: Add ### UPDATED: skills/shared/reviewer-templates.md (replace four highest-materiality OOS-cap lines with legitimacy wording), update hand-maintained agents/reviewer-*.md matching lines or regenerate via python3 python/cli.py generate pre-rendered-reviewer-prompts, regenerate committed agents/code-reviewer.md (and other generator-owned agents) from templates, and extend python/test_rendering.py or generate check so proposal prompts cannot drift back to materiality


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Design annotate loses filed URL on capped rollups
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Design Step 5b annotate still maps one issue URL only to the first pre-cap OOS slot after cap rollup, leaving later accepted blocks without Filed URL so they remain unfiled and can be picked up again on a later prepare pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit design_oos.py annotate step: when cap produces one issue URL, stamp that URL on every source OOS block listed in the order file (or write OOS_FILE_MAP rows for each); cover multi-accepted cap-1 rollup in test_design_oos.py
  - From Cursor-Innovation: Add a firm `### UPDATED: python/larch/design/design_oos.py` step: after successful `issue-cap`, rewrite `order_file` from capped combined headers (or, when cap yields one issue, stamp every accepted source block with the single rollup URL and record `OOS_FILE_MAP` rows for all originals). Extend `test_design_oos.py` for multi-accepted → one capped issue → all sources annotated / `skip-no-items` on rerun.
  - From Cursor-Pragmatic: Add an UPDATED design_oos.py step: after cap=1 rollup, stamp every source OOS block in oos-accepted-design.md with the single filed URL (or port the implement stable-id mapping); extend test_design_oos.py to assert all rollup sources carry Filed URL and skip re-file on rerun
  - From Cursor-Requirements: Add a firm ### UPDATED: python/larch/design/design_oos.py step: when prepare/issue-cap collapses to one ISSUE_URL, annotate every order-listed accepted source block (or all still-unfiled accepts) with that URL and emit OOS_FILE_MAP rows per source; extend python/tests/design/test_design_oos.py with a capped multi-OOS annotate case asserting every original block is marked filed


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Hand-maintained specialist agents duplicate the old materiality-only OOS cap prose
- **Description**: Hand-maintained specialist agents duplicate the old materiality-only OOS cap prose. Scenario: Seven hand-maintained reviewer-*.md files still embed highest-materiality bullets independent of reviewer-templates.md; updating templates plus generate check will not refresh these specialists, leaving a secondary prompt surface on the old standard
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-correctness.md:65
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Rejected-OOS audit could read `findings-classification.tsv` instead of parsing `oos.md` footers
- **Description**: Rejected-OOS audit could read `findings-classification.tsv` instead of parsing `oos.md` footers. Scenario: Parsing `Result=` from markdown footers is brittle if tally formatting changes; classification TSV already records per-item OOS outcomes.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/review_phase_detail.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

