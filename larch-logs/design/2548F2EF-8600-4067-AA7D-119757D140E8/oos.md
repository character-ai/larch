### OOS_1: Add new validator harnesses to docs/linting.md harness-table
- **Description**: `docs/linting.md:206-280` documents the existing /design harness entries (`test-design-driver`, `test-emit-plan`, etc.) with operator-facing table rows and shard annotations. The new `make test-parse-plan-commands` / `test-validate-plan-commands` targets should get equivalent rows; plan only names `Makefile`. Discoverability gap only.
- **Reviewer**: Cursor-Arch, Cursor-dyn-lint-registration (and broader docs-linting reviewers)
- **Vote tally**: pending
- **Phase**: design


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: Regenerate docs/topology.md after updating skills/shared/topology.tsv
- **Description**: `docs/topology.md` is auto-generated from `skills/shared/topology.tsv` via `bash scripts/generate-topology-docs.sh`. Plan updates only the TSV but not the regenerated doc. `docs/topology.md` will drift until next regeneration cycle.
- **Reviewer**: Cursor-Edge
- **Vote tally**: pending
- **Phase**: design


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: Optional refinement — run validator after every `revise-plan-with-waterfall.sh` invocation
- **Description**: Issue body explicitly flags this as "open for /design refinement". FINDING_4 addresses the bulk case (post-Gate-B EMIT_PLAN) but plan does not address inner per-finding waterfall revisions inside Gate B's `Apply per-finding` loop. Worth considering as a follow-up once FINDING_4 lands.
- **Reviewer**: Cursor-Requirements
- **Vote tally**: pending
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: Hybrid validation alternative — `shellcheck` / `bash -n` on fenced bodies + generated flag manifest
- **Description**: The custom parser + `--help` grep approach will drift as repo scripts evolve their CLI. A complementary path: lay `bash -n` (syntax check) and `shellcheck` over fenced bodies, AND maintain a generated flag manifest (e.g., emit `--help`-extractable manifest at lint time, cache for validator). Lower drift, higher coverage at cost of one more dependency (shellcheck) and a generated artifact. Worth considering as a v2 enhancement issue.
- **Reviewer**: Cursor-Innovation
- **Vote tally**: pending
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: Optional refinement — validator in `/implement` Preflight
- **Description**: Step 1c Q3 declared this out of scope. Recorded here as a known follow-up: validate the `larch:plan` block when `/implement` reads it, catching hand-edited plans that bypassed /design. Issue-#2674 ships /design coverage only.
- **Reviewer**: (synthesis carry-over from /design Step 1c)
- **Vote tally**: pending
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: TSV escaping/charset contract for parse-plan-commands.sh
- **Description**: Plan's TSV doesn't define escaping for tab/newline/quote in script paths or flag values. While script paths in this repo don't contain such characters today, the contract gap could break downstream consumers if a future plan introduces unusual paths. Documenting the constraint (e.g., "paths/flags MUST NOT contain tab or newline; parser rejects otherwise") satisfies the gap with minimal effort.
- **Reviewer**: Cursor-Innovation
- **Vote tally**: pending
- **Phase**: design

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

