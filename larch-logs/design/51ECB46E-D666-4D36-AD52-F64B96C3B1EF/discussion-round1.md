## Decision 1: run_ship scope
- **Question**: What specifically needs to change in run_ship, which already returns a typed ShipResult and has no KEY=value emission?
- **Resolution**: Decompose the 777-line body into smaller testable sub-functions. No emit-layer change needed since emit_result is already separate.
- **Source**: user

## Decision 2: review_core emit style
- **Question**: Should the pure core for review_core accumulate KV pairs and emit at the end (batch) or emit incrementally through a callback?
- **Resolution**: Batch at end. Pure core returns a ReviewCoreResult dataclass; thin emit layer calls _emit_kv for each field at the end.
- **Source**: user

## Decision 3: PR structure
- **Question**: One PR or three separate incremental PRs?
- **Resolution**: One PR covering all three targets: review_core, postplan deciders, and run_ship decomposition.
- **Source**: user

## Decision 4: Typed-domain dependency
- **Question**: Is the typed-domain-objects blocker (Finding type) already resolved?
- **Resolution**: Yes — issue #4978 is DONE. review_types.py already has Finding, ReviewCoreStatus, and related types. Design can proceed for all three targets.
- **Source**: codebase

## Decision 5: Postplan deciders scope
- **Question**: Which functions in design_lifecycle.py are the "design postplan deciders"?
- **Resolution**: _shared_step2b_postplan_body (around line 3033) is the primary target — it interleaves POSTPLAN_RC=/POSTPLAN_STATUS= emission with sentinel writes (_touch calls). Split into a pure decision function returning (rc, status, rows_to_emit, sentinels_to_touch) and a thin execution layer.
- **Source**: codebase
