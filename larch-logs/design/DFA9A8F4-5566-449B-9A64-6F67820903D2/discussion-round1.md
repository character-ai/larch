## Decision 1: Scope of the unified helper output
- **Question**: Should the shared helper emit just the OOS clause, the full voter-prompt body, or two named fragments?
- **Resolution**: Full voter-prompt body, with skill-specific deltas (ballot ID grammar `FINDING_N` vs `FINDING_N`+`OOS_N`, context file references like diff/plan, panel-role tagline) passed in as flags. Matches the issue's "emits the common voter-prompt body" wording. Eliminates drift across the entire prompt, not just the OOS section.
- **Source**: user

## Decision 2: Problem-vs-solution rule scope
- **Question**: Should the "evaluate problem, not remedy" rule apply to OOS only, to all FINDING items, or both?
- **Resolution**: The unified prompt carries both:
  1. The existing general rule ("Do NOT vote NO solely because you dislike or distrust the proposed fix — fix proposals are informational; the coder decides the exact change. Vote NO only when the stated problem is not real or not worth raising.") applies to ALL findings (in-scope and OOS), and `/design` plan voters gain it via the unified helper (currently they lack it).
  2. The OOS section gains an explicit, emphatic problem-vs-solution clause ("evaluate the problem described... treat any suggested remedy as informational only") as reinforcement.
- **Source**: user

## Decision 3: Test harness coverage
- **Question**: Does the new helper need a dedicated harness, or are updates to the two existing dispatcher harnesses sufficient?
- **Resolution**: Add a new dedicated harness for the helper itself (asserts the helper's output for canonical inputs: FINDING-only mode, FINDING+OOS mode, problem-vs-solution clause presence) AND update both `scripts/test-dispatch-plan-voters.sh` and `scripts/test-dispatch-code-voters.sh` to assert their composed prompts contain the unified text.
- **Source**: user

## Decision 4: voting-protocol.md sync strategy
- **Question**: How should `skills/shared/voting-protocol.md` be kept in sync with the canonical OOS text?
- **Resolution**: Embed the canonical OOS clause verbatim in `voting-protocol.md` with a comment pointing at the helper script as the runtime authority. Simple to verify, low coupling, survives helper-script renames.
- **Source**: user

## Decision 5: SKILL.md main-agent-vote-required prose
- **Question**: Should the canonical OOS clause text be embedded inline in the main-agent-vote-required prose for both `/design` and `/implement`, or only one of them?
- **Resolution**: Both `/design` SKILL.md Step 3 MAV paragraph (line ~598) and `/implement` SKILL.md Step 5 MAV paragraph (line ~1238) get the canonical OOS clause text inline. Ensures all three filing surfaces (plan voters, code voters, main-agent fallback in both `/design` and `/implement`) emit the same instruction — the issue's acceptance criterion "All three filing surfaces emit the same OOS judging instruction".
- **Source**: user

## Decision 6: Main-agent paths in scope
- **Question**: Which main-agent fallback paths must be updated to reference / embed the canonical OOS text?
- **Resolution** (resolved by Decision 5 + codebase inspection): The two SKILL.md paragraphs identified above. Note that `/review` does not have its own main-agent adjudication prose — `skills/review/scripts/review-core.sh` only emits `REVIEW_CORE_STATUS=main-agent-vote-required`; the actual adjudication prose lives in `/implement` SKILL.md Step 5 (for `/review-and-fix` flows) and `/design` SKILL.md Step 3 (for plan-review MAV). The issue mentions `review-core.sh` but the actual adjudication text is in the SKILL.md files; updating those two paragraphs covers the `/review`-MAV surface.
- **Source**: codebase (skills/review/scripts/review-core.sh:650-684 only emits status; no inline rubric text)

5 decisions resolved (1 from codebase, 5 from user).
