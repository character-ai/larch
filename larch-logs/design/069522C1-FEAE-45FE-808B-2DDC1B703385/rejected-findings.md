### [Plan Review] FINDING_1

### FINDING_1: Pytest must preserve voter1 sentinel harness scenarios
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The bash harness (`scripts/test-dispatch-code-voters.sh`) exercises late-sentinel, missing-sentinel, and wait-timeout behavior through fake `CLAUDE_PLUGIN_ROOT` trees that symlink `scripts/dispatch-code-voters.sh` and invoke it directly (e.g. `make_voter1_delayed_done_plugin_root` at lines 144–148; voter1 cases at 606–633). The plan ports coverage to pytest but does not require those entrypoints to call `python/cli.py agent dispatch-voters`. After the bash script is deleted, those scenarios cannot run; voter-1 `.done` arbitration parity regresses while simpler happy-path CLI tests may still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `### NEW: python/test_agent_voters.py`, add an explicit port note: fake `CLAUDE_PLUGIN_ROOT` trees must stop symlinking `scripts/dispatch-code-voters.sh`; invoke `python3 <repo>/python/cli.py agent dispatch-voters` (or a cli.py stub that delegates to the real verb) for voter1-delayed-done, voter1-missing-done, and wait-barrier scenarios


### [Plan Review] FINDING_3

### FINDING_3: Render and validate all voter prompts before any subprocess launch
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Retired bash builds and validates Claude, Codex, and Cursor prompts before backgrounding Claude (`scripts/dispatch-code-voters.sh:107–123`: three `make_voter_prompt_file` calls, then `launch-claude-review` in background). A Python port that renders only the Claude prompt, then `Popen`s, can leave a running Claude voter if a later Codex/Cursor render or ballot-pointer check fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit prelaunch step: render voter plus ballot-pointer validation for claude, codex, and cursor; exit 2 on any failure; only then start Claude Popen and dispatch-waterfall


