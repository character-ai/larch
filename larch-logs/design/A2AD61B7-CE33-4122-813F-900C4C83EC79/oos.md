### FINDING_4: Plan-size and trailer metadata wiring is incomplete
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Plan-size accounting and trailer metadata are not fully scoped or threaded, so the reported size signals and optional trailer state can be inaccurate or unmachineverifiable.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Innovation: Derive firm paths via extract_scope_paths (or shared helper with the same heading regex, section bounds, and backtick stripping); count firm headings and distinct surfaces from that path list only, excluding MAY_UPDATE
  - From Cursor-Pragmatic: Move the parse CLI bullet to plan_quality.py optional_trailers_main (emit oversize_override, extend metadata_trailer_lines), keeping OptionalMetadata/OPTIONAL_KEYS in _plan_quality_commands.py.
  - From Cursor-Requirements: In parse_optional_metadata, add `oversize_override` to both `keys` and `values` (`oversize_override=operator`), and extend `test_plan_quality.py` optional-trailer snapshot/validate cases accordingly.
  - From Codex-Requirements: Add explicit threshold output keys for the configured limits and thread them through postplan/result-env allowlists, docs, and tests where size KVs are presented.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

