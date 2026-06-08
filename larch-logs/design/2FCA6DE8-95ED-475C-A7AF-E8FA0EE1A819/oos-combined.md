### OOS_1: Dual-stack drift risk between bash ship path and Python CLI until E1
- **Description**: B1 keeps both the bash helpers (reachable via `LARCH_SHIP_PR_IMPL=bash` through `scripts/ship-pr.sh` and its transitive closure) and the new Python `cli.py` verbs implementing the same git/gh/ci primitives until E1 retires the bash ship path. Contract drift between the two stacks (KV keys, exit codes, behavior) would surface only on the legacy ship path or a partial cutover, where it is hard to detect. Track convergence/removal as part of E1.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh; python/cli.py
- **Phase**: design

### OOS_2: Reconsider 6 companion *_cli.py modules vs in-module main() dispatch
- **Description**: The B1 plan adds six thin companion modules (`git_cli.py`, `push_cli.py`, `pr_cli.py`, `merge_cli.py`, `gh_cli.py`, `ci_cli.py`) plus colocated test files for ~40 verbs. The `docs/python-migration.md` house style registers `(domain, verb) -> (module, main)` directly (e.g. `ship.main`, `migration_lint.main`); `report_tokens_cli.py` is the lone exception for a large multi-step pipeline. Single-verb domains like `merge` (`merge pr`) make the cost obvious — a whole companion + test + agent-lint/Makefile pins for one wrapper. Consider registering one `main(argv)` per domain module with internal subcommand dispatch and dropping the companions, keeping logic in the typed modules. Related evidence: the plan introduces `git.sync_local_main` for the CLI while the ship Python path keeps a separate `rebase._sync_local_main`, i.e. parallel implementations of the same primitive worth unifying.
- **Reviewer**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/cli.py; python/report_tokens_cli.py
- **Phase**: design
