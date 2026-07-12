### FINDING_2: `/status` lacks a wire path for gate-specific diagnostics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Vendor Gate Routing, Codex-dyn-Vendor Gate Routing
- **Severity**: major
- **Concern**: `CODEX_STATE=probe-failed` cannot distinguish a CLI-version gate from other probe failures, while `status check` emits only fixed KVs. `/larch:status` therefore cannot reliably render the actionable upgrade message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In _auth.py status_check_main, emit an optional single-line KV (for example CODEX_PROBE_DETAIL=) with the sanitized upgrade message when gate detail is present; preserve existing keys/values and CODEX_STATE=probe-failed. Update skills/status/SKILL.md to parse that KV and prefer it over the generic probe-failed phrase; extend python/tests/agents/test_agents.py status-check tests for gate vs generic failures.
  - From Cursor-Innovation: Define one stdout channel in status check (e.g. framed CODEX_PROBE_DETAIL block or one optional KV) and add matching Step 1 parse/render rules in skills/status/SKILL.md; test in test_agents.py
  - From Cursor-Pragmatic: Have status_check_main emit the gate-aware explanation (for example DEGRADED_EXPLANATION_BEGIN/END using the same text as degraded_tools_gate) while keeping existing KV keys; update skills/status/SKILL.md step 2 to parse and print the Codex line from that block when present.
  - From Cursor-Requirements: Have `status check` emit the gate diagnostic on stdout (for example a `DEGRADED_EXPLANATION_BEGIN/END` block mirroring `degraded_tools_gate`) and update `skills/status/SKILL.md` to render that Codex line instead of the generic probe-failed phrase when present
  - From Cursor-dyn-Vendor Gate Routing: Have `status check` emit the actionable gate text on stderr (KV keys unchanged) or document a concrete gate-detail file read in status step 2 before rendering Codex state.
  - From Codex-dyn-Vendor Gate Routing: Either emit the actionable gate text on stderr from `status_check_main` (KV unchanged), or add an explicit gate-detail file read in status step 2 before choosing the Codex line.


### FINDING_4: Probe and gate-detail caches are not model/role keyed
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Vendor Gate Routing, Codex-dyn-Vendor Gate Routing
- **Severity**: major
- **Concern**: Existing probe stamps and diagnostic artifacts can be reused across probe-role or model changes, allowing stale healthy results or stale gate messages to survive within the TTL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Key the stamp and gate detail by the resolved model or model set, and invalidate them when it changes
  - From Codex-Pragmatic: Include a safe hash of the resolved review model in the Codex probe and diagnostic cache identity
  - From Cursor-Requirements: Bump `_codex_probe_stamp_kind()` (or equivalent) to include the review-role probe identity, and pair gate-reason storage with that stamp so cache hits still reload gate detail
  - From Cursor-dyn-Vendor Gate Routing: Bump the stamp kind (or invalidate on role/model change), and tie gate-detail expiry to the same identity; write `codex_present=false` when a gate is detected even if a stale positive stamp exists.
  - From Codex-dyn-Vendor Gate Routing: Add the resolved model to the diagnostic cache identity, or persist it with the diagnostic and discard mismatches


### FINDING_8: Gate-detail handoff is incomplete on cache paths
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: minor
- **Concern**: Disabling probe caching or serving a cached probe result may prevent the immediate degraded-tools/status path from receiving or reloading the gate-specific detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Define an invocation handoff that remains readable by the immediate degraded-tools call when probe-result caching is disabled
  - From Cursor-Requirements: State in `_auth.py` that gate detail is loaded from the paired cache file whenever the probe stamp cache is used (not only immediately after a live probe), and clear that artifact when a fresh non-gate probe succeeds


