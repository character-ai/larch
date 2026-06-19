# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_22: **correctness** `python/test_duplicate_code.py` — Several plan-required correctness cases are untested, so regressions in R0801 semantics can ship despite a green suite: `# pylint: disable=all`, block-level disable via `file_state`, “enabled peer still fails when legacy pylint would”, close-equivalent cases where raw `_find_common` output should not fail, cross-file shard guard (`--jobs 2` vs naive file sharding), and spies asserting instance-bound `symilar._find_common` / no `_iter_sims` pre-scan. Only `# pylint: disable=duplicate-code` and basic threshold cases are covered. **Suggested fix:** Add the missing fixtures from the plan, especially the enabled-peer + disabled-file case and close-equivalent pass/fail cases, plus monkeypatch spies on `_iter_sims` and `_find_common` to lock the intended enumeration and binding contract.
- **Reviewer**: dyn-symilar-parity-output.txt
- **Concern**: - **correctness** `python/test_duplicate_code.py` — Several plan-required correctness cases are untested, so regressions in R0801 semantics can ship despite a green suite: `# pylint: disable=all`, block-level disable via `file_state`, “enabled peer still fails when legacy pylint would”, close-equivalent cases where raw `_find_common` output should not fail, cross-file shard guard (`--jobs 2` vs naive file sharding), and spies asserting instance-bound `symilar._find_common` / no `_iter_sims` pre-scan. Only `# pylint: disable=duplicate-code` and basic threshold cases are covered. **Suggested fix:** Add the missing fixtures from the plan, especially the enabled-peer + disabled-file case and close-equivalent pass/fail cases, plus monkeypatch spies on `_iter_sims` and `_find_common` to lock the intended enumeration and binding contract.
- **Suggested revision**: Address the concern above.


