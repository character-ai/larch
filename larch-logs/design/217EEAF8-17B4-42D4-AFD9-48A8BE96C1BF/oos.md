### OOS_1: Operator SKILL catalog still denies realized-outcome diagnostics
- **Description**: Operator SKILL catalog still denies realized-outcome diagnostics. Scenario: The shipped `skills/voter-calibration/SKILL.md` states the tool does not use realized outcomes, while the plan adds `--realized-outcomes`. That mismatch will confuse operators even though offline core metrics stay `gh`-free.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/SKILL.md:9-11
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Append only a realized-outcomes subsection instead of the full `ground_truth_voter_calibration()` report
- **Description**: [OUT_OF_SCOPE] Append only a realized-outcomes subsection instead of the full `ground_truth_voter_calibration()` report. Scenario: The helper already returns a full calibration report. Repeating that verbatim in `/voter-calibration` or each era slice adds unrelated corpus, agreement, and era sections that the feature does not need.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:128-140
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

