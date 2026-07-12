### OOS_1: Deep-queue cross-language routing still uses touched_files only
- **Description**: Deep-queue cross-language routing still uses touched_files only. Scenario: Consumer evidence will tag shell/skill/hook references, but `_risk_reason` still promotes cross-language deep candidates only when touched files span python/ and scripts|skills/. A Python rename with shell consumers in another path may widen later-history scans yet miss deep-priority routing.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/issue/analyze_bugs.py:1292-1307
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Deep-queue cross-language priority still keys off `touched_files`, not bundle consumer evidence
- **Description**: Deep-queue cross-language priority still keys off `touched_files`, not bundle consumer evidence. Scenario: #6946-style cases can list shell consumers in the bundle yet miss deep promotion when the Python fix touches only `python/` paths, because `_risk_reason` still requires both Python and scripts/skills under `touched_files`
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:1301-1304
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Stage 2 SKILL prose still describes cross-language promotion via touched-file heuristics only
- **Description**: Stage 2 SKILL prose still describes cross-language promotion via touched-file heuristics only. Scenario: After this change, bundles can prove cross-language blast radius from consumer evidence, but Stage 2 still tells operators promotion depends on touched Python plus scripts/skills paths, causing operator confusion and mis-tuned `--deep-max` expectations
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: .claude/skills/analyze-bugs/SKILL.md:91-93
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: Widened later-history git failures still collapse to empty history
- **Description**: Widened later-history git failures still collapse to empty history. Scenario: After widening scans, _later_history and revert scans still use _git_stdout, which returns "" on any non-zero git exit. A git log failure on a consumer path would look like no later commits, repeating the false-clear pattern on a widened path.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/issue/analyze_bugs.py:612-616
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

