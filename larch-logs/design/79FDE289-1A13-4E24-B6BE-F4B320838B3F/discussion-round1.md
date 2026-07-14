## Decision 1: Blocking dependency (Piece 1) status
- **Question**: Is Piece 1 of the #7003 split implemented so we can proceed?
- **Resolution**: Yes. Issues #7023 and #7024 are merged (session.py and test_foundation.py now exist in python/tests/support/). review_wire.py does not yet exist.
- **Source**: codebase

## Decision 2: Scope of non-firm-heading files
- **Question**: Should test_review_aggregate.py, test_plan_review_panel.py, test_plan_review_round.py, test_review_phase_detail.py be migrated?
- **Resolution**: Yes, as MAY_UPDATE scope. The issue lists them explicitly under "Migrate review cluster." They should adopt review_wire builders where the pattern is a clear fit; no forced migration of one-off strings.
- **Source**: codebase

## Decision 3: test_support.py slot helper reuse
- **Question**: Is the python/test_support.py make_zero_findings_plan_review_fake_cli function a candidate for slot_manifest helper reuse?
- **Resolution**: The inline NDJSON in make_zero_findings_plan_review_fake_cli (line 204) is a direct slot_manifest_ndjson candidate. Acceptance says "where applicable" - this qualifies.
- **Source**: codebase
