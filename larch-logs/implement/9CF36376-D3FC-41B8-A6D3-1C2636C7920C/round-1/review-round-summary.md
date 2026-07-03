# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_2: Pause-save should exercise the real publish path
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The pause-save tests only exercise argv-level pause state and a mocked publish, so they do not prove the committed pause snapshot is enriched or that no tracking-summary upsert is attempted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add integration coverage asserting committed larch-logs/design/RUN_ID/final-summary.md is non-empty enriched content.
  - From cursor-specialist-testing: Add integration-style pause publish test with real log-publish path, assert enriched committed final-summary.md content, and assert no tracking-issue upsert-summary call.
  - From codex-specialist-testing: Add a pause-save integration or request-capture test that exercises the real log-publish render path for `paused`, asserts the committed `final-summary.md` is enriched, and asserts no tracking-summary upsert is attempted.


### FINDING_5: Log-publish tests should verify committed summary content
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The log-publish tests do not cover stale pre-existing `final-summary.md`, committed enriched content, or suppression of the helper upsert flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add monkeypatched test: seed stale final-summary.md, force render False, assert copy/commit omits stale sentinel.
  - From cursor-specialist-testing: git show committed final-summary.md and assert enrichment markers such as larch:run-summary v=1 and expected outcome heading.
  - From codex-specialist-testing: Capture the real `FinalSummaryRenderRequest` at the helper boundary and assert `upsert_summary_comment=False`, then read the pushed `final-summary.md` with `git show` and assert the enriched run-summary sentinel/body is present.


### FINDING_6: Clarify follow-up upsert should be gated on publish success
- **Reviewer(s)**: dyn-dyn-summary-publish
- **Severity**: important
- **Concern**: Clarify can upsert a tracking comment after log-publish failure or after a missing pre-copy render, which can point at a log tree that was never committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-publish: Gate the follow-up upsert on publish_ok == "true", or pass publish status into the renderer so failed publishes emit run_logs_path: N/A (and skip upsert when no committed snapshot exists).
  - From dyn-dyn-summary-publish: If pre-copy render failed, either skip the upsert pass, re-run `design log-publish` after a successful follow-up render, or treat a missing pre-copy `final-summary.md` as a hard signal not to upsert until a committed snapshot exists.


### FINDING_7: Clarify should resolve mode consistently
- **Reviewer(s)**: dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: Clarify's follow-up summary render resolves mode differently from the pre-copy render, so the committed file and tracking comment can disagree on mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-publish: Reuse _resolve_summary_mode(design_tmpdir) (or the same helper Step 5c uses from session ctx) in _render_clarify_final_summary so both renders share one mode source.


