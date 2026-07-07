## Decision 1: Waiter-subagent wait mode
- **Question**: Include the optional waiter-subagent mode (orchestrator delegates the `bgjob wait` chunk loop to a minimal foreground agent), defer it to a follow-up, or drop it?
- **Resolution**: Drop it entirely. Do not build it and do not file a follow-up issue. Direct-loop chunked `bgjob wait` calls from the orchestrator are the only wait topology.
- **Source**: user

## Decision 2: Acceptance criterion 1 vs retained legacy bg-wait docs
- **Question**: AC 1 requires `git grep -l "run_in_background" skills/` to return only the allowlist doc, but the non-goals keep `skills/shared/design-background-wait.md`, `skills/shared/orchestrator-never.md` items 3-5, and other legacy docs functional until issue 2. How do both hold?
- **Resolution**: The repurposed inverse lint (`lint bg-wait-coverage`) reads an explicit allowlist file; that allowlist enumerates the retained legacy docs until issue 2 deletes them. AC 1 means: no `run_in_background` in `skills/` outside the lint allowlist and historical run logs.
- **Source**: codebase
