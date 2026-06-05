### FINDING_1: Login-home exact model_provider count contradicts stripped fixture
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-bash-harness-portability, Codex-Requirements, Cursor-dyn-fixture-isolation, Cursor-dyn-argv-contract, Codex-dyn-bash-harness-portability
- **Severity**: important
- **Concern**: Multiple reviewers report that the planned `grep -Fxc` assertion expecting exactly one whole-line `model_provider = "openai-larch-env"` match in `login-home/config.toml` conflicts with the copied login fixture and stripping contract. After `external_prepare_codex_auth`, the top-level and nested exact selector lines are stripped; the surviving multiline text is prefixed with `example`, so an exact whole-line count should be zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge: Require grep -Fxc == 0 for exact model_provider = "openai-larch-env" and env_key = "OPENAI_API_KEY" on login-home/config.toml, or add a separate fixture with one deliberate non-stripped exact selector before expecting count 1
  - From Codex-Arch: Resolve the fixture/assertion contract: assert 0 retained exact selector for this fixture, or add a separate clearly non-stripped retained line before expecting count 1
  - From Codex-Innovation: Change the post-table count to expect zero exact selector lines, or add a deliberate separate multiline fixture with an exact retained selector and count that fixture instead
  - From Codex-Pragmatic: Either add one exact model_provider = "openai-larch-env" line inside the copied fixture's multiline body before the assertion, or change the expected count for login-home/config.toml to 0.
  - From Cursor-Requirements, Cursor-dyn-bash-harness-portability: Change the planned count to 0 and keep assert_file_contains for the multiline survivor, or add an explicit fixture line that must retain exactly one exact selector (e.g. inside a multiline body) before asserting count 1
  - From Codex-Requirements: Either change the planned login-home exact count to 0 and keep the targeted multiline preservation assertion, or explicitly modify the fixture to include one exact selector inside a multiline body before asserting count 1
  - From Cursor-dyn-fixture-isolation: Change the login-home post-table check to expect grep -Fxc 'model_provider = "openai-larch-env"' == 0 (with || true), or use a separate post-table fixture without multiline selector text if a positive retention count is required
  - From Cursor-dyn-argv-contract: Change the login-home post-table assertion to expect zero grep -Fxc matches for model_provider = "openai-larch-env" (and keep zero env_key), or relocate count assertions to a fixture where one retained selector is the intended post-strip contract
  - From Codex-dyn-bash-harness-portability: Change the post-table count to assert zero exact model_provider = "openai-larch-env" lines, and keep multiline retained-line checks in the separate multiline fixtures described later


### FINDING_3: Auth override tests should verify -c/config argv adjacency
- **Reviewer(s)**: Codex-dyn-argv-contract
- **Severity**: latent
- **Concern**: The plan adds trusted-project adjacency coverage but still covers env-key auth overrides only with string-presence greps. If a regression drops the required `-c` immediately before `model_provider` or `env_key`, greps may still pass while Codex ignores the auth override.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-argv-contract: Add one minimal argv-pair assertion for external_codex_auth_config_args output, or in the live env-key probe capture, proving model_provider="openai-larch-env" and model_providers.openai-larch-env.env_key="OPENAI_API_KEY" each immediately follow -c

