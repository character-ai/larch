## Plan

Confidence: high. This is a mechanical facade shrink with direct module ownership visible in the repository.

Before editing, confirm Piece 1 has landed. The current checkout still has out-of-scope `run_logs` facade consumers. Do not expand this piece to migrate them. Block implementation until the dependency removes or repoints those consumers.

### UPDATED: python/larch/report/run_logs.py

- Remove the 162 re-export imports targeted by the issue.
- Retain the 26 locally defined classes, helpers, and CLI entrypoints.
- Import `run_log_batch`, `run_log_manifest`, `run_log_commit`, and `run_log_flush` as modules where residual local implementations need them; use qualified references so no bare owner import recreates facade attributes.
- Keep only imports those local implementations use.
- Update the module description and narrow obsolete unused-import suppressions.
- Preserve all local behavior and wire output.

### UPDATED: python/larch/issue/analyze_issues.py

- Remove the 20 private imports used only as re-exports.
- Retain imports consumed by the analyzer’s own entrypoints and report assembly.
- Remove obsolete unused-import suppressions where the shrink permits.
- Do not change analysis logic or output.

### UPDATED: python/larch/design/design_publish.py

Import `append_execution_issue` from `run_log_batch` instead of accessing it through `run_logs`.

### UPDATED: python/larch/design/design_log_publish_flow.py

Use the `run_log_batch` owner for execution-issue recording.

### UPDATED: python/larch/review/review_and_fix.py

Route all execution-issue appends through `run_log_batch`.

### UPDATED: python/larch/issue/file_oos.py

Use `run_log_batch.append_execution_issue` in the warning path.

### UPDATED: python/larch/state/finalize.py

- Import manifest types and lifecycle helpers from `run_log_manifest`.
- Import log commit behavior from `run_log_commit`.
- Preserve teardown recovery, manifest updates, and commit handling.

### UPDATED: python/larch/issue/oos_filer.py

Call `_update_manifest_v2` through `run_log_manifest`, preserving the existing private-use justification and re-entry behavior.

### UPDATED: python/larch/implement/step_7a.py

- Route flush functions and flush-private helpers through `run_log_flush`.
- Import supporting manifest and batch symbols from their defining modules.
- Use `larch.core.proc` directly instead of the facade binding.
- Preserve preterminal outcome checks and degraded flush handling.

### UPDATED: skills/voter-calibration/scripts/voter-calibration.py

Split analyzer imports among `analyze_issues`, `_ground_truth`, `_oos`, and `_util` according to ownership. Keep only true analyzer entrypoints imported from `analyze_issues`.

### UPDATED: python/tests/issue/test_analyze_issues.py

- Exercise private helpers, caches, models, and constants through their defining submodules.
- Keep entrypoint and analyzer-local tests on `analyze_issues`.
- Patch the binding actually resolved by the code under test.
- Add or retain a regression assertion that `_join_implement_run_records` is absent from the facade.

### UPDATED: python/tests/report/test_run_logs.py

- Access batch, manifest, commit, and flush helpers through their defining modules.
- Keep tests for the 26 residual definitions on `run_logs`.
- Move monkeypatch targets to the module whose runtime binding the tested function resolves.
- Add or retain a regression assertion that `effective_run_id` is absent from `run_logs`.

### UPDATED: python/tests/state/test_finalize.py

- Retarget imports, type references, and monkeypatches from `run_logs` to the exact bindings resolved by `finalize`.
- Patch manifest recovery and lifecycle behavior through `finalize.run_log_manifest`, commit behavior through `finalize.run_log_commit`, and any directly imported local binding through `finalize`.
- Preserve recovery, initialization, and teardown failure-path coverage without invoking real manifest, commit, or flush behavior.

### UPDATED: python/tests/implement/test_step_7a.py

- Replace `step_7a.run_logs` patches with the owner-module bindings that `step_7a` resolves, including `step_7a.run_log_flush`, `step_7a.run_log_batch`, `step_7a.run_log_manifest`, and direct `proc` bindings as applicable.
- Preserve flush, diagnostic, preterminal, and degraded-outcome test coverage while preventing real flush or commit behavior.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Replace `from larch.report import run_logs` with `from larch.report import run_log_batch` (or import `append_execution_issue` from `run_log_batch`).
- In `fake_invoke` inside `test_append_warning_normalizes_plain_text_for_final_summary`, call `run_log_batch.append_execution_issue` instead of `run_logs.append_execution_issue`.
- Drop the `run_logs` import if no other test in the file needs it.
- Preserve the warning-normalization regression coverage for plain-text and already-bulleted entries.

### UPDATED: python/tests/review/test_review_and_fix.py

- Retarget the warning-path monkeypatch to `review_and_fix.run_log_batch.append_execution_issue`, or the equivalent exact binding introduced by the production import.
- Preserve the fail-open `OSError` assertion and ensure it exercises the migrated call path.

### UPDATED: python/monkeypatch-facade-binding-baseline.json

Regenerate with `make regen-monkeypatch-facade-binding-baseline`. Confirm facade-binding rows shrink and no new unexplained rows appear.

### UPDATED: python/keyword-only-baseline.json

Regenerate with `make regen-keyword-only-baseline` after import and call-site changes.

### UPDATED: python/suppression-reason-baseline.json

Regenerate with `make regen-suppression-reason-baseline` so removed or narrowed facade suppressions drop from the baseline.

### UPDATED: python/README.md

Replace the monolithic `run_logs.py` description with the residual facade and its `run_log_batch`, `run_log_manifest`, `run_log_commit`, and `run_log_flush` owners.

## Edge cases

- Keep imports required by residual `run_logs` functions even when tests also access those bindings.
- Use qualified owner-module references inside residual `run_logs` helpers so removed names cannot leak back onto the facade.
- Distinguish direct helper tests from consumer-binding monkeypatches. Patching only the defining module may not affect an already imported binding.
- Preserve private-use suppressions for intentional direct calls to owner modules.
- Avoid importing through `run_logs` from any defining submodule, which could create a cycle.
- Consumer tests that fake CLI subprocesses may still call execution-issue helpers directly; retarget those calls to `run_log_batch` even when production dispatch code never imported the facade.

## Failure modes

- Removing the facade before Piece 1 lands can break remaining out-of-scope consumers with `AttributeError`.
- An incorrect monkeypatch target can run real commit or flush behavior during tests.
- Consumer tests left patching facade bindings can fail at patch setup or silently stop exercising intended recovery and fail-open paths.
- `test_implement_dispatch.py` left calling `run_logs.append_execution_issue` fails at runtime with `AttributeError` once the re-export is removed, even though `implement_dispatch` production code does not use the facade.
- Manual baseline edits can retain stale debt or widen a ratchet. Use the regeneration targets and inspect their diffs.
- An over-broad import cleanup can remove dependencies used by the 26 residual definitions.

## Testing strategy

- Run the focused suites:
  - `python3 -m pytest python/tests/report/test_run_logs.py python/tests/issue/test_analyze_issues.py`
  - `python3 -m pytest python/tests/state/test_finalize.py python/tests/implement/test_step_7a.py python/tests/implement/test_implement_dispatch.py python/tests/review/test_review_and_fix.py`
  - `python3 -m pytest python/tests/implement/test_implement_dispatch.py::test_append_warning_normalizes_plain_text_for_final_summary`
  - `make test-voter-calibration`
  - Focused tests for the remaining named production callers.
- Run both facade absence checks from an environment where `python/` is importable:
  - `python -c "import larch.report.run_logs; assert not hasattr(larch.report.run_logs,'effective_run_id')"`
  - `python -c "import larch.issue.analyze_issues; assert not hasattr(larch.issue.analyze_issues,'_join_implement_run_records')"`
- Run `python3 python/cli.py lint monkeypatch-facade-binding`.
- Run the keyword-only and suppression-reason lints after baseline regeneration.
- Run `make py-lint`.
- Search for the removed facade attributes and confirm only intentional residual or dependency-owned references remain.

## Acceptance

- Run the focused suites:
  - `python3 -m pytest python/tests/report/test_run_logs.py python/tests/issue/test_analyze_issues.py`
  - `python3 -m pytest python/tests/state/test_finalize.py python/tests/implement/test_step_7a.py python/tests/implement/test_implement_dispatch.py python/tests/review/test_review_and_fix.py`
  - `python3 -m pytest python/tests/implement/test_implement_dispatch.py::test_append_warning_normalizes_plain_text_for_final_summary`
  - `make test-voter-calibration`
  - Focused tests for the remaining named production callers.
- Run both facade absence checks from an environment where `python/` is importable:
  - `python -c "import larch.report.run_logs; assert not hasattr(larch.report.run_logs,'effective_run_id')"`
  - `python -c "import larch.issue.analyze_issues; assert not hasattr(larch.issue.analyze_issues,'_join_implement_run_records')"`
- Run `python3 python/cli.py lint monkeypatch-facade-binding`.
- Run the keyword-only and suppression-reason lints after baseline regeneration.
- Run `make py-lint`.
- Search for the removed facade attributes and confirm only intentional residual or dependency-owned references remain.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
mechanical_churn: true
oversize_override: operator
diff_lines: 705
