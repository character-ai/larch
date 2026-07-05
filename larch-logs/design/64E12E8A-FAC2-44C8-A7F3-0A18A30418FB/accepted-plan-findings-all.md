### FINDING_1: Negative drift fixtures must not contaminate global FAIL
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Bg Wait Invariants
- **Severity**: blocking
- **Concern**: The planned deliberate-drift / expected-failure coverage in `scripts/test-hook-clone-ownership-parity.sh` needs an isolated assertion path; otherwise intentional negative cases will increment the shared `FAIL` tally and make the harness exit 1 even when the real hook copies are healthy. Some of the temp-hook cases also need a helper that can compare arbitrary hook files so they can be exercised at all.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify negative checks as isolated functions with local pass/fail (or subshells) that assert expected failure without touching global PASS/FAIL before the production compare_* loop; document the pattern in the .md sibling
  - From Cursor-Arch: Require negative checks as isolated helpers with local pass/fail (or subshells) that verify expected failure without mutating global PASS/FAIL before the production compare_* loop; document the pattern in test-hook-clone-ownership.md
  - From Codex-Arch: Run each expected-failure fixture in a subshell or separate helper that snapshots and restores PASS/FAIL, or add a dedicated assertion helper that treats the failure as a pass without mutating the parent counters.
  - From Cursor-Innovation: Add self-test helpers that pass when extract_function includes post-nested drift or compare_renamed_pair rejects fixture drift (subshell or separate pass counter). Never increment the global FAIL tally for expected negative outcomes
  - From Codex-Innovation: Add a helper that compares arbitrary hook files and returns a status, then wrap expected-failure fixtures so they assert non-zero without mutating the final PASS/FAIL tally
  - From Cursor-Pragmatic: In scripts/test-hook-clone-ownership-parity.sh specify each negative probe saves FAIL before the drifted comparison, requires FAIL to increase, then restores FAIL (or runs the drifted comparison in a subshell and asserts non-zero exit) before recording a PASS; document the pattern in scripts/test-hook-clone-ownership-parity.md
  - From Codex-Pragmatic: Run each negative fixture in a subshell or separate helper, assert the nonzero status as the expected outcome, and keep the main PASS/FAIL counters untouched
  - From Cursor-Requirements: In scripts/test-hook-clone-ownership-parity.sh pin a wrapper pattern: run extract+diff on temp hook files in a helper that passes when diff is non-zero (or uses local counters) and only call global fail() when detection regresses; document the pattern in scripts/test-hook-clone-ownership-parity.md
  - From Codex-Requirements: Run each negative fixture in a helper or subshell that asserts a non-zero exit and records that as a pass, while keeping the main PASS/FAIL tally for the real inventory only.
  - From Cursor-dyn-Bg Wait Invariants: Add an expect-drift helper (inline diff without fail()) or a subshell wrapper that records pass when drift is detected without touching global FAIL; document that pattern in the .md sibling


### FINDING_2: Brace-depth negative case needs temp-file extraction
- **Reviewer(s)**: Cursor-dyn-Bg Wait Invariants
- **Severity**: important
- **Concern**: The brace-depth negative fixture cannot reuse `compare_function` because it hardcodes the production hook paths; the nested-body drift case has to run against the temp file itself so a post-nested truncation bug is actually exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Bg Wait Invariants: Specify a temp-fixture block that calls extract_function "$tmp" "<fn>" and asserts the extracted body still contains the post-nested drift line; keep it outside the global FAIL path


### FINDING_3: Step 3 timeout assertion should not be 10800
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `checks_commit_route_main` Step 3 test would lock in `TIMEOUT_S=10800`, which would hide the composite-budget regression that is still present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Assert TIMEOUT_S=15600 (or the derived outer-budget seconds). Pair with stale-sentinel and probe-counter cleanup assertions only


### FINDING_4: Step 3 test patches too shallowly
- **Reviewer(s)**: Cursor-dyn-Bg Wait Invariants
- **Severity**: latent
- **Concern**: The composite Step 3 test needs to patch the inner implementation and seed the stale sentinel / probe counter before the body runs; if the monkeypatch is too shallow, assertions can execute at the wrong layer and miss the cleanup-order regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Bg Wait Invariants: Name the target explicitly: monkeypatch _checks_commit_route_main_impl, seed .completed/step-3-terminal and the probe counter, and assert both sidecars are absent plus TIMEOUT_S=10800 before the impl body runs


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:85-87; python/larch/implement/dispatch_leg.py:28-35; python/tests/implement/test_implement_dispatch.py (planned checks_commit_route step3 test)
- **Concern**: [SCOPE-REDUCTION] Do not drop composite Step 3 marker TIMEOUT_S from 15600 to 10800. Scenario: Live /implement Step 3 runs checks_commit_route_main for checks + step4 commit + folded 4.r under one bg-wait marker. CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS and SKILL/structure pins are 15_600_000 ms (15600 s). hook-bg-poll-guard.sh treats marker TIMEOUT_S (+60 s grace) as liveness; 10800 s would stop probe denial ~4740 s before the composite can finish, re-opening Monitor/TaskOutput polling during commit/rebase and diverging from the 15600000 orchestrator fence
- **Proposed resolution**: Keep _checks_commit_route_marker("step3") at 15600 (prefer CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS // 1000). Limit 10800 to checks-only run_step_checks_main. Drop the planned assert TIMEOUT_S=10800 for checks_commit_route_main; assert 15600 or the derived constant instead. Document that 10800 vs 15600 is intentional (checks-only vs composite), resolving Item 2 without shortening the production path


### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:85-87; python/larch/implement/dispatch_leg.py:28-35; skills/implement/SKILL.md:438-441; python/tests/implement/test_implement_dispatch.py (planned checks_commit_route step3 test)
- **Concern**: [SCOPE-REDUCTION] Do not drop composite Step 3 marker TIMEOUT_S from 15600 to 10800. Scenario: Live /implement Step 3 arms one bg-wait marker for checks_commit_route_main (checks + step4 commit + folded 4.r). CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS and SKILL/structure harness pins are 15_600_000 ms. hook-bg-poll-guard.sh uses marker TIMEOUT_S (+60 s grace) for liveness; 10800 s would end probe denial ~4740 s before the composite can finish, reopening polling during commit/rebase
- **Proposed resolution**: Keep _checks_commit_route_marker("step3") at 15600 (ideally CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS // 1000). Reserve 10800 for checks-only run_step_checks_main. Remove the planned assert TIMEOUT_S=10800 on the composite test; assert 15600 or the derived constant. Treat 10800 vs 15600 as intentional (checks-only vs composite), not a bug to flatten


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:87
- **Concern**: [SCOPE-REDUCTION] Do not change composite Step 3 marker TIMEOUT_S from 15600 to 10800. Scenario: CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS is 15_600_000 ms (checks 10_800_000 + commit 3_600_000 + 4.r 900_000 + slack 300_000). hook-bg-poll-guard.sh expires the marker at TIMEOUT_S+60s. At 10800 the guard can go dead during commit and 4.r while the composite fence still runs up to ~15600s, reopening Monitor/TaskOutput probes mid-wait
- **Proposed resolution**: Keep 15600 on checks_commit_route_main step3 (or derive CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS // 1000). Treat 10800 as checks-only for run_step_checks_main / legacy run-step-checks.sh. Satisfy issue Item 2 by documenting the split, not by aligning down


### FINDING_1: Step 3 composite test needs `--commit-site`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned Step 3 composite test is missing the required `--commit-site` argument, so `checks_commit_route_main` will fail argparse before the cleanup and marker-arming behavior under test can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify argv including --commit-site step4 (and _session/IMPLEMENT_TMPDIR setup like existing composite tests); keep monkeypatch on _checks_commit_route_main_impl
  - From Cursor-Requirements: Specify the new test calls checks_commit_route_main with --checks-site step3 --commit-site step4 (matching skills/implement/SKILL.md Step 3), plus IMPLEMENT_TMPDIR/_session setup and monkeypatch of _checks_commit_route_main_impl. ### 1. correctness — `python/tests/implement/test_implement_dispatch.py` The planned Step 3 composite test only names `--checks-site step3`, but `checks_commit_route_main` requires `--commit-site` as well: parser.add_argument("--checks-site", required=True) commit_site_choices = sorted([*_COMMIT_ROUTE_SITES, "step4"]) parser.add_argument("--commit-site", choices=commit_site_choices, required=True) A test written to the plan as stated will fail at argument parsing before cleanup or marker arming run. Specify `--commit-site step4` in the test plan so it matches the live Step 3 fence in `skills/implement/SKILL.md`. --- **Coverage note (no finding):** Items 1, 2, 4, 5, 6, and 7 from the issue scope are addressed in the plan. Round 1 accepted items (isolated FAIL counters, temp-file brace fixture, 15600 timeout, deep monkeypatch) are incorporated. Item 3 is intentionally reduced to keepalive deduplication only, which fits the minimum-change constraint. Item 4 exclusion text is largely present already in `scripts/test-hook-clone-ownership-parity.md`.


### FINDING_2: Step 3 composite test should assert cleanup before marker write
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned assertions only verify cleanup inside `_checks_commit_route_main_impl`, which runs after marker arming. That leaves a gap where stale sidecars could still exist when the bg-wait marker is written, allowing the regression to slip past the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Also spy/wrap _write_bg_wait_marker (or _bg_wait_marker) to assert both sidecars are absent at marker-write time; keep the post-exit terminal-sentinel assertion


