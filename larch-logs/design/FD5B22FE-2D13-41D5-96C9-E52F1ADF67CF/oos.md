### OOS_1: [OUT_OF_SCOPE] Drop firm public `read_rows` / `row_signature` helpers when ledger evidence is optional and unwired
- **Description**: [OUT_OF_SCOPE] Drop firm public `read_rows` / `row_signature` helpers when ledger evidence is optional and unwired. Scenario: Repo-wide `larch-logs` currently has zero committed `findings-ledger.tsv` files. Step 5 reads the ledger optionally but steps 6-7 never consume ledger rows for resurfacing or revert matching, so firm `### UPDATED: python/findings_ledger.py` plus expanded `test_findings_ledger.py` adds ~60+ lines of public surface with no execution path on the committed corpus.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/findings_ledger.py:116-122
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Prefer one TypedDict bundle over four new dataclasses for a single report section
- **Description**: [OUT_OF_SCOPE] Prefer one TypedDict bundle over four new dataclasses for a single report section. Scenario: Step 1 mandates four immutable dataclasses for one diagnostic renderer. The issue needs structured row/evidence passing, not four named types; extra types expand the diff and test harness without changing diagnostic output.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/analyze_issues.py:154-158
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Trim the `make test-analyze` bullet laundry to outcome-level coverage
- **Description**: [OUT_OF_SCOPE] Trim the `make test-analyze` bullet laundry to outcome-level coverage. Scenario: The plan adds ~20 near-duplicate linting-doc bullets mirroring every test name already listed in `python/test_analyze_issues.py`. That is documentation churn with no runtime contract change and increases maintenance drag on every fixture tweak.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:379-400
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

