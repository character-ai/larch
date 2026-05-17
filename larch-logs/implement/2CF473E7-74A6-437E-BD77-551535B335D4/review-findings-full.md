### FINDING_1: panel [plan-review/accepted]

## CLI contract vs Step 7a invocation mismatch

The plan defines `--log-file PATH` and `--skill implement` in the helper's CLI contract, but the Step 7a SKILL.md invocation snippet omits both. If the implementation enforces its contract, every pre-bump flush fails before flushing. `--log-file` also has no defined purpose in the behavior section.

Vote: YES/NO/EXONERATE
FINDING_1: <vote>

### FINDING_10: panel [plan-review/accepted]

## Exit 0 CI_PASSED=true bullet still references Step 11 refresh

SKILL.md's ship-pr.sh Exit 0 handling (line 1709) still explicitly says "refresh execution-issues summaries and larch-log batches using the Step 11 contract" when CI_PASSED=true. The plan updates the "Execution-issues checkpoint" paragraph but does not rewrite this specific Exit 0 bullet, leaving contradictory orchestrator instructions.

Vote: YES/NO/EXONERATE
FINDING_10: <vote>

### FINDING_11: panel [plan-review/accepted]

## SKILL.md batch mapping table omits execution-issues for Step 7a

The batch mapping table at SKILL.md line 757 says Step 7a tail writes only `token-report`, `timing-report`, and a log-flush commit. After the pre-bump flush is added, this table would need an `execution-issues` entry or consumers will have contradictory guidance about when execution-issues hits the run log.

Vote: YES/NO/EXONERATE
FINDING_11: <vote>

### FINDING_2: panel [plan-review/accepted]

## warn_line not provided by lib-quiet.sh

The plan says sourcing `lib-quiet.sh` makes `warn_line` available for `write_execution_issues_records`. `warn_line` is defined locally in `implement-finalize.sh` (lines 379-382), not in `lib-quiet.sh`. After extraction, the shared library would call an undefined function on the jq/python fallback warning path.

Vote: YES/NO/EXONERATE
FINDING_2: <vote>

### FINDING_3: panel [plan-review/accepted]

## test-implement-finalize.sh sandbox missing lib-execution-issues.sh

The existing `scripts/test-implement-finalize.sh` harness copies only `implement-finalize.sh` and `lib-quiet.sh` into its sandbox. After the extraction of five functions to `lib-execution-issues.sh`, the sandboxed `implement-finalize.sh` will fail to source the new library. The plan does not update this harness or add it to the "Files changed" list.

Vote: YES/NO/EXONERATE
FINDING_3: <vote>

### FINDING_4: panel [plan-review/accepted]

## APPEND_LOG cannot safely carry multi-line larch-log output

The plan emits `APPEND_LOG=<capture>` where capture is full stdout+stderr from `larch-log.sh append`. `larch-log.sh` emits multi-line `KEY=value` output (LOG_WRITTEN, LOG_PATH, BYTES, SHA256, etc.). `emit_kv` does not escape newlines, so those lines would appear as extra top-level key-value records in the helper's stdout envelope, corrupting downstream parsers.

Vote: YES/NO/EXONERATE
FINDING_4: <vote>

### FINDING_5: panel [plan-review/accepted]

## write_execution_issues_records hardcodes step:"18" and safety-net source

The existing `write_execution_issues_records` function hardcodes `"step":"18"` and `"source":"execution-issues.md safety-net"` in every NDJSON record. If the pre-bump flush helper reuses this function unchanged, normal-path records would appear as teardown safety-net records in the audit log, weakening traceability and confusing dedup checks.

Vote: YES/NO/EXONERATE
FINDING_5: <vote>

### FINDING_7: panel [plan-review/accepted]

## Wrong stub doc path (scripts/ vs skills/implement/scripts/)

Plan Steps 1 and 8 reference `scripts/flush-execution-issues.md` as a stub path, but the "Files changed" table correctly places the contract at `skills/implement/scripts/flush-execution-issues.md`. There is no `scripts/flush-execution-issues.md` in the repo. This is internally inconsistent and would produce broken links or a missing file.

Vote: YES/NO/EXONERATE
FINDING_7: <vote>

### FINDING_8: panel [plan-review/accepted]

## set -e leakage from write_execution_issues_records python path

In the current `write_execution_issues_records` implementation, the no-jq python fallback path runs `set +e` before the python call, then `set -e` after it — but the final `set -e` executes unconditionally even on the success path. When this function is extracted to a sourced library, the host script could inherit errexit enabled, violating the file-wide best-effort no-errexit model.

Vote: YES/NO/EXONERATE
FINDING_8: <vote>

### FINDING_9: panel [plan-review/accepted]

## Failure logging should use append-tool-failure.sh not append-execution-issue.sh

The existing Step 11 contract and Step 7a pre-bump tail both specify `append-tool-failure.sh` (with `--output-file`, `--site`, `--tool`, `--exit-code`, `--redact`) for non-zero `larch-log.sh` failures. The plan instead uses `append-execution-issue.sh` with a one-line `--entry`, losing verbatim capture and the established redaction pipeline.

Vote: YES/NO/EXONERATE
FINDING_9: <vote>

### REJ_P1: FINDING_12 [plan-review/rejected]



### REJ_P2: FINDING_6 [plan-review/rejected]



### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/scripts/flush-execution-issues.sh:107-170`: the helper emits `APPEND_LOG_FILE=<append_log_tmp>` on compose failure, append success, and append failure, but the `EXIT` trap deletes that same file before the caller can inspect it. This contradicts the plan’s contract to capture `larch-log.sh append` stdout/stderr to a temp log file and emit its path; a failed append reports a path that no longer exists after process exit, breaking diagnostics and any caller that follows the envelope. Fix by only deleting `record_file` in the trap, or by preserving `append_log_tmp` whenever it is emitted.

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** `correctness` `skills/implement/scripts/flush-execution-issues.sh:107-170`: the helper emits `APPEND_LOG_FILE=<append_log_tmp>` on compose failure, append success, and append failure, but the `EXIT` trap deletes that same file before the caller can inspect it. This contradicts the plan’s contract to capture `larch-log.sh append` stdout/stderr to a temp log file and emit its path; a failed append reports a path that no longer exists after process exit, breaking diagnostics and any caller that follows the envelope. Fix by only deleting `record_file` in the trap, or by preserving `append_log_tmp` whenever it is emitted.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `correctness` — `skills/implement/SKILL.md:1657-1675`, `scripts/implement-finalize.sh:455-882`, `scripts/ship-pr.sh:555-875`, `scripts/larch-log-flush.sh:30-34`: the new flush only runs at Step 7a, but multiple later paths still append to `$IMPLEMENT_TMPDIR/execution-issues.md` after that point. A postbump/changelog/rebase warning can be added after the pre-bump flush, then never reach the committed `execution-issues.ndjson` because Step 18’s safety net appends after the last normal log commit and post-merge commits are suppressed. Reuse `flush-execution-issues.sh` from a central pre-commit/pre-push log path such as `larch-log-flush.sh` or `refresh-run-logs.sh`, or make the later append sites write NDJSON immediately before the next log commit.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 1. **Important** `correctness` — `skills/implement/SKILL.md:1657-1675`, `scripts/implement-finalize.sh:455-882`, `scripts/ship-pr.sh:555-875`, `scripts/larch-log-flush.sh:30-34`: the new flush only runs at Step 7a, but multiple later paths still append to `$IMPLEMENT_TMPDIR/execution-issues.md` after that point. A postbump/changelog/rebase warning can be added after the pre-bump flush, then never reach the committed `execution-issues.ndjson` because Step 18’s safety net appends after the last normal log commit and post-merge commits are suppressed. Reuse `flush-execution-issues.sh` from a central pre-commit/pre-push log path such as `larch-log-flush.sh` or `refresh-run-logs.sh`, or make the later append sites write NDJSON immediately before the next log commit.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** `risk-integration` — `skills/implement/SKILL.md:1657-1675`, `skills/implement/SKILL.md:1722-1732`: moving the execution-issues flush to Step 7a and removing the `CI_PASSED=true` refresh leaves later entries uncommitted. Concrete scenario: `scripts/implement-finalize.sh:451-482` can append Step 8 postbump warnings after the new Step 7a flush, while `scripts/refresh-run-logs.sh:58-68` only refreshes token/timing batches, so the PR can merge without those execution issues in `larch-logs/implement/<RUN_ID>/execution-issues.ndjson`. Add an execution-issues flush before any later log commit/push that can follow post-Step-7a appends, or move/reorder the pre-push refresh so it runs after postbump execution-issues writers.

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** `risk-integration` — `skills/implement/SKILL.md:1657-1675`, `skills/implement/SKILL.md:1722-1732`: moving the execution-issues flush to Step 7a and removing the `CI_PASSED=true` refresh leaves later entries uncommitted. Concrete scenario: `scripts/implement-finalize.sh:451-482` can append Step 8 postbump warnings after the new Step 7a flush, while `scripts/refresh-run-logs.sh:58-68` only refreshes token/timing batches, so the PR can merge without those execution issues in `larch-logs/implement/<RUN_ID>/execution-issues.ndjson`. Add an execution-issues flush before any later log commit/push that can follow post-Step-7a appends, or move/reorder the pre-push refresh so it runs after postbump execution-issues writers.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-155`, `skills/implement/scripts/test-flush-execution-issues.sh:141-149`: the helper emits `APPEND_LOG_FILE=<path>` after a successful append, but the `EXIT` trap deletes that same file before the caller can inspect it. The contract documents `APPEND_LOG_FILE` as part of the output envelope, so a caller or debugging harness following that path gets a dead filename even on `FLUSH_STATUS=ok`. Add a test that parses `APPEND_LOG_FILE` and asserts it exists/readable after success and failure, then either stop deleting `append_log_tmp` when emitted or remove the field from the contract/output.

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: 1. **Important** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-155`, `skills/implement/scripts/test-flush-execution-issues.sh:141-149`: the helper emits `APPEND_LOG_FILE=<path>` after a successful append, but the `EXIT` trap deletes that same file before the caller can inspect it. The contract documents `APPEND_LOG_FILE` as part of the output envelope, so a caller or debugging harness following that path gets a dead filename even on `FLUSH_STATUS=ok`. Add a test that parses `APPEND_LOG_FILE` and asserts it exists/readable after success and failure, then either stop deleting `append_log_tmp` when emitted or remove the field from the contract/output.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Latent** `correctness` — `scripts/lib-execution-issues.sh:67-84`, `scripts/lib-execution-issues.sh:95-112`, `skills/implement/SKILL.md:1657-1669`: moving the flush to Step 7a exposes the existing per-section hash dedupe to duplicate old content when a category receives later entries. Scenario: Step 7a logs `Tool Failures` entry A, later Step 9 appends entry B under the same `### Tool Failures` header, then Step 18 hashes the combined A+B section and appends a second record containing A again because the batch only has hash(A). Fix by deduping at entry granularity or recording/rewriting only unflushed tail entries after the pre-bump flush.

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: 2. **Latent** `correctness` — `scripts/lib-execution-issues.sh:67-84`, `scripts/lib-execution-issues.sh:95-112`, `skills/implement/SKILL.md:1657-1669`: moving the flush to Step 7a exposes the existing per-section hash dedupe to duplicate old content when a category receives later entries. Scenario: Step 7a logs `Tool Failures` entry A, later Step 9 appends entry B under the same `### Tool Failures` header, then Step 18 hashes the combined A+B section and appends a second record containing A again because the batch only has hash(A). Fix by deduping at entry granularity or recording/rewriting only unflushed tail entries after the pre-bump flush.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Latent** `correctness` — `skills/implement/scripts/flush-execution-issues.sh:103-111`, `skills/implement/scripts/flush-execution-issues.sh:151-169`: `APPEND_LOG_FILE` points at `append_log_tmp`, but the `EXIT` trap deletes that file before callers can inspect it. On append failure or success, automation receives a path that no longer exists, contradicting the helper contract and making diagnostics harder. Keep the append log file when emitting `APPEND_LOG_FILE`, and only clean up `record_file`.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 2. **Latent** `correctness` — `skills/implement/scripts/flush-execution-issues.sh:103-111`, `skills/implement/scripts/flush-execution-issues.sh:151-169`: `APPEND_LOG_FILE` points at `append_log_tmp`, but the `EXIT` trap deletes that file before callers can inspect it. On append failure or success, automation receives a path that no longer exists, contradicting the helper contract and making diagnostics harder. Keep the append log file when emitting `APPEND_LOG_FILE`, and only clean up `record_file`.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Latent** `correctness` — `skills/implement/scripts/flush-execution-issues.sh:107-156`: the helper emits `APPEND_LOG_FILE`, but the EXIT trap deletes that same file before the caller can read it. Scenario: a successful append emits `APPEND_LOG_FILE=/tmp/.../flush-execution-issues-append.X`, then `cleanup()` removes it on exit, so any caller following the output contract gets a dead path. Fix by not deleting `append_log_tmp` when it is emitted, or only emit paths that are intentionally preserved.

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: 1. **Latent** `correctness` — `skills/implement/scripts/flush-execution-issues.sh:107-156`: the helper emits `APPEND_LOG_FILE`, but the EXIT trap deletes that same file before the caller can read it. Scenario: a successful append emits `APPEND_LOG_FILE=/tmp/.../flush-execution-issues-append.X`, then `cleanup()` removes it on exit, so any caller following the output contract gets a dead path. Fix by not deleting `append_log_tmp` when it is emitted, or only emit paths that are intentionally preserved.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Latent** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:153-169`: the helper emits `APPEND_LOG_FILE=<path>` but its `EXIT` trap deletes that file before callers can inspect it. A wrapper that follows the documented envelope after `FLUSH_STATUS=failed` gets a dead path, losing the captured `larch-log.sh append` diagnostics outside the markdown entry. Preserve `append_log_tmp` whenever it is emitted, or stop emitting the path after cleanup.

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: 2. **Latent** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:153-169`: the helper emits `APPEND_LOG_FILE=<path>` but its `EXIT` trap deletes that file before callers can inspect it. A wrapper that follows the documented envelope after `FLUSH_STATUS=failed` gets a dead path, losing the captured `larch-log.sh append` diagnostics outside the markdown entry. Preserve `append_log_tmp` whenever it is emitted, or stop emitting the path after cleanup.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Nit** `code-quality` — `docs/run-logs.md:111-113`, `scripts/implement-finalize.md:111-121`: the docs still describe Step 11 as the final execution-issues flush after CI, while the implementation moved that flush to Step 7a and removed the post-CI checkpoint. This leaves the shipped contract inconsistent with runtime behavior. Update these references to Step 7a plus the Step 18 safety net.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 3. **Nit** `code-quality` — `docs/run-logs.md:111-113`, `scripts/implement-finalize.md:111-121`: the docs still describe Step 11 as the final execution-issues flush after CI, while the implementation moved that flush to Step 7a and removed the post-CI checkpoint. This leaves the shipped contract inconsistent with runtime behavior. Update these references to Step 7a plus the Step 18 safety net.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** [correctness] `skills/implement/scripts/flush-execution-issues.sh:103-156`: the helper emits `APPEND_LOG_FILE=<append_log_tmp>` but its `EXIT` trap deletes that same file before the caller can inspect it. This violates the plan’s output-envelope contract and makes the emitted diagnostic path stale on both successful and failed append attempts. Preserve the append log when its path is emitted, or stop emitting `APPEND_LOG_FILE` for files cleaned up during exit.

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** [correctness] `skills/implement/scripts/flush-execution-issues.sh:103-156`: the helper emits `APPEND_LOG_FILE=<append_log_tmp>` but its `EXIT` trap deletes that same file before the caller can inspect it. This violates the plan’s output-envelope contract and makes the emitted diagnostic path stale on both successful and failed append attempts. Preserve the append log when its path is emitted, or stop emitting `APPEND_LOG_FILE` for files cleaned up during exit.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/SKILL.md:1722-1732` — Removing the `CI_PASSED=true` Step 11 refresh leaves post-7a `execution-issues.md` entries with no committed flush path in the branch diff. For example, `scripts/ship-pr.sh` can append PR-prep / diagram / tool-failure warnings after the new Step 7a pre-bump flush, but the committed branch only re-invokes `ship-pr.sh --resume-phase ci-merge` after CI and Step 18’s safety-net append is not followed by a log commit. Keep a later committed flush path for entries created after Step 7a, or wire execution-issues flushing into the existing pre-push/commit-tail log refresh paths before removing the CI checkpoint.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 1. **Important** `correctness` `skills/implement/SKILL.md:1722-1732` — Removing the `CI_PASSED=true` Step 11 refresh leaves post-7a `execution-issues.md` entries with no committed flush path in the branch diff. For example, `scripts/ship-pr.sh` can append PR-prep / diagram / tool-failure warnings after the new Step 7a pre-bump flush, but the committed branch only re-invokes `ship-pr.sh --resume-phase ci-merge` after CI and Step 18’s safety-net append is not followed by a log commit. Keep a later committed flush path for entries created after Step 7a, or wire execution-issues flushing into the existing pre-push/commit-tail log refresh paths before removing the CI checkpoint.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:153-169`: the script emits `APPEND_LOG_FILE=<path>` after append attempts, but the EXIT trap deletes that same temp file before any caller can read it. A failing `larch-log.sh append` run will report a diagnostic path that no longer exists, defeating the contract and hiding useful CI/debug output. Preserve `append_log_tmp` whenever it is emitted, or stop emitting it; add assertions in `skills/implement/scripts/test-flush-execution-issues.sh:141-206` that the reported `APPEND_LOG_FILE` exists and is readable after the helper exits.

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: 1. **Important** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:153-169`: the script emits `APPEND_LOG_FILE=<path>` after append attempts, but the EXIT trap deletes that same temp file before any caller can read it. A failing `larch-log.sh append` run will report a diagnostic path that no longer exists, defeating the contract and hiding useful CI/debug output. Preserve `append_log_tmp` whenever it is emitted, or stop emitting it; add assertions in `skills/implement/scripts/test-flush-execution-issues.sh:141-206` that the reported `APPEND_LOG_FILE` exists and is readable after the helper exits.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** correctness, plan-correctness, source=plan, `skills/implement/scripts/flush-execution-issues.sh:107-110` and `skills/implement/scripts/flush-execution-issues.sh:151-170`: `APPEND_LOG_FILE` points to a temp file that the EXIT trap deletes before callers can read it. Concrete scenario: if `larch-log.sh append` exits 1, the helper emits `APPEND_LOG_FILE=/tmp/.../flush-execution-issues-append.X`, then exits and `cleanup()` removes that file, so the advertised diagnostics path is dead. Preserve the append log whenever its path is emitted, or stop emitting a path that is removed.

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: 1. **Important** correctness, plan-correctness, source=plan, `skills/implement/scripts/flush-execution-issues.sh:107-110` and `skills/implement/scripts/flush-execution-issues.sh:151-170`: `APPEND_LOG_FILE` points to a temp file that the EXIT trap deletes before callers can read it. Concrete scenario: if `larch-log.sh append` exits 1, the helper emits `APPEND_LOG_FILE=/tmp/.../flush-execution-issues-append.X`, then exits and `cleanup()` removes that file, so the advertised diagnostics path is dead. Preserve the append log whenever its path is emitted, or stop emitting a path that is removed.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Important** correctness, plan-correctness, source=plan, `skills/implement/scripts/flush-execution-issues.sh:151-156` and `scripts/lib-execution-issues.sh:67-84`: a successful pre-bump flush leaves the already-flushed markdown in `execution-issues.md`, so later same-category appends produce duplicate records instead of only the new tail. Concrete scenario: Step 7a flushes `### Warnings\n- A`; postbump later appends `- B` under the same `Warnings` header; Step 18 sees a changed file, computes a new section hash for `A+B`, and appends a second record containing both `A` and `B`, duplicating `A` in the NDJSON batch. Truncate or rotate `execution-issues.md` after a successful/no-record flush, or persist enough per-entry state to emit only the newly appended tail.

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: 2. **Important** correctness, plan-correctness, source=plan, `skills/implement/scripts/flush-execution-issues.sh:151-156` and `scripts/lib-execution-issues.sh:67-84`: a successful pre-bump flush leaves the already-flushed markdown in `execution-issues.md`, so later same-category appends produce duplicate records instead of only the new tail. Concrete scenario: Step 7a flushes `### Warnings\n- A`; postbump later appends `- B` under the same `Warnings` header; Step 18 sees a changed file, computes a new section hash for `A+B`, and appends a second record containing both `A` and `B`, duplicating `A` in the NDJSON batch. Truncate or rotate `execution-issues.md` after a successful/no-record flush, or persist enough per-entry state to emit only the newly appended tail.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Latent** `correctness` `skills/implement/scripts/flush-execution-issues.sh:107-155` — The helper emits `APPEND_LOG_FILE=<append_log_tmp>` but the `EXIT` trap deletes that file before callers can inspect it. Any caller or operator following the output envelope gets a dead path even on successful append or composition failure. Preserve emitted append logs, or stop emitting `APPEND_LOG_FILE` except for files that intentionally survive process exit.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 2. **Latent** `correctness` `skills/implement/scripts/flush-execution-issues.sh:107-155` — The helper emits `APPEND_LOG_FILE=<append_log_tmp>` but the `EXIT` trap deletes that file before callers can inspect it. Any caller or operator following the output envelope gets a dead path even on successful append or composition failure. Preserve emitted append logs, or stop emitting `APPEND_LOG_FILE` except for files that intentionally survive process exit.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Latent** `risk-integration` `skills/implement/scripts/flush-execution-issues.sh:104-106`: `APPEND_LOG_FILE=<path>` is emitted on compose/append paths, but the EXIT trap deletes that temp file before callers can inspect it. A failed `larch-log.sh append` can report a diagnostic path that is already gone, weakening failure recovery and making the output envelope misleading. Preserve the append log when its path is emitted, or stop emitting `APPEND_LOG_FILE`.

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: 1. **Latent** `risk-integration` `skills/implement/scripts/flush-execution-issues.sh:104-106`: `APPEND_LOG_FILE=<path>` is emitted on compose/append paths, but the EXIT trap deletes that temp file before callers can inspect it. A failed `larch-log.sh append` can report a diagnostic path that is already gone, weakening failure recovery and making the output envelope misleading. Preserve the append log when its path is emitted, or stop emitting `APPEND_LOG_FILE`.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Nit** [correctness] `skills/implement/scripts/flush-execution-issues.sh:80-100` and `scripts/lib-execution-issues.sh:68-83`: the planned batch idempotency probe checks for the whole-file SHA, but the jq record writer stores normalized per-section SHAs in `source_sha256`. If the sentinel is missing but the batch already contains the records, the helper falls through and reports `FLUSH_STATUS=no-records` instead of the planned `already-flushed`. Align the top-level batch probe with the actual stored hashes, or store a whole-file marker that the probe can find.

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Nit** [correctness] `skills/implement/scripts/flush-execution-issues.sh:80-100` and `scripts/lib-execution-issues.sh:68-83`: the planned batch idempotency probe checks for the whole-file SHA, but the jq record writer stores normalized per-section SHAs in `source_sha256`. If the sentinel is missing but the batch already contains the records, the helper falls through and reports `FLUSH_STATUS=no-records` instead of the planned `already-flushed`. Align the top-level batch probe with the actual stored hashes, or store a whole-file marker that the probe can find.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** [correctness] `scripts/larch-log-flush.sh:30-40`, `scripts/refresh-run-logs.sh:56-68` — Completeness w.r.t plan, source=requirements: post-7a tail flushing only runs when a sentinel or existing `execution-issues.ndjson` batch already exists, so the first execution issue created after an empty Step 7a checkpoint is never flushed before the next log commit. Concrete scenario: Step 7a sees no `execution-issues.md` and exits `FLUSH_STATUS=skip`, creating no sentinel/batch; later `postbump` or CI handling appends a warning; the commit-tail/pre-push guards both evaluate false and skip `flush-execution-issues.sh`, so the PR’s committed run log never receives that issue. Add an explicit “Step 7a checkpoint reached” marker even on skip, or otherwise let post-7a paths flush any non-empty `execution-issues.md` without requiring a prior batch.

- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: 1. **Important** [correctness] `scripts/larch-log-flush.sh:30-40`, `scripts/refresh-run-logs.sh:56-68` — Completeness w.r.t plan, source=requirements: post-7a tail flushing only runs when a sentinel or existing `execution-issues.ndjson` batch already exists, so the first execution issue created after an empty Step 7a checkpoint is never flushed before the next log commit. Concrete scenario: Step 7a sees no `execution-issues.md` and exits `FLUSH_STATUS=skip`, creating no sentinel/batch; later `postbump` or CI handling appends a warning; the commit-tail/pre-push guards both evaluate false and skip `flush-execution-issues.sh`, so the PR’s committed run log never receives that issue. Add an explicit “Step 7a checkpoint reached” marker even on skip, or otherwise let post-7a paths flush any non-empty `execution-issues.md` without requiring a prior batch.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Nit** correctness, `skills/implement/scripts/flush-execution-issues.sh:95-100` and `scripts/lib-execution-issues.sh:67-84`: the planned existing-batch idempotency check looks for the full issue-log SHA, but the jq record path stores per-section normalized SHAs. If the sentinel is missing but the batch already contains records produced by this helper, the explicit Step 4 `already-flushed` path does not recognize them and the helper falls through to composition, usually returning `no-records` instead of the planned `already-flushed`. Align the batch probe with the hashes actually written, or write/probe the full-file SHA consistently.

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Nit** correctness, `skills/implement/scripts/flush-execution-issues.sh:95-100` and `scripts/lib-execution-issues.sh:67-84`: the planned existing-batch idempotency check looks for the full issue-log SHA, but the jq record path stores per-section normalized SHAs. If the sentinel is missing but the batch already contains records produced by this helper, the explicit Step 4 `already-flushed` path does not recognize them and the helper falls through to composition, usually returning `no-records` instead of the planned `already-flushed`. Align the batch probe with the hashes actually written, or write/probe the full-file SHA consistently.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `correctness` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:151-169`: the helper emits `APPEND_LOG_FILE=<path>` but the `EXIT` trap deletes that same temp file before callers can inspect it. A failed `larch-log.sh append` returns a diagnostic path that is already gone, making the output envelope misleading and breaking the documented debugging contract. Preserve the append log when it is emitted, or stop emitting `APPEND_LOG_FILE` for files the helper cleans up.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 1. **Important** `correctness` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:151-169`: the helper emits `APPEND_LOG_FILE=<path>` but the `EXIT` trap deletes that same temp file before callers can inspect it. A failed `larch-log.sh append` returns a diagnostic path that is already gone, making the output envelope misleading and breaking the documented debugging contract. Preserve the append log when it is emitted, or stop emitting `APPEND_LOG_FILE` for files the helper cleans up.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** `risk-integration` `skills/implement/SKILL.md:1722-1732`: The new green-CI path removes the post-CI execution-issues flush but does not add another committed flush for entries appended after Step 7a. A concrete failure is any Step 8/9/10/12 warning or CI/tool failure appended to `$IMPLEMENT_TMPDIR/execution-issues.md` after the pre-bump flush: `CI_PASSED=true` now immediately resumes `ci-merge`, and Step 18 only appends to the tmpdir log without a `larch-log.sh commit`, so the merged PR can miss those execution records. Fix by either keeping a final pre-merge execution-issues flush/commit when `CI_PASSED=true`, or wiring the new helper into the pre-push/log-refresh paths that actually commit before merge.

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/implement/SKILL.md:1722-1732`: The new green-CI path removes the post-CI execution-issues flush but does not add another committed flush for entries appended after Step 7a. A concrete failure is any Step 8/9/10/12 warning or CI/tool failure appended to `$IMPLEMENT_TMPDIR/execution-issues.md` after the pre-bump flush: `CI_PASSED=true` now immediately resumes `ci-merge`, and Step 18 only appends to the tmpdir log without a `larch-log.sh commit`, so the merged PR can miss those execution records. Fix by either keeping a final pre-merge execution-issues flush/commit when `CI_PASSED=true`, or wiring the new helper into the pre-push/log-refresh paths that actually commit before merge.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** `risk-integration` — `skills/implement/SKILL.md:1657-1675`, `skills/implement/SKILL.md:1732-1734`, `scripts/implement-finalize.sh:213-253`: The branch moves the normal execution-issues flush to Step 7a but does not test or provide a committed flush path for entries appended after Step 7a. A concrete failing path is: Step 7a flush succeeds, Step 8a/postbump appends a changelog/rebase warning to `execution-issues.md`, then Step 18 safety-net appends it only after the final transcript commit path, and cleanup removes the tmpdir, so the committed `execution-issues.ndjson` misses the late record. Add a regression harness for “successful pre-bump flush, then append a new postbump issue, then final flush/commit,” and either flush before the last allowed log commit or wire the helper into the shared pre-push/refresh path.

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: 1. **Important** `risk-integration` — `skills/implement/SKILL.md:1657-1675`, `skills/implement/SKILL.md:1732-1734`, `scripts/implement-finalize.sh:213-253`: The branch moves the normal execution-issues flush to Step 7a but does not test or provide a committed flush path for entries appended after Step 7a. A concrete failing path is: Step 7a flush succeeds, Step 8a/postbump appends a changelog/rebase warning to `execution-issues.md`, then Step 18 safety-net appends it only after the final transcript commit path, and cleanup removes the tmpdir, so the committed `execution-issues.ndjson` misses the late record. Add a regression harness for “successful pre-bump flush, then append a new postbump issue, then final flush/commit,” and either flush before the last allowed log commit or wire the helper into the shared pre-push/refresh path.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Important** `risk-integration` — `skills/implement/SKILL.md:1657-1676`, `skills/implement/SKILL.md:1722-1732`: execution issues are flushed only at Step 7a, while the CI-passed checkpoint no longer refreshes them, so any later entries appended by post-bump, CI-fix, rebase, merge, or postmerge paths can be lost from the committed `execution-issues.ndjson`. A successful run that logs a CI helper failure after Step 7a can still merge without another committed execution-issues flush. Either flush execution issues again before a later pre-push/log commit point, or route post-Step-7a entries directly into the larch-log batch when they are recorded.

- **Reviewer**: codex-specialist-structure-output.txt
- **Concern**: 2. **Important** `risk-integration` — `skills/implement/SKILL.md:1657-1676`, `skills/implement/SKILL.md:1722-1732`: execution issues are flushed only at Step 7a, while the CI-passed checkpoint no longer refreshes them, so any later entries appended by post-bump, CI-fix, rebase, merge, or postmerge paths can be lost from the committed `execution-issues.ndjson`. A successful run that logs a CI helper failure after Step 7a can still merge without another committed execution-issues flush. Either flush execution issues again before a later pre-push/log commit point, or route post-Step-7a entries directly into the larch-log batch when they are recorded.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Important** `security` `skills/implement/SKILL.md:1657-1681`, `skills/implement/SKILL.md:1722-1733`, `skills/implement/scripts/flush-execution-issues.sh:151-156` — The new execution-issues flow treats a successful `larch-log.sh append` as durable, but durability depends on the later `larch-log.sh commit`, which is best-effort and ignored with `|| true`; the CI-passed checkpoint also no longer flushes execution issues. If Step 7a append succeeds but the commit fails, or a later CI/merge/tool failure appends a security-relevant warning after Step 7a, the final branch can lack the committed `execution-issues` audit record while Step 18 only retries in tmpdir during teardown. Fix by flushing execution issues through the same pre-push commit path before every push, and only considering records durable after the log commit succeeds, or keep a post-CI/pre-merge refresh that commits and revalidates the resulting tree.

- **Reviewer**: codex-specialist-security-output.txt
- **Concern**: 1. **Important** `security` `skills/implement/SKILL.md:1657-1681`, `skills/implement/SKILL.md:1722-1733`, `skills/implement/scripts/flush-execution-issues.sh:151-156` — The new execution-issues flow treats a successful `larch-log.sh append` as durable, but durability depends on the later `larch-log.sh commit`, which is best-effort and ignored with `|| true`; the CI-passed checkpoint also no longer flushes execution issues. If Step 7a append succeeds but the commit fails, or a later CI/merge/tool failure appends a security-relevant warning after Step 7a, the final branch can lack the committed `execution-issues` audit record while Step 18 only retries in tmpdir during teardown. Fix by flushing execution issues through the same pre-push commit path before every push, and only considering records durable after the log commit succeeds, or keep a post-CI/pre-merge refresh that commits and revalidates the resulting tree.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Latent** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:151-169`: The helper emits `APPEND_LOG_FILE=<path>` but its `EXIT` trap deletes that file before callers can inspect it. The harness checks only that the key is emitted, not that the referenced append log remains readable, so this contract regression can pass CI while breaking diagnostic consumers. Preserve the append log whenever its path is emitted, and add a test that parses `APPEND_LOG_FILE` and asserts the file exists with the captured `larch-log.sh` output.

- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: 2. **Latent** `risk-integration` — `skills/implement/scripts/flush-execution-issues.sh:107-110`, `skills/implement/scripts/flush-execution-issues.sh:151-169`: The helper emits `APPEND_LOG_FILE=<path>` but its `EXIT` trap deletes that file before callers can inspect it. The harness checks only that the key is emitted, not that the referenced append log remains readable, so this contract regression can pass CI while breaking diagnostic consumers. Preserve the append log whenever its path is emitted, and add a test that parses `APPEND_LOG_FILE` and asserts the file exists with the captured `larch-log.sh` output.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Latent** correctness, `skills/implement/scripts/flush-execution-issues.sh:107-170`: the helper emits `APPEND_LOG_FILE=<path>` but the EXIT trap deletes that same temp file before callers can read it. The plan and new contract expose `APPEND_LOG_FILE` as part of the output envelope when append is attempted or composition fails, so a caller/operator following the contract gets a dead path after `FLUSH_STATUS=ok` or `failed`. Preserve the append log once emitted, or copy it to a stable `$IMPLEMENT_TMPDIR` path and emit that; add a harness assertion that the emitted file exists after the helper exits.

- **Reviewer**: codex-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Latent** correctness, `skills/implement/scripts/flush-execution-issues.sh:107-170`: the helper emits `APPEND_LOG_FILE=<path>` but the EXIT trap deletes that same temp file before callers can read it. The plan and new contract expose `APPEND_LOG_FILE` as part of the output envelope when append is attempted or composition fails, so a caller/operator following the contract gets a dead path after `FLUSH_STATUS=ok` or `failed`. Preserve the append log once emitted, or copy it to a stable `$IMPLEMENT_TMPDIR` path and emit that; add a harness assertion that the emitted file exists after the helper exits.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Nit** `code-quality` `skills/implement/scripts/flush-execution-issues.sh:107-155`: `APPEND_LOG_FILE` is emitted after append attempts, but the `EXIT` trap deletes that temp file before callers can inspect it. The output envelope therefore points at a nonexistent diagnostic file, which weakens failure recovery when an operator or wrapper follows the reported path. Keep the append log when it is emitted, or stop emitting `APPEND_LOG_FILE` for paths intentionally cleaned up.

- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/implement/scripts/flush-execution-issues.sh:107-155`: `APPEND_LOG_FILE` is emitted after append attempts, but the `EXIT` trap deletes that temp file before callers can inspect it. The output envelope therefore points at a nonexistent diagnostic file, which weakens failure recovery when an operator or wrapper follows the reported path. Keep the append log when it is emitted, or stop emitting `APPEND_LOG_FILE` for paths intentionally cleaned up.
- **Suggested revision**: Address the concern above.

