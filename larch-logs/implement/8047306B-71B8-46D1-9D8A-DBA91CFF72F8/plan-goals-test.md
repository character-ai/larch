## Goal
Implement issue #3684: [IMPLEMENTING] sh-to-py C4b: implement step-2 dispatch.

## Implementation Plan
## Plan

Port the existing Bash behavior with minimum semantic change.

- Treat `approach-synthesis.txt == NO_SKETCHES`; base the plan on code and docs.
- Keep codex/cursor implementer manifest contracts unchanged.
- Put Step 2 dispatch, recovery-path computation, Step 4 commit wrapper, and the retained Step 2 KV envelope implementation in `python/implement_dispatch.py`.
- Put additive implement launcher CLI mains in `python/agents.py`, following the existing B4 CI launcher pattern.
- Register direct CLI verbs in `python/cli.py`.
- Replace Step 2 and Step 4 skill call sites with post-Step-0 `larch-run.sh` fences:
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement run-dispatch ...`
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement recovery-paths ...`
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement commit ...`
- Keep bare `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ...` only for pre-bootstrap call sites where `larch-run.sh` is not yet available.
- Resolve dispatcher child CLI subprocesses through `sys.executable` plus the absolute plugin CLI path from `LARCH_CLAUDE_PLUGIN_ROOT` or module location. Do not use cwd-relative `python/cli.py` for child launchers.
- Replace absorbed shell harnesses with pytest.
- Create a full surviving Step 2 contract doc before deleting the Bash dispatcher docs. It must absorb the normative contracts from the deleted Step 2 dispatcher and wrapper docs with path retargets only where possible.
- Delete retired shell scripts, sibling `.md` contracts, and shell harnesses after call-site cutover and after the surviving full Step 2 contract doc is in place.
- Append retired paths to `python/migrated-scripts.tsv`.
- Run stale-reference lint and update docs, rules, lint config, test harnesses, prompts, shell sources, comments, and `SECURITY.md` lines that name deleted paths.

## Acceptance

- `python/implement_dispatch.py` importable with all four CLI mains registered in `python/cli.py`: `implement step2-dispatch`, `implement run-dispatch`, `implement recovery-paths`, `implement commit`.
- `python/agents.py` extended with `launch_codex_implement_main` and `launch_cursor_implement_main`, registered as `agent launch-codex-implement` and `agent launch-cursor-implement`.
- `python/test_implement_dispatch.py` covers all stdout contracts, bail reasons, envelope invariants, recovery paths, commit wrapper, launcher surfaces, and 1:1 ports of the key harness assertions.
- `skills/implement/references/step2-dispatch.md` exists and fully absorbs the normative bodies of the deleted `step2-implement.md` and `run-step2-dispatch.md` with path retargets only.
- All absorbed scripts deleted after call-site cutover: `step2-implement.sh`, `run-step2-dispatch.sh`, `compute-step2-recovery-paths.sh`, `commit-implementation.sh`, `launch-codex-implement.sh`, `launch-cursor-implement.sh`, plus their `.md` siblings and all shell harness files.
- `python/migrated-scripts.tsv` updated with all 20+ deleted paths under issue `#3684`.
- `skills/implement/SKILL.md` Step 2 and Step 4 call sites use `larch-run.sh python/cli.py implement run-dispatch` and `larch-run.sh python/cli.py implement commit`.
- No shims; no `LARCH_*_IMPL` selectors.
- `make lint-retired-scripts`, `make py-lint`, `make py-test`, and `bash scripts/relevant-checks.sh` all green.

diff_lines: 9850

## Test plan
(no test plan section in plan-file)
