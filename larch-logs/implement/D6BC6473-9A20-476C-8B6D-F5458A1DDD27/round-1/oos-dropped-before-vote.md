### OOS_1: [OUT_OF_SCOPE] NEVER #15 normal-path checkpoint wording (pre-existing split)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:60` still says to invoke the checkpoint wrapper after pre-driver `oos file` on the normal path, while the Step 8 OOS fence is scoped to `NEXT_ACTION=oos-pipeline` only. On the normal path, disposition runs inside pre-driver `oos file`; the orchestrator-facing checkpoint wrapper is really the security-sidecar branch. Pre-existing split; behavior unchanged by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Security-only checkpoint stamps `step9a1` without Step 9a.1 filing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/references/ship-pr-oos-checkpoint-router.md:15-17` — On the security-only branch, successful checkpoint bookkeeping still stamps `steps_ran.step9a1=true` even though no Step 9a.1 `/issue` filing ran. Pre-existing checkpoint semantics; not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Pre-driver `halt-oos` lacks SECURITY.md disposition for security sidecar
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The new SECURITY.md disposition procedure lives only on the `oos-pipeline` branch, but a non-empty `security-oos-observations.md` at pre-driver time routes to `halt-oos` (`python/oos_filer.py:811-815`), not `oos-pipeline`. Review-routed security findings before the first PR often hit that path. The orchestrator gets Step 18 routing without the imperative read-sidecar / SECURITY.md / clear-sidecar guidance added elsewhere. Pre-existing routing; plan scope targeted the `oos-pipeline` branch only.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Cleared security sidecar can rehydrate on next ship resume
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/references/ship-pr-oos-checkpoint-router.md:9-11`, `python/ship.py:1831-1850` — Clearing the sidecar after private disposition can be undone on the next ship resume: `materialize_manifest_oos` rehydrates security manifest OOS into `security-oos-observations.md` when titles are absent, which can re-trigger `oos-filing`. Behavior lives in unchanged Python; the diff did not introduce the loop.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Security sidecar contents treated as sensitive/untrusted
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:810`, `skills/implement/references/ship-pr-oos-checkpoint-router.md:9` — The sidecar may contain vulnerability details from review/implement output. New prose says read it and forbid public `/issue`, but does not warn the orchestrator to treat contents as sensitive/untrusted and avoid echoing them into chat, PR bodies, or tracking comments. Same read instruction existed in `oos-pipeline.md`; not introduced by this trim.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Exit matrix no longer documents transient retry authority
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/references/ship-pr-exit-matrix.md:25-39` — Removing `## Transient retry authority` leaves exit-6 counter persistence and retry-4 stall seeding documented only in Python (`python/cli.py ship route-exit` / `python/test_implement_dispatch.py`), not in the every-ship matrix load. Prompt-side debugging context is thinner if route-exit regresses. Intentional plan tradeoff; Python tests still own the contract.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Bail-time `steps_ran` invariant pinned only by structure-test needles
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/write-final-report.md:638-642` — The relocated bail-time `steps_ran` invariant is pinned by `test-implement-structure.sh` text needles, not by `test-write-final-report.sh` or a mandatory Step 16 read of that doc. Early bail paths see only the two-line matrix pointer until final-report time. Accepted design; Python stamping remains authoritative.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Stale Step 9a.1 reference in disposition-gate doc
- **Reviewer(s)**: dyn-dyn-oos-routing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/oos-disposition-gate.md:3` still opens with "after the Step 9a.1 `/issue` pipeline finishes," which predates this branch and contradicts the Python pre-driver `oos file` + security-sidecar split. Not introduced by this diff; stale cross-reference can confuse operators during Step 8+ stalls.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Stale `run_logs.py` comment pointer for bail-time invariant
- **Reviewer(s)**: dyn-dyn-terminal-manifest-output.txt
- **Severity**: nit
- **Concern**: `python/run_logs.py:2720-2721` — The `step9a1` verify-completeness comment still points operators at a "bail-time steps_ran invariant" in `skills/implement/SKILL.md`, but this branch moved that prose to `skills/implement/scripts/write-final-report.md:21-25`. Comment predates the diff and was not updated here.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes:** Commit-summary entries (`f5a7cc375`, `0aa3d9ba7`, `5a3463ca6`), run-log OOS markers, and passing test attestations (`make test-implement-structure`, `make test-references-headers`, `make test-write-final-report`) were treated as non-actionable metadata and omitted. NEVER #15 was split: in-scope **FINDING_2** (correctness + oos-routing) vs OOS **FINDING_6** (testing, pre-existing). Security-sidecar routing gap **FINDING_4** (in-scope codex) was kept separate from OOS **FINDING_8** (edge-cases, pre-existing halt-oos path).

