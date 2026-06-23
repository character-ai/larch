# Review Round 1

- Mode: `diff`
- 7 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: materialize early-return leaves stale stable table
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-reviewer-status-artifacts-output.txt
- **Severity**: important
- **Concern**: `materialize_stable_reviewer_status_table()` returns `False` on early-exit guards (unbound round, missing/symlinked source TSV, symlinked round dir) without clearing an existing stable `reviewer-status-table.txt`. After round 1 writes a stable table, a later round that cannot render leaves prior-round icons in place instead of clearing them or surfacing the missing-table path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-dyn-reviewer-status-artifacts-output.txt: On those early-exit paths (and whenever `_write_reviewer_status_table_artifacts` is not reached with a successful stable write), call `_clear_reviewer_status_table(_stable_reviewer_status_table_path(design))` before returning `False`, matching the header-only / `wrote is None` cleanup behavior in `try_write_reviewer_status_tsv()`.


### FINDING_2: subprocess symlinked per-round TSV leaves stale stable table
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-dyn-reviewer-status-artifacts-output.txt
- **Severity**: important
- **Concern**: On the subprocess Step 3 path, a per-round `reviewer-status.tsv` that is a symlink is treated as success because `round_status.is_file()` is true. `sync_latest_reviewer_status()` and `materialize_stable_reviewer_status_table()` then no-op on the symlinked source. If `$DESIGN_TMPDIR/reviewer-status-table.txt` already exists from a prior round, the unified tail skips recovery and Step 3 can emit stale prior-round icons instead of current-round status or the missing-table warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-dyn-reviewer-status-artifacts-output.txt: After subprocess completion, treat `round_status.is_symlink()` like a missing artifact (unlink and route through `try_write_reviewer_status_tsv`, or resolve/copy to a regular file before sync/materialize). If `materialize_stable_reviewer_status_table(..., round_num=round_num)` returns `False`, clear the stable table (or always re-materialize via `_write_reviewer_status_table_artifacts` only after confirming a non-symlink source). Add a regression test where the subprocess leaves a symlinked per-round TSV and a pre-seeded stale stable table.


### FINDING_3: unified tail skips recovery when stale regular stable file remains
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_run_round_body()` tail only materializes when stable is absent or symlinked, not when a stale regular stable file remains after failed refresh. When per-round TSV exists but stable refresh failed and a prior regular stable file is still present, recovery is skipped and stale round-N-1 icons can be shown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: renderer accepts malformed TSV without status column
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `render_reviewer_status_table()` accepts malformed reviewer-status TSVs without a `status` column and emits a false failed-reviewer table. A TSV containing only `slot\nCursor-Arch\n` renders `Cursor-Arch` as ❌ instead of returning `None` and triggering the missing-table warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: skipped reviewer rows render elapsed text
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A subprocess-written `reviewer-status.tsv` row with `status=skipped` and `elapsed=2m` renders as `⊘ 2m` even though skipped rows must render without elapsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: progress-reporting.md conflicts with read-only table contract
- **Reviewer(s)**: dyn-dyn-design-table-contract-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:62` still points orchestrators at `shared/progress-reporting.md` for Step 3 table cadence, but that file was not updated and still documents orchestrator-side `📊` formatting (icon legend, elapsed rules, and example lines at `skills/shared/progress-reporting.md:91-117`). That conflicts with the new read-only contract in the three compact-table SKILL sites, which say Python owns formatting and the orchestrator must only Read and emit `reviewer-status-table.txt`. An agent following the linked doc can resurrect manual rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-table-contract-output.txt: Update `skills/shared/progress-reporting.md` so the `/design` Step 3 path explicitly defers to the pre-rendered `reviewer-status-table.txt` emit contract (or remove the Step 3-specific icon/elapsed guidance from that doc and replace the SKILL.md pointer with a sentence that Step 3 table output is file-only).


### FINDING_8: symlinked stable destination blocks recovery without warning
- **Reviewer(s)**: dyn-dyn-design-table-contract-output.txt
- **Severity**: important
- **Concern**: Symlink-safe table handling skips both clear and write when `reviewer-status-table.txt` is a symlink. `_run_round_body()` treats a symlink as recoverable and retries materialization, but materialization also no-ops on a symlinked stable path, so recovery cannot replace stale content. The SKILL contract only warns when the file is absent, not when it is present-but-unwritable; the Read tool may still follow the symlink and the orchestrator may emit stale or wrong reviewer status with no warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-table-contract-output.txt: Treat an unrefreshable stable destination (symlink or failed write after a successful per-round TSV refresh) as equivalent to “table not found” in the SKILL emit contract, and/or have Python log a bounded warning artifact the orchestrator can surface; alternatively unlink the symlink when explicit `round_num` materialization is requested on the hot path.


