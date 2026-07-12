### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/design/design_lifecycle.py:218-229
- **Concern**: `design_lifecycle.py` barrel still imports private Step 5c trailer helpers omitted from the migration list. Scenario: The plan refactors `design_step5c.py` to replace `_AUTO_COMPOSE_OPTIONAL_TRAILER_RE`, `_split_plan_body_and_trailers`, `_peel_trailing_optional_trailers`, and related trailer helpers with `plan_grammar`, but `design_lifecycle.py` still imports those symbols at module load. Removing or renaming them during the Step 5c refactor raises `ImportError` on `larch.design.design_lifecycle` before any grammar test runs, breaking every registered `design` CLI verb and modules such as `clarify.py` that import the barrel.
- **Proposed resolution**: Add `### UPDATED: python/larch/design/design_lifecycle.py` to drop obsolete Step 5c trailer imports or repoint them to `plan_grammar` public APIs; alternatively keep thin backward-compat aliases in `design_step5c.py` only until the barrel is updated. Add an import smoke test that `import larch.design.design_lifecycle` succeeds after the Step 5c refactor.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_lifecycle.py:218-229
- **Concern**: Prior round-1 barrel-import gap remains: `design_lifecycle.py` still imports Step 5c trailer privates omitted from the firm file list. Scenario: The plan updates `design_step5c.py` to move trailer split/peel/compose logic into `plan_grammar`, but `design_lifecycle.py` still does `from larch.design.design_step5c import (_AUTO_COMPOSE_OPTIONAL_TRAILER_RE, _split_plan_body_and_trailers, _peel_trailing_optional_trailers, ...)`. Those symbols are unused in the barrel but are resolved at import time, so renaming or deleting them breaks `import larch.design.design_lifecycle` and every registered `python/cli.py design …` verb before any grammar test runs
- **Proposed resolution**: Add `### UPDATED: python/larch/design/design_lifecycle.py` to drop stale Step 5c private imports or repoint them to `plan_grammar` public helpers; keep the change limited to the import block

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5c.py:437-456
- **Concern**: Step 5c auto-compose needs a documented trailer subset beyond optional-size; the plan names only optional-size and firm-heading subsets. Scenario: `_AUTO_COMPOSE_OPTIONAL_TRAILER_RE` spans `difficulty:` plus the four Gate B optional-size keys (`diff_added`, `diff_deleted`, `mechanical_churn`, `oversize_override`). The plan exports an optional-size subset matching Gate B/bootstrap/publish, which excludes `difficulty`. Repointing Step 5c peel/split to that subset would leave `difficulty:` in the body, so `_auto_compose_plan_md` and orphan-trailer recovery can drop difficulty or mis-order trailers relative to today’s Step 5c and `test_design_lifecycle.py` auto-compose cases
- **Proposed resolution**: In `plan_grammar.py`, export a documented Step-5c auto-compose subset (optional-size keys plus `difficulty`, still excluding `review_status` / `rounds_completed`) and wire Step 5c split/peel helpers to it explicitly in the `design_step5c.py` plan step

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_wire.py:370-381
- **Concern**: The planned scope extraction can still terminate before parsing accepted level-two firm headings or fenced examples. Scenario: Inside `Files to modify/create`, a valid `## NEW: path` heading matches the local generic `^##\s+` section terminator before the shared firm-heading iterator sees it. A fenced `##` example can likewise end the section early and hide later real paths. Dispatch and dirty-tree scope checks then miss paths even though the shared grammar accepts the plan.
- **Proposed resolution**: Define section-bound precedence around the shared fence-aware iterator: recognize valid firm headings before generic section termination, and ignore all headings while inside fences. Add fixtures combining level-two headings, fenced heading-like text, and later scope entries.

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py:1108-1118
- **Concern**: The plan does not migrate `_extract_file_replacement` to the shared terminal `diff_lines` parser. Scenario: This active revise-plan path still records the last `diff_lines:` line found anywhere in the candidate block. A non-terminal or earlier line can therefore determine the replacement boundary, while the new grammar requires terminal contiguous-trailer semantics. The stated migration of local terminal checks and the test list do not name this extraction path.
- **Proposed resolution**: Use the shared terminal trailer result when selecting the replacement boundary, reject candidates without a valid terminal `diff_lines`, and add a revise-waterfall fixture with an earlier and a final conflicting `diff_lines:` line.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/state/bootstrap.py:863-880
- **Concern**: The bootstrap migration leaves a second local `diff_lines` parser outside the normative grammar. Scenario: `bootstrap` is listed for migration, but its change description only replaces the optional size-trailer regex. Its local whole-line `diff_lines` regex and fence-index scan remain an independent trailer owner, contrary to the single-owner goal and the cleanup check. A malformed or non-terminal candidate can be handled differently by bootstrap than by the shared terminal parser.
- **Proposed resolution**: Route `diff_lines` location and fenced handling through `plan_grammar` while preserving bootstrap’s provenance-stripping policy, then add a bootstrap regression for conflicting/non-terminal `diff_lines` lines.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_lifecycle.py:218-229
- **Concern**: Step 5c refactor omits `design_lifecycle.py` barrel import updates. Scenario: `design_lifecycle.py` eagerly imports private Step 5c trailer helpers (`_AUTO_COMPOSE_OPTIONAL_TRAILER_RE`, `_split_plan_body_and_trailers`, `_peel_trailing_optional_trailers`, `_build_trailer_lines_from_sidecars`, `_optional_trailer_lines_from_values_file`, and related symbols). The plan repoints those helpers to `plan_grammar` and says to remove local regexes, but it does not list `design_lifecycle.py`. Renaming or deleting those privates breaks `from larch.design.design_step5c import ...` at `design_lifecycle` import time, which prevents loading every registered `design` CLI verb and any module that imports `design_lifecycle` (for example `plan_review.py`, `plan_review_loop.py`, `plan_review_normalize.py`) before grammar tests run.
- **Proposed resolution**: Add `### UPDATED: python/larch/design/design_lifecycle.py`: drop removed private re-exports, repoint any retained symbols to `plan_grammar` or thin public Step 5c wrappers, and add a barrel import smoke test so a Step 5c refactor cannot break `larch.design.design_lifecycle` load.
