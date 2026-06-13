# Review Round 4

- Mode: `diff`
- 4 accepted, 4 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Deleted plan-size contract docs still cited across /design skill surface
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The branch deletes `skills/design/scripts/check-plan-size.md` (and lists it in `python/migrated-scripts.tsv`) while normative /design docs still cite it as the plan-size machine contract. `skills/design/references/flags.md` (and related Gate B docs such as `design-postplan-emit.md` and `skills/design/SKILL.md`) point operators and maintainers at a missing file. `test-check-plan-size.md` is also migrated/deleted while still referenced. Threshold, optional-trailer, and drift semantics are therefore undefined in loaded skill rules during Step 2b.5 or Gate B size-brake debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore and repoint check-plan-size.md to Python CLI, or update all cites and remove from migrated-scripts.tsv after sweep.
  - From cursor-specialist-edge-cases-output.txt: Restore an updated check-plan-size.md pointing at python/plan_quality.py and python/cli.py plan check-size, or repoint all normative cites in the same PR.
  - From codex-generic-output.txt: Restore and update the contract doc, or remove the sibling references and point all plan-size contract prose at `python/plan_quality.py` and `python/test_plan_quality.py`.


### FINDING_2: Optional-trailer test parity lost after bash-to-Python cutover
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `make test-trailer-helpers` was retargeted to `pytest -k optional_trailer` with only one basic snapshot/validate test, while `test-trailer-awk.sh` edge-case matrix (0[89] rejection, duplicate-trailer, block-boundary, has-key cases) is orphaned and no longer runs in CI. Optional-trailer regressions can reach /design Gate B undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port test-trailer-awk.sh scenarios into python/test_plan_quality.py or keep awk harness in CI until parity


### FINDING_5: Golden TSV parity suite collects zero cases
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: At `python/test_plan_quality.py:368-371`, `FIXTURE_PAIRS` pairs each `*-plan.md` with `plan.with_suffix(".tsv")` (e.g. `basic-plan.tsv`), but fixtures on disk use retired harness naming (`basic.tsv`, `prefix.tsv`, etc.). No `*-plan.tsv` files exist, so parametrized `test_parse_plan_commands_golden_fixtures` collects zero cases and `make test-parse-plan-commands` can pass without comparing parser output to any golden file. That breaks the plan's byte-compatible TSV contract and leaves parser drift undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Map plans to TSV the way the old harness did, e.g. `plan_path.with_name(plan_path.stem.removesuffix("-plan") + ".tsv")`, and assert the parametrized suite runs all 13 fixture pairs before deleting the shell harness.


### FINDING_6: Auto-fix revalidation hard-codes plugin repo root
- **Reviewer(s)**: dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step-validator-autofix.sh:117-128` passes `--repo-root "$_repo_root"` with `_repo_root` hard-coded to `$CLAUDE_PLUGIN_ROOT` only. The retired `auto-fix-plan-commands.sh` resolved `REPO_ROOT` as `git -C "$PWD" rev-parse --show-toplevel` first, then fell back to `PLUGIN_ROOT`, and revalidation used that root. In a consumer-repo `/design` run whose plan cites `scripts/*` or `skills/*/scripts/*` under the consumer tree, auto-fix revalidation now probes plugin paths instead of consumer paths. That can miss real defects, falsely clear defects, or stall the Gate B autofix loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-callsite-cutover-output.txt: Restore the old precedence in `design-step-validator-autofix.sh` (and/or `plan_quality.auto_fix_commands`): default `--repo-root` to the current git toplevel when available, fall back to `CLAUDE_PLUGIN_ROOT`, and add a harness case that runs auto-fix from a non-plugin cwd with consumer-local script fixtures.


