# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_seed_initial_state_fields` forces `MERGE=false` on any stall seed, overriding `--merge` and `ship-seed-input.env`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: `_seed_initial_state_fields` sets `merge = False` whenever `--stall-step` is non-empty (`python/ship.py:2352-2354`), overriding `ship-seed-input.env` and wrapper `--merge true`. On `/implement --merge`, a Step 5 stall seeds state with `MERGE=false`; the create-if-absent guard blocks re-seeding at Step 8; the ship driver exits after PR creation (`detail=created`, empty `merge_result`) and skips the CI+merge loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Stop forcing merge/draft false on stall_step; honor args/seed-file values and update test_seed_initial_state_stall_profile_forces_merge_and_draft_false.
  - From codex-specialist-correctness-output.txt: Remove or narrow the stall-step merge override, update python/test_ship.py expectations, and update stale prompt/doc text that still describes a stall MERGE=false profile.
  - From cursor-specialist-edge-cases-output.txt: Preserve MERGE from args/seed on stall seed; keep forcing DRAFT=false only; update test_seed_initial_state_stall_profile_forces_merge_and_draft_false.
  - From codex-specialist-edge-cases-output.txt: Honor args.merge for stall seeds, then update python/test_ship.py and skills/implement/scripts/step-8-seed-initial.md to pin the preserved-merge contract.
  - From cursor-specialist-testing-output.txt: Stop forcing MERGE=false on stall seed (preserve args.merge / ship-seed-input.env), or patch MERGE from seed file during recovery or pre-driver
  - From codex-specialist-testing-output.txt: Preserve ship-seed-input.env MERGE for resumable Step 5 stall seeds while still forcing DRAFT=false, and add a regression test for MERGE=true plus --stall-step 5.


### FINDING_2: `test_seed_initial_state_stall_profile_forces_merge_and_draft_false` encodes the old stall `MERGE=false` contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py:384-405` asserts stall seed with `--merge true` and `--stall-step 5` yields `MERGE=false`. No regression test preserves `MERGE=true` on stall seed. A correct `ship.py` fix would fail CI or regress silently if only docs change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace test with stall seed + ship-seed-input.env MERGE=true asserting MERGE=true in state.
  - From cursor-specialist-edge-cases-output.txt: Invert stall-profile test to assert MERGE preserved; add end-to-end stall-recovery MERGE preservation coverage.
  - From cursor-specialist-testing-output.txt: Update that test and add an integration test for stall seed → step5-review recovery → ship with MERGE=true
  - From codex-specialist-correctness-output.txt: update python/test_ship.py expectations
  - From codex-specialist-edge-cases-output.txt: update python/test_ship.py
  - From codex-specialist-testing-output.txt: add a regression test for MERGE=true plus --stall-step 5.


