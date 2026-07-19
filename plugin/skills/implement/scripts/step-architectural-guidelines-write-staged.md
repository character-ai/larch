# step-architectural-guidelines-write-staged

Thin `/implement` architectural-guidelines legacy helper.

## Contract

The live `/implement` prompt no longer writes staged Step 7a assessments. Step 8 compose-time assessment writes the durable note directly through `step-architectural-guidelines-write-compose.sh`.

This wrapper remains available for one release for compatibility with old harnesses or paused runs. New prompt paths should not use staged assessment artifacts.
