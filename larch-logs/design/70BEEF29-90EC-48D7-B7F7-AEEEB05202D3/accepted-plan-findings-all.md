### FINDING_1: collect-findings.sh parses external output without consulting collector STATUS
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: After ns-retry removal, a substantive/structured validation failure leaves narrative in `EXTERNAL_OUTPUT_FILES` while the collector emits `STATUS=NOT_SUBSTANTIVE`. The `/review` collect-findings loop still runs `parse_output_tsv`/`parse_output` on every launched file, so prose can be ingested as junk findings instead of being dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Build the parse set from `collector_results.env`: include only records with `STATUS=OK` (and existing cap_hit rules); skip `NOT_SUBSTANTIVE` files; add a harness case with narrative output plus collector `NOT_SUBSTANTIVE`.
  - From Codex-Arch: Add `python/legacy_review_shell/collect-findings.sh` to the plan. Use `collector-results.env` to parse only external reviewer files with `STATUS=OK`, log non-OK records as today, and add a focused review pipeline test that a `NOT_SUBSTANTIVE` external is logged but absent from findings.


### FINDING_2: No regression test that NOT_SUBSTANTIVE increments COLLECT_FAILURE_COUNT in plan review
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Issue #4016 showed `round-summary.env` with `COLLECT_OK_COUNT=5` and `COLLECT_FAILURE_COUNT=0` after ns-retry masked the first-pass failure. The plan removes ns-retry but only adds embedded prompt invariants, not a collector-evidence tally test proving `NOT_SUBSTANTIVE` increments `COLLECT_FAILURE_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add/extend `python/test_plan_review.py` to stub collector stdout with one `NOT_SUBSTANTIVE` record and assert `round-summary.env` / `.step3-review-result.env` records `COLLECT_FAILURE_COUNT=1` (and that the slot is omitted from paths-file/findings ingestion if applicable).


### FINDING_3: validation-phase.md still documents ns-retry artifacts and relaunchable NOT_SUBSTANTIVE
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Operational steps in `validation-phase.md` still enumerate `*-ns-retry.txt` sidecar candidates and route `NOT_SUBSTANTIVE` through Runtime Timeout Fallback. After collector changes those steps contradict behavior and can mislead implementers updating only high-level collector prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `validation-phase.md` edit, explicitly remove ns-retry path/sidecar bullets and restate `NOT_SUBSTANTIVE` as terminal collector validation (warn + drop) while keeping only launch-level empty/transient retries.


### FINDING_5: test-research-structure.sh still pins -ns-retry.txt sidecar requirement
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The `validation-phase` sidecar pin at `scripts/test-research-structure.sh:249` still requires `-ns-retry.txt`, but the plan only lists `validation-phase.md`. Editing the doc to drop ns-retry sidecar candidates while documenting terminal `NOT_SUBSTANTIVE` can make `make lint` fail on `test-harnesses-7` even though `make lint` is in the test plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `scripts/test-research-structure.sh` to Files to modify/create and either keep `-ns-retry.txt` as a legacy ingest candidate in `validation-phase.md` or remove the contains pin at line 249 in the same change.


### FINDING_6: Missing structured-reviewer-validation no-retry test in test_collect_results.py
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan replaces the substantive ns-retry test only. `/design` plan review calls `collect-results` with both `--substantive-validation` and `--structured-reviewer-validation`. A reviewer can pass substantive checks and still fail structured validation; without a no-retry test for that branch, structured failures could still be retried or promoted to `OK` by mistake.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a pytest where structured validation fails on first pass: assert `STATUS=NOT_SUBSTANTIVE`, no `*-ns-retry*` artifacts, no sidecar promotion, and stderr warning; mirror the existing substantive narrative fixture.


### FINDING_7: check-reviewer-failure-threshold.sh can upgrade NOT_SUBSTANTIVE to OK via raw output heuristics
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: After `collect_results` stops ns-retry, the collector records `STATUS=NOT_SUBSTANTIVE`, but the second pass over `--reviewer-output-files` calls `output_file_is_success` on the still-present narrative file (non-empty, no literal `NOT_SUBSTANTIVE` token) and `count_static_status_once` upgrades the failure to `OK`, undoing the terminal failure the issue requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: ### UPDATED: `python/legacy_review_shell/check-reviewer-failure-threshold.sh` — when a basename already has collector `STATUS=NOT_SUBSTANTIVE` (or other non-OK), do not upgrade it from raw output-file heuristics; add/adjust harness coverage in `python/test_review_pipeline.py`.


### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/cli.py:272-273
- **Concern**: [SCOPE-REDUCTION] Plan makes the registered voting parse-rate-retry CLI compatibility optional. Scenario: Choosing parse-rate-check-only or deleting parse-rate-retry removes an existing CLI entry and argument surface even though the feature only needs to stop result relaunches
- **Proposed resolution**: Require parse_rate_retry_main to remain as a classify-only compatibility wrapper that accepts existing retry arguments and --ctx, ignores retry-only launch data, prints the bare status, and test that behavior unconditionally




### FINDING_1: Runtime-timeout fallback still relaunches Claude on NOT_SUBSTANTIVE
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: After ns-retry removal, research and validation collector docs still mandate Runtime Timeout Fallback (plus Claude Agent relaunch) for any `STATUS != OK`, including `NOT_SUBSTANTIVE`. That treats substantive/structured result-quality failures like launch failures, violating the approved rule: no alt-tool fallback on result-quality failure; warn, tally as failure, drop output, and continue. `NOT_SUBSTANTIVE` must be carved out of runtime-timeout replacement / Claude relaunch in `external-reviewers.md`, `research-phase.md`, and `validation-phase.md`. Reserve runtime fallback for launch-class failures only (timeout, empty output, hard `FAILED`, `CURSOR_EMPTY_RESPONSE`, etc.).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Research/validation still mandate Runtime Timeout Fallback for every collector STATUS != OK After ns-retry removal, substantive/structured failures stay NOT_SUBSTANTIVE. Research §1.4 and validation §2.4 still require Runtime Timeout Fallback plus Claude relaunch for any non-OK STATUS. That replaces content-quality ns-retry with a Claude fallback relaunch, violating the approved no alt-tool fallback on result-quality failure rule and the issue goal to warn, tally, and continue. Explicitly carve NOT_SUBSTANTIVE out of Runtime Timeout Fallback / Claude relaunch in external-reviewers.md, research-phase.md, and validation-phase.md. For NOT_SUBSTANTIVE: emit warning, keep lane-status fallback_runtime_failed with FAILURE_REASON, drop output, do not launch replacement reviewer. Reserve runtime fallback for launch-class failures only (timeout, empty, hard FAILED, CURSOR_EMPTY_RESPONSE as today).
  - From Cursor-Requirements: Restrict Runtime-timeout replacement to launch failures (TIMED_OUT SENTINEL_TIMEOUT EMPTY_OUTPUT FAILED). For NOT_SUBSTANTIVE only warn, set RESEARCH_* to fallback_runtime_failed with FAILURE_REASON, and continue without a Claude relaunch


### FINDING_2: research-phase.md still documents dead ns-retry collector artifacts
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `research-phase.md` still documents `-ns-retry.txt` sidecar candidates and "non-substantive retry" ingestion while `validation-phase.md` cleanup is explicit. Operators following research-phase will hunt dead ns-retry/first-pass artifacts after collector removal; research and validation docs diverge on the same collector contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror validation-phase FINDING_3 in research-phase.md: drop `-ns-retry.txt` and non-substantive-retry sidecar bullets; keep only launch-level `-retry.txt`; restate terminal `NOT_SUBSTANTIVE` handling


### FINDING_3: Plan omits make lint harness update for plan-voter retry prompt
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits a `make lint` harness that still requires plan-voter retry prompt generation. After `parse_rate_retry_main` becomes classify-only, plan-review voter dispatch no longer creates `*plan-voter-prompt-retry.txt`, so `make test-prompt-template-invariants` fails with "plan-voter retry prompt was not rendered".
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add scripts/test-prompt-template-invariants.sh to the plan and update the plan-voter smoke to assert classify-only behavior, such as no retry prompt/artifact, or remove the retry-prompt assertion while preserving the voter prompt invariants



### FINDING_3: Plan omits embedded plan-review-loop.sh STATUS-gated ingestion and tally contract
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan underspecifies `/design` plan-review collection. `python/plan_review.py` still executes gzip-embedded `plan-review-loop.sh` via `run_plan_review_round` / `_LEGACY_ASSETS`, but the plan mainly names `dispatch-plan-review-panel.sh` prompt hardening and a vague "ensure counts as failure" line. Without explicit `plan-review-loop.sh` (and related loop/tally embedded asset) changes, collection, `round-summary.env`, paths-file construction, and `COLLECT_FAILURE_COUNT` can still ingest or list narrative outputs for `NOT_SUBSTANTIVE` reviewers after ns-retry removal, while the proposed `test_plan_review.py` regression expects paths-file omission and `COLLECT_FAILURE_COUNT=1`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit ### UPDATED steps for embedded skills/design/scripts/plan-review-loop.sh (and any sibling loop/tally embedded assets that write round-summary.env): gate findings ingestion on collector STATUS=OK, count NOT_SUBSTANTIVE in COLLECT_FAILURE_COUNT, regenerate all touched _LEGACY_ASSETS blobs.
  - From Cursor-Pragmatic: Add ### UPDATED plan-review-loop.sh under python/plan_review.py: mirror collect-findings STATUS=OK gating when building external parse sets / paths-file; regenerate _LEGACY_ASSETS; extend test_plan_review.py to fail if NOT_SUBSTANTIVE paths are ingested.
  - From Cursor-Requirements: Name the embedded `plan-review-loop.sh` (and regenerate `_LEGACY_ASSETS`) when collector-status-driven `COLLECT_FAILURE_COUNT` / paths-file filtering is implemented, or narrow the test to the exact module that writes `round-summary.env`


### FINDING_4: plan-review first-line format gate still eligible for waterfall fallback
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan does not address `python/agent_waterfall.py` behavior where round 2+ plan-review still passes `--require-first-line-pattern` into normal fallback. A narrative first line can be marked failed before collector validation and relaunched via phase2 or Claude, masking a result-quality failure instead of letting collector structured validation emit `NOT_SUBSTANTIVE` and drop the slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan to remove the plan-review first-line gate and let collector structured validation emit NOT_SUBSTANTIVE, or make format/result gate misses terminal drops for plan-review with no fallback




### FINDING_1: Embedded plan-review scripts listed as on-disk paths but runtime uses `_LEGACY_ASSETS` blobs only
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan lists `skills/design/scripts/plan-review-loop.sh` and `skills/design/scripts/dispatch-plan-review-panel.sh` as editable `### UPDATED:` paths, but those files are absent from the repo. Runtime bodies live only as gzip blobs in `python/plan_review.py` `_LEGACY_ASSETS` (with `plan-review-loop.sh` in `_RETIRE_DESIGN_SKIPS`). An implementer who edits missing on-disk paths without decode-edit-reembed of `_LEGACY_ASSETS` ships no Step 3 `STATUS` gating or `COLLECT_FAILURE_COUNT` fix, so tally masking (#4016) can persist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make the plan explicit: decode each embedded asset from _LEGACY_ASSETS, edit in a temp file, re-encode into plan_review.py (document compresslevel/mtime contract); list python/plan_review.py as the sole runtime authority, not absent on-disk paths
  - From Cursor-Innovation: State explicitly that changes are decode-edit-reembed of `_LEGACY_ASSETS` keys `skills/design/scripts/plan-review-loop.sh`, `skills/design/scripts/dispatch-plan-review-panel.sh`, and `scripts/dispatch-plan-voters.sh` in `python/plan_review.py`, with `python/test_plan_review.py` string pins as the lint backstop.
  - From Cursor-Requirements: Make `python/plan_review.py` `_LEGACY_ASSETS` regeneration the sole edit surface in **Files to modify/create**; document decode via `legacy_asset_bytes()`, edit, re-encode; drop or footnote nonexistent standalone paths


### FINDING_3: Research/validation downstream synthesis/merge gating for `NOT_SUBSTANTIVE` lanes not specified
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Research/validation `NOT_SUBSTANTIVE` outputs are marked terminal, but downstream synthesis/merge gating is not specified. A lane can fail validation with no Claude replacement, yet its fixed output file can remain on disk and synthesis or validation merge can still read narrative content, so required drop-output behavior is not enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add explicit status-gated downstream rules: only STATUS=OK external rows and pre-launch or launch-failure Claude fallback outputs feed synthesis/validation merge; NOT_SUBSTANTIVE lanes get a dropped-lane marker or are omitted from merge prompts while lane-status records fallback_runtime_failed

---

**Merge notes**

- **FINDING_1** merges three sources (Cursor-Arch, Cursor-Innovation risk-integration, Cursor-Requirements) on the same embedded-asset / phantom-path risk; severity is **blocking**.
- **FINDING_2** and **FINDING_3** stay separate: one fixes research-phase runtime-replacement prose; the other specifies downstream merge eligibility for dropped lanes.


### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1 / skills/design/scripts/dispatch-plan-review-panel.sh:1
- **Concern**: [SCOPE-REDUCTION] Embedded plan-review scripts have no on-disk source; plan says edit reviewable source then regenerate _LEGACY_ASSETS. Scenario: Both paths are only in python/plan_review.py _LEGACY_ASSETS and listed in _RETIRE_DESIGN_SKIPS (no skills/design/scripts/*.sh on disk). An implementer can edit a new live file that runtime never materializes, or skip collection/dispatch fixes while still updating tests
- **Proposed resolution**: Spell out the workflow: decode via plan_review.legacy_asset_bytes, edit, re-encode into _LEGACY_ASSETS (same gzip/base64 contract as prior Step 3 ports), or extract live copies and add a test_embedded_*_matches_live_script parity test like review-design-step3-loop.sh




### FINDING_2: parse_rate_retry_main still requires dropped VPR_ARGS flags
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan drops `--launch-mode` and `--retry-prefix-kind` from VPR_ARGS, but `parse_rate_retry_main` still requires them. After `scripts/dispatch-code-voters.sh` removes retry-only VPR_ARGS, classify-only calls exit with argparse error before printing NOT_SUBSTANTIVE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make launch-mode retry-prefix-kind and prompt-file optional no-ops in parse_rate_retry_main; keep accepting legacy argv; add pytest that dispatch-shaped argv without those flags exits 0 with bare NOT_SUBSTANTIVE



