# Discussion Round 1 — scope & hard constraints

## Decision 1: Handling of remote-failed jobs with no clean local equivalent
- **Question**: When a remote-failed CI job has no clean local equivalent (gitleaks history scan, trufflehog, agent-sync needing upstream remote, env-specific failures), how should the iterative local fix-loop handle it?
- **Resolution**: Best-effort local fix-loop: attempt local re-run + fix iteration for every failed job that *does* have a local equivalent; for jobs that cannot be locally fixed (no local equivalent, or per-step cap exhausted without success), bail to the main agent via `exit 3` with an appropriate `BAIL_REASON` so the main orchestrator can attempt resolution outside ship-pr.
- **Source**: user
- **Implication for sketches**: The per-step inner loop must distinguish two terminal states — `LOCALLY_FIXED` (push proceeds for that step) and `UNFIXABLE` (collected into a bail aggregate). After processing every locally-fixable job, if the unfixable set is non-empty, ship-pr exits 3 with `BAIL_REASON` enumerating the unfixable job names.

## Decision 2: Push gate — what must be true locally before re-push
- **Question**: Before re-pushing after a CI-fix iteration, what must be true locally?
- **Resolution**: Every formerly-failed remote job *with a local equivalent* must pass locally. Jobs without a local equivalent are not re-verified locally and follow Decision 1's bail path.
- **Source**: user
- **Implication for sketches**: After the per-step inner loops complete, the push gate is `forall failed_job in remote_failed_jobs: has_local_equiv(failed_job) ⇒ local_run(failed_job) == 0`. If the predicate holds AND the unfixable set is empty, push. Otherwise per Decision 1.

## Decision 3: Granularity of "a failed CI step"
- **Question**: What is the unit we identify and re-run locally — a whole CI job, or a specific step within a job?
- **Resolution**: Job-level. Map `<job-name>` (e.g., `test-harnesses`, `shellcheck`, `agnix`, `lint-mermaid`) to one local command and run that. Mapping table is small and robust to step renames inside a job.
- **Source**: user
- **Implication for sketches**: The mapping table lives in one place (probably a TSV or shell case statement) and keys on the GitHub Actions job name. `gh run view --json jobs` yields the failed job names; `gh run view --log-failed` remains the source of context for the LLM fix prompt.

## Cross-cutting non-goals (derived from Q1c answers, recorded here for traceability)
- Out of scope: pre-flight local-CI mirroring before the first push (Q1c-3 = "Only on CI failure").
- Out of scope: a new top-level orchestration script or new sub-skill (Q1c-4 = "Extend existing scripts").
- Out of scope: a single fix attempt then push (Q1c-2 = per-step iterate-until-pass-or-cap).
- In scope: only the `run_evaluate_failure` recovery path in `scripts/ship-pr.sh`, plus a small new helper script.

## Cross-cutting hard constraints (derived)
- `relevant-checks.sh` and `lint-fix-loop.sh` semantics must remain intact for `step3`/`step5`/`step6` and the non-CI-fail paths; only the `ship-pr-ci-initial` / `ship-pr-ci-merge` sites change.
- The existing fix-vendor 3-tier waterfall (Cursor → Codex → Claude) must remain the LLM dispatch primitive; per-step inner loop reuses `lint-fix-loop.sh` and/or the existing CI launchers rather than introducing a new fixer abstraction.
- `_max_fix=3` outer cap in `run_evaluate_failure` must continue to bound the total invocations regardless of how many jobs failed.
- All new behavior must respect `lib-quiet.sh` FD-3 contract, `lib-net.sh` transient retry classification, and existing `record_failure` / `exit_stall` / `record_ci_counters` envelope conventions.

