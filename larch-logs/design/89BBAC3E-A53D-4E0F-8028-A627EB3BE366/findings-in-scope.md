### FINDING_1: Partial-audit approval has no Step 5→6 handoff
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: Step 4 can run the deps plan before AskUserQuestion, but `dependency_writes_allowed` stays false until the plan carries `partial_audit_approved=true` after the Step 5 second confirmation. Step 6 deps apply has no verb to set or accept that flag, so after `--pair-cap` and operator "Approve all" plus second confirmation, apply still sees `dependency_writes_allowed=false` and skips all edge writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After --pair-cap and operator Approve all plus second confirmation, apply still sees dependency_writes_allowed=false and skips all edge writes Add an explicit post-approval step: re-run deps plan --partial-audit-approved, deps approve-plan, or deps apply --partial-audit-approved immediately before Step 6 when the operator confirms a partial audit

### FINDING_2: In-flight issues (e.g. [DESIGNED]) are not gated from rewrites/closes
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Mutability gating is underspecified and would allow deps to rewrite, close, or add blocked-by edges to in-flight issues. Apply-time skip logic cites `combine_issues._source_close_skip_reason`, which only rejects busy-prefix titles and never checks `[DESIGNED]`, `[OOS]`, or other in-flight groups. Separately, `_is_mutable_regular` is specified to mirror only `combine_issues._BUSY_RE` and `_OOS_RE`, but `_BUSY_RE` excludes `[DESIGNED]` by design (combine-issues keeps `[DESIGNED]` eligible), so deps would treat `[DESIGNED]` as mutable REGULAR and may mutate those issues, violating the in-flight dependency rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: At apply (and plan validation), gate rewrites/closes solely on `_is_mutable_regular(title)` / display group; treat the `_source_close_skip_reason` mention as open-state-only or drop it
  - From Cursor-Pragmatic: Define _is_mutable_regular as not in {DESIGNING,DESIGNED,IMPLEMENTING} display groups AND not matching _BUSY_RE/_OOS_RE; wire _plan_edge and apply revalidation through the same helper; add tests for [DESIGNED]

### FINDING_3: explicit-refs comment scan is underspecified vs fail-closed combine_issues behavior
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan's explicit-refs comment scan is underspecified ("when available") compared to `combine_issues` fail-closed comment reads. Comment-only prose blockers (`depends on #N`, `Blocks #N`) can be silently dropped when per-issue comment fetch is skipped or degraded, violating the requirement to infer dependencies from every issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Match `combine_issues.prose_audit_main`: paginate comments per open issue during `explicit-refs` (or bulk-fetch in `deps fetch`), record per-issue warnings, and fail closed when comment reads fail unless the operator explicitly opts into body-only mode

### FINDING_4: Rewrite outbound path lacks plan/control-marker neutralization
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The rewrite outbound path cites "issue_wire redaction helpers" for control-marker neutralization, but `issue_wire` only strips known `larch:*` named blocks and runs secret redaction. A REGULAR refresh that preserves a `### NEW:` / `### UPDATED:` line or `<!-- larch:plan:start -->` block can republish machine-parsed plan/control grammar into GitHub and mislead later `/design` or `/implement` parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name the concrete pre-edit steps: zero-width neutralize leading `###` lines (reuse `decompose._neutralize_markdown_h3_line_starts`), strip or escape `<!-- larch:* -->` markers, then `redact.redact_secrets_only` before `gh issue edit`

### FINDING_5: Skill steps omit required --output-file arguments for deps CLI verbs
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Skill steps omit required `--output-file` arguments for `deps fetch` and `deps explicit-refs`. If implemented literally, Step 1 or Step 2.5 calls the new CLI with missing required args, so the skill cannot reach planning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Call deps fetch with --output-file "$DEPS_TMPDIR/fetch.json" and deps explicit-refs with --output-file "$DEPS_TMPDIR/explicit-edges.json"

### FINDING_6: Plan omits strict-permissions entries for /deps
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits strict-permissions entries for the new public skill. Strict-permissions consumers are told to allow each public larch skill explicitly; `/deps` would be undocumented and may be denied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Update docs/configuration-and-permissions.md with Skill(deps) and Skill(larch:deps) in sorted order

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/deps/SKILL.md:46-55
- **Concern**: [SCOPE-REDUCTION] Plan forbids auto-flipping dependency edges when the desired client is in-flight. Scenario: Issue scope says non-REGULAR in-flight issues cannot receive new blocked-by edges, and when reasonable the potential dependency should be expressed as the blocker via the other direction (mutable REGULAR client, in-flight blocker). Plan instead warns and skips all such edges with an explicit no-flip rule, so dependencies that could be recorded as REGULAR blocked-by in-flight are never proposed or written.
- **Proposed resolution**: Add a bounded flip path in `deps plan` / Step 3: when desired `(client, blocker)` has an in-flight client and a mutable REGULAR blocker, attempt reversed `(blocker, client)` only when prompt-side rationale shows the reversed scheduling constraint matches the evidence; otherwise keep the loud warning and skip.

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:3,129,145,153,209-210,271-274
- **Concern**: [SCOPE-REDUCTION] Plan adds stale issue closes beyond the requested REGULAR issue rewrite flow. Scenario: A /deps run can close open issues as not planned, adding a destructive mutation path not required for the exported audit skill
- **Proposed resolution**: Remove stale-close proposal, apply, docs, tests, and security paths; keep body rewrites only for stale or inaccurate REGULAR issue parts

### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:65-75,108,116,136,149-151,203,258,278,286,295-297,355
- **Concern**: [SCOPE-REDUCTION] Optional --pair-cap partial-audit mode conflicts with the all-open-issues audit scope. Scenario: The feature asks to audit all currently open issues, but the plan adds a partial mode with extra approval and dependency-write state
- **Proposed resolution**: Remove --pair-cap and partial-audit branches; keep the default complete explicit-ref plus latent dependency audit
