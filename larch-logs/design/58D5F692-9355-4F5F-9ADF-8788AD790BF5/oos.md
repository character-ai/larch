### OOS_1: python/progress_report.py:100-104
- **Description**: python/progress_report.py:100-104. Scenario: [SCOPE-REDUCTION] Parallel `_attribution_labels` / `_human_attribution_labels` builders duplicate prune-map/manifest/voter-label union logic
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/plan_review_tally.py:67-71
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: scoreboard_main `--findings-classification-file` path appears test-only
- **Description**: scoreboard_main `--findings-classification-file` path appears test-only. Scenario: Production scoreboards are built inline in `plan_review_tally.py` and `review_tally.py`; extending the standalone CLI adds ~30 lines and a second scoring entrypoint beyond what the issue requires
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/voting.py:1268-1289
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [SCOPE-REDUCTION] `scoreboard_main --findings-classification-file` adds a second weighted scoring path not used in production
- **Description**: [SCOPE-REDUCTION] `scoreboard_main --findings-classification-file` adds a second weighted scoring path not used in production. Scenario: Production scoreboards come from `plan_review_tally` / `review_tally` markdown; `python/cli.py voting scoreboard` is only covered in `test_voting.py`
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/voting.py:1268-1289
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Parallel `_attribution_labels()` / `_human_attribution_labels()` builders can drift on fallback precedence
- **Description**: Parallel `_attribution_labels()` / `_human_attribution_labels()` builders can drift on fallback precedence. Scenario: Design Top reviewers and inline tally could tokenize the same cell differently if label-map / manifest fallbacks diverge
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/plan_review_tally.py:67-71 python/progress_report.py:100-104
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

