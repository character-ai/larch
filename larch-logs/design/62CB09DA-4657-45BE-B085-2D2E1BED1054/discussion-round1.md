## Decision 1: Fix scope
- **Question**: Which combination of fixes from issue #2803 to include?
- **Resolution**: Belt-and-suspenders: #1 (inline schema in implementer prompt) + #2 (jq self-validation before manifest rename) + #3 (dispatcher recovery path on schema-invalid + non-empty working tree). Skip #4 (periodic schema echo).
- **Source**: user

## Decision 2: Recovery mode for #3
- **Question**: How should the dispatcher recover Codex's uncommitted work on manifest-schema-invalid?
- **Resolution**: Emit STATUS=claude_fallback + ORCHESTRATOR_EDIT_AUTHORITY=allowed (reusing existing envelope at step2-implement.sh:166-191). Orchestrator/Claude composes the commit and commits.
- **Source**: user

## Decision 3: Edit target for #1 and #2
- **Question**: Where should the inline-schema and jq-validation edits live?
- **Resolution**: In `agents/_implementer-base.md` (the shared base). Both `codex-implementer.md` and `cursor-implementer.md` regenerate via `scripts/generate-{codex,cursor}-implementer.sh`. Defensive symmetry for both implementers.
- **Source**: user

## Decision 4: Recovery trigger condition
- **Question**: When does the dispatcher recovery (#3) activate?
- **Resolution**: On `manifest-schema-invalid` AND `git diff HEAD --stat` non-empty (implementer wrote SOMETHING to the working tree). No recovery on empty-tree scenarios.
- **Source**: user

## Decision 5: How Claude fallback recovers the work
- **Question**: How does Claude know what to commit during recovery?
- **Resolution**: Dispatcher passes through the existing claude_fallback envelope. The orchestrator's Step 2 path (already wired for claude_fallback) takes over with the plan, feature description, and `git diff HEAD` of Codex's edits, and Claude writes a valid v1 manifest itself. Dispatcher commits as normal afterward.
- **Source**: user

## Decision 6: Test rigor
- **Question**: What test coverage should the plan require?
- **Resolution**: Offline harness (e.g., `test-step2-manifest-recovery.sh`) that synthesizes a bad-manifest scenario + real working-tree diff and asserts the dispatcher emits STATUS=claude_fallback + AUTH=allowed. Plus a regression check that the generated implementer prompts contain the inline schema literal. No live Codex/Cursor invocation required.
- **Source**: user

## Decision 7: Hard constraints / non-goals
- **Question**: What must NOT break?
- **Resolution**: Standard repo invariants only. Don't change schema_version (stays "1"). Don't break existing claude_fallback / --coder claude envelope. Don't loosen ORCHESTRATOR_EDIT_AUTHORITY semantics (pair invariant: AUTH=allowed iff STATUS=claude_fallback). Preserve `redact-secrets.sh` pass on commit_message. Preserve `relevant-checks.sh` after regenerating agent files. No retry caps or opt-out env vars; no separate SECURITY.md update required (the recovery is gated on "implementer-already-wrote-something", which is narrower than a general escape valve).
- **Source**: user
