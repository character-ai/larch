## Plan

## Context

`approach-synthesis.txt`, `discussion-round1.md`, `brainstorm.md`, and local approved outline files were not present in the checkout. This plan is based on direct repo inspection and the supplied feature scope.

## Approach

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Migrate one surface group per commit:
   - `/design`
   - `/implement`
   - `/review`
   - `/research`
   - stall and state classifiers
   - shared docs and lints
   - harnesses
3. Preserve every existing terminal sentinel and Step 8 handoff sidecar.
4. Make each migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
5. **Clear or recreate each per-step merge-result env before `bgjob start`** so stale KVs from a prior attempt cannot satisfy required-key gates after a fresh child exits `BGJOB_RC=0` without writing new values. Prefer truncating the merge input file immediately before start; optionally stamp a per-run generation token in the merge env.
6. Move step result KVs into a merge env file passed through `bgjob start --merge-result-env`.
7. Treat `$TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
8. Gate normal continuation on both:
   - `BGJOB_RC=0` (with the Step 8 carve-out below)
   - required step KVs present in the final `DONE` stdout and/or the bgjob result env
9. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, any other non-zero rc where the step has no valid completion sidecar, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
10. **Step 8 carve-out:** do not apply the generic `BGJOB_RC=0` gate to `ship route-exit`. The bgjob child must always write current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` (when schema JSON exists) before exit. Prefer making the child exit 0 after `persist_handoff` and keeping the real driver rc only in the sidecar. If the child preserves a non-zero process rc, allow `DONE` continuation to `ship route-exit` when both handoff sidecars are present and current, while still blocking `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, `DEAD`, and missing or stale handoff sidecars.
11. **Parallel lanes:** assign a unique `--step` slug per concurrent external lane so registry rows and result envs cannot clobber each other.
12. **Live-registry rejoin:** before every `bgjob start` for long-lived loops (`design-step3-review`, `implement-step5-review`, `implement-step8-ship`), if an identity-valid registry row exists for that step, refuse a second start and require chunked `bgjob wait` instead; clear only stale or dead rows before a fresh start.
13. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/shared/bgjob-wait.md
- Add examples for wrapper launch, repeated `wait`, `DONE` parsing, and `--merge-result-env`.
- Pin the "no prose, no tools, no sleep between WAITs" rule.
- Name result envs as the completion source of truth.
- Document merge-input freshness: truncate or recreate the merge env before each `bgjob start`.
- Document the Step 8 handoff-sidecar carve-out: route-exit follows sidecar rc/json, not `BGJOB_RC=0` alone.
- Document per-lane unique `--step` slugs for parallel external lanes.

### UPDATED: skills/design/SKILL.md
- Replace Step 3, Step 4 tail, Step 5c, final-summary cancellation, and brainstorm immediate-background instructions with `bgjob start` and chunked `bgjob wait` per `bgjob-wait.md`.
- Delete migrated premature notification recovery prose from live call sites.
- Keep only compatibility text that #6516 will remove later.
- Gate Step 3, Step 5c, and final-summary continuation on `BGJOB_RC=0` plus required KVs from the final `DONE` stdout and `$DESIGN_TMPDIR/bgjob/<step>.result.env`.
- Rebind Step 3 post-`DONE` parsing to read `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` first via `python/cli.py design read-result-env` (or equivalent), with legacy `.step3-review-result.env` fallback only when the bgjob path is absent.
- **Step 4 post-`DONE`:** after final `bgjob wait` `DONE`, parse rejected-findings markers and `SKIP_APPROVE_REQUESTED_GATEC` from (1) `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` via `python/cli.py design read-result-env` and (2) the captured final `DONE` stdout; do not parse thin-launcher wrapper stdout. On `resume@4b` or absent same-turn tail capture, read the bgjob result env first, then disk fallbacks (`dialectic-clarifier-digest.md`, fingerprint-valid status files).
- Rebind Step 3 resume fences to bgjob `DONE` plus result-env parsing; remove `design-step3-review.sh --starting-round` immediate-background resume prose.

### UPDATED: skills/design/references/plan-review.md
- Replace `run_in_background` launch and resume instructions with bgjob launch and wait semantics.
- Preserve `STEP3_REVIEW_LOOP_STATUS` and resume branches.
- Rebind post-`DONE` result parsing to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with controlled legacy fallback.
- Require `BGJOB_RC=0` before routing on loop envelope KVs.
- Resume mid-loop through chunked `bgjob wait` on a live `design-step3-review` registry row; do not relaunch when identity-valid.

### UPDATED: skills/design/references/approval-gates.md
- Rebind **Step 3 outcomes** (`NEXT_ACTION` table and resume branches) from `.step3-review-result.env` to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with legacy fallback only when absent.
- Gate Gate B post-apply resume and Step 3 mid-loop returns on `BGJOB_RC=0` plus required loop envelope KVs from the bgjob result env.
- Replace `design-step3-review.sh --starting-round …` immediate-background resume instructions with bgjob `DONE` plus result-env parsing and live-registry rejoin via `bgjob wait`.
- **Gate C presentation:** after Step 4 `DONE`, read `SKIP_APPROVE_REQUESTED_GATEC` and any framed rejected-findings body from `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` and/or captured final `DONE` stdout; do not depend on thin tail-launcher stdout.
- On `resume@4b`, pause recovery, or Step 4b entry without fresh same-turn capture, read the bgjob result env first, then invoke `design-step3b-tail.sh` as recovery mechanical emit or read fingerprint-valid disk artifacts.
- Rebind any Step 3 re-entry prose that still assumes task-notification completion to bgjob `DONE` plus result-env parsing.

### UPDATED: skills/design/references/finalize-step5.md
- Rebind Step 5c and Step 5d parsing from task-notification stdout to the final `bgjob wait` `DONE` stdout.
- Add `python/cli.py design read-result-env --input "$DESIGN_TMPDIR/bgjob/design-step5c.result.env"` as the primary result read, with stdout fallback only when the file is absent.
- Gate success on `BGJOB_RC=0`.

### UPDATED: skills/design/references/brainstorm.md
- Convert external brainstorm lanes to per-lane bgjob start and wait, or foreground collection where parallelism is not needed.
- Keep Claude Agent fallback behavior unchanged.
- Require **unique `--step` slugs per parallel lane** (for example `design-brainstorm-framing`, `design-brainstorm-diverge`, `design-brainstorm-converge`).
- Truncate per-lane merge-result envs before each lane start.

### UPDATED: skills/design/references/sentinel-host-table.md
- Document bgjob result envs as completion truth.
- Keep terminal sentinels as compatibility transition markers.
- Name `design-step4-tail` result env as Step 4 completion truth.

### UPDATED: skills/design/scripts/design-step3-review.sh
- Remove `.bg-wait-active`, detach, and reattach ownership logic.
- Keep precondition rehydration and pause-save checks.
- Truncate `$DESIGN_TMPDIR/.step3-review-result.env` (merge input) immediately before start.
- Write step KVs to the merge input; daemon merges into `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env`.
- `exec` bgjob start for `design-step3-review` with `--merge-result-env "$DESIGN_TMPDIR/.step3-review-result.env"` and sentinel `.completed/step-3-terminal`.
- On re-entry when a live identity-valid `design-step3-review` registry row exists, refuse a second `bgjob start`.

### UPDATED: skills/design/scripts/design-step3-review.md
- Update the wrapper contract to bgjob ownership and result env parsing.
- Name `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` as completion truth.
- Preserve sentinel behavior descriptions.
- Document live-registry rejoin vs fresh-start rules.

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
- Retire `_bg_wait_marker_context` call paths.
- Keep only compatibility helpers still needed by retained legacy hooks, if any.
- Add small bgjob result path helpers and merge-env freshness helpers if this keeps readers consistent.
- Add `design-step4-tail` result-env path constant alongside existing step mappings.

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

### UPDATED: python/larch/design/design_terminal.py
- Migrate final-summary cancellation to bgjob.
- Preserve `.completed/step-final-summary`.
- Allow `read_result_env_main` to read bgjob result env paths under `$DESIGN_TMPDIR/bgjob/`.
- Truncate merge-result env before final-summary start.

### UPDATED: python/larch/design/design_lifecycle.py
- Repoint lifecycle result parsing to bgjob result envs.
- Remove dependencies on design bg-wait marker contexts.
- Extend `read_result_env_main` to prefer `$DESIGN_TMPDIR/bgjob/<step>.result.env` with legacy fallback.
- Add Step 4 tail result-env read helper for `SKIP_APPROVE_REQUESTED_GATEC` and rejected-findings markers.

### UPDATED: python/larch/review/plan_review_normalize.py
- Repoint `_step3_normalize_read_result_env`, `_step3_read_result_env_quiet`, and `--read-result-env` to read `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` first, with controlled fallback to `.step3-review-result.env` only when absent.
- Include `BGJOB_RC` in required keys for Step 3 completion routing.
- Update comments and normalization paths that still mention task-notification races.
- Preserve Step 3 result KV compatibility for downstream envelopes.

### UPDATED: skills/implement/SKILL.md
- Replace Step 3, Step 5, Step 6, Step 7a, and Step 8 immediate-background fences with bgjob start and wait loops per `bgjob-wait.md`.
- Update anti-halt text so `WAIT` means the next action is another identical `bgjob wait`.
- State explicitly: after the final `bgjob wait` `DONE`, required KVs come from the last `DONE` stdout and `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`, not from the start launcher, notification recovery, or intermediate wait turns.
- **Step 8:** after final `DONE`, proceed to `ship route-exit` when current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` (when required) exist; do not require `BGJOB_RC=0`. Still block `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, `DEAD`, and missing handoff sidecars.
- On live identity-valid `implement-step8-ship` registry row, rejoin via `bgjob wait`; refuse a second `bgjob start`.

### UPDATED: skills/implement/references/self-review.md
- Convert Step 5 review, self-review, and resume variants to bgjob ownership.
- Remove `.step5-wrapper-detached` and `.step5-reattach-active` prompt contracts after tests pin replacement behavior.
- Gate continuation on `BGJOB_RC=0`.

### UPDATED: skills/implement/references/step5-review-branches.md
- Convert MAV, coder-handoff, stall, and resume branches to bgjob start plus chunked wait.
- Rebind resume and re-entry parsing to bgjob result envs with `BGJOB_RC=0` gate.
- Document same-step rejoin: a live identity-valid registry row for the Step 5 loop must be rejoined via `bgjob wait`, not relaunched; stale or dead rows are cleared before a fresh `bgjob start`.

### UPDATED: skills/implement/references/checks-repair-loop.md
- Convert pinned Step 3, Step 5, and Step 6 post-repair re-entry composite launch commands to the shared bgjob start/wait contract.
- After `NEXT_ACTION=continue`, route orchestrator through foreground `bgjob start` plus chunked `bgjob wait`, not bare composite relaunch fences.
- Gate re-entry continuation on `BGJOB_RC=0` and required KVs from result envs.
- Truncate merge-result envs before each re-entry start.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md
- Replace every Step 8 relaunch leg with bgjob start plus wait.
- Keep route-exit inputs unchanged after `DONE` with valid current handoff sidecars.
- Document Step 8 bgjob carve-out: numeric driver rc in `.step-8-ship-handoff.rc` is authoritative for `ship route-exit`; do not treat non-zero `BGJOB_RC` as generic bgjob failure when sidecars are present and current.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md
- Convert CI-fix relaunch prose to bgjob.
- Preserve handoff-sidecar gate before `ship route-exit`.

### UPDATED: skills/implement/references/conflict-resolution.md
- Convert conflict-resolution Phase 4 ship relaunch to bgjob.
- Preserve conflict-routing semantics and Step 8 rejoin rule.

### UPDATED: skills/implement/references/stall-recovery.md
- Convert `step8-shippr` retry instructions to bgjob.
- Keep stall state tokens unchanged.
- Pin live-registry rejoin for `implement-step8-ship`.

### UPDATED: skills/implement/scripts/run-step-checks.sh
- Stop writing `.bg-wait-active`.
- Truncate merge-result envs before each checks leg start.
- Launch Step 3 checks through bgjob with the existing Step 3 sentinel.
- Ensure Step 6 checks legs use the same result env convention.

### UPDATED: skills/implement/scripts/step-5-review.sh
- Replace bespoke loop detach and reattach with bgjob daemon ownership.
- Ensure owner death and orphan handling are delegated to bgjob.
- Write normalized Step 5 KVs to the merge-result env.
- Preserve `.completed/step-5-terminal`.
- On re-entry when a live identity-valid Step 5 registry row exists, refuse a second `bgjob start` and require chunked `bgjob wait` instead.

### UPDATED: skills/implement/scripts/step-5-review.md
- Rebind the contract to bgjob daemon ownership, owner-death/orphan handling, and merge-result env completion.
- Drop detach/reattach sidecar prose.
- Document re-entry rejoin vs fresh-start rules.

### UPDATED: skills/implement/scripts/step-5-resume.sh
- Convert the resume fence to a thin `bgjob start` launcher for `implement-step5-resume` (or equivalent step name).
- Delegate daemon ownership, orphan handling, and result-env merge to bgjob.
- Preserve timing capture and `.completed/step-5-resume-terminal` semantics.

### UPDATED: skills/implement/scripts/step-6-entry.sh
- Convert to bgjob start.
- Preserve `.completed/step-6-terminal`.

### UPDATED: skills/implement/scripts/step-8-ship.sh
- Run the ship driver as a bgjob daemon.
- Preserve `.step-8-ship-handoff.rc`, `.step-8-ship-handoff.json`, and `persist_handoff` ordering.
- Prefer child exit 0 after `persist_handoff`; keep real driver rc in the sidecar.
- Merge any route-exit KVs into the bgjob result env without changing `ship route-exit` consumption.
- On re-entry when a live identity-valid `implement-step8-ship` registry row exists, refuse a second `bgjob start` and require chunked `bgjob wait`.

### UPDATED: skills/implement/scripts/step-8-ship.md
- Replace `.bg-wait-active` and background relaunch guidance with bgjob contract.
- Keep handoff sidecar contract byte-compatible.
- Gate route-exit handoff on current handoff sidecars after final `DONE`; do not require `BGJOB_RC=0`.

### UPDATED: python/larch/implement/dispatch_commit_route.py
- Replace `_write_bg_wait_marker` contexts with bgjob result handling or remove them when wrappers own bgjob launch.
- Update Step 3, Step 5 resume, Step 5 self-review, and commit-route marker branches.
- Parse `BGJOB_RC` from result envs before resume routing.

### UPDATED: python/larch/implement/implement_dispatch.py
- Update branches that launch or parse Step 3, Step 5, Step 6, and Step 8 wrappers.
- Parse `BGJOB_STATUS` and bgjob result env KVs, including `BGJOB_RC`, before existing branch handling.
- Step 8: route to `ship route-exit` from handoff sidecars, not `BGJOB_RC=0` alone.

### UPDATED: python/larch/implement/dispatch_step18.py
- Convert recovery relaunch paths that still reference legacy marker machinery.
- Preserve Step 18 stall and final-report routing.
- Apply Step 8 live-registry rejoin before recovery relaunch.

### UPDATED: python/larch/implement/step_7a.py
- Replace `_bg_wait_marker` usage with bgjob result and sentinel handling.
- Preserve `.completed/step-7a-terminal`.

### UPDATED: python/larch/implement/bg_wait.py
- Narrow to the compatibility surface needed by retained legacy hooks.
- Do not delete the module in this issue.

### UPDATED: python/larch/review/review_and_fix.py
- Audit standalone `/review --diff` and nested Step 5 paths for background assumptions.
- Ensure long loops produce mergeable result KVs for bgjob.

### UPDATED: python/larch/review/plan_review.py
- Ensure plan-review loop outputs remain merge-result-env compatible.
- Write completion KVs into the merge input consumed by `design-step3-review`.

### UPDATED: python/larch/review/review_pipeline.py
- Ensure nested and standalone review loops do not depend on task-notification output.

### UPDATED: skills/research/references/research-phase.md
- Replace Codex lane `run_in_background` instructions with per-lane bgjob start and wait.
- Keep Claude Agent fallback unchanged.
- For parallel lanes, start each separately with a **unique `--step` slug** (`research-arch`, `research-edge`, `research-ext`, `research-sec`) and wait each separately.
- Truncate per-lane merge-result envs before start.

### UPDATED: skills/research/references/validation-phase.md
- Apply the same bgjob conversion to Cursor and Codex validation lanes.
- Require unique `--step` slugs per lane (`validation-code`, `validation-cursor`, `validation-codex`).

### UPDATED: python/larch/state/_tokens.py
- Replace `_abandoned_checks_marker_stall_step` marker logic with bgjob registry inspection.
- Detect abandoned rows by identity-checked dead owner or daemon PGID.
- Never use bare PID liveness or bare registry file presence.

### UPDATED: python/larch/state/_classify.py
- Route abandoned checks detection through the bgjob-aware helper.

### UPDATED: python/larch/state/_state_mgmt.py
- Rename or narrow `_clear_abandoned_checks_marker`.
- Clear stale bgjob registry rows for checks steps on recovery completion.

### UPDATED: skills/shared/orchestrator-never.md
- Add bgjob wait NEVER rules.
- Narrow retained task-notification rules to compatibility-only docs.
- Add Step 8 carve-out: do not treat numeric driver rc in handoff sidecars as generic bgjob failure.
- Do not delete #6516-owned defense text unless it conflicts with migrated call sites.

### UPDATED: skills/shared/final-summary-emit.md
- Rebind `/design` final-summary sources to captured bgjob `DONE` stdout and result env reads.
- Rebind `/implement` Step 17 and Step 18b from task-notification sources to final `bgjob wait` stdout with `BGJOB_RC=0` gate (Step 8 ship driver excluded from that gate).

### UPDATED: docs/workflow-lifecycle.md
- Document bgjob result envs as completion truth for long-running steps.
- Document diagnostics in bgjob logs and result envs.
- Document merge-env truncation before each start.
- Document Step 8 handoff-sidecar carve-out and per-lane unique step slugs.

### UPDATED: docs/run-logs.md
- Extend bgjob diagnostics and result env documentation before run-log capture.

### UPDATED: docs/linting.md
- Update bg-wait coverage and writer-parity docs.
- Add `scripts/test-bgjob.sh` shard expectations.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Shrink to at most `skills/shared/orchestrator-never.md`.
- Remove migrated entries.

### UPDATED: python/larch/lint/lint_bg_wait_writer_parity.py
- Rescope writer parity so it no longer requires `.bg-wait-active` writers.
- Keep compatibility lint passing until #6516 removes legacy hooks.

### UPDATED: python/tests/lint/test_lint_bg_wait_writer_parity.py
- Update expectations for the narrowed compatibility lint.

### UPDATED: scripts/test-design-structure.sh
- Replace task-notification/immediate-background pins with `bgjob-wait.md` references for Step 3, Step 4, Step 5c, and final-summary waits.
- Repoint Step 4 post-`DONE` contract from `design-background-wait.md` to bgjob result-env reads for `SKIP_APPROVE_REQUESTED_GATEC` and rejected-findings markers.
- Drop or rewrite `SHARED_DESIGN_WAIT_MD` notification-recovery `contains` / `not_contains` rows that conflict with bgjob migration.
- Add assertions that migrated design fences require `BGJOB_RC=0` gating (except Step 8 carve-out) and bgjob result-env reads.
- Add Step 4 tail result-env pin for `design-step4-tail`.
- Keep sentinel compatibility assertions.

### UPDATED: skills/design/scripts/test-design-step3-review.sh
- Assert wrapper stdout is exactly the bgjob started line.
- Assert no `.bg-wait-active` writer remains.
- Assert completion parsing prefers `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` and includes `BGJOB_RC` in required keys.
- Add stale merge-env regression: pre-seed merge input with prior-run KVs, start fresh child that writes only `BGJOB_RC=0`, assert routing does not succeed without fresh step KVs.

### UPDATED: scripts/test-implement-structure.sh
- Replace Step 5 and Step 8 task-notification assertions with bgjob assertions.
- Assert `BGJOB_RC=0` gates on Step 5 completion routing.
- Assert Step 8 route-exit follows handoff sidecars without requiring `BGJOB_RC=0`.
- Add Step 5 resume wrapper and `step5-review-branches.md` bgjob contract pins.

### UPDATED: scripts/test-implement-anti-polling-rule.sh
- Update anti-polling rules for bgjob `WAIT`.
- Keep legacy defense assertions only for compatibility surfaces.

### UPDATED: scripts/test-implement-fence-shape.sh
- Update `EXPECTED_OLD` and `EXPECTED_NEW` for changed `skills/implement/SKILL.md` fences.

### UPDATED: skills/implement/scripts/test-step-5-review.sh
- Pin Step 5 bgjob ownership, owner death, orphaned result, and no detach sidecars.
- Pin re-entry behavior: live registry row requires wait rejoin, not second start; dead row cleared before fresh start.
- Add stale merge-env regression assertion.

### UPDATED: skills/implement/scripts/test-step-8-ship.sh
- Assert bgjob launch contract and unchanged handoff rc/json ordering.
- Assert route-exit is reached with valid handoff sidecars even when `BGJOB_RC` is non-zero (pin rc `3` or `6` cases).
- Assert route-exit is not reached without current handoff sidecars or on `BGJOB_RC=timeout` / `BGJOB_RC=orphaned` / `DEAD`.
- Pin live-registry rejoin: second `bgjob start` refused when identity-valid `implement-step8-ship` row exists.

### UPDATED: scripts/test-research-structure.sh
- Assert research and validation lanes use bgjob, not `run_in_background`.
- Assert unique per-lane `--step` slugs (`research-arch`, `research-edge`, `validation-cursor`, etc.).
- Add collision regression: parallel lane starts must not overwrite distinct result env paths.

### UPDATED: scripts/test-hook-bg-poll-guard.sh
- Keep legacy marker coverage.
- Add assertions that bgjob wait loops do not trigger legacy polling denies.

### UPDATED: scripts/test-hook-no-progress-guard.sh
- Keep legacy no-progress coverage.
- Assert bgjob `WAIT` loops do not count as stale background-wait turns.

### UPDATED: scripts/test-render-cost-line-callsites.sh
- Update final-summary source assertions away from task-notification stdout.

### NEW: scripts/test-bgjob.sh
- Add real-process coverage for:
  - one-line start stdout
  - owner death writes `BGJOB_RC=orphaned`
  - budget expiry writes `BGJOB_RC=timeout`
  - external daemon kill yields `DEAD`
  - identity-checked reap does not signal a recycled PID owner
  - bad step names are rejected
- Skip loudly when sandbox limitations block `ps` identity probes.

### UPDATED: Makefile
- Repoint or split `test-bgjob` so real-process `scripts/test-bgjob.sh` is in a `test-harnesses-N` shard.
- Keep Python bgjob unit tests in `py-test`, not duplicated as the only bgjob harness.
- Run `make test-harness-shards-coverage` after shard edits.

### UPDATED: python/tests/implement/test_implement_dispatch.py
- Replace `.bg-wait-active` expectations for Step 3 and Step 5 resume with bgjob start/wait contracts.
- Pin `BGJOB_RC` parsing before resume routing.
- Pin Step 8 route-exit from handoff sidecars without `BGJOB_RC=0` requirement.

### UPDATED: python/tests/implement/test_step_7a.py
- Pin bgjob result handling and `.completed/step-7a-terminal`.

### UPDATED: python/tests/design/test_design_lifecycle.py
- Pin Step 5c result env behavior.
- Add Step 6 in-flight cases for identity-checked registry liveness, missing result env, dead registry rows, and terminal-sentinel precedence.
- Pin final-summary bgjob behavior.
- Pin Step 4 tail result-env read for `SKIP_APPROVE_REQUESTED_GATEC`.

### UPDATED: python/tests/review/test_plan_review.py
- Pin `_step3_normalize_read_result_env` and `--read-result-env` to prefer `bgjob/design-step3-review.result.env`.
- Add `BGJOB_RC` required-key coverage and legacy-path fallback tests.

### UPDATED: python/tests/review/test_review_and_fix.py
- Replace Step 5 detached-wrapper expectations with bgjob registry ownership expectations.

### UPDATED: python/tests/state/test_stall_recovery.py
- Replace abandoned marker tests with abandoned bgjob registry row tests.
- Cover dead owner, dead daemon, live registry without result env, stale dead registry not blocking, and cleared registry.

### MAY_UPDATE: python/tests/bgjob/test_daemon.py
- Add any missing daemon unit coverage found while wiring real-process shell tests.

### MAY_UPDATE: python/tests/bgjob/test_wait.py
- Add parsing and `DEAD` edge coverage if the migration needs a wait helper adjustment.

### MAY_UPDATE: python/tests/bgjob/test_bgjob_cli.py
- Add CLI flag coverage for any new helper option needed by migrated wrappers.

### MAY_UPDATE: scripts/hook-deny-run-in-background.sh
- Update only if registry row shape changes.
- Keep it denying `run_in_background` while a larch bgjob is active in the clone.

### MAY_UPDATE: scripts/test-hook-deny-run-in-background.sh
- Update fixture rows only if registry shape changes.

## Edge cases

- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` with no intervening prose or tools.
- `BGJOB_STATUS=DEAD` must not parse stale step stdout as success.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to failure or stall.
- `bgjob wait` shell exit 0 on `WAIT` or `DEAD` must not advance the step.
- Existing sentinels may exist from prior attempts. Result env plus identity-checked registry state must decide current completion.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each `bgjob start`.
- Step 6 must not treat Step 5c as idle when the terminal sentinel is absent and a live identity-valid `design-step5c` registry row exists; dead registry rows must not block Step 6.
- Step 5 re-entry must rejoin a live registry row via `bgjob wait` and must not launch a second loop daemon.
- Step 8 re-entry must rejoin a live `implement-step8-ship` registry row via `bgjob wait` and must not launch a second ship driver.
- Step 8 must write handoff rc/json before any route-exit handling sees the result.
- Step 8 `DONE` with numeric driver rc in `.step-8-ship-handoff.rc` (for example `3` or `6`) must still reach `ship route-exit` when sidecars are current; `BGJOB_RC=0` is not required for Step 8.
- Parallel research, validation, or brainstorm lanes must use distinct `--step` slugs so registry rows and result envs do not clobber each other.
- Step 4 Gate C must not read `SKIP_APPROVE_REQUESTED_GATEC` or rejected-findings body from thin tail-launcher stdout after bgjob migration.
- Gate B Step 3 resume must not read only legacy `.step3-review-result.env` or relaunch via immediate-background fences.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing.
- A prompt path continues on `DONE` without checking `BGJOB_RC` (except the documented Step 8 carve-out).
- A result env omits a required legacy KV, causing false success or false stall.
- Stale merge-input env satisfies KVs after `BGJOB_RC=0` without fresh child output.
- Step 3 normalize still reads `.step3-review-result.env` and misses `BGJOB_RC` or fresh loop status.
- Gate B resume still launches `design-step3-review.sh` immediate-background instead of rejoining via `bgjob wait`.
- Step 4 or Gate C still parses tail-launcher stdout and misses `SKIP_APPROVE_REQUESTED_GATEC` or rejected-findings body.
- Parallel lanes reuse one `--step` slug and overwrite result envs mid-run.
- Step 5 detach sidecars are removed before bgjob owner-death and re-entry tests cover the replacement.
- Step 5 resume path remains on legacy direct launch because `step-5-resume.sh` or `step5-review-branches.md` were not migrated.
- Step 8 route-exit is blocked by a blanket `BGJOB_RC=0` gate despite valid numeric handoff rc.
- A second live Step 8 ship daemon starts and races on the same handoff files.
- Checks repair-loop still relaunches bare composites and bypasses bgjob wait.
- Step 6 treats dead registry presence as in-flight and blocks cleanup forever.
- Step 8 handoff sidecar ordering changes and breaks `ship route-exit`.
- `test-design-structure.sh` still pins notification-recovery literals and fails CI after skill migration.
- Allowlist shrinks before all skill prose is migrated, causing lint failure.
- Hook tests are over-pruned and accidentally delete #6516 compatibility coverage.

## Testing strategy

Run targeted tests with each surface group:

1. Design:
   - `bash scripts/test-design-structure.sh`
   - `bash skills/design/scripts/test-design-step3-review.sh`
   - `python3 -m pytest python/tests/design/test_design_lifecycle.py python/tests/review/test_plan_review.py -q`
2. Implement:
   - `bash scripts/test-implement-structure.sh`
   - `bash scripts/test-implement-anti-polling-rule.sh`
   - `bash scripts/test-implement-fence-shape.sh`
   - `bash skills/implement/scripts/test-step-5-review.sh`
   - `bash skills/implement/scripts/test-step-8-ship.sh`
   - `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py -q`
3. Research:
   - `bash scripts/test-research-structure.sh`
4. State:
   - `python3 -m pytest python/tests/state/test_stall_recovery.py -q`
5. Review:
   - `python3 -m pytest python/tests/review/test_review_and_fix.py -q`
6. Lints:
   - `python3 python/cli.py lint bg-wait-coverage`
   - `python3 python/cli.py lint bg-wait-writer-parity`
7. Bgjob:
   - `python3 -m pytest python/tests/bgjob -q`
   - `bash scripts/test-bgjob.sh`
8. Final validation:
   - `make py-lint`
   - `make py-test`
   - affected `test-harnesses-N` shards
   - one full `/design` run and one full `/implement --merge` run on a MODERATE issue, verifying no `<task-notification>` transcript entries for migrated larch launches

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing, registry liveness, and result-env reads.
- Keep Bash wrappers thin and macOS Bash 3.2-compatible.
- Truncate merge-result env inputs in wrappers immediately before every `bgjob start`.
- Use `larch.io` helpers for result env writes and reads where practical.
- Use config constants for bgjob status and rc keys.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion.
- Step 8: prefer child exit 0 after `persist_handoff`; keep driver rc in `.step-8-ship-handoff.rc` for `ship route-exit`.
- Parallel lanes: never reuse a `--step` slug across concurrent external reviewers.

## Acceptance

1. `git grep -l "run_in_background" skills/` returns only lint-allowlisted files and historical run logs; `python/larch/lint/bg_wait_allowlist.txt` holds at most the `skills/shared/orchestrator-never.md` compatibility entry; `python3 python/cli.py lint bg-wait-coverage` enforces this in `make lint`.
2. Every migrated wrapper's harness-visible foreground stdout is exactly one `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>` line, harness-asserted per wrapper.
3. `DONE` continuation is gated on `BGJOB_RC=0` plus required step KVs at every migrated orchestrator branch (Step 8 follows the handoff-sidecar carve-out: current `.step-8-ship-handoff.rc`/`.json` reach `ship route-exit`, while `timeout`, `orphaned`, `DEAD`, and missing sidecars are blocked); prompt-shape harnesses assert the gate text.
4. Step 6 does not treat Step 5c as idle while a live identity-valid `design-step5c` registry row exists and `.completed/step-5c-terminal` is absent; dead registry rows do not block Step 6 (pinned in `test_design_lifecycle.py`).
5. Stall recovery classifies abandoned `implement-step3-checks` and `implement-step5-self-review` legs from dead bgjob registry rows, not `.bg-wait-active` (pinned in `test_stall_recovery.py`).
6. All existing terminal sentinels and the Step 8 handoff rc/json sidecars keep being written; `ship route-exit` and every routing contract stay unchanged; legacy hooks stay functional and inert.
7. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass, including pylint and the pytest unique-basename constraint for new test files.
8. `scripts/test-bgjob.sh` passes in its `test-harnesses` shard against real processes: owner death yields `BGJOB_RC=orphaned` within grace, budget expiry yields `BGJOB_RC=timeout`, an externally killed daemon yields `DEAD` within one poll interval, and identity-checked reap leaves a recycled PID's new owner unharmed.
9. Post-merge validation: one full `/design` run and one full `/implement --merge` run on a MODERATE issue complete with zero `<task-notification>` entries for migrated larch launches; #6516 stays blocked on this issue until all criteria hold.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_added: 1980
diff_deleted: 1350
mechanical_churn: true
diff_lines: 3330
