## Goal
Implement issue #5168: [IMPLEMENTING] [py-code-quality] Packaging 2/9: move VCS modules into larch.git.

## Implementation Plan
**Problem.** Git and GitHub plumbing sits flat in `python/` with no package boundary. `git` (16 importers) and `gh` (18) are shared across many domains, and the related VCS surface (rebase, push, PR creation, merge) is scattered.

**Proposed change.** Move the VCS surface into `larch.git` (and a sibling `larch.gh` if `/design` prefers the split): `git`, `gh`, `repo_roots`, `rebase`, `push`, `pr`, `pr_body`, `merge`. Rewrite all importers to `from larch.git import ...`. Update the `cli.py` `_REGISTRY` entries that point at these modules. Exact module set and any git/gh subpackage split is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats (`MERGE_RESULT` literals, PR-body grammar). Pure move plus import rewrites.

**Acceptance.** VCS modules live under `larch.git`; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations unchanged.

**Effort / risk.** Medium / medium.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
