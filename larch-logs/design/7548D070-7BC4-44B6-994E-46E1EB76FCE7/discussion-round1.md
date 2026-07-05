## Decision 1: Version-resolution symptom is in scope
- **Question**: The issue flags "Larch version: unknown" on the failing runs as a hint of the same ambient repo-root resolution bug. Should the fix also repair the version-resolution symptom?
- **Resolution**: Yes — always include the version fix as part of this change, regardless of whether it shares the exact code path with the assessment persistence bug.
- **Source**: user

## Decision 2: Root cause is ambient repo-root resolution, not a missing invocation
- **Question**: Is the assessment silently skipped because the `--skip-approve` carve-out never invokes persist, or because repo-root resolution yields the wrong root?
- **Resolution**: The Gate C `--skip-approve` carve-out DOES invoke `present-note` and `persist-design-assessment` (approval-gates.md:149). Both are called WITHOUT `--repo-root`, so `_resolve_repo_root(None)` falls back to `CLAUDE_PROJECT_DIR` (unset in the design session) then ambient `cwd`. When cwd is not inside the project repo (e.g., a plugin-cache subshell), guidelines resolve `absent`; `persist_design_assessment` then silently unlinks any stale artifact and returns 0 with no warning.
- **Source**: codebase

## Decision 3: Fix strategy — deterministic authoritative repo-root threaded into Gate C guideline calls
- **Question**: How to guarantee the assessment is always persisted in a repo that has ARCHITECTURAL_GUIDELINES.md?
- **Resolution**: Capture an authoritative repo-root once at session start (known-good cwd) and thread an explicit `--repo-root` into the Gate C `present-note` and `persist-design-assessment` invocations (and version resolution), removing the fragile ambient cwd/env fallback. With both calls using the same explicit root, "absent" reliably means genuinely absent. Prefer the robust/deterministic option over a minimal patch.
- **Source**: user preference (robustness) + codebase

## Decision 4: Scope boundaries and hard constraints
- **Question**: What must not change, and what must the fix include?
- **Resolution**: In scope — assessment persistence on the `--skip-approve` Gate C path, the shared version-resolution symptom, and a regression test driving the `skip_approve_requested=true` Gate C path asserting the assessment artifact is present. Hard constraints — preserve the existing fail-closed persistence contract (non-zero persist exit still logs a bounded `Warnings` line and stops Gate C), do not regress the ~88% currently-working path, keep new logic Python-first per repo conventions, and do not redesign the broader architectural-guidelines subsystem or touch implement-side note handling.
- **Source**: codebase + issue acceptance criteria
