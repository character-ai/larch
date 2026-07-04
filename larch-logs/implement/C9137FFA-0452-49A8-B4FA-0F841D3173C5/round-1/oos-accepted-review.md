### OOS_1: risk-integration: Makefile:37 / .pre-commit-config.yaml:667-672
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Writer-parity lint is not in pre-commit while sibling bg-wait-coverage is CI lint-local runs make lint-only only; future CLONE_PATH omission in a writer file passes PR checks Add lint-bg-wait-writer-parity pre-commit hook mirroring lint-bg-wait-coverage
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: .pre-commit-config.yaml:667-673
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] The new bg-wait writer parity lint is not registered as a pre-commit hook, so CI's make lint-only path will not execute it. Future writer drift or a missing CLONE_PATH stamp can still pass CI because the new check never runs there. Add the hook beside lint-bg-wait-coverage in .pre-commit-config.yaml, and if needed add it to the CI lint job's SKIP list so the external-tools split stays intact.
- **Suggested revision**: Address the concern above.


### OOS_3: **correctness** `Makefile:37-37` — The new `lint-bg-wait-writer-parity` target is wired only into the convenience `lint:` aggregate, but CI and `make lint-only` run pre-commit hooks only (`.github/workflows/ci.yaml:127`, `Makefile:150-151`). Sibling `lint-bg-wait-coverage` is enforced via `.pre-commit-config.yaml:667-669`; writer-parity is not. The branch’s pytest suite exercises synthetic fixtures only (`python/tests/lint/test_lint_bg_wait_writer_parity.py:289-306`), so a merged PR can remove `CLONE_PATH=` from a real inventoried writer and still pass CI. **Suggested fix:** Register `python3 python/cli.py lint bg-wait-writer-parity` in `.pre-commit-config.yaml` beside `lint-bg-wait-coverage` (with `pass_filenames: false` and an inventory-path `files` glob), or add a repo-root acceptance test that runs the lint against the real tree.
- **Reviewer**: dyn-dyn-bgwait-marker-output.txt
- **Concern**: - **correctness** `Makefile:37-37` — The new `lint-bg-wait-writer-parity` target is wired only into the convenience `lint:` aggregate, but CI and `make lint-only` run pre-commit hooks only (`.github/workflows/ci.yaml:127`, `Makefile:150-151`). Sibling `lint-bg-wait-coverage` is enforced via `.pre-commit-config.yaml:667-669`; writer-parity is not. The branch’s pytest suite exercises synthetic fixtures only (`python/tests/lint/test_lint_bg_wait_writer_parity.py:289-306`), so a merged PR can remove `CLONE_PATH=` from a real inventoried writer and still pass CI. **Suggested fix:** Register `python3 python/cli.py lint bg-wait-writer-parity` in `.pre-commit-config.yaml` beside `lint-bg-wait-coverage` (with `pass_filenames: false` and an inventory-path `files` glob), or add a repo-root acceptance test that runs the lint against the real tree.
- **Suggested revision**: Address the concern above.


