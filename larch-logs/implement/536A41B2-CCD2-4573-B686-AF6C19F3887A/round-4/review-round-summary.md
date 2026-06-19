# Review Round 4

- Mode: `diff`
- 4 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: legacy_cluster_digest compares new runner to itself (tautological parity)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-symilar-parity-output.txt, dyn-lint-surface-output.txt
- **Severity**: blocking
- **Concern**: `legacy_cluster_digest()` in `python/duplicate_code_parity.py:44-57` does not derive clusters from legacy pylint. It reuses the new runner pipeline (`_bootstrap_linter` → `_ingest_files` → `_find_commonalities` → `_clusters_from_commonalities` → `_render_digest`), so `assert_parity()` compares two invocations of the same implementation (often both with `jobs=1`). Pylint and the new runner can disagree on reportable clusters while both exit 1, yet digest parity still passes. The merge-blocking cluster-digest gate cannot detect R0801 membership drift between `pylint -j 1` and the new CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement a true pylint close()-based legacy digest and compare it to the new runner digest.
  - From cursor-specialist-edge-cases-output.txt: Build legacy digest from pylint checker close() (or equivalent subprocess) with the same normalization as --emit-cluster-digest
  - From cursor-specialist-testing-output.txt: Implement legacy digest extraction from an independent pylint -j 1 run (close/reporter capture) normalized to the same digest format; compare that to run_duplicate_code().digest.
  - From codex-generic-output.txt: Compute the legacy digest through an independent Pylint `-j 1` / `SimilaritiesChecker.close()` path, or otherwise capture legacy checker reportability without calling `duplicate_code._find_commonalities()` / `_clusters_from_commonalities()`.
  - From dyn-symilar-parity-output.txt: implement `legacy_cluster_digest()` on pylint's own `SimilaritiesChecker.close()` path (bootstrap a linter, ingest modules the legacy way, call `checker.close()`, then normalize emitted R0801 clusters with the same digest format), or extract clusters from pylint's message store after a full `-j 1` run. Keep `run_duplicate_code().digest` on the parallel runner path and assert the two digests match.
  - From dyn-lint-surface-output.txt: Implement a true legacy digest extractor driven by pylint's own checker `close()` path (or parse reportable R0801 output from the subprocess pylint run), and keep the new runner digest separate so the gate compares independent implementations.


### FINDING_3: New runner exit stricter than legacy pylint score-based exit
- **Reviewer(s)**: dyn-symilar-parity-output.txt
- **Severity**: important
- **Concern**: In `python/duplicate_code.py:271-272`, exit status is `1 if clusters else 0`, where `clusters` is any non-empty `_compute_sims()` result. Legacy pylint can still exit `0` when R0801 was emitted but `generate_reports()` returns a score `>= fail-under` (10 in `python/.pylintrc`) and `fail-on` is empty, because `Run` takes the score branch before `msg_status`. The new runner always fails on non-empty clusters, so it is stricter than legacy pylint for minor duplicates that do not pull the score below 10.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-symilar-parity-output.txt: either document and test this as an intentional tightening, or align exit semantics with legacy pylint (for example mirror pylint's post-`close()` exit decision, or pass `--fail-under=0` / equivalent in the legacy parity subprocess and match that contract in the runner).


### FINDING_4: Full-tree legacy/new parity is opt-in and not enforced in CI
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-lint-surface-output.txt
- **Severity**: important
- **Concern**: Full-tree legacy/new parity in `python/test_duplicate_code_parity.py:105-112` is skipped unless `LARCH_DUPLICATE_CODE_FULL_TREE_PARITY=1`. CI runs only `make py-lint-duplicate-code` (`.github/workflows/ci.yaml:608-609`); `make py-lint-duplicate-code-parity` is never wired in. Digest and exit-code regressions on the real `python/` tree can merge undetected despite the plan's mandatory pre-cutover merge blocker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Run full-tree exit-code and true legacy digest parity in CI or as a mandatory make target.
  - From cursor-specialist-edge-cases-output.txt: Wire make py-lint-duplicate-code-parity into CI or run full-tree parity test unconditionally
  - From cursor-specialist-testing-output.txt: Wire make py-lint-duplicate-code-parity into the python-lint-duplicate-code CI job or remove the env skip on test_full_python_tree_legacy_new_parity once finding 1 is fixed.
  - From dyn-lint-surface-output.txt: Wire `make py-lint-duplicate-code-parity` (or an equivalent CLI subcommand) into CI before or alongside the production target, and remove the opt-in skip for the full `python/` tree check once the legacy digest is fixed.


### FINDING_5: CI speed acceptance (≤90s) and matrix sharding not addressed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The diff does not address the plan's ≤90s wall-time hard gate or conditional matrix sharding for `python-lint-duplicate-code` in `.github/workflows/ci.yaml:586-609`. The job may remain a CI bottleneck; the plan acceptance criterion cannot be satisfied without follow-up workflow work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Measure GHA wall time; add matrix sharding if >90s before close.
  - From cursor-specialist-testing-output.txt: Measure ubuntu-latest job duration; if >90s add matrix sharding in ci.yaml in this PR and re-measure before closing the issue.


