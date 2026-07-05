### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Design security OOS leaks into published logs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Design security OOS sidecars written to security-oos-observations.md can be copied into committed design run logs because the publish flow does not exclude that basename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add security-oos-observations.md to the publish exclusion set and regression-test that design log publish omits it.
  - From cursor-specialist-edge-cases: Add security-oos-observations.md to _PUBLISH_EXCLUDE_NAMES (or globs) and regression-test that publish never commits it.
  - From codex-specialist-edge-cases: Move the sidecar outside the published logs or exclude security-oos-observations.md from design publish
  - From cursor-specialist-testing: Add security-oos-observations.md to publish exclusions and test log-publish never copies it.
  - From codex-specialist-testing: Move the sidecar outside the publish tree or exclude security-oos-observations.md from design log publish and add a publish-filter regression test.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

