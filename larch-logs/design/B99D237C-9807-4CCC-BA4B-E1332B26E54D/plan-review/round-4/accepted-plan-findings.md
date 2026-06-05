### FINDING_1: Open-PR resume does not hydrate validated branch/state before writes and PR operations
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-dyn-state-contracts
- **Severity**: important
- **Concern**: Non-fresh open-pr resume can validate the current/state branch but continue using stale or empty `ctx.branch` / `ctx.branch_name` for `_write_ship_state` and `ensure_pr`, causing wrong `BRANCH_NAME` persistence, PR lookup/push/create against the wrong branch, or broken later resume/finalize guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After branch validation succeeds, hydrate working with the probed branch (or matched state BRANCH_NAME) before any open-pr/merged _write_ship_state; add a test that stubs git head feat with mismatched ctx.branch and asserts state writes feat
  - From Codex-Pragmatic: Hydrate working.branch and working.branch_name from the validated resume branch before OOS/ensure/CI, or require ctx.branch to equal the validated branch before classifying open-pr
  - From Cursor-dyn-state-contracts: On non-fresh paths, hydrate working from persisted state keys used in validation (at least BRANCH_NAME; REPO/RUN_ID/MANIFEST_PATH/MERGE/DRAFT/FORKED_TARGET/REPO_UNAVAILABLE when present) before any _write_ship_state, or teach _write_ship_state to preserve keys not supplied


### FINDING_2: Reachable GitHub PR state can be overridden by stale merged-looking local state
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Codex-dyn-resume-routing
- **Severity**: important
- **Concern**: `_resume_plan` can classify a run as merged/postmerge/done based on stale local state flags such as `PR_CLOSED=true`, `MERGE_RESULT=merged`, or `PHASE=postmerge` even when `gh.pr_view` is reachable and reports the PR as OPEN or CLOSED-not-merged, allowing postmerge/done handling before an actual merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: In _resume_plan, make successful gh.pr_view authoritative for normal repos: MERGED routes to merged, OPEN routes only to open-pr when the head matches, and CLOSED non-merged routes fresh; reserve state-only merged predicates for gh-skipped contexts.
  - From Codex-Edge: In _resume_plan, make reachable gh state authoritative: MERGED/merged_at may route to merged; OPEN may route only to open-pr; CLOSED without merged must route fresh regardless of state flags. Use state-only merged predicates only when gh is intentionally skipped, and add a focused closed-not-merged stale-state test.
  - From Codex-Pragmatic: Treat gh.pr_view as ground truth when it succeeds: MERGED may resume postmerge, OPEN may resume open-pr, CLOSED unmerged must fall back fresh; use PR_CLOSED/MERGE_RESULT/PHASE only when gh is intentionally skipped or as supporting evidence after gh MERGED
  - From Codex-Requirements: Clarify _resume_plan so reachable gh CLOSED/non-MERGED is a hard fresh result before state/manifest merged predicates; add a narrow test for CLOSED plus stale merged-looking state flags
  - From Codex-dyn-resume-routing: When gh is reachable, make gh state authoritative: route merged only on gh state MERGED; route OPEN with matching head to open-pr; treat CLOSED-not-MERGED or contradictions as fresh/refuse. Reserve state-only merged predicates for gh-skipped repo_unavailable/forked contexts


### FINDING_3: Open-PR resume can re-enter OOS helpers and erase restored counters
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Open-pr resume can still invoke `_materialize_manifest_oos`, the security OOS file gate, or `_oos_gate`; those helpers call `_write_ship_state` with default-zero counter kwargs, which can erase restored iteration/rebase/fix/retry counters before CI despite the counter-preservation contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Re-entering `_materialize_manifest_oos`, the security-oos file gate, or `_oos_gate` on open-pr resume calls `_write_ship_state` with default-zero counter kwargs and can erase restored `ITERATION`/`REBASE_COUNT`/`FIX_ATTEMPTS`/`TRANSIENT_RETRIES` before CI despite the counter-preservation contract State `PHASE=ci-initial` with restored counters `10/3/4/1` and stale `oos-accepted-*.md` or `security-oos-observations.md` in tmpdir Route open-pr directly to hydrated `ensure_pr` → PR-only early exits → CI seeding; never invoke the three OOS helpers on non-fresh resumes; add a test that open-pr with restored counters plus leftover OOS artifacts still seeds monitor with restored values


### FINDING_4: Resume classification precedence among done, merged, and open-pr is underspecified
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, Cursor-dyn-resume-routing
- **Severity**: important
- **Concern**: `_resume_plan` can match multiple positive resume predicates but the ordering/tie-break is unclear or inconsistent; open-pr-first routing can re-enter CI/OOS/PR handling instead of idempotent done or postmerge handling when `PHASE=done`, `PHASE=postmerge`, `PR_CLOSED=true`, or similar state-only predicates also match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Forked resume interrupted after writing `PHASE=postmerge` but before postmerge completes; next `run_ship()` classifies `open-pr` and skips postmerge Evaluate `done` and `merged` before `open-pr` in `_resume_plan`, or add explicit open-pr exclusions for `PHASE=postmerge`, `PR_CLOSED=true`, and `MERGE_RESULT` in `POST_MERGE_MERGE_RESULTS`; add a forked/state-only test for `PHASE=postmerge` → postmerge-only path
  - From Cursor-Innovation: In _resume_plan, after blocked-rebase and failed-validation fresh fallback, evaluate done (PHASE=done + branch OK) before merged/open-pr; align the Resume starts section with that order; add a test: PHASE=done, open PR, merge=false → no checks/postbump/ensure/OOS/CI
  - From Cursor-dyn-resume-routing: Document and implement fixed classification order in _resume_plan: blocked-rebase → done (PHASE=done) → merged (rule 8, including PHASE=postmerge/PR_CLOSED/MERGE_RESULT/gh MERGED) → open-pr (rule 7) → fresh; add a test with PHASE=postmerge + OPEN PR asserting start=merged


### FINDING_7: Branch mismatch fallback to fresh is unsafe
- **Reviewer(s)**: Codex-dyn-resume-routing
- **Severity**: important
- **Concern**: If state/argv branch expectations disagree with the current checkout or HEAD is detached, routing to fresh can still run checks, postbump, and PR creation using stale branch metadata while git commands operate on the wrong current HEAD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-resume-routing: For state-present branch mismatch, detached HEAD, or ctx.branch/current mismatch, safe-refuse with STALLED/NEEDS_USER_INPUT instead of fresh; only use fresh after a verified current branch matches the requested branch### OOS_1:
- **Description**: Merged/postmerge stall still writes PHASE=done on the main CI success path. Scenario: When run_postmerge_phase returns STALLED, the existing loop still calls _write_ship_state(phase="done"), which can contradict stall/finalize metadata (prior edge review); the plan only guards the new merged-resume branch
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:658-659
- **Phase**: design


