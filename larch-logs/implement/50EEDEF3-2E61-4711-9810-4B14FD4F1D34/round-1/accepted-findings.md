### FINDING_1: **Important** `risk-integration` `docs/linting.md:104` — The branch protection migration docs still list only `test-harnesses (1)` through `(18)`, while CI now runs shards 19 and 20. If an admin follows this list, future PRs could merge even when `test-harnesses (19)` or `(20)` fails. The same stale section also says `make test-harnesses-1` through `make test-harnesses-18` at `docs/linting.md:23`, and the rebalance snippet still uses `range(18)` at `docs/linting.md:90`. Update these references to 20 and add `test-harnesses (19)` / `(20)` to the required-check list at `docs/linting.md:104-124`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `docs/linting.md:104` — The branch protection migration docs still list only `test-harnesses (1)` through `(18)`, while CI now runs shards 19 and 20. If an admin follows this list, future PRs could merge even when `test-harnesses (19)` or `(20)` fails. The same stale section also says `make test-harnesses-1` through `make test-harnesses-18` at `docs/linting.md:23`, and the rebalance snippet still uses `range(18)` at `docs/linting.md:90`. Update these references to 20 and add `test-harnesses (19)` / `(20)` to the required-check list at `docs/linting.md:104-124`. I did not modify files. I also checked shell syntax with `bash -n` on the touched shell scripts and verified `scripts/test-dispatch-code-voters.sh` has 8 `if section_runs` guards.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: docs/linting.md:106-123
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Branch protection checklist lists required checks only through test-harnesses (18). Admin configures required checks from this list and omits (19)-(20); failing jobs on new shards may not block merge. Add bullets for test-harnesses (19) and (20) alongside the existing list.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: docs/linting.md:106-124
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Branch protection checklist omits required check names for test-harnesses (19) and (20). Admin configures branch protection from this list and leaves new matrix jobs non-required so failures on shards 19-20 may not block merges. Add bullets for test-harnesses (19) and (20).
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: docs/linting.md:106-124
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch protection checklist omits test-harnesses (19) and (20). Admins copy a required-check list that stops at (18); merge gates can stay green without gating new shards. Add bullets for test-harnesses (19) and test-harnesses (20) before lint-mermaid.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: docs/linting.md:23
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Usage CI prose still caps the harness matrix at test-harnesses-18. Readers and internal runbooks assume 18 matrix jobs while CI runs 20; failure triage or automation can reference a non-existent ceiling. Update the prose to test-harnesses-20 or avoid a hard-coded last shard index.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: docs/linting.md:23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] CI Usage bullet still caps harness matrix at test-harnesses-18 while CI/Makefile use 20 shards. Readers trust the first Usage bullet and mis-state how many parallel harness jobs exist or omit re-running shards 19-20 when debugging. Update the prose to test-harnesses-20 or avoid a hardcoded last index.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: docs/linting.md:23
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Usage CI bullet still ends harness matrix at test-harnesses-18 while CI uses 20 shards. Readers and tooling assume only 18 parallel harness legs; shard 19/20 behavior and failures are mis-attributed or omitted from operational docs. Update the bullet to test-harnesses-20 or describe the matrix without a stale numeric ceiling.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: docs/linting.md:23 docs/linting.md:90
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Residual shard-count literals still say 18 in the Usage CI paragraph and `range(18)` bin-packing snippet while other sections describe 20 shards. Readers or tooling underestimate matrix width or copy a 18-bin rebalance snippet against a 20-shard Makefile, skewing ops and shard rebalance work. Update the harness range text to 1..20 and adjust the example `range(...)` to match (or derive count from Makefile parsing).
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: docs/linting.md:23-24
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Usage CI bullet still documents test-harnesses matrix through shard 18 only. Readers and operators assume 18 matrix cells while CI and Makefile use 20; contradicts plan File 6 stale-18 doc sweep and the updated CI sharding section in the same file. Update the bullet to `make test-harnesses-1` through `make test-harnesses-20`.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: docs/linting.md:90
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] LPT rebalance snippet still uses range(18) after the shard expansion to 20. Copy-paste rebalance packs into 18 bins then maps awkwardly to 20 Makefile shard lines. Use range(20) or tie bin count to the documented shard total.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: docs/linting.md:90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] LPT example uses range(18) while the live matrix is 20 shards. Copy-paste rebalancing packs into 18 bins while CI runs 20 jobs; uneven or wrong Makefile shard lines. Use range(20) or derive bin count from the Makefile shard list.
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** — [`docs/linting.md:106-123`](docs/linting.md): The “**Branch protection migration**” checklist lists required checks `test-harnesses (1)` … `(18)` only. After this branch, CI emits `test-harnesses (19)` and `(20)` as well; branch protection that follows the doc literally can **omit** those two checks as merge gates while the workflow still runs them. **Suggested fix:** append `- test-harnesses (19)` and `- test-harnesses (20)` to the bullet list (and align any ruleset guidance in the same paragraph).
- **Reviewer**: dyn-ungated-assertions-output.txt
- **Concern**: - **correctness** — [`docs/linting.md:106-123`](docs/linting.md): The “**Branch protection migration**” checklist lists required checks `test-harnesses (1)` … `(18)` only. After this branch, CI emits `test-harnesses (19)` and `(20)` as well; branch protection that follows the doc literally can **omit** those two checks as merge gates while the workflow still runs them. **Suggested fix:** append `- test-harnesses (19)` and `- test-harnesses (20)` to the bullet list (and align any ruleset guidance in the same paragraph). **Harness section split (scout checklist 1–4, correctness):** In [`scripts/test-dispatch-code-voters.sh`](scripts/test-dispatch-code-voters.sh), the last `fi  # end section: regressions-r3-codex` is at `437`, then only a blank line before `echo "PASS: test-dispatch-code-voters.sh"` at `466` — no ungated assertions. There are **eight** `if section_runs` guards at `163,193,264,313,335,357,396,439`. Regression 3 **claude** assertions live only under `edge-and-r3-claude` (`193–262`); the **codex** half is only under `regressions-r3-codex` (`439–463`) — no duplicate claude block in the codex section. In [`skills/review-and-fix/scripts/test-review-and-fix.sh`](skills/review-and-fix/scripts/test-review-and-fix.sh), `fi  # end section: convergence` is at `1945`, then blank lines and `echo "test-review-and-fix: ok"` at `1948` — no ungated tests after the last section. `write_prior_round` is defined inside `convergence` immediately after `if section_runs convergence` (`1228–1239`) and only used from that block onward. `run_orchestrator_case` is defined and used only inside `dispatch` (`253–288`); convergence does not call it, so `--section convergence` does not depend on a helper that would be skipped.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.md (new --section paragraph)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dispatch section described as roughly first 1200 lines; dispatch block ends nearer line 1226. Minor confusion when mapping doc to file. Rephrase to avoid a fixed line count tied to the dispatch section boundary.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** — [`docs/linting.md:23`](docs/linting.md): The “**CI**” usage bullet still says harnesses run via `make test-harnesses-1` through `make test-harnesses-18`, while the same PR updates the dedicated “CI sharding” section and workflow to **20** shards. Readers and copy-pasted automation can assume an 18-wide matrix and mis-map failures to the wrong shard row. **Suggested fix:** change the range to `test-harnesses-20` (or drop a hard-coded upper bound and point at the Makefile / workflow).
- **Reviewer**: dyn-ungated-assertions-output.txt
- **Concern**: - **correctness** — [`docs/linting.md:23`](docs/linting.md): The “**CI**” usage bullet still says harnesses run via `make test-harnesses-1` through `make test-harnesses-18`, while the same PR updates the dedicated “CI sharding” section and workflow to **20** shards. Readers and copy-pasted automation can assume an 18-wide matrix and mis-map failures to the wrong shard row. **Suggested fix:** change the range to `test-harnesses-20` (or drop a hard-coded upper bound and point at the Makefile / workflow).
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** — [`docs/linting.md:90`](docs/linting.md): The LPT snippet still uses `range(18)` for bin count. With twenty CI shards, copy-paste rebalancing uses the wrong number of bins vs the live matrix (same class of drift called out in past run-log findings for 14 vs 18). **Suggested fix:** use `range(20)` or derive the bin count from the discovered shard list so it cannot drift.
- **Reviewer**: dyn-ungated-assertions-output.txt
- **Concern**: - **correctness** — [`docs/linting.md:90`](docs/linting.md): The LPT snippet still uses `range(18)` for bin count. With twenty CI shards, copy-paste rebalancing uses the wrong number of bins vs the live matrix (same class of drift called out in past run-log findings for 14 vs 18). **Suggested fix:** use `range(20)` or derive the bin count from the discovered shard list so it cannot drift.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: skills/review-and-fix/scripts/test-review-and-fix.md:9-11
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dispatch section documented by approximate line count (~1200 lines). Line count drifts on the next harness edit and misleads readers about where convergence begins. Describe by behavior only or cite stable section markers instead of line counts.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: docs/linting.md:105-124
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Branch protection checklist ends at test-harnesses (18) after expanding CI to 20 matrix shards. Admins may omit required status checks for matrix jobs 19-20; merges can satisfy protection while those harness legs are not merge-blocking or are misaligned with enforced CI. Add bullets for `test-harnesses (19)` and `test-harnesses (20)` (and rulesets if used).
- **Suggested revision**: Address the concern above.


