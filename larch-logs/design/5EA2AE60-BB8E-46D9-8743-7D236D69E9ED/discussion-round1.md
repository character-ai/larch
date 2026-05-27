# Discussion — Round 1

## Decision 1: Evidence basis
- **Question**: Did you observe this in a specific recent /implement run, or is this a general design request?
- **Resolution**: Both — specific observation + general hardening request.
- **Source**: user

## Decision 2: Coverage scope of local fix/test loop
- **Question**: Which CI failures should the local fix/test loop cover?
- **Resolution**: Only locally-reproducible jobs (status quo). The existing `fixable` vs `no-local-equivalent` classification in `scripts/ci-failed-jobs.sh` stays. Non-fixable failed jobs still escalate to main-agent bail.
- **Source**: user

## Decision 3: Surface scope
- **Question**: Is this strictly the CI-fix loop in ship-pr.sh, or also broader /implement behavior?
- **Resolution**: ship-pr.sh CI-fix loop only. In-scope code: `run_evaluate_failure`, `run_per_job_local_fix_loop`, `run_ci_fix_vendor`, `_stage_and_push_ci_fixes`, supporting helpers in `scripts/ship-pr.sh`, `scripts/ci-failed-jobs.sh`, `scripts/lint-fix-loop.sh`. Out of scope: /implement Step 0–7 pre-push checks, postmerge, rebase paths.
- **Source**: user

## Decision 4: Symptom shape
- **Question**: Which symptom most closely matches what you observed?
- **Resolution**: Multiple consecutive CI failures (user "Other" answer). Pattern: /implement applies a fix, pushes, CI fails on the same or adjacent surface, applies another fix, pushes, CI fails again — i.e. CI itself is functioning as the test ground for fix validation. The design must address this broad pattern rather than a single specific gap (per-job classification miss, fallback bypass to `run_ci_fix_vendor`, or verification-sweep scope gap may all contribute).
- **Source**: user

## Decision 5: Local fix-loop budget
- **Question**: How aggressive should the local fix/test loop be before giving up?
- **Resolution**: Bigger local budget. Allow more inner iterations than the current `_max_fix=3` outer × `_RCC_MAX_ITER=3` inner because local iterations are cheap relative to CI round-trips. Must still cap so the loop cannot run unbounded (sketches/plan should propose specific caps such as wall-clock or attempt ceilings).
- **Source**: user

## Hard constraints (derived)
- Preserve the existing `run_per_job_local_fix_loop` machinery (designed via #2757, hardened by #2909/PR #2941). Do not regress those fixes.
- Preserve the `ci-local-unfixable` bail behavior for jobs classified `no-local-equivalent` (Decision 2). Escalation to main-agent on unfixable jobs stays.
- Preserve the existing `relevant-checks.sh` pre-push gate as a baseline; the design adds local validation BEYOND it (per-job re-run), not in place of it.

## Non-goals
- Do NOT redesign `relevant-checks.sh` or the pre-commit hook list.
- Do NOT touch /implement Steps 0–7 (initial pre-push checks before ci-initial phase).
- Do NOT add new "fixable" classifications for jobs that genuinely have no local equivalent (e.g., gitleaks scanning history, trufflehog).
