### OOS_1: [OUT_OF_SCOPE] Rebase Checkpoint Macro still documents prompt-side `1.r` invocation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-architecture-output.txt
- **Severity**: nit
- **Concern**: The Rebase Checkpoint Macro still claims every checkpoint (`1.r`, `4.r`, `7.r`, `7a.r`) uses one prompt-side Bash invocation, but `1.r` is now absorbed inside `python/cli.py bootstrap invoke`. Conflicting contracts in one section make it easy for implementers to reintroduce a standalone `rebase-checkpoint-probe.sh 1.r` fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Qualify that 1.r is envelope-driven; only 4.r/7.r/7a.r use direct probe fences.
  - From dyn-architecture-output.txt: Rewrite the thin-implementation bullet to split call sites: `1.r` is bootstrap-envelope only; `4.r` / `7.r` / `7a.r` remain one foreground probe each. Drop the blanket "each checkpoint" wording.


