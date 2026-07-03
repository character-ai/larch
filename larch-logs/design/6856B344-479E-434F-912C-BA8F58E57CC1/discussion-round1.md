## Decision 1: Which AskUserQuestion call sites need the fix
- **Question**: Does the 60-second no-response timeout only hit the two `-s`-gated prompts (Step 1d.7 outline approval, Gate C final approval), or every `AskUserQuestion` call in `/design`?
- **Resolution**: Every call, not just the two `-s`-gated ones. Reproduced directly: two consecutive Step 1c clarifying-question attempts, which fire regardless of `-s`, both returned the harness's "No response after 60s ... proceed using your best judgment" fallback instead of a real answer. The fix must apply uniformly across `/design`.
- **Source**: observed (direct reproduction this session; operator did not answer either attempt)

## Decision 2: What "wait indefinitely" means given a single tool call cannot block forever
- **Question**: Since a single `AskUserQuestion` call appears to hard-time-out at about 60 seconds, how should "wait for answers indefinitely" be implemented?
- **Resolution**: Re-fire the identical `AskUserQuestion` call on every no-response fallback, uncapped, instead of proceeding on a guessed answer. This matches the fallback message's own suggested alternative ("you can re-ask this question later if it's still relevant") and delivers indefinite waiting through retries rather than one unbounded call.
- **Source**: observed (inferred from the fallback message's own wording; operator unavailable to confirm)

## Decision 3: Fix stays local to /design
- **Question**: Should this live in a new cross-skill shared reference (reusable by `/implement` and others), or stay local to `/design`'s own SKILL.md?
- **Resolution**: Keep it local to `/design`'s Anti-patterns section in SKILL.md. The issue is filed specifically against `/design`. Broadening to a shared cross-skill mechanism now would be unrequested scope expansion; other skills can adopt the same pattern later if they hit the same problem.
- **Source**: codebase (issue title scopes explicitly to `/design`; AGENTS.md/KARPATHY_CLAUDE.md favor minimum-change fixes)
