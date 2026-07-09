# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Implement bgjob launchers can reuse stale result envs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-routing
- **Severity**: major
- **Concern**: Implement Step 3/5-resume/6 launchers can reuse stale result envs because they always start bgjobs without the registry rejoin and parent-side clear that Step 5/8 already use, so a fresh wait can observe old BGJOB_RC/NEXT_ACTION and skip new work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add step-5-review/step-8 style rejoin plus rm -f of bgjob/*.result.env before fresh bgjob start.
  - From cursor-specialist-edge-cases: Mirror step-5-review.sh: rm stale result env on fresh launch; rejoin only when registry live or canonical complete KVs present
  - From cursor-specialist-edge-cases: Apply the same pre-start clear/rejoin/canonical validation pattern as step-5-review.sh and step-8-ship.sh
  - From dyn-dyn-bgjob-routing: Port the `step-5-review.sh:174-218` / `step-8-ship.sh:278-301` pattern into `run-step-checks.sh` for each step slug (`implement-step3-checks`, `implement-checks-step5-self-review`, `implement-step6-checks`): rejoin on live registry or validated-complete canonical env; otherwise clear canonical result env and merge env, then start. Add harness cases mirroring `skills/implement/scripts/test-step-5-review.sh:236-284`.
  - From dyn-dyn-bgjob-routing: Reuse the Step 5 / Step 8 launcher contract: classify canonical result env, rejoin when live or complete, otherwise delete stale canonical env (and recreate merge env) before `bgjob start`. Pin with an offline harness like `test-step-5-review.sh`.
  - From dyn-dyn-bgjob-routing: Add the shared prelude (registry rejoin + canonical-env validation + stale clear) before start, and extend `skills/implement/scripts/test-step-5-review.sh` or add `test-step-5-resume.sh` coverage for stale canonical env clearing.
  - From dyn-dyn-bgjob-routing: Extract one shared bash/python helper for “bgjob launcher prelude” and call it from every long-step wrapper; until then, copy the Step 5 pattern verbatim and add structure tests in `scripts/test-implement-structure.sh` requiring it for each implement bgjob slug.


