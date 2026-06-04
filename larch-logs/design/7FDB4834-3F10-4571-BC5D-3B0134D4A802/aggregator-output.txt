### FINDING_1: Python OOS gate misses alternate design OOS paths
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-witness-gap, Codex-dyn-witness-gap
- **Severity**: important
- **Concern**: `python/ship.py` still checks only `$IMPLEMENT_TMPDIR/oos-accepted-design.md`, so design OOS exported through `DESIGN_TMPDIR` or `design-export/oos-accepted-design.md` can be missed and PR creation can proceed without `needs_user_reason=oos-filing`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update python/ship.py OOS accepted-file resolution to match scripts/ship-pr.sh resolve_oos_accepted_design_path before adding the manifest materialization hook
  - From Codex-Edge: Reuse the same design accepted-file resolver/order in _oos_gate before counting accepted files
  - From Codex-Innovation: Update _oos_gate to resolve design OOS in the same order as ship-pr.sh and oos-disposition-checkpoint.sh: DESIGN_TMPDIR, then design-export/oos-accepted-design.md, then oos-accepted-design.md.
  - From Codex-Pragmatic: Extend python/ship.py _oos_gate with the same design path order as ship-pr.sh/oos-disposition-checkpoint.sh before the materialized OOS decision and cover it with a small regression pin
  - From Codex-Requirements: Add a Python resolver mirroring scripts/ship-pr.sh resolve_oos_accepted_design_path and oos-disposition-checkpoint.sh, use it in _oos_gate before PR creation, and cover it in the new structure or Python test.
  - From Cursor-dyn-witness-gap: In python/ship.py resolve design OOS path like resolve_oos_accepted_design_path / checkpoint before _oos_gate; include that path in accepted_files and filed_urls_strict_files when present
  - From Codex-dyn-witness-gap: Update python/ship.py to use the same design-source resolution before `_oos_gate` decisions, or call the checkpoint helper instead of duplicating the gate path

### FINDING_2: All-already-filed OOS branch can skip required NDJSON evidence
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 9a.1 all-already-filed branch says to materialize evidence and return, but the checkpoint requires `oos-issues.ndjson` whenever non-security OOS exists. Existing Filed URLs in design markdown may therefore fail validation if step 6 is skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Clarify step 2: skip steps 3-5 and /issue only; still run step 6 (and step 7 handoff). Tie assertion 12 to step 6 NDJSON evidence, not step 2 return alone
  - From Cursor-Innovation: Mirror sentinel-recovery: explicitly skip steps 3.4-3.5 and step 4; write checkpoint evidence per step 6; then step 7 — replace before returning with continue to step 6

### FINDING_3: Step 2 materialization failure can silently lose manifest-only OOS before ship
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: If `step2-implement.sh` materialization is fail-open and the run bails after Step 2 complete but before `ship-pr`/PR prep, manifest-only `oos_observations[]` may never reach `oos-accepted-main-agent.md`, preventing OOS filing from triggering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Fail closed on materialize when jq reports a non-empty oos_observations array, or add the same pre-OOS hook to every terminal bail path that can follow STATUS=complete with MANIFEST_PATH set

### FINDING_4: Manifest materialized block schema omits required attribution fields
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned materialize-manifest-oos contract lists title/description/phase blocks but omits `Reviewer` and `Vote tally`, diverging from the SKILL dual-write schema and weakening downstream attribution/audit consistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Specify merged block template in materialize-manifest-oos.md (e.g. Reviewer: external implementer, Vote tally: N/A — auto-filed per policy) matching SKILL.md schema

### FINDING_5: oos-pipeline prose conflicts with assertion 15 manifest-token ban
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-witness-gap, Cursor-dyn-assertion-logic, Codex-dyn-assertion-logic
- **Severity**: important
- **Concern**: The plan tells `oos-pipeline.md` to mention `oos_observations[]` / `$MANIFEST_PATH`, while planned assertion 15 forbids those tokens in the same file. An implementation can either follow the prose or satisfy the test, but not both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the manifest-specific wording to materialize-manifest-oos.md and keep oos-pipeline.md Step 1 to “read oos-accepted-main-agent.md after dispatcher materialization.”
  - From Codex-dyn-witness-gap: Remove the `oos_observations[]` and `$MANIFEST_PATH` tokens from planned oos-pipeline.md step 1; say main-agent markdown already includes dispatcher-materialized manifest OOS and point to materialize-manifest-oos.md
  - From Cursor-dyn-assertion-logic: Align assertion 15 with intent: scope the negative grep to step 1 only and forbid `harvest` (or `jq`/`parse` of manifest) near `MANIFEST_PATH`, not the provenance parenthetical; or drop `oos_observations[]`/`$MANIFEST_PATH` from step 1 and cite only `materialize-manifest-oos.md`.
  - From Codex-dyn-assertion-logic: Remove oos_observations[] and $MANIFEST_PATH from the planned oos-pipeline step 1 prose, or narrow the negative check to forbid harvest/jq parsing instructions rather than a neutral materialization pointer

### FINDING_6: run-statistics structure assertion may reject intended SKILL text
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The planned NEVER #5 replacement still mentions `run-statistics`, while assertion 9 appears to require absence of that term in the scoped region, so the intended updated SKILL text can fail the new test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Change the assertion to ban only the old write --batch run-statistics fragment and positively assert the post-checkpoint ownership sentence, or scope the absence check to the single append command sentence.

### FINDING_7: Manifest materializer can duplicate OOS_N headings
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The merge contract does not require monotonic `OOS_N` allocation, so appending manifest blocks to a file with existing dual-write blocks can duplicate headings and break downstream parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify allocate next free OOS_N after scanning existing headings; title dedup only is insufficient

### FINDING_8: Python manifest materialization lacks CI/structure pin
- **Reviewer(s)**: Cursor-Requirements, Codex-dyn-assertion-logic
- **Severity**: important
- **Concern**: The planned tests pin `step2-implement.sh` and `ship-pr.sh`, but not that `python/ship.py` materializes manifest-only OOS before the OOS filing decision. A missed Python wire could still pass structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a fixed-string pin that python/ship.py invokes materialize-manifest-oos.sh before _oos_gate (or extend assertion 15 and spot-grep); optionally add a focused python/test_ship.py case with manifest.json-only OOS
  - From Codex-dyn-assertion-logic: Add a structure assertion that python/ship.py invokes materialize-manifest-oos.sh before the disposition/OOS_PENDING needs_user_reason decision when ctx.manifest_path is set

### FINDING_9: Pre-trigger manifest materializer failure handling is underspecified
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-dispatch-wiring
- **Severity**: important
- **Concern**: New `materialize-manifest-oos.sh` calls in `ship-pr.sh` / `python/ship.py` may fail or be skipped without a clear failure policy. Because `ship-pr.sh` lacks `set -e`, unchecked nonzero exits can leave accepted-OOS files empty and allow PR creation or OOS_PENDING clearing despite manifest OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: For ship-pr.sh and python/ship.py pre-trigger invocations, capture the helper rc; on nonzero, log Tool Failures and stop with NEEDS_USER/STALLED or conservatively force OOS_PENDING instead of clearing/proceeding. Add a regression assertion for this failure path.
  - From Cursor-dyn-dispatch-wiring: Add to UPDATED python/ship.py: invoke materialize immediately before _oos_gate (line 327), gate on Path(ctx.manifest_path).is_file(), subprocess via runner.run without aborting run_ship on non-zero, append Tool Failures to ctx.tmpdir/execution-issues.md on infrastructure failure (mirror step2 fail-open)
  - From Cursor-dyn-dispatch-wiring: Add explicit fail-open contract to UPDATED ship-pr.sh: capture helper rc, append Tool Failures via append-execution-issue.sh on non-zero, always continue to the existing -s oos-accepted-*.md OOS_PENDING branch at lines 1192-1196

### FINDING_10: OOS pipeline omits public-filing redaction requirement
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The new canonical OOS pipeline omits the existing dual-write redaction requirement before public `/issue` filing and `oos-issues` log rows, so internal URLs or PII from materialized manifest OOS may be forwarded verbatim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: In oos-pipeline.md step 3.4/4/6, add a mandatory sanitize-before-filing/logging instruction that applies SKILL.md's secrets/internal-URL/PII redaction contract to issue bodies and larch-log records, and pin it in the structure test.

### FINDING_11: Assertion 2 count does not prove distinct entry paths were updated
- **Reviewer(s)**: Codex-dyn-assertion-logic
- **Severity**: important
- **Concern**: Counting three occurrences of the load directive in `SKILL.md` does not ensure the Python driver selector, Exit 0 OOS branch, and OOS checkpoint paragraph were each updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-assertion-logic: Add three scoped fixed-string checks keyed to the Python driver selector, the Exit 0 OOS branch, and the OOS checkpoint paragraph; keep the total count only as a secondary guard

### FINDING_12: Assertion 8b can pass with split, non-equivalent substrings
- **Reviewer(s)**: Codex-dyn-assertion-logic
- **Severity**: important
- **Concern**: Assertion 8b checks two substrings separately even though the invariant requires a single suppression sentence tying failed issue filing to no accepted disposition URL rows in `oos-issues.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-assertion-logic: Pin one exact fixed string or a single-line grep that contains both the suppression phrase and oos-issues NDJSON; make the negative check line-scoped to ISSUES_FAILED>0 plus append accepted disposition URLs

### FINDING_13: ship-pr materialization order is not pinned before OOS_PENDING trigger
- **Reviewer(s)**: Codex-dyn-assertion-logic
- **Severity**: important
- **Concern**: A loose invocation grep could pass even if `materialize-manifest-oos.sh` is called after the existing `OOS_PENDING` size check, still skipping manifest-only OOS during PR prep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-assertion-logic: Add an order check that the materialize-manifest-oos.sh call in run_pr_prep_phase appears before the first state_set OOS_PENDING true branch
