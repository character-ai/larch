### FINDING_1: **Important** correctness: `skills/upgrade-larch/scripts/upgrade-larch.sh:294-314` and `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:217-222` - the cap prune still only inspects the first `VERSION_COUNT - KEEP_LIMIT` sorted entries, so protected entries in that prefix are skipped without pruning replacement candidates. Concrete scenario: the new active-session case seeds `29.1.20`-`29.1.28`, installs `29.1.30`, and pins `29.1.21`; the script removes `29.1.20`, skips pinned `29.1.21`, and leaves 9 cached versions, while the updated test incorrectly expects `29.1.22` to remain. Fix the loop to continue pruning until the retained set is at most 8, skipping protected versions but removing later unpinned candidates, and update the test to assert `29.1.22` is removed in that case.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness: `skills/upgrade-larch/scripts/upgrade-larch.sh:294-314` and `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:217-222` - the cap prune still only inspects the first `VERSION_COUNT - KEEP_LIMIT` sorted entries, so protected entries in that prefix are skipped without pruning replacement candidates. Concrete scenario: the new active-session case seeds `29.1.20`-`29.1.28`, installs `29.1.30`, and pins `29.1.21`; the script removes `29.1.20`, skips pinned `29.1.21`, and leaves 9 cached versions, while the updated test incorrectly expects `29.1.22` to remain. Fix the loop to continue pruning until the retained set is at most 8, skipping protected versions but removing later unpinned candidates, and update the test to assert `29.1.22` is removed in that case.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:163-173 (per round-1 diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Over-cap active-session expectations only prune one directory while KEEP_LIMIT requires two removals from 10 cached versions. Cap-correct script removes 29.1.20 and 29.1.22 but test still requires 29.1.22 to exist → harness fails; or harness passes while cache stays >8 versions → false green. Assert absence of both pruned versions (or adjust seed/pins so only one removal is required); match current workspace if that is the intended final state.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:219-222;skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:265-267
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] active-session and crlf cap-prune assertions require 29.1.22 to remain after upgrade while only requiring 29.1.20 to be pruned 10 cached version dirs with KEEP_LIMIT=8 and only 29.1.21 pinned/executing: upgrade-larch.sh removes 29.1.20 then 29.1.22; the test loops still demand 29.1.22 exist so the harness fails on a correct run Add a second prune assertion for 29.1.22 (and remove it from the keep list), add a multi-pin variant, or seed fewer than 10 dirs if the intent is a single trim; align the written plan bullet with cap math
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:active-session-keeps-version (diff.txt hunk: loop keeps 29.1.22 after single prune of 29.1.20)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Cap loop removes two dirs (20 and 22) when ten cached versions exist, LATEST_STABLE is 30, only 21 is pinned, and INSTALLED_VERSION basename stays 21. CI/local harness fails: test expects 29.1.22 directory to remain after upgrade. Add assertion that 29.1.22 is pruned and remove 29.1.22 from the keep loop (or reduce seeded versions so only one eviction is needed).
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:crlf-session-root-keeps-version (diff.txt hunk: same keep list including 29.1.22)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Same cap arithmetic as active-session with CRLF-trimmed pin on 29.1.21. Same failure mode as active-session case for crlf-session-root-keeps-version. Mirror the active-session fix for the CRLF case.
- **Suggested revision**: Address the concern above.


