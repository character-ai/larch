# read-result-env.sh

## Purpose

`read-result-env.sh` safely converts a machine `KEY=VALUE` result-env file into a sourceable env file containing only caller-allowlisted keys. It refuses symlinked and non-regular inputs so orchestrators can source the generated output without reopening untrusted paths.

Allowlist filtering, symlink refusal, and CR/LF rejection are delegated to the Rust `design read-result-env` owner. This script owns fallback-input selection, WARN/ERROR stdout replay, and single-quote encoding for sourceable output.

## Argv

```text
scripts/read-result-env.sh --input PATH --allow KEY [--allow KEY ...] --output PATH [--fallback-input PATH]
```

- `--input PATH` is the primary result-env file.
- `--allow KEY` may be repeated; only these keys are written to the sourceable output.
- `--output PATH` receives sourceable assignments via atomic temp-file then `mv`.
- `--fallback-input PATH` is a compatibility-only fallback stream for callers that historically merged producer stdout when the primary result env was unavailable.

## Result-env grammar

The primary and fallback inputs use the `phase_driver_read_result_env` parser:

- Blank lines are ignored.
- Records split at the first `=` only.
- Embedded `=` characters in values are preserved.
- Nonblank lines without `=` are silently skipped.
- Values containing CR or LF bytes are silently skipped (key not written).

Physical newline smuggling is either a second parsed record or a nonblank line without `=` (silently skipped); the helper never decodes escaped newlines.

## Allowlist and replay

Allowlisted keys are written to `--output` as single-quoted shell assignments, for example `INIT_STATUS='ok'`. Non-allowlisted keys are ignored, except `WARN` and `ERROR`: those records are replayed to stdout as `WARN=<body>` or `ERROR=<body>` using the substring after the first `=` as the body, and they are not written to the sourceable output.

Single quotes in values are encoded by ending the single-quoted string, inserting a double-quoted single quote, then reopening the single-quoted string. This yields sourceable Bash that round-trips literal `'` characters.

## Fallback semantics

Without `--fallback-input`, missing, symlinked, or otherwise non-regular primary inputs exit `1` before reading.

With `--fallback-input`, a missing, symlinked, or non-regular primary input is nonfatal and the fallback file is parsed instead. The primary path is classified before any read, so a non-regular primary is never opened. A regular primary result-env is always the source of truth; fallback is not used to mask parse failures in a regular primary file.

The fallback input must itself be a regular non-symlink file. Missing, symlinked, directory, or otherwise non-regular fallback inputs exit `1`.

When fallback is used because the primary input is a symlink, the helper emits a visible symlink-refusal breadcrumb before parsing fallback. For the Step 0b design init result-env, this preserves the existing operator-facing breadcrumb; other callers receive a `WARN=` line naming the refused primary path.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Parsed successfully and atomically wrote `--output` |
| `1` | Argv error; missing/symlink/non-regular primary without fallback; missing/symlink/non-regular fallback; output temp-file or move failure |

## Symlink-refusal rationale

The caller sources only the generated output, never the primary result-env directly. Refusing symlinked result-env and fallback files preserves that trust boundary and prevents a producer or race from redirecting the orchestrator into unexpected file contents.

## Harness

`scripts/test-read-result-env.sh` covers allowlists, first-`=` parsing, primary/fallback parity, malformed-line skip, fallback behavior, symlink breadcrumbs, fallback input refusal, quoting, sourceability, and WARN/ERROR replay.

```bash
bash scripts/test-read-result-env.sh
```

Wired through `make test-read-result-env`.
