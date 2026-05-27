## Proposed Design Outline

### Goals
- Enforce the three minimal `monitor_rc` propagation tokens (init within 3 non-blank lines above monitor, `|| monitor_rc=` on monitor logical-end line, later `if`/`case` referencing `monitor_rc`) for every top-level Family B writer block currently subject to `fence_has_family_b_pid_capture_and_wait`.
- Run identically in the Markdown-fence path and the shell-file path so SKILL.md fences and shell wrappers (e.g. `ship-pr.sh`-shaped fences) share one enforcement surface.
- Add negative `test-lint-foreground-markers.sh` fixtures covering "monitor_rc capture present but no branch" and "no monitor_rc capture at all".

### Non-goals
- Do NOT verify the structural two-branch shape from BASH_AUTHORING.md §4 (success-branch `wait $PID` exit / failure-branch bounded reap). Operator confirmed minimal-presence at Step 1c.
- Do NOT widen Family B scope: nested-only basenames (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`) and `step-7a.sh` (foreground-only) remain excluded — `family_b_pid_writer_required` gates the new check just like today.
- Do NOT alter the existing PID-capture / monitor-presence / wait-identifier-match / wait-after-monitor checks already in `fence_has_family_b_pid_capture_and_wait`.
- Do NOT change `BASH_AUTHORING.md` §4 prose, the canonical example fence, or the linter banner / comment markers.

### Approach sketch
- Extend `scripts/lint-foreground-markers.sh` `fence_has_family_b_pid_capture_and_wait` with three additional in-line checks executed after the existing wait check confirms a matching `wait`. Each missing token emits a distinct error line and increments `VIOLATIONS`; checks accumulate (not first-violation-wins) so operators see every missing token in one run.
- Reuse the existing line walk by indexing on `capture_idx` (PID line), `monitor_idx` (monitor start line), and the wait line. The "monitor's logical-end line" is the last line of the backslash-continuation chain that begins at `monitor_idx`; reuse `line_ends_with_backslash_continuation` to walk it.
- The `|| monitor_rc=` token is matched on the merged logical line (consistent with how the existing `&` check merges over backslash-continuation at the writer side).
- The `if`/`case` referencing `monitor_rc` is searched from after the wait line through end-of-fence (any `^[[:space:]]*(if|case|elif|while|until)\b` whose body / condition mentions `monitor_rc`).
- Honor the existing per-line `# lint-foreground-markers: ok <reason>` suppression at the anchor line (already wired before the new checks run).
- Add fixture markdown blocks and shell-wrapper snippets to `scripts/test-lint-foreground-markers.sh` matching the two negative cases listed in the issue Acceptance section; ensure positive fixtures (the canonical two-branch shape) still pass.
- Sync the docs anchor in `BASH_AUTHORING.md` §4 only as needed to name the new error messages so operators grep from the lint output to the prose rule (a one-line cross-reference, no rewrite).

### Surfaces in scope
- `scripts/lint-foreground-markers.sh` — extend `fence_has_family_b_pid_capture_and_wait`; `scan_shell_file_for_family_b_wait` inherits via the existing call from line 777.
- `scripts/test-lint-foreground-markers.sh` — add negative fixtures and ensure existing canonical-shape positive fixtures still pass.
- `scripts/lint-foreground-markers.md` — sibling contract doc updates for the new checks and error-message catalog.
- Optional one-line cross-reference in `BASH_AUTHORING.md` §4 naming the new lint error message tokens (deferred unless reviewer asks).

### Open questions
- None.
