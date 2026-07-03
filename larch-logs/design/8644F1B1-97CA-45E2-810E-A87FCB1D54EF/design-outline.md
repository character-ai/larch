## Proposed Design Outline

### Goals
- A live `.bg-wait-active` marker gates only its own repo clone; foreign markers never deny Bash, Read, Monitor, TaskOutput, waiter, or clamp paths.
- A session can always read a `.bg-wait-active` marker file to self-diagnose.
- Every deny reason names the triggering marker path, its STEP, and the hook's plugin version.

### Non-goals
- No change to same-clone deny behavior; the guard's core purpose stays intact.
- No sessionstart-health version-skew check (deferred to OOS follow-up).
- No shared Bash library; hooks stay self-contained.

### Approach sketch
- Duplicate `marker_foreign_clone()` + `clone_paths_same()` from `hook-no-progress-guard.sh` (#5927) into `hook-bg-poll-guard.sh`.
- Filter foreign-clone markers inside the live-marker collection loop, so `live_dirs_file` / `live_markers_file` never hold foreign dirs; this also fixes sole-live-dir clamp binding and denial-count attribution.
- Exempt paths with basename `.bg-wait-active` from Bash-probe and Read denial.
- Enrich all three deny emitters (`json_deny`, `json_deny_monitor`, `json_deny_probe`) with marker path, STEP, and hook version via printf formatting, not jq.
- Add cross-clone regression cases; keep same-clone deny cases green.

### Surfaces in scope
- `scripts/hook-bg-poll-guard.sh` and sibling `.md`
- `scripts/test-hook-bg-poll-guard.sh` and sibling `.md`
- `SECURITY.md` guard paragraph

### Open questions
- None.
