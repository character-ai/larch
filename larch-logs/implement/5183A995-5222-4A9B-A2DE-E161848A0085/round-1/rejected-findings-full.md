### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: test_apply_bump_threads_base ad-hoc runner
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_apply_bump_threads_base` introduces ad-hoc `BaseRunner` instead of reusing existing `StubRunner`/`RaceRunner` patterns in the same file. Future `apply_bump` guard changes require updating multiple bespoke runner classes. Build the test with `StubRunner` response dict entries for upstream fetch/show (and status/add/commit stubs).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: has_bump=False test skips drop_bump_commit path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `has_bump=False` test does not cover `drop_bump_commit` dropping a bump (`python/test_rebase.py:975-1014`). If drop staging breaks while `has_bump=False`, CI may still pass because the test never exercises the drop path. Add handlers so `drop_bump_commit` succeeds, assert drop/staging calls occur, and classify/apply stubs still never run.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: defer_push / RebaseResult.pushed contract undocumented for drivers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `defer_push=True` returns `Outcome.OK` with `pushed=False` while local bump commits may exist (`python/rebase.py:619-627`); contract is undocumented on `RebaseResult`. Phase 7 driver may treat OK as remote-updated and skip deferred push; CI can see stale remote branch while local HEAD has rebump commits. Document `pushed` semantics on `rebase_and_rebump`/`RebaseResult`; `ship.py` must check `pushed` or mirror bash defer-push then stage-and-push. (Overlaps docstring gap in FINDING_5 but targets driver/contract risk.)
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: duplicate rebump happy-path handler lists
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_rebump_happy_path_handlers` is used only by new tests; older rebump tests duplicate the same handler list. Drift between happy-path handler sets can make one rebump test pass while another breaks silently. Migrate `test_rebase_result_uses_apply_result_new_version` and `test_version_regression_guard_recomputes_target` to the shared helper.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: repeated classify/apply monkeypatch boilerplate
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Three new tests repeat identical classify/apply monkeypatch boilerplate. Higher cost to change stub signatures or classification fixtures across rebump tests. Extract shared `_patch`/`_apply` helpers or pytest fixtures used by defer_push/has_bump/base tests.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: apply_bump base guard local naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_bump` guard uses `base_label` in git specs but keeps `origin_*` local variable names (`python/version_bump.py:580-616`). Readers debugging fork/upstream flows may mis-trace which ref version guards use. Rename locals to `base_show`/`base_version` (or `published_version`).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

