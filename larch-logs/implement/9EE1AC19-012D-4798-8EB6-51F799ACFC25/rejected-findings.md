### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `test_parity_apply_bump_clean_repo` may not prove successful apply parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Test uses a repo without `origin`; both sides likely `APPLIED=false`. Test can pass on mutual fetch failure without proving successful apply parity on a clean tree with `origin`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rename to document failure parity or use `_init_repo_with_origin` and assert `APPLIED=true` and version/commit fields.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No colocated `test_bump_worktree.py`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No `test_bump_worktree.py`; shared drop helpers regress with only indirect coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `python/test_bump_worktree.py` for `sorted_changed_files` and `drop_replay_commit` edge cases.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `bump_branch_guard` stall messages skip `redact_outbound`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Stalled messages skip `redact_outbound`. Phase 7 may surface Stalled to operators with branch names or path-like secrets verbatim in logs/KV output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Wrap stall messages with `redact.redact_outbound` before raise `Stalled`; add regression test.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `check_bump_version_pre` touches sentinel at unvalidated `implement_tmpdir`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A compromised or mistaken `implement_tmpdir` (or symlinked directory) could create `.bump-version-armed` outside the intended session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve and confine `implement_tmpdir` under trusted session root before touch; skip on escape.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: `apply_bump` is an oversized function with nested closures
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `apply_bump` (~160 lines) embeds staging rollback and `origin/main` retry logic in nested closures. Same-version-race or regression fixes require editing one large function, increasing subtle-regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract stage/rollback and fetch-verify-retry helpers to module-level functions.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `drop_replay_commit` stuck mid-rebase when abort fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When rebase `--onto` fails and `--abort` fails, repo is left in rebase state; drop returns error only. Phase 7 driver should treat as stall requiring manual `git rebase --abort`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Keep explicit error; Phase 7 driver should treat as stall requiring manual `git rebase --abort`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_24: `bump_worktree.py` missing from plan/README module inventory
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `bump_worktree.py` is not listed in the implementation plan but is required by the port; integrators may omit it when tracing Phase 2 deliverables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `bump_worktree.py` to plan/README module inventory once committed.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicate Markdown/RST format detection paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `detect_format` and `_detect_conflict_format` duplicate format-detection rules with slight differences. Extensionless conflict paths may classify differently than commit/detect paths after a one-sided edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate into one shared format resolver used by `auto_resolve` and `detect_format`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `sorted_changed_files` sort order may diverge from bash `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `sorted_changed_files` sorts paths by UTF-8 bytes; bash `drop-bump-commit.sh` uses `LC_ALL=C sort`. For non-ASCII paths in `LARCH_BUMP_FILES`, Guard 4 exact-equality vs drop-bump behavior could diverge (unexpected changed-files string vs drop, or the opposite).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align with `LC_ALL=C` semantics or add a parity fixture with non-ASCII filenames.
  - From cursor-specialist-correctness-output.txt: Use `LC_ALL=C` byte-sort parity (subprocess `sort` or `locale.strxfrm`) or restrict/document ASCII-only bump paths.
  - From cursor-specialist-edge-cases-output.txt: Restrict to ASCII paths or use a documented C-locale byte-sort helper.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `changelog.py` is a large mixed-responsibility module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `changelog.py` combines pure transforms, git wrappers, and `auto_resolve` in one large file, making navigation and Phase 7 driver wiring review harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting pure text helpers when next editing the module.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate `ProcRunner` test adapter across test modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_version_bump` and `test_changelog` each define a duplicate `ProcRunner` test adapter; `Runner` protocol changes require duplicate edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share via `conftest` or a `test_helpers` module.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `commit_changelog` is Markdown-only; RST commit path missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `commit_changelog` only commits Markdown changelogs while RST text operations are implemented. Callers or Phase 7 wiring passing `CHANGELOG.rst` get `committed=False` / errors despite plan/README implying broader changelog surface; bash commit path is also MD-only today, but Python API and plan acceptance still leave an RST commit gap for Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep README deferral; implement RST commit when wiring live path.
  - From cursor-specialist-correctness-output.txt: Document in plan or defer RST commit explicitly until Phase 7 (README already notes deferral).
  - From cursor-specialist-edge-cases-output.txt: Phase 7: add RST commit path or document that only `write_changelog_entry` + manual commit is supported until then.
  - From cursor-specialist-plan-fidelity-output.txt: Implement RST path in `commit_changelog` or formally narrow Phase 2 plan acceptance away from "every operation."


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

