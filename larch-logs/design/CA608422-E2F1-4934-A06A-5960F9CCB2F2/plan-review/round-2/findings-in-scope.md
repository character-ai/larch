Merging the seven reviewer inputs into a normalized finding list: overlapping items on `test_ci_monitor.py` and `ship-pr.md`, with the rest kept separate.
### FINDING_1: SECURITY.md Step 0 still documents Cursor-first omitted-`--coder` routing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Step 0 paragraph in `SECURITY.md` still describes a Cursor-first reversal and tells operators to pin `--coder=codex` for Codex. After #3337, Codex is the omitted-`--coder` default; unchanged text misstates product direction and instructs operators to pin the tool they already get by default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the ~105 edit, replace Cursor-first reversal wording with Codex-first (#3337), update the availability arrow to Codex then Cursor then Claude, and invert pin guidance (e.g. operators who want Cursor pin --coder=cursor); keep explicit-pin fail-closed sentences

### FINDING_2: `python/test_ci_monitor.py` not in plan; full `make py-test` will fail after codex-first flip
- **Reviewer(s)**: Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan limits Python test updates to `test_config.py` (and optionally `test_agents.py` / `test_rebase.py`), but `FIXER_TIER_ORDER` drives `ci_monitor.run_ci_fix` / `evaluate_failure` / `monitor`. After `config.py` flips to codex-first, tests that assert `launch_calls == ["cursor"]`, mock only Apply CI fixes (cursor), or assume `start_attempt=0` hits Cursor will fail under full `make py-test` even if a narrowed pytest list in the plan passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add python/test_ci_monitor.py to the plan: retarget tier-order assertions and commit-script mocks to codex-first (and rotation attempt 0/1 comments); run make py-test in Testing strategy
  - From Cursor-Requirements: Add ### UPDATED: python/test_ci_monitor.py: retarget cursor-first assertions/stubs/comments (e.g. launch_calls == ["codex"], codex commit-msg keys, line 900 rotation comment) and list the file in Testing strategy alongside test_config.py

### FINDING_3: `docs/linting.md` omitted from implement-bootstrap doc sync
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: `implement-bootstrap.md` requires `docs/linting.md` to stay in sync for Step 0 wording, but the plan updates bootstrap without `linting.md`. The Makefile harness table can still document omitted-`--coder` as Cursor → Codex → Claude after Part 2 lands, giving operators and contributors the wrong routing contract without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Extend Part 2 doc sync to docs/linting.md (line ~272) per bootstrap.md:169; add docs/linting.md to the post-edit grep list in Failure modes

### FINDING_4: `scripts/ship-pr.md` still Cursor-centric for tier order and `first-fixer-non-health`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan covers arrow-order edits but not first-fixer tier-name literals tied to cursor-first. After a codex-first flip, prose at line 72 (and related waterfall lines) can still name the Cursor CI-fix launcher / first tier (`cursor`) for `first-fixer-non-health`, disagreeing with codex-first base order and rotation-aware `first_tier` from `start_attempt % 3`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit ship-pr.md edits: line 72 Codex (or first-tier) CI-fix launcher; line 118 first tier (codex) and codex→cursor→claude launch order; line 154 drop literal cursor tier (first tier of rotated list)
  - From Cursor-Pragmatic: Extend the `ship-pr.md` grep/sync pass to line 72 (and any similar first-fixer sentences): first-tier launcher wording, not Cursor-only

### FINDING_5: `skills/implement/SKILL.md` Exit 3 still names Cursor-only CI-fix launcher
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan rewrites the Step 0 `phase_coder_select` paragraph (~511) but Exit 3 (~1169) still says `first-fixer-non-health` fires when the Cursor CI-fix launcher reports `LAUNCHER_FAILURE_CLASS=other`. After codex-first `run_ci_fix_vendor`, bail keys on the rotated first tier (`first_tier` from `start_attempt % 3`), which is Codex on attempt 0 — not Cursor-only. Operators can mis-debug Exit 3 / autonomous CI-fix as a Cursor-only path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a `skills/implement/SKILL.md` doc-sync step for ~1169: describe first-tier / rotated-first-tier CI-fix launcher (match `scripts/ship-pr.md:154`), not Cursor by name

---

**Merge notes (for voters, not machine output):** Seven source slots collapsed to five findings. `test_ci_monitor.py` (Cursor-Edge + Cursor-Requirements) and `ship-pr.md` first-fixer / tier-order drift (Cursor-Innovation + Cursor-Pragmatic) were merged as one behavioral risk each. `SECURITY.md`, `docs/linting.md`, and `skills/implement/SKILL.md` remain separate because they need distinct edits. No `[OUT_OF_SCOPE]` tags in input; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` (non-empty merge).
