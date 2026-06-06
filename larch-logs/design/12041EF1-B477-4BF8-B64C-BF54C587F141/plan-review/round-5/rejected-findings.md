### [Plan Review] FINDING_3

### FINDING_3: Makefile shard registration lacks verify-first guard for optional helper
- **Reviewer(s)**: Cursor-dyn-dependency-gate
- **Severity**: important
- **Concern**: The plan gates Item 4 script work on helper presence, but the Makefile update is unconditional. If `scripts/check-scope-reduction-marker.sh` is absent after #3548, adding a target or shard entry that invokes it can break `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-gate: Mark Makefile edits verify-first with the same observable gate as Item 4: test -f scripts/check-scope-reduction-marker.sh (or test -x) before adding .PHONY recipe and shard entry; omit the Makefile subsection entirely when the helper is absent


