# test-lint-readability-preamble.sh contract

## Purpose

Regression harness for `scripts/lint-readability-preamble.sh`.

It proves the lint accepts a fully compliant fixture and rejects each supported variant independently.

## Fixture Shape

The harness builds temporary fixture roots for:

- compliant: every manifest file contains the required line for its variant.
- external-prompt non-compliant: one external prompt file omits the `<READABILITY_STYLE>` line.
- orchestrator-inline non-compliant: one inline composition file has no MANDATORY readability directive.
- orchestrator-inline partial-count: a multi-directive inline composition file has fewer MANDATORY readability directives than the manifest requires.
- orchestrator-inline missing-file: a manifest-row file is absent from the fixture root.

Each fixture mirrors only the paths named in the lint manifest.

## Assertions

The harness asserts:

- compliant fixture exits 0 with empty stderr.
- the external-prompt failure exits non-zero and names the offending path.
- orchestrator-inline count failures exit non-zero and report expected/found counts.
- the absent orchestrator-inline file exits non-zero with the generic missing-directive message.

## Edit-in-sync

Update this file with `scripts/test-lint-readability-preamble.sh`, `scripts/lint-readability-preamble.sh`, and `scripts/lint-readability-preamble.md` when the manifest or accepted line patterns change.
