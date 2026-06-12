## Goal
Implement issue #4059: [IMPLEMENTING] [OOS] Admission gate fails open on all blocker subprocess failures\n\n## Out-of-Scope Observation.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Code review panel (rounds 1-5) — cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, cursor-specialist-testing
**Phase**: review
**Vote tally**: N/A — combined OOS per Rule A (same logical concern: admission blocker fail-open)

## Description

`python/admission.py` `gate_main` (and its helper functions) treats any non-zero exit from the blocker helper subprocess — including import errors, source failures, and dispatcher errors — as an empty blocker list, allowing `ADMISSION_RESULT=pass` even when the blocker checker could not run at all. The plan preserves the D3 fail-open posture for degraded *GitHub API reads inside a successful blocker invocation*, but subprocess-level failures (non-zero exit from `bash -euo pipefail -c 'source "$1"; all_open_blockers "$2"' bash ...`) should return `ADMISSION_ERROR=blocker all-open failed` and exit 2 so a broken tool cannot silently unblock a DESIGNED issue. Suggested fix: distinguish subprocess non-zero from GitHub-API degradation inside the subprocess; fail-close on the former, preserve fail-open only for the latter (matching the plan's D3 note that "True source/win failures still exit 2").

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
