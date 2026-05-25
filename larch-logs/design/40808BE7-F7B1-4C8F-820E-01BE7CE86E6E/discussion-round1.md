## Decision 1: Padded-attest rename scope
- **Question**: Should the rename of the misleading padded-attestation test touch only the echo description, or also the stub kind name?
- **Resolution**: Rename echo description AND the underlying stub kind `zero_findings_padded_attest` (and all references in test-aggregate-findings.sh).
- **Source**: user

## Decision 2: New AGGREGATED=true stub kind name
- **Question**: What naming convention should the new merged-blocks-plus-impure-attestation stub kind follow?
- **Resolution**: `merge_plus_impure_attest` — mirrors existing `merge_plus_spurious_attest` for symmetry (pure→rejected, impure→accepted-then-stripped).
- **Source**: user

## Decision 3: File scope
- **Question**: Are changes confined to `skills/review/scripts/test-aggregate-findings.sh`?
- **Resolution**: Yes — the OOS body explicitly names that file; no changes to `aggregate-findings.sh` (the SUT). Only test additions and renames.
- **Source**: codebase + OOS body

## Decision 4: LOC budget
- **Question**: What is the diff-size envelope?
- **Resolution**: < 30 LOC total per OOS estimate (new stanza + new test block + 2 rename touch-ups).
- **Source**: OOS body
