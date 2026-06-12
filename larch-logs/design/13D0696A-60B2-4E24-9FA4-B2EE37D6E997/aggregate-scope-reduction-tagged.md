### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:401-447
- **Concern**: [SCOPE-REDUCTION] Prompt-side Codex sidecar ingestion is expanded into research validation and voter markdown orchestrator docs. Scenario: Those paths are not launcher call sites and are not enforced by scripts or CI. A rates-and-drafter fix can ship while research validation and judge lanes still omit retry sidecars. The plan adds ~400 lines of orchestrator prose beyond the approved outline surfaces.
- **Proposed resolution**: Limit ledger-completeness edits to script-owned call sites named in the issue audit (launch-codex-exec launch-codex-ci launch-codex-drafter design-step2b-drafter ship-pr lint-fix auto-fix). File follow-up issues for prompt-side retry matrices.

### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:37-43
- **Concern**: [SCOPE-REDUCTION] Plan treats scope-files.txt as a repo file to update, but no such repo file exists. Scenario: Implementer may create or edit a bogus root file instead of updating the design scope manifest, leaving the actual implementation scope declaration wrong
- **Proposed resolution**: Remove the ### UPDATED: scope-files.txt file entry. Keep scope-manifest updates as design metadata, or name the real staged-context scope artifact outside the repo file list

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:1-855
- **Concern**: [SCOPE-REDUCTION] The plan grew to ~1235 diff lines across 50+ surfaces while the bound issue is a SIMPLE-tier rate fix plus drafter ledger gap and drift guard.. Scenario: It ships the core pricing correction buried in research/validation voter retry-glob prose, a new Makefile target, and broad launcher model threading that the acceptance checks do not require.
- **Proposed resolution**: Phase 1: `python/report_tokens_cost.py`, drift test, docs/fixtures, drafter + autofix + lint-fix + ship-pr recovery ingestion only. Defer `skills/research/references/research-phase.md`, `validation-phase.md`, nested NOT_SUBSTANTIVE glob rules, and `test-design-step2b-drafter` Makefile wiring.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:120-255
- **Concern**: [SCOPE-REDUCTION] `MODEL=` threading through every Codex/Cursor launcher is prep for out-of-scope per-record pricing, not required to fix wrong defaults or the drafter gap.. Scenario: The issue needs `DEFAULT_VENDOR_MODEL` aligned with `agent-model-args.sh` and optional model on new sidecars; touching `launch-review.sh`, `launch-codex-implement.sh`, `run-negotiation-round.sh`, `review-and-fix.sh`, etc. multiplies review risk without changing repriced totals today.
- **Proposed resolution**: Limit model capture to new sidecar producers/consumers (drafter, autofix, CI sidecars, shared helper) plus the sanitized drift test; skip retroactive model fields on direct-ledger paths until per-record pricing is in scope.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/dialectic-protocol.md:449-461
- **Concern**: [SCOPE-REDUCTION] Codex judge ledger ingestion is prompt-only; HARD `/design` still depends on the orchestrator reading updated markdown during Step 2a.5.. Scenario: `launch-codex-exec.sh` judge launches write `${OUTPUT}.token-record` but today nothing mechanical ingests them; prose in `dialectic-protocol.md` alone does not satisfy the issue audit or live `token report` (ledger-driven) completeness for judge spend.
- **Proposed resolution**: Add one shared sidecar-ingest helper and call it from the Step 2a.5 judge collection fence (or `dialectic-execution.md` host script), mirroring the mechanical `design-step2b-drafter.sh` pattern; keep `dialectic-protocol.md` as documentation only.

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:86-278
- **Concern**: [SCOPE-REDUCTION] Repo-wide model metadata threading exceeds the approved SIMPLE pricing drift guard. Scenario: The approved outline needs DEFAULT_VENDOR_MODEL plus a consistency test, but the plan changes TokenLedger schema, token record-vendor CLI, launcher helper arity, and many direct-ledger launchers even though pricing still ignores per-record model
- **Proposed resolution**: Drop model field plumbing, helper arity changes, and launcher/test churn. Keep the pricing table DEFAULT_VENDOR_MODEL map and the sanitized agent-model-args.sh consistency test

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:401-467
- **Concern**: [SCOPE-REDUCTION] Prompt-only Codex sidecar ingestion across research/validation/voting/judge docs is not mechanically enforced. Scenario: Updates to `skills/research/references/*.md`, `skills/shared/voting-protocol.md`, and `skills/shared/dialectic-protocol.md` rely on the orchestrator following prose. Missed ingestion or double-ingestion will not fail CI; `#3689` acceptance only requires `/design` `codex_plan_draft` plus rate authority.
- **Proposed resolution**: Limit this PR to shell/Python hooks with harness coverage (Step 2b drafter, autofix, lint-fix, ship recovery). File follow-up issues for prompt-side collector ingestion, or add a single shared ingestion helper invoked from existing wrapper scripts instead of markdown-only instructions.
