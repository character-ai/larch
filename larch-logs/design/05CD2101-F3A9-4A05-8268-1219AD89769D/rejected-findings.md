### [Plan Review] FINDING_3

### FINDING_3: All-pinned overflow test fixture may miss implicit preservation paths
- **Reviewer(s)**: Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness
- **Severity**: important
- **Concern**: The planned test does not specify fixture values tightly enough to prove both implicit preservation paths are covered while also exercising the cap-overflow warning path with zero evictable candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness: Revise the plan's test fixture to specify post-install >8 entries and zero evictable candidates, for example GH_OUTPUT and INSTALL_RESULT_VERSION = 50.0.10, PLUGIN_ROOT_VERSION = 50.0.1, CACHED_VERSIONS = 50.0.1 through 50.0.9, SESSION_PINNED_VERSIONS = 50.0.2 through 50.0.9, with no rm/stat failure knobs; then assert all original cache dirs plus 50.0.10 remain and the cap-overflow warning appears.

