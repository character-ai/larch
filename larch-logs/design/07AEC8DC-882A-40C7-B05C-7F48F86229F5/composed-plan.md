## Plan

Fix the `set -e` violation in `step5_parse_checks_capture_file` and
`step5_parse_lint_capture_file` (in
`skills/review-and-fix/scripts/review-implement-step5-loop.sh`) by making the
shared helper `step5_parse_kv_tokens` **total**: drop the `return 1` at the
end so the function always exits 0 and signals "key not found" via empty
stdout. Callers already discriminate via `[[ -n "$v" ]]`, so semantics at
every call site are byte-identical.

After the existing read loop in each wrapper, add a post-loop required-field
sanity check that surfaces malformed capture files in run logs:

- **`step5_parse_checks_capture_file`** — required field discriminator is
  **at least one of** `STEP5_CHK_STATUS`, `STEP5_CHK_RELEVANT_CHECKS_OK`, or
  `STEP5_CHK_RELEVANT_CHECKS_SKIPPED` (all three are real producer outputs
  of `scripts/run-relevant-checks-captured.sh`; `RELEVANT_CHECKS_SKIPPED=true`
  is the legitimate clean envelope in consumer repos lacking
  `scripts/relevant-checks.sh`). When all three are empty:
  - Emit stderr line:
    `step5_parse_checks_capture_file: required field missing (none of STATUS, RELEVANT_CHECKS_OK, RELEVANT_CHECKS_SKIPPED) in capture file: <path>`
  - **Fail closed**: also set `STEP5_CHK_STATUS=fail` and
    `STEP5_CHK_FAILURE_REASON=malformed-capture` so the existing fail-handling
    in `run_implement_loop` emits a `stall` envelope with reason
    `relevant-checks-malformed-capture` instead of falling through silently.

- **`step5_parse_lint_capture_file`** — when `STEP5_LINT_STATUS` is still
  empty, emit
  `step5_parse_lint_capture_file: required field missing (LINT_FIX_STATUS) in capture file: <path>`
  to stderr only. No global override is needed: the existing `case` on
  `STEP5_LINT_STATUS` in `run_implement_loop` already routes unrecognized
  (including empty) values to its `*` default arm, which stalls.

Update the sibling doc `skills/review-and-fix/scripts/review-implement-step5-loop.md`
with one short paragraph documenting the new return semantics
(`step5_parse_kv_tokens` always exits 0; key-absent is empty stdout) and the
wrapper-level required-field check (three-way checks-side discriminator;
fail-closed override on the checks side; stderr-only on the lint side).
No drift-prone line numbers.

### Test harness

Add a new **`parsers`** section to `skills/review-and-fix/scripts/test-review-and-fix.sh`
gated behind `--section parsers` (extend the `--section` whitelist from
`dispatch|convergence` to `dispatch|convergence|parsers`). The section sources
`review-implement-step5-loop.sh` directly and runs under `set -euo pipefail`,
exercising the bug surface. **Eight test cases** (each must print `ok: parsers <case>`):

1. **`step5_parse_kv_tokens` matrix** under `set -e`: positive
   (`KEY=value` → matched value, exit 0), negative (`OTHER=foo` → empty
   stdout, exit 0 — the regression), empty line (empty input → empty
   stdout, exit 0).
2. **Checks capture — passing single-line form**: `RELEVANT_CHECKS_OK=true SITE=foo COVERAGE=full`
   → `STEP5_CHK_RELEVANT_CHECKS_OK=true`, no stderr `required field missing`.
3. **Checks capture — multi-line failing form**: `STATUS=fail` +
   `FAILURE_REASON=bad-thing` → globals set correctly, no stderr.
4. **Checks capture — `RELEVANT_CHECKS_SKIPPED=true` form**: legitimate
   skip envelope; `STEP5_CHK_RELEVANT_CHECKS_SKIPPED=true`, no stderr
   `required field missing`.
5. **Checks capture — malformed (fail-closed)**: `IRRELEVANT=true`
   (none of the three discriminators). Stderr contains
   `required field missing`; `STEP5_CHK_STATUS=fail` and
   `STEP5_CHK_FAILURE_REASON=malformed-capture`; wrapper returned 0
   under `set -e`.
6. **Lint capture — passing form**: `LINT_FIX_STATUS=applied`
   (real producer value — `lint-fix-loop.sh` emits one of `applied`,
   `main-agent-required`, `failed`, `no-changes`). Asserts
   `STEP5_LINT_STATUS=applied`, no stderr.
7. **Lint capture — malformed (stderr-only)**: `OTHER=stuff`. Stderr
   contains `required field missing`; `STEP5_LINT_STATUS=""` (not
   overridden — caller's `*` default handles it); wrapper returned 0
   under `set -e`.

For substring assertions on stderr absence, capture stderr to a temp file
(`2>"$TMP/stderr.log"`) and grep explicitly — do not rely on terminal output.
Use existing harness conventions (`TMP=$(mktemp -d ...)`, `fail`/`pass`
helpers, `section_runs parsers` guard). Do not touch the existing `dispatch`
or `convergence` sections.

Update sibling `skills/review-and-fix/scripts/test-review-and-fix.md` to
extend the documented `--section` union from `dispatch|convergence` to
`dispatch|convergence|parsers` and add one short note describing what the
parsers slice covers.

### Makefile

Add a `test-review-and-fix-parsers` target mirroring the existing
`test-review-and-fix-dispatch` and `test-review-and-fix-convergence` recipes,
register it on an existing `test-harnesses-N` shard (alongside the other two
section targets, on the lightest matching row), add it to `.PHONY`, and
update any adjacent comment that enumerates the section targets (e.g.
"two section targets" → "three section targets"). Run
`scripts/test-harness-shards-coverage.sh` to confirm shard coverage still
passes.

### Constraint

No edits inside the existing while-loop bodies of
`step5_parse_checks_capture_file` / `step5_parse_lint_capture_file` besides
the new post-loop required-field guard. `run_implement_loop` call sites are
untouched.

## Acceptance

- `step5_parse_kv_tokens` in `skills/review-and-fix/scripts/review-implement-step5-loop.sh`
  always exits 0; "key not found" is encoded via empty stdout. The `return 1`
  is removed and a one-line comment documents the new contract.
- Both wrappers have a post-loop required-field check. On malformed input:
  - Checks wrapper emits stderr `step5_parse_checks_capture_file: required field missing (none of STATUS, RELEVANT_CHECKS_OK, RELEVANT_CHECKS_SKIPPED) in capture file: <path>` and additionally sets `STEP5_CHK_STATUS=fail` + `STEP5_CHK_FAILURE_REASON=malformed-capture`.
  - Lint wrapper emits stderr `step5_parse_lint_capture_file: required field missing (LINT_FIX_STATUS) in capture file: <path>` and does NOT override `STEP5_LINT_STATUS`.
- Sibling doc `review-implement-step5-loop.md` has one short paragraph
  documenting the new return semantics and wrapper-level check (no
  drift-prone line numbers).
- `skills/review-and-fix/scripts/test-review-and-fix.sh` has a new `parsers`
  section with the 7 enumerated test cases above (test 1 is a three-input
  matrix; the rest are single cases), each emitting `ok: parsers <case>`.
  The `--section` whitelist includes `parsers`. The `dispatch` and
  `convergence` sections are unchanged.
- Sibling `test-review-and-fix.md` documents the new `parsers` value in the
  `--section` union and notes what the slice covers.
- `Makefile` has a `test-review-and-fix-parsers` target on a
  `test-harnesses-N` shard, mirroring the other section targets. `.PHONY`
  covers the new target. The section-targets-enumerating comment (if
  present) is updated. `bash scripts/test-harness-shards-coverage.sh`
  passes.
- `bash scripts/relevant-checks.sh` passes on the resulting tree.
- Running `bash skills/review-and-fix/scripts/test-review-and-fix.sh --section parsers`
  exits 0 with all `ok: parsers <case>` lines.
- Existing `--section dispatch` and `--section convergence` continue to pass.

diff_lines: 110
