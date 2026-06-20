# Review Round 4

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Blanket `contextlib.suppress(OSError)` swallows reviewer-status TSV write failures in `plan_review_round.py`
- **Reviewer(s)**: dyn-robustness-output.txt
- **Severity**: important
- **Concern**: At panel-failed, pruned-empty, collect-failed, and post-collection call sites, the entire `write_reviewer_status_tsv()` call is wrapped in `contextlib.suppress(OSError)`, so `mkdir`, `write_text`, and `sync_latest_reviewer_status` failures are swallowed with no `execution-issues.md` entry. That recreates the original #4848 symptom (missing `reviewer-status.tsv` / `latest-reviewer-status.tsv`) without any operator-visible signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-robustness-output.txt: Remove the outer `suppress` around the producer, or catch only expected `realpath` misses inside `write_reviewer_status_tsv` and log write/sync failures via `run-log append-failure` under `Warnings` before continuing the round.


### FINDING_3: Blanket `contextlib.suppress(OSError)` swallows reviewer-status TSV write failures on subprocess fallback path
- **Reviewer(s)**: dyn-robustness-output.txt
- **Severity**: important
- **Concern**: The `RUN_STEP3_PLAN_REVIEW_LOOP_SH` subprocess fallback path in `python/plan_review.py:1274-1279` uses the same blanket `contextlib.suppress(OSError)` around `write_reviewer_status_tsv()` and `sync_latest_reviewer_status()`, so injected stubs that omit the artifact can still fail silently on disk errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-robustness-output.txt: Mirror the in-process path: let write failures surface or log them; reserve `suppress` for non-fatal `realpath` lookups only.


### FINDING_5: `status_by_norm_basename` last-writer collision can flip retry success to failure
- **Reviewer(s)**: dyn-robustness-output.txt
- **Severity**: important
- **Concern**: `status_by_norm_basename` is a single-key dict: each normalized basename keeps only the last collector record seen. When both a phase-1 output and a `-retry`/`-phase2`/`-phase3` variant normalize to the same basename (the intended join case), parse order decides whether the slot is `done` or `failed`; a trailing phase-1 `EMPTY_OUTPUT` record can overwrite a successful retry `OK`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-robustness-output.txt: On basename collision, prefer `OK` over non-OK statuses (or prefer the lexicographically latest suffix path), or key the lookup by `(normalized_basename, slot)` instead of basename alone.


### FINDING_9: Subprocess fallback may materialize status from stale `collector-results.env`
- **Reviewer(s)**: dyn-integration-paths-output.txt
- **Severity**: important
- **Concern**: The `RUN_STEP3_PLAN_REVIEW_LOOP_SH` subprocess fallback calls `write_reviewer_status_tsv(tmpdir, round_num)` without `collect_text`, so it reads whatever is already on disk in `collector-results.env`. The in-process `execute_round` path clears that file when collection is skipped (`python/plan_review_round.py:602-603`) and passes explicit `collect_text=""` on pre-collection terminals (`python/plan_review_round.py:538, 568`), but the subprocess seam has no equivalent guard. A harness stub (or legacy loop body) that omits `reviewer-status.tsv` without refreshing `collector-results.env` can materialize a post-notification table from a prior round's collector records instead of all-`skipped` for the current round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-integration-paths-output.txt: Mirror the in-process contract in `_run_round_body`: pass `collect_text=""` when parsed loop status is a pre-collection terminal (`panel-failed` with no collection), and/or clear or ignore stale `collector-results.env` before materialization; add a subprocess regression test with stale on-disk collector data and no per-round status file.


### FINDING_10: Subprocess fallback lacks header-only fallback when `reviewer-status.tsv` is a symlink
- **Reviewer(s)**: dyn-integration-paths-output.txt
- **Severity**: important
- **Concern**: When `reviewer-status.tsv` is absent because the path is a symlink (including a dangling one), `not round_status.is_file()` is true, `write_reviewer_status_tsv` returns `None` at `python/plan_review_round.py:381-382`, and `_run_round_body` has no header-only fallback. In-process terminals duplicate that fallback (`python/plan_review_round.py:539-545`, `569-575`), and `_clean_round_dir` (`python/plan_review.py:1259-1261`) never removes symlinks, so a leftover symlink can block production of both the per-round and `latest` files while a prior round's `latest-reviewer-status.tsv` stays stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-integration-paths-output.txt: After a `None` return, reuse the same header-only / manifest-based fallback `execute_round` uses; optionally unlink a dangling `reviewer-status.tsv` symlink in `_clean_round_dir` before materialization.


