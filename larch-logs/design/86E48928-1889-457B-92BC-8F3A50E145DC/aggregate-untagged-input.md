### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:5837-5859
- **Concern**: `launch-claude-review --agent-file` renders specialists outside `_review_specialist_render_args` and omits `--findings-ledger-file`. Scenario: Static code-review slots are manifest `agent`-only rows (`review_pipeline.py` ~1012-1022). Codex/Cursor use `launch-review` (plan covers that path). Claude fallback launches via `launch-claude-review` with `--agent-file`, which inline-renders `render specialist` without ledger injection, so round 2+ Claude reviewers never see prior-round rows
- **Proposed resolution**: Route the `--agent-file` branch through `_review_render_specialist_prompt` (or shared `_review_specialist_render_args` plus ledger flag), passing the same resolved `--findings-ledger-file` as other dispatch sites; add a `launch-claude-review` regression test

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/findings_ledger.py:57-62 / python/review_tally.py:628-698
- **Concern**: Plan does not define how tally assembles `title`, `file_line`, and `reason` from ballot blocks. Scenario: Tally loops `split_ballot` blocks but only uses full block text today. Without a shared parser, ledger rows may ship empty or inconsistent `file_line`/`title`/`reason`, weakening cross-round duplicate skip rules that key on those columns
- **Proposed resolution**: Add `findings_ledger.entry_from_block(block: Path) -> dict` (heading title, `- **Location**:` / TSV `location`, concern/`what` via `review_aggregate._problem_text` patterns); call it from both tally writers; unit-test representative code-review and plan-review block shapes ## Findings **1. [correctness]** `python/agents.py:5837-5859` — Claude fallback reviewers miss the ledger. The plan wires ledger injection through `agents.py` `_review_specialist_render_args` / `_review_render_specialist_prompt` and Codex sentinel replay. Static slots built in `review_pipeline.py` carry `agent` only, no `prompt_file`. On Claude fallback, `agent_waterfall.py` calls `launch-claude-review --agent-file`, which re-renders via a separate inline argv list and never passes `--findings-ledger-file`. Round 2+ Claude specialists will not see prior-round ledger rows. **Suggested revision:** Reuse `_review_render_specialist_prompt` (or extend `_review_specialist_render_args`) in `launch_claude_review_main` and pass the same resolved ledger path as `agent_voters.py` / `review_pipeline.py`. **2. [correctness]** `python/findings_ledger.py` / tally call sites — ballot projection fields are unspecified. The plan lists ledger columns and says to source them from ballot data the tally already holds, but does not name a parser for `title`, `file_line`, and `reason`. Ballot blocks use `### FINDING_N:` headings and `- **Location**:` / `- **Concern**:` fields (see `voting.ballot_parse`, `review_aggregate._problem_text`). Without a shared helper, implementers may emit blank or inconsistent cells and duplicate suppression will be unreliable. **Suggested revision:** Add a single `entry_from_block()` helper in `findings_ledger.py` and call it from `review_tally.py` and `plan_review_tally.py`; cover both block shapes in `test_findings_ledger.py`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rendering.py:1035-1109
- **Concern**: Plan does not pin where the ledger section is injected in render_voter_main. Scenario: If implementers append prompt_section at the end, judge duplicate-suppression rules appear after Read the ballot from this path and vote-format instructions, weakening the v1 token win
- **Proposed resolution**: Inject the judge ledger block after the rubric and before out.append(Read the ballot...); mirror the same before-plan-read placement in render_plan_review_main and before agent body in render_specialist_main

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_tally.py:628-733 and python/plan_review_tally.py:304-334
- **Concern**: Ledger assembly lacks a concrete title/file_line/reason extraction contract. Scenario: The plan says title, file_line, and reason come from parsed ballot data the tally already holds, but tally_code_votes and plan_review_tally only split the ballot into per-item block files and read raw text for classification. There is no existing structured title, file_line, or reason field. Implementers may emit empty or inconsistent ledger cells, so round-2+ reviewer/judge skip rules have little to match on and the core duplicate-suppression goal fails silently.
- **Proposed resolution**: Add a small shared helper in python/findings_ledger.py (or voting.py) that, given each split block path, derives title from the ### FINDING_N:/OOS_N: heading, file_line from the first backtick path:line in the block (reuse existing path-line regexes), and reason from the concern/first paragraph; call it from both tally writers when building entries. Extend python/test_findings_ledger.py and tally integration tests with a realistic ballot fixture asserting non-empty title and file_line.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:3924-3949 and python/agents.py:5837-5858
- **Concern**: Codex sentinel write and Claude launch-claude-review render paths are not in the dispatch wiring list. Scenario: The plan wires --findings-ledger-file through _review_specialist_render_args and agents.py launch-review, but Codex compact prompts are written in _review_write_codex_prompt_sentinel without FINDINGS_LEDGER_FILE, and Claude fallback specialists render via launch_claude_review_main --agent-file with a bare render specialist argv. If env-based default derivation is incomplete in either subprocess, static Claude/Codex-replay reviewers in round 2+ can miss the ledger while dynamic slots and judges get it, leaving duplicate suppression partial.
- **Proposed resolution**: Extend the plan to require FINDINGS_LEDGER_FILE in _review_write_codex_prompt_sentinel and in the _review_specialist_render_args sentinel mapping; pass --findings-ledger-file (or the resolved path) in launch_claude_review_main render argv the same way as launch-review. Add agent/launch tests for both paths on a nested IMPLEMENT_TMPDIR/round-2 layout.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:1546-1558
- **Concern**: Ephemeral implement ledger lacks explicit anti-flush guard unlike design publish exclusion. Scenario: `reviewer-prune-ledger.tsv` is explicitly flushed from `IMPLEMENT_TMPDIR` via `run-log write --batch reviewer-prune-ledger`. `findings-ledger.tsv` will live at the same parent root. Plan only cites round-artifact allowlisting and `design_log_publish_flow.py` exclusion; it never states that implement must not copy the prune-ledger flush pattern. An implementer following the adjacent precedent can commit the ephemeral ledger to `larch-logs/implement/<RUN_ID>/`.
- **Proposed resolution**: Add an explicit plan step: do not add a `run-log write` batch for `findings-ledger.tsv` in `review_and_fix.py` (or elsewhere); rely on tmpdir cleanup only. Optionally add a regression test that post-Step-5 flush paths never reference `findings-ledger`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/findings_ledger.py:57-62
- **Concern**: Ledger row assembly underspecified for title file_line and reason columns. Scenario: Issue requires `title`, `file:line`, and one-line `reason` per row. Plan says tally already holds this from `voting.split_ballot`, but `split_ballot` only writes per-item `.md` blocks; tally currently consumes `artifact_text` wholesale and does not parse structured title/location/reason fields. Without a pinned extraction helper, both tally call sites may emit empty or inconsistent `file_line`/`reason` cells, weakening cross-round duplicate matching that v1 depends on entirely via prompt injection.
- **Proposed resolution**: Add a shared `findings_ledger.entry_from_ballot_block(...)` (or equivalent) that parses the `### FINDING_N:` heading for `title`, reuses existing ballot text helpers (e.g. `voting.ballot_parse` / `review_aggregate._problem_text` patterns) for `reason`, and extracts the first repo-relative `path:line` token for `file_line`; call it from both `review_tally.py` and `plan_review_tally.py` when assembling entries.
