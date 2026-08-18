# test-step-7a.sh

Delegation smoke for `skills/implement/scripts/step-7a.sh`.

## Cases

The smoke tests only the wrapper contract:

1. Repository-root fallback when `CLAUDE_PLUGIN_ROOT` is unset.
2. Explicit `CLAUDE_PLUGIN_ROOT` selection.
3. Exact `scripts/larch.sh implement step-7a` routing and argument forwarding.
4. Stdout, stderr, and exit-status passthrough.

## Behavioral authority

`python/tests/implement/test_step_7a.py` owns Step 7a behavior. It covers orchestration order, Code Flow generation and rejection/failure cleanup, diagram upsert gating, fork target selection, rebase exit propagation, the execution-issues checkpoint, terminal KVs, bgjob transport, and argument failures. Shared diagrams-comment merge behavior is covered by `python/tests/rendering/test_rendering.py`.

## Assertion parity

| Former Bash concern | Current coverage |
| --- | --- |
| Green orchestration, token mark, Code Flow section, upsert, checkpoint | `test_step7a_orchestrates_generation_upsert_and_checkpoint_in_order` |
| Architecture preservation and legacy diagram markers | `python/tests/rendering/test_rendering.py` diagrams-upsert tests |
| Small/non-runtime skip and forked skip | `test_step7a_skips_diagram_for_small_non_runtime_change` and fork target test |
| Forked generation, upstream repo, and checkpoint argv | `test_step7a_rehydrates_fork_target_for_generation_and_checkpoint` |
| Sanitizer rejection variants and stale-artifact cleanup | `test_step7a_sanitizer_skip_clears_stale_artifacts_and_omits_upsert` |
| Generation failure, warning, and stale-artifact cleanup | `test_step7a_diagram_failure_exits_zero_and_clears_stale_artifacts` |
| Upsert failure continues to checkpoint | `test_step7a_upsert_failure_keeps_checkpoint_and_exit_success` |
| Empty issue number skips the upsert but runs the checkpoint | `test_step7a_empty_issue_number_skips_upsert_but_runs_checkpoint` |
| Checkpoint success and the retired publication command fence | checkpoint tests in `test_step_7a.py` |
| Rebase conflict, failure, and unexpected exit | `test_step7a_rebase_failure_*` tests |
| Session lookup and terminal KVs | session and terminal-KV tests in `test_step_7a.py` |
| Wrapper root selection, routing, argv, streams, and exit status | this smoke |

Run both lanes with `make test-step-7a`. Run `make agent-lint` and ShellCheck for the retained Bash smoke.

## Invariants

The smoke is Bash 3.2-compatible and uses a fake plugin CLI, so it never exercises Step 7a behavior through the wrapper.
