### [Plan Review] FINDING_2

### FINDING_2: Duplicated-contract clusters do not require a single-sourcing fix
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The report-contract validator could accept a duplicated-contract cluster that mentions parallel parsers or copied field names but does not explicitly prescribe single-sourcing as the class fix, leaving a required corrective action unenforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the deterministic report contract and fixture coverage to reject duplicated-contract clusters that lack an explicit single-sourcing class fix


### [Plan Review] FINDING_3

### FINDING_3: `--zones-only` does not forward the resolved search query
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The planned `--zones-only` path can resolve a zone-specific query without setting the state that causes Step 2 to pass `--search`, so `prepare` may fall back to the default `[BUG] in:title` query instead of using the requested zones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit Step 1 --zones branch that sets SEARCH_EXPLICIT=true and RESOLVED_SEARCH from the zone CLI; pin that wiring in scripts/test-learn-from-bugs-structure.sh.


### [Plan Review] FINDING_4

### FINDING_4: Section 2 headline ordering conflicts with the existing intro text
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The report contract requires the generated origin headline to be Section 2’s first content block, while the documented template places introductory prose on the section line before that headline. The plan does not establish which layout is authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define one Section 2 layout: headline immediately after the section heading (relocate or remove the intro sentence), and make the validator and structural harness pin that exact order.


### [Plan Review] FINDING_5

### FINDING_5: The report-contract validator has no executable CLI wiring
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: major
- **Concern**: The plan requires validation before printing, marker persistence, or filing but does not specify the validator subcommand, arguments, output grammar, failure behavior, or exact Step 4 invocation. Implementations could therefore omit or inconsistently wire the check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify the cli.py subcommand, argv/stdout contract, non-zero failure behavior, and the exact Step 4 fence that passes ORIGIN_HEADLINE_PATH plus ${RUN_DIR}/report.md.
  - From Codex-Innovation: Add the exact `python3 ... learn-from-bugs validate-report` command, its required inputs, whole-line result grammar, nonzero failure handling, and place it after report generation but before printing, marker persistence, or filing


### [Plan Review] FINDING_6

### FINDING_6: Guideline-only residual clusters can omit the required prose-only warning
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Validation that checks only markers already present succeeds vacuously when a report omits `prose-only prevention: unlikely to stick`. A guideline-only residual cluster can therefore pass without the required warning, citations, and mechanical-alternative or explicit-no-alternative line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Pass the validator enough expected residual metadata to identify guideline-only clusters, or add a deterministic per-cluster residual-kind marker and reject any guideline-only cluster lacking the exact warning, citations, and mechanical-alternative line
  - From Codex-Pragmatic: Add a narrow check that identifies guideline-only residual clusters from a small explicit report grammar and requires the marker and mechanical-alternative line. Add the mandated fixture where a guideline-only cluster without the marker fails validation
  - From Codex-Requirements: Make validation detect guideline-only residual clusters and require the marker and alternative line, or add another deterministic artifact that identifies which clusters require the marker and validate the report against it.


