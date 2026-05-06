# scripts/test-generate-topology-docs.sh - contract

Offline regression harness for `scripts/generate-topology-docs.sh`. It exercises write mode and `--check` mode through temporary output files, asserts anchor rendering, verifies drift detection, and covers malformed TSV rows, colon-bearing keys, forbidden display characters, stale authority values, and missing authority paths.

The harness uses the generator's `LARCH_TOPOLOGY_TSV` and `LARCH_TOPOLOGY_DOC` environment overrides so tests can mutate fixture inputs and outputs without changing committed files. The production registry path does not set those variables.

Invoked by `make test-generate-topology-docs` and assigned to a `test-harnesses-N` shard. Keep this file in sync with changes to the generator's TSV schema, validation grammar, or output table shape.
