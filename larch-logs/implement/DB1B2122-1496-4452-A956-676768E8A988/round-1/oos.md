### OOS_1: [OUT_OF_SCOPE] `assert_no_flag_kvs` gap is test-hardening only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `assert_no_flag_kvs` only greps for `HARD_REQUESTED` and `POSITIONAL_KIND`, not all eight success keys — out of scope for parser behavior; test-hardening only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: (No separate fix beyond noting test-hardening scope; in-scope reviewers cover the same gap in FINDING_4.)


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] `test-design-structure.sh` missing Step 0-pre contract pins
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Structural pins cover script presence, `VALIDATION_ERROR` / `POSITIONAL_KIND` in the script, SKILL wiring, and removal of `remaining tokens after flags`, but not the plan’s `set +e` / `_argv_rc` capture or full acceptance-level CI parity with Step 0a pins. Verdict: no in-scope Important defect on primary issue/flag paths; remaining items are latent edge cases and orchestrator hardening gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: (Out of scope unless acceptance-level CI parity with Step 0a pins is desired; see FINDING_10 for the actionable pin gap.)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] `references/flags.md` positional tail not updated for parser semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Positional tail section not updated for parser/`--`/no-reparse semantics. Operators reading flags.md alone may misunderstand vs parse-design-argv.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update positional tail when flags.md is next edited for #3133 follow-ups.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Step 0a duplicates weak `CLAUDE_PLUGIN_ROOT` guard
- **Reviewer(s)**: dyn-skill-fence-kv-protocol-output.txt
- **Severity**: latent
- **Concern**: Step 0a uses the same `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` + empty-only guard pattern; Step 0-pre duplicates a pre-existing weakness rather than introducing a new guard style.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-fence-kv-protocol-output.txt: (Pre-existing Step 0a pattern; see FINDING_12 for Step 0-pre hardening direction.)


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_5: [OUT_OF_SCOPE] Structural pins do not require harness full stdout on validation failure
- **Reviewer(s)**: dyn-partial-emission-coverage-output.txt
- **Severity**: latent
- **Concern**: `test-design-structure.sh` pins assert parser script contains `VALIDATION_ERROR=` and `POSITIONAL_KIND=` and SKILL wiring, but do not require the offline harness to enforce full stdout on validation failure. Harness strengthening would close that gap without changing runtime behavior; `validation_error()` today correctly emits only `VALIDATION_ERROR` and exits 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-partial-emission-coverage-output.txt: (Harness strengthening gap; see FINDING_4 for actionable test fix.)

---

**Subsumed / not elevated**: Input FINDING_2 (embedded `=` breaks `${_line#*=}`) is contradicted by dyn-skill-fence-kv-protocol-output.txt (single-line `%%=*`/`#*=` preserves values after the first `=`) and folded into FINDING_6 only for the newline/`=` harness gap where still relevant. Input FINDING_39 recorded as non-actionable OOS confirmation only and not duplicated above.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

