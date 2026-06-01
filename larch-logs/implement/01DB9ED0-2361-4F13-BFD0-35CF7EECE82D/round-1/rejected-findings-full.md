### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: correctness: python/rebase.py:255
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] _sync_local_main ignores branch_force failure Stale local main skews classify_bump Check branch_force rc or mirror bash warning behavior
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: correctness: python/rebase.py:62-67,452-458
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Missing bash changelog_first_version_heading fallback when bump subject is not semver Bump dropped with non-template subject but valid ## [X.Y.Z] in CHANGELOG: bash stages bullets and drops companion commit; Python skips and can replay stale Update CHANGELOG during rebase Mirror ship_pr_record_old_bump_version using changelog.first_version_heading when subject parse fails
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: python/git.py:63-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] branch_force has no unit test. Incorrect -f argv for _sync_local_main undetected. Add test_branch_force_argv in test_git.py.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: security: python/rebase.py:288-302
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Deterministic prepass calls git.add without -- before conflict paths. A conflicted file whose name starts with - can make git add interpret it as a flag and stage unintended paths before force-push. Use git add -- path (or extend git.add to always pass --) at all three prepass call sites.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: security: python/rebase.py:324-327
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] conflict_csv is built from raw unmerged paths without larch_validate_vendor_conflict_csv parity. Custom launch_fn or comma/newline/.. paths can bypass launcher validation or mis-route the fixer agent. Validate each path in Python with the same rules as larch_validate_vendor_conflict_csv before join; stall on invalid segments.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: risk-integration: python/rebase.py:467-469
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] TransientNetworkError attaches unredacted fetch_result. A driver that logs exc.result may leak fetch stderr containing auth or infrastructure details. Redact fetch stdout/stderr on the exception or document and enforce redacted logging only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: correctness: python/rebase.py:473-490
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No detection of in-progress rebase before git rebase base_target Retry after partial resolution aborts rebase and stalls losing staged resolutions Branch on rebase-merge state into _resolve_conflicts or rebase_continue instead of fresh rebase
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: correctness: python/rebase.py:258-264
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] _is_empty_or_already_applied matches broad no changes substring Hook stderr containing no changes may cause inappropriate rebase --skip Narrow signatures to git empty-commit messages
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: correctness: python/rebase.py:536-544
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] RebaseResult always pushed True with empty detail Noop force-push indistinguishable from fresh push in logs Propagate noop vs pushed from _force_push_branch into result
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_38: **Latent** `correctness` `python/rebase.py:346-350` — After `git rebase --continue` exits 0 with no `U` paths, `_resolve_conflicts` returns immediately. If git left a rebase in progress without unmerged entries (unusual), `rebase_and_rebump` would proceed to classify/rebump/push on a dirty rebase state. **Suggested fix:** After a successful continue, optionally verify `.git/rebase-merge` / `rebase-apply` is gone (or loop continue until finished), mirroring bash’s repeated `--continue` / `rebase-push --continue` episodes.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 4. **Latent** `correctness` `python/rebase.py:346-350` — After `git rebase --continue` exits 0 with no `U` paths, `_resolve_conflicts` returns immediately. If git left a rebase in progress without unmerged entries (unusual), `rebase_and_rebump` would proceed to classify/rebump/push on a dirty rebase state. **Suggested fix:** After a successful continue, optionally verify `.git/rebase-merge` / `rebase-apply` is gone (or loop continue until finished), mirroring bash’s repeated `--continue` / `rebase-push --continue` episodes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_39: **Nit** `correctness` `python/test_rebase.py` — Plan bullets_path resolution includes `IMPLEMENT_TMPDIR` env fallback (`_rebump_bullets_path` at `rebase.py:51-53`); tests cover explicit `tmpdir` and explicit `bullets_path` but not env-based resolution. **Suggested fix:** Add `monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, …)` and assert the resolved path.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 5. **Nit** `correctness` `python/test_rebase.py` — Plan bullets_path resolution includes `IMPLEMENT_TMPDIR` env fallback (`_rebump_bullets_path` at `rebase.py:51-53`); tests cover explicit `tmpdir` and explicit `bullets_path` but not env-based resolution. **Suggested fix:** Add `monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, …)` and assert the resolved path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: python/rebase.py:24
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate bump subject regex vs version_bump Two regexes can diverge on subject format changes Share parse helper from version_bump
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

