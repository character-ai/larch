### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:159-188
- **Concern**: Defects-found exit 4 can be lost if result-env writing fails. Scenario: write_result_env_and_emit currently returns the result-env write status after emitting stdout; under set -e a defects-found branch that calls it before exit 4 can abort with rc 1 or 3, so Step 5c may take the plan-write/result-env path instead of the validator shared handler
- **Proposed resolution**: Make the defects-found branch best-effort the result-env write but unconditionally exit 4, relying on stdout fallback when the file write fails; add a focused harness case for result-env write refusal on VALIDATE_STATUS=defects-found

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-exit-code-threading
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1521-1527; <TMPDIR>/plan.txt:32-47,89-97
- **Concern**: Driver WARN replay is a current `_publish_rc` ∈ {0,1,3} gate, but the plan's SKILL.md and test-design-structure update lists omit it.. Scenario: rc 4 handling is explicit for items 3-5, Step 5d, and the unexpected guard, but WARN replay sits between the driver contract and item 3; its retry-settled/latest-rc behavior would rely on inference and lacks a structure pin.
- **Proposed resolution**: Add a narrow plan bullet: Driver WARN replay runs only after the Step 5c rc-4 retry loop settles to latest `_publish_rc` ∈ {0,1,3}, and is skipped on rc 4/Cancel; add a matching `scripts/test-design-structure.sh` grep.

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-parse-state-lifecycle
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:398-410
- **Concern**: Planned test-design-publish updates do not cover stale rc-4 result-env quarantine. Scenario: The plan relies on rm -f before every retry and rc-3 stdout-authoritative parsing, but the proposed test-design-publish cases only cover the existing result-env symlink/write-failure path and do not seed a stale VALIDATE_STATUS=defects-found env before a retry/skip-validate attempt
- **Proposed resolution**: Add one narrow stale-env case, or state that this edge is intentionally covered by scripts/test-design-structure.sh because the quarantine lives in SKILL.md rather than design-publish.sh
