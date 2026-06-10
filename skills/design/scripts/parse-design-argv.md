# parse-design-argv.sh

**Consumer**: `SKILL.md` Step 0-pre, before `session-setup.sh` creates `DESIGN_TMPDIR`.

## Argv

The script receives the raw public `/design` argv as positional parameters (`"$@"`). The orchestrator must pass one shell-quoted word per original argv token so verbal tails preserve spaces and shell metacharacters.

Reserved internal `--output PATH` support exists only for the orchestrator and must appear before public argv tokens:

```bash
parse-design-argv.sh --output "$argv_env" <PUBLIC_ARGV_WORDS>
```

Any later/public `--output` token is not a supported `/design` flag and remains a validation error. Before invoking the Step 0-pre fence, substitute `<PUBLIC_ARGV_WORDS>` with those quoted tokens (never leave the literal placeholder in the rendered Bash). Example: public argv `--hard add a foo` → invoke `parse-design-argv.sh --output "$argv_env" '--hard' 'add a foo'`.

## Allowlist

`skills/design/references/flags.md` is normative for the public flag allowlist and tier mapping. This parser implements only Step 0-pre validation and raw flag binding; Step 0b still maps `--hard` to `design_classification`.

## Machine output

On success, stdout always contains exactly these nine uppercase KVs, one per line, including when `--output` is used:

- `HARD_REQUESTED=true|false`
- `PARTITION_REQUESTED=true|false`
- `BRAINSTORM_REQUESTED=true|false`
- `APPROVE_REQUESTED=true|false` (set by `--per-round-approval`)
- `SKIP_APPROVE_REQUESTED=true|false` (set by `--skip-approve` / `-s`)
- `NO_DEDUP_REQUESTED=true|false`
- `RUN_ID=<value>` (empty when absent)
- `POSITIONAL_KIND=issue|verbal|none`
- `POSITIONAL_VALUE=<value>` (empty when absent)

On validation failure, stdout contains only `VALIDATION_ERROR=<token>`.

When leading internal `--output PATH` is present, the script additionally writes a sourceable env file atomically. On exit `0`, the output file contains all nine orchestrator-facing bindings:

```bash
hard_requested='<value>'
partition_requested='<value>'
brainstorm_requested='<value>'
approve_requested='<value>'
skip_approve_requested='<value>'
no_dedup_requested='<value>'
run_id='<value>'
POSITIONAL_KIND='<value>'
POSITIONAL_VALUE='<value>'
```

On exit `3`, the output file contains only:

```bash
VALIDATION_ERROR='<encoded-token>'
```

Single quotes in values are encoded by closing the quote, inserting a double-quoted single quote, and reopening the quote. If the output temp-file write or atomic `mv` fails, the script exits `1`.

## Positional classification

The parser scans leading flags only until the first positional token or bare `--` terminator.

- First positional token all digits (`^[0-9]+$`) → `POSITIONAL_KIND=issue`, `POSITIONAL_VALUE=<digits>` only. Any additional tokens after a numeric issue are ignored (not joined into `POSITIONAL_VALUE` and not reclassified as verbal).
- First positional token non-empty and non-numeric → `POSITIONAL_KIND=verbal`, `POSITIONAL_VALUE=<tail joined by single spaces>`.
- No positional token → `POSITIONAL_KIND=none`, `POSITIONAL_VALUE=`.

Emitted KV values must not contain embedded newline or carriage-return characters; such input yields `VALIDATION_ERROR=newline-in-value` on exit `3`.

## End-of-options

Bare `--` terminates the flag scan. It is not a validation error and is excluded from `POSITIONAL_VALUE`. Tail tokens after `--` are positional only and are never re-parsed as flags.

## Exit codes

Retired flag: `--approve` is rejected with `VALIDATION_ERROR=--approve` (exit `3`) — use `--per-round-approval` instead.

| Code | Meaning |
|------|---------|
| `0` | Parsed OK; nine uppercase KVs on stdout; sourceable output file written when requested |
| `1` | Internal/parser/output write failure |
| `3` | Public argv validation error; `VALIDATION_ERROR=<token>` on stdout; sourceable validation output when requested |

## Bash 3.2

Keep this script compatible with macOS Bash 3.2: no associative arrays, namerefs, `mapfile`, case-conversion expansions, or Bash 4-only redirects.

## Orchestrator handoff

The `SKILL.md` fence creates a temp env file, invokes this parser with leading `--output "$argv_env"`, redirects parser stdout to `/dev/null`, captures stderr before `<PUBLIC_ARGV_WORDS>`, stores the return code explicitly, and restores `set -e`. It preserves the literal `PUBLIC_ARGV_WORDS` stderr guard immediately after capture.

The orchestrator gates `source "$argv_env"` on the parser return code. Exit `0` sources the lowercase booleans plus `run_id`, `POSITIONAL_KIND`, and `POSITIONAL_VALUE`, then emits one compact diagnostic `printf` from sourced values. Exit `3` sources `VALIDATION_ERROR` and preserves the existing two warning forms: with-token `printf '%s %s\n' ... "$VALIDATION_ERROR"` and without-token `printf '%s\n' ...`. A sourced `VALIDATION_ERROR` on any non-`3` path is a hard abort.

Step 0b sub-step 1 must consume only `POSITIONAL_KIND` and `POSITIONAL_VALUE`; it must never re-parse `$ARGUMENTS`, the public argv tail, or flag allowlist membership. For verbal tails, render each original argv token as a separate shell-quoted word before invoking this script so `POSITIONAL_VALUE` is reconstructed with single spaces and shell metacharacters intact.

Downstream flag-key consumer: `design-init-runparams.md`.

## Harness

`skills/design/scripts/test-parse-design-argv.sh` (Makefile target: `test-parse-design-argv`) covers legacy stdout, leading internal `--output`, sourceability, public `--output` rejection, numeric/verbal tails, metacharacter values, quote-bearing validation tokens, and newline-smuggling rejection.
