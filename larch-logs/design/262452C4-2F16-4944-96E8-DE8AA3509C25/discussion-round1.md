# Discussion Round 1

## Decision 1: Suppression scope
- **Question**: How wide should the Step 5b.5 narrative-suppression guidance go — just that step, or also a shared note for any /design file-authoring step?
- **Resolution**: Both. Tighten the Step 5b.5 section of `skills/design/SKILL.md` and `skills/design/references/finalize-step5.md`, AND add a shared anti-narrative note covering any `/design` step that authors a file (diagram, plan, etc.). The shared note is the durable lever; the 5b.5 tightening is the point fix.
- **Source**: user

## Decision 2: Sanitizer pre-check in Step 5b.5
- **Question**: Several listed lines ("Let me verify the candidate passes the Mermaid sanitizer…", "Ran N shell commands", "Diagram candidate is valid (STATUS=ok). Continuing to Step 5c…") come from Claude pre-running the sanitizer during Step 5b.5 even though Step 5c owns the authoritative sanitize. Forbid that pre-check, or keep it and suppress only the narration?
- **Resolution**: Keep allowing the optional sanitizer pre-check; suppress only its narration. Do NOT add an instruction forbidding the sanitizer in Step 5b.5.
- **Source**: user

## Decision 3: Hard constraint — harness-rendered lines are out of scope
- **Question**: Are harness tool-use renderings (`⏺ Write(...)`, `Wrote N lines to …`, `Ran N shell commands`) suppressible via skill instructions?
- **Resolution**: No. Those are Claude Code harness renderings of tool use, not Claude-authored prose. They are uncontrollable from the skill layer and explicitly out of scope; the issue author already acknowledges this ("not all of them may be under our control"). Only Claude-authored prose lines are in scope.
- **Source**: codebase + issue

## Non-goals
- Do NOT change script/Python behavior (`design-step3b-entry.sh`, `design-step3b-sanitize.sh`, `design-step5c`). The offending lines are orchestrator prose, not script stdout. This is a docs/skill-prompt change only.
- Do NOT forbid the Step 5b.5 sanitizer pre-check (Decision 2).
- Do NOT attempt to suppress harness tool-use renderings (Decision 3).
