# Plan Review Maintainer Reference

**Consumer**: maintainers editing the Step 3 review surface.

**Contract**: editing-only authority for producer ownership, harness inventory, byte-preserved templates, and prompt-source maintenance. Runtime orchestration reads `plan-review-runtime.md`, not this file.

**When to load**: only while editing or maintaining plan-review prompts, renderers, tests, or topology. Do not load during `/design` Steps 0 through 5.

The runtime contracts, slot identities, returned-artifact interpretation, fallback adjudication, and panel tiers live in `plan-review-runtime.md`. Python producer internals live in `python/plan_review.py`; prompt bodies are rendered by `python/cli.py render plan-review` and `python/cli.py render voter`. Preserve the accepted finding and OOS templates in `plan-review-runtime.md` byte-for-byte when changing their producers or tests.

Harness authorities include `skills/design/scripts/test-step3-orchestrator-fence.sh`, `skills/design/scripts/test-design-step3-mav.sh`, `skills/design/scripts/test-step3-review-cap.sh`, and the plan-review Python tests named by `skills/design/SKILL.md`.

<!-- Retained migration inventory for agent-lint S030: test-step3-orchestrator-fence.sh test-design-step3-mav.sh test-step3-review-cap.sh -->
