### FINDING_1: Lint scan scope is too narrow
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Scanning only `python/larch` while implicitly excluding tests leaves raw `"gh"` argv literals elsewhere in the intended Python surface unenforced, allowing adoption to decay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Scan the repository Python source scope, exempt only python/larch/git/ and the explicit test-fixture suppression allowlist or pragmas.
  - From Codex-Innovation: Scan the required Python scope outside larch/git and represent fixture exemptions with a documented explicit allowlist or same-line reason-bearing pragmas.
  - From Codex-Pragmatic: Scan every intended Python source outside larch/git, and use an explicit fixture pragma or allowlist rather than implicit test-file exclusion
  - From Codex-Requirements: Scan the full intended Python surface outside python/larch/git and suppress test fixtures only through the specified explicit pragma or versioned allowlist; add coverage for an unsuppressed fixture violation and an explicit suppression


### FINDING_2: Tuple scanning falsely flags CLI registry keys
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Ast Gate Integrator, Codex-dyn-Ast Gate Integrator
- **Severity**: major
- **Concern**: A blanket `ast.List`/`ast.Tuple` scan for literals beginning with `"gh"` reports permanent `_REGISTRY` dispatch-key tuples that are not subprocess argv, making the zero-finding gate unreachable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either skip list/tuple literals used as ast.Dict keys (covers _REGISTRY), or restrict detection to ast.List only (all live gh argv literals outside larch/git/ use lists today). Add a negative fixture that mirrors _REGISTRY tuple keys and assert it is not reported.
  - From Cursor-dyn-Ast Gate Integrator: Limit violations to gh-argv shapes (for example list literals, or tuple/list nodes that are Call args or assigned to argv-like names), or explicitly exempt _REGISTRY dict-key tuples in python/larch/cli.py; document whichever permanent carve-out stays.
  - From Codex-dyn-Ast Gate Integrator: Plan an explicit approved same-line reason-bearing pragma for these non-argv dispatcher keys, or rewrite them to use a named non-literal domain key.


### FINDING_3: Tests lack a registry-key negative control
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The planned tests do not prove that registry-style tuple dict keys are ignored while actual list argv literals are reported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one case: a module-level dict with ("gh", "resolve-repo") (and optionally ("git", "sync")) keys plus a separate ["gh", "api"] assignment; expect only the list assignment is reported.


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/cli.py:618-621
- **Concern**: [SCOPE-REDUCTION] Blanket list/tuple first-element rule also matches CLI dispatch dict keys, not gh argv literals (G-Py-7). Scenario: The plan flags every ast.List/ast.Tuple whose first Constant is "gh" in every expression context. That matches the four permanent `("gh", "<subcmd>")` keys in the `_COMMANDS` registry in `python/larch/cli.py`. They are CLI route tuples, not subprocess argv. With no baseline, the lint stays red after repoint work unless those lines get perpetual pragmas.
- **Proposed resolution**: Narrow the rule to gh argv shapes the issue targets: flag literals passed as the first positional arg to a call and/or assigned for runner/subprocess execution, and explicitly skip literals used only as ast.Dict keys. Add a pytest fixture mirroring the cli.py dispatch-key pattern and assert it is not reported.


### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/cli.py:618-621
- **Concern**: [SCOPE-REDUCTION] Broad list/tuple literal rule flags CLI route registry tuples, not gh argv. Scenario: The plan flags every `ast.List`/`ast.Tuple` whose first element is the constant `"gh"`. `python/larch/cli.py` defines four permanent `("gh", "<subcommand>")` dispatcher keys in the command table. Those are route identifiers, not subprocess argv. After repoint work removes real `["gh", ...]` call sites, the lint still fails on these lines, so the no-baseline gate cannot pass on a clean tree.
- **Proposed resolution**: Narrow detection to gh argv construction: skip list/tuple nodes used only as `ast.Dict` keys (covering the CLI table), or otherwise tie findings to argv-shaped use (call first argument, assignment to argv-like names, return of argv). Add an explicit regression test that `("gh", "resolve-repo")` route keys stay clean while a real `proc.run(["gh", ...])` literal still reports.


### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/cli.py:618-621
- **Concern**: [SCOPE-REDUCTION] Context-blind list/tuple rule will flag CLI dispatcher registry keys. Scenario: Plan flags every list/tuple whose first element is the literal "gh" in all AST contexts. After repoint removes real argv literals, four intentional _REGISTRY keys `("gh", <verb>)` in python/larch/cli.py remain. Testing expects a clean scan with zero findings, so the gate cannot pass without extra handling the plan does not name.
- **Proposed resolution**: Either restrict detection to ast.List only (all current production argv violations outside larch/git/ use list syntax; the only tuple matches outside git/ are these registry keys), or keep tuple detection and add an explicit plan step for same-line `# lint-gh-argv-literal: ok CLI dispatcher registry key` pragmas on those four entries (or a documented allowlist for that registry block). ### 1. correctness — `python/larch/cli.py:618-621` **Concern:** The plan bans every `ast.List` / `ast.Tuple` whose first element is the constant `"gh"`, in every expression context. That rule matches the four `("gh", <verb>)` dispatcher keys in `_REGISTRY`, which are route tuples, not subprocess argv. They sit outside `larch/git/` and will still be present after repoint. The testing strategy requires a clean post-repoint scan, so this is a hard false positive the plan never addresses. **Suggested revision:** Prefer the minimum-change fix: detect `ast.List` only. Every real argv violation outside `larch/git/` today uses list syntax (`["gh", ...]`); the only `("gh", ...)` tuples outside `git/` are these registry keys. If tuple detection stays, add a firm plan step (pragma or allowlist) for `python/larch/cli.py:618-621`.


### FINDING_2: Production pragmas can disable the hard ban
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Allowing production literals to use the planned pragma lets violating code bypass the adoption lint, allowing enforcement to decay while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Permit pragma suppression only for explicit test-fixture paths or a reason-bearing fixture allowlist; reject production pragmas and replace the planned production-side suppression test with that rejection case


### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [SCOPE-REDUCTION] Production pragmas defeat the hard ban. Scenario: The plan explicitly permits and tests a production-side pragma, so a new raw production `["gh", ...]` argv can bypass the required ban with a comment.
- **Proposed resolution**: Restrict suppression to test fixtures under `python/tests/` or an explicit fixture allowlist, and remove production-side pragma support and coverage.


