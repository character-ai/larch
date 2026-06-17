### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-code-voters.sh:144-148,606-633
- **Concern**: Stub PLUGIN_ROOT voter1/wait-barrier cases shell `scripts/dispatch-code-voters.sh` directly; plan does not require pytest to replace those entrypoints with `python/cli.py agent dispatch-voters`. Scenario: After the script is deleted, late-sentinel, missing-sentinel, and wait-timeout cases that build `make_voter1_delayed_done_plugin_root` / invoke `"$voter1_plugin/scripts/dispatch-code-voters.sh"` cannot run; parity for voter-1 `.done` arbitration regresses while simpler happy-path CLI tests still pass
- **Proposed resolution**: In `### NEW: python/test_agent_voters.py`, add an explicit port note: fake `CLAUDE_PLUGIN_ROOT` trees must stop symlinking `scripts/dispatch-code-voters.sh`; invoke `python3 <repo>/python/cli.py agent dispatch-voters` (or a cli.py stub that delegates to the real verb) for voter1-delayed-done, voter1-missing-done, and wait-barrier scenarios

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:1-130
- **Concern**: Child CLI subprocesses must resolve python/cli.py from CLAUDE_PLUGIN_ROOT not from Path(__file__) alone. Scenario: The bash script uses PLUGIN_ROOT/CLI for render voter launch-claude-review dispatch-waterfall wait-reviewers and parse-rate-retry. Harness fixtures such as make_voter1_delayed_done_plugin_root stub only voter1_plugin/python/cli.py. If agent_voters hardcodes the real repo cli.py path stub interception breaks and late-sentinel plus parallel-dispatch regressions fail or test the wrong code
- **Proposed resolution**: Resolve plugin_root via os.environ.get("CLAUDE_PLUGIN_ROOT") with the same repo-root fallback as agents._plugin_root and build every child argv from plugin_root / "python" / "cli.py"

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:51-66
- **Concern**: Plan does not require rendering and validating all three voter prompts before any subprocess launch. Scenario: Retired bash builds claude, codex, and cursor prompts at scripts/dispatch-code-voters.sh:107-109 before backgrounding Claude at :115-123. A Python port that renders only the Claude prompt then Popen's can leave a running Claude voter if a later codex/cursor render or ballot-pointer check fails
- **Proposed resolution**: Add an explicit prelaunch step: render voter plus ballot-pointer validation for claude, codex, and cursor; exit 2 on any failure; only then start Claude Popen and dispatch-waterfall

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: docs/review-agents.md
- **Concern**: [SCOPE-REDUCTION] Plan lists docs/review-agents.md but the tracked file has no dispatch-code-voters.sh or code-review voter-dispatch surface to retarget. Scenario: Implementer may make unrelated doc edits during closeout
- **Proposed resolution**: Drop docs/review-agents.md from Files to modify/create unless the final stale-reference sweep finds a concrete voter-dispatch literal there

