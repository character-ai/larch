### OOS_3:
- **Description**: Implement materialization copies the full larch:plan inner text, including the new review_status and rounds_completed header, into IMPLEMENT_TMPDIR/plan.txt without stripping. Scenario: Preflight refusal uses the header parser, but implementers and plan-adequacy audit see machine provenance lines mixed into the implementation plan body
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/bootstrap.py:655-657
- **Phase**: design

