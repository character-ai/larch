# test-architectural-guidelines-step

Thin `/implement` architectural-guidelines regression harness.

## Purpose

Verifies the combined Phase A prepare helper, explicit retirement of the read and materialize wrappers, prepare exit-code routing prose, and staged-to-durable pin behavior.

## Callers

`make lint` runs this harness through the script sibling checks. `skills/implement/SKILL.md` owns the prompt-side sequencing. The Python CLI owns parsing, path checks, staged assessment writes, durable pinning, and invalidation.

## Harness

`skills/implement/scripts/test-architectural-guidelines-step.sh` pins the prompt-side staging prose, retired wrapper absence, prepare routing, and staged-to-durable copy behavior.
