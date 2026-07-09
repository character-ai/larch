## Goal
Implement issue #6673: [IMPLEMENTING] [FEATURE] I-Flush-1: post-flush manifest completeness check; a missing required run-log artifact must be a recorded execution issue, never a silent status string.

## Implementation Plan
## Plan

## Approach

Enforce I-Flush-1 at the existing run-log commit seam. Before `_copy_tree_to_repo`, verify that every required artifact for the staged run is present in the log tree or waived by a category-keyed execution issue in the **committed** execution-issues artifact. Do not backfill historical logs.

**Ordering and short-circuits.** Run the new check only inside `_commit_run`, after all existing early exits (post-merge sentinel, default-branch refusal, placeholder run-id noop, secret scrub errors) and only when the staged `log_root/skill/run_id` tree would actually be copied and committed. **Preserve the empty-run-directory noop (FINDING_3):** call `verify_run_log_completeness` only when `_run_dir(log_root, skill, run_id).is_dir()`; if the run directory is absent, keep the existing early-return path unchanged (shared-only or no-op commits must not regress to `RUN_LOG_INCOMPLETE_RC`).

**Shared reachability.** Move or share `_verify_condition_reached` and its bail helpers (`_final_summary_bail_signal_without_pr_evidence`, `_manifest_step9a1_*`, etc.) into `run_log_manifest.py` (or a sibling module imported by both `run_logs.py` and `run_log_commit.py`) to avoid import cycles. Derive required rows from the same predicates `verify-completeness` uses today; do not introduce simplified step heuristics.

Required artifact model:

- Frozen `RequiredArtifact` row: `slug` (batch slug from `_LARCH_LOG_BATCHES` when applicable), `relative_path`, `skill`, and a reachability condition token evaluated via the shared helpers.
- **Implement** required rows (only when reachability is true):
  - `session-transcript.jsonl` (`slug=session-transcript`) when `step7a` or `step8` reachability is true (same signals as `_verify_condition_reached` for those conditions: `token-report.json`, `timing-report.json`, `execution-issues.ndjson`, `session-transcript.jsonl`, or chained `step8`/`step9a1` evidence).
  - `final-summary.md` when `step8` reachability is true.
  - `review-findings-full.jsonl` (`slug=review-findings-full`) **only** when `code-review-tally.json` exists in the run dir. Do **not** gate on implement `step5` (which chains through `step7a`) and never on `plan-review-tally.json` (always materialized at Step 0).
- **Design** required rows (separate reachability; do not alias implement `step5`):
  - `final-summary.md` when design publish/log-commit evidence exists (non-empty staged design run tree with `manifest.json` and publish-step completion markers).
  - `session-transcript.jsonl` when design transcript capture was attempted (publish/snapshot path ran) unless transcript capture already recorded an execution issue.
  - **Per-round plan-review classification (FINDING_1, FINDING_4, FINDING_5):** when `_design_plan_review_reached(run_dir)` is true, enumerate every `plan-review/round-N/` directory under the staged (published) run tree and emit one `RequiredArtifact` per round for `plan-review/round-N/findings-classification.tsv`. Do **not** treat a single glob hit as sufficient for all rounds. Do **not** require top-level `review-findings-full.jsonl` for design (committed design logs store plan-review bodies under `plan-review/round-N/` per `docs/run-logs.md`).
- Optional telemetry (`token-report.json`, `timing-report.json`, difficulty records, etc.) stays fail-soft.

**Design plan-review reachability (FINDING_4, FINDING_5).** Define `_design_plan_review_reached(run_dir)` from **committed-tree evidence only**: at least one `plan-review/round-*` directory exists under the staged run dir (e.g. presence of `plan-review/round-1/` or any `plan-review/round-N/findings-classification.tsv`). **Do not** key off `.completed/step-3` — the published tree excludes top-level `.completed`, and pause log-publish snapshots may retain that sentinel without any `plan-review/` subtree (`test_pause_log_publish_retains_completed_sentinels`). Requiring classification TSV when only `.completed/step-3` exists would block paths that succeed today.

**Omission waiver matching (FINDING_2).** For each missing required row, accept only a **committed** execution-issues record that names the artifact. Implement logs: `execution-issues.ndjson` under the staged run dir. Design logs: `execution-issues.md` under the staged run dir. **Reject session-local status strings** (`SESSION_TRANSCRIPT_STATUS=write-failed`, live `$TMPDIR/execution-issues.md`, or any pre-commit tmpdir copy) unless rendered into the committed execution-issues artifact at `run_dir`. `artifact_present_or_waived` must parse execution issues from `run_dir` paths only; add a committed-only parse path (or equivalent run-dir-only guard) so stale live tmpdir warnings cannot satisfy the gate before the artifact is staged.

Implement the matcher by reusing `exec_issue_detail.load_issue_detail_groups` / `structured_body_dedupe_keys` for both NDJSON and design markdown bodies. Require:

1. `category` ∈ `_EXECUTION_ISSUE_CATEGORIES` (typically `Warnings` for capture failures).
2. Body text that names the artifact's `slug`, `relative_path`, or canonical filename (e.g. `session-transcript`, `session-transcript.jsonl`, `review-findings-full`, or round-specific `plan-review/round-2/findings-classification.tsv`).

Recognize the **actual capture warning shapes**:

- Implement: `- **Step {label}: session-transcript status={status}:** {message}` from `_capture_transcript_append_warning` in `run_log_flush.py`.
- Design: `design Step {label} session-transcript {status}: {message}` from `_append_transcript_warning` in `design_publish.py`.

Also accept batch-slug mentions tied to `_LARCH_LOG_BATCHES` keys (`session-transcript`, `review-findings-full`).

**Exit codes and refresh surfacing.** Add a distinct `run-log commit` exit code (`RUN_LOG_INCOMPLETE_RC`) and `REFRESH_SKIP_RUN_LOG_INCOMPLETE`. Map that rc in `flush_logs_pre` to `RefreshSkip(reason=REFRESH_SKIP_RUN_LOG_INCOMPLETE, error=...)`; reserve `REFRESH_SKIP_COMMIT_FAILED` for other commit failures. Teach `refresh_run_logs_main` to print `REFRESH_COMMITTED=false REASON=run-log-incomplete ERROR=...` (same branch as `REFRESH_SKIP_COMMIT_FAILED`). Return the incompleteness rc from `larch_log_flush_main` after emitting the warning. Do not add `REFRESH_SKIP_RUN_LOG_INCOMPLETE` to `REFRESH_SKIP_MERGE_OK` or `REFRESH_SKIP_POST_ENSURE_PR_OK`.

Rewire `verify_completeness_main` to consume the shared required-row helpers where practical, preserving stdout grammar `OK` / `MISSING=...`.

## Files to modify/create

### UPDATED: ARCHITECTURAL_INVARIANTS.md

Append the requested `## Run-log integrity` section after `## Workflow integrity`.

Keep the text byte-identical to the feature description.

### UPDATED: python/larch/core/config.py

Add `RUN_LOG_INCOMPLETE_RC` (distinct documented exit code for required-artifact omissions).

Add `REFRESH_SKIP_RUN_LOG_INCOMPLETE = "run-log-incomplete"`.

Do not add the new skip reason to `REFRESH_SKIP_MERGE_OK` or `REFRESH_SKIP_POST_ENSURE_PR_OK`.

### UPDATED: python/larch/report/run_log_manifest.py

Add shared completeness surface (avoid import cycles with `run_logs.py`):

- `@dataclass(frozen=True) RequiredArtifact` with `slug`, `relative_path`, `skill`, `condition`.
- Move or re-export `_verify_condition_reached` and bail helpers here from `run_logs.py` (or import from a new `run_log_reachability.py` colocated under `larch/report/`).
- `_design_plan_review_reached(run_dir)` → true only when the staged run dir contains at least one `plan-review/round-*` directory (published-tree evidence). **No** `.completed/step-3` predicate.
- `_design_publish_reached(run_dir)` for final-summary/transcript gating on design runs.
- `_design_plan_review_round_dirs(run_dir) -> list[Path]` — sorted enumeration of every `plan-review/round-N/` under the staged tree.
- `_implement_code_review_voting_reached(run_dir)` → `_verify_has_file(..., "code-review-tally.json")` only.
- `required_artifacts_for_run(*, run_dir, skill, manifest) -> list[RequiredArtifact]` applying reachability before emitting rows; for design plan-review, emit one row per discovered round directory.
- `artifact_present_or_waived(*, run_dir, artifact, execution_issues_path) -> bool` using **run-dir-only** `exec_issue_detail` parsers and slug/filename/round-path matching rules above.
- `_load_committed_execution_issues(run_dir, skill) -> ...` — parse only `run_dir/execution-issues.ndjson` or `run_dir/execution-issues.md`; never consult session tmpdir paths.
- `verify_run_log_completeness(*, run_dir, skill) -> tuple[bool, list[str]]` returning `(True, [])` or `(False, missing_descriptions)`.

Keep schema evolution additive; missing optional artifacts must not fail.

### UPDATED: python/larch/report/run_log_commit.py

After existing refusal/placeholder/scrub short-circuits and before `_copy_tree_to_repo`:

- If `not _run_dir(log_root, skill, run_id).is_dir()`, skip completeness and keep the existing noop/early-return behavior unchanged.
- Otherwise call `verify_run_log_completeness` against `log_root/skill/run_id`.

On failure, return `CommandResult` with `RUN_LOG_INCOMPLETE_RC` and terse stderr listing missing artifacts (slug/path per row).

Keep placeholder run-id, default-branch refusal, secret scrub, and volatile-only behavior unchanged.

### UPDATED: python/larch/report/run_log_flush.py

Thread the new commit result through `flush_logs_pre`, `refresh_run_logs_main`, and `larch_log_flush_main`:

- In `flush_logs_pre`, when `_commit_run.returncode == RUN_LOG_INCOMPLETE_RC`, return `RefreshSkip(skipped=True, reason=REFRESH_SKIP_RUN_LOG_INCOMPLETE, error=stderr)`.
- Keep `REFRESH_SKIP_COMMIT_FAILED` for all other nonzero commit results.
- In `refresh_run_logs_main`, include `REFRESH_SKIP_RUN_LOG_INCOMPLETE` in the `REFRESH_COMMITTED=false` branch beside `REFRESH_SKIP_COMMIT_FAILED` and `REFRESH_SKIP_RECOVERY_FAILED`; print `ERROR=` when `skip.error` is non-empty.
- In `larch_log_flush_main`, after printing the warning on incompleteness, **return** `RUN_LOG_INCOMPLETE_RC` (not `0`).

### UPDATED: python/larch/report/run_logs.py

Re-import reachability helpers from the shared module instead of owning duplicate logic.

Rewire `verify_completeness_main` to delegate required-row derivation to shared helpers where compatible with `docs/run-logs-required-files.tsv` conditions.

Preserve stdout grammar: `OK` or `MISSING=...`.

### UPDATED: python/tests/report/test_run_log_flush.py

Add focused regression coverage with monkeypatched git commit/copy seams (no real git mutations):

1. **Green path:** seed step7a reachability (`token-report.json` or `final-summary.md`), all required artifacts present; commit proceeds unchanged.
2. **Recorded omission:** seed step7a reachability, omit `session-transcript.jsonl`, write committed `execution-issues.ndjson` using the exact body shape from `_capture_transcript_append_warning` (category `Warnings`, mentions `session-transcript`); commit proceeds.
3. **Silent omission:** seed step7a reachability, omit `session-transcript.jsonl`, no execution-issues entry; commit fails with `RUN_LOG_INCOMPLETE_RC`.
4. **#6263-shaped path:** seed step7a reachability, omit transcript, set session-local `SESSION_TRANSCRIPT_STATUS=write-failed` only (not in committed execution-issues); commit fails with `RUN_LOG_INCOMPLETE_RC`.
5. **Implement review gate:** `code-review-tally.json` present, `review-findings-full.jsonl` absent, no waiver → fail; with `step7a` evidence but **no** `code-review-tally.json` → transcript/final-summary rules apply, findings file not required.
6. **Refresh mapping:** incompleteness rc maps to `REFRESH_SKIP_RUN_LOG_INCOMPLETE`, not `REFRESH_SKIP_COMMIT_FAILED`; `refresh_run_logs_main` emits `REFRESH_COMMITTED=false REASON=run-log-incomplete ERROR=...`.
7. **Flush rc:** `larch_log_flush_main` returns nonzero on incompleteness.
8. **Empty run dir noop (FINDING_3):** when `log_root/skill/run_id` is not a directory, commit path unchanged (no `RUN_LOG_INCOMPLETE_RC`).
9. **Committed-only waiver (FINDING_2):** live tmpdir `execution-issues.md` names missing artifact but staged run dir has no committed entry → commit fails.

Each transcript-gate test must seed reachability first so the gate is not vacuous.

### UPDATED: python/tests/report/test_run_logs.py

Add unit coverage for `artifact_present_or_waived` using real capture warning bodies (implement NDJSON and design markdown).

Add design reachability tests using a **published-tree fixture without `.completed`**:

- `plan-review/round-1/findings-classification.tsv` present → round-1 TSV required; no top-level `review-findings-full.jsonl`.
- **Multi-round (FINDING_1):** `round-1` and `round-2` directories present, only `round-1/findings-classification.tsv` exists, no waiver → `verify_run_log_completeness` fails naming `round-2`.
- `.completed/step-3` present without any `plan-review/round-*` → `_design_plan_review_reached` false; no classification TSV required.

Add test that live tmpdir execution-issues path is ignored when committed artifact lacks the waiver.

Update existing `verify_completeness` expectations only if shared helper imports change behavior.

## Edge cases

- Missing artifact with an execution issue that does not name the slug/path/filename must fail.
- Empty or malformed committed execution-issues files must not satisfy the check.
- Prior committed logs are not scanned or backfilled.
- Optional token/timing telemetry must not become required.
- Implement `plan-review-tally.json` must never trigger `review-findings-full.jsonl` requirement.
- Runs that reached Step 7a without code review must not require `review-findings-full.jsonl`.
- Design logs use `execution-issues.md`; implement logs use `execution-issues.ndjson`.
- Generic execution-issue category without artifact-specific body text must not waive.
- Multi-round design review: each `plan-review/round-N/` must have its own `findings-classification.tsv` or a round-specific waiver.
- Absent `log_root/skill/run_id` directory must not trigger incompleteness (preserve noop).
- Design pause snapshots with `.completed/step-3` but no `plan-review/` must not require classification files.

## Failure modes

- Import cycles if completeness helpers import `run_logs.py` commit paths. Keep shared logic in `run_log_manifest.py` (or `run_log_reachability.py`) below both callers.
- Over-broad reachability can block legitimate early bailouts. Gate each row only when shared bail-aware predicates say the phase ran.
- Over-loose omission matching can accept placeholder JSON. Require category + artifact-specific body text via committed `exec_issue_detail` parsing.
- Reading waivers from live tmpdir before commit can false-pass silent omissions. Enforce run-dir-only execution-issues reads.
- Running completeness on missing run dir regresses shared-only noop commits. Guard with `is_dir()` before verify.
- Using `.completed/step-3` for design reachability blocks pause log-publish paths. Use published `plan-review/round-*` only.
- Single-round glob satisfying multi-round requirement loses classification data. Enumerate all round directories.
- Collapsing incompleteness into `REFRESH_SKIP_COMMIT_FAILED` hides diagnostics. Use dedicated skip reason and refresh envelope branch.
- Returning `0` from `larch_log_flush_main` on incompleteness defeats the new exit code. Propagate `RUN_LOG_INCOMPLETE_RC`.
- Requiring design `review-findings-full.jsonl` would block every design publish. Use per-round `findings-classification.tsv` only.

## Testing strategy

Run focused tests only:

- `python3 -m pytest python/tests/report/test_run_log_flush.py`
- `python3 -m pytest python/tests/report/test_run_logs.py -k "verify_completeness or artifact_present_or_waived or design_plan_review"`

Then run changed-file lint if available:

- `make py-lint`

Do not run broad harnesses unless shell or skill prompts change.

## Acceptance

Run focused tests only:

- `python3 -m pytest python/tests/report/test_run_log_flush.py`
- `python3 -m pytest python/tests/report/test_run_logs.py -k "verify_completeness or artifact_present_or_waived or design_plan_review"`

Then run changed-file lint if available:

- `make py-lint`

Do not run broad harnesses unless shell or skill prompts change.

diff_lines: 580

## Test plan
(no test plan section in plan-file)
