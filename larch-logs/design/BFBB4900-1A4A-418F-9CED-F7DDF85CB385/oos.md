### OOS_1: G-Sec-3 still cites `.claude/rules/gh-body-file.md` as the new-call-site reminder; the plan removes rule citations but does not name a replacement pointer.
- **Description**: G-Sec-3 still cites `.claude/rules/gh-body-file.md` as the new-call-site reminder; the plan removes rule citations but does not name a replacement pointer.. Scenario: After deletion G-Sec-3 loses the only guideline-level link between egress redaction and the mechanical gh argv guard at new call sites; authors may rely on memory even though lint gh-body-inline exists.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: ARCHITECTURAL_GUIDELINES.md:107
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: python/README.md still lists check_topology_rule_paths.py at the python/ root
- **Description**: python/README.md still lists check_topology_rule_paths.py at the python/ root. Scenario: The module lives at python/larch/lint/check_topology_rule_paths.py. This is stale operator docs, not a functional regression from rule deletion.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/README.md:16
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: G-Sec-3 still points new gh callers at the removed gh-body-file rule.
- **Description**: G-Sec-3 still points new gh callers at the removed gh-body-file rule.. Scenario: Removing the Note without a replacement drops the guideline-level pointer that inline gh --body is lint-backed at new call sites; operators who read only ARCHITECTURAL_GUIDELINES.md may miss the enforcement surface.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: ARCHITECTURAL_GUIDELINES.md:107
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

