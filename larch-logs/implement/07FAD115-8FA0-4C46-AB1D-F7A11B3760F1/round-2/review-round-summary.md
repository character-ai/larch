# Review Round 2

- Mode: `diff`
- 6 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Duplicate `/bug` entries in public skills catalog (`README.md`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `/bug` appears twice in the public skills catalog table (`README.md` ~67–95) with slightly different descriptions. Item 9 intended a single entry near `/issue`. Duplicate rows confuse consumers and drift from the plan/`docs/skills.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove one /bug block and keep a single row next to /issue.
  - From cursor-specialist-edge-cases-output.txt: Remove the duplicate /bug block after /implement (lines 91-95) and keep a single row near /issue peers
  - From cursor-specialist-testing-output.txt: Remove the duplicate row; keep one entry near /issue per plan
  - From codex-generic-output.txt: Remove the duplicate block after `/implement` and keep the single entry in ASCII order near `/block-issue` (matching `docs/skills.md`).


### FINDING_13: Stale `steps_ran.step9a1=true` without `run-statistics.md` passes audit/verify (`python/audit_runs.py`, `python/run_logs.py`)
- **Reviewer(s)**: dyn-runlog-step9a1-output.txt
- **Severity**: important
- **Concern**: When manifest has `steps_ran.step9a1=true` but `run-statistics.md` is absent, the Step 9a.1 reachability predicate returns `False`, so required-file scans treat the step as “not reached” and skip the `run-statistics.md` requirement. A committed run with provisional `oos-issues.ndjson`, stale `step9a1=true`, and no stats can pass `audit-runs scan-run` and `run-log verify-completeness`, even though `_step9a1_heuristic()` correctly marks it incomplete. This regresses versus the pre-branch ndjson-only failure path; existing tests cover empty `steps_ran` + ndjson but not stale `step9a1=true` + ndjson.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-step9a1-output.txt: Treat explicit `step9a1=true` without `run-statistics.md` as in-scope for the requirement (return `True` from the reachability predicate, or add a dedicated corrupt-state branch that fails when manifest claims true but stats are missing), mirror the same logic in `_verify_condition_reached()` and `audit_runs._scan_required()`, and add paired audit/verify-completeness regression tests for `{"steps_ran":{"step9a1":true}}` + provisional ndjson.


### FINDING_14: Step 9a.1 completion contract disagrees across docs and consumers (`docs/run-logs.md`, `skills/implement/SKILL.md`, `python/run_logs.py`, `python/audit_runs.py`)
- **Reviewer(s)**: dyn-runlog-step9a1-output.txt
- **Severity**: important
- **Concern**: Docs and orchestrator prose say Step 9a.1 completion is signaled by `run-statistics.md` **or** explicit `steps_ran.step9a1=true`, but shipped consumers do not honor “explicit true alone.” `_step9a1_heuristic()` returns `False` when manifest has `step9a1=true` but stats are absent, and audit/verify treat that state as step-not-reached. Operators may believe Step 9a.1 completed on manifest true alone while audit tooling and refresh heuristics disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-step9a1-output.txt: Pick one contract and align all five surfaces (`run_logs.py`, `audit_runs.py`, `pr_body.py`, `docs/run-logs.md`, `skills/implement/SKILL.md`). The safer choice for checkpoint-failed retries is: completion requires post-checkpoint `run-statistics.md`; explicit `step9a1=true` is valid only together with that file (or document that explicit true without stats is a corrupt/stale marker that must fail audits).


### FINDING_16: Ok-path append failure leaves attempted sentinel and blocks retry (`design-step-validator-autofix.sh`)
- **Reviewer(s)**: dyn-design-wrapper-output.txt
- **Severity**: important
- **Concern**: On the ok path, when `run-log append-failure` fails, the wrapper sets `_autofix_status=failed` but still exits 0 and leaves the `.plan-command-autofix-*.attempted` sentinel in place. A retry in the same site/target/evidence cycle surfaces `AUTOFIX_STATUS=skipped-cycle-cap` instead of another repair attempt, even though autofix never succeeded and no ok-path Warnings row was written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-wrapper-output.txt: Remove or clear the attempted sentinel when ok-path append fails (or when nonzero helper rc forces `failed`), so a real retry can run; keep skipped-cycle-cap only for genuine one-attempt-per-cycle success or exhaustion.


### FINDING_3: Title-only OOS block matching can collapse distinct blocks (`python/oos_filer.py`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Title-only fallback in `_issue_matches_block` can match two different blocks to one persisted issue. After checkpoint failure, a second distinct OOS block with the same normalized title may be skipped and never filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require stable-id or filed-URL match when multiple blocks share a normalized title, or disable title-only fallback in that case.


### FINDING_8: Non-filing OOS terminal paths lack disposition-checkpoint test assertions (`python/test_oos_filer.py`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-filing OOS terminal paths lack assertions that `disposition-checkpoint` runs. A refactor could write `run-statistics` and stamp `step9a1=true` on skipped/empty/already-filed paths without invoking the checkpoint; existing tests would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parametrized fake.calls assertions for disposition-checkpoint on empty already_filed skipped/forked and sentinel-recovery paths


