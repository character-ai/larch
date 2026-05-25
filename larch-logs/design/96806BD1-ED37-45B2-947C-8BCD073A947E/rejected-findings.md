### [Plan Review] FINDING_19

### FINDING_19: TSV assembly narrative omits explicit KV-to-column binding / key-scanned parsing rules
- **Reviewer(s)**: Cursor-dyn-schema-wire-consistency
- **Severity**: nit
- **Concern**: Implementers might assume fixed stdout line offsets for `emit_kv` output; extra or reordered KV lines could mis-slot fields unless mapping is key-based.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-schema-wire-consistency: Spell out that tally maps `PARSED_VOTE`→`vN_vote` through `PARSED_UNCERTAIN`→`vN_uncertain` and parses captured stdout by `^PARSED_` keys (ignore unknown keys and rely on key match not line order)

---


### [Plan Review] FINDING_21

### FINDING_21: New Makefile harness target not documented in `docs/linting.md`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: `make test-findings-classification` may be wired into lint shards but absent from canonical maintainer documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a docs/linting.md row for make test-findings-classification near the existing plan-review tally and voter prompt harness entries

---

**Notes for downstream voters (non-binding):** Several clusters (notably **FINDING_1** and parts of **FINDING_8** / **FINDING_12**) contain **contradictory** proposed resolutions across reviewers; the aggregator preserves them verbatim by design. No `### OOS_N:` blocks were present in the supplied input.

### [Plan Review] FINDING_4

### FINDING_4: `JUDGE_ERROR` vs empty `vN_vote` not pinned to one wire value
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: nit
- **Concern**: Prose equates empty parsed vote with `JUDGE_ERROR` while the TSV schema allows empty cells, so consumers cannot distinguish missing vote from malformed vote if both render empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document whether vN_vote stays empty for JUDGE_ERROR or emits the literal JUDGE_ERROR and align parser plus harness fixtures with that choice
  - From Cursor-Requirements: Document whether vN_vote emits literal JUDGE_ERROR or stays empty and align parser tally and fixtures

---


### [Plan Review] FINDING_6

### FINDING_6: Zero judges plus empty ballot intersection / `eligible_count==0` early exit ambiguity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: Early exit when `eligible_count==0` can skip clarifying Decision 1 (per-row) vs Decision 2 (header-only) when `block_files` is also empty, leaving artifact shape non-deterministic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Decide expected artifact (header-only vs rows) and encode it in tally plus a harness case so the intersection is deterministic
  - From Cursor-Arch: Declare expected TSV shape for simultaneous zero judges and zero findings and add a harness assertion

---


