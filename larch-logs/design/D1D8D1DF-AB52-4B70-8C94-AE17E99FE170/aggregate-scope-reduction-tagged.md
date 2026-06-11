### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:19-23,120-132,736-739
- **Concern**: [SCOPE-REDUCTION] Public generic artifact profile over-expands this SIMPLE change. Scenario: The /implement feature can ship with pinned artifacts plus reusable internals; adding public --profile generic path, vocabulary, and evidence override surfaces creates extra CLI and path-validation scope before the /design port uses it
- **Proposed resolution**: Keep internal constants or helper functions for later reuse, document the intended /design parameters, and defer public generic-profile flags and generic-profile tests to #3992

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report.sh (plan.txt:120-132,289-292,736-739)
- **Concern**: [SCOPE-REDUCTION] Public generic artifact profiles and test-only overrides over-serve the SIMPLE lane. Scenario: The issue requires /implement reporting plus reuse seams for future /design adoption, not a new public profile API with generic swapping tests in this PR
- **Proposed resolution**: Keep the canonical /implement CLI and add only the named reuse seams needed by this change. Defer public generic profile flags, artifact-prefix swapping, and test-only override machinery to #3992 unless a current /implement caller needs them

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:88-91,455-457,611-615,695
- **Concern**: [SCOPE-REDUCTION] Python ledger-ready sidecar creates a second handoff protocol. Scenario: The Python driver already emits one JSON stdout object; a tmpdir sidecar can be stale, missing, or read from the wrong invocation before Main Claude edits, causing missed or duplicate ledger rows
- **Proposed resolution**: Require Python ledger-ready fields inside the existing JSON envelope only; delete the sidecar option and its tests/docs

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:19-23,120-132,736-739
- **Concern**: [SCOPE-REDUCTION] Public generic artifact profile flags overexpose future /design reuse. Scenario: /implement can ship with canonical paths and internal reusable helpers; public generic flags add path and vocabulary override surface, containment checks, and tests for a non-goal /design caller
- **Proposed resolution**: Keep an internal profile table or factorization only; expose the /implement CLI now and defer public generic flags to #3992 when /design wires in

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-cross-surface-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:204-217,580-601,715; skills/implement/scripts/stall-recovery-report.sh:543-555,1258-1288; scripts/ship-pr.sh:1259-1264,1820-1822; scripts/ci-decide.sh:84-139; python/config.py:40-45; skills/implement/references/codex-manifest-schema.md:71-91
- **Concern**: [SCOPE-REDUCTION] Tier B bail-token union and ci-local-unfixable grammar are planned as parallel alignments, not one canonical source with explicit lint comparisons. Scenario: Current lint only compares TSV, code, and doc allowlist rows, while real token sources live in bash, Python, ci-decide, bootstrap, and manifest docs; a new or renamed emitter can remain outside the Tier B union and render as redacted, violating the full bail-token enum requirement while lint still passes
- **Proposed resolution**: Revise the plan to name one canonical Tier B token export and one compound grammar constant; have stall-recovery-report.sh lint compare the TSV/rendering projection against python/config.py, scripts/ship-pr.sh needs_user_bail_reason, scripts/ci-decide.sh emitters, and the other listed sources; have Python and bash validation/tests read or compare against that same export rather than duplicating the regex

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-cross-surface-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:92-100,446-454,470-489,740-748; scripts/lint-fix-loop.sh:516-519,575-582; scripts/lint-fix-loop.md:17-32,145-156; scripts/run-step5-review.md:1-50
- **Concern**: [SCOPE-REDUCTION] LINT_FIX_LEDGER_* contract is repeated across emitter, prompt parser, docs, and tests without a canonical field list or parity check. Scenario: If one surface uses a different KV name, prompt-side Step 3, Step 5, or Step 6 can miss a main-agent-required handoff; the run can succeed without recording the escalation, so requirement 2 is incomplete
- **Proposed resolution**: Define the eight LINT_FIX_LEDGER_* names once in a small contract helper or table; make lint-fix-loop.sh emission, SKILL.md parsing docs, run-step5-review.md docs, and tests compare to that list; avoid separately maintained enumerations
