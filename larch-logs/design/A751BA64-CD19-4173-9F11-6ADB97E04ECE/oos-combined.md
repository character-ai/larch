### OOS_1: Aggregated rollup of 6 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 6 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **Compose-time prepare verb collides with existing prepare CLI**: [Files: python/larch/cli.py]
    ### OOS_1: Compose-time prepare verb collides with existing prepare CLI
    - **Reviewer(s)**: Cursor-Innovation
    - **Severity**: important
    - **Concern**: Introducing a second compose-time “prepare” verb alongside the existing architectural-guidelines prepare path risks ambiguous wrapper wiring or half-migrated live dispatch.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Innovation: Name compose-time verbs explicitly (e.g. compose-prepare / compose-write-assessment), repurpose prepare_main in place, and list exact retired vs live dispatch rows in python/larch/cli.py


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **Post-merge drop-rate acceptance audit omitted from testing strategy**: [Files: N/A]
    ### OOS_2: Post-merge drop-rate acceptance audit omitted from testing strategy
    - **Description**: Post-merge drop-rate acceptance audit omitted from testing strategy. Scenario: Issue acceptance asks operators to re-sample merged implement PRs and confirm ~0% drop rate; the plan has no verification step
    - **Reviewer**: Cursor-Requirements
    - **Severity**: latent
    - **Focus area**: correctness
    - **Location**: N/A
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **N/A**: [Files: N/A N/A. EXPECTED_OLD/EXPECTED_NEW scripts/test-implement-fence-shape.sh]
    ### OOS_3: N/A
    - **Description**: N/A. Scenario: SKILL.md removes the Phase A Bash fence; fence-shape harness may need EXPECTED_OLD/EXPECTED_NEW updates per readability-style plan-drafting reminder
    - **Reviewer**: Cursor-Requirements
    - **Severity**: latent
    - **Focus area**: code-quality
    - **Location**: scripts/test-implement-fence-shape.sh
    - **Phase**: design

    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **Keep ship pr stdout JSON-only**: [Files: diff/guideline paths/status]
    ### OOS_4: Keep `ship pr` stdout JSON-only
    - **Reviewer(s)**: Codex-Arch
    - **Severity**: important
    - **Concern**: The compose-time helper is expected to preserve a single-JSON wrapper on stdout, but the plan would let diff/guideline blocks leak into that channel and break the Step 8 wire surface.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Codex-Arch: Keep ship pr stdout JSON-only. Write materialized diff and guideline status to tmpdir files, put only safe paths/status in state or the route-exit handoff, and have the guidelines-assessment branch read those files.


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **Retire the live final_report drop-notice path**:
    ### OOS_5: Retire the live `final_report` drop-notice path
    - **Reviewer(s)**: Cursor-Innovation
    - **Severity**: important
    - **Concern**: The plan does not explicitly remove the stale-fingerprint drop path, so `final_report` can still persist the HEAD-drift notice and invalidate the implement note even after the compose-time fix.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Innovation: In the `final_report.py` update, delete `_persist_drop_notice_and_invalidate` and stale-fingerprint drop branches; read only a consumable compose-time durable note for current `HEAD`, or omit the section with a bounded warning


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
  - **Re-enter compose after ship_merge rebases**:
    ### OOS_6: Re-enter compose after `ship_merge` rebases
    - **Reviewer(s)**: Cursor-Pragmatic
    - **Severity**: important
    - **Concern**: The rebase path in `ship_merge` only pins or invalidates; it does not re-run the compose-time assessment, so the PR body can keep a stale or dropped note while merge continues.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Pragmatic: Require ship_merge to invoke the same compose-time helper used before pr-create (including NEEDS_USER_INPUT exit when reassessment is required) and update PR body via ensure_pr before returning to ci-initial


    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 6 entries
- **Phase**: implement
