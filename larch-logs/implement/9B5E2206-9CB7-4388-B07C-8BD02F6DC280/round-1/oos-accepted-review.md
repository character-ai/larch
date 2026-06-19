### OOS_1: [OUT_OF_SCOPE] `skills/pause/SKILL.md` uses `-x` guard on non-executable `python/cli.py`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `/pause` repo fallback checks `python/cli.py` with `-x` even though the shipped file is not executable and is invoked via `python3`. When `REPO` is unset in the live design env, the fallback is skipped and `pause-save` may persist state without `--repo`, causing resume to target the wrong ambient repository. Tests may mask this by chmodding a fake CLI executable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Use -f or -r for python/cli.py and adjust the pause-skill test fixture so cli.py is not chmod +x.
  - From codex-specialist-edge-cases-output.txt: Use -f or -r, or remove the guard and let python3 gh resolve-repo fail open; update the pause test to keep fake python/cli.py non-executable.


### OOS_2: [OUT_OF_SCOPE] `phantom-probe.md` still names retired bash thin implementation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/references/phantom-probe.md` still names `lib-phantom-probe.sh` as the checkpoint-probe thin implementation, but runtime combined checkpoints use `python/phantom.py`. Maintainers may edit the wrong file expecting 1.r/4.r/7.r/7a.r behavior to change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update reference to name python/phantom.py for combined checkpoints; reserve lib-phantom-probe.sh for phantom-probe-with-warn.sh only.


