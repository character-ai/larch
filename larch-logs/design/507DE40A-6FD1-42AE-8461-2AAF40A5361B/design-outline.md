## Proposed Design Outline

### Goals
- Add `/triage <issue-number> [--repo OWNER/REPO] [--report-only]`: root-cause, verify, and update an issue into a design-ready state.
- Generalize the existing verify-first patterns (synthetic stall reports; stale OOS) into one reusable pre-`/design` entry point.
- Emit a machine-readable verdict on stdout (`TRIAGE_VERDICT`, `ISSUE_UPDATED`) for future automation.

### Non-goals
- Not a code editor or plan author: never edits code, never writes a `/design` plan.
- Not a replacement for `/design` verify-first, `/bug` (filing), or `/research` (read-only research, no issue mutation).

### Approach sketch
- New `skills/triage/SKILL.md` is thin orchestration (like `/bug`, `/research`); deterministic logic reuses or extends Python helpers behind `cli.py` per G-Skill-2: git-ref/repo validation (G-Sec-1), redaction (G-Sec-3), GitHub mutation + re-verify (G-Ext-2/4), and the verdict grammar.
- Phases mirror `/issue` untrusted-content wrapping (G-Sec-2): fetch → evidence → verify → repro (read-only) → cross-reference → verdict → act.
- Valid verdict rewrites the issue body into one coherent design-ready spec via `gh issue edit --body-file`, idempotently (G-Idem-1); already-fixed/duplicate/invalid verdicts comment, close NOT_PLANNED, and restore a lifecycle-renamed title.
- `--report-only` performs every phase up to the verdict but skips all mutation.

### Surfaces in scope
- `skills/triage/SKILL.md` (new)
- `README.md` (skill catalog, feature matrix, aliases)
- `AGENTS.md` (canonical-sources pointer)
- `SECURITY.md` (untrusted-content handling + read-only/idempotent repro hard rule)

### Open questions
- None. (Thin SKILL.md + existing Python helpers; add triage-specific Python only if deterministic logic emerges, per G-Skill-2.)
