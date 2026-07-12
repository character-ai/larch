## Plan

## Approach

1. Expand `run_log_corpus.py` into the shared, symlink-safe API for committed run-log scans without changing `load_run_manifest` semantics.
   - Keep `load_run_manifest` limited to accepted non-symlink `manifest.json` files. A `run-manifest.json` alone must not satisfy this acceptance gate.
   - Promote the existing contained, non-symlink child-directory walk as `safe_child_run_dirs(root, ...)`, with deterministic ordering and structured warnings for missing, unreadable, unresolved, and unsafe roots or children.
   - Catch and distinguish root resolution failures from child-directory enumeration `OSError` failures so callers can preserve existing warning and counter behavior.
   - Centralize metadata candidate reads behind a private helper. The default candidate order is `manifest.json`, then `run-manifest.json`; callers can explicitly pin candidates to `("manifest.json",)` when their historical behavior must ignore alternate manifests.
   - Require metadata candidates to be regular non-symlink files containing JSON objects. Unreadable, malformed, and non-object candidates permit trying the next allowed candidate.
   - Make metadata fallback behavior field-specific and explicit:
     - `run_started_at(run_dir, *, allow_updated_at_fallback, continue_on_empty=False, manifest_candidates=...)` reads `started_at`, then optionally `updated_at`, from the first valid manifest object by default. It consults a later allowed candidate only when an earlier candidate is unavailable or `continue_on_empty=True`.
     - `run_ended_at(run_dir, *, continue_on_empty=False, manifest_candidates=...)` reads `ended_at`, then `completed_at`, then `updated_at`, preserving `_ground_truth_run_ended_at`’s per-candidate precedence and alternate-candidate behavior.
     - `larch_version(run_dir, *, continue_on_empty=False, manifest_candidates=...)` preserves empty-string output for absent or invalid values. Ground truth opts into alternate-candidate fallback after an empty or invalid preferred version; callers that historically stop at the first valid manifest object retain that behavior.
   - Define `round_num_from_path(path) -> int | None`. Each caller explicitly maps `None` to its existing representation (`""`, `0`, or omitted) before sorting, labels, JSON, or TSV output.
   - Provide two distinct classification APIs:
     - `classification_tsv_paths(skill, run_dir, *, round_sort)` returns canonical TSV classification artifacts for one contained run directory, with caller-selected numeric or lexical round ordering.
     - `discover_classifications(log_root, *, skills, round_sort)` walks only safe child directories and returns stable `(skill, path)` pairs for canonical design, implement, and review layouts.
   - Keep recursive or non-canonical discovery out of the generic root-level API. Callers such as fluff analysis retain required recursive design-specific behavior through a narrowly scoped safe helper built on `safe_child_run_dirs`, not raw corpus globs.
   - Provide a narrow contained-run recursive-inspection helper, or an equivalent validated-run contract, for GC’s escape-symlink and size walks. It must permit recursive inspection only after `safe_child_run_dirs` has validated the run directory and must not become a generic corpus-root traversal API.

2. Repoint every committed run-log scanner and fallback enumerator in scope.
   - Remove copied directory safety checks, round parsing, classification triple-globs, and dual-manifest metadata loops where the shared API preserves the existing contract.
   - Repoint direct committed-corpus enumeration in difficulty calibration, ground truth, rejected analysis, OOS, audit runs, GC, token reporting, fluff analysis, voter calibration, and the existing report recovery paths through the safe API.
   - Preserve caller-owned behavior: schema filtering, JSONL fallbacks, date parsing, panel-label remapping, report ordering, warning counters, date windows, version cutoffs, artifact-specific filters, and fixed per-run artifact lookups.
   - Preserve each caller’s metadata policy by passing explicit fallback and candidate options:
     - Rejected analysis uses `run_started_at(..., allow_updated_at_fallback=True, continue_on_empty=False)` to retain its `updated_at` date-window fallback and first-valid-object stop behavior.
     - Strict ground-truth started-time filtering uses `run_started_at(..., allow_updated_at_fallback=False, continue_on_empty=True)` to retain alternate-manifest fallback when a valid preferred object lacks `started_at`.
     - GC and fluff use `manifest_candidates=("manifest.json",)` so `run-manifest.json` never changes their historical timestamp, version, retention, or bucketing behavior.
   - Keep `retro_fix_cursor.py`, `retro_v3_sweep.py`, and `cleanup_implement_logs.py` unchanged because #7008 owns their deletion. Exempt only these paths from the adoption ratchet.

3. Add and enforce a mechanical adoption ratchet.
   - Scan tracked Python sources in `python/` plus the two in-scope skill scanner scripts.
   - Use AST-based call inspection to reject new raw committed-corpus glob, recursive glob, walk, `scandir`, copied canonical classification discovery, and dual-manifest traversal patterns outside `run_log_corpus.py`.
   - Distinguish unsafe corpus-root traversal from fixed artifact lookups and recursive inspection inside a run directory already returned by `safe_child_run_dirs`.
   - Permit validated per-run recursive inspection only through the narrow shared helper or a narrowly recognized containment proof. Do not exempt `gc_run_logs.py` wholesale.
   - Distinguish committed corpus traversal from run-log writers, fixed artifact lookups, unrelated directory traversal, and session-local paths.
   - Use narrow, reason-bearing exemptions only for the three #7008 deletion targets while they remain present.
   - Register `lint run-log-walkers` in `cli.py`; invoke it from `make lint`, `py-lint-checks-fast`, and pre-commit for every source file the lint scans.
   - Document the check and its local command in `docs/linting.md`.

## Files to modify/create

### UPDATED: python/larch/report/run_log_corpus.py

- Promote the safe child-directory walker as `safe_child_run_dirs`.
- Preserve containment checks, symlink rejection, deterministic ordering, and warning reporting.
- Catch root resolution and child enumeration `OSError` separately. Expose enough warning detail for difficulty calibration and other callers to retain their current counters.
- Add a private metadata-candidate reader with these invariants:
  - Default precedence is `manifest.json` before `run-manifest.json`.
  - Callers may pin candidate scope, including `("manifest.json",)`.
  - Candidates must be non-symlink regular files.
  - Unreadable, malformed, and non-object JSON candidates are unavailable and permit trying the next allowed candidate.
  - A valid JSON object with an absent or invalid requested field stops or continues based on the field helper’s explicit `continue_on_empty` option.
- Add `run_started_at`, `run_ended_at`, and `larch_version` with explicit fallback and candidate controls:
  - `run_started_at(..., allow_updated_at_fallback=False)` returns only `started_at` unless the caller explicitly permits `updated_at`.
  - `run_ended_at` preserves `ended_at`, `completed_at`, `updated_at` precedence.
  - `larch_version` preserves current empty-string behavior for absent or invalid values.
- Add `round_num_from_path(path) -> int | None`, recognizing both `round-N` directory names and filenames containing `round-N`.
- Add `classification_tsv_paths(skill, run_dir, *, round_sort)` for per-run canonical TSV discovery.
- Add `discover_classifications(log_root, *, skills, round_sort)` for canonical root-level discovery using only directories returned by `safe_child_run_dirs`.
- Add a narrow, documented contained-run recursive inspection helper or callback contract for GC’s safe directory-size and escape-symlink checks. It must reject unvalidated roots and escaping paths.
- Pin stable return types, path ordering, skill ordering, candidate behavior, and numeric-versus-lexical round sort behavior in docstrings and tests.
- Keep `load_run_manifest` and `run_dirs` manifest-acceptance behavior unchanged. Do not let `run-manifest.json` satisfy that gate.

### UPDATED: python/larch/calibration/difficulty_calibration.py

- Replace `_safe_child_run_dirs` with `safe_child_run_dirs`.
- Replace local round parsing with `round_num_from_path`, mapping `None` to the existing difficulty-calibration empty-round behavior.
- Use `classification_tsv_paths` for canonical TSV sources while retaining implement and review JSONL fallback paths.
- Adapt shared walker warnings into existing `AnalyzerState` counters with pinned semantics:
  - Map root resolution failures to `missing_skill_roots`.
  - Map child-directory enumeration `OSError` to `unreadable_skill_roots`.
  - Preserve existing unsafe-child handling.
- Preserve manifest parsing for difficulty records unless the shared metadata helper is behaviorally equivalent for that exact field policy.
- Add or update regression coverage for both root-resolution and enumeration-error accounting, plus byte-stable round and report output.

### UPDATED: python/larch/issue/_ground_truth.py

- Replace classification triple-globs with `discover_classifications` or `classification_tsv_paths` as appropriate. Preserve numeric round ordering and caller-owned panel remapping.
- Replace local round parsing with `round_num_from_path`, mapping `None` to each existing ground-truth default before comparisons or output.
- Replace every dual-name metadata loop, including `_ground_truth_run_ended_at`, with shared metadata helpers:
  - Use `run_started_at(..., allow_updated_at_fallback=False, continue_on_empty=True)` for strict `started_at` verdict eligibility, preserving alternate-manifest fallback after a valid preferred manifest lacks `started_at`.
  - Use the caller’s existing normal timestamp mode where `updated_at` is currently permitted.
  - Use `run_ended_at(..., continue_on_empty=True)` to preserve `ended_at` → `completed_at` → `updated_at` precedence across candidate manifests.
  - Use `larch_version(..., continue_on_empty=True)` where current ground-truth behavior skips an empty or invalid preferred version and checks `run-manifest.json`.
- Repoint `_ground_truth_gc_slimmed_fallback` to `safe_child_run_dirs` for each skill root under `log_root`, preserving `seen_gc` deduplication and fallback counts.
- Preserve review TSV schema filtering, version validation, datetime parsing, and all date-window semantics at the caller boundary.
- Do not exempt this module from the ratchet.

### UPDATED: python/larch/issue/rejected_analysis.py

- Replace direct `implement/*` and `review/*` corpus globs with `safe_child_run_dirs(logs / "implement")` and `safe_child_run_dirs(logs / "review")`.
- Preserve implement-before-review processing, date-window filtering, `_join_run_findings` ordering, and current warning behavior.
- Replace `_run_started_at` with `run_started_at(..., allow_updated_at_fallback=True, continue_on_empty=False)` to preserve `updated_at` fallback and first-valid-object stop behavior.
- Replace `_round_from_path` with `round_num_from_path`, explicitly mapping `None` to existing values.
- Use `classification_tsv_paths(..., round_sort="lexical")` where it replaces copied canonical glob logic. Preserve rejected analysis’s existing lexical multi-round ordering and JSONL fallback ordering.
- Preserve current empty-value, review-versus-implement, and date-window behavior.
- Add regression fixtures for symlinked and escaping child run directories, `updated_at`-only inclusion, first-valid-object timestamp stopping, lexical classification ordering, JSONL fallback behavior, and empty-round formatting.

### UPDATED: python/larch/issue/_oos.py

- Repoint `iter_filed_oos_records` committed `implement` and `design` run enumeration through `safe_child_run_dirs`.
- Preserve artifact-specific filtering, record ordering, and all non-corpus reads.
- Use shared metadata helpers only where their explicitly selected fallback and candidate policy matches current behavior.
- Add focused coverage for safe enumeration without changing OOS record selection.

### UPDATED: python/larch/review/_voting_calibration.py

- Replace the dual-manifest timestamp loop with `run_started_at` using the existing caller-specific `updated_at` and first-valid-object policy.
- Replace classification triple-globs with `discover_classifications` or `classification_tsv_paths`, pinning the existing sort order.
- Convert the shared timestamp string through the existing datetime parser.
- Preserve `VoterCalibrationDiscoveryRow`, run-directory derivation, code-review panel-label mapping, sorting, and recent-run window behavior.
- Add a regression assertion that fixture output remains unchanged.

### UPDATED: python/larch/report/gc_run_logs.py

- Replace `_iter_run_dirs` with `safe_child_run_dirs`.
- Replace direct timestamp parsing with `run_started_at(..., allow_updated_at_fallback=False, manifest_candidates=("manifest.json",))`.
- Preserve the existing Git commit-date fallback whenever `manifest.json` has no usable `started_at`, including when only `run-manifest.json` supplies one.
- Route recursive escape-symlink detection and directory sizing through the shared validated-run inspection contract. Retain the deeper escape-symlink check before any slimming or deletion.
- Add regression tests proving:
  - An `updated_at`-only `manifest.json` still takes the Git-date fallback path.
  - A missing `manifest.json` plus `run-manifest.json` with `started_at` still takes the Git-date fallback path.
  - Validated recursive inspection rejects escaping descendants without requiring a broad lint exemption.

### UPDATED: python/larch/report/final_report.py

- Route committed run-manifest reads used by scanner-style report recovery through the shared corpus API only where its explicit candidate and field contract matches.
- Preserve status recovery, main-model lookup, and empty-value behavior.
- Leave dispatcher and session-manifest reads alone because they are not committed corpus walks.
- Add focused tests for any changed metadata fallback boundary.

### UPDATED: python/larch/report/tokens.py

- Repoint both committed `larch-logs` corpus iterators used by panel-prompt and checks-digest reporting through `safe_child_run_dirs` and contained per-run artifact checks.
- Preserve existing canonical layout coverage, artifact selection, ordering, symlink filtering, and report output.
- Keep fixed lookups such as a ledger inside an already selected run directory as caller-owned artifact reads. They must remain outside the lint’s prohibited corpus-root traversal category.
- Add focused `python/tests/report/test_tokens.py` coverage for safe child enumeration, rejected symlinked run directories, and unchanged panel-prompt and checks-digest output ordering.

### UPDATED: python/larch/issue/audit_runs.py

- Repoint corpus candidate-run enumeration in `map_runs_main` through `safe_child_run_dirs` before checking `parent-issue.md`, `manifest.json`, or other accepted artifacts.
- Use the shared committed-run manifest reader where an accepted run manifest is required.
- Preserve direct reads of non-corpus state and sidecar artifacts.
- Keep existing informational versus failing outcomes for missing, malformed, or pre-cutover data.
- Add a regression test ensuring symlinked candidate directories are excluded while existing informational and failing outcomes remain unchanged.

### UPDATED: skills/fluff-analysis/scripts/fluff-analysis.py

- Import shared corpus helpers through the script’s existing `python/` path setup.
- Replace copied manifest metadata reads and round parsing with shared helpers, using `manifest_candidates=("manifest.json",)` and `run_started_at(..., allow_updated_at_fallback=False)` to preserve manifest-only period bucketing.
- Use manifest-only version reads as well, so a `run-manifest.json`-only directory cannot change version filtering or counts.
- Replace raw implement run enumeration with `safe_child_run_dirs`.
- Replace raw design run enumeration with a scoped, safe recursive design discovery path built from `safe_child_run_dirs`. Preserve existing non-plan-review design coverage rather than narrowing discovery to canonical plan-review TSV locations.
- Use `classification_tsv_paths` only for the canonical artifacts it covers. Retain caller-owned recursive design handling and JSONL fallbacks.
- Preserve string-shaped report fields, deterministic ordering, thread-pool behavior, cutoff and version filters, in-progress session analysis, and existing CLI output.
- Remove imports from sibling scanner modules when the shared corpus API owns those helpers.
- Extend corpus harness coverage for symlink rejection, design-layout retention, unchanged period bucketing, and a `run-manifest.json`-only directory that remains excluded from historical manifest-only metadata behavior.

### UPDATED: skills/voter-calibration/scripts/voter-calibration.py

- Replace `_discover` with `discover_classifications` using the existing skill set and pinned sort policy.
- Keep the script’s existing panel labels and downstream row format as caller-owned mapping.
- Preserve plugin-root import bootstrapping and CLI output.
- Add or update the existing harness to assert unchanged fixture output.

### NEW: python/larch/lint/lint_run_log_walkers.py

- Implement the AST ratchet as a module-level `main(argv) -> int`.
- Enumerate tracked Python sources in `python/` and the two in-scope skill scanner scripts. Exclude generated, fixture, cache, and committed run-log trees.
- Detect:
  - Raw committed-corpus `glob`, `rglob`, `walk`, and `scandir` traversal.
  - Copied canonical classification traversal.
  - Dual-name `manifest.json` / `run-manifest.json` candidate loops.
- Treat recursive inspection as valid only when it uses the shared validated-run helper or a narrow, structurally provable already-validated run directory. Reject corpus-root recursive walks.
- Avoid false positives for run-log writers, fixed artifact reads inside a selected run, ordinary manifest reads, unrelated traversal, and session-local paths.
- Exempt `run_log_corpus.py` as the sole shared API owner.
- Temporarily exempt only `retro_fix_cursor.py`, `retro_v3_sweep.py`, and `cleanup_implement_logs.py`, each with an inline #7008 reason.
- Emit stable file, line, rule, and remediation diagnostics.
- Fail closed on unreadable or invalid Python source.

### UPDATED: python/larch/cli.py

- Register `("lint", "run-log-walkers")` to the new lint module.

### UPDATED: Makefile

- Add a `lint-run-log-walkers` target.
- Add the target to `.PHONY`.
- Add it to the `lint` aggregate.
- Add `run-log-walkers` to the `py-lint-checks-fast` foreach list so CI fast lint enforces the ratchet.

### UPDATED: .pre-commit-config.yaml

- Add a `lint-run-log-walkers` pre-commit hook mirroring the existing Python lint-hook convention.
- Scope it to every source file scanned by the ratchet: `python/**/*.py` plus `skills/fluff-analysis/scripts/fluff-analysis.py` and `skills/voter-calibration/scripts/voter-calibration.py`.
- Keep `pass_filenames: false` so the hook checks the complete tracked scanner surface rather than only the changed path list.

### UPDATED: docs/linting.md

- Document `python3 python/cli.py lint run-log-walkers`.
- State that the check is included in the standard lint aggregate, fast Python lint, and pre-commit.
- Briefly distinguish valid shared-helper use and fixed per-run artifact reads from prohibited copied committed-corpus traversal.

### UPDATED: python/tests/report/test_run_log_corpus.py

- Cover safe child discovery, including missing roots, root-resolution failures, child-enumeration `OSError`, symlink children, containment, ordering, and warnings.
- Prove `load_run_manifest` remains `manifest.json`-only.
- Cover default dual-name precedence, explicit manifest-only candidate scope, and malformed or non-object candidate fallback.
- Cover `run_started_at` with and without `updated_at` fallback, including first-valid-object stop behavior and `continue_on_empty` behavior.
- Cover `run_ended_at` precedence: `ended_at`, then `completed_at`, then `updated_at`, including alternate-candidate fallback.
- Cover `larch_version` first-object and continue-on-empty modes, absent values, and invalid types.
- Cover malformed JSON, symlink manifests, missing fields, and invalid value types.
- Cover round extraction from directories, filenames, and paths without a round.
- Cover `classification_tsv_paths` and `discover_classifications` for all three canonical layouts, safe-root filtering, deterministic skill and path ordering, and both supported round-sort policies.
- Cover the narrow validated-run recursive inspection contract, including an escaping descendant.

### UPDATED: python/tests/calibration/test_difficulty_calibration.py

- Assert root-resolution failures map to `missing_skill_roots`.
- Assert child-enumeration `OSError` maps to `unreadable_skill_roots`.
- Lock existing unsafe-child accounting, round formatting, and fixture output.

### UPDATED: python/tests/issue/test_rejected_analysis.py

- Add regression coverage for safe implement and review enumeration, including symlinked and escaping child directories.
- Lock existing implement and review ordering, date-window behavior, lexical classification ordering, JSONL fallback behavior, and empty-round formatting.
- Add fixtures proving `updated_at`-only runs remain eligible and that a valid preferred manifest with no usable timestamps does not fall through to the alternate manifest.

### UPDATED: python/tests/issue/test_audit_runs.py

- Add a regression test proving `map_runs_main` excludes symlinked candidate run directories while existing informational and failing outcomes remain unchanged.

### UPDATED: python/tests/issue/test_ground_truth.py

- Add coverage for strict started-at alternate-manifest fallback after a valid preferred manifest lacks `started_at`.
- Add coverage for shared started-at strict mode, ended-at fallback precedence, version alternate-candidate behavior, safe GC fallback enumeration, and unchanged review schema filtering.

### UPDATED: python/tests/issue/test_oos.py

- Add focused safe-walker coverage for committed design and implement enumeration while preserving artifact-specific selection.

### UPDATED: python/tests/report/test_gc_run_logs.py

- Add regression tests proving `updated_at` does not replace GC’s Git-date fallback when `started_at` is absent.
- Add a regression test proving `run-manifest.json`-only `started_at` does not replace GC’s Git-date fallback.
- Cover validated recursive inspection and escaping descendant handling.

### UPDATED: python/tests/report/test_tokens.py

- Add focused coverage for safe committed-corpus enumeration in both affected token iterators.
- Prove symlinked run directories are excluded while fixed artifacts inside valid runs remain discoverable.
- Lock existing panel-prompt and checks-digest output ordering.

### UPDATED: python/tests/review/test_voting.py

- Lock existing voter-calibration classification ordering, panel attribution, and recent-window output against the shared discovery API.

### NEW: python/tests/lint/test_lint_run_log_walkers.py

- Test accepted shared-helper usage and validated per-run recursive inspection.
- Test rejection of raw glob, recursive glob, walk, `scandir`, classification triple-glob, and dual-manifest loop patterns.
- Test that unrelated file traversal, fixed artifact reads, run-log writers, ordinary manifest reads, and session-local paths do not trigger.
- Test owner exclusion and the narrow #7008 exemptions.
- Test coverage of `python/` and both in-scope skill scanner scripts.
- Test CLI return codes and stable diagnostics.

## Edge cases

- A review artifact may have only `run-manifest.json`; metadata helpers must still read it when the caller’s historical metadata contract permits dual-name lookup.
- If both manifest names exist, `manifest.json` wins unless the caller explicitly uses `continue_on_empty=True` and the preferred valid object lacks a usable requested field.
- Callers with historical manifest-only behavior must pass `manifest_candidates=("manifest.json",)`; disabling `updated_at` fallback alone is insufficient.
- `load_run_manifest` must continue rejecting a run that has only `run-manifest.json`.
- A malformed preferred manifest must permit checking the next allowed candidate.
- A valid preferred manifest object with no `started_at` must not implicitly fall through to `run-manifest.json` unless the caller explicitly opts into that historical behavior.
- Rejected analysis must retain `updated_at` fallback but stop after a valid preferred object when both relevant timestamp fields are empty.
- Strict ground-truth verdict filtering must not accept `updated_at`, but must retain its existing alternate-manifest `started_at` fallback.
- GC retention must not accept `updated_at` or `run-manifest.json` `started_at` when `manifest.json` lacks `started_at`.
- Ground-truth ended-time selection must retain `ended_at` → `completed_at` → `updated_at` precedence.
- Review classification files still need caller-owned schema validation.
- Classification APIs must preserve canonical layouts only; fluff’s recursive design layouts remain explicitly caller-owned and safe-walker-based.
- `round_num_from_path` returns `None`; each caller must map it before using legacy string, integer, or nullable output fields.
- Rejected analysis must use lexical classification round ordering.
- GC must scan safely even when a run lacks an accepted manifest, because it can recover the date from Git.
- JSONL fallback sources are caller-specific and must not disappear when canonical TSV discovery moves to the shared helper.
- Recursive directory sizing and symlink inspection are valid only within an already validated run directory.
- The lint must not classify run-log writers, fixed artifact lookups, or session-local paths as corpus walkers.
- The lint exemption must remain limited to the three files scheduled for deletion by #7008.

## Failure modes

- A field-specific metadata fallback or candidate-scope mismatch could alter run eligibility, version selection, retention, or period bucketing.
- Applying manifest acceptance to review artifacts could silently drop valid `run-manifest.json` metadata.
- Applying dual-manifest metadata to GC or fluff could change Git-date retention, period buckets, version filtering, or counts.
- Replacing GC enumeration with manifest-filtered `run_dirs` could hide malformed runs from retention.
- Replacing fluff’s recursive design discovery with only canonical plan-review discovery could drop existing design coverage.
- An unpinned round conversion could alter sorting, labels, JSONL keys, or empty-round rendering.
- A shared walker that does not distinguish resolution from enumeration failures could change difficulty-calibration warning counters.
- Overbroad lint matching could block legitimate artifact code or validated per-run inspection; narrow negative tests must cover exclusions.
- Underbroad lint matching could allow another copied walker; positive fixtures must cover every forbidden traversal shape.
- A broad GC exemption could permit new unsafe corpus-root recursion.
- Omitting `tokens.py` or either skill scanner script from ratchet scope could leave committed-corpus walkers unmanaged.
- A fast-lint or pre-commit wiring omission could let bypassing scanners land without local or CI enforcement.
- The skill scripts can fail outside the checkout if imports bypass their existing plugin-root bootstrap.

## Testing strategy

- Run focused corpus, token, and lint tests:
  - `python3 -m pytest python/tests/report/test_run_log_corpus.py python/tests/report/test_tokens.py python/tests/lint/test_lint_run_log_walkers.py -q`
- Run affected scanner suites:
  - `python3 -m pytest python/tests/calibration/test_difficulty_calibration.py -q`
  - `python3 -m pytest python/tests/issue/test_ground_truth.py python/tests/issue/test_rejected_analysis.py python/tests/issue/test_audit_runs.py python/tests/issue/test_oos.py -q`
  - `python3 -m pytest python/tests/review/test_voting.py -q`
  - `python3 -m pytest python/tests/report/test_gc_run_logs.py python/tests/report/test_final_report.py -q`
- Run script harnesses:
  - `bash skills/fluff-analysis/scripts/test-fluff-analysis.sh`
  - `bash skills/fluff-analysis/scripts/test-fluff-analysis-corpus.sh`
  - `bash skills/voter-calibration/scripts/test-voter-calibration.sh`
- Run enforcement paths:
  - `python3 python/cli.py lint run-log-walkers`
  - `make py-lint-checks-fast`
  - Run the targeted pre-commit hook for changed `python/` and skill-scanner Python files.
- Run Python lint and type checks only for the changed Python files.
- Verify report output, scanner counts, token reports, voter-calibration output, ground-truth verdicts, GC retention dates, and fluff period bucketing remain unchanged on existing fixtures.

## Acceptance

- Run focused corpus, token, and lint tests:
  - `python3 -m pytest python/tests/report/test_run_log_corpus.py python/tests/report/test_tokens.py python/tests/lint/test_lint_run_log_walkers.py -q`
- Run affected scanner suites:
  - `python3 -m pytest python/tests/calibration/test_difficulty_calibration.py -q`
  - `python3 -m pytest python/tests/issue/test_ground_truth.py python/tests/issue/test_rejected_analysis.py python/tests/issue/test_audit_runs.py python/tests/issue/test_oos.py -q`
  - `python3 -m pytest python/tests/review/test_voting.py -q`
  - `python3 -m pytest python/tests/report/test_gc_run_logs.py python/tests/report/test_final_report.py -q`
- Run script harnesses:
  - `bash skills/fluff-analysis/scripts/test-fluff-analysis.sh`
  - `bash skills/fluff-analysis/scripts/test-fluff-analysis-corpus.sh`
  - `bash skills/voter-calibration/scripts/test-voter-calibration.sh`
- Run enforcement paths:
  - `python3 python/cli.py lint run-log-walkers`
  - `make py-lint-checks-fast`
  - Run the targeted pre-commit hook for changed `python/` and skill-scanner Python files.
- Run Python lint and type checks only for the changed Python files.
- Verify report output, scanner counts, token reports, voter-calibration output, ground-truth verdicts, GC retention dates, and fluff period bucketing remain unchanged on existing fixtures.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 525
diff_deleted: 570
mechanical_churn: true
oversize_override: operator
diff_lines: 1095
