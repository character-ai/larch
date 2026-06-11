# Review Round 1

- Mode: `diff`
- 5 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 5 resume re-enters review loop without immediate background
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-background-migration-parity-output.txt, dyn-timeout-tier-calibration-output.txt, dyn-background-resume-state-output.txt
- **Severity**: important
- **Concern**: Step 5 backgrounds the initial review loop, but MAV and coder handoff resume paths invoke `step-5-resume.sh` in the foreground. That helper can synchronously re-enter `run-step5-review.sh`, so later review rounds can still block the orchestrator and bypass the intended timeout contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add run_in_background true and timeout 21600000 to step-5-resume fences, or re-invoke run-step5-review.sh directly with the same background contract instead of nesting it in step-5-resume.sh.
  - From codex-specialist-edge-cases-output.txt: Add immediate-background instructions and timeout to the ready-to-commit resume fence, or split the short commit path from the long review-loop re-entry and background the long call.
  - From codex-specialist-testing-output.txt: Background the ready-to-commit resume path or split the helper so the next run-step5-review.sh launch is its own immediate-background fence, then add a structural regression check.
  - From dyn-background-migration-parity-output.txt: Either route resume through the same background contract (annotate the `step-5-resume.sh` fence with Immediate-background + `21600000`, or split resume so the orchestrator re-invokes `run-step5-review.sh` in its own backgrounded Bash call), and add a harness assertion that MAV resume paths never nest a long loop inside a foreground-only wrapper.
  - From dyn-timeout-tier-calibration-output.txt: Either annotate the `step-5-resume.sh` fence with the same immediate-background + `21600000` contract, or stop nesting `run-step5-review.sh` inside `step-5-resume.sh` and have the orchestrator re-invoke `run-step5-review.sh` directly with the same parameters as the initial Step 5 fence.
  - From dyn-background-resume-state-output.txt: Route all Step 5 loop (re)entries through one wrapper (`step-5-resume.sh` or `run-step5-review.sh` directly) with the same Immediate-background + `timeout: 21600000` contract, or teach `step-5-resume.sh` to emit a “reinvoke loop in background” orchestrator instruction instead of nesting a blocking `run-step5-review.sh` call.


### FINDING_11: Design final-summary and publish timeouts may be too low
- **Reviewer(s)**: dyn-background-migration-parity-output.txt, dyn-timeout-tier-calibration-output.txt
- **Severity**: important
- **Concern**: Design final-summary and publish fences use a 10-minute timeout. As an explicit background timeout, that can kill slow publish or summary work after approval and leave partial external mutations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-background-migration-parity-output.txt: Align publish/final-summary timeouts with other long-running design fences (at least `1800000`, preferably `21600000` if publish is on the critical path), or split 5c into shorter foreground phases with explicit checkpoint/resume semantics.
  - From dyn-timeout-tier-calibration-output.txt: Bump the summary/publish tier above observed final-report durations (e.g. align with a dedicated publish tier ≥1800000 ms, or reuse the 21600000 multi-hour tier if publish+render can overlap with slow `gh` I/O).


### FINDING_12: Anti-halt prose does not define background wait semantics
- **Reviewer(s)**: dyn-background-migration-parity-output.txt
- **Severity**: important
- **Concern**: Implement and design anti-halt guidance can be read as “continue after Bash returns,” but `run_in_background: true` can return before the script finishes. That creates a race where orchestrators parse stdout or advance before `<task-notification>`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-background-migration-parity-output.txt: Add an explicit carve-out to both skills’ anti-halt sections: for Immediate-background fences, do not parse stdout or advance steps until `<task-notification>` fires; only then apply the existing “continue to Step N+1” banners.


### FINDING_14: Implement checks timeout can abort normal long check runs
- **Reviewer(s)**: dyn-timeout-tier-calibration-output.txt
- **Severity**: important
- **Concern**: `run-step-checks.sh` fences use a 30-minute timeout, but recorded check invocations can run for hours. With immediate background, the timeout becomes a hard kill rather than only a background trigger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timeout-tier-calibration-output.txt: Raise the checks tier to cover observed P99 (e.g. ≥10800000 ms / 3h, or derive from `scripts/relevant-checks.sh` / harness shard timings), and use that value consistently at Step 3, Step 5 (self-review + MAV), and Step 6.


### FINDING_2: Design Step 3 resumes bypass the backgrounded wrapper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-background-migration-parity-output.txt, dyn-background-resume-state-output.txt
- **Severity**: important
- **Concern**: Design Step 3 backgrounds the initial review wrapper, but mid-loop returns still call `run-step3-review.sh` directly. Those resume paths can run foreground and can bypass wrapper-owned status normalization and stdout handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Route all Step 3 resumes through design-step3-review.sh with the same immediate-background banner and timeout as the initial fence.
  - From cursor-specialist-edge-cases-output.txt: Add Immediate-background required banners before every run-step3-review.sh resume fence, or teach design-step3-review.sh --starting-round and use it for all invocations.
  - From codex-specialist-edge-cases-output.txt: Route resumes through a backgrounded wrapper or add starting-round support to design-step3-review.sh and require run_in_background: true for every resume.
  - From codex-specialist-testing-output.txt: Add a background-capable resume wrapper or explicit immediate-background resume fences, and add a structural test that forbids prompt-side foreground run-step3-review.sh loop resumes.
  - From dyn-background-migration-parity-output.txt: Add an explicit backgrounded resume fence (wrapper or repeated `design-step3-review.sh` call with the same `21600000` timeout) for every orchestrator-side resume after `STEP3_REVIEW_LOOP_STATUS` handoff, and document that mid-loop returns must not call `run-step3-review.sh` synchronously from the main agent.
  - From dyn-background-resume-state-output.txt: Extend `design-step3-review.sh` to forward `--starting-round` (and optional phase markers), use it for every loop (re)entry in `skills/design/SKILL.md`, and pin the same Immediate-background + `timeout: 21600000` requirement on those resume fences.


