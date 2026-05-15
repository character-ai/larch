# test-parse-input.sh contract

**Purpose**: regression coverage for `parse-input.sh`, the `/issue` batch-mode parser. The harness exercises OOS input, generic `### <title>` input, ambiguous heading boundaries, body-file output, negative invocation paths, and the stderr parse breadcrumb.

**Coverage**:

1. Baseline OOS and generic items parse into `ITEM_<i>_TITLE`, `ITEM_<i>_BODY_FILE`, optional OOS metadata, and `ITEMS_TOTAL`.
2. Issues #129, #131, #132, and #138 stay locked: OOS subheading absorption, generic bodies with OOS-shaped bullets, empty inline OOS descriptions, nested `### OOS_N:` prose inside generic bodies, and incomplete-OOS pending-heading split behavior.
3. Generic structured bodies preserve labels such as `**Slice**`, `**File**`, `**Reviewer**`, `**Problem**`, and `**Suggested fix**` verbatim.
4. Missing `--output-dir` and unwritable `--output-dir` fail non-zero.
5. Stdout never reintroduces the legacy inline `ITEM_<i>_BODY=<base64>` contract.
6. Stderr includes the visible `▶ parse-input:` breadcrumb for single generic, multi-item generic, and OOS inputs, with the expected item count and mode.

**Helper shape**: `run_parser_capture` writes parser stdout and stderr to temporary files, verifies the process exited 0, checks the no-inline-body invariant, then assigns captured stdout/stderr to caller-named variables with `printf -v`. `run_parser` wraps that helper for older assertions that only inspect stdout.

**Edit-in-sync rules**:

- Any change to `parse-input.sh` stdout keys or body-file emission must update the stdout assertions and the `ITEM_<i>_BODY=` regression guard.
- Any change to heading boundary semantics (`### <title>` or `### OOS_N:` handling) must update the relevant issue-numbered cases and the parser sibling doc.
- Any change to the breadcrumb prefix, mode label, count wording, or title-list formatting must update the breadcrumb assertions here and the breadcrumb note in `parse-input.md`.

**Execution**: `bash skills/issue/scripts/test-parse-input.sh` exits 0 on success and 1 on the first failed assertion. Wired into `make lint` via `test-parse-input`, included in the issue skill harness set.
