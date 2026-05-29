## Decision 1: Collapsed-fence target shape
- **Question**: When collapsing the live Family-B fences (background writer + breadcrumb-monitor.sh + PID-capture + monitor_rc + wait), what should each become?
- **Resolution**: Plain foreground calls. Drop shell `&`, the breadcrumb-monitor.sh invocation, PID capture, `monitor_rc`, post-monitor `wait`, all sentinel/LARCH_BREADCRUMB_* exports, the `**⚠ Background required**` banners, and the `# Background pair required` per-anchor comments. No explicit `run_in_background: true` is required even for long scripts: empirically confirmed that when a foreground Bash-tool command exceeds its timeout the harness AUTO-BACKGROUNDS it (does NOT kill it) and emits a `<task-notification>` on completion — the same one-shot-completion path AGENTS.md already endorses. So ship-pr.sh / ci-wait.sh (>10-min) are safe as plain foreground calls.
- **Source**: user + empirical test (probe ID bfxjowoxq auto-backgrounded at the 8s tool timeout)

## Decision 2: Cleanup exhaustiveness
- **Question**: Remove every breadcrumb/Family-B reference across the in-scope surfaces, or only the enumerated files?
- **Resolution**: Exhaustive across skill fences (skills/**, .claude/skills/**, .claude/rules/*.md) and the in-scope public docs. The issue explicitly includes "residual stale references". Leave nothing behind except deliberately-preserved surfaces (Decision 4).
- **Source**: user

## Decision 3: Orphaned Stage-3 no-op shims
- **Question**: Once all fences are gone, should Stage 4 also delete the now-orphaned no-op shims Stage 3 left behind?
- **Resolution**: Delete them. Remove scripts/breadcrumb-monitor.sh + scripts/breadcrumb-monitor.md; drop the two larch_quiet no-op compatibility shims (larch_quiet_append_done_trap, larch_quiet_write_paired_pid_file) from scripts/lib-quiet.sh and scripts/lib-quiet.md; fix the scripts/test-design-structure.sh reference. Stage 5 (#3120) does not claim these.
- **Source**: user

## Decision 4: Preserve (hard constraints — must NOT be removed)
- **Question**: What breadcrumb-adjacent surfaces must survive Stage 4?
- **Resolution**: (a) The committed larch-logs/<run-id>/breadcrumbs/ forensics directory and its documentation in docs/run-logs.md — preserve the forensics-directory references; only remove live-streaming/monitor machinery text. (b) The polling-loop ban (general orchestrator discipline) in AGENTS.md and the residual spirit of NEVER #9 — stays. (c) The redaction toolchain (redact-secrets.sh, redact-tmpdir-paths.sh) — stays (used by larch-log.sh commit). (d) BASH_AUTHORING.md loses §4 ONLY; §1-§3 stay, so the CLAUDE.md `@BASH_AUTHORING.md` import is unchanged.
- **Source**: codebase + parent issue #3111

## Decision 5: #2919 close
- **Question**: Does this piece need to close #2919?
- **Resolution**: #2919 is already CLOSED. No design/implementation action required beyond an optional back-reference comment check. Not a code change.
- **Source**: codebase (gh issue view 2919 -> CLOSED)

## Decision 6: Stage 4 / Stage 5 boundary
- **Question**: Are the #3063 hardening "Preserve / lift into own issues" items in scope here?
- **Resolution**: No. Those are Stage 5 (#3120, blocked-by this piece): design-log-publish symlink/render-cache rescans, SECURITY.md render-cache language, lib-quiet sanitize_diagnostic_line audit, ship-pr.sh fallback-relay sanitization, mermaid embedded-`=` regression. Out of scope for Stage 4.
- **Source**: codebase (Stage 5 #3120 body)
