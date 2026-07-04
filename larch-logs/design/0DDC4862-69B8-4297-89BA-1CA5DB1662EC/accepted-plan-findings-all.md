### FINDING_1: Self-review fallback still loses counts
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-Run Log Observability
- **Severity**: blocking
- **Concern**: The self-review path still materializes an empty `review-findings-full.jsonl`, so when `code-review-tally.json` is absent the fallback cannot reconstruct the real accepted/rejected counts and can collapse nonzero self-review runs to `0 findings` or `N/A`; the fallback also needs to reuse the shared tally derivation and the plan needs direct final-report coverage for this exact path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In write_self_review_tally emit minimal code-review JSONL records mirroring the markdown-derived accepted/rejected counts (or document an explicit non-goal and drop resilience for self-review); keep empty-jsonl only when both counts are zero
  - From Cursor-Arch: Import the existing helper for the fallback path.
  - From Codex-Arch: Derive self-review counts from the accepted/rejected markdown inputs that write_self_review_tally already reads, or keep a recoverable self-review tally marker in the committed run log.
  - From Cursor-Innovation: When derived accepted+rejected are both zero, return N/A unless the JSONL contains at least one phase=code-review record (panel zero-finding runs still get 0 findings only when the file has such records or another panel-only signal exists). Do not treat a present-but-empty JSONL as proof of zero findings
  - From Codex-Innovation: Keep the fallback for code-review runs only, or derive self-review counts from the self-review markdown artifacts when the tally file is absent.
  - From Cursor-Pragmatic: Extend the write_self_review_tally plan step to emit minimal phase: code-review accepted/rejected stub records into the findings batch input (matching the tallied counts) before run-log write, reusing the same counting rules as today. Keep the shared JSONL fallback unchanged. Add a test_pr_body.py case: tally missing, nonempty self-review findings jsonl, expect 2/3 accepted not 0 findings.
  - From Cursor-Pragmatic: Add one direct final-report test in `test_pr_body.py` (or the optional `test_final_report.py` integration test) that builds a run dir with populated `review-findings-full.jsonl`, no `code-review-tally.json`, and asserts the rendered line matches the stub-record counts; keep the existing self-review sidecar tests.
  - From Codex-dyn-Run Log Observability: Persist self-review counts into a durable non-empty artifact before the flush, or narrow the fallback to a path that can actually reconstruct self-review counts.


### FINDING_3: Run-root tally trace can be lost or misnamed
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The committed tally-failure trace is not guaranteed to land or be discoverable: the run-root sidecar can be written before the run directory exists, and the warning text can point at the ephemeral tmpdir path instead of the durable run-root artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Ensure run_dir.mkdir(parents=True, exist_ok=True) before the run-root sidecar write, or defer/copy the run-root sidecar after the findings leg completes
  - From Cursor-Innovation: Require Warnings text to reference the run-root relative path larch-logs/implement/<run_id>/code-review-tally.flush.err (or both paths with the run-root path first)


### FINDING_4: Tally warning append is not fail-open
- **Reviewer(s)**: Cursor-dyn-Run Log Observability, Codex-dyn-Run Log Observability
- **Severity**: important
- **Concern**: Appending the execution-issues warning is still unguarded, so a permissions or disk OSError can turn a tolerated tally failure into a nonzero Step 5 exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Run Log Observability: Wrap execution-issues append inside the new helper with contextlib.suppress(OSError), matching _flush_review_batches_for_result and _append_scout_flush_warning.
  - From Codex-dyn-Run Log Observability: Wrap the warning append in `contextlib.suppress(OSError)` or an equivalent fail-open guard, and keep the sidecar as the durable trace.


### FINDING_1: Missing second caller update for widened tally helper
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: `_derive_code_review_tally` is being widened to return `(accepted, rejected, seen)`, but `round_runner.py` still unpacks two values. That leaves normal Step 5 round completion exposed to a `ValueError` when composed findings exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either update `round_runner.py` to ignore the third value, or keep the existing two-value helper and add a separate shared helper for the final-report `seen` case.
  - From Cursor-Innovation: Enumerate every caller (`batch_report.py` and `round_runner.py`) in the plan and update both unpack sites, or keep the 2-tuple API and add a separate `seen` probe so `round_runner` stays unchanged.
  - From Codex-Innovation: Update `round_runner.py` along with `batch_report.py`, for example unpack `derived_accepted, derived_rejected, _seen = _derive_code_review_tally(composed_findings)`, or use a small result object and update both callers.
  - From Cursor-Pragmatic: Enumerate every caller (`batch_report.py` and `round_runner.py`) in the plan and update both unpack sites, or keep the 2-tuple API and add a separate `seen` probe so `round_runner` stays unchanged.
  - From Codex-Pragmatic: Update every existing caller, including `round_runner`, to handle the new seen value, or keep the old two-value helper and add a separate helper for final-report seen detection.
  - From Cursor-Requirements: Add `python/larch/review/round_runner.py` to the plan: update the import site to unpack all three values (ignore `seen` if unused) and note both call sites in `batch_report.py` and `round_runner.py` must change together
  - From Codex-Requirements: Add `### UPDATED: python/larch/review/round_runner.py` and update this unpack to ignore the seen flag, or keep the existing helper backward-compatible and expose a separate seen-aware helper.


### FINDING_2: Self-review warning append is still not fail-open
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The self-review path still has a bare `run_logs.append_execution_issue` call after a tolerated `write-tally` or findings flush failure. If that append raises `OSError`, Step 5 can still exit non-zero even though the contract is best-effort observability only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap the remaining write_self_review_tally Warnings append in contextlib.suppress(OSError), matching _append_scout_flush_warning and the helper, or route all failure text through the helper and drop the legacy append.
  - From Codex-Arch: Wrap the retained self-review `run_logs.append_execution_issue` call in `contextlib.suppress(OSError)`, or route it through the same fail-open helper path.
  - From Cursor-Innovation: Wrap the legacy self-review Warnings append in `contextlib.suppress(OSError)`, or drop it when the shared helper already recorded the tally failure.
  - From Cursor-Pragmatic: Wrap the retained self-review Warnings append in `contextlib.suppress(OSError)`, or route both tally and findings failures through one fail-open helper and drop the second unguarded append.


### FINDING_3: Update self-review tests for emitted code-review records
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds nonzero self-review `phase: code-review` records, but the existing `test_write_self_review_tally_nonzero_counts` still asserts `review-findings-full.jsonl` stays empty. Without updating that expectation, CI will fail even if the runtime change is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit plan bullet to update `test_write_self_review_tally_nonzero_counts` (and any other self-review tests that pin empty findings) alongside the new regression cases.


### FINDING_4: Self-review synthetic JSONL row counts are underspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_derive_code_review_tally` counts one accepted or rejected outcome per JSONL row, so the self-review path must emit exactly the right number of synthetic rows. If it writes one row per bucket or any fixed small number, the final summary can show the wrong accepted/rejected ratio.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify and test that self-review writes exactly `accepted` rows with `outcome: accepted` and `rejected` rows with `outcome: rejected` before the findings `run-log write`, with no prose-only aggregate rows.


### FINDING_1: Self-review synthetic rows need stable calibration IDs
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Self-review synthetic JSONL rows are underspecified against the run-log record contract: they can satisfy the plan with phase/outcome-only rows, but that shape no longer satisfies the documented v2 review-findings-full schema. Because `difficulty_calibration` drops rows without a stable identity field, the self-review accepted-count fallback becomes unrecoverable even when the final-report tally fallback can still count the rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Require each synthetic self-review row to be a minimal v2 review-findings-full record with a stable id plus schema_version, issue_number, reviewer_slots, round_num, category, and prose_body, while keeping one row per accepted or rejected outcome.`
  - From Cursor-Pragmatic: `In \`write_self_review_tally\`, emit one row per accepted/rejected finding with \`phase: code-review\`, the matching \`outcome\`, \`round_num: 1\`, and a unique \`id\` (for example \`SELF_REVIEW_A1\` / \`SELF_REVIEW_R1\`). Pin the shape in \`test_write_self_review_tally_nonzero_counts\` or a small calibration test.`


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:1076-1099
- **Concern**: [SCOPE-REDUCTION] Self-review synthetic JSONL rows omit the existing `SELF_REVIEW_*` id contract from `self_review_tally.py`. Scenario: The plan emits `phase: code-review` rows with only `outcome`, but `difficulty_calibration._parse_jsonl_source` drops rows without `finding_id`/`id` as malformed. A tolerated tally failure with nonzero self-review counts would still fix the summary ratio yet regress calibration from `accepted_count=0` (today's empty file) to `accepted_count=None`, and audit rows would not match the established `SELF_REVIEW_ACCEPTED_n` / `SELF_REVIEW_REJECTED_n` shape.
- **Proposed resolution**: Build the JSONL from `self_review_tally_items({"mode":"self-review","accepted_count":…,"rejected_count":…})`, emitting one row per item with those ids, `phase: code-review`, `outcome`, and `round_num: "1"` before the `run-log write` subprocess.


