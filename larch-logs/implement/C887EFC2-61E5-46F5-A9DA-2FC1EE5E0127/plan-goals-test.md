## Goal
Implement issue #5840: [IMPLEMENTING] [BUG] Stale skill-closure baseline: implement token gate loose ~16% (round IX).

## Implementation Plan
**Severity**: Medium (CI ratchet under-measures; no runtime change).

**What**: `python/skill-closure-baseline.json` (added by #5783, PR #5831) was generated against the **pre-#5787** verbose `implement/SKILL.md` and never regenerated, even though #5783 merged *after* #5787 compressed that file. The implement **token** gate is therefore loose by ~16%.

**Evidence**:
- Committed baseline: implement `skill_md_estimated_tokens=33760`, `closure_estimated_tokens=38486`.
- Fresh `python3 python/cli.py skill-closure report`: implement `28413` / `33139` (delta **-5347 tokens, ~16%**). Design matches (-16 / -4). All line counts match.
- `git show c73008dd4^:skills/implement/SKILL.md` = 789 lines / 33760 tokens = **exact** match to the committed baseline, proving it was captured before #5787's prose compression.
- The `skill-closure-growth` lint runs **green** (live < baseline everywhere) — so the gate is *loose*, not red.

**Consequence**: `implement/SKILL.md` prose can regrow ~21K characters (as long as net lines stay <=789) and pass the gate silently — defeating the enabler's stated "stops silent backsliding" purpose for the very file the round compressed. The line gate (789) is still exact, so line growth is still caught.

**Root cause #2 (why it shipped undetected)**: no test asserts the committed baseline equals a fresh scan, and the gate is one-directional (`>`), so a shrink never forces a re-baseline (`lint_skill_closure_growth.py:407`). The repo precedent is `complexity-baseline.json`, which is STRICT (regen-enforced).

**Fix**:
- Run `make regen-skill-closure-baseline` and commit the refreshed data.
- Add a STRICT freshness check (test/CI assertion that committed baseline == fresh `--write`), mirroring the `complexity-baseline.json` contract.

**Origin**: PR #5831 (#5783), umbrella #5788.

## Test plan
(no test plan section in plan-file)
