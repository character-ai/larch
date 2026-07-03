### OOS_1: Skill relay should read the report file when --out is used.
- **Description**: Skill relay should read the report file when --out is used.. Scenario: The CLI contract prints only REPORT_FILE= with --out while the skill still says relay markdown stdout. Operators using --out get a path line without the report body unless the skill reads the file.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/difficulty-calibration/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Reuse discover_voter_calibration_logs for classification path enumeration.
- **Description**: Reuse discover_voter_calibration_logs for classification path enumeration.. Scenario: The plan re-specifies three glob patterns that already live in discover_voter_calibration_logs. A future path change could update one site and silently desync accepted-count joins from voter-calibration.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/_voting_calibration.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Import JSONL enumeration from `rejected_analysis` instead of reimplementing it.
- **Description**: [OUT_OF_SCOPE] Import JSONL enumeration from `rejected_analysis` instead of reimplementing it.. Scenario: Duplicating `_implement_jsonl_records` / `_review_jsonl_records` logic invites path-precedence drift already present in `rejected_analysis` and `fluff-analysis`. Call the existing helpers (or extract a shared reader) for enumeration only; keep calibration-specific tier math local.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: [SCOPE-REDUCTION] Collapse duplicate escalation/substantiality HARD triggers in plan prose.
- **Description**: [SCOPE-REDUCTION] Collapse duplicate escalation/substantiality HARD triggers in plan prose.. Scenario: The plan lists escalation and substantiality separately but both hinge on the same non-empty `difficulty-rating.json.escalations` array, which adds parser surface without new signal.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/calibration/difficulty_calibration.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: The skill does not say how to relay markdown when `--out` is passed.
- **Description**: The skill does not say how to relay markdown when `--out` is passed.. Scenario: CLI mode prints only `REPORT_FILE=...` on stdout; the skill tells the agent to relay stdout, so operators can get a path line without the report body.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/difficulty-calibration/SKILL.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

