## Decision 1: Invariant assessment semantics — blocking, not aspirational
- **Question**: When an ARCHITECTURAL_INVARIANTS.md assessment finds a violation, should it mirror the guidelines' non-blocking deviation note, or block?
- **Resolution**: Block. An invariant violation is a hard gate, not an aspirational deviation note. (This intentionally goes beyond the issue's "pure mirror" framing and adds new control flow.)
- **Source**: user

## Decision 2: Enforcement surfaces — both /design and /implement
- **Question**: Which surface(s) carry the blocking behavior?
- **Resolution**: Both. /design Gate C blocks a plan that violates an invariant, and /implement Step 8 ship blocks a diff that violates an invariant. The assessment is still presented/persisted everywhere guidelines are, regardless. Step 8 carries the real code-level teeth (an actual diff to check); Gate C blocks on plan-text judgment.
- **Source**: user

## Decision 3: Remediation is agentic with a bounded fallback — treat a violation exactly like a CI failure
- **Question**: When a violation blocks, does the operator override / manually fix, or is it hard-stop?
- **Resolution**: Agentic auto-remediation first, hard-stop only as the terminal fallback. A violation is fixed by the agentic process, the same way a CI failure is: the run auto-remediates (revise the plan at /design, revise the diff at /implement Step 8), re-assesses, and loops until the invariant holds — no operator override prompt and no "operator must fix and re-run" hand-off up front. ONLY if the agentic process cannot fix the violation (bounded retries exhausted / determined impossible) does it escalate to a hard-stop for the operator. This is precisely larch's CI-fix escalation model (auto-fix loop, then fail-out to operator when unfixable). Reuse existing fix-and-retry machinery (Gate-B-style auto-apply at design, CI-fix-style loop at implement) rather than build a bespoke escape-hatch prompt.
- **Source**: user

## Decision 4: Reader half already landed — this issue completes the rest
- **Question**: What is the current state of the mirror?
- **Resolution**: Commit 7bac75536 (Fixes #6469) already landed the reader half: INVARIANTS_FILENAME, _INVARIANT_HEADING_RE, parse_invariant_entries(), read_invariants() (present/absent/invalid + symlink/non-regular rejection + repo-root containment via the shared _validate_architectural_file), architectural_knowledge_required() (reads both), invariants_read_main(), and the `architectural-invariants read` cli verb (emits the `architectural_invariants` untrusted-content block). The issue's premise "No code or skill reads it yet" is now stale. Remaining scope: the other 10 cli verbs, the assessment/note artifact layer, and the /design + /implement + SECURITY.md + fluff-analysis skill wiring.
- **Source**: codebase

## Decision 5: Module structure follows the #6469 precedent (parallel functions, separate cli namespace)
- **Question**: DRY-by-`--kind`-flag vs. a parallel module/namespace?
- **Resolution**: Follow the precedent #6469 already set: parallel named functions in the same module sharing private helpers (read_invariants alongside read_guidelines; parse_invariant_entries alongside parse_guideline_entries), and a separate `architectural-invariants` cli namespace with distinct `*_main` entrypoints (invariants_read_main), NOT a `--kind` flag bolted onto the guidelines verbs. Extract shared helpers where guidelines/invariants logic is identical. Exact structure is a Step 2b decision, but this precedent is binding.
- **Source**: codebase

## Decision 6: Invariants file stays blank; blocking path is dormant until populated
- **Question**: Does this issue populate real I-* entries or feed both files to the Step 2 coder/reviewers?
- **Resolution**: No. Populating ARCHITECTURAL_INVARIANTS.md with real I-* entries is out of scope (its own effort), and feeding both files to the Step 2 coder + reviewers is #6469's scope. Because the file is blank, the blocking + agentic-remediation path is wired but never triggers today; every consumer must fail-closed and independently optional (present -> include; absent -> omit silently; invalid/symlink/non-regular -> omit and warn). No inter-file dependency between guidelines and invariants.
- **Source**: issue
