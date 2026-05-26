# test-tracking-issue-read-sentinel.sh contract

## Purpose

Regression harness for the `--sentinel` branch of `scripts/tracking-issue-read.sh`. It pins the `ISSUE_NUMBER=`, `RUN_ID=`, and `ADOPTED=` field contracts, plus the usage-level numeric validation for argv `--issue`.

## Invariants

1. **Allowed `ADOPTED` values**: exactly `true` or `false` when the key is present with a valid value, or empty (key absent or explicit `ADOPTED=`). No other non-empty value is accepted — strict equality on the extracted value (case-sensitive, no whitespace trimming other than trailing `\r`).
2. **Allowed `ISSUE_NUMBER` values**: any non-empty extracted value must match `^[0-9]+$`. Empty and missing values pass through as `ISSUE_NUMBER=`.
3. **Allowed `RUN_ID` values**: any non-empty extracted value must match `^[A-Za-z0-9._-]+$`. Empty and missing values pass through as `RUN_ID=`.
4. **Absence semantics**: empty sentinel fields mean "sentinel unusable". Absent keys and explicit empty keys are semantically identical on stdout. Consumers MUST NOT treat empty `ADOPTED=` as `false`.
5. **Parser behavior**:
   - Column-0 keys only: indented lines are silently treated as absent.
   - First match wins for duplicate keys (`grep -m1`).
   - Leading UTF-8 BOM stripped from the sentinel file's content before parsing.
   - Trailing `\r` stripped from extracted values (CRLF tolerance).
   - Other trailing whitespace NOT stripped.
6. **Malformed-value no-echo**: invalid `ISSUE_NUMBER=`, `RUN_ID=`, and `ADOPTED=` errors use the fixed token `'malformed-value-omitted'` and never echo the malformed value verbatim in stdout.
7. **Stdout shape on success**: exactly three lines — `ISSUE_NUMBER=<val>\n`, `RUN_ID=<val>\n`, `ADOPTED=<val>\n` — in that order.
8. **Stdout shape on failure**: exactly two lines — `FAILED=true\n` followed by `ERROR=<single-line message>\n` — and exit 1.
9. **Newline-injection scope**: the harness intentionally does not pin embedded-newline rejection for sentinel values. `extract_sentinel_key` is line-oriented (`grep -m1 ... | sed ...`), so a literal newline in the file becomes a separate physical line and is not exposed to the post-extraction case-pattern validator. Same-line invalid bytes (space, slash, tab, non-trailing CR) are pinned.

## Test cases (28 total)

| ID | Input | Expected |
|---|---|---|
| a | `ADOPTED=true` | exit 0, exact three-line stdout with empty `ISSUE_NUMBER` and `RUN_ID` |
| b | `ADOPTED=false` | exit 0, exact three-line stdout |
| c | empty file | exit 0, all three keys emitted empty |
| d | `ADOPTED=` | exit 0, same as empty file |
| e | `ADOPTED=yes` | exit 1, exact two-line stdout: `FAILED=true` + fixed-token `ERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'`; no verbatim echo of the rejected value (both quoted and raw forms checked) |
| f | `ADOPTED=TRUE` | exit 1, exact two-line stdout: `FAILED=true` + fixed-token `ERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'`; no verbatim echo of the rejected value (both quoted and raw forms checked) |
| g | `ADOPTED=1` | exit 1, exact two-line stdout: `FAILED=true` + fixed-token `ERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'`; no verbatim echo of the rejected value (both quoted and raw forms checked) |
| h | `ADOPTED=true` plus trailing space | exit 1, exact two-line stdout: `FAILED=true` + fixed-token `ERROR=invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'`; no verbatim echo of the rejected value (both quoted and raw forms checked) |
| i | sentinel file missing | exit 1, exact not-found envelope |
| j | `ISSUE_NUMBER=123`, `ADOPTED=true`, no `RUN_ID` | exit 0, `RUN_ID=` |
| j2 | `ISSUE_NUMBER=456`, `RUN_ID=abc123`, `ADOPTED=false` | exit 0, exact three-line stdout |
| k | duplicate `ADOPTED=` lines | exit 0, first wins |
| l | CRLF on sentinel keys | exit 0, trailing `\r` stripped |
| m | UTF-8 BOM-prefixed file | exit 0, first key parses |
| n | leading whitespace before key | exit 0, indented key treated as absent |
| o | unreadable sentinel file | exit 1, exact unreadable envelope; skipped as root |
| p | `ISSUE_NUMBER=abc` | exit 1, fixed-token invalid-ISSUE_NUMBER error |
| q | `ISSUE_NUMBER=12.3` | exit 1, fixed-token invalid-ISSUE_NUMBER error |
| r | explicit empty `ISSUE_NUMBER=` | exit 0, empty pass-through |
| s | missing `ISSUE_NUMBER` | exit 0, empty pass-through |
| t | `RUN_ID=has space` | exit 1, fixed-token invalid-RUN_ID error, malformed value omitted |
| u | `RUN_ID=path/traversal` | exit 1, fixed-token invalid-RUN_ID error, malformed value omitted |
| v | `RUN_ID` with embedded tab | exit 1, fixed-token invalid-RUN_ID error |
| w | `RUN_ID` with non-trailing CR | exit 1, fixed-token invalid-RUN_ID error |
| x | explicit empty `RUN_ID=` | exit 0, empty pass-through |
| y | missing `RUN_ID` | exit 0, empty pass-through |
| z | `ISSUE_NUMBER=42`, `RUN_ID=run-1.0_test-abc`, `ADOPTED=true` | exit 0, exact three-line stdout |
| aa | argv `--issue abc --out-dir <path>` | exit 1, `FAILED=true ERROR=usage: --issue must be numeric` before out-dir or `gh` work |

## Makefile wiring

Makefile target: `test-tracking-issue-read-sentinel` — `bash scripts/test-tracking-issue-read-sentinel.sh`. Listed in `.PHONY` and exactly one `test-harnesses-N:` shard prerequisite list. Local `make lint` invokes it through `test-harnesses`; CI invokes it through the shard that contains this target.

## `agent-lint.toml` exclusion

The harness is Makefile-only (not referenced from any `SKILL.md`), so agent-lint would flag it as dead. An exclusion entry in `agent-lint.toml` sits next to the existing `scripts/test-tracking-issue-write.sh` exclusion, with the same rationale.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/tracking-issue-read.sh` | Script under test. Every behavioral change in its `--sentinel` branch or argv `--issue` validation must be mirrored here. |
| `scripts/tracking-issue-read.md` | Canonical contract document. Any field-contract or parser behavior change requires updating the contract and harness in sync. |
| `Makefile` | The `test-tracking-issue-read-sentinel` recipe and one `test-harnesses-N:` shard invoke this harness. Adding or removing targets must stay in sync with the `.PHONY` line. |
| `agent-lint.toml` | Exclusion entry for this Makefile-only harness. |

## Conventions

Bash 3.2-safe. No external `gh` stub needed for sentinel mode; the argv validation case exits before `gh`.
