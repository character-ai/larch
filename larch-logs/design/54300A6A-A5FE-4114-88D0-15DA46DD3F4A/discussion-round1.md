## Decision 1: Arg threading for the composite fence
- **Question**: Should step-6-entry.sh accept --forked-target only, or also --rebase-checkpoint-7r and other checks-commit-route args?
- **Resolution**: --forked-target is the only variable arg. Everything else (--checks-site step6, --commit-site step7, --emit-step7-breadcrumb, --rebase-checkpoint-7r) is fixed for Step 6 and should be hardcoded in step_6_entry_main. This keeps the SKILL.md fence minimal.
- **Source**: codebase (SKILL.md line 609)

## Decision 2: Degradation KV warning handling
- **Question**: Should UNTRACKED_BASELINE=missing / GIT_PROBE_FAILED=true warnings be logged internally by the composite, or remain in SKILL.md orchestrator?
- **Resolution**: Relay as KVs; SKILL.md orchestrator continues to log the warnings. No change to existing warning handling.
- **Source**: codebase (issue text says "relay the KVs")

## Decision 3: test-implement-rebase-macro.sh update
- **Question**: Does test-implement-rebase-macro.sh line 44 need updating since the exact checks-commit-route text for Step 6 is removed from SKILL.md?
- **Resolution**: Yes. Line 44 checks for the literal SKILL.md text and will fail after the fold. Must be updated to check the new step-6-entry.sh composite invocation with --forked-target.
- **Source**: codebase (scripts/test-implement-rebase-macro.sh:44)
