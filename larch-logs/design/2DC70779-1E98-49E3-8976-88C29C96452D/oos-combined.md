### OOS_1: Aggregated rollup of 4 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 4 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **Summary inventory row still describes single-candidate argv truncation**: [Files: docs/linting.md:29]
    ### OOS_1: Summary inventory row still describes single-candidate argv truncation
    - **Description**: Summary inventory row still describes single-candidate argv truncation. Scenario: The MAY_UPDATE scope fixes only the `test-harnesses-15` harness row. Row 29 still says argv parsing ignores suffix tokens after `||`, `|`, `&&`, and `;`, which will contradict per-segment scanning and `lint-bare-grep-probe.md` after this change
    - **Reviewer**: Cursor-Requirements
    - **Severity**: latent
    - **Focus area**: risk-integration
    - **Location**: docs/linting.md:29
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **Harness contract bullet still claims suffix argv truncation only**: [Files: scripts/test-lint-bare-grep-probe.md:29-30]
    ### OOS_2: Harness contract bullet still claims suffix argv truncation only
    - **Description**: Harness contract bullet still claims suffix argv truncation only. Scenario: The planned harness-doc update adds new families but does not explicitly retire the existing "Argv truncation at `||`, `|`, `&`..." bullet, which will read as "later segments are never checked" after multi-segment scanning
    - **Reviewer**: Cursor-Requirements
    - **Severity**: latent
    - **Focus area**: correctness
    - **Location**: scripts/test-lint-bare-grep-probe.md:29-30
    - **Phase**: design




    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **then is a argv terminator but not a multi-candidate segment boundary**: [Files: scripts/lint-bare-grep-probe.sh:252-256]
    ### OOS_3: `then` is a argv terminator but not a multi-candidate segment boundary
    - **Description**: `then` is a argv terminator but not a multi-candidate segment boundary. Scenario: Same-line `if true; then rg PATTERN` tokenizes with `then` before `rg`. `candidate_index()` already misses this shape; a boundary loop that only splits on `||`, `&&`, `;`, `|`, and openers will still miss post-`then` grep-family commands.
    - **Reviewer**: Cursor-dyn-Awk Parser Guard
    - **Severity**: latent
    - **Focus area**: correctness
    - **Location**: scripts/lint-bare-grep-probe.sh:252-256
    - **Phase**: design

    Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
  - **Add an explicit regression for & segment restarts**: [Files: allowed/flagged ../root]
    ### OOS_4: Add an explicit regression for `&` segment restarts
    - **Reviewer(s)**: Cursor-Pragmatic
    - **Severity**: latent
    - **Concern**: The planned regression coverage mentions `||`, `&&`, `;`, pipelines, and `|&`, but not a standalone `&` boundary, so a bad background-separator restart could still go untested.
    - **Suggested revisions (informational for voters; coder decides)**:
      - From Cursor-Pragmatic: Add one allowed/flagged pair, e.g. flag `sleep 1 & rg PATTERN ../root` and keep a safe no-path `sleep 1 & true` or similar non-grep control if needed


    Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 4 entries
- **Phase**: implement
