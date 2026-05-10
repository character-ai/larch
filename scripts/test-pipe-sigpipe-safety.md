# test-pipe-sigpipe-safety.sh

Lint harness that detects SIGPIPE/pipefail anti-patterns in `scripts/test-*.sh`.

**Purpose**: prevent reintroduction of `producer | head` and `bash -c "..." | grep -q` pipelines in pipefail-on test scripts. On Linux, these patterns cause `set -o pipefail` to propagate SIGPIPE (exit 141) as a pipeline failure, producing transient CI failures.

**Primary callers**: `make test-pipe-sigpipe-safety` (Makefile target); also runs as a step in `.github/workflows/ci.yaml` lint job.

**Invariants**:
- Only checks scripts that activate `set -euo pipefail` or `set -eo pipefail` at top level.
- Excludes: comment lines, `|| true` guards, `echo`/`printf` as leftmost producer, here-string (`<<<`) as source, pipeline continuation lines, `| head` inside single-quoted strings.
- Exits 0 when no violations found; exits 1 with `file:line` context on any violation.

**Makefile wiring**: `test-pipe-sigpipe-safety` target; appended to `test-harnesses-7` shard.

**CI wiring**: `Pipe SIGPIPE safety lint` step in the `lint` job of `.github/workflows/ci.yaml`.

**Edit-in-sync**: when adding new safe-exclusion patterns, update the exclusion list in both the script and the Safe exclusions comment block at the top of the script.
