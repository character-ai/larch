## Plan

### Summary

Move the `[DESIGNING]`→`[DESIGNED]` title rename in `skills/design/scripts/design-publish.sh` to right after the architecture-diagram upsert, and drop its `PUBLISH_OK==true` gate. The issue is admitted to `/implement` as soon as the plan + diagram are posted — it no longer waits on, and can no longer be blocked or delayed by, the design-log PR. The `design_reentry_marker_write` guard stays after publish, still gated on `PUBLISH_OK==true`.

SIMPLE-tier reorder inside one script, plus its contract, two test harnesses, and stale prose in three docs. No `/implement`, security, or publish-model change. No new flags, modes, or result-env keys.

New publish-tail order: `plan-block-write.sh` → `upsert-diagrams-comment.sh` → **rename `--state designed`** → `design-log-publish.sh` → `render-final-summary.sh --post-publish-only` → `design_reentry_marker_write`.

### Files to modify

**`skills/design/scripts/design-publish.sh`** (core)
- Lift the rename sub-block (`_rename_out=$(... tracking-issue-write.sh rename --issue "$ISSUE" --state designed ...)` plus its `RENAMED` / `_rename_seen` parse and the `if`/`else`) out of the `if [[ -n "$SESSION_ID" ]] && [[ "${PUBLISH_OK:-}" == true ]]; then ... fi` block.
- Insert it as a new block immediately after the `upsert-diagrams-comment.sh` block and before the `design-log-publish.sh` publish block, gated on `if [[ -n "$SESSION_ID" ]]; then ... fi` only (no `PUBLISH_OK`).
- Leave the reentry-marker sub-block (`source lib-design-reentry-guard.sh` + `design_reentry_marker_write` + `append-tool-failure.sh` handling) in place, still inside `if [[ -n "$SESSION_ID" ]] && [[ "${PUBLISH_OK:-}" == true ]]`. That block now holds only the marker logic.
- Update the rename-failure warn string: drop the now-inaccurate "and logs may have published" clause; keep the literal `[DESIGNED]` and `rename failed` tokens so the existing result-env regex assertion still matches.
- Preserve everything else byte-for-byte: `set +e`/`set -e` capture, `RENAMED=""` init, `write_result_env_and_emit`, exit codes, `${REPO:+--repo "$REPO"}` threading. Do NOT add result-env keys, exports, or a scrub preflight.

**`skills/design/scripts/design-publish.md`** (contract; also corrects pre-existing drift)
- Rewrite the "Ordering invariants" success line to the new order; drop the stale `--pre-publish-only` render step and the stale marker-before-upsert position (neither matches the code).
- Rename responsibilities item: runs right after diagram upsert, gated only on `SESSION_ID` (not `PUBLISH_OK`); Step 6 cleanup stays publish-gated outside the driver.
- Marker responsibilities item: correct "before publish/rename" to after publish, only when `SESSION_ID` non-empty and `PUBLISH_OK=true`.
- Publish responsibilities item: drop the stale `render-final-summary.sh --pre-publish-only` mention.
- Leave `Edit in sync`, `Exit codes`, `Result env`, `Migration limit` unchanged.

**`skills/design/scripts/test-design-publish.sh`** (harness)
- Happy-path ordering: change `plan→upsert→publish→rename→marker` to `plan→upsert→rename→publish→marker` (assert `plan < upsert < rename < publish < marker`); update the message.
- `PUBLISH_OK=false` case: flip the rename assertion — assert `tracking-issue-write` IS present in `RENAME_LOG` and `RENAMED=true` in the result env. Keep the marker assertion (still skipped on `PUBLISH_OK=false`).
- Unexpected-publish-rc and exit-0-without-`PUBLISH_OK=` cases: flip the rename assertion to assert the rename ran.
- Leave unchanged: `SESSION_ID`-empty → rename skipped; happy-path marker file exists; marker-failure non-blocking; exit-3 path; upsert/plan-block-write/render assertions.

**`scripts/test-design-structure.sh`** (structural pin)
- Add one assertion near check (25): `publish_upsert_line < publish_rename_line < publish_log_line` (rename after upsert, before publish).
- Do not edit existing (25) (`publish_log < marker`; `rename < marker`) or (15b) (`plan < upsert < log`) assertions — they stay true under the new order.

**`skills/design/SKILL.md`** (Step 5c prose)
- Item 6: state only Step 6 cleanup stays `PUBLISH_OK`-gated; the `[DESIGNED]` rename is no longer `PUBLISH_OK`-gated. Preserve the pinned substring `` : > "$DESIGN_TMPDIR/.completed/step-5c"` **only when** `PLAN_WRITE_OK=true` `` exactly.
- Item 4: reorder the responsibilities parenthetical to "(plan block write, diagrams upsert, `[DESIGNED]` rename, log publish, summary render, reentry marker)".
- Leave the Step 5d footer logic, warning-replay prose, and Step 6 cleanup gating unchanged.

**`scripts/implement-admission.md`** (1-line doc-accuracy fix)
- In the `missing-designed-prefix` recovery note, replace "it will rename the issue to `[DESIGNED]` on successful publish" with wording reflecting the new timing (e.g. "once the plan and architecture diagram are posted; the design-log PR may publish afterward"). Keep the rest, including the legacy `[PLANNED]` migration sentence.

**`skills/design/references/approval-gates.md`** (1-line doc-accuracy fix)
- In the Gate C "Approve final design" bullet, swap "run `design-log-publish.sh`, rename tracking issue" to "rename tracking issue, run `design-log-publish.sh`".

### Edge cases

- `SESSION_ID` empty (defensive; never hit in real runs): rename still skipped (keeps the `SESSION_ID` guard); marker still skipped. Matches today.
- Publish fails after a successful rename: issue is already `[DESIGNED]` with `larch:plan`; `RENAMED=true`; `SUMMARY_OUTCOME=failed-publish` and the "log publish incomplete" footer still fire; `/implement` can proceed. Intended.
- Rename fails (best-effort): warn emitted, run continues to publish as before; only the warn text changed.
- Spurious `/design` re-invocation after publish failure: no reentry marker written, but the already-`[DESIGNED]` title routes to the already-planned path — no protection gap.

### Failure modes

1. A test silently keeps the old order green — mitigated by the new structure pin + flipped harness assertions (both fail loudly if the rename drifts back behind publish).
2. Result-env regex drift — keep `[DESIGNED]` and `rename failed` literally in the new warn text.
3. SKILL.md structure-pin breakage — edit only the trailing rename/cleanup clause; preserve the `step-5c` sentinel substring.

## Acceptance

- `design-publish.sh` renames to `[DESIGNED]` after the diagram upsert and before `design-log-publish.sh`, gated only on `[ -n "$SESSION_ID" ]` (no `PUBLISH_OK` condition on the rename).
- The reentry-marker block remains after publish, still gated on `SESSION_ID` non-empty AND `PUBLISH_OK==true`.
- On a publish failure (`PUBLISH_OK=false`) with a non-empty `SESSION_ID`, the rename has already run: `RENAMED=true` appears in `.design-publish-result.env` and the issue title is `[DESIGNED]`.
- No `--scrub-only` mode, `ADMISSION_READY`/`RENAME_NOOP` keys, or other new result-env keys are introduced.
- `bash skills/design/scripts/test-design-publish.sh` passes: the happy-path ordering case asserts `plan→upsert→rename→publish→marker`, and the `PUBLISH_OK=false` / unexpected-rc / no-`PUBLISH_OK` cases assert the rename ran.
- `bash scripts/test-design-structure.sh` passes: the new `upsert < rename < publish_log` pin holds and the existing (15b)/(25) pins stay green.
- No stale ordering/gating prose remains: `design-publish.md`, SKILL.md Step 5c, `implement-admission.md` ("on successful publish" removed), and `approval-gates.md` (Gate C parenthetical reordered) reflect rename-before-publish.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes for the touched `.sh` / `.md` surfaces.

diff_lines: 95
