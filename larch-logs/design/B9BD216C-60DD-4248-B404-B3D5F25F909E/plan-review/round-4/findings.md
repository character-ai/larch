### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/run-logs.md:22-48;skills/cleanup/scripts/cleanup.sh:33-47
- **Concern**: maxdepth-4 newest-activity scan cannot see depth-5 session writes under larch-logs/implement/<RUN_ID>/round-<N>/. Scenario: From a session tmpdir root, find -maxdepth 4 stops at larch-logs/implement/<RUN_ID>/round-<N> (depth 4) and never measures round-<N>/findings.md, findings-classification.tsv, or breadcrumbs/*.log (depth 5). review-core/review-and-fix flush those paths live via --log-root "$IMPLEMENT_TMPDIR/larch-logs". A long /implement run can refresh only depth-5 batch files while the depth-4 manifest stays stale; /cleanup would treat the session as older than LARCH_CLEANUP_RETENTION_DAYS and rm -rf it despite active work. The plan also lists round-1/findings.md as a keep case while mandating maxdepth 4, so the proposed harness could pass on manifest.json while production still mis-deletes round artifacts.
- **Proposed resolution**: Raise the bounded scan to maxdepth 5 (or document manifest-only retention and drop the round-<N>/findings.md harness/edge-case). Reconcile the depth rationale in the plan and cleanup.md with docs/run-logs.md path shapes.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh (planned); docs/run-logs.md:387-408
- **Concern**: maxdepth-4 activity scan does not reach round artifact files like larch-logs/implement/<RUN_ID>/round-<N>/findings.md. Scenario: The plan removes sentinel protection, so a stale session whose only fresh activity is a round artifact file below depth 4 can be deleted despite active review/log writes
- **Proposed resolution**: Use maxdepth 5 for the session activity scan and make the cleanup harness assert a fresh round-1/findings.md case, not only manifest.json

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh (proposed); plan.txt:26,160,172,95
- **Concern**: maxdepth-4 scan cannot see fresh `larch-logs/implement/<RUN_ID>/round-<N>/findings.md`. Scenario: From a session tmpdir root, `find … -maxdepth 4` reaches `larch-logs/implement/<RUN_ID>/manifest.json` (depth 4) but not `…/round-1/findings.md` (depth 5). On APFS, parent dir mtimes do not refresh on child edits. A long-running `/implement` that only updates round artifacts under `larch-logs/` (e.g. `review-and-fix.sh` `write-round`) while older shallow files look stale can be misclassified as expired and `rm -rf`'d while Claude is still open. The plan’s mitigation and `test-cleanup.sh` case both cite `round-1/findings.md`, which contradicts `maxdepth 4`.
- **Proposed resolution**: Raise the bounded scan to `-maxdepth 5` (or document that retention relies on tmpdir-root `round-<N>/` writes and drop the `larch-logs/.../round-*` test claim). Align failure-mode #6 and edge-case bullets with the chosen depth.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:planned
- **Concern**: The proposed maxdepth-4 newest-activity scan does not reach round log files that the plan names as protected docs/run-logs.md:47-48 shows larch-logs/implement/<RUN_ID>/round-<N>/findings.md one level below the maxdepth-4 scan.. Scenario: On APFS, editing findings.md may not refresh parent directory mtimes, so /cleanup can classify an active long-running session as stale and delete it despite fresh round output.
- **Proposed resolution**: Use maxdepth 5 or otherwise explicitly include larch-logs/*/*/round-*/* in newest-activity, and make test-cleanup.sh assert a stale ancestor plus fresh larch-logs/implement/<RUN_ID>/round-1/findings.md case rather than only manifest.json.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:26; docs/run-logs.md:47-48
- **Concern**: maxdepth-4 does not reach round log files. Scenario: The plan says maxdepth 4 protects larch-logs/implement/<RUN_ID>/round-<N>/findings.md, but from the session root that file is depth 5. A long-running stale-looking session with only a fresh round file can still be deleted.
- **Proposed resolution**: Change the cleanup scan to maxdepth 5 or add a targeted round-* file scan, and update the plan/tests to match.

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:39-47; docs/run-logs.md:47-48
- **Concern**: The proposed maxdepth-4 activity scan does not reach round artifact files. Scenario: The plan claims maxdepth 4 protects larch-logs/implement/<RUN_ID>/round-<N>/findings.md, but that file is depth 5 below the session root; with stale ancestors on APFS, cleanup can delete an active session that only refreshed a round artifact
- **Proposed resolution**: Raise the cleanup scan/test contract to maxdepth 5 or explicitly include the round artifact path depth, and keep the manifest case as separate depth-4 coverage

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/run-logs.md:22-48
- **Concern**: 1. Cleanup plan uses maxdepth 4 but requires preserving fresh round artifacts at depth 5. Scenario: The plan says maxdepth 4 protects larch-logs/<skill>/<RUN_ID>/round-<N>/findings.md, but from the session root that path is depth 5, so a stale session with only a fresh round findings file can still be deleted
- **Proposed resolution**: Change the cleanup scan and tests to maxdepth 5, or narrow the acceptance criteria to only paths reachable at maxdepth 4 such as larch-logs/implement/<RUN_ID>/manifest.json

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-caller-inventory, Codex-dyn-caller-inventory
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/run-logs.md:45-58 docs/run-logs.md:387-408
- **Concern**: Planned /cleanup maxdepth-4 activity scan misses depth-5 round artifacts. Scenario: The plan says maxdepth 4 covers larch-logs/implement/<RUN_ID>/round-<N>/findings.md, but that file is five levels below the session root; a live run that only refreshes round files can be misclassified stale and deleted
- **Proposed resolution**: Use maxdepth 5 if round-<N> files are part of the retention contract, or narrow the contract/tests to depth-4 manifest.json only

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-depth-alignment, Codex-dyn-depth-alignment
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:26,94-98,160,172,178; docs/run-logs.md:22-49
- **Concern**: Proposed cleanup maxdepth-4 scan does not reach every run-log path it claims to protect. docs/run-logs.md places manifest.json at larch-logs/implement/<RUN_ID>/manifest.json depth 4 from the session root, but round-<N>/findings.md is depth 5. The planned test also allows either manifest.json or round-1/findings.md, so an implementation could test only the shallower manifest path and miss the boundary.. Scenario: A stale session whose only fresh write is larch-logs/implement/<RUN_ID>/round-1/findings.md can be deleted because find "$entry" -mindepth 1 -maxdepth 4 sees round-1/ but not findings.md, and the plan itself notes APFS may not bump parent directory mtime on child edits.
- **Proposed resolution**: Use maxdepth 5 if round files must be protected, and require test-cleanup.sh to set freshness only on larch-logs/implement/<RUN_ID>/round-1/findings.md for the boundary case. Alternatively keep maxdepth 4 but remove the round-<N>/findings.md protection claim.
