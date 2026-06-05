### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-90,121-122
- **Concern**: Post-table grep -Fxc expects exactly one exact model_provider selector on login-home/config.toml after login-path external_prepare_codex_auth. Scenario: copied-config.toml supplies two exact-match strip targets (top-level line 77 and nested [model_providers.other] line 83); login-path strip removes both, and assert_top_level_not_line already requires zero top-level matches. Only example model_provider = "openai-larch-env" survives inside multiline text, which grep -Fxc does not count. A count==1 assertion false-fails on correct strip behavior or pressures the implementer to retain a selector the plan also says must be absent
- **Proposed resolution**: Require grep -Fxc == 0 for exact model_provider = "openai-larch-env" and env_key = "OPENAI_API_KEY" on login-home/config.toml, or add a separate fixture with one deliberate non-stripped exact selector before expecting count 1

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-90
- **Concern**: Plan asks for exactly one retained exact model_provider selector while also requiring the nested selector to be absent. Scenario: The copied fixture only has strip-target selectors outside multiline text; after external_prepare_codex_auth the exact grep count should be 0, so the planned assertion either fails or pushes the test toward retaining a selector the plan says to remove
- **Proposed resolution**: Resolve the fixture/assertion contract: assert 0 retained exact selector for this fixture, or add a separate clearly non-stripped retained line before expecting count 1

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-codex-implementer.sh:349-353
- **Concern**: Plan adds a global /tmp larch-codex-home-* snapshot helper for both happy-path and 4h auth-prep-failure cleanup. Scenario: Happy path already records the temp home via STUB_CODEX_HOME_FILE; a global /tmp diff adds concurrency noise tolerance you only need when the stub never runs (4h)
- **Proposed resolution**: For happy-path only assert [[ ! -d "$(cat "$CODEX_HOME_FILE")" ]] after launch; keep the /tmp before/after snapshot solely for the 4h case

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-128
- **Concern**: Planned exact-count assertion expects one retained exact model_provider line, but the copied login fixture has no safe exact line left after stripping. Scenario: Line 83 is the nested selector the plan also says must be absent, and line 87 is prefixed with example so grep -Fxc 'model_provider = "openai-larch-env"' will count zero and fail the proposed tests
- **Proposed resolution**: Change the post-table count to expect zero exact selector lines, or add a deliberate separate multiline fixture with an exact retained selector and count that fixture instead

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-90
- **Concern**: The plan moves the exact retained model_provider count to login-home/config.toml, but the copied-config fixture has no exact retained model_provider line after stripping; the exact line at line 83 is the nested selector the plan also says must be absent, and the multiline line at line 87 has an example prefix.. Scenario: Implementing the plan as written makes grep -Fxc 'model_provider = "openai-larch-env"' return 0 instead of 1, so test-lib-external-launcher-common fails despite production behavior being unchanged.
- **Proposed resolution**: Either add one exact model_provider = "openai-larch-env" line inside the copied fixture's multiline body before the assertion, or change the expected count for login-home/config.toml to 0.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-bash-harness-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-89; plan.txt:11-16
- **Concern**: Planned grep -Fxc count of 1 for exact line model_provider = "openai-larch-env" on login-home/config.toml does not match the copied-config fixture. Scenario: After external_prepare_codex_auth on the login fixture, the stripper removes every exact selector line (top-level and nested under [model_providers.other]); the only surviving text is example model_provider = "openai-larch-env" inside the multiline block, so grep -Fxc returns 0 and the new assertion false-fails on correct behavior
- **Proposed resolution**: Change the planned count to 0 and keep assert_file_contains for the multiline survivor, or add an explicit fixture line that must retain exactly one exact selector (e.g. inside a multiline body) before asserting count 1

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-89; scripts/lib-external-launcher-common.sh:603-604
- **Concern**: Planned exact-count assertion for one retained model_provider on login-home has no retained exact line in the fixture. Scenario: The strip helper removes the top-level and nested exact selector lines, while the only multiline survivor is prefixed with example, so grep -Fxc 'model_provider = "openai-larch-env"' returns 0 unless the implementer invents an unstated fixture change
- **Proposed resolution**: Either change the planned login-home exact count to 0 and keep the targeted multiline preservation assertion, or explicitly modify the fixture to include one exact selector inside a multiline body before asserting count 1

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-fixture-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-90
- **Concern**: Post-table grep -Fxc expects exactly one retained model_provider = "openai-larch-env" on login-home/config.toml. Scenario: The copied-config fixture keeps a multiline body line example model_provider = "openai-larch-env" (lines 85-88); after external_prepare_codex_auth the exact line model_provider = "openai-larch-env" should appear zero times, so an == 1 assertion fails on the intended fixture or passes only if multiline preservation is accidentally broken
- **Proposed resolution**: Change the login-home post-table check to expect grep -Fxc 'model_provider = "openai-larch-env"' == 0 (with || true), or use a separate post-table fixture without multiline selector text if a positive retention count is required

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-argv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14-16
- **Concern**: Login-home post-table count expects exactly one retained model_provider line. Scenario: external_prepare_codex_auth on the copied login fixture (OPENAI_API_KEY unset) strips every top-level model_provider = "openai-larch-env" line; existing harness already asserts removal via assert_top_level_not_line at scripts/test-lib-external-launcher-common.sh:121-122, and grep -Fxc on the stripped file yields 0 whole-line matches (multiline body keeps only example model_provider = "openai-larch-env")
- **Proposed resolution**: Change the login-home post-table assertion to expect zero grep -Fxc matches for model_provider = "openai-larch-env" (and keep zero env_key), or relocate count assertions to a fixture where one retained selector is the intended post-strip contract

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-argv-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:92-105; scripts/lib-external-launcher-common.sh:710-723; scripts/test-check-reviewers.sh:394-400
- **Concern**: Plan adds trusted-project adjacency but still leaves env-key auth overrides covered only by string-presence greps. Scenario: The helper contract emits alternating -c/config argv pairs; if a regression drops -c before model_provider or env_key, current/proposed greps still pass while real Codex ignores the auth override and falls back or fails auth
- **Proposed resolution**: Add one minimal argv-pair assertion for external_codex_auth_config_args output, or in the live env-key probe capture, proving model_provider="openai-larch-env" and model_providers.openai-larch-env.env_key="OPENAI_API_KEY" each immediately follow -c

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-bash-harness-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-90,121-128
- **Concern**: Plan expects exactly one retained exact model_provider line after login auth prep, but the fixture has no exact retained line once top-level and nested selectors are stripped. Scenario: The new grep -Fxc assertion will fail, or the implementer may mix multiline-retention content into the post-table fixture despite the plan saying to keep those fixtures separate
- **Proposed resolution**: Change the post-table count to assert zero exact model_provider = "openai-larch-env" lines, and keep multiline retained-line checks in the separate multiline fixtures described later
