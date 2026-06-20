### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Postplan consumer root re-derived from live cwd at postapply time
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cwd-callsite-audit-output.txt
- **Severity**: important
- **Concern**: Postplan consumer root is derived from live `Path.cwd()` at `_run_post_apply` time (via `_consumer_repo_root()`), not captured once at loop entry or read from a durable session/env handoff. If the plan-review loop starts with cwd on the plugin cache or another non-git directory, `_consumer_repo_root()` returns `None`, subprocess cwd falls back to `_REPO_ROOT`, and consumer-only scripts can be false-flagged as `missing-script` again. The fix does not follow the `#4509` handoff pattern in `dirty_tree.py` (`LARCH_CONSUMER_REPO` fallback). Production correctness depends on an undocumented assumption that the loop process inherits consumer-repo cwd; the regression test only covers the happy path where the harness sets `cwd=str(consumer)` explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Capture consumer_root once at `run_step3_review` entry or read a durable session env key and pass that stored path into `_run_post_apply` instead of re-deriving from cwd at call time.
  - From dyn-cwd-callsite-audit-output.txt: Capture the consumer repo root once at `run_step3_review` entry (for example `git rev-parse --show-toplevel` from the invoking cwd, or `LARCH_CONSUMER_REPO` when set by the design launcher), store it on the loop driver, pass it into `_run_post_apply`, and add a negative test where loop cwd is the plugin cache but the consumer root is supplied via env so postplan still resolves consumer-only scripts.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Silent fallback to plugin-cache cwd when consumer root unresolved
- **Reviewer(s)**: dyn-cwd-callsite-audit-output.txt
- **Severity**: important
- **Concern**: When `_consumer_repo_root()` returns `None`, `_run_command(..., cwd=None)` silently falls back to `_REPO_ROOT` (plugin cache), which is the failure mode that produced false `missing-script` defects and `postplan-operator-required` in `#4847`. There is no WARN, KV, or execution-issues entry on that path, so a mis-launched loop (wrong cwd, non-git tmpdir, or future launcher regression) reproduces the bug without surfacing why.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cwd-callsite-audit-output.txt: When postplan is about to run and consumer-root resolution fails, emit a loud warning (and optionally fail closed for validator subprocesses) instead of silently using plugin-cache cwd; at minimum log `CONSUMER_REPO_ROOT=unresolved` before falling back.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Copy-failure path returns `scrub_violations="0"` despite prior redactions
- **Reviewer(s)**: dyn-violation-counter-threading-output.txt
- **Severity**: important
- **Concern**: On a mid-copy `_copy_tree_redacted` failure, `_publish_design_logs` returns `scrub_violations="0"` even when earlier siblings already accumulated a non-zero `pre_scrub_violations` total (and the recursive helper may return a partial `total` in its second tuple element that the caller never reads). The publish path still fails closed (no PR), but `design log-publish` emits `SECRET_SCRUB_VIOLATIONS=0`, so operators cannot tell that secret-shaped values were already redacted during the aborted publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-violation-counter-threading-output.txt: On copy failure, return `str(pre_scrub_violations)` (and, if the failed child returns a partial count, add that too) instead of the literal `"0"`; add a regression test that fails copy on the second tmpdir child after the first child produced violations and asserts the emitted count is non-zero.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Commit-failure path drops scrub-violation telemetry
- **Reviewer(s)**: dyn-violation-counter-threading-output.txt
- **Severity**: important
- **Concern**: The same hard-coded `"0"` is returned when `run-log commit` fails after a successful redacted copy, even though `pre_scrub_violations` may already reflect redactions and `_commit_run` may have printed `SECRET_SCRUB_VIOLATIONS=<n>` on stdout. The caller never parses `commit.stdout` on that branch, so credential-rotation telemetry is dropped on commit failure as well as copy failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-violation-counter-threading-output.txt: On commit failure, parse `_scrub_violations(commit.stdout)` when present, else fall back to `str(pre_scrub_violations)`, and surface that in the returned tuple / `_emit("SECRET_SCRUB_VIOLATIONS", ...)`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

