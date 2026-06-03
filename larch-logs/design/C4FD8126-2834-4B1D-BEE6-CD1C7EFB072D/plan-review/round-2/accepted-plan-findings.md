### FINDING_1: Test 16 harness still uses tmpdir-root qa-pending paths
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-harness-table-completeness
- **Severity**: important
- **Concern**: In `test-step2-dispatch.sh`, test 16’s Codex stub and post-run assertion still write and read `qa-pending.json` at the session tmpdir root (`$IMPLEMENT_TMPDIR/qa-pending.json` and `QA_PENDING_16=$TMP16/qa-pending.json`). The planned Codex Step 2 path moves `QA_PENDING_PATH` to `$TMPDIR/codex-step2-out/qa-pending.json` while the plan only retargets `STEP2_MANIFEST_PATH` for test 16. The dispatcher repair then reads the subdir path, sees a missing or wrong file, and exits `STATUS=bailed` (`qa-pending-missing` / `manifest-schema-invalid`), so test 16 fails despite being listed in the harness table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In test 16 stub: write qa-pending under $IMPDIR/codex-step2-out/ (or derive from STEP2_MANIFEST_PATH dirname); set QA_PENDING_16=$TMP16/codex-step2-out/qa-pending.json
  - From Cursor-dyn-harness-table-completeness: Extend the test-step2-dispatch.sh plan for test 16: stub writes to $IMPLEMENT_TMPDIR/codex-step2-out/qa-pending.json (or dirname of STEP2_MANIFEST_PATH); set QA_PENDING_16=$TMP16/codex-step2-out/qa-pending.json


### FINDING_2: SECURITY.md not updated for narrowed Codex --add-dir grant
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan narrows Codex Step 2 `--add-dir` without updating `SECURITY.md` (~line 105). After landing, operators and security reviewers may still believe the full dispatcher session tmpdir is Codex-writable and mis-scope tamperable artifacts (e.g. `session-env.sh`, plan copies) relative to shipped behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add a minimal SECURITY.md edit in the plan: Codex implementer --add-dir is limited to codex-step2-out/ (dirname of manifest/qa/transcript), not all of IMPLEMENT_TMPDIR; orchestrator-owned files outside that subdir are outside the Codex write grant


### FINDING_3: Proposed harness case id collides with existing fail 4b
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A proposed new harness case labeled `test 4b` would collide with the existing `fail 4b` in `test-codex-implementer.sh` (line 344), which already asserts `CODEX_HOME` is a per-invocation `/tmp` directory. Reusing `4b` for a transcript-parent test would break pass/fail numbering or overwrite the wrong assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name the new transcript-directory case 11c (after parent-mismatch test 11) or another unused id; keep fail 4b for the CODEX_HOME check only


### FINDING_4: launch-codex-implement.md still documents full tmpdir grant
- **Reviewer(s)**: Cursor-dyn-split-dependency-isolation
- **Severity**: important
- **Concern**: A planned sibling edit only removes the Codex-writable sentence and adds a subdir note, but leaves “The granted directory is the ENTIRE session tmpdir” and dispatcher-tmpdir-wide framing (e.g. `scripts/launch-codex-implement.md` line 14) that contradicts narrowed `SESSION_TMPDIR`. Operators reading only that doc may still believe baseline files, sidecars, and other `$IMPLEMENT_TMPDIR` artifacts are inside the `--add-dir` grant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-split-dependency-isolation: Rewrite the whole `--add-dir` invariant bullet: `SESSION_TMPDIR` is `dirname("$MANIFEST_PATH")` (on the codex path, `$IMPLEMENT_TMPDIR/codex-step2-out/`); only manifest, qa-pending, and transcript live there; other tmpdir artifacts are launcher-written and outside the grant. Drop "ENTIRE session tmpdir" and the Codex-writable list

---

**Merge notes**: Input `FINDING_1` and `FINDING_4` describe the same test-16 path mismatch and were merged. `FINDING_2` (`SECURITY.md`) and `FINDING_4` here (launcher doc) are separate files and fixes and were kept apart. No `[OUT_OF_SCOPE]` inputs; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

