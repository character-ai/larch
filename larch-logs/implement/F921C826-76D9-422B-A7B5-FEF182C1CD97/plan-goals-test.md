## Goal
Implement issue #5308: [IMPLEMENTING] [BUG] --merge flag lost after Step 5 stall recovery: ship-pr-state.sh seeded with MERGE=false, never corrected on successful resume.

## Implementation Plan
## Summary

When `/implement --merge` hits a Step 5 code-review stall and is recovered via `transient-infra/step5-review`, the CI+merge loop never runs even though the run ultimately creates a PR successfully. The root cause is that the Step 5 stall missing-state path hard-codes `--merge false` when seeding `ship-pr-state.sh`, and the create-if-absent guard on `step-8-seed-initial.sh` prevents correction on the successful resume, so the ship driver always sees `MERGE=false` and exits at PR creation.

## Original report

Running `/implement --merge` on a long run that hit a Step 5 stall:

1. Step 5 round 2 stalled (coder-failed).
2. Stall was classified as `transient-infra/step5-review` and the run retried from Step 5.
3. Round 2 completed successfully (`coder-main-agent-required` → main agent applied fixes → checks passed).
4. PR was created (e.g., PR #5302) but CI+merge loop never ran.
5. Ship driver returned `detail: "created"` with `merge_result: ""`.

The operator had to merge the PR manually and clean up the branch themselves.

## Reproduction scenario

1. Run `/implement --merge <issue>` on an issue whose Step 5 code review will stall (e.g., external coders fail on round 2).
2. Allow stall recovery to classify the stall as `transient-infra/step5-review`.
3. Observe the resume: Step 5 completes, Step 6 checks pass, Step 7a runs, Step 8 ship creates a PR.
4. Note that `ship.py` returns `{"detail":"created","merge_result":""}` — the CI+merge loop never starts.

## Expected behavior

After stall recovery, the run should resume with the original `--merge` flag preserved. The ship driver should enter the CI+monitor+merge loop and merge the PR automatically when CI is green.

## Observed behavior

The ship driver (`python/cli.py ship pr`) is invoked with `--merge false` because `ship-pr-state.sh` was seeded with `MERGE=false` during the stall bailout, and the create-if-absent guard (`step-8-seed-initial.sh` lines 91–93) refuses to re-seed it on the pre-driver pass at Step 8.

Concretely:
- `ship.py` line 1840: `if not working.merge or …: return ShipResult(OK, detail=ensured.status)` exits immediately after PR creation.
- Driver stdout: `{"detail":"created","merge_result":"","outcome":"OK","pr_number":<N>,"pr_url":"..."}`

## Root cause analysis

The chain is:

1. `bootstrap.py:1722` writes `MERGE=true` to `$IMPLEMENT_TMPDIR/ship-seed-input.env` when `--merge` is passed.
2. `SKILL.md:623` (Step 5 `stall` missing-state branch) instructs the orchestrator to seed `ship-pr-state.sh` via `step-8-seed-initial.sh --merge false --draft false`.
3. `step-8-seed-initial.sh:131` resolves `MERGE_RESOLVED` as `first_nonempty "$ARG_MERGE" "$(read_kv_file "$seed_file" MERGE)" false`. When `--merge false` is passed as `$ARG_MERGE`, it wins and overrides the `true` in `ship-seed-input.env`.
4. `step-8-seed-initial.sh:91–93`: the create-if-absent guard refuses to re-seed a non-empty state file, so after the stall the `MERGE=false` is permanent for this run.
5. `step-8-ship.sh:76` reads `MERGE_RESOLVED="${merge:-$(read_state_key MERGE "")}"` from `ship-pr-state.sh` → `false`.
6. `ship pr --merge false` → `working.merge = False` → driver exits at `ship.py:1840` without entering the CI+merge loop.

The hardcoded `--merge false` in the stall seed instruction (`SKILL.md:623`) is the proximate bug. Its purpose is to avoid auto-merge in a stalled/bailing run, but it permanently poisons the flag for any successful resume that follows.

## Evidence

- `SKILL.md:623`: `…seed $IMPLEMENT_TMPDIR/ship-pr-state.sh with skills/implement/scripts/step-8-seed-initial.sh and pass --merge false --draft false…`
- `step-8-seed-initial.sh:91–93`: create-if-absent guard: `if [ -s "$state_file" ] && grep -Eq '^[A-Za-z_]…=' "$state_file"; then … exit 2; fi`
- `step-8-seed-initial.sh:131`: `MERGE_RESOLVED=$(first_nonempty "$ARG_MERGE" "$(read_kv_file "$seed_file" MERGE)" false)` — `$ARG_MERGE=false` wins over `ship-seed-input.env`
- `bootstrap.py:1722`: correctly writes `"MERGE": _bool_text(opts.merge_requested)` to `ship-seed-input.env` on initial bootstrap
- `ship.py:1840`: `if not working.merge or working.draft or …: return ShipResult(OK, …)` — exits at PR creation when `working.merge` is False
- Observed ship driver JSON from a real run: `{"detail":"created","merge_result":"","outcome":"OK","pr_number":5302,"pr_url":"..."}`

## Affected files

- `skills/implement/SKILL.md` — line 623: the stall-branch instruction that hardcodes `--merge false`
- `skills/implement/scripts/step-8-seed-initial.sh` — lines 91–93 (create-if-absent guard) and line 131 (MERGE resolution)
- `python/ship.py` — line 1840: merge-bypass exit gate
- `python/bootstrap.py` — line 1722: correct source of truth for MERGE (already correct, not the bug)

## Suggested fix(es)

**Option A (preferred):** Change the `SKILL.md:623` stall-branch instruction to pass the correct MERGE value from `ship-seed-input.env` rather than hardcoding `false`. The orchestrator can read `MERGE` from `$IMPLEMENT_TMPDIR/ship-seed-input.env` before invoking the seeder and pass `--merge "$seed_merge"`. This preserves the original intent (use `false` if the user didn't pass `--merge`) while not clobbering a true value on successful resume.

**Option B:** Add a `python/cli.py ship patch-state-key` (or similar) call before the pre-driver that restores `MERGE` from `ship-seed-input.env` when the stall seed has populated `ship-pr-state.sh` with `MERGE=false` but `ship-seed-input.env` says `MERGE=true`. This adds a targeted patch step rather than changing the seeder call.

**Option C:** Change `step-8-seed-initial.sh` to ignore `$ARG_MERGE` when `$ARG_MERGE=false` AND `ship-seed-input.env` says `MERGE=true`. This is fragile because callers explicitly intending `--merge false` (e.g., `--draft` mode) would be overridden.

Option A is cleanest: the orchestrator has the `ship-seed-input.env` path available and can read MERGE from it before calling the seeder.

## Open questions

- Should `SKILL.md:623` (and the analogous `coder-main-agent-required` + terminal-stall path at line 639) both be updated, or only the `stall` branch? The `coder-main-agent-required` stall path (line 639) says "seed or key-rewrite with the same durable-bail pattern as the stall branch," so both need fixing.
- Should the pre-driver (`python/cli.py ship pre-driver`) defensively detect a MERGE discrepancy (state file says false, seed file says true) and self-correct, as a belt-and-suspenders guard for future similar issues?

## Test plan
(no test plan section in plan-file)
