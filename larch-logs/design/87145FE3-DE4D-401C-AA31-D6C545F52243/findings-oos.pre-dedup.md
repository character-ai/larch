### OOS_1: Hand-maintained specialist agents duplicate the old materiality-only OOS cap prose
- **Description**: Hand-maintained specialist agents duplicate the old materiality-only OOS cap prose. Scenario: Seven hand-maintained reviewer-*.md files still embed highest-materiality bullets independent of reviewer-templates.md; updating templates plus generate check will not refresh these specialists, leaving a secondary prompt surface on the old standard
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-correctness.md:65
- **Phase**: design



### OOS_2: Rejected-OOS audit could read `findings-classification.tsv` instead of parsing `oos.md` footers
- **Description**: Rejected-OOS audit could read `findings-classification.tsv` instead of parsing `oos.md` footers. Scenario: Parsing `Result=` from markdown footers is brittle if tally formatting changes; classification TSV already records per-item OOS outcomes.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/review_phase_detail.py
- **Phase**: design



