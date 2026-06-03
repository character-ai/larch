# parse-design-argv.sh

**Consumer**: `SKILL.md` Step 0-pre, before `session-setup.sh` creates `DESIGN_TMPDIR`.

## Argv

The script receives the raw public `/design` argv as positional parameters (`"$@"`). The orchestrator must pass one shell-quoted word per original argv token so verbal tails preserve spaces and shell metacharacters.

Before invoking the Step 0-pre fence, substitute `<PUBLIC_ARGV_WORDS>` with those quoted tokens (never leave the literal placeholder in the rendered Bash). Example: public argv `--hard add a foo` → invoke `parse-design-argv.sh '--hard' 'add a foo'`.

## Allowlist

`skills/design/references/flags.md` is normative for the public flag allowlist and tier mapping. This parser implements only Step 0-pre validation and raw flag binding; Step 0b still maps `--hard` to `design_classification`.

## Machine output

On success, stdout contains exactly these eight KVs, one per line:

- `HARD_REQUESTED=true|false`
- `PARTITION_REQUESTED=true|false`
- `BRAINSTORM_REQUESTED=true|false`
- `MANUAL_REQUESTED=true|false`
- `NO_DEDUP_REQUESTED=true|false`
- `RUN_ID=<value>` (empty when absent)
- `POSITIONAL_KIND=issue|verbal|none`
- `POSITIONAL_VALUE=<value>` (empty when absent)

On validation failure, stdout contains only `VALIDATION_ERROR=<token>`.

## Positional classification

The parser scans leading flags only until the first positional token or bare `--` terminator.

- First positional token all digits (`^[0-9]+$`) → `POSITIONAL_KIND=issue`, `POSITIONAL_VALUE=<digits>` only. Any additional tokens after a numeric issue are ignored (not joined into `POSITIONAL_VALUE` and not reclassified as verbal).
- First positional token non-empty and non-numeric → `POSITIONAL_KIND=verbal`, `POSITIONAL_VALUE=<tail joined by single spaces>`.
- No positional token → `POSITIONAL_KIND=none`, `POSITIONAL_VALUE=`.

Emitted KV values must not contain embedded newline or carriage-return characters; such input yields `VALIDATION_ERROR=newline-in-value` on exit `3`.

## End-of-options

Bare `--` terminates the flag scan. It is not a validation error and is excluded from `POSITIONAL_VALUE`. Tail tokens after `--` are positional only and are never re-parsed as flags.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Parsed OK; eight KVs on stdout |
| `3` | Validation error; `VALIDATION_ERROR=<token>` on stdout |

The script never intentionally exits `1` or `2`; the orchestrator owns user-facing aborts.

## Bash 3.2

Keep this script compatible with macOS Bash 3.2: no associative arrays, namerefs, `mapfile`, case-conversion expansions, or Bash 4-only redirects.

## Stdout-only rationale

Step 0-pre runs before `session-setup.sh`, so no `DESIGN_TMPDIR` exists and there is no result-env file. The stdout KV stream is the complete machine contract. The parser emits machine KVs with direct `printf` to stdout because the orchestrator captures command substitution stdout.

## Orchestrator handoff

The `SKILL.md` fence captures stdout with `set +e`, stores the return code explicitly, then restores `set -e`. It branches on exit `3` or a `VALIDATION_ERROR=` line before Step 0a. On success, bind the mental booleans plus `run_id`, `POSITIONAL_KIND`, and `POSITIONAL_VALUE` from the captured KVs.

Step 0b sub-step 1 must consume only `POSITIONAL_KIND` and `POSITIONAL_VALUE`; it must never re-parse `$ARGUMENTS`, the public argv tail, or flag allowlist membership. For verbal tails, render each original argv token as a separate shell-quoted word before invoking this script so `POSITIONAL_VALUE` is reconstructed with single spaces and shell metacharacters intact.

Downstream flag-key consumer: `design-init-runparams.md`.

## Harness

`skills/design/scripts/test-parse-design-argv.sh` (Makefile target: `test-parse-design-argv`).
