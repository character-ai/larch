# test-write-final-report.sh

Delegation smoke for `skills/implement/scripts/write-final-report.sh`.

## Cases

The smoke tests only the wrapper contract:

1. Repository-root fallback when `CLAUDE_PLUGIN_ROOT` is unset.
2. Explicit `CLAUDE_PLUGIN_ROOT` selection.
3. Exact `python/cli.py final-report write` routing and argument forwarding.
4. Stdout, stderr, and exit-status passthrough.

## Behavioral authority

`python/tests/report/test_final_report.py` owns final-report write behavior. It covers the outcome matrix, `--comment-only` preservation of tracked `final-summary.md`, manifest reconcile stamp and failure, upsert and missing-arg failures, token-cost unavailable variants, Claude-subprocess cost lines, force-flag rendering, PR line-count cache/recompute, review-phase live-dir mismatch (#3794), and the happy-path summary shape. Shared renderer and tracking surfaces also live under `python/tests/git/test_pr_body.py` (`render_run_summary`, `post_tracking`, `write_final_report`).

## Assertion parity

| Former Bash concern | Current coverage |
| --- | --- |
| Happy path merged summary, DONE outcome, Mode omitted, line counts | `test_write_final_report_happy_path_writes_final_summary` |
| `--comment-only` leaves tracked `final-summary.md` untouched | `test_write_final_report_comment_only_preserves_tracked_final_summary` |
| Upsert failure exits non-zero with `STATUS=failed` | `test_write_final_report_main_upsert_failure_emits_status_failed` / `test_write_final_report_tracking_upsert_failure_surfaces_reason` |
| Missing `--implement-tmpdir` emits failed envelope | `test_write_final_report_main_missing_tmpdir_emits_failed_envelope` |
| Outcome matrix (merged/stalled/design-only/bailed*/forked/pr-*/force-merged) | `test_write_final_report_outcome_matrix` |
| Force flag true/false/omit/invalid and legacy Path omitted | `test_write_final_report_force_flag_and_legacy_path` |
| Exec / warning counts and detail | existing `test_write_final_report_*exec*` / `*warning*` / `*ndjson*` tests |
| Manifest stamp fields and reconcile failure | `test_write_final_report_manifest_stamp_and_failure` |
| Malformed / all-zero / Claude-only-zero cost N/A | `test_write_final_report_cost_unavailable_variants` |
| `claude_sub` nonzero cost line | `test_write_final_report_claude_sub_nonzero_cost_line` |
| Line-count compute, repo-unavailable, gh-fail, cache, stale PR | `test_write_final_report_line_counts_cache_and_repo_unavailable` |
| Review Phase Detail + #3794 live-dir mismatch | `test_write_final_report_includes_review_timing_gantt`, `test_write_final_report_review_phase_live_dir_mismatch` |
| Wrapper root selection, routing, argv, streams, and exit status | this smoke |

Run both lanes with `make test-write-final-report`. Run `make agent-lint` and ShellCheck for the retained Bash smoke.

## Invariants

The smoke is Bash 3.2-compatible and uses a fake plugin CLI, so it never exercises final-report behavior through the wrapper.
