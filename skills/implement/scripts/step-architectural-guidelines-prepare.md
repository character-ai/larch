# step-architectural-guidelines-prepare

Thin `/implement` architectural-guidelines legacy helper.

## Contract

The live `/implement` prompt no longer calls this helper from Step 7a. Step 8 compose-time assessment is owned by `python/cli.py ship pr`, which materializes the final diff after pre-PR rebase/log prep and requests prompt-side assessment only when needed.

This wrapper remains available for one release for compatibility with old harnesses or paused runs. New prompt paths should use the compose-time gate and `step-architectural-guidelines-write-compose.sh`.
