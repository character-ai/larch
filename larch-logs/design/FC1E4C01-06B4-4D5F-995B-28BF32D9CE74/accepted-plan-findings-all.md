### FINDING_1: Adoption ratchet is not enforced on CI fast lint or pre-commit
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The new run-log walker ratchet is wired only into the standalone `lint-run-log-walkers` / `make lint` aggregate. It is not included in `py-lint-checks-fast` or `.pre-commit-config.yaml`, so CI and pre-commit can miss new bypassing walkers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `run-log-walkers` to the `py-lint-checks-fast` foreach list (and a pre-commit hook on `^python/.*\.py$` mirroring `lint-wire-artifact-pairing`). Document the check in `docs/linting.md` if that file is updated elsewhere in the PR.


### FINDING_2: `_ground_truth_run_ended_at` remains a dual-manifest traversal
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-dyn-Corpus Parity Auditor
- **Severity**: major
- **Concern**: The plan migrates other manifest readers but leaves `_ground_truth_run_ended_at` independently traversing `manifest.json` and `run-manifest.json`. The new AST ratchet will likely reject this remaining loop, and the shared API mandate remains incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the shared corpus reader with `run_ended_at` (or a parameterized manifest timestamp helper covering `ended_at` / `completed_at` / `updated_at`) and repoint `_ground_truth_run_ended_at`; add corpus tests for the ended-at precedence chain.
  - From Codex-Innovation: Add a shared `run_ended_at` helper or expose the shared manifest-candidate reader, then replace `_ground_truth_run_ended_at` with it while preserving its ended/completed/updated fallback order
  - From Cursor-dyn-Corpus Parity Auditor: Add run_ended_at (or a shared dual-manifest ended/completed/updated_at metadata reader) to run_log_corpus.py, repoint _ground_truth_run_ended_at, and cover precedence/fallback in test_run_log_corpus.py; do not exempt ground_truth from the ratchet


### FINDING_3: Rejected-analysis run enumeration still bypasses the safe walker
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: The prepare scan still enumerates `implement/*` and `review/*` with direct globs. This bypasses symlink and containment checks and conflicts with the stated single safe-walk API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Enumerate implement/review runs via the promoted safe child-directory walker (or a thin wrapper that preserves current skill partitioning) and add/adjust rejected-analysis fixtures for symlink and out-of-root children.
  - From Cursor-Innovation: Replace the `implement/*` and `review/*` globs with `safe_child_run_dirs` on `logs / "implement"` and `logs / "review"` (preserve date-window filtering and `_join_run_findings` ordering).
  - From Codex-Requirements: Plan an explicit replacement of rejected-analysis run enumeration with the public safe child-directory helper, while preserving its implement/review ordering and date-window behavior.


### FINDING_4: Additional committed run-log scanners are missing from the repoint set
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: `iter_filed_oos_records` still directly globs committed `implement` and `design` runs. The new ratchet or the stated centralization goal will expose this remaining unsafe scanner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/larch/issue/_oos.py` to repoint skill-root enumeration through the promoted safe child-directory walker (and shared manifest metadata reads if applicable), or add an explicit narrow exemption with reason if this path is intentionally out of scope.
  - From Codex-Pragmatic: Add this module to the firm update set and use the shared safe walker, preserving its existing artifact-specific filtering.


### FINDING_5: Ground-truth GC fallback remains an unsafe corpus walk
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: `_ground_truth_gc_slimmed_fallback` continues to enumerate skill-root run directories with `glob("*")`, bypassing the shared symlink and containment checks and potentially triggering the new ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Repoint the gc-slimmed fallback counter through `safe_child_run_dirs` on each skill root under `log_root`, preserving the `seen_gc` dedupe semantics.
  - From Codex-Pragmatic: Route this fallback through the shared safe child-directory helper, or explicitly justify why it is outside the mandated scanner surface and exempt it narrowly.


### FINDING_6: Fluff-analysis run enumeration is not repointed
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Fluff-analysis still uses raw globs for implement/design run enumeration. Replacing only metadata and classification helpers leaves an unsafe scanner in scope and may cause immediate ratchet failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the fluff-analysis update to enumerate committed runs via the shared safe child-directory walker per skill root; keep thread-pool and cutoff/version filters caller-side.
  - From Cursor-Requirements: Repoint fluff implement/design run enumeration to the promoted safe child-directory helper (with warning adaptation) or state explicitly why committed-log symlink safety is out of scope for this script


### FINDING_7: Audit-runs still admits symlinked candidate directories
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The audit-runs plan centralizes manifest reads but not run-directory discovery. Direct `root.glob("*/parent-issue.md")` and `root.glob("*/manifest.json")` can admit symlinked or escaping child directories without shared containment checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify that audit-runs corpus enumeration uses the shared safe child-directory walker, and add a regression test covering symlinked candidate run directories.


### FINDING_8: Classification discovery needs distinct APIs and pinned layout/sort semantics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Corpus Parity Auditor, Codex-dyn-Corpus Parity Auditor
- **Severity**: major
- **Concern**: Callers currently use different classification-discovery shapes: log-root triple-globs, per-run TSV paths, recursive fluff layouts, and different round ordering. A single unspecified `discover_classifications(log_root)` contract could drop JSONL fallbacks, change design coverage, alter numeric versus lexicographic ordering, or change panel attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement both contracts explicitly (e.g. `discover_classifications(log_root)` plus `classification_paths_for_run(skill, run_dir)`), and state which callers use which; keep JSONL fallbacks in callers per the plan.
  - From Cursor-Innovation: Pin the return type in the plan/API (e.g. `(skill: design|implement|review, path: Path)` plus deterministic sort keys) and state that panel labels like `code-review` remain caller-owned remapping; add a regression test that ground-truth and voter-calibration outputs stay unchanged on fixtures.
  - From Cursor-Requirements: Keep fluff design discovery caller-specific: either extend the shared helper with an opt-in recursive design mode or filter canonical results without dropping non-plan-review layouts, and lock behavior with existing fluff corpus harnesses
  - From Cursor-dyn-Corpus Parity Auditor: Add a per-run `classification_tsv_paths(skill, run_dir, *, round_sort=...)` API plus log-root `discover_classifications(log_root)`; pin sort policy per caller in the plan and tests.
  - From Codex-dyn-Corpus Parity Auditor: Make `discover_classifications` enumerate only directories returned by the contained, non-symlink-safe walker, or require and document an equivalent safe-root filter for every canonical layout


### FINDING_9: `round_num_from_path` has incompatible caller conventions
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Corpus Parity Auditor
- **Severity**: minor
- **Concern**: Existing callers use incompatible return types and empty-round defaults: `str` / `""`, `int` / `0`, and `int | None`. An unspecified shared contract can change sorting, labels, and output formatting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify the shared helper signature and per-caller empty-round mapping in `run_log_corpus.py`; add corpus tests for the empty-round case and extend affected scanner tests to lock caller-specific formatting.
  - From Cursor-Innovation: Specify one return type (recommend `int | None`) and list per-caller coercion at each `### UPDATED:` site so sorting, JSONL round keys, and empty-round handling stay byte-stable.
  - From Cursor-dyn-Corpus Parity Auditor: Add a per-run `classification_tsv_paths(skill, run_dir, *, round_sort=...)` API plus log-root `discover_classifications(log_root)`; pin sort policy per caller in the plan and tests.


### FINDING_10: Shared timestamp and manifest fallback semantics are under-specified
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-Corpus Parity Auditor, Codex-dyn-Corpus Parity Auditor
- **Severity**: major
- **Concern**: Existing callers differ in whether they consult `run-manifest.json`, accept `updated_at`, or stop after the first parseable manifest object with empty timestamps. A uniform helper could change run eligibility, version selection, or period bucketing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify fluff calls `run_started_at(..., allow_updated_at_fallback=False)` (or equivalent) and keeps manifest.json-only reads unless the issue explicitly expands scope; add corpus tests for period bucketing
  - From Cursor-dyn-Corpus Parity Auditor: Document and test that run_started_at(..., allow_updated_at=True) stops after the first successfully parsed manifest object; only unreadable/malformed/non-object candidates advance to run-manifest.json
  - From Codex-dyn-Corpus Parity Auditor: Define field-specific candidate behavior, or keep the fallback policy at each caller boundary: continue to the alternate manifest only where the prior caller did so, while preserving first-candidate precedence elsewhere


### FINDING_11: GC must preserve its started-at-only retention contract
- **Reviewer(s)**: Codex-dyn-Corpus Parity Auditor
- **Severity**: major
- **Concern**: Migrating GC to the shared `run_started_at` helper may introduce `updated_at` fallback and change retention or slimming decisions that currently fall back to Git commit dates when `started_at` is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Corpus Parity Auditor: Call `run_started_at` with the fallback disabled for GC, then retain the existing Git-date fallback when no usable `started_at` exists


### FINDING_12: Shared walker does not preserve difficulty-calibration OSError accounting
- **Reviewer(s)**: Cursor-dyn-Corpus Parity Auditor
- **Severity**: minor
- **Concern**: Difficulty calibration currently maps `glob` `OSError` to `unreadable_skill_roots`, while the shared walker only guards resolution failures. Adopting it directly can raise instead of preserving counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Corpus Parity Auditor: Extend the promoted walker (or the difficulty adapter) to catch glob OSError and map it to unreadable_skill_roots; add a unit test


### FINDING_14: Larch-version fallback policy differs by caller
- **Reviewer(s)**: Codex-dyn-Corpus Parity Auditor
- **Severity**: major
- **Concern**: `_ground_truth_run_larch_version` can skip a preferred manifest with a missing or invalid version and use `run-manifest.json`, while other callers stop at the first JSON object even when relevant fields are empty. A uniform first-object policy can lose valid alternate metadata or introduce metadata previously ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Corpus Parity Auditor: Define field-specific candidate behavior, or keep the fallback policy at each caller boundary: continue to the alternate manifest only where the prior caller did so, while preserving first-candidate precedence elsewhere


### FINDING_1: Rejected-analysis must preserve `updated_at` fallback
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Migrating rejected-analysis to the shared `run_started_at` helper with its default `allow_updated_at_fallback=False` would exclude runs whose only usable timestamp is `updated_at`, changing date-window filtering, survivor counts, and ordering. The migration must also preserve first-valid-object stop semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `rejected_analysis.py`, call `run_started_at(..., allow_updated_at_fallback=True)` (and keep first-valid-object stop semantics). Add a regression fixture with only `updated_at` set to lock date-window inclusion.
  - From Cursor-Requirements: Add an explicit rejected-analysis line: use `run_started_at(..., allow_updated_at_fallback=True)` with `continue_on_empty=False`, preserving first-valid-object stop when both timestamp fields are empty.


### FINDING_5: Preserve manifest-only metadata policy in fluff analysis
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Fluff analysis currently reads only `manifest.json`, while default shared metadata helpers may also read `run-manifest.json`. Repointing without an explicit manifest scope would include run-manifest-only runs and change period bucketing, version filtering, and counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin fluff to `manifest.json`-only reads (add a `manifest_candidates`/`single_candidate` helper option, or keep the existing single-file read for enumeration filters) and extend corpus harness fixtures for run-manifest-only directories.
  - From Cursor-Pragmatic: Use the same manifest.json-only candidate scope as GC for fluff started-at reads (allow_updated_at_fallback=False is not enough), and extend the existing period-bucketing harness to cover run-manifest-only fixtures.


### FINDING_6: Preserve rejected-analysis classification round ordering
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Rejected-analysis currently sorts classification TSVs lexically, whereas the shared classification helper may apply a different round-order policy. An unspecified policy could reorder multi-round runs and change findings or ledger ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass the lexical `round_sort` policy in the rejected-analysis repoint and lock it in `python/tests/issue/test_rejected_analysis.py`.


### FINDING_7: Name `map_runs_main` in the audit-runs migration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The audit-runs plan does not explicitly cover the unsafe corpus globs in `map_runs_main`. Missing this helper could leave symlinked run directories reachable or cause the new ratchet to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name `map_runs_main` explicitly: enumerate via `safe_child_run_dirs`, then check `parent-issue.md` / `manifest.json` inside each contained run dir; add a symlink run-dir regression beside the planned audit-runs test.


### FINDING_8: Account for GC recursive safety and sizing walks
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: GC retains recursive `os.walk` calls for escape-symlink detection and directory sizing. The planned ratchet appears to reject such committed-corpus walks, so the plan must distinguish validated per-run inspection from unsafe corpus traversal without creating a broad exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define and test a narrow exemption/category for recursive inspection inside an already validated run directory, or move the reusable safe recursive inspection into `run_log_corpus.py`; do not add a broad GC-file exemption.


### FINDING_10: Preserve alternate-manifest fallback in strict ground-truth reads
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Strict ground-truth discovery continues to the alternate manifest when `manifest.json` is valid but lacks `started_at`. A default first-object stop in the shared helper would exclude runs whose timestamp exists only in `run-manifest.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add continue_on_empty=True to the strict ground-truth run_started_at call (or an equivalent helper flag) and lock it with a fixture where manifest.json is a valid object without started_at and run-manifest.json supplies it.


### FINDING_11: Preserve GC’s manifest.json-only timestamp policy
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: GC currently reads `started_at` only from `manifest.json` before falling back to Git dates. Default shared metadata discovery could start accepting `run-manifest.json`, changing retention and slimming dates for runs that were previously handled by Git fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit manifest-candidate scope to the shared metadata helpers (for example candidates=("manifest.json",) or allow_alternate_manifest=False) and use manifest.json-only mode in gc_run_logs.py; add a regression where manifest.json is absent and run-manifest.json has started_at to prove Git fallback is unchanged.


### FINDING_12: Preserve difficulty-calibration error-counter semantics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Replacing the local child-directory scan with `safe_child_run_dirs` can change how root `OSError` cases are classified. Resolve failures and child-enumeration failures must continue mapping to their existing counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin the adapter: map resolve failures to missing_skill_roots and child-enumeration OSError to unreadable_skill_roots, and assert both counters in test_difficulty_calibration.py.


### FINDING_13: Account for existing committed-corpus walkers in `tokens.py`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Existing `tokens.py` iterators use recursive and per-skill committed `larch-logs` globs but are outside the repoint set. The new ratchet could fail immediately, or the plan could leave these walkers outside the shared containment policy without documenting a narrowly justified exception.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Repoint both iterators through safe_child_run_dirs (and contained per-run artifact checks) or add a narrowly justified exemption with negative lint fixtures; include tokens.py in the firm file set and add focused lint coverage.
  - From Cursor-Requirements: Spell out ratchet treatment in the lint plan: either document these as allowed fixed-artifact lookups in the rule/tests, or add a narrow grandfather/exclusion for tokens.py panel/checks-digest iterators.


### FINDING_14: Extend the pre-commit ratchet to skill scanner scripts
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The pre-commit hook currently filters only `python/.*\.py`, so changes to the in-scope skill scanner scripts would not trigger the run-log-walker ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the two scanner-script paths to the hook filter, or scope the hook to every tracked Python source that the ratchet scans.


