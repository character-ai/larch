# test-cache-key-runtime-audit.sh

**Purpose**: Regression harness for `scripts/cache-key-runtime-audit.py`. It builds minimal transcript fixtures and verifies BASELINE, EXPECTED-GROWTH, CACHE-INVALIDATING, and missing-log-root behavior.

**Primary callers**: `make test-cache-key-runtime-audit`, plus `make test-harnesses-7`.

**Contract owner**: `scripts/cache-key-runtime-audit.md` remains the primary audit contract for classifications, inputs, and report semantics.

**Edit-in-sync**: When changing stable-prefix selection, classification labels, CLI error behavior, or Makefile wiring for the runtime audit, update this harness and document in the same PR.
