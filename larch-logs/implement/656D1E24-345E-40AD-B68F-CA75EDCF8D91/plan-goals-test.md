## Goal
Implement issue #6906: [IMPLEMENTING] [BUG] ci-fixer invalid-route-handoff when handoff file contains lowercase ledger keys.

## Implementation Plan
## Plan

## Approach

Update the embedded Python in `read_key` so it ignores keys outside `[A-Z][A-Z0-9_]*`.

Keep the existing fail-closed behavior for relevant uppercase entries:

- Reject malformed non-empty lines without `=`.
- Reject duplicate uppercase keys.
- Reject control characters in uppercase-key values.
- Return the requested key unchanged when valid.

Do not change the route-exit writer, handoff format, call sites, or ledger consumption.

## Files to modify/create

### UPDATED: skills/implement/scripts/step-8-ci-fixer.sh

- Change the key-pattern branch in `read_key` from `SystemExit(2)` to `continue`.
- Run duplicate-key and value validation only after a key passes the uppercase pattern.
- Preserve the parser’s missing-file, symlink, UTF-8, malformed-line, duplicate-key, and control-character behavior.
- Leave all `read_key` call sites unchanged.

### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh

- Add shared route-handoff fixture setup that creates a real temporary Git checkout for `REPO_ROOT`: initialize it with `git init`, configure a local test identity, add an initial file, and create one commit. This is required because `--start` runs `git -C "$REPO_ROOT" rev-parse HEAD` before reading the route handoff.
- Have the fixture write valid `session-env.sh` and `ship-pr-state.sh` files that point to that initialized checkout and provide a non-empty `REPO` and `PR_NUMBER`.
- Add a route handoff containing the reported lowercase `ledger_*` entries alongside valid uppercase routing fields, with an intentionally invalid `CI_FAILURE_SCOPE`.
- Assert the invocation reaches `REASON=unknown-ci-failure-scope`, and does not emit `REASON=invalid-route-handoff`, proving parsing continued past the lowercase ledger block.
- Add focused negative route-handoff cases, using the same real Git-backed fixture, that confirm duplicate uppercase keys and control characters in an uppercase value still return `REASON=invalid-route-handoff`.
- Keep the tests offline and choose the invalid scope so execution stops deterministically after route parsing, before main-health validation, tier selection, or bgjob launch.

## Edge cases

- A lowercase or mixed-case key is ignored even if it duplicates another ignored key.
- An ignored key’s value does not affect routing validation.
- Empty lines and lines without `=` remain invalid.
- Duplicate valid uppercase keys remain invalid, including keys other than the requested key.
- Control characters in valid uppercase-key values remain invalid.
- Missing requested keys still produce an empty result and follow existing caller validation.
- Route-parser fixtures must use a real committed Git repository, not only a directory containing `.git`, because the start path validates `HEAD` before it parses the handoff.

## Failure modes

- Validating the value before filtering the key would still let unrelated ledger data break routing.
- Filtering malformed lines too broadly could hide a corrupted handoff. Keep the existing no-`=` rejection.
- A mkdir-only `.git` fixture would return `REASON=invalid-head` and fail to exercise the route parser.
- A test that permits bgjob launch could become environment-dependent. Force a deterministic stop after route parsing.

## Testing strategy

- Run `bash skills/implement/scripts/test-step-8-ci-fixer.sh`.
- Run `bash -n skills/implement/scripts/step-8-ci-fixer.sh skills/implement/scripts/test-step-8-ci-fixer.sh`.
- Run ShellCheck for both changed scripts through the repository’s changed-file lint path.
- Run `scripts/lint-bash32.sh skills/implement/scripts/step-8-ci-fixer.sh skills/implement/scripts/test-step-8-ci-fixer.sh`.
- Confirm the lowercase-ledger regression fixture reports `REASON=unknown-ci-failure-scope` and does not contain `REASON=invalid-route-handoff`.
- Confirm the duplicate-uppercase-key and uppercase-value-control-character fixtures report `REASON=invalid-route-handoff`.

## Acceptance

- Run `bash skills/implement/scripts/test-step-8-ci-fixer.sh`.
- Run `bash -n skills/implement/scripts/step-8-ci-fixer.sh skills/implement/scripts/test-step-8-ci-fixer.sh`.
- Run ShellCheck for both changed scripts through the repository’s changed-file lint path.
- Run `scripts/lint-bash32.sh skills/implement/scripts/step-8-ci-fixer.sh skills/implement/scripts/test-step-8-ci-fixer.sh`.
- Confirm the lowercase-ledger regression fixture reports `REASON=unknown-ci-failure-scope` and does not contain `REASON=invalid-route-handoff`.
- Confirm the duplicate-uppercase-key and uppercase-value-control-character fixtures report `REASON=invalid-route-handoff`.

mechanical_churn: false
diff_lines: 75

## Test plan
(no test plan section in plan-file)
