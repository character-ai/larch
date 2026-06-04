### [Plan Review] FINDING_2

### FINDING_2: WARN replay rc gate lacks explicit structure coverage
- **Reviewer(s)**: Codex-dyn-exit-code-threading
- **Severity**: latent
- **Concern**: The plan explicitly covers rc 4 handling in several places, but omits a structure pin for driver WARN replay after the Step 5c retry loop settles, leaving its skip/run behavior for rc 4 or Cancel under-specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-exit-code-threading: Add a narrow plan bullet: Driver WARN replay runs only after the Step 5c rc-4 retry loop settles to latest `_publish_rc` ∈ {0,1,3}, and is skipped on rc 4/Cancel; add a matching `scripts/test-design-structure.sh` grep.


### [Plan Review] FINDING_3

### FINDING_3: Planned tests miss stale rc-4 result-env quarantine
- **Reviewer(s)**: Codex-dyn-parse-state-lifecycle
- **Severity**: latent
- **Concern**: Planned `test-design-publish` updates do not exercise the stale `VALIDATE_STATUS=defects-found` result-env scenario before retry or skip-validate, even though the plan depends on stale env removal and stdout-authoritative parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-parse-state-lifecycle: Add one narrow stale-env case, or state that this edge is intentionally covered by scripts/test-design-structure.sh because the quarantine lives in SKILL.md rather than design-publish.sh

