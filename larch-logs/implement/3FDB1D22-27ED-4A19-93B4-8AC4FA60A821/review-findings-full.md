### REJ_C1: Cursor-Structure (round 1) [code-review/rejected]

**Finding**: `larch-logs/implement/<RUN_ID>/` files added to the branch — manifest.json, plan-goals-test.md, plan-review-tally.json — not listed in the three-file implementation plan. Manifest shows `status: in-progress`.
**Reason not implemented**: This is normal larch workflow behavior. Implementing issue #2142 via `/implement` automatically commits run logs to the branch as part of the tracking lifecycle documented in `docs/run-logs.md`. The larch-log flush commit is an expected PR artifact, not a defect. The manifest will be updated to terminal status at merge.

### REJ_C2: Cursor-Correctness (round 1) [code-review/rejected]

**Finding 1 (important)**: `larch-logs/` artifacts not in plan. Same as Structure finding — routine larch operation.
**Reason not implemented**: Normal workflow artifact. See above.
**Finding 2 (latent)**: The pattern `Security (process exited with code|command failed)` matches any stderr containing those words, not only exit code 45. Could false-positive on non-auth `security` CLI errors.
**Reason not implemented**: This exact pattern was analyzed and justified in issue #2142. The two-word qualifier `Security (process exited with code|command failed)` is what Cursor actually emits and is unambiguous. Narrower patterns (e.g. `: 45`) would miss other transient security exit codes. The issue explicitly documents why this pattern is correct and the acknowledged trade-off.

### REJ_C3: Cursor-Testing (round 1) [code-review/rejected]

**Finding 1 (important)**: `larch-logs/` artifacts. Same as above.
**Reason not implemented**: Normal workflow artifact.
**Finding 2 (latent)**: Regex broadness. Same as Correctness finding 2.
**Reason not implemented**: Acknowledged design decision per issue #2142.

### REJ_C4: Cursor-Security (round 1) [code-review/rejected]

**Finding 1 (latent)**: `manifest.json` exposes `operator_cwd` and `operator_repo_root` absolute paths.
**Reason not implemented**: Per `docs/run-logs.md` these fields are intentionally not redacted for provenance. This is policy-by-contract, not an accidental leak.
**Finding 2 (latent)**: Regex broadness for non-auth security failures. Same as Correctness finding 2.
**Reason not implemented**: Acknowledged design decision per issue #2142.

### REJ_C5: Cursor-Plan-fidelity (round 1) [code-review/rejected]

**Finding (important)**: `larch-logs/` not listed in the written plan's three-file scope; manifest `status: in-progress`.
**Reason not implemented**: Normal larch run-log workflow. The manifest will reflect terminal status at PR merge per the larch lifecycle.

### REJ_C6: Generic-Codex (round 1) [code-review/rejected]

NO_ISSUES_FOUND — no rejected findings.

