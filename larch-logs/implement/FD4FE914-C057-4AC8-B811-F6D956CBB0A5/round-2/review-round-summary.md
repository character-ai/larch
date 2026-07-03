# Review Round 2

- Mode: `diff`
- 6 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Unsupported pagination flag breaks prefetch
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: blocking
- **Concern**: `fetch_bug_issues` passes an unsupported `--page` flag to `gh issue list`, so live prefetch and the mirrored offline expectation fail before `/analyze-bugs` can build a manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Replace this with a supported pagination path, such as `gh api` REST or GraphQL cursor pagination, while preserving `--state all` semantics and the `[BUG]` prefix filter.
  - From codex-specialist-edge-cases: Use a supported pagination path, such as `gh api` with cursors, or increase/use `--limit` with documented bounds and client-side filtering.
  - From codex-specialist-testing: Use a supported pagination surface, such as `gh api --paginate` or GraphQL pagination, and update the offline test to assert the supported argv shape rather than `--page`.


### FINDING_3: Stale deep verdict survives refresh triage
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Refresh triage reuses a cached ledger row and can leave an old `deep_verdict` in place, so report rendering may prefer stale deep output over the new triage result when no fresh deep row arrives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Track current-run stage state or pass refresh into ingest/report, and clear or ignore cached deep fields whenever refresh re-triages a key until a valid current-run deep row is ingested.
  - From codex-specialist-edge-cases: On refresh or current-run triage ingest, clear deep fields unless a new deep result is ingested, or add run/stage provenance and make report precedence truly current-run first.
  - From codex-specialist-testing: Track current-run stage provenance or clear deep fields when refresh triage is ingested, then make report precedence use only current-run output before key-matched cached rows.


### FINDING_4: PR fallback lacks reachability check
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: PR fallback only proves the merge commit exists locally. It does not prove that the fix commit is reachable from the pinned evidence ref, so a commit on another branch or a stale object can be mistaken for proof that the fix landed on main.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: After `cat-file`, require `git merge-base --is-ancestor <fix_sha> <evidence_ref>` before accepting PR fallback evidence.


### FINDING_5: Ledger ingest trusts any manifest issue row
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Ledger ingest accepts any schema-valid row for any issue in the manifest, not just the batch or queue being processed, so off-task output can certify unqueued issues and poison the local ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Validate ingest rows against the specific batch or queue file for that stage, and reject issue numbers not assigned to that Task.


### FINDING_7: Deep ingest runs even when verifier was skipped
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Stage 2 unconditionally runs `--ingest-deep` even when deep verification did not run, so a correct deep skip can still fail at ingest because the ingest file is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Document and implement skip deep ingest when DEEP_PENDING=0 or teach ledger ingest to treat absent empty deep results as no-op.


### FINDING_8: Missing plan coverage in offline suite
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The fake-runner test suite still omits several plan-required regression paths, including refresh, stale cache-key joins, deep ingest rejection, PR fallback cases, and other ledger/report behaviors, so regressions can ship without coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: The offline suite still omits several plan-listed regression cases after round 1 expansion. Missing tests for --refresh skip bypass deep ingest PR success stale cache-key join later_history_hash invalidation and related resume paths let ledger/report regressions ship unnoticed. Add RecordingRunner tests for each remaining plan acceptance bullet especially refresh ingest deep PR fallback and cache-key join behavior.
  - From codex-specialist-testing: Add offline fake-runner tests for those plan-listed paths before shipping, especially the refresh and live-argv compatibility cases above.
