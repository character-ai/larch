# test-lint-readability-preamble.sh contract

## Purpose

Regression harness for `scripts/lint-readability-preamble.sh`.

It proves the lint accepts a fully compliant fixture and rejects each supported variant independently.

## Fixture Shape

The harness builds three temporary fixture roots:

- compliant: every manifest file contains the required line for its variant.
- external-prompt non-compliant: one external prompt file omits the `<READABILITY_STYLE>` line.
- orchestrator-inline non-compliant: one inline composition file omits the MANDATORY readability directive.

Each fixture mirrors only the paths named in the lint manifest.

## Assertions

The harness asserts:

- compliant fixture exits 0 with empty stderr.
- the external-prompt failure exits non-zero and names the offending path.
- the orchestrator-inline failure exits non-zero and names the offending path.

## Edit-in-sync

Update this file with `scripts/test-lint-readability-preamble.sh`, `scripts/lint-readability-preamble.sh`, and `scripts/lint-readability-preamble.md` when the manifest or accepted line patterns change.
