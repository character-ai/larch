## Goal
Implement issue #6295: [IMPLEMENTING] Wire the readability directive into the code-reviewer agents.

## Implementation Plan
## Plan

## Approach

Add `**MANDATORY — READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**` to every reviewer agent prompt body. This uses the same `orchestrator-inline` directive form that SKILL.md files already use; the agent's Read tool can follow it. Keep TSV grammar and output sentinels byte-stable.

Update `skills/shared/reviewer-templates.md` first (canonical source for generated agents), then regenerate four generated agents and all pre-rendered bodies. Add the directive directly to five hand-maintained specialist agents.

Extend `lint_readability_preamble.py` with `_agent_files()` and `_check_agent_path_form()` modeled after `_skill_files()` / `_check_skill_path_form()`. This auto-walks `agents/code-reviewer.md` and `agents/reviewer-*.md` using the existing `orchestrator-inline` check; no new variant or TSV rows needed.

After adding the directive line to agent files, `python/skill-closure-baseline.json` must be regenerated because panel-tier closure includes those files and the line count will grow.

## Files to modify/create

### UPDATED: skills/shared/reviewer-templates.md

Add the directive to each of the four `<!-- BEGIN GENERATED_BODY -->` bodies (Code Reviewer, Plan Fidelity, Code Robustness, Security + Structure + Tests). Place it after the opening "You are..." sentence. Keep output grammar byte-stable.

### UPDATED: agents/code-reviewer.md

Regenerate via `python3 python/cli.py generate code-reviewer-agent`.

### UPDATED: agents/reviewer-plan-fidelity.md

Regenerate via `python3 python/cli.py generate reviewer-plan-fidelity-agent`.

### UPDATED: agents/reviewer-code-robustness.md

Regenerate via `python3 python/cli.py generate reviewer-code-robustness-agent`.

### UPDATED: agents/reviewer-security-structure-tests.md

Regenerate via `python3 python/cli.py generate reviewer-security-structure-tests-agent`.

### UPDATED: agents/reviewer-correctness.md

Add the directive by hand after the opening "You are..." line.

### UPDATED: agents/reviewer-edge-cases.md

Add the directive by hand.

### UPDATED: agents/reviewer-security.md

Add the directive by hand.

### UPDATED: agents/reviewer-structure.md

Add the directive by hand.

### UPDATED: agents/reviewer-testing.md

Add the directive by hand.

### UPDATED: agents/pre-rendered/.manifest

Regenerate via `python3 python/cli.py generate pre-rendered-reviewer-prompts` after all agent edits.

### UPDATED: agents/pre-rendered/reviewer-code-robustness-body.txt

Regenerate from `agents/reviewer-code-robustness.md`.

### UPDATED: agents/pre-rendered/reviewer-correctness-body.txt

Regenerate from `agents/reviewer-correctness.md`.

### UPDATED: agents/pre-rendered/reviewer-edge-cases-body.txt

Regenerate from `agents/reviewer-edge-cases.md`.

### UPDATED: agents/pre-rendered/reviewer-plan-fidelity-body.txt

Regenerate from `agents/reviewer-plan-fidelity.md`.

### UPDATED: agents/pre-rendered/reviewer-security-body.txt

Regenerate from `agents/reviewer-security.md`.

### UPDATED: agents/pre-rendered/reviewer-security-structure-tests-body.txt

Regenerate from `agents/reviewer-security-structure-tests.md`.

### UPDATED: agents/pre-rendered/reviewer-structure-body.txt

Regenerate from `agents/reviewer-structure.md`.

### UPDATED: agents/pre-rendered/reviewer-testing-body.txt

Regenerate from `agents/reviewer-testing.md`.

### UPDATED: python/larch/lint/lint_readability_preamble.py

Add two functions modeled after `_skill_files()` / `_check_skill_path_form()`:
- `_agent_files(root)`: walks `agents/code-reviewer.md` and `agents/reviewer-*.md`.
- `_check_agent_path_form(*, root)`: checks each file for the `orchestrator-inline` directive via `_orchestrator_style_re`; reports missing directive and wrong path form.

Call `_check_agent_path_form(root=root)` in `main()` alongside the existing `_check_skill_path_form` call.

### UPDATED: scripts/lint-readability-preamble.tsv.md

Add a sentence to `## Dynamic skill coverage` noting that the lint also walks `agents/code-reviewer.md` and `agents/reviewer-*.md`.

### UPDATED: python/tests/lint/test_lint_readability_preamble.py

Add tests:
- `test_missing_agent_directive`: `agents/code-reviewer.md` without directive → rc 1.
- `test_agent_directive_present`: `agents/code-reviewer.md` with correct directive → rc 0.
- `test_agent_wrong_path_form`: `agents/reviewer-foo.md` with dev-path directive → rc 1.
- `test_non_reviewer_agent_not_checked`: `agents/codex-implementer.md` without directive → rc 0.

### UPDATED: python/skill-closure-baseline.json

Regenerate via `python3 python/cli.py lint skill-closure-growth --write` after directive additions and generate check passes.

## Edge cases

- Do not add `<READABILITY_STYLE>` token to agent prompts; that wiring only exists in the brainstorm and plan-review render surfaces.
- Exclude `agents/_implementer-base.md`, `agents/codex-implementer.md`, `agents/cursor-implementer.md`, and `agents/orchestrator-aggregator.md` from the auto-walk (not reviewer agents with user-facing finding text).
- Pre-rendered `agents/pre-rendered/reviewer-*-body.txt` files inherit the directive from their source agents via regeneration.

## Failure modes

- If the directive text disrupts reviewer output grammar (TSV headers, JSONL keys, `no_issues_found` sentinel), parsers silently drop findings. Place the directive before the output-format section, never inside it.
- If `skill-closure-baseline.json` is not regenerated, CI fails on `lint skill-closure-growth --skill panel-tier`.
- If pre-rendered bodies are not regenerated after agent edits, `generate check` fails.

## Testing strategy

1. Edit `reviewer-templates.md` and hand-maintained agents.
2. Regenerate: `python3 python/cli.py generate code-reviewer-agent`, `reviewer-plan-fidelity-agent`, `reviewer-code-robustness-agent`, `reviewer-security-structure-tests-agent`, `pre-rendered-reviewer-prompts`.
3. Run `python3 python/cli.py lint readability-preamble`.
4. Run `python3 -m pytest python/tests/lint/test_lint_readability_preamble.py -q`.
5. Run `python3 python/cli.py generate check`.
6. Run `python3 python/cli.py lint skill-closure-growth --write`.
7. Run `python3 python/cli.py lint skill-closure-growth --skill panel-tier`.
8. Run `python3 python/cli.py checks run-relevant`.

## Acceptance

1. Edit `reviewer-templates.md` and hand-maintained agents.
2. Regenerate: `python3 python/cli.py generate code-reviewer-agent`, `reviewer-plan-fidelity-agent`, `reviewer-code-robustness-agent`, `reviewer-security-structure-tests-agent`, `pre-rendered-reviewer-prompts`.
3. Run `python3 python/cli.py lint readability-preamble`.
4. Run `python3 -m pytest python/tests/lint/test_lint_readability_preamble.py -q`.
5. Run `python3 python/cli.py generate check`.
6. Run `python3 python/cli.py lint skill-closure-growth --write`.
7. Run `python3 python/cli.py lint skill-closure-growth --skill panel-tier`.
8. Run `python3 python/cli.py checks run-relevant`.

diff_lines: 170

## Test plan
(no test plan section in plan-file)
