## Decision 1: audit.txt write location
- **Question**: Should `audit.txt` be written only on the refuse path (not on the pass path)?
- **Resolution**: Yes. Repo-wide grep confirms no script consumer reads `audit.txt` on the pass path. The only references are in `preflight-plan-audit.md` (spec) and SKILL.md item 4. Item 4 writes it unconditionally today; the plan will restrict the write to the refuse-path only.
- **Source**: codebase

## Decision 2: scope boundary
- **Question**: Are items 4-7 (plan-adequacy audit, audit-refuse handling, semantic materiality, pass gate) outside the new script?
- **Resolution**: Yes. The new `implement-preflight.sh` covers items 1-3 plus emergency fallback composition. Items 4-7 remain prompt-side in SKILL.md unchanged.
- **Source**: codebase

## Decision 3: strip_lifecycle_prefix availability
- **Question**: Is `strip_one_lifecycle_prefix` (as named in SKILL.md) available in `tracking-issue-write.sh`?
- **Resolution**: The function is named `strip_lifecycle_prefix` (not `strip_one_lifecycle_prefix`) in `tracking-issue-write.sh` line 127. The new script should source that helper or inline the strip logic.
- **Source**: codebase
