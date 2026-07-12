### FINDING_1: Sweep report timing conflicts with legacy stages
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: S3 is described as rendering the integrated report before legacy ledger and deep stages complete, so combined runs could omit later triage/deep results or produce inconsistent report state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Limit S3 to refuter ingest plus sweep-result artifact write. Keep existing Stage 3 report as the only final render after ledger and deep complete.
  - From Cursor-Innovation: Insert S0-S3 immediately after Stage 0 prefetch and before Stage 1 ledger, then keep Stage 3 report as the single render entrypoint that merges verification and sweep sections.
  - From Cursor-Pragmatic: Limit sweep S3 to refuter ingest plus writing a validated sweep artifact; keep Stage 3 `analyze-bugs report` as the sole final render after stages 1-2 (or document an explicit combined ordering if stages 1-2 are skipped).


### FINDING_2: Chronic-zone prioritization is not bound to analytics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Ranking can fall back to path-only zones or diff size because ledger-derived chronic-zone membership is not explicitly loaded and consulted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Load ledger chronic names via build_analytics_view, tag a merge when _zones_for_files(touched) intersects that set, and rank chronic-tagged merges before diff size.
  - From Cursor-Innovation: In sweep_enumeration, pass LEDGER_PATH, build a synthetic manifest with generated_at at the pinned tip, call build_analytics_view with empty bundles, and mark a merge chronic when any touched zone intersects analytics.chronic_zones. Add a fixture ledger that makes chronic-zone-first observable.
  - From Cursor-Pragmatic: Load `ledger_path` during enumeration, call `build_analytics_view` with a synthetic manifest (`generated_at=now`, empty bundles), derive `chronic_zone_names`, and rank commits whose touched zones intersect that set ahead of others; test with ledger fixtures that have no current-run bundles.
  - From Cursor-Requirements: In prepare/enumeration load ledger_path plus prefetch manifest, call build_analytics_view (or a shared helper), derive chronic zone names, and rank commits whose touched zones intersect that set ahead of others; add a fixture proving a non-chronic-zone commit loses to a chronic-zone commit at equal diff size


### FINDING_4: Sweep flags must be separated from prefetch arguments
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Forwarding `--sweep` and `--sweep-max` through prefetch can cause prefetch argument rejection and prevent sweep startup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Parse sweep controls separately, forward only legacy flags to prefetch, then invoke `analyze-bugs sweep`; reject `--sweep-max` without `--sweep`


### FINDING_7: Per-merge bundles need an explicit first-parent diff base
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Without defining the diff against the first parent, merge-specific changes may be omitted from touched-file, size, and symbol evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Compute each merge bundle against its first parent, such as `<merge_sha>^1` to `<merge_sha>`, and test that merge-specific changes appear in the bundle


### FINDING_8: Sweep-only survivors need a follow-up body
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Sweep survivors may appear in the report without creating `follow-up-issue.md`, leaving the approval-gated `/issue` path with nothing to file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When validated sweep candidates exist, always create or extend follow-up-issue.md (sweep section even if followups is empty). Keep dedup-on /issue unchanged.
  - From Cursor-Pragmatic: When validated sweep survivors exist, always create or extend `follow-up-issue.md` (sweep section even if bug followups are empty), emit the follow-up path in report output, and test sweep-only filing.
  - From Cursor-Requirements: In the sweep report extension create or append follow-up-issue.md when Sweep candidates exist even if bug followups are empty; test sweep-only survivor output


### FINDING_11: Sweep ingest must hard-fail on malformed or incomplete input
- **Reviewer(s)**: Cursor-dyn-Sweep State Integrator
- **Severity**: major
- **Concern**: Reusing soft-success ledger ingest semantics can allow missing, malformed, rejected, or incomplete finder/refuter output to advance reporting as a false zero-candidate success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Sweep State Integrator: Add dedicated sweep ingest helpers that return non-zero when any selected merge is missing, any row is rejected, expected refutations are incomplete, or INGEST_ACCEPTED does not exactly match the prepare manifest; do not reuse ledger_main exit 0 on partial ingest
  - From Cursor-dyn-Sweep State Integrator: Require the refuter ingest path to hard-fail when the JSONL path is missing, empty, or short of the queued (merge_sha, finding_index) set; add a test mirroring test_ledger_ingest for missing deep file but expecting non-zero


### FINDING_12: Capped sweeps need a resumable frontier
- **Reviewer(s)**: Codex-dyn-Sweep State Integrator
- **Severity**: major
- **Concern**: Advancing `last_sweep_sha` to the pinned tip while retaining only a skipped count can permanently omit unswept commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Sweep State Integrator: Persist skipped SHAs or an equivalent resumable frontier; advance last_sweep_sha only after all preceding commits are swept, and mark capped reports incomplete


### FINDING_1: Empty sweep handling is undefined
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Strict ingestion rejects empty inputs, conflicting with successful zero-commit and zero-finding sweep cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Explicitly bypass result-file parsing for zero selected merges and zero refutation queues; still reject empty files when work was dispatched


### FINDING_4: Sweep ingestion lacks executable fail-closed fences
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The workflow does not require executable Python ingestion steps or exact acceptance enforcement, allowing prompt-side validation and partial success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror triage/deep: add bash fences for sweep prepare, ingest-finder, and ingest-refuter; save finder JSONL under fixed RUN_DIR paths; abort the run on any non-zero ingest exit before refuter dispatch or legacy stages.


### FINDING_5: Refuter dispatch handoff is unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The refuter queue path, required output keys, per-task inputs, and exact coverage validation are not defined.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Have ingest-finder emit REFUTER_QUEUE_PATH plus queue length KVs; document that S2 dispatches one refuter per queue row using only that file; require ingest-refuter to verify the accepted key set exactly matches the queue before writing the validated sweep-result artifact.


