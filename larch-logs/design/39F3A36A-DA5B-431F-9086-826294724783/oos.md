### OOS_1: [OUT_OF_SCOPE] Verdict corpus discovery still walks standalone `review/*` classifier runs
- **Description**: [OUT_OF_SCOPE] Verdict corpus discovery still walks standalone `review/*` classifier runs. Scenario: Issue scope and filed-OOS evidence center on `design/` and `implement/`. `_ground_truth_discover_classifiers` also ingests `review/*/review-findings-classification-round-*.tsv`, so verdict mode can count standalone review `run_dir` values toward `--min-runs` and mix review-only evidence into the capstone corpus without matching the incentivized design/implement loop the issue describes.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/analyze_issues.py:1651-1661
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] Verdict corpus discovery still ingests standalone `review/*` classifier runs
- **Description**: [OUT_OF_SCOPE] Verdict corpus discovery still ingests standalone `review/*` classifier runs. Scenario: `_ground_truth_discover_classifiers` also walks `review/*/review-findings-classification-round-*.tsv`. Post-filter `review/` run_dirs can count toward `--min-runs` even though filed-OOS evidence and issue scope center on `design/` and `implement/`, weakening the incentivized-era corpus gate.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:1651-1661
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [SCOPE-REDUCTION] Severity calibration table is extra to the verdict/token-allocation capstone.
- **Description**: [SCOPE-REDUCTION] Severity calibration table is extra to the verdict/token-allocation capstone.. Scenario: This adds a second calibration dimension and renderer work the feature can ship without.
- **Reviewer**: Codex-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:179-199
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

