# test-architectural-guidelines-step

Thin `/implement` architectural-guidelines regression harness.

## Contract

Verifies the Step 7a staging retirement, Step 8 `guidelines-assessment` routing, compose-time assessment reference, conflict/CI-fix no-Phase-A rerun prose, and direct durable-note write behavior.

## Tests

`make lint` runs this harness through the script sibling checks. The Python CLI owns compose-time metadata validation and durable note writes. The live prompt owns authoring the assessment and relaunching Step 8.
