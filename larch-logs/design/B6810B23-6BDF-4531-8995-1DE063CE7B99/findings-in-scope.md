### FINDING_1: phase2_relaunch_count is initialized after its first increment path
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Cursor-Edge, Codex-Edge, Codex-Requirements, Cursor-Innovation, Cursor-Requirements, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-kv-consumer-sync, Cursor-dyn-increment-placement, Codex-dyn-increment-placement
- **Severity**: important
- **Concern**: The planned `phase2_relaunch_count` initializer is placed after the grouped phase-2 reuse loop, but the planned fall-through path inside that earlier loop increments the variable before relaunching. Under `set -u`, a reuse-copy failure can read an unset variable and abort; if initialized later, the count can also be reset before the combined fallback threshold is computed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch, Codex-Pragmatic: Initialize phase2_relaunch_count=0 before the grouped phase-2 loop, before any possible increment; keep fallback_count=0 at the phase-3 loop if desired
  - From Cursor-Edge, Codex-Edge, Codex-Requirements: Initialize phase2_relaunch_count=0 before grouped phase-2 processing, for example before phase2_grouped_failed=(), and leave fallback_count=0 where it is.
  - From Cursor-Innovation, Cursor-Requirements: Initialize `phase2_relaunch_count=0` before the grouped phase-2 loop (~479); keep `combined_fallback` after phase-3 collect as planned
  - From Codex-Innovation: Initialize phase2_relaunch_count=0 before the grouped phase-2 loop, for example near phase2_grouped_failed=(), and keep fallback_count=0 at the phase-3 loop
  - From Cursor-Pragmatic: Initialize phase2_relaunch_count=0 once before the phase2_grouped loop (~479); increment only in the reuse_slot_result fall-through branch; never reset it alongside fallback_count=0
  - From Codex-dyn-kv-consumer-sync: Initialize phase2_relaunch_count before the grouped phase-2 loop, for example before phase2_grouped_failed=(), and keep combined_fallback computation after phase-3 collect
  - From Cursor-dyn-increment-placement, Codex-dyn-increment-placement: Initialize phase2_relaunch_count=0 before the grouped phase-2 loop, for example before phase2_grouped_failed=() at line 479, and keep the increment after fi and immediately before launch_slot at line 508. Leave fallback_count=0 at line 520; it is top-level, not in a subshell or function, and remains visible after the phase-3 loop.

### FINDING_2: dispatch panel WARN contract omits phase-2 relaunches
- **Reviewer(s)**: Codex-dyn-kv-consumer-sync
- **Severity**: nit
- **Concern**: `skills/review/scripts/dispatch-panel.md` still describes `WARN=cost-fallback-exceeded-threshold` as based only on the Phase 3 fallback count, but the planned behavior can also trigger from phase-2 reuse fall-through relaunches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-consumer-sync: Update the WARN sentence to say the threshold uses the combined phase-2 fall-through relaunch count plus phase-3 Claude count while keeping the DISPATCH_OK Phase 3 failure wording unchanged
