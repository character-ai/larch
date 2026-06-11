### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:31-36
- **Concern**: [SCOPE-REDUCTION] Round-directory mtime fallback can reject the live Step 3 root manifest. Scenario: During active Step 3, dispatch-plan-review-panel.sh writes plan-review-slots.ndjson, then later writes prune-decision.env in plan-review/round-N, while round-start-s is absent until terminal paths. The proposed root manifest check requires manifest mtime >= round dir mtime when round-start-s is absent, so the real live manifest can be rejected and progress falls back to the shallow generic report.
- **Proposed resolution**: Use the Step 3 timing mark as the freshness anchor when start_s exists. Only fall back to round directory mtime when both step_start_s and round-start-s are absent. Add the active-round test with round dir mtime newer than the manifest to match the current dispatch order.

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:31-36
- **Concern**: [SCOPE-REDUCTION] Root-manifest freshness uses round-dir mtime after prune-decision writes. Scenario: dispatch-plan-review-panel.sh finalizes plan-review-slots.ndjson, then writes prune-decision.env into plan-review/round-N. That makes the round directory newer than the manifest while round-start-s is still absent on normal active rounds. The plan then requires manifest mtime >= round-dir mtime whenever round-start-s is missing, so the live Step 3 manifest is rejected and _render_design falls back to the same shallow generic progress the issue reports.
- **Proposed resolution**: In the common window after panel dispatch while reviewers are still returning, p/progress would still show only design Step 3 — plan review — started … ago and last artifact instead of round N and returned/total counts. When step_start_s is present, do not require manifest mtime >= round-dir mtime by itself. Accept the root manifest if manifest mtime >= step_start_s and at least one manifest output path is non-empty with mtime >= round-dir mtime; otherwise return empty. Keep the round-dir mtime rejection only for the no-markers case. Add a regression where round-dir mtime is newer than the manifest after a prune-decision write but fresh outputs exist.
