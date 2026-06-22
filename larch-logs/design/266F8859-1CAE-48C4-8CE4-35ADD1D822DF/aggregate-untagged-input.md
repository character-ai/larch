### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:830
- **Concern**: Plan SKILL.md refresh misattributes oos-accumulated-seq-seed.awk replacement. Scenario: The plan says to point readers at Python OOS disposition modules after deleting the three awk files. OOS_WRITE_SEQ seeding is not in those modules; review_tally._seed_oos_seq in python/review_tally.py:258-273 already inlines oos-accumulated-seq-seed.awk. oos-has-legacy-finding-block-opener.awk has no runtime callers. Operators may look in the wrong module when seq seeding breaks.
- **Proposed resolution**: In the SKILL.md update, cite python/review_tally.py (_seed_oos_seq) for OOS_WRITE_SEQ seeding, python/file_oos.py (or oos_disposition) for non_security_oos gate counting, and python/design_oos.py only for design prepare counting. Note the legacy-opener awk was unused dead code.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:5-7
- **Concern**: Plan explicitly does not port two of the three awk processors, despite the issue scope requiring block-count, sequence-seed, and legacy-block-opener detection to move into python/design_oos.py. Scenario: The PR can delete oos-accumulated-seq-seed.awk and oos-has-legacy-finding-block-opener.awk without adding their in-process Python equivalents in the requested module, leaving the stated feature only partially delivered
- **Proposed resolution**: Revise the plan to add firm python/design_oos.py equivalents for sequence-seed and legacy-block-opener detection, with proportionate coverage or harness updates, before deleting all three awk files
