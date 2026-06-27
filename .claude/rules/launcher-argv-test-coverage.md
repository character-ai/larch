---
paths: ["python/larch/agents/agents.py", "python/test_launch_review.py", "python/cli.py", "scripts/launch-*.sh", "scripts/test-launch-*.sh", "python/design_step_log.py", "python/test_design_step_log.py", "python/review_and_fix.py", "python/test_review_and_fix.py", "python/implement_dispatch.py", "python/test_implement_dispatch.py", "skills/implement/scripts/test-step2-*.sh", "skills/design/scripts/design-step3-review.sh", "skills/design/scripts/test-design-step3-review.sh", "python/plan_review.py", "python/test_plan_review.py"]
---

# Launcher Argv Test Coverage

Changing argv validation, output grammar, or rejection messages in
`scripts/launch-*.sh`, the Step 1/5 launchers, or the Step 2 dispatcher
stack (`implement run-dispatch` / `implement step2-dispatch`) requires a
same-PR regression harness update. "Ship launcher change → file OOS for
harness gap → fix later" is the bug.

Harness paths are **not** uniform:

- `python/cli.py agent launch-review --tool cursor|codex` → `python/test_launch_review.py`
- `python/cli.py plan step1-log` → `python/test_design_step_log.py`
- `python/cli.py review-and-fix step5` → `python/test_review_and_fix.py` via Make targets `test-review-and-fix-step5`, `test-review-and-fix-step5-starting-round`, `test-review-and-fix-dispatch`, `test-review-and-fix-convergence`, and `test-review-and-fix-parsers`
- `python/cli.py agent launch-codex-implement` / `agent launch-cursor-implement` → `python/test_implement_dispatch.py` (and `python/test_implement_dispatch.py` for cross-coder dispatcher coverage)
- `python/cli.py implement run-dispatch` → `python/test_implement_dispatch.py`
- `python/cli.py plan-review run` → `python/test_plan_review.py`

The sibling `<basename>.md` (per `.claude/rules/script-md-siblings.md`)
names the current harness; read it before assuming a path. `docs/linting.md`
lists CI harnesses.

When you change a launcher:

- **Read the matching harness**. Asserted reject paths, accept paths,
  validation message text, and exit codes are contract.
- **Add or extend assertions in the same PR** for every new accept path and
  reject path, exact validation message text (pin literally), and each
  branch exit code.
- **Apply parity to other launchers** per
  `.claude/rules/external-tool-launcher-parity.md` when the surface is
  shared: timeout grammar, api-key forwarding, model arg passing.

If a concrete reason blocks same-PR coverage, file an OOS issue naming the
missing assertion; do not ship with a quiet harness gap.
