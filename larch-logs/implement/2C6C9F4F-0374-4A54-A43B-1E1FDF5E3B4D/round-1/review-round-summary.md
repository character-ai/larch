# Review Round 1

- Mode: `diff`
- 8 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Stop hook jq runtime failure emits truncated block JSON
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The plan acceptance criteria require byte-identical `jq -cn` vs static-fallback block JSON for `hook-stop-fail-close.sh`. When `jq -cn` fails at runtime (`skills/implement/scripts/hook-stop-fail-close.sh:80-81`), the `||` branch emits a shortened single-line reason that omits the multiline `REASON`, the active tmpdir basename, and the operator-escape instructions present in the successful jq path. Operators who hit the jq runtime fallback during a post-/review Stop block see less actionable text than the jq success path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror `deny-edit-write.sh`: use a fixed-literal static JSON for jq-absent and jq-runtime-failure paths, or reconstruct the full reason without jq before `hook_emit`.
  - From cursor-specialist-edge-cases-output.txt: Align the static fallback with the full REASON template via jq --arg, or add a harness asserting both branches emit equivalently actionable JSON.


### FINDING_3: Pre-commit shell hooks not narrowed to residual manifest
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-residual-scope-output.txt
- **Severity**: important
- **Concern**: The plan's `### UPDATED: .pre-commit-config.yaml` section calls for narrowing `shellcheck`, `bash-syntax-check`, and `lint-bash32` file selection to residual-manifest paths. CI shellcheck now feeds only `python3 python/cli.py residual-bash paths --null-delimited` into `xargs`, but pre-commit still uses `types: [shell]` / `files: \.(sh|inc\.bash)$` with no manifest `files:` filter. Wrapper scripts scope whole-repo scans via the manifest, but pre-commit still triggers on any shell file change repo-wide. Local `make shellcheck` can still scan every `*.sh`, while CI omits paths missing from `scripts/residual-bash-paths.txt`, diverging local and CI enumeration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Point pre-commit `files:` at manifest rows (or a generated glob) as the plan specified, keeping positional handling inside the wrappers.
  - From codex-specialist-correctness-output.txt: Make pre-commit selection manifest-driven or intersect positional filenames with `python3 python/cli.py residual-bash paths --root "$REPO_ROOT"`.
  - From dyn-residual-scope-output.txt: Add manifest-based `files:` filters (or always route zero-arg pre-commit wrappers through `residual-bash paths`) so local and CI enumerate the same set; add a CI or pytest gate that fails when `git ls-files '*.sh' '*.inc.bash'` diverges from manifest output.


### FINDING_7: Residual manifest still includes non-residual orchestration and helper shells
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: blocking
- **Concern**: `scripts/residual-bash-paths.txt:22-148` still includes non-residual Bash utilities, live orchestration bodies, and sourced helper libraries despite the E3 residual inventory limits. CI now treats those paths as approved residual Bash via `python3 python/cli.py residual-bash paths --null-delimited` instead of blocking or requiring port/delete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Remove non-residual entries from the manifest; port/delete them or publish blockers if prerequisites are incomplete.


### FINDING_9: lint-bash32 manifest mode skips git ls-files intersection
- **Reviewer(s)**: dyn-residual-scope-output.txt
- **Severity**: important
- **Concern**: When the manifest exists, `scripts/lint-bash32.sh:50-62` lists manifest paths only and does not intersect with `git ls-files --cached --others --exclude-standard`. The contract doc still describes untracked-aware `git ls-files` enumeration. The plan required preserving untracked non-ignored residual scanning via intersection, not a pure manifest replace. A tracked `*.sh` omitted from the manifest is skipped by `make lint-bash32` even though pre-commit may still lint it positionally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-residual-scope-output.txt: Discover shell candidates via `git ls-files` (or find fallback), intersect with the manifest set, then scan; update `lint-bash32.md` to match.


### FINDING_10: Manifest reader lacks existence/completeness validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-residual-scope-output.txt, dyn-retirement-cleanup-output.txt
- **Severity**: important
- **Concern**: `python/residual_bash.py:34-55` validates manifest syntax but not on-disk presence. Linters skip missing manifest rows quietly (`[[ -f "$path" ]] || return 0`). Stale manifest rows or a new tracked shell not added to the manifest let `make lint-bash32` and CI shellcheck exit 0 without scanning those files. There is no automated completeness check beyond `python/test_residual_bash.py` spot assertions; the plan required a whole-tree compliance pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add optional `--check-exists` for CI or have linters warn on manifest paths missing under ROOT.
  - From cursor-specialist-testing-output.txt: Add existence validation test or CLI flag; fail on missing manifest paths.
  - From dyn-residual-scope-output.txt: Add a gate (pytest or `make lint`) comparing manifest output to `git ls-files '*.sh' '*.inc.bash'`; optionally warn or fail on manifest rows whose files are missing.
  - From dyn-retirement-cleanup-output.txt: Add a pytest that diffs tracked shell paths against manifest output (both directions) and fails on any orphan or missing row.


### FINDING_11: Missing manifest-scoped linter harness fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-residual-scope-output.txt
- **Severity**: important
- **Concern**: Plan-required manifest-scoped linter harness fixtures were not added. `scripts/test-lint-bash32.sh`, `scripts/test-lint-awk-multibyte-regex.sh`, and `scripts/test-lint-renderer-substitution-safety.sh` still use bare `TMPROOT` trees without `scripts/residual-bash-paths.txt` and rely on legacy `find`/`git ls-files` fallback, so accidental coverage loss from manifest drift is not regression-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add TMPROOT manifest fixtures with in-scope and out-of-scope shells; assert scan vs skip per linter.
  - From codex-specialist-testing-output.txt: Add fixture manifests and assertions for in-scope residual scans, out-of-scope skips, `--root` fixture manifest use, and standalone `.awk` coverage.
  - From dyn-residual-scope-output.txt: Add cases that copy a fixture manifest into `TMPROOT`, place out-of-scope shell fixtures, and assert they are not scanned while in-scope residual paths and standalone `.awk` files still are.


### FINDING_12: oos-file-conflict-deps.sh uses unbound SCRIPT_DIR
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/oos-file-conflict-deps.sh:13` initializes `REPO_ROOT` from `SCRIPT_DIR` before `SCRIPT_DIR` is defined. Running `bash skills/implement/scripts/oos-file-conflict-deps.sh --help` exits with `SCRIPT_DIR: unbound variable` before argument parsing, breaking the OOS dependency helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Restore SCRIPT_DIR before REPO_ROOT or derive REPO_ROOT directly from BASH_SOURCE.


### FINDING_14: Topology and docs mislabel full manifest as narrow residual inventory
- **Reviewer(s)**: dyn-retirement-cleanup-output.txt
- **Severity**: important
- **Concern**: `skills/shared/topology.tsv:20`, `AGENTS.md:149`, and `docs/python-migration.md:185-195` describe residual Bash as a narrow deliberate inventory (hooks, linters, thin wrappers, sleep helper, harnesses), but `scripts/residual-bash-paths.txt` lists all ~163 tracked shells including full `/design` and `/implement` orchestration wrappers. That mislabels the post-E3 Bash surface and conflicts with the issue DoD ("hooks + linters + thin wrappers only"). Operators will read "residual = small" but linters scope "residual = everything left."
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-cleanup-output.txt: Update the topology row description to "all remaining tracked Bash (hooks, linters, thin wrappers, G-track orchestration fences, harnesses)" or split the manifest into category sections and point topology at the authoritative enumerator contract.
  - From dyn-retirement-cleanup-output.txt: Align prose with the manifest's actual role (linter/CI enumeration of **all** remaining tracked Bash) and distinguish that from the issue's long-term "terminal inventory" goal, or shrink the manifest to the narrow categories and port/delete orchestration shells per the original compliance pass.


