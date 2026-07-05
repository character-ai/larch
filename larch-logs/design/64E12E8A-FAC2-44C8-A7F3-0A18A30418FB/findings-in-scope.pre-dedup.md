### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py
- **Concern**: Planned checks_commit_route step3 test omits required --commit-site argv. Scenario: checks_commit_route_main requires both --checks-site and --commit-site; a test described with only --checks-site step3 fails argparse before pre-arm cleanup or marker arming run, so the new regression never executes
- **Proposed resolution**: Specify argv including --commit-site step4 (and _session/IMPLEMENT_TMPDIR setup like existing composite tests); keep monkeypatch on _checks_commit_route_main_impl



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py
- **Concern**: Step3 composite test must assert cleanup before marker write not only before impl entry. Scenario: Item 1 requires clearing stale sidecars before arming; assertions only inside _checks_commit_route_main_impl run after _write_bg_wait_marker, so cleanup placed after marker write but before impl would still pass while hook denial stays off during marker creation
- **Proposed resolution**: Also spy/wrap _write_bg_wait_marker (or _bg_wait_marker) to assert both sidecars are absent at marker-write time; keep the post-exit terminal-sentinel assertion



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:65-72
- **Concern**: [SCOPE-REDUCTION] Inline step3 cleanup in checks_commit_route_main duplicates run_step_checks_main. Scenario: Plan adds a third copy at composite entry while run_step_checks_main already unlinks the same two paths; two call sites can drift again (prior OOS_4/OOS_6)
- **Proposed resolution**: Clear stale .completed/step-3-terminal and bg-poll-guard-probe-denials.step-3-terminal.count inside _bg_wait_marker when terminal_sentinel is .completed/step-3-terminal, then delete the duplicate block in run_step_checks_main; adjust the new test accordingly



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py
- **Concern**: Planned Step 3 composite test omits required --commit-site argv. Scenario: checks_commit_route_main requires both --checks-site and --commit-site (dispatch_commit_route.py:849-851). A test invoked with only --checks-site step3 fails at argparse before pre-arm cleanup or marker arming run, so the planned assertions never execute.
- **Proposed resolution**: Specify the new test calls checks_commit_route_main with --checks-site step3 --commit-site step4 (matching skills/implement/SKILL.md Step 3), plus IMPLEMENT_TMPDIR/_session setup and monkeypatch of _checks_commit_route_main_impl. ### 1. correctness — `python/tests/implement/test_implement_dispatch.py` The planned Step 3 composite test only names `--checks-site step3`, but `checks_commit_route_main` requires `--commit-site` as well: parser.add_argument("--checks-site", required=True) commit_site_choices = sorted([*_COMMIT_ROUTE_SITES, "step4"]) parser.add_argument("--commit-site", choices=commit_site_choices, required=True) A test written to the plan as stated will fail at argument parsing before cleanup or marker arming run. Specify `--commit-site step4` in the test plan so it matches the live Step 3 fence in `skills/implement/SKILL.md`. --- **Coverage note (no finding):** Items 1, 2, 4, 5, 6, and 7 from the issue scope are addressed in the plan. Round 1 accepted items (isolated FAIL counters, temp-file brace fixture, 15600 timeout, deep monkeypatch) are incorporated. Item 3 is intentionally reduced to keepalive deduplication only, which fits the minimum-change constraint. Item 4 exclusion text is largely present already in `scripts/test-hook-clone-ownership-parity.md`.



