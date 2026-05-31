### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:234
- **Concern**: Plan SECURITY.md rewrite lists replacement retention facts and two preserve clauses but not the still-accurate outer-loop enumeration fail-open sentence. Scenario: Implementer may drop Age-pass find enumeration errors are swallowed while adding nested-scan fail-safe; auditors conflate per-entry skip-deletion with enumeration abort or miss that cleanup exits 0 when top-level find fails
- **Proposed resolution**: Add explicit KEEP for enumeration-error swallowing (and dangling-symlink reap / pgrep informational sentences) in the SECURITY.md plan step, or scope the edit to retention-enumeration sentences only

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:234; plan.txt ### UPDATED SECURITY.md
- **Concern**: SECURITY.md rewrite omits preserving top-level enumeration find-failure semantics. Scenario: The plan’s replacement text documents nested-scan warn-and-skip but its preserve list only names symlink and secrets sentences. Today’s paragraph also documents that cache/tmp enumeration `find` errors are swallowed (`2>/dev/null`, loop `|| true`) with exit 0 and zero counts — behavior that remains at `cleanup.sh:58` and `:107` and is distinct from per-entry `should_remove_by_age` fail-safe. A full paragraph swap per the plan can drop that operator contract.
- **Proposed resolution**: Operator sees exit 0 and `CACHE_REMOVED=0` after a permission/I/O failure on the cache enumeration `find`, with no stderr signal, and cannot tell enumeration failure from an empty stale set (differs from nested-scan failure, which warns per entry). Extend the SECURITY.md plan step: explicitly retain (or restate) enumeration-swallowed semantics alongside the new nested-scan fail-safe and depth-5 tradeoff bullets.

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: correctness
- **Location**: SECURITY.md:234
- **Concern**: SECURITY.md update omits explicit preservation of the "enumeration errors are swallowed" sentence. Scenario: The plan replaces the paragraph containing both the wrong enumeration claim and the accurate "Age-pass `find` enumeration errors are swallowed (`2>/dev/null` on `find`, `|| true` on the read loop) — cleanup exits 0 and deletions may no-op with counts 0 rather than aborting" sentence. The plan says to preserve "never-delete-through-symlink" and "unredacted-secrets" sentences but does not name this accurate claim, so an implementer rewriting the paragraph may drop it.
- **Proposed resolution**: Add an explicit "Preserve the enumeration-error-swallowing sentence ('Age-pass `find` enumeration errors are swallowed …')" instruction to the SECURITY.md update step, alongside the existing preserve directives for the never-delete-through-symlink and unredacted-secrets sentences.

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/cleanup/scripts/cleanup.md:21
- **Concern**: Plan rewrites retention invariants but instructs keeping the Edit-in-sync bullet verbatim with "top-level mtime age checks". Scenario: After landing, the contract doc describes bounded nested-activity deletion in Invariants while Edit-in-sync still tells maintainers to sync on "top-level mtime age checks," inviting the same doc drift this PR fixes
- **Proposed resolution**: When updating Invariants, reword the Edit-in-sync trigger to nested-activity / maxdepth-5 retention (same file touch; no runtime change)

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: correctness
- **Location**: SECURITY.md:234
- **Concern**: Plan "Preserve" list for the `/cleanup` retention paragraph omits the accurate outer-enumeration error sentence. Scenario: The paragraph contains "Age-pass `find` enumeration errors are swallowed (`2>/dev/null` on `find`, `|| true` on the read loop) — cleanup exits 0 and deletions may no-op with counts 0 rather than aborting." This describes outer-loop enumeration failure (lines 58, 107 in cleanup.sh), distinct from the new nested-scan fail-safe the plan adds. The plan's "Replace with … Preserve [never-delete-through-symlink and unredacted-secrets]" instruction does not name this sentence; an implementer following the "Replace with" template as a full paragraph rewrite drops it.
- **Proposed resolution**: Add to the SECURITY.md plan instruction: also preserve the "Age-pass `find` enumeration errors are swallowed" sentence (describes outer-enumeration behavior, distinct from the nested-scan fail-safe added by this change).

### OOS_1:
- **Description**: Age is measured by each entry's top-level mtime persists after plan lands. Scenario: `docs/skills.md` is manually maintained (not auto-generated from SKILL.md), is covered by `scripts/test-quick-mode-docs-sync.sh` as a checked public doc but "top-level mtime" is not in STALE_PHRASES — so no CI guard catches it. After the plan corrects five files, docs/skills.md remains directly contradictory to all of them.
- **Reviewer**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/skills.md:47
- **Phase**: design
