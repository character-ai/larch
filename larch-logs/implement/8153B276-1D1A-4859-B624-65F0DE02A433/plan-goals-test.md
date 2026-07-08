## Goal
Implement issue #6533: [IMPLEMENTING] Migrate /design Step 4 tail, Step 5c, and Step 6 liveness to bgjob (#6524 chunk 4/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 4/11.

Scope: migrate the /design Step 4 tail (Gate C presentation inputs), Step 5c publish wrapper, and Step 6 in-flight liveness from `run_in_background`/marker machinery to bgjob start/wait with identity-checked registry liveness, including the design Python core/lifecycle result-env plumbing.

Dependencies: blocked by #6532 (chunk 3/11: /design Step 3 review loop). Merge it first (chunks 1 and 2 are transitive prerequisites through it).

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them (final-summary cancellation, brainstorm lanes, and `design_terminal.py` migrate in the next design chunk).

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel (here: `.completed/step-4`, `.completed/step-5c-terminal`).
3. Make each migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate each per-step merge-result env before `bgjob start`.**
5. Move step result KVs into a merge env file passed through `bgjob start --merge-result-env`.
6. Treat `$DESIGN_TMPDIR/bgjob/<step>.result.env` (`design-step4-tail`, `design-step5c`) as the completion source of truth after `bgjob wait` returns `DONE`.
7. Gate normal continuation on both `BGJOB_RC=0` and required step KVs present in the final `DONE` stdout and/or the bgjob result env.
8. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
9. **Parallel lanes:** assign a unique `--step` slug per step (`design-step4-tail`, `design-step5c`) so registry rows and result envs cannot clobber each other.
10. Step 6 liveness classification must be identity-checked (owner or daemon PGID alive via identity helpers), never bare registry file presence or `.bg-wait-active`.
11. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/design/SKILL.md
- Chunk-scoped: Step 4 tail and Step 5c sections only (Step 3 landed in the previous chunk; final-summary and brainstorm land in the next).
- Replace Step 4 tail and Step 5c immediate-background instructions with `bgjob start` and chunked `bgjob wait` per `bgjob-wait.md`.
- Delete migrated premature notification recovery prose from these live call sites; keep only compatibility text that #6516 will remove later.
- Gate Step 5c continuation on `BGJOB_RC=0` plus required KVs from the final `DONE` stdout and `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`.
- **Step 4 post-`DONE`:** after final `bgjob wait` `DONE`, parse rejected-findings markers and `SKIP_APPROVE_REQUESTED_GATEC` from (1) `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` via `python/cli.py design read-result-env` and (2) the captured final `DONE` stdout; do not parse thin-launcher wrapper stdout. On `resume@4b` or absent same-turn tail capture, read the bgjob result env first, then disk fallbacks (`dialectic-clarifier-digest.md`, fingerprint-valid status files).

### UPDATED: skills/design/references/approval-gates.md
- Chunk-scoped: Gate C presentation and `resume@4b` branches (Step 3 outcomes and Gate B landed in the previous chunk).
- **Gate C presentation:** after Step 4 `DONE`, read `SKIP_APPROVE_REQUESTED_GATEC` and any framed rejected-findings body from `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` and/or captured final `DONE` stdout; do not depend on thin tail-launcher stdout.
- On `resume@4b`, pause recovery, or Step 4b entry without fresh same-turn capture, read the bgjob result env first, then invoke `design-step3b-tail.sh` as recovery mechanical emit or read fingerprint-valid disk artifacts.

### UPDATED: skills/design/references/finalize-step5.md
- Rebind Step 5c and Step 5d parsing from task-notification stdout to the final `bgjob wait` `DONE` stdout.
- Add `python/cli.py design read-result-env --input "$DESIGN_TMPDIR/bgjob/design-step5c.result.env"` as the primary result read, with stdout fallback only when the file is absent.
- Gate success on `BGJOB_RC=0`.

### UPDATED: skills/design/scripts/design-step3b-tail.sh
- Convert Step 4 tail launch to bgjob with `--step design-step4-tail`.
- Remove no-progress sidecar and `.bg-wait-active` setup.
- Truncate merge-result env before start.
- Write `SKIP_APPROVE_REQUESTED_GATEC`, rejected-findings framing markers, and any Gate C preview KVs into the merge input before daemon exit.
- Preserve `.completed/step-4`.

### UPDATED: skills/design/scripts/design-step3b-tail.md
- Replace "orchestrator backgrounds the fence" contract with foreground bgjob launch plus wait.
- Remove legacy marker arming details.
- Name `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` as completion truth for `SKIP_APPROVE_REQUESTED_GATEC` and rejected-findings body.
- Document that thin wrapper stdout is only the `BGJOB_STATUS=STARTED` line.

### UPDATED: skills/design/scripts/design-step5c.sh
- Make the wrapper a thin bgjob launcher for `design-step5c`.
- Pass the Step 5c status merge env and `.completed/step-5c-terminal` sentinel.

### UPDATED: skills/design/scripts/design-step5c.md
- Rebind the wrapper contract to bgjob.
- Name `$DESIGN_TMPDIR/bgjob/design-step5c.result.env` as the completion source.

### UPDATED: python/larch/design/design_core.py
- Chunk-scoped: this chunk retires the `design-step5c` marker call path (see `design_step5c.py` below); the final-summary call path and the end-state narrowing of `_bg_wait_marker_context` land in the next design chunk.
- Add small bgjob result path helpers and merge-env freshness helpers if this keeps readers consistent.
- Add `design-step4-tail` result-env path constant alongside existing step mappings.

### UPDATED: python/larch/design/design_lifecycle.py
- Repoint lifecycle result parsing to bgjob result envs.
- Remove dependencies on design bg-wait marker contexts.
- Extend `read_result_env_main` to prefer `$DESIGN_TMPDIR/bgjob/<step>.result.env` with legacy fallback.
- Add Step 4 tail result-env read helper for `SKIP_APPROVE_REQUESTED_GATEC` and rejected-findings markers.

### UPDATED: python/larch/design/design_step5c.py
- Stop owning bg-wait marker setup.
- Ensure Step 5c writes a merge-result env before exit.
- Keep `.completed/step-5c-terminal` write ordering.
- Ensure emitted KVs match the current prompt contract.

### UPDATED: python/larch/design/design_step6.py
- Replace `_step6_in_flight` marker detection with bgjob-aware, **identity-checked liveness** logic:
  - terminal sentinel present means not in flight
  - live identity-valid `design-step5c` registry row (owner or daemon PGID alive via identity helpers) means in flight
  - missing `bgjob/design-step5c.result.env` while publish is expected means in flight only when a live registry row exists
  - stale dead registry rows must not block Step 6; reap or ignore dead rows before classifying
- Never treat bare registry file presence or `.bg-wait-active` as sufficient for in-flight.
- Update diagnostics to say `bgjob wait`, not task notification or `.bg-wait-active`.

### UPDATED: python/tests/design/test_design_lifecycle.py
- Chunk-scoped: Step 4 tail, Step 5c, and Step 6 pins (final-summary pins land in the next design chunk).
- Pin Step 5c result env behavior.
- Add Step 6 in-flight cases for identity-checked registry liveness, missing result env, dead registry rows, and terminal-sentinel precedence.
- Pin Step 4 tail result-env read for `SKIP_APPROVE_REQUESTED_GATEC`.

### UPDATED: scripts/test-design-structure.sh
- Chunk-scoped: Step 4 and Step 5c rows only.
- Replace task-notification/immediate-background pins with `bgjob-wait.md` references for Step 4 and Step 5c waits.
- Repoint Step 4 post-`DONE` contract from `design-background-wait.md` to bgjob result-env reads for `SKIP_APPROVE_REQUESTED_GATEC` and rejected-findings markers.
- Drop or rewrite `SHARED_DESIGN_WAIT_MD` notification-recovery `contains` / `not_contains` rows that conflict with this chunk's migrated fences.
- Add assertions that these migrated design fences require `BGJOB_RC=0` gating and bgjob result-env reads.
- Add Step 4 tail result-env pin for `design-step4-tail`.
- Keep sentinel compatibility assertions.

### MAY_UPDATE: scripts/test-implement-anti-polling-rule.sh
- This harness also pins /design SKILL.md background-wait hot paths; update only rows this chunk's edits break. The full bgjob rewrite of this harness lands with the /implement checks chunk.

## Edge cases

- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` with no intervening prose or tools.
- `BGJOB_STATUS=DEAD` must not parse stale step stdout as success.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to failure or stall.
- Existing sentinels may exist from prior attempts. Result env plus identity-checked registry state must decide current completion.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each `bgjob start`.
- Step 6 must not treat Step 5c as idle when the terminal sentinel is absent and a live identity-valid `design-step5c` registry row exists; dead registry rows must not block Step 6.
- Step 4 Gate C must not read `SKIP_APPROVE_REQUESTED_GATEC` or rejected-findings body from thin tail-launcher stdout after bgjob migration.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing.
- A prompt path continues on `DONE` without checking `BGJOB_RC`.
- A result env omits a required legacy KV, causing false success or false stall.
- Step 4 or Gate C still parses tail-launcher stdout and misses `SKIP_APPROVE_REQUESTED_GATEC` or rejected-findings body.
- Step 6 treats dead registry presence as in-flight and blocks cleanup forever.
- `design-step4-tail` and `design-step5c` reuse one `--step` slug and overwrite result envs mid-run.
- `test-design-structure.sh` still pins notification-recovery literals and fails CI after skill migration.

## Testing strategy

1. `bash scripts/test-design-structure.sh`
2. `python3 -m pytest python/tests/design/test_design_lifecycle.py -q`
3. `python3 python/cli.py lint bg-wait-coverage`
4. `python3 python/cli.py lint bg-wait-writer-parity`
5. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing, registry liveness, and result-env reads.
- Keep Bash wrappers thin and macOS Bash 3.2-compatible.
- Truncate merge-result env inputs in wrappers immediately before every `bgjob start`.
- Use `larch.io` helpers for result env writes and reads where practical.
- Use config constants for bgjob status and rc keys.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion.

## Acceptance

1. Migrated `design-step3b-tail.sh` and `design-step5c.sh` harness-visible foreground stdout is exactly one `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>` line each.
2. Step 5c `DONE` continuation is gated on `BGJOB_RC=0` plus required KVs; Gate C reads `SKIP_APPROVE_REQUESTED_GATEC` and rejected-findings body from `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` and/or captured final `DONE` stdout, never from thin tail-launcher stdout; prompt-shape harnesses assert the gate text.
3. Step 6 does not treat Step 5c as idle while a live identity-valid `design-step5c` registry row exists and `.completed/step-5c-terminal` is absent; dead registry rows do not block Step 6 (pinned in `test_design_lifecycle.py`).
4. `.completed/step-4` and `.completed/step-5c-terminal` keep being written; every routing contract stays unchanged; legacy hooks stay functional and inert.
5. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 300
diff_deleted: 210
mechanical_churn: true
diff_lines: 510

## Test plan
(no test plan section in plan-file)
