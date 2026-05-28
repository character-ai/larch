## Decision 1: Part B scope correction
- **Question**: Issue Part B claims `list_cached_versions()` and `sort_versions()` are both dead. Are they?
- **Resolution**: Only `list_cached_versions()` is dead. `sort_versions()` is still called by `version_gt()` (line 50) and `collect_active_session_versions()` (line 194), both reachable from the prune path. Per user clarification (Step 1c): remove only `list_cached_versions()`, keep `sort_versions()`. Update the design plan to reflect this corrected scope.
- **Source**: user
