### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:72-83
- **Concern**: Acceptance and testing name `make test-cleanup` but the plan never wires a Makefile target and none exists today. Scenario: No `test-cleanup:` recipe in `Makefile`; `test-harnesses-12` omits it while `docs/linting.md:284` claims it runs there — implementer gate fails or harness never runs in CI
- **Proposed resolution**: Add `test-cleanup` target (`bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh`), append to `test-harnesses-12` and `.PHONY`, or change acceptance to direct `bash skills/cleanup/scripts/test-cleanup.sh`

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:234
- **Concern**: Plan omits SECURITY.md sync while removing clock-fatal exit, per-entry find fail-closed, and depth-5 activity scan. Scenario: Auditors/operators still read depth-5 / date-fatal / per-entry skip guarantees; trust model diverges from post-change cleanup (including silent global find no-op)
- **Proposed resolution**: Add SECURITY.md to Files to modify: replace depth-5 and date-fatal prose with top-level mtime via find -mtime, document exit 0 on enumeration failure, keep symlink and dangling-reap bullets

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:73-83
- **Concern**: Acceptance requires make test-cleanup but plan does not wire the harness into Makefile. Scenario: Repo has skills/cleanup/scripts/test-cleanup.sh and docs/linting.md documents make test-cleanup, yet Makefile has no test-cleanup target and test-harnesses-12 does not invoke it; PR can pass relevant-checks while new cases never run in CI
- **Proposed resolution**: Add Makefile step: test-cleanup target, .PHONY entry, and test-harnesses-12 prerequisite (or fix acceptance to bash skills/cleanup/scripts/test-cleanup.sh and align docs)

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:234
- **Concern**: Plan omits SECURITY.md while retention semantics change. Scenario: Paragraph still documents depth-5 newest-activity scan per-entry find fail-closed skip date +%s fatal exit and -L guard; post-PR code uses top-level find -mtime no clock-fatal path and ! -type l — auditors and operators read stale trust-boundary text
- **Proposed resolution**: Add ### UPDATED: SECURITY.md:234 — replace depth-5/date/per-entry-scan sentences with top-level mtime via find -mtime +N note tmp entries use ! -type l (not -L on glob) and drop date-fatal / per-entry activity-scan failure bullets; add SECURITY.md to cleanup.md Edit-in-sync list

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:4,90; docs/linting.md:284; plan.txt:72-75,81-83
- **Concern**: Plan gates on `make test-cleanup` but no Makefile recipe exists and `test-harnesses-12` does not invoke the harness. Scenario: `.PHONY` lists `test-cleanup` (Makefile:4) with no `test-cleanup:` target; shard 12 runs `test-cleanup-tmpdir` only (Makefile:90). `docs/linting.md:284` still claims the harness is a lint prerequisite via that shard. Plan acceptance/testing require `make test-cleanup` without wiring it, so stdout-contract harness edits in `skills/cleanup/scripts/test-cleanup.sh` are not exercised by `make lint` / `bash scripts/relevant-checks.sh`
- **Proposed resolution**: Add a minimal Makefile block: `test-cleanup` recipe → `bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh`, add `test-cleanup` to `test-harnesses-12`, and align `docs/linting.md:284` (plan already updates that row’s depth wording)

### OOS_1:
- **Description**: `/cleanup` trust-boundary prose still documents depth-5 activity scan clock-fatal exit and per-entry find fail-closed skip. Scenario: Post-PR SECURITY.md contradicts runtime: no `date +%s` fatal path no descendant scan no per-entry skip-on-find-failure — auditors misread deletion guarantees
- **Reviewer**: unknown-slot
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:234
- **Phase**: design
