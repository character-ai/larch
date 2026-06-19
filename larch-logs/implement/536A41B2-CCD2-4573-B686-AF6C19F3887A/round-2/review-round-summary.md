# Review Round 2

- Mode: `diff`
- 8 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Parity fixture tests compare exit codes only, not legacy vs new digest equality
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-symilar-parity-output.txt, dyn-lint-surface-output.txt
- **Severity**: important
- **Concern**: Parity tests on fixtures verify exit codes but never compute a legacy cluster digest or assert `legacy_digest == new_digest`. Two runners could disagree on reportable R0801 cluster membership while both exit `1`, passing CI despite violating the equivalence contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add legacy digest extraction and assert legacy_digest == new_digest on shared fixtures.
  - From cursor-specialist-edge-cases-output.txt: Add legacy_cluster_digest helper plus fixture and full-tree tests asserting exit code and digest equality.
  - From dyn-symilar-parity-output.txt: Add a shared legacy digest helper (reuse the new runner’s normalization over pylint’s own ingestion/`_compute_sims` path), assert digest equality in parity tests on fixtures, and add an opt-in full-tree gate (pytest marker or CI step) that fails when exit codes or digests diverge.
  - From dyn-lint-surface-output.txt: In the same test (and any full-tree gate), compute `legacy_digest` via the shared legacy extractor and assert `legacy_digest == new_digest`, not merely that the new digest is non-empty.


### FINDING_2: `test_digest_mismatch_blocks_even_when_exit_codes_match` is tautological
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-symilar-parity-output.txt
- **Severity**: important
- **Concern**: The digest-mismatch gate test uses a hardcoded `wrong_digest` and never compares actual legacy vs new digests when both exit `1`. It cannot detect real cluster-membership divergence with matching exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Compare actual legacy and new digests; add a negative case with an intentionally wrong digest.
  - From cursor-specialist-testing-output.txt: A compute legacy digest via helper; assert legacy_digest == new_digest; add negative digest-mismatch case
  - From dyn-symilar-parity-output.txt: Replace this with a test that runs both runners on the same fixture, asserts matching digests on the happy path, and asserts the gate fails when the new digest is intentionally perturbed while exit codes still match.


### FINDING_3: No automated full-tree legacy vs new parity gate despite Makefile cutover
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-symilar-parity-output.txt, dyn-lint-surface-output.txt
- **Severity**: important
- **Concern**: There is no `duplicate_code_parity.py` (or equivalent) helper and no encoded full-`python/` tree gate comparing exit codes and cluster digests. With the Makefile already cut over to the new runner, file-set or cluster drift on the real `python/` tree could change CI pass/fail vs the legacy baseline without any test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement parity helper and run exit-code + digest comparison on python/ in pytest or CI.
  - From cursor-specialist-edge-cases-output.txt: Add legacy_cluster_digest helper plus fixture and full-tree tests asserting exit code and digest equality.
  - From cursor-specialist-testing-output.txt: Add legacy digest helper plus pytest/make harness asserting exit codes and digests on python/ with python/.pylintrc; wire into CI or make py-test
  - From dyn-symilar-parity-output.txt: Add a shared legacy digest helper (reuse the new runner’s normalization over pylint’s own ingestion/`_compute_sims` path), assert digest equality in parity tests on fixtures, and add an opt-in full-tree gate (pytest marker or CI step) that fails when exit codes or digests diverge.
  - From dyn-lint-surface-output.txt: Add a shared helper (e.g. `python/duplicate_code_parity.py`) that runs legacy pylint, derives the same normalized digest shape as `--emit-cluster-digest`, and exposes `assert_parity(root, rcfile)`; wire it into `test_duplicate_code_parity.py` (fixture + optional full `python/` tree), and add a `make` or CI step that fails when legacy/new exit codes or digests diverge.


### FINDING_4: `_legacy_exit` collapses pylint exit codes, masking parity failures
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-symilar-parity-output.txt, dyn-lint-surface-output.txt
- **Severity**: important
- **Concern**: `_legacy_exit` maps every non-zero pylint return to `1`. Pylint 4.0.5 reports R0801 under the refactor bit (exit `8`, not `1`). Config/import/internal failures (exit `2+`) can be misclassified as duplicate-found exit `1`, hiding real parity failures and masking raw legacy/new exit-code mismatch even when digests agree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Propagate legacy exit codes verbatim or fail gate when legacy exit not in {0,1}
  - From dyn-symilar-parity-output.txt: Either document and test that parity is digest-primary when duplicates exist (normalize legacy rc the same way in the gate script), or align the new runner’s failure rc with pylint’s bitmask for R0801-only invocations if exact rc parity is required.
  - From dyn-lint-surface-output.txt: Preserve the raw pylint return code (or map only pylint’s duplicate-finding codes to `0`/`1` and pass through `2+` unchanged), and assert exact equality with the new runner’s exit code in parity tests.


### FINDING_5: ThreadPoolExecutor fallback runs concurrent `_find_common` on shared `symilar`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-parallel-pairs-output.txt
- **Severity**: important
- **Concern**: On `PermissionError` from `ProcessPoolExecutor`, both fork and spawn paths silently fall back to `ThreadPoolExecutor` with concurrent `_find_common` calls against one shared `symilar`/`linesets`. Pylint’s `Symilar` is not documented as thread-safe; this can produce nondeterministic digests or pass/fail drift in restricted sandboxes. The plan requires fail-closed exit `2` on worker failures or deterministic serial degradation, not a thread pool on shared pylint state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fall back to serial comparison instead of threaded parallel.
  - From dyn-parallel-pairs-output.txt: Treat `PermissionError` like any other pool failure: exit `2` with a clear stderr message, or degrade deterministically to the existing serial path (`jobs == 1` / `_find_common_chunk_with` in the parent) and log that parallelism was disabled; do not use `ThreadPoolExecutor` on shared pylint state.


### FINDING_6: `_canonicalize_commonalities` silently keeps unpickled worker `LineSet` copies on lookup failure
- **Reviewer(s)**: dyn-parallel-pairs-output.txt
- **Severity**: important
- **Concern**: `_canonicalize_commonalities` rebinds worker `LineSet` references by `lineset.name` and silently keeps unpickled worker copies when lookup fails (`canonical.get(..., commonality.fst_lset)`). Because `Symilar._compute_sims` deduplicates couples by `LineSet` identity (`id`-based hashing), name mismatches across worker chunks can leave duplicate `LineSet` objects in play, inflating clusters and changing exit code and digest versus serial execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parallel-pairs-output.txt: Fail closed (exit `2`) when either side of a commonality cannot be rebound to a parent `linesets` entry; optionally assert name-to-index bijection during ingestion so canonicalization is keyed by stable pair indices instead of path strings alone.


### FINDING_7: Ingestion omits pylint `pure_python` guard
- **Reviewer(s)**: dyn-symilar-parity-output.txt
- **Severity**: important
- **Concern**: Ingestion omits pylint’s `node.pure_python` guard from `_check_astroid_module`. Legacy pylint skips `process_tokens` / `SimilaritiesChecker.process_module` for non-pure-python modules, while this runner always ingests discovered modules. A non-pure-python file in the discovery set would enter `linesets` here but not in legacy pylint, breaking file-set and cluster parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-symilar-parity-output.txt: Mirror pylint’s branch: when `not node.pure_python`, skip ingestion (and optionally record the skip) instead of calling `process_module`.


### FINDING_9: Parallel merge path untested for pylint-disable / close-equivalent fixtures
- **Reviewer(s)**: dyn-parallel-pairs-output.txt
- **Severity**: important
- **Concern**: Parallel correctness is only exercised on simple all-enabled duplicate fixtures at `jobs=2`. All pylint-disable / close-equivalent attribution cases run with default `jobs=1` only, leaving `_canonicalize_commonalities` + `_compute_sims` unvalidated for the attribution rules that most often diverge between raw `_find_common` yields and reportable R0801 clusters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parallel-pairs-output.txt: Add parametrized tests that rerun the disable/close-equivalent fixtures at `jobs=2` (and ideally `jobs>2` with enough files to span multiple chunks), asserting exit code and digest equality with the serial baseline.


