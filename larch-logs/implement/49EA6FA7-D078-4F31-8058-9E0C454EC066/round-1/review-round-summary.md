# Review Round 1

- Mode: `diff`
- 10 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Manifest-backed scout-archetype-yield.tsv is header-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, codex-specialist-edge-cases-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: When `--manifest-file` is set, `tally_code_votes()` writes only the `scout-archetype-yield.tsv` header and still emits `YIELD_TSV_FILE`. The retired `tally-code-votes.sh` built per-archetype yield rows from the manifest plus per-reviewer score data (including zero-count backfill and orphan `WARN` handling). Downstream consumers (`review_pipeline.py`, review skills, `review_and_fix.py`) treat `YIELD_TSV_FILE` as populated scout yield telemetry, so dynamic-archetype rounds now log a header-only artifact and lose per-archetype yield ratios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port `write_archetype_map`, score_rows join, and yield_ratio row emission from the deleted shell.
  - From codex-specialist-correctness-output.txt: Port manifest map, zero-row scoreboard, collector status, and yield-ratio calculations.
  - From codex-specialist-testing-output.txt: Recreate manifest-to-archetype yield row generation and add a manifest-backed tally test.
  - From codex-specialist-edge-cases-output.txt: Port legacy manifest mapping, collector dead rows, NOT_SUBSTANTIVE warnings, and populated yield TSV generation.
  - From dyn-artifact-contracts-output.txt: Port the shell’s `write_archetype_map`, score-row aggregation, zero-count manifest backfill, and orphan `WARN` logic into `tally_code_votes()`, then keep emitting `YIELD_TSV_FILE` only when the TSV has the expected rows.


### FINDING_11: Missing default `AGGREGATE_DISPATCH_SH` dispatch argv test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required default aggregate dispatch argv test is missing; all tests set `AGGREGATE_DISPATCH_SH`. Production aggregate with unset override can build wrong dispatch argv (single shell string vs argv list) and fail to merge findings before voting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest that leaves `AGGREGATE_DISPATCH_SH` unset and asserts `dispatch_argv` starts with `[sys.executable, cli.py, agent, dispatch-waterfall]`.


### FINDING_13: Missing `REVIEW_CORE_PRUNE_NITS_SH` override test for review core
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `REVIEW_CORE_PRUNE_NITS_SH` override test for `_call_maybe_override` is absent. Override seam regressions could route review core to the wrong prune executable without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add review-core test setting `REVIEW_CORE_PRUNE_NITS_SH` to stub and asserting stub invocation.


### FINDING_14: Missing compose tests for strict plan category and prune-label-map normalization
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required compose tests for strict plan category and prune-label-map reviewer normalization are missing. Newly ported `compose_review.py` helpers can emit wrong category or `reviewer_slots` in `review-findings-full.jsonl`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixtures exercising `_extract_category` strict mode and `plan-review-prune-label-map.tsv` normalization.


### FINDING_16: Aggregate validator dropped suggested-revision traceability checks
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The aggregate validator dropped suggested-revision traceability checks and the `LARCH_AGGREGATE_REVISION_TRACE_STRICT=1` failure path. A merged finding can include untraceable reviewer-attributed fix text and strict validation still accepts it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Restore the traceability helpers and strict-env behavior, plus tests for untraceable Suggested revisions bullets.


### FINDING_2: `--not-substantive-count` is accepted but never used
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: `--not-substantive-count` is parsed but never read. The shell appended degraded-panel `NOT_SUBSTANTIVE` warning blocks to `voting-tally.md` whenever the count was greater than zero (including the zero-effective-voter path). `review_pipeline.py` still forwards this flag from `check-reviewer-failure-threshold`, so `NOT_SUBSTANTIVE` dead slots no longer appear in the committed tally artifact operators and run logs rely on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit the shell-equivalent NOT_SUBSTANTIVE warning blocks when `int(args.not_substantive_count) > 0`.
  - From codex-specialist-edge-cases-output.txt: Port legacy manifest mapping, collector dead rows, NOT_SUBSTANTIVE warnings, and populated yield TSV generation.
  - From dyn-artifact-contracts-output.txt: Mirror the shell branches: when `int(args.not_substantive_count) > 0`, append the NOT_SUBSTANTIVE warning to `voting_tally_file` in both the `effective == 0` early return and the normal tally path.


### FINDING_3: `--collector-results-file` unused; dead manifest slots missing from scoreboard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: `--collector-results-file` is accepted but unused, and manifest orphan rows are missing from the reviewer scoreboard. The shell appended zero-count scoreboard rows for manifest outputs absent from `score_rows`, using collector `STATUS=` values (for example `NOT_SUBSTANTIVE`). The Python scoreboard only includes reviewers that proposed at least one finding, so dead or narrative-only scout slots disappear from `voting-tally.md` even though `review_pipeline.py` passes both `--manifest-file` and `--collector-results-file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port collector-status parsing and manifest dead-row append logic from deleted `tally-code-votes.sh`.
  - From codex-specialist-edge-cases-output.txt: Port legacy manifest mapping, collector dead rows, NOT_SUBSTANTIVE warnings, and populated yield TSV generation.
  - From dyn-artifact-contracts-output.txt: Port the shell’s collector parsing and manifest backfill awk logic so `voting-tally.md` retains zero-count rows with the correct `STATUS=` suffix for slots that produced no scored findings.


### FINDING_6: Plan-mode aggregation dropped scope-reduction parity validation
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation no longer validates tagged scope-reduction parity before appending withheld blocks. If aggregator output recreates a withheld `[SCOPE-REDUCTION]` finding, the new code appends the original too and persists duplicates instead of failing validation. This can produce duplicate or corrupted plan-review ballots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port the old parity validator and restore the original findings file on parity failure.
  - From codex-specialist-testing-output.txt: Port the deleted shell parity checks and add a plan-mode aggregate test for accidental scope-reduction merge rejection.


### FINDING_7: Accepted OOS numbering restarts at `OOS_1` every round
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Accepted OOS header numbering always starts at `OOS_1` and ignores the prior accumulated OOS sequence. If `accumulated-oos.md` already contains `OOS_1`, a later round mirrors another accepted OOS as `OOS_1` and creates duplicate IDs, breaking downstream filing and conflict tracking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Seed the OOS sequence from accumulated OOS when session env is present before writing normalized accepted-OOS blocks.
  - From codex-specialist-edge-cases-output.txt: Seed `oos_seq` from `accumulated-oos.md` when `session_env_path` is present before writing normalized accepted OOS blocks.
  - From codex-specialist-testing-output.txt: Seed `oos_seq` from accumulated OOS when `--session-env-path` is present and add a multi-round accepted-OOS test.


### FINDING_8: `emit_tally()` dropped fallback counting for legacy tally files
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: `emit_tally()` dropped the shell’s fallback counting when aggregate `ACCEPTED_COUNT` / `REJECTED_COUNT` / `NEUTRAL_COUNT` keys are absent from `review-tally.env`. Legacy tally files with per-finding `ACCEPTED=true`, `ACCEPTED=false`, `_OUTCOME=rejected`, and related rows now render zero accepted and zero rejected in `review-round-summary.md`, `review-summary.json`, and compact `rejected-findings.md` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restore fallback counting from `ACCEPTED=false`, `ACCEPTED=true`, and `OUTCOME` rows when count keys are missing.
  - From codex-specialist-edge-cases-output.txt: Restore fallback counting from `ACCEPTED=true`, `ACCEPTED=false`, `_OUTCOME=rejected`, and `REJECTED_SUBTYPE` rows.
  - From codex-specialist-testing-output.txt: Restore fallback counting for `*_ACCEPTED` and `_OUTCOME` rows and add an emit-tally fallback-count test.
  - From dyn-artifact-contracts-output.txt: Restore the shell fallback counters in `_count_from_tally()` (or a helper) before building round summary, JSON, and compact rejected output.


