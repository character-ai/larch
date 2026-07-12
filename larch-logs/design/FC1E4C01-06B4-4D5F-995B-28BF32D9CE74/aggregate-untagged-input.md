### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/rejected_analysis.py:289-296
- **Concern**: Pin `allow_updated_at_fallback=True` for rejected-analysis `run_started_at` migration. Scenario: `_run_started_at` falls back to `updated_at` when `started_at` is absent. The shared helper defaults `allow_updated_at_fallback=False`. A default-false migration drops `updated_at`-only runs from the prepare scan date window and changes survivor counts/order without a test that uses `updated_at`-only manifests.
- **Proposed resolution**: In `rejected_analysis.py`, call `run_started_at(..., allow_updated_at_fallback=True)` (and keep first-valid-object stop semantics). Add a regression fixture with only `updated_at` set to lock date-window inclusion.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/design/design_step_log.py:42
- **Concern**: Committed run-log discovery remains outside the repoint set. Scenario: The plan requires all in-repo committed run-log scanners to use the shared API and limits ratchet exemptions to three #7008 files, but `_resolve_run_id` still globs `larch-logs/implement/*/manifest.json`. The new ratchet would either reject this path or require an unlisted exemption, leaving the adoption contract incomplete. Add this module to the repoint set and resolve the run ID through `safe_child_run_dirs` plus the existing manifest acceptance rules, or explicitly narrow the ratchet and feature scope.
- **Proposed resolution**:

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_manifest.py:411
- **Concern**: Committed classification traversal is omitted from the migration plan. Scenario: The plan says every committed run-log scanner must use `run_log_corpus`, but `_design_plan_review_round_dirs` still enumerates committed `plan-review/round-*` directories with a raw glob. This is a corpus walk distinct from the listed writer and session-local exceptions. It can bypass the shared containment and symlink policy and conflicts with the planned ratchet. Add this caller to the repoint set, or document a precise non-corpus classification for why it is excluded.
- **Proposed resolution**:

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/report/run_log_corpus.py:51-53
- **Concern**: The classification APIs do not state file-level safety requirements. Scenario: The plan pins safe child-directory discovery but does not require `classification_tsv_paths` or `discover_classifications` to reject symlinked or escaping classification files. A run directory can contain a symlink such as `findings-classification.tsv` pointing outside the committed corpus, and callers will read the target through the shared API. Require returned artifacts to be regular non-symlink files whose resolved paths remain contained by the run directory, and add regression coverage for symlinked and escaping classification artifacts.
- **Proposed resolution**:

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:95-109
- **Concern**: Fluff metadata migration omits manifest.json-only policy. Scenario: Fluff `_enumerate_*` and `manifest_*` read only `manifest.json` today; runs with only `run-manifest.json` are skipped. Shared `run_started_at` / `larch_version` default to dual-name candidates, so period bucketing and version filters can admit runs the script currently ignores. Pin fluff to `manifest.json`-only reads (add a `manifest_candidates`/`single_candidate` helper option, or keep the existing single-file read for enumeration filters) and extend corpus harness fixtures for run-manifest-only directories.
- **Proposed resolution**:

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/rejected_analysis.py:812-816
- **Concern**: `classification_tsv_paths` round sort not pinned for rejected-analysis. Scenario: Rejected-analysis orders TSVs with plain `sorted(run_dir.glob(...))` (lexical path order), not numeric `round-N`. Calling the shared helper without an explicit lexical `round_sort` can reorder multi-round runs and change `_join_run_findings` / ledger ordering. Pass the lexical `round_sort` policy in the rejected-analysis repoint and lock it in `python/tests/issue/test_rejected_analysis.py`.
- **Proposed resolution**:

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:806-822
- **Concern**: `map_runs_main` unsafe globs are not named in the audit-runs plan slice. Scenario: The only `root.glob("*/…")` corpus scans in `audit_runs.py` live in `map_runs_main`. The plan speaks generically about candidate enumeration; if that helper is missed, the new ratchet fails on landing or symlinked run dirs remain reachable during PR-to-run resolution. Name `map_runs_main` explicitly: enumerate via `safe_child_run_dirs`, then check `parent-issue.md` / `manifest.json` inside each contained run dir; add a symlink run-dir regression beside the planned audit-runs test.
- **Proposed resolution**:

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/gc_run_logs.py:117-150
- **Concern**: The ratchet scope does not account for GC's retained recursive corpus walks. Scenario: The plan explicitly rejects raw committed-corpus walk/scandir patterns, but leaves `_has_escape_symlink` and `_dir_bytes` using `os.walk` in `gc_run_logs.py`. Unless the new lint classifies these required per-run safety and sizing walks as an allowed category, the planned ratchet will fail on an unchanged required path or force an unjustified exemption.
- **Proposed resolution**: Define and test a narrow exemption/category for recursive inspection inside an already validated run directory, or move the reusable safe recursive inspection into `run_log_corpus.py`; do not add a broad GC-file exemption.

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:63,134,141,190-214
- **Concern**: The plan mandates regression coverage that is missing from its firm file list. Scenario: The plan requires difficulty-calibration coverage, fluff-analysis corpus-harness updates, voter-calibration harness updates, and final-report boundary tests, but does not list those test or harness files under `Files to modify/create`. An implementation can follow the firm file set, omit these required checks, and still claim the stated validation was delivered.
- **Proposed resolution**: Add the exact affected test and harness paths to `Files to modify/create`, including `python/tests/calibration/test_difficulty_calibration.py`, the fluff and voter shell harnesses, and `python/tests/report/test_final_report.py` if its metadata boundary changes.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/_ground_truth.py:1276-1294
- **Concern**: Ground-truth strict started-at migration omits alternate-manifest fallback when the preferred manifest object lacks started_at. Scenario: _ground_truth_run_started_at_strict keeps scanning run-manifest.json when manifest.json parses but has no started_at. The plan only pins run_started_at(..., allow_updated_at_fallback=False) for verdict filtering. With default first-object stop, runs whose started_at lives only in run-manifest.json would be excluded as missing-started_at.
- **Proposed resolution**: Add continue_on_empty=True to the strict ground-truth run_started_at call (or an equivalent helper flag) and lock it with a fixture where manifest.json is a valid object without started_at and run-manifest.json supplies it.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/gc_run_logs.py:74-93
- **Concern**: Shared run_started_at adoption can enable run-manifest.json for GC even though GC is manifest.json-only today. Scenario: _parse_started_at reads only run_dir/manifest.json before the Git-date fallback. run_started_at tries run-manifest.json when manifest.json is missing or unreadable. GC retention and slimming dates can shift for runs that only have run-manifest.json.
- **Proposed resolution**: Add an explicit manifest-candidate scope to the shared metadata helpers (for example candidates=("manifest.json",) or allow_alternate_manifest=False) and use manifest.json-only mode in gc_run_logs.py; add a regression where manifest.json is absent and run-manifest.json has started_at to prove Git fallback is unchanged.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:95-109
- **Concern**: Fluff period bucketing is manifest.json-only but the shared started-at helper defaults to dual-name candidates. Scenario: manifest_started and _design_run_manifest read only manifest.json and never consult run-manifest.json. Replacing them with default run_started_at would bucket runs using started_at from run-manifest.json when manifest.json is missing, changing period counts and version filters.
- **Proposed resolution**: Use the same manifest.json-only candidate scope as GC for fluff started-at reads (allow_updated_at_fallback=False is not enough), and extend the existing period-bucketing harness to cover run-manifest-only fixtures.

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty_calibration.py:216-227
- **Concern**: Difficulty calibration counter mapping for root OSError is under-specified. Scenario: _safe_child_run_dirs bumps missing_skill_roots on log_base.resolve OSError and unreadable_skill_roots on glob OSError. The plan only calls out unreadable-root adaptation, so a straight safe_child_run_dirs swap can relabel missing roots and change analyzer warning output.
- **Proposed resolution**: Pin the adapter: map resolve failures to missing_skill_roots and child-enumeration OSError to unreadable_skill_roots, and assert both counters in test_difficulty_calibration.py.

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/tokens.py:2548-2619
- **Concern**: Committed corpus glob iterators in tokens.py are outside the repoint set and will trip the new ratchet. Scenario: _iter_panel_prompt_size_files uses larch-logs/** recursive glob and _iter_checks_digest_size_files uses per-skill */artifact globs. Neither file is listed for repoint, yet the planned AST ratchet forbids raw committed-corpus traversal outside run_log_corpus.py. make py-lint-checks-fast and pre-commit will fail once the lint lands.
- **Proposed resolution**: Repoint both iterators through safe_child_run_dirs (and contained per-run artifact checks) or add a narrowly justified exemption with negative lint fixtures; include tokens.py in the firm file set and add focused lint coverage.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/rejected_analysis.py:289-296
- **Concern**: The rejected-analysis `### UPDATED` block does not pin `run_started_at(..., allow_updated_at_fallback=True)` like GC and fluff do for `False`.. Scenario: The shared helper defaults `allow_updated_at_fallback=False`. `_run_started_at` today accepts `updated_at` from the first valid manifest object; switching to the default would drop runs that only have `updated_at`, changing date-window filtering and survivor counts.
- **Proposed resolution**: Add an explicit rejected-analysis line: use `run_started_at(..., allow_updated_at_fallback=True)` with `continue_on_empty=False`, preserving first-valid-object stop when both timestamp fields are empty.

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/tokens.py:2548-2619
- **Concern**: The new ratchet plan does not say how existing `tokens.py` committed `larch-logs` discovery (`root.glob("**/{PANEL_PROMPT_SIZE_BASENAME}")` and `root.glob(f"{skill}/*/{CHECKS_DIGEST_SIZE_BASENAME}")`) stays clean.. Scenario: The lint is meant to fail closed on new corpus walkers with no baseline file listed. Those iterators are outside the repoint set but remain in tracked `python/larch/report/tokens.py`, so the first `lint run-log-walkers` / `py-lint-checks-fast` run can fail before any repointed scanner lands.
- **Proposed resolution**: Spell out ratchet treatment in the lint plan: either document these as allowed fixed-artifact lookups in the rule/tests, or add a narrow grandfather/exclusion for `tokens.py` panel/checks-digest iterators.

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:168-171
- **Concern**: Prior accepted fix remains incomplete: the hook excludes Python scanner scripts under `skills/`. Scenario: The firm plan changes `skills/fluff-analysis/scripts/fluff-analysis.py` and `skills/voter-calibration/scripts/voter-calibration.py`, but a later raw walker added to either path will not trigger the pre-commit ratchet because `files: ^python/.*\.py$` excludes both
- **Proposed resolution**: Add the two scanner-script paths to the hook filter, or scope the hook to every tracked Python source that the ratchet scans
