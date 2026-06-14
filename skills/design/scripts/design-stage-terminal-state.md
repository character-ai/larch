# design-stage-terminal-state.sh

`design-stage-terminal-state.sh` writes the strict `/design` terminal-state KV file used by the generic stall-reporting core.

## Contract

Inputs are `--design-tmpdir`, `--outcome`, `--step`, `--phase`, `--site`, `--trigger`, `--bail-reason`, `--exit-code`, and `--source-script`. Optional inputs are `--failure-detail-log`, `--root-cause-hint`, `--summary-outcome`, and `--evidence-ref`.

The helper validates `$DESIGN_TMPDIR` through `scripts/lib-design-tmpdir.sh`. It validates tokens through `python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery validate-token --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR"`, then validates the completed candidate with `stall-recovery validate-terminal-state` before the atomic rename.

`FAILURE_DETAIL_LOG` must be a regular, readable, non-symlink file under `$DESIGN_TMPDIR`. The written state excludes raw prompt text, issue bodies, feature text, plans, repo paths, URLs, and log tails.

## Callers

Prompt-owned hard halts use this helper before the final-summary path. Intended callers include Step 0b clarify hard halts, Step 2b.5 decompose-panel retry exhaustion, publish failures, postplan failures, and publish-tail hard exits.

## Harness

`test-design-stage-terminal-state.sh` covers valid staging, token rejection, path confinement, symlink rejection, state preservation, and KV-only stdout.
