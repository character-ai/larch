### Architectural guideline deviations (mild; non-blocking)

- **G-Md-2 (a contract change sweeps its prose consumers in the same change)**: the plan inverts the Step 2 coverage-KV contract — `skills/implement/SKILL.md` Step 2 now branches on `PLAN_COVERAGE_DISPOSITION_REQUIRED` — but the surface list omits `skills/implement/references/step2-dispatch.md`, which currently documents those coverage KVs as advisory / must-not-branch. The implementer must sweep `step2-dispatch.md` in the same change. Rationale for proceeding: minor and downstream-covered (mandatory G-Md-2 lint obligation + the newly-forced plan-fidelity finder + CI), and already surfaced in the published rejected-findings report as FINDING_9.

Notes (not deviations):
- `### UPDATED: python/tests/implement/test_implement_self_review.py` names a file that does not exist yet; the implementer should create it as `### NEW:` (harmless for coverage — a created file counts as touched).
- New `scope_disposition.py` dataclasses should be `frozen` per G-Py-1.
