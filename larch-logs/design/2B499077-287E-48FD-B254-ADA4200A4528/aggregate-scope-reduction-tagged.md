### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:543-598
- **Concern**: [SCOPE-REDUCTION] Collapsing the foreground `step-5-entry.sh` fence and the immediate-background `review-and-fix step5` fence into one background `step-5-review.sh` call defers the Step 5 banner until `<task-notification>`. Scenario: The plan removes orchestrator-side banner printing and emits the banner only from wrapper stdout inside an immediate-background fence. `/implement` anti-halt and `orchestrator-never.md` forbid reading child output before notification, so the operator loses the long-running Step 5 start breadcrumb for the whole review loop. That regresses the current foreground-entry contract and progress-reporting step-start visibility.
- **Proposed resolution**: Keep one Bash call but restore operator-visible banner timing: have the orchestrator print the same byte-stable banner line immediately before launching `step-5-review.sh` (inline the existing cap precedence in SKILL prose), or document an explicit immediate-background carve-out that permits emitting the wrapper's leading banner before the yield.
