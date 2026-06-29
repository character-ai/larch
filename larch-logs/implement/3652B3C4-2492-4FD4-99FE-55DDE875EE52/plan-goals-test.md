## Goal
Implement issue #5779: [IMPLEMENTING] [py-code-quality] [pkg-payoff] 14/14: Mirror flat test_*.py into the larch package tree (low priority).

## Implementation Plan
**Improvement #4 (test-tree symmetry).** Part of the post-#4982 packaging-payoff umbrella.

#### Problem
148 flat `test_*.py` modules sit in `python/`; **zero** live inside the `larch/` package. Runtime moved into packages; tests did not follow, so the test layout no longer mirrors the runtime tree.

#### Scope
- Relocate flat `python/test_*.py` to mirror the `larch/` package tree, or a parallel `python/tests/` tree that mirrors it.
- Update pytest config (`pythonpath`, discovery) and the flat-test harness assumptions.
- Decide consistently on the 7 intentional-residual test/CI-harness modules (`ci_timing_fetch`, `pytest_ci_timing`, `pytest_sharding`, `review_test_support`, `harness_ci_timing`, `harness_makefile`, `harness_shard_packer`).

#### Acceptance
- Tests pass from their new locations; `make py-test` green; CI sharding and timing harness still work.

#### Honest caveat (LOW value)
Low value in an LLM-only repo: agents locate `test_agents.py` by grep whether it is flat or nested, so there is no token, error, or concurrency payoff. This also **reverses the #4982 intentional-residual decision** to keep tests flat. Included for completeness per the explicit "do all" scope; deprioritize relative to 1/14 through 13/14.

#### Dependencies
Independent. Blocks the umbrella only.

## Test plan
(no test plan section in plan-file)
