### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: correctness: `_resolve_conflicts` uses CI-style waterfall, not bash recovery waterfall
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_resolve_conflicts` uses CI-style `run_waterfall` (first-tier “other” short-circuit; no fallback after win with remaining unmerged paths). Bash `run_recovery_waterfall` tries all tiers with `rebase --continue` verify between attempts. Python short-circuits or raises `NeedsUserInput` after one tier. Conflict resolution should use recovery-style tier loop: no first-tier other bail, verify per tier, continue to next tier on failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: `NeedsUserInput` when conflicts remain after winning waterfall untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Agent appears to win but tree still has unmerged paths; escalation via `NeedsUserInput` (“conflicts remain”) may not be exercised in tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub `launch_fn` success with persistent U paths; assert `NeedsUserInput` conflicts remain message.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: security: `TransientNetworkError` may attach unredacted fetch `CommandResult`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `TransientNetworkError` on fetch can attach an unredacted `CommandResult` on `.result`; future driver logging of `exception.result` could leak tokens/URLs from `git fetch` stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact or drop `.result` on outbound errors; keep only redacted message


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: security: conflict CSV built without path validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Conflict file list is built via comma-join without Python path validation. An unmerged path containing a comma splits into wrong `--conflict-files` entries; fixers may edit unintended files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Port `larch_validate_vendor_conflict_csv` before join; stall on invalid paths


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: `bullets_path` / tmpdir paths not confined to session tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `bullets_path`, `tmpdir`, and `IMPLEMENT_TMPDIR` are not constrained to the session tmpdir; a misconfigured caller could write bullets or launcher captures outside the intended tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document trust boundary; resolve and confine paths under `IMPLEMENT_TMPDIR` in Phase 7 driver


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: security: launcher `--output` may be relative
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Launcher `--output` may be relative when `output_dir` is relative; `launch-*-ci.sh` rejects non-absolute `OUTPUT`, so waterfall can fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve `out_root` with `Path.resolve()` before launch


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: broad `"no changes"` substring enables `--skip`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Continue failure handling treats any stderr containing `"no changes"` as skip-worthy; incidental messages could trigger blind `--skip` without bash/git-rebase-skip parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Tighten signatures to bash/git-rebase-skip parity


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: architecture: `_sync_local_main` ignores `branch_force` failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `git branch -f main` failure is ignored; classification may proceed with stale local `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Check returncode; warn or `Stalled`


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: risk-integration: all-tier launcher health failure becomes `NeedsUserInput`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Infra blip during rebase conflict resolution surfaces `NeedsUserInput` whereas bash might orchestrator-retry; Phase 7 driver retry policy vs `NeedsUserInput` needs alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Phase 7 driver retry policy vs NeedsUserInput


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: architecture: force-push path ignores fetch errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Fetch errors before lease-guarded force-push may be ignored silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optionally check fetch rc before push


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality / architecture: `_resolve_conflicts` lacks per-file fixer prompt context
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_resolve_conflicts` passes only a `--conflict-files` CSV via launchers; it does not build `conflict-resolution.md`-style per-file prompt blocks (`repo` / `run_id` unused). Agents lack upstream/feature context required by the plan, reducing fix quality versus Phase 1–4 procedure (or plan wording should be aligned with launcher-only delegation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan wording with launcher delegation or implement prompt assembly in `rebase.py`


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: architecture: `RebaseResult.detail` always empty
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan specifies redacted `detail` on outcomes; field is always empty so callers cannot surface human-readable results without parsing other fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Populate `detail` via `redact.redact_outbound` on key outcomes or document as driver-owned

---

**Merge notes (for voters, not machine output):**
- Input **FINDING_19** (CHANGELOG prepass) and **FINDING_20** (drop_bump stall) are subsumed under **FINDING_1** (same acceptance-test gap).
- Input **FINDING_21** (multi-hop) is subsumed under **FINDING_1**.
- Input **FINDING_37** (edge drop-changelog tests) is subsumed under **FINDING_1**.
- Input **FINDING_42** merged into **FINDING_3**; input **FINDING_44** merged into **FINDING_2** (OOS tag retained on merged heading per aggregator rules).
- **FINDING_12** vs **FINDING_13**: kept separate (waterfall algorithm vs inter-tier tree rollback).
- No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: `ScriptRunner` duplicates stub-runner patterns
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/test_rebase.py` `ScriptRunner` duplicates `ProcRunner` / `StubRunner` patterns from `test_version_bump.py`. Future argv/env changes require parallel edits in two harness implementations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: duplicate bump-subject regex vs `version_bump.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/rebase.py` duplicates bump subject regex/parsing vs `version_bump.py`. Divergent regex or template changes could desync drop-bump version extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: double resolution of rebump bullets path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `rebase_and_rebump` resolves rebump bullets path twice (`python/rebase.py` ~481–501). Low risk today but adds noise when evolving path resolution rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: `python/README.md` phase heading stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: README title still says Phase 1–2 only; docs mislead readers about Phase 3 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

