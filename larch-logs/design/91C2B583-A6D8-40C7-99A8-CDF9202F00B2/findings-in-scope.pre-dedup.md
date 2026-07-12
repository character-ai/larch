### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py
- **Concern**: Cursor argv profile specs omit the required `agent` subcommand and `-p` flag. Scenario: Production launchers always build `cursor agent -p ...` (_review_launcher.py:1251-1264, _ci_launcher.py:384,993, _drafter.py:178-188). The Approach lists only `--trust`, `--mode ask`/`--force`, and `--output-format json`, and the test pinning list also omits both tokens, so builders or tests derived from the plan can ship argv that Cursor rejects or that later migration cannot swap in.
- **Proposed resolution**: Add `agent` and `-p` immediately after `cursor` in all four Cursor profile specs, and extend the Cursor full-list argv tests to assert both on every profile.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py
- **Concern**: Codex argv builder specs omit the required `exec` subcommand. Scenario: Every production Codex launch uses `codex exec` before sandbox flags (_review_launcher.py:888-905, _drafter.py:270-286, _ci_launcher.py:287+). The Approach names sandbox, `-C`, add-directories, and auth flags but not `exec`, and the Codex argv test list does not pin it either.
- **Proposed resolution**: A builder or test written only from the plan can emit `codex --sandbox ...`, which is not the production command shape later pieces must match. Prefix both Codex profiles with `codex exec` in the Approach and add `exec` to the Codex full-list argv assertions.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py: Claude profile definitions
- **Concern**: Claude profiles omit the valid review-subprocess shape without read tools. Scenario: launch_claude_review may omit --read-tools-add-dir, but the builder would have no exact profile for its base argv without --add-dir, --allowedTools, or --permission-mode
- **Proposed resolution**: Add a no-read-tools Claude review profile and test its exact argv and stdin behavior



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/agents/_vendor.py
- **Concern**: Fixed run_vendor_launch step order preflight before model resolution conflicts with Cursor review production. Scenario: _review_launcher.py resolves model args and writes model-args preflight artifacts before cursor_auth_preflight and cursor_preread_service_token; a single global cap then preflight then model resolution order changes which failure path runs and breaks the review-ask argv profile contract later pieces must preserve
- **Proposed resolution**: Add profile configurable phase ordering or split preflight into model-args and auth phases; register review-ask with model resolution before auth preflight while ci-write and implement-write keep auth before model args



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/agents/_vendor.py
- **Concern**: [SCOPE-REDUCTION] Parallel process-result and model types duplicate allowlisted _types.py helpers. Scenario: _types.py already defines RunExternalAgentResult LaunchResult and ModelArgResult on the import allowlist; redefining them in _vendor.py adds dead parallel types and drift risk without changing piece-1 behavior
- **Proposed resolution**: Reuse RunExternalAgentResult for injected executor results ModelArgResult for model resolution output and LaunchResult where a terminal launch envelope is needed; reserve new _vendor.py dataclasses for descriptor table hooks and Claude parsed-envelope outcomes only



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/agents/_vendor.py:descriptor declarations
- **Concern**: 1. The plan defines frozen vendor descriptors but never specifies one exported descriptor table or lookup contract.. Scenario: Only individual constants may ship, leaving later fixer lanes without the required shared selection surface and forcing another dispatch map.
- **Proposed resolution**: Add an immutable registry keyed by codex, cursor, and claude, then test registry uniqueness, lookup, and required capabilities.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py
- **Concern**: Cap budget check omits timing step in check-budget argv. Scenario: Review and implement launchers always invoke `python/cli.py token check-budget` with `--step <timing_task_kind>`; cap-hit sidecars embed the full stdout (`STATUS=... TOTAL=... CAP=... STEP=...`). The plan covers cap command construction and unchanged cap-hit payload but never requires a launch-request timing step or asserts `--step` in the argv. A foundation implementation can emit `STEP=unknown` sidecars and break the acceptance wire-compat goal when later pieces wire real timing kinds.
- **Proposed resolution**: Add a `timing_task_kind` (or equivalent) field on the frozen launch request, pass it as `--step` in the cap-check argv, and extend the cap-command tests to pin the full argv including `--step`.



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py:run_vendor_launch
- **Concern**: The accepted nonzero lifecycle fix remains incomplete: retry exhaustion still suppresses completion promotion. Scenario: Existing launchers promote the terminal `.inner.done` marker even when retries end with a nonzero result. The proposed lifecycle would leave waiters without the terminal marker despite successful postprocessing and accounting.
- **Proposed resolution**: Promote completion after a terminal nonzero result when all hooks succeed. Suppress promotion only when timing, postprocessing, or usage raises. Test promotion and hook-failure suppression for both zero and nonzero results.



