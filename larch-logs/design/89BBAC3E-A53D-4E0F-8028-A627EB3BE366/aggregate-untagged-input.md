### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/deps/SKILL.md:142-154
- **Concern**: Partial-audit approval flag has no Step 5→6 handoff. Scenario: Step 4 runs deps plan before AskUserQuestion, but dependency_writes_allowed stays false until plan carries partial_audit_approved=true after the Step 5 second confirmation; Step 6 deps apply has no verb to set or accept that flag
- **Proposed resolution**: After --pair-cap and operator Approve all plus second confirmation, apply still sees dependency_writes_allowed=false and skips all edge writes Add an explicit post-approval step: re-run deps plan --partial-audit-approved, deps approve-plan, or deps apply --partial-audit-approved immediately before Step 6 when the operator confirms a partial audit

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:44-45,208-209
- **Concern**: Apply-time skip cites `combine_issues._source_close_skip_reason` but that helper only rejects busy-prefix titles, not `[DESIGNED]`, `[OOS]`, or other in-flight groups. Scenario: An implementer mirroring `_source_close_skip_reason` could rewrite or close `[DESIGNED]`/`[OOS]` issues after title drift because `_BUSY_RE` omits `[DESIGNED]` and `_source_close_skip_reason` never checks `_OOS_RE` (`python/combine_issues.py:23-24`, `917-933`)
- **Proposed resolution**: At apply (and plan validation), gate rewrites/closes solely on `_is_mutable_regular(title)` / display group; treat the `_source_close_skip_reason` mention as open-state-only or drop it

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:61-63,187-190
- **Concern**: explicit-refs comment scan is underspecified ("when available") vs `combine_issues` fail-closed comment reads. Scenario: Comment-only prose blockers (`depends on #N`, `Blocks #N`) can be silently dropped when per-issue comment fetch is skipped or degraded, violating the issue requirement to infer dependencies from every issue
- **Proposed resolution**: Match `combine_issues.prose_audit_main`: paginate comments per open issue during `explicit-refs` (or bulk-fetch in `deps fetch`), record per-issue warnings, and fail closed when comment reads fail unless the operator explicitly opts into body-only mode

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:84,209
- **Concern**: Rewrite outbound path cites "issue_wire redaction helpers" for control-marker neutralization, but `issue_wire` only strips known `larch:*` named blocks and runs secret redaction. Scenario: A REGULAR refresh that preserves a `### NEW:` / `### UPDATED:` line or `<!-- larch:plan:start -->` block can republish machine-parsed plan/control grammar into GitHub and mislead later `/design` or `/implement` parsers (`python/decompose.py:66-67` is the existing neutralization pattern)
- **Proposed resolution**: Name the concrete pre-edit steps: zero-width neutralize leading `###` lines (reuse `decompose._neutralize_markdown_h3_line_starts`), strip or escape `<!-- larch:* -->` markers, then `redact.redact_secrets_only` before `gh issue edit`

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/deps_audit.py:218-221
- **Concern**: _is_mutable_regular is specified to mirror only combine_issues._BUSY_RE and _OOS_RE. Scenario: combine_issues._BUSY_RE excludes [DESIGNED] by design (combine-issues keeps [DESIGNED] eligible); deps would treat [DESIGNED] as mutable REGULAR and may rewrite/close those issues and add blocked-by edges to them, violating the in-flight dependency rule
- **Proposed resolution**: Define _is_mutable_regular as not in {DESIGNING,DESIGNED,IMPLEMENTING} display groups AND not matching _BUSY_RE/_OOS_RE; wire _plan_edge and apply revalidation through the same helper; add tests for [DESIGNED]

### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:121-132,180-189
- **Concern**: Skill steps omit required --output-file arguments for deps fetch and deps explicit-refs. Scenario: Implemented literally, Step 1 or Step 2.5 calls the new CLI with missing required args, so the skill cannot reach planning
- **Proposed resolution**: Call deps fetch with --output-file "$DEPS_TMPDIR/fetch.json" and deps explicit-refs with --output-file "$DEPS_TMPDIR/explicit-edges.json"

### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:13-38
- **Concern**: Plan omits strict-permissions entries for the new public skill. Scenario: Strict-permissions consumers are told to allow each public larch skill explicitly; /deps would be undocumented and may be denied
- **Proposed resolution**: Update docs/configuration-and-permissions.md with Skill(deps) and Skill(larch:deps) in sorted order
