# Review Round 3

- Mode: `diff`
- 6 accepted, 7 rejected (2 neutral)

## Accepted Findings

### FINDING_2: Plan-required edge-case tests missing in test_duplicate_code.py
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed edge cases lack pytest coverage: astroid parse failure, empty tree, single file, `--jobs 0`, and worker-error paths. Regressions in parse-fail or `jobs=0` handling can ship without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the four tmp_path tests specified in the plan
  - From cursor-specialist-testing-output.txt: Add focused tmp_path tests for each missing edge case from the plan.


### FINDING_3: ≤90s GHA wall-time acceptance and conditional sharding not evidenced
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Post-cutover ≤90s GHA timing and conditional `ci.yaml` sharding are plan acceptance criteria but absent from the diff. The dedicated duplicate-code job may remain a multi-minute bottleneck, so the issue can close without meeting the stated speed goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Measure GHA wall time; add matrix sharding if >90s
  - From cursor-specialist-testing-output.txt: Measure GHA wall time after cutover; add matrix sharding in ci.yaml in the same PR if >90s.


### FINDING_4: test_digest_mismatch does not assert parity failure on digest mismatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_digest_mismatch_blocks_even_when_exit_codes_match` never asserts that `assert_parity` fails on digest mismatch. A future regression that changes cluster normalization but preserves exit code 1 would not be caught despite the plan’s merge-blocker requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add fixture/monkeypatch that forces digest mismatch and expects AssertionError
  - From cursor-specialist-testing-output.txt: Add a test that forces digest mismatch with matching exit codes and asserts assert_parity raises.


### FINDING_6: py-lint-duplicate-code chains assert_parity, defeating CI speed goal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-lint-surface-output.txt
- **Severity**: important
- **Concern**: `py-lint-duplicate-code` runs `assert_parity` after every CLI run, which subprocess-invokes legacy `pylint -j 1` plus additional full ingest/compare passes. GHA `python-lint-duplicate-code` still pays the legacy serial pylint bottleneck on every CI invocation, so the ≤90s speed acceptance criterion cannot be met. On success this is roughly three full-tree passes (parallel CLI, legacy pylint subprocess, serial `run_duplicate_code`), beyond the plan’s pre-cutover merge gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Remove assert_parity from the production Makefile target; keep parity in pytest/offline gates only. Run python/cli.py lint duplicate-code in CI. Add matrix sharding only if wall time remains >90s after dropping legacy pylint.
  - From cursor-specialist-testing-output.txt: Remove assert_parity from the default Makefile target; keep parity as a separate gate or rely on test_full_python_tree_legacy_new_parity.
  - From codex-generic-output.txt: Remove line 57 from the target. Keep parity as a pre-cutover or opt-in validation command, not in the shipped CI target.
  - From dyn-lint-surface-output.txt: Keep `py-lint-duplicate-code` as a single `python/cli.py lint duplicate-code` line for CI. Move full-tree parity to pytest (`test_full_python_tree_legacy_new_parity`) or a separate opt-in make target such as `py-lint-duplicate-code-parity`.


### FINDING_10: Legacy parity digest does not independently validate legacy behavior
- **Reviewer(s)**: codex-generic-output.txt, dyn-lint-surface-output.txt
- **Severity**: important
- **Concern**: The “legacy” digest is built through shared new-runner discovery/ingestion helpers and/or a different enumeration strategy (`checker._iter_sims()` vs production `itertools.combinations` plus `_find_common`). If the new runner skips or misprocesses a file, or if the two enumeration paths diverge, `assert_parity()` can pass even though real pylint would report different clusters. Parity therefore may not check “legacy CLI vs new CLI under one normalization contract.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Build the legacy digest from Pylint’s native run/checker close path, or otherwise use an independent legacy extractor that does not reuse the new runner’s ingestion and clustering helpers.
  - From dyn-lint-surface-output.txt: Drive the legacy digest through the same combinations + `_find_common` + `_clusters_from_commonalities` path (or a shared helper), and keep the subprocess `pylint` call for exit-code comparison only.


### FINDING_11: Default pytest runs full-tree legacy/new parity
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Default `pytest` now runs full-tree legacy/new parity, which invokes the old single-process duplicate-code scan during `make py-test`. That moves the same multi-minute work into the python test job and contradicts the intended focused `tmp_path` default coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Gate the full-tree parity test behind an explicit env var or marker, and keep default collection limited to small fixture tests.


