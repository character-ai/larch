### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: docs/linting.md:190-204, docs/linting.md:272
- **Concern**: 4. New Makefile harness is not added to the canonical linting documentation. Scenario: The plan registers test-parse-codex-usage in Makefile, but docs/linting.md is the repository's Makefile-target catalog and already documents adjacent token and launcher harnesses; leaving it stale weakens discoverability and standards consistency.
- **Proposed resolution**: Add a docs/linting.md row for make test-parse-codex-usage and update adjacent token/launcher harness descriptions to mention per-bucket Codex JSONL coverage.


### [Plan Review] FINDING_21

### FINDING_21:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-external-agent.sh:220-277
- **Concern**: Wrapper stdout lines mix into events.jsonl sidecar. Scenario: Runs with wrapper noise but no usage events record zero cost with no ledger row
- **Proposed resolution**: Document in parse-codex-usage.md; add noisy-interleave fixture; track stderr-routing follow-up


### [Plan Review] FINDING_41

### FINDING_41:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/run-negotiation-round.sh:84-85; scripts/lint-fix-loop.sh:160-162; scripts/check-reviewers.sh:197-200
- **Concern**: Stated wherever Codex is launched scope ignores direct codex exec call sites. Scenario: User-visible direct Codex lanes keep no JSON/per-bucket capture, while health probes need an explicit exclusion, leaving partial coverage ambiguous
- **Proposed resolution**: Grep codex exec in the plan, classify each direct call as excluded probe or update it to use the helper/ledger; narrow the stated goal if only three launchers are intended


### [Plan Review] FINDING_54

### FINDING_54:
- **Reviewer(s)**: Codex-dyn-stub-audit
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-launch-review.sh:603-618
- **Concern**: Finding 6: the seven cited test-launch-review stub line numbers include line 603, which is only a comment; the actual stdout-emitting stub is line 618. Scenario: The plan describes seven codex stubs, but rg shows six token-emitting printf sites at 174, 559, 618, 803, 872, and 973, with 603 duplicating the stdout-stub reference as prose
- **Proposed resolution**: Revise the plan to say six stubs plus the adjacent comment at 603 that must be updated; retain each existing --output-last-message write before emitting the JSONL usage event


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:149-151
- **Concern**: Stdout auth-classification regression test is review-only. Scenario: `launch-codex-implement.sh` also classifies auth from `SIDECAR_LOG` after the same stderr split; a Codex regression there would not be caught by `test-launch-review.sh` alone
- **Proposed resolution**: Add a stub case to `test-codex-implementer.sh` or document why implement auth patterns are identical and covered indirectly


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:77-105
- **Concern**: Three launchers will duplicate KV parsing from helper stdout. Scenario: Drift risk across `launch-review.sh`, `launch-codex-implement.sh`, and `launch-codex-ci.sh` (wrong `cache_read` mapping or dropped fields)
- **Proposed resolution**: Extract a tiny sourced helper (e.g. `scripts/lib-parse-codex-kv.sh`) or document one canonical awk/`while read` block reused by all three launchers


