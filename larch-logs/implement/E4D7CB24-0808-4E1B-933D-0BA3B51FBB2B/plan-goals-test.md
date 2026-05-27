## Goal
Implement issue #2975: [IMPLEMENTING] When starting, /design and /implement should change issue title bracketed status prefix ASAP, immediately after verifying it's eligible to be worked on\n\nIf, for some reason, they later discover they can't work on it, they should reset it to the original value..

## Implementation Plan
## Plan

This is a SIMPLE-tier design. The smallest change that achieves the goal is a pure call-site relocation of an existing helper inside `phase_tracking` of `scripts/implement-bootstrap.sh`, plus contract-doc updates in two markdown files and test-harness updates in one file. No new states, no new helpers, no new admission paths.

### Files to modify/create

### UPDATED: `scripts/implement-bootstrap.sh`

Move the `rename_to_implementing` call site inside `phase_tracking` so the `[IMPLEMENTING]` title rename fires immediately after the validation that determines the issue is eligible to be worked on, BEFORE any larch-logs writes or GitHub adoption comment posting. Apply to both Branch 1 resume and Branch 2 adopt.

**Branch 1 resume (currently lines ~609-616):**

Current ordering:
```
BRANCH_SELECTED=branch-1-resume
ISSUE_NUMBER_RESOLVED=$sentinel_issue
RUN_ID=$sentinel_run_id
run_larch_log_init "$ISSUE_NUMBER_RESOLVED" "$RUN_ID" "Branch 1 resume" || return 0
rename_to_implementing "$ISSUE_NUMBER_RESOLVED" "Branch 1 resume"
emit_tracking_breadcrumb_if_enabled
return 0
```

New ordering: move `rename_to_implementing` to fire immediately after the sentinel-validation chain establishes `BRANCH_SELECTED=branch-1-resume`, `ISSUE_NUMBER_RESOLVED`, and `RUN_ID`. The rename runs before `run_larch_log_init`.

```
BRANCH_SELECTED=branch-1-resume
ISSUE_NUMBER_RESOLVED=$sentinel_issue
RUN_ID=$sentinel_run_id
rename_to_implementing "$ISSUE_NUMBER_RESOLVED" "Branch 1 resume"
run_larch_log_init "$ISSUE_NUMBER_RESOLVED" "$RUN_ID" "Branch 1 resume" || return 0
emit_tracking_breadcrumb_if_enabled
return 0
```

**Branch 2 adopt (currently lines ~640-679):**

The `get-issue-state.sh` block validates `STATE=OPEN` / `IS_PR=false`. Right after validation passes and `BRANCH_SELECTED=branch-2-adopt` + `ISSUE_NUMBER_RESOLVED=$ISSUE_NUMBER_OPT` are set, fire `rename_to_implementing` BEFORE `resolve_run_id`, `run_larch_log_init`, and `post-tracking-issue.sh`. Delete the late call near the end of the function.

Current tail of Branch 2 adopt:
```
BRANCH_SELECTED=branch-2-adopt
ISSUE_NUMBER_RESOLVED=$ISSUE_NUMBER_OPT
if ! RUN_ID=$(resolve_run_id); then
    tracking_init_failed
    return 0
fi
run_larch_log_init "$ISSUE_NUMBER_RESOLVED" "$RUN_ID" "Branch 2 adopt" || return 0
post_out=$("$CLAUDE_PLUGIN_ROOT/skills/implement/scripts/post-tracking-issue.sh" ...)
post_rc=$?
posted=$(kv_value_from_block POSTED "$post_out")
if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]; then
    DEFERRED=true
    rm -f "$sentinel"
    return 0
fi

rename_to_implementing "$ISSUE_NUMBER_RESOLVED" "Branch 2 adopt"
emit_tracking_breadcrumb_if_enabled
return 0
```

New tail:
```
BRANCH_SELECTED=branch-2-adopt
ISSUE_NUMBER_RESOLVED=$ISSUE_NUMBER_OPT
rename_to_implementing "$ISSUE_NUMBER_RESOLVED" "Branch 2 adopt"
if ! RUN_ID=$(resolve_run_id); then
    tracking_init_failed
    return 0
fi
run_larch_log_init "$ISSUE_NUMBER_RESOLVED" "$RUN_ID" "Branch 2 adopt" || return 0
post_out=$("$CLAUDE_PLUGIN_ROOT/skills/implement/scripts/post-tracking-issue.sh" ...)
post_rc=$?
posted=$(kv_value_from_block POSTED "$post_out")
if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]; then
    DEFERRED=true
    rm -f "$sentinel"
    return 0
fi

emit_tracking_breadcrumb_if_enabled
return 0
```

The deleted late call is replaced by the new early call. `tracking-issue-write.sh rename --state implementing` is idempotent (strip-one-prefix-and-prepend), so even if a future path were to call it twice, the second call is a no-op.

### UPDATED: `skills/implement/SKILL.md` — Bootstrap behavior map (rows 701-702)

Update the table rows that document Branch 2 ordering and the POSTED=false defer behavior. The old rows are now stale relative to the relocated rename.

**Row 701 (Branch 2 open issue) — current:**

```
| Branch 2 open issue | `get-issue-state.sh`, derive `RUN_ID` (`--run-id` > `session-id` > `LARCH_TOKEN_SESSION_ID`), `larch-log.sh init`, `post-tracking-issue.sh --run-id "$RUN_ID"`, best-effort implementing rename. | Continue with `BRANCH_SELECTED=branch-2-adopt`. |
```

**Row 701 — new:**

```
| Branch 2 open issue | `get-issue-state.sh`, best-effort implementing rename, derive `RUN_ID` (`--run-id` > `session-id` > `LARCH_TOKEN_SESSION_ID`), `larch-log.sh init`, `post-tracking-issue.sh --run-id "$RUN_ID"`. | Continue with `BRANCH_SELECTED=branch-2-adopt`. |
```

**Row 702 (Branch 2 POSTED=false) — current:**

```
| Branch 2 metadata post returns `POSTED=false` | No sentinel, no rename, `DEFERRED=true`, exit 0. | Continue to plan materialization; summary publication is deferred by construction. |
```

**Row 702 — new:**

```
| Branch 2 metadata post returns `POSTED=false` | No sentinel, rename already attempted before `post-tracking-issue.sh`, `DEFERRED=true`, exit 0. Title is `[IMPLEMENTING]` even though sentinel was never written; see Edge cases in #2975's design for the admission-retry implication. | Continue to plan materialization; summary publication is deferred by construction. |
```

No other SKILL.md edits needed. The "Resume safety net" paragraph below the table already says Branch 1 always re-runs rename — that remains true under the new ordering and is still load-bearing.

### UPDATED: `scripts/implement-bootstrap.md` — clarify POSTED=false ordering

Update the existing prose about `DEFERRED=true paths such as forked targets and POSTED=false metadata defers` (around line 97) so it reflects that the rename has already fired before the `POSTED=false` defer is recorded. Smallest fix is a parenthetical clarification:

Current:
```
Phase 3 uses permissive `should_run_phase_plan_materialize`: it runs when there is no bail reason, no stall, and the repo is available. This intentionally allows `DEFERRED=true` paths such as forked targets and `POSTED=false` metadata defers so Step 2 still receives `feature-description.txt` and `plan.txt`.
```

New:
```
Phase 3 uses permissive `should_run_phase_plan_materialize`: it runs when there is no bail reason, no stall, and the repo is available. This intentionally allows `DEFERRED=true` paths such as forked targets and `POSTED=false` metadata defers (the implementing rename has already fired before `post-tracking-issue.sh` so the title visibly reflects in-progress status even on defer) so Step 2 still receives `feature-description.txt` and `plan.txt`.
```

No other line in `implement-bootstrap.md` materially asserts the old rename ordering; line 113 ("Rename to `[IMPLEMENTING]` | Best-effort inside `phase_tracking` Branch 1 and Branch 2") remains correct.

### UPDATED: `skills/implement/scripts/test-implement-bootstrap.sh`

Three assertion changes — one flip (B4) and two additions (B4-plan, B4-all):

**B4 (line ~741, POSTED=false deferred):** the current assertion `assert_not_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4 no rename"` is now incorrect — the rename fires before `post-tracking-issue.sh` so the POSTED=false invoke log contains it. Flip to:

```
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4 rename fires before post-tracking-issue"
```

Also update the case-header comment that describes the old behavior, if present.

**B4-plan (line ~763, POSTED=false deferred guard at plan phase):** add an `assert_contains` for the rename invocation. Locate the variant's invoke-log read after `run_bootstrap --up-to-phase plan ... LARCH_TEST_POSTED=false ...`. Add:

```
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4-plan rename fires before post-tracking-issue"
```

**B4-all (line ~794, POSTED=false deferred guard for the `--up-to-phase all` end-to-end flow):** add the same assertion as B4-plan, scoped to the B4-all variant's invoke log:

```
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4-all rename fires before post-tracking-issue"
```

`GP-adopt-rename-fail` (lines ~1475-1483) and `GP2-rename-fail` (lines ~1485-1493) continue to pass without modification — they assert the rename was attempted and that a failing rename ends up in `execution-issues.md` under the Branch 2 / Branch 1 adoption site. Both remain true after the relocation.

`B4-plan-dirty-resume` (line ~1079) is unrelated to this change — review during implementation but no change expected; it tests a resume path, not the POSTED=false adoption path.

### Approach

- **Strategy**: pure call-site relocation of the existing `rename_to_implementing` helper inside `phase_tracking`. The helper body, exit-code handling, `IMPLEMENT_TMPDIR/tracking-rename.stderr.log` capture path, and `tracking-issue-write.sh` invocation are unchanged.
- **Why no new helper**: the existing helper already does exactly what we need; we are only changing *when* it fires.
- **Why no new state in `tracking-issue-write.sh`**: the `implementing` state and the strip-one-prefix-then-prepend rename semantics already produce the correct `[DESIGNED] foo` → `[IMPLEMENTING] foo` swap.
- **Why no admission carve-out in `implement-admission.sh`**: the user has explicitly accepted a "no reset, no rollback" posture; addressing the FINDING_2 admission-retry concern via documentation + operator workaround keeps the change minimal and avoids touching a security-sensitive admission surface. See Edge cases below.
- **Why no `/design` change**: the user has decided the current Step 0b sub-step 5.5 rename position in `/design` is acceptable.

### Edge cases

- **Idempotent rename on resume**: Branch 1 resume re-runs the rename on a title that is already `[IMPLEMENTING]`. `tracking-issue-write.sh rename` is idempotent in this case (strips the existing `[IMPLEMENTING] ` prefix and re-prepends it, ending up with the same title); `RENAMED=false` is treated as idempotent success by the helper's caller.
- **`get-issue-state.sh` already validated `OPEN`/`!IS_PR`**: when execution reaches the new rename site for Branch 2 adopt, `issue_state` is `OPEN` and `issue_is_pr` is `false`. No additional validation is needed at the rename site.
- **Preflight admission already enforced `[DESIGNED]`**: by the time `phase_tracking` Branch 2 adopt runs, `implement-admission.sh` has already rejected `[IMPLEMENTING]` / `[DESIGNING]` / `[DONE]` and required `[DESIGNED]`. The rename from `[DESIGNED] foo` to `[IMPLEMENTING] foo` is a clean prefix swap.
- **`resolve_run_id` failure (rare)**: rename has happened; `tracking_init_failed` sets `IMPLEMENT_BAIL_REASON=tracking-init-failed` and `STALL_TRACKING=true`. Title is `[IMPLEMENTING]`. Per user, acceptable.
- **`run_larch_log_init` failure**: rename has happened; function returns 0 without setting BAIL_REASON. Title is `[IMPLEMENTING]`. Per user, acceptable.
- **`post-tracking-issue.sh` POSTED=false (B4 test case)**: rename has happened; `DEFERRED=true`, sentinel removed, function returns. Title is `[IMPLEMENTING]`. Per user, acceptable. Test assertion flips (see Testing strategy).
- **POSTED=false defer + fresh `/implement` retry (FINDING_2 admission-block scenario)**: when `post-tracking-issue.sh` fails (POSTED=false), `parent-issue.md` was never written so a later `/implement` cannot match by sentinel. The issue title is now `[IMPLEMENTING]`, which `implement-admission.sh` rejects via the managed-prefix check (exit 5). Two operator workarounds preserve retryability without code changes:
  1. **Preserve `$IMPLEMENT_TMPDIR` and re-enter via `--resume-plan-tail`**: the helper writes `parent-issue.md` only on successful post-tracking, so this workaround applies only when the operator manually writes the sentinel from the preserved tmpdir's known `ISSUE_NUMBER` / `RUN_ID`, or when the failed post-tracking eventually succeeds and the operator retries.
  2. **Manual title revert**: from the GitHub UI or via `gh issue edit <N> --title "<original>"`, strip the `[IMPLEMENTING] ` prefix and re-run `/implement` fresh.

  This regression is documented and accepted as a known trade-off of the "rename ASAP after eligibility" directive. The alternative (admission carve-out) was considered and rejected as out-of-scope for a SIMPLE-tier change to a security-sensitive admission surface.
- **Resume-plan-tail short-circuits (lines ~559, ~573)**: these paths return 0 without calling rename today; that remains correct — they assume the title was already renamed in the original adoption run.

### Failure modes

1. **Stale documentation in unsurveyed contract files**: any other contract/SKILL.md/sibling `.md` file that explicitly states the rename happens "after `post-tracking-issue.sh`" is now incorrect. Earliest signal: `make lint` or a contract-doc grep during plan-review/post-merge audit. Mitigation: grep for `rename.*implementing.*after|after.*rename.*implementing|no rename|stalled rename|post-tracking.*rename` across `scripts/*.md`, `skills/implement/**/*.md`, and `docs/` during implementation; update any matches in the same PR.
2. **POSTED=false admission-block becomes a recurring support burden**: if operators frequently hit `post-tracking-issue.sh` failures, the manual-revert workaround above becomes friction. Earliest signal: repeated user reports of "exit 5 managed-prefix" after a previous defer. Mitigation: separate follow-up issue can add an admission carve-out if the friction is observed in practice; not in scope for #2975.
3. **Hidden test fixtures asserting call order in invoke-log.txt**: a test other than B4 might assert ordering implicitly (e.g., `assert_contains` on a concatenated snippet that spans rename+post-tracking). Earliest signal: `test-implement-bootstrap.sh` failure on an un-named test case after the move. Mitigation: run the full harness once after editing and flip any other ordering-sensitive assertions.

### Testing strategy

- **B4 assertion flip** as described above.
- **B4-plan and B4-all positive rename assertions** as described above (FINDING_3).
- Run `bash skills/implement/scripts/test-implement-bootstrap.sh` and confirm all cases pass.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) to exercise pre-commit hooks repo-wide.
- No new test cases needed beyond the three above — existing GP-adopt-rename-fail and GP2-rename-fail already cover the rename's interaction with failure paths; their semantics remain correct under the new ordering.
- No SKILL.md prose changes beyond rows 701-702 are expected; if `make lint` flags stale prose elsewhere, fix it in the same PR.

diff_lines: 35

## Acceptance

- `scripts/implement-bootstrap.sh` `phase_tracking` Branch 1 resume invokes `rename_to_implementing` immediately after `ISSUE_NUMBER_RESOLVED` and `RUN_ID` are set from the sentinel, before `run_larch_log_init`.
- `scripts/implement-bootstrap.sh` `phase_tracking` Branch 2 adopt invokes `rename_to_implementing` immediately after `get-issue-state.sh` validates `STATE=OPEN` and `IS_PR=false` and `BRANCH_SELECTED=branch-2-adopt` / `ISSUE_NUMBER_RESOLVED` are set, before `resolve_run_id`, `run_larch_log_init`, and `post-tracking-issue.sh`.
- The late `rename_to_implementing` call at the tail of `phase_tracking` Branch 2 adopt is removed.
- `skills/implement/SKILL.md` Bootstrap behavior table rows for "Branch 2 open issue" and "Branch 2 metadata post returns `POSTED=false`" are updated to reflect the new ordering.
- `scripts/implement-bootstrap.md` POSTED=false defer prose includes a parenthetical noting the rename has already fired before the defer is recorded.
- `skills/implement/scripts/test-implement-bootstrap.sh`: the B4 case asserts the rename invocation IS present in the invoke log (the prior `assert_not_contains` is flipped to `assert_contains`); B4-plan and B4-all gain new positive `assert_contains` checks for `tracking-issue-write rename --issue 123 --state implementing`.
- `bash skills/implement/scripts/test-implement-bootstrap.sh` passes end-to-end (including the GP-adopt-rename-fail and GP2-rename-fail cases without modification).
- `make lint` (`bash scripts/relevant-checks.sh`) passes.

diff_lines: 35

## Test plan
(no test plan section in plan-file)
