### OOS_1: [OUT_OF_SCOPE] Closeout and diff materialization use mismatched HEAD snapshots
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: latent
- **Concern**: Closeout and materialize_implementation_diff do not share one frozen HEAD snapshot, so durable-note metadata and the diff fingerprint can come from different repository states. That can surface as a commit-vs-tag-object mismatch on annotated-tag checkouts or as a race if HEAD changes between the closeout git call and the pin helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Align HEAD resolution: use _current_head(... verify_commit=True) in closeout or pin using the SHA from the single materialization inside pin_note_from_staged_for_current_head"
  - From cursor-specialist-edge-cases: "Resolve HEAD once and thread that SHA through both pin metadata and materialize_implementation_diff."
  - From codex-specialist-edge-cases: "Thread one frozen head through the whole pin path, for example by letting materialize_implementation_diff accept the caller’s frozen head_sha, or by having the pin helper resolve/materialize/return the same head it writes into durable metadata and making closeout use that single snapshot."
  - From cursor-specialist-testing: "Consider unifying HEAD resolution at the closeout boundary or threading a verified SHA into materialization in a follow-up."
  - From codex-specialist-testing: "Use one frozen HEAD SHA for both diff materialization and durable-note metadata, and add a regression test for drift between closeout HEAD resolution and materialization."

### OOS_2: [OUT_OF_SCOPE] Add failure-path coverage for unresolved HEAD
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The HEAD resolution failure path needs an explicit RuntimeError contract. Without regression coverage, a broken or unborn HEAD could slip through without the expected exception and later diff steps might still run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Add a monkeypatched subprocess test asserting RuntimeError when HEAD resolution fails"
  - From cursor-specialist-edge-cases: "Add a monkeypatched subprocess test where rev-parse fails and assert RuntimeError."
  - From cursor-specialist-testing: "Add a monkeypatched subprocess test asserting RuntimeError and that merge-base/diff are never called when rev-parse fails."

### OOS_3: [OUT_OF_SCOPE] Base ref can drift across repeated materializations
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: A separate materialization path still leaves origin/main live across calls, so the base ref can move between snapshots even though HEAD is frozen per call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Address in a follow-up if cross-call base pinning is required."

### OOS_4: [OUT_OF_SCOPE] Stale-check fallback can rematerialize after pin
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The ship pin path can still materialize twice. If the durable snapshot is missing after a successful pin, the stale check falls back to live materialization and can observe a newer HEAD between the two calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Reuse the pin helper’s live diff/fingerprint in the stale check or skip live fallback immediately after a successful pin."

