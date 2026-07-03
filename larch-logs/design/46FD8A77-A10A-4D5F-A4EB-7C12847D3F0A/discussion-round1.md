# Discussion Round 1 — issue #6178

## Decision 1: Fix scope
- **Question**: What should this design deliver for the /research hook-leak bug?
- **Resolution**: Hook activation gate + docs. Add a session-scoped activation sentinel: /research writes it at start and removes it at cleanup; deny-edit-write.sh denies only while it is present, otherwise allows. Update harness, contract doc, coupling rule, and SECURITY.md. A leaked or stale hook registration deliberately fails open when no live /research run exists. Upstream repro/report doc is OUT of scope (user declined the third option).
- **Source**: user

## Decision 2: Stale-sentinel backstop
- **Question**: If /research exits abnormally and never removes its activation sentinel, how should the hook treat the leftover sentinel in that same session?
- **Resolution**: TTL expiry. Ignore (allow) a sentinel older than a fixed TTL (~6 hours, comfortably above any real /research run) so a crashed /research cannot reproduce the stuck-session symptom indefinitely. A live run keeps full protection.
- **Source**: user

## Hard constraints (codebase-derived, not user questions)
- Matcher stays exactly `Edit|Write|NotebookEdit` (`.claude/rules/research-readonly-hook-coupling.md`).
- Hook command stays anchored at `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh`.
- Deny envelope stays fixed-ASCII-literal and byte-identical across jq and printf paths.
- Coupling rule: SKILL.md frontmatter, deny script, harness, and SECURITY.md must be edited in sync.
- While /research is genuinely active, the /tmp-only allow predicate keeps its fail-closed-on-ambiguity semantics; the new gate only decides whether the hook is active at all.
