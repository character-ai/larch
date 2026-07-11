### FINDING_4: [OUT_OF_SCOPE] Preserve Guidance text in guideline parsing
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-gate-sequencing
- **Severity**: minor
- **Concern**: `parse_guideline_entries` still drops `- Guidance:` bullets. Folding G-Gate-1 requirements into Why currently preserves them for assessments, but future edits that restore the conventional Guidance structure could silently drop normative ship-blocking and persisted-state requirements. Regression coverage should pin the parser-retained G-Gate-1 contract phrases and verify live writer paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test_parse_guideline_entries_g_gate_1_retains_contract asserting parsed output contains update author guidance and verify every live writer path.
  - From dyn-dyn-gate-sequencing: `parse_guideline_entries` still drops `- Guidance:` bullets repo-wide. G-Gate-1’s Why-fold works around that for assessments, but it diverges from the Why/Guidance/Deviate convention used elsewhere in `ARCHITECTURAL_GUIDELINES.md` and will drop normative text if a future edit moves rules back into `- Guidance:`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Disambiguate the Gate-1 suffixes
- **Reviewer(s)**: dyn-dyn-gate-sequencing
- **Severity**: minor
- **Concern**: `G-Gate-1` and `I-Gate-1` use the same `Gate-1` suffix for different axes—release sequencing versus self-declared disarm metadata—which may cause investigators to apply the wrong rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-sequencing: A short cross-reference in each entry would reduce the risk of applying the wrong rule during gate/producer investigations.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
