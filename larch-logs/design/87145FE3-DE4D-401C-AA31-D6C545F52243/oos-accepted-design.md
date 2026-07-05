### OOS_1: Reviewer proposal prompts still use highest-materiality wording
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Oos Pipeline Correctness
- **Severity**: important
- **Concern**: Reviewer-facing proposal prompts and generated reviewer bodies still prefer highest-materiality OOS items, so the loosened legitimacy standard will not reach proposal time consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/shared/reviewer-templates.md replacing highest-materiality with highest-legitimacy in all four OOS proposal bullets; regenerate auto-generated agents via python3 python/cli.py generate; sync the five hand-maintained agents/reviewer-*.md specialist variants; extend python/test_rendering.py if needed
  - From Codex-Arch: Update these prompt surfaces to the legitimacy rule and regenerate generated reviewer agents/pre-rendered prompts where the template feeds them.
  - From Cursor-Innovation: ### UPDATED: skills/shared/reviewer-templates.md: switch cap-3 wording to highest-legitimacy concrete items; regenerate agents via python3 python/cli.py generate check; add reviewer-templates to oos-acceptance-rubric Update triggers
  - From Cursor-Pragmatic: Add `### UPDATED: skills/shared/reviewer-templates.md` to the plan, regenerate auto-generated reviewer agents via the existing generate targets, and sync hand-maintained specialist agent variants that duplicate the OOS proposal cap lines
  - From Codex-Pragmatic: Update the canonical reviewer templates and generated or hand-maintained agent/pre-rendered bodies, or strip the old cap text from loaded bodies; add a rendered-prompt assertion that OOS proposal sections no longer contain highest-materiality or materiality-gate wording
  - From Codex-Requirements: Add `skills/shared/reviewer-templates.md` and the generated or pre-rendered reviewer artifacts to the plan, then regenerate/check the affected agents so OOS proposal guidance uses highest-legitimacy concrete items consistently.
  - From Cursor-dyn-Oos Pipeline Correctness: Add `### UPDATED: skills/shared/reviewer-templates.md` (all four Out-of-Scope sections) to use highest-legitimacy/concrete wording; regenerate derived `agents/*.md` and `agents/pre-rendered/*-body.txt` via the repo generate check flow


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
- **Filed URL**: https://github.com/character-ai/larch/issues/6384
### OOS_2: Design rollup annotation marks only the first accepted OOS
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: When the design cap collapses multiple accepted OOS originals into one rollup, only the first source block gets the filed URL, leaving later originals unfiled or prone to re-file on the next prepare pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: When cap collapses multiple originals into one rollup, annotate every original accepted OOS number with the rollup URL and write matching OOS_FILE_MAP rows, or persist an explicit source-to-rollup map; add a focused test for multi-OOS cap, annotate, then rerun prepare skipping via sentinel


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_3: Rejected-OOS audit could join findings-classification.tsv instead of parsing oos.md bodies
- **Description**: Rejected-OOS audit could join findings-classification.tsv instead of parsing oos.md bodies. Scenario: Parsing free-form oos.md duplicates tally semantics and risks missing legacy heading shapes or mis-reading Result= when footer format drifts
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/review_phase_detail.py:127-154
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Hand-maintained specialist agents duplicate materiality-only OOS cap prose outside reviewer-templates
- **Description**: Hand-maintained specialist agents duplicate materiality-only OOS cap prose outside reviewer-templates. Scenario: Even after `reviewer-templates.md` changes, several hand-maintained `agents/reviewer-*.md` files keep their own "highest-materiality" lines unless explicitly synced
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-correctness.md:65-66
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_5: Reviewer-template OOS proposal text still says highest-materiality after rubric rewrite
- **Description**: Reviewer-template OOS proposal text still says highest-materiality after rubric rewrite. Scenario: The canonical rubric and `rendering.py` move to legitimacy, but `reviewer-templates.md` (source for `python/cli.py render reviewer` and generated `agents/*.md`) still instructs reviewers to keep highest-materiality OOS proposals; that can drift proposal quality on render-reviewer surfaces outside the files the plan already updates
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/reviewer-templates.md:239-505
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_6: Rejected-OOS audit could join classification TSV instead of parsing `oos.md` footers
- **Description**: Rejected-OOS audit could join classification TSV instead of parsing `oos.md` footers. Scenario: `oos.md` contains both accepted and rejected OOS (`review_tally.py:1011-1029`); filtering on `Result=` in prose is fragile though the plan failure-modes section mentions it
- **Reviewer**: Cursor-dyn-Oos Pipeline Correctness
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/review_phase_detail.py:126-154
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: Reviewer templates still gate OOS by highest-materiality
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Canonical reviewer templates and generated reviewer prompts still cap Out-of-Scope proposals with highest-materiality wording, so proposal-time OOS selection keeps using the old materiality gate even if rendering.py and the rubric are updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/shared/reviewer-templates.md: replace highest-materiality / materiality-gate cap bullets with legitimacy selection; add reviewer-templates.md to the rewritten Update triggers list in oos-acceptance-rubric.md; regenerate auto-generated agents via existing generate targets and extend test_rendering.py or generate check as needed
  - From Cursor-Innovation: Add `### UPDATED: skills/shared/reviewer-templates.md` to swap highest-materiality / materiality-gate cap text for highest-legitimacy / legitimacy auto-reject wording (mirror `rendering.py`), extend the rubric Update triggers list, and add a testing step to regenerate affected agents and run `python3 python/cli.py generate check`.
  - From Cursor-Requirements: Add ### UPDATED: skills/shared/reviewer-templates.md (replace four highest-materiality OOS-cap lines with legitimacy wording), update hand-maintained agents/reviewer-*.md matching lines or regenerate via python3 python/cli.py generate pre-rendered-reviewer-prompts, regenerate committed agents/code-reviewer.md (and other generator-owned agents) from templates, and extend python/test_rendering.py or generate check so proposal prompts cannot drift back to materiality


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_8: Design annotate loses filed URL on capped rollups
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Design Step 5b annotate still maps one issue URL only to the first pre-cap OOS slot after cap rollup, leaving later accepted blocks without Filed URL so they remain unfiled and can be picked up again on a later prepare pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit design_oos.py annotate step: when cap produces one issue URL, stamp that URL on every source OOS block listed in the order file (or write OOS_FILE_MAP rows for each); cover multi-accepted cap-1 rollup in test_design_oos.py
  - From Cursor-Innovation: Add a firm `### UPDATED: python/larch/design/design_oos.py` step: after successful `issue-cap`, rewrite `order_file` from capped combined headers (or, when cap yields one issue, stamp every accepted source block with the single rollup URL and record `OOS_FILE_MAP` rows for all originals). Extend `test_design_oos.py` for multi-accepted → one capped issue → all sources annotated / `skip-no-items` on rerun.
  - From Cursor-Pragmatic: Add an UPDATED design_oos.py step: after cap=1 rollup, stamp every source OOS block in oos-accepted-design.md with the single filed URL (or port the implement stable-id mapping); extend test_design_oos.py to assert all rollup sources carry Filed URL and skip re-file on rerun
  - From Cursor-Requirements: Add a firm ### UPDATED: python/larch/design/design_oos.py step: when prepare/issue-cap collapses to one ISSUE_URL, annotate every order-listed accepted source block (or all still-unfiled accepts) with that URL and emit OOS_FILE_MAP rows per source; extend python/tests/design/test_design_oos.py with a capped multi-OOS annotate case asserting every original block is marked filed


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_9: Hand-maintained specialist agents duplicate the old materiality-only OOS cap prose
- **Description**: Hand-maintained specialist agents duplicate the old materiality-only OOS cap prose. Scenario: Seven hand-maintained reviewer-*.md files still embed highest-materiality bullets independent of reviewer-templates.md; updating templates plus generate check will not refresh these specialists, leaving a secondary prompt surface on the old standard
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-correctness.md:65
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_10: Rejected-OOS audit could read `findings-classification.tsv` instead of parsing `oos.md` footers
- **Description**: Rejected-OOS audit could read `findings-classification.tsv` instead of parsing `oos.md` footers. Scenario: Parsing `Result=` from markdown footers is brittle if tally formatting changes; classification TSV already records per-item OOS outcomes.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/review_phase_detail.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
