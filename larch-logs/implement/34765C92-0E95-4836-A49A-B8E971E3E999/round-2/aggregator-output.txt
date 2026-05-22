Here is the normalized structured finding list. Duplicates merged by shared behavioral risk; IDs follow first-seen order of the earliest contributing input (`FINDING_1` … `FINDING_15`). Generic **Suggested revision** text `"Address the concern above."` appears unchanged across many inputs; where it is literally identical for every reviewer in a merged group, a single bullet lists all those slots.

### FINDING_1: Implement SKILL Step 2 prose misaligned with `run-step2-dispatch` (plan path, workflow, session-env)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 2 documentation still implies `run-step2-dispatch` derives `PLAN_FILE` and workflow from `session-env.sh`, while the launcher now uses `IMPLEMENT_TMPDIR/plan.txt` and a fixed HARD workflow. That mis-trains orchestrators on wrong env vs tmpdir sources for Step 2 debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Stale `skills/shared/subskill-invocation.md` (manifest / persist-post-plan-keys era)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Multiple reviewers note manifest / persist-post-plan-keys (or related retired session-env) prose is stale per plan OOS_1; operators may chase removed scripts or wrong handoff surfaces. Explicitly deferred to a dedicated docs pass / separate issue rather than this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: `scripts/ship-pr.sh` `resolve_plan_file` drops valid conventional plan when `PLAN_FILE` is outside `IMPLEMENT_TMPDIR`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `resolve_plan_file` can return empty when `session-env` `PLAN_FILE` points outside `IMPLEMENT_TMPDIR` (legacy or hand-edited), even when `IMPLEMENT_TMPDIR/plan.txt` exists. PR-body / forwarding paths then lose issue-anchored plan context despite a valid conventional plan on disk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Stale `docs/review-agents.md` Step 5 / `POST_PLAN_WORKFLOW_PATH` narrative vs launcher
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Consumer doc still ties round-cap / Step 5 wiring to `POST_PLAN_WORKFLOW_PATH` or otherwise diverges from `run-step5-review.sh` (fixed cap, unified plan path). Deferred out of this PR per plan OOS_2 / follow-up doc passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Acceptance “grep-clean” breadth vs explicit OOS doc deferrals (norm conflict)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Acceptance criteria imply grep-clean documentation while OOS notes defer specific files (e.g. `docs/review-agents.md` under OOS_2). Reviewers flag a process/norm conflict: either widen the follow-up doc pass, narrow the acceptance criterion, or record an explicit tracked follow-up and reconcile the Acceptance bullet with the deferrals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: `scripts/test-run-step5-review.sh` misleading SIMPLE vs HARD labels after unified Step 5
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Section titles and assert labels still refer to SIMPLE vs HARD workflows though `run-step5-review.sh` no longer branches on `POST_PLAN_WORKFLOW_PATH`, so duplicate cases can exercise the same path under misleading names—risking wrong “fixes,” false expectations, or masked regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: `scripts/test-write-run-params.sh` trivial-case JSON assertions weaker than main happy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The trivial-case `jq` assertion omits `design_classification_source` (and `workflow_path`) compared to stricter primary checks, weakening the enum / field cutover guarantee for that preset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: `hooks/hooks.json` — PostToolUse `hook-post-design.sh` removal and tmpdir disambiguation risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Without per-design `session_id` export tied to design Skill, `resolve_implement_tmpdir` may select the wrong tmpdir among cwd-matched candidates when `LARCH_TOKEN_SESSION_ID` is unset or stale. Reviewer suggests re-adding a SID-only PostToolUse hook for design or hardening tmpdir disambiguation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Core implement steps pin plan reads to `IMPLEMENT_TMPDIR/plan.txt` (security posture note)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Plan reads are pinned to conventional `IMPLEMENT_TMPDIR/plan.txt`, reducing trust in `session-env` `PLAN_FILE` for core steps; reviewer frames this as mitigating / no new vulnerability and recommends keeping the conventional plan path authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] `scripts/ship-pr.sh` `resolve_plan_file` — prefix guard without symlink canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Prefix-only under-tmpdir guard without `realpath`/non-regular-file rejection could allow symlink edge cases to bypass the intended constraint if the threat model requires that depth of validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: `skills/design/scripts/design-driver.sh` deprecated `CLASSIFY` action handled as passthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `ACTION=CLASSIFY` lines become `ACTION_PASSTHROUGH` instead of failing closed, so stale transcripts or automation can skip tier/router work silently without a failure signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: `scripts/run-step5-review.md` vs `scripts/run-step5-review.sh` empty-plan policy mismatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Markdown claims a non-empty plan requirement while the script only checks `-f`, so a zero-byte `plan.txt` can pass the launcher and confuse downstream review behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: `skills/implement/SKILL.md` Step 5 orchestrator prose vs fixed Step 5 round-cap behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Prose still suggests mirroring workflow mapping into `round_cap` while `run-step5-review.sh` uses a fixed base round cap (plus degraded inflation), risking future desync between prompt-side gates/banners and the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: `scripts/test-design-structure.sh` duplicate harness labels after CLASSIFY pin removal
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Duplicate `(14b)`-style labels make CI failures point at the wrong check id; distinct checks should have unique ids.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Git history vs plan single-atomic-commit guidance
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Multiple commits on the branch vs plan language favoring a single atomic commit reduces a single revert boundary for the cutover; squash before merge or relax plan language for future work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge map (for traceability only, not a vote)**  
- Input 3 + 15 → **FINDING_3** (`ship-pr.sh` / `resolve_plan_file` + conventional `plan.txt`).  
- Input 2, 5, 9, 14, 18, 24 → **FINDING_2** (`subskill-invocation.md`, `[OUT_OF_SCOPE]` preserved).  
- Input 4, 10, 19 → **FINDING_4** (`review-agents.md`, `[OUT_OF_SCOPE]` preserved).  
- Input 6 + 20 → **FINDING_5** (acceptance vs OOS reconciliation).  
- Inputs 7, 8, 11, 12, 13, 16, 17, 21, 22, 23 kept distinct (no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`; that token must not appear when any `### FINDING_N:` exists).
