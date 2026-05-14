### REJ_C1: Cursor-Structure (round 1) [code-review/rejected]

**Finding**: larch-logs/implement/BEBE5A71.../manifest.json — committed manifest.json shows status "in-progress"; reviewers expecting terminal manifest status for merged run logs may misread run completeness.
**Reason not implemented**: larch-log flush commits are normal larch behavior (evidenced by the recent `chore(larch-logs): flush implement run ...` commits on main). The `status: "in-progress"` is expected at mid-run; the larch-log system updates it to `done` at Step 18. This is not a bug in the code under review.

### REJ_C2: Cursor-Structure (round 1) [code-review/rejected]

**Finding**: test-codex-implementer.sh:382-395 — positional argv assertions for lines 5-8 are brittle; legitimate argv reordering would break the test.
**Reason not implemented**: The positional assertions are intentional mechanical contracts per the launcher's design principles (same pattern as the existing lines 1-6). The plan explicitly acknowledged this as an acceptable trade-off. A follow-up issue can address if brittleness becomes painful.

### REJ_C3: Cursor-Correctness/Edge-cases/Generic-Codex (round 1) [code-review/rejected]

**Finding**: scripts/launch-codex-implement.sh:318-326 — $PWD might not equal git rev-parse --show-toplevel if launcher is invoked from a subdirectory.
**Reason not implemented**: The SKILL.md cwd contract explicitly requires: "invoke the dispatcher with process cwd = the consumer git repo's working tree." This invariant pre-exists and is load-bearing for the existing `-C "$PWD"` flag. Adding a defensive assertion would be scope creep; if the contract is ever violated, the same fix applies to the pre-existing `-C "$PWD"` too.

### REJ_C4: Multiple reviewers (round 1) [code-review/rejected]

**Finding**: larch-logs run artifacts committed in the diff (manifest, plan-goals-test, tally files).
**Reason not implemented**: These are expected larch run-log commits (triggered by the pre-commit hook via larch-log-flush.sh). They are part of larch's normal workflow per the larch-logs documentation. They will be updated to status=done at Step 18.

