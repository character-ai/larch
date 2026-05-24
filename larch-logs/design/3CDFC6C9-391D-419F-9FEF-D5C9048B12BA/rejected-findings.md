### [Plan Review] FINDING_4

### FINDING_4: Slot-positional v1/v2/v3 vs `review-core.sh`'s compacted voter handoff
- **Concern**: `review-core.sh:594-615` builds `EFFECTIVE_VOTER_FILES` only from successful voter slots before passing to `tally-code-votes.sh --voter-files`. If voter slot 2 fails and slot 3 succeeds, the tally script sees only 2 paths and cannot put v3's vote in the `v3_*` columns with v2 columns empty — slot 3 shifts into v2 columns, breaking per-judge column identity that Fixture B relies on.
- **Proposed resolution**: Pass fixed-slot metadata to tally — either `--voter-1-file/--voter-2-file/--voter-3-file` with empty placeholders for missing slots, or a `--voter-slots-file` NDJSON with `{slot:N, status:..., path:...}` records. `tally-code-votes.sh` then writes columns by slot number rather than compact iteration. Vote thresholds remain driven by effective voter count. Add a "missing middle slot" fixture. Raised by ~5 reviewers (mostly Codex-side, dyn-artifact).


