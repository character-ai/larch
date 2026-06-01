## Decision 1: Helper exit-code contract
- **Question**: Should `oos-disposition-checkpoint.sh` propagate the gate's exit 2 as helper exit 2, or preserve today's Bash-block collapse (gate exit 2 → block exit 1)?
- **Resolution**: Mirror the gate's 0/1/2. Helper exits 0=proceed, 1=disposition gap (gate exit 1), 2=validation/setup error (gate exit 2 AND the pre-gate input-resolution failures that already exit 2 today: ambiguous/undiscoverable oos-issues.ndjson without session-id; non-security accepted OOS with no resolved ndjson). Refinement over the current Bash-block collapse; matches the existing prose's distinct exit-1 vs exit-2 remediation so the orchestrator branches on rc.
- **Source**: user

## Decision 2: Failure logging scope
- **Question**: Should the helper call `append-tool-failure.sh` for all non-zero exits, or only gate failures (today's behavior)?
- **Resolution**: Log all non-zero exits. Helper calls `append-tool-failure.sh` for both gate failures and pre-gate setup/validation failures, with distinct `--site` tokens, so every checkpoint failure lands in `execution-issues.md`. Today only gate failures are logged; pre-gate validation exits are stderr-only.
- **Source**: user

## Decision 3: Extraction boundary (in-scope vs out-of-scope)
- **Question**: What moves into the helper vs. stays in the orchestrator?
- **Resolution**: Helper owns ALL input computation (FORKED_TARGET / REPO_UNAVAILABLE read from ship-pr-state.sh; commit range via merge-base origin/main..HEAD with origin/main..HEAD fallback; RUN_ID + oos-issues.ndjson discovery with find/sort/ambiguity; design-OOS path DESIGN_TMPDIR vs design-export/; non-security accepted-OOS block count via oos-non-security-block-count.awk over the accepted-OOS CSV; the "non-security OOS requires resolved ndjson" precondition), gate invocation, and failure logging. The orchestrator RETAINS: clearing OOS_PENDING, the unconditional run-statistics write on pass, and the `--resume-phase pr-create` re-entry. Helper "computes-and-gates"; it does NOT clear OOS_PENDING. No `ship-pr.sh` edits in this issue (different block).
- **Source**: issue + codebase (skills/implement/SKILL.md Step 8+ inline block lines 1193-1283)

## Decision 4: Carve-outs preserved
- **Question**: Are the fork-mode / repo_unavailable gate-skip carve-outs preserved?
- **Resolution**: Yes. When FORKED_TARGET=true or REPO_UNAVAILABLE=true (from ship-pr-state.sh), the gate is skipped (gate receives --fork-mode / --repo-unavailable). Preserve NEVER #17 / #18. Keep the gate's existing exit-code semantics and --oos-issues-ndjson / --filed-urls-file / --filed-urls-strict-file / --commit-range wiring intact.
- **Source**: issue + codebase

## Decision 5: Helper interface
- **Question**: What is the helper's CLI surface?
- **Resolution**: `oos-disposition-checkpoint.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" [--design-tmpdir ...]`. ISSUE_NUMBER not required (gate inputs derive from tmpdirs + git). Lives at skills/implement/scripts/oos-disposition-checkpoint.sh.
- **Source**: issue

## Decision 6: Test + contract-sibling scope
- **Question**: Where does test coverage live; does the new script need an .md sibling?
- **Resolution**: Extend skills/implement/scripts/test-oos-disposition-gate.sh with checkpoint-level coverage (ndjson discovery, ambiguity, fork / repo-unavailable skips) per the issue. New oos-disposition-checkpoint.sh REQUIRES an oos-disposition-checkpoint.md contract sibling per .claude/rules/script-md-siblings.md. test-implement-structure.sh may pin the old inline block and need updating when the inline bash is replaced by the helper call.
- **Source**: issue + codebase convention
