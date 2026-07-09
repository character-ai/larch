# Discussion Round 1 — issue #6624

## Decision 1: Optional fix items in scope
- **Question**: Besides the primary fix (new `progress statusline` verb + compact renderer + docs), which optional issue items are in scope?
- **Resolution**: In scope: item 2 (feature + stopgap docs), item 6 (liveness hardening in `_discover_live_run`), and item 3 (PostToolUse per-wait-chunk snapshot hook, hard-gated on verifying hook `systemMessage` is UI-only and never enters model context; drop item 3 if verification fails). Out of scope: item 4 (manual empirical characterization + upstream Claude Code issue).
- **Source**: user

## Decision 2: Statusline is always-on, zero-config, larch-scoped
- **Question**: How does the one-time `statusLine` configuration land in settings?
- **Resolution**: Fully automatic; the operator never edits any config file. Larch's SessionStart machinery auto-installs and maintains a user-level `statusLine` entry pointing at a stable launcher path under `~/.cache/larch/` (refreshed each session start to the current plugin version, so upgrades never break it). Strict no-clobber: never overwrite or wrap a pre-existing non-larch `statusLine`; only install when absent or when the existing entry is larch's own. The renderer emits empty stdout when no live larch run matches the session cwd, so non-larch sessions and non-larch repos show a blank status line (no visible effect).
- **Source**: user (requirements); platform docs (mechanism)

## Decision 3: No manual trigger surface for the statusline
- **Question**: Should operators be able to trigger the statusline manually?
- **Resolution**: No. The statusline is event-driven plus `refreshInterval` timer only. The existing `p`/`progress` UserPromptSubmit hook stays unchanged for idle windows (issue item 5), and second-terminal `progress report --cwd` remains the documented on-demand stopgap.
- **Source**: user

## Decision 4: Fail-silent renderer contract
- **Question**: What happens when the data the status report tails (timing ledger, session pointers, tmpdir files) is missing, empty, or unparseable?
- **Resolution**: The status line is NOT displayed at all: the statusline command emits empty stdout and exits 0 in every failure or no-data case (missing/empty/corrupt source files, discovery failure, any internal exception). It must never print error text, whitespace-only output, or partial/garbage rows. Empty stdout is the documented "blank status line" path in Claude Code.
- **Source**: user

## Platform facts binding the design (verified 2026-07-08, docs v2.1.204)
- `statusLine` is a settings.json-only key; plugins cannot provide it (plugin settings support only `agent` and `subagentStatusLine`). Source: code.claude.com/docs/en/plugins.md.
- Settings precedence: `.claude/settings.local.json` > `.claude/settings.json` (project) > `~/.claude/settings.json` (user).
- Settings hot-reload: statusLine config changes apply at the next interaction; no restart needed.
- `refreshInterval` (min 1s) re-runs the command on a timer in addition to conversation events; whether it fires mid-turn during a long foreground Bash call is **undocumented** — docs must hedge the observed cadence.
- Statusline stdin JSON includes `cwd`, `session_id`, `workspace.*`, `model.*`; empty stdout ⇒ blank status line (documented, not an error).
- Operator's `~/.claude/settings.json` currently has **no** `statusLine` entry (verified), so install-if-absent covers this operator.

## Hard constraints (issue non-goals, carried forward)
- Do not revert or weaken the bgjob transport (spurious-notification fix must stand).
- No periodic progress text in tool results or model context.
- Keep `scripts/hook-progress-report.sh` unchanged for idle windows.
