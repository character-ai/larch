# lib-plan-optional-trailers.sh / lib-plan-optional-trailers.awk

Shared optional-trailer helpers for `/design` plan-size gating, revision preservation, and Gate B dedup. The Bash library sources the awk implementation for all metadata-block parsing.

## Bash API (`lib-plan-optional-trailers.sh`)

| Function | Role |
|----------|------|
| `snapshot_optional_trailer_keys` | Write present keys to a file; companion `.values` via `snapshot_optional_trailer_values`. |
| `snapshot_optional_trailer_values` | Write `key=value` lines for present keys. |
| `plan_has_optional_trailer_key` | Exit **0** if `key` is present in the final block; **1** otherwise. |
| `plan_has_any_optional_trailer` | Exit **0** if any of `diff_added`, `diff_deleted`, `mechanical_churn` is present. |
| `parse_plan_optional_metadata` | Four-line `parse` output (see awk `parse` mode). |
| `validate_optional_trailer_keys_preserved` | Compare snapshotted keys against a revised plan. |
| `validate_optional_trailers_preserved` | Keys plus value equality via companion `.values`. |
| `dedup_plan_preserve_optional_trailers` | Mechanical dedup with snapshot validation (used by `gate-b-dedup-plan.sh`). |

## Awk modes (`lib-plan-optional-trailers.awk`)

Invoked as `awk -v mode=<mode> -v trailer_nr=<N> [-v key=<k>] -f lib-plan-optional-trailers.awk <plan>`.

| Mode | Output / exit |
|------|----------------|
| `keys` | Present keys in fixed order: `diff_added`, `diff_deleted`, `mechanical_churn` (one per line). |
| `values` | `key=value` for each present key (same order). |
| `parse` | Four lines: `block_len`, `diff_added` or `-`, `diff_deleted` or `-`, `mechanical_churn` (`false` when absent). |
| `has_key` | Exit **0** if `-v key=` is present; **1** otherwise. |

### `trailer_nr` contract

`trailer_nr` is the 1-based line number of the last non-empty line (the required `diff_lines:` trailer). The upward scan starts at `trailer_nr - 1`; `diff_lines:` itself is never parsed as optional metadata.

### Final contiguous block

Scan upward from the line above `diff_lines:`. Lines matching strict optional-trailer regexes join the block; any other line (including blank) stops the scan. Duplicate keys in the block: **last match in file order** wins (closest to `diff_lines:`).

### Octal guard

`diff_added: 08`, `diff_added: 09`, `diff_deleted: 08`, and `diff_deleted: 09` match the strict line regex but are rejected as absent (`has_key` exit **1**; omitted from `keys`/`values`). Values such as `010` are retained.

### `block_len` (`parse` line 1)

`block_len` is the count of strict optional-trailer lines collected in the upward scan, including duplicate keys (physical line count), not the count of distinct present keys. `check-plan-size.sh` subtracts `block_len` from plan body line count.

## Callers

- `check-plan-size.sh` — Step 2b.5 thresholds (`parse_plan_optional_metadata`).
- `revise-plan-with-waterfall.sh` — revision preservation.
- `plan-review-loop.sh` — review-loop snapshot/validate.
- `gate-b-dedup-plan.sh` — `--snapshot-trailers` / `--dedup` (see `references/approval-gates.md`).

## Harnesses

- `test-trailer-awk.sh` — direct awk unit coverage (contract: `test-trailer-awk.md`).
- `test-trailer-helpers.sh` — combined harness (`test-trailer-dedup.sh`, `test-trailer-has-any.sh`, `test-trailer-validate.sh`, `test-trailer-awk.sh`).
- `test-gate-b-dedup-plan.sh` — integration coverage for `gate-b-dedup-plan.sh`.
- `test-check-plan-size.sh` — plan-size integration.
