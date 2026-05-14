## Goal
Script-enforce plan-review voter dispatch via dispatch-plan-voters.sh

## Implementation Plan
Goal: Script-enforce plan-review voter dispatch for Voter-2 (Codex) + Voter-3 (Cursor).

## Implementation Plan

1. Create scripts/dispatch-plan-voters.sh
   - Parse --ballot-file, --design-tmpdir, --codex-available, --cursor-available, --session-env-path
   - Fail-closed if run-external-agent.sh not present (never-bypasses-wrapper invariant)
   - If codex_available=true: launch via run-external-agent.sh --tool codex in background subshell; VOTER_2_STATUS=launched
   - If codex_available=false: VOTER_2_STATUS=fallback (orchestrator launches Claude subagent)
   - If cursor_available=true: launch via run-external-agent.sh --tool cursor in background subshell; VOTER_3_STATUS=launched
   - If cursor_available=false: VOTER_3_STATUS=fallback
   - Call wait-for-reviewers.sh for launched external voters
   - Call append-tool-failure.sh on launch/wait failures
   - Emit: VOTER_2_PATH, VOTER_3_PATH, VOTER_2_STATUS, VOTER_3_STATUS, DISPATCH_OK
   - EXIT trap to remove temp prompt files

2. Create scripts/dispatch-plan-voters.md — sibling contract doc

3. Create scripts/test-dispatch-plan-voters.sh
   - Stubs for run-external-agent.sh, wait-for-reviewers.sh, agent-model-args.sh, cursor-auth-flags.sh, cursor-wrap-prompt.sh, append-tool-failure.sh
   - Happy path: both available, envelope correct
   - Codex fallback: codex_available=false → VOTER_2_STATUS=fallback
   - Cursor fallback: cursor_available=false → VOTER_3_STATUS=fallback
   - Launch failure: stub run-external-agent.sh non-zero → append-tool-failure.sh called
   - Never-bypasses-wrapper: grep script for codex exec / cursor agent

4. Edit skills/design/references/plan-review.md lines 46-50
   - Replace Voter 2/3 prose launch instructions with dispatch-plan-voters.sh invocation

5. Edit skills/design/SKILL.md line 685
   - Update "Voting Panel launch-order" reference to note dispatch-plan-voters.sh is used

diff_lines: 230

## Test plan
(no test plan section in plan-file)
