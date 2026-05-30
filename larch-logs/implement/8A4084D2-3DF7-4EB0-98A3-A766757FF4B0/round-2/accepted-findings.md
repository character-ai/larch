### FINDING_11: mermaid-safe-content.md still documents root npm audit
- **Reviewer(s)**: dyn-mermaid-path-sync-output.txt
- **Severity**: latent
- **Concern**: After Part 3 removed root `package.json`, the shared skill contract still tells maintainers to run bare `npm audit` from repo root, breaking the documented bump workflow vs `mermaid-lint/package.json` and `(cd mermaid-lint && npm ci)` used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mermaid-path-sync-output.txt: Change the sentence to run audit from the toolchain directory (for example, “Run `(cd mermaid-lint && npm audit)` opportunistically during bumps”) so it matches `docs/installation-and-setup.md`, `docs/linting.md`, and the `(cd mermaid-lint && npm ci)` pattern used everywhere else.


### FINDING_2: Already-latest path repairs marketplace but does not slim active plugin install
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When the operator is already on latest stable, marketplace cone repair can run without uninstall+install. Legacy fat dirs (`larch-logs/`, install-time `node_modules/`, etc.) can remain in the active `PLUGIN_ROOT` cache until a version bump, so disk/speed wins are deferred for always-current users.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After marketplace repair on the already-latest branch (or when legacy larch-logs/ was detected), run uninstall+install or document mandatory one-time reinstall.
  - From cursor-specialist-security-output.txt: Resync cache on cone repair (same-version install) or document that only marketplace—not active install—was slimmed
  - From cursor-specialist-edge-cases-output.txt: Detect legacy install artifacts on idempotent path and force one-time uninstall+install; note restart when slimming reinstall runs


### FINDING_3: Already-latest branch mutates marketplace contrary to closed plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The already-latest early-exit calls `refresh_larch_marketplace` when the cone check fails, contradicting the closed plan decision that the idempotent path performs no marketplace mutation. Users on latest stable with a legacy full marketplace clone can trigger remove + sparse re-add on every `/upgrade-larch` without a plugin reinstall, whereas the plan intended one-time migration on the next actual upgrade only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Remove marketplace repair from the already-latest branch; keep repair only on the upgrade path; revert related doc claims in upgrade-larch.md step 2 and docs/installation-and-setup.md Upgrade paragraph.


### FINDING_4: Failed marketplace remove is ignored before sparse re-add
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: latent
- **Concern**: In `refresh_larch_marketplace`, failed `claude plugin marketplace remove` is swallowed (`|| true`) but `add_sparse_larch_marketplace` still runs while `$MARKETPLACE_CLONE` may remain. `marketplace add` can fail with already-exists, tripping `ERR`/`recover()` after uninstall on the full upgrade path—leaving no installed plugin and a wedged marketplace until manual `rm -rf` and recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed unless clone dir is absent; align with recovery banner rm -rf step.
  - From cursor-specialist-security-output.txt: Fail closed on remove failure or require manual rm -rf of MARKETPLACE_CLONE before add
  - From cursor-specialist-edge-cases-output.txt: Fail closed on remove failure for re-add path, or rm -rf clone before add when remove fails
  - From dyn-shell-upgrade-logic-output.txt: Before `add_sparse_larch_marketplace` in both re-add branches, if `remove_larch_marketplace` fails (or unconditionally when `[ -d "$MARKETPLACE_CLONE" ]`), run `rm -rf -- "$MARKETPLACE_CLONE"` and log that automatic cleanup ran; then call `add_sparse_larch_marketplace`. Keep `recover()` as the backstop for add/network failures.
  - From dyn-migration-path-risk-output.txt: Mirror `recover()` inside the automated re-add paths: if `remove_larch_marketplace` fails (or before any sparse re-add), `rm -rf -- "$MARKETPLACE_CLONE"` when `[ -d "$MARKETPLACE_CLONE" ]`, then call `add_sparse_larch_marketplace`; optionally log that automatic cleanup ran. Keep the existing warning/recovery banner as a backstop for add/network failures.


### FINDING_8: upgrade-larch.md stale step cross-reference (prune step 8 vs 7)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: After step renumbering, the idempotency bullet still says prune runs at step 8 while prune is now step 7, misdirecting readers tracing behavior cross-references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Change step 8 to step 7 in the idempotency bullet.


