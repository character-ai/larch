## Decision 1: Brainstorm auto-enable semantics
- **Question**: When the issue title starts with "Brainstorm" (case-insensitive), should brainstorm mode be auto-enabled even if `--brainstorm` was NOT passed on argv?
- **Resolution**: Yes. Print a bold info banner and set `brainstorm_requested=true` regardless of argv. Continue execution normally.
- **Source**: user

## Decision 2: [... Report] regex semantics
- **Question**: What exact regex should the new `[... Report]` rejection use?
- **Resolution**: Match the existing larch convention. The only surviving filter today is the jq regex `^\[.*report\] ` (case-insensitive) at skills/issue/scripts/list-issues.sh:148. Extract a shared helper that both the dedup-skip and the new /design rejection consume.
- **Source**: user

## Decision 3: Resume behavior for [DESIGNING]/[DESIGNED] titles
- **Question**: Should /design still reject titles with [DESIGNING]/[DESIGNED]/[IMPLEMENTING]/[DONE] prefix even when the body has a `larch:plan` block (legitimate resume case)?
- **Resolution**: Yes — always reject. Title prefix is the sole signal. Operators wanting to resume an interrupted run must manually rename the title back.
- **Source**: user

## Decision 4: Brainstorm prefix case sensitivity
- **Question**: Should the "Brainstorm" trigger match case-insensitively?
- **Resolution**: Yes — match `[Bb][Rr][Aa][Ii][Nn][Ss][Tt][Oo][Rr][Mm]` (same case-insensitive treatment as the 5 reject prefixes).
- **Source**: user

## Decision 5: Feature scope (helper extraction)
- **Question**: Should the implementation extract a shared helper and migrate the existing list-issues.sh report-prefix filter to use it, or keep the new check inline in /design Step 0b?
- **Resolution**: Extract a shared helper. The new helper replaces the duplicated regex logic between /issue dedup snapshot and the new /design Step 0b filter. Both callers reference one source of truth.
- **Source**: user

## Decision 6: Tier classification
- **Question**: Given the scope includes new .sh helper + .sh client refactor + new tests (NOT doc-only), should we re-tier away from --trivial?
- **Resolution**: Keep --trivial despite scope-tier mismatch. Operator explicitly chose to proceed.
- **Source**: user

## Decision 7: Audit findings (no migration required)
- **Question**: User's premise that scripts under skills/fix-issue/scripts/ still exist and need migration — is this correct?
- **Resolution**: No. `skills/fix-issue/` is fully deleted. Only stale references survive (CHANGELOG history, committed larch-logs/ artifacts, one orphan comment at skills/issue/scripts/add-blocked-by.sh:13). The remaining live report-prefix filter is in skills/issue/scripts/list-issues.sh:148 only. The "migration" step in the user's original instruction reduces to "extract a shared helper" (still in scope) plus "clean the orphan comment in add-blocked-by.sh" (in scope).
- **Source**: codebase
