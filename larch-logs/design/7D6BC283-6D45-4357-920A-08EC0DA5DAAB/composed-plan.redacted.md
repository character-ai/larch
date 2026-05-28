## Plan

### UPDATED: `scripts/implement-bootstrap.md`

Add a new subsection `## Resume-tail idempotency` documenting the audit findings for `phase_plan_materialize` lines ~750-911 on `--resume-plan-tail` re-entry.

- State the load-bearing invariant: `run_dirty_tree_checkpoint` runs at the top of `phase_plan_materialize` after the resume-skip block; on the canonical dirty-tree-then-resume sequence, the first pass bails at this checkpoint (sets `IMPLEMENT_BAIL_REASON=dirty-tree` and returns 0) **before** any helper at lines 754-911 runs. So those unguarded helpers always execute exactly once across the dirty-tree-then-resume sequence, not twice.
- Enumerate each helper called after the dirty-tree checkpoint with its idempotency property even if it did re-run:
  - `create-branch.sh --branch <name>` (line ~765): NOT idempotent in isolation — exits 1 with "ERROR: Branch already exists" if the branch exists. Safe only because the first-pass bail prevents this line from running twice on the canonical flow.
  - `git-current-branch.sh` (line ~775): read-only, idempotent.
  - `redact-secrets.sh | redact-tmpdir-paths.sh` pipelines (lines ~795, ~842, ~882): read-only filter pipelines that produce stable output from stable input. Safe to re-run.
  - `run-step1-plan-log.sh` write (line ~809): writes under `$IMPLEMENT_TMPDIR/larch-logs/`, session-scoped tmpdir, idempotent within the same tmpdir.
  - `write-tally.sh --phase plan-review` (line ~846): same session tmpdir, atomic compose+write of a tally batch; idempotent within the same tmpdir.
  - `tracking-issue-summary.sh upsert-summary --marker "<!-- larch:plan v1 runid=$RUN_ID -->"` (line ~894): marker-based upsert, idempotent by construction — finds the existing marker and replaces the comment.
  - `append-tool-failure.sh` calls (lines ~799, ~812, ~826, ~860, ~883, ~897): all failure-only paths gated on the helper above them returning non-zero. NOT independently idempotent if forced to re-run (each call appends a new entry to `execution-issues.md`), but on the canonical flow each fires at most once because the gating helpers are themselves idempotent and the first-pass bail prevents the surrounding block from running twice. If a future change makes any of these failure paths reachable on resume, the audit must be revisited.
  - `emit_plan_materialize_breadcrumbs_if_enabled` (line ~910): conditional breadcrumb emitter at function tail; reads env state, emits only when enabled. Safe to re-run.
- Cross-reference `phase_tracking` early-return at lines 540-582: on `RESUME_PLAN_TAIL=true`, `phase_tracking` short-circuits before `rename_to_implementing`, `run_larch_log_init`, or `post-tracking-issue.sh` could re-run, so the duplicate tracking metadata concern in issue #2977 is already mitigated there.
- Note that the audit covers the canonical "dirty-tree bail → single resume" sequence (the path exercised by `test-implement-bootstrap.sh` case B7-plan-dirty-tree resume tail). Multi-resume sequences (resume → dirty-tree → resume again) are out of scope.

### UPDATED: `scripts/test-implement-structure.sh`

Extend the dirty-tree recovery contract pins near lines 419-450:

- `grep -Fq` assertion that `scripts/implement-bootstrap.md` contains the literal substring `Resume-tail idempotency`. Failure message: `implement-bootstrap.md must document resume-tail idempotency invariant`.
- `grep -Fq` assertion that the same file contains the literal substring `the first pass bails at this checkpoint`. Failure message: `implement-bootstrap.md must pin the dirty-tree first-pass-bail-before-helpers invariant`.
- Args-contract pins ensuring both bootstrap calls in `SKILL.md` Step 0 thread the full propagation surface. Mirror the existing `_ib_preflight` count-at-least-2 pattern at lines 416-417 for each of the other four expansion tokens:
  - `_ib_caller_env` — count of the exact expansion literal currently in `SKILL.md` is **>= 2**, failure message `SKILL.md must expand _ib_caller_env in both bootstrap invocations`.
  - `_ib_issue` — same count-at-least-2 pattern, failure message `SKILL.md must expand _ib_issue in both bootstrap invocations`.
  - `_ib_fork` — same count-at-least-2 pattern, failure message `SKILL.md must expand _ib_fork in both bootstrap invocations`.
  - `_ib_run_id` — same count-at-least-2 pattern, failure message `SKILL.md must expand _ib_run_id in both bootstrap invocations`.
- Read the exact expansion literal already in `SKILL.md` before pinning so the literal matches byte-for-byte. Style: mirror the `read -r ... <<'EOF' ... grep -cF` block at lines 413-417.
- No new awk parser logic; all pins are simple `grep -Fq` / `grep -cF` lines mirroring the existing style at lines 419-424 (prose pins) and 416-417 (count-at-least-2 expansion pin).

### UPDATED: `scripts/implement-bootstrap.sh`

No logic edits. Only optional: add a single inline comment near the top of `phase_plan_materialize` (after the resume-skip block ending at line 749) pointing to the new "Resume-tail idempotency" section in `scripts/implement-bootstrap.md`. Cap at one comment line. Skip the comment if the function body is already self-explanatory after the documentation update lands.

## Acceptance

1. `scripts/implement-bootstrap.md` contains a section whose heading text includes `Resume-tail idempotency`, and the section body contains the literal sentence fragment `the first pass bails at this checkpoint`.
2. The same section enumerates the post-checkpoint helpers (`create-branch.sh`, `git-current-branch.sh`, `redact-secrets.sh | redact-tmpdir-paths.sh`, `run-step1-plan-log.sh`, `write-tally.sh`, `tracking-issue-summary.sh`, `append-tool-failure.sh`, `emit_plan_materialize_breadcrumbs_if_enabled`) with their idempotency properties on resume.
3. `scripts/test-implement-structure.sh` includes new `grep -Fq` assertions for the two prose pins (`Resume-tail idempotency`, `the first pass bails at this checkpoint`) with the specified failure messages.
4. `scripts/test-implement-structure.sh` includes count-at-least-2 assertions for `_ib_caller_env`, `_ib_issue`, `_ib_fork`, and `_ib_run_id` expansions in `SKILL.md`, each with its specified failure message.
5. `bash scripts/test-implement-structure.sh` exits 0 against the working tree after the documentation update lands.
6. `bash scripts/relevant-checks.sh` (or `make lint`) exits 0.
7. `scripts/implement-bootstrap.sh` has no logic changes (only an optional single inline comment is permitted in `phase_plan_materialize`).

diff_lines: 80
