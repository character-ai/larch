### OOS_1: Add new validator harnesses to docs/linting.md harness-table
- **Description**: `docs/linting.md:206-280` documents the existing /design harness entries (`test-design-driver`, `test-emit-plan`, etc.) with operator-facing table rows and shard annotations. The new `make test-parse-plan-commands` / `test-validate-plan-commands` targets should get equivalent rows; plan only names `Makefile`. Discoverability gap only.
- **Reviewer**: Cursor-Arch, Cursor-dyn-lint-registration (and broader docs-linting reviewers)
- **Vote tally**: pending
- **Phase**: design

### OOS_4: Hybrid validation alternative — `shellcheck` / `bash -n` on fenced bodies + generated flag manifest
- **Description**: The custom parser + `--help` grep approach will drift as repo scripts evolve their CLI. A complementary path: lay `bash -n` (syntax check) and `shellcheck` over fenced bodies, AND maintain a generated flag manifest (e.g., emit `--help`-extractable manifest at lint time, cache for validator). Lower drift, higher coverage at cost of one more dependency (shellcheck) and a generated artifact. Worth considering as a v2 enhancement issue.
- **Reviewer**: Cursor-Innovation
- **Vote tally**: pending
- **Phase**: design

### OOS_5: Optional refinement — validator in `/implement` Preflight
- **Description**: Step 1c Q3 declared this out of scope. Recorded here as a known follow-up: validate the `larch:plan` block when `/implement` reads it, catching hand-edited plans that bypassed /design. Issue-#2674 ships /design coverage only.
- **Reviewer**: (synthesis carry-over from /design Step 1c)
- **Vote tally**: pending
- **Phase**: design

