# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Harness pins require absent CHECKPOINT_NEXT macro prose in SKILL.md
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-bootstrap-routing-output.txt, dyn-dyn-skill-contract-output.txt
- **Severity**: blocking
- **Concern**: `scripts/test-implement-rebase-macro.sh` pins two exact `CHECKPOINT_NEXT` macro contract strings that are not present in `skills/implement/SKILL.md`. The harness exits 1, so `make lint` / harness shard 18 fails in CI while unit tests can still pass. The orchestrator macro contract for `4.r`/`7.r`/`7a.r` is underspecified relative to the Python emitter until SKILL prose or harness pins are reconciled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bootstrap-routing-output.txt: Add the pinned `CHECKPOINT_NEXT` macro rules to the Rebase Checkpoint Macro section in `skills/implement/SKILL.md`, aligned with `skills/implement/references/rebase-checkpoint-routing.md` and the updated call sites.
  - From dyn-dyn-skill-contract-output.txt: Either add the missing macro contract sentences to the Rebase Checkpoint Macro section in `SKILL.md`, or relax the harness needles to match the prose actually shipped.


### FINDING_2: SKILL.md macro and Step 1.r routing still prescribe ROUTE-based branching for 4.r/7.r/7a.r
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-bootstrap-routing-output.txt, dyn-dyn-skill-contract-output.txt
- **Severity**: important
- **Concern**: The Rebase Checkpoint Macro (line 158) and Step 1.r routing (line 292) still tell the orchestrator to branch `4.r`/`7.r`/`7a.r` on `ROUTE=continue|conflict|bail`, while step call sites (lines 538, 722, 741) and `python/push.py` use `CHECKPOINT_NEXT=continue|load-routing` with fail-closed handling for missing or malformed macro keys. An orchestrator following the macro header can skip `rebase-checkpoint-routing.md` on `ROUTE=continue` when `CHECKPOINT_NEXT` is missing or malformed, or mis-route when `CHECKPOINT_NEXT` and `ROUTE` disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bootstrap-routing-output.txt: Rewrite the `4.r` / `7.r` / `7a.r` half of line 158 to mirror the call sites: parse `CHECKPOINT_NEXT`, load the reference only on `load-routing` or malformed macro, and keep `ROUTE` / `REBASE_RC` as detail inside that branch.
  - From dyn-dyn-skill-contract-output.txt: Rewrite the macro's conditional-routing paragraph for `4.r`/`7.r`/`7a.r` to match the `CHECKPOINT_NEXT=continue|load-routing` contract (`continue` = skip reference, `load-routing` or missing/malformed = load `rebase-checkpoint-routing.md`), and drop the stale `ROUTE`-as-skip-predicate language there.
  - From dyn-dyn-skill-contract-output.txt: Replace that sentence with the `CHECKPOINT_NEXT` macro rule used at the call sites, and keep `ROUTE`/`REBASE_*` parsing inside `rebase-checkpoint-routing.md` only after `CHECKPOINT_NEXT=load-routing`.


### FINDING_4: Stale ROUTE=conflict|bail can bypass Step 2 blockers in _bootstrap_next
- **Reviewer(s)**: dyn-dyn-preflight-envelope-output.txt
- **Severity**: important
- **Concern**: `_bootstrap_next` checks `ROUTE=conflict|bail` before `_step2_blockers`, so a stale preserved `ROUTE` can emit `BOOTSTRAP_NEXT=rebase-routing` even when Step 2 blockers are present (`REPO_UNAVAILABLE=true`, missing `plan.txt` / `feature-description.txt`, empty `PLAN_FILE`, etc.). The old Step 0 table evaluated blocker cleanup first; resume paths that keep an old `ROUTE` in `bootstrap-routing.env` but fail materialization on the current pass can now enter `rebase-checkpoint-routing.md` instead of `cleanup`. The plan's failure-mode note covers malformed/absent `ROUTE` (branch 6) but not explicit `conflict|bail` (branch 2).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-preflight-envelope-output.txt: Gate branch 2 the same way as branch 6: only route to `rebase-routing` on `ROUTE=conflict|bail` when `not _step2_blockers(data)`, or evaluate `_step2_blockers` before any `ROUTE`-based rebase branch. Add a matrix test for `REPO_UNAVAILABLE=true` + `ROUTE=conflict` + `continue_tail_attempted=false` expecting `cleanup`.


### FINDING_6: Absorbed 1.r entry predicates diverge between SKILL.md and rebase-checkpoint-routing.md
- **Reviewer(s)**: dyn-dyn-skill-contract-output.txt
- **Severity**: important
- **Concern**: Absorbed `1.r` entry in `skills/implement/references/rebase-checkpoint-routing.md` is still defined as `CHECKPOINT_NEXT=load-routing` or missing/malformed `CHECKPOINT_NEXT`, while Step 0 and Step 1.r routing in `SKILL.md` (lines 284, 292) gate absorbed `1.r` only on `BOOTSTRAP_NEXT=rebase-routing`. That creates dual, potentially divergent entry predicates for the same checkpoint (for example, an orchestrator could treat missing `CHECKPOINT_NEXT` as rebase failure even when `BOOTSTRAP_NEXT=step2`, or use `CHECKPOINT_NEXT` instead of `BOOTSTRAP_NEXT` to enter conflict handling).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-contract-output.txt: Update the absorbed `1.r` "when to load" text to say entry is selected by `BOOTSTRAP_NEXT=rebase-routing` from the Step 0 envelope, and reserve `CHECKPOINT_NEXT` for foreground `4.r`/`7.r`/`7a.r` probes only.


