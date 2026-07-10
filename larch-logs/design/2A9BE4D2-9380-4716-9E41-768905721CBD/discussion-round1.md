## Decision 1: Status value for "no CI workflow"
- **Question**: When a repo has no workflow named "CI", what should the main-health probe report instead of `error`?
- **Resolution**: Introduce a new `skip` status. The probe returns `MAIN_CI_STATUS=skip`; `/implement` continues past the main-health gate. Do NOT reuse `pass` (reusing `pass` would conflate "verified green" with "no gate").
- **Source**: user

## Decision 2: Scope of the skip condition
- **Question**: Which cases count as "no CI gate to check"?
- **Resolution**: Only when the "CI" workflow does not exist in the repo (gh returns rc=1 with stderr "could not find any workflows named CI"). A "CI" workflow that exists but has zero push->main runs stays `error` (unchanged). Do not broaden to the empty-result case.
- **Source**: user

## Decision 3: /design scope (codebase finding, not asked)
- **Question**: Does /design also need this fix (issue title says "and likely /design")?
- **Resolution**: No. /design does not probe main-health. No `MAIN_CI_STATUS` consumer exists under `skills/design/` or `python/larch/design/`. The fix is `/implement`-scoped only (preflight probe + SKILL.md consumer).
- **Source**: codebase

## Hard constraints (must not break)
- The main-health status contract is validated in two code sites (`python/larch/implement/main_health.py` MAIN_HEALTH_STATUSES, `python/larch/implement/preflight.py` envelope validation) and consumed as prose in `skills/implement/SKILL.md` and `skills/implement/references/step2-main-health-fix.md`. Adding `skip` must update all of them coherently or preflight will reject the row.
- Do NOT touch the PR-CI `decide` path (`_VALID_CI_STATUS` in `python/larch/implement/ci.py`); it is unrelated (PR checks, includes `merged`).
- `wait_main_health` must treat `skip` as terminal (return immediately, like pass/fail), or a skip row would loop until timeout.
