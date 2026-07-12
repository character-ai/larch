## Goal
Implement issue #7075: [IMPLEMENTING] contract-unification [FEATURE] plan_grammar.py follow-ups: TRAILER_KEYS-derived preflight regex, promised consumer tests, fence-state consolidation.

## Implementation Plan
## Plan

### UPDATED: python/larch/design/plan_grammar.py

- Move `_balanced_fence_line_indices` here from `issue_create.py`.
- Reuse it in `iter_heading_events` so heading parsing, issue creation, and OOS validation share balanced backtick and tilde fence semantics.
- Preserve marker-length and whitespace-only closing-suffix rules. An unmatched opener must not hide later headings.

### UPDATED: python/larch/issue/issue_create.py

- Import `_balanced_fence_line_indices` from `plan_grammar`.
- Remove the local helper and its fence regex.
- Preserve existing issue parsing behavior for balanced, mismatched, and unclosed fences.

### UPDATED: python/larch/issue/file_oos.py

- Import `_balanced_fence_line_indices` from `plan_grammar` instead of `issue_create.py`.
- Keep `_validate_issue_cap_input`’s heading count aligned with `parse_issue_input` under the shared fence semantics.

### UPDATED: python/larch/implement/preflight.py

- Build `_RECOGNIZED_TRAILER_PREFIX_RE` from `plan_grammar.TRAILER_KEYS`:
  `_RECOGNIZED_TRAILER_PREFIX_RE = re.compile(r"^(?:" + "|".join(plan_grammar.TRAILER_KEYS) + r"):")`
- Keep malformed terminal metadata policy and error text unchanged.

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Update G-Md-3 to identify the helper in `python/larch/design/plan_grammar.py`.
- Continue referring to the helper by symbol rather than line number.

### UPDATED: python/tests/design/test_plan_grammar.py

- Add shared-helper coverage for balanced backtick and tilde fences, longer opening markers, invalid closers, and unclosed openers.
- Verify `iter_heading_events` skips exactly the balanced fenced lines and preserves headings after unmatched openers.

### UPDATED: python/tests/issue/test_file_oos.py

- Add focused OOS issue-cap coverage showing fenced OOS-shaped headings are excluded from raw heading counts under the shared helper.
- Cover the behavior needed to keep issue-cap validation aligned with parsed issue items after the import move.

### UPDATED: python/tests/implement/test_preflight.py

- Add direct `_malformed_terminal_metadata` coverage for valid metadata, malformed recognized prefixes, unrecognized adjacent lines, and non-terminal `diff_lines`.
- Assert the recognized-prefix regex covers every `TRAILER_KEYS` member so registry additions cannot silently escape Preflight validation.

### UPDATED: python/tests/calibration/test_difficulty.py

- Add registry-driven final-trailer fixtures that exercise `match_trailer_line` and `parse_final_trailers` through difficulty lookup and rewrite paths.
- Verify all shared trailer keys remain compatible with difficulty metadata.
- Preserve invalid adjacent difficulty, legacy `confidence:`, fallback, and contiguous-block behavior.

### UPDATED: python/tests/agents/test_agents.py

- Extend `parse_drafter_output` tests for valid typed `diff_lines`, malformed values, missing trailers, and non-terminal `diff_lines`.
- Confirm rejection leaves sentinel, scout, and dialectic behavior unchanged.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Add an auto-compose fixture containing the full shared trailer registry.
- Verify composition preserves recognized provenance and size trailers in canonical order with `diff_lines` terminal.

## Edge cases

- Support backtick and tilde fences with longer opening markers.
- Close a fence only with the same marker character, sufficient length, and no non-whitespace suffix.
- Treat unmatched openers as unbalanced, so they do not hide later headings.
- Keep OOS raw-heading counting and issue parsing consistent for fenced heading-like text.
- Stop malformed metadata scanning at unrecognized prefixes.
- Keep `diff_lines` mandatory and terminal for drafter parsing.

## Failure modes

- Divergent fence semantics could change issue, OOS, or plan heading boundaries. Reuse one helper and run all three focused fence suites.
- Removing the helper from `issue_create.py` without repointing `file_oos.py` would break OOS validation imports. Move that consumer in the same change.
- A registry-derived regex could accept malformed values as prefixes. Keep value validation in `match_trailer_line`.
- Consumer tests could pass without reaching shared helpers. Assert observable lookup, rewrite, rejection, composition, and OOS-validation results.

## Testing strategy

Run focused tests:

- `python3 -m pytest python/tests/design/test_plan_grammar.py`
- `python3 -m pytest python/tests/issue/test_issue_create.py`
- `python3 -m pytest python/tests/issue/test_file_oos.py`
- `python3 -m pytest python/tests/implement/test_preflight.py`
- `python3 -m pytest python/tests/calibration/test_difficulty.py`
- `python3 -m pytest python/tests/agents/test_agents.py`
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`

Run changed-file lint and type checks per `docs/linting.md`. Run `python3 python/cli.py lint layering`. Grep production Python to confirm only `plan_grammar.py` defines `_balanced_fence_line_indices`.

## Difficulty rationale

This is a multi-file grammar consolidation with several consumers. Direct code and existing regression fixtures provide high confidence. The change remains behavior-preserving and does not alter a security, session, merge, or CI surface.

## Acceptance

Run focused tests:

- `python3 -m pytest python/tests/design/test_plan_grammar.py`
- `python3 -m pytest python/tests/issue/test_issue_create.py`
- `python3 -m pytest python/tests/issue/test_file_oos.py`
- `python3 -m pytest python/tests/implement/test_preflight.py`
- `python3 -m pytest python/tests/calibration/test_difficulty.py`
- `python3 -m pytest python/tests/agents/test_agents.py`
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`

Run changed-file lint and type checks per `docs/linting.md`. Run `python3 python/cli.py lint layering`. Grep production Python to confirm only `plan_grammar.py` defines `_balanced_fence_line_indices`.

oversize_override: operator
diff_lines: 205

## Test plan
(no test plan section in plan-file)
