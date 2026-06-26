# Review Round 1

- Mode: `diff`
- 5 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: fluff-analysis inflates artifact count for empty/malformed assessments
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-gatec-persist-output.txt, dyn-dyn-runlog-audit-output.txt
- **Severity**: important
- **Concern**: `_collect_guideline_assessment_coverage` sets `has_artifact=True` for existing but empty, whitespace-only, symlinked, or otherwise non-regular `architectural-guideline-assessment.md` files while `assessment_kind` stays `"missing"`. That inflates the coverage table “runs with assessment artifact” aggregate while `audit-runs` `_guideline_assessment_scan_obj` correctly returns `fail` for the same files, breaking the shared clean/deviation classification contract across audit surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Set has_artifact=False for symlinks non-regular files and regular files where not body.strip(); only non-empty clean or deviation bodies get has_artifact=True
  - From dyn-dyn-gatec-persist-output.txt: Treat whitespace-only bodies like a missing artifact (`has_artifact=False`, `assessment_kind="missing"`), or add a distinct `malformed` kind and exclude it from the artifact count.
  - From dyn-dyn-runlog-audit-output.txt: Align fluff ingest with audit-runs: treat empty/whitespace-only, symlink, and non-regular paths as non-artifacts (`has_artifact=False`, `assessment_kind="missing"`) or add an explicit `malformed` kind excluded from the "with artifact" aggregate; add a fixture run with an empty assessment file and assert aggregate counts stay consistent with audit-runs semantics.


### FINDING_5: unreadable assessment file aborts audit-runs scan-run
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_guideline_assessment_scan_obj()` assumes `read_text()` succeeds. A permission-locked, race-corrupted, or otherwise unreadable `architectural-guideline-assessment.md` raises out of `scan_run_main` instead of emitting a per-run `fail` row, aborting `audit-runs scan-run --skill design` for the whole PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Catch OSError around the read, return a fail row with a detail message, and keep scanning the remaining runs.
  - From codex-specialist-testing-output.txt: Wrap read_text in try/except OSError and emit a fail JSON object with detail


### FINDING_9: design GC keep set omits architectural-guideline-assessment.md
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-dyn-runlog-audit-output.txt
- **Severity**: important
- **Concern**: The branch adds `architectural-guideline-assessment.md` as a committed auditable design artifact but `SKILL_KEEP["design"]` in `gc_run_logs.py` still omits that basename. After `/gc-run-logs` slimming, the file is deleted with other non-keep forensics, so `audit-runs` and `/fluff-analysis` lose historical evidence the feature is meant to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Add the file to the design keep set in GC docs and code and cover it with a regression test.
  - From dyn-dyn-runlog-audit-output.txt: Add `architectural-guideline-assessment.md` to `SKILL_KEEP["design"]`, mirror it in the `docs/run-logs.md` retention consumer-core list, and add a `python/test_gc_run_logs.py` regression asserting slimming retains it.


### FINDING_12: persist-design-assessment accepts whitespace-only sidecar input
- **Reviewer(s)**: dyn-dyn-gatec-persist-output.txt
- **Severity**: important
- **Concern**: On the `present` + `--assessment-file` path, `persist_design_assessment` accepts whitespace-only sidecar input: `_normalize_assessment_text("")` becomes `"\n"`, the CLI exits `0`, and Gate C can approve. The committed file is empty per `audit_runs._guideline_assessment_scan_obj` (`body.strip()` is false → `fail`), so persistence succeeds while downstream audit treats the artifact as malformed. There is no test for an empty sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gatec-persist-output.txt: After reading `--assessment-file`, reject content whose `strip()` is empty with a non-zero exit (mirror the audit-runs non-empty rule) before calling `_write_design_assessment_atomic`.


### FINDING_13: stale symlink/directory survives absent/invalid persistence path
- **Reviewer(s)**: dyn-dyn-gatec-persist-output.txt
- **Severity**: important
- **Concern**: On `absent`/`invalid`, `_safe_unlink_assessment` only removes regular non-symlink files and `persist_design_assessment` returns `0` when no `OSError` is raised. A stale `architectural-guideline-assessment.md` symlink or directory remains in `$DESIGN_TMPDIR`, so Gate C persistence “succeeds” but Step 5c publish later hits `_copy_tree_redacted` which returns `ok=False` for a top-level symlink and aborts the whole publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gatec-persist-output.txt: After `_safe_unlink_assessment`, if the path still exists (symlink, directory, or other non-regular entry), exit non-zero with stderr, same as unlink failure, so Gate C halts before approval.


