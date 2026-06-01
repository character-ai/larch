## Plan

Two changes to `scripts/ship-pr.sh` (#3299): (1) absorb the remaining prompt-side `step8b_rebase` rebase/re-bump handoff into the script, reusing `run_rebase_rebump`'s deterministic helpers; (2) fold `CLONE_TAG_FULL` into argv-init. Keep `conflict-resolution.md` Phase 1–4 prompt-side via the `exit 5` + `CALLER_KIND=ship_pr_pre_push` escape, with a resume route back to the postbump force-push-gate.

**Scope correction (verified):** `step8_apply_bump_same_version` is ALREADY internal — `_run_step8_same_version_mechanically()` (ship-pr.sh ~line 2913, landed in #2649 before #3299 was filed). The only remaining prompt-side rebase/re-bump handoff is `step8b_rebase`. This plan also retires the now-dead `step8_apply_bump_same_version` `exit 5` references.

### UPDATED: `scripts/ship-pr.sh`
- **Add `run_step8b_rebase_rebump_internal()`** (next to `run_rebase_rebump`). Reproduce the sub-procedure step 1–7 deterministic body for the step8 family by reusing existing helpers — `drop-bump-commit.sh`, `_run_rebase_rebump_verify_plain_no_push` (or the `--no-push --keep-on-conflict` vendor/waterfall variant already inside `run_rebase_rebump`), and `_run_rebase_rebump_from_step3` with `defer_push=true` so push stays owned by the force-push-gate. Failure routing is step8-family: hard failures call `exit_stall 8b` (stall → Step 18), not `exit_stall 10|12`; the same-version/`HAS_BUMP=false`/degraded-STATUS branches mirror Block β step8b handling. On a non-bump-only conflict, emit `emit_kv CONFLICT_FILES`, set `CALLER_KIND=ship_pr_pre_push`, `RESUME_PHASE=ship-pr-rrr-phase14-postbump`, `STALL_TRACKING=false`, then `exit 5` — do NOT call `exit_stall` (which emits exit code 4 and routes to Step 16, bypassing Phase 1–4); this mirrors the existing `step8b_rebase` exit-5 shape at lines ~1467–1469. Prefer factoring shared body out of `run_rebase_rebump` over copy-paste; a `phase`/`caller_family` parameter selecting the `exit_stall` target and push-deferral keeps one code path.
- **Rewrite the `conflict` arm of `run_bump_phase`** (lines ~1464–1473): replace `state_set_many RESUME_PHASE force-push-gate CALLER_KIND step8b_rebase` + `exit 5` with a call to `run_step8b_rebase_rebump_internal`; on success fall through to re-run the force-push-gate (re-invoke postbump with the `.postbump-phase=force-push-gate` checkpoint, i.e. `advance_phase bump` then loop, matching today's `--resume-phase force-push-gate` resume). Preserve `step8b_rebase` as a contract token in a comment (do not delete the name).
- **Extend the Exit-5 resume dispatch** (lines ~3764–3786): add a dedicated `ship-pr-rrr-phase14-postbump` resume token arm: when invoked with `--resume-phase ship-pr-rrr-phase14-postbump`, re-run the internal re-bump tail then the force-push-gate. Do NOT widen the `ship-pr-rrr-phase14` guard — its `ci-initial|ci-merge` check at lines ~3774–3776 must remain untouched; `ship-pr-rrr-phase14-postbump` is a separate dispatch arm that never enters the CI phase path.
- **Fold `CLONE_TAG_FULL` into argv-init**: when `--expected-tmpdir-basename-prefix` is absent, derive the prefix internally as `claude-implement-<CLONE_TAG_FULL>-`, where `CLONE_TAG_FULL` = `${CLONE_TAG:-$(basename "$PWD")}` sanitized via `tr -c 'A-Za-z0-9_-' '_'` and truncated to 32 chars (byte-identical to the current SKILL.md formula, incl. the `_` empty-fallback). Keep `--expected-tmpdir-basename-prefix` accepted as an explicit override. Preserve the existing CR/LF rejection (line ~3715).

### UPDATED: `scripts/ship-pr.md`
- Document `run_step8b_rebase_rebump_internal`, the new resume token/route, and the internal `CLONE_TAG_FULL` derivation under the existing argv-init / exit-code / resume-phase sections. Note `step8b_rebase` is now produced only as an internal marker (no `exit 5`), and `step8_apply_bump_same_version` `exit 5` is retired. Keep the `--expected-tmpdir-basename-prefix` override documented.

### UPDATED: `skills/implement/SKILL.md`
- Remove the inline `CLONE_TAG_FULL` block (lines ~1135–1143) and the `--expected-tmpdir-basename-prefix` argv line (line ~1152) from the Step 8+ `Invoke:` block; ship-pr.sh now derives it. If `CLONE_TAG` must reach ship-pr.sh, `export CLONE_TAG` in the Invoke block (see Edge cases) — otherwise rely on `basename "$PWD"`.
- Trim the Exit-5 handler (line ~1184): drop the `step8b_rebase`/`step8_apply_bump_same_version` → `rebase-rebump-subprocedure.md` branch (now internal). Keep the `ship_pr_pre_push` → `conflict-resolution.md` branch, and add the new postbump resume token to the "re-invoke `ship-pr.sh --resume-phase`" line.
- Update NEVER #8 and NEVER #15 prose that references the prompt-side step8b/step8_apply sub-procedure Skill path: note the step8 family is now script-internal (parallel to the existing 10/12 note). Do NOT delete the NEVER entries; reword to reflect internal ownership.

### UPDATED: `skills/implement/references/rebase-rebump-subprocedure.md`
- Retain. Update the **Consumer** header and the `step8b_rebase` / `step8_apply_bump_same_version` references to read "now handled internally by `ship-pr.sh`; retained for historical/contract reference," mirroring the existing 10/12 note. Do not delete sections.

### UPDATED: `skills/implement/references/bump-verification.md`
- Retain. Add a one-line note that Block β's step8b-family handling is now executed inside ship-pr.sh; Blocks α/γ remain live for Step 8's direct bump. No semantic edits to the matrices.

### UPDATED: `skills/implement/references/conflict-resolution.md`
- In the Phase 4 exit-0 handler (see line ~112): branch on `RESUME_PHASE` read from `ship-pr-state.sh`. If `RESUME_PHASE=ship-pr-rrr-phase14-postbump` (set by the step8b internal path), re-invoke `ship-pr.sh --resume-phase ship-pr-rrr-phase14-postbump`. Otherwise keep the existing `--resume-phase ship-pr-rrr-phase14` for `ci-initial|ci-merge` origins. Also update the consumer note at line ~16 to acknowledge the postbump resume variant.

### UPDATED: `scripts/test-ship-pr.sh`
- Assert the postbump-conflict path no longer `exit 5`s with `step8b_rebase`; it runs the internal rebase+re-bump and reaches the force-push-gate.
- Assert non-bump-only conflict emits exit rc=5 (not rc=4/`exit_stall`) with `CALLER_KIND=ship_pr_pre_push`, `RESUME_PHASE=ship-pr-rrr-phase14-postbump`, `STALL_TRACKING=false`, and `CONFLICT_FILES` on FD 3. Update any existing assertions that expected rc=4 for this path.
- Assert step8-family hard failures route to `exit_stall 8b` (stall → Step 18), not 10/12.
- Add argv-init coverage: internal `--expected-tmpdir-basename-prefix` derivation equals the legacy formula; explicit flag overrides; `CLONE_TAG` precedence; basename fallback; 32-char truncation; CR/LF rejection unchanged.

### UPDATED: `scripts/test-ship-pr-rebase-phase14.sh`
- Cover the new postbump force-push-gate resume route after a Phase 1–4 (`ship_pr_pre_push`) escape raised from the step8b path; assert the CI-phase `ship-pr-rrr-phase14` guard is unchanged.

### UPDATED: `scripts/test-implement-rebase-macro.sh`
- Update `step8b_rebase` token expectations to the internal-ownership shape; keep the contract-token presence assertions.

### Approach
- **Reuse, don't duplicate.** The deterministic drop/rebase/re-bump already lives in `run_rebase_rebump` + `_run_rebase_rebump_from_step3` + `_run_rebase_rebump_verify_plain_no_push`. Factor the shared body so the step8b path differs only in (a) `exit_stall` target (8b vs 10/12), (b) push deferral (force-push-gate owns the push), and (c) post-success continuation (force-push-gate vs `ci-wait`). Mirrors the existing 10/12 internalization.
- **Phase 1–4 stays prompt-side.** Non-bump conflicts emit `exit 5` (rc=5, `STALL_TRACKING=false`) with `CALLER_KIND=ship_pr_pre_push` and `RESUME_PHASE=ship-pr-rrr-phase14-postbump`. Phase 4 exit-0 reads `RESUME_PHASE` from state and re-invokes `ship-pr.sh --resume-phase ship-pr-rrr-phase14-postbump`, resuming the force-push-gate without entering the CI phase guard.
- **Idempotent resume.** The force-push-gate resume re-enters `run_bump_phase`; classify-bump returns `NONE` on an already-bumped HEAD (no double bump), then postbump reads `.postbump-phase=force-push-gate` and force-pushes. Preserve this existing resume contract.
- **CLONE_TAG_FULL** is a pure function of `${CLONE_TAG:-$(basename "$PWD")}`; ship-pr.sh runs in the clone cwd, so the derivation is local.

### Edge cases
- `--forked` target: `run_step8b_rebase` returns 2 (bail) on conflict, NOT 1 — internal path entered only for the non-forked `return 1` conflict. Preserve the forked bail.
- `repo_unavailable=true`: postbump returns 2 (bail); internal path not entered. Preserve.
- `SKIPPED_ALREADY_FRESH=true`: re-bump no-ops; force-push-gate still runs.
- `HAS_BUMP=false` (forked or no bump skill): classify yields `NONE`; rebase/force-push with no new bump commit. Preserve.
- Bump-only conflict (`plugin.json`/`CHANGELOG`): the deterministic pre-pass + `drop-bump-commit` removes the bump first; resolves without Phase 1–4. Preserve.
- `CLONE_TAG` visibility: if `/implement` sets `CLONE_TAG` as a non-exported shell var, ship-pr.sh falls back to `basename "$PWD"`. Verify the export at the call site; `export CLONE_TAG` in the SKILL.md Invoke block or keep passing the flag when `CLONE_TAG` is set. Default `basename "$PWD"` matches the historical else-branch.

### Failure modes
- **Resume routes to a CI phase with no PR (highest risk).** If Phase 4 exit-0 re-invokes `ship-pr-rrr-phase14` instead of `ship-pr-rrr-phase14-postbump`, resume hits `die_usage "... requires PHASE ci-initial or ci-merge"` or re-enters CI logic with no PR. Mitigation: the dedicated `ship-pr-rrr-phase14-postbump` arm never enters the `ci-initial|ci-merge` guard; Phase 4 reads `RESUME_PHASE` from state. Validated by `test-ship-pr-rebase-phase14.sh`.
- **Stale/double bump (Invariant #1).** Mis-wired push deferral or classify-NONE idempotency could force-push without a fresh bump. Signal: `check-bump-version --mode post` `VERIFIED=false`/`BUMP_TYPE=NONE`. Mitigation: keep `_run_rebase_rebump_from_step3`'s STATUS-first Block β gating and version-regression correction in the shared body; `defer_push=true` so force-push-gate owns the single push.
- **Failure-routing drift (Invariant #3).** A degraded-git failure calling `exit_stall 10|12` instead of `8b` bails to a nonexistent CI loop / 12d pre-PR. Mitigation: parameterize the `exit_stall` target by caller family; assert the 8b target in tests.

### Testing strategy
- Extend `test-ship-pr.sh`, `test-ship-pr-rebase-phase14.sh`, `test-implement-rebase-macro.sh` (internal step8b path, Phase 1–4 resume-to-force-push-gate, step8-family stall routing, CLONE_TAG_FULL argv-init).
- Re-run bump-verification regression coverage and `scripts/test-step2-dispatch.sh` to confirm no stale `step8b_rebase` exit-5 dispatch expectation remains.
- Run `bash scripts/relevant-checks.sh` (or `make lint`), `make lint-bash32`, and the script's harness via the Makefile targets.
- Keep edits disjoint from the parallel "Step 18" `ship-pr.sh` issue (single-writer to `ship-pr.sh`).

## Acceptance

- [ ] Postbump (`run_step8b_rebase`) conflict is handled **internally** in `ship-pr.sh` (new `run_step8b_rebase_rebump_internal`); `run_bump_phase` no longer `exit 5`s with `CALLER_KIND=step8b_rebase` to the prompt-side sub-procedure.
- [ ] On a non-bump-only conflict the internal path emits `exit 5` (rc=5, not `exit_stall`/rc=4) with `CALLER_KIND=ship_pr_pre_push`, `RESUME_PHASE=ship-pr-rrr-phase14-postbump`, `STALL_TRACKING=false`, and `CONFLICT_FILES` on FD 3.
- [ ] `conflict-resolution.md` Phase 4 exit-0 reads `RESUME_PHASE` from state and resumes via `--resume-phase ship-pr-rrr-phase14-postbump` back to the postbump force-push-gate; the existing `ship-pr-rrr-phase14` CI guard (`ci-initial|ci-merge`) is untouched.
- [ ] step8-family hard failures route to `exit_stall 8b` (stall → Step 18), never `exit_stall 10|12`.
- [ ] `CLONE_TAG_FULL` is derived inside `ship-pr.sh` argv-init (byte-identical to the old SKILL.md formula); `--expected-tmpdir-basename-prefix` remains an accepted optional override; CR/LF rejection preserved; the SKILL.md Step 8+ Invoke block no longer computes it inline.
- [ ] Dead `step8_apply_bump_same_version` exit-5 references are retired (SKILL.md exit-5 handler + any vestigial state set); the contract token name is preserved where it still marks internal state.
- [ ] `rebase-rebump-subprocedure.md` and `bump-verification.md` are retained with historical/internal-ownership notes (no section deletions); Blocks α/γ stay live for Step 8.
- [ ] Contract `caller_kind` tokens are not renamed; version-bump-freshness (Invariant #1) and degraded-git fail-closed (Invariant #3) are preserved.
- [ ] Tests updated and green: `test-ship-pr.sh`, `test-ship-pr-rebase-phase14.sh`, `test-implement-rebase-macro.sh`, bump-verification regression, `test-step2-dispatch.sh`; `make lint` and `make lint-bash32` pass.

diff_lines: 360
