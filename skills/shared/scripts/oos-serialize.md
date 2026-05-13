# oos-serialize.sh Contract

`skills/shared/scripts/oos-serialize.sh` extracts accepted out-of-scope review observations from a ballot file while holding security-tagged observations locally.

Primary caller: `skills/review/scripts/emit-tally.sh`.

Inputs: `--findings-file`, `--output-file`, and optional `--session-env-path`. The current implementation treats all OOS blocks in the input file as accepted; callers should pass an accepted-findings file when threshold filtering is needed.

Stdout is `OOS_ACCEPTED` and `OOS_HELD_SECURITY`.

Harness: `skills/shared/scripts/test-oos-serialize.sh`, wired through `make test-oos-serialize`.
