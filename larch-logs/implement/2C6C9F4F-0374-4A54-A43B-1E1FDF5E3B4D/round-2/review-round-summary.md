# Review Round 2

- Mode: `diff`
- 1 accepted, 10 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Stop hook missing static block JSON fallback when jq and python3 fail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-hook-streams-output.txt, dyn-retirement-cleanup-output.txt
- **Severity**: important
- **Concern**: After removing the static emit fallback, `skills/implement/scripts/hook-stop-fail-close.sh` only calls `hook_emit` when `HOOK_OUT` is non-empty after `jq -cn` and an optional `python3` retry. When both `jq` and `python3` are missing or fail on an active post-`/review` boundary (`review-round-summary.md` present, `.review-boundary-passed` absent), the hook exits 0 with no `decision:block` JSON on stdout, allowing session stop past the guard. `scripts/deny-edit-write.sh` still uses a fixed-literal fallback for the same failure class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Restore fixed-literal fallback after python3 attempt (mirror deny-edit-write.sh) and cover jq-failure and jq-absent paths in a dedicated harness.
  - From dyn-hook-streams-output.txt: Restore a final fixed-literal `hook_emit` fallback (matching the prior static envelope shape) whenever `HOOK_OUT` is still empty after the `python3 -c` attempt, and add a harness case that stubs `jq`/`python3` to force that path.
  - From dyn-retirement-cleanup-output.txt: Add a fail-closed static `decision:block` fallback (fixed reason or templated with safe escaping) routed through `hook_emit`, mirroring the deny-hook pattern, and cover it in the Stop-hook harness.


