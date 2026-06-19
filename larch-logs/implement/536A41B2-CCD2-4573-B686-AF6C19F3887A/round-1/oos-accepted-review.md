### OOS_1: correctness: python/test_duplicate_code_parity.py:69-91
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Mandatory legacy-vs-new cluster-digest parity gate is not implemented; only exit codes are compared and digest-mismatch test is vacuous. Both runners can exit 1 while reporting different reportable clusters; Makefile cutover would not catch R0801 semantic drift. Add legacy close-equivalent digest helper and assert exit code plus digest equality on fixtures and the full python/ tree.
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/test_duplicate_code.py:1-265
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-required edge-case tests are missing (close-equivalent gating, disable=all, enabled-peer-vs-disabled, cross-shard guard, _iter_sims non-use, namespace binding). Regressions in parallel binding or close-equivalent suppression could ship untested. Add the missing fixtures from the implementation plan.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/test_duplicate_code_parity.py:43-91
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [blocking] Parity helper does not compute or compare a legacy cluster digest and maps all nonzero Pylint statuses to 1. A runner that changes reportable cluster membership but still exits 1 passes the parity tests. Add a pinned legacy digest extractor, compare legacy and new digests, and preserve fatal/config statuses.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/duplicate_code.py:184-201,485-501
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Pylint bootstrap SystemExit paths escape the runner's promised exit-2 fail-closed contract. A bad rcfile option can make _config_initialization call sys.exit(32), bypassing DuplicateCodeError handling. Catch Pylint SystemExit/bootstrap/API failures and convert them to DuplicateCodeError so the CLI returns 2.
- **Suggested revision**: Address the concern above.


### OOS_5: correctness: python/test_duplicate_code_parity.py:81-91
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Parity tests do not run legacy pylint or compare legacy vs new cluster digests. Mandatory merge-blocker parity is unenforced; digest drift vs legacy pylint could ship undetected. Add full-tree (or opt-in) test running both runners and asserting equal exit codes and digests via shared helper.
- **Suggested revision**: Address the concern above.


### OOS_6: risk-integration: python/test_duplicate_code_parity.py:69-91
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] The parity tests never compare a legacy Pylint reportable-cluster digest against the new runner’s digest. A runner that misses or adds clusters while still exiting 1 can pass the pre-cutover test coverage that is supposed to guard the Makefile swap. Add a real legacy digest extractor that uses Pylint 4.0.5 close-equivalent cluster normalization, then assert legacy and new digests match on fixtures and the mandatory full-tree gate.
- **Suggested revision**: Address the concern above.


### OOS_7: risk-integration: python/test_duplicate_code_parity.py:69-91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Parity tests never compare legacy pylint cluster digests to the new runner; digest-mismatch test uses a hardcoded dummy digest. A regression that preserves exit code 1 but changes reportable cluster membership ships undetected because CI never asserts legacy_digest == new_digest. Add a legacy digest helper, assert digest equality on fixture trees, and test that intentional digest mismatch fails the gate when exit codes match.
- **Suggested revision**: Address the concern above.


### OOS_8: risk-integration: python/test_duplicate_code_parity.py:43-91
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] The required parity gate does not compare a legacy reportable-cluster digest to the new runner digest, and _legacy_exit collapses every non-zero Pylint exit into 1. A legacy fatal/config failure or a cluster-membership mismatch can pass these tests once Makefile:45-56 has already cut CI over to the new runner. Add a real legacy close-equivalent digest extractor, preserve fatal legacy exits as gate failures, and assert both exit-code equality and legacy/new digest equality in the parity tests.
- **Suggested revision**: Address the concern above.


### OOS_9: correctness: python/duplicate_code.py:189-194
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Pylint _config_initialization can raise SystemExit(32), but duplicate_code_main only maps DuplicateCodeError to the required exit 2 at python/duplicate_code.py:499-501. A bad .pylintrc option can make the new CI target exit with Pylint’s private code instead of the runner’s documented config-error contract. Wrap Pylint bootstrap/config initialization SystemExit and convert non-zero exits into DuplicateCodeError, then add a focused test for an rcfile/config failure.
- **Suggested revision**: Address the concern above.


### OOS_10: **correctness** `python/test_duplicate_code_parity.py:69-91` — The plan’s merge-blocking parity gate requires **both** exit-code equality and **reportable-cluster digest equality** between legacy `pylint -j 1` and the new runner on the real `python/` tree (and on fixtures). The parity module never computes a legacy digest: `test_legacy_pylint_and_new_runner_agree_on_exit_code_for_fixture` only compares exit codes, and `test_digest_mismatch_blocks_even_when_exit_codes_match` hardcodes `legacy_rc = 1` and only checks `digest != "[]"`. There is no `python/duplicate_code_parity.py` helper. Cluster membership drift (both exit `1`, different reportable clusters) would not be caught before Makefile cutover. **Suggested fix:** Add a shared close-equivalent digest helper (ideally driven off pylint’s own `SimilaritiesChecker.close()` / `_compute_sims` path), assert `legacy_digest == new_digest` in fixture tests, and add an opt-in full-tree gate test for `python/` that fails on any digest mismatch.
- **Reviewer**: dyn-symilar-parity-output.txt
- **Concern**: - **correctness** `python/test_duplicate_code_parity.py:69-91` — The plan’s merge-blocking parity gate requires **both** exit-code equality and **reportable-cluster digest equality** between legacy `pylint -j 1` and the new runner on the real `python/` tree (and on fixtures). The parity module never computes a legacy digest: `test_legacy_pylint_and_new_runner_agree_on_exit_code_for_fixture` only compares exit codes, and `test_digest_mismatch_blocks_even_when_exit_codes_match` hardcodes `legacy_rc = 1` and only checks `digest != "[]"`. There is no `python/duplicate_code_parity.py` helper. Cluster membership drift (both exit `1`, different reportable clusters) would not be caught before Makefile cutover. **Suggested fix:** Add a shared close-equivalent digest helper (ideally driven off pylint’s own `SimilaritiesChecker.close()` / `_compute_sims` path), assert `legacy_digest == new_digest` in fixture tests, and add an opt-in full-tree gate test for `python/` that fails on any digest mismatch.
- **Suggested revision**: Address the concern above.


### OOS_11: **risk-integration** `python/test_duplicate_code.py:226-235` — Parallel-path regression coverage is thin relative to the plan and the new concurrency surface. Only one serial-vs-parallel digest test exists (`jobs=2`, three files). Missing guards include: cross-file shard detection (duplicate spanning files a naive file-slice shard would split), spy/assertion that `_iter_sims` is not used for partitioning, worker-exception → exit `2`, and instance-bound `_find_common` calls. A future refactor could reintroduce file sharding or `_iter_sims` pre-scan without CI catching it. **Suggested fix:** Add the plan’s focused tests: monkeypatch/spy on pair enumeration and `_find_common` binding, a three-plus-file cross-shard fixture, and a worker-failure test asserting exit `2` plus stderr.
- **Reviewer**: dyn-parallel-pairs-output.txt
- **Concern**: - **risk-integration** `python/test_duplicate_code.py:226-235` — Parallel-path regression coverage is thin relative to the plan and the new concurrency surface. Only one serial-vs-parallel digest test exists (`jobs=2`, three files). Missing guards include: cross-file shard detection (duplicate spanning files a naive file-slice shard would split), spy/assertion that `_iter_sims` is not used for partitioning, worker-exception → exit `2`, and instance-bound `_find_common` calls. A future refactor could reintroduce file sharding or `_iter_sims` pre-scan without CI catching it. **Suggested fix:** Add the plan’s focused tests: monkeypatch/spy on pair enumeration and `_find_common` binding, a three-plus-file cross-shard fixture, and a worker-failure test asserting exit `2` plus stderr.
- **Suggested revision**: Address the concern above.


### OOS_12: **risk-integration** `python/test_duplicate_code_parity.py:69-91` — The parity module does not enforce legacy-vs-new cluster-digest equality. `test_legacy_pylint_and_new_runner_agree_on_exit_code_for_fixture` checks exit codes only; `test_digest_mismatch_blocks_even_when_exit_codes_match` compares against hardcoded `"[]"` instead of a legacy digest extractor. The plan’s merge-blocker gate (exit code **and** digest match) is therefore not automated. **Suggested fix:** Implement a shared legacy close-equivalent digest helper (as planned) and assert `legacy_digest == new_digest` on fixture trees, including a case where both exit `1` but digests must still match.
- **Reviewer**: dyn-parallel-pairs-output.txt
- **Concern**: - **risk-integration** `python/test_duplicate_code_parity.py:69-91` — The parity module does not enforce legacy-vs-new cluster-digest equality. `test_legacy_pylint_and_new_runner_agree_on_exit_code_for_fixture` checks exit codes only; `test_digest_mismatch_blocks_even_when_exit_codes_match` compares against hardcoded `"[]"` instead of a legacy digest extractor. The plan’s merge-blocker gate (exit code **and** digest match) is therefore not automated. **Suggested fix:** Implement a shared legacy close-equivalent digest helper (as planned) and assert `legacy_digest == new_digest` on fixture trees, including a case where both exit `1` but digests must still match.
- **Suggested revision**: Address the concern above.


### OOS_13: **architecture** `python/test_duplicate_code_parity.py:64-91` — The parity-gate architecture described in the plan is not wired: there is no legacy close-equivalent digest extractor, no full-tree legacy-vs-new comparison, and `test_digest_mismatch_blocks_even_when_exit_codes_match` only asserts the new digest is not `"[]"` rather than comparing legacy and new signatures. The branch already cut over `Makefile` `py-lint-duplicate-code` to the new CLI, so the merge-blocker validation layer is missing from the lint surface. **Suggested fix:** Add a shared parity helper (for example `python/duplicate_code_parity.py`) that computes legacy and new cluster digests with the same normalization, add a real-tree gate test/command, and make digest equality a hard blocker before/alongside the Makefile swap.
- **Reviewer**: dyn-lint-surface-output.txt
- **Concern**: - **architecture** `python/test_duplicate_code_parity.py:64-91` — The parity-gate architecture described in the plan is not wired: there is no legacy close-equivalent digest extractor, no full-tree legacy-vs-new comparison, and `test_digest_mismatch_blocks_even_when_exit_codes_match` only asserts the new digest is not `"[]"` rather than comparing legacy and new signatures. The branch already cut over `Makefile` `py-lint-duplicate-code` to the new CLI, so the merge-blocker validation layer is missing from the lint surface. **Suggested fix:** Add a shared parity helper (for example `python/duplicate_code_parity.py`) that computes legacy and new cluster digests with the same normalization, add a real-tree gate test/command, and make digest equality a hard blocker before/alongside the Makefile swap.
- **Suggested revision**: Address the concern above.


### OOS_14: **architecture** `python/test_duplicate_code.py:1-265` — The parallel pair-comparison architecture lacks several plan-mandated contract tests (`_iter_sims` not used for partitioning, instance-bound `_find_common`, cross-file shard guard, close-equivalent false-positive/negative cases, enabled-vs-disabled peer behavior). The Makefile and comments claim pair-index parallelism on a configured checker-owned Symilar instance, but the test suite does not validate those structural invariants. **Suggested fix:** Add the missing spy/monkeypatch tests from the plan so serial vs parallel paths, pair enumeration, and close-equivalent gating are enforced in CI via `python-tests`.
- **Reviewer**: dyn-lint-surface-output.txt
- **Concern**: - **architecture** `python/test_duplicate_code.py:1-265` — The parallel pair-comparison architecture lacks several plan-mandated contract tests (`_iter_sims` not used for partitioning, instance-bound `_find_common`, cross-file shard guard, close-equivalent false-positive/negative cases, enabled-vs-disabled peer behavior). The Makefile and comments claim pair-index parallelism on a configured checker-owned Symilar instance, but the test suite does not validate those structural invariants. **Suggested fix:** Add the missing spy/monkeypatch tests from the plan so serial vs parallel paths, pair enumeration, and close-equivalent gating are enforced in CI via `python-tests`.
- **Suggested revision**: Address the concern above.


