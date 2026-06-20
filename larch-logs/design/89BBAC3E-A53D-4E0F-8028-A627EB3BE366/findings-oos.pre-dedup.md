### OOS_1: [SCOPE-REDUCTION] New `python/deps_audit.py` reimplements open-issue pagination, native dependency reads, and prose scanning already present in `combine_issues` (`list_open`, `fetch_deps_main`, `prose_audit_main`)
- **Description**: [SCOPE-REDUCTION] New `python/deps_audit.py` reimplements open-issue pagination, native dependency reads, and prose scanning already present in `combine_issues` (`list_open`, `fetch_deps_main`, `prose_audit_main`). Scenario: Duplicate regex/API surfaces will drift from `combine_issues`/`blocker` fixes and inflate the ~1645-line diff without adding issue-required behavior
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:169-228,234-263
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] MVP defaults to uncapped full latent semantic pairing over all uncovered issue pairs, plus optional `--pair-cap` partial-audit machinery not requested in the issue
- **Description**: [SCOPE-REDUCTION] MVP defaults to uncapped full latent semantic pairing over all uncovered issue pairs, plus optional `--pair-cap` partial-audit machinery not requested in the issue. Scenario: The issue asks to infer dependencies, not to run O(n²) prompt-side latent pairing on every open issue; large repos may stall, burn tokens, or ship incomplete edge sets while still proposing body rewrites
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:67-75,134-136,142-151
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] Step 0 fixes `DEPS_TMPDIR` under `/tmp` without `mktemp -d`
- **Description**: [SCOPE-REDUCTION] Step 0 fixes `DEPS_TMPDIR` under `/tmp` without `mktemp -d`. Scenario: Colliding fixed paths under `/tmp` can clobber concurrent `/deps` runs (contrast `combine-issues` SKILL and `combine_issues.fetch_main` temp handling)
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:116-117
- **Phase**: design



