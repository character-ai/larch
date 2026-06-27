## Plan

## Scope inputs

- `approach-synthesis.txt` is `NO_SKETCHES`; draft from direct repo inspection.
- `discussion-round1.md` resolves all open questions.
- The approved outline is binding: change prompt/reference surfaces only. Do not change `python/ship.py`, `python/file_oos.py`, `oos-pipeline.md`, or `execution-issues-tracking.md` behavior.
- Direct inspection confirmed the current stale branch loads `execution-issues-tracking.md` and `oos-pipeline.md` in `skills/implement/SKILL.md`, and `ship.py` emits `needs_user_reason="oos-filing"` only for a non-empty `security-oos-observations.md` sidecar.

## Approach

1. Replace the Step 8+ `oos-pipeline` branch prose with the Python security-sidecar path:
   - Do not load `execution-issues-tracking.md`.
   - Do not load or run `oos-pipeline.md`.
   - State that `/issue` filing is forbidden for this path.
   - **Imperative private-disposition procedure** (relocated from `oos-pipeline.md` step 1 security-sidecar bullet): read `$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` `## Security Findings in OOS Workflows` private disclosure (no public `/issue`), and clear the sidecar only after private disposition completes.
   - Read `ship-pr-oos-checkpoint-router.md`, then invoke `step-8-oos-checkpoint.sh`.
   - Make clear the checkpoint should stall while `security-oos-observations.md` remains non-empty and private SECURITY.md disposition is pending.

2. Rewrite NEVER #14 and #15 so global rules match the Python split (accepted FINDING_2, FINDING_3):
   - NEVER #14 **How to apply**: non-security accepted OOS is filed by pre-driver `python/cli.py oos file` before `step-8-ship.sh` (bash `/issue` batch filing is legacy Step 9a.1 only). On `NEXT_ACTION=oos-pipeline`, perform SECURITY.md private disposition for `security-oos-observations.md` (read sidecar, follow `## Security Findings in OOS Workflows`, no public `/issue`, clear sidecar only after private disposition), then invoke `step-8-oos-checkpoint.sh` through the Step 8 checkpoint wrapper with **no** `/issue` call. Remove stale phrases **"After the OOS pipeline"** and any wording that implies running the dead OOS pipeline body on the Python security branch. Only checkpoint `NEXT_ACTION=reship` may write run statistics, stamp the manifest, and clear `OOS_PENDING=false`.
   - NEVER #15 **How to apply**: replace "immediately after the `/issue` pipeline" with "after security-sidecar disposition (when applicable) and before/at the Step 8 OOS checkpoint wrapper on the `oos-pipeline` branch, or after pre-driver `oos file` on the normal path." Keep the `OOS_PENDING` sentinel rationale; do not imply public issue filing on the security branch.

3. Keep the OOS checkpoint routing flow intact:
   - Preserve the existing `step-8-oos-checkpoint.sh` fence.
   - Preserve the distinction between OOS-checkpoint `NEXT_ACTION=stall` and post-driver `stall`.
   - Replace the OOS checkpoint fence intro **"run the OOS pipeline when needed"** with security-sidecar disposition language (private SECURITY.md flow, then checkpoint). The Python branch must never imply a public `/issue` batch or dead pipeline load.

4. Trim `ship-pr-exit-matrix.md` to branch-routing content only:
   - Update the `oos-pipeline` branch row to the security-sidecar stall path (no `execution-issues-tracking.md`, no `/issue` pipeline, include imperative read-sidecar / SECURITY.md private-disposition line).
   - Remove `## Transient retry authority`. Keep only the existing branch-semantics instruction that the orchestrator must not sleep on `RESHIP_DELAY_SECONDS`.
   - Remove `## OOS cap contract` entirely (cap authority stays in `oos-pipeline.md`, `execution-issues-tracking.md`, and `python/cli.py oos file` / `oos issue-cap`; do **not** relocate cap prose into the security-sidecar router).
   - Remove `## Bail-time steps_ran invariant` after relocating it to `write-final-report.md` (see item 6).
   - Remove `## Active driver ownership notes` after relocating its surviving sentences (see items 7–8).
   - Add a two-line `## Terminal manifest contract` pointer: terminal runs must leave explicit `steps_ran` via `python/cli.py final-report write`; full invariant lives in `write-final-report.md`.
   - Preserve the `complete`, `reship`, `ci-fix`, `operator-bail`, post-driver `stall`, and `tool-failure` branch meanings intact.

5. Update `ship-pr-oos-checkpoint-router.md` as checkpoint-only home:
   - Adjust `Consumer` / `When to load` text so it no longer assumes an OOS pipeline body just ran.
   - Add a short security-sidecar subsection:
     - `security-oos-observations.md` is private-disposition material;
     - **Imperative**: read `$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` `## Security Findings in OOS Workflows` private disclosure (no public `/issue`), and clear the sidecar only after private disposition;
     - public `/issue` filing is forbidden;
     - checkpoint stall is expected until SECURITY.md disposition clears the sidecar.
   - Add one sentence: OOS issue-cap enforcement applies only on the pre-driver `python/cli.py oos file` path for non-security OOS; this branch does not run cap or `/issue --input-file` batch emission.
   - Do **not** add `## OOS cap contract` or bail-time `steps_ran` invariant sections (accepted FINDING_3, 5, 6, 8).
   - Preserve existing checkpoint rc and bookkeeping semantics.

6. Relocate bail-time `steps_ran` invariant to a ship-wide terminal reference (accepted FINDING_3):
   - Move the verbatim `## Bail-time steps_ran invariant` body from `ship-pr-exit-matrix.md` into `skills/implement/scripts/write-final-report.md` as a new section documenting the `python/cli.py final-report write` / `run-log manifest` contract.
   - Rely on existing `python/test_write-final-report.sh` / `test-write-final-report.sh` coverage for stamping behavior; do not duplicate the full block into the OOS router.

7. Relocate surviving active-driver notes without retaining the section header (accepted FINDING_7):
   - Move the Exit-4 `conflict-resolution.md` mandatory-read instruction into the SKILL.md post-driver `stall` branch (`RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`).
   - Move only the `python/cli.py pr checks` diagnostic fallback sentence into the `operator-bail` branch bullet in `ship-pr-exit-matrix.md` `## Branch semantics` (when CI failure metadata lacks `failed_run_id`).
   - Drop `finalize-state.sh`, `ci-merge`, and other ownership prose already covered elsewhere.

8. Integrate empty-`FAILED_RUN_ID` branch into `ship-pr-ci-fix.md` numbered procedure (accepted FINDING_4):
   - After step 1 `FAILED_RUN_ID` read, add step 1b (or renumber): when `FAILED_RUN_ID` is empty, run `python/cli.py pr checks` as the fallback diagnostic path, then route to `operator-bail` or post-driver `stall`; **skip steps 3–12** (no empty-run-id sentinel, `gh run-logs`, autonomous repair, commit, push, or ship re-entry).
   - Do not retain this sentence under deleted active-driver notes.
   - Pin the empty-`FAILED_RUN_ID` early-exit branch in `test-implement-structure.sh` near the existing `FAILED_RUN_ID` needle.

9. Update structural pins in `scripts/test-implement-structure.sh`:
   - Stop requiring `ship-pr-net-retries-python.count`, `steps_ran.step9a1`, `oos issue-cap`, and `finalize-state.sh` inside `ship-pr-exit-matrix.md`.
   - Forbid matrix retention of `## Transient retry authority`, `## OOS cap contract`, `## Bail-time steps_ran invariant`, and `## Active driver ownership notes`.
   - Require the slim `## Terminal manifest contract` pointer and operator-bail `pr checks` fallback in the matrix.
   - Forbid `/issue` pipeline wording in SKILL `oos-pipeline` branch, OOS checkpoint intro, NEVER #14/#15, and router security-sidecar section.
   - **Forbid stale non-`/issue` pipeline steering** (FINDING_3): `After the OOS pipeline`, `run the OOS pipeline when needed`, and similar dead-pipeline phrasing in SKILL NEVER #14/#15 and OOS checkpoint intro.
   - **Require** NEVER #14/#15 Python split pins: `pre-driver` + `python/cli.py oos file`, security-sidecar disposition on `oos-pipeline`, and explicit no `/issue` on the security branch.
   - Forbid `oos issue-cap`, `/issue --input-file`, and bail-time `steps_ran` section headers in `ship-pr-oos-checkpoint-router.md`.
   - **Require** security-sidecar imperative disposition pins in router and SKILL: `security-oos-observations.md`, `SECURITY.md` `## Security Findings in OOS Workflows`, and clear-sidecar-only-after-private-disposition wording (FINDING_2).
   - Require bail-time `steps_ran` invariant content in `write-final-report.md`.
   - Require `pr checks` fallback and empty-`FAILED_RUN_ID` skip-steps-3–12 branch in `ship-pr-ci-fix.md` near `FAILED_RUN_ID`.
   - Update SKILL branch pins: security-sidecar route, no `oos-pipeline.md` / `execution-issues-tracking.md` load on `oos-pipeline`, router read before checkpoint fence.
   - Add pin for phase14 `conflict-resolution.md` mandatory read in SKILL post-driver `stall`.
   - Remove `require_near(skill, 'oos-pipeline.md', ...)` and similar stale OOS-pipeline load pins.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

- Update the index-only reachability note around `execution-issues-tracking.md` so Step 8 `oos-pipeline` is no longer named as a load site.
- Rewrite NEVER #14 and #15 per Approach item 2 (Python split; remove **"After the OOS pipeline"**; require pre-driver `oos file` + security-sidecar disposition; no stale `/issue` pipeline steering on the security branch).
- Replace the `oos-pipeline` branch skeleton with slim security-sidecar handling:
  - mention `security-oos-observations.md`;
  - **imperative**: read the sidecar, follow `SECURITY.md` `## Security Findings in OOS Workflows` private disclosure (no public `/issue`), clear sidecar only after private disposition;
  - forbid `/issue` for this branch;
  - read `ship-pr-oos-checkpoint-router.md`;
  - proceed to the checkpoint fence.
- Update the OOS checkpoint fence intro: remove **"run the OOS pipeline when needed"**; state security-sidecar disposition then checkpoint only.
- In the post-driver `stall` branch, add a mandatory read of `conflict-resolution.md` when `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

- Rewrite the `oos-pipeline` branch semantics to the security-sidecar path (no tracking ref, no `/issue` pipeline; include imperative private-disposition line).
- Delete `## Transient retry authority`.
- Delete `## OOS cap contract` (do not relocate to router).
- Delete `## Bail-time steps_ran invariant` after moving body to `write-final-report.md`.
- Add slim `## Terminal manifest contract` pointer to `write-final-report.md`.
- Delete `## Active driver ownership notes`; add `pr checks` fallback to `operator-bail` branch bullet only.
- Keep the `complete`, `reship`, `ci-fix`, `operator-bail`, post-driver `stall`, and `tool-failure` branch meanings intact.

### UPDATED: skills/implement/references/ship-pr-oos-checkpoint-router.md

- Broaden consumer/load text to cover the Python security-sidecar branch (no prior OOS pipeline body).
- Add security-sidecar subsection (private disposition imperative, forbid `/issue`, stall until sidecar clears).
- Add one-sentence cap authority pointer to pre-driver `oos file` only.
- Do **not** add moved OOS cap or bail-time `steps_ran` sections.
- Preserve existing checkpoint rc and bookkeeping semantics.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md

- After step 1 `FAILED_RUN_ID` read, add an explicit empty-`FAILED_RUN_ID` branch: run `python/cli.py pr checks`, route to `operator-bail` or stall, skip steps 3–12 autonomous repair and log capture (integrate into numbered procedure, not a dangling sentence).

### UPDATED: skills/implement/scripts/write-final-report.md

- Add relocated `## Bail-time steps_ran invariant` section (verbatim from current matrix) documenting explicit `steps_ran.step9a1=false` / `step8` / `step7a` stamping and verify-completeness expectations for terminal non-merge outcomes.

### UPDATED: scripts/test-implement-structure.sh

- Update matrix pins for slimmer `ship-pr-exit-matrix.md` (removed sections, terminal pointer, operator-bail `pr checks`).
- Add forbids for removed matrix sections and stale `/issue` / dead-pipeline / NEVER pipeline wording (`After the OOS pipeline`, `run the OOS pipeline when needed`).
- Add router forbids for OOS cap and bail-time invariant headers; require security-sidecar imperative disposition content only.
- Require bail-time invariant in `write-final-report.md`.
- Require `pr checks` fallback and empty-`FAILED_RUN_ID` early-exit branch in `ship-pr-ci-fix.md`.
- Update SKILL branch pins for security-sidecar route, NEVER #14/#15 split, and phase14 conflict-resolution mandatory read.
- Remove stale `oos-pipeline.md` load proximity pins.

## Edge cases

- Non-security accepted OOS remains on the Python pre-driver `python/cli.py oos file` path. Do not reroute it through prompt prose or the security-sidecar branch.
- Security-routed OOS must not become a public GitHub issue through `/issue`; operators must have the imperative SECURITY.md private-disposition steps, not stall-with-no-procedure.
- OOS-checkpoint stall is not the same as post-driver stall. Do not send it to Step 16.
- Phase14 pre-push conflict resolution must remain reachable after trimming active-driver notes from the matrix.
- `execution-issues-tracking.md` may still reference `oos-pipeline.md` for bash-path Step 9a.1 prose. Do not remove those cross-references.
- Runs that bail before `NEXT_ACTION=oos-pipeline` still need the `steps_ran` contract via the every-ship matrix load pointer plus `write-final-report.md` / Python stamping, not via the OOS router.
- `NEXT_ACTION=ci-fix` with empty `FAILED_RUN_ID` must not run steps 3–12 with an empty run id; use `pr checks` then operator-bail or stall.

## Failure modes

- If NEVER #14/#15 still say **"After the OOS pipeline"** or the checkpoint intro still says **"run the OOS pipeline when needed,"** the orchestrator can steer toward dead bash filing or dead pipeline loads on the security branch.
- If the security-sidecar subsection omits the imperative read-sidecar / SECURITY.md private-disposition steps, rare `oos-filing` stalls have no operator procedure.
- If OOS cap or `/issue` batch prose lands in the security-sidecar router, contradictory instructions return on rare security stalls.
- If bail-time `steps_ran` moves only into the OOS router, pre-OOS bail paths lose the prompt-side audit reminder.
- If the `pr checks` / empty-`FAILED_RUN_ID` fallback is deleted or left as a dangling sentence without a numbered early-exit branch, operator-bail and ci-fix lose the only documented CI diagnostic path or run empty `gh run-logs`.
- If tests still require old matrix needles (`oos issue-cap`, full `steps_ran` block in matrix), `make test-implement-structure` will fail after the intended trim.

## Testing strategy

- Run `make test-implement-structure`.
- Run `make test-references-headers` if reference headers change.
- Run `make test-write-final-report` if `write-final-report.md` contract text changes warrant harness alignment.
- Grep-check the final tree:
  - `skills/implement/SKILL.md` `oos-pipeline` branch and NEVER #14/#15 do not steer to `/issue` or dead pipeline phrasing on the security path.
  - `ship-pr-exit-matrix.md` does not contain removed section headers; `operator-bail` mentions `pr checks` fallback.
  - `ship-pr-oos-checkpoint-router.md` has security-sidecar imperative disposition rules but no OOS cap section or bail-time invariant header.
  - `write-final-report.md` contains the relocated bail-time `steps_ran` invariant.
  - `ship-pr-ci-fix.md` contains empty-`FAILED_RUN_ID` → `pr checks` → skip-steps-3–12 branch integrated into numbered steps.
  - `conflict-resolution.md` remains named in the SKILL post-driver `stall` path.

## Acceptance

- Run `make test-implement-structure`.
- Run `make test-references-headers` if reference headers change.
- Run `make test-write-final-report` if `write-final-report.md` contract text changes warrant harness alignment.
- Grep-check the final tree:
  - `skills/implement/SKILL.md` `oos-pipeline` branch and NEVER #14/#15 do not steer to `/issue` or dead pipeline phrasing on the security path.
  - `ship-pr-exit-matrix.md` does not contain removed section headers; `operator-bail` mentions `pr checks` fallback.
  - `ship-pr-oos-checkpoint-router.md` has security-sidecar imperative disposition rules but no OOS cap section or bail-time invariant header.
  - `write-final-report.md` contains the relocated bail-time `steps_ran` invariant.
  - `ship-pr-ci-fix.md` contains empty-`FAILED_RUN_ID` → `pr checks` → skip-steps-3–12 branch integrated into numbered steps.
  - `conflict-resolution.md` remains named in the SKILL post-driver `stall` path.

review_status: complete
rounds_completed: 3
diff_added: 78
diff_deleted: 62
mechanical_churn: false
diff_lines: 140
